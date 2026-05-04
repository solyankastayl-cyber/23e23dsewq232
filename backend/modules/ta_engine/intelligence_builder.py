"""
Intelligence Builder — Unified Decision Payload
================================================

Builds the intelligence scorecard payload combining:
- Market state
- Dominant pattern
- MTF context
- Similarity/Probability
- Watch levels
- Next action
"""

from typing import Dict, List, Optional


def build_next_action(pattern: Dict, lifecycle: str = None) -> str:
    """
    Build next action recommendation based on pattern state.
    """
    lc = lifecycle or pattern.get("lifecycle", "forming")
    ptype = pattern.get("type", "")
    
    if lc == "confirmed_up":
        return "Uptrend continuation in progress"
    
    if lc == "confirmed_down":
        return "Downtrend continuation in progress"
    
    if lc == "invalidated":
        return "Pattern invalidated. Previous scenario void."
    
    # Forming patterns
    if ptype in ["triangle", "symmetrical_triangle"]:
        return "Breakout will define direction"
    
    if ptype in ["ascending_triangle"]:
        return "Bias up. Wait for breakout confirmation"
    
    if ptype in ["descending_triangle"]:
        return "Bias down. Wait for breakdown confirmation"
    
    if ptype in ["rectangle", "loose_range", "range"]:
        return "Range bound. Trade levels or wait for breakout"
    
    if ptype in ["double_top", "triple_top", "head_and_shoulders"]:
        return "Bearish reversal forming. Watch neckline"
    
    if ptype in ["double_bottom", "triple_bottom"]:
        return "Bullish reversal forming. Watch neckline"
    
    if ptype in ["bull_flag", "pennant"]:
        return "Bullish continuation. Wait for breakout"
    
    if ptype in ["bear_flag"]:
        return "Bearish continuation. Wait for breakdown"
    
    if ptype in ["rising_wedge"]:
        return "Bearish bias. Watch for breakdown"
    
    if ptype in ["falling_wedge"]:
        return "Bullish bias. Watch for breakout"
    
    return "Monitor structure development"


def build_intelligence_payload(
    market_state: str,
    dominant_pattern: Dict,
    lifecycle: Dict = None,
    mtf_context: Dict = None,
    watch_levels: List[Dict] = None,
    probabilities: Dict = None,
    similarity_matches: List[Dict] = None,
    live_probability: Dict = None,
    bayesian_probability: Dict = None,
    performance: Dict = None,
) -> Dict:
    """
    Build the complete intelligence payload for the scorecard.
    
    V2 additions:
    - live_probability: Real-time probability from price action
    - bayesian_probability: Prior + posterior with evidence
    
    V3 additions:
    - performance: Historical pattern performance (win rate, etc.)
    """
    lc = lifecycle or {}
    lc_state = lc.get("state", dominant_pattern.get("lifecycle", "forming"))
    
    payload = {
        # Market state
        "market_state": market_state,
        
        # Dominant pattern
        "dominant": {
            "type": dominant_pattern.get("type"),
            "confidence": round(dominant_pattern.get("confidence", 0), 2),
            "lifecycle": lc_state,
            "bias": dominant_pattern.get("bias", "neutral"),
        },
        
        # MTF context
        "mtf": None,
        
        # Next action
        "next_action": build_next_action(dominant_pattern, lc_state),
        
        # Watch levels (top 4)
        "watch_levels": [],
        
        # Historical probability
        "probabilities": probabilities,
        
        # Live probability (real-time)
        "live_probability": live_probability,
        
        # Bayesian probability (prior + posterior)
        "bayesian_probability": bayesian_probability,
        
        # Performance stats (self-learning)
        "performance": performance,
        
        # Similarity info
        "similarity": None,
    }
    
    # Add MTF context if available
    if mtf_context:
        payload["mtf"] = {
            "timeframe": mtf_context.get("timeframe", "1D"),
            "state": mtf_context.get("market_state"),
            "has_range": mtf_context.get("range") is not None,
            "bias": mtf_context.get("bias"),
        }
    
    # Add watch levels (filtered, max 4)
    if watch_levels:
        filtered_levels = []
        for lvl in watch_levels[:4]:
            if lvl.get("price"):
                filtered_levels.append({
                    "price": round(lvl["price"], 2),
                    "type": lvl.get("type", "level"),
                    "label": lvl.get("label", ""),
                })
        payload["watch_levels"] = filtered_levels
    
    # Add similarity info
    if similarity_matches:
        payload["similarity"] = {
            "count": len(similarity_matches),
            "top_matches": [
                {
                    "type": m.get("pattern", {}).get("type"),
                    "similarity": m.get("similarity"),
                    "outcome": m.get("outcome"),
                }
                for m in similarity_matches[:3]
            ],
        }
    
    return payload


__all__ = ["build_next_action", "build_intelligence_payload"]
