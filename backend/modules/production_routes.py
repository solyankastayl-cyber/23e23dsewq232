"""
Production Infrastructure Routes

Routes for:
- Meta-Alpha Portfolio (PHASE 45)
- Execution Reconciliation
- System Metrics & Health
- Chaos Testing
- Stress Testing
"""

from fastapi import APIRouter, HTTPException, Query
from datetime import datetime, timezone

router = APIRouter(prefix="/api/v1/system", tags=["System Infrastructure"])


# ══════════════════════════════════════════════════════════════
# System Health & Metrics
# ══════════════════════════════════════════════════════════════

@router.get("/health")
async def get_system_health():
    """Get overall system health."""
    from modules.system_metrics import get_metrics_engine
    engine = get_metrics_engine()
    health = engine.get_health()
    return health.model_dump()


@router.get("/metrics")
async def get_system_metrics():
    """Get system metrics."""
    from modules.system_metrics import get_metrics_engine
    engine = get_metrics_engine()
    return engine.get_summary()


# ══════════════════════════════════════════════════════════════
# Reconciliation
# ══════════════════════════════════════════════════════════════

@router.get("/reconciliation/summary")
async def get_reconciliation_summary():
    """Get reconciliation summary."""
    from modules.execution_reconciliation import get_reconciliation_engine
    engine = get_reconciliation_engine()
    return engine.get_summary()


@router.get("/reconciliation/state")
async def get_reconciliation_state():
    """Get reconciliation state."""
    from modules.execution_reconciliation import get_reconciliation_engine
    engine = get_reconciliation_engine()
    return engine.get_state().model_dump()


@router.post("/reconciliation/run")
async def run_reconciliation(exchange: str = Query(default="BINANCE")):
    """Run full reconciliation check."""
    from modules.execution_reconciliation import get_reconciliation_engine
    engine = get_reconciliation_engine()
    result = await engine.run_full_reconciliation(exchange)
    return result


# ══════════════════════════════════════════════════════════════
# Chaos Testing
# ══════════════════════════════════════════════════════════════

@router.get("/chaos/summary")
async def get_chaos_summary():
    """Get chaos testing summary."""
    from modules.system_chaos import get_chaos_engine
    engine = get_chaos_engine()
    return engine.get_summary()


@router.get("/chaos/results")
async def get_chaos_results(limit: int = Query(default=10)):
    """Get recent chaos test results."""
    from modules.system_chaos import get_chaos_engine
    engine = get_chaos_engine()
    results = engine.get_results(limit)
    return {"results": [r.model_dump() for r in results]}


@router.post("/chaos/run")
async def run_chaos_test(
    chaos_type: str = Query(..., description="Type of chaos test"),
    duration_seconds: int = Query(default=30),
    intensity: float = Query(default=0.5),
):
    """Run a chaos test."""
    from modules.system_chaos import get_chaos_engine, ChaosType, ChaosConfig
    
    try:
        ct = ChaosType(chaos_type.upper())
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Unknown chaos type: {chaos_type}")
    
    config = ChaosConfig(
        chaos_type=ct,
        duration_seconds=duration_seconds,
        intensity=intensity,
    )
    
    engine = get_chaos_engine()
    result = await engine.run_chaos(config)
    
    return result.model_dump()


@router.post("/chaos/abort")
async def abort_chaos():
    """Abort running chaos test."""
    from modules.system_chaos import get_chaos_engine
    engine = get_chaos_engine()
    engine.abort_chaos()
    return {"status": "aborted"}


# ══════════════════════════════════════════════════════════════
# Stress Testing
# ══════════════════════════════════════════════════════════════

@router.get("/stress/summary")
async def get_stress_summary():
    """Get stress testing summary."""
    from modules.stress_testing import get_stress_engine
    engine = get_stress_engine()
    return engine.get_summary()


@router.get("/stress/results")
async def get_stress_results(limit: int = Query(default=10)):
    """Get recent stress test results."""
    from modules.stress_testing import get_stress_engine
    engine = get_stress_engine()
    results = engine.get_results(limit)
    return {"results": [r.model_dump() for r in results]}


@router.post("/stress/run")
async def run_stress_test(
    test_type: str = Query(..., description="Type of stress test"),
    duration_seconds: int = Query(default=60),
    target_rate: int = Query(default=100),
):
    """Run a stress test."""
    from modules.stress_testing import get_stress_engine, StressTestType, StressTestConfig
    
    try:
        tt = StressTestType(test_type.upper())
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Unknown stress test type: {test_type}")
    
    config = StressTestConfig(
        test_type=tt,
        duration_seconds=duration_seconds,
        target_rate=target_rate,
    )
    
    engine = get_stress_engine()
    result = await engine.run_test(config)
    
    return result.model_dump()


# ══════════════════════════════════════════════════════════════
# Combined Status
# ══════════════════════════════════════════════════════════════

@router.get("/status")
async def get_full_system_status():
    """Get complete system status."""
    from modules.system_metrics import get_metrics_engine
    from modules.execution_reconciliation import get_reconciliation_engine
    from modules.system_chaos import get_chaos_engine
    from modules.stress_testing import get_stress_engine
    
    metrics = get_metrics_engine()
    reconciliation = get_reconciliation_engine()
    chaos = get_chaos_engine()
    stress = get_stress_engine()
    
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "health": metrics.get_health().model_dump(),
        "reconciliation": reconciliation.get_summary(),
        "chaos_testing": chaos.get_summary(),
        "stress_testing": stress.get_summary(),
    }
