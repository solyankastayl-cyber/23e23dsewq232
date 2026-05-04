"""
PHASE 4 — Entry Timing & Wrong Early Reduction

Complete Entry Timing Stack:
- 4.1: Wrong Early Diagnostic Engine
- 4.2: Entry Mode Selector
- 4.3: Entry Execution Strategy
- 4.4: Entry Quality Score
- 4.5: Entry Timing Integration
- 4.6: Wrong Early Re-Measurement
- 4.7: MTF Entry Timing Layer (HTF + LTF + Alignment)
- 4.8: Microstructure Entry Layer (Liquidity + Orderbook + Imbalance + Absorption + Sweep)
"""

from .diagnostics import (
    WrongEarlyEngine,
    get_wrong_early_engine,
    WRONG_EARLY_REASONS,
)

from .mode_selector import (
    EntryModeEngine,
    get_entry_mode_engine,
    ENTRY_MODES,
)

from .execution_strategy import (
    EntryExecutionStrategy,
    get_execution_strategy_engine,
    EXECUTION_STRATEGIES,
)

from .quality import (
    EntryQualityEngine,
    get_entry_quality_engine,
    ENTRY_QUALITY_FACTORS,
)

from .integration import (
    EntryTimingIntegration,
    get_entry_timing_integration,
    FINAL_ENTRY_DECISIONS,
)

from .backtest import (
    EntryTimingBacktester,
    get_entry_timing_backtester,
)

from .mtf import (
    HTFAnalyzer,
    get_htf_analyzer,
    LTFRefinementEngine,
    get_ltf_engine,
    MTFAlignmentEngine,
    get_mtf_alignment_engine,
    MTFDecisionEngine,
    get_mtf_decision_engine,
)

from .microstructure import (
    MicrostructureDecisionEngine,
    get_microstructure_engine,
    MICROSTRUCTURE_DECISIONS,
)

__all__ = [
    # Phase 4.1
    "WrongEarlyEngine",
    "get_wrong_early_engine",
    "WRONG_EARLY_REASONS",
    # Phase 4.2
    "EntryModeEngine",
    "get_entry_mode_engine",
    "ENTRY_MODES",
    # Phase 4.3
    "EntryExecutionStrategy",
    "get_execution_strategy_engine",
    "EXECUTION_STRATEGIES",
    # Phase 4.4
    "EntryQualityEngine",
    "get_entry_quality_engine",
    "ENTRY_QUALITY_FACTORS",
    # Phase 4.5
    "EntryTimingIntegration",
    "get_entry_timing_integration",
    "FINAL_ENTRY_DECISIONS",
    # Phase 4.6
    "EntryTimingBacktester",
    "get_entry_timing_backtester",
    # Phase 4.7
    "HTFAnalyzer",
    "get_htf_analyzer",
    "LTFRefinementEngine",
    "get_ltf_engine",
    "MTFAlignmentEngine",
    "get_mtf_alignment_engine",
    "MTFDecisionEngine",
    "get_mtf_decision_engine",
    # Phase 4.8
    "MicrostructureDecisionEngine",
    "get_microstructure_engine",
    "MICROSTRUCTURE_DECISIONS",
]
