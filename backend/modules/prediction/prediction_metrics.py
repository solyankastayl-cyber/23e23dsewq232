"""
Prediction Metrics

Computes accuracy and performance metrics from evaluated predictions.
"""

from typing import Dict, List, Optional
from collections import defaultdict


class PredictionMetrics:
    """
    Computes prediction performance metrics.
    
    Metrics:
    - accuracy: % of correct predictions
    - partial_rate: % of partial correct
    - wrong_rate: % of wrong predictions
    - avg_error: average error %
    - direction_accuracy: % of correct direction
    - confidence_calibration: predicted vs actual confidence
    - bias_skew: bull vs bear accuracy
    """
    
    def compute(
        self, 
        predictions: List[Dict],
        symbol: Optional[str] = None
    ) -> Dict:
        """
        Compute metrics from list of resolved predictions.
        
        Args:
            predictions: List of prediction documents with evaluations
            symbol: Optional filter by symbol
        
        Returns:
            Metrics dictionary
        """
        # Filter by symbol if specified
        if symbol:
            predictions = [p for p in predictions if p.get("symbol") == symbol.upper()]
        
        # Filter only resolved
        resolved = [p for p in predictions if p.get("status") == "resolved"]
        
        if not resolved:
            return self._empty_metrics()
        
        total = len(resolved)
        
        # Count results
        results = defaultdict(int)
        for p in resolved:
            result = p.get("evaluation", {}).get("result", "unknown")
            results[result] += 1
        
        correct = results.get("correct", 0)
        partial = results.get("partial", 0)
        wrong = results.get("wrong", 0)
        
        # Calculate accuracy
        accuracy = correct / total if total > 0 else 0
        accuracy_with_partial = (correct + partial * 0.5) / total if total > 0 else 0
        
        # Calculate average error
        errors = [
            p.get("evaluation", {}).get("error_pct", 0) 
            for p in resolved 
            if p.get("evaluation", {}).get("error_pct") is not None
        ]
        avg_error = sum(errors) / len(errors) if errors else 0
        
        # Direction accuracy
        direction_correct = sum(
            1 for p in resolved 
            if p.get("evaluation", {}).get("direction_correct", False)
        )
        direction_accuracy = direction_correct / total if total > 0 else 0
        
        # Bias analysis
        bias = self._compute_bias(resolved)
        
        # Confidence calibration
        calibration = self._compute_calibration(resolved)
        
        # Contribution performance
        contribution_performance = self._compute_contribution_performance(resolved)
        
        return {
            "total_predictions": total,
            "results": {
                "correct": correct,
                "partial": partial,
                "wrong": wrong,
            },
            "accuracy": round(accuracy, 4),
            "accuracy_with_partial": round(accuracy_with_partial, 4),
            "direction_accuracy": round(direction_accuracy, 4),
            "avg_error_pct": round(avg_error, 4),
            "bias": bias,
            "calibration": calibration,
            "contribution_performance": contribution_performance,
        }
    
    def _compute_bias(self, predictions: List[Dict]) -> Dict:
        """Compute bull vs bear accuracy bias."""
        bullish = [p for p in predictions if p.get("prediction", {}).get("direction") == "bullish"]
        bearish = [p for p in predictions if p.get("prediction", {}).get("direction") == "bearish"]
        neutral = [p for p in predictions if p.get("prediction", {}).get("direction") == "neutral"]
        
        def accuracy_for(preds):
            if not preds:
                return 0
            correct = sum(1 for p in preds if p.get("evaluation", {}).get("result") == "correct")
            return correct / len(preds)
        
        bull_acc = accuracy_for(bullish)
        bear_acc = accuracy_for(bearish)
        
        # Skew: positive = bullish bias working better
        skew = bull_acc - bear_acc if bullish and bearish else 0
        
        return {
            "bullish_predictions": len(bullish),
            "bearish_predictions": len(bearish),
            "neutral_predictions": len(neutral),
            "bullish_accuracy": round(bull_acc, 4),
            "bearish_accuracy": round(bear_acc, 4),
            "skew": round(skew, 4),  # positive = bullish works better
        }
    
    def _compute_calibration(self, predictions: List[Dict]) -> Dict:
        """
        Compute confidence calibration.
        
        Good calibration: 70% confidence predictions are correct 70% of the time.
        """
        # Group by confidence buckets
        buckets = {
            "high": {"preds": [], "threshold": 0.7},
            "medium": {"preds": [], "threshold": 0.5},
            "low": {"preds": [], "threshold": 0.0},
        }
        
        for p in predictions:
            conf = p.get("prediction", {}).get("confidence", 0)
            conf_label = p.get("prediction", {}).get("confidence_label", "LOW").lower()
            
            if conf_label in buckets:
                buckets[conf_label]["preds"].append(p)
        
        calibration = {}
        for label, data in buckets.items():
            preds = data["preds"]
            if not preds:
                calibration[label] = {
                    "count": 0,
                    "expected_accuracy": data["threshold"],
                    "actual_accuracy": 0,
                    "calibration_error": 0,
                }
                continue
            
            correct = sum(1 for p in preds if p.get("evaluation", {}).get("result") == "correct")
            actual_acc = correct / len(preds)
            
            # Calculate average confidence in this bucket
            avg_conf = sum(p.get("prediction", {}).get("confidence", 0) for p in preds) / len(preds)
            
            calibration[label] = {
                "count": len(preds),
                "expected_accuracy": round(avg_conf, 4),
                "actual_accuracy": round(actual_acc, 4),
                "calibration_error": round(abs(avg_conf - actual_acc), 4),
            }
        
        return calibration
    
    def _compute_contribution_performance(self, predictions: List[Dict]) -> Dict:
        """
        Compute performance of each contribution factor.
        
        Used for weight calibration.
        """
        factors = ["pattern", "structure", "momentum"]
        performance = {f: {"total_weight": 0, "correct_weight": 0} for f in factors}
        
        for p in predictions:
            contributions = p.get("contributions", {})
            is_correct = p.get("evaluation", {}).get("result") == "correct"
            
            for factor in factors:
                weight = abs(contributions.get(factor, 0))
                performance[factor]["total_weight"] += weight
                if is_correct:
                    performance[factor]["correct_weight"] += weight
        
        # Calculate performance ratio
        result = {}
        for factor in factors:
            total = performance[factor]["total_weight"]
            correct = performance[factor]["correct_weight"]
            
            result[factor] = {
                "contribution_ratio": round(correct / total, 4) if total > 0 else 0.5,
                "total_contribution": round(total, 4),
            }
        
        return result
    
    def _empty_metrics(self) -> Dict:
        """Return empty metrics structure."""
        return {
            "total_predictions": 0,
            "results": {"correct": 0, "partial": 0, "wrong": 0},
            "accuracy": 0,
            "accuracy_with_partial": 0,
            "direction_accuracy": 0,
            "avg_error_pct": 0,
            "bias": {
                "bullish_predictions": 0,
                "bearish_predictions": 0,
                "neutral_predictions": 0,
                "bullish_accuracy": 0,
                "bearish_accuracy": 0,
                "skew": 0,
            },
            "calibration": {},
            "contribution_performance": {},
        }


# Singleton
_metrics: Optional[PredictionMetrics] = None


def get_prediction_metrics() -> PredictionMetrics:
    """Get singleton metrics instance."""
    global _metrics
    if _metrics is None:
        _metrics = PredictionMetrics()
    return _metrics


def compute_prediction_metrics(predictions: List[Dict], symbol: Optional[str] = None) -> Dict:
    """Convenience function to compute metrics."""
    return get_prediction_metrics().compute(predictions, symbol)
