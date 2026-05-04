"""
PHASE 4.7.1 — HTF Analyzer

Main HTF analyzer that combines all HTF engines.
Provides directional permission layer for trading.
"""

from typing import Dict, Optional
from datetime import datetime, timezone

from .htf_structure_engine import HTFStructureEngine
from .htf_bias_engine import HTFBiasEngine
from .htf_strength_engine import HTFStrengthEngine
from .htf_permission_engine import HTFPermissionEngine


class HTFAnalyzer:
    """
    Higher Timeframe Analyzer.
    
    Answers 3 questions:
    1. What is the HTF direction?
    2. How strong is that direction?
    3. What trading is allowed?
    
    Does NOT:
    - Generate entry signals
    - Find micro timing
    - Duplicate Prediction Engine
    """
    
    def __init__(self):
        self.structure_engine = HTFStructureEngine()
        self.bias_engine = HTFBiasEngine()
        self.strength_engine = HTFStrengthEngine()
        self.permission_engine = HTFPermissionEngine()
    
    def analyze(self, data: Dict) -> Dict:
        """
        Analyze HTF context.
        
        Args:
            data: HTF input with structure, trend, momentum, quality
        
        Returns:
            HTF analysis with bias, strength, permission
        """
        # Step 1: Evaluate structure
        structure_ctx = self.structure_engine.evaluate(data)
        
        # Step 2: Compute bias
        trend = data.get("trend", {})
        momentum = data.get("momentum", {})
        quality = data.get("quality", {})
        
        bias_result = self.bias_engine.compute(
            structure_ctx=structure_ctx,
            trend=trend,
            momentum=momentum,
            quality=quality
        )
        
        # Step 3: Compute strength
        strength = self.strength_engine.compute(
            bias_result=bias_result,
            structure_ctx=structure_ctx,
            quality=quality
        )
        
        # Step 4: Compute permissions
        permission = self.permission_engine.compute(
            bias=bias_result["htf_bias"],
            strength=strength,
            structure_ctx=structure_ctx
        )
        
        return {
            "htf_bias": bias_result["htf_bias"],
            "htf_strength": strength,
            "htf_structure": structure_ctx["market_phase"],
            "htf_permission": permission,
            "bullish_score": bias_result["bullish_score"],
            "bearish_score": bias_result["bearish_score"],
            "reasons": bias_result["reasons"],
            "analyzed_at": datetime.now(timezone.utc).isoformat()
        }
    
    def generate_mock_input(self, scenario: str = "bullish_trend") -> Dict:
        """Generate mock HTF input for testing."""
        scenarios = {
            "bullish_trend": {
                "structure": {
                    "market_phase": "trend",
                    "hh_count": 4, "hl_count": 3,
                    "lh_count": 1, "ll_count": 0,
                    "bos": 2, "choch": 0,
                    "range_score": 0.15, "compression_score": 0.20
                },
                "trend": {"trend_bias": 0.72, "ema_stack": "bullish", "price_vs_ema200": "above"},
                "momentum": {"momentum_bias": 0.65, "rsi_state": "bullish", "macd_state": "bullish"},
                "quality": {"setup_quality": 0.78, "noise_score": 0.18, "conflict_score": 0.12}
            },
            "bearish_trend": {
                "structure": {
                    "market_phase": "trend",
                    "hh_count": 0, "hl_count": 1,
                    "lh_count": 4, "ll_count": 3,
                    "bos": 2, "choch": 0,
                    "range_score": 0.12, "compression_score": 0.18
                },
                "trend": {"trend_bias": -0.68, "ema_stack": "bearish", "price_vs_ema200": "below"},
                "momentum": {"momentum_bias": -0.60, "rsi_state": "bearish", "macd_state": "bearish"},
                "quality": {"setup_quality": 0.75, "noise_score": 0.20, "conflict_score": 0.15}
            },
            "range": {
                "structure": {
                    "market_phase": "range",
                    "hh_count": 2, "hl_count": 2,
                    "lh_count": 2, "ll_count": 2,
                    "bos": 0, "choch": 1,
                    "range_score": 0.72, "compression_score": 0.45
                },
                "trend": {"trend_bias": 0.05, "ema_stack": "mixed", "price_vs_ema200": "at"},
                "momentum": {"momentum_bias": 0.10, "rsi_state": "neutral", "macd_state": "neutral"},
                "quality": {"setup_quality": 0.55, "noise_score": 0.35, "conflict_score": 0.30}
            }
        }
        return scenarios.get(scenario, scenarios["bullish_trend"])
    
    def health_check(self) -> Dict:
        """Health check."""
        return {
            "ok": True,
            "module": "htf_analyzer",
            "version": "4.7.1",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }


# Singleton
_htf_analyzer: Optional[HTFAnalyzer] = None


def get_htf_analyzer() -> HTFAnalyzer:
    """Get singleton HTF analyzer."""
    global _htf_analyzer
    if _htf_analyzer is None:
        _htf_analyzer = HTFAnalyzer()
    return _htf_analyzer
