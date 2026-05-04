"""
Lifecycle Builder
=================

Builds position lifecycle from Event Ledger events.
"""

import time
from typing import Dict, List, Optional, Any

from .lifecycle_types import (
    PositionLifecycle,
    LifecycleEvent,
    LifecyclePhase,
    LifecycleEventType,
    LifecycleStats
)


class LifecycleBuilder:
    """
    Builds position lifecycle from events.
    
    Pipeline:
    Event Ledger → Filter by position → Sort → Build timeline → Calculate stats
    """
    
    # Event type to phase mapping
    PHASE_MAP = {
        "SIGNAL_RECEIVED": LifecyclePhase.ENTRY,
        "STRATEGY_DECISION_MADE": LifecyclePhase.ENTRY,
        "ORDER_CREATED": LifecyclePhase.ENTRY,
        "ORDER_SUBMITTED": LifecyclePhase.ENTRY,
        "ORDER_FILLED": LifecyclePhase.ENTRY,
        "POSITION_OPENED": LifecyclePhase.ENTRY,
        
        "POSITION_SCALED": LifecyclePhase.ADJUSTMENT,
        "POSITION_REDUCED": LifecyclePhase.ADJUSTMENT,
        "POSITION_HEDGED": LifecyclePhase.ADJUSTMENT,
        "STOP_UPDATED": LifecyclePhase.ADJUSTMENT,
        "TP_UPDATED": LifecyclePhase.ADJUSTMENT,
        
        "CLOSE_ORDER_CREATED": LifecyclePhase.EXIT,
        "CLOSE_ORDER_FILLED": LifecyclePhase.EXIT,
        "POSITION_CLOSED": LifecyclePhase.CLOSED,
        "POSITION_LIQUIDATED": LifecyclePhase.CLOSED,
        "POSITION_FORCED_CLOSE": LifecyclePhase.CLOSED
    }
    
    def build(
        self,
        position_id: str,
        events: List[Dict[str, Any]],
        price_history: Optional[List[Dict]] = None
    ) -> PositionLifecycle:
        """
        Build complete lifecycle from events.
        """
        
        lifecycle = PositionLifecycle(position_id=position_id)
        
        if not events:
            return lifecycle
        
        # Sort events by timestamp
        sorted_events = sorted(
            events,
            key=lambda e: e.get("created_at", e.get("createdAt", 0))
        )
        
        # Build timeline
        prev_timestamp = 0
        for event in sorted_events:
            lc_event = self._convert_event(event, prev_timestamp)
            lifecycle.events.append(lc_event)
            prev_timestamp = lc_event.timestamp
            
            # Extract position info from POSITION_OPENED
            event_type = event.get("event_type", event.get("eventType", ""))
            payload = event.get("payload", {})
            
            if event_type == "POSITION_OPENED":
                lifecycle.symbol = payload.get("symbol", "")
                lifecycle.exchange = payload.get("exchange", "")
                lifecycle.side = payload.get("side", "")
                lifecycle.strategy_id = payload.get("strategy_id", payload.get("strategyId"))
                lifecycle.profile_id = payload.get("profile_id", payload.get("profileId"))
                lifecycle.opened_at = lc_event.timestamp
            
            elif event_type in ["POSITION_CLOSED", "POSITION_LIQUIDATED"]:
                lifecycle.closed_at = lc_event.timestamp
                lifecycle.is_closed = True
        
        # Determine current phase
        lifecycle.current_phase = self._determine_current_phase(lifecycle.events)
        
        # Store price history for MAE/MFE
        lifecycle.price_history = price_history or []
        
        # Calculate stats
        lifecycle.stats = self._calculate_stats(lifecycle)
        
        return lifecycle
    
    def _convert_event(
        self,
        event: Dict,
        prev_timestamp: int
    ) -> LifecycleEvent:
        """Convert ledger event to lifecycle event"""
        
        event_type = event.get("event_type", event.get("eventType", ""))
        timestamp = event.get("created_at", event.get("createdAt", 0))
        payload = event.get("payload", {})
        
        phase = self.PHASE_MAP.get(event_type, LifecyclePhase.ACTIVE)
        
        return LifecycleEvent(
            event_id=event.get("event_id", event.get("eventId", "")),
            event_type=event_type,
            phase=phase,
            timestamp=timestamp,
            price=payload.get("price"),
            size=payload.get("size", payload.get("quantity")),
            pnl=payload.get("pnl", payload.get("unrealized_pnl")),
            pnl_pct=payload.get("pnl_pct"),
            metadata={
                k: v for k, v in payload.items()
                if k not in ["price", "size", "quantity", "pnl", "unrealized_pnl", "pnl_pct"]
            },
            duration_from_prev=timestamp - prev_timestamp if prev_timestamp else 0
        )
    
    def _determine_current_phase(self, events: List[LifecycleEvent]) -> LifecyclePhase:
        """Determine current lifecycle phase"""
        
        if not events:
            return LifecyclePhase.ENTRY
        
        # Get last event's phase
        last_event = events[-1]
        
        # If closed, return CLOSED
        if last_event.event_type in ["POSITION_CLOSED", "POSITION_LIQUIDATED", "POSITION_FORCED_CLOSE"]:
            return LifecyclePhase.CLOSED
        
        # If has closing events, return EXIT
        if last_event.phase == LifecyclePhase.EXIT:
            return LifecyclePhase.EXIT
        
        # If has adjustments after open, return ADJUSTMENT or ACTIVE
        has_opened = any(e.event_type == "POSITION_OPENED" for e in events)
        has_adjustment = any(e.phase == LifecyclePhase.ADJUSTMENT for e in events)
        
        if has_opened:
            if has_adjustment:
                # Check if recent adjustment
                adjustment_events = [e for e in events if e.phase == LifecyclePhase.ADJUSTMENT]
                if adjustment_events:
                    last_adj = adjustment_events[-1]
                    if (int(time.time() * 1000) - last_adj.timestamp) < 300000:  # 5 min
                        return LifecyclePhase.ADJUSTMENT
            return LifecyclePhase.ACTIVE
        
        return LifecyclePhase.ENTRY
    
    def _calculate_stats(self, lifecycle: PositionLifecycle) -> LifecycleStats:
        """Calculate lifecycle statistics"""
        
        stats = LifecycleStats(position_id=lifecycle.position_id)
        
        if not lifecycle.events:
            return stats
        
        stats.total_events = len(lifecycle.events)
        
        # Find key events
        open_event = None
        close_event = None
        entry_price = 0
        exit_price = 0
        
        for event in lifecycle.events:
            if event.event_type == "POSITION_OPENED":
                open_event = event
                if event.price:
                    entry_price = event.price
                    stats.entry_price = entry_price
            
            elif event.event_type in ["POSITION_CLOSED", "POSITION_LIQUIDATED"]:
                close_event = event
                if event.price:
                    exit_price = event.price
                    stats.exit_price = exit_price
                if event.pnl:
                    stats.realized_pnl = event.pnl
            
            elif event.event_type == "POSITION_SCALED":
                stats.scale_events += 1
            
            elif event.event_type == "POSITION_REDUCED":
                stats.reduce_events += 1
            
            elif event.event_type in ["STOP_UPDATED", "TP_UPDATED"]:
                stats.stop_updates += 1
        
        # Calculate durations
        first_event = lifecycle.events[0]
        last_event = lifecycle.events[-1]
        
        stats.total_duration_minutes = (last_event.timestamp - first_event.timestamp) / 60000
        
        if open_event:
            stats.entry_duration_minutes = (open_event.timestamp - first_event.timestamp) / 60000
            
            if close_event:
                stats.active_duration_minutes = (close_event.timestamp - open_event.timestamp) / 60000
        
        # Calculate MAE/MFE from price history or events
        if lifecycle.price_history:
            mae, mfe = self._calculate_mae_mfe_from_history(
                lifecycle.price_history,
                entry_price,
                lifecycle.side
            )
            stats.mae = mae["value"]
            stats.mae_pct = mae["pct"]
            stats.mae_timestamp = mae.get("timestamp")
            stats.mfe = mfe["value"]
            stats.mfe_pct = mfe["pct"]
            stats.mfe_timestamp = mfe.get("timestamp")
        else:
            # Estimate from events
            stats.mae, stats.mfe = self._estimate_mae_mfe_from_events(
                lifecycle.events,
                entry_price,
                lifecycle.side
            )
        
        # Calculate realized PnL %
        if stats.entry_price > 0 and stats.exit_price:
            if lifecycle.side == "LONG":
                stats.realized_pnl_pct = (stats.exit_price - stats.entry_price) / stats.entry_price
            else:
                stats.realized_pnl_pct = (stats.entry_price - stats.exit_price) / stats.entry_price
        
        # Calculate capture efficiency
        if stats.mfe > 0 and stats.realized_pnl > 0:
            stats.capture_efficiency = stats.realized_pnl / stats.mfe
        
        return stats
    
    def _calculate_mae_mfe_from_history(
        self,
        price_history: List[Dict],
        entry_price: float,
        side: str
    ) -> tuple:
        """Calculate MAE/MFE from price history"""
        
        mae = {"value": 0.0, "pct": 0.0, "timestamp": None}
        mfe = {"value": 0.0, "pct": 0.0, "timestamp": None}
        
        if not entry_price or not price_history:
            return mae, mfe
        
        for point in price_history:
            price = point.get("price", 0)
            timestamp = point.get("timestamp")
            
            if side == "LONG":
                pnl = price - entry_price
            else:
                pnl = entry_price - price
            
            pnl_pct = pnl / entry_price if entry_price else 0
            
            # Update MAE (worst loss)
            if pnl < mae["value"]:
                mae["value"] = pnl
                mae["pct"] = pnl_pct
                mae["timestamp"] = timestamp
            
            # Update MFE (best profit)
            if pnl > mfe["value"]:
                mfe["value"] = pnl
                mfe["pct"] = pnl_pct
                mfe["timestamp"] = timestamp
        
        return mae, mfe
    
    def _estimate_mae_mfe_from_events(
        self,
        events: List[LifecycleEvent],
        entry_price: float,
        side: str
    ) -> tuple:
        """Estimate MAE/MFE from event PnL values"""
        
        mae = 0.0
        mfe = 0.0
        
        for event in events:
            if event.pnl is not None:
                if event.pnl < mae:
                    mae = event.pnl
                if event.pnl > mfe:
                    mfe = event.pnl
        
        return mae, mfe


# Global builder instance
lifecycle_builder = LifecycleBuilder()
