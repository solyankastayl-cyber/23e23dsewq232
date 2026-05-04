"""
Explanation Engine V1 — Human-Readable Analysis Explanations
============================================================

Converts:
  decision + mtf_context + structure + scenarios
  ↓
  Human-readable explanation (deterministic, not AI-generated)

This is NOT GPT generation. This is a deterministic explanation engine:
  - Stable
  - Fast
  - Predictable
  - No hallucinations

Output Contract:
{
    "summary": str,
    "technical_reasoning": str,
    "scenario_explanation": str,
    "risk_factors": str,
    "invalidation_explanation": str,
    "short_text": str,
    "confidence": float
}
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional


class ExplanationEngineV1:
    """
    Deterministic explanation generator.
    
    Takes analysis results and produces human-readable explanations
    that can be read, shared, and used as content.
    """

    def generate(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate explanation from analysis data.
        
        Args:
            data: {
                "decision": {...},
                "mtf_context": {...},
                "structure_context": {...},
                "scenarios": [primary, alternative]
            }
        
        Returns:
            {
                "summary": str,
                "technical_reasoning": str,
                "scenario_explanation": str,
                "risk_factors": str,
                "invalidation_explanation": str,
                "short_text": str,
                "confidence": float
            }
        """
        decision = data.get("decision", {})
        mtf = data.get("mtf_context", {})
        structure = data.get("structure_context", {})
        scenarios = data.get("scenarios", [])
        
        # Extract primary scenario
        primary = scenarios[0] if scenarios else {}
        alternative = scenarios[1] if len(scenarios) > 1 else {}
        
        # Build each explanation component
        summary = self._build_summary(decision, mtf, structure)
        reasoning = self._build_reasoning(decision, structure, mtf)
        scenario_exp = self._build_scenario_explanation(primary, alternative, decision)
        risks = self._build_risks(decision, mtf, structure)
        invalidation = self._build_invalidation(primary)
        short = self._build_short_text(decision, primary)
        
        return {
            "summary": summary,
            "technical_reasoning": reasoning,
            "scenario_explanation": scenario_exp,
            "risk_factors": risks,
            "invalidation_explanation": invalidation,
            "short_text": short,
            "confidence": decision.get("confidence", 0.5),
        }

    # ---------------------------------------------------------
    # SUMMARY — One-line market overview
    # ---------------------------------------------------------
    def _build_summary(
        self,
        decision: Dict[str, Any],
        mtf: Dict[str, Any],
        structure: Dict[str, Any],
    ) -> str:
        """Build one-line market summary."""
        bias = decision.get("bias", "neutral")
        confidence = decision.get("confidence", 0.5)
        strength = decision.get("strength", "medium")
        dominant_tf = decision.get("dominant_tf", mtf.get("dominant_tf", "1D"))
        alignment = decision.get("alignment", mtf.get("alignment", "mixed"))
        context = decision.get("context", "trend_continuation")
        
        # Confidence qualifier
        if confidence >= 0.75:
            conf_text = "high-conviction"
        elif confidence >= 0.55:
            conf_text = "moderate"
        else:
            conf_text = "low-conviction"
        
        # Build summary based on bias
        if bias == "bullish":
            if context == "pullback":
                return f"Market shows {conf_text} bullish bias with pullback opportunity on {dominant_tf} structure. Multi-timeframe alignment: {alignment}."
            elif context == "trend_continuation":
                return f"Market shows {conf_text} bullish trend continuation driven by {dominant_tf} timeframe. Structural strength: {strength}."
            else:
                return f"Market displays bullish conditions with {conf_text} conviction. Dominant structure: {dominant_tf}."
        
        elif bias == "bearish":
            if context == "relief_bounce":
                return f"Market shows {conf_text} bearish bias with relief bounce inside {dominant_tf} downtrend. Multi-timeframe alignment: {alignment}."
            elif context == "trend_continuation":
                return f"Market shows {conf_text} bearish trend continuation driven by {dominant_tf} structure. Structural weakness confirmed."
            else:
                return f"Market displays bearish pressure with {conf_text} conviction. Dominant structure: {dominant_tf}."
        
        else:  # neutral
            regime = structure.get("regime", "range")
            return f"Market is currently neutral inside {regime} conditions. No strong directional conviction until breakout confirmation."

    # ---------------------------------------------------------
    # TECHNICAL REASONING — Why this bias
    # ---------------------------------------------------------
    def _build_reasoning(
        self,
        decision: Dict[str, Any],
        structure: Dict[str, Any],
        mtf: Dict[str, Any],
    ) -> str:
        """Build technical reasoning explanation."""
        parts = []
        
        # Structure state
        regime = structure.get("regime", "range")
        market_phase = structure.get("market_phase", "range")
        last_event = structure.get("last_event", "none")
        
        # State description
        if regime == "expansion":
            parts.append("Current market structure indicates expansion conditions with strong directional momentum.")
        elif regime == "compression":
            parts.append("Market is in compression phase, indicating potential breakout ahead.")
        elif regime == "range":
            parts.append(f"Current market structure indicates range-bound conditions inside {market_phase} phase.")
        else:
            parts.append(f"Current market structure indicates {regime} conditions.")
        
        # Last event (structural signals)
        if last_event != "none":
            event_map = {
                "choch_up": "Character Change (CHOCH) to the upside detected — early reversal signal",
                "choch_down": "Character Change (CHOCH) to the downside detected — potential trend shift",
                "bos_up": "Break of Structure (BOS) upward confirmed — bullish continuation",
                "bos_down": "Break of Structure (BOS) downward confirmed — bearish continuation",
                "hh": "New Higher High formed — bullish structure intact",
                "hl": "Higher Low confirmed — bullish trend continuation signal",
                "lh": "Lower High formed — bearish structure developing",
                "ll": "New Lower Low confirmed — bearish continuation",
            }
            event_text = event_map.get(last_event, f"Key structural event: {last_event}")
            parts.append(event_text + ".")
        
        # MTF alignment
        alignment = mtf.get("alignment", decision.get("alignment", "mixed"))
        global_bias = mtf.get("global_bias", decision.get("bias", "neutral"))
        
        if alignment in ["full_bullish", "aligned"] and global_bias == "bullish":
            parts.append("Multi-timeframe alignment strongly supports bullish continuation.")
        elif alignment in ["full_bearish", "aligned"] and global_bias == "bearish":
            parts.append("Multi-timeframe alignment confirms persistent downside pressure.")
        elif alignment == "mixed":
            parts.append("Timeframes show mixed signals, reducing overall conviction. Waiting for confirmation.")
        
        # Confidence context
        confidence = decision.get("confidence", 0.5)
        if confidence >= 0.75:
            parts.append("High confidence signal with strong structural backing.")
        elif confidence < 0.55:
            parts.append("Lower confidence due to conflicting signals — caution advised.")
        
        return " ".join(parts)

    # ---------------------------------------------------------
    # SCENARIO EXPLANATION — What to expect
    # ---------------------------------------------------------
    def _build_scenario_explanation(
        self,
        primary: Dict[str, Any],
        alternative: Dict[str, Any],
        decision: Dict[str, Any],
    ) -> str:
        """Build scenario explanation."""
        parts = []
        
        if primary:
            direction = primary.get("direction", "neutral")
            probability = primary.get("probability", 0.5)
            prob_pct = int(probability * 100)
            trigger = primary.get("trigger", "N/A")
            title = primary.get("title", f"{direction} scenario")
            
            parts.append(f"**Primary scenario:** {title} ({prob_pct}% probability).")
            parts.append(f"Trigger condition: {trigger}.")
            
            if primary.get("summary"):
                parts.append(primary["summary"])
        
        if alternative:
            alt_direction = alternative.get("direction", "neutral")
            alt_prob = alternative.get("probability", 0.3)
            alt_pct = int(alt_prob * 100)
            alt_trigger = alternative.get("trigger", "N/A")
            
            parts.append(f"**Alternative scenario:** {alternative.get('title', alt_direction)} ({alt_pct}% probability).")
            parts.append(f"Would require: {alt_trigger}.")
        
        if not parts:
            parts.append("Scenario data unavailable — waiting for structural confirmation.")
        
        return " ".join(parts)

    # ---------------------------------------------------------
    # RISK FACTORS — What could go wrong
    # ---------------------------------------------------------
    def _build_risks(
        self,
        decision: Dict[str, Any],
        mtf: Dict[str, Any],
        structure: Dict[str, Any],
    ) -> str:
        """Build risk factors explanation."""
        risks = []
        
        # MTF alignment risk
        alignment = mtf.get("alignment", decision.get("alignment", "mixed"))
        if alignment == "mixed":
            risks.append("Mixed multi-timeframe alignment reduces directional conviction")
        
        # Range/compression risk
        regime = structure.get("regime", "range")
        if regime == "range":
            risks.append("Range conditions may invalidate trend continuation setups")
        elif regime == "compression":
            risks.append("Compression phase — breakout direction uncertain")
        
        # Confidence risk
        confidence = decision.get("confidence", 0.5)
        if confidence < 0.55:
            risks.append("Low confidence signal — higher probability of false move")
        
        # Tradeability risk
        tradeability = decision.get("tradeability", "conditional")
        if tradeability == "low":
            risks.append("Low tradeability — consider waiting for better setup")
        elif tradeability == "conditional":
            risks.append("Conditional tradeability — requires confirmation")
        
        # Context-specific risks
        context = decision.get("context", "")
        if context == "relief_bounce":
            risks.append("Counter-trend bounce — may fail quickly")
        elif context == "pullback":
            risks.append("Pullback in progress — depth uncertain")
        
        if not risks:
            return "No major conflicting signals detected. Setup appears clean."
        
        return " | ".join(risks)

    # ---------------------------------------------------------
    # INVALIDATION — What breaks the thesis
    # ---------------------------------------------------------
    def _build_invalidation(self, primary: Dict[str, Any]) -> str:
        """Build invalidation explanation."""
        if not primary:
            return "Invalidation levels not available."
        
        invalidation = primary.get("invalidation", "")
        direction = primary.get("direction", "neutral")
        
        if invalidation:
            return f"Scenario becomes invalid if: {invalidation}. Monitor this level closely for position management."
        
        # Fallback based on direction
        if direction == "bearish":
            return "Scenario invalidates on confirmed bullish reclaim of resistance structure."
        elif direction == "bullish":
            return "Scenario invalidates on loss of key support structure."
        
        return "Watch for structural break in opposite direction for invalidation."

    # ---------------------------------------------------------
    # SHORT TEXT — For sharing/content
    # ---------------------------------------------------------
    def _build_short_text(
        self,
        decision: Dict[str, Any],
        primary: Dict[str, Any],
    ) -> str:
        """Build short shareable text."""
        bias = decision.get("bias", "neutral").upper()
        confidence = decision.get("confidence", 0.5)
        conf_pct = int(confidence * 100)
        
        if not primary:
            return f"{bias} bias ({conf_pct}% confidence) — waiting for setup confirmation."
        
        probability = primary.get("probability", 0.5)
        prob_pct = int(probability * 100)
        trigger = primary.get("trigger", "key level")
        
        return f"{bias} setup ({prob_pct}%) — watching trigger at {trigger}."


# ---------------------------------------------------------
# Factory / Singleton
# ---------------------------------------------------------
_explanation_engine_v1_instance: Optional[ExplanationEngineV1] = None


def get_explanation_engine_v1() -> ExplanationEngineV1:
    """Get singleton instance of ExplanationEngineV1."""
    global _explanation_engine_v1_instance
    if _explanation_engine_v1_instance is None:
        _explanation_engine_v1_instance = ExplanationEngineV1()
    return _explanation_engine_v1_instance


# Direct import singleton
explanation_engine_v1 = ExplanationEngineV1()
