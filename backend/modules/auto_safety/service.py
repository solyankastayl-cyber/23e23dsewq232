"""
Auto Safety Service
===================
Sprint A4: Core safety gate to prevent AUTO mode self-destruction
Sprint WS-2: Broadcasts safety state changes via WebSocket

Rule:
- DETERMINISTIC, no AI, no adaptive sizing
- Simple boolean gates
- Explicit logging for every block
"""

from __future__ import annotations

import logging
import json
import hashlib
from typing import Any, Dict, Optional

from .config import AUTO_SAFETY_DEFAULTS
from .repository import AutoSafetyRepository

logger = logging.getLogger(__name__)


class AutoSafetyService:
    """
    Auto Safety Gate — Production-safe layer for AUTO mode
    
    Flow:
    1. Runtime calls evaluate_auto_permission(signal, size_notional_pct)
    2. Service checks ALL safety gates in order
    3. If ANY gate fails → return {"allowed": False, "reason": "..."}
    4. If all pass → return {"allowed": True}
    
    WS-2: Broadcasts state snapshot only when changed (hash-based debounce).
    """
    
    def __init__(self, repository: AutoSafetyRepository):
        self.repo = repository
        self._initialized = False
        self._last_safety_hash = None  # WS-2: Debounce via hash
    
    async def initialize(self) -> None:
        """Initialize config + state on startup"""
        if self._initialized:
            return
        
        # Ensure config exists (with defaults)
        await self.repo.get_or_create_config(AUTO_SAFETY_DEFAULTS)
        
        # Ensure state exists
        await self.repo.get_or_create_state()
        
        self._initialized = True
        logger.info("[AutoSafety] Service initialized")
    
    async def get_config(self) -> Dict[str, Any]:
        """Get current config"""
        return await self.repo.get_or_create_config(AUTO_SAFETY_DEFAULTS)
    
    async def update_config(self, patch: Dict[str, Any]) -> Dict[str, Any]:
        """Update config (operator override)"""
        updated = await self.repo.update_config(patch)
        logger.info(f"[AutoSafety] Config updated: {patch}")
        return updated
    
    async def get_state(self) -> Dict[str, Any]:
        """Get current state"""
        return await self.repo.get_or_create_state()
    
    async def evaluate_auto_permission(
        self,
        signal: Dict[str, Any],
        size_notional_pct: float = 0.10,
    ) -> Dict[str, Any]:
        """
        Evaluate whether AUTO execution is allowed for this signal.
        
        Args:
            signal: Signal dict {symbol, side, ...}
            size_notional_pct: Trade size as % of portfolio (e.g., 0.10 = 10%)
        
        Returns:
            {"allowed": bool, "reason": str | None}
        """
        config = await self.get_config()
        state = await self.get_state()
        
        # DEBUG
        logger.warning(f"[AutoSafety] evaluate_auto_permission: enabled={config.get('enabled')}, auto_mode_enabled={config.get('auto_mode_enabled')}")
        
        # Gate 0: Is AUTO safety enabled?
        if not config.get("enabled", True):
            logger.warning("[AutoSafety] AUTO safety disabled (dangerous!) - allowing")
            return {"allowed": True, "reason": None}
        
        # Gate 1: Is AUTO mode globally enabled?
        if not config.get("auto_mode_enabled", False):
            reason = "AUTO_MODE_DISABLED"
            await self._record_block(state, reason)
            logger.info(f"[AutoSafety] BLOCKED: {reason}")
            return {"allowed": False, "reason": reason}
        
        # Gate 2: Symbol whitelist
        symbol = signal.get("symbol")
        allowed_symbols = config.get("allowed_symbols", [])
        if symbol not in allowed_symbols:
            reason = f"SYMBOL_NOT_ALLOWED ({symbol} not in {allowed_symbols})"
            await self._record_block(state, reason)
            logger.info(f"[AutoSafety] BLOCKED: {reason}")
            return {"allowed": False, "reason": reason}
        
        # Gate 3: Max trades per hour
        max_trades_per_hour = config.get("max_trades_per_hour", 3)
        if state.get("trades_last_hour", 0) >= max_trades_per_hour:
            reason = f"MAX_TRADES_PER_HOUR ({state['trades_last_hour']} >= {max_trades_per_hour})"
            await self._record_block(state, reason)
            logger.info(f"[AutoSafety] BLOCKED: {reason}")
            return {"allowed": False, "reason": reason}
        
        # Gate 4: Max concurrent positions
        max_concurrent = config.get("max_concurrent_positions", 2)
        if state.get("concurrent_positions", 0) >= max_concurrent:
            reason = f"MAX_CONCURRENT_POSITIONS ({state['concurrent_positions']} >= {max_concurrent})"
            await self._record_block(state, reason)
            logger.info(f"[AutoSafety] BLOCKED: {reason}")
            return {"allowed": False, "reason": reason}
        
        # Gate 5: Max single trade notional %
        max_single_trade = config.get("max_single_trade_notional_pct", 0.10)
        if size_notional_pct > max_single_trade:
            reason = f"TRADE_SIZE_TOO_LARGE ({size_notional_pct*100:.1f}% > {max_single_trade*100:.1f}%)"
            await self._record_block(state, reason)
            logger.info(f"[AutoSafety] BLOCKED: {reason}")
            return {"allowed": False, "reason": reason}
        
        # Gate 6: Max capital deployed %
        max_capital_deployed = config.get("max_capital_deployed_pct", 0.30)
        current_deployed = state.get("capital_deployed_pct", 0.0)
        if current_deployed + size_notional_pct > max_capital_deployed:
            reason = f"MAX_CAPITAL_DEPLOYED ({(current_deployed + size_notional_pct)*100:.1f}% > {max_capital_deployed*100:.1f}%)"
            await self._record_block(state, reason)
            logger.info(f"[AutoSafety] BLOCKED: {reason}")
            return {"allowed": False, "reason": reason}
        
        # Gate 7: Daily loss limit (kill switch trigger)
        daily_loss_limit = config.get("daily_loss_limit_usd", -200.0)
        daily_pnl = state.get("daily_pnl_usd", 0.0)
        if daily_pnl <= daily_loss_limit:
            reason = f"DAILY_LOSS_LIMIT_TRIGGERED (${daily_pnl:.2f} <= ${daily_loss_limit:.2f})"
            await self._record_block(state, reason)
            logger.critical(f"[AutoSafety] KILL SWITCH: {reason}")
            
            # Trigger kill switch
            from modules.strategy_engine.kill_switch import get_kill_switch
            try:
                kill_switch = get_kill_switch()
                await kill_switch.activate(reason)
                logger.critical("[AutoSafety] Kill switch activated")
            except Exception as e:
                logger.error(f"[AutoSafety] Failed to activate kill switch: {e}")
            
            return {"allowed": False, "reason": reason}
        
        # Gate 8: Max consecutive losses (kill switch trigger)
        max_consecutive_losses = config.get("max_consecutive_losses", 3)
        consecutive_losses = state.get("consecutive_losses", 0)
        if consecutive_losses >= max_consecutive_losses:
            reason = f"MAX_CONSECUTIVE_LOSSES ({consecutive_losses} >= {max_consecutive_losses})"
            await self._record_block(state, reason)
            logger.critical(f"[AutoSafety] KILL SWITCH: {reason}")
            
            # Trigger kill switch
            from modules.strategy_engine.kill_switch import get_kill_switch
            try:
                kill_switch = get_kill_switch()
                await kill_switch.activate(reason)
                logger.critical("[AutoSafety] Kill switch activated")
            except Exception as e:
                logger.error(f"[AutoSafety] Failed to activate kill switch: {e}")
            
            return {"allowed": False, "reason": reason}
        
        # ALL GATES PASSED
        # Clear last_block_reason on success
        await self.repo.update_state({"last_block_reason": None})
        
        # WS-2: Broadcast safety state after successful check
        await self._broadcast_safety_state()
        
        logger.info(f"[AutoSafety] ALLOWED: {symbol} (size={size_notional_pct*100:.1f}%)")
        return {"allowed": True, "reason": None}
    
    async def _record_block(self, state: Dict[str, Any], reason: str) -> None:
        """Record block reason in state for visibility"""
        await self.repo.update_state({"last_block_reason": reason})
        
        # WS-2: Broadcast safety state after block
        await self._broadcast_safety_state()
    
    async def increment_trades_last_hour(self) -> None:
        """Increment trade counter (called after successful execution)"""
        state = await self.get_state()
        new_count = state.get("trades_last_hour", 0) + 1
        await self.repo.update_state({"trades_last_hour": new_count})
        logger.info(f"[AutoSafety] Trades last hour: {new_count}")
        
        # WS-2: Broadcast safety state after counter update
        await self._broadcast_safety_state()
    
    async def reset_hourly_counters(self) -> None:
        """Reset hourly counters (should be called by a cron job)"""
        await self.repo.update_state({"trades_last_hour": 0})
        logger.info("[AutoSafety] Hourly counters reset")
        
        # WS-2: Broadcast safety state after reset
        await self._broadcast_safety_state()
    
    async def _broadcast_safety_state(self) -> None:
        """
        Broadcast safety state snapshot via WebSocket.
        
        WS-2: Only broadcasts if state changed (hash-based debounce).
        """
        try:
            from modules.ws_hub.service_locator import get_ws_broadcaster
            
            broadcaster = get_ws_broadcaster()
            state = await self.repo.get_or_create_state()
            
            # Hash-based debounce: only broadcast if changed
            new_hash = hashlib.md5(
                json.dumps(state, sort_keys=True).encode()
            ).hexdigest()
            
            if new_hash != self._last_safety_hash:
                self._last_safety_hash = new_hash
                await broadcaster.broadcast_snapshot("safety.state", state)
                logger.debug(f"[WS-2] safety.state broadcast (hash={new_hash[:8]})")
        
        except Exception as e:
            logger.debug(f"[WS-2] safety broadcast failed (non-critical): {e}")
