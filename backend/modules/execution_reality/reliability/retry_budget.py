"""
P1.1+ Retry Budget - System-wide retry throttling

Prevents self-DDoS during incidents:
- Global retry limit per time window
- Escalation to Risk Guard when exhausted
- Per-operation tracking

CRITICAL: Without this, system DDOSes exchange during outages
"""

import logging
import time
from typing import Dict, Optional
from datetime import datetime, timezone
from collections import deque

logger = logging.getLogger(__name__)


class RetryBudget:
    """
    Global retry budget to prevent self-DDoS.
    
    Tracks retry attempts system-wide and enforces limits.
    When budget exhausted → escalate to Risk Guard.
    
    Example:
        max_retries_per_minute = 50
        If exceeded → block new retries, emit CRITICAL alert
    """
    
    def __init__(
        self,
        max_retries_per_minute: int = 50,
        max_retries_per_operation: int = 20,
        window_seconds: int = 60
    ):
        """
        Initialize retry budget.
        
        Args:
            max_retries_per_minute: Global retry limit per minute
            max_retries_per_operation: Per-operation limit (prevent single op spam)
            window_seconds: Rolling window size
        """
        self.max_retries_global = max_retries_per_minute
        self.max_retries_per_op = max_retries_per_operation
        self.window_seconds = window_seconds
        
        # Rolling window of retry timestamps
        self._retry_timestamps: deque = deque()
        
        # Per-operation counters (operation_key -> deque of timestamps)
        self._operation_retries: Dict[str, deque] = {}
        
        # Budget exhaustion tracking
        self.budget_exhausted = False
        self.exhaustion_count = 0
        
        logger.info(
            f"✅ RetryBudget initialized | "
            f"global={max_retries_per_minute}/min | "
            f"per_op={max_retries_per_operation}/min"
        )
    
    def can_retry(self, operation_key: Optional[str] = None) -> bool:
        """
        Check if retry is allowed.
        
        Args:
            operation_key: Operation identifier (e.g., "submit_market_order")
        
        Returns:
            True if retry allowed, False if budget exhausted
        """
        now = time.time()
        
        # Clean old entries (outside window)
        self._cleanup_old_entries(now)
        
        # Check global budget
        global_count = len(self._retry_timestamps)
        if global_count >= self.max_retries_global:
            if not self.budget_exhausted:
                self.budget_exhausted = True
                self.exhaustion_count += 1
                logger.critical(
                    f"🔥 RETRY BUDGET EXHAUSTED | "
                    f"global_retries={global_count}/{self.max_retries_global} | "
                    f"exhaustion_count={self.exhaustion_count} | "
                    f"escalate_to_risk_guard=True"
                )
            return False
        
        # Check per-operation budget (if operation_key provided)
        if operation_key:
            if operation_key not in self._operation_retries:
                self._operation_retries[operation_key] = deque()
            
            op_deque = self._operation_retries[operation_key]
            # Clean old entries for this operation
            cutoff = now - self.window_seconds
            while op_deque and op_deque[0] < cutoff:
                op_deque.popleft()
            
            op_count = len(op_deque)
            if op_count >= self.max_retries_per_op:
                logger.warning(
                    f"⚠️ Operation retry budget exceeded | "
                    f"operation={operation_key} | "
                    f"retries={op_count}/{self.max_retries_per_op}"
                )
                return False
        
        # Budget available
        if self.budget_exhausted:
            # Recovered
            self.budget_exhausted = False
            logger.info(
                f"✅ Retry budget RECOVERED | "
                f"global_retries={global_count}/{self.max_retries_global}"
            )
        
        return True
    
    def record_retry(self, operation_key: Optional[str] = None):
        """
        Record a retry attempt.
        
        Args:
            operation_key: Operation identifier
        """
        now = time.time()
        
        # Record global
        self._retry_timestamps.append(now)
        
        # Record per-operation
        if operation_key:
            if operation_key not in self._operation_retries:
                self._operation_retries[operation_key] = deque()
            self._operation_retries[operation_key].append(now)
    
    def _cleanup_old_entries(self, now: float):
        """Remove entries outside rolling window"""
        cutoff = now - self.window_seconds
        
        # Clean global timestamps
        while self._retry_timestamps and self._retry_timestamps[0] < cutoff:
            self._retry_timestamps.popleft()
        
        # Clean per-operation timestamps
        for op_key, op_deque in self._operation_retries.items():
            while op_deque and op_deque[0] < cutoff:
                op_deque.popleft()
    
    def get_stats(self) -> Dict:
        """
        Get current retry budget stats.
        
        Returns:
            {
                "global_retries": int,
                "global_limit": int,
                "utilization": float (0.0-1.0),
                "exhausted": bool,
                "exhaustion_count": int,
                "per_operation": {operation_key: count}
            }
        """
        now = time.time()
        self._cleanup_old_entries(now)
        
        global_count = len(self._retry_timestamps)
        utilization = global_count / self.max_retries_global if self.max_retries_global > 0 else 0.0
        
        per_op_stats = {
            op_key: len(op_deque)
            for op_key, op_deque in self._operation_retries.items()
            if len(op_deque) > 0
        }
        
        return {
            "global_retries": global_count,
            "global_limit": self.max_retries_global,
            "utilization": round(utilization, 2),
            "exhausted": self.budget_exhausted,
            "exhaustion_count": self.exhaustion_count,
            "per_operation": per_op_stats,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }


# Global singleton instance
_global_retry_budget: Optional[RetryBudget] = None


def get_retry_budget() -> RetryBudget:
    """Get global retry budget singleton"""
    global _global_retry_budget
    if _global_retry_budget is None:
        _global_retry_budget = RetryBudget(
            max_retries_per_minute=50,
            max_retries_per_operation=20,
            window_seconds=60
        )
    return _global_retry_budget


def reset_retry_budget():
    """Reset global retry budget (for testing)"""
    global _global_retry_budget
    _global_retry_budget = None
