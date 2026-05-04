"""
PHASE 4.3 — Slippage Engine
===========================

Execution intelligence для анализа качества исполнения:
- Slippage Calculator: фактическое проскальзывание
- Execution Latency Tracker: latency измерение
- Fill Quality Analyzer: качество заполнения
- Liquidity Impact Engine: влияние на ликвидность

Интеграция с:
- Strategy evaluation
- Execution quality metrics
- Exchange reliability
- Broker simulator calibration
"""

from .slippage_types import (
    SlippageDirection,
    FillQuality,
    LiquidityImpact,
    ExecutionGrade,
    SlippageResult,
    LatencyMetrics,
    FillAnalysis,
    LiquidityImpactResult,
    ExecutionAnalysis,
    ExecutionSnapshot
)
from .slippage_calculator import SlippageCalculator
from .execution_latency_tracker import ExecutionLatencyTracker
from .fill_quality_analyzer import FillQualityAnalyzer
from .liquidity_impact_engine import LiquidityImpactEngine
from .slippage_repository import SlippageRepository

__all__ = [
    # Types
    "SlippageDirection",
    "FillQuality",
    "LiquidityImpact",
    "ExecutionGrade",
    "SlippageResult",
    "LatencyMetrics",
    "FillAnalysis",
    "LiquidityImpactResult",
    "ExecutionAnalysis",
    "ExecutionSnapshot",
    # Engines
    "SlippageCalculator",
    "ExecutionLatencyTracker",
    "FillQualityAnalyzer",
    "LiquidityImpactEngine",
    "SlippageRepository"
]
