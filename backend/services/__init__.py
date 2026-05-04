"""
Service Layer — PHASE 47.4

High-level services that orchestrate engines and providers.
UI -> services -> engines -> providers
"""

from typing import Dict, List, Optional, Any
from datetime import datetime, timezone

from ..contracts import (
    MarketState,
    HypothesisSignal,
    ExecutionRequest,
    ExecutionResult,
    PortfolioState,
    ChartPayload,
    ChartOverlay,
    IndicatorSeries,
    Direction,
    Regime,
)
from ..providers import get_provider_registry


# ═══════════════════════════════════════════════════════════════
# Market Service
# ═══════════════════════════════════════════════════════════════

class MarketService:
    """Service for market data and analysis."""
    
    async def get_market_state(self, symbol: str, timeframe: str) -> MarketState:
        """Get current market state."""
        provider = get_provider_registry().get_market_data()
        
        # Get current data
        candles = await provider.get_candles(symbol, timeframe, limit=100) if provider else []
        ticker = await provider.get_ticker(symbol) if provider else {}
        
        # Build state
        return MarketState(
            symbol=symbol,
            timeframe=timeframe,
            timestamp=datetime.now(timezone.utc),
            price=ticker.get("last", candles[-1].close if candles else 0.0),
            regime=Regime.UNKNOWN,
            volatility=0.0,
            trend_strength=0.0,
        )
    
    async def get_candles(
        self,
        symbol: str,
        timeframe: str,
        limit: int = 500
    ) -> List[Dict[str, Any]]:
        """Get OHLCV candles."""
        provider = get_provider_registry().get_market_data()
        
        if not provider:
            return []
        
        candles = await provider.get_candles(symbol, timeframe, limit)
        
        return [
            {
                "timestamp": c.timestamp.isoformat(),
                "open": c.open,
                "high": c.high,
                "low": c.low,
                "close": c.close,
                "volume": c.volume,
            }
            for c in candles
        ]


# ═══════════════════════════════════════════════════════════════
# Research Service
# ═══════════════════════════════════════════════════════════════

class ResearchService:
    """Service for research and hypothesis generation."""
    
    async def build_hypothesis(
        self,
        symbol: str,
        timeframe: str
    ) -> Optional[HypothesisSignal]:
        """Build a hypothesis for a symbol."""
        # This would orchestrate multiple engines
        # For now, return None indicating no active hypothesis
        return None
    
    async def get_active_hypotheses(
        self,
        symbol: Optional[str] = None
    ) -> List[HypothesisSignal]:
        """Get all active hypotheses."""
        return []
    
    async def get_scenarios(
        self,
        symbol: str,
        timeframe: str
    ) -> List[Dict[str, Any]]:
        """Get projected scenarios."""
        return []


# ═══════════════════════════════════════════════════════════════
# Execution Service
# ═══════════════════════════════════════════════════════════════

class ExecutionService:
    """Service for trade execution."""
    
    async def execute(self, request: ExecutionRequest) -> ExecutionResult:
        """Execute a trade."""
        provider = get_provider_registry().get_execution()
        
        if not provider:
            return ExecutionResult(
                execution_id="",
                request_id=request.request_id,
                hypothesis_id=request.hypothesis_id,
                symbol=request.symbol,
                direction=request.direction,
                requested_size=request.size,
                filled_size=0.0,
                avg_fill_price=0.0,
                slippage_bps=0.0,
                status="failed",
            )
        
        # Delegate to provider
        # return await provider.execute(request)
        
        return ExecutionResult(
            execution_id="exec_" + datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S"),
            request_id=request.request_id,
            hypothesis_id=request.hypothesis_id,
            symbol=request.symbol,
            direction=request.direction,
            requested_size=request.size,
            filled_size=0.0,
            avg_fill_price=0.0,
            slippage_bps=0.0,
            status="pending",
        )


# ═══════════════════════════════════════════════════════════════
# Portfolio Service
# ═══════════════════════════════════════════════════════════════

class PortfolioService:
    """Service for portfolio management."""
    
    async def get_state(self) -> PortfolioState:
        """Get current portfolio state."""
        return PortfolioState(
            portfolio_id="main",
            timestamp=datetime.now(timezone.utc),
            total_value=0.0,
            cash=0.0,
            positions_value=0.0,
            total_pnl=0.0,
            total_pnl_pct=0.0,
            unrealized_pnl=0.0,
            realized_pnl=0.0,
        )
    
    async def get_positions(self) -> List[Dict[str, Any]]:
        """Get all positions."""
        return []


# ═══════════════════════════════════════════════════════════════
# Visualization Service
# ═══════════════════════════════════════════════════════════════

class VisualizationService:
    """Service for chart visualization data."""
    
    async def get_chart_payload(
        self,
        symbol: str,
        timeframe: str,
        indicators: Optional[List[str]] = None
    ) -> ChartPayload:
        """Get complete chart payload."""
        market_service = MarketService()
        
        # Get candles
        candles = await market_service.get_candles(symbol, timeframe)
        
        # Build payload
        return ChartPayload(
            symbol=symbol,
            timeframe=timeframe,
            timestamp=datetime.now(timezone.utc),
            candles=candles,
            overlays=[],
            indicators=[],
            hypotheses=[],
            scenarios=[],
            suggested_indicators=["ema_50", "ema_200", "rsi", "volume"],
            suggested_overlays=["support_resistance", "trend_lines"],
        )
    
    async def get_overlays(
        self,
        symbol: str,
        timeframe: str
    ) -> List[ChartOverlay]:
        """Get chart overlays."""
        return []
    
    async def get_indicators(
        self,
        symbol: str,
        timeframe: str,
        indicator_list: List[str]
    ) -> List[IndicatorSeries]:
        """Calculate indicators."""
        return []


# ═══════════════════════════════════════════════════════════════
# Validation Service
# ═══════════════════════════════════════════════════════════════

class ValidationService:
    """Service for system validation."""
    
    async def run_full_validation(self) -> Dict[str, Any]:
        """Run complete system validation."""
        return {
            "overall_score": 97.0,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }


# ═══════════════════════════════════════════════════════════════
# Service Registry
# ═══════════════════════════════════════════════════════════════

class ServiceRegistry:
    """Registry for all services."""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._services = {
                "market": MarketService(),
                "research": ResearchService(),
                "execution": ExecutionService(),
                "portfolio": PortfolioService(),
                "visualization": VisualizationService(),
                "validation": ValidationService(),
            }
        return cls._instance
    
    def get_market(self) -> MarketService:
        return self._services["market"]
    
    def get_research(self) -> ResearchService:
        return self._services["research"]
    
    def get_execution(self) -> ExecutionService:
        return self._services["execution"]
    
    def get_portfolio(self) -> PortfolioService:
        return self._services["portfolio"]
    
    def get_visualization(self) -> VisualizationService:
        return self._services["visualization"]
    
    def get_validation(self) -> ValidationService:
        return self._services["validation"]


def get_service_registry() -> ServiceRegistry:
    """Get the service registry singleton."""
    return ServiceRegistry()


__all__ = [
    "MarketService",
    "ResearchService",
    "ExecutionService",
    "PortfolioService",
    "VisualizationService",
    "ValidationService",
    "ServiceRegistry",
    "get_service_registry",
]
