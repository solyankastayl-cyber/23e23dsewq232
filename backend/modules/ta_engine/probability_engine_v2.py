"""
Probability Engine V2 — Weighted Probabilistic Outcomes
========================================================

Calculates outcome probabilities using weighted similarity:
P(outcome) = Σ(similarity × confidence × recency × regime_weight × mtf_weight)

This is quant-style probabilistic TA.
"""

import math
from datetime import datetime, timezone
from typing import Dict, List, Optional


def recency_weight(timestamp: int, half_life_days: int = 30) -> float:
    """
    Calculate recency weight with exponential decay.
    
    Args:
        timestamp: Unix timestamp of historical pattern
        half_life_days: Days until weight drops to 50%
    
    Returns:
        Weight in (0, 1] range
    """
    if not timestamp:
        return 0.5
    
    now = datetime.now(timezone.utc).timestamp()
    age_days = (now - timestamp) / 86400
    
    # Exponential decay
    return math.exp(-age_days / half_life_days)


def regime_weight(current_regime: str, historical_regime: str) -> float:
    """
    Weight based on market regime match.
    
    Same regime = 1.2 (bonus)
    Different regime = 0.7 (penalty)
    """
    if not current_regime or not historical_regime:
        return 1.0
    
    current = current_regime.upper()
    historical = historical_regime.upper()
    
    if current == historical:
        return 1.2
    
    # Partial match for similar regimes
    similar = {
        "COMPRESSION": ["RANGE", "CONSOLIDATION"],
        "TREND": ["EXPANSION", "BREAKOUT"],
    }
    
    for key, related in similar.items():
        if current == key or current in related:
            if historical == key or historical in related:
                return 1.0
    
    return 0.7


def mtf_weight(current_bias: str, higher_tf_bias: str) -> float:
    """
    Weight based on MTF alignment.
    
    Aligned bias = 1.2 (bonus)
    Opposite bias = 0.6 (penalty)
    """
    if not current_bias or not higher_tf_bias:
        return 1.0
    
    current = current_bias.lower()
    higher = higher_tf_bias.lower()
    
    if current == higher:
        return 1.2
    
    if current == "neutral" or higher == "neutral":
        return 1.0
    
    # Opposite biases
    if (current == "bullish" and higher == "bearish") or \
       (current == "bearish" and higher == "bullish"):
        return 0.6
    
    return 1.0


def compute_match_weight(match: Dict, context: Dict) -> float:
    """
    Compute total weight for a single match.
    
    Weight = similarity × confidence × recency × regime × mtf × type_bonus
    """
    from .pattern_similarity_engine import type_match_bonus
    
    sim = match.get("similarity", 0)
    pattern = match.get("pattern", {})
    
    # Confidence
    conf = pattern.get("confidence", 0.5)
    
    # Recency
    ts = match.get("timestamp")
    rec = recency_weight(ts, half_life_days=30)
    
    # Regime alignment
    reg_w = regime_weight(
        context.get("regime"),
        pattern.get("regime") or pattern.get("market_state")
    )
    
    # MTF alignment
    mtf_w = mtf_weight(
        pattern.get("bias"),
        context.get("mtf_bias")
    )
    
    # Type bonus
    type_w = type_match_bonus(
        context.get("pattern_type"),
        pattern.get("type")
    )
    
    return sim * conf * rec * reg_w * mtf_w * type_w


def aggregate_probabilities(matches: List[Dict], context: Dict) -> Optional[Dict]:
    """
    Aggregate weighted probabilities across all matches.
    
    Returns:
        {
            "breakout_up": 0.68,
            "breakdown": 0.22,
            "neutral": 0.10,
            "edge": "bullish",
            "confidence": 0.68,
            "sample_size": 7
        }
    """
    scores = {
        "breakout_up": 0,
        "breakdown": 0,
        "neutral": 0,
    }
    
    total_weight = 0
    
    for m in matches:
        w = compute_match_weight(m, context)
        outcome = m.get("outcome", "neutral")
        
        if outcome in scores:
            scores[outcome] += w
        else:
            scores["neutral"] += w
        
        total_weight += w
    
    if total_weight == 0:
        return None
    
    # Normalize to probabilities
    probs = {
        k: round(v / total_weight, 2)
        for k, v in scores.items()
    }
    
    # Determine edge
    if probs["breakout_up"] > probs["breakdown"] + 0.15:
        edge = "bullish"
        confidence = probs["breakout_up"]
    elif probs["breakdown"] > probs["breakout_up"] + 0.15:
        edge = "bearish"
        confidence = probs["breakdown"]
    else:
        edge = "neutral"
        confidence = max(probs.values())
    
    return {
        "breakout_up": probs["breakout_up"],
        "breakdown": probs["breakdown"],
        "neutral": probs["neutral"],
        "edge": edge,
        "confidence": confidence,
        "sample_size": len(matches),
    }


def build_probability_context(
    pattern: Dict,
    market_state: str,
    mtf_bias: str = None,
) -> Dict:
    """Build context dict for probability calculation."""
    return {
        "pattern_type": pattern.get("type"),
        "regime": market_state,
        "mtf_bias": mtf_bias,
    }


__all__ = [
    "recency_weight",
    "regime_weight", 
    "mtf_weight",
    "compute_match_weight",
    "aggregate_probabilities",
    "build_probability_context",
]
