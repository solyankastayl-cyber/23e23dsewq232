"""
Pattern Context Fit Engine
===========================

Evaluates how well a pattern fits the current market context.

KEY CONCEPT:
Pattern alone ≠ Signal
Pattern × Context = Signal

SCORING:
- HIGH (1.2+): Pattern strongly aligned with context
- MEDIUM (0.9-1.2): Moderate alignment
- LOW (<0.9): Pattern conflicts with context

MATRIX: Pattern Type × Market Regime

| Pattern      | Compression | Range   | Trend   | Volatile |
|--------------|-------------|---------|---------|----------|
| Triangle     | 1.3x        | 1.1x    | 0.7x    | 0.6x     |
| Rectangle    | 1.2x        | 1.3x    | 0.6x    | 0.7x     |
| Flag/Pennant | 0.7x        | 0.8x    | 1.4x    | 0.8x     |
| H&S          | 0.9x        | 1.0x    | 1.2x    | 0.7x     |
| Wedge        | 1.2x        | 1.0x    | 0.9x    | 0.8x     |
| Channel      | 0.8x        | 1.3x    | 1.0x    | 0.7x     |
"""

from typing import Dict, List, Optional


# ═══════════════════════════════════════════════════════════════
# PATTERN × REGIME MATRIX
# ═══════════════════════════════════════════════════════════════

PATTERN_REGIME_MATRIX = {
    # Consolidation patterns work best in compression/range
    "triangle": {
        "compression": 1.30,
        "range": 1.10,
        "trend": 0.70,
        "volatile": 0.60,
    },
    "ascending_triangle": {
        "compression": 1.25,
        "range": 1.15,
        "trend": 0.80,
        "volatile": 0.65,
    },
    "descending_triangle": {
        "compression": 1.25,
        "range": 1.15,
        "trend": 0.80,
        "volatile": 0.65,
    },
    "symmetric_triangle": {
        "compression": 1.35,
        "range": 1.05,
        "trend": 0.65,
        "volatile": 0.60,
    },
    "rectangle": {
        "compression": 1.20,
        "range": 1.30,
        "trend": 0.60,
        "volatile": 0.70,
    },
    # Continuation patterns work best in trends
    "flag": {
        "compression": 0.70,
        "range": 0.80,
        "trend": 1.40,
        "volatile": 0.80,
    },
    "bull_flag": {
        "compression": 0.70,
        "range": 0.75,
        "trend": 1.45,
        "volatile": 0.75,
    },
    "bear_flag": {
        "compression": 0.70,
        "range": 0.75,
        "trend": 1.45,
        "volatile": 0.75,
    },
    "pennant": {
        "compression": 0.80,
        "range": 0.85,
        "trend": 1.35,
        "volatile": 0.75,
    },
    # Reversal patterns
    "head_and_shoulders": {
        "compression": 0.90,
        "range": 1.00,
        "trend": 1.20,
        "volatile": 0.70,
    },
    "inverse_head_and_shoulders": {
        "compression": 0.90,
        "range": 1.00,
        "trend": 1.20,
        "volatile": 0.70,
    },
    "double_top": {
        "compression": 0.85,
        "range": 1.10,
        "trend": 1.15,
        "volatile": 0.75,
    },
    "double_bottom": {
        "compression": 0.85,
        "range": 1.10,
        "trend": 1.15,
        "volatile": 0.75,
    },
    # Wedges
    "wedge": {
        "compression": 1.20,
        "range": 1.00,
        "trend": 0.90,
        "volatile": 0.80,
    },
    "rising_wedge": {
        "compression": 1.15,
        "range": 1.05,
        "trend": 0.95,
        "volatile": 0.80,
    },
    "falling_wedge": {
        "compression": 1.15,
        "range": 1.05,
        "trend": 0.95,
        "volatile": 0.80,
    },
    # Channel patterns
    "channel": {
        "compression": 0.80,
        "range": 1.30,
        "trend": 1.00,
        "volatile": 0.70,
    },
    "ascending_channel": {
        "compression": 0.75,
        "range": 1.25,
        "trend": 1.10,
        "volatile": 0.70,
    },
    "descending_channel": {
        "compression": 0.75,
        "range": 1.25,
        "trend": 1.10,
        "volatile": 0.70,
    },
}

# Default for unknown patterns
DEFAULT_REGIME_SCORES = {
    "compression": 1.0,
    "range": 1.0,
    "trend": 1.0,
    "volatile": 0.85,
}


def evaluate_context_fit(
    pattern: Dict,
    context: Dict,
) -> Dict:
    """
    Evaluate how well a pattern fits the market context.
    
    Args:
        pattern: Pattern object with type, direction, stage
        context: Market context from context_engine
    
    Returns:
        {
            "score": float,       # 0.3 to 1.5
            "label": str,         # "HIGH" | "MEDIUM" | "LOW"
            "aligned": bool,      # Pattern aligned with context?
            "reasons": list,      # Why this score
            "recommendation": str # Action recommendation
        }
    """
    if not pattern or not context:
        return _empty_fit("Missing pattern or context")
    
    score = 1.0
    reasons = []
    
    pattern_type = pattern.get("type", "").lower().replace(" ", "_").replace("-", "_")
    pattern_direction = pattern.get("direction", pattern.get("bias", "neutral")).lower()
    pattern_stage = pattern.get("stage", "forming")
    
    regime = context.get("regime", "range")
    structure = context.get("structure", "neutral")
    impulse = context.get("impulse", "none")
    volatility = context.get("volatility", "mid")
    
    # ═══════════════════════════════════════════════════════════════
    # 1. REGIME FIT (from matrix)
    # ═══════════════════════════════════════════════════════════════
    regime_multipliers = PATTERN_REGIME_MATRIX.get(pattern_type, DEFAULT_REGIME_SCORES)
    regime_score = regime_multipliers.get(regime, 1.0)
    
    score *= regime_score
    
    if regime_score >= 1.2:
        reasons.append(f"Pattern optimal in {regime} regime (+{int((regime_score-1)*100)}%)")
    elif regime_score <= 0.8:
        reasons.append(f"Pattern weak outside typical regime ({regime}, -{int((1-regime_score)*100)}%)")
    
    # ═══════════════════════════════════════════════════════════════
    # 2. STRUCTURE ALIGNMENT
    # ═══════════════════════════════════════════════════════════════
    if pattern_direction == structure:
        score *= 1.20
        reasons.append(f"Direction aligned with structure ({structure})")
    elif pattern_direction != "neutral" and structure != "neutral" and pattern_direction != structure:
        score *= 0.75
        reasons.append(f"Direction conflicts with structure ({pattern_direction} vs {structure})")
    
    # ═══════════════════════════════════════════════════════════════
    # 3. IMPULSE ALIGNMENT
    # ═══════════════════════════════════════════════════════════════
    impulse_match = False
    if pattern_direction == "bullish" and impulse == "up":
        score *= 1.15
        impulse_match = True
        reasons.append("Bullish momentum supports pattern")
    elif pattern_direction == "bearish" and impulse == "down":
        score *= 1.15
        impulse_match = True
        reasons.append("Bearish momentum supports pattern")
    elif pattern_direction == "bullish" and impulse == "down":
        score *= 0.85
        reasons.append("Counter-trend pattern (bullish vs down impulse)")
    elif pattern_direction == "bearish" and impulse == "up":
        score *= 0.85
        reasons.append("Counter-trend pattern (bearish vs up impulse)")
    
    # ═══════════════════════════════════════════════════════════════
    # 4. VOLATILITY ADJUSTMENT
    # ═══════════════════════════════════════════════════════════════
    if volatility == "low":
        # Low volatility dampens pattern reliability
        score *= 0.90
        reasons.append("Low volatility reduces breakout probability")
    elif volatility == "high":
        # High volatility can accelerate patterns but reduces reliability
        if pattern_type in ("flag", "pennant", "bull_flag", "bear_flag"):
            score *= 1.05  # Continuation patterns benefit from volatility
        else:
            score *= 0.95
            reasons.append("High volatility may cause false breakouts")
    
    # ═══════════════════════════════════════════════════════════════
    # 5. STAGE BONUS
    # ═══════════════════════════════════════════════════════════════
    if pattern_stage == "confirmed":
        score *= 1.10
        reasons.append("Pattern confirmed (higher confidence)")
    elif pattern_stage == "mature":
        score *= 1.05
        reasons.append("Pattern mature (ready for breakout)")
    
    # ═══════════════════════════════════════════════════════════════
    # CLAMP AND LABEL
    # ═══════════════════════════════════════════════════════════════
    score = max(0.30, min(1.50, score))
    label = _get_label(score)
    aligned = score >= 0.95
    
    recommendation = _build_recommendation(label, pattern_direction, regime, structure)
    
    return {
        "score": round(score, 2),
        "label": label,
        "aligned": aligned,
        "reasons": reasons,
        "recommendation": recommendation,
        "_components": {
            "regime": round(regime_score, 2),
            "structure_aligned": pattern_direction == structure,
            "impulse_aligned": impulse_match,
            "volatility": volatility,
        }
    }


def _empty_fit(reason: str) -> Dict:
    """Return empty context fit result."""
    return {
        "score": 1.0,
        "label": "UNKNOWN",
        "aligned": False,
        "reasons": [reason],
        "recommendation": "Insufficient data for context evaluation",
        "_components": {},
    }


def _get_label(score: float) -> str:
    """Get label from score."""
    if score >= 1.15:
        return "HIGH"
    elif score >= 0.90:
        return "MEDIUM"
    else:
        return "LOW"


def _build_recommendation(label: str, direction: str, regime: str, structure: str) -> str:
    """Build action recommendation based on fit analysis."""
    if label == "HIGH":
        return f"Pattern strongly supported by {regime} market. Consider entry on confirmation."
    elif label == "MEDIUM":
        return "Pattern moderately aligned. Wait for additional confirmation before entry."
    else:
        conflict = ""
        if direction != structure and direction != "neutral" and structure != "neutral":
            conflict = f" Pattern direction ({direction}) conflicts with market structure ({structure})."
        return f"Pattern poorly aligned with current context.{conflict} Consider waiting for better setup."


def batch_evaluate_patterns(
    patterns: List[Dict],
    context: Dict,
) -> List[Dict]:
    """
    Evaluate context fit for multiple patterns.
    
    Returns patterns with context_fit attached, sorted by fit score.
    """
    results = []
    
    for p in patterns:
        fit = evaluate_context_fit(p, context)
        results.append({
            **p,
            "context_fit": fit,
        })
    
    # Sort by context fit score descending
    results.sort(key=lambda x: x.get("context_fit", {}).get("score", 0), reverse=True)
    
    return results


def get_tradeable_status(context_fit: Dict) -> bool:
    """
    Determine if pattern is tradeable based on context fit.
    
    LOW context fit → Not tradeable
    """
    label = context_fit.get("label", "UNKNOWN")
    return label in ("HIGH", "MEDIUM")


def adjust_confidence_by_context(
    base_confidence: float,
    context_fit: Dict,
) -> float:
    """
    Adjust pattern confidence by context fit score.
    
    base_confidence: 0.0 to 1.0
    Returns: adjusted confidence (0.0 to 1.0)
    """
    fit_score = context_fit.get("score", 1.0)
    adjusted = base_confidence * fit_score
    return max(0.0, min(1.0, adjusted))
