"""
PHASE 23.1 — Scenario Registry
==============================
Registry of predefined crisis scenarios.

Contains baseline scenarios for:
- Flash Crash
- Volatility Shock
- Correlation Spike
- Liquidity Freeze
- Regime Flip
"""

from typing import Dict, Any, Optional, List

from .simulation_types import (
    ScenarioType,
    SeverityLevel,
    SimulationScenario,
    SHOCK_MAGNITUDES,
)


# ══════════════════════════════════════════════════════════════
# SCENARIO REGISTRY
# ══════════════════════════════════════════════════════════════

SCENARIO_REGISTRY: Dict[str, SimulationScenario] = {
    # ─────────────────────────────────────────────────────────
    # FLASH CRASH SCENARIOS
    # ─────────────────────────────────────────────────────────
    "flash_crash_low": SimulationScenario(
        scenario_name="flash_crash_low",
        scenario_type=ScenarioType.FLASH_CRASH,
        severity=SeverityLevel.LOW,
        price_shock=-0.08,
        volatility_shock=0.30,
        liquidity_shock=-0.25,
        correlation_shock=0.20,
        description="Minor flash crash with 8% price drop",
    ),
    "flash_crash_medium": SimulationScenario(
        scenario_name="flash_crash_medium",
        scenario_type=ScenarioType.FLASH_CRASH,
        severity=SeverityLevel.MEDIUM,
        price_shock=-0.15,
        volatility_shock=0.55,
        liquidity_shock=-0.40,
        correlation_shock=0.30,
        description="Moderate flash crash with 15% price drop",
    ),
    "flash_crash_high": SimulationScenario(
        scenario_name="flash_crash_high",
        scenario_type=ScenarioType.FLASH_CRASH,
        severity=SeverityLevel.HIGH,
        price_shock=-0.25,
        volatility_shock=0.85,
        liquidity_shock=-0.55,
        correlation_shock=0.45,
        description="Severe flash crash with 25% price drop",
    ),
    "flash_crash_extreme": SimulationScenario(
        scenario_name="flash_crash_extreme",
        scenario_type=ScenarioType.FLASH_CRASH,
        severity=SeverityLevel.EXTREME,
        price_shock=-0.40,
        volatility_shock=1.30,
        liquidity_shock=-0.75,
        correlation_shock=0.60,
        description="Extreme flash crash (Black Swan) with 40% price drop",
    ),
    
    # ─────────────────────────────────────────────────────────
    # VOLATILITY SHOCK SCENARIOS
    # ─────────────────────────────────────────────────────────
    "vol_shock_low": SimulationScenario(
        scenario_name="vol_shock_low",
        scenario_type=ScenarioType.VOL_SHOCK,
        severity=SeverityLevel.LOW,
        price_shock=-0.03,
        volatility_shock=0.35,
        liquidity_shock=-0.15,
        correlation_shock=0.15,
        description="Minor volatility expansion",
    ),
    "vol_shock_medium": SimulationScenario(
        scenario_name="vol_shock_medium",
        scenario_type=ScenarioType.VOL_SHOCK,
        severity=SeverityLevel.MEDIUM,
        price_shock=-0.06,
        volatility_shock=0.65,
        liquidity_shock=-0.30,
        correlation_shock=0.25,
        description="Moderate volatility spike",
    ),
    "vol_shock_high": SimulationScenario(
        scenario_name="vol_shock_high",
        scenario_type=ScenarioType.VOL_SHOCK,
        severity=SeverityLevel.HIGH,
        price_shock=-0.10,
        volatility_shock=1.00,
        liquidity_shock=-0.45,
        correlation_shock=0.35,
        description="High volatility regime shift",
    ),
    "vol_shock_extreme": SimulationScenario(
        scenario_name="vol_shock_extreme",
        scenario_type=ScenarioType.VOL_SHOCK,
        severity=SeverityLevel.EXTREME,
        price_shock=-0.15,
        volatility_shock=1.50,
        liquidity_shock=-0.60,
        correlation_shock=0.50,
        description="Extreme volatility explosion",
    ),
    
    # ─────────────────────────────────────────────────────────
    # CORRELATION SPIKE SCENARIOS
    # ─────────────────────────────────────────────────────────
    "corr_spike_low": SimulationScenario(
        scenario_name="corr_spike_low",
        scenario_type=ScenarioType.CORR_SPIKE,
        severity=SeverityLevel.LOW,
        price_shock=-0.04,
        volatility_shock=0.20,
        liquidity_shock=-0.10,
        correlation_shock=0.25,
        description="Minor correlation increase, diversification weakens",
    ),
    "corr_spike_medium": SimulationScenario(
        scenario_name="corr_spike_medium",
        scenario_type=ScenarioType.CORR_SPIKE,
        severity=SeverityLevel.MEDIUM,
        price_shock=-0.08,
        volatility_shock=0.40,
        liquidity_shock=-0.20,
        correlation_shock=0.40,
        description="Moderate correlation spike, diversification failing",
    ),
    "corr_spike_high": SimulationScenario(
        scenario_name="corr_spike_high",
        scenario_type=ScenarioType.CORR_SPIKE,
        severity=SeverityLevel.HIGH,
        price_shock=-0.12,
        volatility_shock=0.60,
        liquidity_shock=-0.35,
        correlation_shock=0.55,
        description="High correlation regime, diversification breakdown",
    ),
    "corr_spike_extreme": SimulationScenario(
        scenario_name="corr_spike_extreme",
        scenario_type=ScenarioType.CORR_SPIKE,
        severity=SeverityLevel.EXTREME,
        price_shock=-0.18,
        volatility_shock=0.90,
        liquidity_shock=-0.50,
        correlation_shock=0.70,
        description="Extreme correlation (everything falls together)",
    ),
    
    # ─────────────────────────────────────────────────────────
    # LIQUIDITY FREEZE SCENARIOS
    # ─────────────────────────────────────────────────────────
    "liq_freeze_low": SimulationScenario(
        scenario_name="liq_freeze_low",
        scenario_type=ScenarioType.LIQ_FREEZE,
        severity=SeverityLevel.LOW,
        price_shock=-0.03,
        volatility_shock=0.25,
        liquidity_shock=-0.30,
        correlation_shock=0.15,
        description="Minor liquidity tightening",
    ),
    "liq_freeze_medium": SimulationScenario(
        scenario_name="liq_freeze_medium",
        scenario_type=ScenarioType.LIQ_FREEZE,
        severity=SeverityLevel.MEDIUM,
        price_shock=-0.07,
        volatility_shock=0.45,
        liquidity_shock=-0.50,
        correlation_shock=0.25,
        description="Moderate liquidity squeeze",
    ),
    "liq_freeze_high": SimulationScenario(
        scenario_name="liq_freeze_high",
        scenario_type=ScenarioType.LIQ_FREEZE,
        severity=SeverityLevel.HIGH,
        price_shock=-0.12,
        volatility_shock=0.70,
        liquidity_shock=-0.70,
        correlation_shock=0.40,
        description="Severe liquidity freeze, slippage increases",
    ),
    "liq_freeze_extreme": SimulationScenario(
        scenario_name="liq_freeze_extreme",
        scenario_type=ScenarioType.LIQ_FREEZE,
        severity=SeverityLevel.EXTREME,
        price_shock=-0.18,
        volatility_shock=1.00,
        liquidity_shock=-0.85,
        correlation_shock=0.55,
        description="Complete liquidity crisis",
    ),
    
    # ─────────────────────────────────────────────────────────
    # REGIME FLIP SCENARIOS
    # ─────────────────────────────────────────────────────────
    "regime_flip_trend_to_range": SimulationScenario(
        scenario_name="regime_flip_trend_to_range",
        scenario_type=ScenarioType.REGIME_FLIP,
        severity=SeverityLevel.MEDIUM,
        price_shock=-0.05,
        volatility_shock=0.30,
        liquidity_shock=-0.15,
        correlation_shock=0.20,
        regime_shift="TREND_TO_RANGE",
        description="Market transitions from trending to ranging",
    ),
    "regime_flip_range_to_vol": SimulationScenario(
        scenario_name="regime_flip_range_to_vol",
        scenario_type=ScenarioType.REGIME_FLIP,
        severity=SeverityLevel.HIGH,
        price_shock=-0.10,
        volatility_shock=0.70,
        liquidity_shock=-0.30,
        correlation_shock=0.35,
        regime_shift="RANGE_TO_VOL_EXPANSION",
        description="Market breaks out of range into volatility expansion",
    ),
    "regime_flip_bull_to_bear": SimulationScenario(
        scenario_name="regime_flip_bull_to_bear",
        scenario_type=ScenarioType.REGIME_FLIP,
        severity=SeverityLevel.HIGH,
        price_shock=-0.20,
        volatility_shock=0.80,
        liquidity_shock=-0.40,
        correlation_shock=0.45,
        regime_shift="BULL_TO_BEAR",
        description="Market regime flip from bull to bear",
    ),
    "regime_flip_crisis": SimulationScenario(
        scenario_name="regime_flip_crisis",
        scenario_type=ScenarioType.REGIME_FLIP,
        severity=SeverityLevel.EXTREME,
        price_shock=-0.30,
        volatility_shock=1.20,
        liquidity_shock=-0.65,
        correlation_shock=0.60,
        regime_shift="CRISIS_MODE",
        description="Full crisis regime activation",
    ),
}


# ══════════════════════════════════════════════════════════════
# REGISTRY FUNCTIONS
# ══════════════════════════════════════════════════════════════

def get_scenario(scenario_name: str) -> Optional[SimulationScenario]:
    """Get scenario by name."""
    return SCENARIO_REGISTRY.get(scenario_name)


def list_scenarios() -> List[Dict[str, Any]]:
    """List all available scenarios."""
    return [
        {
            "name": name,
            "type": scenario.scenario_type.value,
            "severity": scenario.severity.value,
            "description": scenario.description,
        }
        for name, scenario in SCENARIO_REGISTRY.items()
    ]


def get_scenarios_by_type(scenario_type: ScenarioType) -> List[SimulationScenario]:
    """Get all scenarios of a specific type."""
    return [
        scenario
        for scenario in SCENARIO_REGISTRY.values()
        if scenario.scenario_type == scenario_type
    ]


def get_scenarios_by_severity(severity: SeverityLevel) -> List[SimulationScenario]:
    """Get all scenarios of a specific severity."""
    return [
        scenario
        for scenario in SCENARIO_REGISTRY.values()
        if scenario.severity == severity
    ]
