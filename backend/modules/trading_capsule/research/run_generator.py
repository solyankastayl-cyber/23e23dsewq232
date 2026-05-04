"""
Run Generator (S2.2)
====================

Generates ExperimentRuns for an experiment.

For each strategy in experiment, creates:
1. ExperimentRun
2. SimulationRun (via simulation_run_service)

Links them together for tracking.
"""

from typing import List
import threading

from .experiment_types import (
    ResearchExperiment,
    ExperimentRun,
    RunStatus
)


class RunGenerator:
    """
    Generates simulation runs for experiments.
    
    Thread-safe singleton.
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._initialized = True
        print("[RunGenerator] Initialized")
    
    def generate_runs(self, experiment: ResearchExperiment) -> List[ExperimentRun]:
        """
        Generate ExperimentRuns for all strategies in experiment.
        
        Args:
            experiment: Research experiment
            
        Returns:
            List of created ExperimentRuns
        """
        runs = []
        
        for strategy_id in experiment.strategies:
            # Create simulation run
            simulation_run_id = self._create_simulation_run(
                experiment,
                strategy_id
            )
            
            # Create experiment run linking to simulation
            exp_run = ExperimentRun(
                experiment_id=experiment.experiment_id,
                strategy_id=strategy_id,
                simulation_run_id=simulation_run_id,
                status=RunStatus.PENDING
            )
            
            runs.append(exp_run)
            
            print(f"[RunGenerator] Created run for strategy: {strategy_id} -> {simulation_run_id}")
        
        return runs
    
    def _create_simulation_run(
        self,
        experiment: ResearchExperiment,
        strategy_id: str
    ) -> str:
        """
        Create a SimulationRun for a strategy.
        
        Returns simulation_run_id.
        """
        try:
            from ..simulation.simulation_run_service import simulation_run_service
            from ..simulation.simulation_types import CapitalProfile, Timeframe
            
            # Map capital profile
            capital_profile_map = {
                "SMALL": CapitalProfile.SMALL,
                "MEDIUM": CapitalProfile.MEDIUM,
                "LARGE": CapitalProfile.LARGE
            }
            capital_profile = capital_profile_map.get(
                experiment.capital_profile,
                CapitalProfile.SMALL
            )
            
            # Map timeframe
            timeframe_map = {
                "1D": Timeframe.D1,
                "4H": Timeframe.H4,
                "1H": Timeframe.H1
            }
            timeframe = timeframe_map.get(
                experiment.timeframe,
                Timeframe.D1
            )
            
            # Create simulation run
            sim_run = simulation_run_service.create_run(
                strategy_id=strategy_id,
                asset=experiment.asset,
                start_date=experiment.start_date,
                end_date=experiment.end_date,
                capital_profile=capital_profile,
                initial_capital_usd=experiment.initial_capital_usd,
                timeframe=timeframe,
                dataset_id=experiment.dataset_id
            )
            
            return sim_run.run_id
            
        except Exception as e:
            print(f"[RunGenerator] Failed to create simulation run: {e}")
            # Return a placeholder ID for now
            import uuid
            return f"sim_{uuid.uuid4().hex[:8]}"


# Global singleton
run_generator = RunGenerator()
