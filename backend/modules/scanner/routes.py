"""
Scanner API Routes

REST API for scanner operations.
"""

from fastapi import APIRouter, Query, HTTPException
from typing import Optional, List
from datetime import datetime

from .asset_registry import get_asset_registry
from .job_queue import get_job_queue
from .scan_planner import get_scan_planner
from .prediction_scan_worker import get_prediction_scan_worker
from .scheduler import get_scanner_scheduler


router = APIRouter(prefix="/api/scanner", tags=["scanner"])


@router.get("/health")
async def health():
    """Health check for scanner service."""
    return {
        "status": "ok",
        "service": "scanner",
        "timestamp": datetime.utcnow().isoformat(),
    }


# ══════════════════════════════════════════════════════════════
# ASSET REGISTRY
# ══════════════════════════════════════════════════════════════

@router.get("/assets")
async def get_assets(limit: int = 50):
    """Get active assets from registry."""
    registry = get_asset_registry()
    assets = registry.get_active_assets(limit=limit)
    
    return {
        "count": len(assets),
        "assets": [a.to_dict() for a in assets],
    }


@router.post("/assets/seed")
async def seed_assets():
    """Seed default top 50 crypto assets."""
    registry = get_asset_registry()
    count = registry.seed_default_assets()
    
    return {
        "status": "seeded",
        "count": count,
    }


@router.get("/assets/stats")
async def get_asset_stats():
    """Get asset registry statistics."""
    registry = get_asset_registry()
    return registry.get_stats()


# ══════════════════════════════════════════════════════════════
# JOB QUEUE
# ══════════════════════════════════════════════════════════════

@router.get("/queue/stats")
async def get_queue_stats():
    """Get job queue statistics."""
    queue = get_job_queue()
    return queue.get_queue_stats()


@router.get("/queue/pending")
async def get_pending_jobs(limit: int = 20):
    """Get pending jobs in queue."""
    queue = get_job_queue()
    jobs = queue.get_pending_jobs(limit=limit)
    
    return {
        "count": len(jobs),
        "jobs": [j.to_dict() for j in jobs],
    }


@router.post("/queue/cleanup")
async def cleanup_queue():
    """Clean up stale and old jobs."""
    queue = get_job_queue()
    
    stale_cleared = queue.clear_stale_jobs()
    old_deleted = queue.cleanup_old_jobs()
    
    return {
        "stale_jobs_cleared": stale_cleared,
        "old_jobs_deleted": old_deleted,
    }


# ══════════════════════════════════════════════════════════════
# SCAN PLANNER
# ══════════════════════════════════════════════════════════════

@router.post("/scan/universe")
async def scan_universe(
    limit: int = Query(50, description="Number of assets to scan"),
    timeframes: List[str] = Query(["4H", "1D"], description="Timeframes"),
):
    """Enqueue scan jobs for asset universe."""
    planner = get_scan_planner()
    result = planner.enqueue_universe_scan(limit=limit, timeframes=timeframes)
    
    return result


@router.post("/scan/asset/{symbol}")
async def scan_asset(
    symbol: str,
    timeframes: List[str] = Query(["4H", "1D"], description="Timeframes"),
):
    """Enqueue scan jobs for single asset."""
    planner = get_scan_planner()
    result = planner.enqueue_single_asset(symbol.upper(), timeframes=timeframes)
    
    return result


# ══════════════════════════════════════════════════════════════
# PREDICTIONS (SNAPSHOTS)
# ══════════════════════════════════════════════════════════════

@router.get("/predictions/latest")
async def get_latest_predictions(
    symbol: Optional[str] = None,
    timeframe: Optional[str] = None,
    limit: int = 50,
):
    """Get latest prediction snapshots."""
    worker = get_prediction_scan_worker()
    
    if symbol:
        # Get specific asset
        pred = worker.get_latest_prediction(symbol.upper(), timeframe or "1D")
        if pred:
            return {"predictions": [pred]}
        return {"predictions": []}
    
    # Get batch
    predictions = worker.get_latest_predictions_batch(limit=limit)
    
    return {
        "count": len(predictions),
        "predictions": predictions,
    }


@router.get("/predictions/top")
async def get_top_predictions(limit: int = 20):
    """Get top ranked valid predictions (Decision Engine filtered)."""
    worker = get_prediction_scan_worker()
    predictions = worker.get_top_predictions(limit=limit)
    
    return {
        "count": len(predictions),
        "predictions": predictions,
    }


@router.get("/predictions/all")
async def get_all_predictions(limit: int = 50, valid_only: bool = False):
    """Get all latest predictions (including invalid for analysis)."""
    worker = get_prediction_scan_worker()
    predictions = worker.get_latest_predictions_batch(
        limit=limit,
        valid_only=valid_only
    )
    
    return {
        "count": len(predictions),
        "predictions": predictions,
    }


# ══════════════════════════════════════════════════════════════
# DEBUG / SINGLE ASSET SCAN
# ══════════════════════════════════════════════════════════════

@router.get("/debug/{symbol}")
async def debug_single_asset(
    symbol: str,
    timeframe: str = "4H",
):
    """
    Debug: run real TA + Prediction for a single asset.
    
    Returns full pipeline output for manual verification.
    Shows: candle count, pattern, structure, indicators, prediction.
    """
    from .ta_to_prediction_adapter import build_real_ta, build_real_prediction
    
    # Run TA
    ta_payload = build_real_ta(symbol.upper(), timeframe.upper())
    
    # Run Prediction
    prediction = build_real_prediction(ta_payload)
    
    # Enrich with score
    from .ranking import enrich_prediction_with_score
    enriched = enrich_prediction_with_score(prediction)
    
    return {
        "symbol": symbol.upper(),
        "timeframe": timeframe.upper(),
        "ta_summary": {
            "price": ta_payload.get("price"),
            "pattern": ta_payload.get("pattern"),
            "structure": ta_payload.get("structure"),
            "indicators": ta_payload.get("indicators"),
            "ta_source": ta_payload.get("_ta_source"),
            "ta_regime": ta_payload.get("_ta_layers_regime"),
            "error": ta_payload.get("_error"),
        },
        "prediction": enriched,
    }


# ══════════════════════════════════════════════════════════════
# SCHEDULER
# ══════════════════════════════════════════════════════════════

@router.get("/status")
async def get_scanner_status():
    """Get scanner scheduler status."""
    scheduler = get_scanner_scheduler()
    return scheduler.get_status()


@router.post("/tick")
async def trigger_tick(asset_limit: int = 50):
    """
    Manually trigger scheduler tick.
    
    Uses REAL TA Engine + Prediction Engine.
    """
    from .ta_to_prediction_adapter import build_real_ta, build_real_prediction
    
    scheduler = get_scanner_scheduler()
    result = scheduler.tick(
        build_ta_fn=build_real_ta,
        build_prediction_fn=build_real_prediction,
        asset_limit=asset_limit,
    )
    
    return result


@router.post("/full-scan")
async def trigger_full_scan(
    asset_limit: int = 50,
    timeframes: List[str] = Query(["4H", "1D"], description="Timeframes"),
):
    """
    Trigger a full scan of the universe.
    
    Uses REAL TA Engine + Prediction Engine.
    """
    from .ta_to_prediction_adapter import build_real_ta, build_real_prediction
    
    scheduler = get_scanner_scheduler()
    result = scheduler.run_full_scan(
        build_ta_fn=build_real_ta,
        build_prediction_fn=build_real_prediction,
        asset_limit=asset_limit,
        timeframes=timeframes,
    )
    
    return result


# ══════════════════════════════════════════════════════════════
# LOGGING & MONITORING
# ══════════════════════════════════════════════════════════════

@router.get("/logs/recent")
async def get_recent_logs(limit: int = 50):
    """Get recent scan logs for monitoring."""
    from .scan_logger import get_recent_logs
    logs = get_recent_logs(limit=limit)
    return {
        "count": len(logs),
        "logs": logs,
    }


@router.get("/logs/summary")
async def get_logs_summary():
    """Get summary statistics from scan logs."""
    from .scan_logger import get_logs_summary
    return get_logs_summary()


@router.post("/logs/clear")
async def clear_logs():
    """Clear all scan logs."""
    from .scan_logger import clear_logs
    return clear_logs()


# ══════════════════════════════════════════════════════════════
# P3: OUTCOME TRACKING & METRICS
# ══════════════════════════════════════════════════════════════

@router.post("/outcomes/resolve")
async def run_outcome_resolution():
    """Run outcome resolution worker to resolve pending predictions."""
    from pymongo import MongoClient
    import os
    
    client = MongoClient(os.environ.get("MONGO_URL", "mongodb://localhost:27017"))
    db = client[os.environ.get("DB_NAME", "test_database")]
    
    from workers.prediction_outcome_worker import run_prediction_outcome_worker, create_price_provider
    
    price_provider = create_price_provider(db)
    result = run_prediction_outcome_worker(db, price_provider)
    
    return {
        "status": "complete",
        "stats": result
    }


@router.get("/metrics")
async def get_prediction_metrics():
    """Get global prediction metrics."""
    from pymongo import MongoClient
    import os
    
    client = MongoClient(os.environ.get("MONGO_URL", "mongodb://localhost:27017"))
    db = client[os.environ.get("DB_NAME", "test_database")]
    
    from modules.prediction.metrics_engine import get_latest_metrics_snapshot
    
    snapshot = get_latest_metrics_snapshot(db)
    return snapshot or {"status": "no_metrics_yet"}


@router.get("/metrics/by-regime")
async def get_metrics_by_regime():
    """Get prediction metrics grouped by regime."""
    from pymongo import MongoClient
    import os
    
    client = MongoClient(os.environ.get("MONGO_URL", "mongodb://localhost:27017"))
    db = client[os.environ.get("DB_NAME", "test_database")]
    
    from modules.prediction.metrics_engine import get_metrics_by_regime
    
    return get_metrics_by_regime(db)


@router.get("/metrics/by-model")
async def get_metrics_by_model():
    """Get prediction metrics grouped by model."""
    from pymongo import MongoClient
    import os
    
    client = MongoClient(os.environ.get("MONGO_URL", "mongodb://localhost:27017"))
    db = client[os.environ.get("DB_NAME", "test_database")]
    
    from modules.prediction.metrics_engine import get_metrics_by_model
    
    return get_metrics_by_model(db)


@router.post("/metrics/compute")
async def compute_metrics_snapshot():
    """Compute and store new metrics snapshot."""
    from pymongo import MongoClient
    import os
    
    client = MongoClient(os.environ.get("MONGO_URL", "mongodb://localhost:27017"))
    db = client[os.environ.get("DB_NAME", "test_database")]
    
    from workers.prediction_metrics_worker import run_prediction_metrics_worker
    
    snapshot = run_prediction_metrics_worker(db)
    return {
        "status": "computed",
        "global": snapshot.get("global", {})
    }


# ══════════════════════════════════════════════════════════════
# P4: CALIBRATION
# ══════════════════════════════════════════════════════════════

@router.get("/calibration/status")
async def get_calibration_status():
    """Get current calibration status."""
    from pymongo import MongoClient
    import os
    
    client = MongoClient(os.environ.get("MONGO_URL", "mongodb://localhost:27017"))
    db = client[os.environ.get("DB_NAME", "test_database")]
    
    from modules.prediction.calibration_engine_v2 import get_calibration_status
    
    return get_calibration_status(db)


@router.post("/calibration/recalibrate")
async def run_recalibration():
    """Run recalibration based on resolved outcomes."""
    from pymongo import MongoClient
    import os
    
    client = MongoClient(os.environ.get("MONGO_URL", "mongodb://localhost:27017"))
    db = client[os.environ.get("DB_NAME", "test_database")]
    
    from workers.prediction_calibration_worker import run_prediction_calibration_worker
    
    result = run_prediction_calibration_worker(db)
    return {
        "status": "recalibrated",
        "regime_weights": result.get("regime_weights", {}),
        "model_weights": result.get("model_weights", {})
    }


# ══════════════════════════════════════════════════════════════
# P5: STABILITY & ANTI-DRIFT
# ══════════════════════════════════════════════════════════════

@router.get("/stability/status")
async def get_stability_status():
    """Get current stability status."""
    from pymongo import MongoClient
    import os
    
    client = MongoClient(os.environ.get("MONGO_URL", "mongodb://localhost:27017"))
    db = client[os.environ.get("DB_NAME", "test_database")]
    
    from modules.prediction.stability_engine import get_stability_status
    
    return get_stability_status(db)


@router.get("/stability/models")
async def get_model_health():
    """Get model health status and penalties."""
    from pymongo import MongoClient
    import os
    
    client = MongoClient(os.environ.get("MONGO_URL", "mongodb://localhost:27017"))
    db = client[os.environ.get("DB_NAME", "test_database")]
    
    from modules.prediction.stability_engine import get_stability_status
    
    doc = get_stability_status(db)
    return {
        "model_health": doc.get("model_health", {}),
        "model_penalties": doc.get("model_penalties", {}),
        "regime_instability": doc.get("regime_instability", {})
    }


@router.post("/stability/rebuild")
async def rebuild_stability():
    """Rebuild stability document."""
    from pymongo import MongoClient
    import os
    
    client = MongoClient(os.environ.get("MONGO_URL", "mongodb://localhost:27017"))
    db = client[os.environ.get("DB_NAME", "test_database")]
    
    from workers.prediction_stability_worker import run_prediction_stability_worker
    
    result = run_prediction_stability_worker(db)
    return {
        "status": "rebuilt",
        "model_health": result.get("model_health", {}),
        "calibration_guard": result.get("calibration_guard", {})
    }


# ══════════════════════════════════════════════════════════════
# P6: HISTORICAL BACKTEST
# ══════════════════════════════════════════════════════════════

@router.post("/backtest/run/{symbol}")
async def run_single_backtest(symbol: str, timeframe: str = "4H", days: int = 180):
    """
    Run backtest for a single symbol.
    
    First loads historical candles, then runs backtest.
    """
    from pymongo import MongoClient
    import os
    
    client = MongoClient(os.environ.get("MONGO_URL", "mongodb://localhost:27017"))
    db = client[os.environ.get("DB_NAME", "test_database")]
    
    from modules.scanner.market_data import get_market_data_provider
    from modules.ta_engine.per_tf_builder import build_ta_from_candles
    from modules.prediction.prediction_engine_v3 import build_prediction_regime_aware
    from workers.prediction_backtest_worker import run_backtest_worker
    
    # Load historical candles
    provider = get_market_data_provider()
    
    # Calculate limit based on days and timeframe
    if timeframe == "4H":
        limit = days * 6  # 6 candles per day
    elif timeframe == "1D":
        limit = days
    else:
        limit = days * 6
    
    candles = provider.get_candles(symbol, timeframe, limit=limit)
    
    if not candles or len(candles) < 150:
        return {
            "error": f"Not enough candles for {symbol}: got {len(candles) if candles else 0}, need 150+"
        }
    
    # Define builders
    def ta_builder(candles, sym, tf):
        return build_ta_from_candles(candles, sym, tf)
    
    # PHASE 2.2: Use V2 prediction engine
    def prediction_builder(inp):
        from modules.prediction.prediction_engine_v2 import build_prediction_v2
        return build_prediction_v2(inp)
    
    # Run backtest
    result = run_backtest_worker(
        db=db,
        symbol=symbol,
        timeframe=timeframe,
        candles=candles,
        ta_builder=ta_builder,
        prediction_builder=prediction_builder,
        use_v2=True  # Enable V2 decision-based filtering
    )
    
    return result


@router.post("/backtest/run-multi")
async def run_multi_backtest(
    symbols: str = "BTC,ETH,SOL",
    timeframes: str = "4H,1D",
    days: int = 180
):
    """
    Run backtest for multiple symbols and timeframes.
    
    Args:
        symbols: Comma-separated list of symbols
        timeframes: Comma-separated list of timeframes
        days: Days of history
    """
    from pymongo import MongoClient
    import os
    
    client = MongoClient(os.environ.get("MONGO_URL", "mongodb://localhost:27017"))
    db = client[os.environ.get("DB_NAME", "test_database")]
    
    from modules.scanner.market_data import get_market_data_provider
    from modules.ta_engine.per_tf_builder import build_ta_from_candles
    from modules.prediction.prediction_engine_v3 import build_prediction_regime_aware
    from workers.prediction_backtest_worker import run_multi_asset_backtest
    
    symbol_list = [s.strip().upper() for s in symbols.split(",")]
    tf_list = [t.strip().upper() for t in timeframes.split(",")]
    
    provider = get_market_data_provider()
    
    def candle_loader(symbol, timeframe, days):
        if timeframe == "4H":
            limit = days * 6
        elif timeframe == "1D":
            limit = days
        else:
            limit = days * 6
        return provider.get_candles(symbol, timeframe, limit=limit)
    
    def ta_builder(candles, sym, tf):
        return build_ta_from_candles(candles, sym, tf)
    
    def prediction_builder(inp):
        return build_prediction_regime_aware(inp)
    
    result = run_multi_asset_backtest(
        db=db,
        symbols=symbol_list,
        timeframes=tf_list,
        candle_loader=candle_loader,
        ta_builder=ta_builder,
        prediction_builder=prediction_builder,
        days=days
    )
    
    return result


@router.get("/backtest/metrics")
async def get_backtest_metrics():
    """Get global backtest metrics."""
    from pymongo import MongoClient
    import os
    
    client = MongoClient(os.environ.get("MONGO_URL", "mongodb://localhost:27017"))
    db = client[os.environ.get("DB_NAME", "test_database")]
    
    from modules.prediction.backtest_repository import get_backtest_results
    from modules.prediction.backtest_metrics import compute_backtest_metrics
    
    results = get_backtest_results(db, limit=5000)
    return compute_backtest_metrics(results)


@router.get("/backtest/metrics/by-regime")
async def get_backtest_metrics_by_regime():
    """Get backtest metrics grouped by regime."""
    from pymongo import MongoClient
    import os
    
    client = MongoClient(os.environ.get("MONGO_URL", "mongodb://localhost:27017"))
    db = client[os.environ.get("DB_NAME", "test_database")]
    
    from modules.prediction.backtest_repository import get_backtest_results
    from modules.prediction.backtest_metrics import group_by_field
    
    results = get_backtest_results(db, limit=5000)
    return group_by_field(results, "regime")


@router.get("/backtest/metrics/by-model")
async def get_backtest_metrics_by_model():
    """Get backtest metrics grouped by model."""
    from pymongo import MongoClient
    import os
    
    client = MongoClient(os.environ.get("MONGO_URL", "mongodb://localhost:27017"))
    db = client[os.environ.get("DB_NAME", "test_database")]
    
    from modules.prediction.backtest_repository import get_backtest_results
    from modules.prediction.backtest_metrics import group_by_field
    
    results = get_backtest_results(db, limit=5000)
    return group_by_field(results, "model")


@router.get("/backtest/metrics/by-symbol")
async def get_backtest_metrics_by_symbol():
    """Get backtest metrics grouped by symbol."""
    from pymongo import MongoClient
    import os
    
    client = MongoClient(os.environ.get("MONGO_URL", "mongodb://localhost:27017"))
    db = client[os.environ.get("DB_NAME", "test_database")]
    
    from modules.prediction.backtest_repository import get_backtest_results
    from modules.prediction.backtest_metrics import group_by_field
    
    results = get_backtest_results(db, limit=5000)
    return group_by_field(results, "symbol")


@router.get("/backtest/summary")
async def get_backtest_summary():
    """Get summary of stored backtest results."""
    from pymongo import MongoClient
    import os
    
    client = MongoClient(os.environ.get("MONGO_URL", "mongodb://localhost:27017"))
    db = client[os.environ.get("DB_NAME", "test_database")]
    
    from modules.prediction.backtest_repository import get_backtest_summary
    
    return get_backtest_summary(db)


@router.delete("/backtest/clear")
async def clear_backtest_results(symbol: str = None):
    """Clear backtest results (optionally for specific symbol)."""
    from pymongo import MongoClient
    import os
    
    client = MongoClient(os.environ.get("MONGO_URL", "mongodb://localhost:27017"))
    db = client[os.environ.get("DB_NAME", "test_database")]
    
    from modules.prediction.backtest_repository import clear_backtest_results as clear_bt
    
    cleared = clear_bt(db, symbol)
    return {"cleared": cleared}


def register_routes(app):
    """Register scanner routes with FastAPI app."""
    app.include_router(router)
