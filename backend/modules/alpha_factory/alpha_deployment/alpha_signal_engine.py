"""
PHASE 13.7 - Alpha Signal Engine
==================================
Generates live alpha signals from deployed factors.

Workflow:
1. Get factor values from Alpha DAG
2. Apply deployment weights
3. Transform to trading signals
4. Apply regime adjustments
5. Output to strategy/risk/portfolio layers
"""

from typing import Dict, List, Optional, Any
from datetime import datetime, timezone, timedelta
import math
import random

from .deployment_types import (
    DeployedAlpha,
    AlphaSignal,
    DeploymentStatus,
    SignalDirection,
    SignalQuality
)
from .deployment_registry import DeploymentRegistry, get_deployment_registry
from .deployment_repository import DeploymentRepository


class AlphaSignalEngine:
    """
    Generates live alpha signals from deployed factors.
    
    Takes factor values from Alpha DAG and produces trading signals.
    """
    
    # Signal thresholds
    LONG_THRESHOLD = 0.3
    SHORT_THRESHOLD = -0.3
    STRONG_THRESHOLD = 0.6
    
    # Quality thresholds
    HIGH_QUALITY_CONFIDENCE = 0.7
    MEDIUM_QUALITY_CONFIDENCE = 0.5
    
    def __init__(
        self,
        registry: DeploymentRegistry = None
    ):
        self.registry = registry or get_deployment_registry()
        self.repository = DeploymentRepository()
        
        # Signal history
        self._recent_signals: Dict[str, List[AlphaSignal]] = {}
    
    def generate_signals(
        self,
        factor_values: Dict[str, float],
        symbol: str = "BTCUSDT",
        regime: str = "TRENDING",
        regime_confidence: float = 0.7
    ) -> List[AlphaSignal]:
        """
        Generate signals from factor values.
        
        Args:
            factor_values: Dict of factor_id -> value from DAG
            symbol: Target symbol
            regime: Current market regime
            regime_confidence: Regime detection confidence
        
        Returns:
            List of generated signals
        """
        signals = []
        
        # Get active deployments
        active_deployments = self.registry.get_active()
        shadow_deployments = self.registry.get_shadow()
        
        all_deployments = active_deployments + shadow_deployments
        
        for deployment in all_deployments:
            factor_id = deployment.factor_id
            
            # Get factor value
            value = factor_values.get(factor_id)
            if value is None:
                continue
            
            # Generate signal
            signal = self._generate_signal(
                deployment=deployment,
                factor_value=value,
                symbol=symbol,
                regime=regime,
                regime_confidence=regime_confidence
            )
            
            if signal:
                signals.append(signal)
                
                # Update deployment metrics
                self.registry.update_live_metrics(
                    factor_id=factor_id,
                    signal_count_delta=1
                )
        
        # Save signals
        if signals:
            self.repository.save_signals_batch(signals)
            
            # Update recent cache
            if symbol not in self._recent_signals:
                self._recent_signals[symbol] = []
            self._recent_signals[symbol].extend(signals)
            
            # Keep only recent
            cutoff = datetime.now(timezone.utc) - timedelta(hours=1)
            self._recent_signals[symbol] = [
                s for s in self._recent_signals[symbol]
                if s.timestamp and s.timestamp > cutoff
            ]
        
        return signals
    
    def _generate_signal(
        self,
        deployment: DeployedAlpha,
        factor_value: float,
        symbol: str,
        regime: str,
        regime_confidence: float
    ) -> Optional[AlphaSignal]:
        """
        Generate a single signal from a deployed factor.
        """
        # Determine direction
        direction = self._determine_direction(factor_value)
        
        # Calculate strength
        strength = self._calculate_strength(factor_value)
        
        # Calculate confidence
        confidence = self._calculate_confidence(
            deployment=deployment,
            factor_value=factor_value,
            regime=regime,
            regime_confidence=regime_confidence
        )
        
        # Determine quality
        quality = self._determine_quality(confidence, strength)
        
        # Calculate weights
        raw_weight = deployment.weight
        regime_weight = self._apply_regime_adjustment(
            deployment=deployment,
            regime=regime,
            base_weight=raw_weight
        )
        final_weight = regime_weight * confidence
        
        # Create signal
        signal = AlphaSignal(
            signal_id="",  # Auto-generated
            deployment_id=deployment.deployment_id,
            symbol=symbol,
            direction=direction,
            strength=strength,
            confidence=confidence,
            quality=quality,
            factor_id=deployment.factor_id,
            factor_family=deployment.factor_family,
            raw_weight=raw_weight,
            regime_adjusted_weight=regime_weight,
            final_weight=final_weight,
            regime=regime,
            regime_confidence=regime_confidence,
            deployment_status=deployment.status,
            shadow_mode=deployment.shadow_mode,
            timestamp=datetime.now(timezone.utc),
            expires_at=datetime.now(timezone.utc) + timedelta(hours=4)
        )
        
        return signal
    
    def _determine_direction(self, value: float) -> SignalDirection:
        """Determine signal direction from factor value."""
        if value >= self.LONG_THRESHOLD:
            return SignalDirection.LONG
        elif value <= self.SHORT_THRESHOLD:
            return SignalDirection.SHORT
        else:
            return SignalDirection.NEUTRAL
    
    def _calculate_strength(self, value: float) -> float:
        """Calculate signal strength from factor value."""
        # Normalize to -1 to 1
        strength = max(-1.0, min(1.0, value))
        return round(strength, 4)
    
    def _calculate_confidence(
        self,
        deployment: DeployedAlpha,
        factor_value: float,
        regime: str,
        regime_confidence: float
    ) -> float:
        """
        Calculate signal confidence.
        
        Based on:
        - Factor metrics (IC, Sharpe)
        - Regime alignment
        - Signal strength
        """
        # Base confidence from metrics
        base = 0.5
        
        # Boost from IC
        if deployment.ic > 0.05:
            base += min(0.2, deployment.ic * 2)
        
        # Boost from Sharpe
        if deployment.sharpe > 1.0:
            base += min(0.15, (deployment.sharpe - 1.0) * 0.1)
        
        # Regime alignment
        if regime in deployment.regime_dependency:
            base += 0.1 * regime_confidence
        elif deployment.regime_dependency:
            base -= 0.1  # Penalty for wrong regime
        
        # Signal strength bonus
        abs_value = abs(factor_value)
        if abs_value > 0.5:
            base += 0.05
        
        # Stability factor
        base *= (0.7 + 0.3 * deployment.stability)
        
        return round(max(0.1, min(0.95, base)), 4)
    
    def _determine_quality(self, confidence: float, strength: float) -> SignalQuality:
        """Determine signal quality tier."""
        abs_strength = abs(strength)
        
        if confidence >= self.HIGH_QUALITY_CONFIDENCE and abs_strength >= 0.5:
            return SignalQuality.HIGH
        elif confidence >= self.MEDIUM_QUALITY_CONFIDENCE:
            return SignalQuality.MEDIUM
        elif confidence >= 0.3:
            return SignalQuality.LOW
        else:
            return SignalQuality.UNCERTAIN
    
    def _apply_regime_adjustment(
        self,
        deployment: DeployedAlpha,
        regime: str,
        base_weight: float
    ) -> float:
        """Apply regime-based weight adjustment."""
        # Check regime weights
        if regime in deployment.regime_weights:
            return base_weight * deployment.regime_weights[regime]
        
        # Check regime dependency
        if deployment.regime_dependency:
            if regime in deployment.regime_dependency:
                return base_weight * 1.2  # Boost for matching regime
            else:
                return base_weight * 0.6  # Reduce for non-matching
        
        return base_weight
    
    def aggregate_signals(
        self,
        signals: List[AlphaSignal],
        method: str = "weighted"
    ) -> Dict:
        """
        Aggregate multiple signals into a final signal.
        
        Methods:
        - weighted: Weighted average
        - voting: Majority voting
        - consensus: Require consensus
        """
        if not signals:
            return {
                "direction": SignalDirection.NEUTRAL.value,
                "strength": 0.0,
                "confidence": 0.0,
                "quality": SignalQuality.UNCERTAIN.value,
                "signal_count": 0
            }
        
        # Filter out uncertain signals
        valid_signals = [s for s in signals if s.quality != SignalQuality.UNCERTAIN]
        
        if not valid_signals:
            return {
                "direction": SignalDirection.NEUTRAL.value,
                "strength": 0.0,
                "confidence": 0.0,
                "quality": SignalQuality.UNCERTAIN.value,
                "signal_count": len(signals)
            }
        
        if method == "weighted":
            return self._aggregate_weighted(valid_signals)
        elif method == "voting":
            return self._aggregate_voting(valid_signals)
        else:
            return self._aggregate_weighted(valid_signals)
    
    def _aggregate_weighted(self, signals: List[AlphaSignal]) -> Dict:
        """Weighted average aggregation."""
        total_weight = sum(s.final_weight for s in signals)
        if total_weight == 0:
            total_weight = 1
        
        # Weighted strength
        weighted_strength = sum(
            s.strength * s.final_weight for s in signals
        ) / total_weight
        
        # Average confidence
        avg_confidence = sum(s.confidence for s in signals) / len(signals)
        
        # Direction from weighted strength
        if weighted_strength >= self.LONG_THRESHOLD:
            direction = SignalDirection.LONG
        elif weighted_strength <= self.SHORT_THRESHOLD:
            direction = SignalDirection.SHORT
        else:
            direction = SignalDirection.NEUTRAL
        
        # Quality
        if avg_confidence >= self.HIGH_QUALITY_CONFIDENCE:
            quality = SignalQuality.HIGH
        elif avg_confidence >= self.MEDIUM_QUALITY_CONFIDENCE:
            quality = SignalQuality.MEDIUM
        else:
            quality = SignalQuality.LOW
        
        return {
            "direction": direction.value,
            "strength": round(weighted_strength, 4),
            "confidence": round(avg_confidence, 4),
            "quality": quality.value,
            "signal_count": len(signals),
            "method": "weighted"
        }
    
    def _aggregate_voting(self, signals: List[AlphaSignal]) -> Dict:
        """Majority voting aggregation."""
        long_count = sum(1 for s in signals if s.direction == SignalDirection.LONG)
        short_count = sum(1 for s in signals if s.direction == SignalDirection.SHORT)
        neutral_count = len(signals) - long_count - short_count
        
        if long_count > short_count and long_count > neutral_count:
            direction = SignalDirection.LONG
            strength = long_count / len(signals)
        elif short_count > long_count and short_count > neutral_count:
            direction = SignalDirection.SHORT
            strength = -short_count / len(signals)
        else:
            direction = SignalDirection.NEUTRAL
            strength = 0.0
        
        avg_confidence = sum(s.confidence for s in signals) / len(signals)
        
        return {
            "direction": direction.value,
            "strength": round(strength, 4),
            "confidence": round(avg_confidence, 4),
            "quality": SignalQuality.MEDIUM.value,
            "signal_count": len(signals),
            "method": "voting",
            "votes": {
                "long": long_count,
                "short": short_count,
                "neutral": neutral_count
            }
        }
    
    def get_recent_signals(
        self,
        symbol: str,
        limit: int = 50
    ) -> List[AlphaSignal]:
        """Get recent signals for symbol."""
        return self.repository.get_signals(symbol=symbol, limit=limit)
    
    def get_active_signal_summary(self, symbol: str) -> Dict:
        """Get summary of active signals for symbol."""
        signals = self.repository.get_recent_signals(symbol, hours=1)
        
        if not signals:
            return {
                "symbol": symbol,
                "active_signals": 0,
                "direction": "neutral",
                "avg_strength": 0,
                "avg_confidence": 0
            }
        
        aggregated = self.aggregate_signals(signals)
        
        return {
            "symbol": symbol,
            "active_signals": len(signals),
            "direction": aggregated["direction"],
            "avg_strength": aggregated["strength"],
            "avg_confidence": aggregated["confidence"],
            "quality": aggregated["quality"],
            "by_family": self._group_by_family(signals)
        }
    
    def _group_by_family(self, signals: List[AlphaSignal]) -> Dict:
        """Group signals by factor family."""
        by_family = {}
        for signal in signals:
            family = signal.factor_family
            if family not in by_family:
                by_family[family] = {"count": 0, "avg_strength": 0, "signals": []}
            by_family[family]["count"] += 1
            by_family[family]["signals"].append(signal.strength)
        
        for family in by_family:
            strengths = by_family[family]["signals"]
            by_family[family]["avg_strength"] = round(sum(strengths) / len(strengths), 4)
            del by_family[family]["signals"]
        
        return by_family
    
    def get_stats(self) -> Dict:
        """Get engine statistics."""
        return {
            "thresholds": {
                "long": self.LONG_THRESHOLD,
                "short": self.SHORT_THRESHOLD,
                "strong": self.STRONG_THRESHOLD,
                "high_quality_confidence": self.HIGH_QUALITY_CONFIDENCE,
                "medium_quality_confidence": self.MEDIUM_QUALITY_CONFIDENCE
            },
            "recent_signals_cached": {
                symbol: len(signals)
                for symbol, signals in self._recent_signals.items()
            },
            "repository": self.repository.get_stats()
        }


# Global singleton
_signal_engine_instance: Optional[AlphaSignalEngine] = None


def get_signal_engine() -> AlphaSignalEngine:
    """Get singleton signal engine instance."""
    global _signal_engine_instance
    if _signal_engine_instance is None:
        _signal_engine_instance = AlphaSignalEngine()
    return _signal_engine_instance
