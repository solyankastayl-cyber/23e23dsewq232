"""Order Projection (P1 - FSM Integration)

Локальное состояние ордеров = проекция из event stream.
Проекция не «додумывает» состояние — только apply(event).

P1: Strict FSM validation - prevents invalid state transitions.
"""

from typing import Dict, Optional, List
from pydantic import BaseModel
from ..events.execution_event_types import ExecutionEvent, EXECUTION_EVENT_TYPES
from ..state.order_state_machine import (
    OrderState,
    OrderStateMachine,
    OrderStateViolationError,
    get_next_state_from_event
)
import logging

logger = logging.getLogger(__name__)


class Order(BaseModel):
    """Проекция ордера (состояние = результат replay events)"""
    client_order_id: str
    exchange_order_id: Optional[str] = None
    symbol: str
    side: str  # BUY | SELL
    order_type: str  # LIMIT | MARKET
    price: Optional[float] = None
    requested_qty: float
    filled_qty: float = 0.0
    avg_fill_price: Optional[float] = None
    status: str  # P1: Now uses OrderState values (PENDING, ACKNOWLEDGED, etc.)
    exchange: str  # binance | paper | simulation
    reject_reason: Optional[str] = None


class OrderProjection:
    """
    Проекция состояния ордеров.
    
    P1: With FSM validation - strict state transitions.
    """

    def __init__(self):
        self._orders: Dict[str, Order] = {}  # client_order_id -> Order

    def apply(self, event: ExecutionEvent, strict: bool = False) -> None:
        """
        Применить событие к проекции с FSM validation.
        
        P1: Validates state transitions via OrderStateMachine.
        
        Args:
            event: Execution event to apply
            strict: If True, enforce strict FSM (raises on violation).
                   If False, allow exchange reconciliation (log warning only).
                   Default False for exchange events tolerance.
        """
        client_order_id = event.client_order_id

        if event.event_type == EXECUTION_EVENT_TYPES["ORDER_SUBMIT_REQUESTED"]:
            # Создаём новый ордер в состоянии PENDING
            payload = event.payload
            self._orders[client_order_id] = Order(
                client_order_id=client_order_id,
                symbol=event.symbol,
                side=payload.get("side", "BUY"),
                order_type=payload.get("order_type", "LIMIT"),
                price=payload.get("price"),
                requested_qty=payload.get("qty", 0.0),
                status=OrderState.PENDING.value,
                exchange=event.exchange
            )
            logger.info(f"Order projection: {OrderState.PENDING.value} | {client_order_id}")

        elif event.event_type == EXECUTION_EVENT_TYPES["ORDER_ACKNOWLEDGED"]:
            # Transition: PENDING/SUBMITTED → ACKNOWLEDGED
            if client_order_id in self._orders:
                order = self._orders[client_order_id]
                current_state = OrderState(order.status)
                next_state = OrderState.ACKNOWLEDGED
                
                # P1: Validate transition (relaxed for exchange events)
                OrderStateMachine.validate_transition(
                    current_state,
                    next_state,
                    client_order_id,
                    strict=strict
                )
                
                order.status = next_state.value
                order.exchange_order_id = event.exchange_order_id
                logger.info(
                    f"Order projection: {current_state.value} → {next_state.value} | "
                    f"{client_order_id} | exchange_id={event.exchange_order_id}"
                )

        elif event.event_type == EXECUTION_EVENT_TYPES["ORDER_REJECTED"]:
            # Transition: * → REJECTED
            if client_order_id in self._orders:
                order = self._orders[client_order_id]
                current_state = OrderState(order.status)
                next_state = OrderState.REJECTED
                
                # P1: Validate transition (relaxed for exchange events)
                OrderStateMachine.validate_transition(
                    current_state,
                    next_state,
                    client_order_id,
                    strict=strict
                )
                
                order.status = next_state.value
                order.reject_reason = event.payload.get("reason")
                logger.info(
                    f"Order projection: {current_state.value} → {next_state.value} | "
                    f"{client_order_id} | reason={event.payload.get('reason')}"
                )

        elif event.event_type == EXECUTION_EVENT_TYPES["ORDER_FILL_RECORDED"]:
            # Transition: ACKNOWLEDGED → PARTIALLY_FILLED or FILLED
            if client_order_id in self._orders:
                order = self._orders[client_order_id]
                current_state = OrderState(order.status)
                
                # Update fill quantities
                fill_qty = event.payload.get("fill_qty", 0.0)
                fill_price = event.payload.get("fill_price", 0.0)
                order.filled_qty += fill_qty

                # Recalculate avg_fill_price (weighted average)
                if order.avg_fill_price is None:
                    order.avg_fill_price = fill_price
                else:
                    total_filled = order.filled_qty
                    if total_filled > 0:
                        order.avg_fill_price = (
                            (order.avg_fill_price * (total_filled - fill_qty) + fill_price * fill_qty) / total_filled
                        )

                # Determine next state based on fill qty
                next_state = get_next_state_from_event(
                    event.event_type,
                    current_state,
                    order.filled_qty,
                    order.requested_qty
                )
                
                # P1: Validate transition (relaxed for exchange events)
                OrderStateMachine.validate_transition(
                    current_state,
                    next_state,
                    client_order_id,
                    strict=strict
                )
                
                order.status = next_state.value
                logger.info(
                    f"Order projection: {current_state.value} → {next_state.value} | "
                    f"{client_order_id} | filled={order.filled_qty}/{order.requested_qty}"
                )

        elif event.event_type == EXECUTION_EVENT_TYPES["FILL_PARTIAL"]:
            # P1.1D: Частичное исполнение от биржи
            if client_order_id in self._orders:
                order = self._orders[client_order_id]
                current_state = OrderState(order.status)
                
                # Update fill from exchange event
                fill_qty = event.payload.get("executed_qty", 0.0)
                fill_price = event.payload.get("price", 0.0)
                cumulative_filled = event.payload.get("cumulative_filled_qty", fill_qty)
                
                order.filled_qty = cumulative_filled
                
                # Update avg price
                if fill_price > 0:
                    order.avg_fill_price = fill_price
                
                # Determine state
                next_state = OrderState.PARTIALLY_FILLED
                
                # P1: Validate transition (relaxed for exchange events)
                OrderStateMachine.validate_transition(
                    current_state,
                    next_state,
                    client_order_id,
                    strict=strict
                )
                
                order.status = next_state.value
                logger.info(
                    f"Order projection: {current_state.value} → {next_state.value} | "
                    f"{client_order_id} | filled={order.filled_qty}/{order.requested_qty}"
                )

        elif event.event_type == EXECUTION_EVENT_TYPES["FILL_FULL"]:
            # P1.1D: Full fill от биржи
            if client_order_id in self._orders:
                order = self._orders[client_order_id]
                current_state = OrderState(order.status)
                
                # Update final fill
                cumulative_filled = event.payload.get("cumulative_filled_qty", order.requested_qty)
                fill_price = event.payload.get("price", 0.0)
                
                order.filled_qty = cumulative_filled
                if fill_price > 0:
                    order.avg_fill_price = fill_price
                
                next_state = OrderState.FILLED
                
                # P1: Validate transition (relaxed for exchange events)
                OrderStateMachine.validate_transition(
                    current_state,
                    next_state,
                    client_order_id,
                    strict=strict
                )
                
                order.status = next_state.value
                logger.info(
                    f"Order projection: {current_state.value} → {next_state.value} | "
                    f"{client_order_id} | FULLY FILLED"
                )

        elif event.event_type == EXECUTION_EVENT_TYPES["ORDER_CANCELED"]:
            # Transition: * → CANCELED
            if client_order_id in self._orders:
                order = self._orders[client_order_id]
                current_state = OrderState(order.status)
                next_state = OrderState.CANCELED
                
                # P1: Validate transition (relaxed for exchange events)
                OrderStateMachine.validate_transition(
                    current_state,
                    next_state,
                    client_order_id,
                    strict=strict
                )
                
                order.status = next_state.value
                logger.info(
                    f"Order projection: {current_state.value} → {next_state.value} | "
                    f"{client_order_id}"
                )

    def get_order(self, client_order_id: str) -> Optional[Order]:
        """Получить ордер по ID"""
        return self._orders.get(client_order_id)

    def list_orders(self, limit: int = 20) -> List[Order]:
        """Список всех ордеров (для debug)"""
        orders = list(self._orders.values())
        return orders[-limit:]
