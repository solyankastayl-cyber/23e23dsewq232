"""
MTF Context Engine — Multi-Timeframe Market Intelligence
=========================================================

Takes structure analysis from multiple timeframes and produces
a single unified understanding of WHERE we are in the market.

This runs BEFORE decision and scenarios.

Pipeline:
    levels → structure → patterns → MTF_CONTEXT → decision → scenarios

Output:
    {
        "global_bias": "bearish",
        "local_context": "relief_bounce",
        "alignment": "mixed",
        "dominant_tf": "30D",
        "confidence": 0.68,
        "summary": "Short-term bounce inside bearish higher timeframe structure"
    }
"""

from typing import Dict, Any, Optional


TF_WEIGHTS = {
    "4H": 1,
    "1D": 3,
    "7D": 5,
    "30D": 8,
    "180D": 10,
    "1Y": 12,
}

# Ordered from short to long
TF_ORDER = ["4H", "1D", "7D", "30D", "180D", "1Y"]


def compute_global_bias(tf_data: Dict[str, Dict[str, Any]]) -> str:
    """Weighted bias aggregation across timeframes."""
    score = 0

    for tf, data in tf_data.items():
        weight = TF_WEIGHTS.get(tf, 1)
        bias = data.get("bias", "neutral")

        if bias == "bullish":
            score += weight
        elif bias == "bearish":
            score -= weight

    if score > 5:
        return "bullish"
    elif score < -5:
        return "bearish"
    return "neutral"


def compute_alignment(tf_data: Dict[str, Dict[str, Any]]) -> str:
    """Check if all timeframes agree on direction."""
    biases = [d.get("bias", "neutral") for d in tf_data.values() if d.get("bias") != "neutral"]

    if not biases:
        return "neutral"
    if all(b == "bullish" for b in biases):
        return "full_bullish"
    if all(b == "bearish" for b in biases):
        return "full_bearish"
    return "mixed"


def compute_confidence(tf_data: Dict[str, Dict[str, Any]], alignment: str) -> float:
    """
    Confidence = how much we trust the global bias.
    Full alignment → high confidence.
    Mixed → lower confidence.
    """
    total_weight = 0
    aligned_weight = 0
    global_bias = compute_global_bias(tf_data)

    for tf, data in tf_data.items():
        weight = TF_WEIGHTS.get(tf, 1)
        total_weight += weight
        if data.get("bias") == global_bias:
            aligned_weight += weight

    if total_weight == 0:
        return 0.5

    base = aligned_weight / total_weight

    # Bonus for full alignment
    if alignment in ("full_bullish", "full_bearish"):
        base = min(1.0, base + 0.1)

    return round(base, 2)


def detect_dominant_tf(tf_data: Dict[str, Dict[str, Any]]) -> str:
    """Find the highest-weight TF that has a clear bias."""
    best_tf = "1D"
    best_weight = 0

    for tf in TF_ORDER:
        if tf not in tf_data:
            continue
        bias = tf_data[tf].get("bias", "neutral")
        weight = TF_WEIGHTS.get(tf, 1)
        if bias != "neutral" and weight > best_weight:
            best_weight = weight
            best_tf = tf

    return best_tf


def detect_local_context(tf_data: Dict[str, Dict[str, Any]], current_tf: str) -> str:
    """
    Detect local context by comparing short vs long TF bias.

    Returns:
        "relief_bounce"       — long bearish, short bullish
        "pullback"            — long bullish, short bearish
        "trend_continuation"  — aligned
        "compression"         — neutral everywhere
        "reversal_candidate"  — CHOCH on key TF
    """
    # Get short and long TF biases
    ordered = [tf for tf in TF_ORDER if tf in tf_data]
    if len(ordered) < 2:
        return "trend_continuation"

    short_tf = ordered[0]
    long_tf = ordered[-1]

    short_bias = tf_data[short_tf].get("bias", "neutral")
    long_bias = tf_data[long_tf].get("bias", "neutral")

    # Check for CHOCH events
    for tf in ordered:
        last_event = tf_data[tf].get("last_event", "none")
        if "choch" in last_event:
            return "reversal_candidate"

    if long_bias == "bearish" and short_bias == "bullish":
        return "relief_bounce"

    if long_bias == "bullish" and short_bias == "bearish":
        return "pullback"

    if long_bias == "neutral" and short_bias == "neutral":
        return "compression"

    return "trend_continuation"


def build_summary(
    global_bias: str,
    local_context: str,
    alignment: str,
    dominant_tf: str,
    tf_data: Dict[str, Dict[str, Any]],
) -> str:
    """Build human-readable one-line summary."""

    # Find which TF has the CHOCH/BOS event
    event_tf = None
    for tf in TF_ORDER:
        if tf in tf_data and "choch" in tf_data[tf].get("last_event", ""):
            event_tf = tf
            break

    bias_word = "Bullish" if global_bias == "bullish" else "Bearish" if global_bias == "bearish" else "Neutral"

    summaries = {
        "relief_bounce": "Short-term bounce inside bearish higher timeframe structure",
        "pullback": "Pullback within bullish higher timeframe trend",
        "trend_continuation": f"{bias_word} trend aligned across timeframes",
        "compression": "No clear direction — market compressed across timeframes",
        "reversal_candidate": f"Potential reversal: structural break detected on {event_tf or dominant_tf}",
    }

    base = summaries.get(local_context, f"Market context: {local_context}")

    if alignment == "mixed" and local_context == "trend_continuation":
        base = "Directional bias exists but timeframes are not fully aligned"

    return base


def build_mtf_context(
    tf_data: Dict[str, Dict[str, Any]],
    current_tf: str = "1D",
) -> Dict[str, Any]:
    """
    Main entry point. Takes structure analysis from multiple TFs,
    returns unified MTF context.

    Args:
        tf_data: {
            "1D": {"bias": "bearish", "regime": "expansion", "last_event": "choch_up", ...},
            "7D": {"bias": "bearish", "regime": "trend_down", ...},
            "30D": {"bias": "bearish", "regime": "trend_down", ...},
        }
        current_tf: The TF user is viewing

    Returns:
        MTF context dict
    """
    if not tf_data:
        return {
            "global_bias": "neutral",
            "local_context": "unknown",
            "alignment": "neutral",
            "dominant_tf": current_tf,
            "confidence": 0.5,
            "summary": "Insufficient multi-timeframe data",
            "tf_breakdown": {},
        }

    global_bias = compute_global_bias(tf_data)
    alignment = compute_alignment(tf_data)
    confidence = compute_confidence(tf_data, alignment)
    dominant_tf = detect_dominant_tf(tf_data)
    local_context = detect_local_context(tf_data, current_tf)
    summary = build_summary(global_bias, local_context, alignment, dominant_tf, tf_data)

    # Per-TF breakdown for transparency
    tf_breakdown = {}
    for tf in TF_ORDER:
        if tf not in tf_data:
            continue
        d = tf_data[tf]
        tf_breakdown[tf] = {
            "bias": d.get("bias", "neutral"),
            "regime": d.get("regime", "unknown"),
            "last_event": d.get("last_event", "none"),
        }

    return {
        "global_bias": global_bias,
        "local_context": local_context,
        "alignment": alignment,
        "dominant_tf": dominant_tf,
        "confidence": confidence,
        "summary": summary,
        "tf_breakdown": tf_breakdown,
    }
