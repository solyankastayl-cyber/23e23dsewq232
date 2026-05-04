"""
PHASE 13.3 - Factor Templates
==============================
Templates for factor generation.

Supports 8 template types:
1. single_feature     - A
2. pair_feature       - A + B
3. triple_feature     - A + B + C
4. ratio_feature      - A / B
5. difference_feature - A - B
6. conditional_feature - A if B
7. regime_conditioned  - A only in regime R
8. interaction_feature - A * B
"""

from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass

from .factor_types import FactorTemplate, FactorFamily


@dataclass
class TemplateConfig:
    """Configuration for a factor template."""
    template: FactorTemplate
    min_inputs: int
    max_inputs: int
    required_categories: int  # Minimum different categories
    default_transforms: List[str]
    description: str


# Template configurations
TEMPLATE_CONFIGS: Dict[FactorTemplate, TemplateConfig] = {
    FactorTemplate.SINGLE_FEATURE: TemplateConfig(
        template=FactorTemplate.SINGLE_FEATURE,
        min_inputs=1,
        max_inputs=1,
        required_categories=1,
        default_transforms=["zscore"],
        description="Single feature as factor"
    ),
    FactorTemplate.PAIR_FEATURE: TemplateConfig(
        template=FactorTemplate.PAIR_FEATURE,
        min_inputs=2,
        max_inputs=2,
        required_categories=1,
        default_transforms=["weighted_sum", "zscore"],
        description="Weighted sum of two features"
    ),
    FactorTemplate.TRIPLE_FEATURE: TemplateConfig(
        template=FactorTemplate.TRIPLE_FEATURE,
        min_inputs=3,
        max_inputs=3,
        required_categories=2,
        default_transforms=["weighted_sum", "zscore"],
        description="Weighted sum of three features"
    ),
    FactorTemplate.RATIO_FEATURE: TemplateConfig(
        template=FactorTemplate.RATIO_FEATURE,
        min_inputs=2,
        max_inputs=2,
        required_categories=1,
        default_transforms=["ratio", "zscore"],
        description="Ratio of two features"
    ),
    FactorTemplate.DIFFERENCE_FEATURE: TemplateConfig(
        template=FactorTemplate.DIFFERENCE_FEATURE,
        min_inputs=2,
        max_inputs=2,
        required_categories=1,
        default_transforms=["difference", "zscore"],
        description="Difference of two features"
    ),
    FactorTemplate.CONDITIONAL_FEATURE: TemplateConfig(
        template=FactorTemplate.CONDITIONAL_FEATURE,
        min_inputs=2,
        max_inputs=2,
        required_categories=1,
        default_transforms=["conditional"],
        description="Feature A active only when B condition met"
    ),
    FactorTemplate.REGIME_CONDITIONED: TemplateConfig(
        template=FactorTemplate.REGIME_CONDITIONED,
        min_inputs=1,
        max_inputs=2,
        required_categories=1,
        default_transforms=["regime_mask"],
        description="Feature active only in specific regimes"
    ),
    FactorTemplate.INTERACTION_FEATURE: TemplateConfig(
        template=FactorTemplate.INTERACTION_FEATURE,
        min_inputs=2,
        max_inputs=2,
        required_categories=2,
        default_transforms=["product", "zscore"],
        description="Interaction (product) of two features"
    ),
}


# Family to feature category mapping
FAMILY_CATEGORY_MAP: Dict[FactorFamily, List[str]] = {
    FactorFamily.TREND: ["price", "structure"],
    FactorFamily.BREAKOUT: ["volatility", "price", "volume"],
    FactorFamily.REVERSAL: ["price", "structure", "microstructure"],
    FactorFamily.LIQUIDITY: ["liquidity", "microstructure"],
    FactorFamily.CORRELATION: ["correlation", "context"],
    FactorFamily.MICROSTRUCTURE: ["microstructure", "volume"],
    FactorFamily.MACRO: ["context", "correlation"],
    FactorFamily.REGIME: ["context", "volatility"],
    FactorFamily.MOMENTUM: ["price", "volume"],
    FactorFamily.VOLATILITY: ["volatility", "price"],
    FactorFamily.VOLUME: ["volume", "liquidity"],
    FactorFamily.STRUCTURE: ["structure", "price"],
}


# Regime types for regime-conditioned factors
REGIME_TYPES = [
    "TRENDING_UP",
    "TRENDING_DOWN",
    "RANGE",
    "HIGH_VOL",
    "LOW_VOL",
    "BREAKOUT",
    "CONSOLIDATION",
    "RISK_ON",
    "RISK_OFF"
]


def get_template_config(template: FactorTemplate) -> TemplateConfig:
    """Get configuration for a template."""
    return TEMPLATE_CONFIGS.get(template)


def infer_family_from_categories(categories: List[str]) -> FactorFamily:
    """Infer factor family from input categories."""
    category_set = set(categories)
    
    # Priority-based matching
    if "liquidity" in category_set:
        return FactorFamily.LIQUIDITY
    if "microstructure" in category_set:
        return FactorFamily.MICROSTRUCTURE
    if "correlation" in category_set:
        return FactorFamily.CORRELATION
    if "context" in category_set:
        return FactorFamily.MACRO
    if "volatility" in category_set and "price" in category_set:
        return FactorFamily.BREAKOUT
    if "structure" in category_set:
        return FactorFamily.STRUCTURE
    if "volatility" in category_set:
        return FactorFamily.VOLATILITY
    if "volume" in category_set:
        return FactorFamily.VOLUME
    if "price" in category_set:
        return FactorFamily.MOMENTUM
    
    return FactorFamily.TREND


def infer_direction(inputs: List[str], categories: List[str]) -> str:
    """Infer expected direction from inputs."""
    # Simple heuristics
    bullish_keywords = ["strength", "momentum", "bullish", "long", "buy", "compression"]
    bearish_keywords = ["exhaustion", "bearish", "short", "sell", "weakness"]
    
    input_str = " ".join(inputs).lower()
    
    bullish_score = sum(1 for kw in bullish_keywords if kw in input_str)
    bearish_score = sum(1 for kw in bearish_keywords if kw in input_str)
    
    if bullish_score > bearish_score:
        return "LONG"
    elif bearish_score > bullish_score:
        return "SHORT"
    return "NEUTRAL"
