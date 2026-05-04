"""
Visual Mapping Engine
=====================

Converts ta_context (brain) into chart_render_plan (visual).

RULE: If a factor is in top_drivers → it MUST appear on the chart.
Chart = projection of the decision, not random layers.

Pipeline:
  ta_context.top_drivers → render_plan → GraphVisibilityEngine → Chart

Input:  ta_context (from ContributionEngine)
Output: chart_render_plan
"""

from __future__ import annotations
from typing import Any, Dict, List, Optional


# ═══════════════════════════════════════════════════════════════
# DRIVER → VISUAL MAPPING REGISTRY
# ═══════════════════════════════════════════════════════════════
# Each TA source_id maps to its visual representation.
# "overlay" = drawn on main chart (EMA lines, BB bands)
# "pane"    = separate sub-chart (RSI, MACD)
# "zone"    = background region (POI, supply/demand)
# "level"   = horizontal line (fib, S/R, liquidity)
# "marker"  = discrete event (CHOCH, sweep, displacement)

INDICATOR_VISUAL_MAP = {
    # Trend overlays
    "ema_20":     {"type": "overlay", "id": "ema_20",     "label": "EMA 20"},
    "ema_50":     {"type": "overlay", "id": "ema_50",     "label": "EMA 50"},
    "ema_200":    {"type": "overlay", "id": "ema_200",    "label": "EMA 200"},
    "sma_stack":  {"type": "overlay", "id": "ema_20",     "label": "SMA Stack",   "also": ["ema_50", "ema_200"]},
    "bb":         {"type": "overlay", "id": "bollinger_bands", "label": "Bollinger Bands"},
    "vwap":       {"type": "overlay", "id": "vwap",       "label": "VWAP"},
    "vwma":       {"type": "overlay", "id": "ema_20",     "label": "VWMA"},
    "hma":        {"type": "overlay", "id": "ema_20",     "label": "HMA"},
    "kc":         {"type": "overlay", "id": "bollinger_bands", "label": "Keltner Channels"},
    "dc":         {"type": "overlay", "id": "ema_20",     "label": "Donchian"},
    "st":         {"type": "overlay", "id": "ema_20",     "label": "Supertrend"},
    "ichi":       {"type": "overlay", "id": "ema_50",     "label": "Ichimoku"},
    "psar":       {"type": "overlay", "id": "ema_20",     "label": "Parabolic SAR"},

    # Oscillator panes
    "rsi":        {"type": "pane", "id": "rsi",       "label": "RSI"},
    "srsi":       {"type": "pane", "id": "rsi",       "label": "Stoch RSI"},
    "macd":       {"type": "pane", "id": "macd",      "label": "MACD"},
    "stoch":      {"type": "pane", "id": "stochastic","label": "Stochastic"},
    "cci":        {"type": "pane", "id": "rsi",       "label": "CCI"},
    "willr":      {"type": "pane", "id": "rsi",       "label": "Williams %R"},
    "mom":        {"type": "pane", "id": "macd",      "label": "Momentum"},
    "roc":        {"type": "pane", "id": "macd",      "label": "ROC"},
    "trix":       {"type": "pane", "id": "macd",      "label": "TRIX"},
    "adx":        {"type": "pane", "id": "adx",       "label": "ADX"},
    "dmi":        {"type": "pane", "id": "adx",       "label": "DMI"},
    "aroon":      {"type": "pane", "id": "adx",       "label": "Aroon"},

    # Volume panes
    "obv":        {"type": "pane", "id": "volume",    "label": "OBV"},
    "adl":        {"type": "pane", "id": "volume",    "label": "ADL"},
    "cmf":        {"type": "pane", "id": "volume",    "label": "CMF"},
    "vol":        {"type": "pane", "id": "volume",    "label": "Volume"},
    "mfi":        {"type": "pane", "id": "volume",    "label": "MFI"},

    # Volatility (informational — boost overlay)
    "atr":        {"type": "info",  "id": "atr",      "label": "ATR"},
    "bbw":        {"type": "info",  "id": "bbw",      "label": "BB Width"},
    "hv":         {"type": "info",  "id": "hv",       "label": "Hist. Vol"},
}

# Non-indicator sources mapping
SOURCE_VISUAL_MAP = {
    "mtf":           {"type": "info",    "label": "MTF Context"},
    "structure":     {"type": "info",    "label": "Structure Context"},
    "fib":           {"type": "level",   "label": "Fibonacci Levels"},
    "poi":           {"type": "zone",    "label": "POI Zone"},
    "liquidity":     {"type": "level",   "label": "Liquidity Pool"},
    "displacement":  {"type": "marker",  "label": "Displacement"},
    "choch":         {"type": "marker",  "label": "CHOCH"},
    "pattern":       {"type": "overlay", "label": "Pattern"},
}


class VisualMappingEngine:
    """
    Converts ta_context into chart_render_plan.
    
    The render_plan tells the frontend EXACTLY what to show and WHY.
    GraphVisibilityEngine then applies caps/limits on top.
    """

    MAX_OVERLAYS = 3
    MAX_PANES = 2
    MAX_ZONES = 2
    MAX_ANNOTATIONS = 3

    def build(self, ta_context: Dict[str, Any], decision: Dict[str, Any]) -> Dict[str, Any]:
        """
        Build chart render plan from ta_context and decision.
        
        Returns:
        {
            "overlays": ["ema_20", "ema_50", "bollinger_bands"],
            "panes": ["rsi", "volume"],
            "show_fib": true,
            "show_poi": true,
            "show_liquidity": true,
            "show_choch": false,
            "show_displacement": true,
            "annotations": [
                {"type": "divergence", "indicator": "RSI", "reason": "RSI divergence..."},
                {"type": "sweep", "side": "BSL", "reason": "BSL Pool bearish..."}
            ],
            "reason_map": {
                "ema_20": "EMA Stack: SMA 20 > 50 > 200 — bullish alignment",
                "rsi": "RSI oversold at 28 — potential reversal",
                "poi": "Supply Zone: price in distribution zone",
                "fib": "Fibonacci: price near 61.8% retracement"
            },
            "driver_count": 7,
            "visual_summary": "Chart shows 3 overlays, 2 panes, 1 zone — driven by 7 top factors"
        }
        """
        top_drivers = ta_context.get("top_drivers", [])
        all_contributions = ta_context.get("all_contributions", [])
        decision_bias = decision.get("bias", "neutral") if decision else "neutral"

        # Build lookup for contribution details
        contrib_lookup = {}
        for c in all_contributions:
            key = c.get("source_id", c.get("name", "").lower())
            contrib_lookup[key] = c

        # Collect visual elements from top drivers
        overlays = []       # indicator IDs for main chart
        panes = []          # indicator IDs for sub-panes
        annotations = []    # markers / events
        reason_map = {}     # element → why it's shown
        show_fib = False
        show_poi = False
        show_liquidity = False
        show_choch = False
        show_displacement = False

        seen_overlays = set()
        seen_panes = set()

        for driver in top_drivers:
            name = driver.get("name", "")
            source = driver.get("source", "")
            source_id = driver.get("source_id", name.lower().replace(" ", "_"))
            signal = driver.get("signal", "neutral")
            score = driver.get("score", 0)
            description = driver.get("description", "")
            impact = driver.get("impact", 0)

            reason_text = description or f"{name}: {signal} (score={score:+.3f}, impact={impact*100:.1f}%)"

            # Try indicator visual map first
            ind_key = source_id.lower()
            if ind_key in INDICATOR_VISUAL_MAP:
                vis = INDICATOR_VISUAL_MAP[ind_key]
                vis_type = vis["type"]
                vis_id = vis["id"]

                if vis_type == "overlay" and vis_id not in seen_overlays:
                    overlays.append(vis_id)
                    seen_overlays.add(vis_id)
                    reason_map[vis_id] = reason_text
                    # Add 'also' overlays (e.g., SMA stack → ema_20 + ema_50 + ema_200)
                    for also_id in vis.get("also", []):
                        if also_id not in seen_overlays:
                            overlays.append(also_id)
                            seen_overlays.add(also_id)

                elif vis_type == "pane" and vis_id not in seen_panes:
                    panes.append(vis_id)
                    seen_panes.add(vis_id)
                    reason_map[vis_id] = reason_text

                elif vis_type == "info":
                    # Informational — doesn't need visual but noted
                    reason_map[vis_id] = reason_text
                continue

            # Non-indicator sources
            if source == "fib" or "fib" in name.lower():
                show_fib = True
                reason_map["fib"] = reason_text

            elif source == "poi" or "supply" in name.lower() or "demand" in name.lower():
                show_poi = True
                poi_type = "supply" if "supply" in name.lower() else "demand"
                annotations.append({
                    "type": "zone",
                    "subtype": poi_type,
                    "reason": reason_text,
                })
                reason_map["poi"] = reason_text

            elif source == "liquidity" or "bsl" in name.lower() or "ssl" in name.lower():
                show_liquidity = True
                liq_side = "bsl" if "bsl" in name.lower() else "ssl"
                annotations.append({
                    "type": "liquidity",
                    "subtype": liq_side,
                    "reason": reason_text,
                })
                reason_map["liquidity"] = reason_text

            elif source == "choch" or "choch" in name.lower():
                show_choch = True
                reason_map["choch"] = reason_text

            elif source == "displacement" or "displacement" in name.lower():
                show_displacement = True
                annotations.append({
                    "type": "displacement",
                    "reason": reason_text,
                })
                reason_map["displacement"] = reason_text

            elif source == "mtf" or source == "structure":
                reason_map[source] = reason_text

        # ═══════════════════════════════════════════════════════════════
        # APPLY CAPS (Graph can't be overloaded)
        # ═══════════════════════════════════════════════════════════════
        overlays = overlays[:self.MAX_OVERLAYS]
        panes = panes[:self.MAX_PANES]
        annotations = annotations[:self.MAX_ANNOTATIONS]

        # ═══════════════════════════════════════════════════════════════
        # ENSURE MINIMUM VISIBILITY
        # ═══════════════════════════════════════════════════════════════
        # If no overlays from top_drivers, add EMA based on trend
        if not overlays:
            overlays = ["ema_20", "ema_50"]
            reason_map["ema_20"] = "Default: trend reference"

        # If no panes from top_drivers, add RSI (universal)
        if not panes:
            panes = ["rsi"]
            reason_map["rsi"] = "Default: momentum reference"

        # Count visuals
        visual_count = len(overlays) + len(panes) + (1 if show_fib else 0) + (1 if show_poi else 0) + (1 if show_liquidity else 0)

        return {
            "overlays": overlays,
            "panes": panes,
            "show_fib": show_fib,
            "show_poi": show_poi,
            "show_liquidity": show_liquidity,
            "show_choch": show_choch,
            "show_displacement": show_displacement,
            "annotations": annotations,
            "reason_map": reason_map,
            "driver_count": len(top_drivers),
            "visual_count": visual_count,
            "visual_summary": f"Chart shows {len(overlays)} overlays, {len(panes)} panes, {len(annotations)} annotations — driven by {len(top_drivers)} top factors",
        }


# Singleton
_engine: Optional[VisualMappingEngine] = None

def get_visual_mapping_engine() -> VisualMappingEngine:
    global _engine
    if _engine is None:
        _engine = VisualMappingEngine()
    return _engine
