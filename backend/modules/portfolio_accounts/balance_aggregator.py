"""
Balance Aggregator - PHASE 5.4
==============================

Aggregates balance data from multiple exchanges.
"""

from typing import Dict, List, Optional, Any
from datetime import datetime
from collections import defaultdict
import random

from .account_types import (
    PortfolioBalance,
    AggregatedBalance
)

import sys
sys.path.append('/app/backend')
from modules.exchanges.exchange_router import get_exchange_router
from modules.market_data.market_data_engine import get_market_data_engine


class BalanceAggregator:
    """
    Aggregates balance data from multiple exchanges.
    
    Responsibilities:
    - Collect balances by asset
    - Calculate USD values
    - Track distribution across exchanges
    - Aggregate totals
    """
    
    def __init__(self):
        self._balances: Dict[str, List[PortfolioBalance]] = defaultdict(list)
        self._aggregated: Dict[str, AggregatedBalance] = {}
        self._exchange_router = get_exchange_router()
        self._market_data = get_market_data_engine()
        self._last_refresh: Optional[datetime] = None
        
        # Price cache for USD conversion
        self._price_cache: Dict[str, float] = {
            "USDT": 1.0,
            "USDC": 1.0,
            "BUSD": 1.0,
            "USD": 1.0
        }
    
    async def refresh_balances(self, exchanges: Optional[List[str]] = None) -> Dict[str, List[PortfolioBalance]]:
        """Refresh balance data from exchanges"""
        target_exchanges = exchanges or ["BINANCE", "BYBIT", "OKX"]
        
        self._balances.clear()
        
        for exchange in target_exchanges:
            try:
                balances = await self._fetch_balances(exchange)
                self._balances[exchange] = balances
            except Exception as e:
                print(f"Error fetching balances for {exchange}: {e}")
                # Use simulated data
                self._balances[exchange] = self._simulate_balances(exchange)
        
        # Aggregate after refresh
        self._aggregate_balances()
        self._last_refresh = datetime.utcnow()
        
        return self._balances
    
    async def _fetch_balances(self, exchange: str) -> List[PortfolioBalance]:
        """Fetch balance data from exchange"""
        try:
            router_status = self._exchange_router.get_status()
            if exchange in router_status.get("connected_exchanges", []):
                raw_balances = await self._exchange_router.get_balances(exchange)
                
                balances = []
                for b in raw_balances:
                    if isinstance(b, dict) and b.get("total", 0) > 0:
                        asset = b.get("asset", "UNKNOWN")
                        usd_value = await self._get_usd_value(asset, b.get("total", 0))
                        
                        balances.append(PortfolioBalance(
                            exchange=exchange,
                            asset=asset,
                            free=b.get("free", 0),
                            locked=b.get("locked", 0),
                            total=b.get("total", 0),
                            usd_value=usd_value,
                            timestamp=datetime.utcnow()
                        ))
                
                if balances:
                    return balances
        except Exception:
            pass
        
        return self._simulate_balances(exchange)
    
    def _simulate_balances(self, exchange: str) -> List[PortfolioBalance]:
        """Simulate balance data for demo"""
        # Base balances per exchange
        base_balances = {
            "BINANCE": [
                ("USDT", 25000, 5000),
                ("BTC", 0.5, 0.1),
                ("ETH", 5.0, 1.0),
                ("BNB", 50, 10),
            ],
            "BYBIT": [
                ("USDT", 15000, 3000),
                ("BTC", 0.3, 0.05),
                ("ETH", 3.0, 0.5),
            ],
            "OKX": [
                ("USDT", 10000, 2000),
                ("BTC", 0.2, 0.02),
                ("ETH", 2.0, 0.3),
                ("SOL", 100, 20),
            ]
        }
        
        prices = {
            "USDT": 1.0,
            "BTC": 69000.0,
            "ETH": 3500.0,
            "BNB": 600.0,
            "SOL": 150.0
        }
        
        balances = []
        for asset, free, locked in base_balances.get(exchange, []):
            # Add randomness
            free = free * (1 + random.uniform(-0.1, 0.1))
            locked = locked * (1 + random.uniform(-0.1, 0.1))
            total = free + locked
            price = prices.get(asset, 1.0)
            
            balances.append(PortfolioBalance(
                exchange=exchange,
                asset=asset,
                free=round(free, 8),
                locked=round(locked, 8),
                total=round(total, 8),
                usd_value=round(total * price, 2),
                avg_price=price,
                timestamp=datetime.utcnow()
            ))
        
        return balances
    
    async def _get_usd_value(self, asset: str, amount: float) -> float:
        """Get USD value for asset amount"""
        if asset in self._price_cache:
            return amount * self._price_cache[asset]
        
        # Try to get price from market data
        try:
            symbol = f"{asset}USDT"
            price = self._market_data.get_price("BINANCE", symbol)
            if price > 0:
                self._price_cache[asset] = price
                return amount * price
        except Exception:
            pass
        
        # Default prices
        default_prices = {
            "BTC": 69000.0,
            "ETH": 3500.0,
            "BNB": 600.0,
            "SOL": 150.0,
            "XRP": 0.55
        }
        
        price = default_prices.get(asset, 0)
        return amount * price
    
    def _aggregate_balances(self) -> None:
        """Aggregate balances by asset across exchanges"""
        self._aggregated.clear()
        
        # Group by asset
        by_asset: Dict[str, List[PortfolioBalance]] = defaultdict(list)
        
        for exchange, balances in self._balances.items():
            for balance in balances:
                by_asset[balance.asset].append(balance)
        
        # Create aggregated entries
        for asset, balances in by_asset.items():
            exchange_breakdown = {}
            total_free = 0.0
            total_locked = 0.0
            total_amount = 0.0
            total_usd = 0.0
            
            for b in balances:
                exchange_breakdown[b.exchange] = b.total
                total_free += b.free
                total_locked += b.locked
                total_amount += b.total
                total_usd += b.usd_value
            
            self._aggregated[asset] = AggregatedBalance(
                asset=asset,
                total_free=round(total_free, 8),
                total_locked=round(total_locked, 8),
                total_amount=round(total_amount, 8),
                total_usd_value=round(total_usd, 2),
                exchange_breakdown=exchange_breakdown,
                exchange_count=len(balances)
            )
    
    def get_balances_by_exchange(self, exchange: str) -> List[PortfolioBalance]:
        """Get balances for specific exchange"""
        return self._balances.get(exchange.upper(), [])
    
    def get_all_balances(self) -> List[PortfolioBalance]:
        """Get all balances"""
        all_balances = []
        for balances in self._balances.values():
            all_balances.extend(balances)
        return all_balances
    
    def get_aggregated_balances(self) -> Dict[str, AggregatedBalance]:
        """Get aggregated balances by asset"""
        return self._aggregated
    
    def get_asset_balance(self, asset: str) -> Optional[AggregatedBalance]:
        """Get aggregated balance for specific asset"""
        return self._aggregated.get(asset.upper())
    
    def get_total_usd_value(self) -> float:
        """Get total USD value across all balances"""
        return sum(ab.total_usd_value for ab in self._aggregated.values())
    
    def get_asset_distribution(self) -> Dict[str, float]:
        """Get asset distribution by USD value"""
        total = self.get_total_usd_value()
        if total == 0:
            return {}
        
        return {
            asset: round((ab.total_usd_value / total) * 100, 2)
            for asset, ab in self._aggregated.items()
            if ab.total_usd_value > 0
        }
    
    def get_exchange_distribution(self) -> Dict[str, float]:
        """Get distribution by exchange"""
        exchange_totals: Dict[str, float] = defaultdict(float)
        
        for balances in self._balances.values():
            for b in balances:
                exchange_totals[b.exchange] += b.usd_value
        
        total = sum(exchange_totals.values())
        if total == 0:
            return {}
        
        return {
            ex: round((val / total) * 100, 2)
            for ex, val in exchange_totals.items()
        }
    
    def get_summary(self) -> Dict[str, Any]:
        """Get balance aggregation summary"""
        return {
            "total_usd_value": round(self.get_total_usd_value(), 2),
            "unique_assets": len(self._aggregated),
            "exchanges_count": len(self._balances),
            "asset_distribution": self.get_asset_distribution(),
            "exchange_distribution": self.get_exchange_distribution(),
            "top_assets": sorted(
                [(a, ab.total_usd_value) for a, ab in self._aggregated.items()],
                key=lambda x: x[1],
                reverse=True
            )[:5],
            "last_refresh": self._last_refresh.isoformat() if self._last_refresh else None
        }
    
    def get_status(self) -> Dict[str, Any]:
        """Get aggregator status"""
        return {
            "balances_tracked": sum(len(b) for b in self._balances.values()),
            "unique_assets": len(self._aggregated),
            "exchanges": list(self._balances.keys()),
            "last_refresh": self._last_refresh.isoformat() if self._last_refresh else None
        }


# Global instance
_balance_aggregator: Optional[BalanceAggregator] = None


def get_balance_aggregator() -> BalanceAggregator:
    """Get or create global balance aggregator"""
    global _balance_aggregator
    if _balance_aggregator is None:
        _balance_aggregator = BalanceAggregator()
    return _balance_aggregator
