"""
Simulation Runner (S2.2)
========================

Runs simulations for experiment runs in parallel.

Features:
- ThreadPoolExecutor for parallel execution
- Configurable max_parallel_runs
- Progress tracking
- Error handling per run
"""

from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
import threading
import time

from .experiment_types import (
    ExperimentRun,
    RunStatus
)


# Configuration
MAX_PARALLEL_RUNS = 4
EXPERIMENT_TIMEOUT_SECONDS = 6 * 3600  # 6 hours


class SimulationRunner:
    """
    Runs simulations in parallel.
    
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
        
        # Thread pool
        self._executor: Optional[ThreadPoolExecutor] = None
        
        # Active runs tracking
        self._active_runs: Dict[str, str] = {}  # run_id -> experiment_id
        
        # Config
        self.max_parallel = MAX_PARALLEL_RUNS
        
        self._initialized = True
        print(f"[SimulationRunner] Initialized (max_parallel={self.max_parallel})")
    
    def _get_executor(self) -> ThreadPoolExecutor:
        """Get or create thread pool"""
        if self._executor is None:
            self._executor = ThreadPoolExecutor(
                max_workers=self.max_parallel,
                thread_name_prefix="sim_runner"
            )
        return self._executor
    
    # ===========================================
    # Run Simulations
    # ===========================================
    
    def start_runs(self, experiment_id: str) -> int:
        """
        Start all runs for an experiment.
        
        Returns number of runs started.
        """
        from .experiment_manager import experiment_manager
        
        runs = experiment_manager.get_experiment_runs(experiment_id)
        pending_runs = [r for r in runs if r.status == RunStatus.PENDING]
        
        if not pending_runs:
            print(f"[SimulationRunner] No pending runs for experiment: {experiment_id}")
            return 0
        
        executor = self._get_executor()
        
        for run in pending_runs:
            self._active_runs[run.run_id] = experiment_id
            executor.submit(self._execute_run, run)
        
        print(f"[SimulationRunner] Started {len(pending_runs)} runs for experiment: {experiment_id}")
        return len(pending_runs)
    
    def _execute_run(self, run: ExperimentRun):
        """
        Execute a single simulation run.
        
        Updates status via experiment_manager.
        """
        from .experiment_manager import experiment_manager
        
        try:
            # Update status to RUNNING
            experiment_manager.update_run_status(
                run.run_id,
                RunStatus.RUNNING
            )
            
            # Execute simulation
            success = self._run_simulation(run.simulation_run_id)
            
            # Update status based on result
            if success:
                experiment_manager.update_run_status(
                    run.run_id,
                    RunStatus.COMPLETED
                )
            else:
                experiment_manager.update_run_status(
                    run.run_id,
                    RunStatus.FAILED,
                    error_message="Simulation execution failed"
                )
                
        except Exception as e:
            print(f"[SimulationRunner] Run {run.run_id} failed: {e}")
            experiment_manager.update_run_status(
                run.run_id,
                RunStatus.FAILED,
                error_message=str(e)
            )
        finally:
            self._active_runs.pop(run.run_id, None)
    
    def _run_simulation(self, simulation_run_id: str) -> bool:
        """
        Run simulation via SimulationEngine.
        
        Returns success status.
        """
        try:
            from ..simulation.simulation_engine import simulation_engine
            from ..simulation.simulation_run_service import simulation_run_service
            
            # Get simulation run
            sim_run = simulation_run_service.get_run(simulation_run_id)
            if not sim_run:
                print(f"[SimulationRunner] Simulation run not found: {simulation_run_id}")
                return False
            
            # Start simulation via engine
            # Note: This is a simplified version - actual implementation
            # would use the full simulation engine pipeline
            simulation_run_service.start_run(simulation_run_id)
            
            # For now, mark as completed after brief delay
            # In real implementation, this would monitor the actual simulation
            time.sleep(0.5)  # Simulate processing
            
            simulation_run_service.complete_run(
                simulation_run_id,
                final_equity_usd=sim_run.initial_capital_usd * 1.05,  # Placeholder
                total_trades=10  # Placeholder
            )
            
            return True
            
        except Exception as e:
            print(f"[SimulationRunner] Simulation failed: {e}")
            return False
    
    # ===========================================
    # Status / Control
    # ===========================================
    
    def get_active_runs(self) -> Dict[str, str]:
        """Get currently active runs: run_id -> experiment_id"""
        return dict(self._active_runs)
    
    def is_running(self, experiment_id: str) -> bool:
        """Check if experiment has active runs"""
        return any(
            exp_id == experiment_id
            for exp_id in self._active_runs.values()
        )
    
    def cancel_runs(self, experiment_id: str):
        """Cancel all runs for an experiment"""
        # Mark runs as cancelled
        from .experiment_manager import experiment_manager
        
        runs = experiment_manager.get_experiment_runs(experiment_id)
        for run in runs:
            if run.status in [RunStatus.PENDING, RunStatus.RUNNING]:
                experiment_manager.update_run_status(
                    run.run_id,
                    RunStatus.FAILED,
                    error_message="Cancelled by user"
                )
                self._active_runs.pop(run.run_id, None)
    
    def shutdown(self):
        """Shutdown thread pool"""
        if self._executor:
            self._executor.shutdown(wait=False)
            self._executor = None
            self._active_runs.clear()


# Global singleton
simulation_runner = SimulationRunner()
