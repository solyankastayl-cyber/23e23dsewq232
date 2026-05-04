"""
Strategy Visibility Service
============================
Sprint A3: Signal and Decision recording for operator visibility
Sprint WS-3: Broadcasts strategy.signals via WebSocket when state changes.
"""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional


class StrategyVisibilityService:
    def __init__(self, repository):
        self.repo = repository

    async def record_signal(
        self,
        signal: Dict[str, Any],
        decision_status: str,
        runtime_mode: str,
        risk_reason: Optional[str] = None,
    ) -> None:
        """
        Record signal to live snapshot layer.
        
        Sprint WS-3: Broadcasts strategy.signals snapshot after state fixation.
        
        Args:
            signal: Runtime signal dict
            decision_status: APPROVED | REJECTED | PENDING
            runtime_mode: MANUAL | SEMI_AUTO | AUTO
            risk_reason: Optional rejection reason
        """
        live_doc = {
            "symbol": signal["symbol"],
            "direction": "LONG" if signal["side"] == "BUY" else "SHORT",
            "confidence": signal.get("confidence"),
            "strategy": signal.get("strategy"),
            "setup_type": signal.get("strategy"),
            "regime": signal.get("metadata", {}).get("regime"),
            "drivers": signal.get("metadata", {}).get("drivers", {}),
            "thesis": signal.get("thesis"),
            "source": signal.get("source", "UNKNOWN"),
            "status": decision_status,
            "risk_reason": risk_reason,
            "runtime_mode": runtime_mode,
        }
        
        # State fixation: write to storage
        await self.repo.upsert_live_signal(live_doc)
        
        # WS-3: Broadcast strategy.signals snapshot AFTER storage write
        await self._broadcast_signals_if_changed()

    async def record_decision(
        self,
        signal: Dict[str, Any],
        decision_status: str,
        runtime_mode: str,
        risk_reason: Optional[str] = None,
        decision_id: Optional[str] = None,
    ) -> None:
        """
        Record decision to append-only log.
        
        Sprint WS-3: Also triggers strategy.signals broadcast (decision affects signal status).
        
        Args:
            signal: Runtime signal dict
            decision_status: APPROVED | REJECTED | PENDING | EXECUTED
            runtime_mode: MANUAL | SEMI_AUTO | AUTO
            risk_reason: Optional rejection reason
            decision_id: Optional decision ID for PENDING
        """
        doc = {
            "decision_id": decision_id,
            "symbol": signal["symbol"],
            "direction": "LONG" if signal["side"] == "BUY" else "SHORT",
            "confidence": signal.get("confidence"),
            "strategy": signal.get("strategy"),
            "regime": signal.get("metadata", {}).get("regime"),
            "drivers": signal.get("metadata", {}).get("drivers", {}),
            "thesis": signal.get("thesis"),
            "status": decision_status,
            "risk_reason": risk_reason,
            "runtime_mode": runtime_mode,
            "source": signal.get("source", "UNKNOWN"),
            "created_at": int(time.time() * 1000),
        }
        
        # State fixation: write to storage
        await self.repo.insert_decision(doc)
        
        # WS-3: Broadcast strategy.signals snapshot AFTER decision recorded
        await self._broadcast_signals_if_changed()

    async def get_live_signals(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get current live signals."""
        return await self.repo.get_live_signals(limit=limit)

    async def get_recent_decisions(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent decisions."""
        return await self.repo.get_recent_decisions(limit=limit)

    async def get_summary(self, window_minutes: int = 60) -> Dict[str, int]:
        """Get strategy summary for time window."""
        since_ms = int(time.time() * 1000) - (window_minutes * 60 * 1000)
        return await self.repo.get_summary(since_ms=since_ms)
    
    async def _broadcast_signals_if_changed(self):
        """
        Sprint WS-3: Broadcast strategy.signals snapshot if state changed.
        
        This method:
        1. Gets current live signals (state fixation)
        2. Broadcasts via WebSocket (with hash debounce)
        
        Called after record_signal() or record_decision().
        """
        try:
            from modules.ws_hub.service_locator import get_ws_broadcaster
            
            broadcaster = get_ws_broadcaster()
            
            # State fixation: get current live signals
            signals = await self.repo.get_live_signals(limit=50)
            
            # Broadcast (debouncer will skip if hash unchanged)
            await broadcaster.broadcast_snapshot("strategy.signals", signals)
        
        except Exception:
            # Non-critical: don't break strategy logic if WS fails
            pass  # Silent fail (WS is optional transport layer)
