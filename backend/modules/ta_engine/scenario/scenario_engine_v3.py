"""
Scenario Engine V3 — Decision-Driven Scenarios
==============================================

Scenarios are now built from:
  decision + mtf_context + structure_context + base_layer + primary_pattern

NOT from:
  - Bare levels alone
  - Single pattern alone

Key rules:
  - If decision.bias = neutral → scenario is range/compression/wait
  - If alignment = mixed → summary must reflect this
  - If primary_pattern = None → scenarios still build (from decision/structure)
  - Pattern is evidence, not driver

Output:
{
  "scenarios": [
    {
      "type": "primary",
      "direction": "bearish",
      "title": "Bearish continuation after relief bounce",
      "probability": 0.64,
      "summary": "Short-term bounce inside bearish higher timeframe structure...",
      "trigger": "rejection below 89200",
      "invalidation": "acceptance above 90300",
      "action": "wait rejection from resistance / follow downside continuation"
    },
    {
      "type": "alternative",
      ...
    }
  ]
}
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass
class ScenarioV3:
    """Single scenario object."""
    type: str                   # primary | alternative
    direction: str              # bullish | bearish | neutral
    title: str
    probability: float          # 0..1
    summary: str
    trigger: str
    invalidation: str
    action: str


class ScenarioEngineV3:
    """
    Decision-driven scenario generator.
    
    Priority:
      1. Decision (bias, confidence, context, alignment)
      2. MTF Context (global_bias, local_context, dominant_tf)
      3. Structure Context (regime, market_phase, last_event)
      4. Base Layer (supports, resistances)
      5. Primary Pattern (optional evidence)
    """

    def build(
        self,
        decision: Dict[str, Any],
        mtf_context: Dict[str, Any],
        structure_context: Dict[str, Any],
        base_layer: Dict[str, Any],
        current_price: float,
        primary_pattern: Optional[Dict[str, Any]] = None,
        alternative_patterns: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """
        Build scenarios from decision-first logic.
        
        Returns:
            {"scenarios": [primary_scenario, alternative_scenario]}
        """
        alternative_patterns = alternative_patterns or []
        
        # Extract decision data
        bias = decision.get("bias", "neutral")
        confidence = float(decision.get("confidence", 0.5) or 0.5)
        context = decision.get("context", "trend_continuation")
        alignment = decision.get("alignment", "mixed")
        strength = decision.get("strength", "medium")
        dominant_tf = decision.get("dominant_tf", "1D")
        tradeability = decision.get("tradeability", "conditional")
        decision_summary = decision.get("summary", "")
        
        # Extract MTF context
        global_bias = mtf_context.get("global_bias", "neutral")
        local_context = mtf_context.get("local_context", "trend_continuation")
        mtf_alignment = mtf_context.get("alignment", "mixed")
        
        # Extract structure context
        regime = structure_context.get("regime", "range")
        market_phase = structure_context.get("market_phase", "range")
        last_event = structure_context.get("last_event", "none")
        
        # Extract levels
        supports = self._extract_prices(base_layer.get("supports", []))
        resistances = self._extract_prices(base_layer.get("resistances", []))
        nearest_support = self._nearest_below(current_price, supports)
        nearest_resistance = self._nearest_above(current_price, resistances)
        
        # Pattern info (evidence only)
        pattern_name = self._pattern_name(primary_pattern)
        pattern_direction = primary_pattern.get("direction", "neutral") if primary_pattern else "neutral"
        
        # Build primary scenario
        primary = self._build_primary(
            bias=bias,
            confidence=confidence,
            context=context,
            alignment=alignment,
            strength=strength,
            dominant_tf=dominant_tf,
            tradeability=tradeability,
            decision_summary=decision_summary,
            global_bias=global_bias,
            local_context=local_context,
            regime=regime,
            market_phase=market_phase,
            last_event=last_event,
            current_price=current_price,
            support=nearest_support,
            resistance=nearest_resistance,
            pattern_name=pattern_name,
        )
        
        # Build alternative scenario
        alternative = self._build_alternative(
            bias=bias,
            confidence=confidence,
            context=context,
            alignment=alignment,
            local_context=local_context,
            regime=regime,
            market_phase=market_phase,
            current_price=current_price,
            support=nearest_support,
            resistance=nearest_resistance,
            alternative_patterns=alternative_patterns,
        )
        
        return {
            "scenarios": [
                self._serialize(primary),
                self._serialize(alternative),
            ]
        }

    # ---------------------------------------------------------
    # PRIMARY SCENARIO
    # ---------------------------------------------------------
    def _build_primary(
        self,
        bias: str,
        confidence: float,
        context: str,
        alignment: str,
        strength: str,
        dominant_tf: str,
        tradeability: str,
        decision_summary: str,
        global_bias: str,
        local_context: str,
        regime: str,
        market_phase: str,
        last_event: str,
        current_price: float,
        support: Optional[float],
        resistance: Optional[float],
        pattern_name: Optional[str],
    ) -> ScenarioV3:
        """Build primary scenario based on decision bias."""
        
        # === NEUTRAL BIAS ===
        if bias == "neutral":
            return self._build_neutral_primary(
                context=context,
                regime=regime,
                market_phase=market_phase,
                confidence=confidence,
                support=support,
                resistance=resistance,
                pattern_name=pattern_name,
            )
        
        # === BEARISH BIAS ===
        if bias == "bearish":
            return self._build_bearish_primary(
                context=context,
                local_context=local_context,
                alignment=alignment,
                strength=strength,
                dominant_tf=dominant_tf,
                regime=regime,
                market_phase=market_phase,
                last_event=last_event,
                confidence=confidence,
                decision_summary=decision_summary,
                current_price=current_price,
                support=support,
                resistance=resistance,
                pattern_name=pattern_name,
            )
        
        # === BULLISH BIAS ===
        return self._build_bullish_primary(
            context=context,
            local_context=local_context,
            alignment=alignment,
            strength=strength,
            dominant_tf=dominant_tf,
            regime=regime,
            market_phase=market_phase,
            last_event=last_event,
            confidence=confidence,
            decision_summary=decision_summary,
            current_price=current_price,
            support=support,
            resistance=resistance,
            pattern_name=pattern_name,
        )

    def _build_neutral_primary(
        self,
        context: str,
        regime: str,
        market_phase: str,
        confidence: float,
        support: Optional[float],
        resistance: Optional[float],
        pattern_name: Optional[str],
    ) -> ScenarioV3:
        """Neutral decision → range/compression/wait scenario."""
        
        # Title based on context
        if regime == "compression":
            title = "Compression persists — wait for expansion"
        elif context == "relief_bounce":
            title = "Counter-trend bounce without confirmation"
        elif context == "pullback":
            title = "Pullback without continuation signal"
        else:
            title = "Range continuation — no directional edge"
        
        # Summary
        summary_parts = [
            f"Market shows no clear directional edge in current {market_phase or regime} conditions."
        ]
        if support and resistance:
            summary_parts.append(f"Price oscillates between {self._fmt(support)} support and {self._fmt(resistance)} resistance.")
        if pattern_name:
            summary_parts.append(f"Visible structure ({pattern_name}) does not confirm directional bias.")
        summary_parts.append("Wait for confirmed breakout or structural change before committing directionally.")
        
        summary = " ".join(summary_parts)
        
        # Trigger/Invalidation
        if support and resistance:
            trigger = f"decisive break above {self._fmt(resistance)} or below {self._fmt(support)}"
            invalidation = "continued range-bound behavior"
        else:
            trigger = "structural break with follow-through"
            invalidation = "return to range"
        
        # Action
        if support and resistance:
            action = f"trade range {self._fmt(support)} ↔ {self._fmt(resistance)} or wait for breakout"
        else:
            action = "wait for directional confirmation"
        
        return ScenarioV3(
            type="primary",
            direction="neutral",
            title=title,
            probability=round(max(0.45, min(0.55, confidence)), 2),
            summary=summary,
            trigger=trigger,
            invalidation=invalidation,
            action=action,
        )

    def _build_bearish_primary(
        self,
        context: str,
        local_context: str,
        alignment: str,
        strength: str,
        dominant_tf: str,
        regime: str,
        market_phase: str,
        last_event: str,
        confidence: float,
        decision_summary: str,
        current_price: float,
        support: Optional[float],
        resistance: Optional[float],
        pattern_name: Optional[str],
    ) -> ScenarioV3:
        """Bearish decision → bearish scenario."""
        
        # Title — context-aware
        if local_context == "relief_bounce":
            title = "Bearish continuation after relief bounce"
        elif local_context == "trend_continuation":
            title = f"Bearish trend continuation ({dominant_tf} led)"
        elif regime == "expansion":
            title = "Downside expansion continues"
        elif pattern_name:
            title = f"Bearish continuation from {pattern_name}"
        else:
            title = "Bearish continuation"
        
        # Summary — decision-driven
        summary_parts = []
        
        # Core message from decision
        if decision_summary:
            summary_parts.append(decision_summary)
        else:
            if local_context == "relief_bounce":
                summary_parts.append(f"Short-term bounce inside bearish {dominant_tf} higher-timeframe structure.")
            else:
                summary_parts.append(f"Bearish bias dominates across {dominant_tf} structure.")
        
        # Alignment context
        if alignment == "mixed":
            summary_parts.append("Higher and lower timeframes not fully aligned — downside should be confirmed, not assumed.")
        elif alignment in ["full_bearish", "aligned"]:
            summary_parts.append("Multi-timeframe alignment supports bearish continuation.")
        
        # Last event
        if "choch" in last_event:
            summary_parts.append(f"Structural shift detected ({last_event}) — watching for confirmation.")
        
        # Levels context
        if resistance:
            summary_parts.append(f"Resistance near {self._fmt(resistance)} acts as rejection zone.")
        if support:
            summary_parts.append(f"Downside target: support near {self._fmt(support)}.")
        
        # Pattern evidence
        if pattern_name:
            summary_parts.append(f"Pattern evidence: {pattern_name}.")
        
        summary = " ".join(summary_parts)
        
        # Trigger
        if resistance:
            trigger = f"rejection below {self._fmt(resistance)}"
        else:
            trigger = "renewed downside momentum"
        
        # Invalidation
        if resistance:
            invalidation = f"acceptance above {self._fmt(resistance)}"
        else:
            invalidation = "bullish structural reclaim"
        
        # Action
        if resistance and support:
            action = f"wait rejection from {self._fmt(resistance)} / target {self._fmt(support)}"
        elif resistance:
            action = f"wait rejection from {self._fmt(resistance)} / follow downside"
        else:
            action = "wait downside confirmation before short entries"
        
        return ScenarioV3(
            type="primary",
            direction="bearish",
            title=title,
            probability=round(max(0.52, confidence), 2),
            summary=summary,
            trigger=trigger,
            invalidation=invalidation,
            action=action,
        )

    def _build_bullish_primary(
        self,
        context: str,
        local_context: str,
        alignment: str,
        strength: str,
        dominant_tf: str,
        regime: str,
        market_phase: str,
        last_event: str,
        confidence: float,
        decision_summary: str,
        current_price: float,
        support: Optional[float],
        resistance: Optional[float],
        pattern_name: Optional[str],
    ) -> ScenarioV3:
        """Bullish decision → bullish scenario."""
        
        # Title — context-aware
        if local_context == "pullback":
            title = "Bullish continuation after pullback"
        elif local_context == "trend_continuation":
            title = f"Bullish trend continuation ({dominant_tf} led)"
        elif regime == "expansion":
            title = "Upside expansion continues"
        elif pattern_name:
            title = f"Bullish continuation from {pattern_name}"
        else:
            title = "Bullish continuation"
        
        # Summary — decision-driven
        summary_parts = []
        
        # Core message from decision
        if decision_summary:
            summary_parts.append(decision_summary)
        else:
            if local_context == "pullback":
                summary_parts.append(f"Pullback inside bullish {dominant_tf} higher-timeframe structure.")
            else:
                summary_parts.append(f"Bullish bias dominates across {dominant_tf} structure.")
        
        # Alignment context
        if alignment == "mixed":
            summary_parts.append("Timeframe alignment is mixed — continuation needs confirmation above resistance.")
        elif alignment in ["full_bullish", "aligned"]:
            summary_parts.append("Multi-timeframe alignment supports bullish continuation.")
        
        # Last event
        if "choch" in last_event:
            summary_parts.append(f"Structural shift detected ({last_event}) — watching for confirmation.")
        
        # Levels context
        if support:
            summary_parts.append(f"Support near {self._fmt(support)} acts as key hold level.")
        if resistance:
            summary_parts.append(f"Upside target: resistance near {self._fmt(resistance)}.")
        
        # Pattern evidence
        if pattern_name:
            summary_parts.append(f"Pattern evidence: {pattern_name}.")
        
        summary = " ".join(summary_parts)
        
        # Trigger
        if support:
            trigger = f"hold above {self._fmt(support)}"
        else:
            trigger = "continued bullish momentum"
        
        # Invalidation
        if support:
            invalidation = f"loss of {self._fmt(support)}"
        else:
            invalidation = "bearish structural break"
        
        # Action
        if support and resistance:
            action = f"buy hold above {self._fmt(support)} / target {self._fmt(resistance)}"
        elif support:
            action = f"buy hold above {self._fmt(support)} / follow upside"
        else:
            action = "wait upside confirmation before long entries"
        
        return ScenarioV3(
            type="primary",
            direction="bullish",
            title=title,
            probability=round(max(0.52, confidence), 2),
            summary=summary,
            trigger=trigger,
            invalidation=invalidation,
            action=action,
        )

    # ---------------------------------------------------------
    # ALTERNATIVE SCENARIO
    # ---------------------------------------------------------
    def _build_alternative(
        self,
        bias: str,
        confidence: float,
        context: str,
        alignment: str,
        local_context: str,
        regime: str,
        market_phase: str,
        current_price: float,
        support: Optional[float],
        resistance: Optional[float],
        alternative_patterns: List[Dict[str, Any]],
    ) -> ScenarioV3:
        """Build alternative scenario — opposite of primary."""
        
        alt_prob = round(min(0.48, max(0.20, 1.0 - confidence)), 2)
        alt_pattern = self._pattern_name(alternative_patterns[0] if alternative_patterns else None)
        
        # === BEARISH PRIMARY → BULLISH ALTERNATIVE ===
        if bias == "bearish":
            title = "Recovery extension"
            
            summary_parts = [
                "If price reclaims resistance and structure improves, rebound may extend higher."
            ]
            if local_context == "relief_bounce":
                summary_parts.append("Current bounce could strengthen into genuine reversal.")
            if alignment == "mixed":
                summary_parts.append("Mixed alignment leaves room for upside surprise.")
            if alt_pattern:
                summary_parts.append(f"Alternative structure: {alt_pattern}.")
            
            summary = " ".join(summary_parts)
            
            trigger = f"close above {self._fmt(resistance)}" if resistance else "bullish reclaim"
            invalidation = f"rejection below {self._fmt(resistance)}" if resistance else "renewed downside"
            action = "only above confirmed reclaim"
            
            return ScenarioV3(
                type="alternative",
                direction="bullish",
                title=title,
                probability=alt_prob,
                summary=summary,
                trigger=trigger,
                invalidation=invalidation,
                action=action,
            )
        
        # === BULLISH PRIMARY → BEARISH ALTERNATIVE ===
        if bias == "bullish":
            title = "Failed continuation / deeper pullback"
            
            summary_parts = [
                "Upside momentum may fail, rotating price back toward support."
            ]
            if local_context == "pullback":
                summary_parts.append("Current pullback could deepen into trend break.")
            if alignment == "mixed":
                summary_parts.append("Mixed alignment warns of potential reversal.")
            if alt_pattern:
                summary_parts.append(f"Alternative structure: {alt_pattern}.")
            
            summary = " ".join(summary_parts)
            
            trigger = f"loss of {self._fmt(support)}" if support else "bearish structural break"
            invalidation = f"hold above {self._fmt(support)}" if support else "bullish continuation"
            action = "protect longs on failed breakout"
            
            return ScenarioV3(
                type="alternative",
                direction="bearish",
                title=title,
                probability=alt_prob,
                summary=summary,
                trigger=trigger,
                invalidation=invalidation,
                action=action,
            )
        
        # === NEUTRAL PRIMARY → BREAKOUT ALTERNATIVE ===
        title = "Directional breakout"
        
        summary_parts = [
            "Neutral market may resolve into directional expansion."
        ]
        if regime == "compression":
            summary_parts.append("Compression typically precedes significant breakout.")
        if support and resistance:
            summary_parts.append(f"Watch for decisive break above {self._fmt(resistance)} or below {self._fmt(support)}.")
        if alt_pattern:
            summary_parts.append(f"Alternative structure: {alt_pattern}.")
        
        summary = " ".join(summary_parts)
        
        if support and resistance:
            trigger = f"break above {self._fmt(resistance)} or below {self._fmt(support)}"
        else:
            trigger = "structural expansion"
        
        invalidation = "continued range-bound behavior"
        action = "wait confirmed breakout with follow-through"
        
        return ScenarioV3(
            type="alternative",
            direction="breakout",
            title=title,
            probability=alt_prob,
            summary=summary,
            trigger=trigger,
            invalidation=invalidation,
            action=action,
        )

    # ---------------------------------------------------------
    # HELPERS
    # ---------------------------------------------------------
    def _extract_prices(self, rows: List[Dict[str, Any]]) -> List[float]:
        """Extract prices from level objects."""
        out = []
        for row in rows:
            price = row.get("price")
            if price is not None:
                out.append(float(price))
        return sorted(set(out))

    def _nearest_below(self, price: float, levels: List[float]) -> Optional[float]:
        """Find nearest level below price."""
        below = [x for x in levels if x < price]
        return max(below) if below else None

    def _nearest_above(self, price: float, levels: List[float]) -> Optional[float]:
        """Find nearest level above price."""
        above = [x for x in levels if x > price]
        return min(above) if above else None

    def _pattern_name(self, pattern: Optional[Dict[str, Any]]) -> Optional[str]:
        """Extract readable pattern name."""
        if not pattern:
            return None
        raw = pattern.get("type")
        if not raw:
            return None
        return raw.replace("_", " ")

    def _fmt(self, value: Optional[float]) -> str:
        """Format price value."""
        if value is None:
            return "N/A"
        if value >= 1000:
            return f"{value:,.0f}"
        return f"{value:.2f}"

    def _serialize(self, scenario: ScenarioV3) -> Dict[str, Any]:
        """Convert scenario to dict."""
        return {
            "type": scenario.type,
            "direction": scenario.direction,
            "title": scenario.title,
            "probability": scenario.probability,
            "summary": scenario.summary,
            "trigger": scenario.trigger,
            "invalidation": scenario.invalidation,
            "action": scenario.action,
        }


# ---------------------------------------------------------
# Factory / Singleton
# ---------------------------------------------------------
_scenario_engine_v3_instance: Optional[ScenarioEngineV3] = None


def get_scenario_engine_v3() -> ScenarioEngineV3:
    """Get singleton instance of ScenarioEngineV3."""
    global _scenario_engine_v3_instance
    if _scenario_engine_v3_instance is None:
        _scenario_engine_v3_instance = ScenarioEngineV3()
    return _scenario_engine_v3_instance


# Direct import singleton
scenario_engine_v3 = ScenarioEngineV3()
