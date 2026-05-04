"""System Health Model (P1.2 Enhanced)

Центральная модель оценки здоровья системы.
Основа для защиты капитала + execution quality control.
"""

import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class SystemHealth:
    """Модель здоровья системы (P1.2: с latency awareness)"""

    def __init__(self):
        self.status = "HEALTHY"  # HEALTHY | WARNING | CRITICAL
        
        self.metrics: Dict[str, Any] = {
            "daily_pnl_pct": 0.0,
            "drawdown_pct": 0.0,
            "reject_rate": 0.0,
            "reconciliation_critical": 0,
            
            # P1.2: Latency metrics (first-class citizens)
            "latency_p50_ms": 0,
            "latency_p95_ms": 0,
            "latency_p99_ms": 0,
            "latency_status": "UNKNOWN"  # HEALTHY | WARNING | CRITICAL
        }

    def update_metrics(self, metrics: Dict[str, Any]) -> None:
        """Обновить metrics"""
        self.metrics.update(metrics)
        logger.debug(f"Health metrics updated: {self.metrics}")
    
    def update_latency(self, latency_health: Dict[str, Any]) -> None:
        """
        P1.2: Update latency metrics from latency_tracker.
        
        Args:
            latency_health: {status, p95_ms, p99_ms, ...}
        """
        self.metrics["latency_status"] = latency_health.get("status", "UNKNOWN")
        self.metrics["latency_p95_ms"] = latency_health.get("p95_ms", 0)
        self.metrics["latency_p99_ms"] = latency_health.get("p99_ms", 0)
        logger.debug(f"[P1.2] Latency health updated: {latency_health}")

    def evaluate(self) -> str:
        """
        Оценить здоровье системы по metrics.
        
        P1.2: Latency as execution risk (PRIORITY logic).
        
        Returns:
            "HEALTHY" | "WARNING" | "CRITICAL"
        """
        current_status = "HEALTHY"
        
        # ========================================
        # CRITICAL CONDITIONS (highest priority)
        # ========================================
        
        # P1.2: Latency CRITICAL
        if self.metrics.get("latency_status") == "CRITICAL":
            logger.critical(
                f"⚠️ CRITICAL: Latency critical | "
                f"p95={self.metrics.get('latency_p95_ms')}ms | "
                f"p99={self.metrics.get('latency_p99_ms')}ms"
            )
            self.status = "CRITICAL"
            return "CRITICAL"
        
        # Drawdown CRITICAL
        if self.metrics["drawdown_pct"] < -0.15:
            logger.warning(f"CRITICAL: drawdown {self.metrics['drawdown_pct']:.2%} < -15%")
            self.status = "CRITICAL"
            return "CRITICAL"

        # Reconciliation CRITICAL
        if self.metrics["reconciliation_critical"] > 0:
            logger.warning(f"CRITICAL: reconciliation_critical={self.metrics['reconciliation_critical']}")
            self.status = "CRITICAL"
            return "CRITICAL"

        # ========================================
        # WARNING CONDITIONS
        # ========================================
        
        # P1.2: Latency WARNING
        if self.metrics.get("latency_status") == "WARNING":
            logger.warning(
                f"⚠️ WARNING: Latency degraded | "
                f"p95={self.metrics.get('latency_p95_ms')}ms"
            )
            current_status = "WARNING"
        
        # Daily PnL WARNING
        if self.metrics["daily_pnl_pct"] < -0.07:
            logger.warning(f"WARNING: daily_pnl {self.metrics['daily_pnl_pct']:.2%} < -7%")
            current_status = "WARNING"

        # Reject rate WARNING
        if self.metrics["reject_rate"] > 0.2:
            logger.warning(f"WARNING: reject_rate {self.metrics['reject_rate']:.2%} > 20%")
            current_status = "WARNING"

        # Set final status
        self.status = current_status
        return current_status

    def to_dict(self) -> Dict[str, Any]:
        """Преобразовать в dict для API"""
        return {
            "status": self.status,
            "metrics": self.metrics
        }
