"""
Backtest Repository

Storage for historical backtest results.
Separate collection from live predictions to avoid mixing.
"""

from typing import Dict, Any, List
import time


def save_backtest_results(db, results: List[Dict[str, Any]]) -> int:
    """
    Save backtest results to database.
    
    Args:
        db: MongoDB database
        results: List of backtest result dicts
    
    Returns:
        Number of results saved
    """
    if not results:
        return 0
    
    try:
        db.prediction_backtests.insert_many(results)
        return len(results)
    except Exception as e:
        print(f"[BacktestRepo] Error saving results: {e}")
        return 0


def get_backtest_results(
    db,
    symbol: str = None,
    timeframe: str = None,
    regime: str = None,
    limit: int = 1000
) -> List[Dict[str, Any]]:
    """
    Get backtest results with optional filters.
    """
    try:
        query = {"mode": "historical_backtest"}
        if symbol:
            query["symbol"] = symbol
        if timeframe:
            query["timeframe"] = timeframe
        if regime:
            query["regime"] = regime
        
        cursor = db.prediction_backtests.find(
            query,
            {"_id": 0}
        ).limit(limit)
        
        return list(cursor)
    except Exception:
        return []


def clear_backtest_results(db, symbol: str = None) -> int:
    """
    Clear backtest results (optionally for specific symbol).
    """
    try:
        query = {"mode": "historical_backtest"}
        if symbol:
            query["symbol"] = symbol
        
        result = db.prediction_backtests.delete_many(query)
        return result.deleted_count
    except Exception:
        return 0


def get_backtest_summary(db) -> Dict[str, Any]:
    """Get summary of stored backtest results."""
    try:
        pipeline = [
            {"$match": {"mode": "historical_backtest"}},
            {"$group": {
                "_id": {"symbol": "$symbol", "timeframe": "$timeframe"},
                "count": {"$sum": 1}
            }}
        ]
        result = list(db.prediction_backtests.aggregate(pipeline))
        
        summary = {}
        total = 0
        for r in result:
            key = f"{r['_id']['symbol']}_{r['_id']['timeframe']}"
            summary[key] = r['count']
            total += r['count']
        
        return {
            "total": total,
            "by_asset_tf": summary
        }
    except Exception:
        return {"total": 0, "by_asset_tf": {}}
