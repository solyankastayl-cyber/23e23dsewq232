"""
Execution Gateway Routes

PHASE 39 — Execution Gateway Layer

API endpoints for execution management.

Endpoints:
- POST /api/v1/execution-gateway/execute      - Execute trade request
- GET  /api/v1/execution-gateway/orders       - Get orders
- GET  /api/v1/execution-gateway/fills        - Get fills
- GET  /api/v1/execution-gateway/approvals    - Get pending approvals
- POST /api/v1/execution-gateway/approve      - Approve pending order
- POST /api/v1/execution-gateway/reject       - Reject pending order
- GET  /api/v1/execution-gateway/config       - Get gateway config
- POST /api/v1/execution-gateway/mode         - Set execution mode
- GET  /api/v1/execution-gateway/stats        - Get statistics
"""

from typing import Optional, List
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from .gateway_engine import get_execution_gateway
from .gateway_repository import get_gateway_repository
from .gateway_types import (
    ExecutionRequest,
    ExecutionMode,
    OrderSide,
    OrderType,
    OrderStatus,
)


router = APIRouter(prefix="/api/v1/execution-gateway", tags=["Execution Gateway"])


# ══════════════════════════════════════════════════════════════
# Request/Response Models
# ══════════════════════════════════════════════════════════════

class ExecuteTradeRequest(BaseModel):
    """Request to execute a trade."""
    symbol: str
    side: str  # BUY or SELL
    size_usd: float = Field(gt=0)
    
    order_type: str = "MARKET"
    limit_price: Optional[float] = None
    stop_price: Optional[float] = None
    
    strategy: str = "MANUAL"
    hypothesis_id: Optional[str] = None
    
    preferred_exchange: Optional[str] = None
    urgency: str = "NORMAL"
    reduce_only: bool = False
    max_slippage_bps: float = 50.0


class ApproveOrderRequest(BaseModel):
    """Request to approve pending order."""
    approval_id: str
    approved_by: str = "user"
    approved_size_usd: Optional[float] = None  # Modify size if needed


class RejectOrderRequest(BaseModel):
    """Request to reject pending order."""
    approval_id: str
    rejected_by: str = "user"
    reason: str = ""


class SetModeRequest(BaseModel):
    """Request to set execution mode."""
    mode: str  # PAPER, LIVE, APPROVAL


# ══════════════════════════════════════════════════════════════
# Execute Endpoint
# ══════════════════════════════════════════════════════════════

@router.post("/execute")
async def execute_trade(request: ExecuteTradeRequest):
    """
    Execute a trade through the gateway.
    
    Flow:
    1. Safety Gate check
    2. Exchange routing
    3. Order execution
    4. Portfolio update
    """
    try:
        gateway = get_execution_gateway()
        repo = get_gateway_repository()
        
        # Create execution request
        exec_request = ExecutionRequest(
            symbol=request.symbol.upper(),
            side=OrderSide(request.side.upper()),
            size_usd=request.size_usd,
            order_type=OrderType(request.order_type.upper()),
            limit_price=request.limit_price,
            stop_price=request.stop_price,
            strategy=request.strategy,
            hypothesis_id=request.hypothesis_id,
            preferred_exchange=request.preferred_exchange,
            urgency=request.urgency,
            reduce_only=request.reduce_only,
            max_slippage_bps=request.max_slippage_bps,
        )
        
        # Execute
        result = await gateway.execute(exec_request)
        
        # Save order and result
        order = gateway.get_order(result.order_id) if result.order_id else None
        if order:
            repo.save_order(order)
        repo.save_result(result)
        
        return {
            "status": "ok",
            "phase": "39",
            "execution_result": {
                "request_id": result.request_id,
                "success": result.success,
                "status": result.status.value,
                "order_id": result.order_id,
                "exchange_order_id": result.exchange_order_id,
                "exchange": result.exchange,
                "symbol": result.symbol,
                "side": result.side.value,
                "requested_size_usd": result.requested_size_usd,
                "filled_size_usd": result.filled_size_usd,
                "filled_size_base": result.filled_size_base,
                "avg_price": result.avg_price,
                "expected_price": result.expected_price,
                "slippage_bps": result.slippage_bps,
                "fee": result.fee,
                "total_cost": result.total_cost,
                "safety_check_passed": result.safety_check_passed,
                "safety_adjustments": result.safety_adjustments,
                "failure_reason": result.failure_reason,
                "latency_ms": result.latency_ms,
            },
            "mode": gateway.get_config().execution_mode.value,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ══════════════════════════════════════════════════════════════
# Orders Endpoint
# ══════════════════════════════════════════════════════════════

@router.get("/orders")
async def get_orders(
    status: Optional[str] = None,
    strategy: Optional[str] = None,
    symbol: Optional[str] = None,
    limit: int = Query(default=50, ge=1, le=500),
):
    """Get execution orders."""
    try:
        gateway = get_execution_gateway()
        
        orders = gateway.get_orders(
            status=OrderStatus(status) if status else None
        )
        
        # Filter in memory
        if strategy:
            orders = [o for o in orders if o.strategy == strategy]
        if symbol:
            orders = [o for o in orders if o.symbol.upper() == symbol.upper()]
        
        orders = orders[:limit]
        
        return {
            "status": "ok",
            "phase": "39",
            "count": len(orders),
            "orders": [
                {
                    "order_id": o.order_id,
                    "request_id": o.request_id,
                    "exchange": o.exchange,
                    "symbol": o.symbol,
                    "side": o.side.value,
                    "order_type": o.order_type.value,
                    "size_base": o.size_base,
                    "size_quote": o.size_quote,
                    "expected_price": o.expected_price,
                    "status": o.status.value,
                    "strategy": o.strategy,
                    "exchange_order_id": o.exchange_order_id,
                    "created_at": o.created_at.isoformat(),
                }
                for o in orders
            ],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/orders/{order_id}")
async def get_order(order_id: str):
    """Get specific order by ID."""
    try:
        gateway = get_execution_gateway()
        order = gateway.get_order(order_id)
        
        if not order:
            raise HTTPException(status_code=404, detail=f"Order {order_id} not found")
        
        return {
            "status": "ok",
            "phase": "39",
            "order": {
                "order_id": order.order_id,
                "request_id": order.request_id,
                "exchange": order.exchange,
                "symbol": order.symbol,
                "exchange_symbol": order.exchange_symbol,
                "side": order.side.value,
                "order_type": order.order_type.value,
                "size_base": order.size_base,
                "size_quote": order.size_quote,
                "limit_price": order.limit_price,
                "stop_price": order.stop_price,
                "expected_price": order.expected_price,
                "time_in_force": order.time_in_force,
                "reduce_only": order.reduce_only,
                "strategy": order.strategy,
                "status": order.status.value,
                "exchange_order_id": order.exchange_order_id,
                "created_at": order.created_at.isoformat(),
                "submitted_at": order.submitted_at.isoformat() if order.submitted_at else None,
            },
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ══════════════════════════════════════════════════════════════
# Fills Endpoint
# ══════════════════════════════════════════════════════════════

@router.get("/fills")
async def get_fills(
    order_id: Optional[str] = None,
    strategy: Optional[str] = None,
    symbol: Optional[str] = None,
    limit: int = Query(default=50, ge=1, le=500),
):
    """Get execution fills."""
    try:
        gateway = get_execution_gateway()
        
        fills = gateway.get_fills(order_id=order_id)
        
        # Filter in memory
        if strategy:
            fills = [f for f in fills if f.strategy == strategy]
        if symbol:
            fills = [f for f in fills if f.symbol.upper() == symbol.upper()]
        
        fills = fills[:limit]
        
        return {
            "status": "ok",
            "phase": "39",
            "count": len(fills),
            "fills": [
                {
                    "fill_id": f.fill_id,
                    "order_id": f.order_id,
                    "exchange_order_id": f.exchange_order_id,
                    "exchange": f.exchange,
                    "symbol": f.symbol,
                    "side": f.side.value,
                    "filled_size": f.filled_size,
                    "filled_value": f.filled_value,
                    "avg_price": f.avg_price,
                    "expected_price": f.expected_price,
                    "slippage_bps": f.slippage_bps,
                    "fee": f.fee,
                    "is_complete": f.is_complete,
                    "strategy": f.strategy,
                    "filled_at": f.filled_at.isoformat(),
                }
                for f in fills
            ],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ══════════════════════════════════════════════════════════════
# Approvals Endpoints
# ══════════════════════════════════════════════════════════════

@router.get("/approvals")
async def get_pending_approvals():
    """Get pending approval requests."""
    try:
        gateway = get_execution_gateway()
        approvals = gateway.get_pending_approvals()
        
        return {
            "status": "ok",
            "phase": "39",
            "count": len(approvals),
            "approvals": [
                {
                    "approval_id": a.approval_id,
                    "request_id": a.request_id,
                    "order_id": a.order_id,
                    "symbol": a.symbol,
                    "exchange": a.exchange,
                    "side": a.side.value,
                    "size_usd": a.size_usd,
                    "size_base": a.size_base,
                    "order_type": a.order_type.value,
                    "strategy": a.strategy,
                    "hypothesis_id": a.hypothesis_id,
                    "portfolio_risk": a.portfolio_risk,
                    "strategy_risk": a.strategy_risk,
                    "expected_slippage_bps": a.expected_slippage_bps,
                    "liquidity_impact": a.liquidity_impact,
                    "system_recommendation": a.system_recommendation,
                    "recommendation_reason": a.recommendation_reason,
                    "suggested_size_usd": a.suggested_size_usd,
                    "expires_at": a.expires_at.isoformat(),
                    "created_at": a.created_at.isoformat(),
                    "status": a.status,
                }
                for a in approvals
            ],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/approve")
async def approve_order(request: ApproveOrderRequest):
    """Approve a pending order."""
    try:
        gateway = get_execution_gateway()
        repo = get_gateway_repository()
        
        result = await gateway.approve_order(
            approval_id=request.approval_id,
            approved_by=request.approved_by,
            approved_size_usd=request.approved_size_usd,
        )
        
        # Update in DB
        repo.update_approval(
            approval_id=request.approval_id,
            status="APPROVED",
            approved_by=request.approved_by,
            approved_size_usd=request.approved_size_usd,
        )
        
        if result.order_id:
            order = gateway.get_order(result.order_id)
            if order:
                repo.save_order(order)
        
        repo.save_result(result)
        
        return {
            "status": "ok",
            "phase": "39",
            "approval_id": request.approval_id,
            "approved": result.success,
            "execution_result": {
                "request_id": result.request_id,
                "success": result.success,
                "status": result.status.value,
                "order_id": result.order_id,
                "filled_size_usd": result.filled_size_usd,
                "avg_price": result.avg_price,
                "slippage_bps": result.slippage_bps,
            },
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/reject")
async def reject_order(request: RejectOrderRequest):
    """Reject a pending order."""
    try:
        gateway = get_execution_gateway()
        repo = get_gateway_repository()
        
        success = await gateway.reject_order(
            approval_id=request.approval_id,
            rejected_by=request.rejected_by,
            reason=request.reason,
        )
        
        if success:
            repo.update_approval(
                approval_id=request.approval_id,
                status="REJECTED",
                approved_by=request.rejected_by,
            )
        
        return {
            "status": "ok",
            "phase": "39",
            "approval_id": request.approval_id,
            "rejected": success,
            "reason": request.reason,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ══════════════════════════════════════════════════════════════
# Config Endpoints
# ══════════════════════════════════════════════════════════════

@router.get("/config")
async def get_config():
    """Get gateway configuration."""
    try:
        gateway = get_execution_gateway()
        config = gateway.get_config()
        
        return {
            "status": "ok",
            "phase": "39",
            "config": {
                "execution_mode": config.execution_mode.value,
                "max_single_order_usd": config.max_single_order_usd,
                "daily_loss_limit_usd": config.daily_loss_limit_usd,
                "max_portfolio_risk": config.max_portfolio_risk,
                "max_slippage_bps": config.max_slippage_bps,
                "approval_timeout_seconds": config.approval_timeout_seconds,
                "default_exchange": config.default_exchange,
                "testnet_mode": config.testnet_mode,
                "max_retries": config.max_retries,
            },
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/mode")
async def set_execution_mode(request: SetModeRequest):
    """Set execution mode."""
    try:
        gateway = get_execution_gateway()
        
        mode = ExecutionMode(request.mode.upper())
        gateway.set_execution_mode(mode)
        
        return {
            "status": "ok",
            "phase": "39",
            "execution_mode": mode.value,
            "message": f"Execution mode set to {mode.value}",
        }
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid mode: {request.mode}. Valid modes: PAPER, LIVE, APPROVAL"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ══════════════════════════════════════════════════════════════
# Stats Endpoint
# ══════════════════════════════════════════════════════════════

@router.get("/stats")
async def get_stats():
    """Get gateway statistics."""
    try:
        gateway = get_execution_gateway()
        repo = get_gateway_repository()
        
        daily_stats = gateway.get_daily_stats()
        fill_stats = repo.get_fill_statistics(hours_back=24)
        
        return {
            "status": "ok",
            "phase": "39",
            "mode": gateway.get_config().execution_mode.value,
            "daily_stats": daily_stats,
            "fill_stats": fill_stats,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ══════════════════════════════════════════════════════════════
# Health Endpoint
# ══════════════════════════════════════════════════════════════

@router.get("/health")
async def health():
    """Gateway health check."""
    try:
        gateway = get_execution_gateway()
        config = gateway.get_config()
        
        return {
            "status": "ok",
            "phase": "39",
            "module": "Execution Gateway",
            "execution_mode": config.execution_mode.value,
            "testnet_mode": config.testnet_mode,
            "endpoints": [
                "POST /api/v1/execution-gateway/execute",
                "GET  /api/v1/execution-gateway/orders",
                "GET  /api/v1/execution-gateway/fills",
                "GET  /api/v1/execution-gateway/approvals",
                "POST /api/v1/execution-gateway/approve",
                "POST /api/v1/execution-gateway/reject",
                "GET  /api/v1/execution-gateway/config",
                "POST /api/v1/execution-gateway/mode",
                "GET  /api/v1/execution-gateway/stats",
            ],
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
