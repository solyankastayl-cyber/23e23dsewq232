"""
Portfolio Broker Service (S4.2)
===============================

Multi-strategy execution broker for portfolio simulation.

Responsibilities:
- Route orders to strategy slots
- Track positions per slot
- Manage fills and trades
- Calculate slot-level PnL
- Emit execution events

Pipeline:
ExecutionDecision → PortfolioBroker → SlotBroker → Fill → Trade
"""

import threading
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
import uuid

from .portfolio_types import (
    PortfolioSimulation,
    PortfolioStrategySlot,
    PortfolioState,
    SlotStatus
)
from .portfolio_broker_types import (
    PortfolioOrder,
    PortfolioPosition,
    PortfolioTrade,
    ExecutionEvent,
    SlotExecutionSummary,
    OrderSide,
    OrderType,
    OrderStatus,
    TradeType,
    PositionSide,
    ExecutionEventType
)
from .portfolio_repository import portfolio_repository
from .portfolio_state_service import portfolio_state_service


# ===========================================
# Slot Broker
# ===========================================

class SlotBroker:
    """
    Broker adapter for a single strategy slot.
    
    Manages orders, positions, and trades for one slot.
    """
    
    def __init__(
        self,
        simulation_id: str,
        slot_id: str,
        strategy_id: str,
        initial_capital: float
    ):
        self.simulation_id = simulation_id
        self.slot_id = slot_id
        self.strategy_id = strategy_id
        
        # Capital
        self.cash_usd = initial_capital
        self.allocated_capital = initial_capital
        
        # Storage
        self.orders: Dict[str, PortfolioOrder] = {}
        self.positions: Dict[str, PortfolioPosition] = {}  # asset -> position
        self.trades: List[PortfolioTrade] = []
        self.events: List[ExecutionEvent] = []
        
        # Current prices
        self.current_prices: Dict[str, float] = {}
        
        # PnL
        self.realized_pnl = 0.0
        
        # Lock
        self._lock = threading.Lock()
    
    def update_price(self, asset: str, price: float, timestamp: str = None) -> None:
        """Update current price for asset"""
        with self._lock:
            self.current_prices[asset] = price
            
            # Update position if exists
            if asset in self.positions:
                pos = self.positions[asset]
                pos.current_price = price
                self._update_position_pnl(pos)
                pos.updated_at = datetime.now(timezone.utc)
    
    def submit_order(
        self,
        asset: str,
        side: OrderSide,
        quantity: float,
        order_type: OrderType = OrderType.MARKET,
        price: Optional[float] = None,
        trade_type: TradeType = TradeType.ENTRY,
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None,
        signal_id: Optional[str] = None
    ) -> PortfolioOrder:
        """
        Submit an order through the slot broker.
        
        For simulation: immediately fills market orders.
        """
        with self._lock:
            current_price = self.current_prices.get(asset, price or 0)
            notional = quantity * current_price
            
            order = PortfolioOrder(
                simulation_id=self.simulation_id,
                slot_id=self.slot_id,
                strategy_id=self.strategy_id,
                asset=asset,
                symbol=asset,
                side=side,
                order_type=order_type,
                quantity=quantity,
                price=price,
                notional_usd=notional,
                status=OrderStatus.NEW,
                trade_type=trade_type,
                source_signal_id=signal_id
            )
            
            self.orders[order.order_id] = order
            
            # Emit event
            self._emit_event(
                ExecutionEventType.ORDER_SUBMITTED,
                order_id=order.order_id,
                data={"asset": asset, "side": side.value, "quantity": quantity}
            )
            
            # For market orders in simulation: immediate fill
            if order_type == OrderType.MARKET:
                self._fill_order(order, current_price, stop_loss, take_profit)
            
            return order
    
    def _fill_order(
        self,
        order: PortfolioOrder,
        fill_price: float,
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None
    ) -> None:
        """Fill an order"""
        # Calculate fee (0.1% taker)
        fee = order.quantity * fill_price * 0.001
        
        # Check cash for BUY
        if order.side == OrderSide.BUY:
            total_cost = (order.quantity * fill_price) + fee
            if total_cost > self.cash_usd:
                order.status = OrderStatus.REJECTED
                self._emit_event(
                    ExecutionEventType.ORDER_REJECTED,
                    order_id=order.order_id,
                    data={"reason": "Insufficient cash"}
                )
                return
        
        # Update order
        order.filled_quantity = order.quantity
        order.filled_price = fill_price
        order.filled_notional_usd = order.quantity * fill_price
        order.fee_usd = fee
        order.status = OrderStatus.FILLED
        order.filled_at = datetime.now(timezone.utc)
        
        # Update cash and position
        self._apply_fill(order, stop_loss, take_profit)
        
        # Emit event
        self._emit_event(
            ExecutionEventType.ORDER_FILLED,
            order_id=order.order_id,
            data={"price": fill_price, "quantity": order.quantity, "fee": fee}
        )
    
    def _apply_fill(
        self,
        order: PortfolioOrder,
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None
    ) -> None:
        """Apply fill to position and cash"""
        asset = order.asset
        
        if order.side == OrderSide.BUY:
            # Deduct cash
            self.cash_usd -= (order.filled_notional_usd + order.fee_usd)
            
            # Update or create position
            if asset in self.positions and self.positions[asset].side != PositionSide.FLAT:
                pos = self.positions[asset]
                # Average entry
                old_notional = pos.size * pos.entry_price
                new_notional = order.filled_quantity * order.filled_price
                pos.size += order.filled_quantity
                pos.entry_price = (old_notional + new_notional) / pos.size if pos.size > 0 else 0
                pos.current_price = order.filled_price
                pos.notional_usd = pos.size * pos.current_price
                pos.updated_at = datetime.now(timezone.utc)
                
                self._emit_event(
                    ExecutionEventType.POSITION_UPDATED,
                    position_id=pos.position_id,
                    data={"new_size": pos.size, "new_entry": pos.entry_price}
                )
            else:
                pos = PortfolioPosition(
                    simulation_id=self.simulation_id,
                    slot_id=self.slot_id,
                    strategy_id=self.strategy_id,
                    asset=asset,
                    symbol=asset,
                    side=PositionSide.LONG,
                    size=order.filled_quantity,
                    entry_price=order.filled_price,
                    current_price=order.filled_price,
                    notional_usd=order.filled_notional_usd,
                    stop_loss=stop_loss,
                    take_profit=take_profit,
                    opened_at=datetime.now(timezone.utc)
                )
                self.positions[asset] = pos
                
                # Create open trade
                trade = PortfolioTrade(
                    simulation_id=self.simulation_id,
                    slot_id=self.slot_id,
                    strategy_id=self.strategy_id,
                    asset=asset,
                    symbol=asset,
                    side="LONG",
                    entry_price=order.filled_price,
                    entry_quantity=order.filled_quantity,
                    entry_notional_usd=order.filled_notional_usd,
                    entry_timestamp=order.filled_at,
                    entry_order_id=order.order_id,
                    is_closed=False
                )
                self.trades.append(trade)
                
                self._emit_event(
                    ExecutionEventType.POSITION_OPENED,
                    position_id=pos.position_id,
                    data={"side": "LONG", "size": pos.size, "entry": pos.entry_price}
                )
        
        elif order.side == OrderSide.SELL:
            if asset not in self.positions:
                return
            
            pos = self.positions[asset]
            
            # Calculate PnL
            pnl = (order.filled_price - pos.entry_price) * order.filled_quantity - order.fee_usd
            self.realized_pnl += pnl
            
            # Add cash
            self.cash_usd += order.filled_notional_usd - order.fee_usd
            
            # Find open trade and close it
            for trade in reversed(self.trades):
                if trade.asset == asset and not trade.is_closed:
                    trade.exit_price = order.filled_price
                    trade.exit_quantity = order.filled_quantity
                    trade.exit_notional_usd = order.filled_notional_usd
                    trade.exit_timestamp = order.filled_at
                    trade.exit_order_id = order.order_id
                    trade.realized_pnl_usd = pnl
                    trade.realized_pnl_pct = pnl / trade.entry_notional_usd if trade.entry_notional_usd > 0 else 0
                    trade.total_fees_usd = order.fee_usd * 2  # Entry + exit
                    if trade.entry_timestamp and trade.exit_timestamp:
                        trade.holding_period_seconds = int((trade.exit_timestamp - trade.entry_timestamp).total_seconds())
                    trade.is_closed = True
                    break
            
            # Update position
            pos.size -= order.filled_quantity
            if pos.size <= 0:
                pos.size = 0
                pos.side = PositionSide.FLAT
                pos.unrealized_pnl_usd = 0
                pos.unrealized_pnl_pct = 0
                
                self._emit_event(
                    ExecutionEventType.POSITION_CLOSED,
                    position_id=pos.position_id,
                    data={"pnl": pnl}
                )
            else:
                pos.updated_at = datetime.now(timezone.utc)
                self._update_position_pnl(pos)
    
    def _update_position_pnl(self, pos: PortfolioPosition) -> None:
        """Update unrealized PnL for position"""
        if pos.size <= 0 or pos.side == PositionSide.FLAT:
            pos.unrealized_pnl_usd = 0
            pos.unrealized_pnl_pct = 0
            return
        
        if pos.side == PositionSide.LONG:
            pos.unrealized_pnl_usd = (pos.current_price - pos.entry_price) * pos.size
        elif pos.side == PositionSide.SHORT:
            pos.unrealized_pnl_usd = (pos.entry_price - pos.current_price) * pos.size
        
        entry_notional = pos.entry_price * pos.size
        pos.unrealized_pnl_pct = pos.unrealized_pnl_usd / entry_notional if entry_notional > 0 else 0
        pos.notional_usd = pos.size * pos.current_price
    
    def _emit_event(
        self,
        event_type: ExecutionEventType,
        order_id: str = None,
        position_id: str = None,
        trade_id: str = None,
        data: Dict[str, Any] = None
    ) -> None:
        """Emit execution event"""
        event = ExecutionEvent(
            simulation_id=self.simulation_id,
            slot_id=self.slot_id,
            event_type=event_type,
            order_id=order_id,
            position_id=position_id,
            trade_id=trade_id,
            data=data or {}
        )
        self.events.append(event)
    
    def get_equity(self) -> float:
        """Get total equity for slot"""
        unrealized = sum(p.unrealized_pnl_usd for p in self.positions.values())
        position_value = sum(p.notional_usd for p in self.positions.values() if p.side != PositionSide.FLAT)
        return self.cash_usd + position_value
    
    def get_execution_summary(self) -> SlotExecutionSummary:
        """Get execution summary for slot"""
        filled = [o for o in self.orders.values() if o.status == OrderStatus.FILLED]
        rejected = [o for o in self.orders.values() if o.status == OrderStatus.REJECTED]
        closed_trades = [t for t in self.trades if t.is_closed]
        winning = [t for t in closed_trades if t.realized_pnl_usd > 0]
        
        # Get current position
        open_pos = None
        for pos in self.positions.values():
            if pos.side != PositionSide.FLAT:
                open_pos = pos
                break
        
        return SlotExecutionSummary(
            slot_id=self.slot_id,
            strategy_id=self.strategy_id,
            total_orders=len(self.orders),
            filled_orders=len(filled),
            rejected_orders=len(rejected),
            total_trades=len(closed_trades),
            winning_trades=len(winning),
            losing_trades=len(closed_trades) - len(winning),
            has_open_position=open_pos is not None,
            position_side=open_pos.side.value if open_pos else "FLAT",
            position_size=open_pos.size if open_pos else 0,
            realized_pnl_usd=self.realized_pnl,
            unrealized_pnl_usd=sum(p.unrealized_pnl_usd for p in self.positions.values()),
            total_fees_usd=sum(o.fee_usd for o in filled)
        )


# ===========================================
# Portfolio Broker Service
# ===========================================

class PortfolioBrokerService:
    """
    Multi-strategy execution broker.
    
    Manages SlotBrokers for each strategy slot.
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
        
        # Simulation -> Slot Brokers
        self._brokers: Dict[str, Dict[str, SlotBroker]] = {}
        
        self._initialized = True
        print("[PortfolioBrokerService] Initialized")
    
    # ===========================================
    # Initialize Brokers
    # ===========================================
    
    def initialize_simulation(
        self,
        simulation_id: str
    ) -> Dict[str, SlotBroker]:
        """
        Initialize slot brokers for a simulation.
        
        Creates one SlotBroker per strategy slot.
        """
        simulation = portfolio_repository.get_simulation(simulation_id)
        if not simulation:
            return {}
        
        slots = portfolio_repository.get_slots_by_simulation(simulation_id)
        
        brokers = {}
        for slot in slots:
            broker = SlotBroker(
                simulation_id=simulation_id,
                slot_id=slot.slot_id,
                strategy_id=slot.strategy_id,
                initial_capital=slot.allocated_capital_usd
            )
            brokers[slot.slot_id] = broker
        
        self._brokers[simulation_id] = brokers
        
        print(f"[PortfolioBrokerService] Initialized {len(brokers)} slot brokers for {simulation_id}")
        return brokers
    
    def get_slot_broker(
        self,
        simulation_id: str,
        slot_id: str
    ) -> Optional[SlotBroker]:
        """Get broker for a specific slot"""
        if simulation_id not in self._brokers:
            return None
        return self._brokers[simulation_id].get(slot_id)
    
    def get_all_slot_brokers(
        self,
        simulation_id: str
    ) -> Dict[str, SlotBroker]:
        """Get all slot brokers for simulation"""
        return self._brokers.get(simulation_id, {})
    
    # ===========================================
    # Order Routing
    # ===========================================
    
    def submit_order(
        self,
        simulation_id: str,
        slot_id: str,
        asset: str,
        side: str,
        quantity: float,
        order_type: str = "MARKET",
        price: Optional[float] = None,
        trade_type: str = "ENTRY",
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None,
        signal_id: Optional[str] = None
    ) -> Optional[PortfolioOrder]:
        """
        Submit order through portfolio broker.
        
        Routes to appropriate slot broker.
        """
        broker = self.get_slot_broker(simulation_id, slot_id)
        if not broker:
            return None
        
        order = broker.submit_order(
            asset=asset,
            side=OrderSide[side],
            quantity=quantity,
            order_type=OrderType[order_type],
            price=price,
            trade_type=TradeType[trade_type],
            stop_loss=stop_loss,
            take_profit=take_profit,
            signal_id=signal_id
        )
        
        # Update slot in repository
        self._sync_slot_state(simulation_id, slot_id)
        
        return order
    
    # ===========================================
    # Price Updates
    # ===========================================
    
    def update_prices(
        self,
        simulation_id: str,
        prices: Dict[str, float],
        timestamp: str = None
    ) -> None:
        """
        Update prices across all slot brokers.
        
        Called on each market tick.
        """
        brokers = self.get_all_slot_brokers(simulation_id)
        
        for asset, price in prices.items():
            for broker in brokers.values():
                broker.update_price(asset, price, timestamp)
        
        # Update portfolio state
        self._update_portfolio_state(simulation_id)
    
    # ===========================================
    # State Sync
    # ===========================================
    
    def _sync_slot_state(self, simulation_id: str, slot_id: str) -> None:
        """Sync slot broker state to repository"""
        broker = self.get_slot_broker(simulation_id, slot_id)
        if not broker:
            return
        
        slot = portfolio_repository.get_slot(slot_id)
        if not slot:
            return
        
        # Update slot
        slot.current_capital_usd = broker.get_equity()
        slot.realized_pnl_usd = broker.realized_pnl
        slot.unrealized_pnl_usd = sum(p.unrealized_pnl_usd for p in broker.positions.values())
        slot.total_trades = len([t for t in broker.trades if t.is_closed])
        slot.has_open_position = any(p.side != PositionSide.FLAT for p in broker.positions.values())
        
        portfolio_repository.update_slot(slot)
    
    def _update_portfolio_state(self, simulation_id: str) -> None:
        """Update portfolio state from all brokers"""
        brokers = self.get_all_slot_brokers(simulation_id)
        if not brokers:
            return
        
        simulation = portfolio_repository.get_simulation(simulation_id)
        if not simulation:
            return
        
        # Aggregate from all brokers
        total_equity = sum(b.get_equity() for b in brokers.values())
        total_cash = sum(b.cash_usd for b in brokers.values())
        total_realized = sum(b.realized_pnl for b in brokers.values())
        total_unrealized = sum(
            sum(p.unrealized_pnl_usd for p in b.positions.values())
            for b in brokers.values()
        )
        open_positions = sum(
            1 for b in brokers.values()
            for p in b.positions.values()
            if p.side != PositionSide.FLAT
        )
        
        # Get current state
        current_state = portfolio_repository.get_latest_state(simulation_id)
        
        # Calculate peak and drawdown
        peak = max(current_state.peak_equity_usd if current_state else simulation.total_capital_usd, total_equity)
        drawdown_usd = peak - total_equity
        drawdown_pct = drawdown_usd / peak if peak > 0 else 0
        
        # Create new state
        initial_capital = simulation.total_capital_usd
        total_pnl = total_equity - initial_capital
        
        new_state = PortfolioState(
            simulation_id=simulation_id,
            equity_usd=total_equity,
            cash_usd=total_cash,
            used_capital_usd=total_equity - total_cash,
            free_capital_usd=total_cash,
            total_pnl_usd=total_pnl,
            total_pnl_pct=total_pnl / initial_capital if initial_capital > 0 else 0,
            peak_equity_usd=peak,
            drawdown_usd=drawdown_usd,
            drawdown_pct=drawdown_pct,
            total_positions=len(brokers),
            open_positions=open_positions,
            version=(current_state.version + 1) if current_state else 1
        )
        
        portfolio_repository.save_state(new_state)
    
    # ===========================================
    # Queries
    # ===========================================
    
    def get_all_orders(
        self,
        simulation_id: str,
        slot_id: Optional[str] = None
    ) -> List[PortfolioOrder]:
        """Get all orders for simulation"""
        brokers = self.get_all_slot_brokers(simulation_id)
        orders = []
        
        for broker in brokers.values():
            if slot_id is None or broker.slot_id == slot_id:
                orders.extend(broker.orders.values())
        
        return orders
    
    def get_all_positions(
        self,
        simulation_id: str,
        slot_id: Optional[str] = None
    ) -> List[PortfolioPosition]:
        """Get all positions for simulation"""
        brokers = self.get_all_slot_brokers(simulation_id)
        positions = []
        
        for broker in brokers.values():
            if slot_id is None or broker.slot_id == slot_id:
                positions.extend(broker.positions.values())
        
        return positions
    
    def get_all_trades(
        self,
        simulation_id: str,
        slot_id: Optional[str] = None,
        closed_only: bool = False
    ) -> List[PortfolioTrade]:
        """Get all trades for simulation"""
        brokers = self.get_all_slot_brokers(simulation_id)
        trades = []
        
        for broker in brokers.values():
            if slot_id is None or broker.slot_id == slot_id:
                if closed_only:
                    trades.extend([t for t in broker.trades if t.is_closed])
                else:
                    trades.extend(broker.trades)
        
        return trades
    
    def get_execution_summaries(
        self,
        simulation_id: str
    ) -> List[SlotExecutionSummary]:
        """Get execution summaries for all slots"""
        brokers = self.get_all_slot_brokers(simulation_id)
        return [broker.get_execution_summary() for broker in brokers.values()]
    
    # ===========================================
    # Cleanup
    # ===========================================
    
    def cleanup_simulation(self, simulation_id: str) -> bool:
        """Cleanup brokers for simulation"""
        if simulation_id in self._brokers:
            del self._brokers[simulation_id]
            return True
        return False
    
    def get_health(self) -> Dict[str, Any]:
        """Get service health"""
        return {
            "service": "PortfolioBrokerService",
            "status": "healthy",
            "version": "s4.2",
            "active_simulations": len(self._brokers),
            "total_slot_brokers": sum(len(b) for b in self._brokers.values())
        }


# Global singleton
portfolio_broker_service = PortfolioBrokerService()


# Import fix for types
from .portfolio_types import PortfolioState
