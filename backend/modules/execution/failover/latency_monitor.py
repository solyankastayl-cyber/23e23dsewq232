"""
Latency Monitor
===============

Мониторинг и анализ латентности с автоматическими алертами.
"""

from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from collections import deque

from .failover_types import (
    LatencyGrade,
    LatencySnapshot,
    FailoverAction
)


class LatencyMonitor:
    """
    Монитор латентности.
    
    Отслеживает:
    - Текущую латентность
    - Тренды латентности
    - Спайки латентности
    
    Пороги:
    - < 200ms → NORMAL
    - 200-500ms → DEGRADED
    - 500-800ms → POOR
    - > 800ms → CRITICAL
    """
    
    def __init__(
        self,
        normal_threshold_ms: float = 200.0,
        degraded_threshold_ms: float = 500.0,
        critical_threshold_ms: float = 800.0,
        spike_multiplier: float = 3.0,
        history_size: int = 100
    ):
        self.normal_threshold = normal_threshold_ms
        self.degraded_threshold = degraded_threshold_ms
        self.critical_threshold = critical_threshold_ms
        self.spike_multiplier = spike_multiplier
        self.history_size = history_size
        
        # Per-exchange history
        self._history: Dict[str, deque] = {}
        self._baseline: Dict[str, float] = {}
        self._last_grade: Dict[str, LatencyGrade] = {}
    
    def record(
        self,
        exchange: str,
        latency_ms: float,
        endpoint: str = "general"
    ) -> Dict[str, Any]:
        """
        Записать латентность и получить анализ.
        
        Returns:
            Dict с grade, is_spike, recommended_action
        """
        now = datetime.utcnow()
        
        # Initialize
        if exchange not in self._history:
            self._history[exchange] = deque(maxlen=self.history_size)
            self._baseline[exchange] = latency_ms
        
        # Record
        snapshot = LatencySnapshot(
            exchange=exchange,
            endpoint=endpoint,
            latency_ms=latency_ms,
            timestamp=now,
            is_timeout=latency_ms > 5000
        )
        self._history[exchange].append(snapshot)
        
        # Update baseline (exponential moving average)
        alpha = 0.1
        self._baseline[exchange] = (
            alpha * latency_ms + (1 - alpha) * self._baseline[exchange]
        )
        
        # Analyze
        grade = self._determine_grade(latency_ms)
        is_spike = self._detect_spike(exchange, latency_ms)
        action = self._determine_action(grade, is_spike)
        
        # Track grade changes
        prev_grade = self._last_grade.get(exchange, LatencyGrade.NORMAL)
        grade_changed = grade != prev_grade
        self._last_grade[exchange] = grade
        
        return {
            "exchange": exchange,
            "latency_ms": latency_ms,
            "grade": grade.value,
            "is_spike": is_spike,
            "baseline_ms": round(self._baseline[exchange], 2),
            "recommended_action": action.value if action else "NONE",
            "grade_changed": grade_changed,
            "previous_grade": prev_grade.value,
            "timestamp": now.isoformat()
        }
    
    def get_stats(self, exchange: str) -> Dict[str, Any]:
        """Получить статистику латентности"""
        if exchange not in self._history or not self._history[exchange]:
            return self._empty_stats(exchange)
        
        latencies = [s.latency_ms for s in self._history[exchange]]
        
        return {
            "exchange": exchange,
            "sample_count": len(latencies),
            "current_ms": latencies[-1] if latencies else 0,
            "avg_ms": round(sum(latencies) / len(latencies), 2),
            "min_ms": round(min(latencies), 2),
            "max_ms": round(max(latencies), 2),
            "p50_ms": round(self._percentile(latencies, 50), 2),
            "p95_ms": round(self._percentile(latencies, 95), 2),
            "p99_ms": round(self._percentile(latencies, 99), 2),
            "baseline_ms": round(self._baseline.get(exchange, 0), 2),
            "current_grade": self._last_grade.get(exchange, LatencyGrade.NORMAL).value,
            "spike_count": sum(1 for s in self._history[exchange] 
                             if s.latency_ms > self._baseline.get(exchange, 100) * self.spike_multiplier),
            "timeout_count": sum(1 for s in self._history[exchange] if s.is_timeout)
        }
    
    def get_all_stats(self) -> Dict[str, Dict[str, Any]]:
        """Получить статистику по всем биржам"""
        return {ex: self.get_stats(ex) for ex in self._history.keys()}
    
    def get_trend(self, exchange: str, window: int = 20) -> Dict[str, Any]:
        """Получить тренд латентности"""
        if exchange not in self._history:
            return {"exchange": exchange, "trend": "UNKNOWN", "change_pct": 0}
        
        history = list(self._history[exchange])
        if len(history) < window:
            return {"exchange": exchange, "trend": "INSUFFICIENT_DATA", "change_pct": 0}
        
        recent = history[-window:]
        older = history[-window*2:-window] if len(history) >= window*2 else history[:window]
        
        recent_avg = sum(s.latency_ms for s in recent) / len(recent)
        older_avg = sum(s.latency_ms for s in older) / len(older)
        
        if older_avg > 0:
            change_pct = (recent_avg - older_avg) / older_avg * 100
        else:
            change_pct = 0
        
        if change_pct > 20:
            trend = "INCREASING"
        elif change_pct < -20:
            trend = "IMPROVING"
        else:
            trend = "STABLE"
        
        return {
            "exchange": exchange,
            "trend": trend,
            "change_pct": round(change_pct, 2),
            "recent_avg_ms": round(recent_avg, 2),
            "older_avg_ms": round(older_avg, 2)
        }
    
    def _determine_grade(self, latency_ms: float) -> LatencyGrade:
        """Определить grade латентности"""
        if latency_ms < 50:
            return LatencyGrade.EXCELLENT
        elif latency_ms < 100:
            return LatencyGrade.GOOD
        elif latency_ms < self.normal_threshold:
            return LatencyGrade.NORMAL
        elif latency_ms < self.degraded_threshold:
            return LatencyGrade.DEGRADED
        elif latency_ms < self.critical_threshold:
            return LatencyGrade.POOR
        else:
            return LatencyGrade.CRITICAL
    
    def _detect_spike(self, exchange: str, latency_ms: float) -> bool:
        """Обнаружить спайк латентности"""
        baseline = self._baseline.get(exchange, self.normal_threshold)
        return latency_ms > baseline * self.spike_multiplier
    
    def _determine_action(
        self,
        grade: LatencyGrade,
        is_spike: bool
    ) -> Optional[FailoverAction]:
        """Определить рекомендуемое действие"""
        if grade == LatencyGrade.CRITICAL:
            return FailoverAction.PAUSE_NEW_POSITIONS
        elif grade == LatencyGrade.POOR:
            return FailoverAction.REDUCE_POSITION_SIZE
        elif grade == LatencyGrade.DEGRADED:
            return FailoverAction.THROTTLE_REQUESTS
        elif is_spike:
            return FailoverAction.THROTTLE_REQUESTS
        return None
    
    def _percentile(self, data: List[float], p: float) -> float:
        """Вычислить перцентиль"""
        if not data:
            return 0.0
        sorted_data = sorted(data)
        idx = int(len(sorted_data) * p / 100)
        return sorted_data[min(idx, len(sorted_data) - 1)]
    
    def _empty_stats(self, exchange: str) -> Dict[str, Any]:
        """Пустая статистика"""
        return {
            "exchange": exchange,
            "sample_count": 0,
            "current_ms": 0,
            "avg_ms": 0,
            "min_ms": 0,
            "max_ms": 0,
            "p50_ms": 0,
            "p95_ms": 0,
            "p99_ms": 0,
            "baseline_ms": 0,
            "current_grade": "UNKNOWN",
            "spike_count": 0,
            "timeout_count": 0
        }
