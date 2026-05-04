"""
Pattern Ranking Engine V2 — Context-Aware Decision System

Not just: winner = max(score)
But: winner = CONTEXT-AWARE DECISION

SCORING FORMULA:
final_score = BASE_SCORE
            + STRUCTURE_ALIGNMENT
            + HTF_ALIGNMENT
            + REGIME_BONUS
            - CONFLICT_PENALTY

CONFIDENCE STATES:
- CLEAR: Strong dominant, can act
- WEAK: Moderate confidence, be careful
- CONFLICTED: Competing signals, don't force trade
"""

from typing import Dict, List, Optional


def rank_patterns_v2(
    patterns: List[Dict],
    structure: Optional[Dict] = None,
    htf_context: Optional[Dict] = None,
    regime: Optional[Dict] = None,
) -> List[Dict]:
    """
    Rank patterns with context-aware scoring.
    
    Args:
        patterns: List of pattern candidates with base scores
        structure: Current structure layer (trend, phase)
        htf_context: Higher timeframe context (bias)
        regime: Regime layer (range/trend/compression)
    
    Returns:
        Ranked list with final_score and components breakdown
    """
    if not patterns:
        return []
    
    structure = structure or {}
    htf_context = htf_context or {}
    regime = regime or {}
    
    ranked = []
    
    for p in patterns:
        # Normalize base score to 0-100 scale
        base = p.get("score", 0)
        if base <= 1:
            base = base * 100  # Convert 0.76 → 76
        
        # Calculate context bonuses
        structure_bonus = _score_structure_alignment(p, structure)
        htf_bonus = _score_htf_alignment(p, htf_context)
        regime_bonus = _score_regime(p, regime)
        conflict_penalty = _score_conflict(p, patterns)
        
        # Final score
        final_score = (
            base
            + structure_bonus
            + htf_bonus
            + regime_bonus
            - conflict_penalty
        )
        
        # Clamp to reasonable bounds
        final_score = max(0, min(100, final_score))
        
        ranked.append({
            **p,
            "final_score": round(final_score, 2),
            "base_score": round(base, 2),
            "components": {
                "base": round(base, 2),
                "structure": structure_bonus,
                "htf": htf_bonus,
                "regime": regime_bonus,
                "conflict": -conflict_penalty,
            }
        })
    
    # Sort by final_score descending
    ranked.sort(key=lambda x: x["final_score"], reverse=True)
    
    return ranked


def _score_structure_alignment(p: Dict, structure: Dict) -> float:
    """
    Bonus/penalty based on structure alignment.
    
    Bullish pattern + bullish structure = +10
    Bullish pattern + bearish structure = -8
    Neutral pattern = 0
    """
    trend = structure.get("trend", "neutral")
    bias = p.get("bias", "neutral")
    
    if bias == "neutral":
        return 0
    
    if bias == trend:
        return 10  # Aligned with structure
    
    # Opposing bias
    if (bias == "bullish" and trend == "bearish") or \
       (bias == "bearish" and trend == "bullish"):
        return -8
    
    return 0


def _score_htf_alignment(p: Dict, htf: Dict) -> float:
    """
    Bonus/penalty based on higher timeframe alignment.
    
    Pattern aligned with HTF = +8
    Pattern against HTF = -6
    """
    htf_bias = htf.get("bias") or htf.get("trend")
    
    if not htf_bias or htf_bias == "neutral":
        return 0
    
    bias = p.get("bias", "neutral")
    
    if bias == "neutral":
        return 0
    
    if bias == htf_bias:
        return 8  # Aligned with HTF
    
    # Opposing HTF
    return -6


def _score_regime(p: Dict, regime: Dict) -> float:
    """
    Bonus/penalty based on market regime.
    
    Range regime favors range patterns
    Trend regime favors directional patterns
    """
    r = regime.get("regime", "unknown")
    pattern_type = p.get("type", "").lower()
    bias = p.get("bias", "neutral")
    
    # RANGE regime
    if r == "range":
        # Range patterns get bonus in range regime
        if "range" in pattern_type:
            return 8
        # Directional patterns penalized in range
        if bias != "neutral":
            return -4
        return 0
    
    # TREND regime
    if r == "trend":
        # Directional patterns get bonus in trend
        if bias != "neutral":
            return 6
        return 0
    
    # COMPRESSION regime
    if r == "compression":
        # Compression favors breakout patterns
        if pattern_type in ["triangle", "wedge", "pennant", "flag"]:
            return 6
        return 0
    
    return 0


def _score_conflict(current: Dict, all_patterns: List[Dict]) -> float:
    """
    Penalty when there are competing patterns with similar scores.
    
    Opposing bias + similar score = penalty
    """
    penalty = 0
    current_bias = current.get("bias", "neutral")
    current_score = current.get("score", 0)
    
    if current_score <= 1:
        current_score = current_score * 100
    
    for p in all_patterns:
        if p == current:
            continue
        
        p_bias = p.get("bias", "neutral")
        p_score = p.get("score", 0)
        
        if p_score <= 1:
            p_score = p_score * 100
        
        # Check for conflict: opposing bias with close score
        is_opposing = (
            (current_bias == "bullish" and p_bias == "bearish") or
            (current_bias == "bearish" and p_bias == "bullish")
        )
        
        score_diff = abs(current_score - p_score)
        
        if is_opposing and score_diff < 10:
            penalty += 6  # Significant conflict
        elif is_opposing and score_diff < 20:
            penalty += 3  # Mild conflict
    
    return penalty


def compute_confidence_state(ranked: List[Dict]) -> str:
    """
    Compute overall confidence state based on pattern ranking.
    
    Returns:
        - "clear": Strong dominant pattern, can act
        - "weak": Moderate confidence, be careful
        - "conflicted": Competing signals, don't force trade
    """
    if not ranked:
        return "unknown"
    
    if len(ranked) < 2:
        score = ranked[0].get("final_score", 0)
        if score > 75:
            return "clear"
        if score > 50:
            return "weak"
        return "uncertain"
    
    # Compare top 2
    top_score = ranked[0].get("final_score", 0)
    second_score = ranked[1].get("final_score", 0)
    diff = top_score - second_score
    
    # Check for opposing biases
    top_bias = ranked[0].get("bias", "neutral")
    second_bias = ranked[1].get("bias", "neutral")
    is_conflicting = (
        (top_bias == "bullish" and second_bias == "bearish") or
        (top_bias == "bearish" and second_bias == "bullish")
    )
    
    # Decision logic
    if diff < 5 and is_conflicting:
        return "conflicted"
    
    if diff < 5:
        return "weak"
    
    if top_score > 80:
        return "clear"
    
    if top_score > 60:
        return "weak"
    
    return "uncertain"


def compute_market_quality(ranked: List[Dict], confidence_state: str) -> Dict:
    """
    Compute overall market quality assessment.
    
    Returns:
        - quality: "high" / "medium" / "low"
        - tradeable: bool
        - description: str
    """
    if not ranked:
        return {
            "quality": "low",
            "tradeable": False,
            "description": "No patterns detected"
        }
    
    top = ranked[0]
    top_score = top.get("final_score", 0)
    
    if confidence_state == "clear" and top_score > 75:
        return {
            "quality": "high",
            "tradeable": True,
            "description": f"Clear {top.get('type', 'pattern')} setup with strong confluence"
        }
    
    if confidence_state == "weak":
        return {
            "quality": "medium",
            "tradeable": True,
            "description": "Moderate setup, manage risk carefully"
        }
    
    if confidence_state == "conflicted":
        return {
            "quality": "low",
            "tradeable": False,
            "description": "Market conflicted, wait for clarity"
        }
    
    return {
        "quality": "low",
        "tradeable": False,
        "description": "Insufficient signal strength"
    }
