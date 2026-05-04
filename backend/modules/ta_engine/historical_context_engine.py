"""
Historical Context Engine
==========================

Pattern × Context × History → Learning Layer

KEY CONCEPT:
- Pattern alone ≠ Signal
- Pattern × Context = Signal  
- Pattern × Context × History = INTELLIGENT Signal

WHAT THIS DOES:
1. Builds a unique key from pattern + context combination
2. Retrieves historical performance for that key
3. Computes historical fit (winrate, avg move, resolution time)
4. Adjusts confidence based on historical performance
5. TIME-WEIGHTED STATS (recency decay) — recent outcomes weigh more
6. DRIFT DETECTION — detects if edge is improving/degrading

SCORING:
- STRONG (≥65% winrate): +15% confidence boost
- GOOD (≥55%): +8% boost
- NEUTRAL (45-55%): no change
- WEAK (<45%): -8% penalty
- POOR (<35%): -15% penalty
- INSUFFICIENT (<10 samples): no adjustment

ADJUSTMENT RANGE: 0.85x to 1.15x (soft, no overcorrection)

RECENCY DECAY:
- HALF_LIFE_DAYS = 30 (outcomes older than 30 days have 50% weight)
- Recent outcomes influence more than old ones
- System adapts to changing market conditions
"""

from typing import Dict, List, Optional, Any
from datetime import datetime, timezone
import math


# ═══════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════

HALF_LIFE_DAYS = 30  # Key parameter: outcomes lose 50% weight after 30 days
MIN_SAMPLES = 10     # Minimum samples for historical adjustment


def build_history_key(pattern: Dict, context: Dict) -> str:
    """
    Build unique key from pattern + context combination.
    
    Key format: {pattern_type}|{regime}|{structure}|{impulse}|{volatility}
    Example: "descending_triangle|compression|bearish|down|mid"
    
    Args:
        pattern: Pattern object with type, direction, stage
        context: Market context from context_engine
    
    Returns:
        Pipe-separated key string
    """
    pattern_type = str(pattern.get("type", "unknown")).lower().replace(" ", "_").replace("-", "_")
    regime = str(context.get("regime", "unknown")).lower()
    structure = str(context.get("structure", "neutral")).lower()
    impulse = str(context.get("impulse", "none")).lower()
    volatility = str(context.get("volatility", "mid")).lower()
    
    return "|".join([pattern_type, regime, structure, impulse, volatility])


# ═══════════════════════════════════════════════════════════════
# RECENCY DECAY / TIME WEIGHTING
# ═══════════════════════════════════════════════════════════════

def time_weight(ts: float, half_life_days: int = HALF_LIFE_DAYS) -> float:
    """
    Calculate exponential decay weight based on age.
    
    Recent outcomes have weight close to 1.0
    Old outcomes decay towards 0
    
    Args:
        ts: Unix timestamp of the record
        half_life_days: Days after which weight is 50%
    
    Returns:
        Weight between 0 and 1
    """
    now = datetime.now(timezone.utc).timestamp()
    age_days = max(0.0, (now - ts) / 86400)
    return math.exp(-age_days / half_life_days)


def get_timestamp(record: Dict) -> float:
    """Extract timestamp from record, handling various formats."""
    created_at = record.get("created_at")
    
    if isinstance(created_at, datetime):
        return created_at.timestamp()
    elif isinstance(created_at, (int, float)):
        return float(created_at)
    elif isinstance(created_at, str):
        try:
            dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
            return dt.timestamp()
        except:
            pass
    
    # Default: assume recent if no timestamp
    return datetime.now(timezone.utc).timestamp()


# ═══════════════════════════════════════════════════════════════
# WEIGHTED STATISTICS (with recency decay)
# ═══════════════════════════════════════════════════════════════

def compute_weighted_stats(records: List[Dict], half_life_days: int = HALF_LIFE_DAYS) -> Optional[Dict]:
    """
    Compute time-weighted statistics from historical records.
    
    Recent outcomes have more weight than older ones.
    
    Args:
        records: List of outcome records from MongoDB
        half_life_days: Decay half-life in days
    
    Returns:
        Weighted stats or None if insufficient data
    """
    if not records:
        return None
    
    # Filter valid records
    valid_records = [r for r in records if r.get("outcome") in ("win", "loss")]
    
    if not valid_records:
        return None
    
    weighted_wins = 0.0
    weighted_losses = 0.0
    total_weight = 0.0
    weighted_move = 0.0
    weighted_time = 0.0
    
    raw_wins = 0
    raw_losses = 0
    
    for r in valid_records:
        ts = get_timestamp(r)
        w = time_weight(ts, half_life_days)
        
        total_weight += w
        
        if r.get("outcome") == "win":
            weighted_wins += w
            raw_wins += 1
        else:
            weighted_losses += w
            raw_losses += 1
        
        move = float(r.get("move_pct", 0) or 0)
        duration = float(r.get("duration_h", 0) or 0)
        
        weighted_move += move * w
        weighted_time += duration * w
    
    wl_sum = weighted_wins + weighted_losses
    if wl_sum == 0 or total_weight == 0:
        return None
    
    # Raw stats (unweighted)
    raw_total = raw_wins + raw_losses
    raw_winrate = raw_wins / raw_total if raw_total > 0 else 0
    
    # Weighted stats
    weighted_winrate = weighted_wins / wl_sum
    
    # Calculate avg move and time
    moves = [float(r.get("move_pct", 0) or 0) for r in valid_records]
    durations = [float(r.get("duration_h", 0) or 0) for r in valid_records]
    
    return {
        "samples": len(valid_records),
        "weighted_samples": round(total_weight, 2),
        "wins": raw_wins,
        "losses": raw_losses,
        "winrate": round(weighted_winrate, 4),
        "raw_winrate": round(raw_winrate, 4),
        "avg_move_pct": round(weighted_move / total_weight, 2) if total_weight > 0 else 0,
        "avg_resolution_h": round(weighted_time / total_weight, 1) if total_weight > 0 else 0,
        "best_move_pct": round(max(moves), 2) if moves else 0,
        "worst_move_pct": round(min(moves), 2) if moves else 0,
    }


def compute_stats(records: List[Dict]) -> Optional[Dict]:
    """
    Compute statistics from historical outcome records.
    Uses weighted stats by default.
    
    Args:
        records: List of outcome records from MongoDB
    
    Returns:
        Stats object or None if insufficient data
    """
    return compute_weighted_stats(records)


# ═══════════════════════════════════════════════════════════════
# DRIFT DETECTION
# ═══════════════════════════════════════════════════════════════

def detect_drift(records: List[Dict], recent_n: int = 10, min_total: int = 20) -> Dict:
    """
    Detect if pattern performance is improving or degrading.
    
    Compares recent N outcomes vs older outcomes.
    
    Args:
        records: Historical outcome records
        recent_n: Number of recent records to compare
        min_total: Minimum total records for drift detection
    
    Returns:
        Drift analysis with label and delta
    """
    if not records or len(records) < min_total:
        return {
            "label": "INSUFFICIENT",
            "delta": None,
            "recent_winrate": None,
            "old_winrate": None,
            "message": f"Need {min_total}+ samples for drift detection"
        }
    
    # Sort by timestamp
    def get_sort_key(r):
        return get_timestamp(r)
    
    ordered = sorted(records, key=get_sort_key)
    
    # Split into recent and old
    recent = ordered[-recent_n:]
    old = ordered[:-recent_n]
    
    if len(old) < recent_n:
        return {
            "label": "INSUFFICIENT",
            "delta": None,
            "recent_winrate": None,
            "old_winrate": None,
            "message": "Not enough historical data for comparison"
        }
    
    # Calculate winrates
    wr_recent = sum(1 for r in recent if r.get("outcome") == "win") / len(recent)
    wr_old = sum(1 for r in old if r.get("outcome") == "win") / len(old)
    
    delta = round(wr_recent - wr_old, 4)
    
    # Determine drift label
    if delta > 0.15:
        label = "STRONG_IMPROVING"
        message = f"Edge strengthening significantly (+{int(delta*100)}%)"
    elif delta > 0.08:
        label = "IMPROVING"
        message = f"Recent performance improving (+{int(delta*100)}%)"
    elif delta < -0.15:
        label = "STRONG_DEGRADING"
        message = f"Edge weakening significantly ({int(delta*100)}%)"
    elif delta < -0.08:
        label = "DEGRADING"
        message = f"Recent performance declining ({int(delta*100)}%)"
    else:
        label = "STABLE"
        message = "Performance consistent over time"
    
    return {
        "label": label,
        "delta": delta,
        "recent_winrate": round(wr_recent, 4),
        "old_winrate": round(wr_old, 4),
        "message": message,
    }


# ═══════════════════════════════════════════════════════════════
# HISTORICAL FIT SCORING
# ═══════════════════════════════════════════════════════════════

def compute_historical_fit(stats: Optional[Dict], min_samples: int = MIN_SAMPLES) -> Dict:
    """
    Compute historical fit score and label from stats.
    
    Args:
        stats: Stats from compute_stats()
        min_samples: Minimum samples required for adjustment
    
    Returns:
        Historical fit object with score, label, confidence
    """
    if not stats or stats.get("samples", 0) < min_samples:
        return {
            "score": 1.0,
            "label": "INSUFFICIENT",
            "winrate": None,
            "samples": stats.get("samples", 0) if stats else 0,
            "reason": f"Need {min_samples}+ samples for historical adjustment",
        }
    
    winrate = stats["winrate"]
    samples = stats["samples"]
    
    # Map winrate to multiplier (soft adjustment)
    if winrate >= 0.65:
        score = 1.15
        label = "STRONG"
        reason = f"Historically strong ({int(winrate*100)}% winrate over {samples} samples)"
    elif winrate >= 0.55:
        score = 1.08
        label = "GOOD"
        reason = f"Good historical performance ({int(winrate*100)}% winrate)"
    elif winrate >= 0.45:
        score = 1.0
        label = "NEUTRAL"
        reason = f"Neutral historical performance ({int(winrate*100)}% winrate)"
    elif winrate >= 0.35:
        score = 0.92
        label = "WEAK"
        reason = f"Below average historical performance ({int(winrate*100)}% winrate)"
    else:
        score = 0.85
        label = "POOR"
        reason = f"Poor historical performance ({int(winrate*100)}% winrate)"
    
    return {
        "score": score,
        "label": label,
        "winrate": winrate,
        "samples": samples,
        "reason": reason,
    }


def apply_historical_adjustment(confidence: float, hist_fit: Dict) -> float:
    """
    Apply historical fit adjustment to confidence.
    
    Soft adjustment with clamping to prevent overcorrection.
    
    Args:
        confidence: Current confidence (0.0 to 1.0)
        hist_fit: Historical fit from compute_historical_fit()
    
    Returns:
        Adjusted confidence (clamped to 0.05 - 0.95)
    """
    if not hist_fit or hist_fit.get("label") == "INSUFFICIENT":
        return confidence
    
    score = hist_fit.get("score", 1.0)
    adjusted = confidence * score
    
    # Clamp to reasonable range
    return round(max(0.05, min(0.95, adjusted)), 4)


def get_tradeable_from_historical(hist_fit: Dict) -> bool:
    """
    Determine if setup should be tradeable based on historical performance.
    
    POOR historical fit → not tradeable
    """
    label = hist_fit.get("label", "NEUTRAL")
    return label not in ("POOR",)


def build_historical_summary(stats: Optional[Dict], hist_fit: Dict, drift: Optional[Dict] = None) -> str:
    """
    Build human-readable summary for frontend.
    """
    if hist_fit.get("label") == "INSUFFICIENT":
        samples = hist_fit.get("samples", 0)
        return f"Insufficient historical data ({samples} samples, need 10+)"
    
    winrate = hist_fit.get("winrate", 0)
    samples = hist_fit.get("samples", 0)
    label = hist_fit.get("label", "NEUTRAL")
    
    base = f"{label}: {int(winrate*100)}% winrate ({samples} samples)"
    
    if stats:
        avg_move = stats.get("avg_move_pct", 0)
        avg_time = stats.get("avg_resolution_h", 0)
        base += f", avg {avg_move}% move in {avg_time}h"
    
    # Add drift info
    if drift and drift.get("label") not in ("INSUFFICIENT", None):
        drift_label = drift.get("label")
        if drift_label in ("IMPROVING", "STRONG_IMPROVING"):
            base += " ↑"
        elif drift_label in ("DEGRADING", "STRONG_DEGRADING"):
            base += " ↓"
    
    return base


# ═══════════════════════════════════════════════════════════════
# FULL PIPELINE FUNCTION
# ═══════════════════════════════════════════════════════════════

def evaluate_historical_context(
    pattern: Dict,
    context: Dict,
    records: List[Dict],
    min_samples: int = MIN_SAMPLES,
) -> Dict:
    """
    Full pipeline: build key → compute stats → get fit → detect drift → return result.
    
    Args:
        pattern: Pattern object
        context: Market context
        records: Historical outcome records for this key
        min_samples: Minimum samples for adjustment
    
    Returns:
        Complete historical context evaluation with drift
    """
    key = build_history_key(pattern, context)
    stats = compute_weighted_stats(records)
    hist_fit = compute_historical_fit(stats, min_samples)
    drift = detect_drift(records)
    summary = build_historical_summary(stats, hist_fit, drift)
    
    return {
        "key": key,
        "stats": stats,
        "fit": hist_fit,
        "drift": drift,
        "summary": summary,
    }
