"""
Pattern Selection Engine (PSE) v2.0
====================================

Production-ready pattern selection with multi-stage filtering.

Pipeline:
1. candidate generation (from detectors)
2. hard gating (kill garbage immediately)
3. local relevance gating (recency, proximity)
4. geometry quality scoring
5. market-context fit scoring
6. conflict resolution (dedupe overlapping patterns)
7. final winner selection

Key principle: BETTER TO SHOW 0 PATTERNS THAN 1 BAD PATTERN.
"""

from typing import List, Optional, Tuple, Dict, Any
from .pattern_candidate import PatternCandidate


class PatternSelector:
    """
    Pattern Selection Engine v2.0 — cascade filtering for selecting ONE best pattern.
    
    Stages:
    1. Hard gates - reject garbage immediately
    2. Geometry score - shape quality
    3. Context score - market fit
    4. Relevance score - recency and proximity
    5. Final score - weighted combination
    6. Conflict resolution - dedupe overlapping
    7. Winner selection - with gap check
    """
    
    # ═══════════════════════════════════════════════════════════════
    # THRESHOLDS — Strict to avoid garbage
    # ═══════════════════════════════════════════════════════════════
    
    MIN_TOUCHES = 4              # Minimum pivot points
    MIN_SPAN = 12                # Minimum candles span
    MIN_CONTAINMENT = 0.65       # % of candles inside pattern
    MIN_GEOMETRY_SCORE = 0.62    # Shape quality threshold
    MIN_CONTEXT_SCORE = 0.50     # Market fit threshold  
    MIN_RELEVANCE_SCORE = 0.60   # Recency/proximity threshold
    MIN_FINAL_SCORE = 0.68       # Overall threshold
    MIN_WINNER_GAP = 0.05        # Gap between top-1 and top-2
    
    # Score weights for final score
    WEIGHT_GEOMETRY = 0.40
    WEIGHT_CONTEXT = 0.25
    WEIGHT_RELEVANCE = 0.25
    WEIGHT_CLARITY = 0.10
    
    # ═══════════════════════════════════════════════════════════════
    # FORBIDDEN PATTERN TYPES — belong to MARKET STATE, not patterns
    # ═══════════════════════════════════════════════════════════════
    FORBIDDEN_AS_PATTERN = {
        "horizontal_channel", "ascending_channel", "descending_channel",
        "channel", "range", "sideways", "trend", "uptrend", "downtrend",
        "compression", "expansion",
    }
    
    # Pattern specificity ranking (higher = more specific, prefer over generic)
    SPECIFICITY_RANK = {
        "head_shoulders": 10,
        "inverse_head_shoulders": 10,
        "head_and_shoulders": 10,
        "inverse_head_and_shoulders": 10,
        "double_top": 9,
        "double_bottom": 9,
        "triple_top": 9,
        "triple_bottom": 9,
        "ascending_triangle": 8,
        "descending_triangle": 8,
        "symmetrical_triangle": 7,
        "rising_wedge": 7,
        "falling_wedge": 7,
        "bull_flag": 6,
        "bear_flag": 6,
        "pennant": 6,
        "rectangle": 5,
        "range": 4,
        "breakout_up": 3,
        "breakdown": 3,
    }
    
    def __init__(self):
        pass
    
    # ═══════════════════════════════════════════════════════════════
    # STAGE 1: HARD GATING — Kill garbage immediately
    # ═══════════════════════════════════════════════════════════════
    
    def _passes_hard_gates(self, candidate: PatternCandidate, candles: List[Dict]) -> bool:
        """
        Hard gates - reject garbage before any scoring.
        
        Checks:
        1. Not forbidden pattern type
        2. Minimum touches
        3. Minimum span
        4. Valid point order
        5. Minimum containment
        """
        if not candidate:
            return False
        
        pattern_type = (candidate.type or "").lower().replace(" ", "_").replace("-", "_")
        
        # 1. Forbidden type check
        if pattern_type in self.FORBIDDEN_AS_PATTERN:
            print(f"[PatternSelector] HARD_GATE: {pattern_type} is forbidden (market_state)")
            return False
        
        for keyword in ["channel", "trend", "sideways"]:
            if keyword in pattern_type:
                print(f"[PatternSelector] HARD_GATE: {pattern_type} contains forbidden keyword")
                return False
        
        # 2. Minimum touches
        touches = candidate.touches or 0
        anchor_count = 0
        if candidate.anchor_points:
            # anchor_points can be dict or list depending on pattern type
            if isinstance(candidate.anchor_points, dict):
                for side, pts in candidate.anchor_points.items():
                    if isinstance(pts, list):
                        anchor_count += len(pts)
                    elif isinstance(pts, (int, float)):
                        anchor_count += 1  # Single point
                    elif isinstance(pts, tuple):
                        anchor_count += 1
            elif isinstance(candidate.anchor_points, list):
                anchor_count = len(candidate.anchor_points)
        touches = max(touches, anchor_count)
        
        if touches < self.MIN_TOUCHES:
            print(f"[PatternSelector] HARD_GATE: {pattern_type} only {touches} touches < {self.MIN_TOUCHES}")
            return False
        
        # 3. Minimum span
        start_idx = candidate.start_index or 0
        end_idx = candidate.end_index or (len(candles) - 1 if candles else 0)
        span = end_idx - start_idx
        
        if span < self.MIN_SPAN:
            print(f"[PatternSelector] HARD_GATE: {pattern_type} span {span} < {self.MIN_SPAN}")
            return False
        
        # 4. Containment check (if available)
        containment = candidate.containment or 0.7  # Default assume OK
        if containment < self.MIN_CONTAINMENT:
            print(f"[PatternSelector] HARD_GATE: {pattern_type} containment {containment:.2f} < {self.MIN_CONTAINMENT}")
            return False
        
        return True
    
    # ═══════════════════════════════════════════════════════════════
    # STAGE 2: GEOMETRY QUALITY SCORING
    # ═══════════════════════════════════════════════════════════════
    
    def _compute_geometry_score(self, candidate: PatternCandidate, candles: List[Dict]) -> float:
        """
        Compute geometry quality score.
        
        Components:
        - fit_score: how well points fit the lines (30%)
        - shape_validity: does shape match pattern type (30%)
        - containment: % of candles inside boundaries (20%)
        - symmetry: balance/symmetry of pattern (10%)
        - breakout_clarity: clear breakout level (10%)
        """
        scores = candidate.scores or {}
        
        # Get individual scores from detector or compute defaults
        fit_score = scores.get("geometry", scores.get("fit", 0.7))
        shape_score = scores.get("shape_validity", 0.7)
        containment = candidate.containment or 0.7
        symmetry = scores.get("symmetry", 0.7)
        cleanliness = scores.get("cleanliness", scores.get("breakout_clarity", 0.7))
        
        # Also use line_scores if available
        line_scores = candidate.line_scores or {}
        if line_scores:
            upper_score = line_scores.get("upper", 0) / 50  # Normalize
            lower_score = line_scores.get("lower", 0) / 50
            fit_score = max(fit_score, (upper_score + lower_score) / 2)
        
        geometry_score = (
            fit_score * 0.30 +
            shape_score * 0.30 +
            containment * 0.20 +
            symmetry * 0.10 +
            cleanliness * 0.10
        )
        
        return min(1.0, max(0.0, geometry_score))
    
    # ═══════════════════════════════════════════════════════════════
    # STAGE 3: CONTEXT FIT SCORING
    # ═══════════════════════════════════════════════════════════════
    
    def _compute_context_score(
        self, 
        candidate: PatternCandidate, 
        market_state: Dict[str, Any],
        structure: Dict[str, Any],
        levels: List[Dict]
    ) -> float:
        """
        Compute market context fit score.
        
        Components:
        - regime_fit: does pattern match market regime (30%)
        - structure_fit: aligns with HH/HL/LH/LL (30%)
        - level_fit: pattern at key levels (20%)
        - volatility_fit: appropriate volatility (10%)
        - volume_fit: volume confirmation (10%)
        """
        pattern_type = (candidate.type or "").lower()
        direction = (candidate.direction or "").lower()
        
        # Regime fit
        regime = (market_state.get("regime") or "unknown").lower() if market_state else "unknown"
        bias = (market_state.get("bias") or "neutral").lower() if market_state else "neutral"
        
        regime_fit = 0.5  # Default neutral
        
        # Bullish patterns prefer bullish/accumulation context
        if direction == "bullish":
            if bias in ["bullish", "accumulation"]:
                regime_fit = 0.9
            elif bias == "neutral":
                regime_fit = 0.6
            else:
                regime_fit = 0.3
        # Bearish patterns prefer bearish/distribution context
        elif direction == "bearish":
            if bias in ["bearish", "distribution"]:
                regime_fit = 0.9
            elif bias == "neutral":
                regime_fit = 0.6
            else:
                regime_fit = 0.3
        
        # Structure fit
        structure_fit = 0.5
        if structure:
            trend_score = structure.get("trend_score", 0)
            # Bullish patterns prefer uptrend structure
            if direction == "bullish" and trend_score > 0:
                structure_fit = 0.7 + trend_score * 0.3
            elif direction == "bearish" and trend_score < 0:
                structure_fit = 0.7 + abs(trend_score) * 0.3
            else:
                structure_fit = 0.5
        
        # Level fit - pattern near key levels
        level_fit = 0.5
        breakout = candidate.breakout_level
        invalidation = candidate.invalidation
        if levels and (breakout or invalidation):
            for lvl in levels:
                lvl_price = lvl.get("price", 0)
                if breakout and abs(breakout - lvl_price) / max(breakout, 1) < 0.02:
                    level_fit = 0.9
                    break
                if invalidation and abs(invalidation - lvl_price) / max(invalidation, 1) < 0.02:
                    level_fit = 0.8
                    break
        
        # Volatility and volume (use defaults if not available)
        volatility_fit = 0.7
        volume_fit = 0.7
        
        context_score = (
            regime_fit * 0.30 +
            structure_fit * 0.30 +
            level_fit * 0.20 +
            volatility_fit * 0.10 +
            volume_fit * 0.10
        )
        
        return min(1.0, max(0.0, context_score))
    
    # ═══════════════════════════════════════════════════════════════
    # STAGE 4: RELEVANCE SCORING
    # ═══════════════════════════════════════════════════════════════
    
    def _compute_relevance_score(
        self,
        candidate: PatternCandidate,
        candles: List[Dict],
        current_price: float
    ) -> float:
        """
        Compute relevance score - how important is pattern NOW.
        
        Components:
        - recency_score: ends near right edge (45%)
        - proximity_score: near current price (35%)
        - active_status: not expired/broken (20%)
        """
        total_candles = len(candles) if candles else 1
        end_idx = candidate.end_index or total_candles - 1
        
        # Recency: pattern should end near right edge
        recency = end_idx / total_candles if total_candles > 0 else 0
        recency_score = candidate.recency_score or recency
        
        # Proximity: key levels near current price
        proximity_score = 0.5
        if current_price and current_price > 0:
            breakout = candidate.breakout_level
            invalidation = candidate.invalidation
            
            best_distance = 1.0
            if breakout:
                dist = abs(breakout - current_price) / current_price
                best_distance = min(best_distance, dist)
            if invalidation:
                dist = abs(invalidation - current_price) / current_price
                best_distance = min(best_distance, dist)
            
            # Convert distance to score (closer = higher)
            if best_distance < 0.01:
                proximity_score = 1.0
            elif best_distance < 0.02:
                proximity_score = 0.9
            elif best_distance < 0.05:
                proximity_score = 0.7
            elif best_distance < 0.10:
                proximity_score = 0.5
            elif best_distance < 0.15:
                proximity_score = 0.3
            else:
                proximity_score = 0.1
        
        # Active status
        active_score = 0.8 if candidate.status in ["active", "forming", None] else 0.4
        
        relevance_score = (
            recency_score * 0.45 +
            proximity_score * 0.35 +
            active_score * 0.20
        )
        
        return min(1.0, max(0.0, relevance_score))
    
    # ═══════════════════════════════════════════════════════════════
    # STAGE 5: CLARITY SCORING
    # ═══════════════════════════════════════════════════════════════
    
    def _compute_clarity_score(self, candidate: PatternCandidate) -> float:
        """
        Compute clarity score - how visually clear is the pattern.
        
        Components:
        - touches: more touches = clearer (40%)
        - symmetry: balanced shape (30%)
        - cleanliness: not noisy (30%)
        """
        scores = candidate.scores or {}
        
        touches = candidate.touches or 4
        touch_score = min(1.0, touches / 8)  # Normalize to 8 max
        
        symmetry = scores.get("symmetry", 0.7)
        cleanliness = scores.get("cleanliness", 0.7)
        
        clarity_score = (
            touch_score * 0.40 +
            symmetry * 0.30 +
            cleanliness * 0.30
        )
        
        return min(1.0, max(0.0, clarity_score))
    
    # ═══════════════════════════════════════════════════════════════
    # STAGE 6: CONFLICT RESOLUTION
    # ═══════════════════════════════════════════════════════════════
    
    def _dedupe_overlapping_patterns(self, candidates: List[PatternCandidate]) -> List[PatternCandidate]:
        """
        Remove overlapping patterns, keeping the most specific one.
        
        Two patterns overlap if they share >70% of the same range.
        """
        if len(candidates) <= 1:
            return candidates
        
        # Sort by specificity (higher = better) then by final_score
        def sort_key(c):
            pattern_type = (c.type or "").lower().replace(" ", "_").replace("-", "_")
            specificity = self.SPECIFICITY_RANK.get(pattern_type, 5)
            return (specificity, c.final_score or 0)
        
        sorted_candidates = sorted(candidates, key=sort_key, reverse=True)
        
        result = []
        for candidate in sorted_candidates:
            # Check if overlaps with any already selected
            overlaps = False
            c_start = candidate.start_index or 0
            c_end = candidate.end_index or 100
            c_range = c_end - c_start
            
            for selected in result:
                s_start = selected.start_index or 0
                s_end = selected.end_index or 100
                
                # Calculate overlap
                overlap_start = max(c_start, s_start)
                overlap_end = min(c_end, s_end)
                overlap = max(0, overlap_end - overlap_start)
                
                if c_range > 0 and overlap / c_range > 0.70:
                    overlaps = True
                    break
            
            if not overlaps:
                result.append(candidate)
        
        return result
    
    # ═══════════════════════════════════════════════════════════════
    # MAIN SELECTION METHOD
    # ═══════════════════════════════════════════════════════════════
    
    def select(
        self,
        candidates: List[PatternCandidate],
        candles: List[Dict] = None,
        current_price: float = None,
        market_state: Dict[str, Any] = None,
        structure_context: Dict[str, Any] = None,
        levels: List[Dict] = None,
        liquidity: Dict[str, Any] = None,
        fib: Dict[str, Any] = None,
        poi: Dict[str, Any] = None,
    ) -> Tuple[Optional[PatternCandidate], List[PatternCandidate]]:
        """
        Select primary pattern using cascade filtering.
        
        Returns:
            (primary, alternatives) tuple
            primary is None if nothing qualifies
        """
        if not candidates:
            print("[PatternSelector] No candidates provided")
            return None, []
        
        candles = candles or []
        survivors = []
        
        print(f"[PatternSelector] Starting with {len(candidates)} candidates")
        
        for c in candidates:
            # Stage 1: Hard gates
            if not self._passes_hard_gates(c, candles):
                continue
            
            # Stage 2: Geometry score
            c.geometry_score = self._compute_geometry_score(c, candles)
            if c.geometry_score < self.MIN_GEOMETRY_SCORE:
                print(f"[PatternSelector] REJECT {c.type}: geometry_score {c.geometry_score:.2f} < {self.MIN_GEOMETRY_SCORE}")
                continue
            
            # Stage 3: Context score
            c.context_score = self._compute_context_score(c, market_state, structure_context, levels)
            if c.context_score < self.MIN_CONTEXT_SCORE:
                print(f"[PatternSelector] REJECT {c.type}: context_score {c.context_score:.2f} < {self.MIN_CONTEXT_SCORE}")
                continue
            
            # Stage 4: Relevance score
            c.relevance_score = self._compute_relevance_score(c, candles, current_price)
            if c.relevance_score < self.MIN_RELEVANCE_SCORE:
                print(f"[PatternSelector] REJECT {c.type}: relevance_score {c.relevance_score:.2f} < {self.MIN_RELEVANCE_SCORE}")
                continue
            
            # Stage 5: Clarity score
            c.clarity_score = self._compute_clarity_score(c)
            
            # Final score
            c.final_score = (
                c.geometry_score * self.WEIGHT_GEOMETRY +
                c.context_score * self.WEIGHT_CONTEXT +
                c.relevance_score * self.WEIGHT_RELEVANCE +
                c.clarity_score * self.WEIGHT_CLARITY
            )
            
            print(f"[PatternSelector] SURVIVOR {c.type}: final={c.final_score:.2f} "
                  f"(geo={c.geometry_score:.2f}, ctx={c.context_score:.2f}, "
                  f"rel={c.relevance_score:.2f}, clar={c.clarity_score:.2f})")
            
            survivors.append(c)
        
        # Stage 6: Dedupe overlapping patterns
        survivors = self._dedupe_overlapping_patterns(survivors)
        
        if not survivors:
            print("[PatternSelector] No survivors after all filters")
            return None, []
        
        # Sort by final score
        survivors.sort(key=lambda x: x.final_score or 0, reverse=True)
        
        best = survivors[0]
        second = survivors[1] if len(survivors) > 1 else None
        
        # Check minimum final score
        if best.final_score < self.MIN_FINAL_SCORE:
            print(f"[PatternSelector] REJECT best {best.type}: final_score {best.final_score:.2f} < {self.MIN_FINAL_SCORE}")
            return None, []
        
        # Check winner gap (ambiguity check)
        if second:
            gap = best.final_score - second.final_score
            if gap < self.MIN_WINNER_GAP:
                print(f"[PatternSelector] AMBIGUOUS: gap {gap:.3f} < {self.MIN_WINNER_GAP} "
                      f"({best.type}={best.final_score:.2f} vs {second.type}={second.final_score:.2f})")
                # Return best but mark as weak
                best.status = "ambiguous"
        
        # Get alternatives
        alternatives = survivors[1:3] if len(survivors) > 1 else []
        
        print(f"[PatternSelector] WINNER: {best.type} final_score={best.final_score:.2f}")
        
        return best, alternatives
    
    def explain_selection(
        self, 
        primary: Optional[PatternCandidate],
        alternatives: List[PatternCandidate]
    ) -> dict:
        """Generate explanation for the selection."""
        if primary is None:
            return {
                "status": "no_pattern",
                "reason": "No pattern passed all quality filters",
                "primary": None,
                "alternatives": [],
            }
        
        return {
            "status": "active" if primary.status != "ambiguous" else "ambiguous",
            "primary": {
                "type": primary.type,
                "direction": primary.direction,
                "final_score": round(primary.final_score or 0, 3),
                "geometry_score": round(primary.geometry_score or 0, 3),
                "context_score": round(primary.context_score or 0, 3),
                "relevance_score": round(primary.relevance_score or 0, 3),
                "clarity_score": round(primary.clarity_score or 0, 3),
            },
            "alternatives": [
                {
                    "type": a.type,
                    "direction": a.direction,
                    "final_score": round(a.final_score or 0, 3),
                }
                for a in (alternatives or [])
            ],
        }


# Singleton instance
_selector = None

def get_pattern_selector() -> PatternSelector:
    """Get singleton pattern selector instance."""
    global _selector
    if _selector is None:
        _selector = PatternSelector()
    return _selector
