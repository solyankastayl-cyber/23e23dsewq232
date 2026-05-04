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
from typing import Dict, Optional
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
        self.window_size = window_size
        self._inflight: Dict[str, Dict] = {}
        
        # Sliding windows for percentile calculation
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
            self._inflight[client_order_id] = {"trace_id": trace_id, "symbol": symbol}
        self._inflight[client_order_id]["signal_ts"] = ts
    
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
    
    def mark_submit_requested(self, client_order_id: str, timestamp: Optional[datetime] = None):
        """Mark order submitted to exchange (alias for compatibility)"""
        self.mark_submit(client_order_id, timestamp)
    
    def mark_submit(self, client_order_id: str, timestamp: Optional[datetime] = None):
        """Mark order submitted to exchange"""
        ts = timestamp or datetime.now(timezone.utc)
        if client_order_id not in self._inflight:
            self._inflight[client_order_id] = {}
        self._inflight[client_order_id]["submit_ts"] = ts
    
    def mark_ack_received(self, client_order_id: str, timestamp: Optional[datetime] = None):
        """Mark exchange ACK received (alias for compatibility)"""
        self.mark_ack(client_order_id, timestamp)
    
    def mark_ack(self, client_order_id: str, timestamp: Optional[datetime] = None):
        """Mark exchange ACK received"""
        ts = timestamp or datetime.now(timezone.utc)
        if client_order_id in self._inflight:
            self._inflight[client_order_id]["ack_ts"] = ts
    
    def mark_first_fill(self, client_order_id: str, timestamp: Optional[datetime] = None):
        """Mark first fill (alias for mark_fill)"""
        self.mark_fill(client_order_id, None, None, timestamp)
    
    def mark_full_fill(self, client_order_id: str, timestamp: Optional[datetime] = None):
        """Mark full fill (alias for mark_fill)"""
        self.mark_fill(client_order_id, None, None, timestamp)
    
    def mark_fill(self, client_order_id: str, slippage_pct: Optional[float] = None, pnl_impact_usdt: Optional[float] = None, timestamp: Optional[datetime] = None):
        """Mark order filled (end of pipeline)"""
        ts = timestamp or datetime.now(timezone.utc)
        if client_order_id not in self._inflight:
            logger.warning(f"Fill for unknown order: {client_order_id}")
            return
        
        data = self._inflight[client_order_id]
        data["fill_ts"] = ts
        data["slippage_pct"] = slippage_pct
        data["pnl_impact_usdt"] = pnl_impact_usdt
        
        self._calculate_and_record(client_order_id)
    
    # === Latency Calculation ===
    
    def _calculate_and_record(self, client_order_id: str):
        """Calculate all latency metrics and record to sliding window"""
        data = self._inflight[client_order_id]
        
        signal_ts = data.get("signal_ts")
        submit_ts = data.get("submit_ts")
        ack_ts = data.get("ack_ts")
        fill_ts = data.get("fill_ts")
        
        internal_ms = None
        network_ms = None
        execution_ms = None
        total_ms = None
        
        # Internal latency (signal → submit)
        if signal_ts and submit_ts:
            internal_ms = (submit_ts - signal_ts).total_seconds() * 1000
            self._internal_latencies_ms.append(internal_ms)
        
        # Network latency (submit → ack)
        if submit_ts and ack_ts:
            network_ms = (ack_ts - submit_ts).total_seconds() * 1000
            self._network_latencies_ms.append(network_ms)
        
        # Execution latency (ack → fill)
        if ack_ts and fill_ts:
            execution_ms = (fill_ts - ack_ts).total_seconds() * 1000
            self._execution_latencies_ms.append(execution_ms)
        
        # Total latency (signal → fill)
        if signal_ts and fill_ts:
            total_ms = (fill_ts - signal_ts).total_seconds() * 1000
            self._total_latencies_ms.append(total_ms)
        
        logger.info(
            f"📊 LATENCY | "
            f"order={client_order_id} | "
            f"total={total_ms:.0f if total_ms else 0}ms | "
            f"internal={internal_ms:.0f if internal_ms else 0}ms | "
            f"network={network_ms:.0f if network_ms else 0}ms | "
            f"execution={execution_ms:.0f if execution_ms else 0}ms"
        )
        
        del self._inflight[client_order_id]
    
    # === Stats & Health ===
    
    def get_stats(self) -> Dict:
        """Get P50/P95/P99 latency stats (NOT averages!)"""
        def percentile(data: deque, p: float) -> Optional[float]:
            if not data:
                return None
            sorted_data = sorted(data)
            index = int(len(sorted_data) * p / 100)
            return sorted_data[min(index, len(sorted_data) - 1)]
        
        return {
            "count": len(self._total_latencies_ms),
            "p50_total_ms": percentile(self._total_latencies_ms, 50),
            "p95_total_ms": percentile(self._total_latencies_ms, 95),
            "p99_total_ms": percentile(self._total_latencies_ms, 99),
            "p50_internal_ms": percentile(self._internal_latencies_ms, 50),
            "p95_internal_ms": percentile(self._internal_latencies_ms, 95),
            "p50_network_ms": percentile(self._network_latencies_ms, 50),
            "p95_network_ms": percentile(self._network_latencies_ms, 95),
            "p50_execution_ms": percentile(self._execution_latencies_ms, 50),
            "p95_execution_ms": percentile(self._execution_latencies_ms, 95)
        }
    
    def get_health_status(self) -> Dict:
        """
        Get health status based on fund-grade thresholds.
        p95 > 1500ms → WARNING
        p99 > 3000ms → CRITICAL
        """
        stats = self.get_stats()
        
        if stats["count"] == 0:
            return {"status": "UNKNOWN", "reason": "insufficient_data"}
        
        p95 = stats.get("p95_total_ms")
        p99 = stats.get("p99_total_ms")
        
        if p99 and p99 > 3000:
            return {
                "status": "CRITICAL",
                "reason": f"p99_{p99:.0f}ms_exceeds_3000ms",
                "p95_ms": p95,
                "p99_ms": p99
            }
        
        if p95 and p95 > 1500:
            return {
                "status": "WARNING",
                "reason": f"p95_{p95:.0f}ms_exceeds_1500ms",
                "p95_ms": p95,
                "p99_ms": p99
            }
        
        return {"status": "HEALTHY", "p95_ms": p95, "p99_ms": p99}
    
    def get_inflight_count(self) -> int:
        """Get count of in-flight orders"""
        return len(self._inflight)


# === Singleton ===

_latency_tracker: Optional[LatencyTracker] = None


def get_latency_tracker() -> LatencyTracker:
    """Get singleton latency tracker"""
    global _latency_tracker
    if _latency_tracker is None:
        _latency_tracker = LatencyTracker(window_size=100)
    return _latency_tracker


def reset_latency_tracker():
    """Reset singleton (for testing)"""
    global _latency_tracker
    _latency_tracker = None
