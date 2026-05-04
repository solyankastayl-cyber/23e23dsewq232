"""
Scanner Logger

Logs each scan result for monitoring and debugging.
Format: symbol, tf, pattern, trend, direction, target, confidence

USAGE:
    from modules.scanner.scan_logger import log_scan_result, get_recent_logs
"""

import time
import json
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from pathlib import Path


# Log file path
LOG_DIR = Path("/app/backend/logs")
LOG_FILE = LOG_DIR / "scanner_log.jsonl"


def ensure_log_dir():
    """Create log directory if not exists."""
    LOG_DIR.mkdir(parents=True, exist_ok=True)


def log_scan_result(
    symbol: str,
    timeframe: str,
    ta_payload: Dict[str, Any],
    prediction: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Log a scan result for monitoring.
    
    Returns the log entry for confirmation.
    """
    ensure_log_dir()
    
    # Extract key fields
    pattern = ta_payload.get("pattern", {})
    structure = ta_payload.get("structure", {})
    direction = prediction.get("direction", {})
    confidence = prediction.get("confidence", {})
    
    # Build log entry
    entry = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "symbol": symbol,
        "tf": timeframe,
        "price": ta_payload.get("price", 0),
        # Pattern
        "pattern": pattern.get("type", "none"),
        "pattern_dir": pattern.get("direction", "neutral"),
        "pattern_conf": round(pattern.get("confidence", 0), 2),
        # Structure
        "state": structure.get("state", "unknown"),
        "trend": structure.get("trend", "flat"),
        "trend_str": round(structure.get("trend_strength", 0), 2),
        # Prediction
        "pred_dir": direction.get("label", "neutral"),
        "pred_score": round(direction.get("score", 0), 3),
        "conf_value": round(confidence.get("value", 0), 2),
        "conf_label": confidence.get("label", "LOW"),
        # Target (from base scenario)
        "target": prediction.get("scenarios", {}).get("base", {}).get("target_price"),
        "expected_return": round(
            prediction.get("scenarios", {}).get("base", {}).get("expected_return", 0), 4
        ),
        # Regime
        "regime": prediction.get("regime", "unknown"),
        "regime_conf": round(prediction.get("regime_confidence", 0), 2),
        "model": prediction.get("model", "unknown"),
        # P2: Decision Engine fields
        "stability": round(prediction.get("stability", 0), 3),
        "stability_label": prediction.get("stability_label", "?"),
        "valid": prediction.get("valid", False),
        "score": round(prediction.get("score", 0), 4),
        "rejection_reason": prediction.get("rejection_reason"),
        # Meta
        "ta_source": ta_payload.get("_ta_source", "unknown"),
        "ta_regime": ta_payload.get("_ta_layers_regime", "unknown"),
        "error": ta_payload.get("_error"),
    }
    
    # Append to log file
    try:
        with open(LOG_FILE, "a") as f:
            f.write(json.dumps(entry) + "\n")
    except Exception as e:
        print(f"[ScanLogger] Write error: {e}")
    
    return entry


def get_recent_logs(limit: int = 50) -> List[Dict[str, Any]]:
    """
    Get recent scan logs.
    
    Returns list of log entries, newest first.
    """
    if not LOG_FILE.exists():
        return []
    
    try:
        with open(LOG_FILE, "r") as f:
            lines = f.readlines()
        
        # Parse and reverse (newest first)
        logs = []
        for line in reversed(lines[-limit:]):
            try:
                logs.append(json.loads(line.strip()))
            except json.JSONDecodeError:
                continue
        
        return logs
    except Exception as e:
        print(f"[ScanLogger] Read error: {e}")
        return []


def get_logs_summary() -> Dict[str, Any]:
    """
    Get summary statistics from logs.
    
    Returns:
        - total_scans
        - valid/invalid counts (P2)
        - direction_distribution
        - pattern_distribution
        - regime_distribution
        - avg_confidence, avg_stability (P2)
        - metrics_by_regime
    """
    logs = get_recent_logs(limit=500)
    
    if not logs:
        return {"total_scans": 0}
    
    # Count directions
    dir_counts = {"bullish": 0, "bearish": 0, "neutral": 0}
    pattern_counts = {}
    regime_counts = {}
    confidences = []
    stabilities = []
    symbols = set()
    
    # P2: valid/invalid tracking
    valid_count = 0
    invalid_count = 0
    rejection_reasons = {}
    
    # Metrics by regime
    regime_metrics = {}
    
    for log in logs:
        symbols.add(log.get("symbol", ""))
        
        pred_dir = log.get("pred_dir", "neutral")
        dir_counts[pred_dir] = dir_counts.get(pred_dir, 0) + 1
        
        pattern = log.get("pattern", "none")
        pattern_counts[pattern] = pattern_counts.get(pattern, 0) + 1
        
        regime = log.get("regime", "unknown")
        regime_counts[regime] = regime_counts.get(regime, 0) + 1
        
        conf = log.get("conf_value", 0)
        if conf > 0:
            confidences.append(conf)
        
        stability = log.get("stability", 0)
        if stability > 0:
            stabilities.append(stability)
        
        # P2: valid tracking
        if log.get("valid", False):
            valid_count += 1
        else:
            invalid_count += 1
            reason = log.get("rejection_reason")
            if reason:
                rejection_reasons[reason] = rejection_reasons.get(reason, 0) + 1
        
        # Aggregate by regime
        if regime not in regime_metrics:
            regime_metrics[regime] = {
                "count": 0,
                "bullish": 0,
                "bearish": 0,
                "neutral": 0,
                "valid": 0,
                "confidence_sum": 0,
                "stability_sum": 0,
            }
        rm = regime_metrics[regime]
        rm["count"] += 1
        rm[pred_dir] = rm.get(pred_dir, 0) + 1
        rm["confidence_sum"] += conf
        rm["stability_sum"] += stability
        if log.get("valid"):
            rm["valid"] += 1
    
    # Compute regime-level stats
    for regime, rm in regime_metrics.items():
        rm["avg_confidence"] = round(rm["confidence_sum"] / rm["count"], 3) if rm["count"] > 0 else 0
        rm["avg_stability"] = round(rm["stability_sum"] / rm["count"], 3) if rm["count"] > 0 else 0
        rm["valid_pct"] = round(rm["valid"] / rm["count"], 2) if rm["count"] > 0 else 0
        rm["bullish_pct"] = round(rm["bullish"] / rm["count"], 2) if rm["count"] > 0 else 0
        rm["bearish_pct"] = round(rm["bearish"] / rm["count"], 2) if rm["count"] > 0 else 0
        del rm["confidence_sum"]
        del rm["stability_sum"]
    
    return {
        "total_scans": len(logs),
        "unique_symbols": len(symbols),
        # P2: Decision Engine stats
        "valid_predictions": valid_count,
        "invalid_predictions": invalid_count,
        "valid_rate": round(valid_count / len(logs), 2) if logs else 0,
        "rejection_reasons": rejection_reasons,
        # Distributions
        "direction_distribution": dir_counts,
        "pattern_distribution": pattern_counts,
        "regime_distribution": regime_counts,
        "metrics_by_regime": regime_metrics,
        # Averages
        "avg_confidence": round(sum(confidences) / len(confidences), 3) if confidences else 0,
        "avg_stability": round(sum(stabilities) / len(stabilities), 3) if stabilities else 0,
        # Bias checks
        "always_bullish": dir_counts.get("bearish", 0) == 0 and dir_counts.get("bullish", 0) > 0,
        "always_bearish": dir_counts.get("bullish", 0) == 0 and dir_counts.get("bearish", 0) > 0,
    }


def clear_logs():
    """Clear all logs."""
    if LOG_FILE.exists():
        LOG_FILE.unlink()
    return {"status": "cleared"}
