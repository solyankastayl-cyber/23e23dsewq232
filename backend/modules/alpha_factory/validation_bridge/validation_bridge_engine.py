"""
Validation Bridge Engine - Main orchestrator for AF3
Combines Alpha Factory + V1 Validation for self-correcting verdicts and actions
"""
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

from .alpha_validation_models import CombinedAlphaTruth, AF3Action, ValidationBridgeSummary
from .validation_metrics_adapter import ValidationMetricsAdapter
from .alpha_validation_evaluator import AlphaValidationEvaluator


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class ValidationBridgeEngine:
    """
    Main engine that bridges Alpha Factory with V1 Validation Layer.
    
    Flow:
    1. Get Alpha metrics (historical truth from TT4)
    2. Get Validation metrics (live truth from V1)
    3. Evaluate combined verdict
    4. Generate actions based on verdicts
    5. Submit actions to TT5 Control Layer
    """
    
    # Action magnitudes
    INCREASE_MAG = 0.15
    REDUCE_MAG = 0.20
    DISABLE_MAG = 1.0
    
    def __init__(
        self, 
        alpha_query_service=None, 
        validation_adapter: Optional[ValidationMetricsAdapter] = None
    ):
        self.alpha_query_service = alpha_query_service
        self.validation_adapter = validation_adapter or ValidationMetricsAdapter()
        self.evaluator = AlphaValidationEvaluator()
    
    def evaluate_symbols(self) -> List[Dict[str, Any]]:
        """
        Evaluate all symbols with combined alpha + validation metrics.
        """
        truths = []
        
        # Get alpha metrics by symbol
        symbol_metrics = self._get_alpha_symbol_metrics()
        
        # If no alpha metrics, derive symbols from validation data
        if not symbol_metrics:
            symbol_metrics = self._derive_symbols_from_validation()
        
        for alpha_m in symbol_metrics:
            symbol = alpha_m.get("scope_key", alpha_m.get("symbol", "UNKNOWN"))
            
            # Get validation metrics for this symbol
            validation_m = self.validation_adapter.get_metrics(symbol=symbol)
            
            # Evaluate combined truth
            truth = self.evaluator.evaluate(
                scope="symbol",
                scope_key=symbol,
                alpha_metrics=alpha_m,
                validation_metrics=validation_m
            )
            
            truths.append(truth.to_dict())
        
        return truths
    
    def _derive_symbols_from_validation(self) -> List[Dict[str, Any]]:
        """
        If no alpha metrics exist, derive symbol list from validation data.
        Returns placeholder alpha metrics for each symbol found in validation.
        """
        by_symbol = self.validation_adapter.get_metrics_by_symbol()
        
        derived = []
        for symbol, metrics in by_symbol.items():
            # Create placeholder alpha metrics based on validation
            derived.append({
                "scope": "symbol",
                "scope_key": symbol,
                "symbol": symbol,
                "profit_factor": None,  # No historical data
                "win_rate": 0.0,
                "expectancy": 0.0,
                "trades": 0,
                "source": "derived_from_validation"
            })
        
        return derived
    
    def evaluate_entry_modes(self) -> List[Dict[str, Any]]:
        """
        Evaluate entry modes with combined truth.
        """
        truths = []
        
        # Get alpha metrics by entry mode
        mode_metrics = self._get_alpha_entry_mode_metrics()
        
        for alpha_m in mode_metrics:
            mode = alpha_m.get("scope_key", alpha_m.get("entry_mode", "UNKNOWN"))
            
            # Get validation metrics (global for now, could be per-mode)
            validation_m = self.validation_adapter.get_metrics()
            
            truth = self.evaluator.evaluate(
                scope="entry_mode",
                scope_key=mode,
                alpha_metrics=alpha_m,
                validation_metrics=validation_m
            )
            
            truths.append(truth.to_dict())
        
        return truths
    
    def build_actions(self, truths: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Generate actions from combined truths.
        """
        actions = []
        
        for t in truths:
            verdict = t["combined_verdict"]
            scope = t["scope"]
            scope_key = t["scope_key"]
            confidence = t["confidence"]
            decay_severity = t.get("decay_severity", "none")
            
            action = self._verdict_to_action(
                verdict=verdict,
                scope=scope,
                scope_key=scope_key,
                confidence=confidence,
                decay_severity=decay_severity
            )
            
            if action:
                actions.append(action.to_dict())
        
        return actions
    
    def build_summary(self, truths: List[Dict[str, Any]], actions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Build summary of evaluation results.
        """
        verdicts = [t["combined_verdict"] for t in truths]
        
        strong_confirmed = sum(1 for v in verdicts if v == "STRONG_CONFIRMED_EDGE")
        strong_decaying = sum(1 for v in verdicts if v == "STRONG_BUT_DECAYING")
        weak = sum(1 for v in verdicts if v == "WEAK_EDGE")
        no_edge = sum(1 for v in verdicts if v == "NO_EDGE")
        
        high_priority = sum(1 for a in actions if a.get("urgent", False))
        
        # Determine health
        if no_edge > len(truths) * 0.5:
            health = "critical"
        elif strong_decaying > len(truths) * 0.3:
            health = "warning"
        else:
            health = "healthy"
        
        return ValidationBridgeSummary(
            total_symbols=len(truths),
            strong_confirmed=strong_confirmed,
            strong_decaying=strong_decaying,
            weak_edge=weak,
            no_edge=no_edge,
            actions_generated=len(actions),
            high_priority_actions=high_priority,
            overall_health=health
        ).to_dict()
    
    def run_full_evaluation(self) -> Dict[str, Any]:
        """
        Run complete evaluation and return all results.
        """
        # Evaluate symbols
        symbol_truths = self.evaluate_symbols()
        
        # Build actions
        actions = self.build_actions(symbol_truths)
        
        # Build summary
        summary = self.build_summary(symbol_truths, actions)
        
        return {
            "truths": symbol_truths,
            "actions": actions,
            "summary": summary,
            "timestamp": utc_now(),
        }
    
    def _verdict_to_action(
        self, 
        verdict: str, 
        scope: str, 
        scope_key: str,
        confidence: float,
        decay_severity: str
    ) -> Optional[AF3Action]:
        """
        Convert verdict to action.
        """
        if verdict == "STRONG_CONFIRMED_EDGE":
            return AF3Action(
                scope=scope,
                scope_key=scope_key,
                action="INCREASE_ALLOCATION",
                magnitude=self.INCREASE_MAG,
                reason="live_edge_confirmed",
                combined_verdict=verdict,
                confidence=confidence,
                urgent=False,
                requires_approval=False
            )
        
        elif verdict == "STRONG_BUT_DECAYING":
            urgent = decay_severity == "severe"
            return AF3Action(
                scope=scope,
                scope_key=scope_key,
                action="REDUCE_RISK",
                magnitude=self.REDUCE_MAG if decay_severity == "mild" else 0.30,
                reason="historical_edge_not_confirmed_live",
                combined_verdict=verdict,
                confidence=confidence,
                urgent=urgent,
                requires_approval=urgent
            )
        
        elif verdict == "NO_EDGE":
            return AF3Action(
                scope=scope,
                scope_key=scope_key,
                action="DISABLE_SYMBOL",
                magnitude=self.DISABLE_MAG,
                reason="no_live_or_historical_edge",
                combined_verdict=verdict,
                confidence=confidence,
                urgent=True,
                requires_approval=True
            )
        
        else:  # WEAK_EDGE
            return AF3Action(
                scope=scope,
                scope_key=scope_key,
                action="KEEP",
                magnitude=0.0,
                reason="edge_weak_continue_observing",
                combined_verdict=verdict,
                confidence=confidence,
                urgent=False,
                requires_approval=False
            )
    
    def _get_alpha_symbol_metrics(self) -> List[Dict[str, Any]]:
        """Get alpha metrics by symbol from query service"""
        if self.alpha_query_service:
            try:
                # Use get_metrics with scope="symbol"
                if hasattr(self.alpha_query_service, "get_metrics"):
                    metrics = self.alpha_query_service.get_metrics("symbol")
                    return metrics if isinstance(metrics, list) else []
            except Exception as e:
                print(f"[AF3] Error getting alpha symbol metrics: {e}")
        return []
    
    def _get_alpha_entry_mode_metrics(self) -> List[Dict[str, Any]]:
        """Get alpha metrics by entry mode"""
        if self.alpha_query_service:
            try:
                if hasattr(self.alpha_query_service, "get_metrics"):
                    metrics = self.alpha_query_service.get_metrics("entry_mode")
                    return metrics if isinstance(metrics, list) else []
            except Exception as e:
                print(f"[AF3] Error getting alpha entry mode metrics: {e}")
        return []
