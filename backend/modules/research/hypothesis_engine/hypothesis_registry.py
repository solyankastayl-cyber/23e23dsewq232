"""
PHASE 6.1 - Hypothesis Registry
================================
Registry with initial 6 trading hypotheses.
"""

from datetime import datetime, timezone
from typing import Dict, List, Optional
from .hypothesis_types import (
    HypothesisDefinition, HypothesisCondition, ExpectedOutcome,
    HypothesisCategory, HypothesisStatus, ConditionOperator
)


# Initial 6 hypotheses as per requirements
INITIAL_HYPOTHESES: List[HypothesisDefinition] = [
    # 1. Volatility Compression Breakout
    HypothesisDefinition(
        hypothesis_id="volatility_compression_breakout",
        name="Volatility Compression Breakout",
        description="After period of volatility compression (low ATR, Bollinger squeeze), expect explosive breakout movement",
        category=HypothesisCategory.VOLATILITY,
        condition_set=[
            HypothesisCondition(
                indicator="volatility_compression",
                operator=ConditionOperator.GTE,
                value=0.7,
                description="Volatility compression score >= 0.7",
                weight=1.5
            ),
            HypothesisCondition(
                indicator="bollinger_squeeze",
                operator=ConditionOperator.EQ,
                value=True,
                description="Bollinger bands squeeze detected",
                weight=1.2
            ),
            HypothesisCondition(
                indicator="volume_confirmation",
                operator=ConditionOperator.GTE,
                value=1.2,
                description="Volume above 20-period average",
                weight=1.0
            )
        ],
        expected_outcome=ExpectedOutcome(
            direction="LONG",  # or SHORT based on breakout direction
            target_move_pct=3.0,
            time_horizon_candles=10,
            confidence=0.6
        ),
        applicable_regimes=["COMPRESSION", "RANGE", "TREND_UP", "TREND_DOWN"],
        applicable_timeframes=["1h", "4h", "1d"],
        status=HypothesisStatus.ACTIVE,
        tags=["breakout", "volatility", "high-probability"]
    ),
    
    # 2. Liquidity Sweep Reversal
    HypothesisDefinition(
        hypothesis_id="liquidity_sweep_reversal",
        name="Liquidity Sweep Reversal",
        description="After liquidity sweep (stop hunt) at key level, expect reversal in opposite direction",
        category=HypothesisCategory.LIQUIDITY,
        condition_set=[
            HypothesisCondition(
                indicator="liquidity_sweep",
                operator=ConditionOperator.EQ,
                value=True,
                description="Liquidity sweep detected",
                weight=1.5
            ),
            HypothesisCondition(
                indicator="key_level_proximity",
                operator=ConditionOperator.LTE,
                value=0.5,
                description="Within 0.5% of key S/R level",
                weight=1.3
            ),
            HypothesisCondition(
                indicator="rejection_wick",
                operator=ConditionOperator.GTE,
                value=0.6,
                description="Strong rejection wick >= 60% of candle",
                weight=1.2
            )
        ],
        expected_outcome=ExpectedOutcome(
            direction="LONG",  # opposite of sweep direction
            target_move_pct=2.5,
            time_horizon_candles=8,
            confidence=0.55
        ),
        applicable_regimes=["RANGE", "TREND_UP", "TREND_DOWN"],
        applicable_timeframes=["15m", "1h", "4h"],
        status=HypothesisStatus.ACTIVE,
        tags=["reversal", "liquidity", "mean-reversion"]
    ),
    
    # 3. Funding Extreme Reversal
    HypothesisDefinition(
        hypothesis_id="funding_extreme_reversal",
        name="Funding Rate Extreme Reversal",
        description="When funding rate reaches extreme levels, expect mean reversion",
        category=HypothesisCategory.FUNDING,
        condition_set=[
            HypothesisCondition(
                indicator="funding_rate_zscore",
                operator=ConditionOperator.GTE,
                value=2.0,
                description="Funding rate Z-score >= 2.0 (extreme positive)",
                weight=1.5
            ),
            HypothesisCondition(
                indicator="open_interest_change",
                operator=ConditionOperator.GTE,
                value=10.0,
                description="OI increased by >= 10% in last 24h",
                weight=1.0
            ),
            HypothesisCondition(
                indicator="price_divergence",
                operator=ConditionOperator.GTE,
                value=0.5,
                description="Price divergence from funding expectation",
                weight=0.8
            )
        ],
        expected_outcome=ExpectedOutcome(
            direction="SHORT",  # opposite of extreme funding
            target_move_pct=4.0,
            time_horizon_candles=24,
            confidence=0.55
        ),
        applicable_regimes=["TREND_UP", "EXPANSION"],
        applicable_timeframes=["4h", "1d"],
        status=HypothesisStatus.ACTIVE,
        tags=["funding", "reversal", "derivatives"]
    ),
    
    # 4. BOS with OI Continuation
    HypothesisDefinition(
        hypothesis_id="bos_with_oi_continuation",
        name="Break of Structure with OI Continuation",
        description="BOS confirmed by rising OI suggests trend continuation",
        category=HypothesisCategory.STRUCTURE,
        condition_set=[
            HypothesisCondition(
                indicator="bos_detected",
                operator=ConditionOperator.EQ,
                value=True,
                description="Break of Structure detected",
                weight=1.5
            ),
            HypothesisCondition(
                indicator="open_interest_trend",
                operator=ConditionOperator.GTE,
                value=5.0,
                description="OI growing >= 5% during move",
                weight=1.3
            ),
            HypothesisCondition(
                indicator="volume_confirmation",
                operator=ConditionOperator.GTE,
                value=1.5,
                description="Volume >= 1.5x average",
                weight=1.0
            )
        ],
        expected_outcome=ExpectedOutcome(
            direction="LONG",  # in direction of BOS
            target_move_pct=3.5,
            time_horizon_candles=12,
            confidence=0.6
        ),
        applicable_regimes=["TREND_UP", "TREND_DOWN", "EXPANSION"],
        applicable_timeframes=["1h", "4h"],
        status=HypothesisStatus.ACTIVE,
        tags=["structure", "continuation", "derivatives"]
    ),
    
    # 5. Trend Exhaustion Reversal
    HypothesisDefinition(
        hypothesis_id="trend_exhaustion_reversal",
        name="Trend Exhaustion Reversal",
        description="Extended trend with weakening momentum suggests reversal",
        category=HypothesisCategory.TREND,
        condition_set=[
            HypothesisCondition(
                indicator="trend_duration",
                operator=ConditionOperator.GTE,
                value=20,
                description="Trend lasted >= 20 candles",
                weight=1.2
            ),
            HypothesisCondition(
                indicator="rsi_divergence",
                operator=ConditionOperator.EQ,
                value=True,
                description="RSI divergence present",
                weight=1.5
            ),
            HypothesisCondition(
                indicator="volume_decline",
                operator=ConditionOperator.GTE,
                value=0.3,
                description="Volume declined >= 30% from trend start",
                weight=1.0
            ),
            HypothesisCondition(
                indicator="momentum_weakening",
                operator=ConditionOperator.GTE,
                value=0.5,
                description="Momentum weakening score >= 0.5",
                weight=1.3
            )
        ],
        expected_outcome=ExpectedOutcome(
            direction="SHORT",  # opposite of trend
            target_move_pct=5.0,
            time_horizon_candles=15,
            confidence=0.5
        ),
        applicable_regimes=["TREND_UP", "TREND_DOWN"],
        applicable_timeframes=["4h", "1d"],
        status=HypothesisStatus.ACTIVE,
        tags=["reversal", "exhaustion", "divergence"]
    ),
    
    # 6. Volume Anomaly False Breakout
    HypothesisDefinition(
        hypothesis_id="volume_anomaly_false_breakout",
        name="Volume Anomaly False Breakout",
        description="Breakout without volume confirmation likely to fail",
        category=HypothesisCategory.VOLUME,
        condition_set=[
            HypothesisCondition(
                indicator="breakout_detected",
                operator=ConditionOperator.EQ,
                value=True,
                description="Price breakout detected",
                weight=1.0
            ),
            HypothesisCondition(
                indicator="volume_ratio",
                operator=ConditionOperator.LT,
                value=0.8,
                description="Volume below average during breakout",
                weight=1.5
            ),
            HypothesisCondition(
                indicator="weak_trend_strength",
                operator=ConditionOperator.GTE,
                value=0.5,
                description="ADX/trend strength weak",
                weight=1.2
            )
        ],
        expected_outcome=ExpectedOutcome(
            direction="SHORT",  # fade the breakout
            target_move_pct=2.0,
            time_horizon_candles=6,
            confidence=0.55
        ),
        applicable_regimes=["RANGE", "COMPRESSION"],
        applicable_timeframes=["15m", "1h", "4h"],
        status=HypothesisStatus.ACTIVE,
        tags=["false-breakout", "volume", "fade"]
    )
]


class HypothesisRegistry:
    """
    Registry for managing hypothesis definitions
    """
    
    def __init__(self):
        self._hypotheses: Dict[str, HypothesisDefinition] = {}
        self._load_initial_hypotheses()
    
    def _load_initial_hypotheses(self):
        """Load initial hypotheses"""
        now = datetime.now(timezone.utc)
        for h in INITIAL_HYPOTHESES:
            h.created_at = now
            h.updated_at = now
            self._hypotheses[h.hypothesis_id] = h
    
    def get(self, hypothesis_id: str) -> Optional[HypothesisDefinition]:
        """Get hypothesis by ID"""
        return self._hypotheses.get(hypothesis_id)
    
    def get_all(self) -> List[HypothesisDefinition]:
        """Get all hypotheses"""
        return list(self._hypotheses.values())
    
    def get_active(self) -> List[HypothesisDefinition]:
        """Get active hypotheses"""
        return [h for h in self._hypotheses.values() if h.status == HypothesisStatus.ACTIVE]
    
    def get_by_category(self, category: HypothesisCategory) -> List[HypothesisDefinition]:
        """Get hypotheses by category"""
        return [h for h in self._hypotheses.values() if h.category == category]
    
    def get_by_status(self, status: HypothesisStatus) -> List[HypothesisDefinition]:
        """Get hypotheses by status"""
        return [h for h in self._hypotheses.values() if h.status == status]
    
    def add(self, hypothesis: HypothesisDefinition) -> bool:
        """Add new hypothesis"""
        if hypothesis.hypothesis_id in self._hypotheses:
            return False
        
        now = datetime.now(timezone.utc)
        hypothesis.created_at = now
        hypothesis.updated_at = now
        self._hypotheses[hypothesis.hypothesis_id] = hypothesis
        return True
    
    def update(self, hypothesis: HypothesisDefinition) -> bool:
        """Update existing hypothesis"""
        if hypothesis.hypothesis_id not in self._hypotheses:
            return False
        
        hypothesis.updated_at = datetime.now(timezone.utc)
        self._hypotheses[hypothesis.hypothesis_id] = hypothesis
        return True
    
    def update_status(self, hypothesis_id: str, status: HypothesisStatus) -> bool:
        """Update hypothesis status"""
        if hypothesis_id not in self._hypotheses:
            return False
        
        self._hypotheses[hypothesis_id].status = status
        self._hypotheses[hypothesis_id].updated_at = datetime.now(timezone.utc)
        return True
    
    def delete(self, hypothesis_id: str) -> bool:
        """Delete hypothesis"""
        if hypothesis_id not in self._hypotheses:
            return False
        
        del self._hypotheses[hypothesis_id]
        return True
    
    def search(self, query: str) -> List[HypothesisDefinition]:
        """Search hypotheses by name or description"""
        query_lower = query.lower()
        return [
            h for h in self._hypotheses.values()
            if query_lower in h.name.lower() or query_lower in h.description.lower()
        ]
    
    def get_stats(self) -> Dict:
        """Get registry statistics"""
        hypotheses = list(self._hypotheses.values())
        
        status_counts = {}
        for status in HypothesisStatus:
            status_counts[status.value] = len([h for h in hypotheses if h.status == status])
        
        category_counts = {}
        for category in HypothesisCategory:
            category_counts[category.value] = len([h for h in hypotheses if h.category == category])
        
        return {
            "total": len(hypotheses),
            "by_status": status_counts,
            "by_category": category_counts
        }


# Singleton instance
_registry_instance: Optional[HypothesisRegistry] = None


def get_hypothesis_registry() -> HypothesisRegistry:
    """Get singleton registry instance"""
    global _registry_instance
    if _registry_instance is None:
        _registry_instance = HypothesisRegistry()
    return _registry_instance
