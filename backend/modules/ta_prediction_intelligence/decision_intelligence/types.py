"""
Canonical output contract for Step 12 Decision Intelligence.

`to_dict()` is JSON-safe, values are rounded/clamped at the builder layer.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

DECISION_VERSION = "v1"
DECISION_BUILDER_VERSION = "1.0.0"

# ---- enums (string literals, not Python enums, for JSON stability) --------
PRIMARY_SCENARIOS = ("bull", "base", "bear", "none")
BIAS_VALUES = ("bullish", "bearish", "neutral")
STRENGTHS = ("strong", "moderate", "weak", "no_edge")
RISK_LEVELS = ("low", "elevated", "high", "extreme")
DOMINANCE_LABELS = ("dominant", "clear", "thin", "ambiguous")
ACTION_FRAMES = ("continuation", "reversal", "range", "uncertainty")


@dataclass
class DecisionIntelligenceContext:
    primary_scenario: str = "none"
    secondary_scenario: Optional[str] = None
    scenario_probability: float = 0.0
    secondary_probability: float = 0.0
    scenario_dominance: float = 0.0
    scenario_dominance_label: str = "ambiguous"
    decision_confidence: float = 0.0
    signal_strength: str = "no_edge"
    risk_level: str = "low"
    risk_score: float = 0.0
    alignment_score: float = 0.0
    temporal_score: float = 0.0
    action_frame: str = "uncertainty"
    decision_bias: str = "neutral"
    drivers: List[str] = field(default_factory=list)
    risks: List[str] = field(default_factory=list)
    summary: str = ""
    version: str = DECISION_VERSION
    builder_version: str = DECISION_BUILDER_VERSION

    def to_dict(self) -> Dict[str, Any]:
        return {
            "primary_scenario": self.primary_scenario,
            "secondary_scenario": self.secondary_scenario,
            "scenario_probability": float(round(self.scenario_probability, 4)),
            "secondary_probability": float(round(self.secondary_probability, 4)),
            "scenario_dominance": float(round(self.scenario_dominance, 4)),
            "scenario_dominance_label": self.scenario_dominance_label,
            "decision_confidence": float(round(self.decision_confidence, 4)),
            "signal_strength": self.signal_strength,
            "risk_level": self.risk_level,
            "risk_score": float(round(self.risk_score, 4)),
            "alignment_score": float(round(self.alignment_score, 4)),
            "temporal_score": float(round(self.temporal_score, 4)),
            "action_frame": self.action_frame,
            "decision_bias": self.decision_bias,
            "drivers": list(self.drivers or []),
            "risks": list(self.risks or []),
            "summary": self.summary,
            "version": self.version,
            "builder_version": self.builder_version,
        }
