"""
System Metrics & Telemetry Layer

Collects and exposes system metrics for monitoring and stress testing.

Metrics:
- latency
- execution time
- slippage
- PnL drift
- portfolio exposure
- signal throughput
- API failures
- memory usage
- CPU usage
"""

from typing import Optional, Dict, List
from datetime import datetime, timezone, timedelta
from pydantic import BaseModel, Field
from collections import deque
import time
import psutil
import os


class MetricType(str):
    LATENCY = "latency"
    EXECUTION_TIME = "execution_time"
    SLIPPAGE = "slippage"
    SIGNAL_THROUGHPUT = "signal_throughput"
    API_ERRORS = "api_errors"
    MEMORY_USAGE = "memory_usage"
    CPU_USAGE = "cpu_usage"
    QUEUE_DEPTH = "queue_depth"


class MetricSample(BaseModel):
    """Single metric sample."""
    metric_type: str
    value: float
    unit: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    labels: Dict[str, str] = Field(default_factory=dict)


class SystemMetrics(BaseModel):
    """Aggregated system metrics."""
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    # Latency
    avg_latency_ms: float = 0.0
    p95_latency_ms: float = 0.0
    p99_latency_ms: float = 0.0
    
    # Execution
    avg_execution_time_ms: float = 0.0
    avg_slippage_bps: float = 0.0
    
    # Throughput
    signals_per_minute: float = 0.0
    trades_per_hour: float = 0.0
    
    # Errors
    api_error_rate: float = 0.0
    total_errors_1h: int = 0
    
    # Resources
    memory_usage_pct: float = 0.0
    memory_used_mb: float = 0.0
    cpu_usage_pct: float = 0.0
    
    # Queues
    execution_queue_depth: int = 0
    signal_queue_depth: int = 0


class SystemHealth(BaseModel):
    """Overall system health status."""
    status: str = "HEALTHY"  # HEALTHY, DEGRADED, UNHEALTHY
    
    # Component status
    exchange_connectivity: bool = True
    portfolio_state_valid: bool = True
    risk_state_valid: bool = True
    kill_switch_ready: bool = True
    circuit_breakers_ready: bool = True
    
    # Performance
    latency_ok: bool = True
    memory_ok: bool = True
    error_rate_ok: bool = True
    
    # Reconciliation
    positions_synced: bool = True
    balances_synced: bool = True
    
    issues: List[str] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class SystemMetricsEngine:
    """
    System Metrics & Telemetry Engine
    
    Collects and aggregates system metrics.
    """
    
    def __init__(self):
        # Metric buffers (last 1 hour)
        self._latency_samples: deque = deque(maxlen=3600)
        self._execution_samples: deque = deque(maxlen=3600)
        self._slippage_samples: deque = deque(maxlen=1000)
        self._error_samples: deque = deque(maxlen=1000)
        self._signal_samples: deque = deque(maxlen=3600)
        
        # Counters
        self._total_signals: int = 0
        self._total_trades: int = 0
        self._total_errors: int = 0
        
        # Start time
        self._start_time = datetime.now(timezone.utc)
    
    def record_latency(self, latency_ms: float, endpoint: str = "unknown"):
        """Record API latency."""
        self._latency_samples.append(MetricSample(
            metric_type=MetricType.LATENCY,
            value=latency_ms,
            unit="ms",
            labels={"endpoint": endpoint},
        ))
    
    def record_execution_time(self, time_ms: float, order_type: str = "unknown"):
        """Record execution time."""
        self._execution_samples.append(MetricSample(
            metric_type=MetricType.EXECUTION_TIME,
            value=time_ms,
            unit="ms",
            labels={"order_type": order_type},
        ))
    
    def record_slippage(self, slippage_bps: float, symbol: str = "unknown"):
        """Record slippage in basis points."""
        self._slippage_samples.append(MetricSample(
            metric_type=MetricType.SLIPPAGE,
            value=slippage_bps,
            unit="bps",
            labels={"symbol": symbol},
        ))
    
    def record_signal(self):
        """Record a signal processed."""
        self._total_signals += 1
        self._signal_samples.append(MetricSample(
            metric_type=MetricType.SIGNAL_THROUGHPUT,
            value=1,
            unit="count",
        ))
    
    def record_trade(self):
        """Record a trade executed."""
        self._total_trades += 1
    
    def record_error(self, error_type: str = "unknown"):
        """Record an API error."""
        self._total_errors += 1
        self._error_samples.append(MetricSample(
            metric_type=MetricType.API_ERRORS,
            value=1,
            unit="count",
            labels={"error_type": error_type},
        ))
    
    def get_metrics(self) -> SystemMetrics:
        """Get aggregated system metrics."""
        now = datetime.now(timezone.utc)
        
        # Calculate latency percentiles
        latencies = [s.value for s in self._latency_samples]
        avg_latency = sum(latencies) / len(latencies) if latencies else 0
        p95_latency = sorted(latencies)[int(len(latencies) * 0.95)] if len(latencies) > 20 else avg_latency
        p99_latency = sorted(latencies)[int(len(latencies) * 0.99)] if len(latencies) > 100 else p95_latency
        
        # Execution time
        exec_times = [s.value for s in self._execution_samples]
        avg_exec = sum(exec_times) / len(exec_times) if exec_times else 0
        
        # Slippage
        slippages = [s.value for s in self._slippage_samples]
        avg_slippage = sum(slippages) / len(slippages) if slippages else 0
        
        # Throughput
        one_min_ago = now - timedelta(minutes=1)
        signals_1m = sum(1 for s in self._signal_samples if s.timestamp > one_min_ago)
        
        one_hour_ago = now - timedelta(hours=1)
        
        # Error rate
        errors_1h = sum(1 for s in self._error_samples if s.timestamp > one_hour_ago)
        total_requests = len([s for s in self._latency_samples if s.timestamp > one_hour_ago])
        error_rate = errors_1h / total_requests if total_requests > 0 else 0
        
        # System resources
        memory = psutil.virtual_memory()
        cpu = psutil.cpu_percent(interval=0.1)
        
        return SystemMetrics(
            avg_latency_ms=round(avg_latency, 2),
            p95_latency_ms=round(p95_latency, 2),
            p99_latency_ms=round(p99_latency, 2),
            avg_execution_time_ms=round(avg_exec, 2),
            avg_slippage_bps=round(avg_slippage, 2),
            signals_per_minute=signals_1m,
            trades_per_hour=self._total_trades,
            api_error_rate=round(error_rate, 4),
            total_errors_1h=errors_1h,
            memory_usage_pct=round(memory.percent, 1),
            memory_used_mb=round(memory.used / 1024 / 1024, 1),
            cpu_usage_pct=round(cpu, 1),
        )
    
    def get_health(self) -> SystemHealth:
        """Get overall system health."""
        health = SystemHealth()
        metrics = self.get_metrics()
        
        # Check latency
        if metrics.p99_latency_ms > 1000:
            health.latency_ok = False
            health.issues.append(f"High latency: p99={metrics.p99_latency_ms}ms")
        
        # Check memory
        if metrics.memory_usage_pct > 90:
            health.memory_ok = False
            health.issues.append(f"High memory usage: {metrics.memory_usage_pct}%")
        
        # Check error rate
        if metrics.api_error_rate > 0.05:
            health.error_rate_ok = False
            health.issues.append(f"High error rate: {metrics.api_error_rate*100:.1f}%")
        
        # Check safety components
        try:
            from modules.safety_kill_switch import get_kill_switch, KillSwitchState
            ks = get_kill_switch()
            # Kill switch is ready if it's in ACTIVE state (not triggered)
            health.kill_switch_ready = ks.get_status().state == KillSwitchState.ACTIVE
        except Exception:
            health.kill_switch_ready = False
            health.issues.append("Kill switch not accessible")
        
        try:
            from modules.circuit_breaker import get_circuit_breaker
            cb = get_circuit_breaker()
            health.circuit_breakers_ready = not cb.is_any_tripped()
        except Exception:
            pass
        
        # Determine overall status
        if health.issues:
            if len(health.issues) > 2 or not health.kill_switch_ready:
                health.status = "UNHEALTHY"
            else:
                health.status = "DEGRADED"
        
        return health
    
    def get_summary(self) -> Dict:
        """Get metrics summary."""
        metrics = self.get_metrics()
        health = self.get_health()
        
        uptime = datetime.now(timezone.utc) - self._start_time
        
        return {
            "health_status": health.status,
            "uptime_seconds": int(uptime.total_seconds()),
            "metrics": {
                "latency": {
                    "avg_ms": metrics.avg_latency_ms,
                    "p95_ms": metrics.p95_latency_ms,
                    "p99_ms": metrics.p99_latency_ms,
                },
                "execution": {
                    "avg_time_ms": metrics.avg_execution_time_ms,
                    "avg_slippage_bps": metrics.avg_slippage_bps,
                },
                "throughput": {
                    "signals_per_minute": metrics.signals_per_minute,
                    "trades_per_hour": metrics.trades_per_hour,
                },
                "errors": {
                    "rate": metrics.api_error_rate,
                    "count_1h": metrics.total_errors_1h,
                },
                "resources": {
                    "memory_pct": metrics.memory_usage_pct,
                    "memory_mb": metrics.memory_used_mb,
                    "cpu_pct": metrics.cpu_usage_pct,
                },
            },
            "health_checks": {
                "exchange_connectivity": health.exchange_connectivity,
                "kill_switch_ready": health.kill_switch_ready,
                "circuit_breakers_ready": health.circuit_breakers_ready,
                "latency_ok": health.latency_ok,
                "memory_ok": health.memory_ok,
                "error_rate_ok": health.error_rate_ok,
            },
            "issues": health.issues,
        }


# Singleton
_metrics_engine: Optional[SystemMetricsEngine] = None

def get_metrics_engine() -> SystemMetricsEngine:
    global _metrics_engine
    if _metrics_engine is None:
        _metrics_engine = SystemMetricsEngine()
    return _metrics_engine
