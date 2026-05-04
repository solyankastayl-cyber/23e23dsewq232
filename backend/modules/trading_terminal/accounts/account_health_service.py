"""
Account Health Service (TR1)
============================

Health monitoring for exchange connections.

Features:
- Connection health checks
- Latency monitoring
- Permission validation
"""

import threading
import time
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

from .account_types import (
    AccountHealthStatus,
    AccountHealthCheck,
    ConnectionStatus
)
from .account_service import account_service


class AccountHealthService:
    """
    Account health monitoring service.
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        # Health check history
        self._health_history: Dict[str, List[AccountHealthCheck]] = {}
        self._max_history = 100
        
        # Thresholds
        self._latency_warning_ms = 500
        self._latency_error_ms = 2000
        
        self._initialized = True
        print("[AccountHealthService] Initialized")
    
    # ===========================================
    # Health Checks
    # ===========================================
    
    def check_health(self, connection_id: str) -> AccountHealthCheck:
        """
        Perform health check on a connection.
        """
        conn = account_service.get_connection(connection_id)
        
        if not conn:
            return AccountHealthCheck(
                connection_id=connection_id,
                status=AccountHealthStatus.ERROR,
                status_reason="Connection not found",
                auth_check=False,
                balance_check=False,
                permission_check=False
            )
        
        # Check connection status
        if conn.status == ConnectionStatus.DISABLED:
            return AccountHealthCheck(
                connection_id=connection_id,
                status=AccountHealthStatus.WARNING,
                status_reason="Connection is disabled",
                auth_check=True,
                balance_check=False,
                permission_check=True
            )
        
        # Perform health check
        start_time = time.time()
        
        warnings = []
        auth_ok = True
        balance_ok = True
        permission_ok = True
        
        # Check auth by fetching state
        try:
            state = account_service.get_account_state(connection_id, force_refresh=True)
            if not state:
                auth_ok = False
                balance_ok = False
        except Exception as e:
            auth_ok = False
            warnings.append(f"Auth error: {str(e)}")
        
        # Check permissions
        if not conn.permissions:
            permission_ok = False
            warnings.append("No permissions detected")
        elif "READ" not in conn.permissions:
            permission_ok = False
            warnings.append("Missing READ permission")
        
        # Calculate latency
        latency_ms = (time.time() - start_time) * 1000
        
        if latency_ms > self._latency_error_ms:
            warnings.append(f"High latency: {latency_ms:.0f}ms")
        elif latency_ms > self._latency_warning_ms:
            warnings.append(f"Elevated latency: {latency_ms:.0f}ms")
        
        # Determine overall status
        if not auth_ok:
            status = AccountHealthStatus.ERROR
            reason = "Authentication failed"
        elif not permission_ok:
            status = AccountHealthStatus.ERROR
            reason = "Permission check failed"
        elif not balance_ok:
            status = AccountHealthStatus.DEGRADED
            reason = "Unable to fetch balances"
        elif latency_ms > self._latency_error_ms:
            status = AccountHealthStatus.DEGRADED
            reason = f"High latency: {latency_ms:.0f}ms"
        elif latency_ms > self._latency_warning_ms or warnings:
            status = AccountHealthStatus.WARNING
            reason = warnings[0] if warnings else "Minor issues detected"
        else:
            status = AccountHealthStatus.HEALTHY
            reason = "All checks passed"
        
        health = AccountHealthCheck(
            connection_id=connection_id,
            status=status,
            status_reason=reason,
            auth_check=auth_ok,
            balance_check=balance_ok,
            permission_check=permission_ok,
            latency_ms=latency_ms,
            warnings=warnings
        )
        
        # Store in history
        self._store_health_check(connection_id, health)
        
        return health
    
    def check_all_health(self) -> List[AccountHealthCheck]:
        """Check health of all connections"""
        connections = account_service.get_all_connections()
        results = []
        
        for conn in connections:
            health = self.check_health(conn.connection_id)
            results.append(health)
        
        return results
    
    # ===========================================
    # History
    # ===========================================
    
    def _store_health_check(self, connection_id: str, check: AccountHealthCheck) -> None:
        """Store health check in history"""
        if connection_id not in self._health_history:
            self._health_history[connection_id] = []
        
        self._health_history[connection_id].append(check)
        
        # Limit history size
        if len(self._health_history[connection_id]) > self._max_history:
            self._health_history[connection_id] = self._health_history[connection_id][-self._max_history:]
    
    def get_health_history(self, connection_id: str, limit: int = 20) -> List[AccountHealthCheck]:
        """Get health check history"""
        history = self._health_history.get(connection_id, [])
        return list(reversed(history[-limit:]))
    
    # ===========================================
    # Summary
    # ===========================================
    
    def get_health_summary(self) -> Dict[str, Any]:
        """Get health summary for all connections"""
        connections = account_service.get_all_connections()
        
        healthy = 0
        warning = 0
        degraded = 0
        error = 0
        
        for conn in connections:
            health = self.check_health(conn.connection_id)
            
            if health.status == AccountHealthStatus.HEALTHY:
                healthy += 1
            elif health.status == AccountHealthStatus.WARNING:
                warning += 1
            elif health.status == AccountHealthStatus.DEGRADED:
                degraded += 1
            else:
                error += 1
        
        return {
            "total": len(connections),
            "healthy": healthy,
            "warning": warning,
            "degraded": degraded,
            "error": error,
            "overall_status": "HEALTHY" if error == 0 and degraded == 0 else (
                "WARNING" if error == 0 else "ERROR"
            )
        }
    
    # ===========================================
    # Service Health
    # ===========================================
    
    def get_service_health(self) -> Dict[str, Any]:
        """Get service health"""
        return {
            "service": "AccountHealthService",
            "status": "healthy",
            "phase": "TR1",
            "tracked_connections": len(self._health_history)
        }


# Global singleton
account_health_service = AccountHealthService()
