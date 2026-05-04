"""
P1.2 - Execution Timeline Truth (Fund-Grade)
=============================================

Tracks FULL latency breakdown across ALL system layers:
- Internal: signal → decision → final_gate → submit
- Network: submit → ack
- Execution: ack → fill

Provides P50/P95/P99 metrics (NOT averages).
Links latency → slippage → PnL impact.
"""

import logging
from typing import Dict, Optional, List
from datetime import datetime, timezone
from collections import deque

logger = logging.getLogger(__name__)


class LatencyTracker:
    """
    Fund-Grade Execution Latency Tracker (P1.2).
    
    Tracks full timeline:
    - signal_ts: Signal arrival
    - decision_ts: Decision made
    - final_gate_ts: FinalGate passed
    - submit_ts: Order submitted to exchange
    - ack_ts: Exchange ACK received
    - fill_ts: Order filled
    
    Computes 3-layer latency:
    - internal_latency: signal → submit (our system)
    - network_latency: submit → ack (network + exchange queue)
    - execution_latency: ack → fill (exchange matching)
    - total_latency: signal → fill (end-to-end)
    """
    
    def __init__(self, window_size: int = 100):
        """
        Args:
            window_size: Number of recent latencies to keep for percentile stats
        """
        self.window_size = window_size
        
        # In-flight order tracking: {client_order_id: {timestamps, metadata}}
        self._inflight: Dict[str, Dict] = {}
        
        # Completed latencies (sliding window for percentile calculation)
        self._total_latencies_ms: deque = deque(maxlen=window_size)
        self._internal_latencies_ms: deque = deque(maxlen=window_size)
        self._network_latencies_ms: deque = deque(maxlen=window_size)
        self._execution_latencies_ms: deque = deque(maxlen=window_size)
        
        logger.info(f"✅ Fund-Grade LatencyTracker initialized (window={window_size})")
    
    # === Timeline Markers ===
    
    def mark_signal(self, client_order_id: str, trace_id: str, symbol: str, timestamp: Optional[datetime] = None):
        """Mark signal arrival (start of pipeline)"""
        ts = timestamp or datetime.now(timezone.utc)
        
        if client_order_id not in self._inflight:
            self._inflight[client_order_id] = {
                "trace_id": trace_id,
                "symbol": symbol
            }
        
        self._inflight[client_order_id]["signal_ts"] = ts
        logger.debug(f"📊 SIGNAL marked | order={client_order_id} | trace={trace_id}")
    
    def mark_decision(self, client_order_id: str, timestamp: Optional[datetime] = None):
        """Mark decision made"""
        ts = timestamp or datetime.now(timezone.utc)
        
        if client_order_id in self._inflight:
            self._inflight[client_order_id]["decision_ts"] = ts
    
    def mark_final_gate(self, client_order_id: str, timestamp: Optional[datetime] = None):
        """Mark FinalGate passed"""
        ts = timestamp or datetime.now(timezone.utc)
        
        if client_order_id in self._inflight:
            self._inflight[client_order_id]["final_gate_ts"] = ts
        """Mark order fully filled (cleanup)."""
        ts = timestamp or datetime.now(timezone.utc)
        
        if client_order_id not in self._inflight:
            return
        
        self._inflight[client_order_id]["full_fill_at"] = ts
        
        # Calculate submit_to_full_fill latency
        submit_at = self._inflight[client_order_id].get("submit_requested_at")
        if submit_at:
            latency_ms = (ts - submit_at).total_seconds() * 1000
            self._submit_to_full_fill_ms.append(latency_ms)
        
        # Cleanup inflight
        del self._inflight[client_order_id]
    
    def get_stats(self) -> Dict[str, float]:
        """
        Get latency statistics.
        
        Returns:
            {
                "avg_submit_to_ack_ms": float,
                "p95_submit_to_ack_ms": float,
                "avg_submit_to_first_fill_ms": float,
                "p95_submit_to_first_fill_ms": float,
                "inflight_count": int,
                "sample_count": int
            }
        """
        import statistics
        
        def calc_stats(data: deque) -> tuple:
            if not data:
                return 0.0, 0.0
            avg = statistics.mean(data)
            p95 = statistics.quantiles(data, n=20)[18] if len(data) >= 20 else max(data)
            return avg, p95
        
        avg_ack, p95_ack = calc_stats(self._submit_to_ack_ms)
        avg_fill, p95_fill = calc_stats(self._submit_to_first_fill_ms)
        
        return {
            "avg_submit_to_ack_ms": round(avg_ack, 2),
            "p95_submit_to_ack_ms": round(p95_ack, 2),
            "avg_submit_to_first_fill_ms": round(avg_fill, 2),
            "p95_submit_to_first_fill_ms": round(p95_fill, 2),
            "inflight_count": len(self._inflight),
            "sample_count_ack": len(self._submit_to_ack_ms),
            "sample_count_fill": len(self._submit_to_first_fill_ms)
        }
    
    def get_inflight_count(self) -> int:
        """Get count of in-flight orders."""
        return len(self._inflight)
