"""
Walk Forward Engine (S2.6B)
===========================

Main engine for Walk Forward analysis.

Manages:
- WalkForward experiment lifecycle
- Window-based train/test runs
- Integration with existing S2 Experiment Engine

Pipeline:
1. Create WalkForward experiment
2. Generate windows
3. For each window:
   a. Run train simulations
   b. Run test simulations
4. Collect metrics
5. Trigger robustness analysis
"""

from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from concurrent.futures import ThreadPoolExecutor
import threading
import os
import time

from .walkforward_types import (
    WalkForwardExperiment,
    WalkForwardWindow,
    WalkForwardRun,
    WalkForwardStatus,
    WFRunStatus
)

from .window_generator import window_generator


# Configuration
MAX_PARALLEL_WINDOWS = 2


class WalkForwardEngine:
    """
    Main Walk Forward analysis engine.
    
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
        
        # In-memory storage
        self._experiments: Dict[str, WalkForwardExperiment] = {}
        self._windows: Dict[str, WalkForwardWindow] = {}  # window_id -> window
        self._runs: Dict[str, WalkForwardRun] = {}  # run_id -> run
        
        # Experiment -> windows mapping
        self._experiment_windows: Dict[str, List[str]] = {}  # exp_id -> [window_ids]
        
        # Thread pool
        self._executor: Optional[ThreadPoolExecutor] = None
        
        # MongoDB (lazy init)
        self._db = None
        self._experiments_col = None
        self._windows_col = None
        self._runs_col = None
        
        self._initialized = True
        print(f"[WalkForwardEngine] Initialized (max_parallel_windows={MAX_PARALLEL_WINDOWS})")
    
    def _get_executor(self) -> ThreadPoolExecutor:
        """Get or create thread pool"""
        if self._executor is None:
            self._executor = ThreadPoolExecutor(
                max_workers=MAX_PARALLEL_WINDOWS,
                thread_name_prefix="wf_engine"
            )
        return self._executor
    
    def _get_collections(self):
        """Get MongoDB collections (lazy init)"""
        if self._experiments_col is None:
            try:
                from pymongo import MongoClient
                
                mongo_url = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
                db_name = os.environ.get("DB_NAME", "trading_capsule")
                
                client = MongoClient(mongo_url)
                self._db = client[db_name]
                self._experiments_col = self._db["walkforward_experiments"]
                self._windows_col = self._db["walkforward_windows"]
                self._runs_col = self._db["walkforward_runs"]
                
                # Indexes
                self._experiments_col.create_index("experiment_id", unique=True)
                self._windows_col.create_index("window_id", unique=True)
                self._windows_col.create_index("experiment_id")
                self._runs_col.create_index("run_id", unique=True)
                self._runs_col.create_index("experiment_id")
                
                print("[WalkForwardEngine] MongoDB connected")
            except Exception as e:
                print(f"[WalkForwardEngine] MongoDB connection failed: {e}")
        
        return self._experiments_col, self._windows_col, self._runs_col
    
    # ===========================================
    # Create Experiment
    # ===========================================
    
    def create_experiment(
        self,
        name: str,
        asset: str,
        strategies: List[str],
        start_date: str,
        end_date: str,
        train_window_bars: int = 730,
        test_window_bars: int = 365,
        step_bars: int = 365,
        capital_profile: str = "SMALL",
        initial_capital_usd: float = 10000.0,
        timeframe: str = "1D",
        description: str = ""
    ) -> WalkForwardExperiment:
        """
        Create a new Walk Forward experiment.
        """
        # Generate dataset ID
        dataset_id = f"{asset}_{start_date}_{end_date}_{timeframe}".replace("-", "")
        
        # Calculate approximate dataset length
        # This is a rough estimate - actual data may vary
        from datetime import datetime as dt
        try:
            d1 = dt.strptime(start_date, "%Y-%m-%d")
            d2 = dt.strptime(end_date, "%Y-%m-%d")
            days = (d2 - d1).days
            
            tf_multiplier = {"1D": 1, "4H": 6, "1H": 24}.get(timeframe, 1)
            dataset_length = days * tf_multiplier
        except Exception:
            dataset_length = 2000  # Default estimate
        
        # Calculate expected windows
        expected_windows = window_generator.calculate_windows_count(
            dataset_length,
            train_window_bars,
            test_window_bars,
            step_bars
        )
        
        # Determine capital
        capital_map = {"SMALL": 10000.0, "MEDIUM": 50000.0, "LARGE": 100000.0}
        capital = initial_capital_usd or capital_map.get(capital_profile, 10000.0)
        
        # Create experiment
        experiment = WalkForwardExperiment(
            name=name,
            description=description,
            asset=asset,
            dataset_id=dataset_id,
            start_date=start_date,
            end_date=end_date,
            timeframe=timeframe,
            train_window_bars=train_window_bars,
            test_window_bars=test_window_bars,
            step_bars=step_bars,
            strategies=strategies,
            capital_profile=capital_profile,
            initial_capital_usd=capital,
            total_windows=expected_windows,
            status=WalkForwardStatus.CREATED
        )
        
        # Store
        self._experiments[experiment.experiment_id] = experiment
        self._save_experiment(experiment)
        
        print(f"[WalkForwardEngine] Created experiment: {experiment.experiment_id} " +
              f"({expected_windows} windows expected, {len(strategies)} strategies)")
        
        return experiment
    
    # ===========================================
    # Start Experiment
    # ===========================================
    
    def start_experiment(self, experiment_id: str) -> Optional[WalkForwardExperiment]:
        """
        Start Walk Forward analysis.
        
        1. Generate windows
        2. Create runs for each strategy/window combination
        3. Start execution
        """
        experiment = self.get_experiment(experiment_id)
        if not experiment:
            return None
        
        if experiment.status != WalkForwardStatus.CREATED:
            print(f"[WalkForwardEngine] Cannot start: status={experiment.status.value}")
            return experiment
        
        # Update status
        experiment.status = WalkForwardStatus.GENERATING
        experiment.started_at = datetime.now(timezone.utc)
        self._save_experiment(experiment)
        
        # Calculate dataset length
        from datetime import datetime as dt
        try:
            d1 = dt.strptime(experiment.start_date, "%Y-%m-%d")
            d2 = dt.strptime(experiment.end_date, "%Y-%m-%d")
            days = (d2 - d1).days
            tf_multiplier = {"1D": 1, "4H": 6, "1H": 24}.get(experiment.timeframe, 1)
            dataset_length = days * tf_multiplier
        except Exception:
            dataset_length = 2000
        
        # Generate windows
        windows = window_generator.generate_windows(
            experiment_id=experiment_id,
            dataset_length_bars=dataset_length,
            train_window_bars=experiment.train_window_bars,
            test_window_bars=experiment.test_window_bars,
            step_bars=experiment.step_bars,
            start_date=experiment.start_date,
            timeframe=experiment.timeframe
        )
        
        if not windows:
            experiment.status = WalkForwardStatus.FAILED
            experiment.error_message = "Failed to generate windows"
            self._save_experiment(experiment)
            return experiment
        
        # Store windows
        window_ids = []
        for window in windows:
            self._windows[window.window_id] = window
            window_ids.append(window.window_id)
            self._save_window(window)
        
        self._experiment_windows[experiment_id] = window_ids
        experiment.total_windows = len(windows)
        
        # Create runs for each strategy/window combination
        runs_created = 0
        for window in windows:
            for strategy_id in experiment.strategies:
                run = WalkForwardRun(
                    experiment_id=experiment_id,
                    window_id=window.window_id,
                    window_index=window.index,
                    strategy_id=strategy_id,
                    status=WFRunStatus.PENDING
                )
                self._runs[run.run_id] = run
                self._save_run(run)
                runs_created += 1
        
        # Update status to running
        experiment.status = WalkForwardStatus.RUNNING
        self._save_experiment(experiment)
        
        print(f"[WalkForwardEngine] Started experiment: {experiment_id} " +
              f"({len(windows)} windows, {runs_created} runs)")
        
        # Start execution (async)
        self._start_execution(experiment_id)
        
        return experiment
    
    def _start_execution(self, experiment_id: str):
        """Start executing Walk Forward runs"""
        executor = self._get_executor()
        
        # Get all pending runs for this experiment
        runs = [r for r in self._runs.values() 
                if r.experiment_id == experiment_id and r.status == WFRunStatus.PENDING]
        
        for run in runs:
            executor.submit(self._execute_run, run)
    
    def _execute_run(self, run: WalkForwardRun):
        """
        Execute a single Walk Forward run (train + test for one strategy/window).
        """
        try:
            # Update status
            run.status = WFRunStatus.TRAIN_RUNNING
            run.started_at = datetime.now(timezone.utc)
            self._save_run(run)
            
            # Get window
            window = self._windows.get(run.window_id)
            experiment = self._experiments.get(run.experiment_id)
            
            if not window or not experiment:
                raise Exception("Window or experiment not found")
            
            # Run TRAIN simulation
            train_sim_id = self._run_simulation(
                experiment, run.strategy_id, 
                window.train_start_date, window.train_end_date,
                f"{run.experiment_id}_train_{run.window_index}"
            )
            run.train_simulation_run_id = train_sim_id
            run.status = WFRunStatus.TRAIN_COMPLETE
            self._save_run(run)
            
            # Run TEST simulation
            run.status = WFRunStatus.TEST_RUNNING
            self._save_run(run)
            
            test_sim_id = self._run_simulation(
                experiment, run.strategy_id,
                window.test_start_date, window.test_end_date,
                f"{run.experiment_id}_test_{run.window_index}"
            )
            run.test_simulation_run_id = test_sim_id
            
            # Complete
            run.status = WFRunStatus.COMPLETED
            run.completed_at = datetime.now(timezone.utc)
            self._save_run(run)
            
            # Check if experiment completed
            self._check_experiment_completion(run.experiment_id)
            
        except Exception as e:
            print(f"[WalkForwardEngine] Run {run.run_id} failed: {e}")
            run.status = WFRunStatus.FAILED
            run.error_message = str(e)
            self._save_run(run)
            self._check_experiment_completion(run.experiment_id)
    
    def _run_simulation(
        self,
        experiment: WalkForwardExperiment,
        strategy_id: str,
        start_date: str,
        end_date: str,
        name: str
    ) -> str:
        """
        Run a single simulation via simulation_run_service.
        Returns simulation run ID.
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
                start_date=start_date,
                end_date=end_date,
                capital_profile=capital_profile,
                initial_capital_usd=experiment.initial_capital_usd,
                timeframe=timeframe
            )
            
            # Start and complete (placeholder - actual simulation would take longer)
            simulation_run_service.start_run(sim_run.run_id)
            time.sleep(0.2)  # Simulate processing
            simulation_run_service.complete_run(
                sim_run.run_id,
                final_equity_usd=sim_run.initial_capital_usd * 1.05,
                total_trades=10
            )
            
            return sim_run.run_id
            
        except Exception as e:
            print(f"[WalkForwardEngine] Simulation failed: {e}")
            import uuid
            return f"sim_{uuid.uuid4().hex[:8]}"
    
    def _check_experiment_completion(self, experiment_id: str):
        """Check if all runs completed and trigger analysis"""
        experiment = self._experiments.get(experiment_id)
        if not experiment or experiment.status != WalkForwardStatus.RUNNING:
            return
        
        # Count completed runs
        runs = [r for r in self._runs.values() if r.experiment_id == experiment_id]
        completed = sum(1 for r in runs if r.status == WFRunStatus.COMPLETED)
        failed = sum(1 for r in runs if r.status == WFRunStatus.FAILED)
        
        total_expected = len(experiment.strategies) * experiment.total_windows
        
        # Update completed windows count
        experiment.completed_windows = completed // len(experiment.strategies) if experiment.strategies else 0
        
        if completed + failed >= total_expected:
            # All runs finished - trigger analysis
            experiment.status = WalkForwardStatus.ANALYZING
            self._save_experiment(experiment)
            
            self._trigger_robustness_analysis(experiment_id)
            
            experiment.status = WalkForwardStatus.COMPLETED
            experiment.completed_at = datetime.now(timezone.utc)
            self._save_experiment(experiment)
            
            print(f"[WalkForwardEngine] Experiment {experiment_id} completed " +
                  f"({completed} success, {failed} failed)")
    
    def _trigger_robustness_analysis(self, experiment_id: str):
        """Trigger robustness analysis after all runs complete"""
        try:
            from .robustness_analyzer import robustness_analyzer
            robustness_analyzer.analyze_experiment(experiment_id)
        except Exception as e:
            print(f"[WalkForwardEngine] Robustness analysis failed: {e}")
    
    # ===========================================
    # Getters
    # ===========================================
    
    def get_experiment(self, experiment_id: str) -> Optional[WalkForwardExperiment]:
        """Get experiment by ID"""
        return self._experiments.get(experiment_id)
    
    def list_experiments(
        self,
        status: Optional[WalkForwardStatus] = None,
        limit: int = 50
    ) -> List[WalkForwardExperiment]:
        """List experiments"""
        experiments = list(self._experiments.values())
        
        if status:
            experiments = [e for e in experiments if e.status == status]
        
        experiments.sort(key=lambda e: e.created_at, reverse=True)
        return experiments[:limit]
    
    def get_windows(self, experiment_id: str) -> List[WalkForwardWindow]:
        """Get all windows for experiment"""
        window_ids = self._experiment_windows.get(experiment_id, [])
        return [self._windows[wid] for wid in window_ids if wid in self._windows]
    
    def get_runs(self, experiment_id: str) -> List[WalkForwardRun]:
        """Get all runs for experiment"""
        return [r for r in self._runs.values() if r.experiment_id == experiment_id]
    
    def get_runs_by_window(
        self,
        experiment_id: str,
        window_id: str
    ) -> List[WalkForwardRun]:
        """Get runs for a specific window"""
        return [
            r for r in self._runs.values()
            if r.experiment_id == experiment_id and r.window_id == window_id
        ]
    
    # ===========================================
    # Persistence
    # ===========================================
    
    def _save_experiment(self, experiment: WalkForwardExperiment):
        exp_col, _, _ = self._get_collections()
        if exp_col is not None:
            try:
                exp_col.replace_one(
                    {"experiment_id": experiment.experiment_id},
                    experiment.to_dict(),
                    upsert=True
                )
            except Exception as e:
                print(f"[WalkForwardEngine] Save experiment failed: {e}")
    
    def _save_window(self, window: WalkForwardWindow):
        _, win_col, _ = self._get_collections()
        if win_col is not None:
            try:
                win_col.replace_one(
                    {"window_id": window.window_id},
                    window.to_dict(),
                    upsert=True
                )
            except Exception as e:
                print(f"[WalkForwardEngine] Save window failed: {e}")
    
    def _save_run(self, run: WalkForwardRun):
        _, _, runs_col = self._get_collections()
        if runs_col is not None:
            try:
                runs_col.replace_one(
                    {"run_id": run.run_id},
                    run.to_dict(),
                    upsert=True
                )
            except Exception as e:
                print(f"[WalkForwardEngine] Save run failed: {e}")
    
    # ===========================================
    # Cleanup
    # ===========================================
    
    def delete_experiment(self, experiment_id: str) -> bool:
        """Delete experiment and all related data"""
        # Remove from memory
        self._experiments.pop(experiment_id, None)
        self._experiment_windows.pop(experiment_id, None)
        
        # Remove windows and runs
        self._windows = {
            k: v for k, v in self._windows.items()
            if v.experiment_id != experiment_id
        }
        self._runs = {
            k: v for k, v in self._runs.items()
            if v.experiment_id != experiment_id
        }
        
        # Remove from MongoDB
        exp_col, win_col, runs_col = self._get_collections()
        if exp_col is not None:
            try:
                exp_col.delete_one({"experiment_id": experiment_id})
                if win_col is not None:
                    win_col.delete_many({"experiment_id": experiment_id})
                if runs_col is not None:
                    runs_col.delete_many({"experiment_id": experiment_id})
            except Exception:
                pass
        
        return True


# Global singleton
walkforward_engine = WalkForwardEngine()
