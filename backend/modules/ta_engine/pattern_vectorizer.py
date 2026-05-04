"""
Pattern Vectorizer — Feature Extraction for Similarity
=======================================================

Extracts numerical features from patterns for similarity comparison.
Features are normalized to [0,1] range for cosine similarity.
"""

from typing import Dict, Optional


def build_pattern_vector(pattern: Dict) -> Dict:
    """
    Build normalized feature vector from pattern.
    
    Features:
    - height_pct: pattern height as % of price
    - duration: number of bars
    - volatility: internal volatility
    - slope: trend direction (-1 to 1)
    - confidence: detection confidence
    """
    if not pattern:
        return None
    
    # Extract raw features
    raw = {
        "type": pattern.get("type", "unknown"),
        "height_pct": _extract_height_pct(pattern),
        "duration": _extract_duration(pattern),
        "volatility": _extract_volatility(pattern),
        "slope": _extract_slope(pattern),
        "confidence": pattern.get("confidence", 0.5),
        "bias": pattern.get("bias", "neutral"),
        "regime": pattern.get("regime") or pattern.get("market_state", "unknown"),
    }
    
    # Normalize for similarity
    normalized = normalize_vector(raw)
    
    return {
        "raw": raw,
        "normalized": normalized,
    }


def _extract_height_pct(pattern: Dict) -> float:
    """Extract pattern height as percentage of price."""
    top = pattern.get("top") or pattern.get("channel_top") or pattern.get("resistance")
    bottom = pattern.get("bottom") or pattern.get("channel_bottom") or pattern.get("support")
    
    if top and bottom and bottom > 0:
        return abs(top - bottom) / bottom * 100
    
    # Try from range
    if pattern.get("range"):
        r = pattern["range"]
        if r.get("top") and r.get("bottom") and r["bottom"] > 0:
            return abs(r["top"] - r["bottom"]) / r["bottom"] * 100
    
    return 0


def _extract_duration(pattern: Dict) -> int:
    """Extract pattern duration in bars."""
    if pattern.get("duration_bars"):
        return pattern["duration_bars"]
    
    if pattern.get("start_index") is not None and pattern.get("end_index") is not None:
        return abs(pattern["end_index"] - pattern["start_index"])
    
    # Estimate from window
    if pattern.get("window"):
        return pattern["window"].get("size", 20)
    
    return 20  # default


def _extract_volatility(pattern: Dict) -> float:
    """Extract internal volatility."""
    if pattern.get("volatility"):
        return pattern["volatility"]
    
    if pattern.get("channel_width"):
        return pattern["channel_width"]
    
    # Estimate from height
    height = _extract_height_pct(pattern)
    duration = _extract_duration(pattern)
    
    if duration > 0:
        return height / duration * 10  # rough estimate
    
    return 0.5


def _extract_slope(pattern: Dict) -> float:
    """Extract trend slope (-1 to 1)."""
    if pattern.get("slope"):
        return max(-1, min(1, pattern["slope"]))
    
    bias = pattern.get("bias", "neutral")
    if bias == "bullish":
        return 0.5
    elif bias == "bearish":
        return -0.5
    
    return 0


def normalize_vector(raw: Dict) -> Dict:
    """Normalize features to [0,1] range for similarity."""
    return {
        "height_pct": min(raw.get("height_pct", 0) / 20, 1),  # 20% max
        "duration": min(raw.get("duration", 0) / 100, 1),  # 100 bars max
        "volatility": min(raw.get("volatility", 0) / 0.1, 1),  # 10% max
        "slope": (raw.get("slope", 0) + 1) / 2,  # -1..1 -> 0..1
        "confidence": raw.get("confidence", 0.5),
    }


def vector_keys() -> list:
    """Get keys used for similarity comparison."""
    return ["height_pct", "duration", "volatility", "slope", "confidence"]


__all__ = ["build_pattern_vector", "normalize_vector", "vector_keys"]
