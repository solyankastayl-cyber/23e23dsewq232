"""
PHASE 4.7.1 — HTF Strength Engine

Computes strength of HTF bias (0-1).
"""

from typing import Dict


class HTFStrengthEngine:
    """
    Computes how strong the HTF bias is.
    
    Strong bias = more confidence in direction
    Weak bias = more caution needed
    """
    
    def compute(
        self,
        bias_result: Dict,
        structure_ctx: Dict,
        quality: Dict
    ) -> float:
        """
        Compute HTF strength score.
        
        Returns:
            Float 0-1 representing bias strength
        """
        bullish = bias_result.get("bullish_score", 0)
        bearish = bias_result.get("bearish_score", 0)
        
        # Base: dominance difference
        dominance = abs(bullish - bearish)
        
        # Phase bonus/penalty
        phase = structure_ctx.get("market_phase", "transition")
        phase_bonus = 0.0
        if phase == "trend":
            phase_bonus = 0.10
        elif phase == "range":
            phase_bonus = -0.10
        elif phase == "transition":
            phase_bonus = -0.05
        
        # Quality bonus
        quality_bonus = quality.get("setup_quality", 0.5) * 0.15
        
        # Penalties
        conflict_penalty = quality.get("conflict_score", 0) * 0.20
        noise_penalty = quality.get("noise_score", 0) * 0.15
        
        # Compute final strength
        strength = dominance + phase_bonus + quality_bonus - conflict_penalty - noise_penalty
        strength = max(0.0, min(strength, 1.0))
        
        return round(strength, 3)
