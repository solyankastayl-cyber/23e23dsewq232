"""
Research Module (S2)
====================

Strategy Research Lab for Trading Capsule.

S2.1 - Experiment Engine:
- Create experiments
- Manage experiment lifecycle

S2.2 - Multi-Run Simulator:
- Run Generator
- Simulation Runner
- Parallel execution

S2.3 - Strategy Comparator:
- Metrics normalization
- Comparable scorecards
- Warnings layer

S2.4 - Ranking Engine:
- Multi-metric ranking
- Weighted composite score
- Strategy leaderboard

S2.5 - Research Report (coming)
"""

from .experiment_types import (
    ResearchExperiment,
    ExperimentRun,
    ExperimentStatus,
    StrategyScorecard,
    ComparableStrategy,
    StrategyRankingEntry,
    StrategyLeaderboard
)

from .experiment_manager import (
    ExperimentManager,
    experiment_manager
)

from .run_generator import (
    RunGenerator,
    run_generator
)

from .simulation_runner import (
    SimulationRunner,
    simulation_runner
)

from .metrics_normalizer import (
    MetricsNormalizer,
    normalize_metrics
)

from .strategy_comparator import (
    StrategyComparator,
    strategy_comparator
)

from .ranking_engine import (
    RankingEngine,
    ranking_engine
)

from .research_routes import router as research_router


__all__ = [
    # Types
    "ResearchExperiment",
    "ExperimentRun",
    "ExperimentStatus",
    "StrategyScorecard",
    "ComparableStrategy",
    "StrategyRankingEntry",
    "StrategyLeaderboard",
    
    # Experiment Manager (S2.1)
    "ExperimentManager",
    "experiment_manager",
    
    # Run Generator (S2.2)
    "RunGenerator",
    "run_generator",
    
    # Simulation Runner (S2.2)
    "SimulationRunner",
    "simulation_runner",
    
    # Normalizer (S2.3)
    "MetricsNormalizer",
    "normalize_metrics",
    
    # Comparator (S2.3)
    "StrategyComparator",
    "strategy_comparator",
    
    # Ranking (S2.4)
    "RankingEngine",
    "ranking_engine",
    
    # Routes
    "research_router"
]


print("[Research] Module loaded - S2.1/S2.2/S2.3/S2.4 Ready")
