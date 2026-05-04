"""
Prediction Repository

Saves and retrieves predictions from MongoDB for validation.
"""

import time
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone
from bson import ObjectId


class PredictionRepository:
    """
    MongoDB repository for predictions.
    
    Collections:
    - predictions: stored predictions with evaluations
    - prediction_weights: calibrated weights
    """
    
    def __init__(self, db=None):
        self.db = db
        self._ensure_db()
    
    def _ensure_db(self):
        """Ensure database connection."""
        if self.db is None:
            try:
                from core.database import get_database
                self.db = get_database()
            except Exception:
                self.db = None
    
    def save_prediction(self, payload: Dict) -> Optional[str]:
        """
        Save a prediction for later evaluation.
        
        Args:
            payload: Prediction output from engine
        
        Returns:
            Inserted document ID or None if failed
        """
        if self.db is None:
            return None
        
        try:
            # Extract base scenario for target
            base_scenario = payload.get("scenarios", {}).get("base", {})
            
            doc = {
                "symbol": payload.get("symbol", "UNKNOWN"),
                "timeframe": payload.get("timeframe", "1D"),
                "created_at": int(time.time()),
                "created_at_iso": datetime.now(timezone.utc).isoformat(),
                
                "price_at_prediction": payload.get("current_price", 0),
                
                "prediction": {
                    "direction": payload.get("direction", {}).get("label", "neutral"),
                    "direction_score": payload.get("direction", {}).get("score", 0),
                    "target_price": base_scenario.get("target_price", 0),
                    "expected_return": base_scenario.get("expected_return", 0),
                    "confidence": payload.get("confidence", {}).get("value", 0),
                    "confidence_label": payload.get("confidence", {}).get("label", "LOW"),
                    "horizon_days": payload.get("horizon_days", 5),
                },
                
                # Store contributions for calibration
                "contributions": payload.get("direction", {}).get("contributions", {}),
                
                # Store all scenarios
                "scenarios": {
                    name: {
                        "probability": s.get("probability", 0),
                        "target_price": s.get("target_price", 0),
                        "expected_return": s.get("expected_return", 0),
                    }
                    for name, s in payload.get("scenarios", {}).items()
                },
                
                # Status tracking
                "status": "pending",  # pending | resolved | expired
                
                # Evaluation (filled later)
                "evaluation": {
                    "result": None,  # correct | wrong | partial
                    "real_price": None,
                    "error_pct": None,
                    "direction_correct": None,
                    "evaluated_at": None,
                },
                
                # Metadata
                "version": payload.get("version", "v2"),
            }
            
            result = self.db.predictions.insert_one(doc)
            return str(result.inserted_id)
        
        except Exception as e:
            print(f"[PredictionRepo] Save error: {e}")
            return None
    
    def get_pending_predictions(self, limit: int = 100) -> List[Dict]:
        """Get predictions awaiting evaluation."""
        if self.db is None:
            return []
        
        try:
            cursor = self.db.predictions.find(
                {"status": "pending"},
                {"_id": 1, "symbol": 1, "timeframe": 1, "created_at": 1, 
                 "price_at_prediction": 1, "prediction": 1, "contributions": 1}
            ).sort("created_at", 1).limit(limit)
            
            return list(cursor)
        except Exception:
            return []
    
    def get_resolved_predictions(
        self, 
        symbol: Optional[str] = None,
        limit: int = 500
    ) -> List[Dict]:
        """Get evaluated predictions for metrics."""
        if self.db is None:
            return []
        
        try:
            query = {"status": "resolved"}
            if symbol:
                query["symbol"] = symbol.upper()
            
            cursor = self.db.predictions.find(
                query,
                {"_id": 0}
            ).sort("created_at", -1).limit(limit)
            
            return list(cursor)
        except Exception:
            return []
    
    def update_evaluation(
        self, 
        prediction_id: str, 
        evaluation: Dict
    ) -> bool:
        """Update prediction with evaluation result."""
        if self.db is None:
            return False
        
        try:
            result = self.db.predictions.update_one(
                {"_id": ObjectId(prediction_id)},
                {
                    "$set": {
                        "status": "resolved",
                        "evaluation": evaluation,
                    }
                }
            )
            return result.modified_count > 0
        except Exception as e:
            print(f"[PredictionRepo] Update error: {e}")
            return False
    
    def mark_expired(self, prediction_id: str) -> bool:
        """Mark prediction as expired (no price data available)."""
        if self.db is None:
            return False
        
        try:
            result = self.db.predictions.update_one(
                {"_id": ObjectId(prediction_id)},
                {
                    "$set": {
                        "status": "expired",
                        "evaluation.result": "expired",
                        "evaluation.evaluated_at": datetime.now(timezone.utc).isoformat(),
                    }
                }
            )
            return result.modified_count > 0
        except Exception:
            return False
    
    def get_prediction_by_id(self, prediction_id: str) -> Optional[Dict]:
        """Get single prediction by ID."""
        if self.db is None:
            return None
        
        try:
            doc = self.db.predictions.find_one(
                {"_id": ObjectId(prediction_id)},
                {"_id": 0}
            )
            return doc
        except Exception:
            return None
    
    def count_predictions(self, status: Optional[str] = None) -> Dict[str, int]:
        """Count predictions by status."""
        if self.db is None:
            return {"total": 0, "pending": 0, "resolved": 0, "expired": 0}
        
        try:
            pipeline = [
                {"$group": {"_id": "$status", "count": {"$sum": 1}}}
            ]
            
            results = list(self.db.predictions.aggregate(pipeline))
            
            counts = {"total": 0, "pending": 0, "resolved": 0, "expired": 0}
            for r in results:
                status_key = r["_id"] or "unknown"
                counts[status_key] = r["count"]
                counts["total"] += r["count"]
            
            return counts
        except Exception:
            return {"total": 0, "pending": 0, "resolved": 0, "expired": 0}


# Singleton
_repo: Optional[PredictionRepository] = None


def get_prediction_repository() -> PredictionRepository:
    """Get singleton repository instance."""
    global _repo
    if _repo is None:
        _repo = PredictionRepository()
    return _repo
