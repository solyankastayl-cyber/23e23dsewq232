"""
Prediction Backtest Worker

Runs historical backtests for specified assets.
"""

from typing import Dict, Any, List, Callable
import time

from modules.prediction.backtest_runner import run_backtest, compute_horizon_bars
from modules.prediction.backtest_repository import save_backtest_results, clear_backtest_results


def run_backtest_worker(
    db,
    symbol: str,
    timeframe: str,
    candles: List[Dict[str, Any]],
    ta_builder: Callable,
    prediction_builder: Callable,
    step: int = None,
    horizon_days: int = 5,
    clear_existing: bool = True,
    use_v2: bool = True  # Use V2 decision-based engine
) -> Dict[str, Any]:
    """
    Run backtest for a single symbol/timeframe.
    
    Args:
        db: MongoDB database
        symbol: Asset symbol
        timeframe: Timeframe (4H, 1D)
        candles: Historical candle data
        ta_builder: Function to build TA from candles
        prediction_builder: Function to build prediction from TA
        step: Candle step (default: 2 for 4H, 1 for 1D)
        horizon_days: Days to wait for resolution (default 5)
        clear_existing: Clear existing backtest results first
        use_v2: Use V2 decision-based prediction engine
    
    Returns:
        Summary dict with count, timing
    """
    start_time = time.time()
    
    # Default step based on timeframe
    if step is None:
        step = 1 if timeframe == "1D" else 2
    
    # Compute horizon in bars
    horizon_bars = compute_horizon_bars(timeframe, horizon_days)
    
    # Clear existing results if requested
    if clear_existing:
        cleared = clear_backtest_results(db, symbol)
        print(f"[BacktestWorker] Cleared {cleared} existing results for {symbol}")
    
    # Run backtest with V2 flag
    results = run_backtest(
        symbol=symbol,
        timeframe=timeframe,
        candles=candles,
        ta_builder=ta_builder,
        prediction_builder=prediction_builder,
        step=step,
        horizon_bars=horizon_bars,
        min_history=100,
        use_v2=use_v2
    )
    
    # Save results
    saved = save_backtest_results(db, results)
    
    elapsed = time.time() - start_time
    
    return {
        "symbol": symbol,
        "timeframe": timeframe,
        "candles_processed": len(candles),
        "predictions_generated": len(results),
        "predictions_saved": saved,
        "step": step,
        "horizon_bars": horizon_bars,
        "elapsed_seconds": round(elapsed, 2)
    }


def run_multi_asset_backtest(
    db,
    symbols: List[str],
    timeframes: List[str],
    candle_loader: Callable,
    ta_builder: Callable,
    prediction_builder: Callable,
    days: int = 180
) -> Dict[str, Any]:
    """
    Run backtest for multiple assets and timeframes.
    
    Args:
        db: MongoDB database
        symbols: List of symbols to backtest
        timeframes: List of timeframes to backtest
        candle_loader: Function(symbol, timeframe, days) -> candles
        ta_builder: Function to build TA
        prediction_builder: Function to build prediction
        days: Days of history to use
    
    Returns:
        Summary dict with results per asset
    """
    start_time = time.time()
    results = {}
    total_predictions = 0
    
    for symbol in symbols:
        for timeframe in timeframes:
            key = f"{symbol}_{timeframe}"
            
            try:
                # Load candles
                candles = candle_loader(symbol, timeframe, days)
                
                if not candles or len(candles) < 150:
                    results[key] = {"error": f"Not enough candles: {len(candles) if candles else 0}"}
                    continue
                
                # Run backtest
                result = run_backtest_worker(
                    db=db,
                    symbol=symbol,
                    timeframe=timeframe,
                    candles=candles,
                    ta_builder=ta_builder,
                    prediction_builder=prediction_builder
                )
                
                results[key] = result
                total_predictions += result.get("predictions_saved", 0)
                
            except Exception as e:
                results[key] = {"error": str(e)}
    
    elapsed = time.time() - start_time
    
    return {
        "total_predictions": total_predictions,
        "assets_processed": len(symbols) * len(timeframes),
        "elapsed_seconds": round(elapsed, 2),
        "results": results
    }
