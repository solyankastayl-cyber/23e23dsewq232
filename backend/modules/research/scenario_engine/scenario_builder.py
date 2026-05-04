"""
PHASE 6.2 - Scenario Builder
=============================
Builder pattern for creating stress test scenarios.
"""

from typing import Dict, List, Optional, Any
from datetime import datetime, timezone
import uuid

from .scenario_types import (
    ScenarioDefinition, ShockParameters,
    ScenarioType, ScenarioSeverity, ScenarioStatus
)


class ScenarioBuilder:
    """
    Builder pattern for creating scenarios
    """
    
    def __init__(self):
        self._scenario_id: Optional[str] = None
        self._name: Optional[str] = None
        self._description: str = ""
        self._scenario_type: Optional[ScenarioType] = None
        self._shock_parameters: Optional[ShockParameters] = None
        self._severity: ScenarioSeverity = ScenarioSeverity.MEDIUM
        self._duration_candles: int = 50
        self._applicable_symbols: List[str] = ["BTC", "ETH", "SOL"]
        self._applicable_timeframes: List[str] = ["1h", "4h", "1d"]
        self._tags: List[str] = []
        self._author: str = "system"
    
    def with_id(self, scenario_id: str) -> 'ScenarioBuilder':
        self._scenario_id = scenario_id
        return self
    
    def with_name(self, name: str) -> 'ScenarioBuilder':
        self._name = name
        return self
    
    def with_description(self, description: str) -> 'ScenarioBuilder':
        self._description = description
        return self
    
    def with_type(self, scenario_type: ScenarioType) -> 'ScenarioBuilder':
        self._scenario_type = scenario_type
        return self
    
    def with_shock_parameters(
        self,
        price_change_pct: float = 0.0,
        price_volatility_multiplier: float = 1.0,
        liquidity_reduction_pct: float = 0.0,
        spread_multiplier: float = 1.0,
        volume_spike_multiplier: float = 1.0,
        shock_duration_candles: int = 10,
        recovery_candles: int = 20,
        slippage_multiplier: float = 1.0,
        fee_multiplier: float = 1.0,
        latency_ms: int = 0
    ) -> 'ScenarioBuilder':
        """Set shock parameters"""
        self._shock_parameters = ShockParameters(
            price_change_pct=price_change_pct,
            price_volatility_multiplier=price_volatility_multiplier,
            liquidity_reduction_pct=liquidity_reduction_pct,
            spread_multiplier=spread_multiplier,
            volume_spike_multiplier=volume_spike_multiplier,
            shock_duration_candles=shock_duration_candles,
            recovery_candles=recovery_candles,
            slippage_multiplier=slippage_multiplier,
            fee_multiplier=fee_multiplier,
            latency_ms=latency_ms
        )
        return self
    
    def with_severity(self, severity: ScenarioSeverity) -> 'ScenarioBuilder':
        self._severity = severity
        return self
    
    def with_duration(self, duration_candles: int) -> 'ScenarioBuilder':
        self._duration_candles = duration_candles
        return self
    
    def with_applicable_symbols(self, symbols: List[str]) -> 'ScenarioBuilder':
        self._applicable_symbols = symbols
        return self
    
    def with_applicable_timeframes(self, timeframes: List[str]) -> 'ScenarioBuilder':
        self._applicable_timeframes = timeframes
        return self
    
    def with_tags(self, tags: List[str]) -> 'ScenarioBuilder':
        self._tags = tags
        return self
    
    def with_author(self, author: str) -> 'ScenarioBuilder':
        self._author = author
        return self
    
    def validate(self) -> List[str]:
        """Validate the scenario configuration"""
        errors = []
        
        if not self._name:
            errors.append("Name is required")
        
        if not self._scenario_type:
            errors.append("Scenario type is required")
        
        if not self._shock_parameters:
            errors.append("Shock parameters are required")
        
        if self._shock_parameters:
            if self._shock_parameters.shock_duration_candles <= 0:
                errors.append("Shock duration must be positive")
            
            if self._shock_parameters.price_volatility_multiplier < 0:
                errors.append("Volatility multiplier must be non-negative")
        
        if self._duration_candles <= 0:
            errors.append("Duration must be positive")
        
        return errors
    
    def build(self) -> ScenarioDefinition:
        """Build the scenario"""
        errors = self.validate()
        if errors:
            raise ValueError(f"Invalid scenario: {', '.join(errors)}")
        
        scenario_id = self._scenario_id or f"scn_{uuid.uuid4().hex[:12]}"
        now = datetime.now(timezone.utc)
        
        return ScenarioDefinition(
            scenario_id=scenario_id,
            name=self._name,
            description=self._description,
            scenario_type=self._scenario_type,
            shock_parameters=self._shock_parameters,
            severity=self._severity,
            duration_candles=self._duration_candles,
            applicable_symbols=self._applicable_symbols,
            applicable_timeframes=self._applicable_timeframes,
            status=ScenarioStatus.DRAFT,
            author=self._author,
            created_at=now,
            updated_at=now,
            tags=self._tags
        )
    
    @staticmethod
    def from_dict(data: Dict) -> 'ScenarioBuilder':
        """Create builder from dictionary"""
        builder = ScenarioBuilder()
        
        if 'scenario_id' in data:
            builder.with_id(data['scenario_id'])
        
        if 'name' in data:
            builder.with_name(data['name'])
        
        if 'description' in data:
            builder.with_description(data['description'])
        
        if 'scenario_type' in data:
            stype = data['scenario_type']
            if isinstance(stype, str):
                stype = ScenarioType(stype)
            builder.with_type(stype)
        
        if 'shock_parameters' in data:
            sp = data['shock_parameters']
            builder.with_shock_parameters(
                price_change_pct=sp.get('price_change_pct', 0.0),
                price_volatility_multiplier=sp.get('price_volatility_multiplier', 1.0),
                liquidity_reduction_pct=sp.get('liquidity_reduction_pct', 0.0),
                spread_multiplier=sp.get('spread_multiplier', 1.0),
                volume_spike_multiplier=sp.get('volume_spike_multiplier', 1.0),
                shock_duration_candles=sp.get('shock_duration_candles', 10),
                recovery_candles=sp.get('recovery_candles', 20),
                slippage_multiplier=sp.get('slippage_multiplier', 1.0),
                fee_multiplier=sp.get('fee_multiplier', 1.0),
                latency_ms=sp.get('latency_ms', 0)
            )
        
        if 'severity' in data:
            severity = data['severity']
            if isinstance(severity, str):
                severity = ScenarioSeverity(severity)
            builder.with_severity(severity)
        
        if 'duration_candles' in data:
            builder.with_duration(data['duration_candles'])
        
        if 'applicable_symbols' in data:
            builder.with_applicable_symbols(data['applicable_symbols'])
        
        if 'applicable_timeframes' in data:
            builder.with_applicable_timeframes(data['applicable_timeframes'])
        
        if 'tags' in data:
            builder.with_tags(data['tags'])
        
        if 'author' in data:
            builder.with_author(data['author'])
        
        return builder


# Preset builders for common scenarios
class ScenarioPresets:
    """Factory for common scenario presets"""
    
    @staticmethod
    def flash_crash(severity_pct: float = 20.0) -> ScenarioBuilder:
        """Create flash crash scenario"""
        return (
            ScenarioBuilder()
            .with_name(f"Flash Crash -{severity_pct}%")
            .with_description(f"Sudden {severity_pct}% price drop")
            .with_type(ScenarioType.FLASH_CRASH)
            .with_severity(ScenarioSeverity.EXTREME if severity_pct >= 20 else ScenarioSeverity.HIGH)
            .with_shock_parameters(
                price_change_pct=-severity_pct,
                price_volatility_multiplier=3.0,
                liquidity_reduction_pct=40.0,
                spread_multiplier=4.0,
                volume_spike_multiplier=5.0,
                shock_duration_candles=10,
                recovery_candles=30,
                slippage_multiplier=3.0
            )
            .with_tags(["crash", "preset"])
        )
    
    @staticmethod
    def liquidity_crisis(reduction_pct: float = 50.0) -> ScenarioBuilder:
        """Create liquidity crisis scenario"""
        return (
            ScenarioBuilder()
            .with_name(f"Liquidity Crisis -{reduction_pct}%")
            .with_description(f"Market liquidity drops by {reduction_pct}%")
            .with_type(ScenarioType.LIQUIDITY_DRAIN)
            .with_severity(ScenarioSeverity.HIGH)
            .with_shock_parameters(
                price_change_pct=-5.0,
                price_volatility_multiplier=1.5,
                liquidity_reduction_pct=reduction_pct,
                spread_multiplier=5.0,
                volume_spike_multiplier=0.3,
                shock_duration_candles=25,
                recovery_candles=20,
                slippage_multiplier=4.0
            )
            .with_tags(["liquidity", "preset"])
        )
    
    @staticmethod
    def black_swan() -> ScenarioBuilder:
        """Create black swan scenario"""
        return (
            ScenarioBuilder()
            .with_name("Black Swan Event")
            .with_description("Extreme tail event combining multiple stresses")
            .with_type(ScenarioType.BLACK_SWAN)
            .with_severity(ScenarioSeverity.EXTREME)
            .with_shock_parameters(
                price_change_pct=-50.0,
                price_volatility_multiplier=5.0,
                liquidity_reduction_pct=80.0,
                spread_multiplier=10.0,
                volume_spike_multiplier=10.0,
                shock_duration_candles=20,
                recovery_candles=60,
                slippage_multiplier=6.0,
                latency_ms=2000
            )
            .with_duration(100)
            .with_tags(["black-swan", "extreme", "preset"])
        )
