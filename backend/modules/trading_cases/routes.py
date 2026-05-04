"""
TradingCase API Routes

Endpoints for managing trading cases.
"""

from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any

from .models import TradingCase, CaseCreateRequest, CaseUpdateRequest, CaseCloseRequest
from .service import get_trading_case_service

router = APIRouter(prefix="/api/trading", tags=["trading_cases"])


@router.get("/cases", response_model=List[TradingCase])
async def get_all_cases(experiment_id: str = None) -> List[TradingCase]:
    """
    Get all trading cases.
    
    Query params:
    - experiment_id: Optional filter by experiment (default: no filter)
    """
    try:
        service = get_trading_case_service()
        return service.get_cases(experiment_id=experiment_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/cases/active", response_model=List[TradingCase])
async def get_active_cases(experiment_id: str = None) -> List[TradingCase]:
    """
    Get active trading cases.
    
    Query params:
    - experiment_id: Optional filter by experiment (default: no filter)
    """
    try:
        service = get_trading_case_service()
        return service.get_active_cases(experiment_id=experiment_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/cases/closed", response_model=List[TradingCase])
async def get_closed_cases(experiment_id: str = None) -> List[TradingCase]:
    """
    Get closed trading cases.
    
    Query params:
    - experiment_id: Optional filter by experiment (default: no filter)
    """
    try:
        service = get_trading_case_service()
        return service.get_closed_cases(experiment_id=experiment_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/cases/{case_id}", response_model=TradingCase)
async def get_case(case_id: str) -> TradingCase:
    """Get case by ID."""
    try:
        service = get_trading_case_service()
        case = service.get_case(case_id)
        
        if not case:
            raise HTTPException(status_code=404, detail=f"Case {case_id} not found")
        
        return case
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/cases", response_model=TradingCase)
async def create_case(request: CaseCreateRequest) -> TradingCase:
    """Create a new trading case."""
    try:
        service = get_trading_case_service()
        return await service.create_case(request)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/cases/{case_id}", response_model=TradingCase)
async def update_case(case_id: str, update: CaseUpdateRequest) -> TradingCase:
    """Update a trading case."""
    try:
        service = get_trading_case_service()
        return await service.update_case(case_id, update)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/cases/{case_id}/close", response_model=TradingCase)
async def close_case(case_id: str, close_request: CaseCloseRequest) -> TradingCase:
    """Close a trading case."""
    try:
        service = get_trading_case_service()
        return await service.close_case(case_id, close_request)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/cases/{case_id}/order")
async def execute_order(case_id: str, order_request: Dict[str, Any]) -> Dict[str, Any]:
    """Execute an order for a case."""
    try:
        service = get_trading_case_service()
        order = await service.execute_order(case_id, order_request)
        
        return {
            "ok": True,
            "order": order.dict() if hasattr(order, 'dict') else order
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/cases/sync")
async def sync_positions() -> Dict[str, Any]:
    """Sync positions from exchange to cases."""
    try:
        service = get_trading_case_service()
        await service.sync_positions()
        
        return {
            "ok": True,
            "message": "Positions synced"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/positions", response_model=List[TradingCase])
async def get_positions() -> List[TradingCase]:
    """
    Get current positions (active cases).
    
    Alias for /cases/active for convenience.
    """
    return await get_active_cases()
