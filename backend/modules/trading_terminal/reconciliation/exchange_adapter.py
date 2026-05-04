"""
State Reconciliation Layer - Exchange Adapter
Fetches current state from exchanges for comparison.

In production, this would integrate with actual exchange APIs.
Currently provides mock data for testing.
"""

import random
from typing import Optional, List
from datetime import datetime, timedelta

from .recon_types import (
    ExchangeState,
    ExchangePosition,
    ExchangeOrder,
    ExchangeBalance,
    ExchangeFill
)


class ExchangeAdapter:
    """
    Adapter for fetching exchange state.
    
    In production:
    - Uses Vault to get API credentials
    - Makes actual API calls to exchanges
    - Handles rate limiting and errors
    
    Currently returns mock data for testing.
    """
    
    # Supported exchanges
    SUPPORTED_EXCHANGES = ["BINANCE", "BYBIT", "OKX", "COINBASE"]
    
    def __init__(self):
        """Initialize exchange adapter"""
        self._mock_mode = True
    
    async def fetch_exchange_state(
        self,
        exchange: str,
        key_id: Optional[str] = None
    ) -> ExchangeState:
        """
        Fetch complete state from an exchange.
        
        Args:
            exchange: Exchange name
            key_id: Vault key ID for credentials (optional in mock mode)
        
        Returns:
            ExchangeState with positions, orders, balances, fills
        """
        exchange = exchange.upper()
        
        if self._mock_mode:
            return self._generate_mock_state(exchange)
        
        # Production implementation would:
        # 1. Get credentials from Vault using key_id
        # 2. Make API calls to exchange
        # 3. Parse responses into ExchangeState
        
        raise NotImplementedError("Production exchange integration not implemented")
    
    async def fetch_positions(
        self,
        exchange: str,
        key_id: Optional[str] = None
    ) -> List[ExchangePosition]:
        """Fetch only positions from exchange"""
        state = await self.fetch_exchange_state(exchange, key_id)
        return state.positions
    
    async def fetch_orders(
        self,
        exchange: str,
        key_id: Optional[str] = None
    ) -> List[ExchangeOrder]:
        """Fetch only open orders from exchange"""
        state = await self.fetch_exchange_state(exchange, key_id)
        return state.orders
    
    async def fetch_balances(
        self,
        exchange: str,
        key_id: Optional[str] = None
    ) -> List[ExchangeBalance]:
        """Fetch balances from exchange"""
        state = await self.fetch_exchange_state(exchange, key_id)
        return state.balances
    
    def _generate_mock_state(self, exchange: str) -> ExchangeState:
        """Generate mock exchange state for testing"""
        
        # Generate mock positions
        positions = []
        if random.random() > 0.3:  # 70% chance of having positions
            num_positions = random.randint(1, 3)
            symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT"]
            
            for i in range(num_positions):
                symbol = random.choice(symbols)
                side = random.choice(["LONG", "SHORT"])
                size = round(random.uniform(0.01, 1.0), 4)
                entry_price = self._get_mock_price(symbol)
                
                positions.append(ExchangePosition(
                    symbol=symbol,
                    side=side,
                    size=size,
                    entry_price=entry_price,
                    unrealized_pnl=round(random.uniform(-100, 200), 2),
                    leverage=random.choice([5, 10, 20]),
                    margin_type="CROSS",
                    liquidation_price=entry_price * (0.8 if side == "LONG" else 1.2)
                ))
        
        # Generate mock orders
        orders = []
        if random.random() > 0.5:  # 50% chance of having open orders
            num_orders = random.randint(1, 3)
            
            for i in range(num_orders):
                symbol = random.choice(["BTCUSDT", "ETHUSDT", "SOLUSDT"])
                side = random.choice(["BUY", "SELL"])
                order_type = random.choice(["LIMIT", "STOP_LIMIT"])
                price = self._get_mock_price(symbol) * random.uniform(0.95, 1.05)
                
                orders.append(ExchangeOrder(
                    order_id=f"ex_ord_{random.randint(100000, 999999)}",
                    symbol=symbol,
                    side=side,
                    type=order_type,
                    status="NEW",
                    price=round(price, 2),
                    quantity=round(random.uniform(0.01, 0.5), 4),
                    filled_quantity=0,
                    created_at=datetime.utcnow() - timedelta(minutes=random.randint(5, 60))
                ))
        
        # Generate mock balances
        balances = [
            ExchangeBalance(
                asset="USDT",
                free=round(random.uniform(1000, 50000), 2),
                locked=round(random.uniform(0, 1000), 2),
                total=0  # Will be calculated
            ),
            ExchangeBalance(
                asset="BTC",
                free=round(random.uniform(0, 1), 6),
                locked=0,
                total=0
            ),
            ExchangeBalance(
                asset="ETH",
                free=round(random.uniform(0, 5), 4),
                locked=0,
                total=0
            )
        ]
        
        # Calculate totals
        for balance in balances:
            balance.total = balance.free + balance.locked
        
        # Generate mock fills (recent trades)
        fills = []
        if random.random() > 0.4:
            num_fills = random.randint(1, 5)
            
            for i in range(num_fills):
                symbol = random.choice(["BTCUSDT", "ETHUSDT"])
                
                fills.append(ExchangeFill(
                    trade_id=f"trade_{random.randint(1000000, 9999999)}",
                    order_id=f"ord_{random.randint(100000, 999999)}",
                    symbol=symbol,
                    side=random.choice(["BUY", "SELL"]),
                    price=self._get_mock_price(symbol),
                    quantity=round(random.uniform(0.01, 0.5), 4),
                    fee=round(random.uniform(0.01, 1.0), 4),
                    fee_asset="USDT",
                    timestamp=datetime.utcnow() - timedelta(minutes=random.randint(1, 120))
                ))
        
        return ExchangeState(
            exchange=exchange,
            positions=positions,
            orders=orders,
            balances=balances,
            fills=fills,
            api_latency_ms=random.randint(50, 300),
            rate_limit_remaining=random.randint(100, 1000)
        )
    
    def _get_mock_price(self, symbol: str) -> float:
        """Get mock current price for a symbol"""
        prices = {
            "BTCUSDT": 67500.0,
            "ETHUSDT": 3450.0,
            "SOLUSDT": 175.0,
            "BNBUSDT": 580.0,
        }
        base_price = prices.get(symbol, 100.0)
        # Add some variance
        return round(base_price * random.uniform(0.99, 1.01), 2)
    
    def get_supported_exchanges(self) -> List[str]:
        """Get list of supported exchanges"""
        return self.SUPPORTED_EXCHANGES.copy()


# Singleton instance
_adapter_instance = None

def get_exchange_adapter() -> ExchangeAdapter:
    """Get singleton ExchangeAdapter instance"""
    global _adapter_instance
    if _adapter_instance is None:
        _adapter_instance = ExchangeAdapter()
    return _adapter_instance
