"""
OPS1 Position Service
=====================

Main service for deep position monitoring.
"""

import time
import threading
from typing import Dict, List, Optional, Any

from .position_types import (
    DeepPositionState,
    PositionOwnership,
    PositionRiskView,
    PositionStatus,
    PositionSummary,
    RiskLevel
)
from .position_enricher import position_enricher
from .position_repository import position_repository


class PositionService:
    """
    Main service for OPS1 Deep Position Monitor.
    
    Provides complete visibility into positions with:
    - Identity, market, ownership, lifecycle, risk data
    - Queries by symbol, strategy, profile
    - Summary and analytics
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._portfolio_value = 100000.0  # Default portfolio value
        
        self._initialized = True
        print("[PositionService] Initialized (OPS1)")
    
    # ===========================================
    # Position Management
    # ===========================================
    
    def register_position(
        self,
        raw_position: Dict[str, Any],
        events: Optional[List[Dict]] = None
    ) -> DeepPositionState:
        """
        Register a new position or update existing.
        
        Enriches with ownership, risk, and event data.
        """
        
        # Enrich position
        deep_state = position_enricher.enrich(
            raw_position,
            events=events,
            portfolio_value=self._portfolio_value
        )
        
        # Save to repository
        position_repository.save(deep_state)
        
        return deep_state
    
    def update_position(
        self,
        position_id: str,
        updates: Dict[str, Any],
        events: Optional[List[Dict]] = None
    ) -> Optional[DeepPositionState]:
        """
        Update an existing position.
        """
        
        # Get current state
        current = position_repository.get(position_id)
        if not current:
            return None
        
        # Apply updates
        raw = {
            "position_id": position_id,
            "exchange": updates.get("exchange", current.exchange),
            "symbol": updates.get("symbol", current.symbol),
            "side": updates.get("side", current.side),
            "quantity": updates.get("quantity", current.quantity),
            "entry_price": updates.get("entry_price", current.entry_price),
            "mark_price": updates.get("mark_price", current.mark_price),
            "leverage": updates.get("leverage", current.leverage),
            "stop_loss": updates.get("stop_loss", current.stop_loss),
            "take_profit": updates.get("take_profit", current.take_profit),
            "opened_at": current.opened_at,
            "strategy_id": current.ownership.strategy_id if current.ownership else None,
            "profile_id": current.ownership.profile_id if current.ownership else None
        }
        
        # Re-enrich
        updated = position_enricher.enrich(raw, events, self._portfolio_value)
        
        # Preserve some state
        updated.realized_pnl = updates.get("realized_pnl", current.realized_pnl)
        updated.scale_count = current.scale_count
        updated.reduce_count = current.reduce_count
        
        # Save
        position_repository.save(updated)
        
        return updated
    
    def close_position(
        self,
        position_id: str,
        exit_price: float,
        realized_pnl: float
    ) -> Optional[DeepPositionState]:
        """
        Close a position.
        """
        
        current = position_repository.get(position_id)
        if not current:
            return None
        
        current.status = PositionStatus.CLOSED
        current.closed_at = int(time.time() * 1000)
        current.realized_pnl = realized_pnl
        current.total_pnl = current.unrealized_pnl + realized_pnl
        current.mark_price = exit_price
        
        position_repository.save(current)
        return current
    
    # ===========================================
    # Queries
    # ===========================================
    
    def get_position(self, position_id: str) -> Optional[DeepPositionState]:
        """Get position by ID"""
        return position_repository.get(position_id)
    
    def get_all_positions(self, include_closed: bool = False) -> List[DeepPositionState]:
        """Get all positions"""
        return position_repository.get_all(include_closed)
    
    def get_by_symbol(self, symbol: str, include_closed: bool = False) -> List[DeepPositionState]:
        """Get positions by symbol"""
        return position_repository.get_by_symbol(symbol, include_closed)
    
    def get_by_exchange(self, exchange: str, include_closed: bool = False) -> List[DeepPositionState]:
        """Get positions by exchange"""
        return position_repository.get_by_exchange(exchange, include_closed)
    
    def get_by_strategy(self, strategy_id: str, include_closed: bool = False) -> List[DeepPositionState]:
        """Get positions by strategy"""
        return position_repository.get_by_strategy(strategy_id, include_closed)
    
    def get_by_profile(self, profile_id: str, include_closed: bool = False) -> List[DeepPositionState]:
        """Get positions by profile"""
        return position_repository.get_by_profile(profile_id, include_closed)
    
    def get_by_status(self, status: str) -> List[DeepPositionState]:
        """Get positions by status"""
        return position_repository.get_by_status(status)
    
    # ===========================================
    # Risk View
    # ===========================================
    
    def get_position_risk(self, position_id: str) -> Optional[PositionRiskView]:
        """Get risk view for position"""
        pos = position_repository.get(position_id)
        return pos.risk_view if pos else None
    
    def get_high_risk_positions(self, min_level: str = "HIGH") -> List[DeepPositionState]:
        """Get positions above a risk level"""
        
        level_order = ["LOW", "MODERATE", "HIGH", "CRITICAL"]
        min_idx = level_order.index(min_level) if min_level in level_order else 2
        
        all_pos = position_repository.get_all(include_closed=False)
        
        return [
            p for p in all_pos
            if p.risk_view and level_order.index(p.risk_view.risk_level.value) >= min_idx
        ]
    
    # ===========================================
    # Ownership
    # ===========================================
    
    def get_position_ownership(self, position_id: str) -> Optional[PositionOwnership]:
        """Get ownership info for position"""
        pos = position_repository.get(position_id)
        return pos.ownership if pos else None
    
    # ===========================================
    # Summary & Analytics
    # ===========================================
    
    def get_summary(self) -> PositionSummary:
        """Get aggregated position summary"""
        
        all_positions = position_repository.get_all(include_closed=False)
        closed_positions = position_repository.get_by_status("CLOSED")
        
        summary = PositionSummary()
        summary.open_positions = len(all_positions)
        summary.total_positions = summary.open_positions + len(closed_positions)
        
        largest_exposure = 0.0
        highest_risk_score = -1
        risk_order = {"LOW": 0, "MODERATE": 1, "HIGH": 2, "CRITICAL": 3}
        
        for pos in all_positions:
            # PnL
            summary.total_unrealized_pnl += pos.unrealized_pnl
            summary.total_realized_pnl += pos.realized_pnl
            
            # Exposure
            if pos.risk_view:
                summary.total_exposure_usd += pos.risk_view.exposure_usd
                
                # Largest position
                if pos.risk_view.exposure_usd > largest_exposure:
                    largest_exposure = pos.risk_view.exposure_usd
                    summary.largest_position_symbol = pos.symbol
                    summary.largest_position_exposure = largest_exposure
                
                # Highest risk
                risk_score = risk_order.get(pos.risk_view.risk_level.value, 0)
                if risk_score > highest_risk_score:
                    highest_risk_score = risk_score
                    summary.highest_risk_position_id = pos.position_id
                    summary.highest_risk_level = pos.risk_view.risk_level.value
            
            # By exchange
            if pos.exchange not in summary.positions_by_exchange:
                summary.positions_by_exchange[pos.exchange] = 0
            summary.positions_by_exchange[pos.exchange] += 1
            
            # By strategy
            if pos.ownership and pos.ownership.strategy_id:
                strat = pos.ownership.strategy_id
                if strat not in summary.positions_by_strategy:
                    summary.positions_by_strategy[strat] = 0
                summary.positions_by_strategy[strat] += 1
            
            # By status
            status = pos.status.value
            if status not in summary.positions_by_status:
                summary.positions_by_status[status] = 0
            summary.positions_by_status[status] += 1
            
            # Win/loss
            if pos.unrealized_pnl > 0:
                summary.winning_positions += 1
            else:
                summary.losing_positions += 1
        
        summary.total_pnl = summary.total_unrealized_pnl + summary.total_realized_pnl
        
        return summary
    
    # ===========================================
    # Configuration
    # ===========================================
    
    def set_portfolio_value(self, value: float):
        """Set portfolio value for risk calculations"""
        self._portfolio_value = value
    
    def get_portfolio_value(self) -> float:
        """Get current portfolio value"""
        return self._portfolio_value
    
    # ===========================================
    # Health
    # ===========================================
    
    def get_health(self) -> Dict[str, Any]:
        """Get service health"""
        summary = self.get_summary()
        
        return {
            "module": "OPS1 Deep Position Monitor",
            "status": "healthy",
            "openPositions": summary.open_positions,
            "totalUnrealizedPnl": round(summary.total_unrealized_pnl, 2),
            "totalExposureUsd": round(summary.total_exposure_usd, 2),
            "highestRiskLevel": summary.highest_risk_level,
            "portfolioValue": self._portfolio_value,
            "timestamp": int(time.time() * 1000)
        }


# Global singleton
position_service = PositionService()
