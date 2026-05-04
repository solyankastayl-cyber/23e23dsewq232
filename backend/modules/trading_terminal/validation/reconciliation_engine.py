"""Reconciliation Engine - Runs full validation on terminal state"""

from typing import Dict, Any, List
import logging
from .data_validator import DataValidator
from .validation_types import ValidationResult, ValidationSeverity, AggregatedValidation

logger = logging.getLogger(__name__)


class ReconciliationEngine:
    """Runs full validation on terminal state"""

    def __init__(self):
        self.validator = DataValidator()
        self._price_cache: Dict[str, float] = {}

    async def get_live_price(self, symbol: str) -> float:
        """Get live price from Coinbase"""
        try:
            from modules.data.coinbase_auto_init import coinbase_auto_init
            asset = symbol.replace("USDT", "").upper()
            ticker = await coinbase_auto_init.get_live_ticker(asset)
            if ticker.get("ok") and ticker.get("ticker"):
                price = float(ticker["ticker"].get("price", 0))
                self._price_cache[symbol] = price
                return price
        except Exception as e:
            logger.warning(f"[Reconciliation] Failed to get live price: {e}")
        
        # Return cached price if available
        return self._price_cache.get(symbol, 0)

    def validate_terminal_state(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Run all validations and return aggregated result (sync version)"""
        market_price = self._extract_market_price(state)
        micro_source = state.get("micro", {}).get("source", "unknown")
        
        results: List[ValidationResult] = []
        
        # Core validations
        results.append(self.validator.validate_execution_vs_market(state.get("execution"), market_price))
        results.append(self.validator.validate_position_vs_symbol(state.get("position"), state.get("symbol", "")))
        results.append(self.validator.validate_micro_source(state.get("micro")))
        results.append(self.validator.validate_decision_confidence(state.get("decision"), micro_source))
        results.append(self.validator.validate_execution_levels(state.get("execution")))
        results.append(self.validator.validate_timeframe_consistency(state))
        
        return self._aggregate(results)

    async def validate_terminal_state_async(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Run all validations with live price check (async version)"""
        symbol = state.get("symbol", "BTCUSDT")
        timeframe = state.get("timeframe", "4H")
        
        # Get live market price
        live_price = await self.get_live_price(symbol)
        
        # Use live price if available, otherwise fall back to micro
        market_price = live_price if live_price > 0 else self._extract_market_price(state)
        
        micro_source = state.get("micro", {}).get("source", "unknown")
        
        results: List[ValidationResult] = []
        
        # Core validations with live price
        results.append(self.validator.validate_execution_vs_market(state.get("execution"), market_price))
        results.append(self.validator.validate_position_vs_symbol(state.get("position"), state.get("symbol", "")))
        results.append(self.validator.validate_micro_source(state.get("micro")))
        results.append(self.validator.validate_decision_confidence(state.get("decision"), micro_source))
        results.append(self.validator.validate_execution_levels(state.get("execution")))
        results.append(self.validator.validate_timeframe_consistency(state))
        
        # Add live price info and timeframe
        agg = self._aggregate(results)
        agg["live_price"] = live_price
        agg["price_source"] = "coinbase" if live_price > 0 else "mock"
        agg["timeframe"] = timeframe
        
        return agg

    def _extract_market_price(self, state: Dict[str, Any]) -> float:
        """Extract market price from micro or execution"""
        micro = state.get("micro", {})
        execution = state.get("execution", {})
        
        # Try mid_price from micro first
        if micro.get("mid_price"):
            return micro["mid_price"]
        
        # Fallback to best_bid/ask average
        if micro.get("best_bid") and micro.get("best_ask"):
            return (micro["best_bid"] + micro["best_ask"]) / 2
        
        # Last resort: entry price
        return execution.get("entry", 0)

    def _aggregate(self, results: List[ValidationResult]) -> Dict[str, Any]:
        """Aggregate validation results"""
        issues = [r.to_dict() for r in results]
        
        critical = [r for r in results if not r.valid and r.severity == ValidationSeverity.CRITICAL]
        warnings = [r for r in results if r.severity == ValidationSeverity.WARNING]
        infos = [r for r in results if r.severity == ValidationSeverity.INFO]
        
        return AggregatedValidation(
            is_valid=len(critical) == 0,
            critical_count=len(critical),
            warning_count=len(warnings),
            info_count=len(infos),
            issues=issues
        ).to_dict()


# Singleton instance
_reconciliation_engine = None

def get_reconciliation_engine() -> ReconciliationEngine:
    global _reconciliation_engine
    if _reconciliation_engine is None:
        _reconciliation_engine = ReconciliationEngine()
    return _reconciliation_engine
