"""
CHOCH Validation Engine — Structure Shift Validation
=====================================================

CHOCH сам по себе = ничто.
CHOCH + sweep + displacement = сигнал.

Validation rules:
1. Был ли sweep до CHOCH? (+0.30)
2. Был ли displacement после CHOCH? (+0.35)
3. Качество structural break? (+0.20)
4. Локация (около key zone)? (+0.15)

Score threshold:
- >= 0.70 → VALID
- 0.45-0.69 → WEAK/WATCH
- < 0.45 → FAKE

Output:
{
    "is_valid": true,
    "direction": "bullish",
    "score": 0.81,
    "label": "valid_choch",
    "reasons": ["sell-side liquidity swept", "bullish displacement confirmed"],
    "event_time": 1731628800
}
"""
from __future__ import annotations
from typing import Any, Dict, List, Optional


class CHOCHValidationEngine:
    """
    Validates Change of Character (CHOCH) events.
    
    A valid CHOCH requires:
    - Liquidity sweep before the break
    - Displacement (strong move) after the break
    - Quality structural break (not noise)
    - Good location (near key zones)
    """

    def __init__(
        self,
        sweep_weight: float = 0.30,
        displacement_weight: float = 0.35,
        structure_weight: float = 0.20,
        location_weight: float = 0.15,
        valid_threshold: float = 0.70,
        weak_threshold: float = 0.45,
    ):
        self.sweep_weight = sweep_weight
        self.displacement_weight = displacement_weight
        self.structure_weight = structure_weight
        self.location_weight = location_weight
        self.valid_threshold = valid_threshold
        self.weak_threshold = weak_threshold

    def build(
        self,
        structure_context: Dict[str, Any],
        liquidity: Dict[str, Any],
        displacement: Dict[str, Any],
        base_layer: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Validate the most recent CHOCH event.
        
        Returns:
            {
                "is_valid": bool,
                "direction": str,
                "score": float,
                "label": str,
                "reasons": [],
                "components": {},
                "event_time": int | null
            }
        """
        # Extract last CHOCH event from structure_context
        choch_event = self._extract_last_choch(structure_context)
        
        if not choch_event:
            return self._empty_result("no_choch_found")

        # Determine CHOCH direction
        direction = self._get_choch_direction(choch_event)
        event_time = choch_event.get("time", choch_event.get("timestamp", 0))
        event_index = choch_event.get("index", 0)

        # Score each component
        sweep_score, sweep_details = self._score_sweep(
            liquidity, choch_event, direction, event_index
        )
        displacement_score, displacement_details = self._score_displacement(
            displacement, choch_event, direction, event_index
        )
        structure_score, structure_details = self._score_structure_break(
            structure_context, choch_event, direction
        )
        location_score, location_details = self._score_location(
            base_layer, choch_event, direction
        )

        # Calculate total score
        total = sweep_score + displacement_score + structure_score + location_score

        # Build reasons
        reasons = self._build_reasons(
            sweep_score, sweep_details,
            displacement_score, displacement_details,
            structure_score, structure_details,
            location_score, location_details,
            direction
        )

        return {
            "is_valid": total >= self.valid_threshold,
            "direction": direction,
            "score": round(total, 2),
            "label": self._get_label(total),
            "reasons": reasons,
            "components": {
                "sweep": {"score": round(sweep_score, 2), "max": self.sweep_weight, "details": sweep_details},
                "displacement": {"score": round(displacement_score, 2), "max": self.displacement_weight, "details": displacement_details},
                "structure": {"score": round(structure_score, 2), "max": self.structure_weight, "details": structure_details},
                "location": {"score": round(location_score, 2), "max": self.location_weight, "details": location_details},
            },
            "event_time": event_time,
            "event_index": event_index,
            "choch_type": choch_event.get("type", "unknown"),
        }

    def _empty_result(self, reason: str) -> Dict[str, Any]:
        return {
            "is_valid": False,
            "direction": "unknown",
            "score": 0.0,
            "label": "no_choch",
            "reasons": [reason],
            "components": {},
            "event_time": None,
            "event_index": None,
            "choch_type": None,
        }

    # ---------------------------------------------------------
    # EXTRACT CHOCH EVENT
    # ---------------------------------------------------------
    def _extract_last_choch(self, structure_context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Extract the most recent CHOCH event from structure context."""
        if not structure_context:
            return None

        # Try multiple sources
        # 1. Direct events list
        events = structure_context.get("events", [])
        for event in reversed(events):
            event_type = event.get("type", "").lower()
            if "choch" in event_type:
                return event

        # 2. Last event field
        last_event = structure_context.get("last_event", "")
        if "choch" in str(last_event).lower():
            return {
                "type": last_event,
                "time": structure_context.get("last_event_time", 0),
                "index": structure_context.get("last_event_index", 0),
            }

        # 3. Structural events
        structural_events = structure_context.get("structural_events", [])
        for event in reversed(structural_events):
            if "choch" in event.get("type", "").lower():
                return event

        return None

    def _get_choch_direction(self, choch_event: Dict[str, Any]) -> str:
        """Determine CHOCH direction."""
        event_type = choch_event.get("type", "").lower()
        
        if "up" in event_type or "bullish" in event_type:
            return "bullish"
        if "down" in event_type or "bearish" in event_type:
            return "bearish"
        
        # Fallback: check price movement if available
        return "bullish" if "up" in event_type else "bearish"

    # ---------------------------------------------------------
    # SWEEP SCORE (0.30 max)
    # ---------------------------------------------------------
    def _score_sweep(
        self,
        liquidity: Dict[str, Any],
        choch_event: Dict[str, Any],
        direction: str,
        event_index: int,
    ) -> tuple[float, str]:
        """
        Check if liquidity was swept before CHOCH.
        
        For bullish CHOCH: need sell-side sweep
        For bearish CHOCH: need buy-side sweep
        """
        if not liquidity:
            return 0.0, "no_liquidity_data"

        sweeps = liquidity.get("sweeps", [])
        if not sweeps:
            return 0.0, "no_sweeps_detected"

        # Look for sweep before CHOCH
        target_sweep_type = "sell_side_sweep" if direction == "bullish" else "buy_side_sweep"
        
        for sweep in sweeps:
            sweep_index = sweep.get("index", 0)
            sweep_type = sweep.get("type", "")
            
            # Sweep should be before or around CHOCH event
            if sweep_index <= event_index + 5 and sweep_index >= event_index - 20:
                if sweep_type == target_sweep_type:
                    strength = sweep.get("strength", 1.0)
                    # Strong sweep = full points, weak = partial
                    score = min(self.sweep_weight, self.sweep_weight * (strength / 3.0))
                    return score, f"{sweep_type}_found"

        # Check if there's ANY sweep nearby (partial credit)
        for sweep in sweeps:
            sweep_index = sweep.get("index", 0)
            if abs(sweep_index - event_index) <= 30:
                return self.sweep_weight * 0.3, "sweep_nearby_wrong_type"

        return 0.0, "no_sweep_before_choch"

    # ---------------------------------------------------------
    # DISPLACEMENT SCORE (0.35 max)
    # ---------------------------------------------------------
    def _score_displacement(
        self,
        displacement: Dict[str, Any],
        choch_event: Dict[str, Any],
        direction: str,
        event_index: int,
    ) -> tuple[float, str]:
        """
        Check if displacement (strong move) occurred after CHOCH.
        
        For bullish CHOCH: need bullish displacement
        For bearish CHOCH: need bearish displacement
        """
        if not displacement:
            return 0.0, "no_displacement_data"

        events = displacement.get("events", [])
        if not events:
            return 0.0, "no_displacement_events"

        # Look for displacement after CHOCH
        for event in events:
            start_index = event.get("start_index", 0)
            event_direction = event.get("direction", "")
            
            # Displacement should be after CHOCH
            if start_index >= event_index - 5 and start_index <= event_index + 30:
                if event_direction == direction:
                    strength = event.get("strength", 1.5)
                    # Scale by strength (1.5 is threshold, 3.0 is very strong)
                    score = min(self.displacement_weight, self.displacement_weight * (strength / 2.5))
                    return score, f"{direction}_displacement_confirmed"

        # Check recent displacement direction
        recent = displacement.get("recent_displacement")
        if recent == direction:
            return self.displacement_weight * 0.5, "recent_displacement_matches"

        # Check current state
        state = displacement.get("current_state", "")
        if state == "expansion":
            return self.displacement_weight * 0.3, "expansion_state_partial"

        return 0.0, "no_displacement_after_choch"

    # ---------------------------------------------------------
    # STRUCTURE BREAK SCORE (0.20 max)
    # ---------------------------------------------------------
    def _score_structure_break(
        self,
        structure_context: Dict[str, Any],
        choch_event: Dict[str, Any],
        direction: str,
    ) -> tuple[float, str]:
        """
        Check quality of the structural break.
        
        Good CHOCH breaks:
        - Last LH for bullish
        - Last HL for bearish
        """
        if not structure_context:
            return 0.0, "no_structure_data"

        # Check if structure aligns with CHOCH direction
        bias = structure_context.get("bias", "neutral")
        
        # If bias already matches direction, CHOCH is confirmatory
        if (direction == "bullish" and bias in ["bullish", "neutral"]) or \
           (direction == "bearish" and bias in ["bearish", "neutral"]):
            score = self.structure_weight * 0.8
            detail = "structure_supports_direction"
        else:
            # CHOCH against current bias = needs more confirmation
            score = self.structure_weight * 0.5
            detail = "choch_against_current_bias"

        # Check structure strength
        strength = structure_context.get("structure_score", 0.5)
        score *= min(strength * 1.5, 1.0)

        return min(score, self.structure_weight), detail

    # ---------------------------------------------------------
    # LOCATION SCORE (0.15 max)
    # ---------------------------------------------------------
    def _score_location(
        self,
        base_layer: Dict[str, Any],
        choch_event: Dict[str, Any],
        direction: str,
    ) -> tuple[float, str]:
        """
        Check if CHOCH occurred near key zones.
        
        Good locations:
        - Near support for bullish
        - Near resistance for bearish
        """
        if not base_layer:
            return self.location_weight * 0.5, "no_base_layer_partial"

        supports = base_layer.get("supports", [])
        resistances = base_layer.get("resistances", [])

        # Check if we have zones
        if direction == "bullish" and supports:
            return self.location_weight, "near_support_zone"
        if direction == "bearish" and resistances:
            return self.location_weight, "near_resistance_zone"

        # Partial credit for having some structure
        if supports or resistances:
            return self.location_weight * 0.5, "zones_available"

        return 0.0, "no_key_zones"

    # ---------------------------------------------------------
    # HELPERS
    # ---------------------------------------------------------
    def _get_label(self, score: float) -> str:
        """Convert score to label."""
        if score >= self.valid_threshold:
            return "valid_choch"
        if score >= self.weak_threshold:
            return "weak_choch"
        return "fake_choch"

    def _build_reasons(
        self,
        sweep_score: float, sweep_details: str,
        displacement_score: float, displacement_details: str,
        structure_score: float, structure_details: str,
        location_score: float, location_details: str,
        direction: str,
    ) -> List[str]:
        """Build human-readable reasons list."""
        reasons = []

        # Sweep
        if sweep_score >= self.sweep_weight * 0.7:
            side = "sell-side" if direction == "bullish" else "buy-side"
            reasons.append(f"{side} liquidity swept")
        elif sweep_score > 0:
            reasons.append("partial liquidity event")
        else:
            reasons.append("no liquidity sweep before break")

        # Displacement
        if displacement_score >= self.displacement_weight * 0.7:
            reasons.append(f"{direction} displacement confirmed")
        elif displacement_score > 0:
            reasons.append("weak displacement")
        else:
            reasons.append("no displacement after break")

        # Structure
        if structure_score >= self.structure_weight * 0.7:
            reasons.append("clean structural break")
        elif structure_score > 0:
            reasons.append("structure break in noise")

        # Location
        if location_score >= self.location_weight * 0.7:
            zone = "support" if direction == "bullish" else "resistance"
            reasons.append(f"near key {zone} zone")

        return reasons


# ---------------------------------------------------------
# Factory / Singleton
# ---------------------------------------------------------
_choch_validation_engine_instance: Optional[CHOCHValidationEngine] = None


def get_choch_validation_engine() -> CHOCHValidationEngine:
    """Get singleton instance of CHOCHValidationEngine."""
    global _choch_validation_engine_instance
    if _choch_validation_engine_instance is None:
        _choch_validation_engine_instance = CHOCHValidationEngine()
    return _choch_validation_engine_instance


# Direct import singleton
choch_validation_engine = CHOCHValidationEngine()
