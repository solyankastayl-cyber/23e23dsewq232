"""
Safety Service (SEC1)
=====================

Main service for Execution Safety Layer.

Coordinates all guards and provides unified API.
"""

import threading
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

from .safety_types import (
    SafetyDecision,
    SafetyDecisionResult,
    SafetyGuardType,
    SafetyConfig,
    SafetyEvent,
    SafetyEventType,
    SafetyStats,
    OrderValidationRequest,
    QuarantineState
)
from .duplicate_guard import duplicate_guard
from .position_guard import position_guard
from .execution_rate_guard import execution_rate_guard
from .stale_order_guard import stale_order_guard
from .exchange_sync_guard import exchange_sync_guard


class SafetyService:
    """
    Main Execution Safety Service.
    
    Provides unified interface for:
    - Order validation through all guards
    - Configuration management
    - Event logging
    - Quarantine management
    - Statistics
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
        
        # Guards
        self._duplicate_guard = duplicate_guard
        self._position_guard = position_guard
        self._rate_guard = execution_rate_guard
        self._stale_guard = stale_order_guard
        self._sync_guard = exchange_sync_guard
        
        # Configuration
        self._config = SafetyConfig()
        
        # Events
        self._events: List[SafetyEvent] = []
        self._max_events = 1000
        
        # Quarantines
        self._quarantines: Dict[str, QuarantineState] = {}
        
        # Statistics
        self._stats = SafetyStats()
        
        self._initialized = True
        print("[SafetyService] Initialized (SEC1)")
    
    # ===========================================
    # Order Validation
    # ===========================================
    
    def validate_order(
        self,
        order: OrderValidationRequest,
        current_position: Optional[Dict] = None,
        current_price: Optional[float] = None
    ) -> SafetyDecisionResult:
        """
        Validate order through all safety guards.
        
        Order of checks:
        1. Quarantine check
        2. Duplicate check
        3. Rate limit check
        4. Position limit check
        
        Returns first blocking result or aggregated result.
        """
        self._stats.total_validations += 1
        
        all_warnings = []
        
        # Check 1: Quarantine
        quarantine = self._check_quarantine(order.exchange, order.symbol)
        if quarantine:
            self._stats.blocked_orders += 1
            self._log_event(SafetyEventType.ORDER_BLOCKED_DUPLICATE, order.order_id, 
                          order.symbol, order.exchange, SafetyGuardType.DUPLICATE,
                          SafetyDecision.BLOCK, f"Quarantined: {quarantine.reason}")
            return SafetyDecisionResult(
                decision=SafetyDecision.BLOCK,
                guard=SafetyGuardType.DUPLICATE,
                order_id=order.order_id,
                reason=f"Target is quarantined: {quarantine.reason}"
            )
        
        # Check 2: Duplicate
        dup_result = self._duplicate_guard.validate(order)
        if dup_result.decision == SafetyDecision.BLOCK:
            self._stats.blocked_orders += 1
            self._stats.duplicate_blocks += 1
            self._log_event(SafetyEventType.ORDER_BLOCKED_DUPLICATE, order.order_id,
                          order.symbol, order.exchange, SafetyGuardType.DUPLICATE,
                          SafetyDecision.BLOCK, dup_result.reason)
            return dup_result
        all_warnings.extend(dup_result.warnings)
        
        # Check 3: Rate limit
        rate_result = self._rate_guard.validate(order)
        if rate_result.decision == SafetyDecision.BLOCK:
            self._stats.blocked_orders += 1
            self._stats.rate_limit_blocks += 1
            self._log_event(SafetyEventType.ORDER_BLOCKED_RATE_LIMIT, order.order_id,
                          order.symbol, order.exchange, SafetyGuardType.RATE,
                          SafetyDecision.BLOCK, rate_result.reason)
            return rate_result
        all_warnings.extend(rate_result.warnings)
        
        # Check 4: Position limit
        pos_result = self._position_guard.validate(order, current_position, current_price)
        if pos_result.decision == SafetyDecision.BLOCK:
            self._stats.blocked_orders += 1
            self._stats.position_limit_blocks += 1
            self._log_event(SafetyEventType.ORDER_BLOCKED_POSITION_LIMIT, order.order_id,
                          order.symbol, order.exchange, SafetyGuardType.POSITION,
                          SafetyDecision.BLOCK, pos_result.reason)
            return pos_result
        all_warnings.extend(pos_result.warnings)
        
        # Track for stale order detection
        self._stale_guard.track_order(order.order_id, order.symbol, order.side, order.exchange)
        
        # All checks passed
        if all_warnings:
            self._stats.warnings_issued += len(all_warnings)
            return SafetyDecisionResult(
                decision=SafetyDecision.WARN,
                order_id=order.order_id,
                reason=f"Order allowed with {len(all_warnings)} warning(s)",
                warnings=all_warnings
            )
        
        return SafetyDecisionResult(
            decision=SafetyDecision.ALLOW,
            order_id=order.order_id,
            reason="All safety checks passed"
        )
    
    def _check_quarantine(self, exchange: str, symbol: str) -> Optional[QuarantineState]:
        """Check if exchange or symbol is quarantined"""
        # Check exchange quarantine
        ex_key = f"EXCHANGE:{exchange}"
        if ex_key in self._quarantines:
            q = self._quarantines[ex_key]
            if q.active:
                return q
        
        # Check symbol quarantine
        sym_key = f"SYMBOL:{exchange}:{symbol}"
        if sym_key in self._quarantines:
            q = self._quarantines[sym_key]
            if q.active:
                return q
        
        return None
    
    # ===========================================
    # Quarantine Management
    # ===========================================
    
    def quarantine_exchange(self, exchange: str, reason: str, duration_minutes: Optional[int] = None):
        """Quarantine an entire exchange"""
        key = f"EXCHANGE:{exchange}"
        expires_at = None
        if duration_minutes:
            expires_at = datetime.now(timezone.utc).replace(microsecond=0)
            from datetime import timedelta
            expires_at += timedelta(minutes=duration_minutes)
        
        self._quarantines[key] = QuarantineState(
            target_type="EXCHANGE",
            target=exchange,
            reason=reason,
            expires_at=expires_at
        )
        self._stats.active_quarantines = len([q for q in self._quarantines.values() if q.active])
        
        self._log_event(SafetyEventType.EXCHANGE_QUARANTINED, None, None, exchange,
                       None, SafetyDecision.QUARANTINE, reason)
    
    def quarantine_symbol(self, exchange: str, symbol: str, reason: str, duration_minutes: Optional[int] = None):
        """Quarantine a specific symbol"""
        key = f"SYMBOL:{exchange}:{symbol}"
        expires_at = None
        if duration_minutes:
            expires_at = datetime.now(timezone.utc).replace(microsecond=0)
            from datetime import timedelta
            expires_at += timedelta(minutes=duration_minutes)
        
        self._quarantines[key] = QuarantineState(
            target_type="SYMBOL",
            target=f"{exchange}:{symbol}",
            reason=reason,
            expires_at=expires_at
        )
        self._stats.active_quarantines = len([q for q in self._quarantines.values() if q.active])
        
        self._log_event(SafetyEventType.SYMBOL_QUARANTINED, None, symbol, exchange,
                       None, SafetyDecision.QUARANTINE, reason)
    
    def lift_quarantine(self, key: str) -> bool:
        """Lift a quarantine by key"""
        if key in self._quarantines:
            self._quarantines[key].active = False
            self._stats.active_quarantines = len([q for q in self._quarantines.values() if q.active])
            return True
        return False
    
    def get_quarantines(self, active_only: bool = True) -> List[Dict]:
        """Get all quarantines"""
        quarantines = list(self._quarantines.values())
        if active_only:
            quarantines = [q for q in quarantines if q.active]
        return [q.to_dict() for q in quarantines]
    
    # ===========================================
    # Stale Order Check
    # ===========================================
    
    def check_stale_orders(self) -> List[Dict]:
        """Check for stale orders and return events"""
        events = self._stale_guard.check_stale_orders()
        
        for event in events:
            self._events.append(event)
            self._stats.stale_orders_detected += 1
        
        return [e.to_dict() for e in events]
    
    def get_stale_orders(self) -> List[Dict]:
        """Get current stale orders"""
        return self._stale_guard.get_stale_orders()
    
    def update_order_status(self, order_id: str, status: str):
        """Update order status for stale tracking"""
        self._stale_guard.update_order(order_id, status)
    
    # ===========================================
    # Exchange Sync
    # ===========================================
    
    def validate_exchange_sync(
        self,
        exchange_positions: Dict[str, Dict],
        exchange_orders: Dict[str, Dict],
        exchange_balances: Dict[str, float]
    ) -> SafetyDecisionResult:
        """Validate exchange sync"""
        result = self._sync_guard.validate_sync(
            exchange_positions, exchange_orders, exchange_balances
        )
        
        if result.decision == SafetyDecision.QUARANTINE:
            self._stats.exchange_desyncs += 1
            self._log_event(SafetyEventType.EXCHANGE_DESYNC, None, None, None,
                          SafetyGuardType.EXCHANGE_SYNC, SafetyDecision.QUARANTINE,
                          result.reason)
        
        return result
    
    # ===========================================
    # Configuration
    # ===========================================
    
    def get_config(self) -> Dict[str, Any]:
        """Get current configuration"""
        return self._config.to_dict()
    
    def update_config(self, config_update: Dict[str, Any]) -> Dict[str, Any]:
        """Update configuration"""
        if "duplicate" in config_update:
            for k, v in config_update["duplicate"].items():
                if hasattr(self._config.duplicate, k):
                    setattr(self._config.duplicate, k, v)
        
        if "position" in config_update:
            for k, v in config_update["position"].items():
                if hasattr(self._config.position, k):
                    setattr(self._config.position, k, v)
        
        if "rate" in config_update:
            for k, v in config_update["rate"].items():
                if hasattr(self._config.rate, k):
                    setattr(self._config.rate, k, v)
        
        if "stale" in config_update:
            for k, v in config_update["stale"].items():
                if hasattr(self._config.stale, k):
                    setattr(self._config.stale, k, v)
        
        if "exchangeSync" in config_update:
            for k, v in config_update["exchangeSync"].items():
                if hasattr(self._config.exchange_sync, k):
                    setattr(self._config.exchange_sync, k, v)
        
        self._log_event(SafetyEventType.CONFIG_UPDATED, None, None, None,
                       None, None, "Configuration updated")
        
        return self._config.to_dict()
    
    # ===========================================
    # Events & Statistics
    # ===========================================
    
    def _log_event(
        self,
        event_type: SafetyEventType,
        order_id: Optional[str],
        symbol: Optional[str],
        exchange: Optional[str],
        guard: Optional[SafetyGuardType],
        decision: Optional[SafetyDecision],
        message: str
    ):
        """Log safety event"""
        event = SafetyEvent(
            event_type=event_type,
            order_id=order_id,
            symbol=symbol,
            exchange=exchange,
            guard=guard,
            decision=decision,
            message=message
        )
        
        self._events.append(event)
        
        # Trim events if needed
        if len(self._events) > self._max_events:
            self._events = self._events[-self._max_events:]
    
    def get_events(self, limit: int = 50) -> List[Dict]:
        """Get recent events"""
        return [e.to_dict() for e in self._events[-limit:]]
    
    def get_stats(self) -> Dict[str, Any]:
        """Get statistics"""
        return self._stats.to_dict()
    
    def get_rate_status(self) -> Dict[str, Any]:
        """Get current rate limit status"""
        return self._rate_guard.get_current_rates()
    
    # ===========================================
    # Health
    # ===========================================
    
    def get_health(self) -> Dict[str, Any]:
        """Get service health"""
        return {
            "module": "Execution Safety Layer",
            "phase": "SEC1",
            "status": "healthy",
            "guards": {
                "duplicate": self._duplicate_guard.get_stats(),
                "position": self._position_guard.get_stats(),
                "rate": self._rate_guard.get_stats(),
                "stale": self._stale_guard.get_stats(),
                "exchangeSync": self._sync_guard.get_stats()
            },
            "stats": self._stats.to_dict(),
            "quarantines": len([q for q in self._quarantines.values() if q.active]),
            "recentEvents": len(self._events)
        }


# Global singleton
safety_service = SafetyService()
