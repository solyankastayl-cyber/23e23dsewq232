"""
Runtime Daemon — Sprint 2: Live Auto-Loop

Managed background loop that calls run_once() at configurable intervals.
NOT a dumb while True — it has:
- Controlled start/stop via API
- State tracking (is_running, last_cycle_ts, error_state, cycles_count)
- Error recovery (continues after single-cycle failures)
- Graceful shutdown
"""

import asyncio
import logging
import time
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class RuntimeDaemon:
    """
    Background runtime loop daemon.
    
    Lifecycle:
      POST /api/runtime/daemon/start  → starts background loop
      POST /api/runtime/daemon/stop   → stops gracefully
      GET  /api/runtime/daemon/status  → current state
    """
    
    def __init__(self, runtime_service):
        self.runtime_service = runtime_service
        self._task = None
        self._running = False
        self._cycles_count = 0
        self._last_cycle_at = None
        self._last_error = None
        self._started_at = None
        
        logger.info("[RuntimeDaemon] Initialized")
    
    @property
    def is_running(self) -> bool:
        return self._running and self._task is not None and not self._task.done()
    
    def get_status(self) -> dict:
        """Get daemon status snapshot."""
        return {
            "is_running": self.is_running,
            "cycles_count": self._cycles_count,
            "last_cycle_at": self._last_cycle_at,
            "last_error": self._last_error,
            "started_at": self._started_at,
            "uptime_sec": int(time.time() - self._started_at) if self._started_at else 0,
        }
    
    async def start(self) -> dict:
        """Start the background loop."""
        if self.is_running:
            return {"ok": True, "message": "Already running", **self.get_status()}
        
        # Ensure runtime is enabled
        await self.runtime_service.start_runtime()
        
        self._running = True
        self._started_at = time.time()
        self._last_error = None
        self._task = asyncio.create_task(self._loop())
        
        logger.info("[RuntimeDaemon] Background loop STARTED")
        return {"ok": True, "message": "Daemon started", **self.get_status()}
    
    async def stop(self) -> dict:
        """Stop the background loop gracefully."""
        self._running = False
        
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        
        self._task = None
        self._started_at = None
        
        logger.info("[RuntimeDaemon] Background loop STOPPED")
        return {"ok": True, "message": "Daemon stopped", **self.get_status()}
    
    async def _loop(self):
        """
        Main loop — runs run_once() at configured interval.
        
        Invariants:
        - Single-cycle failure does NOT kill the daemon
        - Interval is read from RuntimeController each cycle (live-configurable)
        - Loop respects _running flag for graceful shutdown
        """
        logger.info("[RuntimeDaemon] Loop thread started")
        
        while self._running:
            cycle_start = time.time()
            
            try:
                # Execute one cycle
                result = await self.runtime_service.run_once()
                
                self._cycles_count += 1
                self._last_cycle_at = datetime.now(timezone.utc).isoformat()
                
                if result.get("ok"):
                    self._last_error = None
                    summary = result.get("summary", {})
                    signals = summary.get("signals", 0)
                    approved = summary.get("approved", 0)
                    executed = summary.get("executed", 0)
                    
                    if signals > 0:
                        logger.info(
                            f"[RuntimeDaemon] Cycle #{self._cycles_count}: "
                            f"signals={signals}, approved={approved}, executed={executed}"
                        )
                else:
                    reason = result.get("reason", result.get("error", "UNKNOWN"))
                    # These are expected states, not errors
                    if reason not in ("RUNTIME_DISABLED", "KILL_SWITCH_ACTIVE", "MARKET_DATA_STALE_BLOCK"):
                        self._last_error = reason
                        logger.warning(f"[RuntimeDaemon] Cycle #{self._cycles_count} blocked: {reason}")
                    
            except asyncio.CancelledError:
                logger.info("[RuntimeDaemon] Loop cancelled")
                break
            except Exception as e:
                self._last_error = str(e)
                logger.error(f"[RuntimeDaemon] Cycle #{self._cycles_count} FAILED: {e}")
                # Continue — don't kill the daemon for a single cycle failure
            
            # Get interval from controller (live-configurable)
            try:
                state = await self.runtime_service.get_runtime_state()
                interval = state.get("loop_interval_sec", 60)
            except Exception:
                interval = 60
            
            # Sleep with cancellation support
            elapsed = time.time() - cycle_start
            sleep_time = max(1, interval - elapsed)
            
            try:
                await asyncio.sleep(sleep_time)
            except asyncio.CancelledError:
                break
        
        logger.info("[RuntimeDaemon] Loop thread exited")


# ─── Singleton ─────────────────────────────────────────
_daemon_instance = None


def init_runtime_daemon(runtime_service) -> RuntimeDaemon:
    global _daemon_instance
    _daemon_instance = RuntimeDaemon(runtime_service)
    return _daemon_instance


def get_runtime_daemon() -> RuntimeDaemon:
    if _daemon_instance is None:
        raise RuntimeError("RuntimeDaemon not initialized")
    return _daemon_instance
