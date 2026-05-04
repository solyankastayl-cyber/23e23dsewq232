"""
Calibration Engine

Self-adjusting weights based on prediction performance.
System learns which signals work better and adjusts accordingly.
"""

import time
from typing import Dict, List, Optional
from datetime import datetime, timezone


# Default weights
DEFAULT_WEIGHTS = {
    "pattern": 0.40,
    "structure": 0.30,
    "momentum": 0.30,
}

# Weight limits (prevent extreme values)
MIN_WEIGHT = 0.10
MAX_WEIGHT = 0.70

# Minimum predictions needed for calibration
MIN_PREDICTIONS_FOR_CALIBRATION = 50


class CalibrationEngine:
    """
    Adaptive weight calibration based on prediction performance.
    
    Process:
    1. Collect predictions with contribution tracking
    2. After enough data, compute which factors perform better
    3. Adjust weights proportionally
    4. Save new weights to database
    """
    
    def __init__(self, db=None):
        self.db = db
        self._ensure_db()
        self._cached_weights: Optional[Dict] = None
        self._cache_timestamp: int = 0
        self._cache_ttl: int = 300  # 5 minutes
    
    def _ensure_db(self):
        """Ensure database connection."""
        if self.db is None:
            try:
                from core.database import get_database
                self.db = get_database()
            except Exception:
                self.db = None
    
    def get_weights(self, force_refresh: bool = False) -> Dict:
        """
        Get current calibrated weights.
        
        Uses caching to avoid frequent DB reads.
        """
        now = int(time.time())
        
        # Return cached if valid
        if not force_refresh and self._cached_weights and (now - self._cache_timestamp) < self._cache_ttl:
            return self._cached_weights.copy()
        
        # Try to load from DB
        weights = self._load_weights_from_db()
        
        if weights:
            self._cached_weights = weights
            self._cache_timestamp = now
            return weights.copy()
        
        return DEFAULT_WEIGHTS.copy()
    
    def calibrate(self, predictions: List[Dict]) -> Optional[Dict]:
        """
        Calibrate weights based on prediction performance.
        
        Args:
            predictions: List of resolved predictions with contributions
        
        Returns:
            New weights if calibration performed, None otherwise
        """
        # Filter resolved predictions with contributions
        valid = [
            p for p in predictions 
            if p.get("status") == "resolved" 
            and p.get("contributions")
            and p.get("evaluation", {}).get("result") in ["correct", "partial", "wrong"]
        ]
        
        if len(valid) < MIN_PREDICTIONS_FOR_CALIBRATION:
            return None
        
        # Calculate performance scores for each factor
        scores = self._calculate_factor_scores(valid)
        
        # Convert scores to weights
        new_weights = self._scores_to_weights(scores)
        
        # Save to database
        self._save_weights(new_weights, scores, len(valid))
        
        # Update cache
        self._cached_weights = new_weights
        self._cache_timestamp = int(time.time())
        
        return new_weights
    
    def _calculate_factor_scores(self, predictions: List[Dict]) -> Dict[str, float]:
        """
        Calculate performance score for each factor.
        
        Higher score = factor contributes more to correct predictions.
        """
        factors = ["pattern", "structure", "momentum"]
        
        # Accumulate contribution-weighted results
        factor_data = {f: {"correct_sum": 0.0, "wrong_sum": 0.0, "total_sum": 0.0} for f in factors}
        
        for p in predictions:
            contributions = p.get("contributions", {})
            result = p.get("evaluation", {}).get("result", "wrong")
            
            # Weight: 1.0 for correct, 0.5 for partial, 0.0 for wrong
            result_weight = {"correct": 1.0, "partial": 0.5, "wrong": 0.0}.get(result, 0.0)
            
            for factor in factors:
                contrib_value = abs(contributions.get(factor, 0))
                
                factor_data[factor]["total_sum"] += contrib_value
                factor_data[factor]["correct_sum"] += contrib_value * result_weight
                
                if result == "wrong":
                    factor_data[factor]["wrong_sum"] += contrib_value
        
        # Calculate score: ratio of correct contribution to total
        scores = {}
        for factor in factors:
            total = factor_data[factor]["total_sum"]
            correct = factor_data[factor]["correct_sum"]
            
            if total > 0:
                scores[factor] = correct / total
            else:
                scores[factor] = 0.5  # Default neutral score
        
        return scores
    
    def _scores_to_weights(self, scores: Dict[str, float]) -> Dict[str, float]:
        """
        Convert performance scores to weights.
        
        Higher performing factors get higher weights.
        Applies min/max limits.
        """
        # Normalize scores to sum to 1
        total_score = sum(scores.values())
        
        if total_score == 0:
            return DEFAULT_WEIGHTS.copy()
        
        weights = {}
        for factor, score in scores.items():
            raw_weight = score / total_score
            
            # Apply limits
            clamped_weight = max(MIN_WEIGHT, min(MAX_WEIGHT, raw_weight))
            weights[factor] = round(clamped_weight, 4)
        
        # Re-normalize after clamping
        total = sum(weights.values())
        weights = {k: round(v / total, 4) for k, v in weights.items()}
        
        return weights
    
    def _load_weights_from_db(self) -> Optional[Dict]:
        """Load weights from database."""
        if self.db is None:
            return None
        
        try:
            doc = self.db.prediction_weights.find_one({"_id": "default"})
            if doc and "weights" in doc:
                return doc["weights"]
            return None
        except Exception:
            return None
    
    def _save_weights(
        self, 
        weights: Dict, 
        scores: Dict, 
        sample_size: int
    ):
        """Save calibrated weights to database."""
        if self.db is None:
            return
        
        try:
            doc = {
                "weights": weights,
                "performance_scores": scores,
                "sample_size": sample_size,
                "last_calibration": datetime.now(timezone.utc).isoformat(),
                "last_calibration_ts": int(time.time()),
            }
            
            self.db.prediction_weights.update_one(
                {"_id": "default"},
                {"$set": doc},
                upsert=True
            )
        except Exception as e:
            print(f"[Calibration] Failed to save weights: {e}")
    
    def get_calibration_status(self) -> Dict:
        """Get current calibration status and info."""
        if self.db is None:
            return {
                "status": "no_database",
                "weights": DEFAULT_WEIGHTS,
                "using_defaults": True,
            }
        
        try:
            doc = self.db.prediction_weights.find_one({"_id": "default"})
            
            if not doc:
                return {
                    "status": "not_calibrated",
                    "weights": DEFAULT_WEIGHTS,
                    "using_defaults": True,
                }
            
            return {
                "status": "calibrated",
                "weights": doc.get("weights", DEFAULT_WEIGHTS),
                "performance_scores": doc.get("performance_scores", {}),
                "sample_size": doc.get("sample_size", 0),
                "last_calibration": doc.get("last_calibration"),
                "using_defaults": False,
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "weights": DEFAULT_WEIGHTS,
                "using_defaults": True,
            }
    
    def reset_calibration(self) -> bool:
        """Reset to default weights."""
        if self.db is None:
            return False
        
        try:
            self.db.prediction_weights.delete_one({"_id": "default"})
            self._cached_weights = None
            return True
        except Exception:
            return False


# Singleton
_calibration_engine: Optional[CalibrationEngine] = None


def get_calibration_engine() -> CalibrationEngine:
    """Get singleton calibration engine."""
    global _calibration_engine
    if _calibration_engine is None:
        _calibration_engine = CalibrationEngine()
    return _calibration_engine


def get_calibrated_weights() -> Dict:
    """Convenience function to get current weights."""
    return get_calibration_engine().get_weights()


def run_calibration(predictions: List[Dict]) -> Optional[Dict]:
    """Convenience function to run calibration."""
    return get_calibration_engine().calibrate(predictions)
