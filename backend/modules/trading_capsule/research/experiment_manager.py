"""
Experiment Manager (S2.1)
=========================

Manages research experiment lifecycle.

Operations:
- create_experiment: Create new experiment
- start_experiment: Start experiment (generates runs)
- get_experiment: Get experiment by ID
- list_experiments: List all experiments
- complete_experiment: Mark experiment as completed
- cancel_experiment: Cancel running experiment
"""

from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
import threading
import os

from .experiment_types import (
    ResearchExperiment,
    ExperimentStatus,
    ExperimentRun,
    RunStatus
)


class ExperimentManager:
    """
    Service for managing research experiments.
    
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
        self._experiments: Dict[str, ResearchExperiment] = {}
        self._runs: Dict[str, ExperimentRun] = {}
        
        # MongoDB (lazy init)
        self._db = None
        self._experiments_collection = None
        self._runs_collection = None
        
        self._initialized = True
        print("[ExperimentManager] Initialized")
    
    def _get_collections(self):
        """Get MongoDB collections (lazy init)"""
        if self._experiments_collection is None:
            try:
                from pymongo import MongoClient
                
                mongo_url = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
                db_name = os.environ.get("DB_NAME", "trading_capsule")
                
                client = MongoClient(mongo_url)
                self._db = client[db_name]
                self._experiments_collection = self._db["research_experiments"]
                self._runs_collection = self._db["experiment_runs"]
                
                # Create indexes
                self._experiments_collection.create_index("experiment_id", unique=True)
                self._experiments_collection.create_index("status")
                self._runs_collection.create_index("run_id", unique=True)
                self._runs_collection.create_index("experiment_id")
                
                print("[ExperimentManager] MongoDB connected")
            except Exception as e:
                print(f"[ExperimentManager] MongoDB connection failed: {e}")
        
        return self._experiments_collection, self._runs_collection
    
    # ===========================================
    # Create Experiment (S2.1)
    # ===========================================
    
    def create_experiment(
        self,
        name: str,
        asset: str,
        strategies: List[str],
        start_date: str,
        end_date: str,
        capital_profile: str = "SMALL",
        initial_capital_usd: float = 10000.0,
        timeframe: str = "1D",
        description: str = ""
    ) -> ResearchExperiment:
        """
        Create a new research experiment.
        
        Args:
            name: Experiment name
            asset: Asset to test (e.g., "BTCUSDT")
            strategies: List of strategy IDs to compare
            start_date: Simulation start date (YYYY-MM-DD)
            end_date: Simulation end date (YYYY-MM-DD)
            capital_profile: SMALL, MEDIUM, LARGE
            initial_capital_usd: Starting capital
            timeframe: 1D, 4H, 1H
            description: Optional description
            
        Returns:
            Created ResearchExperiment
        """
        # Determine capital based on profile
        capital_map = {
            "SMALL": 10000.0,
            "MEDIUM": 50000.0,
            "LARGE": 100000.0
        }
        capital = initial_capital_usd or capital_map.get(capital_profile, 10000.0)
        
        # Generate dataset ID
        dataset_id = f"{asset}_{start_date}_{end_date}_{timeframe}".replace("-", "")
        
        # Create experiment
        experiment = ResearchExperiment(
            name=name,
            description=description,
            asset=asset,
            dataset_id=dataset_id,
            start_date=start_date,
            end_date=end_date,
            timeframe=timeframe,
            strategies=strategies,
            capital_profile=capital_profile,
            initial_capital_usd=capital,
            total_runs=len(strategies),
            status=ExperimentStatus.CREATED
        )
        
        # Store in memory
        self._experiments[experiment.experiment_id] = experiment
        
        # Persist to MongoDB
        self._save_experiment(experiment)
        
        print(f"[ExperimentManager] Created experiment: {experiment.experiment_id} with {len(strategies)} strategies")
        return experiment
    
    # ===========================================
    # Start Experiment
    # ===========================================
    
    def start_experiment(self, experiment_id: str) -> Optional[ResearchExperiment]:
        """
        Start an experiment (triggers run generation).
        
        Flow:
        1. Update status to GENERATING
        2. Generate ExperimentRuns
        3. Update status to RUNNING
        4. Trigger SimulationRunner (async)
        """
        experiment = self.get_experiment(experiment_id)
        if not experiment:
            return None
        
        if experiment.status != ExperimentStatus.CREATED:
            print(f"[ExperimentManager] Cannot start experiment {experiment_id}: status={experiment.status.value}")
            return experiment
        
        # Update status
        experiment.status = ExperimentStatus.GENERATING
        experiment.started_at = datetime.now(timezone.utc)
        self._save_experiment(experiment)
        
        # Generate runs (via run_generator)
        from .run_generator import run_generator
        runs = run_generator.generate_runs(experiment)
        
        # Store runs
        for run in runs:
            self._runs[run.run_id] = run
            self._save_run(run)
        
        # Update to RUNNING
        experiment.status = ExperimentStatus.RUNNING
        self._save_experiment(experiment)
        
        print(f"[ExperimentManager] Started experiment: {experiment_id} with {len(runs)} runs")
        return experiment
    
    # ===========================================
    # Get / List
    # ===========================================
    
    def get_experiment(self, experiment_id: str) -> Optional[ResearchExperiment]:
        """Get experiment by ID"""
        # Check memory first
        if experiment_id in self._experiments:
            return self._experiments[experiment_id]
        
        # Try MongoDB
        exp_col, _ = self._get_collections()
        if exp_col is not None:
            try:
                doc = exp_col.find_one({"experiment_id": experiment_id}, {"_id": 0})
                if doc:
                    experiment = self._doc_to_experiment(doc)
                    self._experiments[experiment_id] = experiment
                    return experiment
            except Exception:
                pass
        
        return None
    
    def list_experiments(
        self,
        status: Optional[ExperimentStatus] = None,
        limit: int = 50
    ) -> List[ResearchExperiment]:
        """List experiments with optional status filter"""
        experiments = list(self._experiments.values())
        
        # Filter by status
        if status:
            experiments = [e for e in experiments if e.status == status]
        
        # Sort by created_at desc
        experiments.sort(key=lambda e: e.created_at, reverse=True)
        
        return experiments[:limit]
    
    def get_experiment_runs(self, experiment_id: str) -> List[ExperimentRun]:
        """Get all runs for an experiment"""
        return [
            r for r in self._runs.values()
            if r.experiment_id == experiment_id
        ]
    
    # ===========================================
    # Update / Complete
    # ===========================================
    
    def update_run_status(
        self,
        run_id: str,
        status: RunStatus,
        error_message: str = ""
    ) -> Optional[ExperimentRun]:
        """Update run status"""
        run = self._runs.get(run_id)
        if not run:
            return None
        
        run.status = status
        if status == RunStatus.RUNNING:
            run.started_at = datetime.now(timezone.utc)
        elif status in [RunStatus.COMPLETED, RunStatus.FAILED]:
            run.completed_at = datetime.now(timezone.utc)
            run.error_message = error_message
        
        self._save_run(run)
        
        # Check if experiment completed
        self._check_experiment_completion(run.experiment_id)
        
        return run
    
    def _check_experiment_completion(self, experiment_id: str):
        """Check if all runs completed and update experiment status"""
        experiment = self.get_experiment(experiment_id)
        if not experiment or experiment.status != ExperimentStatus.RUNNING:
            return
        
        runs = self.get_experiment_runs(experiment_id)
        
        completed = sum(1 for r in runs if r.status == RunStatus.COMPLETED)
        failed = sum(1 for r in runs if r.status == RunStatus.FAILED)
        
        experiment.completed_runs = completed
        experiment.failed_runs = failed
        
        # All runs finished?
        if completed + failed == experiment.total_runs:
            experiment.status = ExperimentStatus.COMPLETED
            experiment.completed_at = datetime.now(timezone.utc)
            
            # Trigger ranking (async)
            self._trigger_ranking(experiment_id)
            
            print(f"[ExperimentManager] Experiment {experiment_id} completed: {completed} success, {failed} failed")
        
        self._save_experiment(experiment)
    
    def _trigger_ranking(self, experiment_id: str):
        """Trigger ranking calculation after experiment completes"""
        try:
            from .ranking_engine import ranking_engine
            leaderboard = ranking_engine.rank_experiment(experiment_id)
            
            if leaderboard and leaderboard.winner_strategy_id:
                experiment = self.get_experiment(experiment_id)
                if experiment:
                    experiment.winner_strategy_id = leaderboard.winner_strategy_id
                    experiment.winner_composite_score = leaderboard.winner_score
                    self._save_experiment(experiment)
        except Exception as e:
            print(f"[ExperimentManager] Ranking failed: {e}")
    
    def complete_experiment(
        self,
        experiment_id: str,
        winner_strategy_id: str = "",
        winner_score: float = 0.0
    ) -> Optional[ResearchExperiment]:
        """Mark experiment as completed"""
        experiment = self.get_experiment(experiment_id)
        if not experiment:
            return None
        
        experiment.status = ExperimentStatus.COMPLETED
        experiment.completed_at = datetime.now(timezone.utc)
        experiment.winner_strategy_id = winner_strategy_id
        experiment.winner_composite_score = winner_score
        
        self._save_experiment(experiment)
        return experiment
    
    def cancel_experiment(self, experiment_id: str) -> Optional[ResearchExperiment]:
        """Cancel running experiment"""
        experiment = self.get_experiment(experiment_id)
        if not experiment:
            return None
        
        if experiment.status not in [ExperimentStatus.CREATED, ExperimentStatus.RUNNING]:
            return experiment
        
        experiment.status = ExperimentStatus.CANCELLED
        self._save_experiment(experiment)
        
        return experiment
    
    # ===========================================
    # Persistence
    # ===========================================
    
    def _save_experiment(self, experiment: ResearchExperiment):
        """Save experiment to MongoDB"""
        exp_col, _ = self._get_collections()
        if exp_col is not None:
            try:
                doc = experiment.to_dict()
                exp_col.replace_one(
                    {"experiment_id": experiment.experiment_id},
                    doc,
                    upsert=True
                )
            except Exception as e:
                print(f"[ExperimentManager] Save failed: {e}")
    
    def _save_run(self, run: ExperimentRun):
        """Save run to MongoDB"""
        _, runs_col = self._get_collections()
        if runs_col is not None:
            try:
                doc = run.to_dict()
                runs_col.replace_one(
                    {"run_id": run.run_id},
                    doc,
                    upsert=True
                )
            except Exception as e:
                print(f"[ExperimentManager] Save run failed: {e}")
    
    def _doc_to_experiment(self, doc: Dict[str, Any]) -> ResearchExperiment:
        """Convert MongoDB document to ResearchExperiment"""
        return ResearchExperiment(
            experiment_id=doc.get("experiment_id", ""),
            name=doc.get("name", ""),
            description=doc.get("description", ""),
            asset=doc.get("asset", "BTCUSDT"),
            dataset_id=doc.get("dataset_id", ""),
            start_date=doc.get("start_date", ""),
            end_date=doc.get("end_date", ""),
            timeframe=doc.get("timeframe", "1D"),
            strategies=doc.get("strategies", []),
            capital_profile=doc.get("capital_profile", "SMALL"),
            initial_capital_usd=doc.get("initial_capital_usd", 10000.0),
            status=ExperimentStatus(doc.get("status", "CREATED")),
            total_runs=doc.get("total_runs", 0),
            completed_runs=doc.get("completed_runs", 0),
            failed_runs=doc.get("failed_runs", 0),
            winner_strategy_id=doc.get("winner_strategy_id", ""),
            winner_composite_score=doc.get("winner_composite_score", 0.0)
        )
    
    # ===========================================
    # Cleanup
    # ===========================================
    
    def delete_experiment(self, experiment_id: str) -> bool:
        """Delete experiment and its runs"""
        # Remove from memory
        self._experiments.pop(experiment_id, None)
        self._runs = {
            k: v for k, v in self._runs.items()
            if v.experiment_id != experiment_id
        }
        
        # Remove from MongoDB
        exp_col, runs_col = self._get_collections()
        if exp_col is not None:
            try:
                exp_col.delete_one({"experiment_id": experiment_id})
                if runs_col is not None:
                    runs_col.delete_many({"experiment_id": experiment_id})
                return True
            except Exception:
                pass
        
        return True


# Global singleton
experiment_manager = ExperimentManager()
