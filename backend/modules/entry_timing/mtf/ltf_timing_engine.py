"""
PHASE 4.7.2 — LTF Timing Engine

Computes LTF timing score for entry.
"""

from typing import Dict


class LTFTimingEngine:
    """
    Computes LTF timing score.
    
    Combines structure, confirmation, conflict, volatility
    into a single timing score 0-1.
    """
    
    def compute(
        self,
        structure_ctx: Dict,
        confirmation_ctx: Dict,
        conflict_ctx: Dict,
        volatility: Dict,
        quality: Dict
    ) -> float:
        """
        Compute timing score.
        
        Returns:
            Float 0-1 representing timing quality
        """
        score = 0.0
        
        # Structure contribution (30%)
        score += structure_ctx.get("structure_strength", 0) * 0.30
        
        # Pullback readiness (20%)
        if structure_ctx.get("pullback_ready", False):
            score += 0.20
        
        # Confirmation contribution (20%)
        if confirmation_ctx.get("ltf_confirmation", False):
            score += 0.20
        
        # Breakout strength bonus (15%)
        reasons = confirmation_ctx.get("reasons", [])
        if "breakout_strength_good" in reasons:
            score += 0.15
        
        # Volatility contribution (10%)
        vol_state = volatility.get("volatility_state", "normal")
        if vol_state == "normal":
            score += 0.10
        elif vol_state == "elevated":
            score += 0.05
        
        # Noise penalty
        noise = quality.get("noise_score", 0)
        score *= (1 - noise * 0.25)
        
        # Conflict penalty (heavy)
        if conflict_ctx.get("ltf_conflict", False):
            score *= 0.35
        
        return round(max(0.0, min(score, 1.0)), 3)
