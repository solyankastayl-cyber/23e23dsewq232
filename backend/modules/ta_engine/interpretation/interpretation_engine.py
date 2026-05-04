"""
Interpretation Engine — TA Language Layer
==========================================

Transforms raw TA data into human-readable analysis.

Key principle:
- NO "no pattern" / "no trade" / "invalid" language
- ALWAYS provide market context, structure, phase
- Research language, NOT trading terminal language

TF Roles:
- HTF (1M, 6M, 1Y): Macro context, trend, regime
- MTF (1D, 7D): Primary TA, patterns
- LTF (4H): Local detail, confirmation
"""

from typing import Dict, Any, List, Optional


class InterpretationEngine:
    """
    Transforms TA data into readable market interpretation.
    
    Rules:
    - NEVER say "no pattern" / "no trade" / "invalid"
    - ALWAYS describe market state, phase, context
    - Use Research language, not trading terminal
    """

    def interpret(self, tf_role: str, data: Dict[str, Any]) -> str:
        """
        Generate interpretation for a timeframe.
        
        Args:
            tf_role: 'htf', 'mtf', or 'ltf'
            data: TF analysis data
            
        Returns:
            Human-readable interpretation string
        """
        if tf_role == "htf":
            return self._interpret_htf(data)
        elif tf_role == "mtf":
            return self._interpret_mtf(data)
        else:
            return self._interpret_ltf(data)

    def _interpret_htf(self, data: Dict[str, Any]) -> str:
        """
        HTF interpretation (1M, 6M, 1Y).
        Focus: Macro context, trend, regime, major levels.
        NEVER say "no analysis" — HTF is CONTEXT.
        """
        trend = data.get("trend", "neutral")
        regime = data.get("regime", "unknown")
        levels = data.get("levels", [])
        pattern = data.get("pattern")

        parts = []

        # TREND — always describe
        if trend == "uptrend":
            parts.append("Market remains in a macro uptrend with higher lows.")
        elif trend == "downtrend":
            parts.append("Market remains in a macro downtrend with lower highs.")
        elif trend == "range":
            parts.append("Market is consolidating within a broad range.")
        else:
            parts.append("Market structure is neutral, no clear directional control.")

        # REGIME — add context
        if regime == "compression":
            parts.append("Compression phase — volatility contracting.")
        elif regime == "expansion":
            parts.append("Expansion phase — volatility increasing.")
        elif regime == "trending":
            parts.append("Trending environment.")
        elif regime == "ranging":
            parts.append("Ranging environment.")

        # LEVELS — key structural level
        if levels:
            major_level = levels[0]
            price = major_level.get("price", 0)
            level_type = major_level.get("type", "level")
            if price:
                parts.append(f"Key {level_type} around {self._fmt(price)} defines the current structure.")

        # PATTERN — only if present and confident
        if pattern and pattern.get("type"):
            ptype = pattern.get("type", "").replace("_", " ")
            parts.append(f"A {ptype} is forming on higher timeframe.")

        return " ".join(parts)

    def _interpret_mtf(self, data: Dict[str, Any]) -> str:
        """
        MTF interpretation (1D, 7D).
        Focus: Primary TA layer, patterns, structure.
        """
        pattern = data.get("pattern")
        structure = data.get("structure", {})
        levels = data.get("levels", [])
        trend = data.get("trend", "neutral")

        parts = []

        if pattern and pattern.get("type"):
            ptype = pattern.get("type", "").replace("_", " ").title()
            direction = pattern.get("direction", "neutral")
            confidence = pattern.get("confidence", pattern.get("final_score", 0))

            if direction == "bullish":
                parts.append(f"Bullish {ptype} structure is forming.")
            elif direction == "bearish":
                parts.append(f"Bearish {ptype} structure is forming.")
            else:
                parts.append(f"{ptype} structure is developing.")
            
            if confidence >= 0.7:
                parts.append("High confidence setup.")
            elif confidence >= 0.5:
                parts.append("Moderate confidence.")
        else:
            # No pattern — describe structure instead
            bias = structure.get("bias", trend)
            if bias == "bullish":
                parts.append("Bullish structure developing — higher lows forming.")
            elif bias == "bearish":
                parts.append("Bearish structure developing — lower highs forming.")
            else:
                parts.append("No dominant pattern — structure is still developing.")

        # LEVEL CONTEXT
        if levels:
            nearest = levels[0]
            price = nearest.get("price", 0)
            level_type = nearest.get("type", "level")
            if price:
                parts.append(f"Price is interacting with {level_type} near {self._fmt(price)}.")

        return " ".join(parts)

    def _interpret_ltf(self, data: Dict[str, Any]) -> str:
        """
        LTF interpretation (4H).
        Focus: Local detail, micro patterns, confirmation.
        """
        pattern = data.get("pattern")
        trend = data.get("trend", "neutral")
        structure = data.get("structure", {})

        if pattern and pattern.get("type"):
            ptype = pattern.get("type", "").replace("_", " ").title()
            direction = pattern.get("direction", "neutral")
            return f"Locally, {ptype} suggests short-term {direction} pressure."

        # No pattern — describe local structure
        bias = structure.get("bias", trend)
        if bias == "bullish":
            return "Local bullish structure — momentum turning up."
        elif bias == "bearish":
            return "Local bearish structure — momentum turning down."
        
        return "No clear short-term formation — market is in transition."

    def build_summary(
        self, 
        htf_interp: Optional[str], 
        mtf_interp: Optional[str], 
        ltf_interp: Optional[str]
    ) -> str:
        """
        Build global summary from all timeframe interpretations.
        
        Format:
        Macro: [htf]
        Mid-term: [mtf]
        Short-term: [ltf]
        """
        parts = []

        if htf_interp:
            parts.append(f"Macro: {htf_interp}")
        if mtf_interp:
            parts.append(f"Mid-term: {mtf_interp}")
        if ltf_interp:
            parts.append(f"Short-term: {ltf_interp}")

        return " ".join(parts)

    def build_one_line_summary(
        self,
        htf_data: Optional[Dict],
        mtf_data: Optional[Dict],
        ltf_data: Optional[Dict],
    ) -> str:
        """
        Build compact one-line summary for UI header.
        
        Format: Macro: Range · Mid-term: Falling Wedge · Short-term: Triangle
        """
        parts = []
        
        # HTF
        if htf_data:
            trend = htf_data.get("trend", "neutral")
            trend_map = {
                "uptrend": "Uptrend",
                "downtrend": "Downtrend",
                "range": "Range",
                "neutral": "Neutral",
            }
            parts.append(f"Macro: {trend_map.get(trend, 'Neutral')}")
        
        # MTF
        if mtf_data:
            pattern = mtf_data.get("pattern")
            if pattern and pattern.get("type"):
                ptype = pattern.get("type", "").replace("_", " ").title()
                parts.append(f"Mid-term: {ptype}")
            else:
                trend = mtf_data.get("trend", "neutral")
                if trend in ["bullish", "uptrend"]:
                    parts.append("Mid-term: Bullish Structure")
                elif trend in ["bearish", "downtrend"]:
                    parts.append("Mid-term: Bearish Structure")
                else:
                    parts.append("Mid-term: Developing")
        
        # LTF
        if ltf_data:
            pattern = ltf_data.get("pattern")
            if pattern and pattern.get("type"):
                ptype = pattern.get("type", "").replace("_", " ").title()
                parts.append(f"Short-term: {ptype}")
            else:
                trend = ltf_data.get("trend", "neutral")
                if trend in ["bullish", "uptrend"]:
                    parts.append("Short-term: Local Bullish")
                elif trend in ["bearish", "downtrend"]:
                    parts.append("Short-term: Local Bearish")
                else:
                    parts.append("Short-term: Consolidation")
        
        return " · ".join(parts)

    def enrich_tf_data(self, tf_data: Dict[str, Any], tf_role: str) -> Dict[str, Any]:
        """
        Enrich TF data with interpretation.
        Adds 'interpretation' field to data.
        """
        interpretation = self.interpret(tf_role, tf_data)
        tf_data["interpretation"] = interpretation
        
        # Add state/phase even if no pattern
        if not tf_data.get("state"):
            trend = tf_data.get("trend", "neutral")
            if trend == "uptrend":
                tf_data["state"] = "bullish"
            elif trend == "downtrend":
                tf_data["state"] = "bearish"
            else:
                tf_data["state"] = "range"
        
        if not tf_data.get("phase"):
            regime = tf_data.get("regime", "unknown")
            if regime == "compression":
                tf_data["phase"] = "compression"
            elif regime == "expansion":
                tf_data["phase"] = "expansion"
            elif regime in ["trending", "uptrend", "downtrend"]:
                tf_data["phase"] = "trending"
            else:
                tf_data["phase"] = "consolidation"
        
        # Add explanation even if no pattern
        if not tf_data.get("explanation"):
            tf_data["explanation"] = interpretation
        
        return tf_data

    def _fmt(self, v: Optional[float]) -> str:
        """Format price for display."""
        if v is None:
            return "N/A"
        if v >= 1000:
            return f"{v:,.0f}"
        return f"{v:.2f}"


# Singleton
_interpretation_engine = None

def get_interpretation_engine() -> InterpretationEngine:
    """Get interpretation engine singleton."""
    global _interpretation_engine
    if _interpretation_engine is None:
        _interpretation_engine = InterpretationEngine()
    return _interpretation_engine
