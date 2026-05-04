"""
Rate Limit Monitor
==================

Мониторинг rate limits бирж.
"""

from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta

from .failover_types import (
    RateLimitStatus,
    FailoverAction
)


class RateLimitMonitor:
    """
    Монитор rate limits.
    
    Отслеживает:
    - Использование лимитов
    - Приближение к лимитам
    - Превышение лимитов
    
    Автоматически:
    - Throttle requests
    - Queue orders
    - Switch mode
    """
    
    # Default exchange limits
    EXCHANGE_LIMITS = {
        "BINANCE": {
            "requests": {"limit": 1200, "window": 60},
            "orders": {"limit": 100, "window": 10},
            "weight": {"limit": 6000, "window": 60}
        },
        "BYBIT": {
            "requests": {"limit": 600, "window": 60},
            "orders": {"limit": 100, "window": 60},
            "weight": {"limit": 5000, "window": 60}
        },
        "OKX": {
            "requests": {"limit": 60, "window": 2},
            "orders": {"limit": 60, "window": 2},
            "weight": {"limit": 6000, "window": 60}
        }
    }
    
    def __init__(
        self,
        warning_threshold_pct: float = 70.0,
        critical_threshold_pct: float = 90.0
    ):
        self.warning_threshold = warning_threshold_pct
        self.critical_threshold = critical_threshold_pct
        
        # Per-exchange, per-type tracking
        self._usage: Dict[str, Dict[str, List[datetime]]] = {}
        self._last_status: Dict[str, Dict[str, RateLimitStatus]] = {}
    
    def record_request(
        self,
        exchange: str,
        limit_type: str = "requests",
        weight: int = 1
    ) -> RateLimitStatus:
        """
        Записать использование rate limit.
        
        Returns:
            RateLimitStatus с текущим состоянием
        """
        now = datetime.utcnow()
        exchange = exchange.upper()
        
        # Initialize
        if exchange not in self._usage:
            self._usage[exchange] = {}
        if limit_type not in self._usage[exchange]:
            self._usage[exchange][limit_type] = []
        
        # Add current request
        for _ in range(weight):
            self._usage[exchange][limit_type].append(now)
        
        # Get status
        return self.get_status(exchange, limit_type)
    
    def get_status(
        self,
        exchange: str,
        limit_type: str = "requests"
    ) -> RateLimitStatus:
        """Получить статус rate limit"""
        exchange = exchange.upper()
        now = datetime.utcnow()
        
        # Get limits
        limits = self.EXCHANGE_LIMITS.get(exchange, self.EXCHANGE_LIMITS["BINANCE"])
        type_limits = limits.get(limit_type, {"limit": 1000, "window": 60})
        
        limit_value = type_limits["limit"]
        window_seconds = type_limits["window"]
        cutoff = now - timedelta(seconds=window_seconds)
        
        # Count recent usage
        if exchange in self._usage and limit_type in self._usage[exchange]:
            # Clean old entries
            self._usage[exchange][limit_type] = [
                ts for ts in self._usage[exchange][limit_type]
                if ts > cutoff
            ]
            used = len(self._usage[exchange][limit_type])
        else:
            used = 0
        
        remaining = max(0, limit_value - used)
        utilization = (used / limit_value * 100) if limit_value > 0 else 0
        
        status = RateLimitStatus(
            exchange=exchange,
            limit_type=limit_type,
            limit_value=limit_value,
            used_value=used,
            remaining=remaining,
            reset_at=now + timedelta(seconds=window_seconds),
            window_seconds=window_seconds,
            utilization_pct=round(utilization, 2),
            is_approaching_limit=utilization >= self.warning_threshold,
            is_exceeded=utilization >= 100
        )
        
        # Cache
        if exchange not in self._last_status:
            self._last_status[exchange] = {}
        self._last_status[exchange][limit_type] = status
        
        return status
    
    def get_all_status(self, exchange: str) -> Dict[str, RateLimitStatus]:
        """Получить все статусы для биржи"""
        exchange = exchange.upper()
        limits = self.EXCHANGE_LIMITS.get(exchange, self.EXCHANGE_LIMITS["BINANCE"])
        
        return {
            limit_type: self.get_status(exchange, limit_type)
            for limit_type in limits.keys()
        }
    
    def get_recommended_action(self, exchange: str) -> Dict[str, Any]:
        """Получить рекомендуемое действие"""
        all_status = self.get_all_status(exchange)
        
        max_utilization = 0
        critical_types = []
        warning_types = []
        
        for limit_type, status in all_status.items():
            if status.utilization_pct > max_utilization:
                max_utilization = status.utilization_pct
            
            if status.is_exceeded:
                critical_types.append(limit_type)
            elif status.is_approaching_limit:
                warning_types.append(limit_type)
        
        # Determine action
        if critical_types:
            action = FailoverAction.PAUSE_NEW_POSITIONS
            severity = "CRITICAL"
        elif warning_types:
            action = FailoverAction.THROTTLE_REQUESTS
            severity = "WARNING"
        else:
            action = FailoverAction.NONE
            severity = "NORMAL"
        
        # Calculate throttle factor
        if max_utilization >= 100:
            throttle_factor = 0.1
        elif max_utilization >= 90:
            throttle_factor = 0.3
        elif max_utilization >= 70:
            throttle_factor = 0.6
        else:
            throttle_factor = 1.0
        
        return {
            "exchange": exchange,
            "max_utilization_pct": round(max_utilization, 2),
            "severity": severity,
            "recommended_action": action.value,
            "throttle_factor": throttle_factor,
            "critical_limits": critical_types,
            "warning_limits": warning_types,
            "can_execute": not critical_types,
            "should_throttle": len(warning_types) > 0
        }
    
    def estimate_wait_time(self, exchange: str, limit_type: str = "requests") -> float:
        """Оценить время ожидания до освобождения лимита"""
        status = self.get_status(exchange, limit_type)
        
        if not status.is_exceeded:
            return 0.0
        
        # Simple estimation based on window
        return status.window_seconds * 0.5
    
    def can_execute(self, exchange: str, required_weight: int = 1) -> bool:
        """Можно ли выполнить запрос"""
        status = self.get_status(exchange, "requests")
        return status.remaining >= required_weight
    
    def get_comparison(self) -> List[Dict[str, Any]]:
        """Сравнить все биржи по rate limits"""
        result = []
        
        for exchange in self.EXCHANGE_LIMITS.keys():
            all_status = self.get_all_status(exchange)
            
            max_util = max(s.utilization_pct for s in all_status.values())
            total_remaining = sum(s.remaining for s in all_status.values())
            
            result.append({
                "exchange": exchange,
                "max_utilization_pct": round(max_util, 2),
                "total_remaining": total_remaining,
                "healthy": max_util < self.warning_threshold,
                "status": all_status
            })
        
        result.sort(key=lambda x: x["max_utilization_pct"])
        return result
