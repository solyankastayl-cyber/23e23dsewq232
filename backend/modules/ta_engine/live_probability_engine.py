"""
Live Probability Engine — Real-time probability updates
========================================================

Updates probability based on:
1. Price position relative to pattern boundaries
2. Recent candle behavior (compression, expansion)
3. Volume changes
4. Time in pattern

This runs AFTER pattern detection and BEFORE UI rendering.
"""

from typing import Dict, Optional, List
from datetime import datetime, timezone


def compute_live_probability(
    pattern: Dict,
    candles: List[Dict],
    prior_probability: Dict = None,
) -> Optional[Dict]:
    """
    Compute live probability update based on current price action.
    
    Args:
        pattern: Dominant pattern dict (must have breakout_level, invalidation)
        candles: Recent candles (last 10-20)
        prior_probability: Historical probability from similarity engine
    
    Returns:
        {
            "breakout_up": 0.71,
            "breakdown": 0.19,
            "neutral": 0.10,
            "edge": "bullish",
            "confidence": 0.71,
            "drift": +0.09,  # change from prior
            "factors": ["price_near_resistance", "volume_increasing"]
        }
    """
    if not pattern or not candles or len(candles) < 5:
        return None
    
    # Extract pattern levels from multiple sources
    breakout_level = pattern.get("breakout_level") or pattern.get("resistance")
    invalidation_level = pattern.get("invalidation") or pattern.get("support")
    
    # Try boundaries (V4 pattern format)
    boundaries = pattern.get("boundaries", [])
    if not breakout_level or not invalidation_level:
        for b in boundaries:
            bid = b.get("id", "")
            if "upper" in bid and not breakout_level:
                # Use y2 (current end of trendline)
                breakout_level = b.get("y2") or b.get("y1")
            if "lower" in bid and not invalidation_level:
                invalidation_level = b.get("y2") or b.get("y1")
    
    # Try meta/boundaries (legacy format)
    if not breakout_level or not invalidation_level:
        meta = pattern.get("meta", {})
        meta_boundaries = meta.get("boundaries", {})
        breakout_level = breakout_level or meta.get("resistance") or meta_boundaries.get("upper", {}).get("y2")
        invalidation_level = invalidation_level or meta.get("support") or meta_boundaries.get("lower", {}).get("y2")
    
    # Try levels array
    if not breakout_level or not invalidation_level:
        levels = pattern.get("levels", [])
        for lvl in levels:
            lvl_type = lvl.get("type", "")
            if "resistance" in lvl_type or "upper" in lvl_type or "breakout" in lvl_type:
                breakout_level = breakout_level or lvl.get("price") or lvl.get("y")
            if "support" in lvl_type or "lower" in lvl_type or "invalidation" in lvl_type:
                invalidation_level = invalidation_level or lvl.get("price") or lvl.get("y")
    
    if not breakout_level or not invalidation_level:
        return None
    
    # Current state
    current_price = candles[-1].get("close", 0)
    current_high = candles[-1].get("high", 0)
    current_low = candles[-1].get("low", 0)
    
    # Calculate range position (0 = at support, 1 = at resistance)
    range_size = breakout_level - invalidation_level
    if range_size <= 0:
        return None
    
    position_in_range = (current_price - invalidation_level) / range_size
    position_in_range = max(0, min(1, position_in_range))  # clamp to [0, 1]
    
    # Factors for probability adjustment
    factors = []
    
    # Factor 1: Position in range
    # Closer to breakout = higher bullish probability
    position_factor = position_in_range - 0.5  # -0.5 to +0.5
    
    # Factor 2: Recent momentum (last 5 candles)
    recent_candles = candles[-5:]
    closes = [c.get("close", 0) for c in recent_candles]
    if len(closes) >= 2:
        momentum = (closes[-1] - closes[0]) / closes[0] if closes[0] > 0 else 0
        momentum_factor = momentum * 10  # scale to reasonable range
        momentum_factor = max(-0.2, min(0.2, momentum_factor))
        
        if momentum_factor > 0.05:
            factors.append("momentum_bullish")
        elif momentum_factor < -0.05:
            factors.append("momentum_bearish")
    else:
        momentum_factor = 0
    
    # Factor 3: Distance to breakout
    distance_to_breakout = (breakout_level - current_price) / current_price if current_price > 0 else 0
    distance_to_breakdown = (current_price - invalidation_level) / current_price if current_price > 0 else 0
    
    if distance_to_breakout < 0.02:  # Within 2%
        factors.append("near_breakout")
        position_factor += 0.1
    elif distance_to_breakdown < 0.02:
        factors.append("near_breakdown")
        position_factor -= 0.1
    
    # Factor 4: Volume (if available)
    volumes = [c.get("volume", 0) for c in recent_candles if c.get("volume")]
    if len(volumes) >= 3:
        avg_vol = sum(volumes[:-1]) / len(volumes[:-1])
        current_vol = volumes[-1]
        if avg_vol > 0 and current_vol > avg_vol * 1.5:
            factors.append("volume_spike")
            # Volume spike in direction of move
            if closes[-1] > closes[-2]:
                position_factor += 0.05
            else:
                position_factor -= 0.05
    
    # Factor 5: Compression (volatility decreasing)
    highs = [c.get("high", 0) for c in recent_candles]
    lows = [c.get("low", 0) for c in recent_candles]
    if highs and lows:
        recent_range = max(highs) - min(lows)
        older_candles = candles[-10:-5] if len(candles) >= 10 else []
        if older_candles:
            older_highs = [c.get("high", 0) for c in older_candles]
            older_lows = [c.get("low", 0) for c in older_candles]
            older_range = max(older_highs) - min(older_lows) if older_highs and older_lows else 0
            
            if older_range > 0 and recent_range < older_range * 0.6:
                factors.append("compression")
    
    # Calculate base probabilities
    base_up = 0.5 + position_factor + momentum_factor
    base_down = 1 - base_up - 0.1  # Leave 10% for neutral
    base_neutral = 0.1
    
    # Normalize
    total = base_up + base_down + base_neutral
    prob_up = max(0.05, min(0.90, base_up / total))
    prob_down = max(0.05, min(0.90, base_down / total))
    prob_neutral = 1 - prob_up - prob_down
    
    # Calculate drift from prior
    drift = 0
    if prior_probability and prior_probability.get("breakout_up"):
        drift = prob_up - prior_probability["breakout_up"]
    
    # Determine edge
    if prob_up > prob_down + 0.15:
        edge = "bullish"
        confidence = prob_up
    elif prob_down > prob_up + 0.15:
        edge = "bearish"
        confidence = prob_down
    else:
        edge = "neutral"
        confidence = max(prob_up, prob_down)
    
    return {
        "breakout_up": round(prob_up, 2),
        "breakdown": round(prob_down, 2),
        "neutral": round(prob_neutral, 2),
        "edge": edge,
        "confidence": round(confidence, 2),
        "drift": round(drift, 3),
        "factors": factors,
        "position_in_range": round(position_in_range, 2),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def apply_bayesian_update(
    prior: Dict,
    live: Dict,
    evidence: List[str] = None,
) -> Dict:
    """
    Apply Bayesian update to combine prior (historical) and live probability.
    
    P(outcome|evidence) ∝ P(evidence|outcome) × P(outcome)
    
    Args:
        prior: Historical probability from similarity engine
        live: Live probability from price action
        evidence: List of evidence factors
    
    Returns:
        Posterior probability with evidence
    """
    if not prior:
        return {
            "posterior_up": live.get("breakout_up", 0.5) if live else 0.5,
            "posterior_down": live.get("breakdown", 0.5) if live else 0.5,
            "prior_up": 0.5,
            "prior_down": 0.5,
            "evidence": evidence or [],
        }
    
    prior_up = prior.get("breakout_up", 0.5)
    prior_down = prior.get("breakdown", 0.5)
    
    if not live:
        return {
            "posterior_up": prior_up,
            "posterior_down": prior_down,
            "prior_up": prior_up,
            "prior_down": prior_down,
            "evidence": evidence or [],
        }
    
    live_up = live.get("breakout_up", 0.5)
    live_down = live.get("breakdown", 0.5)
    
    # Simple weighted combination (0.4 prior + 0.6 live)
    # Live data is more recent, so slightly higher weight
    posterior_up = prior_up * 0.4 + live_up * 0.6
    posterior_down = prior_down * 0.4 + live_down * 0.6
    
    # Normalize
    total = posterior_up + posterior_down
    if total > 0:
        posterior_up = posterior_up / total
        posterior_down = posterior_down / total
    
    return {
        "posterior_up": round(posterior_up, 2),
        "posterior_down": round(posterior_down, 2),
        "prior_up": round(prior_up, 2),
        "prior_down": round(prior_down, 2),
        "evidence": evidence or live.get("factors", []),
    }


__all__ = ["compute_live_probability", "apply_bayesian_update"]
