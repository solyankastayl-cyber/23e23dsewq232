"""
Pattern Ranker
==============
Ranks and filters pattern candidates.
"""

from __future__ import annotations

from typing import Any, Dict, List
from .pattern_candidate import PatternCandidate


class PatternRanker:
    """Ranks patterns by score and filters duplicates."""
    
    def rank(
        self,
        candidates: List[PatternCandidate],
        structure_context: Dict[str, Any],
        liquidity: Dict[str, Any],
        displacement: Dict[str, Any],
        poi: Dict[str, Any],
    ) -> List[PatternCandidate]:
        """
        Rank candidates by total score.
        Remove near-duplicates (same type + overlapping window).
        """
        if not candidates:
            return []
        
        # Sort by total score descending
        ranked = sorted(
            candidates,
            key=lambda c: c.scores.total,
            reverse=True
        )
        
        # Remove near-duplicates
        filtered: List[PatternCandidate] = []
        for candidate in ranked:
            if not self._is_duplicate(candidate, filtered):
                filtered.append(candidate)
        
        return filtered
    
    def _is_duplicate(self, candidate: PatternCandidate, existing: List[PatternCandidate]) -> bool:
        """Check if candidate overlaps with existing patterns of same type."""
        for e in existing:
            same_type = candidate.type == e.type
            overlap = not (
                candidate.window.end_index < e.window.start_index or
                e.window.end_index < candidate.window.start_index
            )
            # Also check significant overlap percentage
            if same_type and overlap:
                overlap_start = max(candidate.window.start_index, e.window.start_index)
                overlap_end = min(candidate.window.end_index, e.window.end_index)
                overlap_size = overlap_end - overlap_start
                candidate_size = candidate.window.end_index - candidate.window.start_index
                if candidate_size > 0 and overlap_size / candidate_size > 0.5:
                    return True
        return False
