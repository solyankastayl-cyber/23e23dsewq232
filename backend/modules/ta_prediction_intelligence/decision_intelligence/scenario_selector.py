"""
Scenario Selector — picks primary/secondary scenarios from the scenarios list.

Accepts either the canonical list-of-dicts shape produced by the scenario
builder, or a dict shape (defensive — some tests pass plain dicts). Returns a
deterministic tuple of fields the downstream engines can rely on.
"""
from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional

# Public mapping: scenario name -> decision_bias (bullish/bearish/neutral).
SCENARIO_BIAS: Dict[str, str] = {
    "bull": "bullish",
    "base": "neutral",
    "bear": "bearish",
    "none": "neutral",
}


def _normalise_scenarios(scenarios: Any) -> List[Dict[str, Any]]:
    """Accept list[dict] (canonical) or dict[name->dict|prob]. Returns list[dict]."""
    if not scenarios:
        return []
    if isinstance(scenarios, list):
        out: List[Dict[str, Any]] = []
        for s in scenarios:
            if not isinstance(s, dict):
                continue
            name = s.get("name") or s.get("scenario")
            prob = s.get("probability")
            if prob is None:
                prob = s.get("prob")
            if prob is None:
                continue
            try:
                prob_f = float(prob)
            except (TypeError, ValueError):
                continue
            out.append({"name": str(name or "").lower(), "probability": prob_f})
        return out
    if isinstance(scenarios, dict):
        out = []
        for k, v in scenarios.items():
            try:
                if isinstance(v, dict):
                    prob_f = float(v.get("probability", v.get("prob", 0.0)))
                else:
                    prob_f = float(v)
            except (TypeError, ValueError):
                continue
            out.append({"name": str(k).lower(), "probability": prob_f})
        return out
    return []


def select_primary_scenario(scenarios: Any) -> Dict[str, Any]:
    """
    Returns:
      {
        "primary": str,          # bull/base/bear/none
        "secondary": Optional[str],
        "primary_prob": float,
        "secondary_prob": float,
      }
    Deterministic tie-break: by (-probability, name) — lexicographic on name.
    """
    norm = _normalise_scenarios(scenarios)
    if not norm:
        return {
            "primary": "none",
            "secondary": None,
            "primary_prob": 0.0,
            "secondary_prob": 0.0,
        }
    ordered = sorted(
        norm,
        key=lambda s: (-float(s.get("probability", 0.0)), str(s.get("name", ""))),
    )
    primary = ordered[0]
    secondary = ordered[1] if len(ordered) > 1 else None
    return {
        "primary": primary.get("name") or "none",
        "secondary": (secondary.get("name") if secondary else None),
        "primary_prob": float(primary.get("probability") or 0.0),
        "secondary_prob": float(secondary.get("probability") or 0.0) if secondary else 0.0,
    }
