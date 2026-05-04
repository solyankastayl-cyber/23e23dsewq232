"""
Decision Engine
================

Converts pattern analysis into actionable trading decisions.

Key outputs:
- final_bias: bullish/bearish/neutral
- bias_score: weighted confidence
- market_state: trend/range/compression/expansion
- cross_tf_alignment: aligned_bullish/aligned_bearish/mixed
"""

from typing import Dict, List, Optional


TF_WEIGHTS = {
    "4H": 0.10,
    "1D": 0.20,
    "7D": 0.20,
    "30D": 0.25,
    "180D": 0.15,
    "1Y": 0.10
}


def compute_final_bias(setups_by_tf: Dict) -> Dict:
    """
    Aggregate bias across multiple timeframes with weighted scoring.
    
    Returns:
        {"bias": "bullish"|"bearish"|"neutral", "score": float}
    """
    if not setups_by_tf:
        return {"bias": "neutral", "score": 0.0}
    
    score = 0.0
    total_weight = 0.0
    
    for tf, setup in setups_by_tf.items():
        weight = TF_WEIGHTS.get(tf.upper(), 0.1)
        direction = setup.get("direction", "neutral")
        
        if direction == "bullish":
            score += weight
        elif direction == "bearish":
            score -= weight
        
        total_weight += weight
    
    # Normalize if not all TFs present
    if total_weight > 0 and total_weight < 1.0:
        score = score / total_weight
    
    if score > 0.15:
        return {"bias": "bullish", "score": round(score, 3)}
    elif score < -0.15:
        return {"bias": "bearish", "score": round(score, 3)}
    else:
        return {"bias": "neutral", "score": round(score, 3)}


def compute_alignment(setups_by_tf: Dict) -> str:
    """
    Check if all timeframes agree on direction.
    
    Returns:
        "aligned_bullish" | "aligned_bearish" | "mixed" | "unknown"
    """
    if not setups_by_tf:
        return "unknown"
    
    directions = []
    for setup in setups_by_tf.values():
        direction = setup.get("direction")
        if direction and direction != "neutral":
            directions.append(direction)
    
    if not directions:
        return "neutral"
    
    if all(d == "bullish" for d in directions):
        return "aligned_bullish"
    if all(d == "bearish" for d in directions):
        return "aligned_bearish"
    
    return "mixed"


def detect_market_state(structure_context: Dict, patterns: List[Dict]) -> str:
    """
    Determine overall market state from structure and patterns.
    
    Returns:
        "compression" | "range" | "expansion" | "trend"
    """
    if not structure_context:
        return "unknown"
    
    regime = structure_context.get("regime", "")
    
    # Direct regime mapping
    if regime == "compression":
        return "compression"
    
    if regime == "range":
        return "range"
    
    # Check for expansion signals in patterns
    pattern_types = [p.get("type", "").lower() for p in patterns if p]
    
    if any(pt in ["breakout", "breakout_up", "breakdown", "flag", "pennant"] for pt in pattern_types):
        return "expansion"
    
    if regime in ["trend_up", "trend_down"]:
        return "trend"
    
    return "consolidation"


def build_decision(
    structure_context: Dict,
    primary_pattern: Optional[Dict],
    alternative_patterns: List[Dict],
    multi_tf_setups: Optional[Dict] = None
) -> Dict:
    """
    Build complete decision object.
    
    HARDENED V2:
    - Uses structure_context bias/regime from StructureEngineV2
    - Penalizes mixed alignment
    - Downgrades confidence when pattern direction != structure bias
    """
    # Single TF fallback
    if not multi_tf_setups and primary_pattern:
        multi_tf_setups = {
            "1D": {
                "direction": primary_pattern.get("direction", "neutral"),
                "confidence": primary_pattern.get("confidence", 0.5)
            }
        }
    
    bias_result = compute_final_bias(multi_tf_setups or {})
    alignment = compute_alignment(multi_tf_setups or {})
    
    all_patterns = ([primary_pattern] if primary_pattern else []) + (alternative_patterns or [])
    market_state = detect_market_state(structure_context or {}, all_patterns)
    
    # Use structure bias as primary source of truth
    structure_bias = (structure_context or {}).get("bias", "neutral")
    structure_regime = (structure_context or {}).get("regime", "unknown")
    
    # If structure has clear bias, use it
    if structure_bias != "neutral":
        final_bias = structure_bias
    else:
        final_bias = bias_result["bias"]
    
    # Overall confidence — HARDENED
    confidence = 0.35  # Start lower (was 0.5)
    
    if primary_pattern:
        pattern_conf = primary_pattern.get("confidence", 0.5)
        pattern_dir = primary_pattern.get("direction", "neutral")
        bias_conf = abs(bias_result.get("score", 0))
        
        # Alignment bonus/penalty
        alignment_mod = 0.0
        if "aligned" in alignment:
            alignment_mod = 0.1
        elif alignment == "mixed":
            alignment_mod = -0.1  # PENALTY for mixed
        
        # Direction mismatch penalty
        direction_penalty = 0.0
        if pattern_dir != "neutral" and structure_bias != "neutral":
            if pattern_dir != structure_bias:
                direction_penalty = -0.15  # Heavy penalty
        
        confidence = min(0.90, max(0.2,
            pattern_conf * 0.4 + 
            bias_conf * 0.25 + 
            alignment_mod + 
            direction_penalty + 
            0.15
        ))
    else:
        # No pattern — confidence from structure only
        structure_score = (structure_context or {}).get("structure_score", 0.0)
        confidence = min(0.6, max(0.2, structure_score * 0.5 + 0.15))
    
    return {
        "bias": final_bias,
        "score": bias_result["score"],
        "alignment": alignment,
        "market_state": market_state,
        "regime": structure_regime,
        "market_phase": (structure_context or {}).get("market_phase", "unknown"),
        "last_event": (structure_context or {}).get("last_event", "none"),
        "confidence": round(confidence, 3)
    }


# Singleton-style access
decision_engine = {
    "compute_final_bias": compute_final_bias,
    "compute_alignment": compute_alignment,
    "detect_market_state": detect_market_state,
    "build_decision": build_decision
}
