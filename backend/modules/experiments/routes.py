"""
Experiment API Routes

Manage experiment configurations and status.
"""
from fastapi import APIRouter, HTTPException, Depends, Request
from typing import Optional
from .registry import get_experiment_registry
from .config import ExperimentStatus

router = APIRouter(prefix="/api/experiments", tags=["Experiments"])


# Dependency for DB access
async def get_db():
    """
    Get MongoDB database (Motor async).
    
    Returns AsyncIOMotorDatabase for async operations.
    """
    try:
        # Get Motor async db from app state (created in lifespan)
        import os
        from motor.motor_asyncio import AsyncIOMotorClient
        
        mongo_url = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
        client = AsyncIOMotorClient(mongo_url)
        db = client["trading_os"]
        
        return db
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database not available: {e}")


@router.get("/")
async def get_all_experiments():
    """Get all experiments"""
    try:
        registry = get_experiment_registry()
        experiments = await registry.get_all_experiments()
        return {
            "ok": True,
            "count": len(experiments),
            "experiments": [exp.to_dict() for exp in experiments],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/enabled")
async def get_enabled_experiments():
    """Get only enabled experiments"""
    try:
        registry = get_experiment_registry()
        experiments = await registry.get_enabled_experiments()
        return {
            "ok": True,
            "count": len(experiments),
            "experiments": [exp.to_dict() for exp in experiments],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{experiment_id}")
async def get_experiment(experiment_id: str):
    """Get specific experiment"""
    try:
        registry = get_experiment_registry()
        experiment = await registry.get_experiment(experiment_id)
        
        if not experiment:
            raise HTTPException(status_code=404, detail=f"Experiment {experiment_id} not found")
        
        return {
            "ok": True,
            "experiment": experiment.to_dict(),
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{experiment_id}/enable")
async def enable_experiment(experiment_id: str):
    """
    Enable experiment
    
    WARNING: Enabling market_dynamic before baseline completes will contaminate data!
    Only enable after baseline_btc reaches 50+ trades.
    """
    try:
        registry = get_experiment_registry()
        
        # Check if experiment exists
        experiment = await registry.get_experiment(experiment_id)
        if not experiment:
            raise HTTPException(status_code=404, detail=f"Experiment {experiment_id} not found")
        
        # WARNING for market_dynamic
        if experiment_id == "market_dynamic":
            # Check baseline status
            from modules.p27_baseline.monitor import get_p27_monitor
            monitor = get_p27_monitor()
            baseline_status = await monitor.get_status(experiment_id="baseline_btc")
            
            if baseline_status["total_trades"] < 50:
                return {
                    "ok": False,
                    "error": "BLOCKED",
                    "reason": f"baseline_btc has only {baseline_status['total_trades']}/50 trades. Complete baseline first!",
                    "baseline_trades": baseline_status["total_trades"],
                    "baseline_target": 50,
                }
        
        await registry.enable_experiment(experiment_id)
        
        return {
            "ok": True,
            "experiment_id": experiment_id,
            "status": "enabled",
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{experiment_id}/disable")
async def disable_experiment(experiment_id: str):
    """Disable experiment"""
    try:
        registry = get_experiment_registry()
        
        # Check if experiment exists
        experiment = await registry.get_experiment(experiment_id)
        if not experiment:
            raise HTTPException(status_code=404, detail=f"Experiment {experiment_id} not found")
        
        await registry.disable_experiment(experiment_id)
        
        return {
            "ok": True,
            "experiment_id": experiment_id,
            "status": "disabled",
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats/summary")
async def get_experiment_stats():
    """Get experiment statistics"""
    try:
        registry = get_experiment_registry()
        stats = await registry.get_stats()
        return {
            "ok": True,
            "stats": stats,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def experiments_health():
    """Experiments module health check"""
    return {
        "ok": True,
        "module": "Experiments",
        "note": "Experiment isolation infrastructure",
    }


@router.get("/market_dynamic/stats")
async def get_market_dynamic_stats():
    """
    Get market_dynamic runner statistics
    
    Returns scan and signal generation metadata
    """
    try:
        from modules.signal_generator.market_dynamic_runner import get_market_dynamic_runner
        
        runner = get_market_dynamic_runner()
        stats = runner.get_stats()
        
        return {
            "ok": True,
            **stats
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/market_dynamic/preview")
async def get_market_dynamic_preview():
    """
    PHASE 2.4: Get market_dynamic allocation preview.
    
    Shows which signals would be selected for execution
    (but NO actual execution happens).
    
    Returns:
        - market_bias + market_structure
        - signals_total, signals_filtered, selected_count
        - selected_signals (with scores, clusters, reasons)
        - rejected (breakdown by reason)
    """
    try:
        from modules.signal_generator.market_dynamic_runner import get_market_dynamic_runner
        
        runner = get_market_dynamic_runner()
        preview = runner.get_latest_preview()
        
        if not preview:
            return {
                "ok": False,
                "message": "No preview available (runner not active or no signals generated yet)"
            }
        
        return {
            "ok": True,
            **preview
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/market_dynamic/history")
async def get_market_dynamic_history(limit: int = 20, db=Depends(get_db)):
    """
    PHASE 2.5: Get historical snapshots.
    
    Returns:
        - snapshots: List of recent decision cycles
        - statistics: avg_selected, avg_signals, dominant_bias
    """
    try:
        from modules.strategy.snapshot_storage import (
            get_latest_snapshots,
            get_snapshot_statistics
        )
        
        snapshots = await get_latest_snapshots(db, limit=limit)
        stats = await get_snapshot_statistics(db, lookback_hours=24)
        
        return {
            "ok": True,
            "snapshots": snapshots,
            "statistics": stats,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/market_dynamic/performance")
async def get_market_dynamic_performance(horizon: str = "24h", db=Depends(get_db)):
    """
    PHASE 2.6: Get shadow trading performance.
    
    Aggregates resolved shadow trades to calculate:
    - Winrate
    - Avg PnL
    - Breakdown by score, alignment, cluster
    
    Args:
        horizon: Time horizon to analyze ("24h", "48h", "7d")
    """
    try:
        # Overall performance for horizon
        pipeline_overall = [
            {"$unwind": "$horizons"},
            {"$match": {
                "experiment_id": "market_dynamic",
                "horizons.name": horizon,
                "horizons.resolved": True
            }},
            {"$group": {
                "_id": None,
                "total_trades": {"$sum": 1},
                "winrate": {
                    "$avg": {"$cond": [{"$gt": ["$horizons.pnl", 0]}, 1.0, 0.0]}
                },
                "avg_pnl": {"$avg": "$horizons.pnl"},
                "total_pnl": {"$sum": "$horizons.pnl"},
            }}
        ]
        
        overall_results = await db.shadow_trades.aggregate(pipeline_overall).to_list(length=1)
        overall = overall_results[0] if overall_results else {
            "total_trades": 0,
            "winrate": 0.0,
            "avg_pnl": 0.0,
            "total_pnl": 0.0,
        }
        
        # Performance by score bucket
        pipeline_score = [
            {"$unwind": "$horizons"},
            {"$match": {
                "experiment_id": "market_dynamic",
                "horizons.name": horizon,
                "horizons.resolved": True
            }},
            {"$bucket": {
                "groupBy": "$features.score",
                "boundaries": [0.4, 0.5, 0.6, 0.7, 1.0],
                "default": "other",
                "output": {
                    "count": {"$sum": 1},
                    "winrate": {
                        "$avg": {"$cond": [{"$gt": ["$horizons.pnl", 0]}, 1.0, 0.0]}
                    },
                    "avg_pnl": {"$avg": "$horizons.pnl"}
                }
            }}
        ]
        
        score_buckets = await db.shadow_trades.aggregate(pipeline_score).to_list(length=10)
        
        # Performance by alignment
        pipeline_alignment = [
            {"$unwind": "$horizons"},
            {"$match": {
                "experiment_id": "market_dynamic",
                "horizons.name": horizon,
                "horizons.resolved": True
            }},
            {"$group": {
                "_id": "$features.market_structure.alignment",
                "count": {"$sum": 1},
                "winrate": {
                    "$avg": {"$cond": [{"$gt": ["$horizons.pnl", 0]}, 1.0, 0.0]}
                },
                "avg_pnl": {"$avg": "$horizons.pnl"}
            }}
        ]
        
        alignment_results = await db.shadow_trades.aggregate(pipeline_alignment).to_list(length=10)
        
        # Performance by cluster
        pipeline_cluster = [
            {"$unwind": "$horizons"},
            {"$match": {
                "experiment_id": "market_dynamic",
                "horizons.name": horizon,
                "horizons.resolved": True
            }},
            {"$group": {
                "_id": "$features.cluster",
                "count": {"$sum": 1},
                "winrate": {
                    "$avg": {"$cond": [{"$gt": ["$horizons.pnl", 0]}, 1.0, 0.0]}
                },
                "avg_pnl": {"$avg": "$horizons.pnl"}
            }}
        ]
        
        cluster_results = await db.shadow_trades.aggregate(pipeline_cluster).to_list(length=10)
        
        return {
            "ok": True,
            "horizon": horizon,
            "overall": {
                "total_trades": overall.get("total_trades", 0),
                "winrate": round(overall.get("winrate", 0), 4),
                "avg_pnl": round(overall.get("avg_pnl", 0), 6),
                "total_pnl": round(overall.get("total_pnl", 0), 6),
            },
            "by_score": score_buckets,
            "by_alignment": alignment_results,
            "by_cluster": cluster_results,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/market_dynamic/features")
async def get_market_dynamic_features(days: Optional[int] = None, db=Depends(get_db)):
    """
    PHASE 2.7C: Feature Validation Layer
    
    Aggregates shadow trade outcomes across ALL dimensions:
    - cluster (majors/alts/stable)
    - alignment (aligned/misaligned)
    - timeframe (1h/4h/1d)
    - score_bucket (0.3-0.4 / 0.4-0.5 / ... / 0.9-1.0)
    - side (LONG/SHORT)
    
    Returns horizon-separated results (24h / 48h / 7d) with validity flags.
    
    CRITICAL: This is OBSERVATION ONLY. No auto-adaptation.
    
    Args:
        days: Optional time filter (e.g., last 7 days). None = all history.
    
    Returns:
        {
            "horizons": {
                "24h": {
                    "by_cluster": [...],
                    "by_alignment": [...],
                    "by_timeframe": [...],
                    "by_score_bucket": [...],
                    "by_side": [...]
                },
                "48h": {...},
                "7d": {...}
            },
            "meta": {
                "min_sample_size": 10,
                "total_trades": 120,
                "generated_at": "..."
            }
        }
    """
    try:
        from modules.strategy.feature_performance_service import get_feature_performance_service
        
        service = get_feature_performance_service(db)
        result = await service.get_feature_performance(
            experiment_id="market_dynamic",
            days=days
        )
        
        return {
            "ok": True,
            **result
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/market_dynamic/health")
async def get_market_dynamic_health(db=Depends(get_db)):
    """
    PHASE 2.8: System Health Status
    
    Aggregates:
    - Active alerts
    - Performance summary
    - Constraint state
    - Calibration status
    
    Returns overall health status: healthy | warning | critical
    
    Returns:
        {
            "status": "healthy" | "warning" | "critical",
            "summary": {
                "winrate": 0.52,
                "avg_pnl": 0.004,
                "total_trades": 120
            },
            "alerts": [
                {
                    "type": "cluster_degradation",
                    "severity": "warning",
                    "message": "Alts underperforming"
                }
            ],
            "alert_counts": {
                "info": 0,
                "warning": 2,
                "critical": 1
            },
            "constraints": {
                "mode": "defensive",
                "max_positions": 2
            },
            "calibration": {
                "active": true,
                "last_updated": "..."
            }
        }
    """
    try:
        from modules.strategy.observability import get_health_service
        
        service = get_health_service(db)
        result = await service.get_health_status(experiment_id="market_dynamic")
        
        return {
            "ok": True,
            **result
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/market_dynamic/alerts")
async def get_market_dynamic_alerts(
    severity: Optional[str] = None,
    alert_type: Optional[str] = None,
    db=Depends(get_db)
):
    """
    PHASE 2.8: Get active alerts
    
    Args:
        severity: Optional filter ("info" | "warning" | "critical")
        alert_type: Optional filter (e.g., "performance_degradation")
    
    Returns:
        {
            "ok": True,
            "count": 3,
            "alerts": [...]
        }
    """
    try:
        from modules.strategy.observability.alert_storage import AlertStorage
        
        storage = AlertStorage(db)
        alerts = await storage.get_active_alerts(
            experiment_id="market_dynamic",
            severity=severity,
            alert_type=alert_type
        )
        
        return {
            "ok": True,
            "count": len(alerts),
            "alerts": alerts
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/market_dynamic/alerts/history")
async def get_market_dynamic_alert_history(
    hours: int = 24,
    limit: int = 50,
    db=Depends(get_db)
):
    """
    PHASE 2.8: Get alert history (including resolved)
    
    Args:
        hours: Lookback window in hours (default: 24)
        limit: Maximum alerts to return (default: 50)
    
    Returns:
        {
            "ok": True,
            "count": 10,
            "alerts": [...]
        }
    """
    try:
        from modules.strategy.observability.alert_storage import AlertStorage
        
        storage = AlertStorage(db)
        alerts = await storage.get_alert_history(
            experiment_id="market_dynamic",
            hours=hours,
            limit=limit
        )
        
        return {
            "ok": True,
            "count": len(alerts),
            "alerts": alerts
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/market_dynamic/alerts/{alert_id}/resolve")
async def resolve_market_dynamic_alert(alert_id: str, db=Depends(get_db)):
    """
    PHASE 2.8: Mark alert as resolved
    
    Args:
        alert_id: Alert ID to resolve
    
    Returns:
        {
            "ok": True,
            "resolved": true
        }
    """
    try:
        from modules.strategy.observability.alert_storage import AlertStorage
        
        storage = AlertStorage(db)
        resolved = await storage.resolve_alert(alert_id)
        
        if not resolved:
            raise HTTPException(status_code=404, detail=f"Alert {alert_id} not found")
        
        return {
            "ok": True,
            "resolved": True
        }
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/market_dynamic/readiness")
async def get_market_dynamic_readiness(db=Depends(get_db)):
    """
    PHASE 2.9: Execution Readiness Gate
    
    Determines if system is allowed to execute based on health status.
    
    States:
      - READY: Full execution allowed
      - LIMITED: Restricted execution (majors only, reduced positions)
      - BLOCKED: Execution prohibited
    
    Returns:
        {
            "state": "ready" | "limited" | "blocked",
            "execution": {
                "enabled": bool,
                "max_positions": int,
                "allowed_clusters": [...],
                "mode": "full" | "restricted" | "disabled"
            },
            "reason": "...",
            "context": {
                "health": "healthy",
                "critical_alerts": 0,
                "warning_alerts": 2,
                "winrate": 0.52,
                "total_trades": 45
            },
            "override_active": false
        }
    """
    try:
        from modules.strategy.execution_readiness import get_execution_readiness_service
        
        service = get_execution_readiness_service(db)
        result = await service.get_execution_readiness(experiment_id="market_dynamic")
        
        return {
            "ok": True,
            **result
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/market_dynamic/readiness/override")
async def set_readiness_override(
    override_state: str,
    expires_in_minutes: int = 60,
    reason: str = "Manual override",
    db=Depends(get_db)
):
    """
    PHASE 2.9: Set Manual Override
    
    Temporarily override execution readiness state.
    
    IMPORTANT: Anti-danger guard still applies (winrate < 30% forces BLOCKED).
    
    Args:
        override_state: "ready" | "limited" | "blocked"
        expires_in_minutes: TTL in minutes (default: 60)
        reason: Human-readable reason for override
    
    Returns:
        {
            "ok": True,
            "override_id": "...",
            "override_state": "limited",
            "expires_at": "2024-01-01T01:00:00Z",
            "reason": "Testing execution bridge"
        }
    """
    try:
        from modules.strategy.execution_readiness import get_execution_readiness_service
        
        service = get_execution_readiness_service(db)
        result = await service.set_manual_override(
            experiment_id="market_dynamic",
            override_state=override_state,
            expires_in_minutes=expires_in_minutes,
            reason=reason
        )
        
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/market_dynamic/readiness/override")
async def clear_readiness_override(db=Depends(get_db)):
    """
    PHASE 2.9: Clear Manual Override
    
    Remove active override and return to automatic state determination.
    
    Returns:
        {
            "ok": True,
            "cleared": true
        }
    """
    try:
        from modules.strategy.execution_readiness import get_execution_readiness_service
        
        service = get_execution_readiness_service(db)
        cleared = await service.clear_override(experiment_id="market_dynamic")
        
        return {
            "ok": True,
            "cleared": cleared
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/market_dynamic/readiness/history")
async def get_readiness_history(limit: int = 50, db=Depends(get_db)):
    """
    PHASE 2.9: Readiness Decision History
    
    Get audit trail of readiness decisions.
    
    Args:
        limit: Maximum decisions to return (default: 50)
    
    Returns:
        {
            "ok": True,
            "count": 25,
            "decisions": [
                {
                    "state": "blocked",
                    "reason": "...",
                    "timestamp": "..."
                }
            ]
        }
    """
    try:
        from motor.motor_asyncio import AsyncIOMotorDatabase
        
        cursor = db.execution_readiness_decisions.find(
            {"experiment_id": "market_dynamic"}
        ).sort("timestamp", -1).limit(limit)
        
        decisions = await cursor.to_list(length=limit)
        
        # Convert _id to string
        for decision in decisions:
            decision["_id"] = str(decision["_id"])
            if "timestamp" in decision and isinstance(decision["timestamp"], datetime):
                decision["timestamp"] = decision["timestamp"].isoformat()
        
        return {
            "ok": True,
            "count": len(decisions),
            "decisions": decisions
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# PHASE 3.0A: Paper Execution Bridge Endpoints
# ============================================================================

@router.post("/market_dynamic/paper/run-once")
async def run_market_dynamic_paper_once(db=Depends(get_db)):
    """
    PHASE 3.0A: Run paper execution bridge once (manual trigger).
    
    Flow:
      1. Get selected signals from latest snapshot
      2. Check readiness state
      3. Filter by policy (BLOCKED/LIMITED/READY)
      4. Check duplicates & cooldown
      5. Execute paper positions
      6. Return detailed result
    
    Returns:
        {
            "ok": True,
            "readiness_state": "ready",
            "signals_in": 3,
            "signals_after_policy": 2,
            "executed": 2,
            "skipped": {"duplicate": 1, "cooldown": 0, ...}
        }
    """
    try:
        from modules.strategy.paper_execution_bridge import get_paper_bridge_service
        
        service = get_paper_bridge_service(db)
        result = await service.run_once(experiment_id="market_dynamic")
        
        return {
            "ok": True,
            **result
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/market_dynamic/paper/positions")
async def get_market_dynamic_paper_positions(
    status: Optional[str] = None,
    symbol: Optional[str] = None,
    limit: int = 50,
    db=Depends(get_db)
):
    """
    PHASE 3.0A: Get paper positions.
    
    Args:
        status: Optional filter ("open" | "closed")
        symbol: Optional symbol filter
        limit: Max results (default: 50)
    
    Returns:
        {
            "ok": True,
            "count": 10,
            "positions": [...]
        }
    """
    try:
        from modules.strategy.paper_execution_bridge.paper_position_repository import PaperPositionRepository
        
        repo = PaperPositionRepository(db)
        positions = await repo.list_positions(
            experiment_id="market_dynamic",
            status=status,
            symbol=symbol,
            limit=limit
        )
        
        return {
            "ok": True,
            "count": len(positions),
            "positions": positions
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/market_dynamic/paper/decisions")
async def get_market_dynamic_paper_decisions(
    status: Optional[str] = None,
    symbol: Optional[str] = None,
    limit: int = 50,
    db=Depends(get_db)
):
    """
    PHASE 3.0A: Get paper decisions.
    
    Args:
        status: Optional filter ("created" | "executed" | "rejected")
        symbol: Optional symbol filter
        limit: Max results (default: 50)
    
    Returns:
        {
            "ok": True,
            "count": 10,
            "decisions": [...]
        }
    """
    try:
        from modules.strategy.paper_execution_bridge.paper_decision_repository import PaperDecisionRepository
        
        repo = PaperDecisionRepository(db)
        decisions = await repo.list_decisions(
            experiment_id="market_dynamic",
            status=status,
            symbol=symbol,
            limit=limit
        )
        
        return {
            "ok": True,
            "count": len(decisions),
            "decisions": decisions
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/market_dynamic/paper/performance")
async def get_market_dynamic_paper_performance(db=Depends(get_db)):
    """
    PHASE 3.0A: Get paper execution performance summary.
    
    Returns:
        {
            "ok": True,
            "performance": {
                "total_positions": 25,
                "open_positions": 5,
                "closed_positions": 20,
                "winrate": 0.55,
                "avg_pnl": 0.012
            }
        }
    """
    try:
        from modules.strategy.paper_execution_bridge.paper_position_repository import PaperPositionRepository
        
        repo = PaperPositionRepository(db)
        performance = await repo.get_performance(experiment_id="market_dynamic")
        
        return {
            "ok": True,
            "performance": performance
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))



@router.get("/market_dynamic/execution-quality")
async def get_market_dynamic_execution_quality(
    horizon: str = "24h",
    db=Depends(get_db)
):
    """
    PHASE 3.1: Get execution quality report.
    
    Compares shadow_trades vs paper_positions to prove that
    paper execution does not destroy the discovery system's edge.
    
    Returns:
        {
            "ok": True,
            "report": {
                "summary": {
                    "matched_pairs": 25,
                    "shadow_trades": 30,
                    "paper_positions": 28,
                    "match_coverage": 0.83,
                    "execution_quality": 0.0015,
                    "shadow_winrate": 0.60,
                    "paper_winrate": 0.56,
                    "winrate_delta": -0.04
                },
                "frictions": {
                    "policy_rejection_rate": 0.20,
                    "cooldown_miss_rate": 0.10,
                    "avg_entry_delay_pct": 0.0018,
                    "max_entry_delay_pct": 0.0045
                },
                "verdict": {
                    "state": "ready" | "limited" | "blocked",
                    "reason": "...",
                    "gates_passed": ["gate1_coverage", ...],
                    "gates_failed": ["gate2_execution_quality", ...]
                },
                "thresholds": {...}
            }
        }
    
    Gates:
      1. match_coverage >= 0.7
      2. execution_quality > -0.001
      3. winrate_delta >= -0.05
      4. policy_rejection_rate <= 0.35
      5. cooldown_miss_rate <= 0.20
      6. matched_pairs >= 20
    
    Verdict:
      - AUTO_RUN_READY: All gates pass → safe for auto-run
      - AUTO_RUN_LIMITED: Quality ok but warnings → review before auto-run
      - AUTO_RUN_BLOCKED: Quality issues → do NOT enable auto-run
    """
    try:
        from modules.strategy.execution_analysis.execution_quality_service import ExecutionQualityService
        
        service = ExecutionQualityService(db)
        report = await service.get_execution_quality(
            experiment_id="market_dynamic",
            horizon=horizon
        )
        
        return {
            "ok": True,
            "report": report
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Phase 3.0B: Auto-Run Control Endpoints
# ============================================================================

@router.get("/market_dynamic/auto-run/status")
async def get_auto_run_status(request):
    """
    PHASE 3.0B: Get auto-run status.
    
    Returns current state of controlled autonomy:
      - paused / running
      - auto_disabled (hard safety)
      - last run timestamp
      - runs in last hour (rate limiting)
    
    Returns:
        {
            "ok": True,
            "status": {
                "paused": bool,
                "pause_reason": str | null,
                "auto_disabled": bool,
                "auto_disabled_reason": str | null,
                "last_run_at": str | null,
                "runs_last_hour": int
            }
        }
    """
    try:
        state = request.app.state.paper_auto_runner_state
        
        return {
            "ok": True,
            "status": state.get_status()
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/market_dynamic/auto-run/pause")
async def pause_auto_run(request):
    """
    PHASE 3.0B: Pause auto-run (manual control).
    
    Stops scheduler from executing runs.
    Can be resumed via /resume endpoint.
    
    Returns:
        {
            "ok": True,
            "message": "auto-run paused"
        }
    """
    try:
        state = request.app.state.paper_auto_runner_state
        state.pause("manual")
        
        return {
            "ok": True,
            "message": "auto-run paused"
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/market_dynamic/auto-run/resume")
async def resume_auto_run(request):
    """
    PHASE 3.0B: Resume auto-run from paused state.
    
    Re-enables scheduler execution.
    
    Returns:
        {
            "ok": True,
            "message": "auto-run resumed"
        }
    """
    try:
        state = request.app.state.paper_auto_runner_state
        state.resume()
        
        return {
            "ok": True,
            "message": "auto-run resumed"
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/market_dynamic/auto-run/enable")
async def enable_auto_run(request):
    """
    PHASE 3.0B: Enable auto-run from auto_disabled state.
    
    Clears hard safety auto_disabled flag.
    Use only after fixing underlying issue that caused auto-disable.
    
    Returns:
        {
            "ok": True,
            "message": "auto-run enabled"
        }
    """
    try:
        state = request.app.state.paper_auto_runner_state
        state.enable()
        
        return {
            "ok": True,
            "message": "auto-run enabled (auto_disabled cleared)"
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/market_dynamic/auto-run/disable")
async def disable_auto_run(request):
    """
    PHASE 3.0B: Disable auto-run (manual safety).
    
    Sets auto_disabled flag to block execution.
    More serious than pause - requires explicit /enable to clear.
    
    Returns:
        {
            "ok": True,
            "message": "auto-run disabled"
        }
    """
    try:
        state = request.app.state.paper_auto_runner_state
        state.disable("manual")
        
        return {
            "ok": True,
            "message": "auto-run disabled (requires /enable to clear)"
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/market_dynamic/auto-run/audit")
async def get_auto_run_audit(limit: int = 50, db=Depends(get_db)):
    """
    PHASE 3.0B: Get recent auto-run audit logs.
    
    Returns recent decisions (executed, skipped, errors).
    
    Args:
        limit: Max logs to return (default: 50)
    
    Returns:
        {
            "ok": True,
            "logs": [
                {
                    "decision": "AUTO_RUN_EXECUTED" | "AUTO_RUN_SKIPPED" | "AUTO_RUN_ERROR",
                    "reason": str,
                    "timestamp": str,
                    ...
                }
            ]
        }
    """
    try:
        from modules.strategy.paper_auto_runner.audit_logger import AuditLogger
        
        audit = AuditLogger(db)
        logs = await audit.get_recent_logs(
            experiment_id="market_dynamic",
            limit=limit
        )
        
        return {
            "ok": True,
            "count": len(logs),
            "logs": logs
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
