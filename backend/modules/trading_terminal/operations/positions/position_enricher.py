"""
Position Enricher
=================

Enriches raw positions with ownership, strategy, risk, and event data.
"""

import time
from typing import Dict, List, Optional, Any

from .position_types import (
    DeepPositionState,
    PositionOwnership,
    PositionRiskView,
    PositionStatus,
    RiskLevel
)


class PositionEnricher:
    """
    Enriches raw positions with deep metadata.
    
    Pipeline:
    raw position → enrich ownership → enrich risk → enrich events → deep state
    """
    
    def __init__(self):
        self._ownership_cache: Dict[str, PositionOwnership] = {}
    
    def enrich(
        self,
        raw_position: Dict[str, Any],
        events: Optional[List[Dict]] = None,
        portfolio_value: float = 100000.0
    ) -> DeepPositionState:
        """
        Enrich raw position with all metadata.
        """
        
        pos_id = raw_position.get("position_id", raw_position.get("positionId", f"pos_{int(time.time()*1000)}"))
        
        # Create base state
        state = DeepPositionState(
            position_id=pos_id,
            exchange=raw_position.get("exchange", "UNKNOWN"),
            symbol=raw_position.get("symbol", ""),
            side=raw_position.get("side", "LONG"),
            quantity=float(raw_position.get("quantity", raw_position.get("size", 0))),
            entry_price=float(raw_position.get("entry_price", raw_position.get("entryPrice", 0))),
            mark_price=float(raw_position.get("mark_price", raw_position.get("markPrice", 0))),
            avg_price=float(raw_position.get("avg_price", raw_position.get("avgPrice", 0))),
            leverage=raw_position.get("leverage"),
            margin_mode=raw_position.get("margin_mode", raw_position.get("marginMode")),
            opened_at=raw_position.get("opened_at", raw_position.get("openedAt", int(time.time() * 1000)))
        )
        
        # Calculate PnL
        state = self._enrich_pnl(state)
        
        # Enrich with ownership
        state = self._enrich_ownership(state, raw_position, events)
        
        # Enrich with risk
        state = self._enrich_risk(state, portfolio_value)
        
        # Enrich with events
        if events:
            state = self._enrich_from_events(state, events)
        
        # Calculate age
        state.age_minutes = (int(time.time() * 1000) - state.opened_at) / 60000
        
        # Set updated time
        state.updated_at = int(time.time() * 1000)
        
        return state
    
    def _enrich_pnl(self, state: DeepPositionState) -> DeepPositionState:
        """Calculate PnL metrics"""
        
        if state.entry_price > 0 and state.mark_price > 0:
            if state.side == "LONG":
                state.unrealized_pnl = (state.mark_price - state.entry_price) * state.quantity
                state.pnl_pct = (state.mark_price - state.entry_price) / state.entry_price
            else:  # SHORT
                state.unrealized_pnl = (state.entry_price - state.mark_price) * state.quantity
                state.pnl_pct = (state.entry_price - state.mark_price) / state.entry_price
        
        state.total_pnl = state.unrealized_pnl + state.realized_pnl
        
        return state
    
    def _enrich_ownership(
        self,
        state: DeepPositionState,
        raw_position: Dict,
        events: Optional[List[Dict]]
    ) -> DeepPositionState:
        """Enrich with ownership information"""
        
        ownership = PositionOwnership(position_id=state.position_id)
        
        # From raw position
        ownership.strategy_id = raw_position.get("strategy_id", raw_position.get("strategyId"))
        ownership.profile_id = raw_position.get("profile_id", raw_position.get("profileId"))
        ownership.config_id = raw_position.get("config_id", raw_position.get("configId"))
        
        # From events (look for POSITION_OPENED or STRATEGY_DECISION_MADE)
        if events:
            for event in events:
                event_type = event.get("event_type", event.get("eventType", ""))
                payload = event.get("payload", {})
                
                if event_type == "POSITION_OPENED":
                    if not ownership.strategy_id:
                        ownership.strategy_id = payload.get("strategy_id", payload.get("strategyId"))
                    if not ownership.profile_id:
                        ownership.profile_id = payload.get("profile_id", payload.get("profileId"))
                    ownership.assigned_at = event.get("created_at", event.get("createdAt", 0))
                
                elif event_type == "STRATEGY_DECISION_MADE":
                    ownership.decision_trace_id = event.get("event_id", event.get("eventId"))
                    ownership.signal_id = payload.get("signal_id", payload.get("signalId"))
        
        # Map strategy names
        strategy_names = {
            "MOMENTUM_BREAKOUT": "Momentum Breakout",
            "TREND_CONFIRMATION": "Trend Confirmation",
            "MEAN_REVERSION": "Mean Reversion",
            "STR_TREND": "Trend Following",
            "STR_MOMENTUM": "Momentum"
        }
        if ownership.strategy_id:
            ownership.strategy_name = strategy_names.get(ownership.strategy_id, ownership.strategy_id)
        
        profile_names = {
            "CONSERVATIVE": "Conservative",
            "BALANCED": "Balanced",
            "AGGRESSIVE": "Aggressive"
        }
        if ownership.profile_id:
            ownership.profile_name = profile_names.get(ownership.profile_id, ownership.profile_id)
        
        state.ownership = ownership
        return state
    
    def _enrich_risk(
        self,
        state: DeepPositionState,
        portfolio_value: float
    ) -> DeepPositionState:
        """Enrich with risk metrics"""
        
        risk = PositionRiskView(position_id=state.position_id)
        
        # Calculate exposure
        risk.exposure_usd = state.quantity * state.mark_price
        risk.exposure_pct = (risk.exposure_usd / portfolio_value) * 100 if portfolio_value > 0 else 0
        
        # Calculate stop/TP distances
        if state.stop_loss and state.mark_price > 0:
            if state.side == "LONG":
                risk.distance_to_stop_pct = ((state.mark_price - state.stop_loss) / state.mark_price) * 100
            else:
                risk.distance_to_stop_pct = ((state.stop_loss - state.mark_price) / state.mark_price) * 100
        
        if state.take_profit and state.mark_price > 0:
            if state.side == "LONG":
                risk.distance_to_take_profit_pct = ((state.take_profit - state.mark_price) / state.mark_price) * 100
            else:
                risk.distance_to_take_profit_pct = ((state.mark_price - state.take_profit) / state.mark_price) * 100
        
        # Estimate liquidation distance for leveraged positions
        if state.leverage and state.leverage > 1:
            # Simplified: 100% / leverage = approximate liquidation distance
            risk.liquidation_distance_pct = 100 / state.leverage
            if state.side == "LONG":
                risk.liquidation_price = state.entry_price * (1 - risk.liquidation_distance_pct / 100)
            else:
                risk.liquidation_price = state.entry_price * (1 + risk.liquidation_distance_pct / 100)
        
        # Calculate max loss
        if risk.distance_to_stop_pct:
            risk.max_loss_usd = risk.exposure_usd * (risk.distance_to_stop_pct / 100)
            risk.risk_per_trade = (risk.max_loss_usd / portfolio_value) * 100
        
        # Determine risk level
        risk.risk_level, risk.risk_factors = self._assess_risk_level(state, risk)
        
        state.risk_view = risk
        return state
    
    def _assess_risk_level(
        self,
        state: DeepPositionState,
        risk: PositionRiskView
    ) -> tuple:
        """Assess overall risk level"""
        
        factors = []
        score = 0  # 0-100
        
        # Exposure factor
        if risk.exposure_pct > 30:
            score += 30
            factors.append("High exposure (>30%)")
        elif risk.exposure_pct > 15:
            score += 15
            factors.append("Elevated exposure (>15%)")
        
        # Leverage factor
        if state.leverage:
            if state.leverage > 10:
                score += 30
                factors.append("Very high leverage (>10x)")
            elif state.leverage > 5:
                score += 20
                factors.append("High leverage (>5x)")
            elif state.leverage > 3:
                score += 10
                factors.append("Moderate leverage (>3x)")
        
        # PnL factor (losing position)
        if state.pnl_pct < -0.05:
            score += 20
            factors.append("Significant loss (>5%)")
        elif state.pnl_pct < -0.02:
            score += 10
            factors.append("Minor loss (>2%)")
        
        # Liquidation proximity
        if risk.liquidation_distance_pct and risk.liquidation_distance_pct < 10:
            score += 25
            factors.append("Close to liquidation (<10%)")
        
        # Age factor (old positions)
        if state.age_minutes > 1440:  # > 24 hours
            score += 5
            factors.append("Long-held position (>24h)")
        
        # Determine level
        if score >= 60:
            level = RiskLevel.CRITICAL
        elif score >= 40:
            level = RiskLevel.HIGH
        elif score >= 20:
            level = RiskLevel.MODERATE
        else:
            level = RiskLevel.LOW
        
        return level, factors
    
    def _enrich_from_events(
        self,
        state: DeepPositionState,
        events: List[Dict]
    ) -> DeepPositionState:
        """Enrich state from event history"""
        
        state.event_count = len(events)
        
        if events:
            # Get last event
            sorted_events = sorted(events, key=lambda e: e.get("created_at", e.get("createdAt", 0)))
            if sorted_events:
                last = sorted_events[-1]
                state.last_event_id = last.get("event_id", last.get("eventId"))
        
        # Count scale/reduce events
        for event in events:
            event_type = event.get("event_type", event.get("eventType", ""))
            
            if event_type == "POSITION_SCALED":
                state.scale_count += 1
                state.last_scaled_at = event.get("created_at", event.get("createdAt"))
            
            elif event_type == "POSITION_REDUCED":
                state.reduce_count += 1
                state.last_reduced_at = event.get("created_at", event.get("createdAt"))
            
            elif event_type == "POSITION_CLOSED":
                state.status = PositionStatus.CLOSED
                state.closed_at = event.get("created_at", event.get("createdAt"))
            
            elif event_type == "POSITION_LIQUIDATED":
                state.status = PositionStatus.FORCED_CLOSE
                state.closed_at = event.get("created_at", event.get("createdAt"))
        
        # Determine current status based on events
        if state.status == PositionStatus.OPEN:
            if state.scale_count > 0 and state.last_scaled_at:
                # Recent scale
                if (int(time.time() * 1000) - state.last_scaled_at) < 60000:
                    state.status = PositionStatus.SCALING
            elif state.reduce_count > 0 and state.last_reduced_at:
                # Recent reduce
                if (int(time.time() * 1000) - state.last_reduced_at) < 60000:
                    state.status = PositionStatus.REDUCING
        
        return state


# Global enricher instance
position_enricher = PositionEnricher()
