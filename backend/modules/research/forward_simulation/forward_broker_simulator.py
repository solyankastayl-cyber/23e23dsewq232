"""
Forward Broker Simulator
========================

Virtual broker for order execution (PHASE 2.3)
"""

import time
import random
import uuid
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

from .forward_types import (
    SimulatedTrade,
    TradeDirection,
    TradeStatus,
    Candle,
    SimulationConfig
)


@dataclass
class OrderRequest:
    """Order request to broker"""
    symbol: str
    direction: TradeDirection
    size: float
    entry_price: float
    stop_price: float
    target_price: float
    strategy: str = ""
    regime: str = ""
    execution_style: str = ""


@dataclass
class FillResult:
    """Result of order fill"""
    filled: bool = False
    fill_price: float = 0.0
    slippage: float = 0.0
    commission: float = 0.0
    message: str = ""


class BrokerSimulator:
    """
    Simulates broker order execution.
    
    Handles:
    - Order execution with slippage
    - Commission calculation
    - Partial fills (simplified)
    - Stop and target execution
    """
    
    def __init__(self):
        self._default_slippage_pct = 0.05  # 0.05%
        self._default_commission_pct = 0.1  # 0.1%
        
        print("[BrokerSimulator] Initialized (PHASE 2.3)")
    
    def execute_order(
        self,
        order: OrderRequest,
        current_candle: Candle,
        config: SimulationConfig
    ) -> tuple[bool, SimulatedTrade]:
        """
        Execute an order and return a trade.
        """
        
        # Calculate slippage
        slippage_pct = config.slippage_pct / 100
        
        # Slippage direction depends on order direction
        if order.direction == TradeDirection.LONG:
            # Buying - price slips up
            slippage_mult = 1 + random.uniform(0, slippage_pct)
        else:
            # Selling - price slips down
            slippage_mult = 1 - random.uniform(0, slippage_pct)
        
        # Calculate fill price with slippage
        fill_price = order.entry_price * slippage_mult
        
        # Check if price is within candle range
        if fill_price > current_candle.high or fill_price < current_candle.low:
            # Adjust to candle range
            fill_price = max(min(fill_price, current_candle.high), current_candle.low)
        
        # Calculate costs
        slippage_cost = abs(fill_price - order.entry_price) * order.size
        commission_cost = fill_price * order.size * (config.commission_pct / 100)
        
        # Create trade
        trade = SimulatedTrade(
            trade_id=f"sim_{uuid.uuid4().hex[:12]}",
            symbol=order.symbol,
            timeframe="",  # Set by caller
            strategy=order.strategy,
            regime=order.regime,
            execution_style=order.execution_style,
            direction=order.direction,
            status=TradeStatus.OPEN,
            entry_price=fill_price,
            stop_price=order.stop_price,
            target_price=order.target_price,
            position_size=order.size,
            risk_amount=abs(fill_price - order.stop_price) * order.size,
            slippage_cost=slippage_cost,
            commission_cost=commission_cost,
            total_cost=slippage_cost + commission_cost,
            opened_at=int(time.time() * 1000)
        )
        
        return True, trade
    
    def check_stop_target(
        self,
        trade: SimulatedTrade,
        candle: Candle,
        config: SimulationConfig
    ) -> tuple[bool, Optional[TradeStatus], float]:
        """
        Check if stop or target was hit.
        
        Returns: (was_hit, new_status, exit_price)
        """
        
        if trade.status != TradeStatus.OPEN:
            return False, None, 0.0
        
        # Slippage for exit
        slippage_pct = config.slippage_pct / 100
        
        if trade.direction == TradeDirection.LONG:
            # Long position
            # Check stop (price goes below stop)
            if candle.low <= trade.stop_price:
                exit_price = trade.stop_price * (1 - random.uniform(0, slippage_pct))
                exit_price = max(exit_price, candle.low)
                return True, TradeStatus.STOPPED, exit_price
            
            # Check target (price goes above target)
            if candle.high >= trade.target_price:
                exit_price = trade.target_price * (1 - random.uniform(0, slippage_pct * 0.5))
                exit_price = min(exit_price, candle.high)
                return True, TradeStatus.TARGET_HIT, exit_price
        
        else:
            # Short position
            # Check stop (price goes above stop)
            if candle.high >= trade.stop_price:
                exit_price = trade.stop_price * (1 + random.uniform(0, slippage_pct))
                exit_price = min(exit_price, candle.high)
                return True, TradeStatus.STOPPED, exit_price
            
            # Check target (price goes below target)
            if candle.low <= trade.target_price:
                exit_price = trade.target_price * (1 + random.uniform(0, slippage_pct * 0.5))
                exit_price = max(exit_price, candle.low)
                return True, TradeStatus.TARGET_HIT, exit_price
        
        return False, None, 0.0
    
    def close_trade(
        self,
        trade: SimulatedTrade,
        exit_price: float,
        status: TradeStatus,
        exit_bar: int,
        config: SimulationConfig
    ) -> SimulatedTrade:
        """
        Close a trade and calculate P&L.
        """
        
        # Calculate exit commission
        exit_commission = exit_price * trade.position_size * (config.commission_pct / 100)
        
        # Calculate P&L
        if trade.direction == TradeDirection.LONG:
            pnl = (exit_price - trade.entry_price) * trade.position_size
        else:
            pnl = (trade.entry_price - exit_price) * trade.position_size
        
        # Subtract costs
        total_costs = trade.total_cost + exit_commission
        net_pnl = pnl - total_costs
        
        # Calculate R-multiple
        risk_per_unit = abs(trade.entry_price - trade.stop_price)
        if risk_per_unit > 0:
            r_multiple = (pnl / trade.position_size) / risk_per_unit
        else:
            r_multiple = 0
        
        # Update trade
        trade.exit_price = exit_price
        trade.status = status
        trade.pnl = net_pnl
        trade.pnl_pct = net_pnl / (trade.entry_price * trade.position_size) if trade.entry_price > 0 else 0
        trade.r_multiple = r_multiple
        trade.commission_cost += exit_commission
        trade.total_cost = total_costs
        trade.exit_bar = exit_bar
        trade.duration_bars = exit_bar - trade.entry_bar
        trade.closed_at = int(time.time() * 1000)
        
        return trade
    
    def calculate_position_size(
        self,
        capital: float,
        entry_price: float,
        stop_price: float,
        risk_pct: float,
        max_size_pct: float
    ) -> float:
        """
        Calculate position size based on risk.
        """
        
        risk_amount = capital * (risk_pct / 100)
        risk_per_unit = abs(entry_price - stop_price)
        
        if risk_per_unit <= 0:
            return 0.0
        
        # Size based on risk
        size_by_risk = risk_amount / risk_per_unit
        
        # Max size based on capital
        max_position_value = capital * (max_size_pct / 100)
        max_size = max_position_value / entry_price if entry_price > 0 else 0
        
        # Take minimum
        position_size = min(size_by_risk, max_size)
        
        return max(0, position_size)


# Global singleton
broker_simulator = BrokerSimulator()
