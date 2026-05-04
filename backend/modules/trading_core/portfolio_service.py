"""Portfolio Service — PHASE 2: REAL PnL CALCULATION

MongoDB-backed portfolio management:
- Apply fills → update positions
- Calculate REAL unrealized PnL using LIVE mark prices from PriceService
- equity = balance + unrealized (equity ≠ balance)
- Persist portfolio state
- Restore on startup

NO MOCKS: mark_price from PriceService only
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
from motor.motor_asyncio import AsyncIOMotorClient

from modules.exchange.models import OrderResponse
from modules.market_data.price_service import get_price_service

logger = logging.getLogger(__name__)


class PortfolioService:
    """Portfolio service with MongoDB persistence."""
    
    def __init__(self, db_client: AsyncIOMotorClient, account_id: str = "paper_default"):
        self.db = db_client.trading_db
        self.account_id = account_id
    
    async def ensure_indexes(self):
        """Create indexes for portfolio collections."""
        await self.db.positions.create_index([("account_id", 1), ("symbol", 1), ("status", 1)])
        await self.db.portfolio_snapshots.create_index([("account_id", 1)])
        await self.db.fills.create_index([("account_id", 1), ("timestamp", -1)])
        logger.info("[PortfolioService] Indexes created")
    
    async def apply_fill(self, fill: OrderResponse) -> Dict[str, Any]:
        """Apply fill to portfolio (update position, balance, PnL).
        
        This is the SINGLE SOURCE OF TRUTH for portfolio updates.
        All position/balance changes flow through fills.
        
        Args:
            fill: OrderResponse from exchange
        
        Returns:
            Updated position data
        """
        logger.info(
            f"[PortfolioService] Applying fill: {fill.symbol} {fill.side} "
            f"{fill.filled_quantity} @ ${fill.avg_fill_price}"
        )
        
        # 1. Save fill record
        await self._save_fill(fill)
        
        # 2. Update or create position
        position = await self._update_position(fill)
        
        # 3. Update portfolio snapshot (balance, equity, PnL)
        await self._update_portfolio_snapshot()
        
        logger.info(
            f"[PortfolioService] Fill applied: {fill.symbol} position_size={position.get('size', 0)}"
        )
        
        return position
    
    async def _save_fill(self, fill: OrderResponse):
        """Save fill to database."""
        fill_doc = {
            "fill_id": f"fill-{fill.order_id}",
            "account_id": self.account_id,
            "order_id": fill.order_id,
            "client_order_id": fill.client_order_id,
            "symbol": fill.symbol,
            "side": fill.side,
            "quantity": fill.filled_quantity,
            "price": fill.avg_fill_price,
            "fee": 0.0,  # TODO: extract from fill.raw if available
            "timestamp": datetime.now(timezone.utc),
            "raw": fill.raw,
        }
        
        await self.db.fills.insert_one(fill_doc)
        logger.debug(f"[PortfolioService] Fill saved: {fill_doc['fill_id']}")
    
    async def _update_position(self, fill: OrderResponse) -> Dict[str, Any]:
        """Update or create position from fill.
        
        Logic:
        - BUY (LONG): increase position size
        - SELL (SHORT): increase position size (negative direction)
        - Position size = sum of all fills for this symbol
        """
        symbol = fill.symbol
        side_multiplier = 1 if fill.side == "BUY" else -1
        fill_qty = fill.filled_quantity * side_multiplier
        fill_price = fill.avg_fill_price
        
        # Find existing position
        position = await self.db.positions.find_one({
            "account_id": self.account_id,
            "symbol": symbol,
            "status": "OPEN"
        })
        
        if position:
            # Update existing position
            old_size = position["size"]
            old_entry = position["entry_price"]
            
            # Calculate new average entry price
            new_size = old_size + fill_qty
            
            if new_size == 0:
                # Position closed
                position["status"] = "CLOSED"
                position["closed_at"] = datetime.now(timezone.utc)
                position["size"] = 0
                position["realized_pnl"] = position.get("unrealized_pnl", 0)
                
                await self.db.positions.update_one(
                    {"_id": position["_id"]},
                    {"$set": position}
                )
                
                logger.info(f"[PortfolioService] Position closed: {symbol} PnL=${position['realized_pnl']:.2f}")
                return position
            
            else:
                # Position still open, update entry price
                if abs(new_size) > abs(old_size):
                    # Adding to position
                    new_entry = ((old_entry * abs(old_size)) + (fill_price * abs(fill_qty))) / abs(new_size)
                else:
                    # Reducing position (keep old entry)
                    new_entry = old_entry
                
                position["size"] = new_size
                position["entry_price"] = new_entry
                position["side"] = "LONG" if new_size > 0 else "SHORT"
                position["updated_at"] = datetime.now(timezone.utc)
                
                await self.db.positions.update_one(
                    {"_id": position["_id"]},
                    {"$set": position}
                )
                
                logger.info(f"[PortfolioService] Position updated: {symbol} size={new_size:.4f} entry=${new_entry:.2f}")
                return position
        
        else:
            # Create new position
            # Extract fee from fill
            fill_fee = 0.0
            if fill.raw and isinstance(fill.raw, dict):
                fill_fee = fill.raw.get("total_fee", 0.0)
            
            new_position = {
                "account_id": self.account_id,
                "symbol": symbol,
                "side": "LONG" if fill_qty > 0 else "SHORT",
                "size": fill_qty,
                "entry_price": fill_price,
                "entry_fee": fill_fee,  # Track entry fee
                "mark_price": fill_price,  # Initial mark = entry
                "unrealized_pnl": 0.0,
                "unrealized_pnl_pct": 0.0,
                "realized_pnl": 0.0,  # Initialize realized PnL
                "status": "OPEN",
                "opened_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc),
                "closed_at": None,
            }
            
            await self.db.positions.insert_one(new_position)
            
            logger.info(f"[PortfolioService] Position opened: {symbol} {new_position['side']} size={fill_qty:.4f} @ ${fill_price:.2f}, fee=${fill_fee:.2f}")
            return new_position
    
    async def _update_portfolio_snapshot(self):
        """Update portfolio-level metrics (balance, equity, PnL).
        
        CRITICAL:
        - balance = cash + realized PnL (changes only on close)
        - equity = balance + unrealized PnL (changes with mark price)
        - equity ≠ balance (unless no open positions)
        """
        # Get all open positions
        positions = await self.db.positions.find({
            "account_id": self.account_id,
            "status": "OPEN"
        }).to_list(length=100)
        
        # Sum unrealized PnL from positions (already calculated from mark_price)
        total_unrealized = sum(p.get("unrealized_pnl", 0) for p in positions)
        
        # Get realized PnL from closed positions
        closed_positions = await self.db.positions.find({
            "account_id": self.account_id,
            "status": "CLOSED"
        }).to_list(length=1000)
        
        total_realized = sum(p.get("realized_pnl", 0) for p in closed_positions)
        
        # Get initial balance from exchange account
        exchange_account = await self.db.exchange_accounts.find_one({
            "account_id": self.account_id
        })
        
        initial_balance = exchange_account.get("balance_usdt", 10000) if exchange_account else 10000
        
        # Calculate equity
        balance = initial_balance + total_realized
        equity = balance + total_unrealized
        total_pnl = total_realized + total_unrealized
        
        # Calculate risk heat
        total_exposure = sum(abs(p["size"] * p["entry_price"]) for p in positions)
        heat = total_exposure / balance if balance > 0 else 0
        
        # Update or create snapshot
        snapshot = {
            "account_id": self.account_id,
            "balance": balance,
            "equity": equity,
            "realized_pnl": total_realized,
            "unrealized_pnl": total_unrealized,
            "total_pnl": total_pnl,
            "risk_heat": heat,
            "open_positions_count": len(positions),
            "updated_at": datetime.now(timezone.utc),
        }
        
        await self.db.portfolio_snapshots.update_one(
            {"account_id": self.account_id},
            {"$set": snapshot},
            upsert=True
        )
        
        logger.debug(
            f"[PortfolioService] Portfolio snapshot updated: "
            f"balance=${balance:.2f}, equity=${equity:.2f}, PnL=${total_pnl:.2f}"
        )
    
    async def get_portfolio_state(self) -> Dict[str, Any]:
        """Get current portfolio state.
        
        Returns:
            Portfolio snapshot with positions
        """
        snapshot = await self.db.portfolio_snapshots.find_one({"account_id": self.account_id})
        
        if not snapshot:
            # Initialize default
            snapshot = {
                "account_id": self.account_id,
                "balance": 10000.0,
                "equity": 10000.0,
                "realized_pnl": 0.0,
                "unrealized_pnl": 0.0,
                "total_pnl": 0.0,
                "risk_heat": 0.0,
                "open_positions_count": 0,
                "updated_at": datetime.now(timezone.utc),
            }
        
        # Remove _id
        snapshot.pop("_id", None)
        
        # Get positions
        positions = await self.db.positions.find({
            "account_id": self.account_id,
            "status": "OPEN"
        }).to_list(length=100)
        
        # Remove _id from positions
        for pos in positions:
            pos.pop("_id", None)
        
        snapshot["positions"] = positions
        
        return snapshot
    
    async def update_mark_prices_and_pnl(self) -> Dict[str, Any]:
        """Update mark prices for all open positions and recalculate unrealized PnL.
        
        This should be called periodically (e.g., every 1-2s) to keep positions fresh.
        
        CRITICAL:
        - Fetches LIVE mark prices from PriceService
        - Calculates unrealized PnL = (mark - entry) * size
        - Updates equity = balance + unrealized
        - equity ≠ balance (equity changes with price, balance only with realized)
        
        Returns:
            Updated portfolio snapshot
        """
        # Get all open positions
        positions = await self.db.positions.find({
            "account_id": self.account_id,
            "status": "OPEN"
        }).to_list(length=100)
        
        if not positions:
            # No positions → just return snapshot
            return await self.get_portfolio_state()
        
        # Get price service
        price_service = await get_price_service()
        
        # Update each position with live mark price
        for position in positions:
            symbol = position["symbol"]
            entry_price = position["entry_price"]
            size = position["size"]
            side = position["side"]
            
            try:
                # Fetch LIVE mark price
                mark_price = await price_service.get_mark_price(symbol)
                
                # Calculate unrealized PnL
                if side == "LONG":
                    unrealized_pnl = (mark_price - entry_price) * abs(size)
                else:  # SHORT
                    unrealized_pnl = (entry_price - mark_price) * abs(size)
                
                unrealized_pnl_pct = (unrealized_pnl / (entry_price * abs(size))) * 100 if (entry_price * abs(size)) > 0 else 0
                
                # Update position in DB
                await self.db.positions.update_one(
                    {"_id": position["_id"]},
                    {"$set": {
                        "mark_price": mark_price,
                        "unrealized_pnl": unrealized_pnl,
                        "unrealized_pnl_pct": unrealized_pnl_pct,
                        "updated_at": datetime.now(timezone.utc),
                    }}
                )
                
                logger.debug(
                    f"[PortfolioService] Updated {symbol}: entry=${entry_price:.2f}, "
                    f"mark=${mark_price:.2f}, PnL=${unrealized_pnl:.2f} ({unrealized_pnl_pct:+.2f}%)"
                )
            
            except Exception as e:
                logger.error(f"[PortfolioService] Failed to update mark price for {symbol}: {e}")
        
        # Update portfolio snapshot with new unrealized PnL
        await self._update_portfolio_snapshot()
        
        # Return fresh snapshot
        return await self.get_portfolio_state()


# Global instance
_portfolio_service: Optional[PortfolioService] = None


def init_portfolio_service(db_client: AsyncIOMotorClient, account_id: str = "paper_default"):
    """Initialize global portfolio service."""
    global _portfolio_service
    _portfolio_service = PortfolioService(db_client, account_id)
    return _portfolio_service


def get_portfolio_service() -> PortfolioService:
    """Get global portfolio service instance."""
    if _portfolio_service is None:
        raise ValueError("Portfolio service not initialized. Call init_portfolio_service() first.")
    return _portfolio_service
