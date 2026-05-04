"""
Trade Setup Generator — Execution-Ready Trade Setups
====================================================

Converts:
  decision + scenarios + levels + structure + current_price
  ↓
  entry, stop, target_1, target_2, invalidation, rr, valid, reason

Hard rules:
  1. If no usable levels => no setup (don't fantasize)
  2. If rr < 1.5 => valid = false
  3. Primary setup comes from primary scenario
  4. Alternative setup comes from alternative scenario
  5. Entry depends on context (not just nearest level)
  6. Stop always behind invalidation level (structural)

Output:
{
  "trade_setup": {
    "primary": {
      "direction": "short",
      "entry_zone": [88800, 89200],
      "stop_loss": 90500,
      "target_1": 78500,
      "target_2": 68200,
      "invalidation": 90500,
      "rr": 2.1,
      "valid": true,
      "reason": "bearish context + relief bounce into resistance"
    },
    "alternative": {...}
  }
}
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class TradeSetup:
    """Single trade setup object."""
    direction: str                    # long | short
    entry_zone: List[float]           # [low, high]
    stop_loss: float
    target_1: float
    target_2: Optional[float]
    invalidation: float
    rr: float
    valid: bool
    reason: str


class TradeSetupGenerator:
    """
    Trade Setup Generator

    Inputs:
      - decision
      - scenarios
      - base_layer
      - structure_context
      - current_price

    Output:
      - primary setup
      - alternative setup

    Hard rules:
      - if no usable levels => no setup
      - if rr < 1.5 => valid = false
      - primary setup comes from primary scenario
      - alternative setup comes from alternative scenario
    """

    MIN_RR = 1.5
    ENTRY_BUFFER = 0.003   # 0.3%
    STOP_BUFFER = 0.006    # 0.6%

    def build(
        self,
        decision: Dict[str, Any],
        scenarios: List[Dict[str, Any]],
        base_layer: Dict[str, Any],
        structure_context: Dict[str, Any],
        current_price: float,
    ) -> Dict[str, Any]:
        """
        Build trade setups from analysis components.
        
        Args:
            decision: Decision Engine V2 output
            scenarios: Scenario Engine V3 output (list)
            base_layer: Levels data (supports, resistances)
            structure_context: Structure analysis
            current_price: Current market price
        
        Returns:
            {"trade_setup": {"primary": {...}, "alternative": {...}}}
        """
        supports = self._extract_levels(base_layer.get("supports", []), kind="support")
        resistances = self._extract_levels(base_layer.get("resistances", []), kind="resistance")

        primary_scenario = self._find_scenario(scenarios, "primary")
        alternative_scenario = self._find_scenario(scenarios, "alternative")

        primary_setup = self._build_from_scenario(
            scenario=primary_scenario,
            decision=decision,
            supports=supports,
            resistances=resistances,
            structure_context=structure_context,
            current_price=current_price,
            is_alternative=False,
        )

        alternative_setup = self._build_from_scenario(
            scenario=alternative_scenario,
            decision=decision,
            supports=supports,
            resistances=resistances,
            structure_context=structure_context,
            current_price=current_price,
            is_alternative=True,
        )

        return {
            "trade_setup": {
                "primary": self._serialize(primary_setup) if primary_setup else None,
                "alternative": self._serialize(alternative_setup) if alternative_setup else None,
            }
        }

    # =========================================================
    # Core builder
    # =========================================================
    def _build_from_scenario(
        self,
        scenario: Optional[Dict[str, Any]],
        decision: Dict[str, Any],
        supports: List[Dict[str, Any]],
        resistances: List[Dict[str, Any]],
        structure_context: Dict[str, Any],
        current_price: float,
        is_alternative: bool,
    ) -> Optional[TradeSetup]:
        """Build setup from a single scenario."""
        if not scenario:
            return None

        direction = self._resolve_direction(scenario.get("direction"), is_alternative)
        if direction not in {"long", "short"}:
            return None

        context = decision.get("context", "trend_continuation")
        regime = structure_context.get("regime", "range")

        if direction == "short":
            return self._build_short_setup(
                scenario=scenario,
                context=context,
                regime=regime,
                supports=supports,
                resistances=resistances,
                current_price=current_price,
            )

        return self._build_long_setup(
            scenario=scenario,
            context=context,
            regime=regime,
            supports=supports,
            resistances=resistances,
            current_price=current_price,
        )

    # =========================================================
    # SHORT setup
    # =========================================================
    def _build_short_setup(
        self,
        scenario: Dict[str, Any],
        context: str,
        regime: str,
        supports: List[Dict[str, Any]],
        resistances: List[Dict[str, Any]],
        current_price: float,
    ) -> Optional[TradeSetup]:
        """Build short (sell) setup."""
        nearest_resistance = self._nearest_above(current_price, resistances)
        nearest_support = self._nearest_below(current_price, supports)
        next_support = self._second_below(current_price, supports)

        # No usable levels => no setup
        if not nearest_resistance or not nearest_support:
            return None

        # Entry zone based on context
        entry_low, entry_high = self._build_short_entry_zone(
            context=context,
            resistance=nearest_resistance["price"],
            current_price=current_price,
        )

        # Stop behind resistance (structural)
        stop = round(nearest_resistance["price"] * (1 + self.STOP_BUFFER), 2)

        # Targets
        target_1 = round(nearest_support["price"], 2)
        target_2 = round(next_support["price"], 2) if next_support else None
        invalidation = stop

        # Risk/Reward calculation
        rr = self._calc_short_rr(
            entry=(entry_low + entry_high) / 2,
            stop=stop,
            target=target_1,
        )

        # Valid only if RR >= MIN_RR
        valid = rr >= self.MIN_RR

        reason = self._build_short_reason(
            context=context,
            regime=regime,
            resistance=nearest_resistance["price"],
            support=nearest_support["price"],
        )

        return TradeSetup(
            direction="short",
            entry_zone=[entry_low, entry_high],
            stop_loss=stop,
            target_1=target_1,
            target_2=target_2,
            invalidation=invalidation,
            rr=round(rr, 2),
            valid=valid,
            reason=reason,
        )

    # =========================================================
    # LONG setup
    # =========================================================
    def _build_long_setup(
        self,
        scenario: Dict[str, Any],
        context: str,
        regime: str,
        supports: List[Dict[str, Any]],
        resistances: List[Dict[str, Any]],
        current_price: float,
    ) -> Optional[TradeSetup]:
        """Build long (buy) setup."""
        nearest_support = self._nearest_below(current_price, supports)
        nearest_resistance = self._nearest_above(current_price, resistances)
        next_resistance = self._second_above(current_price, resistances)

        # No usable levels => no setup
        if not nearest_support or not nearest_resistance:
            return None

        # Entry zone based on context
        entry_low, entry_high = self._build_long_entry_zone(
            context=context,
            support=nearest_support["price"],
            resistance=nearest_resistance["price"],
            current_price=current_price,
        )

        # Stop behind support (structural)
        stop = round(nearest_support["price"] * (1 - self.STOP_BUFFER), 2)

        # Targets
        target_1 = round(nearest_resistance["price"], 2)
        target_2 = round(next_resistance["price"], 2) if next_resistance else None
        invalidation = stop

        # Risk/Reward calculation
        rr = self._calc_long_rr(
            entry=(entry_low + entry_high) / 2,
            stop=stop,
            target=target_1,
        )

        # Valid only if RR >= MIN_RR
        valid = rr >= self.MIN_RR

        reason = self._build_long_reason(
            context=context,
            regime=regime,
            support=nearest_support["price"],
            resistance=nearest_resistance["price"],
        )

        return TradeSetup(
            direction="long",
            entry_zone=[entry_low, entry_high],
            stop_loss=stop,
            target_1=target_1,
            target_2=target_2,
            invalidation=invalidation,
            rr=round(rr, 2),
            valid=valid,
            reason=reason,
        )

    # =========================================================
    # Entry logic — context-dependent
    # =========================================================
    def _build_short_entry_zone(
        self,
        context: str,
        resistance: float,
        current_price: float,
    ) -> Tuple[float, float]:
        """Build entry zone for short setup based on context."""
        # relief_bounce / rejection logic -> sell near resistance
        if context in {"relief_bounce", "trend_continuation"}:
            low = resistance * (1 - self.ENTRY_BUFFER)
            high = resistance * (1 + self.ENTRY_BUFFER / 2)
            return round(low, 2), round(high, 2)

        # fallback — near current price
        low = current_price * (1 - self.ENTRY_BUFFER)
        high = current_price * (1 + self.ENTRY_BUFFER)
        return round(low, 2), round(high, 2)

    def _build_long_entry_zone(
        self,
        context: str,
        support: float,
        resistance: float,
        current_price: float,
    ) -> Tuple[float, float]:
        """Build entry zone for long setup based on context."""
        # pullback logic -> buy near support
        if context in {"pullback", "trend_continuation"}:
            low = support * (1 - self.ENTRY_BUFFER / 2)
            high = support * (1 + self.ENTRY_BUFFER)
            return round(low, 2), round(high, 2)

        # breakout reclaim logic -> buy after reclaim
        low = resistance * (1 - self.ENTRY_BUFFER / 2)
        high = resistance * (1 + self.ENTRY_BUFFER)
        return round(low, 2), round(high, 2)

    # =========================================================
    # Reasoning — human-readable explanation
    # =========================================================
    def _build_short_reason(
        self,
        context: str,
        regime: str,
        resistance: float,
        support: float,
    ) -> str:
        """Build reason string for short setup."""
        return (
            f"bearish context + {context} into resistance {resistance:,.2f}; "
            f"targeting support {support:,.2f} inside {regime} regime"
        )

    def _build_long_reason(
        self,
        context: str,
        regime: str,
        support: float,
        resistance: float,
    ) -> str:
        """Build reason string for long setup."""
        return (
            f"bullish context + {context} from support {support:,.2f}; "
            f"targeting resistance {resistance:,.2f} inside {regime} regime"
        )

    # =========================================================
    # Risk/Reward calculations
    # =========================================================
    def _calc_short_rr(self, entry: float, stop: float, target: float) -> float:
        """Calculate RR for short trade."""
        risk = max(stop - entry, 1e-9)
        reward = max(entry - target, 0.0)
        return reward / risk

    def _calc_long_rr(self, entry: float, stop: float, target: float) -> float:
        """Calculate RR for long trade."""
        risk = max(entry - stop, 1e-9)
        reward = max(target - entry, 0.0)
        return reward / risk

    # =========================================================
    # Helpers
    # =========================================================
    def _resolve_direction(self, scenario_direction: Optional[str], is_alternative: bool) -> str:
        """Convert scenario direction to trade direction."""
        if scenario_direction == "bearish":
            return "short"
        if scenario_direction == "bullish":
            return "long"
        return "neutral"

    def _find_scenario(self, scenarios: List[Dict[str, Any]], scenario_type: str) -> Optional[Dict[str, Any]]:
        """Find scenario by type."""
        for s in scenarios:
            if s.get("type") == scenario_type:
                return s
        return None

    def _extract_levels(self, rows: List[Dict[str, Any]], kind: str) -> List[Dict[str, Any]]:
        """Extract and sort levels from raw data."""
        clean = []
        for row in rows:
            price = row.get("price")
            if price is None:
                continue
            clean.append({
                "price": float(price),
                "strength": float(row.get("strength", 0.0) or 0.0),
                "type": kind,
            })
        clean.sort(key=lambda x: x["price"])
        return clean

    def _nearest_below(self, price: float, levels: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Find nearest level below price."""
        below = [x for x in levels if x["price"] < price]
        return max(below, key=lambda x: x["price"]) if below else None

    def _nearest_above(self, price: float, levels: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Find nearest level above price."""
        above = [x for x in levels if x["price"] > price]
        return min(above, key=lambda x: x["price"]) if above else None

    def _second_below(self, price: float, levels: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Find second nearest level below price."""
        below = sorted([x for x in levels if x["price"] < price], key=lambda x: x["price"], reverse=True)
        return below[1] if len(below) > 1 else None

    def _second_above(self, price: float, levels: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Find second nearest level above price."""
        above = sorted([x for x in levels if x["price"] > price], key=lambda x: x["price"])
        return above[1] if len(above) > 1 else None

    def _serialize(self, setup: TradeSetup) -> Dict[str, Any]:
        """Convert TradeSetup to dict."""
        return {
            "direction": setup.direction,
            "entry_zone": setup.entry_zone,
            "stop_loss": setup.stop_loss,
            "target_1": setup.target_1,
            "target_2": setup.target_2,
            "invalidation": setup.invalidation,
            "rr": setup.rr,
            "valid": setup.valid,
            "reason": setup.reason,
        }


# ---------------------------------------------------------
# Factory / Singleton
# ---------------------------------------------------------
_trade_setup_generator_instance: Optional[TradeSetupGenerator] = None


def get_trade_setup_generator() -> TradeSetupGenerator:
    """Get singleton instance of TradeSetupGenerator."""
    global _trade_setup_generator_instance
    if _trade_setup_generator_instance is None:
        _trade_setup_generator_instance = TradeSetupGenerator()
    return _trade_setup_generator_instance


# Direct import singleton
trade_setup_generator = TradeSetupGenerator()
