"""
PHASE 4.4 — Entry Quality Factors

Defines factors that contribute to entry quality score.
"""

from typing import Dict, List


ENTRY_QUALITY_FACTORS: List[str] = [
    "trigger_distance_score",
    "extension_score",
    "confirmation_score",
    "retest_score",
    "ltf_alignment_score",
    "volatility_score",
    "structure_acceptance_score",
    "execution_suitability_score"
]


FACTOR_WEIGHTS: Dict[str, float] = {
    "trigger_distance_score": 0.12,
    "extension_score": 0.18,
    "confirmation_score": 0.18,
    "retest_score": 0.12,
    "ltf_alignment_score": 0.14,
    "volatility_score": 0.10,
    "structure_acceptance_score": 0.10,
    "execution_suitability_score": 0.06
}


FACTOR_DESCRIPTIONS: Dict[str, str] = {
    "trigger_distance_score": "How close entry is to trigger level",
    "extension_score": "Risk from price extension beyond trigger",
    "confirmation_score": "Quality of entry confirmation",
    "retest_score": "Quality of retest completion",
    "ltf_alignment_score": "Lower timeframe alignment",
    "volatility_score": "Volatility conditions friendliness",
    "structure_acceptance_score": "Structure level acceptance",
    "execution_suitability_score": "Suitability of execution strategy"
}
