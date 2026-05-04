"""
Anchor-Based Pattern Builder v1
===============================

Builds patterns using anchor-first approach (not regression).

Pipeline:
1. Extract swings from candles
2. Select anchors for each pattern type
3. Build boundaries from anchors
4. Validate touches
5. Calculate scores
6. Generate render contract

Key principle:
- NOT regression fitting
- Explicit anchor selection
- Touch validation with reaction checking
- Hard rejection for invalid patterns
"""

from typing import Dict, List, Optional, Tuple
from datetime import datetime, timezone

from .anchor_selector import get_anchor_selector, AnchorSelector
from .boundary_builder import get_boundary_builder, BoundaryBuilder
from .touch_validator import get_touch_validator, TouchValidator


class AnchorBasedPatternBuilder:
    """
    Builds patterns using anchor-based approach.
    
    Replaces regression-based pattern construction.
    """
    
    PATTERN_LABELS = {
        "falling_wedge": "Falling Wedge",
        "rising_wedge": "Rising Wedge",
        "ascending_triangle": "Ascending Triangle",
        "descending_triangle": "Descending Triangle",
        "symmetrical_triangle": "Symmetrical Triangle",
        "ascending_channel": "Ascending Channel",
        "descending_channel": "Descending Channel",
        "horizontal_channel": "Horizontal Channel",
    }
    
    PATTERN_DIRECTIONS = {
        "falling_wedge": "bullish",
        "rising_wedge": "bearish",
        "ascending_triangle": "bullish",
        "descending_triangle": "bearish",
        "symmetrical_triangle": "neutral",
        "ascending_channel": "bullish",
        "descending_channel": "bearish",
        "horizontal_channel": "neutral",
    }
    
    def __init__(
        self,
        min_touch_score: float = 0.40,  # LOWERED: was 0.55, now more patterns pass
        min_render_quality: float = 0.50,  # LOWERED: was 0.65, now more patterns pass
    ):
        self.anchor_selector = get_anchor_selector()
        self.boundary_builder = get_boundary_builder()
        self.touch_validator = get_touch_validator()
        
        self.min_touch_score = min_touch_score
        self.min_render_quality = min_render_quality
    
    def build(self, candles: List[Dict]) -> Optional[Dict]:
        """
        Build best pattern from candles using anchor-based approach.
        
        Returns:
            Render-ready pattern contract or None if no valid pattern found
        """
        if len(candles) < 20:
            return None
        
        # Step 1: Extract swings
        swing_highs, swing_lows = self.anchor_selector.extract_swings(candles, lookback=5)
        
        print(f"[AnchorPattern] Found {len(swing_highs)} swing highs, {len(swing_lows)} swing lows")
        
        if len(swing_highs) < 2 or len(swing_lows) < 2:
            print("[AnchorPattern] Not enough swings")
            return None
        
        # Step 2: Try each pattern type
        candidates = []
        
        # Try falling wedge
        fw_result = self._build_falling_wedge(candles, swing_highs, swing_lows)
        if fw_result:
            candidates.append(fw_result)
        
        # Try ascending triangle
        at_result = self._build_ascending_triangle(candles, swing_highs, swing_lows)
        if at_result:
            candidates.append(at_result)
        
        # Try descending triangle
        dt_result = self._build_descending_triangle(candles, swing_highs, swing_lows)
        if dt_result:
            candidates.append(dt_result)
        
        # Try channel
        ch_result = self._build_channel(candles, swing_highs, swing_lows)
        if ch_result:
            candidates.append(ch_result)
        
        print(f"[AnchorPattern] {len(candidates)} candidate patterns before filtering")
        
        # ═══════════════════════════════════════════════════════════════
        # STEP 3: VISUAL QUALITY FILTER - Kill garbage patterns
        # ═══════════════════════════════════════════════════════════════
        from modules.ta_engine.visual_quality_engine import get_visual_quality_engine
        vq_engine = get_visual_quality_engine()
        
        vq_filtered = []
        for c in candidates:
            vq_result = vq_engine.validate(c)
            
            if vq_result.passed:
                # Add visual quality data
                c["visual_score"] = vq_result.score
                c["visual_breakdown"] = vq_result.breakdown
                vq_filtered.append(c)
                print(f"[AnchorPattern] VQ PASS {c.get('type')}: score={vq_result.score:.2f}")
            else:
                print(f"[AnchorPattern] VQ REJECTED {c.get('type')}: {vq_result.rejection_reason}")
        
        candidates = vq_filtered
        print(f"[AnchorPattern] {len(candidates)} candidates after VQ filtering")
        
        # ═══════════════════════════════════════════════════════════════
        # STEP 4: SCORE FILTERING - More lenient to find patterns in history
        # ═══════════════════════════════════════════════════════════════
        filtered = []
        for c in candidates:
            touch = c.get("touch_score", 0)
            render = c.get("render_quality", 0)
            combined = c.get("combined_score", 0)
            visual = c.get("visual_score", 0)
            
            # LOWERED thresholds: combined >= 0.50 (was 0.65)
            # This allows more patterns through so history scanner can rank them
            if combined >= 0.50 and touch >= self.min_touch_score and render >= self.min_render_quality:
                filtered.append(c)
            else:
                print(f"[AnchorPattern] SCORE REJECTED {c.get('type')}: "
                      f"combined={combined:.2f}, touch={touch:.2f}, render={render:.2f}")
        
        candidates = filtered
        print(f"[AnchorPattern] {len(candidates)} candidates after strict filtering")
        
        if not candidates:
            print("[AnchorPattern] No valid patterns found (all filtered)")
            return None
        
        # ═══════════════════════════════════════════════════════════════
        # STEP 4: RANKING - Sort by combined score
        # ═══════════════════════════════════════════════════════════════
        candidates.sort(key=lambda x: x.get("combined_score", 0), reverse=True)
        
        # Best = primary
        best = candidates[0]
        
        # ═══════════════════════════════════════════════════════════════
        # STEP 6: LIFECYCLE ANALYSIS
        # ═══════════════════════════════════════════════════════════════
        from modules.ta_engine.pattern_lifecycle_engine import get_pattern_lifecycle_engine
        lifecycle_engine = get_pattern_lifecycle_engine()
        
        lifecycle = lifecycle_engine.analyze(best, candles)
        best["lifecycle"] = {
            "stage": lifecycle.stage,
            "completion": lifecycle.completion,
            "breakout_status": lifecycle.breakout_status,
            "invalidation_status": lifecycle.invalidation_status,
            "state_reason": lifecycle.state_reason,
        }
        
        print(f"[AnchorPattern] Lifecycle: {lifecycle.stage} ({lifecycle.completion*100:.0f}% complete)")
        
        # Apply lifecycle-based scoring adjustment
        if lifecycle.stage == "confirmed":
            best["combined_score"] = min(1.0, best.get("combined_score", 0) * 1.1)
        elif lifecycle.stage == "broken":
            best["combined_score"] = best.get("combined_score", 0) * 0.5
        elif lifecycle.stage == "invalidated":
            # Invalidated patterns should be rejected
            print(f"[AnchorPattern] Pattern invalidated, rejecting")
            if len(candidates) > 1:
                best = candidates[1]
                # Re-analyze lifecycle for new best
                lifecycle = lifecycle_engine.analyze(best, candles)
                best["lifecycle"] = {
                    "stage": lifecycle.stage,
                    "completion": lifecycle.completion,
                    "breakout_status": lifecycle.breakout_status,
                    "invalidation_status": lifecycle.invalidation_status,
                    "state_reason": lifecycle.state_reason,
                }
            else:
                return None
        
        # Alternatives = next 2 (if exist and score >= 0.65)
        alternatives = candidates[1:3] if len(candidates) > 1 else []
        
        print(f"[AnchorPattern] PRIMARY: {best.get('type')} score={best.get('combined_score', 0):.2f}")
        for i, alt in enumerate(alternatives):
            print(f"[AnchorPattern] ALT {i+1}: {alt.get('type')} score={alt.get('combined_score', 0):.2f}")
        
        # Add alternatives to result for frontend
        best["_alternatives"] = alternatives
        best["_total_candidates"] = len(candidates)
        
        return best
    
    def build_with_alternatives(self, candles: List[Dict]) -> Tuple[Optional[Dict], List[Dict]]:
        """
        Build primary pattern and alternatives.
        
        Returns:
            (primary_pattern, [alternatives])
        """
        result = self.build(candles)
        if not result:
            return None, []
        
        alternatives = result.pop("_alternatives", [])
        result.pop("_total_candidates", None)
        
        return result, alternatives
    
    # ═══════════════════════════════════════════════════════════════
    # PATTERN-SPECIFIC BUILDERS
    # ═══════════════════════════════════════════════════════════════
    
    def _build_falling_wedge(
        self,
        candles: List[Dict],
        swing_highs: List,
        swing_lows: List
    ) -> Optional[Dict]:
        """Build falling wedge pattern."""
        
        # Select anchors
        anchors = self.anchor_selector.select_falling_wedge_anchors(swing_highs, swing_lows)
        if not anchors:
            return None
        
        # Build boundaries
        upper_line = self.boundary_builder.build_line_from_anchors(anchors["upper_anchors"])
        lower_line = self.boundary_builder.build_line_from_anchors(anchors["lower_anchors"])
        
        if not upper_line or not lower_line:
            return None
        
        # Validate touches
        upper_touches = self.touch_validator.validate_upper_boundary_touches(
            upper_line.to_dict(), candles, anchors["upper_anchors"]
        )
        lower_touches = self.touch_validator.validate_lower_boundary_touches(
            lower_line.to_dict(), candles, anchors["lower_anchors"]
        )
        
        touch_score = self.touch_validator.calculate_touch_score(upper_touches, lower_touches)
        
        print(f"[FallingWedge] touch_score={touch_score:.2f} upper={len(upper_touches)} lower={len(lower_touches)}")
        
        # HARD REJECTION
        if touch_score < self.min_touch_score:
            print(f"[FallingWedge] REJECTED: touch_score {touch_score} < {self.min_touch_score}")
            return None
        
        # Calculate render quality
        render_quality = self._calculate_render_quality(upper_line, lower_line, upper_touches, lower_touches)
        
        if render_quality < self.min_render_quality:
            print(f"[FallingWedge] REJECTED: render_quality {render_quality} < {self.min_render_quality}")
            return None
        
        # Build render contract
        return self._build_render_contract(
            pattern_type="falling_wedge",
            upper_line=upper_line,
            lower_line=lower_line,
            upper_anchors=anchors["upper_anchors"],
            lower_anchors=anchors["lower_anchors"],
            upper_touches=upper_touches,
            lower_touches=lower_touches,
            touch_score=touch_score,
            render_quality=render_quality,
            candles=candles,
        )
    
    def _build_ascending_triangle(
        self,
        candles: List[Dict],
        swing_highs: List,
        swing_lows: List
    ) -> Optional[Dict]:
        """Build ascending triangle pattern."""
        
        anchors = self.anchor_selector.select_ascending_triangle_anchors(swing_highs, swing_lows)
        if not anchors:
            return None
        
        # Upper = horizontal at resistance
        upper_line = self.boundary_builder.build_horizontal_line(anchors["upper_anchors"])
        # Lower = ascending trendline
        lower_line = self.boundary_builder.build_line_from_anchors(anchors["lower_anchors"])
        
        if not upper_line or not lower_line:
            return None
        
        upper_touches = self.touch_validator.validate_upper_boundary_touches(
            upper_line.to_dict(), candles, anchors["upper_anchors"]
        )
        lower_touches = self.touch_validator.validate_lower_boundary_touches(
            lower_line.to_dict(), candles, anchors["lower_anchors"]
        )
        
        touch_score = self.touch_validator.calculate_touch_score(upper_touches, lower_touches)
        
        print(f"[AscTriangle] touch_score={touch_score:.2f}")
        
        if touch_score < self.min_touch_score:
            return None
        
        render_quality = self._calculate_render_quality(upper_line, lower_line, upper_touches, lower_touches)
        
        if render_quality < self.min_render_quality:
            return None
        
        return self._build_render_contract(
            pattern_type="ascending_triangle",
            upper_line=upper_line,
            lower_line=lower_line,
            upper_anchors=anchors["upper_anchors"],
            lower_anchors=anchors["lower_anchors"],
            upper_touches=upper_touches,
            lower_touches=lower_touches,
            touch_score=touch_score,
            render_quality=render_quality,
            candles=candles,
            breakout_price=anchors.get("resistance_level"),
        )
    
    def _build_descending_triangle(
        self,
        candles: List[Dict],
        swing_highs: List,
        swing_lows: List
    ) -> Optional[Dict]:
        """Build descending triangle pattern."""
        
        anchors = self.anchor_selector.select_descending_triangle_anchors(swing_highs, swing_lows)
        if not anchors:
            return None
        
        upper_line = self.boundary_builder.build_line_from_anchors(anchors["upper_anchors"])
        lower_line = self.boundary_builder.build_horizontal_line(anchors["lower_anchors"])
        
        if not upper_line or not lower_line:
            return None
        
        upper_touches = self.touch_validator.validate_upper_boundary_touches(
            upper_line.to_dict(), candles, anchors["upper_anchors"]
        )
        lower_touches = self.touch_validator.validate_lower_boundary_touches(
            lower_line.to_dict(), candles, anchors["lower_anchors"]
        )
        
        touch_score = self.touch_validator.calculate_touch_score(upper_touches, lower_touches)
        
        if touch_score < self.min_touch_score:
            return None
        
        render_quality = self._calculate_render_quality(upper_line, lower_line, upper_touches, lower_touches)
        
        if render_quality < self.min_render_quality:
            return None
        
        return self._build_render_contract(
            pattern_type="descending_triangle",
            upper_line=upper_line,
            lower_line=lower_line,
            upper_anchors=anchors["upper_anchors"],
            lower_anchors=anchors["lower_anchors"],
            upper_touches=upper_touches,
            lower_touches=lower_touches,
            touch_score=touch_score,
            render_quality=render_quality,
            candles=candles,
            breakout_price=anchors.get("support_level"),
        )
    
    def _build_channel(
        self,
        candles: List[Dict],
        swing_highs: List,
        swing_lows: List
    ) -> Optional[Dict]:
        """Build channel pattern."""
        
        anchors = self.anchor_selector.select_channel_anchors(swing_highs, swing_lows)
        if not anchors:
            return None
        
        upper_line = self.boundary_builder.build_line_from_anchors(anchors["upper_anchors"])
        lower_line = self.boundary_builder.build_line_from_anchors(anchors["lower_anchors"])
        
        if not upper_line or not lower_line:
            return None
        
        upper_touches = self.touch_validator.validate_upper_boundary_touches(
            upper_line.to_dict(), candles, anchors["upper_anchors"]
        )
        lower_touches = self.touch_validator.validate_lower_boundary_touches(
            lower_line.to_dict(), candles, anchors["lower_anchors"]
        )
        
        touch_score = self.touch_validator.calculate_touch_score(upper_touches, lower_touches)
        
        if touch_score < self.min_touch_score:
            return None
        
        render_quality = self._calculate_render_quality(upper_line, lower_line, upper_touches, lower_touches)
        
        if render_quality < self.min_render_quality:
            return None
        
        return self._build_render_contract(
            pattern_type=anchors["type"],  # ascending/descending/horizontal_channel
            upper_line=upper_line,
            lower_line=lower_line,
            upper_anchors=anchors["upper_anchors"],
            lower_anchors=anchors["lower_anchors"],
            upper_touches=upper_touches,
            lower_touches=lower_touches,
            touch_score=touch_score,
            render_quality=render_quality,
            candles=candles,
        )
    
    # ═══════════════════════════════════════════════════════════════
    # HELPER METHODS
    # ═══════════════════════════════════════════════════════════════
    
    def _calculate_render_quality(
        self,
        upper_line,
        lower_line,
        upper_touches: List,
        lower_touches: List
    ) -> float:
        """
        Calculate visual render quality score.
        
        Factors:
        - Touch clarity
        - Boundary separation
        - Pattern proportions
        """
        # Touch count contribution
        total_reactions = sum(1 for t in upper_touches + lower_touches if t.is_reaction)
        touch_contrib = min(1.0, total_reactions / 4)  # Max at 4 reactions
        
        # Boundary clarity (both lines defined)
        boundary_contrib = 1.0 if upper_line and lower_line else 0.5
        
        # Separation clarity
        if upper_line and lower_line:
            start_gap = upper_line.start_price - lower_line.start_price
            end_gap = upper_line.end_price - lower_line.end_price
            avg_gap = (start_gap + end_gap) / 2
            avg_price = (upper_line.start_price + lower_line.start_price) / 2
            gap_pct = avg_gap / avg_price if avg_price else 0
            separation_contrib = min(1.0, gap_pct / 0.05)  # 5% gap = max score
        else:
            separation_contrib = 0.5
        
        # Combine
        quality = (touch_contrib * 0.4 + boundary_contrib * 0.3 + separation_contrib * 0.3)
        
        return round(quality, 3)
    
    def _build_render_contract(
        self,
        pattern_type: str,
        upper_line,
        lower_line,
        upper_anchors: List[Dict],
        lower_anchors: List[Dict],
        upper_touches: List,
        lower_touches: List,
        touch_score: float,
        render_quality: float,
        candles: List[Dict],
        breakout_price: float = None,
    ) -> Dict:
        """Build complete render contract."""
        
        # Calculate window from actual anchors
        all_anchors = upper_anchors + lower_anchors
        all_times = [a.get("time", 0) for a in all_anchors]
        all_indices = [a.get("index", 0) for a in all_anchors]
        
        window_start = min(all_times) if all_times else 0
        window_end = max(all_times) if all_times else 0
        start_idx = min(all_indices) if all_indices else 0
        end_idx = max(all_indices) if all_indices else len(candles) - 1
        
        # Build boundaries for render
        upper_boundary = self.boundary_builder.build_render_boundary(
            "upper_boundary", upper_line, "primary"
        )
        lower_boundary = self.boundary_builder.build_render_boundary(
            "lower_boundary", lower_line, "primary"
        )
        
        # Build touch points for render
        touch_points = []
        for t in upper_touches:
            touch_points.append({
                "time": t.time,
                "price": t.price,
                "side": "upper",
                "is_reaction": t.is_reaction,
            })
        for t in lower_touches:
            touch_points.append({
                "time": t.time,
                "price": t.price,
                "side": "lower",
                "is_reaction": t.is_reaction,
            })
        
        # Determine breakout level
        levels = []
        if breakout_price:
            levels.append({
                "id": "breakout_level",
                "kind": "breakout",
                "price": breakout_price,
                "label": "Breakout",
                "start": window_start,
                "end": window_end,
            })
        else:
            # For wedge/channel, use the convergence point or upper boundary
            if pattern_type in ["falling_wedge", "rising_wedge"]:
                levels.append({
                    "id": "breakout_level",
                    "kind": "bullish_breakout" if "falling" in pattern_type else "bearish_breakdown",
                    "price": upper_line.end_price,
                    "label": "Breakout Target",
                    "start": window_start,
                    "end": window_end,
                })
        
        # Combined score
        combined_score = (touch_score * 0.5 + render_quality * 0.5)
        
        # Build boundaries list for top-level (frontend expects this)
        boundaries_list = [b for b in [upper_boundary, lower_boundary] if b]
        
        return {
            "type": pattern_type,
            "label": self.PATTERN_LABELS.get(pattern_type, pattern_type.replace("_", " ").title()),
            "direction": self.PATTERN_DIRECTIONS.get(pattern_type, "neutral"),
            "status": "active",
            "confidence": combined_score,
            "touch_score": touch_score,
            "render_quality": render_quality,
            "combined_score": combined_score,
            # TOP-LEVEL BOUNDARIES for frontend (CRITICAL FIX!)
            "boundaries": boundaries_list,
            "levels": levels,
            "markers": [],  # Add markers at top-level for frontend
            "window": {
                "start_time": window_start,
                "end_time": window_end,
                "start": window_start,
                "end": window_end,
                "start_index": start_idx,
                "end_index": end_idx,
                "candle_count": end_idx - start_idx + 1,
            },
            "anchors": {
                "upper": upper_anchors,
                "lower": lower_anchors,
            },
            "touches": {
                "upper": [{"time": t.time, "price": t.price, "is_reaction": t.is_reaction, "reaction": t.is_reaction} for t in upper_touches],
                "lower": [{"time": t.time, "price": t.price, "is_reaction": t.is_reaction, "reaction": t.is_reaction} for t in lower_touches],
            },
            "slopes": {
                "upper": upper_line.slope if upper_line else 0,
                "lower": lower_line.slope if lower_line else 0,
            },
            "render": {
                "boundaries": boundaries_list,  # Also keep in render for backwards compat
                "levels": levels,
                "touch_points": touch_points,
                "anchors": [  # Anchors for frontend visualization
                    {
                        "time": a.get("time"),
                        "price": a.get("price"),
                        "type": "upper",
                        "strength": 0.8,  # All anchors are strong by definition
                        "reaction": True,
                    }
                    for a in upper_anchors
                ] + [
                    {
                        "time": a.get("time"),
                        "price": a.get("price"),
                        "type": "lower",
                        "strength": 0.8,
                        "reaction": True,
                    }
                    for a in lower_anchors
                ],
                "markers": [],
                "zones": [],
            },
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }


# Singleton
_anchor_pattern_builder = None

def get_anchor_pattern_builder() -> AnchorBasedPatternBuilder:
    """Get anchor-based pattern builder singleton."""
    global _anchor_pattern_builder
    if _anchor_pattern_builder is None:
        _anchor_pattern_builder = AnchorBasedPatternBuilder()
    return _anchor_pattern_builder
