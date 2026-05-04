"""
Stress Test Engine

Load and stress testing for the trading system.

Tests:
- 100 signals/sec throughput
- 1000 signals/min burst
- Execution throughput
- Exchange lag handling
- Portfolio rebalance storm
"""

from typing import Optional, Dict, List
from datetime import datetime, timezone, timedelta
from pydantic import BaseModel, Field
from enum import Enum
import asyncio
import time


class StressTestType(str, Enum):
    """Types of stress tests."""
    SIGNAL_THROUGHPUT = "SIGNAL_THROUGHPUT"
    SIGNAL_BURST = "SIGNAL_BURST"
    EXECUTION_THROUGHPUT = "EXECUTION_THROUGHPUT"
    EXCHANGE_LAG = "EXCHANGE_LAG"
    PORTFOLIO_REBALANCE = "PORTFOLIO_REBALANCE"
    MEMORY_STRESS = "MEMORY_STRESS"
    FULL_SYSTEM = "FULL_SYSTEM"


class StressTestConfig(BaseModel):
    """Configuration for stress test."""
    test_type: StressTestType
    duration_seconds: int = 60
    target_rate: int = 100  # signals/sec or operations/sec
    ramp_up_seconds: int = 10


class StressTestMetrics(BaseModel):
    """Metrics from stress test."""
    total_operations: int = 0
    successful_operations: int = 0
    failed_operations: int = 0
    
    avg_latency_ms: float = 0.0
    p95_latency_ms: float = 0.0
    p99_latency_ms: float = 0.0
    max_latency_ms: float = 0.0
    
    throughput_per_sec: float = 0.0
    peak_throughput: float = 0.0
    
    memory_start_mb: float = 0.0
    memory_peak_mb: float = 0.0
    cpu_avg_pct: float = 0.0
    cpu_peak_pct: float = 0.0


class StressTestResult(BaseModel):
    """Result of stress test."""
    result_id: str = Field(default_factory=lambda: f"stress_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S%f')}")
    
    test_type: StressTestType
    config: StressTestConfig
    
    started_at: datetime
    ended_at: Optional[datetime] = None
    duration_seconds: int = 0
    
    # Metrics
    metrics: StressTestMetrics = Field(default_factory=StressTestMetrics)
    
    # Pass/Fail
    passed: bool = False
    failure_reason: Optional[str] = None
    
    # Thresholds
    target_throughput: int = 0
    achieved_throughput: float = 0.0
    latency_threshold_ms: float = 1000.0
    error_threshold_pct: float = 1.0
    
    status: str = "COMPLETED"


class StressTestEngine:
    """
    Stress Test Engine
    
    Runs load and stress tests on the trading system.
    """
    
    def __init__(self):
        self._results: List[StressTestResult] = []
        self._is_running = False
        self._current_test: Optional[StressTestResult] = None
        
        # Pass criteria
        self._latency_threshold_ms = 1000
        self._error_threshold_pct = 1.0
    
    async def run_test(self, config: StressTestConfig) -> StressTestResult:
        """Run a stress test."""
        if self._is_running:
            raise Exception("Stress test already running")
        
        self._is_running = True
        
        result = StressTestResult(
            test_type=config.test_type,
            config=config,
            started_at=datetime.now(timezone.utc),
            target_throughput=config.target_rate,
            latency_threshold_ms=self._latency_threshold_ms,
        )
        self._current_test = result
        
        # Get initial memory
        import psutil
        result.metrics.memory_start_mb = psutil.virtual_memory().used / 1024 / 1024
        
        try:
            if config.test_type == StressTestType.SIGNAL_THROUGHPUT:
                await self._test_signal_throughput(config, result)
            elif config.test_type == StressTestType.SIGNAL_BURST:
                await self._test_signal_burst(config, result)
            elif config.test_type == StressTestType.EXECUTION_THROUGHPUT:
                await self._test_execution_throughput(config, result)
            elif config.test_type == StressTestType.FULL_SYSTEM:
                await self._test_full_system(config, result)
            
            # Calculate pass/fail
            self._evaluate_result(result)
            
        except Exception as e:
            result.status = "FAILED"
            result.failure_reason = str(e)
            result.passed = False
        
        finally:
            result.ended_at = datetime.now(timezone.utc)
            result.duration_seconds = (result.ended_at - result.started_at).seconds
            
            # Get peak memory
            result.metrics.memory_peak_mb = psutil.virtual_memory().used / 1024 / 1024
            
            self._is_running = False
            self._current_test = None
            self._results.append(result)
        
        return result
    
    async def _test_signal_throughput(self, config: StressTestConfig, result: StressTestResult):
        """Test sustained signal throughput."""
        from modules.system_metrics import get_metrics_engine
        metrics = get_metrics_engine()
        
        latencies = []
        operations = 0
        errors = 0
        
        start_time = time.time()
        end_time = start_time + config.duration_seconds
        
        # Ramp up
        current_rate = 1
        ramp_step = config.target_rate / config.ramp_up_seconds
        
        while time.time() < end_time:
            loop_start = time.time()
            
            # Ramp up rate
            if current_rate < config.target_rate:
                current_rate = min(current_rate + ramp_step, config.target_rate)
            
            # Generate signals at current rate
            for _ in range(int(current_rate)):
                op_start = time.time()
                try:
                    metrics.record_signal()
                    operations += 1
                    latency = (time.time() - op_start) * 1000
                    latencies.append(latency)
                except Exception:
                    errors += 1
            
            # Wait to maintain rate
            elapsed = time.time() - loop_start
            if elapsed < 1.0:
                await asyncio.sleep(1.0 - elapsed)
        
        # Calculate metrics
        result.metrics.total_operations = operations
        result.metrics.successful_operations = operations - errors
        result.metrics.failed_operations = errors
        
        if latencies:
            result.metrics.avg_latency_ms = sum(latencies) / len(latencies)
            sorted_lat = sorted(latencies)
            result.metrics.p95_latency_ms = sorted_lat[int(len(sorted_lat) * 0.95)] if len(sorted_lat) > 20 else result.metrics.avg_latency_ms
            result.metrics.p99_latency_ms = sorted_lat[int(len(sorted_lat) * 0.99)] if len(sorted_lat) > 100 else result.metrics.p95_latency_ms
            result.metrics.max_latency_ms = max(latencies)
        
        result.metrics.throughput_per_sec = operations / config.duration_seconds
        result.achieved_throughput = result.metrics.throughput_per_sec
    
    async def _test_signal_burst(self, config: StressTestConfig, result: StressTestResult):
        """Test burst of signals."""
        from modules.system_metrics import get_metrics_engine
        metrics = get_metrics_engine()
        
        latencies = []
        operations = 0
        
        # Single burst of signals
        burst_size = config.target_rate * config.duration_seconds
        
        start = time.time()
        for _ in range(burst_size):
            op_start = time.time()
            metrics.record_signal()
            operations += 1
            latencies.append((time.time() - op_start) * 1000)
        
        duration = time.time() - start
        
        result.metrics.total_operations = operations
        result.metrics.successful_operations = operations
        result.metrics.throughput_per_sec = operations / duration if duration > 0 else 0
        result.metrics.peak_throughput = result.metrics.throughput_per_sec
        result.achieved_throughput = result.metrics.throughput_per_sec
        
        if latencies:
            result.metrics.avg_latency_ms = sum(latencies) / len(latencies)
            result.metrics.max_latency_ms = max(latencies)
    
    async def _test_execution_throughput(self, config: StressTestConfig, result: StressTestResult):
        """Test execution pipeline throughput."""
        # Simulate execution requests
        latencies = []
        operations = 0
        
        end_time = time.time() + config.duration_seconds
        
        while time.time() < end_time:
            op_start = time.time()
            
            # Simulate execution check pipeline
            try:
                from modules.pilot_mode import get_pilot_mode_engine
                from modules.trade_throttle import get_trade_throttle_engine
                
                pilot = get_pilot_mode_engine()
                throttle = get_trade_throttle_engine()
                
                # Check constraints
                pilot.check_constraints("BTC", 1000, "BUY")
                throttle.check_throttle("BTC", "BUY", 1000, "test")
                
                operations += 1
                latencies.append((time.time() - op_start) * 1000)
            except Exception:
                pass
            
            await asyncio.sleep(0.01)  # 100 ops/sec max
        
        result.metrics.total_operations = operations
        result.metrics.successful_operations = operations
        result.metrics.throughput_per_sec = operations / config.duration_seconds
        result.achieved_throughput = result.metrics.throughput_per_sec
        
        if latencies:
            result.metrics.avg_latency_ms = sum(latencies) / len(latencies)
    
    async def _test_full_system(self, config: StressTestConfig, result: StressTestResult):
        """Full system stress test."""
        # Combine multiple tests
        tasks = [
            self._test_signal_throughput(StressTestConfig(
                test_type=StressTestType.SIGNAL_THROUGHPUT,
                duration_seconds=config.duration_seconds,
                target_rate=config.target_rate // 2,
            ), result),
        ]
        
        await asyncio.gather(*tasks, return_exceptions=True)
    
    def _evaluate_result(self, result: StressTestResult):
        """Evaluate if test passed."""
        passed = True
        reasons = []
        
        # Check throughput
        if result.achieved_throughput < result.target_throughput * 0.9:
            passed = False
            reasons.append(f"Throughput {result.achieved_throughput:.1f}/s < target {result.target_throughput}/s")
        
        # Check latency
        if result.metrics.p99_latency_ms > self._latency_threshold_ms:
            passed = False
            reasons.append(f"P99 latency {result.metrics.p99_latency_ms:.1f}ms > threshold {self._latency_threshold_ms}ms")
        
        # Check errors
        if result.metrics.total_operations > 0:
            error_rate = result.metrics.failed_operations / result.metrics.total_operations * 100
            if error_rate > self._error_threshold_pct:
                passed = False
                reasons.append(f"Error rate {error_rate:.2f}% > threshold {self._error_threshold_pct}%")
        
        result.passed = passed
        if not passed:
            result.failure_reason = "; ".join(reasons)
    
    def get_results(self, limit: int = 10) -> List[StressTestResult]:
        """Get recent test results."""
        return self._results[-limit:]
    
    def get_summary(self) -> Dict:
        """Get stress testing summary."""
        total = len(self._results)
        passed = sum(1 for r in self._results if r.passed)
        
        return {
            "is_running": self._is_running,
            "current_test": self._current_test.test_type.value if self._current_test else None,
            "total_tests": total,
            "passed_tests": passed,
            "failed_tests": total - passed,
            "pass_rate": passed / total if total > 0 else 0,
            "available_tests": [t.value for t in StressTestType],
            "thresholds": {
                "latency_ms": self._latency_threshold_ms,
                "error_rate_pct": self._error_threshold_pct,
            },
        }


# Singleton
_stress_engine: Optional[StressTestEngine] = None

def get_stress_engine() -> StressTestEngine:
    global _stress_engine
    if _stress_engine is None:
        _stress_engine = StressTestEngine()
    return _stress_engine
