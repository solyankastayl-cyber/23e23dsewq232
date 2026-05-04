"""
Prediction Worker

Background worker for:
1. Evaluating pending predictions when horizon passes
2. Running periodic calibration
3. Cleanup of old predictions
"""

import asyncio
import time
from typing import Optional
from datetime import datetime, timezone


class PredictionWorker:
    """
    Background worker for prediction evaluation and calibration.
    
    Should be run periodically (e.g., every hour).
    """
    
    def __init__(self):
        self._running = False
        self._last_evaluation_run = 0
        self._last_calibration_run = 0
        
        # Run intervals
        self.evaluation_interval = 3600  # 1 hour
        self.calibration_interval = 21600  # 6 hours
    
    async def run_once(self, price_provider=None) -> dict:
        """
        Run single iteration of worker tasks.
        
        Args:
            price_provider: Function to get current price for symbol
                           Should be async: price = await price_provider(symbol)
        
        Returns:
            Summary of work done
        """
        from .prediction_repository import get_prediction_repository
        from .prediction_evaluator import get_prediction_evaluator
        from .prediction_metrics import compute_prediction_metrics
        from .calibration_engine import get_calibration_engine
        
        repo = get_prediction_repository()
        evaluator = get_prediction_evaluator()
        calibration = get_calibration_engine()
        
        summary = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "evaluated": 0,
            "expired": 0,
            "calibrated": False,
            "errors": [],
        }
        
        now = int(time.time())
        
        # ─────────────────────────────────────────────────────────
        # 1. Evaluate pending predictions
        # ─────────────────────────────────────────────────────────
        if now - self._last_evaluation_run >= self.evaluation_interval:
            pending = repo.get_pending_predictions(limit=100)
            
            for prediction in pending:
                # Check if ready for evaluation
                if not evaluator.should_evaluate(prediction):
                    continue
                
                # Get current price
                symbol = prediction.get("symbol", "BTC")
                
                if price_provider:
                    try:
                        current_price = await price_provider(symbol)
                    except Exception as e:
                        summary["errors"].append(f"Price fetch error for {symbol}: {e}")
                        continue
                else:
                    current_price = await self._fallback_price_provider(symbol)
                
                if current_price is None or current_price == 0:
                    # Mark as expired if can't get price
                    repo.mark_expired(str(prediction["_id"]))
                    summary["expired"] += 1
                    continue
                
                # Evaluate
                evaluation = evaluator.evaluate(prediction, current_price)
                
                # Update in DB
                repo.update_evaluation(str(prediction["_id"]), evaluation)
                summary["evaluated"] += 1
            
            self._last_evaluation_run = now
        
        # ─────────────────────────────────────────────────────────
        # 2. Run calibration if enough time passed
        # ─────────────────────────────────────────────────────────
        if now - self._last_calibration_run >= self.calibration_interval:
            resolved = repo.get_resolved_predictions(limit=500)
            
            if len(resolved) >= 50:
                new_weights = calibration.calibrate(resolved)
                if new_weights:
                    summary["calibrated"] = True
                    summary["new_weights"] = new_weights
            
            self._last_calibration_run = now
        
        return summary
    
    async def _fallback_price_provider(self, symbol: str) -> Optional[float]:
        """Fallback price provider using database."""
        try:
            from core.database import get_database
            db = get_database()
            if db is None:
                return None
            
            # Try candles collection
            doc = db.candles.find_one(
                {"symbol": symbol.upper()},
                {"close": 1},
                sort=[("timestamp", -1)]
            )
            
            if doc and "close" in doc:
                return float(doc["close"])
            
            return None
        except Exception:
            return None
    
    def should_run_evaluation(self) -> bool:
        """Check if evaluation should run."""
        return (int(time.time()) - self._last_evaluation_run) >= self.evaluation_interval
    
    def should_run_calibration(self) -> bool:
        """Check if calibration should run."""
        return (int(time.time()) - self._last_calibration_run) >= self.calibration_interval


# Singleton
_worker: Optional[PredictionWorker] = None


def get_prediction_worker() -> PredictionWorker:
    """Get singleton worker instance."""
    global _worker
    if _worker is None:
        _worker = PredictionWorker()
    return _worker


async def run_prediction_worker_once(price_provider=None) -> dict:
    """Convenience function to run worker once."""
    return await get_prediction_worker().run_once(price_provider)
