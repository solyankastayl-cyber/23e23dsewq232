"""
Render Plan Engine - The BRAIN of visualization
================================================
Turns data chaos into a clean trading interface.
KEY PRINCIPLE: 1 graph = 1 setup = 1 story
LOGIC: render_plan = FILTER + PRIORITY + CONTEXT
"""
from __future__ import annotations
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone


class RenderPlanEngine:
    """Builds render_plan from ta_context. Tells frontend EXACTLY what to show."""

    MAX_POI_ZONES = 1
    MAX_LIQUIDITY_EQ = 2
    MAX_LIQUIDITY_SWEEPS = 1
    MAX_SWINGS = 6
    MAX_CHOCH = 1
    MAX_BOS = 1
    MAX_DISPLACEMENT = 1
    MAX_OVERLAYS = 2
    MAX_PANES = 1

    def build(
        self,
        execution: Dict[str, Any],
        primary_pattern: Optional[Dict[str, Any]],
        structure_context: Dict[str, Any],
        liquidity: Dict[str, Any],
        displacement: Dict[str, Any],
        poi: Dict[str, Any],
        indicators: Dict[str, Any],
        current_price: float,
    ) -> Dict[str, Any]:
        """Build render_plan with focused visualization."""
        regime = self._detect_regime(structure_context, displacement)
        focus = self._detect_focus(execution, primary_pattern)

        selected_poi = self._select_poi(poi, current_price)
        selected_liquidity = self._select_liquidity(liquidity)
        simplified_structure = self._simplify_structure(structure_context)
        selected_displacement = self._select_displacement(displacement)
        selected_indicators = self._select_indicators(indicators, regime)

        selected_pattern = None
        if primary_pattern and focus != "structure":
            selected_pattern = self._simplify_pattern(primary_pattern)

        return {
            "execution": self._prepare_execution(execution),
            "pattern": selected_pattern,
            "poi": selected_poi,
            "structure": simplified_structure,
            "liquidity": selected_liquidity,
            "displacement": selected_displacement,
            "indicators": selected_indicators,
            "meta": {
                "regime": regime,
                "focus": focus,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
            "chain_highlight": self._build_chain_highlight(
                execution, selected_liquidity, selected_displacement,
                simplified_structure, selected_poi
            ),
        }

    def _detect_regime(self, structure_context: Dict[str, Any], displacement: Dict[str, Any]) -> str:
        """Detect market regime: trend | range | reversal"""
        trend = structure_context.get("trend", "unknown") if structure_context else "unknown"
        has_choch = bool(structure_context.get("last_choch")) if structure_context else False
        has_displacement = bool(displacement and displacement.get("events"))
        is_range = (structure_context.get("regime") if structure_context else "") in ["range", "compression", "ranging"]

        if has_choch and has_displacement:
            return "reversal"
        if trend in ["uptrend", "downtrend"] and has_displacement:
            return "trend"
        if is_range:
            return "range"
        return "range"

    def _detect_focus(self, execution: Dict[str, Any], pattern: Optional[Dict[str, Any]]) -> str:
        """Detect visualization focus: execution | pattern | structure"""
        if execution and execution.get("valid"):
            return "execution"
        if pattern and pattern.get("type"):
            return "pattern"
        return "structure"

    def _select_poi(self, poi: Dict[str, Any], current_price: float) -> List[Dict[str, Any]]:
        """Select only the closest POI zone to current price."""
        if not poi:
            return []
        zones = poi.get("zones", [])
        if not zones:
            return []

        def zone_distance(z):
            mid = (z.get("price_low", 0) + z.get("price_high", 0)) / 2
            if mid == 0:
                mid = (z.get("lower", 0) + z.get("upper", 0)) / 2
            return abs(mid - current_price) if current_price else 0

        sorted_zones = sorted(zones, key=zone_distance)
        return sorted_zones[:self.MAX_POI_ZONES]

    def _select_liquidity(self, liquidity: Dict[str, Any]) -> Dict[str, Any]:
        """Select limited liquidity data."""
        if not liquidity:
            return {"eq": [], "sweeps": []}
        eq_highs = liquidity.get("eq_highs", [])[:self.MAX_LIQUIDITY_EQ]
        eq_lows = liquidity.get("eq_lows", [])[:self.MAX_LIQUIDITY_EQ]
        sweeps = liquidity.get("sweeps", [])[-self.MAX_LIQUIDITY_SWEEPS:]
        return {
            "eq": eq_highs + eq_lows,
            "sweeps": sweeps,
            "bsl": liquidity.get("bsl"),
            "ssl": liquidity.get("ssl"),
        }

    def _simplify_structure(self, structure_context: Dict[str, Any]) -> Dict[str, Any]:
        """Simplify structure for clean visualization."""
        if not structure_context:
            return {"swings": [], "choch": [], "bos": [], "trend": "unknown", "regime": "unknown", "bias": "neutral"}
        
        swings = structure_context.get("swings", [])
        choch_list = structure_context.get("choch", [])
        bos_list = structure_context.get("bos", [])
        last_choch = structure_context.get("last_choch")
        last_bos = structure_context.get("last_bos")

        return {
            "swings": swings[-self.MAX_SWINGS:] if swings else [],
            "choch": choch_list[-self.MAX_CHOCH:] if choch_list else ([last_choch] if last_choch else []),
            "bos": bos_list[-self.MAX_BOS:] if bos_list else ([last_bos] if last_bos else []),
            "trend": structure_context.get("trend", "unknown"),
            "regime": structure_context.get("regime", "unknown"),
            "bias": structure_context.get("bias", "neutral"),
        }

    def _select_displacement(self, displacement: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Select latest displacement only."""
        if not displacement:
            return []
        events = displacement.get("events", [])
        return events[-self.MAX_DISPLACEMENT:] if events else []

    def _select_indicators(self, indicators: Dict[str, Any], regime: str) -> Dict[str, List[Dict[str, Any]]]:
        """Select regime-appropriate indicators."""
        overlays = indicators.get("overlays", []) if indicators else []
        panes = indicators.get("panes", []) if indicators else []

        if regime == "trend":
            selected_overlays = [ind for ind in overlays if ind.get("type", "").lower() in ["ema_20", "ema_50", "ema", "sma"]][:self.MAX_OVERLAYS]
            return {"overlays": selected_overlays, "panes": []}
        if regime == "range":
            selected_panes = [ind for ind in panes if ind.get("type", "").lower() in ["rsi", "stochastic"]][:self.MAX_PANES]
            return {"overlays": [], "panes": selected_panes}
        # reversal
        selected_overlays = [ind for ind in overlays if ind.get("type", "").lower() in ["ema_20", "ema"]][:1]
        selected_panes = [ind for ind in panes if ind.get("type", "").lower() == "rsi"][:1]
        return {"overlays": selected_overlays, "panes": selected_panes}

    def _simplify_pattern(self, pattern: Dict[str, Any]) -> Dict[str, Any]:
        """Simplify pattern for rendering."""
        return {
            "type": pattern.get("type"),
            "direction_bias": pattern.get("direction_bias", pattern.get("direction")),
            "breakout_level": pattern.get("breakout_level"),
            "invalidation": pattern.get("invalidation"),
            "confidence": pattern.get("confidence"),
            "start_index": pattern.get("start_index"),
            "end_index": pattern.get("end_index"),
            "points": pattern.get("points", []),
        }

    def _prepare_execution(self, execution: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare execution layer for rendering."""
        if not execution:
            return {"valid": False}
        return {
            "valid": execution.get("valid", False),
            "status": execution.get("status", "no_trade"),
            "direction": execution.get("direction"),
            "model": execution.get("model"),
            "risk_profile": execution.get("risk_profile"),
            "size_factor": execution.get("size_factor"),
            "entry_plan": execution.get("entry_plan"),
            "stop_plan": execution.get("stop_plan"),
            "targets": execution.get("targets", []),
            "rr": execution.get("rr"),
        }

    def _build_chain_highlight(
        self,
        execution: Dict[str, Any],
        liquidity: Dict[str, Any],
        displacement: List[Dict[str, Any]],
        structure: Dict[str, Any],
        poi: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Build chain highlight: sweep -> choch -> entry"""
        chain = []
        
        # 1. Sweeps
        sweeps = liquidity.get("sweeps", []) if liquidity else []
        for sweep in sweeps:
            chain.append({
                "step": len(chain) + 1,
                "type": "sweep",
                "label": sweep.get("label", sweep.get("type", "sweep")),
                "direction": sweep.get("direction"),
                "price": sweep.get("price"),
                "candle_index": sweep.get("candle_index"),
            })
        
        # 2. Displacement
        for disp in displacement:
            chain.append({
                "step": len(chain) + 1,
                "type": "displacement",
                "direction": disp.get("direction"),
                "impulse": disp.get("impulse"),
                "start_index": disp.get("start_index"),
                "end_index": disp.get("end_index"),
            })
        
        # 3. CHOCH
        for choch in structure.get("choch", []):
            chain.append({
                "step": len(chain) + 1,
                "type": "choch",
                "direction": choch.get("direction"),
                "price": choch.get("price"),
                "candle_index": choch.get("index") or choch.get("candle_index"),
            })
        
        # 4. POI zone
        for zone in poi:
            chain.append({
                "step": len(chain) + 1,
                "type": "poi",
                "zone_type": zone.get("type"),
                "price_low": zone.get("price_low") or zone.get("lower"),
                "price_high": zone.get("price_high") or zone.get("upper"),
            })
        
        # 5. Entry
        if execution and execution.get("valid"):
            entry_plan = execution.get("entry_plan", {})
            chain.append({
                "step": len(chain) + 1,
                "type": "entry",
                "direction": execution.get("direction"),
                "zone_low": entry_plan.get("zone_low") if entry_plan else None,
                "zone_high": entry_plan.get("zone_high") if entry_plan else None,
                "model": execution.get("model"),
            })
        
        return chain


_render_plan_engine: Optional[RenderPlanEngine] = None


def get_render_plan_engine() -> RenderPlanEngine:
    """Get singleton instance of RenderPlanEngine."""
    global _render_plan_engine
    if _render_plan_engine is None:
        _render_plan_engine = RenderPlanEngine()
    return _render_plan_engine
