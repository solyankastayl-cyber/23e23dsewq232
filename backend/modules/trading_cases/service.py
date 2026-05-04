"""
TradingCase Service

Core logic for managing trading cases lifecycle.
Links Exchange ↔ Cases ↔ Portfolio.
"""

import uuid
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
import logging

from .models import TradingCase, CaseCreateRequest, CaseUpdateRequest, CaseCloseRequest
from .repository import TradingCaseRepository, get_repository

logger = logging.getLogger(__name__)


class TradingCaseService:
    """Service for managing trading case lifecycle."""
    
    def __init__(self, exchange_service, repository: Optional[TradingCaseRepository] = None):
        """
        Initialize TradingCaseService.
        
        Args:
            exchange_service: Exchange service instance (from service_v2)
            repository: TradingCaseRepository instance (optional, uses singleton if not provided)
        """
        self.exchange = exchange_service
        self.repo = repository or get_repository()
    
    # =========================
    # CREATE CASE
    # =========================
    
    async def create_case(self, request: CaseCreateRequest) -> TradingCase:
        """
        Create a new trading case.
        
        This is the entry point for all new trading decisions.
        """
        case_id = f"case-{uuid.uuid4().hex[:12]}"
        
        case = TradingCase(
            case_id=case_id,
            symbol=request.symbol,
            exchange=self.exchange.get_mode() or "paper",
            
            side=request.side,
            status="ACTIVE",
            
            strategy=request.strategy,
            trading_tf=request.trading_tf,
            
            entry_price=request.entry_price,
            avg_entry_price=request.entry_price,
            current_price=request.entry_price,
            
            qty=request.qty,
            size_usd=request.size_usd,
            
            stop_price=request.stop_price,
            target_price=request.target_price,
            
            realized_pnl=0.0,
            unrealized_pnl=0.0,
            unrealized_pnl_pct=0.0,
            
            trade_count=0,
            
            opened_at=datetime.now(timezone.utc),
            closed_at=None,
            
            thesis=request.thesis,
            thesis_history=[],
            switch_reason=None,
            
            fills=[],
            order_ids=[],
            
            decision_id=request.decision_id,
            experiment_id=request.experiment_id,  # STEP 1.5.4: Pass experiment_id from request
        )
        
        self.repo.save(case)
        
        logger.info(f"[TradingCaseService] Created case {case_id}: {request.symbol} {request.side} @ ${request.entry_price}")
        
        return case
    
    # =========================
    # UPDATE CASE
    # =========================
    
    async def update_case(self, case_id: str, update: CaseUpdateRequest) -> TradingCase:
        """Update a trading case."""
        case = self.repo.get(case_id)
        
        if not case:
            raise ValueError(f"Case {case_id} not found")
        
        # Update current price
        if update.current_price:
            case.current_price = update.current_price
            
            # Recalculate unrealized PnL
            if case.side == "LONG":
                case.unrealized_pnl = (case.current_price - case.avg_entry_price) * case.qty
            else:  # SHORT
                case.unrealized_pnl = (case.avg_entry_price - case.current_price) * case.qty
            
            # Calculate unrealized PnL %
            if case.avg_entry_price > 0:
                case.unrealized_pnl_pct = (case.unrealized_pnl / case.size_usd) * 100
        
        # Update thesis
        if update.thesis and update.thesis != case.thesis:
            case.thesis_history.append({
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "old_thesis": case.thesis,
                "new_thesis": update.thesis,
            })
            case.thesis = update.thesis
        
        # Update stop/target
        if update.stop_price:
            case.stop_price = update.stop_price
        
        if update.target_price:
            case.target_price = update.target_price
        
        self.repo.save(case)
        
        return case
    
    # =========================
    # CLOSE CASE
    # =========================
    
    async def close_case(self, case_id: str, close_request: CaseCloseRequest) -> TradingCase:
        """Close a trading case."""
        case = self.repo.get(case_id)
        
        if not case:
            raise ValueError(f"Case {case_id} not found")
        
        case.status = "CLOSED"
        case.closed_at = datetime.now(timezone.utc)
        case.current_price = close_request.close_price
        
        # Final PnL calculation
        if case.side == "LONG":
            final_pnl = (close_request.close_price - case.avg_entry_price) * case.qty
        else:  # SHORT
            final_pnl = (case.avg_entry_price - close_request.close_price) * case.qty
        
        case.realized_pnl = final_pnl
        case.unrealized_pnl = 0.0

        # ── Risk Guard: PnL Sanity Check (Close Integrity) ──
        try:
            from modules.risk_guard import get_risk_guard
            guard = get_risk_guard()
            if guard:
                verified = guard.verify_close_pnl(
                    symbol=case.symbol,
                    side=case.side,
                    entry_price=case.avg_entry_price,
                    exit_price=close_request.close_price,
                    qty=case.qty,
                    stored_pnl=final_pnl,
                )
                if not verified:
                    logger.error(
                        f"[TradingCaseService] PNL MISMATCH on close for case {case_id}! "
                        f"Proceeding with calculated value."
                    )
        except Exception as e:
            logger.error(f"[TradingCaseService] RiskGuard PnL check failed: {e}")

        self.repo.save(case)
        
        logger.info(f"[TradingCaseService] Closed case {case_id}: {close_request.close_reason}, PnL=${final_pnl:.2f}")
        
        # Paper Trading: Write Outcome (CHECK 2, 3, 4)
        await self._write_decision_outcome(case, close_request.close_price)
        
        return case
    
    async def _write_decision_outcome(self, case: TradingCase, close_price: float):
        """
        Write decision outcome to decision_outcomes collection.
        
        Paper Trading Integration: Links Position → Outcome → Analytics
        
        Guarantees:
        - 1 position = 1 outcome (idempotent via upsert)
        - Outcome linked to decision_id and case_id
        - Analytics can read outcome
        """
        if not case.decision_id:
            logger.warning(f"[TradingCaseService] Case {case.case_id} has no decision_id, skipping outcome")
            return
        
        try:
            # Get MongoDB from repository
            db = self.repo.db
            if db is None:
                logger.error("[TradingCaseService] No MongoDB connection for outcome writing")
                return
            
            # Calculate PnL percentage
            if case.avg_entry_price > 0:
                if case.side == "LONG":
                    pnl_pct = ((close_price - case.avg_entry_price) / case.avg_entry_price) * 100
                else:  # SHORT
                    pnl_pct = ((case.avg_entry_price - close_price) / case.avg_entry_price) * 100
            else:
                pnl_pct = 0.0
            
            # Determine win/loss
            is_win = case.realized_pnl > 0
            
            # Create outcome document
            outcome = {
                "decision_id": case.decision_id,
                "case_id": case.case_id,
                "experiment_id": case.experiment_id,  # STEP 1.5.5: Pass experiment_id from case
                "symbol": case.symbol,
                "side": case.side,
                "strategy": case.strategy,
                "entry_price": case.avg_entry_price,
                "exit_price": close_price,
                "signal_price": case.signal_price if hasattr(case, 'signal_price') else 0,
                "qty": case.qty,
                "pnl_usd": case.realized_pnl,
                "pnl_pct": pnl_pct,
                "is_win": is_win,
                "opened_at": case.opened_at.isoformat() if case.opened_at else None,
                "closed_at": case.closed_at.isoformat() if case.closed_at else None,
                "created_at": datetime.now(timezone.utc).isoformat()
            }
            
            # Upsert (prevent duplicates)
            collection = db["decision_outcomes"]
            result = collection.replace_one(
                {"case_id": case.case_id},
                outcome,
                upsert=True
            )
            
            logger.info(
                f"✅ [TradingCaseService] Outcome written: "
                f"decision_id={case.decision_id}, case_id={case.case_id}, "
                f"pnl=${case.realized_pnl:.2f} ({pnl_pct:+.2f}%), "
                f"win={is_win}"
            )
            
        except Exception as e:
            logger.error(
                f"❌ [TradingCaseService] Failed to write outcome for case {case.case_id}: {e}",
                exc_info=True
            )
    
    # =========================
    # EXECUTE ORDER
    # =========================
    
    async def execute_order(self, case_id: str, order_request: Dict[str, Any]) -> Any:
        """
        Execute an order for a case.
        
        Links case → exchange → fills.
        """
        case = self.repo.get(case_id)
        
        if not case:
            raise ValueError(f"Case {case_id} not found")
        
        # Get exchange adapter
        if not self.exchange.is_connected():
            raise RuntimeError("Exchange not connected")
        
        adapter = self.exchange.get_adapter()
        
        # Place order
        order = await adapter.place_order(order_request)
        
        # Track order ID in case
        case.order_ids.append(order.order_id)
        self.repo.save(case)
        
        logger.info(f"[TradingCaseService] Executed order {order.order_id} for case {case_id}")
        
        return order
    
    # =========================
    # SYNC FROM EXCHANGE
    # =========================
    
    async def sync_positions(self):
        """
        Sync positions from exchange to cases.
        
        Updates current_price and unrealized_pnl.
        """
        if not self.exchange.is_connected():
            logger.warning("[TradingCaseService] Exchange not connected, skipping sync")
            return
        
        adapter = self.exchange.get_adapter()
        
        # CRITICAL: Trigger exchange state sync first (updates mark prices, PnL)
        await adapter.sync_state()
        
        # Get all positions from exchange
        positions = await adapter.get_positions()
        
        # Get all active cases
        active_cases = self.repo.get_active()
        
        # Match positions to cases
        for case in active_cases:
            for pos in positions:
                if pos.symbol == case.symbol and pos.side == case.side:
                    # Update case from position
                    case.current_price = pos.mark_price
                    case.unrealized_pnl = pos.unrealized_pnl
                    case.unrealized_pnl_pct = pos.unrealized_pnl_pct
                    case.qty = pos.qty
                    
                    self.repo.save(case)
                    
                    logger.debug(f"[TradingCaseService] Synced case {case.case_id}: price=${pos.mark_price}, pnl=${pos.unrealized_pnl}")
    
    # =========================
    # GETTERS
    # =========================
    
    def get_cases(self, experiment_id: Optional[str] = None) -> List[TradingCase]:
        """
        Get all cases.
        
        Args:
            experiment_id: Optional filter by experiment (None = no filter)
        """
        return self.repo.get_all(experiment_id=experiment_id)
    
    def get_active_cases(self, experiment_id: Optional[str] = None) -> List[TradingCase]:
        """
        Get active cases.
        
        Args:
            experiment_id: Optional filter by experiment (None = no filter)
        """
        return self.repo.get_active(experiment_id=experiment_id)
    
    def get_closed_cases(self, experiment_id: Optional[str] = None) -> List[TradingCase]:
        """
        Get closed cases.
        
        Args:
            experiment_id: Optional filter by experiment (None = no filter)
        """
        return self.repo.get_closed(experiment_id=experiment_id)
    
    def get_case(self, case_id: str) -> Optional[TradingCase]:
        """Get case by ID."""
        return self.repo.get(case_id)


# Singleton instance
_service: Optional[TradingCaseService] = None


def init_trading_case_service(exchange_service):
    """
    Initialize trading case service singleton.
    
    Args:
        exchange_service: Exchange service instance (from get_exchange_service())
    """
    global _service
    _service = TradingCaseService(exchange_service)
    logger.info("[TradingCaseService] Initialized")


def get_trading_case_service() -> TradingCaseService:
    """Get trading case service singleton."""
    if _service is None:
        raise RuntimeError("TradingCaseService not initialized. Call init_trading_case_service() first.")
    return _service
