"""
Prediction Ranking

Score and filter predictions to surface best opportunities.
Without this, you drown in prediction spam.
"""

from typing import Dict
from .types import MIN_CONFIDENCE_FOR_PUBLISH, MIN_EXPECTED_RETURN_FOR_PUBLISH


class PredictionRanking:
    """
    Ranks and filters predictions.
    
    Score formula:
        score = confidence * 0.5 
              + |expected_return| * 2.5 
              + |direction_score| * 0.2
    
    Publishability filters:
        - confidence >= 0.55
        - |expected_return| >= 0.02 (2%)
    """
    
    @staticmethod
    def compute_score(prediction_payload: Dict) -> float:
        """
        Compute prediction score.
        
        Higher score = more interesting signal.
        
        Args:
            prediction_payload: Prediction output dict
        
        Returns:
            Score (0 to ~3)
        """
        try:
            # Handle nested structures
            confidence = prediction_payload.get("confidence", {})
            if isinstance(confidence, dict):
                confidence_val = float(confidence.get("value", 0))
            else:
                confidence_val = float(confidence)
            
            # Get expected return from base scenario
            scenarios = prediction_payload.get("scenarios", {})
            base_scenario = scenarios.get("base", {})
            expected_return = abs(float(base_scenario.get("expected_return", 0)))
            
            # Direction score
            direction = prediction_payload.get("direction", {})
            if isinstance(direction, dict):
                direction_score = abs(float(direction.get("score", 0)))
            else:
                direction_score = 0
            
            # Score formula
            score = (
                confidence_val * 0.5 +
                expected_return * 2.5 +
                direction_score * 0.2
            )
            
            return round(score, 4)
        
        except Exception:
            return 0.0
    
    @staticmethod
    def is_publishable(prediction_payload: Dict) -> bool:
        """
        Check if prediction meets publishability criteria.
        
        Filters out low-quality predictions.
        
        Args:
            prediction_payload: Prediction output dict
        
        Returns:
            True if publishable
        """
        try:
            # Get confidence
            confidence = prediction_payload.get("confidence", {})
            if isinstance(confidence, dict):
                confidence_val = float(confidence.get("value", 0))
            else:
                confidence_val = float(confidence)
            
            # Get expected return
            scenarios = prediction_payload.get("scenarios", {})
            base_scenario = scenarios.get("base", {})
            expected_return = abs(float(base_scenario.get("expected_return", 0)))
            
            # Check thresholds
            if confidence_val < MIN_CONFIDENCE_FOR_PUBLISH:
                return False
            
            if expected_return < MIN_EXPECTED_RETURN_FOR_PUBLISH:
                return False
            
            return True
        
        except Exception:
            return False


def compute_prediction_score(prediction_payload: Dict) -> float:
    """Convenience function to compute score."""
    return PredictionRanking.compute_score(prediction_payload)


def is_prediction_publishable(prediction_payload: Dict) -> bool:
    """Convenience function to check publishability."""
    return PredictionRanking.is_publishable(prediction_payload)


def enrich_prediction_with_score(prediction_payload: Dict) -> Dict:
    """
    Add score and publishable fields to prediction.
    
    Call this before saving prediction snapshots.
    
    Args:
        prediction_payload: Prediction output dict
    
    Returns:
        Enriched prediction with score and publishable fields
    """
    prediction_payload["score"] = compute_prediction_score(prediction_payload)
    prediction_payload["publishable"] = is_prediction_publishable(prediction_payload)
    return prediction_payload
