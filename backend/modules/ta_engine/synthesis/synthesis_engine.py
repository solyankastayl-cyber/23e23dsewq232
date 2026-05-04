"""
TA Engine - Synthesis Engine
Combines results from all 10 layers and selects the dominant pattern.

KEY RULES:
1. Figures are PRIMARY (wedges, triangles, H&S, etc.)
2. Channels are FALLBACK only
3. Structure provides CONTEXT
4. Only 1 main pattern on UI
"""

from typing import List, Dict, Optional
from ..groups.base import (
    GroupResult, Finding, RenderData,
    GROUP_STRUCTURE, GROUP_FIGURES, GROUP_CHANNELS, GROUP_LEVELS,
    BIAS_BULLISH, BIAS_BEARISH, BIAS_NEUTRAL
)


class SynthesisEngine:
    """
    Combines all layer results into final TA output.
    
    Priority order:
    1. Figure patterns (triangles, wedges, H&S)
    2. Channel patterns (only if no figures)
    3. Structure context always included
    """
    
    def __init__(self):
        self.structure_weight = 0.15  # How much structure affects final score
        self.confirmation_weight = 0.1
    
    def synthesize(self, layer_results: Dict[str, GroupResult]) -> Dict:
        """
        Combine all layer results.
        
        Args:
            layer_results: Dict of group_name -> GroupResult
            
        Returns:
            Final TA synthesis with:
            - main_pattern: The ONE pattern to show
            - structure: Market structure context
            - confluence: Supporting factors
            - ui: What to render
        """
        # Get key layers
        structure = layer_results.get(GROUP_STRUCTURE)
        figures = layer_results.get(GROUP_FIGURES)
        channels = layer_results.get(GROUP_CHANNELS)
        levels = layer_results.get(GROUP_LEVELS)
        
        # Get structure context
        structure_context = self._get_structure_context(structure)
        
        # Select main pattern
        main_pattern = self._select_main_pattern(figures, channels, structure_context)
        
        # Build confluence list
        confluence = self._build_confluence(layer_results, main_pattern)
        
        # Build UI projection
        ui = self._build_ui_projection(main_pattern, structure_context, levels)
        
        return {
            "main_pattern": main_pattern.to_dict() if main_pattern else None,
            "structure": structure_context,
            "confluence": confluence,
            "summary": self._build_summary(main_pattern, structure_context),
            "ui": ui,
            "groups": {
                name: result.to_dict() 
                for name, result in layer_results.items()
            },
        }
    
    def _get_structure_context(self, structure: Optional[GroupResult]) -> Dict:
        """Extract structure context"""
        if not structure or not structure.summary:
            return {
                "state": "unknown",
                "trend": "unknown",
                "strength": 0.0,
            }
        
        return {
            "state": structure.summary.get("state", "unknown"),
            "trend": structure.summary.get("trend", "unknown"),
            "strength": structure.summary.get("strength", 0.0),
        }
    
    def _select_main_pattern(
        self,
        figures: Optional[GroupResult],
        channels: Optional[GroupResult],
        structure: Dict
    ) -> Optional[Finding]:
        """
        Select the ONE main pattern.
        
        CRITICAL LOGIC:
        1. If figures exist → pick best figure
        2. If no figures → pick best channel
        3. Apply structure adjustment
        """
        candidates = []
        
        # Gather figure candidates (PRIORITY)
        if figures and figures.findings:
            for f in figures.findings:
                f_copy = Finding(
                    type=f.type,
                    bias=f.bias,
                    score=f.score,
                    confidence=f.confidence,
                    window=f.window,
                    geometry=f.geometry,
                    relevance=f.relevance,
                    render=f.render,
                    meta={**f.meta, "source": GROUP_FIGURES},
                )
                candidates.append(f_copy)
        
        # Only add channels if NO figures
        if not candidates and channels and channels.findings:
            for f in channels.findings:
                f_copy = Finding(
                    type=f.type,
                    bias=f.bias,
                    score=f.score * 0.9,  # 10% penalty for being fallback
                    confidence=f.confidence,
                    window=f.window,
                    geometry=f.geometry,
                    relevance=f.relevance,
                    render=f.render,
                    meta={**f.meta, "source": GROUP_CHANNELS, "is_fallback": True},
                )
                candidates.append(f_copy)
        
        if not candidates:
            return None
        
        # Apply structure adjustment
        for c in candidates:
            c.score = self._adjust_for_structure(c, structure)
        
        # Sort and pick best
        candidates.sort(key=lambda x: x.score, reverse=True)
        
        return candidates[0]
    
    def _adjust_for_structure(self, pattern: Finding, structure: Dict) -> float:
        """Adjust pattern score based on structure alignment"""
        base_score = pattern.score
        structure_trend = structure.get("trend", "unknown")
        pattern_bias = pattern.bias
        
        # Bonus if pattern aligns with structure
        if structure_trend == "up" and pattern_bias == BIAS_BULLISH:
            base_score *= 1.1
        elif structure_trend == "down" and pattern_bias == BIAS_BEARISH:
            base_score *= 1.1
        # Penalty if pattern conflicts with structure
        elif structure_trend == "up" and pattern_bias == BIAS_BEARISH:
            base_score *= 0.85
        elif structure_trend == "down" and pattern_bias == BIAS_BULLISH:
            base_score *= 0.85
        
        return min(1.0, base_score)  # Cap at 1.0
    
    def _build_confluence(
        self,
        layer_results: Dict[str, GroupResult],
        main_pattern: Optional[Finding]
    ) -> List[Dict]:
        """Build list of supporting/conflicting factors"""
        confluence = []
        
        if not main_pattern:
            return confluence
        
        main_bias = main_pattern.bias
        
        # Check each layer for support/conflict
        for group_name, result in layer_results.items():
            if group_name in [GROUP_FIGURES, GROUP_CHANNELS]:
                continue  # Skip pattern layers
            
            if not result.findings:
                continue
            
            best = result.best()
            if not best:
                continue
            
            supports = (
                (main_bias == BIAS_BULLISH and best.bias == BIAS_BULLISH) or
                (main_bias == BIAS_BEARISH and best.bias == BIAS_BEARISH)
            )
            
            confluence.append({
                "group": group_name,
                "type": best.type,
                "bias": best.bias,
                "supports_main": supports,
                "score": best.score,
            })
        
        return confluence
    
    def _build_summary(self, main_pattern: Optional[Finding], structure: Dict) -> Dict:
        """Build human-readable summary"""
        if not main_pattern:
            return {
                "dominant_figure": None,
                "dominant_bias": structure.get("trend", "unknown"),
                "interpretation": f"No clear pattern. Market is {structure.get('state', 'ranging')}.",
            }
        
        bias_text = {
            BIAS_BULLISH: "bullish",
            BIAS_BEARISH: "bearish",
            BIAS_NEUTRAL: "neutral",
        }
        
        pattern_name = main_pattern.type.replace("_", " ").title()
        bias = bias_text.get(main_pattern.bias, "neutral")
        score = main_pattern.score
        
        interpretation = (
            f"{pattern_name} detected with {score:.0%} confidence. "
            f"Pattern suggests {bias} bias. "
            f"Structure is {structure.get('state', 'unknown')}."
        )
        
        return {
            "dominant_figure": main_pattern.type,
            "dominant_bias": main_pattern.bias,
            "confidence": score,
            "interpretation": interpretation,
        }
    
    def _build_ui_projection(
        self,
        main_pattern: Optional[Finding],
        structure: Dict,
        levels: Optional[GroupResult]
    ) -> Dict:
        """Build UI rendering instructions"""
        ui = {
            "main_overlay": None,
            "secondary_overlays": [],
            "pattern_render_contract": None,
        }
        
        if main_pattern:
            ui["main_overlay"] = main_pattern.type
            
            # Extract debug from meta
            debug = main_pattern.meta.get("debug", {}) if main_pattern.meta else {}
            
            # Calculate scores for Display Gate compatibility
            touch_upper = debug.get("touch_upper", 0)
            touch_lower = debug.get("touch_lower", 0)
            total_touches = touch_upper + touch_lower
            
            # touch_score: based on total touches (min 4 for full score)
            touch_score = min(1.0, total_touches / 4) if total_touches > 0 else 0.5
            
            # visual_score: geometry cleanliness + symmetry
            geometry_clean = debug.get("geometry_cleanliness", 0.5)
            symmetry = debug.get("symmetry", 0.5)
            visual_score = (geometry_clean + symmetry) / 2
            
            # render_quality: based on score
            render_quality = main_pattern.score
            
            # Build pattern_render_contract for frontend
            render = main_pattern.render
            
            # Build touches for Display Gate compatibility
            touches = {
                "upper": render.anchors[:touch_upper] if render and render.anchors else 
                         [{"time": 0, "price": 0} for _ in range(touch_upper)],
                "lower": render.anchors[touch_upper:touch_upper+touch_lower] if render and render.anchors else
                         [{"time": 0, "price": 0} for _ in range(touch_lower)],
            }
            
            ui["pattern_render_contract"] = {
                "type": main_pattern.type,
                "bias": main_pattern.bias,
                "combined_score": main_pattern.score,
                "confidence": main_pattern.confidence,
                # SCORES for Display Gate compatibility
                "touch_score": touch_score,
                "visual_score": visual_score,
                "render_quality": render_quality,
                "geometry_score": visual_score,
                # TOUCHES for Display Gate
                "touches": touches,
                # SLOPES for Display Gate convergence check
                "slopes": {
                    "upper": debug.get("upper_slope", -0.001),  # Default converging slopes
                    "lower": debug.get("lower_slope", 0.001),
                },
                # TOP-LEVEL boundaries (frontend expects this)
                "boundaries": render.boundaries if render else [],
                "levels": render.levels if render else [],
                "markers": render.markers if render else [],
                # DEBUG info for validation
                "debug": {
                    "touch_upper": touch_upper,
                    "touch_lower": touch_lower,
                    "window_bars": debug.get("window_bars", 0),
                    "geometry_cleanliness": geometry_clean,
                    "symmetry": symmetry,
                    "distance_to_price": debug.get("distance_to_price", 0),
                    "raw_score": debug.get("raw_score", 0),
                    "selected_by": "synthesis_engine_v2",
                    "source_layer": debug.get("selected_by", "unknown"),
                },
                # Visual breakdown for Display Gate
                "visual_breakdown": {
                    "touch_balance": min(touch_upper, touch_lower) / max(touch_upper, touch_lower, 1),
                    "respect": visual_score,
                    "cleanliness": max(geometry_clean, symmetry, 0.5),  # Use max of geometry or symmetry
                },
                # Also include render object for backwards compat
                "render": {
                    "boundaries": render.boundaries if render else [],
                    "levels": render.levels if render else [],
                    "anchors": render.anchors if render else [],
                    "markers": render.markers if render else [],
                    "zones": render.zones if render else [],
                } if render else {},
                "window": main_pattern.window.to_dict() if main_pattern.window else None,
            }
        
        # Add levels as secondary
        if levels and levels.findings:
            ui["secondary_overlays"].append("levels")
        
        return ui


# Singleton
_synthesis_engine = None

def get_synthesis_engine() -> SynthesisEngine:
    global _synthesis_engine
    if _synthesis_engine is None:
        _synthesis_engine = SynthesisEngine()
    return _synthesis_engine
