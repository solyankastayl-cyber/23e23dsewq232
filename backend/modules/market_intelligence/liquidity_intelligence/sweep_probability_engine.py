"""
PHASE 8 - Sweep Probability Engine
=====================================
Estimates probability of liquidity sweeps.

Analyzes:
- Sweep probability at key levels
- Post-sweep directional bias
- Reclaim probability after sweep
"""

import random
from typing import Dict, List, Optional
from datetime import datetime, timezone

from .liquidity_types import (
    SweepSignal, SweepDirection, PostSweepBias,
    StopCluster, LiquidityZone, StopClusterSide, DEFAULT_CONFIG
)


class SweepProbabilityEngine:
    """
    Estimates the probability of price sweeping liquidity levels.
    
    A sweep occurs when price briefly breaks a level to trigger stops,
    then reverses direction.
    """
    
    def __init__(self, config: Dict = None):
        self.config = config or DEFAULT_CONFIG
        
        # Base probabilities
        self.base_sweep_prob = 0.3
        
        # Factors that increase sweep probability
        self.factors = {
            "stop_cluster_nearby": 0.15,
            "thin_liquidity_above": 0.12,
            "equal_highs_lows": 0.18,
            "range_boundary": 0.10,
            "high_leverage_zone": 0.14,
        }
    
    def calculate_sweep_signals(
        self,
        current_price: float,
        stop_clusters: List[StopCluster],
        liquidity_zones: List[LiquidityZone],
        price_trend: str = "NEUTRAL",  # "UP", "DOWN", "NEUTRAL"
        symbol: str = "BTCUSDT"
    ) -> List[SweepSignal]:
        """
        Calculate sweep probability signals.
        
        Args:
            current_price: Current market price
            stop_clusters: Detected stop clusters
            liquidity_zones: Detected liquidity zones
            price_trend: Current price trend
            symbol: Trading symbol
        
        Returns:
            List of sweep signals
        """
        signals = []
        now = datetime.now(timezone.utc)
        
        # Analyze upside sweeps (sweep above current price)
        upside_signals = self._analyze_upside_sweeps(
            current_price, stop_clusters, liquidity_zones, price_trend, symbol, now
        )
        signals.extend(upside_signals)
        
        # Analyze downside sweeps (sweep below current price)
        downside_signals = self._analyze_downside_sweeps(
            current_price, stop_clusters, liquidity_zones, price_trend, symbol, now
        )
        signals.extend(downside_signals)
        
        # Sort by sweep probability
        signals.sort(key=lambda s: s.sweep_probability, reverse=True)
        
        return signals
    
    def _analyze_upside_sweeps(
        self,
        current_price: float,
        stop_clusters: List[StopCluster],
        liquidity_zones: List[LiquidityZone],
        price_trend: str,
        symbol: str,
        timestamp: datetime
    ) -> List[SweepSignal]:
        """Analyze potential upside sweeps."""
        signals = []
        
        # Get stop clusters above (short stops)
        short_stops_above = [
            c for c in stop_clusters
            if c.side == StopClusterSide.SHORT_STOPS and c.price_level > current_price
        ]
        
        for cluster in short_stops_above[:3]:  # Top 3
            sweep_prob = self._calculate_sweep_probability(
                cluster, liquidity_zones, current_price, "UPSIDE", price_trend
            )
            
            # Post-sweep bias (after sweeping short stops, expect reversal down)
            post_sweep_bias = PostSweepBias.BEARISH
            reclaim_prob = self._calculate_reclaim_probability(
                cluster, price_trend, "UPSIDE"
            )
            
            signals.append(SweepSignal(
                symbol=symbol,
                sweep_probability=sweep_prob,
                sweep_direction=SweepDirection.UPSIDE,
                target_level=cluster.price_level,
                post_sweep_bias=post_sweep_bias,
                reclaim_probability=reclaim_prob,
                trigger_zone=cluster.trigger_type,
                distance_to_target=cluster.distance_from_current,
                distance_pct=cluster.distance_pct,
                confidence=cluster.confidence,
                generated_at=timestamp
            ))
        
        # Check liquidity zones for sweep potential
        sweep_zones = [
            z for z in liquidity_zones
            if z.sweep_probability > 0.4 and z.mid_price > current_price
        ]
        
        for zone in sweep_zones[:2]:
            signals.append(SweepSignal(
                symbol=symbol,
                sweep_probability=zone.sweep_probability,
                sweep_direction=SweepDirection.UPSIDE,
                target_level=zone.mid_price,
                post_sweep_bias=PostSweepBias.BEARISH,
                reclaim_probability=0.6,
                trigger_zone=zone.zone_type.value,
                distance_to_target=zone.mid_price - current_price,
                distance_pct=(zone.mid_price - current_price) / current_price,
                confidence=zone.liquidity_score,
                generated_at=timestamp
            ))
        
        return signals
    
    def _analyze_downside_sweeps(
        self,
        current_price: float,
        stop_clusters: List[StopCluster],
        liquidity_zones: List[LiquidityZone],
        price_trend: str,
        symbol: str,
        timestamp: datetime
    ) -> List[SweepSignal]:
        """Analyze potential downside sweeps."""
        signals = []
        
        # Get stop clusters below (long stops)
        long_stops_below = [
            c for c in stop_clusters
            if c.side == StopClusterSide.LONG_STOPS and c.price_level < current_price
        ]
        
        for cluster in long_stops_below[:3]:
            sweep_prob = self._calculate_sweep_probability(
                cluster, liquidity_zones, current_price, "DOWNSIDE", price_trend
            )
            
            # Post-sweep bias (after sweeping long stops, expect reversal up)
            post_sweep_bias = PostSweepBias.BULLISH
            reclaim_prob = self._calculate_reclaim_probability(
                cluster, price_trend, "DOWNSIDE"
            )
            
            signals.append(SweepSignal(
                symbol=symbol,
                sweep_probability=sweep_prob,
                sweep_direction=SweepDirection.DOWNSIDE,
                target_level=cluster.price_level,
                post_sweep_bias=post_sweep_bias,
                reclaim_probability=reclaim_prob,
                trigger_zone=cluster.trigger_type,
                distance_to_target=cluster.distance_from_current,
                distance_pct=cluster.distance_pct,
                confidence=cluster.confidence,
                generated_at=timestamp
            ))
        
        # Check liquidity zones for sweep potential
        sweep_zones = [
            z for z in liquidity_zones
            if z.sweep_probability > 0.4 and z.mid_price < current_price
        ]
        
        for zone in sweep_zones[:2]:
            signals.append(SweepSignal(
                symbol=symbol,
                sweep_probability=zone.sweep_probability,
                sweep_direction=SweepDirection.DOWNSIDE,
                target_level=zone.mid_price,
                post_sweep_bias=PostSweepBias.BULLISH,
                reclaim_probability=0.6,
                trigger_zone=zone.zone_type.value,
                distance_to_target=current_price - zone.mid_price,
                distance_pct=(current_price - zone.mid_price) / current_price,
                confidence=zone.liquidity_score,
                generated_at=timestamp
            ))
        
        return signals
    
    def _calculate_sweep_probability(
        self,
        cluster: StopCluster,
        liquidity_zones: List[LiquidityZone],
        current_price: float,
        direction: str,
        price_trend: str
    ) -> float:
        """Calculate probability of sweeping a specific level."""
        prob = self.base_sweep_prob
        
        # Factor: Stop cluster strength
        prob += cluster.cluster_strength * 0.2
        
        # Factor: Distance (closer = higher probability)
        if cluster.distance_pct < 0.01:  # Within 1%
            prob += 0.15
        elif cluster.distance_pct < 0.02:
            prob += 0.08
        
        # Factor: Equal highs/lows (very sweep-prone)
        if cluster.trigger_type in ["equal_highs", "equal_lows"]:
            prob += self.factors["equal_highs_lows"]
        
        # Factor: Range boundary
        if cluster.trigger_type in ["range_high", "range_low"]:
            prob += self.factors["range_boundary"]
        
        # Factor: Trend alignment
        if direction == "UPSIDE" and price_trend == "UP":
            prob += 0.1  # Trend supports move to sweep
        elif direction == "DOWNSIDE" and price_trend == "DOWN":
            prob += 0.1
        elif (direction == "UPSIDE" and price_trend == "DOWN") or \
             (direction == "DOWNSIDE" and price_trend == "UP"):
            prob -= 0.05  # Counter-trend sweep less likely
        
        # Factor: Thin liquidity beyond cluster
        thin_zones_beyond = [
            z for z in liquidity_zones
            if z.zone_type.value == "LOW_LIQUIDITY"
        ]
        if thin_zones_beyond:
            prob += self.factors["thin_liquidity_above"]
        
        # Clamp probability
        return max(0.1, min(0.9, prob))
    
    def _calculate_reclaim_probability(
        self,
        cluster: StopCluster,
        price_trend: str,
        sweep_direction: str
    ) -> float:
        """Calculate probability of price reclaiming after sweep."""
        # Base reclaim probability
        reclaim = 0.55
        
        # Strong sweeps more likely to hold (not reclaim)
        reclaim -= cluster.cluster_strength * 0.15
        
        # Trend affects reclaim
        if sweep_direction == "UPSIDE" and price_trend == "UP":
            reclaim -= 0.1  # Strong trend may continue, not reclaim
        elif sweep_direction == "DOWNSIDE" and price_trend == "DOWN":
            reclaim -= 0.1
        
        # Equal highs/lows more likely to reclaim (classic sweep)
        if cluster.trigger_type in ["equal_highs", "equal_lows"]:
            reclaim += 0.15
        
        return max(0.2, min(0.85, reclaim))
    
    def get_highest_probability_sweep(
        self,
        signals: List[SweepSignal]
    ) -> Optional[SweepSignal]:
        """Get the sweep with highest probability."""
        if not signals:
            return None
        return max(signals, key=lambda s: s.sweep_probability)
    
    def get_sweep_summary(
        self,
        signals: List[SweepSignal],
        current_price: float
    ) -> Dict:
        """Get summary of sweep signals."""
        if not signals:
            return {
                "total_signals": 0,
                "dominant_direction": None
            }
        
        upside = [s for s in signals if s.sweep_direction == SweepDirection.UPSIDE]
        downside = [s for s in signals if s.sweep_direction == SweepDirection.DOWNSIDE]
        
        # Determine dominant direction
        avg_up_prob = sum(s.sweep_probability for s in upside) / len(upside) if upside else 0
        avg_down_prob = sum(s.sweep_probability for s in downside) / len(downside) if downside else 0
        
        if avg_up_prob > avg_down_prob + 0.1:
            dominant = "UPSIDE"
        elif avg_down_prob > avg_up_prob + 0.1:
            dominant = "DOWNSIDE"
        else:
            dominant = "NEUTRAL"
        
        highest = self.get_highest_probability_sweep(signals)
        
        return {
            "total_signals": len(signals),
            "upside_signals": len(upside),
            "downside_signals": len(downside),
            "avg_upside_probability": round(avg_up_prob, 3),
            "avg_downside_probability": round(avg_down_prob, 3),
            "dominant_direction": dominant,
            "highest_probability_sweep": highest.to_dict() if highest else None,
            "avg_reclaim_probability": round(
                sum(s.reclaim_probability for s in signals) / len(signals), 3
            )
        }
    
    def get_actionable_sweeps(
        self,
        signals: List[SweepSignal],
        min_probability: float = 0.5,
        max_distance_pct: float = 0.03
    ) -> List[SweepSignal]:
        """Get sweeps that are actionable (high prob, close enough)."""
        return [
            s for s in signals
            if s.sweep_probability >= min_probability
            and s.distance_pct <= max_distance_pct
        ]
