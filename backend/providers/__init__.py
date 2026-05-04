"""
Provider Interfaces — PHASE 47.2

Abstract interfaces for all external dependencies.
Core modules should only interact with these interfaces,
never with concrete implementations directly.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
from datetime import datetime
from pydantic import BaseModel


# ═══════════════════════════════════════════════════════════════
# Market Data Provider
# ═══════════════════════════════════════════════════════════════

class Candle(BaseModel):
    """OHLCV candle data."""
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float


class MarketDataProvider(ABC):
    """Interface for market data sources."""
    
    @abstractmethod
    async def get_candles(
        self,
        symbol: str,
        timeframe: str,
        limit: int = 500
    ) -> List[Candle]:
        """Fetch OHLCV candles."""
        pass
    
    @abstractmethod
    async def get_ticker(self, symbol: str) -> Dict[str, Any]:
        """Get current ticker data."""
        pass
    
    @abstractmethod
    async def get_orderbook(
        self,
        symbol: str,
        depth: int = 20
    ) -> Dict[str, Any]:
        """Get orderbook snapshot."""
        pass
    
    @abstractmethod
    async def get_funding_rate(self, symbol: str) -> float:
        """Get current funding rate."""
        pass
    
    @abstractmethod
    async def get_open_interest(self, symbol: str) -> float:
        """Get open interest."""
        pass


# ═══════════════════════════════════════════════════════════════
# Exchange Provider
# ═══════════════════════════════════════════════════════════════

class OrderRequest(BaseModel):
    """Order request data."""
    symbol: str
    side: str  # buy/sell
    type: str  # market/limit
    quantity: float
    price: Optional[float] = None
    client_order_id: Optional[str] = None


class OrderResponse(BaseModel):
    """Order response data."""
    order_id: str
    client_order_id: Optional[str]
    symbol: str
    side: str
    type: str
    quantity: float
    filled_quantity: float
    price: Optional[float]
    status: str
    timestamp: datetime


class Position(BaseModel):
    """Position data."""
    symbol: str
    side: str
    quantity: float
    entry_price: float
    unrealized_pnl: float
    realized_pnl: float
    leverage: int


class ExchangeProvider(ABC):
    """Interface for exchange operations."""
    
    @abstractmethod
    async def place_order(self, request: OrderRequest) -> OrderResponse:
        """Place a new order."""
        pass
    
    @abstractmethod
    async def cancel_order(self, order_id: str, symbol: str) -> bool:
        """Cancel an existing order."""
        pass
    
    @abstractmethod
    async def get_order(self, order_id: str, symbol: str) -> OrderResponse:
        """Get order status."""
        pass
    
    @abstractmethod
    async def get_open_orders(self, symbol: Optional[str] = None) -> List[OrderResponse]:
        """Get all open orders."""
        pass
    
    @abstractmethod
    async def get_positions(self) -> List[Position]:
        """Get all positions."""
        pass
    
    @abstractmethod
    async def get_balance(self) -> Dict[str, float]:
        """Get account balance."""
        pass
    
    @abstractmethod
    async def set_leverage(self, symbol: str, leverage: int) -> bool:
        """Set leverage for a symbol."""
        pass


# ═══════════════════════════════════════════════════════════════
# Storage Provider
# ═══════════════════════════════════════════════════════════════

class StorageProvider(ABC):
    """Interface for data storage."""
    
    @abstractmethod
    async def save(self, collection: str, data: Dict[str, Any]) -> str:
        """Save data to storage. Returns document ID."""
        pass
    
    @abstractmethod
    async def save_many(self, collection: str, data: List[Dict[str, Any]]) -> List[str]:
        """Save multiple documents."""
        pass
    
    @abstractmethod
    async def find_one(
        self,
        collection: str,
        query: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Find a single document."""
        pass
    
    @abstractmethod
    async def find_many(
        self,
        collection: str,
        query: Dict[str, Any],
        limit: int = 100,
        sort: Optional[List[tuple]] = None
    ) -> List[Dict[str, Any]]:
        """Find multiple documents."""
        pass
    
    @abstractmethod
    async def update_one(
        self,
        collection: str,
        query: Dict[str, Any],
        update: Dict[str, Any]
    ) -> bool:
        """Update a single document."""
        pass
    
    @abstractmethod
    async def delete_one(self, collection: str, query: Dict[str, Any]) -> bool:
        """Delete a single document."""
        pass
    
    @abstractmethod
    async def aggregate(
        self,
        collection: str,
        pipeline: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Run aggregation pipeline."""
        pass


# ═══════════════════════════════════════════════════════════════
# Fractal Provider
# ═══════════════════════════════════════════════════════════════

class FractalMatch(BaseModel):
    """Fractal match result."""
    reference_symbol: str
    reference_start: datetime
    reference_end: datetime
    similarity: float
    projected_path: List[float]
    confidence: float
    metadata: Dict[str, Any] = {}


class FractalProvider(ABC):
    """Interface for fractal analysis."""
    
    @abstractmethod
    async def find_similar_patterns(
        self,
        pattern: List[float],
        min_similarity: float = 0.75,
        limit: int = 5
    ) -> List[FractalMatch]:
        """Find similar historical patterns."""
        pass
    
    @abstractmethod
    async def get_projection(
        self,
        current_pattern: List[float],
        match: FractalMatch
    ) -> List[float]:
        """Get projected path based on match."""
        pass
    
    @abstractmethod
    async def calculate_similarity(
        self,
        pattern1: List[float],
        pattern2: List[float]
    ) -> float:
        """Calculate similarity between two patterns."""
        pass


# ═══════════════════════════════════════════════════════════════
# Execution Provider
# ═══════════════════════════════════════════════════════════════

class ExecutionRequest(BaseModel):
    """Execution request."""
    hypothesis_id: str
    symbol: str
    direction: str  # long/short
    size: float
    entry_type: str  # market/limit
    entry_price: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    max_slippage_bps: int = 50
    timeout_seconds: int = 30


class ExecutionResult(BaseModel):
    """Execution result."""
    execution_id: str
    hypothesis_id: str
    symbol: str
    direction: str
    requested_size: float
    filled_size: float
    avg_fill_price: float
    slippage_bps: float
    status: str  # filled/partial/failed/cancelled
    orders: List[str] = []
    timestamp: datetime


class ExecutionProvider(ABC):
    """Interface for execution operations."""
    
    @abstractmethod
    async def execute(self, request: ExecutionRequest) -> ExecutionResult:
        """Execute a trading request."""
        pass
    
    @abstractmethod
    async def close_position(
        self,
        symbol: str,
        execution_type: str = "market"
    ) -> ExecutionResult:
        """Close an existing position."""
        pass
    
    @abstractmethod
    async def get_execution_status(self, execution_id: str) -> ExecutionResult:
        """Get execution status."""
        pass
    
    @abstractmethod
    async def estimate_impact(
        self,
        symbol: str,
        size: float,
        direction: str
    ) -> Dict[str, float]:
        """Estimate market impact."""
        pass


# ═══════════════════════════════════════════════════════════════
# Indicator Provider
# ═══════════════════════════════════════════════════════════════

class IndicatorResult(BaseModel):
    """Indicator calculation result."""
    name: str
    values: List[float]
    timestamps: List[datetime]
    metadata: Dict[str, Any] = {}


class IndicatorProvider(ABC):
    """Interface for indicator calculations."""
    
    @abstractmethod
    async def calculate(
        self,
        indicator: str,
        candles: List[Candle],
        **params
    ) -> IndicatorResult:
        """Calculate an indicator."""
        pass
    
    @abstractmethod
    async def calculate_batch(
        self,
        indicators: List[str],
        candles: List[Candle],
        params: Dict[str, Dict[str, Any]] = {}
    ) -> Dict[str, IndicatorResult]:
        """Calculate multiple indicators."""
        pass
    
    @abstractmethod
    def get_available_indicators(self) -> List[str]:
        """Get list of available indicators."""
        pass


# ═══════════════════════════════════════════════════════════════
# Notification Provider
# ═══════════════════════════════════════════════════════════════

class Notification(BaseModel):
    """Notification data."""
    type: str  # alert/trade/system
    severity: str  # info/warning/critical
    title: str
    message: str
    data: Dict[str, Any] = {}


class NotificationProvider(ABC):
    """Interface for notifications."""
    
    @abstractmethod
    async def send(self, notification: Notification) -> bool:
        """Send a notification."""
        pass
    
    @abstractmethod
    async def send_batch(self, notifications: List[Notification]) -> List[bool]:
        """Send multiple notifications."""
        pass


# ═══════════════════════════════════════════════════════════════
# Provider Registry
# ═══════════════════════════════════════════════════════════════

class ProviderRegistry:
    """Registry for all providers."""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._providers = {}
        return cls._instance
    
    def register(self, name: str, provider: Any):
        """Register a provider."""
        self._providers[name] = provider
    
    def get(self, name: str) -> Any:
        """Get a provider by name."""
        return self._providers.get(name)
    
    def get_market_data(self) -> Optional[MarketDataProvider]:
        return self._providers.get("market_data")
    
    def get_exchange(self) -> Optional[ExchangeProvider]:
        return self._providers.get("exchange")
    
    def get_storage(self) -> Optional[StorageProvider]:
        return self._providers.get("storage")
    
    def get_fractal(self) -> Optional[FractalProvider]:
        return self._providers.get("fractal")
    
    def get_execution(self) -> Optional[ExecutionProvider]:
        return self._providers.get("execution")
    
    def get_indicator(self) -> Optional[IndicatorProvider]:
        return self._providers.get("indicator")
    
    def get_notification(self) -> Optional[NotificationProvider]:
        return self._providers.get("notification")


def get_provider_registry() -> ProviderRegistry:
    """Get the provider registry singleton."""
    return ProviderRegistry()


__all__ = [
    # Data types
    "Candle",
    "OrderRequest",
    "OrderResponse",
    "Position",
    "FractalMatch",
    "ExecutionRequest",
    "ExecutionResult",
    "IndicatorResult",
    "Notification",
    # Providers
    "MarketDataProvider",
    "ExchangeProvider",
    "StorageProvider",
    "FractalProvider",
    "ExecutionProvider",
    "IndicatorProvider",
    "NotificationProvider",
    # Registry
    "ProviderRegistry",
    "get_provider_registry",
]
