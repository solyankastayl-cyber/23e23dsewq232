"""
Main Decision Intelligence orchestrator.

Invoked from step7_pipeline AFTER temporal intelligence has been computed.
100% read-only: never mutates scenarios, interaction, temporal context, or
any engine data. On missing scenarios → returns a safe "no_edge" context.
"""
from __future__ import annotations

from typing import Any, Dict, Optional

from .alignment_engine import compute_alignment
from .decision_classifier import classify_decision
from .dominance_engine import compute_dominance
from .risk_engine import compute_risk
from .scenario_selector import SCENARIO_BIAS, select_primary_scenario
from .types import DecisionIntelligenceContext


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value) if value is not None else default
    except (TypeError, ValueError):
        return default


def _compute_temporal_score(temporal: Optional[Dict[str, Any]]) -> float:
    if not temporal or not temporal.get("ready"):
        # When temporal layer isn't ready (insufficient_history), neutralise its
        # contribution rather than collapse the decision. 0.5 = neutral.
        return 0.5
    stability = _safe_float(temporal.get("regime_stability_score"))
    continuation = _safe_float(temporal.get("continuation_pressure"))
    instability = _safe_float(temporal.get("instability_pressure"))
    score = (
        stability * 0.40
        + continuation * 0.35
        + (1.0 - instability) * 0.25
    )
    return max(0.0, min(score, 1.0))


def _infer_action_frame(
    primary_scenario: str,
    interaction: Optional[Dict[str, Any]],
    temporal: Optional[Dict[str, Any]],
) -> str:
    itype = str((interaction or {}).get("type") or "").lower()
    if itype in ("trend_continuation", "breakout", "breakout_confirmed", "pullback_continuation"):
        return "continuation"
    if itype in ("early_reversal", "fake_breakout", "rejection", "whipsaw"):
        return "reversal"
    if itype == "compression":
        return "uncertainty"
    if primary_scenario == "base":
        return "range"
    sequence = str((temporal or {}).get("detected_sequence") or "").lower()
    if sequence:
        if "reversal" in sequence:
            return "reversal"
        if "continuation" in sequence:
            return "continuation"
    return "uncertainty"


def _build_summary(
    primary: str,
    bias: str,
    conf: float,
    strength: str,
    risk: str,
    frame: str,
) -> str:
    if primary == "none":
        return "No scenarios available — decision layer yields no edge."
    return (
        f"Primary scenario is {primary} ({bias}) with "
        f"{round(conf * 100)}% decision confidence. "
        f"Signal strength is {strength}; risk level is {risk}; "
        f"action frame is {frame}."
    )


def build_decision_intelligence(result: Dict[str, Any]) -> Dict[str, Any]:
    """
    Read-only transform: returns a dict (JSON-safe, serialised via
    DecisionIntelligenceContext.to_dict()). Safe against any missing key.
    """
    try:
        scenarios = result.get("scenarios") or []
        selected = select_primary_scenario(scenarios)
        primary = selected["primary"]
        secondary = selected["secondary"]
        primary_prob = float(selected["primary_prob"])
        secondary_prob = float(selected["secondary_prob"])

        # Handle the empty / missing case deterministically.
        if primary == "none" or primary_prob <= 0.0:
            ctx = DecisionIntelligenceContext(
                primary_scenario="none",
                secondary_scenario=None,
                scenario_probability=0.0,
                secondary_probability=0.0,
                scenario_dominance=0.0,
                scenario_dominance_label="ambiguous",
                decision_confidence=0.0,
                signal_strength="no_edge",
                risk_level="low",
                risk_score=0.0,
                alignment_score=0.5,
                temporal_score=0.5,
                action_frame="uncertainty",
                decision_bias="neutral",
                drivers=[],
                risks=["missing_scenarios"],
                summary=_build_summary("none", "neutral", 0.0, "no_edge", "low", "uncertainty"),
            )
            return ctx.to_dict()

        dominance, dominance_label = compute_dominance(primary_prob, secondary_prob)
        primary_bias = SCENARIO_BIAS.get(primary, "neutral")

        risk_score, risk_level, risk_reasons = compute_risk(result)
        alignment_score, align_drivers, align_risks = compute_alignment(primary_bias, result)
        temporal = result.get("temporal_intelligence") or {}
        temporal_score = _compute_temporal_score(temporal)

        decision_conf = (
            primary_prob
            * (0.50 + 0.50 * alignment_score)
            * (0.60 + 0.40 * temporal_score)
            * (1.00 - 0.50 * risk_score)
        )
        decision_conf = max(0.0, min(decision_conf, 1.0))

        strength = classify_decision(decision_conf, dominance, risk_level)
        action_frame = _infer_action_frame(primary, result.get("interaction"), temporal)

        drivers: list = []
        risks: list = []
        drivers.extend(align_drivers)
        risks.extend(align_risks)
        risks.extend(risk_reasons)

        summary = _build_summary(
            primary, primary_bias, decision_conf, strength, risk_level, action_frame
        )

        ctx = DecisionIntelligenceContext(
            primary_scenario=primary,
            secondary_scenario=secondary,
            scenario_probability=primary_prob,
            secondary_probability=secondary_prob,
            scenario_dominance=dominance,
            scenario_dominance_label=dominance_label,
            decision_confidence=decision_conf,
            signal_strength=strength,
            risk_level=risk_level,
            risk_score=risk_score,
            alignment_score=alignment_score,
            temporal_score=temporal_score,
            action_frame=action_frame,
            decision_bias=primary_bias,
            drivers=drivers,
            risks=risks,
            summary=summary,
        )
        return ctx.to_dict()
    except Exception as e:  # pragma: no cover — defensive last-resort
        return DecisionIntelligenceContext(
            primary_scenario="none",
            signal_strength="no_edge",
            summary=f"decision_internal_error:{type(e).__name__}",
            risks=["decision_internal_error"],
        ).to_dict()
