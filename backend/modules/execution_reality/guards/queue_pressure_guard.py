"""
Queue Pressure Guard (P1 - Flow Control)
=========================================

Adaptive pressure-based throttling для execution queue.

Prevents system degradation under load:
- Inflight order accumulation
- Queue depth overflow
- Latency spikes
- Execution quality degradation

Pressure Score = weighted composite of:
- inflight_orders (40%)
- queue_depth (30%)
- avg_latency_ms (30%)

Thresholds:
- pressure > 0.9: BLOCK_NEW_ORDERS (hard stop)
- pressure > 0.8: HARD_THROTTLE (10% size)
- pressure > 0.6: REDUCE_SIZE (50% size)
- pressure < 0.6: NORMAL (100% size)
"""

import logging
from typing import Dict, Any
from enum import Enum

logger = logging.getLogger(__name__)


class PressureLevel(str, Enum):
    """Queue pressure levels."""
    NORMAL = "NORMAL"            # < 0.6: No throttling
    MODERATE = "MODERATE"        # 0.6-0.8: Reduce size
    HIGH = "HIGH"                # 0.8-0.9: Hard throttle
    CRITICAL = "CRITICAL"        # > 0.9: Block new orders


class QueuePressureGuard:
    """
    Adaptive pressure-based flow control.
    
    Monitors execution queue health and throttles incoming orders
    to maintain execution quality under load.
    
    Args:
        max_inflight: Maximum inflight orders (default: 20)
        max_queue_depth: Maximum queue depth (default: 50)
        max_latency_ms: Maximum acceptable latency (default: 2000ms)
        inflight_weight: Weight for inflight metric (default: 0.4)
        queue_weight: Weight for queue depth metric (default: 0.3)
        latency_weight: Weight for latency metric (default: 0.3)
    """
    
    def __init__(
        self,
        max_inflight: int = 20,
        max_queue_depth: int = 50,
        max_latency_ms: float = 2000.0,
        inflight_weight: float = 0.4,
        queue_weight: float = 0.3,
        latency_weight: float = 0.3
    ):
        if abs(inflight_weight + queue_weight + latency_weight - 1.0) > 0.01:
            raise ValueError("Weights must sum to 1.0")
        
        self.max_inflight = max_inflight
        self.max_queue_depth = max_queue_depth
        self.max_latency_ms = max_latency_ms
        
        self.inflight_weight = inflight_weight
        self.queue_weight = queue_weight
        self.latency_weight = latency_weight
        
        # Thresholds
        self.threshold_moderate = 0.6
        self.threshold_high = 0.8
        self.threshold_critical = 0.9
        
        logger.info(
            f"✅ QueuePressureGuard initialized: "
            f"max_inflight={max_inflight}, max_queue={max_queue_depth}, "
            f"max_latency={max_latency_ms}ms"
        )
    
    def calculate_pressure(
        self,
        inflight_orders: int,
        queue_depth: int,
        avg_latency_ms: float
    ) -> float:
        """
        Calculate composite pressure score (0.0 - 1.0+).
        
        Args:
            inflight_orders: Number of active orders (not terminal)
            queue_depth: Current queue depth
            avg_latency_ms: Average submit-to-ack latency
        
        Returns:
            Pressure score (0.0 = no pressure, 1.0 = critical)
        """
        # Normalize each metric to 0-1 scale
        inflight_norm = min(inflight_orders / self.max_inflight, 1.0)
        queue_norm = min(queue_depth / self.max_queue_depth, 1.0)
        latency_norm = min((avg_latency_ms or 0.0) / self.max_latency_ms, 1.0)  # Handle None
        
        # Weighted composite
        pressure = (
            inflight_norm * self.inflight_weight +
            queue_norm * self.queue_weight +
            latency_norm * self.latency_weight
        )
        
        return round(pressure, 3)
    
    def get_pressure_level(self, pressure: float) -> PressureLevel:
        """Determine pressure level from score."""
        if pressure >= self.threshold_critical:
            return PressureLevel.CRITICAL
        elif pressure >= self.threshold_high:
            return PressureLevel.HIGH
        elif pressure >= self.threshold_moderate:
            return PressureLevel.MODERATE
        else:
            return PressureLevel.NORMAL
    
    def get_size_multiplier(self, pressure: float) -> float:
        """
        Get position size multiplier based on pressure.
        
        Args:
            pressure: Pressure score
        
        Returns:
            Size multiplier (0.0 - 1.0)
                1.0 = normal
                0.5 = reduce
                0.1 = hard throttle
                0.0 = block
        """
        level = self.get_pressure_level(pressure)
        
        if level == PressureLevel.CRITICAL:
            return 0.0  # Block new orders
        elif level == PressureLevel.HIGH:
            return 0.1  # Hard throttle (10%)
        elif level == PressureLevel.MODERATE:
            return 0.5  # Reduce size (50%)
        else:
            return 1.0  # Normal (100%)
    
    def should_block(self, pressure: float) -> bool:
        """Check if new orders should be blocked."""
        return pressure >= self.threshold_critical
    
    def evaluate(
        self,
        inflight_orders: int,
        queue_depth: int,
        avg_latency_ms: float
    ) -> Dict[str, Any]:
        """
        Evaluate queue pressure and return recommendations.
        
        Args:
            inflight_orders: Number of active orders
            queue_depth: Current queue depth
            avg_latency_ms: Average latency
        
        Returns:
            {
                "pressure": float,
                "level": str (NORMAL/MODERATE/HIGH/CRITICAL),
                "size_multiplier": float,
                "should_block": bool,
                "reason": str
            }
        """
        pressure = self.calculate_pressure(inflight_orders, queue_depth, avg_latency_ms)
        level = self.get_pressure_level(pressure)
        size_multiplier = self.get_size_multiplier(pressure)
        should_block = self.should_block(pressure)
        
        # Determine primary reason
        reasons = []
        if inflight_orders > self.max_inflight * 0.8:
            reasons.append(f"high_inflight({inflight_orders})")
        if queue_depth > self.max_queue_depth * 0.8:
            reasons.append(f"high_queue({queue_depth})")
        if avg_latency_ms and avg_latency_ms > self.max_latency_ms * 0.8:  # Handle None
            reasons.append(f"high_latency({avg_latency_ms:.0f}ms)")
        
        reason = " + ".join(reasons) if reasons else "healthy"
        
        # Log significant pressure changes
        if level in {PressureLevel.HIGH, PressureLevel.CRITICAL}:
            logger.warning(
                f"⚠️ Queue pressure {level.value}: "
                f"score={pressure:.2f}, size_mult={size_multiplier}, "
                f"reason={reason}"
            )
        
        return {
            "pressure": pressure,
            "level": level.value,
            "size_multiplier": size_multiplier,
            "should_block": should_block,
            "reason": reason,
            "metrics": {
                "inflight_orders": inflight_orders,
                "queue_depth": queue_depth,
                "avg_latency_ms": round(avg_latency_ms, 2) if avg_latency_ms is not None else 0.0
            }
        }
