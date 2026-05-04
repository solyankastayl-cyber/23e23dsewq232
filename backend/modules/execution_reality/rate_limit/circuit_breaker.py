"""
Circuit Breaker v2 (P1-B)
==========================

Adaptive circuit breaker для execution protection.

States:
- CLOSED: Normal operation
- OPEN: Blocking all requests (degradation detected)
- HALF_OPEN: Testing recovery (allow limited traffic)

Triggers:
- High latency (p95 > threshold)
- High reject rate (> threshold)
- High timeout rate (> threshold)

Recovery:
- Gradual: slowly increase traffic after OPEN → HALF_OPEN
- Auto-reset after success_threshold consecutive successes
"""

import logging
from enum import Enum
from typing import Optional, Dict, Any
from datetime import datetime, timezone
from collections import deque

logger = logging.getLogger(__name__)


class CircuitState(str, Enum):
    """Circuit breaker states."""
    CLOSED = "CLOSED"          # Normal operation
    OPEN = "OPEN"              # Blocking requests
    HALF_OPEN = "HALF_OPEN"    # Testing recovery


class CircuitBreaker:
    """
    Circuit breaker with adaptive thresholds.
    
    Monitors execution health metrics and opens circuit when degradation detected.
    Supports gradual recovery via HALF_OPEN state.
    
    Args:
        name: Circuit breaker identifier
        latency_threshold_ms: Open if p95 latency exceeds (default: 2000ms)
        reject_rate_threshold: Open if reject rate exceeds (default: 0.15 = 15%)
        timeout_rate_threshold: Open if timeout rate exceeds (default: 0.1 = 10%)
        min_samples: Minimum samples before evaluation (default: 10)
        failure_threshold: Consecutive failures to open (default: 3)
        success_threshold: Consecutive successes to close (default: 5)
        half_open_max_calls: Max calls in HALF_OPEN state (default: 3)
    """
    
    def __init__(
        self,
        name: str = "execution",
        latency_threshold_ms: float = 2000.0,
        reject_rate_threshold: float = 0.15,
        timeout_rate_threshold: float = 0.1,
        min_samples: int = 10,
        failure_threshold: int = 3,
        success_threshold: int = 5,
        half_open_max_calls: int = 3,
        cooldown_seconds: float = 30.0  # P1.5: Auto-recovery cooldown
    ):
        self.name = name
        self.state = CircuitState.CLOSED
        
        # Thresholds
        self.latency_threshold_ms = latency_threshold_ms
        self.reject_rate_threshold = reject_rate_threshold
        self.timeout_rate_threshold = timeout_rate_threshold
        self.min_samples = min_samples
        
        # State transition counters
        self.failure_threshold = failure_threshold
        self.success_threshold = success_threshold
        self.half_open_max_calls = half_open_max_calls
        
        # P1.5: Auto-recovery
        self.cooldown_seconds = cooldown_seconds
        
        # Tracking
        self.consecutive_failures = 0
        self.consecutive_successes = 0
        self.half_open_calls = 0
        self.last_state_change = datetime.now(timezone.utc)
        
        # Trip history (for monitoring)
        self.trip_history: deque = deque(maxlen=10)
        
        logger.info(
            f"✅ CircuitBreaker '{name}' initialized: "
            f"latency_threshold={latency_threshold_ms}ms, "
            f"reject_rate={reject_rate_threshold*100}%, "
            f"timeout_rate={timeout_rate_threshold*100}%, "
            f"cooldown={cooldown_seconds}s"
        )
    
    def evaluate(self, metrics: Dict[str, Any]) -> CircuitState:
        """
        Evaluate execution health and update circuit state.
        
        Args:
            metrics: Execution health metrics from ExecutionMetricsStore
                {
                    "latency_p95_ms": float,
                    "reject_rate": float,
                    "timeout_rate": float,
                    "sample_count": int
                }
        
        Returns:
            Current circuit state after evaluation
        """
        # Extract metrics
        latency_p95 = metrics.get("latency_p95_ms", 0.0)
        reject_rate = metrics.get("reject_rate", 0.0)
        timeout_rate = metrics.get("timeout_rate", 0.0)
        sample_count = metrics.get("sample_count", 0)
        
        # Skip if insufficient samples
        if sample_count < self.min_samples:
            logger.debug(
                f"CircuitBreaker '{self.name}': Insufficient samples "
                f"({sample_count}/{self.min_samples})"
            )
            return self.state
        
        # Check degradation
        is_degraded = (
            latency_p95 > self.latency_threshold_ms or
            reject_rate > self.reject_rate_threshold or
            timeout_rate > self.timeout_rate_threshold
        )
        
        # State machine
        if self.state == CircuitState.CLOSED:
            if is_degraded:
                self.consecutive_failures += 1
                logger.warning(
                    f"⚠️ CircuitBreaker '{self.name}': Degradation detected "
                    f"(failures={self.consecutive_failures}/{self.failure_threshold})"
                )
                
                if self.consecutive_failures >= self.failure_threshold:
                    self._trip(
                        reason=self._get_trip_reason(latency_p95, reject_rate, timeout_rate),
                        metrics=metrics
                    )
            else:
                # Reset failure counter on healthy state
                self.consecutive_failures = 0
        
        elif self.state == CircuitState.OPEN:
            # P1.5: Auto-transition to HALF_OPEN after cooldown
            time_since_trip = (datetime.now(timezone.utc) - self.last_state_change).total_seconds()
            
            if time_since_trip >= self.cooldown_seconds:
                logger.info(
                    f"🔄 CircuitBreaker '{self.name}': Cooldown passed ({time_since_trip:.1f}s), "
                    f"attempting recovery (OPEN → HALF_OPEN)"
                )
                self.attempt_reset()
            else:
                # Still in cooldown
                remaining = self.cooldown_seconds - time_since_trip
                logger.debug(
                    f"CircuitBreaker '{self.name}': In cooldown, "
                    f"recovery in {remaining:.1f}s"
                )
        
        elif self.state == CircuitState.HALF_OPEN:
            self.half_open_calls += 1
            
            if is_degraded:
                # Still degraded → reopen circuit
                logger.error(
                    f"🔥 CircuitBreaker '{self.name}': Recovery failed, reopening"
                )
                self._trip(
                    reason="recovery_failed",
                    metrics=metrics
                )
            else:
                self.consecutive_successes += 1
                
                if self.consecutive_successes >= self.success_threshold:
                    self._reset()
                elif self.half_open_calls >= self.half_open_max_calls:
                    # Max test calls reached → assess
                    if self.consecutive_successes >= self.success_threshold // 2:
                        self._reset()
                    else:
                        self._trip(reason="insufficient_recovery", metrics=metrics)
        
        return self.state
    
    def _trip(self, reason: str, metrics: Dict[str, Any]) -> None:
        """Open circuit (block requests)."""
        self.state = CircuitState.OPEN
        self.consecutive_failures = 0
        self.consecutive_successes = 0
        self.last_state_change = datetime.now(timezone.utc)
        
        # Record trip event
        trip_event = {
            "timestamp": self.last_state_change.isoformat(),
            "reason": reason,
            "metrics": metrics
        }
        self.trip_history.append(trip_event)
        
        logger.critical(
            f"🔥 CircuitBreaker '{self.name}' TRIPPED: {reason} | "
            f"latency={metrics.get('latency_p95_ms')}ms, "
            f"reject_rate={metrics.get('reject_rate')*100:.1f}%, "
            f"timeout_rate={metrics.get('timeout_rate')*100:.1f}%"
        )
    
    def _reset(self) -> None:
        """Close circuit (resume normal operation)."""
        self.state = CircuitState.CLOSED
        self.consecutive_failures = 0
        self.consecutive_successes = 0
        self.half_open_calls = 0
        self.last_state_change = datetime.now(timezone.utc)
        
        logger.info(
            f"✅ CircuitBreaker '{self.name}' RESET: Returning to normal operation"
        )
    
    def _get_trip_reason(
        self,
        latency_p95: float,
        reject_rate: float,
        timeout_rate: float
    ) -> str:
        """Determine primary trip reason."""
        reasons = []
        
        if latency_p95 > self.latency_threshold_ms:
            reasons.append(f"high_latency({latency_p95:.0f}ms)")
        if reject_rate > self.reject_rate_threshold:
            reasons.append(f"high_reject_rate({reject_rate*100:.1f}%)")
        if timeout_rate > self.timeout_rate_threshold:
            reasons.append(f"high_timeout_rate({timeout_rate*100:.1f}%)")
        
        return " + ".join(reasons) if reasons else "unknown"
    
    def is_open(self, critical_intent: bool = False) -> bool:
        """
        Check if circuit is open (blocking requests).
        
        Args:
            critical_intent: If True, only block for CRITICAL failures (exchange down).
                           If False, block for all degradation (normal throttling).
        
        Returns:
            True if should block, False if can proceed
        """
        if self.state != CircuitState.OPEN:
            return False
        
        # CRITICAL_ONLY mode: only block if exchange truly unavailable
        if critical_intent:
            # Check last trip reason - only block for catastrophic failures
            if self.trip_history:
                last_trip = self.trip_history[-1]
                reason = last_trip.get("reason", "")
                
                # Only block STOP_LOSS if exchange is truly dead
                is_catastrophic = (
                    "timeout" in reason.lower() or
                    "failed" in reason.lower() or
                    last_trip.get("metrics", {}).get("timeout_rate", 0) > 0.5
                )
                
                if not is_catastrophic:
                    logger.warning(
                        f"⚠️ Circuit OPEN but allowing CRITICAL intent | "
                        f"reason={reason} (not catastrophic)"
                    )
                    return False  # Allow STOP_LOSS through
            
            return False  # Default: allow critical intents
        
        # Normal mode: block all requests
        return True
    
    def is_closed(self) -> bool:
        """Check if circuit is closed (normal operation)."""
        return self.state == CircuitState.CLOSED
    
    def is_half_open(self) -> bool:
        """Check if circuit is half-open (testing recovery)."""
        return self.state == CircuitState.HALF_OPEN
    
    def attempt_reset(self) -> bool:
        """
        Manually attempt to reset circuit (OPEN → HALF_OPEN).
        
        Returns:
            True if transition successful, False otherwise
        """
        if self.state == CircuitState.OPEN:
            self.state = CircuitState.HALF_OPEN
            self.half_open_calls = 0
            self.consecutive_successes = 0
            self.last_state_change = datetime.now(timezone.utc)
            
            logger.info(
                f"🔄 CircuitBreaker '{self.name}': OPEN → HALF_OPEN (testing recovery)"
            )
            return True
        return False
    
    def get_state(self) -> Dict[str, Any]:
        """
        Get current circuit breaker state.
        
        Returns:
            {
                "name": str,
                "state": str (CLOSED/OPEN/HALF_OPEN),
                "consecutive_failures": int,
                "consecutive_successes": int,
                "last_state_change": str (ISO timestamp),
                "trip_history": List[dict]
            }
        """
        return {
            "name": self.name,
            "state": self.state.value,
            "consecutive_failures": self.consecutive_failures,
            "consecutive_successes": self.consecutive_successes,
            "last_state_change": self.last_state_change.isoformat(),
            "trip_history": list(self.trip_history)
        }
