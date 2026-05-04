"""
PHASE 11 - Adaptive Intelligence API Routes
============================================
REST API endpoints for adaptive intelligence.

Endpoints:
- GET /api/adaptive/system-state
- GET /api/adaptive/strategy-performance
- GET /api/adaptive/parameter-adjustments
- GET /api/adaptive/edge-decay
- GET /api/adaptive/recommendations
- GET /api/adaptive/safety-status
- GET /api/adaptive/health
"""

import random
from typing import List, Optional
from datetime import datetime, timezone
from fastapi import APIRouter, Query, HTTPException
from pydantic import BaseModel

from .adaptive_types import (
    AdaptiveState, PerformanceTrend, EdgeStatus,
    DEFAULT_ADAPTIVE_CONFIG
)
from .adaptive_controller import AdaptiveController
from .strategy_performance_tracker import StrategyPerformanceTracker
from .parameter_optimizer import ParameterOptimizer
from .factor_weight_optimizer import FactorWeightOptimizer
from .edge_decay_detector import EdgeDecayDetector
from .adaptive_repository import AdaptiveRepository


router = APIRouter(prefix="/api/adaptive", tags=["Adaptive Intelligence"])


# Initialize components
controller = AdaptiveController()
performance_tracker = StrategyPerformanceTracker()
parameter_optimizer = ParameterOptimizer()
weight_optimizer = FactorWeightOptimizer()
edge_detector = EdgeDecayDetector()
repository = AdaptiveRepository()


# ===== Mock Data =====

def get_mock_strategies():
    """Generate mock strategies for testing."""
    return [
        {"id": "strat_breakout", "name": "MTF_BREAKOUT", "edge_name": "breakout_edge"},
        {"id": "strat_reversal", "name": "MEAN_REVERSION", "edge_name": "reversal_edge"},
        {"id": "strat_momentum", "name": "MOMENTUM_CONT", "edge_name": "momentum_edge"},
        {"id": "strat_trend", "name": "TREND_FOLLOWING", "edge_name": "trend_edge"}
    ]


def get_mock_factors():
    """Generate mock factors."""
    return {
        "volume_confirmation": "alpha",
        "trend_strength": "alpha",
        "structure_quality": "structure",
        "liquidity_score": "liquidity",
        "flow_pressure": "microstructure"
    }


# ===== Response Models =====

class SystemStateResponse(BaseModel):
    adaptiveState: str
    systemAdaptivityScore: float
    edgesStrengthening: int
    edgesStable: int
    edgesDegrading: int
    edgesCritical: int
    pendingParameterChanges: int
    pendingWeightChanges: int
    strategiesDisabled: int
    inCooldown: bool
    shadowTestsRunning: int
    overallSystemHealth: float
    computed_at: str


class PerformanceResponse(BaseModel):
    strategy_id: str
    name: str
    win_rate: float
    profit_factor: float
    performance_trend: str
    total_trades: int
    computed_at: str


class EdgeDecayResponse(BaseModel):
    strategy_id: str
    edge_name: str
    edge_status: str
    decay_probability: float
    rolling_pf: float
    confirmed_decay: bool
    recommended_action: str
    computed_at: str


# ===== API Endpoints =====

@router.get("/health")
async def adaptive_health():
    """Health check for Adaptive Intelligence module."""
    return {
        "status": "healthy",
        "version": "phase11_adaptive_v1",
        "engines": {
            "performance_tracker": "ready",
            "parameter_optimizer": "ready",
            "weight_optimizer": "ready",
            "edge_detector": "ready",
            "adaptive_controller": "ready"
        },
        "safety_layer": {
            "change_guard": "ready",
            "cooldown_manager": "ready",
            "shadow_mode": "ready",
            "oos_gate": "ready",
            "change_audit": "ready"
        },
        "config": {
            "max_param_change": DEFAULT_ADAPTIVE_CONFIG["max_parameter_change_pct"],
            "shadow_test_hours": DEFAULT_ADAPTIVE_CONFIG["shadow_test_duration_hours"],
            "cooldown_hours": DEFAULT_ADAPTIVE_CONFIG["parameter_cooldown_hours"]
        },
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@router.get("/system-state", response_model=SystemStateResponse)
async def get_system_state():
    """
    Get complete adaptive system state.
    
    Returns unified view of:
    - System adaptivity
    - Edge health
    - Pending changes
    - Safety status
    """
    try:
        now = datetime.now(timezone.utc)
        
        strategies = get_mock_strategies()
        factors = get_mock_factors()
        
        snapshot = controller.evaluate_system(strategies, factors)
        
        # Save to repository
        try:
            repository.save_snapshot(snapshot)
        except Exception:
            pass
        
        return SystemStateResponse(
            adaptiveState=snapshot.adaptive_state.value,
            systemAdaptivityScore=round(snapshot.system_adaptivity_score, 3),
            edgesStrengthening=snapshot.edges_strengthening,
            edgesStable=snapshot.edges_stable,
            edgesDegrading=snapshot.edges_degrading,
            edgesCritical=snapshot.edges_critical,
            pendingParameterChanges=snapshot.pending_parameter_changes,
            pendingWeightChanges=snapshot.pending_weight_changes,
            strategiesDisabled=snapshot.strategies_disabled,
            inCooldown=snapshot.in_cooldown,
            shadowTestsRunning=snapshot.shadow_tests_running,
            overallSystemHealth=round(snapshot.overall_system_health, 3),
            computed_at=now.isoformat()
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/strategy-performance")
async def get_strategy_performance(
    strategy_id: str = Query("strat_breakout", description="Strategy ID")
):
    """Get performance analysis for a strategy."""
    try:
        now = datetime.now(timezone.utc)
        
        perf = performance_tracker.track_performance(
            strategy_id,
            strategy_id.replace("strat_", "").upper()
        )
        
        return {
            "strategy_id": perf.strategy_id,
            "name": perf.name,
            "win_rate": round(perf.win_rate, 4),
            "long_term_win_rate": round(perf.long_term_win_rate, 4),
            "profit_factor": round(perf.profit_factor, 3),
            "expectancy": round(perf.expectancy, 4),
            "max_drawdown": round(perf.max_drawdown, 4),
            "current_drawdown": round(perf.current_drawdown, 4),
            "sharpe_ratio": round(perf.sharpe_ratio, 3),
            "performance_trend": perf.performance_trend.value,
            "trend_strength": round(perf.trend_strength, 3),
            "total_trades": perf.total_trades,
            "computed_at": now.isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/parameter-adjustments")
async def get_parameter_adjustments(
    strategy_id: str = Query("strat_breakout", description="Strategy ID"),
    parameter: str = Query("lookback_window", description="Parameter name")
):
    """Get parameter optimization recommendation."""
    try:
        now = datetime.now(timezone.utc)
        
        # Set some bounds
        parameter_optimizer.set_parameter_bounds(strategy_id, parameter, 10, 100)
        
        # Current value (mock)
        current_value = random.uniform(20, 50)
        
        # Generate mock performance data
        perf_data = [{"pnl": random.gauss(0.002, 0.02)} for _ in range(50)]
        
        adjustment = parameter_optimizer.optimize_parameter(
            strategy_id, parameter, current_value, perf_data
        )
        
        return {
            "parameter_name": adjustment.parameter_name,
            "strategy_id": adjustment.strategy_id,
            "current_value": round(adjustment.current_value, 4),
            "suggested_value": round(adjustment.suggested_value, 4),
            "expected_improvement": round(adjustment.expected_improvement, 4),
            "confidence": round(adjustment.confidence, 3),
            "change_magnitude": round(adjustment.change_magnitude, 4),
            "within_limits": adjustment.within_limits,
            "cooldown_clear": adjustment.cooldown_clear,
            "decision": adjustment.decision.value,
            "rejection_reason": adjustment.rejection_reason,
            "computed_at": now.isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/edge-decay")
async def get_edge_decay(
    strategy_id: str = Query("strat_breakout", description="Strategy ID"),
    edge_name: str = Query("main_edge", description="Edge name")
):
    """Get edge decay analysis."""
    try:
        now = datetime.now(timezone.utc)
        
        signal = edge_detector.detect_decay(strategy_id, edge_name)
        
        return {
            "strategy_id": signal.strategy_id,
            "edge_name": signal.edge_name,
            "edge_status": signal.edge_status.value,
            "decay_probability": round(signal.decay_probability, 3),
            "rolling_pf": round(signal.rolling_pf, 3),
            "rolling_expectancy": round(signal.rolling_expectancy, 4),
            "hit_rate_drift": round(signal.hit_rate_drift, 4),
            "confidence_degradation": round(signal.confidence_degradation, 4),
            "confirmed_decay": signal.confirmed_decay,
            "confirmation_axes": signal.confirmation_axes,
            "recommended_action": signal.recommended_action.value,
            "urgency": round(signal.urgency, 3),
            "computed_at": now.isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/recommendations")
async def get_recommendations():
    """Get pending adaptive recommendations."""
    try:
        now = datetime.now(timezone.utc)
        
        # Evaluate system to generate recommendations
        strategies = get_mock_strategies()
        factors = get_mock_factors()
        
        controller.evaluate_system(strategies, factors)
        
        recommendations = controller.get_pending_recommendations()
        
        return {
            "count": len(recommendations),
            "recommendations": recommendations[:10],  # Limit to 10
            "retrieved_at": now.isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/safety-status")
async def get_safety_status():
    """Get adaptive safety layer status."""
    try:
        now = datetime.now(timezone.utc)
        
        summary = controller.get_controller_summary()
        
        return {
            "controller_state": summary["state"],
            "safety_summary": summary["safety_summary"],
            "limits": summary["limits"],
            "retrieved_at": now.isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats")
async def get_adaptive_stats():
    """Get adaptive intelligence statistics."""
    try:
        repo_stats = repository.get_stats()
        
        return {
            "repository": repo_stats,
            "summaries": {
                "performance": performance_tracker.get_all_strategies_summary(),
                "parameter_optimization": parameter_optimizer.get_optimization_summary(),
                "weight_optimization": weight_optimizer.get_weight_summary(),
                "edge_decay": edge_detector.get_decay_summary()
            },
            "controller": controller.get_controller_summary(),
            "config": DEFAULT_ADAPTIVE_CONFIG,
            "retrieved_at": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
