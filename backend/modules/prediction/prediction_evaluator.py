"""
Prediction Evaluator

Evaluates predictions against actual price outcomes.
"""

import time
from typing import Dict, Optional
from datetime import datetime, timezone


class PredictionEvaluator:
    """
    Evaluates prediction accuracy.
    
    Results:
    - correct: direction correct AND error < 3%
    - partial: direction correct BUT error >= 3%
    - wrong: direction wrong
    """
    
    # Error thresholds
    ERROR_CORRECT_THRESHOLD = 0.03   # 3% error = still correct
    ERROR_PARTIAL_THRESHOLD = 0.10   # 10% error = partial credit
    
    def evaluate(
        self, 
        prediction: Dict, 
        current_price: float
    ) -> Dict:
        """
        Evaluate a prediction against current/final price.
        
        Args:
            prediction: Stored prediction document
            current_price: Actual price at evaluation time
        
        Returns:
            Evaluation result dict
        """
        start_price = prediction.get("price_at_prediction", 0)
        pred_data = prediction.get("prediction", {})
        
        target_price = pred_data.get("target_price", start_price)
        direction = pred_data.get("direction", "neutral")
        
        if start_price == 0:
            return self._error_result("Invalid start price")
        
        # Calculate actual move
        actual_move = (current_price - start_price) / start_price
        
        # Calculate predicted move
        predicted_move = (target_price - start_price) / start_price
        
        # Check direction correctness
        direction_correct = self._check_direction(direction, actual_move)
        
        # Calculate error
        error_pct = abs(current_price - target_price) / target_price if target_price > 0 else 1.0
        
        # Determine result
        result = self._determine_result(direction_correct, error_pct)
        
        return {
            "result": result,
            "real_price": current_price,
            "error_pct": round(error_pct, 4),
            "direction_correct": direction_correct,
            "actual_move": round(actual_move, 4),
            "predicted_move": round(predicted_move, 4),
            "evaluated_at": datetime.now(timezone.utc).isoformat(),
        }
    
    def _check_direction(self, predicted_direction: str, actual_move: float) -> bool:
        """Check if predicted direction matches actual movement."""
        # Small moves (< 0.5%) are considered neutral
        if abs(actual_move) < 0.005:
            return predicted_direction == "neutral"
        
        actual_direction = "bullish" if actual_move > 0 else "bearish"
        
        if predicted_direction == "neutral":
            # Neutral predictions are "correct" if move is small (< 2%)
            return abs(actual_move) < 0.02
        
        return predicted_direction == actual_direction
    
    def _determine_result(self, direction_correct: bool, error_pct: float) -> str:
        """Determine evaluation result."""
        if not direction_correct:
            return "wrong"
        
        if error_pct < self.ERROR_CORRECT_THRESHOLD:
            return "correct"
        
        if error_pct < self.ERROR_PARTIAL_THRESHOLD:
            return "partial"
        
        # Direction was right but target was way off
        return "partial"
    
    def _error_result(self, reason: str) -> Dict:
        """Return error evaluation result."""
        return {
            "result": "error",
            "reason": reason,
            "real_price": None,
            "error_pct": None,
            "direction_correct": None,
            "evaluated_at": datetime.now(timezone.utc).isoformat(),
        }
    
    def should_evaluate(self, prediction: Dict) -> bool:
        """
        Check if prediction should be evaluated now.
        
        Evaluation happens when horizon has passed.
        """
        created_at = prediction.get("created_at", 0)
        horizon_days = prediction.get("prediction", {}).get("horizon_days", 5)
        
        horizon_seconds = horizon_days * 86400
        now = int(time.time())
        
        return now >= (created_at + horizon_seconds)
    
    def get_time_until_evaluation(self, prediction: Dict) -> int:
        """Get seconds until prediction can be evaluated."""
        created_at = prediction.get("created_at", 0)
        horizon_days = prediction.get("prediction", {}).get("horizon_days", 5)
        
        horizon_seconds = horizon_days * 86400
        evaluation_time = created_at + horizon_seconds
        
        return max(0, evaluation_time - int(time.time()))


# Singleton
_evaluator: Optional[PredictionEvaluator] = None


def get_prediction_evaluator() -> PredictionEvaluator:
    """Get singleton evaluator instance."""
    global _evaluator
    if _evaluator is None:
        _evaluator = PredictionEvaluator()
    return _evaluator
