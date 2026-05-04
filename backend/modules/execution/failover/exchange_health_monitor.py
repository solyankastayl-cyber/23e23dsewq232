"""
Exchange Health Monitor
=======================

Мониторинг здоровья биржи: API availability, latency, error rate.
"""

from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from collections import deque
import random

from .failover_types import (
    ExchangeHealthMetrics,
    ExchangeStatus,
    LatencyGrade,
    LatencySnapshot
)


class ExchangeHealthMonitor:
    """
    Монитор здоровья биржи.
    
    Отслеживает:
    - API availability
    - Response latency
    - Error rate
    - WebSocket health
    """
    
    def __init__(
        self,
        latency_window_size: int = 100,
        error_window_seconds: int = 60
    ):
        self.latency_window_size = latency_window_size
        self.error_window_seconds = error_window_seconds
        
        # Per-exchange tracking
        self._latency_history: Dict[str, deque] = {}
        self._error_history: Dict[str, deque] = {}
        self._success_history: Dict[str, deque] = {}
        self._last_health: Dict[str, ExchangeHealthMetrics] = {}
    
    def record_request(
        self,
        exchange: str,
        latency_ms: float,
        success: bool,
        error: Optional[str] = None,
        endpoint: str = "general"
    ) -> None:
        """Записать результат запроса"""
        now = datetime.utcnow()
        
        # Initialize if needed
        if exchange not in self._latency_history:
            self._latency_history[exchange] = deque(maxlen=self.latency_window_size)
            self._error_history[exchange] = deque(maxlen=1000)
            self._success_history[exchange] = deque(maxlen=1000)
        
        # Record latency
        snapshot = LatencySnapshot(
            exchange=exchange,
            endpoint=endpoint,
            latency_ms=latency_ms,
            timestamp=now,
            is_timeout=latency_ms > 5000,
            error=error
        )
        self._latency_history[exchange].append(snapshot)
        
        # Record success/error
        if success:
            self._success_history[exchange].append(now)
        else:
            self._error_history[exchange].append((now, error))
    
    def get_health(self, exchange: str) -> ExchangeHealthMetrics:
        """Получить метрики здоровья биржи"""
        now = datetime.utcnow()
        cutoff = now - timedelta(seconds=self.error_window_seconds)
        
        # Get latency stats
        latencies = self._get_recent_latencies(exchange)
        avg_latency = sum(latencies) / len(latencies) if latencies else 0.0
        p95_latency = self._percentile(latencies, 95) if latencies else 0.0
        p99_latency = self._percentile(latencies, 99) if latencies else 0.0
        
        # Determine latency grade
        latency_grade = self._determine_latency_grade(avg_latency)
        
        # Calculate error rate
        recent_errors = self._count_recent_items(
            self._error_history.get(exchange, deque()), cutoff
        )
        recent_successes = self._count_recent_items(
            self._success_history.get(exchange, deque()), cutoff
        )
        
        total_requests = recent_errors + recent_successes
        error_rate = recent_errors / total_requests if total_requests > 0 else 0.0
        
        # Determine status
        status = self._determine_status(avg_latency, error_rate)
        
        # Calculate health score
        health_score = self._calculate_health_score(avg_latency, error_rate, status)
        
        # Get last error
        last_error = None
        if exchange in self._error_history and self._error_history[exchange]:
            last_error = self._error_history[exchange][-1][1]
        
        # Get last successful request
        last_success = None
        if exchange in self._success_history and self._success_history[exchange]:
            last_success = self._success_history[exchange][-1]
        
        metrics = ExchangeHealthMetrics(
            exchange=exchange,
            status=status,
            health_score=round(health_score, 4),
            avg_latency_ms=round(avg_latency, 2),
            p95_latency_ms=round(p95_latency, 2),
            p99_latency_ms=round(p99_latency, 2),
            latency_grade=latency_grade,
            error_rate=round(error_rate, 4),
            error_count_1m=recent_errors,
            success_count_1m=recent_successes,
            api_available=status != ExchangeStatus.OFFLINE,
            last_successful_request=last_success,
            last_error=last_error,
            updated_at=now
        )
        
        self._last_health[exchange] = metrics
        return metrics
    
    def get_all_health(self) -> Dict[str, ExchangeHealthMetrics]:
        """Получить здоровье всех бирж"""
        exchanges = list(self._latency_history.keys())
        if not exchanges:
            # Return mock data if no real data
            exchanges = ["BINANCE", "BYBIT", "OKX"]
        
        return {ex: self.get_health(ex) for ex in exchanges}
    
    def simulate_requests(self, exchange: str, count: int = 50) -> None:
        """Симулировать запросы для тестирования"""
        for _ in range(count):
            # Simulate varying latency
            base_latency = 80 if exchange == "BINANCE" else 120 if exchange == "BYBIT" else 150
            latency = base_latency + random.uniform(-30, 100)
            
            # Simulate occasional errors
            success = random.random() > 0.03
            error = "Connection timeout" if not success else None
            
            self.record_request(exchange, latency, success, error)
    
    def _get_recent_latencies(self, exchange: str) -> List[float]:
        """Получить недавние значения латентности"""
        if exchange not in self._latency_history:
            return []
        return [s.latency_ms for s in self._latency_history[exchange]]
    
    def _count_recent_items(self, history: deque, cutoff: datetime) -> int:
        """Подсчитать элементы после cutoff"""
        count = 0
        for item in history:
            ts = item if isinstance(item, datetime) else item[0]
            if ts > cutoff:
                count += 1
        return count
    
    def _percentile(self, data: List[float], p: float) -> float:
        """Вычислить перцентиль"""
        if not data:
            return 0.0
        sorted_data = sorted(data)
        idx = int(len(sorted_data) * p / 100)
        return sorted_data[min(idx, len(sorted_data) - 1)]
    
    def _determine_latency_grade(self, avg_latency: float) -> LatencyGrade:
        """Определить оценку латентности"""
        if avg_latency < 50:
            return LatencyGrade.EXCELLENT
        elif avg_latency < 100:
            return LatencyGrade.GOOD
        elif avg_latency < 200:
            return LatencyGrade.NORMAL
        elif avg_latency < 500:
            return LatencyGrade.DEGRADED
        elif avg_latency < 800:
            return LatencyGrade.POOR
        else:
            return LatencyGrade.CRITICAL
    
    def _determine_status(self, latency: float, error_rate: float) -> ExchangeStatus:
        """Определить статус биржи"""
        if error_rate > 0.5:
            return ExchangeStatus.OFFLINE
        elif error_rate > 0.15 or latency > 800:
            return ExchangeStatus.DEGRADED
        elif error_rate > 0.05 or latency > 500:
            return ExchangeStatus.DEGRADED
        else:
            return ExchangeStatus.ONLINE
    
    def _calculate_health_score(
        self,
        latency: float,
        error_rate: float,
        status: ExchangeStatus
    ) -> float:
        """Рассчитать health score"""
        score = 1.0
        
        # Latency penalty
        if latency > 800:
            score -= 0.4
        elif latency > 500:
            score -= 0.25
        elif latency > 200:
            score -= 0.1
        elif latency > 100:
            score -= 0.05
        
        # Error rate penalty
        score -= min(0.5, error_rate * 3)
        
        # Status penalty
        if status == ExchangeStatus.OFFLINE:
            score = 0.0
        elif status == ExchangeStatus.DEGRADED:
            score = min(score, 0.6)
        
        return max(0.0, min(1.0, score))
