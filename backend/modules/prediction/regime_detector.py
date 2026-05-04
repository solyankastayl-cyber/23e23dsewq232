"""
Regime Detector

Detects market regime with hysteresis to prevent jumping between states.

Regimes:
- trend: Strong directional movement
- range: Price oscillating between support/resistance
- compression: Tightening volatility, potential breakout
- high_volatility: Extreme price swings

FIX v2:
- Better trend detection using trend_strength
- Higher threshold for compression (0.60 vs 0.40)
- Market context awareness
"""

from typing import Dict, Any, Optional


def detect_regime(ta: Dict[str, Any], prev_regime: Optional[str] = None) -> str:
    """
    Detect market regime from TA output with hysteresis.
    
    Args:
        ta: TA payload with indicators, structure, pattern
        prev_regime: Previous regime (for hysteresis)
    
    Returns:
        Regime string: "trend", "range", "compression", "high_volatility"
    """
    indicators = ta.get("indicators", {})
    structure = ta.get("structure", {})
    pattern = ta.get("pattern", {})
    
    # Extract key metrics
    trend_strength = float(indicators.get("trend_strength", 0))
    volatility_score = float(indicators.get("volatility_score", 0.5))
    momentum = float(indicators.get("momentum", 0))
    abs_momentum = abs(momentum)
    
    # Structure state
    state = structure.get("state", "range")  # trend, range, compression
    trend_dir = structure.get("trend", "flat")  # up, down, flat
    
    # Pattern info
    pattern_type = pattern.get("type", "none")
    pattern_conf = float(pattern.get("confidence", 0))
    
    # === REGIME DETECTION LOGIC (FIX v2: Better prioritization) ===
    
    # 1. High volatility takes priority (market stress)
    if volatility_score > 0.75 or abs_momentum > 0.10:
        regime = "high_volatility"
    
    # 2. TREND detection (NEW: use trend_strength + momentum)
    elif abs(trend_strength) > 0.04 or abs_momentum > 0.04:
        # Strong directional movement = trend
        regime = "trend"
    
    # 3. Explicit trend state from structure
    elif state in ("trend_up", "trend_down", "trend"):
        regime = "trend"
    
    # 4. Compression only for very tight squeeze (60%+ threshold)
    elif volatility_score < 0.35 and pattern_type in [
        "symmetrical_triangle", "ascending_triangle", "descending_triangle",
        "wedge", "pennant", "tight_range", "flag"
    ] and pattern_conf > 0.5:
        regime = "compression"
    
    # 5. Range detection
    elif state in ("range", "accumulation", "distribution"):
        regime = "range"
    
    # 6. Default to range (safest)
    else:
        regime = "range"
    
    # === HYSTERESIS (prevent regime jumping) ===
    if prev_regime and regime != prev_regime:
        # Stay in trend if momentum still present
        if prev_regime == "trend" and abs_momentum > 0.02:
            return "trend"
        
        # Stay in trend if still moderately strong
        if prev_regime == "trend" and abs(trend_strength) > 0.03:
            return "trend"
        
        # Stay in range if trend not clearly established
        if prev_regime == "range" and abs(trend_strength) < 0.05 and abs_momentum < 0.03:
            return "range"
        
        # Stay in compression if pattern still holds
        if prev_regime == "compression" and pattern_conf > 0.5 and volatility_score < 0.40:
            return "compression"
        
        # Exit high_volatility only when clearly calmed
        if prev_regime == "high_volatility" and (volatility_score > 0.5 or abs_momentum > 0.05):
            return "high_volatility"
    
    return regime


def get_regime_confidence(ta: Dict[str, Any], regime: str) -> float:
    """
    Calculate confidence in detected regime.
    
    Returns 0.0-1.0 confidence score.
    """
    indicators = ta.get("indicators", {})
    structure = ta.get("structure", {})
    
    trend_strength = float(indicators.get("trend_strength", 0))
    volatility_score = float(indicators.get("volatility_score", 0))
    state = structure.get("state", "range")
    
    if regime == "trend":
        # Higher trend strength = higher confidence
        return min(0.4 + trend_strength * 0.6, 0.95)
    
    elif regime == "range":
        # Range confidence = inverse of trend strength
        return min(0.5 + (1 - trend_strength) * 0.4, 0.85)
    
    elif regime == "compression":
        # Based on pattern confidence
        pattern_conf = float(ta.get("pattern", {}).get("confidence", 0.5))
        return min(0.4 + pattern_conf * 0.5, 0.9)
    
    elif regime == "high_volatility":
        # Higher volatility = higher confidence
        return min(0.5 + volatility_score * 0.4, 0.95)
    
    return 0.5


def regime_to_model_name(regime: str) -> str:
    """Map regime to model name for tracking."""
    return {
        "trend": "trend_momentum_v1",
        "range": "range_mean_reversion_v1",
        "compression": "compression_breakout_v1",
        "high_volatility": "high_vol_momentum_v1",
    }.get(regime, "fallback_v1")
