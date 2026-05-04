"""
Exchange Conflict Resolver
===========================
Phase 14.1 — Resolves conflicts between exchange engines into unified context.

Architecture:
    Exchange Engines (5)
           ↓
    Conflict Resolver
           ↓
    Exchange Context (1 unified signal)

This module:
1. Collects outputs from all engines
2. Normalizes to common signal contract
3. Applies weights based on regime
4. Resolves conflicts
5. Returns single ExchangeContext

The Trading Layer consumes ONLY ExchangeContext, never raw engines.
"""

import os
import sys
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime, timezone

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from modules.exchange_intelligence.conflict_resolver.exchange_conflict_types import (
    ExchangeSignal,
    ExchangeContext,
    ExchangeDirection,
    DominantSignalType,
    ConflictAnalysis,
)
from modules.exchange_intelligence.conflict_resolver.exchange_conflict_weights import (
    get_weights,
    BASE_WEIGHTS,
    BIAS_THRESHOLD,
    HIGH_CONFLICT_THRESHOLD,
    DOMINANCE_THRESHOLD,
)

# Import engines
from modules.exchange_intelligence.funding_oi_engine import FundingOIEngine
from modules.exchange_intelligence.derivatives_pressure_engine import DerivativesPressureEngine
from modules.exchange_intelligence.exchange_liquidation_engine import ExchangeLiquidationEngine
from modules.exchange_intelligence.exchange_flow_engine import ExchangeFlowEngine
from modules.exchange_intelligence.exchange_volume_engine import ExchangeVolumeEngine
from modules.exchange_intelligence.exchange_intel_repository import ExchangeIntelRepository


class ExchangeConflictResolver:
    """
    Resolves conflicts between 5 exchange engines into unified context.
    
    Engines:
        - funding_oi: Funding rates and open interest
        - derivatives: Long/short ratio, leverage, premium
        - liquidations: Cascade probability, squeeze probability
        - flow: Order flow imbalance, taker pressure
        - volume: Volume anomalies, participation
    """
    
    def __init__(self, repository: Optional[ExchangeIntelRepository] = None):
        self.repo = repository or ExchangeIntelRepository()
        
        # Initialize engines
        self.funding_engine = FundingOIEngine(self.repo)
        self.derivatives_engine = DerivativesPressureEngine(self.repo)
        self.liquidation_engine = ExchangeLiquidationEngine(self.repo)
        self.flow_engine = ExchangeFlowEngine(self.repo)
        self.volume_engine = ExchangeVolumeEngine(self.repo)
    
    def resolve(self, symbol: str, regime: str = "normal") -> ExchangeContext:
        """
        Resolve all engine signals into unified ExchangeContext.
        
        Args:
            symbol: Trading pair (BTC, ETH, SOL)
            regime: Market regime for weight adjustment
        
        Returns:
            ExchangeContext with unified bias and confidence
        """
        # Step 1: Collect and normalize all signals
        signals = self._collect_signals(symbol)
        
        # Step 2: Get weights for current regime
        weights = get_weights(regime)
        
        # Step 3: Calculate weighted scores
        contributions = {}
        for engine_name, signal in signals.items():
            weight = weights.get(engine_name, 1.0)
            contributions[engine_name] = signal.weighted_score(weight)
        
        # Step 4: Aggregate score
        total_score = sum(contributions.values())
        
        # Step 5: Determine bias
        if total_score > BIAS_THRESHOLD:
            bias = ExchangeDirection.LONG
        elif total_score < -BIAS_THRESHOLD:
            bias = ExchangeDirection.SHORT
        else:
            bias = ExchangeDirection.NEUTRAL
        
        # Step 6: Calculate conflict ratio
        conflict_analysis = self._analyze_conflict(contributions)
        
        # Step 7: Find dominant signal
        dominant = self._find_dominant(contributions)
        
        # Step 8: Calculate overall confidence
        confidence = self._calculate_confidence(signals, conflict_analysis)
        
        return ExchangeContext(
            symbol=symbol,
            bias=bias,
            confidence=confidence,
            conflict_ratio=conflict_analysis.conflict_ratio,
            dominant_signal=dominant,
            contributions=contributions,
            signals=signals,
            timestamp=datetime.now(timezone.utc),
        )
    
    def _collect_signals(self, symbol: str) -> Dict[str, ExchangeSignal]:
        """Collect and normalize signals from all engines."""
        signals = {}
        
        # Funding signal
        funding_signal = self.funding_engine.compute(symbol)
        if funding_signal:
            direction = self._funding_to_direction(funding_signal)
            strength = min(abs(funding_signal.funding_annualized) / 0.5, 1.0)  # Normalize to 50% annual
            signals["funding"] = ExchangeSignal(
                engine="funding",
                direction=direction,
                strength=strength,
                confidence=funding_signal.confidence,
                raw_value=funding_signal.funding_rate,
                drivers=funding_signal.drivers,
            )
        
        # Derivatives signal
        derivatives_signal = self.derivatives_engine.compute(symbol)
        if derivatives_signal:
            direction = self._derivatives_to_direction(derivatives_signal)
            # Use squeeze probability as strength indicator
            strength = derivatives_signal.squeeze_probability
            signals["derivatives"] = ExchangeSignal(
                engine="derivatives",
                direction=direction,
                strength=strength,
                confidence=derivatives_signal.confidence,
                raw_value=derivatives_signal.long_short_ratio,
                drivers=derivatives_signal.drivers,
            )
        
        # Liquidation signal
        liq_signal = self.liquidation_engine.compute(symbol)
        if liq_signal:
            direction = self._liquidation_to_direction(liq_signal)
            # Use cascade probability as strength
            strength = liq_signal.cascade_probability
            signals["liquidations"] = ExchangeSignal(
                engine="liquidations",
                direction=direction,
                strength=strength,
                confidence=liq_signal.confidence,
                raw_value=liq_signal.cascade_probability,
                drivers=liq_signal.drivers,
            )
        
        # Flow signal
        flow_signal = self.flow_engine.compute(symbol)
        if flow_signal:
            direction = self._flow_to_direction(flow_signal)
            strength = flow_signal.flow_intensity
            signals["flow"] = ExchangeSignal(
                engine="flow",
                direction=direction,
                strength=strength,
                confidence=flow_signal.confidence,
                raw_value=flow_signal.aggressive_flow,
                drivers=flow_signal.drivers,
            )
        
        # Volume signal
        volume_signal = self.volume_engine.compute(symbol)
        if volume_signal:
            direction = self._volume_to_direction(volume_signal)
            strength = volume_signal.anomaly_score
            signals["volume"] = ExchangeSignal(
                engine="volume",
                direction=direction,
                strength=strength,
                confidence=volume_signal.confidence,
                raw_value=volume_signal.volume_ratio,
                drivers=volume_signal.drivers,
            )
        
        return signals
    
    def _funding_to_direction(self, signal) -> ExchangeDirection:
        """Convert funding signal to direction."""
        # Extreme funding = contrarian signal (crowded position may unwind)
        # Positive funding = longs pay shorts = market is long heavy
        # For bias: high positive funding = SHORT bias (longs crowded)
        if signal.funding_annualized > 0.05:  # >5% annual = extreme
            return ExchangeDirection.SHORT
        elif signal.funding_annualized < -0.05:
            return ExchangeDirection.LONG
        elif signal.funding_annualized > 0.02:
            return ExchangeDirection.SHORT
        elif signal.funding_annualized < -0.02:
            return ExchangeDirection.LONG
        return ExchangeDirection.NEUTRAL
    
    def _derivatives_to_direction(self, signal) -> ExchangeDirection:
        """Convert derivatives signal to direction."""
        # L/S ratio > 1.2 = longs dominate = SHORT bias (crowded)
        # L/S ratio < 0.8 = shorts dominate = LONG bias (squeeze potential)
        if signal.long_short_ratio > 1.5:
            return ExchangeDirection.SHORT
        elif signal.long_short_ratio < 0.67:
            return ExchangeDirection.LONG
        elif signal.long_short_ratio > 1.2:
            return ExchangeDirection.SHORT
        elif signal.long_short_ratio < 0.8:
            return ExchangeDirection.LONG
        return ExchangeDirection.NEUTRAL
    
    def _liquidation_to_direction(self, signal) -> ExchangeDirection:
        """Convert liquidation signal to direction."""
        # Analyze trapped positions - more trapped longs = bearish pressure
        # More trapped shorts = bullish (short squeeze potential)
        if signal.trapped_shorts_pct > signal.trapped_longs_pct + 0.1:
            return ExchangeDirection.LONG  # Short squeeze potential
        elif signal.trapped_longs_pct > signal.trapped_shorts_pct + 0.1:
            return ExchangeDirection.SHORT  # Long cascade potential
        elif signal.net_liq_flow > 0.2:
            return ExchangeDirection.SHORT  # More long liquidations
        elif signal.net_liq_flow < -0.2:
            return ExchangeDirection.LONG  # More short liquidations
        return ExchangeDirection.NEUTRAL
    
    def _flow_to_direction(self, signal) -> ExchangeDirection:
        """Convert flow signal to direction."""
        if signal.aggressive_flow > 0.2:
            return ExchangeDirection.LONG
        elif signal.aggressive_flow < -0.2:
            return ExchangeDirection.SHORT
        elif signal.taker_buy_ratio > 0.55:
            return ExchangeDirection.LONG
        elif signal.taker_buy_ratio < 0.45:
            return ExchangeDirection.SHORT
        return ExchangeDirection.NEUTRAL
    
    def _volume_to_direction(self, signal) -> ExchangeDirection:
        """Convert volume signal to direction."""
        # Volume alone doesn't give direction, use with price context
        # High volume confirms move, low volume suggests reversal
        if signal.volume_trend == "EXPANDING" or signal.volume_trend == "INCREASING":
            return ExchangeDirection.LONG  # Momentum
        elif signal.volume_trend == "CONTRACTING" or signal.volume_trend == "DECREASING":
            return ExchangeDirection.SHORT  # Exhaustion
        return ExchangeDirection.NEUTRAL
    
    def _analyze_conflict(self, contributions: Dict[str, float]) -> ConflictAnalysis:
        """Analyze conflict between signals."""
        bullish_strength = sum(v for v in contributions.values() if v > 0)
        bearish_strength = abs(sum(v for v in contributions.values() if v < 0))
        total_strength = bullish_strength + bearish_strength
        
        if total_strength == 0:
            conflict_ratio = 0.0
            agreement_ratio = 1.0
        else:
            # Conflict ratio: how much do signals disagree
            minority_strength = min(bullish_strength, bearish_strength)
            conflict_ratio = minority_strength / total_strength
            agreement_ratio = 1.0 - conflict_ratio
        
        bullish_engines = [k for k, v in contributions.items() if v > 0]
        bearish_engines = [k for k, v in contributions.items() if v < 0]
        neutral_engines = [k for k, v in contributions.items() if v == 0]
        
        return ConflictAnalysis(
            bullish_strength=bullish_strength,
            bearish_strength=bearish_strength,
            total_strength=total_strength,
            conflict_ratio=conflict_ratio,
            agreement_ratio=agreement_ratio,
            bullish_engines=bullish_engines,
            bearish_engines=bearish_engines,
            neutral_engines=neutral_engines,
        )
    
    def _find_dominant(self, contributions: Dict[str, float]) -> DominantSignalType:
        """Find the dominant contributing signal."""
        if not contributions:
            return DominantSignalType.NONE
        
        # Find max absolute contribution
        abs_contributions = {k: abs(v) for k, v in contributions.items()}
        sorted_signals = sorted(abs_contributions.items(), key=lambda x: -x[1])
        
        if not sorted_signals:
            return DominantSignalType.NONE
        
        top_signal, top_value = sorted_signals[0]
        
        # Check if it's clearly dominant (1.2x stronger than 2nd)
        if len(sorted_signals) > 1:
            second_value = sorted_signals[1][1]
            if second_value > 0 and top_value / second_value < DOMINANCE_THRESHOLD:
                # No clear dominant, use highest weighted
                pass
        
        return DominantSignalType(top_signal)
    
    def _calculate_confidence(
        self, 
        signals: Dict[str, ExchangeSignal],
        conflict: ConflictAnalysis
    ) -> float:
        """Calculate overall confidence in the resolved context."""
        if not signals:
            return 0.0
        
        # Base confidence = average of engine confidences
        avg_confidence = sum(s.confidence for s in signals.values()) / len(signals)
        
        # Penalize for high conflict
        conflict_penalty = conflict.conflict_ratio * 0.3
        
        # Boost for high agreement
        agreement_boost = conflict.agreement_ratio * 0.1
        
        confidence = avg_confidence - conflict_penalty + agreement_boost
        return max(0.0, min(1.0, confidence))
    
    def get_detailed_analysis(self, symbol: str, regime: str = "normal") -> dict:
        """Get detailed analysis including conflict breakdown."""
        context = self.resolve(symbol, regime)
        signals = self._collect_signals(symbol)
        weights = get_weights(regime)
        
        contributions = {}
        for engine_name, signal in signals.items():
            weight = weights.get(engine_name, 1.0)
            contributions[engine_name] = signal.weighted_score(weight)
        
        conflict = self._analyze_conflict(contributions)
        
        return {
            "context": context.to_dict(),
            "conflict_analysis": conflict.to_dict(),
            "weights_used": weights,
            "regime": regime,
            "raw_signals": {
                name: {
                    "direction": sig.direction.value,
                    "strength": round(sig.strength, 4),
                    "confidence": round(sig.confidence, 4),
                    "raw_value": round(sig.raw_value, 6),
                    "weighted_score": round(contributions.get(name, 0), 4),
                }
                for name, sig in signals.items()
            },
        }


# Singleton instance
_resolver: Optional[ExchangeConflictResolver] = None


def get_conflict_resolver() -> ExchangeConflictResolver:
    """Get singleton resolver instance."""
    global _resolver
    if _resolver is None:
        _resolver = ExchangeConflictResolver()
    return _resolver
