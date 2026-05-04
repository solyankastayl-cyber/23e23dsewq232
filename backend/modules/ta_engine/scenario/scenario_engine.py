"""
Scenario Engine
================

Generates actionable trading scenarios from pattern analysis.

V2: Uses ScenarioEngineV2 for production-quality output with:
- Primary scenario with probability, summary, action
- Alternative scenario with trigger/invalidation
"""

from typing import List, Dict, Optional
from .scenario_engine_v2 import get_scenario_engine_v2


def generate_scenarios(
    primary_pattern: Optional[Dict],
    alternative_patterns: List[Dict],
    decision: Dict,
    structure_context: Optional[Dict] = None,
    base_layer: Optional[Dict] = None,
    current_price: Optional[float] = None
) -> List[Dict]:
    """
    Generate trading scenarios using ScenarioEngineV2.
    
    V2: Structure-first actionable scenarios.
    Output format:
    [
      {
        type: "primary",
        direction: "bearish",
        title: "Bearish continuation after weak bounce",
        probability: 0.62,
        summary: "Market remains in markdown conditions...",
        action: "wait rejection from 89200 / target 68200",
        trigger: "rejection below 89200",
        invalidation: "reclaim above 89200"
      },
      {
        type: "alternative",
        direction: "bullish",
        ...
      }
    ]
    """
    engine = get_scenario_engine_v2()
    
    # Build base_layer from structure_context if not provided
    if base_layer is None and structure_context:
        base_layer = {
            "supports": structure_context.get("active_supports", []),
            "resistances": structure_context.get("active_resistances", []),
            "trendlines": structure_context.get("active_trendlines", []),
            "channels": [],
        }
    base_layer = base_layer or {"supports": [], "resistances": [], "trendlines": [], "channels": []}
    
    # Use current_price from decision or estimate
    if current_price is None:
        current_price = 0.0
    
    result = engine.build(
        structure_context=structure_context or {},
        base_layer=base_layer,
        current_price=current_price,
        decision=decision or {},
        primary_pattern=primary_pattern,
        alternative_patterns=alternative_patterns or [],
    )
    
    return result.get("scenarios", [])


def _build_no_pattern_summary(regime, phase, bias, last_event, structure_context):
    """Build intelligent summary when no pattern is detected."""
    ctx = structure_context or {}
    supports = ctx.get("active_supports", [])
    resistances = ctx.get("active_resistances", [])
    
    support_str = f" Support at {supports[0]['price']:.0f}." if supports else ""
    resist_str = f" Resistance at {resistances[0]['price']:.0f}." if resistances else ""
    levels_str = support_str + resist_str
    
    if regime == "range":
        return {
            "title": "Range-bound consolidation",
            "text": f"Market in {phase} phase. Price oscillating between fixed levels.{levels_str} No dominant pattern — trade the range boundaries or wait for breakout.",
            "action": "range_trade"
        }
    if regime == "compression":
        return {
            "title": "Compression — breakout expected",
            "text": f"Volatility compressing. Price narrowing into a decision point.{levels_str} Watch for directional breakout.",
            "action": "wait_for_breakout"
        }
    if regime in ["trend_up", "expansion"] and bias == "bullish":
        return {
            "title": "Bullish structure continues",
            "text": f"Uptrend with HH/HL structure intact.{levels_str} No clear pattern overlay, but bullish bias persists.",
            "action": "buy_pullback"
        }
    if regime in ["trend_down", "expansion"] and bias == "bearish":
        return {
            "title": "Bearish structure continues",
            "text": f"Downtrend with LH/LL structure intact.{levels_str} No clear pattern overlay, but bearish bias persists.",
            "action": "sell_rally"
        }
    if regime in ["accumulation"]:
        return {
            "title": "Potential accumulation zone",
            "text": f"Range near lows with signs of bullish pressure.{levels_str} Watch for breakout above resistance.",
            "action": "wait_for_confirmation"
        }
    if regime in ["distribution"]:
        return {
            "title": "Potential distribution zone",
            "text": f"Range near highs with signs of bearish pressure.{levels_str} Watch for breakdown below support.",
            "action": "wait_for_confirmation"
        }
    if "choch" in last_event:
        direction = "up" if "up" in last_event else "down"
        return {
            "title": f"Change of Character {direction}",
            "text": f"Structure shift detected ({last_event}).{levels_str} Possible reversal forming — wait for confirmation.",
            "action": "wait_for_confirmation"
        }
    
    return {
        "title": "No dominant pattern",
        "text": f"Market structure: {regime}.{levels_str} No high-confidence pattern detected. Wait for clarity.",
        "action": "wait"
    }


def _build_primary_scenario(
    direction: str,
    confidence: float,
    pattern_type: str,
    market_state: str,
    bias: str
) -> Dict:
    """Build primary trading scenario."""
    
    # Direction-specific scenarios
    if direction == "bullish":
        if market_state == "compression":
            title = "Bullish breakout from compression"
            summary = f"Price is compressing inside a {pattern_type}. Expect upside breakout if resistance clears."
            action = "wait_for_breakout_long"
        elif market_state == "trend":
            title = "Bullish continuation"
            summary = f"{pattern_type.replace('_', ' ').title()} suggests continuation of uptrend. Look for pullback entries."
            action = "buy_pullback"
        else:
            title = "Bullish reversal setup"
            summary = f"Structure suggests potential reversal to upside from {pattern_type}."
            action = "wait_for_confirmation"
            
    elif direction == "bearish":
        if market_state == "compression":
            title = "Bearish breakdown from compression"
            summary = f"Price is compressing inside a {pattern_type}. Expect downside if support fails."
            action = "wait_for_breakdown_short"
        elif market_state == "trend":
            title = "Bearish continuation"
            summary = f"{pattern_type.replace('_', ' ').title()} suggests continuation of downtrend. Look for rally entries."
            action = "sell_rally"
        else:
            title = "Bearish reversal setup"
            summary = f"Structure suggests potential reversal to downside from {pattern_type}."
            action = "wait_for_confirmation"
    else:
        title = "Range continuation"
        summary = f"Market likely remains inside current {pattern_type}. Trade the range boundaries."
        action = "range_trade"
    
    return {
        "type": "primary",
        "title": title,
        "direction": direction,
        "probability": round(confidence, 2),
        "summary": summary,
        "action": action,
        "pattern": pattern_type
    }


def _build_alternative_scenario(
    alt_pattern: Dict,
    primary_direction: str,
    market_state: str
) -> Dict:
    """Build alternative scenario from backup pattern."""
    
    alt_type = alt_pattern.get("type", "unknown")
    alt_direction = alt_pattern.get("direction", "neutral")
    alt_confidence = alt_pattern.get("confidence", 0.4)
    
    if alt_direction == primary_direction:
        # Same direction = weaker version of primary
        title = f"Alternative: {alt_type.replace('_', ' ').title()}"
        summary = f"If primary pattern fails, {alt_type} may still provide similar directional bias."
    else:
        # Opposite direction = reversal of primary
        title = f"Reversal: {alt_type.replace('_', ' ').title()}"
        summary = f"If primary scenario fails, {alt_type} suggests opposite move. Watch for invalidation."
    
    return {
        "type": "alternative",
        "title": title,
        "direction": alt_direction,
        "probability": round(alt_confidence, 2),
        "summary": summary,
        "action": "contingency",
        "pattern": alt_type
    }


def _build_fallback_alternative(
    primary_direction: str,
    confidence: float,
    market_state: str
) -> Dict:
    """Build fallback alternative when no alt patterns exist."""
    
    inverse_prob = round(1 - confidence, 2)
    
    if primary_direction == "bullish":
        return {
            "type": "alternative",
            "title": "False breakout and rejection",
            "direction": "bearish",
            "probability": min(0.4, inverse_prob),
            "summary": "If bullish breakout fails, expect rejection and return to range or lower.",
            "action": "stop_loss",
            "pattern": None
        }
    elif primary_direction == "bearish":
        return {
            "type": "alternative",
            "title": "False breakdown and recovery",
            "direction": "bullish",
            "probability": min(0.4, inverse_prob),
            "summary": "If bearish breakdown fails, expect recovery and potential squeeze higher.",
            "action": "stop_loss",
            "pattern": None
        }
    else:
        return {
            "type": "alternative",
            "title": "Range breakout",
            "direction": "neutral",
            "probability": 0.35,
            "summary": "Consolidation may resolve with directional breakout. Watch boundary tests.",
            "action": "wait",
            "pattern": None
        }


def build_confidence_explanation(pattern: Optional[Dict]) -> Dict:
    """
    Extract and format confidence scores for UI display.
    
    Returns dict of scores with human labels.
    """
    if not pattern:
        return {}
    
    scores = pattern.get("scores", {})
    
    # Map raw scores to human-readable labels
    explanation = {}
    
    if "geometry" in scores:
        explanation["geometry"] = {
            "value": scores["geometry"],
            "label": "Pattern Shape Quality",
            "status": _score_status(scores["geometry"])
        }
    
    if "structure" in scores:
        explanation["structure"] = {
            "value": scores["structure"],
            "label": "Structure Alignment",
            "status": _score_status(scores["structure"])
        }
    
    if "level" in scores:
        explanation["level"] = {
            "value": scores["level"],
            "label": "Level Confluence",
            "status": _score_status(scores["level"])
        }
    
    if "recency" in scores:
        explanation["recency"] = {
            "value": scores["recency"],
            "label": "Pattern Freshness",
            "status": _score_status(scores["recency"])
        }
    
    if "cleanliness" in scores:
        explanation["cleanliness"] = {
            "value": scores["cleanliness"],
            "label": "Pattern Cleanliness",
            "status": _score_status(scores["cleanliness"])
        }
    
    return explanation


def _score_status(score: float) -> str:
    """Convert score to status label."""
    if score >= 0.8:
        return "strong"
    elif score >= 0.6:
        return "good"
    elif score >= 0.4:
        return "moderate"
    else:
        return "weak"


# Singleton access
scenario_engine = {
    "generate_scenarios": generate_scenarios,
    "build_confidence_explanation": build_confidence_explanation
}
