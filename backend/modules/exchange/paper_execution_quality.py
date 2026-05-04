"""Paper Execution Quality — Helper methods for realistic execution simulation

Отдельный модуль для execution quality logic, чтобы не раздувать paper_adapter.
"""

import uuid
import asyncio
import random
import time
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timezone
import logging

from motor.motor_asyncio import AsyncIOMotorClient

from .execution_quality_config import (
    calculate_slippage,
    calculate_fee,
    should_partial_fill,
    REJECTION_CONFIG,
    PARTIAL_FILL_CONFIG,
)

logger = logging.getLogger(__name__)


class OrderRejection(Exception):
    """Exception for order rejections with reason."""
    def __init__(self, reason: str, message: str):
        self.reason = reason
        self.message = message
        super().__init__(message)


async def validate_order(
    order_request: Any,
    account_balance: float,
    open_positions_count: int,
    db: Any
) -> None:
    """Validate order before execution.
    
    Raises OrderRejection if validation fails.
    
    Checks:
    - Duplicate clientOrderId
    - Minimum notional
    - Sufficient balance
    - Max positions limit
    - Lot size validity
    
    Args:
        order_request: OrderRequest object
        account_balance: Current account balance in USDT
        open_positions_count: Number of currently open positions
        db: MongoDB database handle
    
    Raises:
        OrderRejection: With specific reason code
    """
    # Check duplicate client_order_id
    if order_request.client_order_id:
        existing = await db.exchange_orders.find_one({
            "client_order_id": order_request.client_order_id
        })
        if existing:
            raise OrderRejection(
                "DUPLICATE_CLIENT_ORDER_ID",
                f"Order with client_order_id={order_request.client_order_id} already exists"
            )
    
    # Estimate notional (use price from order if LIMIT, or estimate from current market)
    # For MARKET orders, we'll need to estimate based on typical price
    # Simplified: assume USDT pairs, so quantity IS the base amount
    estimated_price = order_request.price if order_request.price else 1.0
    
    # For crypto pairs like BTCUSDT, need to multiply by mark price
    # This is a simplified check - in real implementation, fetch current mark price
    if "USDT" in order_request.symbol or "USD" in order_request.symbol:
        # Symbol is likely XXX/USDT, quantity is in XXX
        # We need mark price to calculate notional
        # For validation purposes, use a reasonable estimate or skip for MARKET
        if order_request.order_type == "MARKET":
            # MARKET orders will be validated against actual mark price in execution
            # For pre-validation, use minimum check on quantity only
            estimated_notional = order_request.quantity * 10000  # Assume reasonable price
        else:
            estimated_notional = order_request.quantity * estimated_price
    else:
        estimated_notional = order_request.quantity * estimated_price
    
    # Check minimum notional
    if estimated_notional < REJECTION_CONFIG["min_notional_usdt"]:
        raise OrderRejection(
            "MIN_NOTIONAL",
            f"Order notional ${estimated_notional:.2f} < minimum ${REJECTION_CONFIG['min_notional_usdt']}"
        )
    
    # Check sufficient balance (simplified: assume 1:1 for now)
    if estimated_notional > account_balance:
        raise OrderRejection(
            "INSUFFICIENT_BALANCE",
            f"Insufficient balance: need ${estimated_notional:.2f}, have ${account_balance:.2f}"
        )
    
    # Check max positions
    if open_positions_count >= REJECTION_CONFIG["max_positions"]:
        raise OrderRejection(
            "MAX_POSITIONS_REACHED",
            f"Max positions ({REJECTION_CONFIG['max_positions']}) reached"
        )
    
    # Check lot size
    if order_request.quantity < REJECTION_CONFIG["min_lot_size"]:
        raise OrderRejection(
            "LOT_SIZE_INVALID",
            f"Quantity {order_request.quantity} < minimum lot size {REJECTION_CONFIG['min_lot_size']}"
        )


async def execute_market_order(
    order_request: Any,
    mark_price: float,
    account_id: str,
    db: Any
) -> Dict[str, Any]:
    """Execute MARKET order with full execution quality simulation.
    
    Features:
    - Realistic slippage (symbol + size dependent)
    - Latency simulation
    - Partial fills for large orders
    - Fee calculation (0.1% taker)
    - Execution quality scoring
    - Multiple fill records
    
    Returns:
        {
            "order_id": str,
            "status": "FILLED" | "PARTIALLY_FILLED",
            "fills": List[dict],  # Fill records
            "total_filled_qty": float,
            "remaining_qty": float,
            "avg_fill_price": float,
            "total_fee": float,
            "execution_quality_score": float,
            "latency_ms": float,
            "slippage_bps": float,
        }
    """
    order_id = f"paper-{uuid.uuid4().hex[:12]}"
    client_order_id = order_request.client_order_id or order_id
    
    # Calculate notional
    notional = order_request.quantity * mark_price
    
    # Check if order should be partially filled
    is_partial, first_fill_ratio = should_partial_fill(notional)
    
    fills = []
    total_filled_qty = 0.0
    total_fee = 0.0
    weighted_price_sum = 0.0
    
    execution_start = time.time()
    
    # FIRST FILL
    # Simulate latency
    latency = random.uniform(0.05, 0.25)
    await asyncio.sleep(latency)
    
    first_qty = order_request.quantity * first_fill_ratio if is_partial else order_request.quantity
    
    # Calculate fill price with realistic slippage
    first_fill_price = calculate_slippage(order_request.symbol, notional * first_fill_ratio, mark_price)
    first_notional = first_qty * first_fill_price
    first_fee = calculate_fee(first_notional, "TAKER")
    
    first_fill = {
        "fill_id": f"fill-{uuid.uuid4().hex[:12]}",
        "order_id": order_id,
        "account_id": account_id,
        "symbol": order_request.symbol,
        "side": order_request.side,
        "quantity": first_qty,
        "price": first_fill_price,
        "fee": first_fee,
        "liquidity": "TAKER",
        "timestamp": datetime.now(timezone.utc),
    }
    
    await db.exchange_fills.insert_one(first_fill.copy())
    fills.append(first_fill)
    
    total_filled_qty += first_qty
    total_fee += first_fee
    weighted_price_sum += first_fill_price * first_qty
    
    logger.info(
        f"[PaperExec] Fill 1/{2 if is_partial else 1}: {order_request.symbol} "
        f"{first_qty:.6f} @ ${first_fill_price:.2f}, fee=${first_fee:.4f}"
    )
    
    # SECOND FILL (if partial)
    if is_partial:
        # Random delay for second fill
        second_delay = random.uniform(
            PARTIAL_FILL_CONFIG["second_fill_delay_min"],
            PARTIAL_FILL_CONFIG["second_fill_delay_max"]
        )
        await asyncio.sleep(second_delay)
        
        remaining_qty = order_request.quantity - first_qty
        
        # Second fill might have slightly different price
        second_fill_price = calculate_slippage(order_request.symbol, remaining_qty * mark_price, mark_price)
        second_notional = remaining_qty * second_fill_price
        second_fee = calculate_fee(second_notional, "TAKER")
        
        second_fill = {
            "fill_id": f"fill-{uuid.uuid4().hex[:12]}",
            "order_id": order_id,
            "account_id": account_id,
            "symbol": order_request.symbol,
            "side": order_request.side,
            "quantity": remaining_qty,
            "price": second_fill_price,
            "fee": second_fee,
            "liquidity": "TAKER",
            "timestamp": datetime.now(timezone.utc),
        }
        
        await db.exchange_fills.insert_one(second_fill.copy())
        fills.append(second_fill)
        
        total_filled_qty += remaining_qty
        total_fee += second_fee
        weighted_price_sum += second_fill_price * remaining_qty
        
        logger.info(
            f"[PaperExec] Fill 2/2: {order_request.symbol} "
            f"{remaining_qty:.6f} @ ${second_fill_price:.2f}, fee=${second_fee:.4f}"
        )
    
    # Calculate metrics
    execution_end = time.time()
    total_latency_ms = (execution_end - execution_start) * 1000
    
    avg_fill_price = weighted_price_sum / total_filled_qty if total_filled_qty > 0 else 0
    
    # Slippage in bps
    slippage_bps = abs((avg_fill_price - mark_price) / mark_price) * 10000
    
    # Execution quality score
    quality_score = calculate_execution_quality_score(
        slippage_bps=slippage_bps,
        latency_ms=total_latency_ms,
        is_partial=is_partial,
        rejected=False,
    )
    
    remaining_qty = order_request.quantity - total_filled_qty
    status = "FILLED" if remaining_qty <= 0.0001 else "PARTIALLY_FILLED"
    
    return {
        "order_id": order_id,
        "client_order_id": client_order_id,
        "status": status,
        "fills": fills,
        "total_filled_qty": total_filled_qty,
        "remaining_qty": remaining_qty,
        "avg_fill_price": avg_fill_price,
        "total_fee": total_fee,
        "execution_quality_score": quality_score,
        "latency_ms": total_latency_ms,
        "slippage_bps": slippage_bps,
    }


def calculate_execution_quality_score(
    slippage_bps: float,
    latency_ms: float,
    is_partial: bool,
    rejected: bool
) -> float:
    """Calculate execution quality score (0-100).
    
    Scoring:
    - Start at 100
    - Deduct for slippage: 2 points per bps
    - Deduct for latency: 1 point per 50ms
    - Deduct 10 points if partial fill
    - Deduct 40 points if rejected
    
    Args:
        slippage_bps: Slippage in basis points
        latency_ms: Execution latency in milliseconds
        is_partial: Whether order was partially filled
        rejected: Whether order was rejected
    
    Returns:
        Quality score (0-100)
    """
    score = 100.0
    
    # Slippage penalty
    score -= slippage_bps * 2.0
    
    # Latency penalty
    score -= latency_ms / 50.0
    
    # Partial fill penalty
    if is_partial:
        score -= 10.0
    
    # Rejection penalty
    if rejected:
        score -= 40.0
    
    # Clamp to [0, 100]
    return max(0.0, min(100.0, score))


def get_quality_grade(score: float) -> str:
    """Convert quality score to letter grade.
    
    A: 90-100
    B: 75-89
    C: 60-74
    D: 0-59
    """
    if score >= 90:
        return "A"
    elif score >= 75:
        return "B"
    elif score >= 60:
        return "C"
    else:
        return "D"
