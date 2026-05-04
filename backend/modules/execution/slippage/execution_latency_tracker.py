"""
Execution Latency Tracker
=========================

Измерение и анализ латентности исполнения.
"""

from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from .slippage_types import LatencyMetrics


class ExecutionLatencyTracker:
    """
    Tracker для измерения латентности исполнения.
    
    Метрики:
    - Submit latency: время от отправки до подтверждения биржи
    - Execution latency: время от подтверждения до первого fill
    - Total latency: общее время исполнения
    - Fill duration: время между первым и последним fill
    """
    
    def __init__(
        self,
        fast_threshold_ms: float = 50.0,
        normal_threshold_ms: float = 200.0,
        slow_threshold_ms: float = 1000.0
    ):
        """
        Args:
            fast_threshold_ms: Порог для FAST оценки
            normal_threshold_ms: Порог для NORMAL оценки
            slow_threshold_ms: Порог для SLOW (выше = TIMEOUT)
        """
        self.fast_threshold = fast_threshold_ms
        self.normal_threshold = normal_threshold_ms
        self.slow_threshold = slow_threshold_ms
    
    def track(
        self,
        order_sent_ts: datetime,
        exchange_ack_ts: Optional[datetime] = None,
        first_fill_ts: Optional[datetime] = None,
        last_fill_ts: Optional[datetime] = None
    ) -> LatencyMetrics:
        """
        Отслеживание латентности.
        
        Args:
            order_sent_ts: Время отправки ордера
            exchange_ack_ts: Время подтверждения биржей
            first_fill_ts: Время первого fill
            last_fill_ts: Время последнего fill
            
        Returns:
            LatencyMetrics с расчётами
        """
        metrics = LatencyMetrics(
            order_sent_ts=order_sent_ts,
            exchange_ack_ts=exchange_ack_ts,
            first_fill_ts=first_fill_ts,
            last_fill_ts=last_fill_ts
        )
        
        # Calculate submit latency
        if exchange_ack_ts:
            metrics.submit_latency_ms = self._calculate_delta_ms(
                order_sent_ts, exchange_ack_ts
            )
        
        # Calculate execution latency
        if exchange_ack_ts and first_fill_ts:
            metrics.execution_latency_ms = self._calculate_delta_ms(
                exchange_ack_ts, first_fill_ts
            )
        
        # Calculate total latency
        fill_end = last_fill_ts or first_fill_ts
        if fill_end:
            metrics.total_latency_ms = self._calculate_delta_ms(
                order_sent_ts, fill_end
            )
        
        # Calculate fill duration
        if first_fill_ts and last_fill_ts and first_fill_ts != last_fill_ts:
            metrics.fill_duration_ms = self._calculate_delta_ms(
                first_fill_ts, last_fill_ts
            )
        
        # Determine grade
        metrics.latency_grade = self._determine_grade(metrics.total_latency_ms)
        
        # Generate notes
        metrics.notes = self._generate_notes(metrics)
        
        return metrics
    
    def track_from_fills(
        self,
        order_sent_ts: datetime,
        exchange_ack_ts: Optional[datetime],
        fills: List[Dict[str, Any]]
    ) -> LatencyMetrics:
        """
        Отслеживание из списка fills.
        
        Args:
            order_sent_ts: Время отправки
            exchange_ack_ts: Время подтверждения
            fills: Список fills с timestamp
            
        Returns:
            LatencyMetrics
        """
        if not fills:
            return self.track(order_sent_ts, exchange_ack_ts)
        
        # Extract timestamps from fills
        fill_timestamps = []
        for fill in fills:
            ts = fill.get("timestamp") or fill.get("time") or fill.get("ts")
            if ts:
                if isinstance(ts, str):
                    try:
                        ts = datetime.fromisoformat(ts.replace('Z', '+00:00'))
                    except ValueError:
                        continue
                fill_timestamps.append(ts)
        
        if not fill_timestamps:
            return self.track(order_sent_ts, exchange_ack_ts)
        
        fill_timestamps.sort()
        first_fill = fill_timestamps[0]
        last_fill = fill_timestamps[-1]
        
        return self.track(order_sent_ts, exchange_ack_ts, first_fill, last_fill)
    
    def _calculate_delta_ms(self, start: datetime, end: datetime) -> float:
        """Рассчитать разницу в миллисекундах"""
        if not start or not end:
            return 0.0
        
        delta = end - start
        return max(0.0, delta.total_seconds() * 1000)
    
    def _determine_grade(self, total_latency_ms: float) -> str:
        """Определить оценку латентности"""
        if total_latency_ms <= 0:
            return "UNKNOWN"
        elif total_latency_ms <= self.fast_threshold:
            return "FAST"
        elif total_latency_ms <= self.normal_threshold:
            return "NORMAL"
        elif total_latency_ms <= self.slow_threshold:
            return "SLOW"
        else:
            return "TIMEOUT"
    
    def _generate_notes(self, metrics: LatencyMetrics) -> str:
        """Генерация заметок"""
        parts = []
        
        if metrics.submit_latency_ms > 0:
            parts.append(f"Submit: {metrics.submit_latency_ms:.1f}ms")
        
        if metrics.execution_latency_ms > 0:
            parts.append(f"Exec: {metrics.execution_latency_ms:.1f}ms")
        
        if metrics.fill_duration_ms > 0:
            parts.append(f"Fill duration: {metrics.fill_duration_ms:.1f}ms")
        
        grade_note = {
            "FAST": "Excellent latency",
            "NORMAL": "Normal latency",
            "SLOW": "High latency - consider optimization",
            "TIMEOUT": "Critical latency - investigate",
            "UNKNOWN": "Latency unknown"
        }
        
        parts.append(grade_note.get(metrics.latency_grade, ""))
        
        return " | ".join(filter(None, parts))
    
    def calculate_statistics(
        self,
        latency_history: List[LatencyMetrics]
    ) -> Dict[str, Any]:
        """
        Рассчитать статистику латентности.
        
        Args:
            latency_history: История замеров
            
        Returns:
            Статистика
        """
        if not latency_history:
            return {
                "count": 0,
                "avg_total_latency_ms": 0,
                "avg_submit_latency_ms": 0,
                "avg_execution_latency_ms": 0,
                "p50_latency_ms": 0,
                "p95_latency_ms": 0,
                "p99_latency_ms": 0
            }
        
        total_latencies = [m.total_latency_ms for m in latency_history if m.total_latency_ms > 0]
        submit_latencies = [m.submit_latency_ms for m in latency_history if m.submit_latency_ms > 0]
        exec_latencies = [m.execution_latency_ms for m in latency_history if m.execution_latency_ms > 0]
        
        def percentile(data: list, p: float) -> float:
            if not data:
                return 0
            sorted_data = sorted(data)
            idx = int(len(sorted_data) * p / 100)
            return sorted_data[min(idx, len(sorted_data) - 1)]
        
        return {
            "count": len(latency_history),
            "avg_total_latency_ms": round(sum(total_latencies) / len(total_latencies), 2) if total_latencies else 0,
            "avg_submit_latency_ms": round(sum(submit_latencies) / len(submit_latencies), 2) if submit_latencies else 0,
            "avg_execution_latency_ms": round(sum(exec_latencies) / len(exec_latencies), 2) if exec_latencies else 0,
            "p50_latency_ms": round(percentile(total_latencies, 50), 2),
            "p95_latency_ms": round(percentile(total_latencies, 95), 2),
            "p99_latency_ms": round(percentile(total_latencies, 99), 2),
            "grade_distribution": self._grade_distribution(latency_history)
        }
    
    def _grade_distribution(self, history: List[LatencyMetrics]) -> Dict[str, int]:
        """Распределение по grades"""
        dist = {"FAST": 0, "NORMAL": 0, "SLOW": 0, "TIMEOUT": 0, "UNKNOWN": 0}
        for m in history:
            grade = m.latency_grade
            if grade in dist:
                dist[grade] += 1
        return dist
