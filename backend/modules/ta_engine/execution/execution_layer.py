"""
Execution Layer
===============

Prop-trader level execution planning.

NOT just "entry / stop / tp" but:
  - ladder entry (partial entries)
  - scale-in plans
  - hard invalidation
  - dynamic targets
  - no-trade when structure doesn't give edge

Output:
  {
    "valid": bool,
    "direction": "long" | "short",
    "model": "retest_rejection" | "breakout_retest" | "single_trigger",
    "risk_profile": "normal" | "reduced" | "speculative",
    "size_factor": 0.0 - 1.0,
    "entry_plan": {...},
    "stop_plan": {...},
    "targets": [...],
    "management": {...},
    "rr": float
  }
"""

from __future__ import annotations
from typing import Any, Dict, List, Optional


class ExecutionLayer:
    """
    Builds execution plan from validated setup.
    
    Key principles:
    - Alignment affects position size
    - Entry model depends on scenario
    - Stop is always structural
    - Targets are logical (liquidity, fib, measured move)
    """

    def build(
        self,
        mtf_context: Dict[str, Any],
        unified_setup: Dict[str, Any],
        trade_setup: Optional[Dict[str, Any]],
        active_pattern: Optional[Dict[str, Any]],
        poi: Dict[str, Any],
        fib: Optional[Dict[str, Any]],
        current_price: float,
    ) -> Dict[str, Any]:
        """
        Build execution plan.
        
        Args:
            mtf_context: MTF orchestrator output
            unified_setup: Unified setup engine output
            trade_setup: Trade setup output
            active_pattern: Primary pattern
            poi: POI zones
            fib: Fibonacci data
            current_price: Current market price
        """
        # Validate unified setup
        if not unified_setup.get("valid", False):
            return self._invalid("unified setup invalid")

        # Get primary trade setup
        primary = None
        if trade_setup:
            primary = trade_setup.get("primary")
        
        # If no trade setup, try to build from unified setup
        if not primary or not primary.get("valid", False):
            primary = self._build_primary_from_unified(unified_setup, active_pattern, current_price)
        
        if not primary:
            return self._invalid("no valid entry found")

        direction = unified_setup.get("direction") or primary.get("direction")
        if direction not in {"long", "short"}:
            return self._invalid("no clear direction")

        alignment = mtf_context.get("alignment", "mixed")
        tradeability = mtf_context.get("tradeability", "low")

        # Calculate position sizing factor
        size_factor = self._size_factor(alignment, tradeability)
        if size_factor <= 0:
            return self._invalid("bad alignment - no trade")

        # Select execution model
        model = self._select_model(unified_setup, active_pattern)
        
        # Build entry plan
        entry_plan = self._build_entry_plan(primary, unified_setup, active_pattern, model, current_price)
        if not entry_plan:
            return self._invalid("cannot build entry plan")
        
        # Build stop plan
        stop_plan = self._build_stop_plan(primary, unified_setup, active_pattern, direction)
        
        # Build targets
        targets = self._build_targets(primary, fib, poi, direction, entry_plan, stop_plan)
        
        # Build management rules
        management = self._build_management(targets, direction, alignment)
        
        # Calculate R:R
        rr = self._calculate_rr(entry_plan, stop_plan, targets)
        
        # Determine status based on price vs entry zone
        status = "valid"
        entry_zone = entry_plan.get("zone") if entry_plan else None
        if entry_zone and len(entry_zone) >= 2:
            zone_low, zone_high = entry_zone[0], entry_zone[1]
            tolerance = abs(zone_high - zone_low) * 0.5
            if direction == "long" and current_price > zone_high + tolerance:
                status = "waiting"
            elif direction == "short" and current_price < zone_low - tolerance:
                status = "waiting"

        return {
            "valid": True,
            "status": status,
            "direction": direction,
            "model": model,
            "risk_profile": self._risk_profile(size_factor),
            "size_factor": round(size_factor, 2),
            "entry_plan": entry_plan,
            "stop_plan": stop_plan,
            "targets": targets,
            "management": management,
            "rr": round(rr, 2) if rr else None,
            "reason": "Waiting for price at entry" if status == "waiting" else None,
        }

    def _build_primary_from_unified(
        self,
        unified_setup: Dict[str, Any],
        active_pattern: Optional[Dict[str, Any]],
        current_price: float,
    ) -> Optional[Dict[str, Any]]:
        """Build primary entry from unified setup if trade_setup not available."""
        entry_ctx = unified_setup.get("entry_context", {})
        if not entry_ctx:
            return None
        
        direction = unified_setup.get("direction")
        if direction not in {"long", "short"}:
            return None
        
        # Get entry zone from pattern levels or preferred zone
        pattern_levels = entry_ctx.get("pattern_levels", {})
        preferred_zone = entry_ctx.get("preferred_zone", {})
        
        entry_zone = None
        if pattern_levels.get("entry_zone"):
            entry_zone = pattern_levels["entry_zone"]
        elif preferred_zone:
            entry_zone = [
                preferred_zone.get("lower", preferred_zone.get("price_low")),
                preferred_zone.get("upper", preferred_zone.get("price_high")),
            ]
        
        if not entry_zone or len(entry_zone) != 2:
            return None
        
        # Get stop and targets
        stop = pattern_levels.get("stop") or (active_pattern or {}).get("invalidation")
        tp1 = pattern_levels.get("tp1") or (active_pattern or {}).get("target_1")
        tp2 = pattern_levels.get("tp2") or (active_pattern or {}).get("target_2")
        
        if not stop:
            return None
        
        return {
            "valid": True,
            "direction": direction,
            "entry_zone": entry_zone,
            "stop_loss": stop,
            "invalidation": stop,
            "target_1": tp1,
            "target_2": tp2,
        }

    def _select_model(self, unified_setup: Dict[str, Any], active_pattern: Optional[Dict[str, Any]]) -> str:
        """
        Select execution model based on setup type.
        
        Models:
        - retest_rejection: sweep → displacement → structure → POI/zone
        - breakout_retest: pattern breakout with retest
        - single_trigger: simple trigger entry
        """
        chain = unified_setup.get("chain", [])
        pattern_type = (active_pattern or {}).get("type", "").lower()

        # Breakout patterns
        breakout_patterns = {
            "descending_triangle", "ascending_triangle", "symmetrical_triangle",
            "channel", "head_and_shoulders", "inverse_head_and_shoulders",
            "rising_wedge", "falling_wedge"
        }
        
        if pattern_type and any(p in pattern_type for p in breakout_patterns):
            return "breakout_retest"

        # Zone-based entry
        if any("zone" in x.lower() for x in chain) or any("poi" in x.lower() for x in chain):
            return "retest_rejection"

        # Fib-based entry
        if any("fib" in x.lower() for x in chain):
            return "retest_rejection"

        return "single_trigger"

    def _build_entry_plan(
        self,
        primary: Dict[str, Any],
        unified_setup: Dict[str, Any],
        active_pattern: Optional[Dict[str, Any]],
        model: str,
        current_price: float,
    ) -> Optional[Dict[str, Any]]:
        """Build entry plan with ladder or single entry."""
        zone = primary.get("entry_zone") or []
        
        # Try to get from pattern
        if len(zone) != 2 and active_pattern:
            breakout = active_pattern.get("breakout_level")
            invalidation = active_pattern.get("invalidation")
            if breakout and invalidation:
                buffer = abs(breakout - invalidation) * 0.05
                direction = unified_setup.get("direction")
                if direction == "long":
                    zone = [breakout, breakout + buffer]
                else:
                    zone = [breakout - buffer, breakout]
        
        if len(zone) != 2:
            return None
        
        try:
            low, high = float(zone[0]), float(zone[1])
            if low > high:
                low, high = high, low
        except (TypeError, ValueError):
            return None

        # Single trigger for simple setups
        if model == "single_trigger":
            mid = round((low + high) / 2, 2)
            return {
                "type": "single",
                "entries": [{"price": mid, "size_pct": 100}],
                "avg_entry": mid,
                "zone_low": round(low, 2),
                "zone_high": round(high, 2),
            }

        # Ladder entry for retest/breakout
        return {
            "type": "ladder",
            "entries": [
                {"price": round(low, 2), "size_pct": 40, "label": "E1"},
                {"price": round((low + high) / 2, 2), "size_pct": 35, "label": "E2"},
                {"price": round(high, 2), "size_pct": 25, "label": "E3"},
            ],
            "avg_entry": round((low * 0.4 + (low + high) / 2 * 0.35 + high * 0.25), 2),
            "zone_low": round(low, 2),
            "zone_high": round(high, 2),
        }

    def _build_stop_plan(
        self,
        primary: Dict[str, Any],
        unified_setup: Dict[str, Any],
        active_pattern: Optional[Dict[str, Any]],
        direction: str,
    ) -> Dict[str, Any]:
        """Build stop loss plan - always structural."""
        # Get stop from multiple sources
        stop = primary.get("stop_loss") or primary.get("invalidation")
        
        if not stop and active_pattern:
            stop = active_pattern.get("invalidation")
        
        if not stop:
            entry_ctx = unified_setup.get("entry_context", {})
            pattern_levels = entry_ctx.get("pattern_levels", {})
            stop = pattern_levels.get("stop")
        
        reason = "structural invalidation"
        
        # Add buffer for safety
        if stop:
            buffer = abs(stop) * 0.002  # 0.2% buffer
            if direction == "long":
                stop = stop - buffer
                reason = "below invalidation swing"
            else:
                stop = stop + buffer
                reason = "above invalidation swing"
        
        return {
            "type": "hard",
            "price": round(stop, 2) if stop else None,
            "reason": reason,
        }

    def _build_targets(
        self,
        primary: Dict[str, Any],
        fib: Optional[Dict[str, Any]],
        poi: Dict[str, Any],
        direction: str,
        entry_plan: Dict[str, Any],
        stop_plan: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """Build logical targets based on structure."""
        targets = []
        
        # Get targets from primary
        tp1 = primary.get("target_1")
        tp2 = primary.get("target_2")
        
        # Calculate measured move if no explicit targets
        avg_entry = entry_plan.get("avg_entry", 0)
        stop_price = stop_plan.get("price", 0)
        
        if avg_entry and stop_price:
            risk = abs(avg_entry - stop_price)
            
            if direction == "long":
                if not tp1:
                    tp1 = avg_entry + risk * 1.5
                if not tp2:
                    tp2 = avg_entry + risk * 2.5
            else:
                if not tp1:
                    tp1 = avg_entry - risk * 1.5
                if not tp2:
                    tp2 = avg_entry - risk * 2.5
        
        if tp1 is not None:
            targets.append({
                "name": "TP1",
                "price": round(tp1, 2),
                "size_pct": 40,
                "reason": "1.5R target",
            })
        
        if tp2 is not None:
            targets.append({
                "name": "TP2", 
                "price": round(tp2, 2),
                "size_pct": 35,
                "reason": "2.5R target",
            })
        
        # Add TP3 if we have room
        if tp2 and avg_entry and stop_price:
            risk = abs(avg_entry - stop_price)
            if direction == "long":
                tp3 = avg_entry + risk * 4
            else:
                tp3 = avg_entry - risk * 4
            
            targets.append({
                "name": "TP3",
                "price": round(tp3, 2),
                "size_pct": 25,
                "reason": "4R target (runner)",
            })
        
        return targets

    def _build_management(
        self,
        targets: List[Dict[str, Any]],
        direction: str,
        alignment: str,
    ) -> Dict[str, Any]:
        """Build position management rules."""
        rules = {
            "move_stop_to_be_at": None,
            "trail_after": None,
            "cancel_if": "no confirmation in entry zone",
            "time_limit": None,
        }
        
        if len(targets) >= 1:
            rules["move_stop_to_be_at"] = "TP1"
        
        if len(targets) >= 2:
            rules["trail_after"] = "TP2"
        
        # Tighter management for counter-trend
        if alignment == "counter_trend":
            rules["cancel_if"] = "no immediate confirmation"
            rules["time_limit"] = "4 candles in entry zone"
        
        return rules

    def _calculate_rr(
        self,
        entry_plan: Dict[str, Any],
        stop_plan: Dict[str, Any],
        targets: List[Dict[str, Any]],
    ) -> Optional[float]:
        """Calculate risk-reward ratio."""
        avg_entry = entry_plan.get("avg_entry")
        stop = stop_plan.get("price")
        
        if not avg_entry or not stop:
            return None
        
        risk = abs(avg_entry - stop)
        if risk == 0:
            return None
        
        # Use first target for R:R
        if targets:
            tp1 = targets[0].get("price")
            if tp1:
                reward = abs(tp1 - avg_entry)
                return reward / risk
        
        return None

    def _size_factor(self, alignment: str, tradeability: str) -> float:
        """
        Calculate position size factor.
        
        aligned + high → 100%
        aligned → 80%
        mixed → 50%
        counter_trend → 25%
        """
        if alignment == "aligned" and tradeability == "high":
            return 1.0
        if alignment == "aligned":
            return 0.8
        if alignment == "mixed":
            return 0.5
        if alignment == "counter_trend":
            return 0.25
        return 0.0

    def _risk_profile(self, size_factor: float) -> str:
        """Determine risk profile from size factor."""
        if size_factor >= 0.9:
            return "normal"
        if size_factor >= 0.5:
            return "reduced"
        return "speculative"

    def _invalid(self, reason: str, status: str = "no_trade") -> Dict[str, Any]:
        """Return invalid execution plan with status."""
        return {
            "valid": False,
            "status": status,  # 'no_trade' | 'waiting'
            "reason": reason,
            "direction": None,
            "model": None,
            "risk_profile": None,
            "size_factor": 0,
            "entry_plan": None,
            "stop_plan": None,
            "targets": [],
            "management": None,
            "rr": None,
        }


# Factory function
_execution_layer = None

def get_execution_layer() -> ExecutionLayer:
    global _execution_layer
    if _execution_layer is None:
        _execution_layer = ExecutionLayer()
    return _execution_layer
