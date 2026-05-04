"""
Prediction Outcome Worker

Resolves pending predictions based on actual price movements.
"""

import time
from typing import Dict, Any, Callable

from modules.prediction.resolution_engine import (
    should_resolve_by_horizon,
    try_early_resolution,
    resolve_at_horizon,
)
from modules.prediction.outcome_repository import (
    get_pending_predictions,
    mark_prediction_resolved,
    log_resolution_event,
)


def run_prediction_outcome_worker(
    db,
    price_provider: Callable[[str], float],
    max_predictions: int = 100
) -> Dict[str, Any]:
    """
    Process pending predictions and resolve those that are due.
    
    Args:
        db: MongoDB database
        price_provider: Function(symbol) -> current_price
        max_predictions: Max predictions to process per run
    
    Returns:
        Summary of processed predictions
    """
    now_ts = int(time.time())
    pending = get_pending_predictions(db, limit=max_predictions)
    
    stats = {
        "processed": 0,
        "resolved": 0,
        "correct": 0,
        "partial": 0,
        "wrong": 0,
        "still_pending": 0,
        "errors": 0,
    }
    
    for pred in pending:
        stats["processed"] += 1
        
        try:
            symbol = pred.get("symbol", "")
            timeframe = pred.get("timeframe", "")
            
            # Get current price
            current_price = price_provider(symbol)
            if current_price <= 0:
                stats["errors"] += 1
                continue
            
            # Try early resolution first
            resolution = try_early_resolution(pred, current_price)
            
            if resolution:
                # Early resolution (target hit or wrong early)
                mark_prediction_resolved(db, pred["_id"], resolution)
                log_resolution_event(
                    db, pred["_id"], symbol, timeframe,
                    f"resolved_{resolution['result']}_early",
                    {"actual_price": current_price, "resolution": resolution}
                )
                stats["resolved"] += 1
                stats[resolution["result"]] = stats.get(resolution["result"], 0) + 1
                continue
            
            # Check horizon-based resolution
            if should_resolve_by_horizon(pred, now_ts):
                resolution = resolve_at_horizon(pred, current_price)
                mark_prediction_resolved(db, pred["_id"], resolution)
                log_resolution_event(
                    db, pred["_id"], symbol, timeframe,
                    f"resolved_{resolution['result']}_horizon",
                    {"actual_price": current_price, "resolution": resolution}
                )
                stats["resolved"] += 1
                stats[resolution["result"]] = stats.get(resolution["result"], 0) + 1
            else:
                stats["still_pending"] += 1
                
        except Exception as e:
            print(f"[OutcomeWorker] Error processing {pred.get('symbol')}: {e}")
            stats["errors"] += 1
    
    return stats


def create_price_provider(db):
    """
    Create a simple price provider using cached market data.
    
    Falls back to prediction's start_price if no current data.
    """
    from modules.scanner.market_data import get_market_data_provider
    
    provider = get_market_data_provider()
    
    def get_price(symbol: str) -> float:
        try:
            # Try to get current price from provider
            candles = provider.get_candles(symbol, "1H", limit=1)
            if candles and len(candles) > 0:
                return float(candles[-1].get("close", 0))
        except Exception as e:
            print(f"[PriceProvider] Error getting price for {symbol}: {e}")
        return 0.0
    
    return get_price
