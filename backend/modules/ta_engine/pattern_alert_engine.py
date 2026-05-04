"""
Pattern Alert Engine — Smart Alert System
==========================================

PRINCIPLE: Minimal alerts, maximum value.

Alert Types:
1. LIFECYCLE TRIGGER (HIGH) - forming → confirmed_up/down
2. PROBABILITY THRESHOLD (MEDIUM) - probability > 70%
3. LEVEL HIT (LOW) - price near breakout/breakdown level

Features:
- Deduplication
- Cooldown (15 min default)
- Severity levels
- Combined alerts (reduce spam)
"""

from typing import Dict, List, Optional
from datetime import datetime, timezone
import time


# In-memory state tracking (per symbol)
_alert_states: Dict[str, Dict] = {}
_last_sent: Dict[str, Dict[str, float]] = {}


def build_alert_state(
    pattern: Dict,
    probabilities: Dict,
    price: float,
    levels: List[Dict],
    symbol: str = "UNKNOWN",
) -> Dict:
    """
    Build current alert state snapshot.
    """
    return {
        "symbol": symbol,
        "pattern_type": pattern.get("type") if pattern else None,
        "lifecycle": pattern.get("lifecycle") if pattern else None,
        "confidence": pattern.get("confidence") if pattern else None,
        "prob_up": probabilities.get("breakout_up", 0) if probabilities else 0,
        "prob_down": probabilities.get("breakdown", 0) if probabilities else 0,
        "price": price,
        "levels": levels or [],
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def detect_alerts(
    prev: Optional[Dict],
    curr: Dict,
    threshold_probability: float = 0.70,
    level_distance_pct: float = 0.02,
) -> List[Dict]:
    """
    Detect alerts by comparing previous and current state.
    
    Returns list of alert dicts with type, severity, message.
    """
    alerts = []
    
    if not curr:
        return alerts
    
    symbol = curr.get("symbol", "")
    
    # 1. LIFECYCLE CHANGE (HIGH severity)
    if prev:
        prev_lc = prev.get("lifecycle")
        curr_lc = curr.get("lifecycle")
        
        if prev_lc != curr_lc:
            if curr_lc == "confirmed_up":
                alerts.append({
                    "type": "lifecycle",
                    "severity": "HIGH",
                    "message": f"{curr['pattern_type']} CONFIRMED UP",
                    "symbol": symbol,
                    "action": "Bullish breakout confirmed",
                })
            elif curr_lc == "confirmed_down":
                alerts.append({
                    "type": "lifecycle",
                    "severity": "HIGH",
                    "message": f"{curr['pattern_type']} CONFIRMED DOWN",
                    "symbol": symbol,
                    "action": "Bearish breakdown confirmed",
                })
            elif curr_lc == "invalidated":
                alerts.append({
                    "type": "lifecycle",
                    "severity": "MEDIUM",
                    "message": f"{curr['pattern_type']} INVALIDATED",
                    "symbol": symbol,
                    "action": "Pattern no longer valid",
                })
    
    # 2. PROBABILITY THRESHOLD (MEDIUM severity)
    if prev:
        prev_up = prev.get("prob_up", 0)
        curr_up = curr.get("prob_up", 0)
        prev_down = prev.get("prob_down", 0)
        curr_down = curr.get("prob_down", 0)
        
        # Bullish probability crossed threshold
        if prev_up < threshold_probability and curr_up >= threshold_probability:
            alerts.append({
                "type": "probability",
                "severity": "MEDIUM",
                "message": f"Bullish probability > {int(threshold_probability * 100)}%",
                "symbol": symbol,
                "value": round(curr_up * 100, 1),
            })
        
        # Bearish probability crossed threshold
        if prev_down < threshold_probability and curr_down >= threshold_probability:
            alerts.append({
                "type": "probability",
                "severity": "MEDIUM",
                "message": f"Bearish probability > {int(threshold_probability * 100)}%",
                "symbol": symbol,
                "value": round(curr_down * 100, 1),
            })
    
    # 3. LEVEL HIT (LOW severity)
    price = curr.get("price", 0)
    if price > 0:
        for lvl in curr.get("levels", []):
            lvl_price = lvl.get("price", 0)
            if lvl_price <= 0:
                continue
            
            distance = abs(price - lvl_price) / lvl_price
            if distance < level_distance_pct:
                lvl_type = lvl.get("type", "level")
                alerts.append({
                    "type": "level_hit",
                    "severity": "LOW",
                    "message": f"Price near {lvl_type} level",
                    "symbol": symbol,
                    "level_price": lvl_price,
                    "current_price": price,
                    "distance_pct": round(distance * 100, 2),
                })
    
    return alerts


def should_send(
    alert: Dict,
    symbol: str,
    cooldown_sec: int = 900,  # 15 min default
) -> bool:
    """
    Check if alert should be sent (not recently sent).
    """
    global _last_sent
    
    key = f"{symbol}_{alert.get('type')}_{alert.get('severity')}"
    
    if symbol not in _last_sent:
        _last_sent[symbol] = {}
    
    if key not in _last_sent[symbol]:
        return True
    
    last_time = _last_sent[symbol][key]
    now = time.time()
    
    return (now - last_time) > cooldown_sec


def mark_sent(alert: Dict, symbol: str):
    """
    Mark alert as sent (update last sent time).
    """
    global _last_sent
    
    key = f"{symbol}_{alert.get('type')}_{alert.get('severity')}"
    
    if symbol not in _last_sent:
        _last_sent[symbol] = {}
    
    _last_sent[symbol][key] = time.time()


def merge_alerts(alerts: List[Dict]) -> Optional[Dict]:
    """
    Merge multiple alerts into single combined alert.
    Reduces notification spam.
    """
    if not alerts:
        return None
    
    if len(alerts) == 1:
        return alerts[0]
    
    # Get highest severity
    severity_order = {"HIGH": 3, "MEDIUM": 2, "LOW": 1}
    max_severity = max(alerts, key=lambda a: severity_order.get(a.get("severity", "LOW"), 0))
    
    return {
        "type": "combined",
        "severity": max_severity.get("severity"),
        "message": " | ".join(a.get("message", "") for a in alerts),
        "symbol": alerts[0].get("symbol", ""),
        "count": len(alerts),
        "alerts": alerts,
    }


def format_telegram_alert(alert: Dict, symbol: str = None) -> str:
    """
    Format alert for Telegram notification.
    """
    sym = symbol or alert.get("symbol", "UNKNOWN")
    severity = alert.get("severity", "LOW")
    
    # Severity emoji
    emoji = "🔴" if severity == "HIGH" else "🟡" if severity == "MEDIUM" else "🔵"
    
    # Build message
    lines = [
        f"{emoji} <b>{sym}</b>",
        "",
        alert.get("message", ""),
    ]
    
    # Add action if present
    if alert.get("action"):
        lines.append("")
        lines.append(f"→ {alert['action']}")
    
    # Add value if present
    if alert.get("value"):
        lines.append(f"Value: {alert['value']}%")
    
    lines.append("")
    lines.append("#FOMOcx #Alert")
    
    return "\n".join(lines)


# Severity filter presets
SEVERITY_FILTERS = {
    "user": ["HIGH", "MEDIUM"],  # User bot: important alerts only
    "admin": ["HIGH", "MEDIUM", "LOW"],  # Admin bot: all alerts
    "critical_only": ["HIGH"],  # Only critical alerts
}


def filter_by_severity(
    alerts: List[Dict],
    preset: str = "user",
) -> List[Dict]:
    """
    Filter alerts by severity preset.
    """
    allowed = SEVERITY_FILTERS.get(preset, SEVERITY_FILTERS["user"])
    return [a for a in alerts if a.get("severity") in allowed]


def process_alert_pipeline(
    symbol: str,
    pattern: Dict,
    probabilities: Dict,
    price: float,
    levels: List[Dict],
    severity_preset: str = "user",
    cooldown_sec: int = 900,
) -> List[Dict]:
    """
    Full alert processing pipeline.
    
    Returns list of alerts that should be sent.
    """
    global _alert_states
    
    # Build current state
    curr = build_alert_state(pattern, probabilities, price, levels, symbol)
    
    # Get previous state
    prev = _alert_states.get(symbol)
    
    # Detect alerts
    alerts = detect_alerts(prev, curr)
    
    # Filter by severity
    alerts = filter_by_severity(alerts, severity_preset)
    
    # Filter by cooldown
    alerts = [a for a in alerts if should_send(a, symbol, cooldown_sec)]
    
    # Mark as sent
    for a in alerts:
        mark_sent(a, symbol)
    
    # Update state
    _alert_states[symbol] = curr
    
    return alerts


__all__ = [
    "build_alert_state",
    "detect_alerts",
    "should_send",
    "mark_sent",
    "merge_alerts",
    "format_telegram_alert",
    "filter_by_severity",
    "process_alert_pipeline",
]
