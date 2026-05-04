"""
Portfolio State Service (S4.1)
==============================

Service for managing portfolio state.

Responsibilities:
- Create initial state from capital
- Update state on events
- Track drawdowns and high water marks
- Calculate capital distribution
"""

import threading
from datetime import datetime, timezone
from typing import Dict, Any, Optional

from .portfolio_types import (
    PortfolioSimulation,
    PortfolioStrategySlot,
    PortfolioState,
    SlotStatus
)
from .portfolio_repository import portfolio_repository


class PortfolioStateService:
    """
    Service for managing portfolio state.
    
    Thread-safe singleton.
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
        self._initialized = True
        print("[PortfolioStateService] Initialized")
    
    # ===========================================
    # Create Initial State
    # ===========================================
    
    def create_initial_state(
        self,
        simulation: PortfolioSimulation
    ) -> PortfolioState:
        """
        Create initial portfolio state.
        
        Called when simulation is created.
        All capital starts as cash.
        """
        state = PortfolioState(
            simulation_id=simulation.simulation_id,
            equity_usd=simulation.total_capital_usd,
            cash_usd=simulation.total_capital_usd,
            used_capital_usd=0.0,
            free_capital_usd=simulation.total_capital_usd,
            margin_used_usd=0.0,
            margin_available_usd=simulation.total_capital_usd,
            total_pnl_usd=0.0,
            total_pnl_pct=0.0,
            peak_equity_usd=simulation.total_capital_usd,
            drawdown_usd=0.0,
            drawdown_pct=0.0,
            total_positions=0,
            open_positions=0,
            timestamp=datetime.now(timezone.utc),
            version=1
        )
        
        # Save to repository
        portfolio_repository.save_state(state)
        
        print(f"[PortfolioStateService] Created initial state for {simulation.simulation_id}")
        return state
    
    # ===========================================
    # Get State
    # ===========================================
    
    def get_portfolio_state(
        self,
        simulation_id: str
    ) -> Optional[PortfolioState]:
        """Get current portfolio state"""
        return portfolio_repository.get_latest_state(simulation_id)
    
    def get_state_history(
        self,
        simulation_id: str,
        limit: int = 100
    ) -> list:
        """Get state history for a simulation"""
        return portfolio_repository.get_state_history(simulation_id, limit)
    
    # ===========================================
    # Update State (S4.2 will extend this)
    # ===========================================
    
    def update_portfolio_state(
        self,
        simulation_id: str,
        equity_delta: float = 0.0,
        cash_delta: float = 0.0,
        positions_delta: int = 0
    ) -> Optional[PortfolioState]:
        """
        Update portfolio state with deltas.
        
        Creates a new state snapshot.
        
        Note: This is a simplified version for S4.1.
        S4.2 will add full position/trade tracking.
        """
        current_state = self.get_portfolio_state(simulation_id)
        if not current_state:
            return None
        
        simulation = portfolio_repository.get_simulation(simulation_id)
        if not simulation:
            return None
        
        # Calculate new values
        new_equity = current_state.equity_usd + equity_delta
        new_cash = current_state.cash_usd + cash_delta
        new_used = new_equity - new_cash
        
        # Update high water mark and drawdown
        new_peak = max(current_state.peak_equity_usd, new_equity)
        drawdown_usd = new_peak - new_equity
        drawdown_pct = drawdown_usd / new_peak if new_peak > 0 else 0
        
        # Calculate PnL
        initial_capital = simulation.total_capital_usd
        total_pnl_usd = new_equity - initial_capital
        total_pnl_pct = total_pnl_usd / initial_capital if initial_capital > 0 else 0
        
        # Create new state
        new_state = PortfolioState(
            simulation_id=simulation_id,
            equity_usd=new_equity,
            cash_usd=new_cash,
            used_capital_usd=new_used,
            free_capital_usd=new_cash,
            margin_used_usd=0.0,
            margin_available_usd=new_cash,
            total_pnl_usd=total_pnl_usd,
            total_pnl_pct=total_pnl_pct,
            peak_equity_usd=new_peak,
            drawdown_usd=drawdown_usd,
            drawdown_pct=drawdown_pct,
            total_positions=current_state.total_positions + positions_delta,
            open_positions=max(0, current_state.open_positions + positions_delta),
            timestamp=datetime.now(timezone.utc),
            version=current_state.version + 1
        )
        
        portfolio_repository.save_state(new_state)
        return new_state
    
    # ===========================================
    # Recalculate from Slots
    # ===========================================
    
    def recalculate_from_slots(
        self,
        simulation_id: str
    ) -> Optional[PortfolioState]:
        """
        Recalculate portfolio state from slot data.
        
        Useful for reconciliation.
        """
        simulation = portfolio_repository.get_simulation(simulation_id)
        if not simulation:
            return None
        
        slots = portfolio_repository.get_slots_by_simulation(simulation_id)
        
        # Sum up slot capitals
        total_current = sum(s.current_capital_usd for s in slots if s.enabled)
        total_pnl = sum(s.realized_pnl_usd + s.unrealized_pnl_usd for s in slots)
        open_positions = sum(1 for s in slots if s.has_open_position)
        
        # Get current state for base values
        current_state = self.get_portfolio_state(simulation_id)
        
        # Calculate equity
        initial_capital = simulation.total_capital_usd
        equity = initial_capital + total_pnl
        used_capital = sum(s.current_capital_usd for s in slots if s.has_open_position)
        cash = equity - used_capital
        
        # Update high water mark
        peak = max(
            current_state.peak_equity_usd if current_state else initial_capital,
            equity
        )
        drawdown_usd = peak - equity
        drawdown_pct = drawdown_usd / peak if peak > 0 else 0
        
        # Create recalculated state
        new_state = PortfolioState(
            simulation_id=simulation_id,
            equity_usd=equity,
            cash_usd=cash,
            used_capital_usd=used_capital,
            free_capital_usd=cash,
            total_pnl_usd=total_pnl,
            total_pnl_pct=total_pnl / initial_capital if initial_capital > 0 else 0,
            peak_equity_usd=peak,
            drawdown_usd=drawdown_usd,
            drawdown_pct=drawdown_pct,
            total_positions=len(slots),
            open_positions=open_positions,
            timestamp=datetime.now(timezone.utc),
            version=(current_state.version + 1) if current_state else 1
        )
        
        portfolio_repository.save_state(new_state)
        return new_state
    
    # ===========================================
    # Health Check
    # ===========================================
    
    def get_health(self) -> Dict[str, Any]:
        """Get service health status"""
        return {
            "service": "PortfolioStateService",
            "status": "healthy",
            "version": "s4.1"
        }


# Global singleton
portfolio_state_service = PortfolioStateService()
