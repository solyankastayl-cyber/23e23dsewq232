"""
Validation Engine - Main orchestrator for live validation
"""
from typing import List, Dict, Optional

from .shadow_trade_repository import ShadowTradeRepository
from .shadow_trading_engine import ShadowTradingEngine
from .expected_vs_actual_engine import ExpectedVsActualEngine
from .validation_metrics_engine import ValidationMetricsEngine


class ValidationEngine:
    """
    Main validation engine that orchestrates:
    - Shadow trade creation
    - Expected vs actual evaluation
    - Metrics computation
    """
    
    def __init__(self, repo: Optional[ShadowTradeRepository] = None):
        self.repo = repo or ShadowTradeRepository()
        self.shadow_engine = ShadowTradingEngine(self.repo)
        self.expected_vs_actual = ExpectedVsActualEngine()
        self.metrics_engine = ValidationMetricsEngine()
    
    # =========== Shadow Trade Operations ===========
    
    def create_shadow_trade(self, terminal_state: dict) -> dict:
        """Create a shadow trade from terminal state"""
        return self.shadow_engine.create_from_terminal_state(terminal_state)
    
    def create_shadow_trade_manual(
        self,
        symbol: str,
        direction: str,
        planned_entry: float,
        planned_stop: float,
        planned_target: float,
        timeframe: str = "4H",
        entry_mode: str = "ENTER_ON_CLOSE",
        decision_action: str = "GO_FULL"
    ) -> dict:
        """Create a shadow trade manually"""
        return self.shadow_engine.create_manual(
            symbol=symbol,
            direction=direction,
            planned_entry=planned_entry,
            planned_stop=planned_stop,
            planned_target=planned_target,
            timeframe=timeframe,
            entry_mode=entry_mode,
            decision_action=decision_action
        )
    
    def get_shadow_trade(self, shadow_id: str) -> Optional[dict]:
        """Get a shadow trade by ID"""
        return self.repo.get_shadow_trade(shadow_id)
    
    def list_shadow_trades(
        self, 
        symbol: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 50
    ) -> List[dict]:
        """List shadow trades"""
        return self.repo.list_shadow_trades(symbol=symbol, status=status, limit=limit)
    
    def cancel_shadow_trade(self, shadow_id: str) -> Optional[dict]:
        """Cancel a shadow trade"""
        return self.shadow_engine.cancel(shadow_id)
    
    # =========== Validation Operations ===========
    
    def validate_shadow_trade(self, shadow_id: str, market_path: List[dict]) -> dict:
        """
        Validate a shadow trade against market path.
        
        market_path should be a list of candle dicts with:
        timestamp, open, high, low, close
        """
        shadow = self.repo.get_shadow_trade(shadow_id)
        if not shadow:
            raise ValueError(f"Shadow trade not found: {shadow_id}")
        
        result = self.expected_vs_actual.evaluate(shadow, market_path)
        
        # Save result
        self.repo.save_validation_result(result)
        
        # Update shadow trade status based on result
        status_map = {
            "WIN": "TARGET_HIT",
            "LOSS": "STOP_HIT",
            "EXPIRED": "EXPIRED",
            "OPEN": "ENTERED",
        }
        new_status = status_map.get(result["result"], shadow["status"])
        self.repo.update_shadow_trade_status(shadow_id, new_status)
        
        return result
    
    def validate_batch(
        self, 
        shadow_ids: List[str], 
        market_paths: Dict[str, List[dict]]
    ) -> List[dict]:
        """Validate multiple shadow trades"""
        results = []
        for shadow_id in shadow_ids:
            if shadow_id in market_paths:
                try:
                    result = self.validate_shadow_trade(shadow_id, market_paths[shadow_id])
                    results.append(result)
                except ValueError:
                    pass
        return results
    
    def get_validation_result(self, shadow_id: str) -> Optional[dict]:
        """Get validation result for a shadow trade"""
        return self.repo.get_validation_result(shadow_id)
    
    def list_validation_results(
        self,
        symbol: Optional[str] = None,
        result_type: Optional[str] = None,
        limit: int = 50
    ) -> List[dict]:
        """List validation results"""
        return self.repo.list_validation_results(
            symbol=symbol, 
            result_type=result_type, 
            limit=limit
        )
    
    # =========== Metrics Operations ===========
    
    def build_metrics(self, symbol: Optional[str] = None) -> dict:
        """Build aggregated validation metrics"""
        results = self.repo.list_validation_results(symbol=symbol, limit=1000)
        return self.metrics_engine.build_metrics(results, symbol=symbol)
    
    def build_symbol_breakdown(self) -> Dict[str, dict]:
        """Build metrics breakdown by symbol"""
        results = self.repo.list_validation_results(limit=1000)
        return self.metrics_engine.build_symbol_breakdown(results)
    
    # =========== Query Operations ===========
    
    def get_pending_trades(self) -> List[dict]:
        """Get all pending shadow trades"""
        return self.repo.get_pending_shadow_trades()
    
    def get_active_trades(self) -> List[dict]:
        """Get all active (entered) shadow trades"""
        return self.repo.get_entered_shadow_trades()
    
    def get_stats(self) -> dict:
        """Get repository and validation stats"""
        repo_stats = self.repo.get_stats()
        metrics = self.build_metrics()
        
        return {
            **repo_stats,
            "win_rate": metrics.get("win_rate", 0),
            "profit_factor": metrics.get("profit_factor"),
            "expectancy": metrics.get("expectancy", 0),
            "wrong_early_rate": metrics.get("wrong_early_rate", 0),
        }
    
    def reset(self):
        """Reset all validation data"""
        self.repo.clear_all()
