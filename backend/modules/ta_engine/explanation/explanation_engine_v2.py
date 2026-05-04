"""
Explanation Engine V2 — Ultra-Compact Trader Explanation
========================================================

Only 3 lines, no water:
  - summary (1 line): what's happening
  - action (1 line): what to do
  - risk (1 line): when it's wrong

Source of truth:
  - decision
  - scenarios (primary)
  - trade_setup (primary)

Output:
{
    "summary": "Bearish. Price is bouncing into resistance.",
    "action": "Look for rejection from 89200.",
    "risk": "Invalid if price holds beyond 90300.",
    "confidence": "medium"
}
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional


class ExplanationEngineV2:
    """
    Ultra-compact explanation generator.
    
    Rules:
      - Only 3 lines
      - No water ("higher timeframe context suggests...")
      - Simple words (trader, not analyst)
      - Use real levels from trade_setup
    """

    def build(
        self,
        decision: Dict[str, Any],
        scenarios: Optional[List[Dict[str, Any]]] = None,
        trade_setup: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Build ultra-compact explanation.
        
        Args:
            decision: Decision Engine V2 output
            scenarios: Scenario Engine V3 output (list)
            trade_setup: Trade Setup Generator output
        
        Returns:
            {
                "summary": str,
                "action": str,
                "risk": str,
                "confidence": str
            }
        """
        primary_scenario = self._get_primary(scenarios or [])
        primary_setup = (trade_setup or {}).get("primary") if trade_setup else None

        # Extract decision data
        bias = decision.get("bias", "neutral")
        context = decision.get("context", "trend_continuation")
        alignment = decision.get("alignment", "mixed")
        strength = decision.get("strength", "weak")
        confidence = decision.get("confidence", 0.5)
        dominant_tf = decision.get("dominant_tf", "1D")

        # Extract levels
        entry = self._mid_entry(primary_setup)
        stop = self._safe_float(primary_setup, "stop_loss")
        target = self._safe_float(primary_setup, "target_1")
        
        # Extract from scenario trigger/invalidation
        trigger_level = self._extract_level_from_trigger(primary_scenario)
        invalidation_level = self._extract_level_from_invalidation(primary_scenario)

        # Build 3 lines
        summary = self._build_summary(bias, context, alignment, dominant_tf)
        action = self._build_action(
            bias=bias,
            context=context,
            entry=entry,
            trigger_level=trigger_level,
            target=target,
        )
        risk = self._build_risk(
            bias=bias,
            stop=stop,
            invalidation_level=invalidation_level,
        )

        return {
            "summary": summary,
            "action": action,
            "risk": risk,
            "confidence": self._confidence_label(confidence, strength),
        }

    # ---------------------------------------------------------
    # SUMMARY — What's happening (1 line)
    # ---------------------------------------------------------
    def _build_summary(
        self,
        bias: str,
        context: str,
        alignment: str,
        dominant_tf: str,
    ) -> str:
        """Build 1-line market summary."""
        
        if bias == "bearish":
            if context == "relief_bounce":
                base = "Bearish. Price is bouncing into resistance."
            elif context == "trend_continuation":
                base = "Bearish. Downtrend continues."
            elif context == "pullback":
                base = "Bearish pullback inside downtrend."
            else:
                base = "Bearish. Downtrend remains in control."
        
        elif bias == "bullish":
            if context == "pullback":
                base = "Bullish. Price is pulling back into support."
            elif context == "trend_continuation":
                base = "Bullish. Uptrend continues."
            elif context == "relief_bounce":
                base = "Bullish bounce inside range."
            else:
                base = "Bullish. Uptrend remains in control."
        
        else:  # neutral
            base = "Neutral. Market is range-bound."

        # Add alignment warning if mixed
        if alignment == "mixed":
            base += " Timeframes mixed."

        return base

    # ---------------------------------------------------------
    # ACTION — What to do (1 line)
    # ---------------------------------------------------------
    def _build_action(
        self,
        bias: str,
        context: str,
        entry: Optional[float],
        trigger_level: Optional[float],
        target: Optional[float],
    ) -> str:
        """Build 1-line action."""
        
        if bias == "bearish":
            if trigger_level:
                return f"Look for rejection from {self._fmt(trigger_level)}."
            if entry:
                return f"Short entries near {self._fmt(entry)}."
            return "Wait for downside confirmation."

        if bias == "bullish":
            if trigger_level:
                return f"Look for bounce from {self._fmt(trigger_level)}."
            if entry:
                return f"Long entries near {self._fmt(entry)}."
            return "Wait for upside confirmation."

        # Neutral
        return "Wait for breakout from the range."

    # ---------------------------------------------------------
    # RISK — When it's wrong (1 line)
    # ---------------------------------------------------------
    def _build_risk(
        self,
        bias: str,
        stop: Optional[float],
        invalidation_level: Optional[float],
    ) -> str:
        """Build 1-line risk/invalidation."""
        
        level = invalidation_level or stop
        
        if level:
            if bias == "bearish":
                return f"Invalid if price holds above {self._fmt(level)}."
            elif bias == "bullish":
                return f"Invalid if price breaks below {self._fmt(level)}."
            else:
                return f"Invalid beyond {self._fmt(level)}."
        
        return "Invalidation unclear — wait for structure."

    # ---------------------------------------------------------
    # HELPERS
    # ---------------------------------------------------------
    def _get_primary(self, scenarios: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Get primary scenario from list."""
        for s in scenarios:
            if s.get("type") == "primary":
                return s
        return scenarios[0] if scenarios else None

    def _mid_entry(self, setup: Optional[Dict[str, Any]]) -> Optional[float]:
        """Get midpoint of entry zone."""
        if not setup:
            return None
        zone = setup.get("entry_zone")
        if isinstance(zone, list) and len(zone) == 2:
            return (float(zone[0]) + float(zone[1])) / 2
        return None

    def _safe_float(self, obj: Optional[Dict[str, Any]], key: str) -> Optional[float]:
        """Safely extract float from dict."""
        try:
            if obj and key in obj and obj[key] is not None:
                return float(obj[key])
        except Exception:
            pass
        return None

    def _extract_level_from_trigger(self, scenario: Optional[Dict[str, Any]]) -> Optional[float]:
        """Extract numeric level from trigger text."""
        if not scenario:
            return None
        text = (scenario.get("trigger") or "")
        return self._extract_number(text)

    def _extract_level_from_invalidation(self, scenario: Optional[Dict[str, Any]]) -> Optional[float]:
        """Extract numeric level from invalidation text."""
        if not scenario:
            return None
        text = (scenario.get("invalidation") or "")
        return self._extract_number(text)

    def _extract_number(self, text: str) -> Optional[float]:
        """Extract first number from text."""
        # Remove commas from numbers like "89,200"
        text = text.replace(",", "")
        buf = ""
        found = False
        for ch in text:
            if ch.isdigit() or ch == ".":
                buf += ch
                found = True
            elif found and buf:
                break
        try:
            return float(buf) if buf else None
        except Exception:
            return None

    def _fmt(self, v: Optional[float]) -> str:
        """Format price for display."""
        if v is None:
            return "N/A"
        if v >= 1000:
            return f"{v:,.0f}"
        return f"{v:.2f}"

    def _confidence_label(self, conf: float, strength: str) -> str:
        """Convert confidence to label."""
        if conf >= 0.75 or strength == "strong":
            return "high"
        if conf >= 0.55 or strength == "medium":
            return "medium"
        return "low"


# ---------------------------------------------------------
# Factory / Singleton
# ---------------------------------------------------------
_explanation_engine_v2_instance: Optional[ExplanationEngineV2] = None


def get_explanation_engine_v2() -> ExplanationEngineV2:
    """Get singleton instance of ExplanationEngineV2."""
    global _explanation_engine_v2_instance
    if _explanation_engine_v2_instance is None:
        _explanation_engine_v2_instance = ExplanationEngineV2()
    return _explanation_engine_v2_instance


# Direct import singleton
explanation_engine_v2 = ExplanationEngineV2()
