"""
Scenario Engine V2 — converts market understanding into actionable scenarios.

This is the bridge from "analysis tool" → "decision tool".
Instead of "pattern found / no pattern", system now outputs:
- Primary scenario with probability, summary, action
- Alternative scenario with trigger/invalidation
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass
class Scenario:
    type: str                   # primary | alternative
    direction: str              # bullish | bearish | neutral
    title: str
    probability: float          # 0..1
    summary: str
    action: str
    trigger: Optional[str] = None
    invalidation: Optional[str] = None


class ScenarioEngineV2:
    """
    Converts market understanding into actionable scenarios.

    Inputs:
      - structure_context
      - base_layer
      - decision
      - primary_pattern
      - alternative_patterns
      - current_price

    Output:
      - scenarios[]
    """

    def build(
        self,
        structure_context: Dict[str, Any],
        base_layer: Dict[str, Any],
        current_price: float,
        decision: Dict[str, Any],
        primary_pattern: Optional[Dict[str, Any]] = None,
        alternative_patterns: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        alternative_patterns = alternative_patterns or []

        supports = self._extract_prices(base_layer.get("supports", []))
        resistances = self._extract_prices(base_layer.get("resistances", []))

        nearest_support = self._nearest_below(current_price, supports)
        nearest_resistance = self._nearest_above(current_price, resistances)

        regime = structure_context.get("regime", "range")
        phase = structure_context.get("market_phase", "range")
        last_event = structure_context.get("last_event", "none")
        bias = decision.get("bias", "neutral")
        confidence = float(decision.get("confidence", decision.get("score", 0.5)) or 0.5)
        alignment = decision.get("alignment", "mixed")

        primary = self._build_primary_scenario(
            regime=regime,
            phase=phase,
            last_event=last_event,
            bias=bias,
            confidence=confidence,
            alignment=alignment,
            current_price=current_price,
            support=nearest_support,
            resistance=nearest_resistance,
            primary_pattern=primary_pattern,
        )

        alternative = self._build_alternative_scenario(
            regime=regime,
            phase=phase,
            last_event=last_event,
            bias=bias,
            confidence=confidence,
            alignment=alignment,
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
    # PRIMARY
    # ---------------------------------------------------------
    def _build_primary_scenario(
        self,
        regime: str,
        phase: str,
        last_event: str,
        bias: str,
        confidence: float,
        alignment: str,
        current_price: float,
        support: Optional[float],
        resistance: Optional[float],
        primary_pattern: Optional[Dict[str, Any]],
    ) -> Scenario:
        pattern_name = self._pattern_name(primary_pattern)

        if bias == "bearish":
            title = self._bearish_title(regime, phase, pattern_name)
            summary = self._bearish_summary(
                regime=regime,
                phase=phase,
                last_event=last_event,
                support=support,
                resistance=resistance,
                pattern_name=pattern_name,
                alignment=alignment,
            )
            action = self._bearish_action(resistance, support)
            trigger = f"rejection below {self._fmt(resistance)}" if resistance else "renewed downside weakness"
            invalidation = f"reclaim above {self._fmt(resistance)}" if resistance else None

            return Scenario(
                type="primary",
                direction="bearish",
                title=title,
                probability=round(max(0.52, confidence), 2),
                summary=summary,
                action=action,
                trigger=trigger,
                invalidation=invalidation,
            )

        if bias == "bullish":
            title = self._bullish_title(regime, phase, pattern_name)
            summary = self._bullish_summary(
                regime=regime,
                phase=phase,
                last_event=last_event,
                support=support,
                resistance=resistance,
                pattern_name=pattern_name,
                alignment=alignment,
            )
            action = self._bullish_action(support, resistance)
            trigger = f"hold above {self._fmt(support)}" if support else "continued strength"
            invalidation = f"loss of {self._fmt(support)}" if support else None

            return Scenario(
                type="primary",
                direction="bullish",
                title=title,
                probability=round(max(0.52, confidence), 2),
                summary=summary,
                action=action,
                trigger=trigger,
                invalidation=invalidation,
            )

        title = "Range continuation"
        summary = self._neutral_summary(
            regime=regime,
            phase=phase,
            support=support,
            resistance=resistance,
            pattern_name=pattern_name,
        )
        action = self._neutral_action(support, resistance)

        return Scenario(
            type="primary",
            direction="neutral",
            title=title,
            probability=round(max(0.50, confidence), 2),
            summary=summary,
            action=action,
            trigger="confirmed break of range boundary",
            invalidation=None,
        )

    # ---------------------------------------------------------
    # ALTERNATIVE
    # ---------------------------------------------------------
    def _build_alternative_scenario(
        self,
        regime: str,
        phase: str,
        last_event: str,
        bias: str,
        confidence: float,
        alignment: str,
        current_price: float,
        support: Optional[float],
        resistance: Optional[float],
        alternative_patterns: List[Dict[str, Any]],
    ) -> Scenario:
        alt_name = self._pattern_name(alternative_patterns[0] if alternative_patterns else None)

        alt_prob = round(min(0.48, max(0.22, 1.0 - confidence)), 2)

        if bias == "bearish":
            return Scenario(
                type="alternative",
                direction="bullish",
                title="Relief bounce extension",
                probability=alt_prob,
                summary=(
                    f"Current decline may pause into a stronger rebound"
                    f"{self._alt_suffix(alt_name)} if price reclaims resistance"
                    f"{self._level_suffix(resistance)} and downside follow-through fades."
                ),
                action="only above resistance reclaim",
                trigger=f"close above {self._fmt(resistance)}" if resistance else "upside reclaim",
                invalidation=f"drop back below {self._fmt(current_price)}",
            )

        if bias == "bullish":
            return Scenario(
                type="alternative",
                direction="bearish",
                title="Failed continuation / deeper pullback",
                probability=alt_prob,
                summary=(
                    f"Upside continuation may fail and rotate back toward support"
                    f"{self._alt_suffix(alt_name)} if momentum fades near resistance."
                ),
                action="protect longs on failed breakout",
                trigger=f"loss of {self._fmt(support)}" if support else "failed hold",
                invalidation=f"reclaim above {self._fmt(resistance)}" if resistance else None,
            )

        return Scenario(
            type="alternative",
            direction="breakout",
            title="Range resolution",
            probability=alt_prob,
            summary=(
                f"Neutral market may resolve into directional expansion"
                f"{self._alt_suffix(alt_name)} once one side of the range is decisively broken."
            ),
            action="wait confirmed breakout",
            trigger=(
                f"break above {self._fmt(resistance)} or below {self._fmt(support)}"
                if support and resistance else "range break"
            ),
            invalidation=None,
        )

    # ---------------------------------------------------------
    # TITLES / SUMMARIES
    # ---------------------------------------------------------
    def _bearish_title(self, regime: str, phase: str, pattern_name: Optional[str]) -> str:
        if pattern_name:
            return f"Bearish continuation from {pattern_name}"
        if phase == "markdown":
            return "Bearish continuation after weak bounce"
        if regime == "expansion":
            return "Downside expansion continues"
        return "Bearish continuation"

    def _bullish_title(self, regime: str, phase: str, pattern_name: Optional[str]) -> str:
        if pattern_name:
            return f"Bullish continuation from {pattern_name}"
        if phase == "markup":
            return "Bullish continuation after pullback"
        if regime == "expansion":
            return "Upside expansion continues"
        return "Bullish continuation"

    def _bearish_summary(
        self,
        regime: str,
        phase: str,
        last_event: str,
        support: Optional[float],
        resistance: Optional[float],
        pattern_name: Optional[str],
        alignment: str,
    ) -> str:
        parts = [
            f"Market remains in {phase or regime} conditions with bearish directional pressure."
        ]
        if resistance:
            parts.append(f"Nearest resistance sits around {self._fmt(resistance)}.")
        if support:
            parts.append(f"Nearest support sits around {self._fmt(support)}.")
        if pattern_name:
            parts.append(f"Selected structure: {pattern_name}.")
        if last_event != "none":
            parts.append(f"Last structural event: {last_event}.")
        if alignment == "mixed":
            parts.append("Higher and lower timeframes are not fully aligned, so downside continuation should be confirmed rather than assumed.")
        return " ".join(parts)

    def _bullish_summary(
        self,
        regime: str,
        phase: str,
        last_event: str,
        support: Optional[float],
        resistance: Optional[float],
        pattern_name: Optional[str],
        alignment: str,
    ) -> str:
        parts = [
            f"Market remains in {phase or regime} conditions with bullish directional pressure."
        ]
        if support:
            parts.append(f"Nearest support sits around {self._fmt(support)}.")
        if resistance:
            parts.append(f"Main upside test is resistance near {self._fmt(resistance)}.")
        if pattern_name:
            parts.append(f"Selected structure: {pattern_name}.")
        if last_event != "none":
            parts.append(f"Last structural event: {last_event}.")
        if alignment == "mixed":
            parts.append("Timeframe alignment is mixed, so continuation needs confirmation above resistance.")
        return " ".join(parts)

    def _neutral_summary(
        self,
        regime: str,
        phase: str,
        support: Optional[float],
        resistance: Optional[float],
        pattern_name: Optional[str],
    ) -> str:
        parts = [f"Market is currently non-directional inside {phase or regime} conditions."]
        if support and resistance:
            parts.append(f"Range is framed by support near {self._fmt(support)} and resistance near {self._fmt(resistance)}.")
        if pattern_name:
            parts.append(f"Visible structure: {pattern_name}.")
        return " ".join(parts)

    # ---------------------------------------------------------
    # ACTIONS
    # ---------------------------------------------------------
    def _bearish_action(self, resistance: Optional[float], support: Optional[float]) -> str:
        if resistance and support:
            return f"wait rejection from {self._fmt(resistance)} / target {self._fmt(support)}"
        if resistance:
            return f"wait rejection from {self._fmt(resistance)}"
        return "wait downside confirmation"

    def _bullish_action(self, support: Optional[float], resistance: Optional[float]) -> str:
        if support and resistance:
            return f"buy support hold / target {self._fmt(resistance)}"
        if support:
            return f"buy hold above {self._fmt(support)}"
        return "wait upside confirmation"

    def _neutral_action(self, support: Optional[float], resistance: Optional[float]) -> str:
        if support and resistance:
            return f"trade range {self._fmt(support)} ↔ {self._fmt(resistance)} or wait breakout"
        return "wait for directional break"

    # ---------------------------------------------------------
    # HELPERS
    # ---------------------------------------------------------
    def _extract_prices(self, rows: List[Dict[str, Any]]) -> List[float]:
        out = []
        for row in rows:
            price = row.get("price")
            if price is not None:
                out.append(float(price))
        return sorted(set(out))

    def _nearest_below(self, price: float, levels: List[float]) -> Optional[float]:
        below = [x for x in levels if x < price]
        return max(below) if below else None

    def _nearest_above(self, price: float, levels: List[float]) -> Optional[float]:
        above = [x for x in levels if x > price]
        return min(above) if above else None

    def _pattern_name(self, pattern: Optional[Dict[str, Any]]) -> Optional[str]:
        if not pattern:
            return None
        raw = pattern.get("type")
        if not raw:
            return None
        return raw.replace("_", " ")

    def _fmt(self, value: Optional[float]) -> str:
        return f"{value:.2f}" if value is not None else "N/A"

    def _alt_suffix(self, alt_name: Optional[str]) -> str:
        return f" using alternative structure {alt_name}" if alt_name else ""

    def _level_suffix(self, level: Optional[float]) -> str:
        return f" near {self._fmt(level)}" if level else ""

    def _serialize(self, scenario: Scenario) -> Dict[str, Any]:
        return {
            "type": scenario.type,
            "direction": scenario.direction,
            "title": scenario.title,
            "probability": scenario.probability,
            "summary": scenario.summary,
            "action": scenario.action,
            "trigger": scenario.trigger,
            "invalidation": scenario.invalidation,
        }


# Singleton
_scenario_engine_v2: Optional[ScenarioEngineV2] = None

def get_scenario_engine_v2() -> ScenarioEngineV2:
    global _scenario_engine_v2
    if _scenario_engine_v2 is None:
        _scenario_engine_v2 = ScenarioEngineV2()
    return _scenario_engine_v2
