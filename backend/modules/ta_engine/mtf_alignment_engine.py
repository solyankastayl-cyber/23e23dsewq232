"""
MTF ALIGNMENT ENGINE
====================

Связывает существующие TF между собой.
НЕ пересоздаёт MTF — использует то, что уже есть.

Даёт:
- direction (bullish/bearish/neutral)
- confidence (0-1)
- alignment status
"""

from typing import Dict, Any, List, Optional


def build_mtf_alignment(tf_data: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    """
    Build MTF alignment from existing TF data.
    
    tf_data = {
        "1D": {"pattern": {...}, "bias": "bullish"},
        "4H": {"pattern": {...}, "bias": "neutral"},
        "7D": {"pattern": {...}, "bias": "bullish"}
    }
    
    Returns:
        {
            "direction": "bullish" | "bearish" | "neutral",
            "confidence": 0.0 - 1.0,
            "alignment": "aligned" | "mixed" | "conflicting",
            "tf_breakdown": {...}
        }
    """
    biases = []
    tf_breakdown = {}

    for tf, data in tf_data.items():
        # Try to get bias from pattern first, then from structure
        pattern = data.get("pattern") or data.get("primary_pattern")
        structure = data.get("structure_context") or data.get("structure", {})
        
        bias = "neutral"
        
        if pattern:
            bias = pattern.get("bias") or pattern.get("direction", "neutral")
        elif structure:
            bias = structure.get("bias", "neutral")
        
        # Normalize bias
        if bias in ("bullish", "up", "long"):
            bias = "bullish"
        elif bias in ("bearish", "down", "short"):
            bias = "bearish"
        else:
            bias = "neutral"
            
        biases.append(bias)
        tf_breakdown[tf] = bias

    # Count
    bullish = biases.count("bullish")
    bearish = biases.count("bearish")
    neutral = biases.count("neutral")
    total = len(biases) or 1

    # Determine overall direction
    if bullish > bearish and bullish > neutral:
        direction = "bullish"
    elif bearish > bullish and bearish > neutral:
        direction = "bearish"
    else:
        direction = "neutral"

    # Calculate confidence
    dominant = max(bullish, bearish)
    confidence = dominant / total if total > 0 else 0

    # Determine alignment status
    if dominant >= total * 0.8:
        alignment = "aligned"
    elif bullish > 0 and bearish > 0:
        alignment = "conflicting"
    else:
        alignment = "mixed"

    return {
        "direction": direction,
        "confidence": round(confidence, 2),
        "alignment": alignment,
        "tf_breakdown": tf_breakdown,
        "stats": {
            "bullish_count": bullish,
            "bearish_count": bearish,
            "neutral_count": neutral,
            "total": total,
        }
    }


def get_alignment_summary(alignment: Dict[str, Any]) -> str:
    """
    Get human-readable alignment summary.
    """
    direction = alignment.get("direction", "neutral")
    confidence = alignment.get("confidence", 0)
    status = alignment.get("alignment", "mixed")
    
    if status == "aligned":
        if direction == "bullish":
            return f"Strong bullish alignment ({int(confidence*100)}% confidence)"
        elif direction == "bearish":
            return f"Strong bearish alignment ({int(confidence*100)}% confidence)"
        else:
            return "Timeframes aligned in neutral stance"
    elif status == "conflicting":
        return "Conflicting signals across timeframes — exercise caution"
    else:
        return "Mixed signals — wait for clearer alignment"


# Factory
def get_mtf_alignment_engine():
    return {
        "build_mtf_alignment": build_mtf_alignment,
        "get_alignment_summary": get_alignment_summary,
    }
