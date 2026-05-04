"""
Execution Metrics Store (P1-A)
===============================

Aggregates execution metrics:
- Latencies (avg, p95)
- Reject rate
- Timeout rate
- Queue depth
- Inflight count

Used for health monitoring and circuit breakers.
"""

import logging
from typing import Dict
from datetime import datetime, timezone
from collections import deque

logger = logging.getLogger(__name__)


class ExecutionMetricsStore:
    """
    Execution metrics aggregator (P1-A).
    
    Tracks:
    - Submit/ACK/Fill latencies
    - Reject rate
    - Timeout rate
    - Queue depth snapshots
    - Inflight count
    """
    
    def __init__(self, window_size: int = 100):
        self.window_size = window_size
        
        # Counters (rolling window)
        self._total_submits = 0
        self._total_acks = 0
        self._total_rejects = 0
        self._total_timeouts = 0
        self._total_fills = 0
        
        # Queue depth snapshots
        self._queue_depth_samples: deque = deque(maxlen=window_size)
        self._inflight_count_samples: deque = deque(maxlen=window_size)
        
        logger.info(f"✅ ExecutionMetricsStore initialized (window={window_size})")
    
    def record_submit(self):
        """Record order submit."""
        self._total_submits += 1
    
    def record_ack(self):
        """Record order ACK."""
        self._total_acks += 1
    
    def record_reject(self):
        """Record order reject."""
        self._total_rejects += 1
    
    def record_timeout(self):
        """Record order timeout."""
        self._total_timeouts += 1
    
    def record_fill(self):
        """Record order fill."""
        self._total_fills += 1
    
    def snapshot_queue_depth(self, depth: int):
        """Snapshot current queue depth."""
        self._queue_depth_samples.append(depth)
    
    def snapshot_inflight_count(self, count: int):
        """Snapshot current inflight count."""
        self._inflight_count_samples.append(count)
    
    def get_metrics(self) -> Dict:
        """
        Get aggregated metrics.
        
        Returns:
            {
                "total_submits": int,
                "total_acks": int,
                "total_rejects": int,
                "total_timeouts": int,
                "reject_rate": float,  # 0.0 - 1.0
                "timeout_rate": float,  # 0.0 - 1.0
                "avg_queue_depth": float,
                "avg_inflight_count": float
            }
        """
        reject_rate = self._total_rejects / max(self._total_submits, 1)
        timeout_rate = self._total_timeouts / max(self._total_submits, 1)
        
        avg_queue_depth = (
            sum(self._queue_depth_samples) / len(self._queue_depth_samples)
            if self._queue_depth_samples else 0.0
        )
        
        avg_inflight = (
            sum(self._inflight_count_samples) / len(self._inflight_count_samples)
            if self._inflight_count_samples else 0.0
        )
        
        return {
            "total_submits": self._total_submits,
            "total_acks": self._total_acks,
            "total_rejects": self._total_rejects,
            "total_timeouts": self._total_timeouts,
            "total_fills": self._total_fills,
            "reject_rate": round(reject_rate, 4),
            "timeout_rate": round(timeout_rate, 4),
            "avg_queue_depth": round(avg_queue_depth, 2),
            "avg_inflight_count": round(avg_inflight, 2)
        }
    
    def get_health_status(self) -> str:
        """
        Determine health status based on metrics.
        
        Returns:
            "HEALTHY" | "WARNING" | "CRITICAL"
        """
        metrics = self.get_metrics()
        
        # CRITICAL conditions
        if metrics["reject_rate"] > 0.3:  # 30% reject rate
            return "CRITICAL"
        if metrics["timeout_rate"] > 0.2:  # 20% timeout rate
            return "CRITICAL"
        if metrics["avg_queue_depth"] > 100:  # Queue too deep
            return "CRITICAL"
        
        # WARNING conditions
        if metrics["reject_rate"] > 0.1:  # 10% reject rate
            return "WARNING"
        if metrics["timeout_rate"] > 0.05:  # 5% timeout rate
            return "WARNING"
        if metrics["avg_queue_depth"] > 50:  # Queue growing
            return "WARNING"
        
        return "HEALTHY"
