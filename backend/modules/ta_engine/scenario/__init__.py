"""
Scenario Engine Module
======================

V3 Architecture:
  scenarios = f(decision, mtf_context, structure_context, base_layer, pattern)

Scenarios are now decision-driven, not level-driven.
"""

from .scenario_engine import (
    generate_scenarios,
    build_confidence_explanation,
    scenario_engine
)

# V2 — Structure-aware scenarios
from .scenario_engine_v2 import (
    ScenarioEngineV2,
    get_scenario_engine_v2,
)

# V3 — Decision-driven scenarios (new architecture)
from .scenario_engine_v3 import (
    ScenarioEngineV3,
    get_scenario_engine_v3,
    scenario_engine_v3,
)

__all__ = [
    # V1 (legacy)
    "generate_scenarios",
    "build_confidence_explanation",
    "scenario_engine",
    # V2
    "ScenarioEngineV2",
    "get_scenario_engine_v2",
    # V3 (new architecture)
    "ScenarioEngineV3",
    "get_scenario_engine_v3",
    "scenario_engine_v3",
]
