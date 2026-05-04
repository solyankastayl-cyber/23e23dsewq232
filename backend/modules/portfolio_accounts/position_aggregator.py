"""
Position Aggregator - PHASE 5.4
===============================

Aggregates position data from multiple exchanges.
"""

from typing import Dict, List, Optional, Any
from datetime import datetime
from collections import defaultdict
import random

from .account_types import (
    PortfolioPosition,
    AggregatedPosition,
    ExposureInfo,
    PositionSide,
    MarginMode
)

import sys
sys.path.append('/app/backend')
from modules.exchanges.exchange_router import get_exchange_router
from modules.market_data.market_data_engine import get_market_data_engine


class PositionAggregator:
    """
    Aggregates position data from multiple exchanges.
    
    Responsibilities:
    - Collect all open positions
    - Group by symbol
    - Group by exchange
    - Calculate long/short split
    - Calculate aggregate exposure
    """
    
    def __init__(self):
        self._positions: Dict[str, List[PortfolioPosition]] = defaultdict(list)
        self._aggregated_by_symbol: Dict[str, AggregatedPosition] = {}
        self._exposure: Dict[str, ExposureInfo] = {}
        self._exchange_router = get_exchange_router()
        self._market_data = get_market_data_engine()
        self._last_refresh: Optional[datetime] = None
    
    async def refresh_positions(self, exchanges: Optional[List[str]] = None) -> Dict[str, List[PortfolioPosition]]:
        """Refresh position data from exchanges"""
        target_exchanges = exchanges or ["BINANCE", "BYBIT", "OKX"]
        
        self._positions.clear()
        
        for exchange in target_exchanges:
            try:
                positions = await self._fetch_positions(exchange)
                self._positions[exchange] = positions
            except Exception as e:
                print(f"Error fetching positions for {exchange}: {e}")
                self._positions[exchange] = self._simulate_positions(exchange)
        
        # Aggregate after refresh
        self._aggregate_positions()
        self._calculate_exposure()
        self._last_refresh = datetime.utcnow()
        
        return self._positions
    
    async def _fetch_positions(self, exchange: str) -> List[PortfolioPosition]:
        """Fetch position data from exchange"""
        try:
            router_status = self._exchange_router.get_status()
            if exchange in router_status.get("connected_exchanges", []):
                raw_positions = await self._exchange_router.get_positions(exchange)
                
                positions = []
                for p in raw_positions:
                    if isinstance(p, dict) and abs(p.get("size", 0)) > 0:
                        symbol = p.get("symbol", "UNKNOWN")
                        mark_price = await self._get_mark_price(exchange, symbol)
                        
                        positions.append(PortfolioPosition(
                            exchange=exchange,
                            symbol=symbol,
                            side=PositionSide.LONG if p.get("size", 0) > 0 else PositionSide.SHORT,
                            size=abs(p.get("size", 0)),
                            entry_price=p.get("entry_price", 0),
                            mark_price=mark_price,
                            unrealized_pnl=p.get("unrealized_pnl", 0),
                            leverage=p.get("leverage", 1),
                            timestamp=datetime.utcnow()
                        ))
                
                if positions:
                    return positions
        except Exception:
            pass
        
        return self._simulate_positions(exchange)
    
    def _simulate_positions(self, exchange: str) -> List[PortfolioPosition]:
        """Simulate position data for demo"""
        # Base positions per exchange
        base_positions = {
            "BINANCE": [
                ("BTCUSDT", "LONG", 0.15, 68500, 69200, 10),
                ("ETHUSDT", "LONG", 2.5, 3450, 3520, 5),
                ("SOLUSDT", "SHORT", 50, 155, 148, 3),
            ],
            "BYBIT": [
                ("BTCUSDT", "LONG", 0.1, 68200, 69200, 10),
                ("ETHUSDT", "SHORT", 1.5, 3580, 3520, 5),
            ],
            "OKX": [
                ("BTCUSDT", "LONG", 0.08, 68800, 69200, 5),
                ("XRPUSDT", "LONG", 10000, 0.52, 0.55, 3),
            ]
        }
        
        positions = []
        for symbol, side, size, entry, mark, leverage in base_positions.get(exchange, []):
            # Add some randomness
            size = size * (1 + random.uniform(-0.1, 0.1))
            entry = entry * (1 + random.uniform(-0.01, 0.01))
            mark = mark * (1 + random.uniform(-0.005, 0.005))
            
            # Calculate PnL
            if side == "LONG":
                pnl = (mark - entry) * size
            else:
                pnl = (entry - mark) * size
            
            notional = size * mark
            margin_used = notional / leverage
            roe = (pnl / margin_used) * 100 if margin_used > 0 else 0
            
            # Calculate liquidation price (simplified)
            if side == "LONG":
                liq_price = entry * (1 - 1/leverage * 0.8)
            else:
                liq_price = entry * (1 + 1/leverage * 0.8)
            
            positions.append(PortfolioPosition(
                exchange=exchange,
                symbol=symbol,
                side=PositionSide.LONG if side == "LONG" else PositionSide.SHORT,
                size=round(size, 8),
                entry_price=round(entry, 2),
                mark_price=round(mark, 2),
                liquidation_price=round(liq_price, 2),
                unrealized_pnl=round(pnl, 2),
                realized_pnl=round(random.uniform(-100, 500), 2),
                leverage=leverage,
                margin_mode=MarginMode.CROSS,
                margin_used=round(margin_used, 2),
                notional_value=round(notional, 2),
                roe_pct=round(roe, 2),
                timestamp=datetime.utcnow()
            ))
        
        return positions
    
    async def _get_mark_price(self, exchange: str, symbol: str) -> float:
        """Get mark price for symbol"""
        try:
            price = self._market_data.get_price(exchange, symbol)
            if price > 0:
                return price
        except Exception:
            pass
        
        # Default prices
        default_prices = {
            "BTCUSDT": 69000.0,
            "ETHUSDT": 3500.0,
            "SOLUSDT": 150.0,
            "XRPUSDT": 0.55,
            "BNBUSDT": 600.0
        }
        return default_prices.get(symbol, 0)
    
    def _aggregate_positions(self) -> None:
        """Aggregate positions by symbol across exchanges"""
        self._aggregated_by_symbol.clear()
        
        # Group by symbol
        by_symbol: Dict[str, List[PortfolioPosition]] = defaultdict(list)
        
        for exchange, positions in self._positions.items():
            for pos in positions:
                by_symbol[pos.symbol].append(pos)
        
        # Create aggregated entries
        for symbol, positions in by_symbol.items():
            total_long_size = 0.0
            total_short_size = 0.0
            total_long_notional = 0.0
            total_short_notional = 0.0
            long_cost = 0.0
            short_cost = 0.0
            total_pnl = 0.0
            positions_by_exchange = {}
            
            for pos in positions:
                if pos.side == PositionSide.LONG:
                    total_long_size += pos.size
                    total_long_notional += pos.notional_value
                    long_cost += pos.size * pos.entry_price
                else:
                    total_short_size += pos.size
                    total_short_notional += pos.notional_value
                    short_cost += pos.size * pos.entry_price
                
                total_pnl += pos.unrealized_pnl
                
                positions_by_exchange[pos.exchange] = {
                    "side": pos.side.value,
                    "size": pos.size,
                    "entry_price": pos.entry_price,
                    "unrealized_pnl": pos.unrealized_pnl
                }
            
            avg_long_entry = (long_cost / total_long_size) if total_long_size > 0 else 0
            avg_short_entry = (short_cost / total_short_size) if total_short_size > 0 else 0
            
            self._aggregated_by_symbol[symbol] = AggregatedPosition(
                symbol=symbol,
                total_long_size=round(total_long_size, 8),
                total_short_size=round(total_short_size, 8),
                net_size=round(total_long_size - total_short_size, 8),
                total_long_notional=round(total_long_notional, 2),
                total_short_notional=round(total_short_notional, 2),
                net_notional=round(total_long_notional - total_short_notional, 2),
                avg_long_entry=round(avg_long_entry, 2),
                avg_short_entry=round(avg_short_entry, 2),
                total_unrealized_pnl=round(total_pnl, 2),
                positions_by_exchange=positions_by_exchange,
                exchange_count=len(positions_by_exchange)
            )
    
    def _calculate_exposure(self) -> None:
        """Calculate exposure info for each symbol"""
        self._exposure.clear()
        
        for symbol, agg in self._aggregated_by_symbol.items():
            exchanges_long = []
            exchanges_short = []
            
            for ex, data in agg.positions_by_exchange.items():
                if data["side"] == "LONG":
                    exchanges_long.append(ex)
                else:
                    exchanges_short.append(ex)
            
            self._exposure[symbol] = ExposureInfo(
                symbol=symbol,
                total_long_size=agg.total_long_size,
                total_short_size=agg.total_short_size,
                net_exposure=agg.net_size,
                gross_exposure=agg.total_long_size + agg.total_short_size,
                long_notional=agg.total_long_notional,
                short_notional=agg.total_short_notional,
                net_notional=agg.net_notional,
                exchanges_long=exchanges_long,
                exchanges_short=exchanges_short,
                avg_long_entry=agg.avg_long_entry,
                avg_short_entry=agg.avg_short_entry,
                total_unrealized_pnl=agg.total_unrealized_pnl
            )
    
    def get_positions_by_exchange(self, exchange: str) -> List[PortfolioPosition]:
        """Get positions for specific exchange"""
        return self._positions.get(exchange.upper(), [])
    
    def get_all_positions(self) -> List[PortfolioPosition]:
        """Get all positions"""
        all_positions = []
        for positions in self._positions.values():
            all_positions.extend(positions)
        return all_positions
    
    def get_positions_by_symbol(self, symbol: str) -> List[PortfolioPosition]:
        """Get positions for specific symbol across all exchanges"""
        positions = []
        for exchange_positions in self._positions.values():
            for pos in exchange_positions:
                if pos.symbol.upper() == symbol.upper():
                    positions.append(pos)
        return positions
    
    def get_aggregated_positions(self) -> Dict[str, AggregatedPosition]:
        """Get aggregated positions by symbol"""
        return self._aggregated_by_symbol
    
    def get_exposure(self, symbol: Optional[str] = None) -> Dict[str, ExposureInfo]:
        """Get exposure info"""
        if symbol:
            exp = self._exposure.get(symbol.upper())
            return {symbol.upper(): exp} if exp else {}
        return self._exposure
    
    def get_long_short_split(self) -> Dict[str, Any]:
        """Get long/short position split"""
        all_positions = self.get_all_positions()
        
        long_count = sum(1 for p in all_positions if p.side == PositionSide.LONG)
        short_count = sum(1 for p in all_positions if p.side == PositionSide.SHORT)
        long_notional = sum(p.notional_value for p in all_positions if p.side == PositionSide.LONG)
        short_notional = sum(p.notional_value for p in all_positions if p.side == PositionSide.SHORT)
        
        return {
            "long_count": long_count,
            "short_count": short_count,
            "long_notional": round(long_notional, 2),
            "short_notional": round(short_notional, 2),
            "net_notional": round(long_notional - short_notional, 2),
            "long_pct": round((long_notional / (long_notional + short_notional)) * 100, 2) if (long_notional + short_notional) > 0 else 0
        }
    
    def get_total_unrealized_pnl(self) -> float:
        """Get total unrealized PnL across all positions"""
        return sum(p.unrealized_pnl for p in self.get_all_positions())
    
    def get_total_notional(self) -> float:
        """Get total notional value of all positions"""
        return sum(p.notional_value for p in self.get_all_positions())
    
    def get_summary(self) -> Dict[str, Any]:
        """Get position aggregation summary"""
        all_positions = self.get_all_positions()
        split = self.get_long_short_split()
        
        return {
            "total_positions": len(all_positions),
            "unique_symbols": len(self._aggregated_by_symbol),
            "exchanges_count": len(self._positions),
            "total_notional": round(self.get_total_notional(), 2),
            "total_unrealized_pnl": round(self.get_total_unrealized_pnl(), 2),
            "long_short_split": split,
            "symbols": list(self._aggregated_by_symbol.keys()),
            "last_refresh": self._last_refresh.isoformat() if self._last_refresh else None
        }
    
    def get_status(self) -> Dict[str, Any]:
        """Get aggregator status"""
        return {
            "positions_tracked": sum(len(p) for p in self._positions.values()),
            "unique_symbols": len(self._aggregated_by_symbol),
            "exchanges": list(self._positions.keys()),
            "last_refresh": self._last_refresh.isoformat() if self._last_refresh else None
        }


# Global instance
_position_aggregator: Optional[PositionAggregator] = None


def get_position_aggregator() -> PositionAggregator:
    """Get or create global position aggregator"""
    global _position_aggregator
    if _position_aggregator is None:
        _position_aggregator = PositionAggregator()
    return _position_aggregator
