"""
PHASE 4.7.1 — HTF Bias Engine

Computes HTF directional bias (bullish/bearish/neutral).
"""

from typing import Dict


class HTFBiasEngine:
    """
    Computes HTF directional bias.
    
    Combines:
    - Structure
    - Trend
    - Momentum
    - Quality factors
    """
    
    def compute(
        self,
        structure_ctx: Dict,
        trend: Dict,
        momentum: Dict,
        quality: Dict
    ) -> Dict:
        """
        Compute HTF bias.
        
        Returns:
            htf_bias (bullish/bearish/neutral), scores, reasons
        """
        bullish = 0.0
        bearish = 0.0
        reasons = []
        
        # Structure contribution (35%)
        bullish += structure_ctx.get("bullish_structure_score", 0) * 0.35
        bearish += structure_ctx.get("bearish_structure_score", 0) * 0.35
        
        # Trend contribution (25%)
        trend_bias = trend.get("trend_bias", 0)
        if trend_bias > 0:
            bullish += abs(trend_bias) * 0.25
        elif trend_bias < 0:
            bearish += abs(trend_bias) * 0.25
        
        # EMA stack (15%)
        ema_stack = trend.get("ema_stack", "mixed")
        if ema_stack == "bullish":
            bullish += 0.15
            reasons.append("ema_alignment_bullish")
        elif ema_stack == "bearish":
            bearish += 0.15
            reasons.append("ema_alignment_bearish")
        
        # Momentum contribution (15%)
        momentum_bias = momentum.get("momentum_bias", 0)
        if momentum_bias > 0:
            bullish += abs(momentum_bias) * 0.15
        elif momentum_bias < 0:
            bearish += abs(momentum_bias) * 0.15
        
        # RSI state (5%)
        rsi_state = momentum.get("rsi_state", "neutral")
        if rsi_state == "bullish":
            bullish += 0.05
            reasons.append("momentum_supportive")
        elif rsi_state == "bearish":
            bearish += 0.05
            reasons.append("momentum_supportive_bearish")
        
        # Quality penalties
        noise_penalty = quality.get("noise_score", 0) * 0.3
        conflict_penalty = quality.get("conflict_score", 0) * 0.4
        
        bullish *= (1 - noise_penalty)
        bearish *= (1 - noise_penalty)
        bullish *= (1 - conflict_penalty)
        bearish *= (1 - conflict_penalty)
        
        # Determine bias
        diff = abs(bullish - bearish)
        
        if diff < 0.12:
            return {
                "htf_bias": "neutral",
                "bullish_score": round(bullish, 3),
                "bearish_score": round(bearish, 3),
                "reasons": reasons + ["mixed_htf"]
            }
        
        if bullish > bearish:
            reasons.append("bullish_structure")
            return {
                "htf_bias": "bullish",
                "bullish_score": round(bullish, 3),
                "bearish_score": round(bearish, 3),
                "reasons": reasons
            }
        
        reasons.append("bearish_structure")
        return {
            "htf_bias": "bearish",
            "bullish_score": round(bullish, 3),
            "bearish_score": round(bearish, 3),
            "reasons": reasons
        }
