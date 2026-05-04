"""
PHASE 19.1 — Strategy Registry
==============================
Registry of strategy families with their configurations.

Each strategy has:
- preferred_regimes: where it works best
- anti_regimes: where it fails
- volatility preferences
- breadth requirements
- interaction requirements
"""

from typing import Dict, Optional

from modules.strategy_brain.strategy_types import (
    StrategyType,
    StrategyConfig,
    StrategyStateEnum,
    RiskProfile,
)


# ══════════════════════════════════════════════════════════════
# STRATEGY REGISTRY
# ══════════════════════════════════════════════════════════════

STRATEGY_REGISTRY: Dict[str, StrategyConfig] = {
    
    # ────────────────────────────────────────────────────────────
    # TREND FOLLOWING
    # ────────────────────────────────────────────────────────────
    StrategyType.TREND_FOLLOWING.value: StrategyConfig(
        strategy_type=StrategyType.TREND_FOLLOWING,
        name="Trend Following",
        description="Follow established trends with momentum confirmation",
        
        preferred_regimes=[
            "TREND_UP", "TREND_DOWN",
            "BREAKOUT_CONFIRMED", "BREAKDOWN_CONFIRMED",
        ],
        anti_regimes=[
            "RANGE", "RANGE_LOW_VOL_NEUTRAL", "RANGE_ACCUMULATION",
            "CONFLICTED", "UNDEFINED",
        ],
        
        preferred_volatility=["NORMAL", "HIGH", "EXPANDING"],
        anti_volatility=["CONTRACTING"],
        
        min_breadth="MIXED",
        
        preferred_interaction=["REINFORCED", "NEUTRAL"],
        anti_interaction=["CONFLICTED", "CANCELLED"],
        
        risk_profile=RiskProfile.MODERATE,
        default_state=StrategyStateEnum.REDUCED,
    ),
    
    # ────────────────────────────────────────────────────────────
    # MEAN REVERSION
    # ────────────────────────────────────────────────────────────
    StrategyType.MEAN_REVERSION.value: StrategyConfig(
        strategy_type=StrategyType.MEAN_REVERSION,
        name="Mean Reversion",
        description="Fade extremes and trade back to mean",
        
        preferred_regimes=[
            "RANGE", "RANGE_LOW_VOL_NEUTRAL", "RANGE_ACCUMULATION",
            "MIXED", "CONSOLIDATION",
        ],
        anti_regimes=[
            "TREND_UP", "TREND_DOWN",
            "BREAKOUT_CONFIRMED", "BREAKDOWN_CONFIRMED",
            "SQUEEZE_SETUP_LONG", "SQUEEZE_SETUP_SHORT",
        ],
        
        preferred_volatility=["NORMAL", "HIGH"],
        anti_volatility=["EXPANDING"],
        
        min_breadth="WEAK",  # Can work in weak breadth
        
        preferred_interaction=["NEUTRAL", "CONFLICTED"],
        anti_interaction=["REINFORCED"],  # Strong trend = bad for MR
        
        risk_profile=RiskProfile.CONSERVATIVE,
        default_state=StrategyStateEnum.REDUCED,
    ),
    
    # ────────────────────────────────────────────────────────────
    # BREAKOUT
    # ────────────────────────────────────────────────────────────
    StrategyType.BREAKOUT.value: StrategyConfig(
        strategy_type=StrategyType.BREAKOUT,
        name="Breakout",
        description="Trade range breakouts and structure breaks",
        
        preferred_regimes=[
            "RANGE_ACCUMULATION", "CONSOLIDATION",
            "SQUEEZE_SETUP_LONG", "SQUEEZE_SETUP_SHORT",
        ],
        anti_regimes=[
            "TREND_UP", "TREND_DOWN",  # Already broke out
            "CONFLICTED", "RISK_OFF",
        ],
        
        preferred_volatility=["LOW", "NORMAL", "EXPANDING"],
        anti_volatility=["HIGH"],  # Too volatile = fake breakouts
        
        min_breadth="MIXED",
        
        preferred_interaction=["REINFORCED", "NEUTRAL"],
        anti_interaction=["CANCELLED"],
        
        risk_profile=RiskProfile.AGGRESSIVE,
        default_state=StrategyStateEnum.REDUCED,
    ),
    
    # ────────────────────────────────────────────────────────────
    # LIQUIDATION CAPTURE
    # ────────────────────────────────────────────────────────────
    StrategyType.LIQUIDATION_CAPTURE.value: StrategyConfig(
        strategy_type=StrategyType.LIQUIDATION_CAPTURE,
        name="Liquidation Capture",
        description="Trade liquidation cascades and squeeze setups",
        
        preferred_regimes=[
            "SQUEEZE_SETUP_LONG", "SQUEEZE_SETUP_SHORT",
            "BREAKOUT_CONFIRMED", "BREAKDOWN_CONFIRMED",
        ],
        anti_regimes=[
            "RANGE_LOW_VOL_NEUTRAL", "CONSOLIDATION",
            "UNDEFINED",
        ],
        
        preferred_volatility=["HIGH", "EXPANDING"],
        anti_volatility=["LOW", "CONTRACTING"],
        
        min_breadth="WEAK",  # Works in weak breadth too
        
        preferred_interaction=["REINFORCED"],
        anti_interaction=["CANCELLED"],
        
        risk_profile=RiskProfile.AGGRESSIVE,
        default_state=StrategyStateEnum.DISABLED,  # Only when conditions met
    ),
    
    # ────────────────────────────────────────────────────────────
    # FLOW FOLLOWING
    # ────────────────────────────────────────────────────────────
    StrategyType.FLOW_FOLLOWING.value: StrategyConfig(
        strategy_type=StrategyType.FLOW_FOLLOWING,
        name="Flow Following",
        description="Follow order flow and exchange signals",
        
        preferred_regimes=[
            "TREND_UP", "TREND_DOWN",
            "BREAKOUT_CONFIRMED", "BREAKDOWN_CONFIRMED",
        ],
        anti_regimes=[
            "RANGE", "CONFLICTED", "UNDEFINED",
        ],
        
        preferred_volatility=["NORMAL", "HIGH"],
        anti_volatility=["LOW"],  # Low vol = weak flow signals
        
        min_breadth="MIXED",
        
        preferred_interaction=["REINFORCED", "NEUTRAL"],
        anti_interaction=["CANCELLED"],
        
        risk_profile=RiskProfile.MODERATE,
        default_state=StrategyStateEnum.REDUCED,
    ),
    
    # ────────────────────────────────────────────────────────────
    # VOLATILITY EXPANSION
    # ────────────────────────────────────────────────────────────
    StrategyType.VOLATILITY_EXPANSION.value: StrategyConfig(
        strategy_type=StrategyType.VOLATILITY_EXPANSION,
        name="Volatility Expansion",
        description="Trade volatility breakouts from compression",
        
        preferred_regimes=[
            "CONSOLIDATION", "RANGE_ACCUMULATION",
            "SQUEEZE_SETUP_LONG", "SQUEEZE_SETUP_SHORT",
        ],
        anti_regimes=[
            "TREND_UP", "TREND_DOWN",
            "CONFLICTED", "RISK_OFF",
        ],
        
        preferred_volatility=["LOW", "CONTRACTING"],  # Before expansion
        anti_volatility=["HIGH"],  # Already expanded
        
        min_breadth="MIXED",
        
        preferred_interaction=["NEUTRAL", "REINFORCED"],
        anti_interaction=["CANCELLED"],
        
        risk_profile=RiskProfile.AGGRESSIVE,
        default_state=StrategyStateEnum.DISABLED,
    ),
    
    # ────────────────────────────────────────────────────────────
    # FUNDING ARB
    # ────────────────────────────────────────────────────────────
    StrategyType.FUNDING_ARB.value: StrategyConfig(
        strategy_type=StrategyType.FUNDING_ARB,
        name="Funding Arbitrage",
        description="Trade funding rate extremes",
        
        preferred_regimes=[
            "RANGE", "RANGE_LOW_VOL_NEUTRAL",
            "CONSOLIDATION",
        ],
        anti_regimes=[
            "TREND_UP", "TREND_DOWN",
            "BREAKOUT_CONFIRMED", "BREAKDOWN_CONFIRMED",
        ],
        
        preferred_volatility=["LOW", "NORMAL"],
        anti_volatility=["HIGH", "EXPANDING"],  # High vol = risky
        
        min_breadth="WEAK",
        
        preferred_interaction=["NEUTRAL"],
        anti_interaction=["REINFORCED"],  # Strong trend breaks arb
        
        risk_profile=RiskProfile.CONSERVATIVE,
        default_state=StrategyStateEnum.REDUCED,
    ),
    
    # ────────────────────────────────────────────────────────────
    # STRUCTURE REVERSAL
    # ────────────────────────────────────────────────────────────
    StrategyType.STRUCTURE_REVERSAL.value: StrategyConfig(
        strategy_type=StrategyType.STRUCTURE_REVERSAL,
        name="Structure Reversal",
        description="Trade key structure breaks for reversals",
        
        preferred_regimes=[
            "RANGE", "MIXED",
            "TREND_UP", "TREND_DOWN",  # End of trend
        ],
        anti_regimes=[
            "BREAKOUT_CONFIRMED", "BREAKDOWN_CONFIRMED",
            "SQUEEZE_SETUP_LONG", "SQUEEZE_SETUP_SHORT",
        ],
        
        preferred_volatility=["NORMAL", "HIGH"],
        anti_volatility=["EXPANDING"],  # Too volatile for reversals
        
        min_breadth="MIXED",
        
        preferred_interaction=["CONFLICTED", "NEUTRAL"],  # Conflict = reversal setup
        anti_interaction=["REINFORCED"],  # Strong trend = no reversal
        
        risk_profile=RiskProfile.AGGRESSIVE,
        default_state=StrategyStateEnum.DISABLED,
    ),
}


# ══════════════════════════════════════════════════════════════
# HELPER FUNCTIONS
# ══════════════════════════════════════════════════════════════

def get_strategy_config(strategy_name: str) -> Optional[StrategyConfig]:
    """Get strategy configuration by name."""
    return STRATEGY_REGISTRY.get(strategy_name)


def get_all_strategies() -> list:
    """Get list of all strategy names."""
    return list(STRATEGY_REGISTRY.keys())


def get_strategies_by_risk_profile(risk_profile: RiskProfile) -> list:
    """Get strategies by risk profile."""
    return [
        name for name, config in STRATEGY_REGISTRY.items()
        if config.risk_profile == risk_profile
    ]


def get_strategies_for_regime(regime: str) -> list:
    """Get strategies suitable for a regime."""
    suitable = []
    for name, config in STRATEGY_REGISTRY.items():
        if regime in config.preferred_regimes:
            suitable.append(name)
    return suitable


def get_registry_summary() -> dict:
    """Get registry summary."""
    return {
        "total_strategies": len(STRATEGY_REGISTRY),
        "strategies": [
            {
                "name": name,
                "type": config.strategy_type.value,
                "risk_profile": config.risk_profile.value,
                "default_state": config.default_state.value,
            }
            for name, config in STRATEGY_REGISTRY.items()
        ],
        "by_risk_profile": {
            "conservative": len(get_strategies_by_risk_profile(RiskProfile.CONSERVATIVE)),
            "moderate": len(get_strategies_by_risk_profile(RiskProfile.MODERATE)),
            "aggressive": len(get_strategies_by_risk_profile(RiskProfile.AGGRESSIVE)),
        },
    }
