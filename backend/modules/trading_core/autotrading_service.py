"""AutoTrading Service — Week 4 (с Persistence)

Automatic trading loop with:
- Background task (runs every N seconds)
- ON/OFF toggle with MongoDB persistence
- Risk guardrails (heat, drawdown)
- Position close logic (TP/SL)
"""

import asyncio
import logging
from typing import Optional
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


async def get_autotrading_settings(db):
    """Load autotrading settings from MongoDB."""
    row = await db.trading_settings.find_one({"key": "autotrading"})
    if not row:
        # Default settings
        return {"enabled": False, "interval_seconds": 10}
    return row


async def save_autotrading_settings(db, enabled: bool = None, interval_seconds: int = None):
    """Save autotrading settings to MongoDB."""
    update = {}
    if enabled is not None:
        update["enabled"] = enabled
    if interval_seconds is not None:
        update["interval_seconds"] = interval_seconds
    
    await db.trading_settings.update_one(
        {"key": "autotrading"},
        {"$set": update},
        upsert=True
    )


class AutoTradingService:
    """Automatic trading service with background loop and persistence."""
    
    def __init__(self, db):
        self.db = db
        self.enabled = False
        self.interval_seconds = 10  # Default 10 seconds
        self.task: Optional[asyncio.Task] = None
        
        # Risk limits
        self.max_risk_heat = 0.7  # 70% max exposure
        self.max_drawdown_pct = 0.10  # 10% max drawdown
        
        # Stats
        self.last_cycle_at: Optional[datetime] = None
        self.total_cycles = 0
        self.total_errors = 0
    
    async def load_settings(self):
        """Load settings from DB."""
        settings = await get_autotrading_settings(self.db)
        self.enabled = settings.get("enabled", False)
        self.interval_seconds = settings.get("interval_seconds", 10)
        logger.info(f"[AutoTrading] Settings loaded: enabled={self.enabled}, interval={self.interval_seconds}s")
    
    async def start_loop(self):
        """Start background autotrading loop."""
        if self.task is not None:
            logger.warning("[AutoTrading] Loop already running")
            return
        
        # Load settings from DB
        await self.load_settings()
        
        self.task = asyncio.create_task(self._background_loop())
        logger.info(f"[AutoTrading] 🚀 Background loop started (interval={self.interval_seconds}s)")
    
    async def stop_loop(self):
        """Stop background autotrading loop."""
        if self.task is None:
            logger.warning("[AutoTrading] Loop not running")
            return
        
        self.task.cancel()
        try:
            await self.task
        except asyncio.CancelledError:
            pass
        
        self.task = None
        logger.info("[AutoTrading] 🛑 Background loop stopped")
    
    async def toggle(self, enabled: bool):
        """Toggle autotrading ON/OFF (with persistence).
        
        Args:
            enabled: True to enable, False to disable
        """
        self.enabled = enabled
        await save_autotrading_settings(self.db, enabled=enabled)
        logger.info(f"[AutoTrading] {'✅ ENABLED' if enabled else '⏸ DISABLED'} (persisted to DB)")
    
    async def set_interval(self, seconds: int):
        """Set autotrading interval (with persistence).
        
        Args:
            seconds: Interval in seconds
        """
        self.interval_seconds = seconds
        await save_autotrading_settings(self.db, interval_seconds=seconds)
        logger.info(f"[AutoTrading] Interval set to {seconds}s (persisted to DB)")
    
    def get_status(self) -> dict:
        """Get autotrading status."""
        return {
            "enabled": self.enabled,
            "interval_seconds": self.interval_seconds,
            "last_cycle_at": self.last_cycle_at.isoformat() if self.last_cycle_at else None,
            "total_cycles": self.total_cycles,
            "total_errors": self.total_errors,
            "max_risk_heat": self.max_risk_heat,
            "max_drawdown_pct": self.max_drawdown_pct,
        }
    
    async def _background_loop(self):
        """Background loop that runs trading cycles."""
        logger.info("[AutoTrading] 🔄 Loop started")
        
        while True:
            try:
                # Reload settings from DB (for dynamic updates)
                settings = await get_autotrading_settings(self.db)
                self.enabled = settings.get("enabled", False)
                self.interval_seconds = settings.get("interval_seconds", 10)
                
                if self.enabled:
                    logger.info(f"[{datetime.now(timezone.utc)}] ▶️ Trading cycle...")
                    await self._run_cycle_safe()
                else:
                    logger.debug(f"[{datetime.now(timezone.utc)}] ⏸ Autotrading disabled")
                
                # Wait for next cycle
                await asyncio.sleep(self.interval_seconds)
            
            except asyncio.CancelledError:
                logger.info("[AutoTrading] Loop cancelled")
                break
            
            except Exception as e:
                self.total_errors += 1
                logger.error(f"[AutoTrading] Loop error: {e}", exc_info=True)
                # Continue loop even on error
                await asyncio.sleep(5)  # Short sleep on error
    
    async def _run_cycle_safe(self):
        """Run trading cycle with safety checks."""
        from modules.trading_core.portfolio_service import get_portfolio_service
        from modules.trading_core.trading_runtime import run_trading_cycle_v3
        from modules.trading_core.close_service import check_and_close_positions
        
        logger.info(f"[AutoTrading] 🔁 Cycle {self.total_cycles + 1} @ {datetime.now(timezone.utc).isoformat()}")
        
        try:
            # Get portfolio state
            portfolio_service = get_portfolio_service()
            portfolio = await portfolio_service.get_portfolio_state()
            
            # 🛑 RISK HEAT CHECK
            risk_heat = portfolio.get("risk_heat", 0)
            if risk_heat > self.max_risk_heat:
                logger.warning(
                    f"[AutoTrading] ⚠️ Risk heat too high: {risk_heat:.2f} > {self.max_risk_heat} — skipping cycle"
                )
                return
            
            # 🛑 DRAWDOWN CHECK
            balance = portfolio.get("balance", 10000)
            equity = portfolio.get("equity", 10000)
            
            if balance > 0:
                drawdown = (balance - equity) / balance if equity < balance else 0
                
                if drawdown > self.max_drawdown_pct:
                    logger.error(
                        f"[AutoTrading] 🛑 DRAWDOWN LIMIT EXCEEDED: {drawdown:.2%} > {self.max_drawdown_pct:.2%} — DISABLING TRADING"
                    )
                    await self.toggle(False)
                    return
            
            # ✅ STEP 1: Check and close positions (TP/SL)
            closed_count = await check_and_close_positions()
            if closed_count > 0:
                logger.info(f"[AutoTrading] Closed {closed_count} positions (TP/SL hit)")
            
            # ✅ STEP 2: Run trading cycle (new signals → decisions → orders)
            result = await run_trading_cycle_v3()
            
            # Update stats
            self.last_cycle_at = datetime.now(timezone.utc)
            self.total_cycles += 1
            
            logger.info(
                f"[AutoTrading] ✅ Cycle complete: "
                f"signals={result.get('signals_count', 0)}, "
                f"decisions={result.get('decisions_count', 0)}, "
                f"orders_filled={result.get('orders_filled', 0)}"
            )
        
        except Exception as e:
            self.total_errors += 1
            logger.error(f"[AutoTrading] Cycle error: {e}", exc_info=True)


# Global instance
_autotrading_service: Optional[AutoTradingService] = None


def init_autotrading_service(db):
    """Initialize global autotrading service.
    
    Args:
        db: MongoDB database instance
    """
    global _autotrading_service
    _autotrading_service = AutoTradingService(db)
    return _autotrading_service


def get_autotrading_service() -> AutoTradingService:
    """Get global autotrading service instance."""
    if _autotrading_service is None:
        raise ValueError("AutoTrading service not initialized")
    return _autotrading_service
