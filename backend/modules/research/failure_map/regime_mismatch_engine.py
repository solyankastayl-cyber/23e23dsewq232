"""
Regime Mismatch Engine
======================

Detects regime mismatches (PHASE 2.2)
"""

import time
import random
import uuid
from typing import Dict, List, Optional, Any

from .failure_types import RegimeMismatch, FailureSeverity


class RegimeMismatchEngine:
    """
    Detects when strategy is executed in wrong regime.
    
    Example: Mean Reversion in Trending market
    """
    
    def __init__(self):
        # Strategy ideal regimes (from Trading Doctrine)
        self._strategy_regimes = {
            "TREND_CONFIRMATION": {
                "ideal": ["TRENDING"],
                "acceptable": ["TRANSITION"],
                "avoid": ["RANGE", "HIGH_VOLATILITY"]
            },
            "MOMENTUM_BREAKOUT": {
                "ideal": ["TRENDING", "HIGH_VOLATILITY"],
                "acceptable": ["TRANSITION"],
                "avoid": ["RANGE", "LOW_VOLATILITY"]
            },
            "MEAN_REVERSION": {
                "ideal": ["RANGE", "LOW_VOLATILITY"],
                "acceptable": ["TRANSITION"],
                "avoid": ["TRENDING", "HIGH_VOLATILITY"]
            }
        }
        
        # Expected performance by regime match
        self._performance_modifiers = {
            "ideal": 1.5,      # 50% better
            "acceptable": 1.0, # Normal
            "avoid": 0.5       # 50% worse
        }
        
        print("[RegimeMismatchEngine] Initialized (PHASE 2.2)")
    
    def detect(
        self,
        trade_id: str,
        strategy: str,
        symbol: str,
        timeframe: str,
        actual_regime: str,
        trade_result: float,
        regime_confidence: float = 0.8
    ) -> Optional[RegimeMismatch]:
        """
        Detect if trade was in wrong regime.
        """
        
        strategy_upper = strategy.upper()
        regime_upper = actual_regime.upper()
        
        config = self._strategy_regimes.get(strategy_upper)
        if not config:
            return None
        
        # Determine regime match level
        match_level = "unknown"
        if regime_upper in config["ideal"]:
            match_level = "ideal"
        elif regime_upper in config["acceptable"]:
            match_level = "acceptable"
        elif regime_upper in config["avoid"]:
            match_level = "avoid"
        
        # Only flag mismatches for "avoid" regimes
        if match_level != "avoid":
            return None
        
        # Calculate expected result in ideal regime
        expected_result = trade_result / self._performance_modifiers["avoid"] * self._performance_modifiers["ideal"]
        
        # Determine severity
        result_delta = expected_result - trade_result
        
        if trade_result < -1.0 and result_delta > 1.0:
            severity = FailureSeverity.CRITICAL
        elif trade_result < 0 and result_delta > 0.5:
            severity = FailureSeverity.HIGH
        elif result_delta > 0.3:
            severity = FailureSeverity.MEDIUM
        else:
            severity = FailureSeverity.LOW
        
        # Determine market behavior description
        behavior_map = {
            "TRENDING": "Strong directional movement",
            "RANGE": "Price oscillating between levels",
            "HIGH_VOLATILITY": "Large price swings",
            "LOW_VOLATILITY": "Compressed price action",
            "TRANSITION": "Regime change in progress"
        }
        
        notes = [
            f"Strategy {strategy_upper} designed for {config['ideal']}, executed in {regime_upper}",
            f"Expected result in ideal regime: {expected_result:.2f}R"
        ]
        
        return RegimeMismatch(
            trade_id=trade_id,
            strategy=strategy_upper,
            symbol=symbol,
            timeframe=timeframe,
            expected_regime=config["ideal"][0],
            actual_regime=regime_upper,
            regime_confidence=regime_confidence,
            trade_result=trade_result,
            expected_result=expected_result,
            market_behavior=behavior_map.get(regime_upper, "Unknown"),
            severity=severity,
            notes=notes,
            detected_at=int(time.time() * 1000)
        )
    
    def scan_trades(
        self,
        trades: List[Dict[str, Any]]
    ) -> List[RegimeMismatch]:
        """Scan multiple trades for regime mismatches"""
        
        mismatches = []
        for trade in trades:
            mismatch = self.detect(
                trade_id=trade.get("trade_id", ""),
                strategy=trade.get("strategy", ""),
                symbol=trade.get("symbol", ""),
                timeframe=trade.get("timeframe", ""),
                actual_regime=trade.get("regime", ""),
                trade_result=trade.get("r_multiple", 0.0),
                regime_confidence=trade.get("regime_confidence", 0.8)
            )
            if mismatch:
                mismatches.append(mismatch)
        
        return mismatches
    
    def generate_simulated_mismatches(
        self,
        strategy: str,
        symbol: str,
        timeframe: str,
        count: int = 30
    ) -> List[RegimeMismatch]:
        """Generate simulated regime mismatches for testing"""
        
        strategy_upper = strategy.upper()
        config = self._strategy_regimes.get(strategy_upper, {
            "ideal": ["RANGE"],
            "avoid": ["TRENDING"]
        })
        
        mismatches = []
        
        for i in range(count):
            # Pick an "avoid" regime
            avoid_regime = random.choice(config.get("avoid", ["RANGE"]))
            
            # Generate trade result (typically worse in wrong regime)
            trade_result = random.uniform(-1.5, 0.5)
            
            mismatch = self.detect(
                trade_id=f"mismatch_{uuid.uuid4().hex[:8]}",
                strategy=strategy_upper,
                symbol=symbol,
                timeframe=timeframe,
                actual_regime=avoid_regime,
                trade_result=trade_result,
                regime_confidence=random.uniform(0.6, 0.95)
            )
            
            if mismatch:
                mismatches.append(mismatch)
        
        return mismatches
    
    def calculate_mismatch_rate(
        self,
        mismatches: List[RegimeMismatch],
        total_trades: int
    ) -> float:
        """Calculate regime mismatch rate"""
        if total_trades == 0:
            return 0.0
        return len(mismatches) / total_trades
    
    def get_regime_matrix(self, strategy: str) -> Dict[str, Any]:
        """Get regime compatibility for strategy"""
        config = self._strategy_regimes.get(strategy.upper(), {})
        return {
            "strategy": strategy.upper(),
            "ideal": config.get("ideal", []),
            "acceptable": config.get("acceptable", []),
            "avoid": config.get("avoid", [])
        }


# Global singleton
regime_mismatch_engine = RegimeMismatchEngine()
