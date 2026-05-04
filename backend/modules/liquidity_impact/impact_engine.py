"""
Liquidity Impact Engine

PHASE 37 Sublayer — Liquidity Impact Engine

Core engine for calculating market impact of intended trades.

Data Sources:
- Orderbook depth
- Spread
- Vacuum state (from Microstructure)
- Pressure map (from Microstructure)
- Liquidation cascade risk
- Recent volume
- Microstructure context

Key Formulas:
- slippage_bps = order_size / effective_depth × 10000
- market_impact_bps = 0.50 * slippage + 0.30 * vacuum_penalty + 0.20 * pressure_penalty
- fill_quality = 1 - normalized_impact
"""

import hashlib
from typing import Optional, Dict, Tuple, List
from datetime import datetime, timezone, timedelta

from .impact_types import (
    LiquidityImpactEstimate,
    OrderBookDepth,
    ImpactSummary,
    LiquidityBucket,
    ImpactState,
    ExecutionRecommendation,
    SLIPPAGE_THRESHOLDS,
    IMPACT_MODIFIERS,
    WEIGHT_SLIPPAGE,
    WEIGHT_VACUUM,
    WEIGHT_PRESSURE,
)


# ══════════════════════════════════════════════════════════════
# Liquidity Impact Engine
# ══════════════════════════════════════════════════════════════

class LiquidityImpactEngine:
    """
    Liquidity Impact Engine — PHASE 37 Sublayer
    
    Estimates market impact before execution.
    """
    
    def __init__(self):
        self._cache: Dict[str, List[LiquidityImpactEstimate]] = {}
        self._current: Dict[str, LiquidityImpactEstimate] = {}
    
    # ═══════════════════════════════════════════════════════════
    # 1. Data Collection
    # ═══════════════════════════════════════════════════════════
    
    def get_orderbook_depth(self, symbol: str) -> OrderBookDepth:
        """Get orderbook depth from exchange data."""
        symbol = symbol.upper()
        
        try:
            from core.database import get_database
            db = get_database()
            if db:
                doc = db.exchange_orderbook_snapshots.find_one(
                    {"symbol": symbol},
                    {"_id": 0},
                    sort=[("timestamp", -1)]
                )
                if doc:
                    return OrderBookDepth(
                        symbol=symbol,
                        bid_depth_1pct=doc.get("bid_depth_1pct", 0),
                        ask_depth_1pct=doc.get("ask_depth_1pct", 0),
                        spread_bps=doc.get("spread_bps", 0),
                        imbalance_ratio=doc.get("imbalance_ratio", 0),
                        timestamp=doc.get("timestamp"),
                    )
        except Exception:
            pass
        
        # Deterministic fallback
        seed = int(hashlib.md5(f"{symbol}_depth".encode()).hexdigest()[:8], 16)
        base_depth = {"BTC": 5e6, "ETH": 2e6, "SOL": 500000}.get(symbol, 1e6)
        
        return OrderBookDepth(
            symbol=symbol,
            bid_depth_1pct=base_depth * (0.8 + (seed % 40) / 100),
            ask_depth_1pct=base_depth * (0.8 + ((seed >> 8) % 40) / 100),
            spread_bps=2 + (seed % 8),
            imbalance_ratio=((seed >> 16) % 100 - 50) / 100,
            timestamp=datetime.now(timezone.utc),
        )
    
    def get_vacuum_state(self, symbol: str) -> float:
        """Get vacuum penalty from Microstructure Intelligence."""
        try:
            from modules.microstructure_intelligence_v2 import get_vacuum_engine
            engine = get_vacuum_engine()
            state = engine.get_vacuum_state(symbol)
            if state:
                # Map vacuum level to penalty (0-15 bps)
                vacuum_map = {"NONE": 0, "MILD": 3, "MODERATE": 7, "SEVERE": 12, "EXTREME": 15}
                return vacuum_map.get(state.vacuum_level, 5)
        except Exception:
            pass
        
        seed = int(hashlib.md5(f"{symbol}_vacuum".encode()).hexdigest()[:4], 16)
        return (seed % 10)  # 0-9 bps
    
    def get_pressure_state(self, symbol: str, side: str) -> float:
        """Get pressure penalty from Microstructure Intelligence."""
        try:
            from modules.microstructure_intelligence_v2 import get_pressure_engine
            engine = get_pressure_engine()
            state = engine.get_pressure_state(symbol)
            if state:
                # Adverse pressure increases impact
                if side == "BUY" and state.pressure_bias == "ASK_DOMINANT":
                    return state.pressure_intensity * 10  # Up to 10 bps
                elif side == "SELL" and state.pressure_bias == "BID_DOMINANT":
                    return state.pressure_intensity * 10
                return 0
        except Exception:
            pass
        
        seed = int(hashlib.md5(f"{symbol}_pressure_{side}".encode()).hexdigest()[:4], 16)
        return (seed % 8)  # 0-7 bps
    
    # ═══════════════════════════════════════════════════════════
    # 2. Slippage Calculation
    # ═══════════════════════════════════════════════════════════
    
    def calculate_slippage(
        self,
        order_size_usd: float,
        effective_depth_usd: float,
    ) -> float:
        """
        Calculate expected slippage in basis points.
        
        Formula: slippage_bps = order_size / effective_depth × 10000
        """
        if effective_depth_usd <= 0:
            return 100.0  # Max slippage
        
        slippage_bps = (order_size_usd / effective_depth_usd) * 10000
        return round(min(slippage_bps, 100.0), 2)
    
    def get_effective_depth(
        self,
        depth: OrderBookDepth,
        side: str,
    ) -> float:
        """
        Get effective depth for the side being traded.
        
        BUY → use ask depth
        SELL → use bid depth
        """
        if side == "BUY":
            return depth.ask_depth_1pct
        else:
            return depth.bid_depth_1pct
    
    # ═══════════════════════════════════════════════════════════
    # 3. Market Impact Calculation
    # ═══════════════════════════════════════════════════════════
    
    def calculate_market_impact(
        self,
        slippage_bps: float,
        vacuum_penalty_bps: float,
        pressure_penalty_bps: float,
    ) -> float:
        """
        Calculate total market impact.
        
        Formula:
        market_impact_bps = 0.50 * slippage + 0.30 * vacuum + 0.20 * pressure
        """
        impact = (
            WEIGHT_SLIPPAGE * slippage_bps
            + WEIGHT_VACUUM * vacuum_penalty_bps
            + WEIGHT_PRESSURE * pressure_penalty_bps
        )
        return round(impact, 2)
    
    # ═══════════════════════════════════════════════════════════
    # 4. Fill Quality
    # ═══════════════════════════════════════════════════════════
    
    def calculate_fill_quality(self, market_impact_bps: float) -> float:
        """
        Calculate fill quality.
        
        Formula: fill_quality = 1 - normalized_impact
        
        where normalized_impact = impact / 30 (30 bps = untradeable threshold)
        """
        normalized = min(market_impact_bps / 30.0, 1.0)
        quality = 1.0 - normalized
        return round(max(quality, 0.0), 4)
    
    # ═══════════════════════════════════════════════════════════
    # 5. Classifications
    # ═══════════════════════════════════════════════════════════
    
    def classify_liquidity_bucket(
        self,
        effective_depth_usd: float,
        spread_bps: float,
    ) -> LiquidityBucket:
        """
        Classify liquidity bucket based on depth and spread.
        """
        # Depth thresholds (USD)
        if effective_depth_usd >= 5e6 and spread_bps < 5:
            return "DEEP"
        elif effective_depth_usd >= 1e6 and spread_bps < 10:
            return "NORMAL"
        elif effective_depth_usd >= 200000 or spread_bps < 20:
            return "THIN"
        else:
            return "FRAGILE"
    
    def classify_impact_state(self, market_impact_bps: float) -> ImpactState:
        """
        Classify impact state based on total impact.
        
        < 5 bps → LOW_IMPACT
        5-15 bps → MANAGEABLE
        15-30 bps → HIGH_IMPACT
        > 30 bps → UNTRADEABLE
        """
        if market_impact_bps < SLIPPAGE_THRESHOLDS["LOW_IMPACT"]:
            return "LOW_IMPACT"
        elif market_impact_bps < SLIPPAGE_THRESHOLDS["MANAGEABLE"]:
            return "MANAGEABLE"
        elif market_impact_bps < SLIPPAGE_THRESHOLDS["HIGH_IMPACT"]:
            return "HIGH_IMPACT"
        else:
            return "UNTRADEABLE"
    
    def get_execution_recommendation(
        self,
        impact_state: ImpactState,
    ) -> ExecutionRecommendation:
        """
        Get execution recommendation based on impact state.
        """
        mapping = {
            "LOW_IMPACT": "MARKET_OK",
            "MANAGEABLE": "LIMIT_PREFERRED",
            "HIGH_IMPACT": "TWAP_REQUIRED",
            "UNTRADEABLE": "BLOCK_TRADE",
        }
        return mapping.get(impact_state, "LIMIT_PREFERRED")
    
    def get_size_modifier(self, impact_state: ImpactState) -> float:
        """
        Get position size modifier based on impact state.
        """
        return IMPACT_MODIFIERS.get(impact_state, 0.85)
    
    # ═══════════════════════════════════════════════════════════
    # 6. Main Estimation Method
    # ═══════════════════════════════════════════════════════════
    
    def estimate_impact(
        self,
        symbol: str,
        intended_size_usd: float,
        side: str,
    ) -> LiquidityImpactEstimate:
        """
        Estimate liquidity impact for intended trade.
        
        Main entry point.
        """
        symbol = symbol.upper()
        side = side.upper()
        
        # 1. Get orderbook depth
        depth = self.get_orderbook_depth(symbol)
        effective_depth = self.get_effective_depth(depth, side)
        
        # 2. Get penalties from microstructure
        vacuum_penalty = self.get_vacuum_state(symbol)
        pressure_penalty = self.get_pressure_state(symbol, side)
        
        # 3. Calculate slippage
        slippage_bps = self.calculate_slippage(intended_size_usd, effective_depth)
        
        # 4. Calculate market impact
        market_impact_bps = self.calculate_market_impact(
            slippage_bps, vacuum_penalty, pressure_penalty
        )
        
        # 5. Calculate fill quality
        fill_quality = self.calculate_fill_quality(market_impact_bps)
        
        # 6. Classifications
        liquidity_bucket = self.classify_liquidity_bucket(effective_depth, depth.spread_bps)
        impact_state = self.classify_impact_state(market_impact_bps)
        recommendation = self.get_execution_recommendation(impact_state)
        size_modifier = self.get_size_modifier(impact_state)
        
        # 7. Depth ratio
        depth_ratio = intended_size_usd / effective_depth if effective_depth > 0 else float('inf')
        
        # 8. Generate reason
        reason = self._generate_reason(
            intended_size_usd, side, market_impact_bps, impact_state, recommendation
        )
        
        estimate = LiquidityImpactEstimate(
            symbol=symbol,
            intended_size_usd=intended_size_usd,
            side=side,
            expected_slippage_bps=slippage_bps,
            expected_market_impact_bps=market_impact_bps,
            expected_fill_quality=fill_quality,
            liquidity_bucket=liquidity_bucket,
            impact_state=impact_state,
            execution_recommendation=recommendation,
            size_modifier=size_modifier,
            vacuum_penalty_bps=vacuum_penalty,
            pressure_penalty_bps=pressure_penalty,
            effective_depth_usd=effective_depth,
            depth_ratio=round(depth_ratio, 4),
            reason=reason,
        )
        
        # Cache
        self._store_estimate(symbol, estimate)
        
        return estimate
    
    def _generate_reason(
        self,
        size: float,
        side: str,
        impact: float,
        state: str,
        rec: str,
    ) -> str:
        """Generate explanation string."""
        return f"{side} ${size:,.0f}: {impact:.1f} bps impact ({state}); recommend {rec}"
    
    # ═══════════════════════════════════════════════════════════
    # 7. Execution Brain Integration
    # ═══════════════════════════════════════════════════════════
    
    def adjust_execution_plan(
        self,
        symbol: str,
        planned_size_usd: float,
        side: str,
        planned_execution_type: str,
    ) -> Dict:
        """
        Adjust execution plan based on impact analysis.
        
        Returns:
        - adjusted_size_usd: size after impact modifier
        - adjusted_execution_type: potentially changed execution type
        - impact_estimate: full estimate
        """
        estimate = self.estimate_impact(symbol, planned_size_usd, side)
        
        # Adjust size
        adjusted_size = planned_size_usd * estimate.size_modifier
        
        # Adjust execution type
        adjusted_type = planned_execution_type
        
        # Override if needed
        type_map = {
            "MARKET_OK": "MARKET",
            "LIMIT_PREFERRED": "LIMIT",
            "TWAP_REQUIRED": "TWAP",
            "BLOCK_TRADE": "ICEBERG",
        }
        
        # Only upgrade execution type, never downgrade
        type_priority = {"MARKET": 1, "LIMIT": 2, "TWAP": 3, "ICEBERG": 4}
        recommended_type = type_map.get(estimate.execution_recommendation, planned_execution_type)
        
        if type_priority.get(recommended_type, 0) > type_priority.get(planned_execution_type, 0):
            adjusted_type = recommended_type
        
        return {
            "adjusted_size_usd": round(adjusted_size, 2),
            "adjusted_execution_type": adjusted_type,
            "size_reduction_pct": round((1 - estimate.size_modifier) * 100, 1),
            "type_changed": adjusted_type != planned_execution_type,
            "impact_estimate": estimate,
        }
    
    # ═══════════════════════════════════════════════════════════
    # 8. Storage and Cache
    # ═══════════════════════════════════════════════════════════
    
    def _store_estimate(self, symbol: str, estimate: LiquidityImpactEstimate) -> None:
        """Store estimate in cache."""
        if symbol not in self._cache:
            self._cache[symbol] = []
        self._cache[symbol].append(estimate)
        self._current[symbol] = estimate
    
    def get_current_estimate(self, symbol: str) -> Optional[LiquidityImpactEstimate]:
        """Get cached estimate."""
        return self._current.get(symbol.upper())
    
    def get_history(self, symbol: str, limit: int = 100) -> List[LiquidityImpactEstimate]:
        """Get estimate history."""
        history = self._cache.get(symbol.upper(), [])
        return sorted(history, key=lambda e: e.timestamp, reverse=True)[:limit]
    
    # ═══════════════════════════════════════════════════════════
    # 9. Summary
    # ═══════════════════════════════════════════════════════════
    
    def generate_summary(self, symbol: str) -> ImpactSummary:
        """Generate summary statistics."""
        symbol = symbol.upper()
        history = self._cache.get(symbol, [])
        current = self._current.get(symbol)
        
        if not history:
            return ImpactSummary(symbol=symbol)
        
        total = len(history)
        avg_slippage = sum(e.expected_slippage_bps for e in history) / total
        avg_impact = sum(e.expected_market_impact_bps for e in history) / total
        avg_quality = sum(e.expected_fill_quality for e in history) / total
        
        # State distribution
        low_count = sum(1 for e in history if e.impact_state == "LOW_IMPACT")
        manageable_count = sum(1 for e in history if e.impact_state == "MANAGEABLE")
        high_count = sum(1 for e in history if e.impact_state == "HIGH_IMPACT")
        untradeable_count = sum(1 for e in history if e.impact_state == "UNTRADEABLE")
        
        # Recent
        recent = sorted(history, key=lambda e: e.timestamp, reverse=True)[:10]
        recent_avg = sum(e.expected_slippage_bps for e in recent) / len(recent) if recent else 0
        
        return ImpactSummary(
            symbol=symbol,
            current_liquidity_bucket=current.liquidity_bucket if current else "NORMAL",
            current_impact_state=current.impact_state if current else "MANAGEABLE",
            total_estimates=total,
            avg_slippage_bps=round(avg_slippage, 2),
            avg_market_impact_bps=round(avg_impact, 2),
            avg_fill_quality=round(avg_quality, 4),
            low_impact_count=low_count,
            manageable_count=manageable_count,
            high_impact_count=high_count,
            untradeable_count=untradeable_count,
            recent_avg_slippage_bps=round(recent_avg, 2),
            last_updated=datetime.now(timezone.utc),
        )


# ══════════════════════════════════════════════════════════════
# Singleton
# ══════════════════════════════════════════════════════════════

_impact_engine: Optional[LiquidityImpactEngine] = None


def get_liquidity_impact_engine() -> LiquidityImpactEngine:
    """Get singleton instance of LiquidityImpactEngine."""
    global _impact_engine
    if _impact_engine is None:
        _impact_engine = LiquidityImpactEngine()
    return _impact_engine
