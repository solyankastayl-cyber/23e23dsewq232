"""
Monte Carlo Stress Engine Module (S5)
=====================================

Monte Carlo stress testing for portfolio simulation.

Features:
- Random market path generation
- Bootstrap, noise injection, crash simulation
- VaR and CVaR calculation
- Tail risk analysis
- Scenario classification

Pipeline:
Portfolio Simulation → Random Paths → 1000 Simulations → Distribution → Tail Risk
"""

from .mc_types import (
    MonteCarloExperiment,
    MonteCarloPath,
    MonteCarloDistribution,
    TailRiskMetrics,
    ScenarioSummary,
    ExperimentStatus,
    PathGeneratorType,
    CrashType
)

from .mc_path_generator import MonteCarloPathGenerator, MarketPath
from .mc_simulation_engine import mc_simulation_engine, mc_repository
from .mc_distribution_analyzer import mc_distribution_analyzer

__all__ = [
    # Types
    "MonteCarloExperiment",
    "MonteCarloPath",
    "MonteCarloDistribution",
    "TailRiskMetrics",
    "ScenarioSummary",
    "ExperimentStatus",
    "PathGeneratorType",
    "CrashType",
    "MarketPath",
    
    # Services
    "MonteCarloPathGenerator",
    "mc_simulation_engine",
    "mc_repository",
    "mc_distribution_analyzer"
]
