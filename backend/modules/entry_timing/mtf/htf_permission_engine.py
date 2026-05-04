"""
PHASE 4.7.1 — HTF Permission Engine

Determines what trading is allowed based on HTF context.
"""

from typing import Dict


class HTFPermissionEngine:
    """
    Determines trading permissions based on HTF.
    
    Outputs:
    - allow_long: Can trade long
    - allow_short: Can trade short
    - allow_countertrend: Can trade against HTF bias
    """
    
    def compute(
        self,
        bias: str,
        strength: float,
        structure_ctx: Dict
    ) -> Dict:
        """
        Compute trading permissions.
        
        Args:
            bias: HTF bias (bullish/bearish/neutral)
            strength: HTF strength (0-1)
            structure_ctx: Structure context with market_phase
        
        Returns:
            Permission flags
        """
        phase = structure_ctx.get("market_phase", "transition")
        
        allow_long = False
        allow_short = False
        allow_countertrend = False
        
        if bias == "bullish":
            allow_long = True
            # Allow shorts only in weak bullish range
            allow_short = strength < 0.35 and phase == "range"
        
        elif bias == "bearish":
            allow_short = True
            # Allow longs only in weak bearish range
            allow_long = strength < 0.35 and phase == "range"
        
        else:  # neutral
            # Both directions allowed in range/transition
            allow_long = phase in ["range", "transition"]
            allow_short = phase in ["range", "transition"]
        
        # Countertrend rules
        if strength > 0.65:
            # Strong trend - no countertrend
            allow_countertrend = False
        elif phase == "range":
            # Range allows countertrend
            allow_countertrend = True
        
        return {
            "allow_long": allow_long,
            "allow_short": allow_short,
            "allow_countertrend": allow_countertrend
        }
