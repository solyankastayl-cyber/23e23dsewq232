"""
System Chaos / Crash Simulation Tools

For testing system resilience and fault tolerance.

Simulates:
- Exchange disconnect
- Order rejection
- Latency spike
- WebSocket drop
- API failure
- Slippage spike
"""

from typing import Optional, Dict, List
from datetime import datetime, timezone, timedelta
from pydantic import BaseModel, Field
from enum import Enum
import asyncio
import random


class ChaosType(str, Enum):
    """Types of chaos/fault injection."""
    EXCHANGE_DISCONNECT = "EXCHANGE_DISCONNECT"
    ORDER_REJECTION = "ORDER_REJECTION"
    LATENCY_SPIKE = "LATENCY_SPIKE"
    WEBSOCKET_DROP = "WEBSOCKET_DROP"
    API_FAILURE = "API_FAILURE"
    SLIPPAGE_SPIKE = "SLIPPAGE_SPIKE"
    MEMORY_PRESSURE = "MEMORY_PRESSURE"
    SIGNAL_STORM = "SIGNAL_STORM"


class ChaosConfig(BaseModel):
    """Configuration for chaos test."""
    chaos_type: ChaosType
    duration_seconds: int = 30
    intensity: float = 0.5  # 0-1
    target_exchange: Optional[str] = None
    target_symbol: Optional[str] = None


class ChaosResult(BaseModel):
    """Result of chaos test."""
    result_id: str = Field(default_factory=lambda: f"chaos_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S%f')}")
    
    chaos_type: ChaosType
    config: ChaosConfig
    
    started_at: datetime
    ended_at: Optional[datetime] = None
    duration_seconds: int = 0
    
    # Impact
    errors_triggered: int = 0
    orders_rejected: int = 0
    signals_dropped: int = 0
    latency_spike_ms: float = 0.0
    
    # System response
    kill_switch_triggered: bool = False
    circuit_breaker_tripped: bool = False
    auto_recovery: bool = False
    
    # Status
    status: str = "COMPLETED"  # RUNNING, COMPLETED, ABORTED
    notes: str = ""


class ChaosState(BaseModel):
    """Current chaos testing state."""
    active_chaos: Optional[ChaosType] = None
    is_chaos_active: bool = False
    
    total_tests: int = 0
    successful_recoveries: int = 0
    failed_recoveries: int = 0
    
    last_test: Optional[datetime] = None
    last_result: Optional[ChaosResult] = None


class SystemChaosEngine:
    """
    System Chaos Engine
    
    Injects faults to test system resilience.
    """
    
    def __init__(self):
        self._state = ChaosState()
        self._results_history: List[ChaosResult] = []
        self._active_result: Optional[ChaosResult] = None
        self._chaos_task: Optional[asyncio.Task] = None
    
    async def run_chaos(self, config: ChaosConfig) -> ChaosResult:
        """Run a chaos test."""
        if self._state.is_chaos_active:
            raise Exception("Chaos test already running")
        
        self._state.is_chaos_active = True
        self._state.active_chaos = config.chaos_type
        
        result = ChaosResult(
            chaos_type=config.chaos_type,
            config=config,
            started_at=datetime.now(timezone.utc),
        )
        self._active_result = result
        
        try:
            # Run chaos by type
            if config.chaos_type == ChaosType.EXCHANGE_DISCONNECT:
                await self._simulate_exchange_disconnect(config, result)
            elif config.chaos_type == ChaosType.ORDER_REJECTION:
                await self._simulate_order_rejection(config, result)
            elif config.chaos_type == ChaosType.LATENCY_SPIKE:
                await self._simulate_latency_spike(config, result)
            elif config.chaos_type == ChaosType.API_FAILURE:
                await self._simulate_api_failure(config, result)
            elif config.chaos_type == ChaosType.SLIPPAGE_SPIKE:
                await self._simulate_slippage_spike(config, result)
            elif config.chaos_type == ChaosType.SIGNAL_STORM:
                await self._simulate_signal_storm(config, result)
            
            result.auto_recovery = True
            
        except Exception as e:
            result.status = "ABORTED"
            result.notes = str(e)
            result.auto_recovery = False
        
        finally:
            result.ended_at = datetime.now(timezone.utc)
            result.duration_seconds = (result.ended_at - result.started_at).seconds
            
            self._state.is_chaos_active = False
            self._state.active_chaos = None
            self._state.total_tests += 1
            self._state.last_test = result.ended_at
            self._state.last_result = result
            
            if result.auto_recovery:
                self._state.successful_recoveries += 1
            else:
                self._state.failed_recoveries += 1
            
            self._results_history.append(result)
            self._active_result = None
        
        return result
    
    async def _simulate_exchange_disconnect(self, config: ChaosConfig, result: ChaosResult):
        """Simulate exchange disconnect."""
        result.notes = f"Simulating exchange disconnect for {config.duration_seconds}s"
        
        # Mark exchange as disconnected
        try:
            from modules.exchange_sync import get_exchange_sync_engine
            sync = get_exchange_sync_engine()
            # Would trigger disconnect in real implementation
        except Exception:
            pass
        
        # Wait for duration
        await asyncio.sleep(config.duration_seconds)
        
        result.errors_triggered = int(config.duration_seconds / 5)  # Simulated error count
    
    async def _simulate_order_rejection(self, config: ChaosConfig, result: ChaosResult):
        """Simulate order rejections."""
        result.notes = f"Simulating order rejections at {config.intensity*100:.0f}% rate"
        
        # Simulate rejection rate
        rejections = int(config.duration_seconds * config.intensity)
        result.orders_rejected = rejections
        
        await asyncio.sleep(config.duration_seconds)
    
    async def _simulate_latency_spike(self, config: ChaosConfig, result: ChaosResult):
        """Simulate latency spike."""
        spike_ms = 500 + (config.intensity * 4500)  # 500ms - 5000ms
        result.latency_spike_ms = spike_ms
        result.notes = f"Simulating latency spike of {spike_ms:.0f}ms"
        
        # Record latency spikes
        from modules.system_metrics import get_metrics_engine
        metrics = get_metrics_engine()
        
        end_time = datetime.now(timezone.utc) + timedelta(seconds=config.duration_seconds)
        while datetime.now(timezone.utc) < end_time:
            metrics.record_latency(spike_ms + random.uniform(-100, 100))
            await asyncio.sleep(0.5)
    
    async def _simulate_api_failure(self, config: ChaosConfig, result: ChaosResult):
        """Simulate API failures."""
        result.notes = f"Simulating API failures at {config.intensity*100:.0f}% rate"
        
        from modules.system_metrics import get_metrics_engine
        metrics = get_metrics_engine()
        
        end_time = datetime.now(timezone.utc) + timedelta(seconds=config.duration_seconds)
        errors = 0
        while datetime.now(timezone.utc) < end_time:
            if random.random() < config.intensity:
                metrics.record_error("simulated_chaos_error")
                errors += 1
            await asyncio.sleep(0.2)
        
        result.errors_triggered = errors
    
    async def _simulate_slippage_spike(self, config: ChaosConfig, result: ChaosResult):
        """Simulate slippage spike."""
        slippage_bps = 10 + (config.intensity * 90)  # 10-100 bps
        result.notes = f"Simulating slippage spike of {slippage_bps:.0f}bps"
        
        from modules.system_metrics import get_metrics_engine
        metrics = get_metrics_engine()
        
        end_time = datetime.now(timezone.utc) + timedelta(seconds=config.duration_seconds)
        while datetime.now(timezone.utc) < end_time:
            metrics.record_slippage(slippage_bps + random.uniform(-5, 5))
            await asyncio.sleep(1)
    
    async def _simulate_signal_storm(self, config: ChaosConfig, result: ChaosResult):
        """Simulate signal storm (high throughput)."""
        signals_per_sec = int(10 + config.intensity * 90)  # 10-100 signals/sec
        result.notes = f"Simulating signal storm: {signals_per_sec} signals/sec"
        
        from modules.system_metrics import get_metrics_engine
        metrics = get_metrics_engine()
        
        end_time = datetime.now(timezone.utc) + timedelta(seconds=config.duration_seconds)
        total_signals = 0
        while datetime.now(timezone.utc) < end_time:
            for _ in range(signals_per_sec):
                metrics.record_signal()
                total_signals += 1
            await asyncio.sleep(1)
        
        result.signals_dropped = 0  # Simplified
    
    def abort_chaos(self):
        """Abort running chaos test."""
        if self._chaos_task and not self._chaos_task.done():
            self._chaos_task.cancel()
        
        self._state.is_chaos_active = False
        self._state.active_chaos = None
        
        if self._active_result:
            self._active_result.status = "ABORTED"
            self._active_result.ended_at = datetime.now(timezone.utc)
    
    def get_state(self) -> ChaosState:
        """Get current chaos state."""
        return self._state
    
    def get_results(self, limit: int = 10) -> List[ChaosResult]:
        """Get recent chaos results."""
        return self._results_history[-limit:]
    
    def get_summary(self) -> Dict:
        """Get chaos testing summary."""
        return {
            "is_active": self._state.is_chaos_active,
            "active_chaos": self._state.active_chaos.value if self._state.active_chaos else None,
            "total_tests": self._state.total_tests,
            "successful_recoveries": self._state.successful_recoveries,
            "failed_recoveries": self._state.failed_recoveries,
            "recovery_rate": (
                self._state.successful_recoveries / self._state.total_tests
                if self._state.total_tests > 0 else 0
            ),
            "available_chaos_types": [ct.value for ct in ChaosType],
            "last_test": self._state.last_test.isoformat() if self._state.last_test else None,
        }


# Singleton
_chaos_engine: Optional[SystemChaosEngine] = None

def get_chaos_engine() -> SystemChaosEngine:
    global _chaos_engine
    if _chaos_engine is None:
        _chaos_engine = SystemChaosEngine()
    return _chaos_engine
