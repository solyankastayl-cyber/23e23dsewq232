"""
Validation Metrics Adapter - Bridge to V1 Validation Layer
"""
from typing import Dict, Any, Optional


class ValidationMetricsAdapter:
    """
    Adapter that connects to V1 Validation Engine to get live/shadow metrics.
    """
    
    def __init__(self, validation_engine=None):
        self.validation_engine = validation_engine
    
    def get_metrics(self, symbol: Optional[str] = None) -> Dict[str, Any]:
        """Get validation metrics for symbol or all"""
        if self.validation_engine and hasattr(self.validation_engine, "build_metrics"):
            return self.validation_engine.build_metrics(symbol=symbol)
        
        # Return empty metrics if no engine available
        return self._empty_metrics()
    
    def get_metrics_by_symbol(self) -> Dict[str, Dict[str, Any]]:
        """Get metrics breakdown by symbol"""
        if self.validation_engine and hasattr(self.validation_engine, "build_symbol_breakdown"):
            return self.validation_engine.build_symbol_breakdown()
        return {}
    
    def get_stats(self) -> Dict[str, Any]:
        """Get validation stats"""
        if self.validation_engine and hasattr(self.validation_engine, "get_stats"):
            return self.validation_engine.get_stats()
        return {
            "total_shadow_trades": 0,
            "total_validation_results": 0,
        }
    
    def has_sufficient_data(self, symbol: Optional[str] = None, min_trades: int = 5) -> bool:
        """Check if we have enough validation data for reliable verdicts"""
        metrics = self.get_metrics(symbol=symbol)
        return metrics.get("trades", 0) >= min_trades
    
    def _empty_metrics(self) -> Dict[str, Any]:
        return {
            "trades": 0,
            "completed_trades": 0,
            "win_rate": 0.0,
            "profit_factor": None,
            "expectancy": 0.0,
            "stop_rate": 0.0,
            "target_rate": 0.0,
            "expired_rate": 0.0,
            "missed_rate": 0.0,
            "wrong_early_rate": 0.0,
            "avg_drift_bps": 0.0,
            "long_win_rate": 0.0,
            "short_win_rate": 0.0,
        }
