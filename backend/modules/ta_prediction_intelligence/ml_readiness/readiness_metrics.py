"""
Five component metrics. Each function:
    * is read-only on Mongo (find / count_documents / aggregate)
    * returns (component_score, blocking_factors_added, details_dict)
    * is pure given the inputs (i.e. no time-of-day randomness)

Formulas are LOCKED per spec.
"""
from __future__ import annotations

import math
from collections import Counter
from typing import Any, Dict, List, Optional, Tuple

from .types import (
    BlockingFactor,
    DOMINANCE_TARGET_SHARE,
    EXPECTED_INTERACTION_TYPES,
    EXPECTED_TREND_STATES,
    EXPECTED_VOLATILITY_STATES,
    MIN_BUCKET_SIZE,
    MIN_DEBUG_SAMPLES,
    NO_DOMINANT_THRESHOLD,
    REGIME_COVERAGE_BLOCKING_MIN_TOTAL,
    REGIME_COVERAGE_BLOCKING_THRESHOLD,
    SEVERE_CLASS_THRESHOLD,
    TARGET_TOTAL_SAMPLES,
    TRACKED_PAIRS,
    UNSTABLE_ENTROPY_THRESHOLD,
)

HISTORY_COL = "ta_prediction_history"
DEBUG_COL = "ta_prediction_debug"
SIM_HISTORY_COL = "ta_prediction_history_sim"
SIM_DEBUG_COL = "ta_prediction_debug_sim"

# Direction noise floor (mirror of debug.taxonomy.SMALL_MOVE_THRESHOLD)
_SMALL_MOVE = 0.0010


def _normalized_entropy(counts: List[int], expected_classes: int) -> float:
    """Shannon entropy normalised by log(expected_classes). Range: [0,1]."""
    total = sum(counts)
    if total <= 0 or expected_classes <= 1:
        return 0.0
    probs = [c / total for c in counts if c > 0]
    if not probs:
        return 0.0
    H = -sum(p * math.log(p) for p in probs)
    denom = math.log(expected_classes)
    if denom <= 0:
        return 0.0
    return max(0.0, min(1.0, H / denom))


def _round(v: Optional[float], n: int = 4) -> Optional[float]:
    if v is None:
        return None
    try:
        return round(float(v), n)
    except (TypeError, ValueError):
        return None


# ══ 1. SAMPLE QUALITY ══════════════════════════════════════════════════════════════
def compute_sample_quality(db: Any) -> Tuple[float, List[str], Dict[str, Any]]:
    """Spec:
        total_score  = min(1, total_samples / 500)
        pair_score   = mean_over_tracked_pairs(min(1, n_pair / 500))
        bucket_score = min(1, min_bucket_size / 20)
        sample_quality = 0.50 * total_score + 0.30 * pair_score + 0.20 * bucket_score
    """
    blocking: List[str] = []
    if db is None:
        return 0.0, [], {"reason": "mongo_unavailable"}

    total_samples = int(
        db[HISTORY_COL].count_documents({"evaluation_state": "evaluated"})
    )
    # Sim counts are surfaced for observability ONLY \u2014 they MUST NOT influence
    # the readiness score / hard gates. Readiness is a live-only contract.
    try:
        live_history_count = int(db[HISTORY_COL].count_documents({}))
    except Exception:
        live_history_count = total_samples
    try:
        sim_history_count = int(db[SIM_HISTORY_COL].count_documents({}))
    except Exception:
        sim_history_count = 0
    try:
        sim_history_evaluated = int(
            db[SIM_HISTORY_COL].count_documents({"evaluation_state": "evaluated"})
        )
    except Exception:
        sim_history_evaluated = 0
    by_pair: Dict[str, int] = {}
    for pair in TRACKED_PAIRS:
        try:
            sym, tf = pair.split("_", 1)
        except ValueError:
            continue
        by_pair[pair] = int(db[HISTORY_COL].count_documents({
            "evaluation_state": "evaluated",
            "symbol": sym.upper(),
            "timeframe": tf.upper(),
        }))

    # Buckets: (symbol, tf, interaction_type)
    buckets: List[Dict[str, Any]] = []
    try:
        cursor = db[HISTORY_COL].aggregate([
            {"$match": {"evaluation_state": "evaluated"}},
            {"$group": {
                "_id": {
                    "symbol": "$symbol",
                    "tf": "$timeframe",
                    "interaction": {
                        "$ifNull": ["$interaction.type", "unknown"]
                    },
                },
                "n": {"$sum": 1},
            }},
        ])
        for r in cursor:
            k = r["_id"]
            buckets.append({
                "symbol": k.get("symbol"),
                "tf": k.get("tf"),
                "interaction_type": k.get("interaction"),
                "n": int(r["n"]),
            })
    except Exception:
        buckets = []
    min_bucket_size = min((b["n"] for b in buckets), default=0) if buckets else 0

    total_score = min(1.0, total_samples / TARGET_TOTAL_SAMPLES)
    if TRACKED_PAIRS:
        pair_score = sum(
            min(1.0, by_pair.get(p, 0) / TARGET_TOTAL_SAMPLES) for p in TRACKED_PAIRS
        ) / float(len(TRACKED_PAIRS))
    else:
        pair_score = 0.0
    bucket_score = min(1.0, min_bucket_size / MIN_BUCKET_SIZE) if MIN_BUCKET_SIZE > 0 else 0.0

    score = 0.50 * total_score + 0.30 * pair_score + 0.20 * bucket_score

    # Blocking factors
    if total_samples >= MIN_BUCKET_SIZE * 3 and min_bucket_size < MIN_BUCKET_SIZE:
        # spec: only if total_samples >= 50 and min_bucket_size < 20
        if total_samples >= 50:
            blocking.append(BlockingFactor.BLIND_BUCKETS.value)

    details = {
        "total": total_samples,
        "by_pair": by_pair,
        "min_bucket_size": min_bucket_size,
        "bucket_count": len(buckets),
        "buckets": buckets[:50],   # cap output size
        "sub_scores": {
            "total_score": _round(total_score),
            "pair_score": _round(pair_score),
            "bucket_score": _round(bucket_score),
        },
        "samples_by_source": {
            "live_total": int(live_history_count),
            "live_evaluated": int(total_samples),
            "simulation_total": int(sim_history_count),
            "simulation_evaluated": int(sim_history_evaluated),
            "scoring_basis": "live_evaluated_only",
        },
    }
    return max(0.0, min(1.0, score)), blocking, details


# ══ 2. CLASS BALANCE ══════════════════════════════════════════════════════════════
def compute_class_balance(db: Any) -> Tuple[float, List[str], Dict[str, Any]]:
    """Spec:
        scenario_entropy  = H([bull, base, bear]) / log(3)
        direction_entropy = H([up, down])         / log(2)
        class_balance     = 0.60 * scenario_entropy + 0.40 * direction_entropy
    """
    blocking: List[str] = []
    if db is None:
        return 0.0, [], {"reason": "mongo_unavailable"}

    scenario_counts = {"bull": 0, "base": 0, "bear": 0}
    direction_counts = {"up": 0, "down": 0}
    flat_count = 0
    n_total = 0
    n_with_outcome = 0
    for r in db[HISTORY_COL].find(
        {"evaluation_state": "evaluated"},
        {"outcome.winning_scenario": 1, "outcome.return_h6": 1},
    ):
        n_total += 1
        outcome = r.get("outcome") or {}
        winning = (outcome.get("winning_scenario") or "").lower()
        if winning in scenario_counts:
            scenario_counts[winning] += 1
            n_with_outcome += 1
        rh6 = outcome.get("return_h6")
        try:
            if rh6 is None:
                continue
            v = float(rh6)
        except (TypeError, ValueError):
            continue
        if v > _SMALL_MOVE:
            direction_counts["up"] += 1
        elif v < -_SMALL_MOVE:
            direction_counts["down"] += 1
        else:
            flat_count += 1

    scenario_entropy = _normalized_entropy(
        [scenario_counts["bull"], scenario_counts["base"], scenario_counts["bear"]], 3
    )
    direction_entropy = _normalized_entropy(
        [direction_counts["up"], direction_counts["down"]], 2
    )
    score = 0.60 * scenario_entropy + 0.40 * direction_entropy

    total_scn = sum(scenario_counts.values())
    max_share = (max(scenario_counts.values()) / total_scn) if total_scn > 0 else 0.0
    if total_scn >= 20 and max_share > SEVERE_CLASS_THRESHOLD:
        blocking.append(BlockingFactor.SEVERE_CLASS_IMBALANCE.value)

    details = {
        "scenario_distribution": scenario_counts,
        "direction_distribution": direction_counts,
        "flat_count": flat_count,
        "max_scenario_share": _round(max_share),
        "scenario_entropy": _round(scenario_entropy),
        "direction_entropy": _round(direction_entropy),
        "n_total": n_total,
    }
    return max(0.0, min(1.0, score)), blocking, details


# ══ 3. ERROR STABILITY ════════════════════════════════════════════════════════════
def compute_error_stability(db: Any) -> Tuple[float, List[str], Dict[str, Any]]:
    """Spec:
        if debug_count < 30 → component=0 + insufficient_debug_samples
        else:
            entropy_stability = 1 - normalized_entropy(root_cause_distribution)
            dominance_score   = min(1, dominant_share / 0.40)
            error_stability   = 0.60 * entropy_stability + 0.40 * dominance_score
        Blocking:
            if normalized_entropy > 0.70 → unstable_error_patterns
            if dominant_share < 0.25     → no_dominant_failure_mode
    """
    blocking: List[str] = []
    if db is None:
        return 0.0, [], {"reason": "mongo_unavailable"}

    debug_count = int(db[DEBUG_COL].estimated_document_count())
    if debug_count < MIN_DEBUG_SAMPLES:
        blocking.append(BlockingFactor.INSUFFICIENT_DEBUG_SAMPLES.value)
        return 0.0, blocking, {
            "debug_count": debug_count,
            "min_required": MIN_DEBUG_SAMPLES,
            "root_cause_entropy": None,
            "dominant_root_cause": None,
            "dominant_share": None,
        }

    cause_counter: Counter = Counter()
    for r in db[DEBUG_COL].find({}, {"root_cause_primary": 1, "no_edge_ignored": 1}):
        # Spec excludes only what reasonable: keep no_edge_ignored OUT of the
        # error sample because it's not really a prediction error.
        if r.get("no_edge_ignored"):
            continue
        rc = r.get("root_cause_primary")
        if rc:
            cause_counter[rc] += 1

    if not cause_counter:
        return 0.0, blocking, {
            "debug_count": debug_count,
            "actionable_with_cause": 0,
            "root_cause_entropy": None,
            "dominant_root_cause": None,
            "dominant_share": None,
        }

    counts = list(cause_counter.values())
    total = sum(counts)
    K = max(2, len(counts))           # spec leaves K open; use len(observed) so
                                      # 2 even causes → entropy=1 (“chaos”).
    norm_entropy = _normalized_entropy(counts, K)
    entropy_stability = max(0.0, 1.0 - norm_entropy)
    dominant_cause, dominant_count = cause_counter.most_common(1)[0]
    dominant_share = dominant_count / total
    dominance_score = min(1.0, dominant_share / DOMINANCE_TARGET_SHARE)

    score = 0.60 * entropy_stability + 0.40 * dominance_score

    if norm_entropy > UNSTABLE_ENTROPY_THRESHOLD:
        blocking.append(BlockingFactor.UNSTABLE_ERROR_PATTERNS.value)
    if dominant_share < NO_DOMINANT_THRESHOLD:
        blocking.append(BlockingFactor.NO_DOMINANT_FAILURE_MODE.value)

    details = {
        "debug_count": debug_count,
        "actionable_with_cause": total,
        "root_cause_distribution": dict(cause_counter.most_common(20)),
        "root_cause_entropy": _round(norm_entropy),
        "dominant_root_cause": dominant_cause,
        "dominant_share": _round(dominant_share),
        "sub_scores": {
            "entropy_stability": _round(entropy_stability),
            "dominance_score": _round(dominance_score),
        },
    }
    return max(0.0, min(1.0, score)), blocking, details


# ══ 4. FEATURE INTEGRITY ═══════════════════════════════════════════════════════════
def compute_feature_integrity(
    data_health_report: Optional[Dict[str, Any]]
) -> Tuple[float, List[str], Dict[str, Any]]:
    """Spec: feature_integrity = data_health.block_scores.features (read-only)."""
    blocking: List[str] = []
    if not isinstance(data_health_report, dict):
        blocking.append(BlockingFactor.FEATURE_INTEGRITY_UNKNOWN.value)
        return 0.0, blocking, {"reason": "data_health_unavailable"}
    block_scores = data_health_report.get("block_scores") or {}
    raw = block_scores.get("features")
    if raw is None:
        blocking.append(BlockingFactor.FEATURE_INTEGRITY_UNKNOWN.value)
        return 0.0, blocking, {"reason": "features_block_score_missing"}
    try:
        score = float(raw)
    except (TypeError, ValueError):
        blocking.append(BlockingFactor.FEATURE_INTEGRITY_UNKNOWN.value)
        return 0.0, blocking, {"reason": "features_block_score_not_numeric", "raw": raw}
    feature_metrics = (
        (data_health_report.get("checks") or {})
        .get("features", {})
        .get("metrics", {})
    )
    return max(0.0, min(1.0, score)), blocking, {
        "score": _round(score),
        "data_health_features_metrics": feature_metrics,
    }


# ══ 5. REGIME COVERAGE ═══════════════════════════════════════════════════════════
def compute_regime_coverage(db: Any) -> Tuple[float, List[str], Dict[str, Any]]:
    """Spec:
        vol_cov         = unique_vol_states_seen / 4
        trend_cov       = unique_trend_states_seen / 4
        interaction_cov = unique_interactions_seen / 8
        regime_coverage = 0.30 * vol_cov + 0.30 * trend_cov + 0.40 * interaction_cov
    Blocking: regime_coverage < 0.35 AND total_samples >= 100
    """
    blocking: List[str] = []
    if db is None:
        return 0.0, [], {"reason": "mongo_unavailable"}

    vol_seen: set = set()
    trend_seen: set = set()
    interaction_seen: set = set()
    n_total = 0
    for r in db[HISTORY_COL].find(
        {"evaluation_state": "evaluated"},
        {"feature_states.volatility": 1, "feature_states.trend": 1,
         "interaction.type": 1},
    ):
        n_total += 1
        fs = r.get("feature_states") or {}
        v = (fs.get("volatility") or "").strip().lower()
        t = (fs.get("trend") or "").strip().lower()
        it = ((r.get("interaction") or {}).get("type") or "").strip().lower()
        if v:
            vol_seen.add(v)
        if t:
            trend_seen.add(t)
        if it:
            interaction_seen.add(it)

    vol_match = vol_seen & set(EXPECTED_VOLATILITY_STATES)
    trend_match = trend_seen & set(EXPECTED_TREND_STATES)
    interaction_match = interaction_seen & set(EXPECTED_INTERACTION_TYPES)

    vol_cov = len(vol_match) / float(len(EXPECTED_VOLATILITY_STATES))
    trend_cov = len(trend_match) / float(len(EXPECTED_TREND_STATES))
    interaction_cov = len(interaction_match) / float(len(EXPECTED_INTERACTION_TYPES))

    score = 0.30 * vol_cov + 0.30 * trend_cov + 0.40 * interaction_cov

    if (
        n_total >= REGIME_COVERAGE_BLOCKING_MIN_TOTAL
        and score < REGIME_COVERAGE_BLOCKING_THRESHOLD
    ):
        blocking.append(BlockingFactor.REGIME_COVERAGE_LOW.value)

    details = {
        "volatility_states_seen": sorted(vol_seen),
        "volatility_states_expected": EXPECTED_VOLATILITY_STATES,
        "trend_states_seen": sorted(trend_seen),
        "trend_states_expected": EXPECTED_TREND_STATES,
        "interaction_types_seen": sorted(interaction_seen),
        "interaction_types_expected": EXPECTED_INTERACTION_TYPES,
        "sub_scores": {
            "vol_cov": _round(vol_cov),
            "trend_cov": _round(trend_cov),
            "interaction_cov": _round(interaction_cov),
        },
        "n_total": n_total,
    }
    return max(0.0, min(1.0, score)), blocking, details
