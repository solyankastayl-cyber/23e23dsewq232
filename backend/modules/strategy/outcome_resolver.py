"""
Outcome Resolver
================

Background worker that resolves shadow trades.

Runs every 15 seconds, finds trades where resolve_at <= now,
fetches current prices, calculates PnL/MFE/MAE.

This creates LABELS for ML training.
"""

import logging
import asyncio
from typing import Dict, Any, Optional
from datetime import datetime, timezone
from motor.motor_asyncio import AsyncIOMotorDatabase

logger = logging.getLogger(__name__)


class OutcomeResolver:
    """
    Resolves shadow trades at specified time horizons.
    
    Architecture:
      Shadow Trade → Wait for resolve_at → Fetch price → Calculate outcome → Update
    """
    
    def __init__(self, db: AsyncIOMotorDatabase, market_data_service=None):
        self.db = db
        self.collection = db.shadow_trades
        self.market_data = market_data_service
        
        # Control
        self._task: Optional[asyncio.Task] = None
        self._running = False
    
    async def start(self):
        """Start background resolution loop."""
        if self._running:
            logger.warning("[OutcomeResolver] Already running")
            return
        
        self._running = True
        self._task = asyncio.create_task(self._loop())
        logger.info("[OutcomeResolver] Started (15s interval)")
    
    async def stop(self):
        """Stop background loop."""
        if not self._running:
            return
        
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        
        logger.info("[OutcomeResolver] Stopped")
    
    async def _loop(self):
        """Main resolution loop."""
        logger.info("[OutcomeResolver] Loop started")
        
        while self._running:
            try:
                resolved_count = await self.resolve_pending()
                
                if resolved_count > 0:
                    logger.info(f"[OutcomeResolver] Resolved {resolved_count} horizons")
                
            except asyncio.CancelledError:
                logger.info("[OutcomeResolver] Loop cancelled")
                break
            except Exception as e:
                logger.error(f"[OutcomeResolver] Loop error: {e}", exc_info=True)
            
            # Sleep 15 seconds
            await asyncio.sleep(15)
    
    async def resolve_pending(self) -> int:
        """
        Find and resolve all pending horizons.
        
        Returns:
            Number of horizons resolved
        """
        if not self.market_data:
            logger.debug("[OutcomeResolver] No market_data service, skipping")
            return 0
        
        now = datetime.now(timezone.utc)
        
        # Find trades with unresolved horizons
        cursor = self.collection.find({
            "horizons": {
                "$elemMatch": {
                    "resolved": False,
                    "resolve_at": {"$lte": now}
                }
            }
        })
        
        trades = await cursor.to_list(length=1000)
        
        if not trades:
            return 0
        
        resolved_count = 0
        
        for trade in trades:
            updated = False
            
            for horizon in trade["horizons"]:
                # Skip if already resolved or not ready
                if horizon["resolved"] or horizon["resolve_at"] > now:
                    continue
                
                # Fetch current price
                try:
                    # Get current market price (sync call, no await)
                    current_price = self.market_data.get_last_price(
                        trade["symbol"],
                        timeframe=trade["timeframe"].lower()
                    )
                    
                    if current_price is None:
                        logger.warning(
                            f"[OutcomeResolver] No price for {trade['symbol']}, skipping"
                        )
                        continue
                    
                    # Calculate PnL
                    pnl = self._calculate_pnl(
                        trade["side"],
                        trade["entry_price"],
                        current_price
                    )
                    
                    # Update horizon
                    horizon["exit_price"] = current_price
                    horizon["pnl"] = round(pnl, 6)
                    horizon["resolved"] = True
                    
                    # MFE/MAE (simplified: actual requires tick data)
                    horizon["mfe"] = round(max(pnl, 0), 6)
                    horizon["mae"] = round(min(pnl, 0), 6)
                    
                    updated = True
                    resolved_count += 1
                    
                    logger.debug(
                        f"[OutcomeResolver] Resolved {trade['symbol']} {horizon['name']}: "
                        f"pnl={pnl:.4f} (entry=${trade['entry_price']:.2f}, "
                        f"exit=${current_price:.2f})"
                    )
                    
                except Exception as e:
                    logger.error(
                        f"[OutcomeResolver] Error resolving {trade['symbol']}: {e}"
                    )
            
            # Update trade if any horizon was resolved
            if updated:
                await self.collection.update_one(
                    {"_id": trade["_id"]},
                    {
                        "$set": {
                            "horizons": trade["horizons"],
                            "updated_at": now
                        }
                    }
                )
        
        return resolved_count
    
    def _calculate_pnl(self, side: str, entry_price: float, exit_price: float) -> float:
        """
        Calculate PnL as percentage.
        
        Args:
            side: "BUY" or "SELL"
            entry_price: Entry price
            exit_price: Exit price
            
        Returns:
            PnL percentage (e.g., 0.012 = +1.2%)
        """
        if side == "BUY":
            return (exit_price - entry_price) / entry_price
        else:  # SELL
            return (entry_price - exit_price) / entry_price


# Singleton
_outcome_resolver: Optional[OutcomeResolver] = None


def get_outcome_resolver(db=None, market_data_service=None) -> OutcomeResolver:
    """Get or create singleton resolver."""
    global _outcome_resolver
    if _outcome_resolver is None:
        _outcome_resolver = OutcomeResolver(db=db, market_data_service=market_data_service)
    return _outcome_resolver
