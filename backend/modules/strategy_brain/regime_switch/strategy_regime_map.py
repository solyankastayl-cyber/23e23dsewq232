"""
PHASE 19.3 — Strategy Regime Map
================================
Mapping between market regimes and optimal strategies.

Defines which strategies work best in each regime.
"""

from typing import Dict, List, Optional, Any

from modules.strategy_brain.regime_switch.strategy_regime_types import (
    RegimeStrategyConfig,
)


# ══════════════════════════════════════════════════════════════
# REGIME STRATEGY MAP
# ══════════════════════════════════════════════════════════════

REGIME_STRATEGY_MAP: Dict[str, RegimeStrategyConfig] = {
    
    # ────────────────────────────────────────────────────────────
    # TRENDING REGIMES
    # ────────────────────────────────────────────────────────────
    
    "TREND_UP": RegimeStrategyConfig(
        regime_name="TREND_UP",
        primary_strategies=[
            "trend_following",
        ],
        secondary_strategies=[
            "breakout",
            "flow_following",
        ],
        anti_strategies=[
            "mean_reversion",
            "structure_reversal",
        ],
    ),
    
    "TREND_DOWN": RegimeStrategyConfig(
        regime_name="TREND_DOWN",
        primary_strategies=[
            "trend_following",
        ],
        secondary_strategies=[
            "breakout",
            "flow_following",
        ],
        anti_strategies=[
            "mean_reversion",
            "structure_reversal",
        ],
    ),
    
    # ────────────────────────────────────────────────────────────
    # RANGE REGIMES
    # ────────────────────────────────────────────────────────────
    
    "RANGE": RegimeStrategyConfig(
        regime_name="RANGE",
        primary_strategies=[
            "mean_reversion",
        ],
        secondary_strategies=[
            "structure_reversal",
            "funding_arb",
        ],
        anti_strategies=[
            "trend_following",
            "breakout",
        ],
    ),
    
    "RANGE_LOW_VOL": RegimeStrategyConfig(
        regime_name="RANGE_LOW_VOL",
        primary_strategies=[
            "mean_reversion",
        ],
        secondary_strategies=[
            "structure_reversal",
            "funding_arb",
        ],
        anti_strategies=[
            "trend_following",
            "breakout",
            "liquidation_capture",
        ],
    ),
    
    "RANGE_LOW_VOL_NEUTRAL": RegimeStrategyConfig(
        regime_name="RANGE_LOW_VOL_NEUTRAL",
        primary_strategies=[
            "mean_reversion",
        ],
        secondary_strategies=[
            "structure_reversal",
            "funding_arb",
        ],
        anti_strategies=[
            "trend_following",
            "breakout",
            "liquidation_capture",
        ],
    ),
    
    "RANGE_HIGH_VOL": RegimeStrategyConfig(
        regime_name="RANGE_HIGH_VOL",
        primary_strategies=[
            "mean_reversion",
        ],
        secondary_strategies=[
            "structure_reversal",
        ],
        anti_strategies=[
            "trend_following",
            "funding_arb",  # Too risky in high vol
        ],
    ),
    
    "RANGE_ACCUMULATION": RegimeStrategyConfig(
        regime_name="RANGE_ACCUMULATION",
        primary_strategies=[
            "breakout",
            "volatility_expansion",
        ],
        secondary_strategies=[
            "mean_reversion",
            "structure_reversal",
        ],
        anti_strategies=[
            "trend_following",
        ],
    ),
    
    # ────────────────────────────────────────────────────────────
    # VOLATILITY REGIMES
    # ────────────────────────────────────────────────────────────
    
    "VOL_EXPANSION": RegimeStrategyConfig(
        regime_name="VOL_EXPANSION",
        primary_strategies=[
            "breakout",
            "volatility_expansion",
        ],
        secondary_strategies=[
            "flow_following",
        ],
        anti_strategies=[
            "mean_reversion",
            "funding_arb",
        ],
    ),
    
    "VOL_COMPRESSION": RegimeStrategyConfig(
        regime_name="VOL_COMPRESSION",
        primary_strategies=[
            "volatility_expansion",  # Anticipating breakout
        ],
        secondary_strategies=[
            "breakout",
            "funding_arb",
        ],
        anti_strategies=[
            "liquidation_capture",
        ],
    ),
    
    # ────────────────────────────────────────────────────────────
    # SQUEEZE REGIMES
    # ────────────────────────────────────────────────────────────
    
    "SQUEEZE": RegimeStrategyConfig(
        regime_name="SQUEEZE",
        primary_strategies=[
            "liquidation_capture",
        ],
        secondary_strategies=[
            "flow_following",
            "breakout",
        ],
        anti_strategies=[
            "mean_reversion",
            "funding_arb",
        ],
    ),
    
    "SQUEEZE_SETUP_LONG": RegimeStrategyConfig(
        regime_name="SQUEEZE_SETUP_LONG",
        primary_strategies=[
            "liquidation_capture",
        ],
        secondary_strategies=[
            "flow_following",
            "trend_following",
        ],
        anti_strategies=[
            "mean_reversion",
            "structure_reversal",
        ],
    ),
    
    "SQUEEZE_SETUP_SHORT": RegimeStrategyConfig(
        regime_name="SQUEEZE_SETUP_SHORT",
        primary_strategies=[
            "liquidation_capture",
        ],
        secondary_strategies=[
            "flow_following",
            "trend_following",
        ],
        anti_strategies=[
            "mean_reversion",
            "structure_reversal",
        ],
    ),
    
    # ────────────────────────────────────────────────────────────
    # BREAKOUT REGIMES
    # ────────────────────────────────────────────────────────────
    
    "BREAKOUT_CONFIRMED": RegimeStrategyConfig(
        regime_name="BREAKOUT_CONFIRMED",
        primary_strategies=[
            "trend_following",
            "flow_following",
        ],
        secondary_strategies=[
            "breakout",
        ],
        anti_strategies=[
            "mean_reversion",
            "structure_reversal",
        ],
    ),
    
    "BREAKDOWN_CONFIRMED": RegimeStrategyConfig(
        regime_name="BREAKDOWN_CONFIRMED",
        primary_strategies=[
            "trend_following",
            "flow_following",
        ],
        secondary_strategies=[
            "breakout",
        ],
        anti_strategies=[
            "mean_reversion",
            "structure_reversal",
        ],
    ),
    
    # ────────────────────────────────────────────────────────────
    # MIXED / UNDEFINED
    # ────────────────────────────────────────────────────────────
    
    "MIXED": RegimeStrategyConfig(
        regime_name="MIXED",
        primary_strategies=[
            "structure_reversal",
        ],
        secondary_strategies=[
            "mean_reversion",
            "funding_arb",
        ],
        anti_strategies=[
            "trend_following",
            "breakout",
        ],
    ),
    
    "UNDEFINED": RegimeStrategyConfig(
        regime_name="UNDEFINED",
        primary_strategies=[
            "funding_arb",  # Safest in undefined
        ],
        secondary_strategies=[
            "mean_reversion",
        ],
        anti_strategies=[
            "trend_following",
            "breakout",
            "liquidation_capture",
        ],
    ),
    
    "CONFLICTED": RegimeStrategyConfig(
        regime_name="CONFLICTED",
        primary_strategies=[
            "funding_arb",  # Safest in conflicted
        ],
        secondary_strategies=[
            "structure_reversal",
        ],
        anti_strategies=[
            "trend_following",
            "breakout",
            "liquidation_capture",
            "flow_following",
        ],
    ),
}


# ══════════════════════════════════════════════════════════════
# HELPER FUNCTIONS
# ══════════════════════════════════════════════════════════════

def get_regime_config(regime_name: str) -> Optional[RegimeStrategyConfig]:
    """Get strategy config for a regime."""
    # Direct match
    if regime_name in REGIME_STRATEGY_MAP:
        return REGIME_STRATEGY_MAP[regime_name]
    
    # Partial match (for combined regimes like RANGE_LOW_VOL_NEUTRAL)
    for key in REGIME_STRATEGY_MAP:
        if key in regime_name or regime_name.startswith(key):
            return REGIME_STRATEGY_MAP[key]
    
    # Default to UNDEFINED
    return REGIME_STRATEGY_MAP.get("UNDEFINED")


def get_all_regimes() -> List[str]:
    """Get list of all defined regimes."""
    return list(REGIME_STRATEGY_MAP.keys())


def get_strategies_for_regime(regime_name: str) -> Dict[str, List[str]]:
    """Get strategy lists for a regime."""
    config = get_regime_config(regime_name)
    if config is None:
        return {
            "primary": [],
            "secondary": [],
            "anti": [],
        }
    
    return {
        "primary": config.primary_strategies,
        "secondary": config.secondary_strategies,
        "anti": config.anti_strategies,
    }


def get_regime_map_summary() -> Dict[str, Any]:
    """Get summary of regime-strategy mapping."""
    return {
        "total_regimes": len(REGIME_STRATEGY_MAP),
        "regimes": [
            {
                "regime": name,
                "primary_count": len(config.primary_strategies),
                "secondary_count": len(config.secondary_strategies),
                "anti_count": len(config.anti_strategies),
            }
            for name, config in REGIME_STRATEGY_MAP.items()
        ],
    }
