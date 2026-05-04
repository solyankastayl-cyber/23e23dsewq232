"""
Exchange Sync Guard (SEC1)
==========================

Detects and handles:
- Position sync issues
- Order sync issues
- Balance desync
"""

import threading
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional

from .safety_types import (
    SafetyDecision,
    SafetyDecisionResult,
    SafetyGuardType,
    SafetyEvent,
    SafetyEventType,
    ExchangeSyncConfig
)


class ExchangeSyncGuard:
    """
    Exchange Sync Validation Guard.
    
    Compares internal state with exchange state:
    - Position sizes
    - Order states
    - Balance amounts
    """
    
    def __init__(self, config: Optional[ExchangeSyncConfig] = None):
        self.config = config or ExchangeSyncConfig()
        
        # Last known internal state
        self._internal_positions: Dict[str, Dict] = {}
        self._internal_orders: Dict[str, Dict] = {}
        self._internal_balances: Dict[str, float] = {}
        
        # Last sync check results
        self._sync_issues: List[Dict] = []
        self._last_sync: Optional[datetime] = None
        
        self._lock = threading.Lock()
    
    def validate_sync(
        self,
        exchange_positions: Dict[str, Dict],
        exchange_orders: Dict[str, Dict],
        exchange_balances: Dict[str, float]
    ) -> SafetyDecisionResult:
        """
        Validate sync between internal state and exchange state.
        
        Returns QUARANTINE if critical desync detected.
        """
        if not self.config.enabled:
            return SafetyDecisionResult(
                decision=SafetyDecision.ALLOW,
                reason="Exchange sync guard disabled"
            )
        
        issues = []
        critical = False
        
        with self._lock:
            # Check 1: Position sync
            for symbol, internal_pos in self._internal_positions.items():
                exchange_pos = exchange_positions.get(symbol, {})
                
                internal_size = internal_pos.get("size", 0)
                exchange_size = exchange_pos.get("size", 0)
                
                if internal_size > 0:  # We have a position
                    if exchange_size == 0:
                        # Exchange doesn't have position we think exists
                        issues.append({
                            "type": "POSITION_MISSING",
                            "symbol": symbol,
                            "internal": internal_size,
                            "exchange": exchange_size,
                            "critical": True
                        })
                        critical = True
                    else:
                        # Check size difference
                        diff_pct = abs(internal_size - exchange_size) / max(internal_size, 0.0001)
                        if diff_pct > self.config.position_tolerance_pct:
                            issues.append({
                                "type": "POSITION_SIZE_MISMATCH",
                                "symbol": symbol,
                                "internal": internal_size,
                                "exchange": exchange_size,
                                "diffPct": diff_pct,
                                "critical": diff_pct > 0.1
                            })
                            if diff_pct > 0.1:
                                critical = True
            
            # Check 2: Phantom positions (exchange has, we don't)
            for symbol, exchange_pos in exchange_positions.items():
                if symbol not in self._internal_positions:
                    exchange_size = exchange_pos.get("size", 0)
                    if exchange_size > 0:
                        issues.append({
                            "type": "POSITION_PHANTOM",
                            "symbol": symbol,
                            "internal": 0,
                            "exchange": exchange_size,
                            "critical": True
                        })
                        critical = True
            
            # Check 3: Balance sync
            for asset, internal_balance in self._internal_balances.items():
                exchange_balance = exchange_balances.get(asset, 0)
                
                if internal_balance > 0:
                    diff_pct = abs(internal_balance - exchange_balance) / max(internal_balance, 0.0001)
                    if diff_pct > self.config.balance_tolerance_pct:
                        issues.append({
                            "type": "BALANCE_MISMATCH",
                            "asset": asset,
                            "internal": internal_balance,
                            "exchange": exchange_balance,
                            "diffPct": diff_pct,
                            "critical": False
                        })
            
            # Store issues
            self._sync_issues = issues
            self._last_sync = datetime.now(timezone.utc)
        
        if critical:
            return SafetyDecisionResult(
                decision=SafetyDecision.QUARANTINE,
                guard=SafetyGuardType.EXCHANGE_SYNC,
                reason=f"Critical exchange desync detected ({len(issues)} issues)",
                details={
                    "issues": issues,
                    "criticalCount": len([i for i in issues if i.get("critical")])
                }
            )
        elif issues:
            return SafetyDecisionResult(
                decision=SafetyDecision.WARN,
                guard=SafetyGuardType.EXCHANGE_SYNC,
                reason=f"Exchange sync warnings ({len(issues)} issues)",
                warnings=[i["type"] for i in issues],
                details={"issues": issues}
            )
        
        return SafetyDecisionResult(
            decision=SafetyDecision.ALLOW,
            reason="Exchange sync OK"
        )
    
    def update_internal_position(self, symbol: str, position: Dict):
        """Update internal position state"""
        with self._lock:
            if position.get("size", 0) == 0:
                self._internal_positions.pop(symbol, None)
            else:
                self._internal_positions[symbol] = position
    
    def update_internal_order(self, order_id: str, order: Optional[Dict]):
        """Update internal order state"""
        with self._lock:
            if order is None:
                self._internal_orders.pop(order_id, None)
            else:
                self._internal_orders[order_id] = order
    
    def update_internal_balance(self, asset: str, balance: float):
        """Update internal balance state"""
        with self._lock:
            self._internal_balances[asset] = balance
    
    def get_sync_issues(self) -> List[Dict]:
        """Get current sync issues"""
        with self._lock:
            return list(self._sync_issues)
    
    def get_stats(self) -> Dict:
        """Get guard statistics"""
        with self._lock:
            return {
                "trackedPositions": len(self._internal_positions),
                "trackedOrders": len(self._internal_orders),
                "trackedBalances": len(self._internal_balances),
                "currentIssues": len(self._sync_issues),
                "lastSync": self._last_sync.isoformat() if self._last_sync else None,
                "enabled": self.config.enabled
            }


# Global instance
exchange_sync_guard = ExchangeSyncGuard()
