"""
Step 7 post-processing helper.

Applies calibration on top of Step-6 interaction-adjusted scenarios and
records the prediction through the repository. Lives here so that BOTH
`live_adapter.fetch_live_context` and `TAPredictionService.build_from_*`
share the exact same post-processing semantics.

Never raises; on any failure returns the input unchanged with applied=false.
"""

from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional, Tuple


def _extract_interaction_type(result: Dict[str, Any]) -> Optional[str]:
    inter = result.get("interaction")
    if not inter:
        return None
    return str(inter.get("type") or "") or None


def _candle_close_ts_from_result(result: Dict[str, Any]) -> Optional[int]:
    live = result.get("_live") or {}
    ts = live.get("last_candle_close_ts")
    if ts is None:
        return None
    try:
        return int(ts)
    except (TypeError, ValueError):
        return None


def apply_step7_postprocess(
    result: Dict[str, Any],
    *,
    source: str = "live",
    persist: bool = True,
) -> Dict[str, Any]:
    """
    Mutates `result` in place with Step-7 fields:
      - scenarios_pre_calibration: snapshot of interaction-adjusted scenarios
      - scenarios: calibrated scenarios (or original if skipped)
      - scenarios_calibration: meta dict (applied/reason/bucket/deltas/…)
      - prediction_id: persisted record id (or None if not persisted)

    Returns `result` for chaining.
    """
    # 1. Calibration adjustment
    try:
        from modules.ta_prediction_intelligence.scenarios.scenario_calibration_adjuster import (
            apply_calibration_adjustment,
        )
        from modules.ta_prediction_intelligence.calibration.calibration_store import (
            get_stats_by_group,
        )

        stats_by_group = get_stats_by_group()
        interaction_adjusted = list(result.get("scenarios") or [])
        ctx = {
            "symbol": result.get("symbol"),
            "timeframe": result.get("timeframe"),
            "interaction_type": _extract_interaction_type(result),
        }
        calibrated, cal_meta = apply_calibration_adjustment(
            interaction_adjusted, ctx, stats_by_group
        )
    except Exception as e:
        calibrated = list(result.get("scenarios") or [])
        cal_meta = {
            "applied": False,
            "reason": f"calibration_internal_error:{type(e).__name__}",
            "explanation": "calibration layer failed; scenarios returned as-is",
        }

    # Snapshot the interaction-adjusted view as pre-calibration reference.
    result["scenarios_pre_calibration"] = [
        dict(s) for s in (result.get("scenarios") or [])
    ]
    result["scenarios"] = calibrated
    result["scenarios_calibration"] = cal_meta

    # 2b. Step 8: build feature snapshot (read-only, always runs). On any
    # failure we keep going — features are additive, not required by Step 6/7.
    feature_bundle: Optional[Dict[str, Any]] = None
    try:
        from modules.ta_prediction_intelligence.learning import get_feature_builder
        builder = get_feature_builder()
        feature_bundle = builder.build(result)
        # Expose only lightweight meta in the response (the full 82-feature
        # vector is NOT pushed to callers; it lives in the Mongo history row).
        result["_features_debug"] = {
            "feature_version": feature_bundle.get("feature_version"),
            "feature_schema_hash": feature_bundle.get("feature_schema_hash"),
            "feature_hash": feature_bundle.get("feature_hash"),
            "builder_version": feature_bundle.get("builder_version"),
            "feature_count": len((feature_bundle or {}).get("features") or {}),
            "states": feature_bundle.get("states"),
            "missing_engines": feature_bundle.get("missing_engines"),
            "latency_ms": feature_bundle.get("latency_ms"),
        }
    except Exception as e:
        feature_bundle = None
        result["_features_debug"] = {
            "feature_version": None,
            "error": f"{type(e).__name__}: {str(e)[:200]}",
        }

    # 2c. Temporal Intelligence — read buffer history (which now includes the
    # snapshot just pushed by feature_builder.build) and derive state evolution,
    # regime memory, persistence, transition pressure, sequence patterns. Pure
    # read-only; never mutates bias/confidence/scenarios/calibration.
    temporal_ctx_dict: Optional[Dict[str, Any]] = None
    try:
        from modules.ta_prediction_intelligence.learning import get_temporal_buffer
        from modules.ta_prediction_intelligence.temporal_intelligence import (
            build_temporal_context,
        )
        sym = (result.get("symbol") or "").upper()
        tf = (result.get("timeframe") or "").upper()
        history = get_temporal_buffer().get(sym, tf) if (sym and tf) else []
        ctx = build_temporal_context(sym, tf, history)
        temporal_ctx_dict = ctx.to_dict()
        result["temporal_intelligence"] = temporal_ctx_dict
    except Exception as e:
        result["temporal_intelligence"] = {
            "ready": False,
            "summary": f"temporal_internal_error:{type(e).__name__}",
        }

    # 2d. Step 12: Decision Intelligence — compress scenarios + engines +
    # interaction + temporal into a primary scenario + decision confidence
    # + risk + explanation. Pure read-only; never mutates upstream fields.
    decision_ctx_dict: Optional[Dict[str, Any]] = None
    try:
        from modules.ta_prediction_intelligence.decision_intelligence import (
            build_decision_intelligence,
        )
        decision_ctx_dict = build_decision_intelligence(result)
        result["decision_intelligence"] = decision_ctx_dict
    except Exception as e:
        result["decision_intelligence"] = {
            "primary_scenario": "none",
            "signal_strength": "no_edge",
            "summary": f"decision_internal_error:{type(e).__name__}",
            "risks": ["decision_internal_error"],
        }

    # 3. Persist the prediction (audit + future calibration + ML-ready features).
    prediction_id: Optional[str] = None
    if persist:
        try:
            from modules.ta_prediction_intelligence.repository import get_repository
            repo = get_repository()
            if repo is not None:
                pid = f"tap-{uuid.uuid4().hex[:16]}"
                prediction_id = repo.record_prediction(
                    symbol=result.get("symbol") or "",
                    timeframe=result.get("timeframe") or "",
                    entry_price=float(
                        (result.get("_live") or {}).get("last_close")
                        or (result.get("meta") or {}).get("price")
                        or 0.0
                    ),
                    candle_close_ts=_candle_close_ts_from_result(result),
                    bias=result.get("bias"),
                    confidence=result.get("confidence"),
                    conflict_ratio=result.get("conflict_ratio"),
                    dominant_engine=result.get("dominant_engine"),
                    contributions=result.get("contributions") or [],
                    interaction=result.get("interaction"),
                    scenarios_original=result.get("scenarios_original") or [],
                    scenarios_interaction_adjusted=result.get(
                        "scenarios_pre_calibration"
                    ) or [],
                    scenarios_calibrated=result.get("scenarios") or [],
                    scenarios_adjustment_meta=result.get("scenarios_adjustment"),
                    scenarios_calibration_meta=result.get("scenarios_calibration"),
                    meta={
                        "_live": result.get("_live") or {},
                    },
                    source=source,
                    prediction_id=pid,
                    features_bundle=feature_bundle,
                    temporal_context=temporal_ctx_dict,
                    decision_context=decision_ctx_dict,
                )
        except Exception:
            prediction_id = None

    result["prediction_id"] = prediction_id
    return result
