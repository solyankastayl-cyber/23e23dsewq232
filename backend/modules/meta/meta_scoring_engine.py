"""
Meta Scoring Engine — production-ready math of decision (Pass 4)

Pipeline:
    combined_analysis → strategy_score → allocation → risk-aware allocation
                       (compute_strategy_score)  (compute_allocation)  (apply_risk_guard)

CRITICAL CONTRACT:
  * No fallback values, no fabrication.
  * LOW quality   → score = 0.0
  * No data       → score = 0.0
  * CRITICAL risk → allocation = 0.0
  * No hypothesis → engine still works (just no booster)
  * sample<30     → no booster, base_score *= 0.5 (demote noise)
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional


# ════════════════════════════════════════════════════════════════════════════
# 1. STRATEGY SCORE — heart of the engine
# ════════════════════════════════════════════════════════════════════════════

def compute_strategy_score(analysis: Optional[Dict[str, Any]]) -> float:
    """
    Convert combined_analysis → strategy_score in [0..1].

    Formula:
        base = agreement * 0.5 + ta_conf * 0.3 + pred_conf * 0.2

        if hypothesis present:
            if sample_size < 30:        base *= 0.5         (noise demote)
            else:
                boost = min(1, PF/2)
                base *= boost

        return clamp(base, 0..1)

    Hard zero conditions:
        * analysis is None or empty
        * quality == "LOW"
        * agreement.score is None
    """
    if not analysis:
        return 0.0

    quality = (analysis.get("quality") or "LOW").upper()
    if quality == "LOW":
        return 0.0  # ❗ honest hard filter

    agreement_block = analysis.get("agreement") or {}
    agreement = agreement_block.get("score")
    if agreement is None:
        return 0.0
    agreement = _clamp01(agreement)

    ta = analysis.get("ta") or {}
    pr = analysis.get("prediction") or {}

    ta_conf = _clamp01(ta.get("confidence"))
    pred_conf = _clamp01(pr.get("confidence"))

    base_score = (
        agreement * 0.5
        + ta_conf * 0.3
        + pred_conf * 0.2
    )

    # Hypothesis modulator
    hypo = analysis.get("hypothesis")
    if hypo:
        pf = float(hypo.get("profit_factor") or 0.0)
        sample = int(hypo.get("sample_size") or 0)

        if sample < 30:
            # ❗ noise protection — demote, do NOT zero out
            base_score *= 0.5
        elif pf > 0:
            boost = min(1.0, pf / 2.0)
            base_score *= boost
        # PF == 0 with valid sample → no change (neutral)

    return _clamp01(base_score)


# ════════════════════════════════════════════════════════════════════════════
# 2. ALLOCATION — confidence weight, NOT a position size
# ════════════════════════════════════════════════════════════════════════════

def compute_allocation(score: float) -> float:
    """
    Map strategy_score (0..1) → allocation weight (0..1).

    Tiered to avoid micro-positions and over-allocation:
      < 0.30          → 0.00   (no edge)
      [0.30, 0.50)    → 0.10   (toe-dip)
      [0.50, 0.70)    → 0.25   (small)
      [0.70, 0.85)    → 0.50   (moderate)
      ≥ 0.85          → 1.00   (full conviction within meta layer)

    NOTE: This is NOT money. Position sizing happens downstream in execution
    layer with portfolio-aware risk caps.
    """
    s = _clamp01(score)
    if s < 0.30:
        return 0.0
    if s < 0.50:
        return 0.10
    if s < 0.70:
        return 0.25
    if s < 0.85:
        return 0.50
    return 1.0


# ════════════════════════════════════════════════════════════════════════════
# 3. RISK GUARD INTEGRATION (P0.6 system_health)
# ════════════════════════════════════════════════════════════════════════════

# Map any health string to canonical {HEALTHY, WARNING, CRITICAL}.
_HEALTH_MAP = {
    "healthy": "HEALTHY",
    "ok": "HEALTHY",
    "good": "HEALTHY",
    "running": "HEALTHY",
    "warning": "WARNING",
    "warn": "WARNING",
    "degraded": "WARNING",
    "critical": "CRITICAL",
    "fatal": "CRITICAL",
    "down": "CRITICAL",
    "error": "CRITICAL",
}


def normalize_health_status(raw: Any) -> str:
    """
    Normalize any provider's health tag → {HEALTHY, WARNING, CRITICAL}.
    Unknown / missing → "WARNING" (conservative default — never silently HEALTHY).
    """
    if raw is None:
        return "WARNING"
    s = str(raw).strip().lower()
    return _HEALTH_MAP.get(s, "WARNING")


def apply_risk_guard(allocation: float, health: Optional[Dict[str, Any]]) -> float:
    """
    Cut allocation based on system health.

      CRITICAL → 0.0
      WARNING  → halve
      HEALTHY  → unchanged
      missing  → treated as WARNING (conservative)
    """
    a = max(0.0, min(1.0, float(allocation or 0.0)))
    status = normalize_health_status((health or {}).get("status"))
    if status == "CRITICAL":
        return 0.0
    if status == "WARNING":
        return a * 0.5
    return a


# ════════════════════════════════════════════════════════════════════════════
# 4. META DECISION — final composer
# ════════════════════════════════════════════════════════════════════════════

def build_meta_decision(
    analysis: Optional[Dict[str, Any]],
    health: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Compose the final meta decision payload.

    Returns:
      {
        "symbol", "timeframe",
        "strategy_score": 0..1,
        "allocation": 0..1,
        "final_bias": bullish|bearish|neutral,
        "quality": HIGH|MEDIUM|LOW,
        "risk_status": HEALTHY|WARNING|CRITICAL,
        "should_trade": bool,
        "reason": str,           # human-readable summary
        "components": {...},     # transparency block
        "timestamp": ISO-8601
      }

    Hard zeros:
      * analysis None / quality=LOW / no agreement → score=0, allocation=0
      * CRITICAL risk → allocation forced to 0 (regardless of score)
    """
    score = compute_strategy_score(analysis)
    allocation_pre_guard = compute_allocation(score)
    allocation = apply_risk_guard(allocation_pre_guard, health)

    risk_status = normalize_health_status((health or {}).get("status"))
    quality = (analysis or {}).get("quality") or "LOW"
    final_bias = (analysis or {}).get("final_bias") or "neutral"
    symbol = (analysis or {}).get("symbol")
    timeframe = (analysis or {}).get("timeframe")

    should_trade = allocation > 0.0

    # Reason — explicit failure ladder so the user knows why allocation=0
    if not analysis:
        reason = "no analysis available"
    elif quality == "LOW":
        reason = "quality=LOW (score forced to 0)"
    elif score == 0.0:
        reason = "strategy_score=0 (no edge)"
    elif risk_status == "CRITICAL":
        reason = "system risk CRITICAL (allocation forced to 0)"
    elif risk_status == "WARNING":
        reason = "system risk WARNING (allocation halved)"
    elif allocation == 0.0:
        reason = f"strategy_score={score:.3f} below allocation threshold"
    else:
        reason = f"score={score:.3f} → allocation={allocation:.2f} ({final_bias})"

    return {
        "symbol": symbol,
        "timeframe": timeframe,
        "strategy_score": round(score, 4),
        "allocation": round(allocation, 4),
        "allocation_pre_risk": round(allocation_pre_guard, 4),
        "final_bias": final_bias,
        "quality": quality,
        "risk_status": risk_status,
        "should_trade": should_trade,
        "reason": reason,
        "components": {
            "agreement": (analysis or {}).get("agreement", {}).get("score"),
            "ta_confidence": ((analysis or {}).get("ta") or {}).get("confidence"),
            "prediction_confidence": ((analysis or {}).get("prediction") or {}).get("confidence"),
            "hypothesis": _hypothesis_summary((analysis or {}).get("hypothesis")),
            "validation_issues": ((analysis or {}).get("validation") or {}).get("issues") or [],
        },
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def _hypothesis_summary(hypo: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if not hypo:
        return None
    return {
        "strategy": hypo.get("strategy"),
        "direction": hypo.get("direction"),
        "profit_factor": hypo.get("profit_factor"),
        "win_rate": hypo.get("win_rate"),
        "sample_size": hypo.get("sample_size"),
        "verdict": hypo.get("verdict"),
    }


# ════════════════════════════════════════════════════════════════════════════
# Helpers
# ════════════════════════════════════════════════════════════════════════════

def _clamp01(v: Any) -> float:
    try:
        n = float(v)
    except (TypeError, ValueError):
        return 0.0
    if not (n == n):  # NaN
        return 0.0
    return max(0.0, min(1.0, n))
