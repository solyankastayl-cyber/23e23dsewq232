"""
PHASE 4.1 — Wrong Early Engine

Main orchestrator for wrong early diagnosis.
Coordinates classifier, repository, and aggregator.
"""

from typing import Dict, List, Optional
from datetime import datetime, timezone

from .wrong_early_classifier import WrongEarlyClassifier
from .wrong_early_repository import WrongEarlyRepository
from .wrong_early_aggregator import WrongEarlyAggregator
from .wrong_early_taxonomy import WRONG_EARLY_REASONS, REASON_DESCRIPTIONS


class WrongEarlyEngine:
    """
    Main engine for wrong early diagnosis.
    
    Usage:
        engine = WrongEarlyEngine()
        result = engine.analyze(trade_data)
        summary = engine.get_summary()
    """
    
    def __init__(self):
        self.classifier = WrongEarlyClassifier()
        self.repository = WrongEarlyRepository()
        self.aggregator = WrongEarlyAggregator()
    
    def analyze(self, data: Dict) -> Dict:
        """
        Analyze a single trade for wrong early classification.
        
        Args:
            data: Trade data including prediction, setup, execution_result, context
        
        Returns:
            Classification result
        """
        # Check if this is a wrong early case
        execution_result = data.get("execution_result", {})
        
        if not execution_result.get("wrong_early", False):
            return {
                "wrong_early": False,
                "reason": None,
                "message": "Trade was not marked as wrong_early"
            }
        
        # Classify the reason
        result = self.classifier.classify(data)
        
        # Add PnL from execution result
        result["pnl"] = execution_result.get("pnl", 0)
        result["trade_timestamp"] = data.get("timestamp")
        
        # Store in repository
        self.repository.save(result)
        
        return result
    
    def analyze_batch(self, data_list: List[Dict]) -> List[Dict]:
        """Analyze multiple trades."""
        return [self.analyze(data) for data in data_list]
    
    def get_summary(self, limit: int = 500) -> Dict:
        """
        Get summary of all recorded wrong early cases.
        
        Args:
            limit: Max records to include in analysis
        
        Returns:
            Comprehensive summary
        """
        records = self.repository.list_all(limit)
        summary = self.aggregator.summarize(records)
        
        # Add metadata
        summary["analysis_timestamp"] = datetime.now(timezone.utc).isoformat()
        summary["records_analyzed"] = len(records)
        summary["unknown_rate"] = self.aggregator.get_unknown_rate(records)
        
        return summary
    
    def get_records(self, limit: int = 100) -> List[Dict]:
        """Get raw records."""
        return self.repository.list_all(limit)
    
    def get_records_by_reason(self, reason: str, limit: int = 50) -> List[Dict]:
        """Get records filtered by reason."""
        return self.repository.find_by_reason(reason, limit)
    
    def get_records_by_symbol(self, symbol: str, limit: int = 50) -> List[Dict]:
        """Get records filtered by symbol."""
        return self.repository.find_by_symbol(symbol, limit)
    
    def get_reason_details(self, reason: str) -> Dict:
        """Get detailed analysis for a specific reason."""
        records = self.repository.list_all(500)
        return self.aggregator.get_reason_details(records, reason)
    
    def get_summary_by_symbol(self) -> Dict[str, Dict]:
        """Get summary broken down by symbol."""
        records = self.repository.list_all(500)
        return self.aggregator.summarize_by_symbol(records)
    
    def get_summary_by_timeframe(self) -> Dict[str, Dict]:
        """Get summary broken down by timeframe."""
        records = self.repository.list_all(500)
        return self.aggregator.summarize_by_timeframe(records)
    
    def get_taxonomy(self) -> Dict:
        """Get the full wrong early taxonomy."""
        return {
            "reasons": WRONG_EARLY_REASONS,
            "descriptions": REASON_DESCRIPTIONS,
            "count": len(WRONG_EARLY_REASONS)
        }
    
    def health_check(self) -> Dict:
        """Health check for the engine."""
        total_records = self.repository.get_total_count()
        
        return {
            "ok": True,
            "module": "wrong_early_diagnostic",
            "version": "4.1",
            "total_records": total_records,
            "taxonomy_count": len(WRONG_EARLY_REASONS),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    
    def simulate_analysis(self, count: int = 50) -> Dict:
        """
        Generate and analyze simulated wrong early trades for testing.
        
        This creates mock data to demonstrate the diagnostic engine.
        """
        import random
        
        symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "AVAXUSDT", "LINKUSDT"]
        timeframes = ["4H", "1H", "1D"]
        directions = ["LONG", "SHORT"]
        execution_types = ["BREAKOUT", "REVERSAL", "CONTINUATION", "MEAN_REVERSION"]
        
        simulated_results = []
        
        for i in range(count):
            # Generate random context that will trigger different reasons
            reason_scenario = random.choice([
                "breakout_fail", "extension", "reversal", "ltf_conflict", 
                "retest", "volatility", "structure", "unknown"
            ])
            
            # Build context based on scenario
            ctx = self._build_scenario_context(reason_scenario)
            
            data = {
                "symbol": random.choice(symbols),
                "timeframe": random.choice(timeframes),
                "prediction": {
                    "direction": random.choice(directions),
                    "confidence": random.uniform(0.6, 0.9),
                    "tradeable": True
                },
                "setup": {
                    "entry": 62000 + random.uniform(-500, 500),
                    "stop_loss": 61000 + random.uniform(-200, 200),
                    "target": 64000 + random.uniform(-300, 300),
                    "execution_type": random.choice(execution_types)
                },
                "execution_result": {
                    "filled": True,
                    "entry_price": 62000 + random.uniform(-100, 100),
                    "outcome": "SL",
                    "pnl": random.uniform(-0.03, -0.005),
                    "wrong_early": True
                },
                "context": ctx
            }
            
            result = self.analyze(data)
            simulated_results.append(result)
        
        return {
            "simulated_count": count,
            "results": simulated_results[-10:],  # Last 10 for display
            "summary": self.get_summary()
        }
    
    def _build_scenario_context(self, scenario: str) -> Dict:
        """Build context dict for a given scenario."""
        import random
        
        base = {
            "close_above_trigger": True,
            "close_below_trigger": True,
            "retest_completed": True,
            "extension_at_entry_atr": random.uniform(0.3, 1.0),
            "ltf_alignment": "aligned",
            "volatility_state": "normal",
            "volatility_value": random.uniform(0.3, 0.6),
            "structure_acceptance": True,
            "exhaustion_confirmed": True,
            "liquidity_sweep_resolved": True,
            "pullback_completed": True,
            "reset_completed": True
        }
        
        if scenario == "breakout_fail":
            base["close_above_trigger"] = False
            base["close_below_trigger"] = False
        elif scenario == "extension":
            base["extension_at_entry_atr"] = random.uniform(1.6, 2.5)
        elif scenario == "reversal":
            base["exhaustion_confirmed"] = False
            base["reversal_candidate"] = True
        elif scenario == "ltf_conflict":
            base["ltf_alignment"] = "conflict"
        elif scenario == "retest":
            base["retest_completed"] = False
        elif scenario == "volatility":
            base["volatility_state"] = random.choice(["high", "extreme"])
            base["volatility_value"] = random.uniform(0.9, 1.5)
        elif scenario == "structure":
            base["structure_acceptance"] = False
        
        return base


# Singleton instance
_engine: Optional[WrongEarlyEngine] = None


def get_wrong_early_engine() -> WrongEarlyEngine:
    """Get singleton engine instance."""
    global _engine
    if _engine is None:
        _engine = WrongEarlyEngine()
    return _engine
