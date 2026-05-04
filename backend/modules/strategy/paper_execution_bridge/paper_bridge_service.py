"""
Paper Bridge Service
====================

Phase 3.0A: Core bridge logic.

Flow:
  1. Get selected signals from snapshot
  2. Check readiness
  3. Filter by policy
  4. Check duplicates
  5. Check cooldown
  6. Get live price
  7. Create paper_decision
  8. Create paper_position
  9. Log audit trail
"""

import logging
from typing import Dict, Any, List
from datetime import datetime, timezone
from motor.motor_asyncio import AsyncIOMotorDatabase

from .config import PAPER_CONFIG, PaperDecisionStatus
from .paper_decision_repository import PaperDecisionRepository
from .paper_position_repository import PaperPositionRepository
from .paper_execution_policy import PaperExecutionPolicy

logger = logging.getLogger(__name__)


class PaperBridgeService:
    """
    Paper execution bridge.
    
    Orchestrates:
      - Readiness checking
      - Signal filtering
      - Deduplication
      - Position creation
      - Audit trail
    """
    
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.decision_repo = PaperDecisionRepository(db)
        self.position_repo = PaperPositionRepository(db)
        self.policy = PaperExecutionPolicy()
    
    async def run_once(self, experiment_id: str = "market_dynamic") -> Dict[str, Any]:
        """
        Run paper execution bridge once.
        
        Args:
            experiment_id: Experiment ID
        
        Returns:
            {
                "ok": True,
                "readiness_state": "ready",
                "signals_received": 3,
                "signals_filtered": 2,
                "positions_created": 2,
                "positions_skipped": 0,
                "decisions": [...]
            }
        """
        logger.info(f"[PaperBridge] Starting run_once for {experiment_id}")
        
        # Step 1: Get readiness
        readiness = await self._get_readiness(experiment_id)
        readiness_state = readiness.get("state", "blocked")
        readiness_reason = readiness.get("reason", "Unknown")
        
        logger.info(f"[PaperBridge] Readiness: {readiness_state} - {readiness_reason}")
        
        # Step 2: Check if execution allowed
        if not self.policy.can_execute(readiness_state):
            logger.warning(f"[PaperBridge] Execution BLOCKED by readiness: {readiness_state}")
            return {
                "ok": True,
                "readiness_state": readiness_state,
                "readiness_reason": readiness_reason,
                "signals_received": 0,
                "signals_filtered": 0,
                "positions_created": 0,
                "positions_skipped": 0,
                "decisions": []
            }
        
        # Step 3: Get selected signals from latest snapshot
        signals = await self._get_selected_signals(experiment_id)
        signals_received = len(signals)
        
        logger.info(f"[PaperBridge] Received {signals_received} signals")
        
        if signals_received == 0:
            logger.info("[PaperBridge] No signals to execute")
            return {
                "ok": True,
                "readiness_state": readiness_state,
                "readiness_reason": readiness_reason,
                "signals_received": 0,
                "signals_filtered": 0,
                "positions_created": 0,
                "positions_skipped": 0,
                "decisions": []
            }
        
        # Step 4: Count current open positions
        current_open_count = await self.position_repo.count_open_positions(experiment_id)
        
        logger.info(f"[PaperBridge] Current open positions: {current_open_count}")
        
        # Step 5: Filter by policy
        filtered_signals = self.policy.filter_signals(
            signals=signals,
            readiness_state=readiness_state,
            current_open_count=current_open_count
        )
        signals_filtered = len(filtered_signals)
        
        logger.info(f"[PaperBridge] Filtered to {signals_filtered} signals")
        
        # Step 6: Execute each signal
        positions_created = 0
        positions_skipped = 0
        decisions = []
        
        for signal in filtered_signals:
            result = await self._execute_signal(
                experiment_id=experiment_id,
                signal=signal,
                readiness_state=readiness_state,
                readiness_reason=readiness_reason
            )
            
            decisions.append(result)
            
            if result["executed"]:
                positions_created += 1
            else:
                positions_skipped += 1
        
        logger.info(
            f"[PaperBridge] Complete: {positions_created} created, {positions_skipped} skipped"
        )
        
        return {
            "ok": True,
            "readiness_state": readiness_state,
            "readiness_reason": readiness_reason,
            "signals_received": signals_received,
            "signals_filtered": signals_filtered,
            "positions_created": positions_created,
            "positions_skipped": positions_skipped,
            "decisions": decisions
        }
    
    async def _execute_signal(
        self,
        experiment_id: str,
        signal: Dict[str, Any],
        readiness_state: str,
        readiness_reason: str
    ) -> Dict[str, Any]:
        """
        Execute single signal.
        
        Steps:
          1. Check duplicate
          2. Check cooldown
          3. Get live price
          4. Create decision
          5. Create position
        
        Returns:
            {
                "symbol": "BTCUSDT",
                "executed": True,
                "position_id": "...",
                "skip_reason": null
            }
        """
        symbol = signal["symbol"]
        timeframe = signal["timeframe"]
        side = signal["side"]
        snapshot_id = signal.get("snapshot_id", "unknown")
        
        # Check duplicate
        is_duplicate = await self.decision_repo.check_duplicate(
            experiment_id=experiment_id,
            snapshot_id=snapshot_id,
            symbol=symbol,
            timeframe=timeframe
        )
        
        if is_duplicate:
            logger.info(f"[PaperBridge] Skipping {symbol}: duplicate decision")
            return {
                "symbol": symbol,
                "executed": False,
                "position_id": None,
                "skip_reason": "duplicate"
            }
        
        # Check cooldown
        has_open = await self.position_repo.check_open_position(
            experiment_id=experiment_id,
            symbol=symbol,
            cooldown_hours=PAPER_CONFIG["cooldown_hours_per_symbol"]
        )
        
        if has_open:
            logger.info(
                f"[PaperBridge] Skipping {symbol}: cooldown active "
                f"({PAPER_CONFIG['cooldown_hours_per_symbol']}h)"
            )
            return {
                "symbol": symbol,
                "executed": False,
                "position_id": None,
                "skip_reason": f"cooldown_{PAPER_CONFIG['cooldown_hours_per_symbol']}h"
            }
        
        # Get live price
        live_price = await self._get_live_price(symbol)
        
        if live_price is None or live_price <= PAPER_CONFIG["min_price"]:
            logger.error(f"[PaperBridge] Skipping {symbol}: invalid price {live_price}")
            return {
                "symbol": symbol,
                "executed": False,
                "position_id": None,
                "skip_reason": "invalid_price"
            }
        
        # Create decision
        decision_id = await self.decision_repo.create_decision(
            experiment_id=experiment_id,
            snapshot_id=snapshot_id,
            symbol=symbol,
            timeframe=timeframe,
            side=side,
            score=signal.get("score", 0),
            confidence=signal.get("confidence", 0),
            features=signal.get("features", {}),
            readiness_state=readiness_state,
            readiness_reason=readiness_reason
        )
        
        # Create position
        position_id = await self.position_repo.create_position(
            experiment_id=experiment_id,
            paper_decision_id=decision_id,
            snapshot_id=snapshot_id,
            symbol=symbol,
            timeframe=timeframe,
            side=side,
            entry_price=live_price,
            size_usd=PAPER_CONFIG["position_size_usd"]
        )
        
        # Update decision status
        await self.decision_repo.update_status(
            decision_id=decision_id,
            status=PaperDecisionStatus.EXECUTED,
            executed_at=datetime.now(timezone.utc)
        )
        
        logger.info(
            f"[PaperBridge] Executed: {symbol} {side} @ ${live_price:.2f} "
            f"(position_id={position_id})"
        )
        
        return {
            "symbol": symbol,
            "executed": True,
            "position_id": position_id,
            "decision_id": decision_id,
            "entry_price": live_price,
            "skip_reason": None
        }
    
    async def _get_readiness(self, experiment_id: str) -> Dict[str, Any]:
        """Get execution readiness."""
        try:
            from modules.strategy.execution_readiness import get_execution_readiness_service
            
            service = get_execution_readiness_service(self.db)
            result = await service.get_execution_readiness(experiment_id=experiment_id)
            
            return result
        
        except Exception as e:
            logger.error(f"[PaperBridge] Failed to get readiness: {e}")
            return {
                "state": "blocked",
                "reason": f"Readiness check failed: {e}"
            }
    
    async def _get_selected_signals(self, experiment_id: str) -> List[Dict[str, Any]]:
        """Get selected signals from latest snapshot."""
        try:
            # Get latest snapshot
            snapshot = await self.db.market_dynamic_snapshots.find_one(
                {"experiment_id": experiment_id},
                sort=[("created_at", -1)]
            )
            
            if not snapshot:
                logger.warning("[PaperBridge] No snapshot found")
                return []
            
            selected_signals = snapshot.get("selected_signals", [])
            
            # Add snapshot_id to each signal
            snapshot_id = str(snapshot["_id"])
            for signal in selected_signals:
                signal["snapshot_id"] = snapshot_id
            
            return selected_signals
        
        except Exception as e:
            logger.error(f"[PaperBridge] Failed to get signals: {e}")
            return []
    
    async def _get_live_price(self, symbol: str) -> float:
        """Get live market price."""
        try:
            # Get latest price from market_data collection
            data = await self.db.market_data.find_one(
                {"symbol": symbol},
                sort=[("timestamp", -1)]
            )
            
            if data:
                return float(data.get("price", 0))
            
            logger.warning(f"[PaperBridge] No market data for {symbol}")
            return 0.0
        
        except Exception as e:
            logger.error(f"[PaperBridge] Failed to get price for {symbol}: {e}")
            return 0.0


# Global singleton
_paper_bridge_service = None


def get_paper_bridge_service(db: AsyncIOMotorDatabase) -> PaperBridgeService:
    """Get or create paper bridge service."""
    global _paper_bridge_service
    if _paper_bridge_service is None:
        _paper_bridge_service = PaperBridgeService(db)
    return _paper_bridge_service
