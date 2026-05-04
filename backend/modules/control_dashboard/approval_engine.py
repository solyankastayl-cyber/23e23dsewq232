"""
Approval Queue Engine

PHASE 40.2 — Approval Queue Engine

Manages orders awaiting human approval (Decision Support mode).

Actions:
- APPROVE: Send to Execution Gateway
- REJECT: Remove from queue
- REDUCE: Decrease size
- OVERRIDE: Modify params
"""

from typing import Optional, List, Dict
from datetime import datetime, timezone, timedelta

from .dashboard_types import (
    PendingExecution,
    ApprovalAction,
    ApprovalResult,
    DashboardAuditLog,
)


# ══════════════════════════════════════════════════════════════
# Approval Queue Engine
# ══════════════════════════════════════════════════════════════

class ApprovalQueueEngine:
    """
    Approval Queue Engine — PHASE 40.2
    
    Manages orders awaiting human approval.
    
    This is the Decision Support layer.
    """
    
    def __init__(self, approval_timeout_seconds: int = 300):
        self._pending: Dict[str, PendingExecution] = {}
        self._history: List[PendingExecution] = []
        self._audit_log: List[DashboardAuditLog] = []
        self._approval_timeout = approval_timeout_seconds
    
    # ═══════════════════════════════════════════════════════════
    # 1. Add Pending Execution
    # ═══════════════════════════════════════════════════════════
    
    def add_pending_execution(
        self,
        symbol: str,
        side: str,
        size_usd: float,
        strategy: str,
        order_type: str = "MARKET",
        limit_price: Optional[float] = None,
        hypothesis_id: Optional[str] = None,
        expected_entry: float = 0.0,
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None,
        confidence: float = 0.0,
        reliability: float = 0.0,
        impact_state: str = "LOW",
        metadata: Optional[Dict] = None,
    ) -> PendingExecution:
        """
        Add new pending execution to approval queue.
        
        Called by Execution Brain when in APPROVAL mode.
        """
        # Get current price for size_base calculation
        current_price = self._get_current_price(symbol)
        size_base = size_usd / current_price if current_price > 0 else 0
        
        # Calculate portfolio risk after
        portfolio_risk_after = self._estimate_portfolio_risk_after(symbol, side, size_usd)
        
        # Generate recommendation
        recommendation, reason = self._generate_recommendation(
            symbol=symbol,
            side=side,
            size_usd=size_usd,
            confidence=confidence,
            reliability=reliability,
            impact_state=impact_state,
            portfolio_risk_after=portfolio_risk_after,
        )
        
        # Create pending execution
        pending = PendingExecution(
            symbol=symbol.upper(),
            side=side.upper(),
            size_usd=size_usd,
            size_base=size_base,
            order_type=order_type.upper(),
            limit_price=limit_price,
            strategy=strategy,
            hypothesis_id=hypothesis_id,
            expected_entry=expected_entry or current_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            confidence=confidence,
            reliability=reliability,
            position_risk=self._calculate_position_risk(size_usd, symbol),
            portfolio_risk_after=portfolio_risk_after,
            impact_state=impact_state,
            system_recommendation=recommendation,
            recommendation_reason=reason,
            expires_at=datetime.now(timezone.utc) + timedelta(seconds=self._approval_timeout),
            metadata=metadata or {},
        )
        
        self._pending[pending.pending_id] = pending
        
        # Log
        self._log_action(
            action="PENDING_CREATED",
            action_type="QUEUE",
            symbol=symbol,
            pending_id=pending.pending_id,
            new_value={"size_usd": size_usd, "side": side},
        )
        
        return pending
    
    # ═══════════════════════════════════════════════════════════
    # 2. Get Pending Executions
    # ═══════════════════════════════════════════════════════════
    
    def get_pending_executions(
        self,
        symbol: Optional[str] = None,
        strategy: Optional[str] = None,
        include_expired: bool = False,
    ) -> List[PendingExecution]:
        """Get pending executions from queue."""
        # Clean expired first
        if not include_expired:
            self._clean_expired()
        
        pending = list(self._pending.values())
        
        # Filter
        if symbol:
            pending = [p for p in pending if p.symbol == symbol.upper()]
        if strategy:
            pending = [p for p in pending if p.strategy == strategy]
        if not include_expired:
            pending = [p for p in pending if p.status == "PENDING"]
        
        # Sort by created_at (newest first)
        pending.sort(key=lambda p: p.created_at, reverse=True)
        
        return pending
    
    def get_pending_execution(self, pending_id: str) -> Optional[PendingExecution]:
        """Get specific pending execution."""
        return self._pending.get(pending_id)
    
    def get_pending_count(self) -> int:
        """Get count of pending executions."""
        self._clean_expired()
        return len([p for p in self._pending.values() if p.status == "PENDING"])
    
    # ═══════════════════════════════════════════════════════════
    # 3. Approve Execution
    # ═══════════════════════════════════════════════════════════
    
    def approve_execution(
        self,
        pending_id: str,
        user: str = "operator",
        note: Optional[str] = None,
    ) -> ApprovalResult:
        """
        Approve pending execution.
        
        Sends order to Execution Gateway.
        """
        pending = self._pending.get(pending_id)
        
        if not pending:
            return ApprovalResult(
                success=False,
                action="APPROVE",
                pending_id=pending_id,
                message=f"Pending execution {pending_id} not found",
            )
        
        if pending.status != "PENDING":
            return ApprovalResult(
                success=False,
                action="APPROVE",
                pending_id=pending_id,
                message=f"Pending execution already processed: {pending.status}",
            )
        
        # Check expiry
        if pending.expires_at and datetime.now(timezone.utc) > pending.expires_at:
            pending.status = "EXPIRED"
            return ApprovalResult(
                success=False,
                action="APPROVE",
                pending_id=pending_id,
                message="Pending execution expired",
            )
        
        # Execute through gateway
        try:
            from modules.execution_gateway import get_execution_gateway
            from modules.execution_gateway.gateway_types import (
                ExecutionRequest,
                OrderSide,
                OrderType,
            )
            
            gateway = get_execution_gateway()
            
            request = ExecutionRequest(
                symbol=pending.symbol,
                side=OrderSide(pending.side),
                size_usd=pending.size_usd,
                order_type=OrderType(pending.order_type),
                limit_price=pending.limit_price,
                strategy=pending.strategy,
                hypothesis_id=pending.hypothesis_id,
                expected_price=pending.expected_entry,
            )
            
            # Execute
            import asyncio
            result = asyncio.get_event_loop().run_until_complete(gateway.execute(request))
            
            # Update status
            pending.status = "APPROVED"
            pending.order_id = result.order_id
            
            # Move to history
            self._history.append(pending)
            del self._pending[pending_id]
            
            # Log
            self._log_action(
                action="APPROVE",
                action_type="APPROVAL",
                symbol=pending.symbol,
                pending_id=pending_id,
                order_id=result.order_id,
                user=user,
            )
            
            return ApprovalResult(
                success=result.success,
                action="APPROVE",
                pending_id=pending_id,
                order_id=result.order_id,
                execution_status=result.status.value,
                message=f"Order executed: {result.status.value}",
            )
            
        except Exception as e:
            return ApprovalResult(
                success=False,
                action="APPROVE",
                pending_id=pending_id,
                message=f"Execution failed: {str(e)}",
            )
    
    # ═══════════════════════════════════════════════════════════
    # 4. Reject Execution
    # ═══════════════════════════════════════════════════════════
    
    def reject_execution(
        self,
        pending_id: str,
        user: str = "operator",
        reason: str = "",
    ) -> ApprovalResult:
        """
        Reject pending execution.
        
        Removes from queue without executing.
        """
        pending = self._pending.get(pending_id)
        
        if not pending:
            return ApprovalResult(
                success=False,
                action="REJECT",
                pending_id=pending_id,
                message=f"Pending execution {pending_id} not found",
            )
        
        if pending.status != "PENDING":
            return ApprovalResult(
                success=False,
                action="REJECT",
                pending_id=pending_id,
                message=f"Pending execution already processed: {pending.status}",
            )
        
        # Update status
        pending.status = "REJECTED"
        
        # Move to history
        self._history.append(pending)
        del self._pending[pending_id]
        
        # Log
        self._log_action(
            action="REJECT",
            action_type="APPROVAL",
            symbol=pending.symbol,
            pending_id=pending_id,
            user=user,
            new_value={"reason": reason},
        )
        
        return ApprovalResult(
            success=True,
            action="REJECT",
            pending_id=pending_id,
            message=f"Pending execution rejected: {reason or 'User rejected'}",
        )
    
    # ═══════════════════════════════════════════════════════════
    # 5. Reduce Execution
    # ═══════════════════════════════════════════════════════════
    
    def reduce_execution(
        self,
        pending_id: str,
        new_size_usd: float,
        user: str = "operator",
        note: Optional[str] = None,
    ) -> ApprovalResult:
        """
        Reduce size of pending execution.
        
        Modifies size before approval.
        """
        pending = self._pending.get(pending_id)
        
        if not pending:
            return ApprovalResult(
                success=False,
                action="REDUCE",
                pending_id=pending_id,
                message=f"Pending execution {pending_id} not found",
            )
        
        if pending.status != "PENDING":
            return ApprovalResult(
                success=False,
                action="REDUCE",
                pending_id=pending_id,
                message=f"Pending execution already processed: {pending.status}",
            )
        
        if new_size_usd >= pending.size_usd:
            return ApprovalResult(
                success=False,
                action="REDUCE",
                pending_id=pending_id,
                message="New size must be smaller than current size",
            )
        
        if new_size_usd <= 0:
            return ApprovalResult(
                success=False,
                action="REDUCE",
                pending_id=pending_id,
                message="New size must be positive",
            )
        
        # Store previous
        previous_size = pending.size_usd
        
        # Update
        current_price = self._get_current_price(pending.symbol)
        pending.size_usd = new_size_usd
        pending.size_base = new_size_usd / current_price if current_price > 0 else 0
        pending.status = "MODIFIED"
        
        # Recalculate risk
        pending.position_risk = self._calculate_position_risk(new_size_usd, pending.symbol)
        pending.portfolio_risk_after = self._estimate_portfolio_risk_after(
            pending.symbol, pending.side, new_size_usd
        )
        
        # Log
        self._log_action(
            action="REDUCE",
            action_type="APPROVAL",
            symbol=pending.symbol,
            pending_id=pending_id,
            previous_size=previous_size,
            new_size=new_size_usd,
            user=user,
        )
        
        # Reset status to pending
        pending.status = "PENDING"
        
        return ApprovalResult(
            success=True,
            action="REDUCE",
            pending_id=pending_id,
            message=f"Size reduced from ${previous_size:.0f} to ${new_size_usd:.0f}",
        )
    
    # ═══════════════════════════════════════════════════════════
    # 6. Override Execution
    # ═══════════════════════════════════════════════════════════
    
    def override_execution(
        self,
        pending_id: str,
        size_override: Optional[float] = None,
        order_type_override: Optional[str] = None,
        limit_price_override: Optional[float] = None,
        user: str = "operator",
        note: Optional[str] = None,
    ) -> ApprovalResult:
        """
        Override params of pending execution.
        
        Can modify size, order type, price.
        """
        pending = self._pending.get(pending_id)
        
        if not pending:
            return ApprovalResult(
                success=False,
                action="OVERRIDE",
                pending_id=pending_id,
                message=f"Pending execution {pending_id} not found",
            )
        
        if pending.status not in ["PENDING", "MODIFIED"]:
            return ApprovalResult(
                success=False,
                action="OVERRIDE",
                pending_id=pending_id,
                message=f"Pending execution already processed: {pending.status}",
            )
        
        # Store previous values
        previous_values = {
            "size_usd": pending.size_usd,
            "order_type": pending.order_type,
            "limit_price": pending.limit_price,
        }
        
        # Apply overrides
        changes = []
        
        if size_override is not None and size_override > 0:
            pending.size_usd = size_override
            current_price = self._get_current_price(pending.symbol)
            pending.size_base = size_override / current_price if current_price > 0 else 0
            changes.append(f"size: ${previous_values['size_usd']:.0f} → ${size_override:.0f}")
        
        if order_type_override:
            pending.order_type = order_type_override.upper()
            changes.append(f"type: {previous_values['order_type']} → {order_type_override.upper()}")
        
        if limit_price_override is not None:
            pending.limit_price = limit_price_override
            changes.append(f"limit: {previous_values['limit_price']} → {limit_price_override}")
        
        if not changes:
            return ApprovalResult(
                success=False,
                action="OVERRIDE",
                pending_id=pending_id,
                message="No changes specified",
            )
        
        # Recalculate risk if size changed
        if size_override:
            pending.position_risk = self._calculate_position_risk(size_override, pending.symbol)
            pending.portfolio_risk_after = self._estimate_portfolio_risk_after(
                pending.symbol, pending.side, size_override
            )
        
        # Mark as modified
        pending.status = "PENDING"  # Reset to pending after modification
        
        # Log
        self._log_action(
            action="OVERRIDE",
            action_type="APPROVAL",
            symbol=pending.symbol,
            pending_id=pending_id,
            previous_value=previous_values,
            new_value={
                "size_usd": pending.size_usd,
                "order_type": pending.order_type,
                "limit_price": pending.limit_price,
            },
            user=user,
        )
        
        return ApprovalResult(
            success=True,
            action="OVERRIDE",
            pending_id=pending_id,
            message=f"Modified: {', '.join(changes)}",
        )
    
    # ═══════════════════════════════════════════════════════════
    # 7. Helper Methods
    # ═══════════════════════════════════════════════════════════
    
    def _clean_expired(self):
        """Clean expired pending executions."""
        now = datetime.now(timezone.utc)
        expired = []
        
        for pending_id, pending in self._pending.items():
            if pending.status == "PENDING" and pending.expires_at and now > pending.expires_at:
                pending.status = "EXPIRED"
                expired.append(pending_id)
        
        for pending_id in expired:
            pending = self._pending.pop(pending_id)
            self._history.append(pending)
            
            self._log_action(
                action="EXPIRED",
                action_type="SYSTEM",
                symbol=pending.symbol,
                pending_id=pending_id,
            )
    
    def _get_current_price(self, symbol: str) -> float:
        """Get current price for symbol."""
        defaults = {
            "BTC": 45000.0,
            "ETH": 2500.0,
            "SOL": 100.0,
            "AVAX": 35.0,
        }
        return defaults.get(symbol.upper(), 100.0)
    
    def _calculate_position_risk(self, size_usd: float, symbol: str) -> float:
        """Calculate position risk contribution."""
        try:
            from modules.risk_budget import get_risk_budget_engine
            engine = get_risk_budget_engine()
            
            result = engine.calculate_risk_contribution(
                symbol=symbol,
                strategy="MANUAL",
                position_size_usd=size_usd,
            )
            return result.risk_contribution
        except Exception:
            # Estimate based on size
            return size_usd / 1000000 * 0.05  # Rough 5% per 100%
    
    def _estimate_portfolio_risk_after(self, symbol: str, side: str, size_usd: float) -> float:
        """Estimate portfolio risk after adding position."""
        try:
            from modules.risk_budget import get_risk_budget_engine
            engine = get_risk_budget_engine()
            
            current = engine.get_portfolio_risk_budget()
            position_risk = self._calculate_position_risk(size_usd, symbol)
            
            return current.total_risk + position_risk
        except Exception:
            return 0.05
    
    def _generate_recommendation(
        self,
        symbol: str,
        side: str,
        size_usd: float,
        confidence: float,
        reliability: float,
        impact_state: str,
        portfolio_risk_after: float,
    ) -> tuple:
        """Generate system recommendation."""
        # Risk threshold
        if portfolio_risk_after > 0.20:
            return "REJECT", "Portfolio risk would exceed 20% limit"
        
        if portfolio_risk_after > 0.18:
            return "REDUCE", f"Portfolio risk ({portfolio_risk_after*100:.1f}%) approaching limit"
        
        # Impact
        if impact_state == "CRITICAL":
            return "REJECT", "Liquidity impact too high"
        
        if impact_state == "HIGH":
            return "REDUCE", "High liquidity impact - consider smaller size"
        
        # Confidence
        if confidence < 0.5:
            return "REDUCE", f"Low confidence ({confidence*100:.0f}%)"
        
        if reliability < 0.5:
            return "REDUCE", f"Low reliability ({reliability*100:.0f}%)"
        
        return "APPROVE", "All checks passed"
    
    def _log_action(
        self,
        action: str,
        action_type: str,
        symbol: Optional[str] = None,
        pending_id: Optional[str] = None,
        order_id: Optional[str] = None,
        previous_size: Optional[float] = None,
        new_size: Optional[float] = None,
        previous_value: Optional[Dict] = None,
        new_value: Optional[Dict] = None,
        user: str = "system",
    ):
        """Log action to audit trail."""
        log = DashboardAuditLog(
            action=action,
            action_type=action_type,
            symbol=symbol,
            pending_id=pending_id,
            order_id=order_id,
            previous_size=previous_size,
            new_size=new_size,
            previous_value=previous_value,
            new_value=new_value,
            user=user,
        )
        self._audit_log.append(log)
        
        # Keep last 1000 entries
        if len(self._audit_log) > 1000:
            self._audit_log = self._audit_log[-1000:]
    
    def get_audit_log(self, limit: int = 100) -> List[DashboardAuditLog]:
        """Get audit log."""
        return self._audit_log[-limit:]
    
    def get_history(self, limit: int = 100) -> List[PendingExecution]:
        """Get processed executions history."""
        return self._history[-limit:]


# ══════════════════════════════════════════════════════════════
# Singleton
# ══════════════════════════════════════════════════════════════

_approval_engine: Optional[ApprovalQueueEngine] = None


def get_approval_engine() -> ApprovalQueueEngine:
    """Get singleton instance."""
    global _approval_engine
    if _approval_engine is None:
        _approval_engine = ApprovalQueueEngine()
    return _approval_engine
