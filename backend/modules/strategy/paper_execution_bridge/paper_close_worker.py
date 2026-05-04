"""
Paper Close Worker
==================

Phase 3.0A: Background worker to close paper positions after 24h.

Features:
  - Idempotent (only closes OPEN positions)
  - Fail-safe (skips if price invalid)
  - Audit trail logging
  - 60s interval
"""

import logging
import asyncio
from typing import Dict, Any
from datetime import datetime, timezone
from motor.motor_asyncio import AsyncIOMotorDatabase

from .paper_position_repository import PaperPositionRepository
from .config import PaperPositionStatus

logger = logging.getLogger(__name__)


class PaperCloseWorker:
    """
    Background worker to close paper positions.
    
    Logic:
      1. Find positions where close_after <= now AND status = OPEN
      2. Get live price
      3. Calculate PnL
      4. Update position status to CLOSED
      5. Log audit trail
    """
    
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.position_repo = PaperPositionRepository(db)
        self._running = False
    
    async def run_once(self, experiment_id: str = "market_dynamic"):
        """
        Run one cycle of closing positions.
        
        Args:
            experiment_id: Experiment ID
        """
        now = datetime.now(timezone.utc)
        positions = await self.position_repo.get_positions_to_close(experiment_id)
        
        if not positions:
            return
        
        logger.info(f"[PaperCloseWorker] Found {len(positions)} positions to close")
        
        for pos in positions:
            # Double-check status (idempotency)
            if pos.get("status") != PaperPositionStatus.OPEN:
                continue
            
            symbol = pos["symbol"]
            
            # Get live price
            exit_price = await self._get_live_price(symbol)
            
            if exit_price is None or exit_price <= 0.0001:
                logger.error(
                    f"[PaperCloseWorker] Skipping {symbol}: invalid price {exit_price}"
                )
                continue
            
            # Calculate PnL
            entry_price = pos["entry_price"]
            side = pos["side"]
            size_usd = pos["size_usd"]
            
            if side == "LONG":
                pnl_pct = (exit_price - entry_price) / entry_price
            else:  # SHORT
                pnl_pct = (entry_price - exit_price) / entry_price
            
            pnl_usd = pnl_pct * size_usd
            
            # Close position
            await self.position_repo.close_position(
                position_id=str(pos["_id"]),
                exit_price=exit_price,
                exit_time=now
            )
            
            logger.info(
                f"[PaperCloseWorker] Closed: {symbol} {side} "
                f"entry=${entry_price:.2f} exit=${exit_price:.2f} "
                f"pnl={pnl_pct:.2%} (${pnl_usd:.2f})"
            )
    
    async def loop_forever(
        self,
        experiment_id: str = "market_dynamic",
        sleep_seconds: int = 60
    ):
        """
        Run worker in infinite loop.
        
        Args:
            experiment_id: Experiment ID
            sleep_seconds: Sleep interval between cycles
        """
        self._running = True
        logger.info(f"[PaperCloseWorker] Started (interval={sleep_seconds}s)")
        
        while self._running:
            try:
                await self.run_once(experiment_id=experiment_id)
            except Exception as e:
                logger.error(f"[PaperCloseWorker] Error: {e}")
                import traceback
                traceback.print_exc()
            
            await asyncio.sleep(sleep_seconds)
    
    def stop(self):
        """Stop worker loop."""
        self._running = False
        logger.info("[PaperCloseWorker] Stopped")
    
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
            
            logger.warning(f"[PaperCloseWorker] No market data for {symbol}")
            return 0.0
        
        except Exception as e:
            logger.error(f"[PaperCloseWorker] Failed to get price for {symbol}: {e}")
            return 0.0


# Global singleton
_paper_close_worker = None


def get_paper_close_worker(db: AsyncIOMotorDatabase) -> PaperCloseWorker:
    """Get or create paper close worker."""
    global _paper_close_worker
    if _paper_close_worker is None:
        _paper_close_worker = PaperCloseWorker(db)
    return _paper_close_worker
