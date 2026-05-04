"""
Debug metrics — Tier 1 / 2 / 3 aggregation.

Tier 1 (key):
    direction_accuracy, scenario_accuracy,
    high_confidence_accuracy, low_confidence_accuracy,
    overconfidence_rate, underconfidence_rate

Tier 2 (matters more than ML):
    error_distribution (% per error_type)
    root_causes_top   (top-K with frequency)

Tier 3 (edge insight):
    by_signal_strength (accuracy per strong/moderate/weak)
    by_interaction_type (accuracy per interaction.type)

No accuracy-shlak: every metric explicitly excludes no_edge_ignored unless
stated. Tier 2 includes no_edge in error_distribution to expose noise floor.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any, Dict, List, Optional

from .taxonomy import (
    OVERCONFIDENT_THRESHOLD,
    UNDERCONFIDENT_THRESHOLD,
    ErrorType,
)


def _round(v: Optional[float], n: int = 4) -> Optional[float]:
    if v is None:
        return None
    try:
        return round(float(v), n)
    except (TypeError, ValueError):
        return None


def _safe_div(num: float, den: float) -> Optional[float]:
    if den <= 0:
        return None
    return num / den


def compute_metrics(
    records: List[Dict[str, Any]],
    *,
    high_conf_threshold: float = OVERCONFIDENT_THRESHOLD,
    low_conf_threshold: float = UNDERCONFIDENT_THRESHOLD,
) -> Dict[str, Any]:
    """
    Pure aggregator. Input: list of debug records (dicts) as produced by
    build_debug_record().

    Returns a 3-tier metrics dict + sample sizes.
    """
    n_total = len(records)
    if n_total == 0:
        return _empty_metrics()

    # ── Filter cohorts ────────────────────────────────────────────────────
    actionable = [r for r in records if not r.get("no_edge_ignored")]
    n_actionable = len(actionable)

    # ── Tier 1: direction / scenario accuracy on actionable cohort ───────
    n_dir_correct = sum(1 for r in actionable if r.get("correct_direction"))
    n_scn_correct = sum(1 for r in actionable if r.get("scenario_correct"))

    high_conf = [
        r for r in actionable
        if (r.get("decision_confidence") or 0.0) >= high_conf_threshold
    ]
    low_conf = [
        r for r in actionable
        if (r.get("decision_confidence") or 0.0) < low_conf_threshold
    ]
    n_high = len(high_conf)
    n_low = len(low_conf)
    n_high_correct = sum(1 for r in high_conf if r.get("correct_direction"))
    n_low_correct = sum(1 for r in low_conf if r.get("correct_direction"))

    n_overconfident = sum(
        1 for r in actionable if r.get("error_type") == ErrorType.OVERCONFIDENT.value
    )
    n_underconfident = sum(
        1 for r in actionable if r.get("error_type") == ErrorType.UNDERCONFIDENT.value
    )

    tier1 = {
        "direction_accuracy": _round(_safe_div(n_dir_correct, n_actionable)),
        "scenario_accuracy": _round(_safe_div(n_scn_correct, n_actionable)),
        "high_confidence_accuracy": _round(_safe_div(n_high_correct, n_high)),
        "low_confidence_accuracy": _round(_safe_div(n_low_correct, n_low)),
        "overconfidence_rate": _round(_safe_div(n_overconfident, n_actionable)),
        "underconfidence_rate": _round(_safe_div(n_underconfident, n_actionable)),
    }

    # ── Tier 2: error distribution + root causes ─────────────────────────
    error_counts: Counter = Counter()
    for r in records:
        et = r.get("error_type") or "unknown"
        error_counts[et] += 1

    error_distribution = {
        et: {
            "count": cnt,
            "share": _round(cnt / n_total, 4),
        }
        for et, cnt in error_counts.most_common()
    }

    cause_counts: Counter = Counter()
    secondary_counts: Counter = Counter()
    for r in records:
        prim = r.get("root_cause_primary")
        if prim:
            cause_counts[prim] += 1
        for sc in r.get("root_causes_secondary") or []:
            secondary_counts[sc] += 1

    root_causes_top = [
        {"cause": cause, "count": cnt, "share": _round(cnt / n_total, 4)}
        for cause, cnt in cause_counts.most_common(10)
    ]
    secondary_top = [
        {"cause": cause, "count": cnt, "share": _round(cnt / n_total, 4)}
        for cause, cnt in secondary_counts.most_common(10)
    ]

    tier2 = {
        "error_distribution": error_distribution,
        "root_causes_top": root_causes_top,
        "root_causes_secondary_top": secondary_top,
    }

    # ── Tier 3: cohort accuracy ──────────────────────────────────────────
    by_strength: Dict[str, Dict[str, int]] = defaultdict(
        lambda: {"n": 0, "correct": 0}
    )
    by_interaction: Dict[str, Dict[str, int]] = defaultdict(
        lambda: {"n": 0, "correct": 0}
    )
    by_pair: Dict[str, Dict[str, int]] = defaultdict(
        lambda: {"n": 0, "correct": 0}
    )
    for r in actionable:
        ss = (r.get("signal_strength") or "unknown").lower()
        it = (r.get("interaction_type") or "none").lower()
        pair = f"{(r.get('symbol') or '').upper()}_{(r.get('tf') or '').upper()}"
        for bucket, key in ((by_strength, ss), (by_interaction, it), (by_pair, pair)):
            bucket[key]["n"] += 1
            if r.get("correct_direction"):
                bucket[key]["correct"] += 1

    def _expand(d: Dict[str, Dict[str, int]]) -> Dict[str, Dict[str, Any]]:
        return {
            k: {
                "n": v["n"],
                "correct": v["correct"],
                "accuracy": _round(_safe_div(v["correct"], v["n"])),
            }
            for k, v in d.items()
        }

    tier3 = {
        "by_signal_strength": _expand(by_strength),
        "by_interaction_type": _expand(by_interaction),
        "by_symbol_tf": _expand(by_pair),
    }

    return {
        "sample_size": {
            "total": n_total,
            "actionable": n_actionable,
            "high_conf": n_high,
            "low_conf": n_low,
            "no_edge_ignored": n_total - n_actionable,
        },
        "tier1": tier1,
        "tier2": tier2,
        "tier3": tier3,
    }


def _empty_metrics() -> Dict[str, Any]:
    return {
        "sample_size": {
            "total": 0, "actionable": 0, "high_conf": 0,
            "low_conf": 0, "no_edge_ignored": 0,
        },
        "tier1": {
            "direction_accuracy": None,
            "scenario_accuracy": None,
            "high_confidence_accuracy": None,
            "low_confidence_accuracy": None,
            "overconfidence_rate": None,
            "underconfidence_rate": None,
        },
        "tier2": {
            "error_distribution": {},
            "root_causes_top": [],
            "root_causes_secondary_top": [],
        },
        "tier3": {
            "by_signal_strength": {},
            "by_interaction_type": {},
            "by_symbol_tf": {},
        },
    }
