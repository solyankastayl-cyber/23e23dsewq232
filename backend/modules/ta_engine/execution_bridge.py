"""
Execution Bridge
================

Converts probability + expectation into actionable execution plan.

INPUT:
- Pattern (direction, confidence)
- Expectation (move_pct, resolution_h)
- Levels (breakout, breakdown)
- Current price

OUTPUT:
{
    "entry": 71800,
    "stop": 67300,
    "target": 75200,
    "rr": 1.8,
    "time_window": {"expected_hours": 34, "max_hold_hours": 51},
    "entry_type": "breakout",
    "quality": "HIGH"
}

QUALITY LEVELS:
- HIGH: R/R >= 2.0
- MEDIUM: R/R >= 1.2
- LOW: R/R < 1.2 (not recommended)

This is the final bridge from analysis to action.
"""

from typing import Dict, Optional, Any


def build_execution_plan(
    pattern: Dict,
    expectation: Dict,
    levels: Dict,
    current_price: float,
    min_confidence: float = 0.55,
) -> Optional[Dict]:
    """
    Build execution plan from pattern + expectation + levels.
    
    Args:
        pattern: Pattern with direction, confidence
        expectation: Expected move_pct and resolution_h
        levels: Breakout/breakdown levels
        current_price: Current price for calculations
    
    Returns:
        Execution plan or None if insufficient data
    """
    # Check minimum confidence
    confidence = pattern.get("confidence", 0)
    if confidence < min_confidence:
        return {
            "status": "SKIP",
            "reason": f"Confidence too low ({int(confidence*100)}% < {int(min_confidence*100)}%)",
            "quality": "INSUFFICIENT",
        }
    
    # Check expectation
    if not expectation or expectation.get("move_pct") is None:
        return {
            "status": "SKIP",
            "reason": "No expectation data available",
            "quality": "INSUFFICIENT",
        }
    
    move_pct = expectation.get("move_pct", 0)
    time_h = expectation.get("resolution_h", 24)
    
    if move_pct <= 0:
        return {
            "status": "SKIP",
            "reason": "Expected move too small",
            "quality": "INSUFFICIENT",
        }
    
    direction = pattern.get("direction", pattern.get("bias", "neutral"))
    
    # ═══════════════════════════════════════════════════════════════
    # DETERMINE ENTRY AND STOP
    # ═══════════════════════════════════════════════════════════════
    
    # Get levels from various sources
    breakout_up = levels.get("breakout_up") or levels.get("breakout") or levels.get("resistance")
    breakdown_down = levels.get("breakdown_down") or levels.get("breakdown") or levels.get("support")
    
    # Fallback to pattern levels if not in levels dict
    if not breakout_up:
        breakout_up = pattern.get("breakout_level") or pattern.get("resistance")
    if not breakdown_down:
        breakdown_down = pattern.get("breakdown_level") or pattern.get("support")
    
    # Use current price as fallback
    if not breakout_up:
        breakout_up = current_price * 1.02  # 2% above
    if not breakdown_down:
        breakdown_down = current_price * 0.98  # 2% below
    
    # Determine entry and stop based on direction
    if direction == "bullish":
        entry = float(breakout_up)
        stop = float(breakdown_down)
        target = entry * (1 + move_pct / 100)
        entry_type = "breakout_long"
    elif direction == "bearish":
        entry = float(breakdown_down)
        stop = float(breakout_up)
        target = entry * (1 - move_pct / 100)
        entry_type = "breakdown_short"
    else:
        # Neutral - can't build execution plan
        return {
            "status": "SKIP",
            "reason": "Neutral direction - no clear entry",
            "quality": "INSUFFICIENT",
        }
    
    # ═══════════════════════════════════════════════════════════════
    # CALCULATE RISK/REWARD
    # ═══════════════════════════════════════════════════════════════
    
    risk = abs(entry - stop)
    reward = abs(target - entry)
    
    if risk <= 0:
        return {
            "status": "SKIP",
            "reason": "Invalid risk calculation (entry = stop)",
            "quality": "INSUFFICIENT",
        }
    
    rr = reward / risk
    
    # ═══════════════════════════════════════════════════════════════
    # DETERMINE QUALITY
    # ═══════════════════════════════════════════════════════════════
    
    if rr >= 2.5:
        quality = "EXCELLENT"
        quality_reason = f"Outstanding R/R ({rr:.1f}:1)"
    elif rr >= 2.0:
        quality = "HIGH"
        quality_reason = f"Strong R/R ({rr:.1f}:1)"
    elif rr >= 1.5:
        quality = "GOOD"
        quality_reason = f"Good R/R ({rr:.1f}:1)"
    elif rr >= 1.2:
        quality = "MEDIUM"
        quality_reason = f"Acceptable R/R ({rr:.1f}:1)"
    elif rr >= 1.0:
        quality = "LOW"
        quality_reason = f"Marginal R/R ({rr:.1f}:1) - extra caution"
    else:
        quality = "POOR"
        quality_reason = f"Poor R/R ({rr:.1f}:1) - not recommended"
    
    # ═══════════════════════════════════════════════════════════════
    # TIME WINDOW
    # ═══════════════════════════════════════════════════════════════
    
    time_window = {
        "expected_hours": round(time_h, 1),
        "max_hold_hours": round(time_h * 1.5, 1),
        "expected_days": round(time_h / 24, 1),
        "max_hold_days": round(time_h * 1.5 / 24, 1),
    }
    
    # ═══════════════════════════════════════════════════════════════
    # POSITION SIZING SUGGESTION (% of account)
    # ═══════════════════════════════════════════════════════════════
    
    risk_pct = abs(entry - stop) / entry * 100
    
    # Suggest position size based on 1% account risk
    # position_size = 1% / risk_pct
    suggested_position = round(1.0 / risk_pct * 100, 1) if risk_pct > 0 else 0
    
    # ═══════════════════════════════════════════════════════════════
    # BUILD RESPONSE
    # ═══════════════════════════════════════════════════════════════
    
    return {
        "status": "ACTIVE",
        "direction": direction,
        "entry": round(entry, 2),
        "stop": round(stop, 2),
        "target": round(target, 2),
        "current_price": round(current_price, 2),
        
        # Risk/Reward
        "risk": round(risk, 2),
        "reward": round(reward, 2),
        "rr": round(rr, 2),
        "risk_pct": round(risk_pct, 2),
        
        # Time
        "time_window": time_window,
        
        # Metadata
        "entry_type": entry_type,
        "quality": quality,
        "quality_reason": quality_reason,
        
        # Suggestion
        "suggested_position_pct": min(suggested_position, 100),
    }


def should_trade(execution_plan: Optional[Dict], strict: bool = False) -> bool:
    """
    Determine if execution plan is tradeable.
    
    Args:
        execution_plan: Plan from build_execution_plan()
        strict: If True, require HIGH quality
    
    Returns:
        True if tradeable
    """
    if not execution_plan:
        return False
    
    if execution_plan.get("status") != "ACTIVE":
        return False
    
    quality = execution_plan.get("quality", "INSUFFICIENT")
    rr = execution_plan.get("rr", 0)
    
    if strict:
        return quality in ("EXCELLENT", "HIGH") and rr >= 2.0
    else:
        return quality not in ("POOR", "INSUFFICIENT") and rr >= 1.0


def format_execution_for_ui(execution_plan: Optional[Dict]) -> Dict:
    """
    Format execution plan for frontend display.
    """
    if not execution_plan or execution_plan.get("status") != "ACTIVE":
        return {
            "show": False,
            "reason": execution_plan.get("reason", "No plan available") if execution_plan else "No data",
        }
    
    direction = execution_plan.get("direction", "neutral")
    entry = execution_plan.get("entry", 0)
    stop = execution_plan.get("stop", 0)
    target = execution_plan.get("target", 0)
    rr = execution_plan.get("rr", 0)
    quality = execution_plan.get("quality", "MEDIUM")
    time_h = execution_plan.get("time_window", {}).get("expected_hours", 0)
    
    # Format time
    if time_h < 24:
        time_str = f"~{int(time_h)}h"
    else:
        time_str = f"~{round(time_h / 24, 1)}d"
    
    # Quality badge
    quality_colors = {
        "EXCELLENT": "#16a34a",
        "HIGH": "#22c55e",
        "GOOD": "#84cc16",
        "MEDIUM": "#eab308",
        "LOW": "#f97316",
        "POOR": "#ef4444",
    }
    
    return {
        "show": True,
        "direction": direction,
        "entry": f"${entry:,.0f}",
        "stop": f"${stop:,.0f}",
        "target": f"${target:,.0f}",
        "rr": f"{rr:.1f}:1",
        "time": time_str,
        "quality": quality,
        "quality_color": quality_colors.get(quality, "#64748b"),
        "entry_raw": entry,
        "stop_raw": stop,
        "target_raw": target,
        "risk_pct": f"{execution_plan.get('risk_pct', 0):.1f}%",
    }


def build_execution_summary(execution_plan: Optional[Dict]) -> str:
    """
    Build one-line summary of execution plan.
    """
    if not execution_plan or execution_plan.get("status") != "ACTIVE":
        return execution_plan.get("reason", "No execution plan") if execution_plan else "No data"
    
    direction = execution_plan.get("direction", "")
    entry = execution_plan.get("entry", 0)
    target = execution_plan.get("target", 0)
    rr = execution_plan.get("rr", 0)
    quality = execution_plan.get("quality", "")
    
    arrow = "↑" if direction == "bullish" else "↓"
    
    return f"{arrow} Entry ${entry:,.0f} → Target ${target:,.0f} | R/R {rr:.1f}:1 | {quality}"
