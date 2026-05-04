"""
PHASE 6.2 - Scenario Registry
==============================
Registry with initial 7 stress test scenarios.
"""

from datetime import datetime, timezone
from typing import Dict, List, Optional
from .scenario_types import (
    ScenarioDefinition, ShockParameters,
    ScenarioType, ScenarioSeverity, ScenarioStatus
)


# Initial 7 stress test scenarios
INITIAL_SCENARIOS: List[ScenarioDefinition] = [
    # 1. Flash Crash -20%
    ScenarioDefinition(
        scenario_id="flash_crash_20",
        name="Flash Crash -20%",
        description="Sudden 20% price drop within 10 candles, simulating a flash crash event like March 2020 COVID crash",
        scenario_type=ScenarioType.FLASH_CRASH,
        shock_parameters=ShockParameters(
            price_change_pct=-20.0,
            price_volatility_multiplier=3.0,
            liquidity_reduction_pct=40.0,
            spread_multiplier=4.0,
            volume_spike_multiplier=5.0,
            shock_duration_candles=10,
            recovery_candles=30,
            slippage_multiplier=3.0,
            fee_multiplier=1.0,
            latency_ms=500
        ),
        severity=ScenarioSeverity.EXTREME,
        duration_candles=50,
        status=ScenarioStatus.ACTIVE,
        tags=["crash", "extreme", "black-swan"]
    ),
    
    # 2. Volatility Spike 3x
    ScenarioDefinition(
        scenario_id="volatility_spike_3x",
        name="Volatility Spike 3x",
        description="Volatility increases 3x normal levels, causing wider price swings and uncertainty",
        scenario_type=ScenarioType.VOLATILITY_SPIKE,
        shock_parameters=ShockParameters(
            price_change_pct=0.0,
            price_volatility_multiplier=3.0,
            liquidity_reduction_pct=20.0,
            spread_multiplier=2.0,
            volume_spike_multiplier=2.5,
            shock_duration_candles=20,
            recovery_candles=15,
            slippage_multiplier=2.0,
            fee_multiplier=1.0,
            latency_ms=100
        ),
        severity=ScenarioSeverity.HIGH,
        duration_candles=40,
        status=ScenarioStatus.ACTIVE,
        tags=["volatility", "uncertainty", "risk"]
    ),
    
    # 3. Liquidity Drain 50%
    ScenarioDefinition(
        scenario_id="liquidity_drain_50",
        name="Liquidity Drain 50%",
        description="Market liquidity drops by 50%, causing high slippage and difficulty executing orders",
        scenario_type=ScenarioType.LIQUIDITY_DRAIN,
        shock_parameters=ShockParameters(
            price_change_pct=-5.0,
            price_volatility_multiplier=1.5,
            liquidity_reduction_pct=50.0,
            spread_multiplier=5.0,
            volume_spike_multiplier=0.3,
            shock_duration_candles=25,
            recovery_candles=20,
            slippage_multiplier=4.0,
            fee_multiplier=1.2,
            latency_ms=200
        ),
        severity=ScenarioSeverity.HIGH,
        duration_candles=50,
        status=ScenarioStatus.ACTIVE,
        tags=["liquidity", "execution", "slippage"]
    ),
    
    # 4. Trend Acceleration
    ScenarioDefinition(
        scenario_id="trend_acceleration",
        name="Trend Acceleration",
        description="Strong directional move accelerates rapidly, testing trend-following and breakout strategies",
        scenario_type=ScenarioType.TREND_ACCELERATION,
        shock_parameters=ShockParameters(
            price_change_pct=30.0,
            price_volatility_multiplier=2.0,
            liquidity_reduction_pct=10.0,
            spread_multiplier=1.5,
            volume_spike_multiplier=3.0,
            shock_duration_candles=15,
            recovery_candles=10,
            slippage_multiplier=1.5,
            fee_multiplier=1.0,
            latency_ms=50
        ),
        severity=ScenarioSeverity.MEDIUM,
        duration_candles=30,
        status=ScenarioStatus.ACTIVE,
        tags=["trend", "momentum", "breakout"]
    ),
    
    # 5. Regime Flip
    ScenarioDefinition(
        scenario_id="regime_flip",
        name="Regime Flip",
        description="Market suddenly changes from trending to ranging or vice versa, testing strategy adaptability",
        scenario_type=ScenarioType.REGIME_FLIP,
        shock_parameters=ShockParameters(
            price_change_pct=0.0,
            price_volatility_multiplier=0.5,  # Volatility compression
            liquidity_reduction_pct=15.0,
            spread_multiplier=1.3,
            volume_spike_multiplier=0.6,
            shock_duration_candles=30,
            recovery_candles=0,  # No recovery, just new regime
            slippage_multiplier=1.2,
            fee_multiplier=1.0,
            latency_ms=0
        ),
        severity=ScenarioSeverity.MEDIUM,
        duration_candles=60,
        status=ScenarioStatus.ACTIVE,
        tags=["regime", "adaptation", "strategy-switch"]
    ),
    
    # 6. Cascade Liquidation
    ScenarioDefinition(
        scenario_id="cascade_liquidation",
        name="Cascade Liquidation",
        description="Cascading liquidations cause rapid price moves and forced selling, like Luna collapse",
        scenario_type=ScenarioType.CASCADE_LIQUIDATION,
        shock_parameters=ShockParameters(
            price_change_pct=-35.0,
            price_volatility_multiplier=4.0,
            liquidity_reduction_pct=60.0,
            spread_multiplier=6.0,
            volume_spike_multiplier=8.0,
            shock_duration_candles=15,
            recovery_candles=40,
            slippage_multiplier=5.0,
            fee_multiplier=1.5,
            latency_ms=1000
        ),
        severity=ScenarioSeverity.EXTREME,
        duration_candles=60,
        status=ScenarioStatus.ACTIVE,
        tags=["liquidation", "extreme", "survival"]
    ),
    
    # 7. Exchange Outage
    ScenarioDefinition(
        scenario_id="exchange_outage",
        name="Exchange Outage",
        description="Primary exchange goes offline, testing failover and multi-exchange routing",
        scenario_type=ScenarioType.EXCHANGE_OUTAGE,
        shock_parameters=ShockParameters(
            price_change_pct=-10.0,  # Gap on return
            price_volatility_multiplier=2.0,
            liquidity_reduction_pct=70.0,  # Only secondary exchanges
            spread_multiplier=3.0,
            volume_spike_multiplier=0.2,  # Very low volume
            shock_duration_candles=20,  # Outage duration
            recovery_candles=5,
            slippage_multiplier=2.5,
            fee_multiplier=1.0,
            latency_ms=5000  # Extreme latency
        ),
        severity=ScenarioSeverity.HIGH,
        duration_candles=30,
        status=ScenarioStatus.ACTIVE,
        tags=["exchange", "outage", "failover"]
    )
]


class ScenarioRegistry:
    """
    Registry for managing scenario definitions
    """
    
    def __init__(self):
        self._scenarios: Dict[str, ScenarioDefinition] = {}
        self._load_initial_scenarios()
    
    def _load_initial_scenarios(self):
        """Load initial scenarios"""
        now = datetime.now(timezone.utc)
        for s in INITIAL_SCENARIOS:
            s.created_at = now
            s.updated_at = now
            self._scenarios[s.scenario_id] = s
    
    def get(self, scenario_id: str) -> Optional[ScenarioDefinition]:
        """Get scenario by ID"""
        return self._scenarios.get(scenario_id)
    
    def get_all(self) -> List[ScenarioDefinition]:
        """Get all scenarios"""
        return list(self._scenarios.values())
    
    def get_active(self) -> List[ScenarioDefinition]:
        """Get active scenarios"""
        return [s for s in self._scenarios.values() if s.status == ScenarioStatus.ACTIVE]
    
    def get_by_type(self, scenario_type: ScenarioType) -> List[ScenarioDefinition]:
        """Get scenarios by type"""
        return [s for s in self._scenarios.values() if s.scenario_type == scenario_type]
    
    def get_by_severity(self, severity: ScenarioSeverity) -> List[ScenarioDefinition]:
        """Get scenarios by severity"""
        return [s for s in self._scenarios.values() if s.severity == severity]
    
    def add(self, scenario: ScenarioDefinition) -> bool:
        """Add new scenario"""
        if scenario.scenario_id in self._scenarios:
            return False
        
        now = datetime.now(timezone.utc)
        scenario.created_at = now
        scenario.updated_at = now
        self._scenarios[scenario.scenario_id] = scenario
        return True
    
    def update(self, scenario: ScenarioDefinition) -> bool:
        """Update existing scenario"""
        if scenario.scenario_id not in self._scenarios:
            return False
        
        scenario.updated_at = datetime.now(timezone.utc)
        self._scenarios[scenario.scenario_id] = scenario
        return True
    
    def delete(self, scenario_id: str) -> bool:
        """Delete scenario"""
        if scenario_id not in self._scenarios:
            return False
        
        del self._scenarios[scenario_id]
        return True
    
    def get_stats(self) -> Dict:
        """Get registry statistics"""
        scenarios = list(self._scenarios.values())
        
        severity_counts = {}
        for severity in ScenarioSeverity:
            severity_counts[severity.value] = len([s for s in scenarios if s.severity == severity])
        
        type_counts = {}
        for stype in ScenarioType:
            type_counts[stype.value] = len([s for s in scenarios if s.scenario_type == stype])
        
        return {
            "total": len(scenarios),
            "by_severity": severity_counts,
            "by_type": type_counts
        }


# Singleton instance
_registry_instance: Optional[ScenarioRegistry] = None


def get_scenario_registry() -> ScenarioRegistry:
    """Get singleton registry instance"""
    global _registry_instance
    if _registry_instance is None:
        _registry_instance = ScenarioRegistry()
    return _registry_instance
