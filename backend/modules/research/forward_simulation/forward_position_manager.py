"""
Forward Position Manager
========================

Manages open positions during simulation (PHASE 2.3)
"""

import time
from typing import Dict, List, Optional, Any

from .forward_types import (
    SimulatedTrade,
    TradeDirection,
    TradeStatus,
    Candle,
    SimulationConfig
)
from .forward_broker_simulator import broker_simulator


class ForwardPositionManager:
    """
    Manages positions during forward simulation.
    
    Tracks:
    - Open positions
    - Position updates (trailing stops, etc.)
    - Position closing
    """
    
    def __init__(self):
        self._open_positions: Dict[str, SimulatedTrade] = {}
        self._closed_positions: List[SimulatedTrade] = []
        
        print("[ForwardPositionManager] Initialized (PHASE 2.3)")
    
    def reset(self):
        """Reset all positions"""
        self._open_positions.clear()
        self._closed_positions.clear()
    
    def open_position(self, trade: SimulatedTrade) -> bool:
        """Add a new open position"""
        if trade.trade_id in self._open_positions:
            return False
        
        self._open_positions[trade.trade_id] = trade
        return True
    
    def get_open_positions(self) -> List[SimulatedTrade]:
        """Get all open positions"""
        return list(self._open_positions.values())
    
    def get_position(self, trade_id: str) -> Optional[SimulatedTrade]:
        """Get specific position"""
        return self._open_positions.get(trade_id)
    
    def close_position(
        self,
        trade_id: str,
        exit_price: float,
        status: TradeStatus,
        exit_bar: int,
        config: SimulationConfig
    ) -> Optional[SimulatedTrade]:
        """Close a position"""
        
        if trade_id not in self._open_positions:
            return None
        
        trade = self._open_positions[trade_id]
        
        # Use broker to close trade
        closed_trade = broker_simulator.close_trade(
            trade=trade,
            exit_price=exit_price,
            status=status,
            exit_bar=exit_bar,
            config=config
        )
        
        # Move from open to closed
        del self._open_positions[trade_id]
        self._closed_positions.append(closed_trade)
        
        return closed_trade
    
    def update_positions(
        self,
        candle: Candle,
        bar_index: int,
        config: SimulationConfig
    ) -> List[SimulatedTrade]:
        """
        Update all open positions with new candle.
        Check stops and targets.
        
        Returns list of closed trades.
        """
        
        closed_trades = []
        positions_to_close = []
        
        for trade_id, trade in self._open_positions.items():
            # Check stop/target hit
            was_hit, new_status, exit_price = broker_simulator.check_stop_target(
                trade=trade,
                candle=candle,
                config=config
            )
            
            if was_hit and new_status:
                positions_to_close.append((trade_id, exit_price, new_status))
        
        # Close positions (done separately to avoid dict modification during iteration)
        for trade_id, exit_price, status in positions_to_close:
            closed = self.close_position(
                trade_id=trade_id,
                exit_price=exit_price,
                status=status,
                exit_bar=bar_index,
                config=config
            )
            if closed:
                closed_trades.append(closed)
        
        return closed_trades
    
    def update_trailing_stop(
        self,
        trade_id: str,
        candle: Candle,
        atr: float
    ) -> bool:
        """
        Update trailing stop for a position.
        Uses ATR-based trailing.
        """
        
        if trade_id not in self._open_positions:
            return False
        
        trade = self._open_positions[trade_id]
        
        # Only trail if in profit
        if trade.direction == TradeDirection.LONG:
            current_profit = candle.close - trade.entry_price
            if current_profit > 0:
                # New stop at close - 2 ATR
                new_stop = candle.close - (2 * atr)
                if new_stop > trade.stop_price:
                    trade.stop_price = new_stop
                    return True
        else:
            current_profit = trade.entry_price - candle.close
            if current_profit > 0:
                # New stop at close + 2 ATR
                new_stop = candle.close + (2 * atr)
                if new_stop < trade.stop_price:
                    trade.stop_price = new_stop
                    return True
        
        return False
    
    def get_closed_positions(self) -> List[SimulatedTrade]:
        """Get all closed positions"""
        return self._closed_positions.copy()
    
    def get_all_trades(self) -> List[SimulatedTrade]:
        """Get all trades (open + closed)"""
        return self.get_open_positions() + self._closed_positions
    
    def get_position_count(self) -> int:
        """Get count of open positions"""
        return len(self._open_positions)
    
    def get_total_exposure(self) -> float:
        """Get total exposure value"""
        return sum(
            t.entry_price * t.position_size
            for t in self._open_positions.values()
        )
    
    def can_open_new_position(
        self,
        capital: float,
        max_exposure_pct: float = 30.0,
        max_positions: int = 5
    ) -> bool:
        """Check if new position can be opened"""
        
        # Check position count
        if self.get_position_count() >= max_positions:
            return False
        
        # Check exposure
        current_exposure = self.get_total_exposure()
        max_exposure = capital * (max_exposure_pct / 100)
        
        if current_exposure >= max_exposure:
            return False
        
        return True


# Global singleton
forward_position_manager = ForwardPositionManager()
