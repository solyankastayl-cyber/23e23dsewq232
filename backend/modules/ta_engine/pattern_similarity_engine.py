"""
Pattern Similarity Engine — Find Similar Historical Patterns
=============================================================

Uses cosine similarity on pattern vectors to find historical matches.
"""

import math
from typing import Dict, List, Optional
from .pattern_vectorizer import vector_keys


def cosine_similarity(a: Dict, b: Dict) -> float:
    """
    Calculate cosine similarity between two normalized vectors.
    
    Returns value in [0, 1] range.
    """
    keys = vector_keys()
    
    dot = sum(a.get(k, 0) * b.get(k, 0) for k in keys)
    mag_a = math.sqrt(sum(a.get(k, 0) ** 2 for k in keys))
    mag_b = math.sqrt(sum(b.get(k, 0) ** 2 for k in keys))
    
    if mag_a == 0 or mag_b == 0:
        return 0
    
    return dot / (mag_a * mag_b)


def find_similar_patterns(
    current_vector: Dict,
    history_vectors: List[Dict],
    threshold: float = 0.75,
    max_results: int = 10,
) -> List[Dict]:
    """
    Find similar patterns in history.
    
    Args:
        current_vector: Normalized vector of current pattern
        history_vectors: List of {vector, outcome, pattern, timestamp}
        threshold: Minimum similarity score (0.75 = 75% similar)
        max_results: Maximum number of results
    
    Returns:
        List of matches sorted by similarity (highest first)
    """
    results = []
    
    for h in history_vectors:
        hist_vec = h.get("vector", {}).get("normalized", {})
        if not hist_vec:
            continue
        
        sim = cosine_similarity(current_vector, hist_vec)
        
        if sim >= threshold:
            results.append({
                "similarity": round(sim, 3),
                "outcome": h.get("outcome", "neutral"),
                "pattern": h.get("pattern", {}),
                "timestamp": h.get("timestamp"),
                "vector": h.get("vector"),
            })
    
    # Sort by similarity descending
    results.sort(key=lambda x: x["similarity"], reverse=True)
    
    return results[:max_results]


def type_match_bonus(current_type: str, hist_type: str) -> float:
    """
    Bonus weight if pattern types match.
    """
    if current_type == hist_type:
        return 1.2
    
    # Partial match for related types
    related = {
        "triangle": ["ascending_triangle", "descending_triangle", "symmetrical_triangle"],
        "wedge": ["rising_wedge", "falling_wedge"],
        "flag": ["bull_flag", "bear_flag"],
        "top": ["double_top", "triple_top"],
        "bottom": ["double_bottom", "triple_bottom"],
    }
    
    for group, types in related.items():
        if current_type in types and hist_type in types:
            return 1.1
    
    return 1.0


__all__ = ["cosine_similarity", "find_similar_patterns", "type_match_bonus"]
