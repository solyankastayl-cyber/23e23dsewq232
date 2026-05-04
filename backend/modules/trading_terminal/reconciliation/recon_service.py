"""
State Reconciliation Layer - Core Service
Main reconciliation logic: compare internal state with exchange state.
"""

import secrets
from typing import List, Optional, Dict, Tuple
from datetime import datetime, timedelta

from .recon_types import (
    ReconciliationRun,
    ReconciliationResult,
    ReconciliationMismatch,
    ReconciliationStatus,
    ReconciliationRequest,
    ReconciliationSummary,
    MismatchType,
    MismatchSeverity,
    ReconciliationAction,
    ExchangeState,
    ExchangePosition,
    ExchangeOrder,
    InternalState,
    InternalPosition,
    InternalOrder
)
from .recon_repository import get_recon_repository, ReconciliationRepository
from .exchange_adapter import get_exchange_adapter, ExchangeAdapter


class ReconciliationService:
    """
    Core reconciliation service.
    
    Compares internal state (positions, orders) with exchange state
    and identifies mismatches.
    
    Features:
    - Position reconciliation (ghost positions, size mismatches)
    - Order reconciliation (ghost orders, status mismatches)
    - Balance reconciliation (drift detection)
    - Quarantine mechanism for problematic exchanges
    - Auto-fix capabilities (optional)
    """
    
    # Thresholds
    POSITION_SIZE_TOLERANCE = 0.0001  # Acceptable size difference
    BALANCE_DRIFT_TOLERANCE = 1.0     # Acceptable balance difference in USDT
    PRICE_TOLERANCE_PERCENT = 0.5     # Acceptable price difference %
    
    def __init__(self):
        """Initialize reconciliation service"""
        self._repo: ReconciliationRepository = get_recon_repository()
        self._adapter: ExchangeAdapter = get_exchange_adapter()
        
        # Track active reconciliation
        self._current_run: Optional[ReconciliationRun] = None
    
    async def run_reconciliation(
        self,
        request: ReconciliationRequest
    ) -> ReconciliationRun:
        """
        Run a full reconciliation across exchanges.
        
        Args:
            request: Configuration for this reconciliation run
        
        Returns:
            ReconciliationRun with results and any mismatches
        """
        # Determine which exchanges to check
        exchanges = request.exchanges or self._adapter.get_supported_exchanges()
        
        # Filter out quarantined exchanges (unless explicitly requested)
        if not request.exchanges:
            quarantined = [q["exchange"] for q in self._repo.get_quarantined_exchanges()]
            exchanges = [e for e in exchanges if e not in quarantined]
        
        # Create run record
        run = ReconciliationRun(
            run_id=self._generate_run_id(),
            status=ReconciliationStatus.RUNNING,
            exchanges=exchanges,
            trigger=request.trigger,
            triggered_by=None
        )
        
        self._current_run = run
        self._repo.save_run(run)
        
        # Process each exchange
        results = []
        all_mismatches = []
        
        for exchange in exchanges:
            result = await self._reconcile_exchange(
                exchange,
                check_positions=request.check_positions,
                check_orders=request.check_orders,
                check_balances=request.check_balances
            )
            results.append(result)
            all_mismatches.extend(result.mismatches)
            
            # Quarantine if critical issues found
            if result.critical_count >= 2:
                self._repo.quarantine_exchange(
                    exchange,
                    reason=f"Critical mismatches detected: {result.critical_count}",
                    run_id=run.run_id
                )
                run.quarantined_exchanges.append(exchange)
        
        # Save mismatches
        self._repo.save_mismatches_batch(all_mismatches)
        
        # Update run with results
        run.results = results
        run.status = self._determine_run_status(results)
        run.total_mismatches = sum(r.mismatch_count for r in results)
        run.total_critical = sum(r.critical_count for r in results)
        run.completed_at = datetime.utcnow()
        run.duration_ms = int((run.completed_at - run.started_at).total_seconds() * 1000)
        
        self._repo.save_run(run)
        self._current_run = None
        
        return run
    
    async def _reconcile_exchange(
        self,
        exchange: str,
        check_positions: bool = True,
        check_orders: bool = True,
        check_balances: bool = True
    ) -> ReconciliationResult:
        """Reconcile a single exchange"""
        started_at = datetime.utcnow()
        mismatches: List[ReconciliationMismatch] = []
        
        try:
            # Fetch exchange state
            exchange_state = await self._adapter.fetch_exchange_state(exchange)
            
            # Fetch internal state
            internal_state = await self._get_internal_state(exchange)
            
            # Compare positions
            positions_checked = 0
            if check_positions:
                position_mismatches, positions_checked = self._compare_positions(
                    exchange,
                    internal_state.positions,
                    exchange_state.positions
                )
                mismatches.extend(position_mismatches)
            
            # Compare orders
            orders_checked = 0
            if check_orders:
                order_mismatches, orders_checked = self._compare_orders(
                    exchange,
                    internal_state.orders,
                    exchange_state.orders
                )
                mismatches.extend(order_mismatches)
            
            # Check balances
            balances_checked = 0
            if check_balances:
                balance_mismatches, balances_checked = self._check_balances(
                    exchange,
                    exchange_state.balances
                )
                mismatches.extend(balance_mismatches)
            
            completed_at = datetime.utcnow()
            
            return ReconciliationResult(
                exchange=exchange,
                status=ReconciliationStatus.COMPLETED,
                positions_checked=positions_checked,
                orders_checked=orders_checked,
                balances_checked=balances_checked,
                mismatches=mismatches,
                mismatch_count=len(mismatches),
                critical_count=len([m for m in mismatches if m.severity == MismatchSeverity.CRITICAL]),
                started_at=started_at,
                completed_at=completed_at,
                duration_ms=int((completed_at - started_at).total_seconds() * 1000)
            )
            
        except Exception as e:
            return ReconciliationResult(
                exchange=exchange,
                status=ReconciliationStatus.FAILED,
                started_at=started_at,
                completed_at=datetime.utcnow(),
                error=str(e)
            )
    
    async def _get_internal_state(self, exchange: str) -> InternalState:
        """
        Get internal state for an exchange.
        
        In production, this would query:
        - positions table
        - orders table
        
        Currently returns mock data matching exchange mock.
        """
        # Mock internal state
        # In production, query actual database
        return InternalState(
            positions=[],
            orders=[]
        )
    
    def _compare_positions(
        self,
        exchange: str,
        internal_positions: List[InternalPosition],
        exchange_positions: List[ExchangePosition]
    ) -> Tuple[List[ReconciliationMismatch], int]:
        """Compare internal positions with exchange positions"""
        mismatches = []
        
        # Build lookup maps
        internal_by_symbol = {p.symbol: p for p in internal_positions}
        exchange_by_symbol = {p.symbol: p for p in exchange_positions}
        
        all_symbols = set(internal_by_symbol.keys()) | set(exchange_by_symbol.keys())
        
        for symbol in all_symbols:
            internal_pos = internal_by_symbol.get(symbol)
            exchange_pos = exchange_by_symbol.get(symbol)
            
            if internal_pos and not exchange_pos:
                # Ghost position: we think we have it, exchange doesn't
                mismatches.append(ReconciliationMismatch(
                    mismatch_id=self._generate_mismatch_id(),
                    mismatch_type=MismatchType.GHOST_POSITION,
                    severity=MismatchSeverity.CRITICAL,
                    exchange=exchange,
                    symbol=symbol,
                    internal_value={
                        "side": internal_pos.side,
                        "size": internal_pos.size,
                        "entry_price": internal_pos.entry_price
                    },
                    exchange_value=None,
                    description=f"Ghost position: {symbol} exists internally but not on exchange",
                    action_taken=ReconciliationAction.ALERT_SENT
                ))
            
            elif exchange_pos and not internal_pos:
                # Missing position: exchange has it, we don't know about it
                mismatches.append(ReconciliationMismatch(
                    mismatch_id=self._generate_mismatch_id(),
                    mismatch_type=MismatchType.MISSING_POSITION,
                    severity=MismatchSeverity.HIGH,
                    exchange=exchange,
                    symbol=symbol,
                    internal_value=None,
                    exchange_value={
                        "side": exchange_pos.side,
                        "size": exchange_pos.size,
                        "entry_price": exchange_pos.entry_price
                    },
                    description=f"Missing position: {symbol} on exchange but not tracked internally",
                    action_taken=ReconciliationAction.MANUAL_REQUIRED
                ))
            
            elif internal_pos and exchange_pos:
                # Both exist, check for mismatches
                if abs(internal_pos.size - exchange_pos.size) > self.POSITION_SIZE_TOLERANCE:
                    mismatches.append(ReconciliationMismatch(
                        mismatch_id=self._generate_mismatch_id(),
                        mismatch_type=MismatchType.POSITION_SIZE_MISMATCH,
                        severity=MismatchSeverity.HIGH,
                        exchange=exchange,
                        symbol=symbol,
                        internal_value={"size": internal_pos.size},
                        exchange_value={"size": exchange_pos.size},
                        description=f"Size mismatch for {symbol}: internal={internal_pos.size}, exchange={exchange_pos.size}",
                        details={"difference": abs(internal_pos.size - exchange_pos.size)}
                    ))
                
                if internal_pos.side != exchange_pos.side:
                    mismatches.append(ReconciliationMismatch(
                        mismatch_id=self._generate_mismatch_id(),
                        mismatch_type=MismatchType.POSITION_SIDE_MISMATCH,
                        severity=MismatchSeverity.CRITICAL,
                        exchange=exchange,
                        symbol=symbol,
                        internal_value={"side": internal_pos.side},
                        exchange_value={"side": exchange_pos.side},
                        description=f"Side mismatch for {symbol}: internal={internal_pos.side}, exchange={exchange_pos.side}"
                    ))
        
        positions_checked = len(all_symbols)
        return mismatches, positions_checked
    
    def _compare_orders(
        self,
        exchange: str,
        internal_orders: List[InternalOrder],
        exchange_orders: List[ExchangeOrder]
    ) -> Tuple[List[ReconciliationMismatch], int]:
        """Compare internal orders with exchange orders"""
        mismatches = []
        
        # Build lookup maps
        internal_by_id = {o.exchange_order_id: o for o in internal_orders if o.exchange_order_id}
        exchange_by_id = {o.order_id: o for o in exchange_orders}
        
        all_ids = set(internal_by_id.keys()) | set(exchange_by_id.keys())
        
        for order_id in all_ids:
            internal_ord = internal_by_id.get(order_id)
            exchange_ord = exchange_by_id.get(order_id)
            
            if internal_ord and not exchange_ord:
                # Ghost order
                mismatches.append(ReconciliationMismatch(
                    mismatch_id=self._generate_mismatch_id(),
                    mismatch_type=MismatchType.GHOST_ORDER,
                    severity=MismatchSeverity.HIGH,
                    exchange=exchange,
                    symbol=internal_ord.symbol,
                    internal_value={
                        "order_id": order_id,
                        "symbol": internal_ord.symbol,
                        "status": internal_ord.status
                    },
                    exchange_value=None,
                    description=f"Ghost order: {order_id} exists internally but not on exchange"
                ))
            
            elif exchange_ord and not internal_ord:
                # Missing order (exchange has order we don't know about)
                # This might be normal for orders created outside our system
                mismatches.append(ReconciliationMismatch(
                    mismatch_id=self._generate_mismatch_id(),
                    mismatch_type=MismatchType.MISSING_ORDER,
                    severity=MismatchSeverity.MEDIUM,
                    exchange=exchange,
                    symbol=exchange_ord.symbol,
                    internal_value=None,
                    exchange_value={
                        "order_id": order_id,
                        "symbol": exchange_ord.symbol,
                        "status": exchange_ord.status
                    },
                    description=f"Untracked order: {order_id} on exchange but not in internal system"
                ))
        
        orders_checked = len(all_ids)
        return mismatches, orders_checked
    
    def _check_balances(
        self,
        exchange: str,
        balances: List
    ) -> Tuple[List[ReconciliationMismatch], int]:
        """Check for balance anomalies"""
        mismatches = []
        
        # In production, would compare with expected balances
        # For now, just check for negative balances or anomalies
        
        for balance in balances:
            if balance.free < 0 or balance.locked < 0:
                mismatches.append(ReconciliationMismatch(
                    mismatch_id=self._generate_mismatch_id(),
                    mismatch_type=MismatchType.BALANCE_DRIFT,
                    severity=MismatchSeverity.CRITICAL,
                    exchange=exchange,
                    symbol=balance.asset,
                    internal_value=None,
                    exchange_value={
                        "asset": balance.asset,
                        "free": balance.free,
                        "locked": balance.locked
                    },
                    description=f"Negative balance detected for {balance.asset}"
                ))
        
        return mismatches, len(balances)
    
    def _determine_run_status(self, results: List[ReconciliationResult]) -> ReconciliationStatus:
        """Determine overall run status from results"""
        if not results:
            return ReconciliationStatus.FAILED
        
        failed = len([r for r in results if r.status == ReconciliationStatus.FAILED])
        
        if failed == len(results):
            return ReconciliationStatus.FAILED
        elif failed > 0:
            return ReconciliationStatus.PARTIAL
        else:
            return ReconciliationStatus.COMPLETED
    
    # ===========================================
    # Query Methods
    # ===========================================
    
    def get_run(self, run_id: str) -> Optional[ReconciliationRun]:
        """Get a specific run"""
        return self._repo.get_run(run_id)
    
    def get_recent_runs(self, limit: int = 20) -> List[ReconciliationRun]:
        """Get recent reconciliation runs"""
        return self._repo.get_recent_runs(limit=limit)
    
    def get_unresolved_mismatches(
        self,
        exchange: Optional[str] = None,
        severity: Optional[MismatchSeverity] = None
    ) -> List[ReconciliationMismatch]:
        """Get unresolved mismatches"""
        return self._repo.get_unresolved_mismatches(
            exchange=exchange,
            severity=severity
        )
    
    def resolve_mismatch(
        self,
        mismatch_id: str,
        notes: Optional[str] = None
    ) -> Optional[ReconciliationMismatch]:
        """Mark a mismatch as resolved"""
        return self._repo.resolve_mismatch(mismatch_id, notes)
    
    def get_summary(self) -> ReconciliationSummary:
        """Get reconciliation summary"""
        last_run = self._repo.get_last_run()
        
        # Get stats for last 24 hours
        since_24h = datetime.utcnow() - timedelta(hours=24)
        
        # Get quarantined exchanges
        quarantined = [q["exchange"] for q in self._repo.get_quarantined_exchanges()]
        
        # Determine which exchanges are in sync
        all_exchanges = self._adapter.get_supported_exchanges()
        in_sync = [e for e in all_exchanges if e not in quarantined]
        
        # Check for exchanges with unresolved issues
        with_issues = set()
        for mismatch in self._repo.get_unresolved_mismatches():
            with_issues.add(mismatch.exchange)
        
        return ReconciliationSummary(
            last_run=last_run.started_at if last_run else None,
            last_status=last_run.status if last_run else None,
            total_runs_24h=self._repo.count_runs_since(since_24h),
            total_mismatches_24h=self._repo.count_mismatches_since(since_24h),
            exchanges_in_sync=[e for e in in_sync if e not in with_issues],
            exchanges_with_issues=list(with_issues),
            quarantined_exchanges=quarantined
        )
    
    # ===========================================
    # Quarantine Management
    # ===========================================
    
    def quarantine_exchange(self, exchange: str, reason: str) -> dict:
        """Manually quarantine an exchange"""
        return self._repo.quarantine_exchange(exchange, reason)
    
    def release_exchange(self, exchange: str) -> bool:
        """Release an exchange from quarantine"""
        return self._repo.release_from_quarantine(exchange)
    
    def get_quarantined_exchanges(self) -> List[dict]:
        """Get list of quarantined exchanges"""
        return self._repo.get_quarantined_exchanges()
    
    # ===========================================
    # Health
    # ===========================================
    
    def get_health(self) -> dict:
        """Get service health status"""
        last_run = self._repo.get_last_run()
        
        return {
            "status": "healthy",
            "version": "recon_v1",
            "last_run": last_run.started_at.isoformat() if last_run else None,
            "next_scheduled_run": None,  # Would be set by scheduler
            "active_exchanges": len(self._adapter.get_supported_exchanges()),
            "quarantined_exchanges": self._repo.count_quarantined(),
            "mismatches_unresolved": self._repo.count_unresolved_mismatches(),
            "timestamp": datetime.utcnow().isoformat()
        }
    
    # ===========================================
    # Helpers
    # ===========================================
    
    def _generate_run_id(self) -> str:
        """Generate unique run ID"""
        return f"recon_{secrets.token_hex(8)}"
    
    def _generate_mismatch_id(self) -> str:
        """Generate unique mismatch ID"""
        return f"mm_{secrets.token_hex(8)}"


# Singleton instance
_service_instance = None

def get_recon_service() -> ReconciliationService:
    """Get singleton ReconciliationService instance"""
    global _service_instance
    if _service_instance is None:
        _service_instance = ReconciliationService()
    return _service_instance
