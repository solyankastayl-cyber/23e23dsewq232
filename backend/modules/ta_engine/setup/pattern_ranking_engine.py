"""
Pattern Ranking Engine
======================

THE KEY: Patterns compete against each other.

Instead of "first triangle found → show it",
now we have "all candidates → rank → select best".

Scoring factors:
1. Geometry (how clean is the pattern) - 30%
2. Structure alignment (does it fit the market regime) - 20%
3. Level alignment (near key S/R?) - 15%
4. Recency (is last touch recent?) - 20%
5. Cleanliness (containment + line quality) - 15%
"""

from typing import List, Optional
from .pattern_candidate import PatternCandidate
from .structure_context_engine import StructureContext


class PatternRankingEngine:
    """
    Ranks pattern candidates by total score.
    
    This is what prevents "triangle everywhere" disease.
    A weak triangle will lose to a strong range or channel.
    """
    
    def __init__(self):
        pass

    def rank(
        self, 
        candidates: List[PatternCandidate], 
        structure_ctx: StructureContext, 
        levels: List[dict], 
        current_price: float
    ) -> List[PatternCandidate]:
        """
        Rank all candidates and return sorted list.
        
        Args:
            candidates: List of PatternCandidate objects
            structure_ctx: Current market structure context
            levels: Detected S/R levels
            current_price: Current close price
            
        Returns:
            Candidates sorted by total_score (highest first)
        """
        if not candidates:
            return []
        
        ranked = []

        for c in candidates:
            # Calculate individual scores
            c.structure_score = self._score_structure_alignment(c, structure_ctx)
            c.level_score = self._score_level_alignment(c, levels, current_price)
            c.recency_score = self._score_recency(c)
            c.cleanliness_score = self._score_cleanliness(c)
            
            # Geometry score from confidence + line quality
            line_avg = 0.0
            if c.line_scores:
                vals = list(c.line_scores.values())
                line_avg = sum(vals) / len(vals) / 20.0  # Normalize to 0-1
            c.geometry_score = (c.confidence + min(1.0, line_avg)) / 2

            # Calculate total score with weights
            c.total_score = (
                c.geometry_score * 0.30 +
                c.structure_score * 0.20 +
                c.level_score * 0.15 +
                c.recency_score * 0.20 +
                c.cleanliness_score * 0.15
            )

            ranked.append(c)

        # Sort by total score (highest first)
        ranked.sort(key=lambda x: x.total_score, reverse=True)
        return ranked

    def _score_structure_alignment(
        self, 
        candidate: PatternCandidate, 
        structure_ctx: StructureContext
    ) -> float:
        """
        Score how well pattern matches market structure.
        
        Key insight:
        - Triangle in compression → HIGH score
        - Triangle in strong trend → LOW score (probably wrong)
        - Range pattern in range regime → HIGH score
        """
        regime = structure_ctx.regime
        pattern_type = candidate.type.lower()
        direction = candidate.direction
        bias = structure_ctx.bias
        
        # Compression regime → triangles are valid
        if regime == "compression":
            if "triangle" in pattern_type:
                return 0.9
            if "wedge" in pattern_type:
                return 0.85
            return 0.5
        
        # Range regime → range patterns win
        if regime == "range":
            if pattern_type == "range" or pattern_type == "horizontal_channel":
                return 0.9
            if "triangle" in pattern_type:
                return 0.4  # Triangles less likely in true range
            return 0.5
        
        # Trend up → bullish patterns win
        if regime == "trend_up":
            if direction == "bullish":
                return 0.85
            if direction == "neutral":
                return 0.6
            return 0.3  # Bearish pattern in uptrend = suspicious
        
        # Trend down → bearish patterns win
        if regime == "trend_down":
            if direction == "bearish":
                return 0.85
            if direction == "neutral":
                return 0.6
            return 0.3
        
        # Reversal candidate → neutral patterns valid
        if regime == "reversal_candidate":
            return 0.65
        
        return 0.5

    def _score_level_alignment(
        self, 
        candidate: PatternCandidate, 
        levels: List[dict], 
        current_price: float
    ) -> float:
        """
        Score based on proximity to key S/R levels.
        
        Pattern near strong level → more significant.
        """
        if not levels or not current_price or current_price == 0:
            return 0.5

        # Find nearest level distance
        nearest_distance = float('inf')
        for level in levels:
            if level.get("price"):
                dist = abs(level["price"] - current_price) / current_price
                if dist < nearest_distance:
                    nearest_distance = dist

        # Score based on distance
        if nearest_distance < 0.01:  # Within 1%
            return 0.9
        if nearest_distance < 0.025:  # Within 2.5%
            return 0.7
        if nearest_distance < 0.05:  # Within 5%
            return 0.55
        return 0.4

    def _score_recency(self, candidate: PatternCandidate) -> float:
        """
        Score based on how recent the last touch was.
        
        Pattern with recent touch → more relevant.
        """
        span = max(candidate.end_index - candidate.start_index, 1)
        
        # How far into the pattern is the last touch?
        # 1.0 = last touch at end, 0.0 = last touch at start
        if span > 0:
            freshness = (candidate.last_touch_index - candidate.start_index) / span
        else:
            freshness = 0.5
        
        return max(0.0, min(1.0, freshness))

    def _score_cleanliness(self, candidate: PatternCandidate) -> float:
        """
        Score based on overall pattern quality.
        
        Combines containment + line quality.
        """
        # Line quality from line_scores
        line_quality = 0.0
        if candidate.line_scores:
            vals = list(candidate.line_scores.values())
            line_quality = sum(vals) / len(vals)
            line_quality = min(1.0, max(0.0, line_quality / 20.0))  # Normalize

        # Combine containment (how well price stayed inside) with line quality
        return (
            candidate.containment * 0.6 +
            line_quality * 0.4
        )


# Singleton instance
pattern_ranking_engine = PatternRankingEngine()
