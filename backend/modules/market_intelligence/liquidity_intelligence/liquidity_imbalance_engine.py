"""
PHASE 8 - Liquidity Imbalance Engine
======================================
Analyzes bid/ask imbalance and order flow pressure.

Detects:
- Bid dominance
- Ask dominance
- Sudden vacuum
- One-sided book pressure
"""

import random
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timezone

from .liquidity_types import (
    LiquidityImbalance, ImbalanceSide, DepthProfile, DEFAULT_CONFIG
)


class LiquidityImbalanceEngine:
    """
    Analyzes liquidity imbalance in the orderbook.
    
    Imbalance indicates potential directional pressure.
    """
    
    def __init__(self, config: Dict = None):
        self.config = config or DEFAULT_CONFIG
        
        # Imbalance thresholds
        self.significant_imbalance = 0.3  # 30% difference
        self.extreme_imbalance = 0.5      # 50% difference
    
    def analyze_imbalance(
        self,
        depth_profile: DepthProfile,
        recent_imbalances: List[float] = None,
        symbol: str = "BTCUSDT"
    ) -> LiquidityImbalance:
        """
        Analyze current liquidity imbalance.
        
        Args:
            depth_profile: Current orderbook depth profile
            recent_imbalances: Historical imbalance values for trend
            symbol: Trading symbol
        
        Returns:
            LiquidityImbalance with analysis
        """
        now = datetime.now(timezone.utc)
        
        # Calculate basic imbalance
        bid_depth = depth_profile.bid_depth
        ask_depth = depth_profile.ask_depth
        
        if bid_depth + ask_depth == 0:
            return self._empty_imbalance(symbol, now)
        
        # Imbalance score: -1 (ask dominant) to +1 (bid dominant)
        imbalance_score = (bid_depth - ask_depth) / (bid_depth + ask_depth)
        
        # Determine dominant side
        if imbalance_score > self.significant_imbalance:
            dominant_side = ImbalanceSide.BID_DOMINANT
        elif imbalance_score < -self.significant_imbalance:
            dominant_side = ImbalanceSide.ASK_DOMINANT
        else:
            dominant_side = ImbalanceSide.BALANCED
        
        # Calculate pressures
        total_depth = bid_depth + ask_depth
        bid_pressure = bid_depth / total_depth
        ask_pressure = ask_depth / total_depth
        net_pressure = bid_pressure - ask_pressure
        
        # Calculate stability (how stable is the imbalance)
        stability = self._calculate_stability(imbalance_score, recent_imbalances)
        
        # Calculate volatility risk
        volatility_risk = self._calculate_volatility_risk(
            imbalance_score, stability, depth_profile
        )
        
        # Determine trend
        trend = self._calculate_trend(imbalance_score, recent_imbalances)
        
        return LiquidityImbalance(
            symbol=symbol,
            imbalance_score=imbalance_score,
            dominant_side=dominant_side,
            imbalance_stability=stability,
            volatility_risk=volatility_risk,
            bid_pressure=bid_pressure,
            ask_pressure=ask_pressure,
            net_pressure=net_pressure,
            imbalance_trend=trend,
            computed_at=now
        )
    
    def _calculate_stability(
        self,
        current_imbalance: float,
        recent_imbalances: List[float] = None
    ) -> float:
        """Calculate how stable the imbalance is."""
        if not recent_imbalances or len(recent_imbalances) < 3:
            return 0.5  # Neutral stability
        
        # Calculate variance of recent imbalances
        mean = sum(recent_imbalances) / len(recent_imbalances)
        variance = sum((x - mean) ** 2 for x in recent_imbalances) / len(recent_imbalances)
        std = variance ** 0.5
        
        # Low variance = high stability
        stability = max(0.1, min(0.95, 1 - std * 2))
        
        return stability
    
    def _calculate_volatility_risk(
        self,
        imbalance_score: float,
        stability: float,
        depth_profile: DepthProfile
    ) -> float:
        """Calculate risk of sudden price moves."""
        risk = 0.3  # Base risk
        
        # Extreme imbalance increases risk
        if abs(imbalance_score) > self.extreme_imbalance:
            risk += 0.3
        elif abs(imbalance_score) > self.significant_imbalance:
            risk += 0.15
        
        # Low stability increases risk
        risk += (1 - stability) * 0.2
        
        # Thin liquidity increases risk
        if depth_profile.liquidity_quality.value in ["POOR", "CRITICAL"]:
            risk += 0.2
        
        # Wide spread increases risk
        if depth_profile.spread_bps > 20:
            risk += 0.1
        
        return max(0.1, min(0.95, risk))
    
    def _calculate_trend(
        self,
        current_imbalance: float,
        recent_imbalances: List[float] = None
    ) -> str:
        """Calculate imbalance trend."""
        if not recent_imbalances or len(recent_imbalances) < 5:
            return "STABLE"
        
        # Compare recent to older
        recent_avg = sum(recent_imbalances[-3:]) / 3
        older_avg = sum(recent_imbalances[-6:-3]) / 3 if len(recent_imbalances) >= 6 else recent_avg
        
        change = recent_avg - older_avg
        
        if change > 0.1:
            return "INCREASING"  # Becoming more bid-dominant
        elif change < -0.1:
            return "DECREASING"  # Becoming more ask-dominant
        else:
            return "STABLE"
    
    def _empty_imbalance(
        self,
        symbol: str,
        timestamp: datetime
    ) -> LiquidityImbalance:
        """Return empty imbalance when no data."""
        return LiquidityImbalance(
            symbol=symbol,
            imbalance_score=0.0,
            dominant_side=ImbalanceSide.BALANCED,
            imbalance_stability=0.0,
            volatility_risk=1.0,
            bid_pressure=0.5,
            ask_pressure=0.5,
            net_pressure=0.0,
            imbalance_trend="UNKNOWN",
            computed_at=timestamp
        )
    
    def detect_sudden_vacuum(
        self,
        current_imbalance: LiquidityImbalance,
        recent_imbalances: List[LiquidityImbalance],
        threshold: float = 0.4
    ) -> Optional[Dict]:
        """Detect sudden liquidity vacuum (rapid change)."""
        if not recent_imbalances:
            return None
        
        # Calculate change from recent average
        recent_scores = [i.imbalance_score for i in recent_imbalances[-5:]]
        avg_score = sum(recent_scores) / len(recent_scores)
        
        change = current_imbalance.imbalance_score - avg_score
        
        if abs(change) >= threshold:
            return {
                "detected": True,
                "change_magnitude": round(change, 4),
                "direction": "BID_VACUUM" if change < 0 else "ASK_VACUUM",
                "severity": "SEVERE" if abs(change) > 0.6 else "MODERATE",
                "implication": "Potential rapid move " + ("down" if change < 0 else "up"),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        
        return None
    
    def detect_one_sided_pressure(
        self,
        imbalance: LiquidityImbalance,
        duration_samples: int = 5
    ) -> Optional[Dict]:
        """Detect sustained one-sided pressure."""
        if abs(imbalance.imbalance_score) < self.significant_imbalance:
            return None
        
        if imbalance.imbalance_stability < 0.6:
            return None  # Not sustained
        
        direction = "BID" if imbalance.imbalance_score > 0 else "ASK"
        
        return {
            "detected": True,
            "direction": f"{direction}_PRESSURE",
            "strength": round(abs(imbalance.imbalance_score), 3),
            "stability": round(imbalance.imbalance_stability, 3),
            "expected_move": "UP" if direction == "BID" else "DOWN",
            "confidence": round(imbalance.imbalance_stability * abs(imbalance.imbalance_score), 3),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    
    def get_trading_signal(
        self,
        imbalance: LiquidityImbalance
    ) -> Dict:
        """Convert imbalance to trading signal."""
        if abs(imbalance.imbalance_score) < self.significant_imbalance:
            signal = "NEUTRAL"
            strength = 0.0
        elif imbalance.dominant_side == ImbalanceSide.BID_DOMINANT:
            signal = "BULLISH"
            strength = min(1.0, abs(imbalance.imbalance_score) * imbalance.imbalance_stability)
        else:
            signal = "BEARISH"
            strength = min(1.0, abs(imbalance.imbalance_score) * imbalance.imbalance_stability)
        
        return {
            "signal": signal,
            "strength": round(strength, 3),
            "volatility_risk": round(imbalance.volatility_risk, 3),
            "trend": imbalance.imbalance_trend,
            "description": f"{imbalance.dominant_side.value} with {imbalance.imbalance_trend} trend"
        }
    
    def get_imbalance_summary(
        self,
        imbalances: List[LiquidityImbalance]
    ) -> Dict:
        """Get summary of imbalance history."""
        if not imbalances:
            return {"total_samples": 0}
        
        scores = [i.imbalance_score for i in imbalances]
        
        bid_dominant_count = sum(1 for i in imbalances if i.dominant_side == ImbalanceSide.BID_DOMINANT)
        ask_dominant_count = sum(1 for i in imbalances if i.dominant_side == ImbalanceSide.ASK_DOMINANT)
        
        return {
            "total_samples": len(imbalances),
            "avg_imbalance": round(sum(scores) / len(scores), 4),
            "max_imbalance": round(max(scores), 4),
            "min_imbalance": round(min(scores), 4),
            "bid_dominant_pct": round(bid_dominant_count / len(imbalances) * 100, 1),
            "ask_dominant_pct": round(ask_dominant_count / len(imbalances) * 100, 1),
            "avg_volatility_risk": round(
                sum(i.volatility_risk for i in imbalances) / len(imbalances), 3
            ),
            "current": imbalances[-1].to_dict() if imbalances else None
        }
