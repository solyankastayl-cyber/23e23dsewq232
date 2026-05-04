"""
Regime Drift Engine
====================

Detects when market context has changed significantly.

PURPOSE:
When context drifts, previously valid setups may become invalid.
This engine detects drift and triggers re-evaluation.

DRIFT TYPES:
- regime_change: compression → trend, etc.
- volatility_shift: low → high
- structure_flip: bullish → bearish
- impulse_reversal: up → down

SEVERITY LEVELS:
- LOW: Minor shift, plan still valid
- MEDIUM: Notable change, reduce confidence
- HIGH: Major drift, invalidate plan

OUTPUT:
{
    "drift_detected": true,
    "severity": "HIGH",
    "changes": [...],
    "recommendation": "Re-evaluate setup",
    "confidence_penalty": 0.15
}
"""

from typing import Dict, List, Optional, Any


# ═══════════════════════════════════════════════════════════════
# DRIFT WEIGHTS (how much each field matters)
# ═══════════════════════════════════════════════════════════════

DRIFT_WEIGHTS = {
    "regime": 3.0,        # Most important
    "structure": 2.0,     # Direction of market
    "impulse": 1.5,       # Momentum direction
    "volatility": 1.0,    # Volatility state
}

# Regime transition severity
REGIME_TRANSITIONS = {
    # From compression
    ("compression", "trend"): "HIGH",
    ("compression", "volatile"): "HIGH",
    ("compression", "range"): "LOW",
    
    # From range
    ("range", "trend"): "MEDIUM",
    ("range", "compression"): "LOW",
    ("range", "volatile"): "MEDIUM",
    
    # From trend
    ("trend", "compression"): "MEDIUM",
    ("trend", "range"): "MEDIUM",
    ("trend", "volatile"): "HIGH",
    
    # From volatile
    ("volatile", "trend"): "MEDIUM",
    ("volatile", "range"): "LOW",
    ("volatile", "compression"): "LOW",
}


def detect_regime_drift(
    current_context: Dict,
    previous_context: Dict,
) -> Dict:
    """
    Detect drift between two context snapshots.
    
    Args:
        current_context: Current market context
        previous_context: Previous context (when plan was built)
    
    Returns:
        Drift analysis with severity and recommendations
    """
    if not current_context or not previous_context:
        return {
            "drift_detected": False,
            "severity": "NONE",
            "changes": [],
            "message": "Insufficient context data",
            "confidence_penalty": 0,
        }
    
    changes = []
    total_drift_score = 0
    
    # ═══════════════════════════════════════════════════════════════
    # CHECK EACH CONTEXT FIELD
    # ═══════════════════════════════════════════════════════════════
    
    # 1. REGIME
    curr_regime = current_context.get("regime", "unknown")
    prev_regime = previous_context.get("regime", "unknown")
    
    if curr_regime != prev_regime:
        transition = (prev_regime, curr_regime)
        severity = REGIME_TRANSITIONS.get(transition, "MEDIUM")
        
        changes.append({
            "field": "regime",
            "from": prev_regime,
            "to": curr_regime,
            "severity": severity,
        })
        
        severity_scores = {"LOW": 1, "MEDIUM": 2, "HIGH": 3}
        total_drift_score += DRIFT_WEIGHTS["regime"] * severity_scores.get(severity, 1)
    
    # 2. STRUCTURE
    curr_structure = current_context.get("structure", "neutral")
    prev_structure = previous_context.get("structure", "neutral")
    
    if curr_structure != prev_structure:
        # Structure flip is significant
        if (prev_structure == "bullish" and curr_structure == "bearish") or \
           (prev_structure == "bearish" and curr_structure == "bullish"):
            severity = "HIGH"
        else:
            severity = "MEDIUM"
        
        changes.append({
            "field": "structure",
            "from": prev_structure,
            "to": curr_structure,
            "severity": severity,
        })
        
        severity_scores = {"LOW": 1, "MEDIUM": 2, "HIGH": 3}
        total_drift_score += DRIFT_WEIGHTS["structure"] * severity_scores.get(severity, 1)
    
    # 3. IMPULSE
    curr_impulse = current_context.get("impulse", "none")
    prev_impulse = previous_context.get("impulse", "none")
    
    if curr_impulse != prev_impulse:
        # Impulse reversal
        if (prev_impulse == "up" and curr_impulse == "down") or \
           (prev_impulse == "down" and curr_impulse == "up"):
            severity = "MEDIUM"
        else:
            severity = "LOW"
        
        changes.append({
            "field": "impulse",
            "from": prev_impulse,
            "to": curr_impulse,
            "severity": severity,
        })
        
        severity_scores = {"LOW": 1, "MEDIUM": 2, "HIGH": 3}
        total_drift_score += DRIFT_WEIGHTS["impulse"] * severity_scores.get(severity, 1)
    
    # 4. VOLATILITY
    curr_vol = current_context.get("volatility", "mid")
    prev_vol = previous_context.get("volatility", "mid")
    
    if curr_vol != prev_vol:
        # Volatility jump
        if (prev_vol == "low" and curr_vol == "high") or \
           (prev_vol == "high" and curr_vol == "low"):
            severity = "MEDIUM"
        else:
            severity = "LOW"
        
        changes.append({
            "field": "volatility",
            "from": prev_vol,
            "to": curr_vol,
            "severity": severity,
        })
        
        severity_scores = {"LOW": 1, "MEDIUM": 2, "HIGH": 3}
        total_drift_score += DRIFT_WEIGHTS["volatility"] * severity_scores.get(severity, 1)
    
    # ═══════════════════════════════════════════════════════════════
    # DETERMINE OVERALL SEVERITY
    # ═══════════════════════════════════════════════════════════════
    
    if total_drift_score == 0:
        overall_severity = "NONE"
        drift_detected = False
        message = "Context stable - no drift detected"
        confidence_penalty = 0
    elif total_drift_score <= 3:
        overall_severity = "LOW"
        drift_detected = True
        message = "Minor context shift - plan still valid"
        confidence_penalty = 0.05
    elif total_drift_score <= 6:
        overall_severity = "MEDIUM"
        drift_detected = True
        message = "Notable context change - reduce confidence"
        confidence_penalty = 0.12
    else:
        overall_severity = "HIGH"
        drift_detected = True
        message = "Major context drift - re-evaluate setup"
        confidence_penalty = 0.20
    
    # ═══════════════════════════════════════════════════════════════
    # BUILD RECOMMENDATION
    # ═══════════════════════════════════════════════════════════════
    
    if overall_severity == "HIGH":
        recommendation = "INVALIDATE - Context changed significantly. Rebuild analysis."
        action = "invalidate"
    elif overall_severity == "MEDIUM":
        recommendation = "CAUTION - Context shifted. Tighten stops or reduce size."
        action = "reduce"
    elif overall_severity == "LOW":
        recommendation = "MONITOR - Minor change. Continue with awareness."
        action = "monitor"
    else:
        recommendation = "PROCEED - Context stable."
        action = "proceed"
    
    return {
        "drift_detected": drift_detected,
        "severity": overall_severity,
        "drift_score": round(total_drift_score, 2),
        "changes": changes,
        "message": message,
        "recommendation": recommendation,
        "action": action,
        "confidence_penalty": confidence_penalty,
        "previous_context": {
            "regime": prev_regime,
            "structure": prev_structure,
            "impulse": prev_impulse,
            "volatility": prev_vol,
        },
        "current_context": {
            "regime": curr_regime,
            "structure": curr_structure,
            "impulse": curr_impulse,
            "volatility": curr_vol,
        },
    }


def apply_drift_penalty(confidence: float, drift: Dict) -> float:
    """
    Apply drift penalty to confidence.
    """
    if not drift or not drift.get("drift_detected"):
        return confidence
    
    penalty = drift.get("confidence_penalty", 0)
    adjusted = confidence - penalty
    
    return round(max(0.05, min(0.95, adjusted)), 4)


def should_invalidate_plan(drift: Dict) -> bool:
    """
    Determine if execution plan should be invalidated.
    """
    if not drift:
        return False
    
    return drift.get("severity") == "HIGH" or drift.get("action") == "invalidate"


def format_drift_for_ui(drift: Dict) -> Dict:
    """
    Format drift data for frontend display.
    """
    if not drift or not drift.get("drift_detected"):
        return {
            "show": False,
            "message": "Context stable",
        }
    
    severity = drift.get("severity", "LOW")
    changes = drift.get("changes", [])
    
    # Color by severity
    colors = {
        "LOW": "#eab308",      # Yellow
        "MEDIUM": "#f97316",   # Orange
        "HIGH": "#ef4444",     # Red
    }
    
    # Build change summary
    change_strs = []
    for c in changes:
        change_strs.append(f"{c['field']}: {c['from']} → {c['to']}")
    
    return {
        "show": True,
        "severity": severity,
        "color": colors.get(severity, "#64748b"),
        "message": drift.get("message", ""),
        "recommendation": drift.get("recommendation", ""),
        "changes": change_strs,
        "action": drift.get("action", "proceed"),
        "penalty": f"-{int(drift.get('confidence_penalty', 0) * 100)}%",
    }


def build_drift_summary(drift: Dict) -> str:
    """
    Build one-line drift summary.
    """
    if not drift or not drift.get("drift_detected"):
        return "Context stable"
    
    severity = drift.get("severity", "LOW")
    changes = drift.get("changes", [])
    
    if not changes:
        return f"Drift: {severity}"
    
    primary_change = changes[0]
    return f"Drift: {severity} ({primary_change['field']}: {primary_change['from']} → {primary_change['to']})"
