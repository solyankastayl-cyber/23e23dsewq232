"""
PHASE 12 - System Intelligence API Routes
==========================================
REST API endpoints for system-level intelligence.

Endpoints:
- GET /api/system/state - unified system snapshot
- GET /api/system/health - system health
- GET /api/system/market-state - global market state
- GET /api/system/strategies - strategy regime
- GET /api/system/research-loop - research status
- GET /api/system/actions - pending decisions
- GET /api/system/stats - system statistics
"""

from typing import Optional
from datetime import datetime, timezone
from fastapi import APIRouter, Query, HTTPException
from pydantic import BaseModel

from .system_types import DEFAULT_SYSTEM_CONFIG
from .decision_orchestrator import DecisionOrchestrator
from .system_repository import SystemRepository


router = APIRouter(prefix="/api/system-intelligence", tags=["System Intelligence"])


# Initialize components
orchestrator = DecisionOrchestrator()
repository = SystemRepository()


# ===== Response Models =====

class SystemStateResponse(BaseModel):
    marketState: str
    systemHealth: float
    healthState: str
    portfolioRisk: float
    capitalDeployment: float
    activeStrategies: int
    disabledStrategies: int
    edgesStrengthening: int
    edgesStable: int
    edgesDecaying: int
    pendingAdaptations: int
    inCooldown: bool
    researchLoopActive: bool
    pendingActions: int
    computed_at: str


class HealthResponse(BaseModel):
    healthState: str
    healthScore: float
    signalQuality: float
    executionQuality: float
    portfolioStability: float
    riskBudgetUsage: float
    edgeStrength: float
    criticalIssues: int
    recommendedAction: str
    computed_at: str


class MarketStateResponse(BaseModel):
    marketState: str
    stateConfidence: float
    volatilityRegime: str
    liquidityRegime: str
    correlationRegime: str
    trendStrength: float
    trendDirection: str
    stateDurationHours: float
    computed_at: str


class ResearchLoopResponse(BaseModel):
    phase: str
    progress: float
    currentTask: str
    targetEdge: Optional[str]
    hypothesesGenerated: int
    scenariosTested: int
    montecarloRuns: int
    adaptationsProposed: int
    successfulDeployments: int
    failedProposals: int
    computed_at: str


# ===== API Endpoints =====

@router.get("/health")
async def system_module_health():
    """Health check for System Intelligence module."""
    return {
        "status": "healthy",
        "version": "phase12_system_intelligence_v1",
        "engines": {
            "global_market_state": "ready",
            "regime_switching": "ready",
            "system_health": "ready",
            "research_loop": "ready",
            "decision_orchestrator": "ready"
        },
        "config": {
            "high_vol_threshold": DEFAULT_SYSTEM_CONFIG["high_volatility_threshold"],
            "pause_threshold": DEFAULT_SYSTEM_CONFIG["pause_trading_health_threshold"],
            "research_interval": DEFAULT_SYSTEM_CONFIG["research_loop_interval_hours"]
        },
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@router.get("/state", response_model=SystemStateResponse)
async def get_system_state():
    """
    Get unified system state snapshot.
    
    Returns complete view of:
    - Market state
    - System health
    - Portfolio status
    - Strategy status
    - Adaptive status
    - Research status
    """
    try:
        now = datetime.now(timezone.utc)
        
        # Mock data from other system components
        portfolio_data = {
            "risk_budget_used": 0.63,
            "capital_deployment": 0.71,
            "current_drawdown": 0.03
        }
        
        adaptive_data = {
            "edges_strengthening": 2,
            "edges_stable": 3,
            "edges_decaying": 1,
            "pending_adaptations": 1,
            "in_cooldown": False,
            "active_strategies": 4,
            "disabled_strategies": 0
        }
        
        # Get unified snapshot
        snapshot = orchestrator.evaluate_system(
            portfolio_data=portfolio_data,
            adaptive_data=adaptive_data
        )
        
        # Save to repository
        try:
            repository.save_snapshot(snapshot)
        except Exception:
            pass
        
        return SystemStateResponse(
            marketState=snapshot.market_state.value,
            systemHealth=round(snapshot.system_health, 3),
            healthState=snapshot.health_state.value,
            portfolioRisk=round(snapshot.portfolio_risk, 4),
            capitalDeployment=round(snapshot.capital_deployment, 3),
            activeStrategies=snapshot.active_strategies,
            disabledStrategies=snapshot.disabled_strategies,
            edgesStrengthening=snapshot.edges_strengthening,
            edgesStable=snapshot.edges_stable,
            edgesDecaying=snapshot.edges_decaying,
            pendingAdaptations=snapshot.pending_adaptations,
            inCooldown=snapshot.in_cooldown,
            researchLoopActive=snapshot.research_loop_active,
            pendingActions=snapshot.pending_actions,
            computed_at=now.isoformat()
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health-status", response_model=HealthResponse)
async def get_system_health():
    """Get detailed system health analysis."""
    try:
        now = datetime.now(timezone.utc)
        
        health = orchestrator.health_engine.analyze_health()
        
        return HealthResponse(
            healthState=health.health_state.value,
            healthScore=round(health.health_score, 3),
            signalQuality=round(health.signal_quality, 3),
            executionQuality=round(health.execution_quality, 3),
            portfolioStability=round(health.portfolio_stability, 3),
            riskBudgetUsage=round(health.risk_budget_usage, 3),
            edgeStrength=round(health.edge_strength, 3),
            criticalIssues=health.critical_issues,
            recommendedAction=health.recommended_action.value,
            computed_at=now.isoformat()
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/market-state", response_model=MarketStateResponse)
async def get_market_state():
    """Get global market state analysis."""
    try:
        now = datetime.now(timezone.utc)
        
        state = orchestrator.market_state_engine.analyze_market_state()
        
        return MarketStateResponse(
            marketState=state.market_state.value,
            stateConfidence=round(state.state_confidence, 3),
            volatilityRegime=state.volatility_regime,
            liquidityRegime=state.liquidity_regime,
            correlationRegime=state.correlation_regime,
            trendStrength=round(state.trend_strength, 3),
            trendDirection=state.trend_direction,
            stateDurationHours=round(state.state_duration_hours, 1),
            computed_at=now.isoformat()
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/strategies")
async def get_strategy_regime():
    """Get current strategy regime and weights."""
    try:
        now = datetime.now(timezone.utc)
        
        regime_summary = orchestrator.regime_engine.get_regime_summary()
        
        return {
            "current_profile": regime_summary["current_profile"],
            "strategy_weights": regime_summary["current_weights"],
            "last_switch": regime_summary["last_switch"],
            "cooldown_clear": regime_summary["cooldown_clear"],
            "computed_at": now.isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/research-loop", response_model=ResearchLoopResponse)
async def get_research_loop():
    """Get autonomous research loop status."""
    try:
        now = datetime.now(timezone.utc)
        
        status = orchestrator.research_loop._get_current_status()
        
        return ResearchLoopResponse(
            phase=status.phase.value,
            progress=round(status.progress, 3),
            currentTask=status.current_task,
            targetEdge=status.target_edge,
            hypothesesGenerated=status.hypotheses_generated,
            scenariosTested=status.scenarios_tested,
            montecarloRuns=status.montecarlo_runs,
            adaptationsProposed=status.adaptations_proposed,
            successfulDeployments=status.successful_deployments,
            failedProposals=status.failed_proposals,
            computed_at=now.isoformat()
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/actions")
async def get_pending_actions():
    """Get pending system actions/decisions."""
    try:
        now = datetime.now(timezone.utc)
        
        pending = orchestrator.get_pending_decisions()
        
        return {
            "count": len(pending),
            "actions": pending[:20],  # Limit to 20
            "trading_paused": orchestrator.trading_paused,
            "emergency_mode": orchestrator.emergency_mode,
            "computed_at": now.isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/actions/{decision_id}/execute")
async def execute_action(decision_id: str):
    """Execute a pending system action."""
    try:
        result = orchestrator.execute_decision(decision_id)
        
        # Save decision
        if result.get("executed"):
            for d in orchestrator.decisions:
                if d.decision_id == decision_id:
                    repository.save_decision(d)
                    break
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats")
async def get_system_stats():
    """Get comprehensive system statistics."""
    try:
        repo_stats = repository.get_stats()
        
        return {
            "repository": repo_stats,
            "orchestrator": orchestrator.get_orchestrator_summary(),
            "config": DEFAULT_SYSTEM_CONFIG,
            "retrieved_at": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/research-loop/start")
async def start_research_loop():
    """Manually start a research cycle."""
    try:
        if orchestrator.research_loop.loop_running:
            return {
                "started": False,
                "reason": "Research loop already running",
                "current_phase": orchestrator.research_loop.current_phase.value
            }
        
        status = orchestrator.research_loop.start_research_cycle(
            decaying_edges=["manual_trigger"],
            edge_metrics={}
        )
        
        return {
            "started": True,
            "phase": status.phase.value,
            "task": status.current_task
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/research-loop/advance")
async def advance_research_loop():
    """Advance research loop to next phase."""
    try:
        status = orchestrator.research_loop.advance_loop()
        
        return {
            "phase": status.phase.value,
            "progress": round(status.progress, 3),
            "task": status.current_task
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
