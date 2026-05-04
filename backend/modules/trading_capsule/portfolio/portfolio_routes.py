"""
Portfolio Routes (S4.1/S4.2/S4.3)
=================================

API endpoints for Portfolio Simulation module.

S4.1 - Core Simulation:
- POST /api/portfolio/simulations - Create simulation
- GET  /api/portfolio/simulations - List simulations
- GET  /api/portfolio/simulations/{id} - Get simulation
- POST /api/portfolio/simulations/{id}/start - Start simulation
- GET  /api/portfolio/simulations/{id}/state - Get portfolio state
- GET  /api/portfolio/simulations/{id}/slots - Get strategy slots

S4.2 - Execution:
- POST /api/portfolio/simulations/{id}/broker/init - Initialize broker
- POST /api/portfolio/simulations/{id}/orders - Submit order
- GET  /api/portfolio/simulations/{id}/orders - Get orders
- GET  /api/portfolio/simulations/{id}/positions - Get positions
- GET  /api/portfolio/simulations/{id}/trades - Get trades
- POST /api/portfolio/simulations/{id}/prices - Update prices

S4.3 - Metrics:
- GET  /api/portfolio/simulations/{id}/metrics - Portfolio metrics
- GET  /api/portfolio/simulations/{id}/metrics/strategies - Strategy metrics
- GET  /api/portfolio/simulations/{id}/correlation - Correlation matrix
- GET  /api/portfolio/simulations/{id}/equity-curve - Equity curve
- GET  /api/portfolio/simulations/{id}/risk-contributions - Risk contributions
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime

from .portfolio_simulation_service import portfolio_simulation_service
from .portfolio_state_service import portfolio_state_service
from .portfolio_broker_service import portfolio_broker_service
from .portfolio_metrics_service import portfolio_metrics_service
from .portfolio_types import PortfolioSimulationStatus

router = APIRouter(prefix="/api/portfolio", tags=["Portfolio Simulation S4"])


# ===========================================
# Request/Response Models
# ===========================================

class CreateSimulationRequest(BaseModel):
    """Request to create a portfolio simulation"""
    allocation_plan_id: str = Field(..., description="ID of allocation plan to use")
    capital_usd: float = Field(100000, description="Total capital in USD")
    name: str = Field("", description="Optional simulation name")
    description: str = Field("", description="Optional description")
    start_date: str = Field("", description="Optional start date (ISO format)")
    end_date: str = Field("", description="Optional end date (ISO format)")
    tags: List[str] = Field(default_factory=list, description="Optional tags")
    config: Dict[str, Any] = Field(default_factory=dict, description="Optional config overrides")


class UpdateSlotRequest(BaseModel):
    """Request to update a slot"""
    enabled: Optional[bool] = None


# ===========================================
# Create Simulation
# ===========================================

@router.post("/simulations", summary="Create Portfolio Simulation")
async def create_simulation(request: CreateSimulationRequest):
    """
    Create a new portfolio simulation.
    
    Creates:
    - Simulation entity
    - Strategy slots from allocation plan
    - Initial portfolio state
    """
    try:
        simulation = portfolio_simulation_service.create_simulation(
            allocation_plan_id=request.allocation_plan_id,
            total_capital_usd=request.capital_usd,
            name=request.name,
            description=request.description,
            start_date=request.start_date,
            end_date=request.end_date,
            tags=request.tags,
            config=request.config
        )
        
        # Get slots and state
        slots = portfolio_simulation_service.get_slots(simulation.simulation_id)
        state = portfolio_simulation_service.get_portfolio_state(simulation.simulation_id)
        
        return {
            "success": True,
            "simulation": simulation.to_dict(),
            "slots_count": len(slots),
            "state": state.to_dict() if state else None
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ===========================================
# List Simulations
# ===========================================

@router.get("/simulations", summary="List Portfolio Simulations")
async def list_simulations(
    status: Optional[str] = Query(None, description="Filter by status"),
    limit: int = Query(50, ge=1, le=100)
):
    """List all portfolio simulations"""
    status_enum = None
    if status:
        try:
            status_enum = PortfolioSimulationStatus(status)
        except ValueError:
            pass
    
    simulations = portfolio_simulation_service.list_simulations(status_enum, limit)
    
    return {
        "simulations": [s.to_dict() for s in simulations],
        "count": len(simulations)
    }


# ===========================================
# Get Simulation
# ===========================================

@router.get("/simulations/{simulation_id}", summary="Get Portfolio Simulation")
async def get_simulation(simulation_id: str):
    """Get a specific portfolio simulation with full details"""
    simulation = portfolio_simulation_service.get_simulation(simulation_id)
    
    if not simulation:
        raise HTTPException(status_code=404, detail=f"Simulation {simulation_id} not found")
    
    # Get related data
    slots = portfolio_simulation_service.get_slots(simulation_id)
    state = portfolio_simulation_service.get_portfolio_state(simulation_id)
    slots_summary = portfolio_simulation_service.get_slots_summary(simulation_id)
    
    return {
        "simulation": simulation.to_dict(),
        "state": state.to_dict() if state else None,
        "slots": [s.to_dict() for s in slots],
        "slots_summary": slots_summary.to_dict()
    }


# ===========================================
# Start Simulation
# ===========================================

@router.post("/simulations/{simulation_id}/start", summary="Start Simulation")
async def start_simulation(simulation_id: str):
    """Start a portfolio simulation"""
    simulation = portfolio_simulation_service.start_simulation(simulation_id)
    
    if not simulation:
        raise HTTPException(status_code=404, detail=f"Simulation {simulation_id} not found")
    
    return {
        "success": True,
        "simulation": simulation.to_dict(),
        "message": f"Simulation started at {simulation.started_at.isoformat() if simulation.started_at else 'N/A'}"
    }


# ===========================================
# Pause Simulation
# ===========================================

@router.post("/simulations/{simulation_id}/pause", summary="Pause Simulation")
async def pause_simulation(simulation_id: str):
    """Pause a running simulation"""
    simulation = portfolio_simulation_service.pause_simulation(simulation_id)
    
    if not simulation:
        raise HTTPException(status_code=404, detail=f"Simulation {simulation_id} not found")
    
    return {
        "success": True,
        "simulation": simulation.to_dict(),
        "message": "Simulation paused"
    }


# ===========================================
# Complete Simulation
# ===========================================

@router.post("/simulations/{simulation_id}/complete", summary="Complete Simulation")
async def complete_simulation(simulation_id: str):
    """Mark simulation as completed"""
    simulation = portfolio_simulation_service.complete_simulation(simulation_id)
    
    if not simulation:
        raise HTTPException(status_code=404, detail=f"Simulation {simulation_id} not found")
    
    return {
        "success": True,
        "simulation": simulation.to_dict(),
        "message": f"Simulation completed at {simulation.completed_at.isoformat() if simulation.completed_at else 'N/A'}"
    }


# ===========================================
# Delete Simulation
# ===========================================

@router.delete("/simulations/{simulation_id}", summary="Delete Simulation")
async def delete_simulation(simulation_id: str):
    """Delete a simulation and all related data"""
    simulation = portfolio_simulation_service.get_simulation(simulation_id)
    
    if not simulation:
        raise HTTPException(status_code=404, detail=f"Simulation {simulation_id} not found")
    
    success = portfolio_simulation_service.delete_simulation(simulation_id)
    
    return {
        "success": success,
        "message": f"Simulation {simulation_id} deleted"
    }


# ===========================================
# Portfolio State
# ===========================================

@router.get("/simulations/{simulation_id}/state", summary="Get Portfolio State")
async def get_portfolio_state(simulation_id: str):
    """Get current portfolio state"""
    state = portfolio_simulation_service.get_portfolio_state(simulation_id)
    
    if not state:
        raise HTTPException(status_code=404, detail=f"State not found for simulation {simulation_id}")
    
    return state.to_dict()


@router.get("/simulations/{simulation_id}/state/history", summary="Get State History")
async def get_state_history(
    simulation_id: str,
    limit: int = Query(100, ge=1, le=1000)
):
    """Get portfolio state history"""
    history = portfolio_state_service.get_state_history(simulation_id, limit)
    
    return {
        "history": [s.to_dict() for s in history],
        "count": len(history)
    }


# ===========================================
# Strategy Slots
# ===========================================

@router.get("/simulations/{simulation_id}/slots", summary="Get Strategy Slots")
async def get_slots(simulation_id: str):
    """Get all strategy slots for a simulation"""
    slots = portfolio_simulation_service.get_slots(simulation_id)
    summary = portfolio_simulation_service.get_slots_summary(simulation_id)
    
    return {
        "slots": [s.to_dict() for s in slots],
        "summary": summary.to_dict()
    }


@router.put("/simulations/{simulation_id}/slots/{slot_id}", summary="Update Slot")
async def update_slot(
    simulation_id: str,
    slot_id: str,
    request: UpdateSlotRequest
):
    """Update a strategy slot (enable/disable)"""
    if request.enabled is not None:
        if request.enabled:
            slot = portfolio_simulation_service.enable_slot(slot_id)
        else:
            slot = portfolio_simulation_service.disable_slot(slot_id)
        
        if not slot:
            raise HTTPException(status_code=404, detail=f"Slot {slot_id} not found")
        
        return {
            "success": True,
            "slot": slot.to_dict()
        }
    
    raise HTTPException(status_code=400, detail="No update parameters provided")


# ===========================================
# S4.2 - Broker / Execution
# ===========================================

class SubmitOrderRequest(BaseModel):
    """Request to submit an order"""
    slot_id: str = Field(..., description="Target slot ID")
    asset: str = Field(..., description="Asset symbol")
    side: str = Field(..., description="BUY or SELL")
    quantity: float = Field(..., description="Order quantity")
    order_type: str = Field("MARKET", description="MARKET or LIMIT")
    price: Optional[float] = Field(None, description="Limit price")
    trade_type: str = Field("ENTRY", description="ENTRY, EXIT, ADD, PARTIAL_EXIT")
    stop_loss: Optional[float] = Field(None, description="Stop loss price")
    take_profit: Optional[float] = Field(None, description="Take profit price")
    signal_id: Optional[str] = Field(None, description="Source signal ID")


class UpdatePricesRequest(BaseModel):
    """Request to update prices"""
    prices: Dict[str, float] = Field(..., description="Asset prices")
    timestamp: Optional[str] = Field(None, description="Price timestamp")


@router.post("/simulations/{simulation_id}/broker/init", summary="Initialize Broker (S4.2)")
async def initialize_broker(simulation_id: str):
    """
    Initialize portfolio broker for simulation.
    
    Creates slot brokers for each strategy.
    Must be called before submitting orders.
    """
    simulation = portfolio_simulation_service.get_simulation(simulation_id)
    if not simulation:
        raise HTTPException(status_code=404, detail=f"Simulation {simulation_id} not found")
    
    brokers = portfolio_broker_service.initialize_simulation(simulation_id)
    
    return {
        "success": True,
        "simulation_id": simulation_id,
        "slots_initialized": len(brokers),
        "message": f"Initialized {len(brokers)} slot brokers"
    }


@router.post("/simulations/{simulation_id}/orders", summary="Submit Order (S4.2)")
async def submit_order(simulation_id: str, request: SubmitOrderRequest):
    """
    Submit an order through portfolio broker.
    
    Routes to appropriate slot broker and executes.
    """
    order = portfolio_broker_service.submit_order(
        simulation_id=simulation_id,
        slot_id=request.slot_id,
        asset=request.asset,
        side=request.side,
        quantity=request.quantity,
        order_type=request.order_type,
        price=request.price,
        trade_type=request.trade_type,
        stop_loss=request.stop_loss,
        take_profit=request.take_profit,
        signal_id=request.signal_id
    )
    
    if not order:
        raise HTTPException(status_code=400, detail="Failed to submit order. Ensure broker is initialized.")
    
    return {
        "success": True,
        "order": order.to_dict()
    }


@router.get("/simulations/{simulation_id}/orders", summary="Get Orders (S4.2)")
async def get_orders(
    simulation_id: str,
    slot_id: Optional[str] = Query(None, description="Filter by slot")
):
    """Get all orders for simulation"""
    orders = portfolio_broker_service.get_all_orders(simulation_id, slot_id)
    
    return {
        "orders": [o.to_dict() for o in orders],
        "count": len(orders)
    }


@router.get("/simulations/{simulation_id}/positions", summary="Get Positions (S4.2)")
async def get_positions(
    simulation_id: str,
    slot_id: Optional[str] = Query(None, description="Filter by slot")
):
    """Get all positions for simulation"""
    positions = portfolio_broker_service.get_all_positions(simulation_id, slot_id)
    
    # Filter out FLAT positions
    active = [p for p in positions if p.side.value != "FLAT"]
    
    return {
        "positions": [p.to_dict() for p in active],
        "count": len(active)
    }


@router.get("/simulations/{simulation_id}/trades", summary="Get Trades (S4.2)")
async def get_trades(
    simulation_id: str,
    slot_id: Optional[str] = Query(None, description="Filter by slot"),
    closed_only: bool = Query(False, description="Only closed trades")
):
    """Get all trades for simulation"""
    trades = portfolio_broker_service.get_all_trades(simulation_id, slot_id, closed_only)
    
    return {
        "trades": [t.to_dict() for t in trades],
        "count": len(trades)
    }


@router.get("/simulations/{simulation_id}/execution-summary", summary="Execution Summary (S4.2)")
async def get_execution_summary(simulation_id: str):
    """Get execution summary for all slots"""
    summaries = portfolio_broker_service.get_execution_summaries(simulation_id)
    
    return {
        "summaries": [s.to_dict() for s in summaries],
        "count": len(summaries)
    }


@router.post("/simulations/{simulation_id}/prices", summary="Update Prices (S4.2)")
async def update_prices(simulation_id: str, request: UpdatePricesRequest):
    """
    Update prices across all slot brokers.
    
    Called on each market tick during simulation.
    """
    portfolio_broker_service.update_prices(
        simulation_id=simulation_id,
        prices=request.prices,
        timestamp=request.timestamp
    )
    
    return {
        "success": True,
        "assets_updated": list(request.prices.keys())
    }


# ===========================================
# S4.3 - Metrics
# ===========================================

@router.get("/simulations/{simulation_id}/metrics", summary="Portfolio Metrics (S4.3)")
async def get_portfolio_metrics(
    simulation_id: str,
    force_recalculate: bool = Query(False, description="Force recalculation")
):
    """
    Get comprehensive portfolio metrics.
    
    Includes: Sharpe, Sortino, Calmar, drawdown, volatility, etc.
    """
    metrics = portfolio_metrics_service.calculate_portfolio_metrics(
        simulation_id,
        force_recalculate
    )
    
    if not metrics:
        raise HTTPException(status_code=404, detail=f"Cannot calculate metrics for {simulation_id}")
    
    return metrics.to_dict()


@router.get("/simulations/{simulation_id}/metrics/strategies", summary="Strategy Metrics (S4.3)")
async def get_strategy_metrics(simulation_id: str):
    """Get metrics for each strategy in portfolio"""
    metrics = portfolio_metrics_service.calculate_all_strategy_metrics(simulation_id)
    
    return {
        "strategies": [m.to_dict() for m in metrics],
        "count": len(metrics)
    }


@router.get("/simulations/{simulation_id}/correlation", summary="Correlation Matrix (S4.3)")
async def get_correlation_matrix(
    simulation_id: str,
    force_recalculate: bool = Query(False, description="Force recalculation")
):
    """
    Get correlation matrix between strategies.
    
    Based on trade returns.
    """
    matrix = portfolio_metrics_service.calculate_correlation_matrix(
        simulation_id,
        force_recalculate
    )
    
    if not matrix:
        raise HTTPException(status_code=404, detail=f"Cannot calculate correlation for {simulation_id}")
    
    return matrix.to_dict()


@router.get("/simulations/{simulation_id}/equity-curve", summary="Equity Curve (S4.3)")
async def get_equity_curve(
    simulation_id: str,
    limit: int = Query(1000, ge=1, le=10000, description="Max data points")
):
    """Get equity curve data points"""
    points = portfolio_metrics_service.get_equity_curve(simulation_id, limit)
    
    return {
        "data": [p.to_dict() for p in points],
        "count": len(points)
    }


@router.get("/simulations/{simulation_id}/risk-contributions", summary="Risk Contributions (S4.3)")
async def get_risk_contributions(simulation_id: str):
    """Get risk contribution per strategy"""
    contributions = portfolio_metrics_service.calculate_risk_contributions(simulation_id)
    
    return {
        "contributions": [c.to_dict() for c in contributions],
        "count": len(contributions)
    }


# ===========================================
# Health
# ===========================================

@router.get("/health", summary="Portfolio Module Health")
async def health():
    """Health check for Portfolio module"""
    sim_health = portfolio_simulation_service.get_health()
    state_health = portfolio_state_service.get_health()
    broker_health = portfolio_broker_service.get_health()
    metrics_health = portfolio_metrics_service.get_health()
    
    return {
        "module": "Portfolio Simulation",
        "phase": "S4.1/S4.2/S4.3",
        "status": "healthy",
        "services": {
            "simulation": sim_health,
            "state": state_health,
            "broker": broker_health,
            "metrics": metrics_health
        },
        "endpoints": {
            "s4.1": {
                "create": "POST /api/portfolio/simulations",
                "list": "GET /api/portfolio/simulations",
                "get": "GET /api/portfolio/simulations/{id}",
                "start": "POST /api/portfolio/simulations/{id}/start",
                "state": "GET /api/portfolio/simulations/{id}/state",
                "slots": "GET /api/portfolio/simulations/{id}/slots"
            },
            "s4.2": {
                "init_broker": "POST /api/portfolio/simulations/{id}/broker/init",
                "submit_order": "POST /api/portfolio/simulations/{id}/orders",
                "get_orders": "GET /api/portfolio/simulations/{id}/orders",
                "get_positions": "GET /api/portfolio/simulations/{id}/positions",
                "get_trades": "GET /api/portfolio/simulations/{id}/trades",
                "update_prices": "POST /api/portfolio/simulations/{id}/prices"
            },
            "s4.3": {
                "metrics": "GET /api/portfolio/simulations/{id}/metrics",
                "strategy_metrics": "GET /api/portfolio/simulations/{id}/metrics/strategies",
                "correlation": "GET /api/portfolio/simulations/{id}/correlation",
                "equity_curve": "GET /api/portfolio/simulations/{id}/equity-curve",
                "risk_contributions": "GET /api/portfolio/simulations/{id}/risk-contributions"
            }
        }
    }
