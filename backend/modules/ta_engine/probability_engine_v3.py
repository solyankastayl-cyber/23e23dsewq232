"""
Probability Engine V3
=====================

Master aggregator for the full Probability Intelligence Stack.

COMBINES:
- Pattern Detection (base confidence)
- Context Engine (Pattern × Context)
- Historical Engine (Pattern × Context × History)
- Recency Decay (time-weighted stats)
- Drift Detection (improving/degrading)
- Expectation Engine (expected move/time)
- Decision Adjustment (final score + tradeable)

OUTPUT:
{
    "history_key": "triangle|compression|bearish|down|mid",
    "historical_stats": {...},
    "historical_fit": {...},
    "drift": {...},
    "expectation": {...},
    "decision": {...},
    "final_confidence": 0.71,
    "tradeable": true,
    "summary": "Confidence: 71% | Status: MODERATE_ENTRY | Trend: ↑ Improving"
}

This is the FINAL intelligence layer before execution.
"""

from typing import Dict, List, Optional, Any

# Import all components
from modules.ta_engine.historical_context_engine import (
    build_history_key,
    compute_weighted_stats,
    detect_drift,
    compute_historical_fit,
    build_historical_summary,
)
from modules.ta_engine.expectation_engine import (
    compute_expectation,
    format_expectation_for_ui,
)
from modules.ta_engine.decision_adjustment_engine import (
    finalize_probability_score,
    determine_tradeable,
    build_decision_summary,
)


def build_probability_v3(
    pattern: Dict,
    context: Dict,
    records: List[Dict],
    context_fit: Optional[Dict] = None,
) -> Dict:
    """
    Build complete probability intelligence for a pattern.
    
    This is the main entry point for the V3 probability stack.
    
    Args:
        pattern: Pattern object with type, direction, confidence
        context: Market context from context_engine
        records: Historical outcome records from MongoDB
        context_fit: Optional pre-computed context fit
    
    Returns:
        Complete probability analysis with all layers
    """
    # ═══════════════════════════════════════════════════════════════
    # 1. HISTORICAL ANALYSIS (time-weighted)
    # ═══════════════════════════════════════════════════════════════
    history_key = build_history_key(pattern, context)
    stats = compute_weighted_stats(records)
    hist_fit = compute_historical_fit(stats)
    
    # ═══════════════════════════════════════════════════════════════
    # 2. DRIFT DETECTION
    # ═══════════════════════════════════════════════════════════════
    drift = detect_drift(records)
    
    # ═══════════════════════════════════════════════════════════════
    # 3. EXPECTATION COMPUTATION
    # ═══════════════════════════════════════════════════════════════
    expectation = compute_expectation(stats, drift)
    
    # ═══════════════════════════════════════════════════════════════
    # 4. CONTEXT FIT (use provided or default)
    # ═══════════════════════════════════════════════════════════════
    if context_fit is None:
        context_fit = pattern.get("context_fit", {})
    
    context_score = float(context_fit.get("score", 1.0))
    context_label = context_fit.get("label", "MEDIUM")
    
    # ═══════════════════════════════════════════════════════════════
    # 5. FINAL PROBABILITY CALCULATION
    # ═══════════════════════════════════════════════════════════════
    base_confidence = float(pattern.get("confidence", 0.5))
    
    prob_result = finalize_probability_score(
        base_confidence=base_confidence,
        context_fit_score=context_score,
        historical_fit_score=hist_fit.get("score", 1.0),
        drift=drift,
        expectation=expectation,
    )
    
    final_confidence = prob_result["final_confidence"]
    
    # ═══════════════════════════════════════════════════════════════
    # 6. TRADEABLE DETERMINATION
    # ═══════════════════════════════════════════════════════════════
    tradeable_result = determine_tradeable(
        final_confidence=final_confidence,
        context_fit_label=context_label,
        historical_fit_label=hist_fit.get("label"),
        drift=drift,
    )
    
    # ═══════════════════════════════════════════════════════════════
    # 7. BUILD SUMMARIES
    # ═══════════════════════════════════════════════════════════════
    historical_summary = build_historical_summary(stats, hist_fit, drift)
    decision_summary = build_decision_summary(
        final_confidence=final_confidence,
        tradeable_result=tradeable_result,
        drift=drift,
        expectation=expectation,
    )
    
    # ═══════════════════════════════════════════════════════════════
    # RETURN COMPLETE RESULT
    # ═══════════════════════════════════════════════════════════════
    return {
        # Keys
        "history_key": history_key,
        
        # Historical layer
        "historical_stats": stats,
        "historical_fit": hist_fit,
        "historical_summary": historical_summary,
        
        # Drift layer
        "drift": drift,
        
        # Expectation layer
        "expectation": expectation,
        "expectation_ui": format_expectation_for_ui(expectation),
        
        # Decision layer
        "decision": tradeable_result,
        "probability_breakdown": prob_result["breakdown"],
        "total_multiplier": prob_result["total_multiplier"],
        
        # Final outputs
        "final_confidence": final_confidence,
        "base_confidence": base_confidence,
        "tradeable": tradeable_result["tradeable"],
        
        # Summaries
        "summary": decision_summary,
    }


def build_probability_v3_minimal(
    pattern: Dict,
    context: Dict,
    records: List[Dict],
) -> Dict:
    """
    Minimal version for quick lookups (fewer computations).
    
    Returns only essential fields.
    """
    history_key = build_history_key(pattern, context)
    stats = compute_weighted_stats(records)
    hist_fit = compute_historical_fit(stats)
    drift = detect_drift(records)
    
    base_confidence = float(pattern.get("confidence", 0.5))
    context_score = float(pattern.get("context_fit", {}).get("score", 1.0))
    
    # Simple calculation
    final = base_confidence * context_score * hist_fit.get("score", 1.0)
    
    # Drift adjustment
    if drift.get("label") == "IMPROVING":
        final *= 1.05
    elif drift.get("label") == "DEGRADING":
        final *= 0.93
    
    final = max(0.05, min(0.95, final))
    
    tradeable = True
    if hist_fit.get("label") == "POOR":
        tradeable = False
    if drift.get("label") == "STRONG_DEGRADING" and final < 0.55:
        tradeable = False
    
    return {
        "history_key": history_key,
        "final_confidence": round(final, 4),
        "tradeable": tradeable,
        "historical_fit_label": hist_fit.get("label"),
        "drift_label": drift.get("label"),
    }


def get_probability_label(confidence: float) -> str:
    """
    Get human-readable label for confidence level.
    """
    if confidence >= 0.75:
        return "VERY_HIGH"
    elif confidence >= 0.65:
        return "HIGH"
    elif confidence >= 0.55:
        return "MODERATE"
    elif confidence >= 0.45:
        return "LOW"
    else:
        return "VERY_LOW"
