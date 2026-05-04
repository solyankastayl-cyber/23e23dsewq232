"""
Monte Carlo Simulation Engine (S5)
==================================

Core simulation engine for Monte Carlo stress testing.

Pipeline:
1. Load portfolio simulation
2. Generate random market paths
3. Replay portfolio on each path
4. Calculate metrics per path
5. Store results
6. Repeat N times
"""

import threading
import random
import math
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

from .mc_types import (
    MonteCarloExperiment,
    MonteCarloPath,
    ExperimentStatus,
    PathGeneratorType
)
from .mc_path_generator import MonteCarloPathGenerator, MarketPath


# ===========================================
# Monte Carlo Repository
# ===========================================

class MonteCarloRepository:
    """Repository for Monte Carlo experiments and paths"""
    
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
        
        self._experiments: Dict[str, MonteCarloExperiment] = {}
        self._paths: Dict[str, List[MonteCarloPath]] = {}  # experiment_id -> paths
        
        self._initialized = True
        print("[MonteCarloRepository] Initialized")
    
    def save_experiment(self, exp: MonteCarloExperiment) -> MonteCarloExperiment:
        self._experiments[exp.experiment_id] = exp
        if exp.experiment_id not in self._paths:
            self._paths[exp.experiment_id] = []
        return exp
    
    def get_experiment(self, exp_id: str) -> Optional[MonteCarloExperiment]:
        return self._experiments.get(exp_id)
    
    def list_experiments(self, limit: int = 50) -> List[MonteCarloExperiment]:
        exps = list(self._experiments.values())
        exps.sort(key=lambda e: e.created_at, reverse=True)
        return exps[:limit]
    
    def delete_experiment(self, exp_id: str) -> bool:
        self._experiments.pop(exp_id, None)
        self._paths.pop(exp_id, None)
        return True
    
    def save_path(self, path: MonteCarloPath) -> MonteCarloPath:
        if path.experiment_id not in self._paths:
            self._paths[path.experiment_id] = []
        self._paths[path.experiment_id].append(path)
        return path
    
    def get_paths(self, exp_id: str) -> List[MonteCarloPath]:
        return self._paths.get(exp_id, [])
    
    def clear_paths(self, exp_id: str) -> None:
        self._paths[exp_id] = []


mc_repository = MonteCarloRepository()


# ===========================================
# Monte Carlo Simulation Engine
# ===========================================

class MonteCarloSimulationEngine:
    """
    Monte Carlo Simulation Engine.
    
    Runs thousands of simulations with randomized market paths.
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
        print("[MonteCarloSimulationEngine] Initialized")
    
    # ===========================================
    # Create Experiment
    # ===========================================
    
    def create_experiment(
        self,
        portfolio_simulation_id: str,
        num_paths: int = 1000,
        horizon_days: int = 365,
        generator_type: str = "BOOTSTRAP",
        name: str = "",
        description: str = "",
        **kwargs
    ) -> MonteCarloExperiment:
        """
        Create a new Monte Carlo experiment.
        """
        gen_type = PathGeneratorType[generator_type] if isinstance(generator_type, str) else generator_type
        
        exp = MonteCarloExperiment(
            portfolio_simulation_id=portfolio_simulation_id,
            num_paths=num_paths,
            horizon_days=horizon_days,
            generator_type=gen_type,
            noise_std=kwargs.get("noise_std", 0.02),
            crash_probability=kwargs.get("crash_probability", 0.05),
            crash_severity_min=kwargs.get("crash_severity_min", -0.20),
            crash_severity_max=kwargs.get("crash_severity_max", -0.50),
            name=name or f"MC_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M')}",
            description=description
        )
        
        mc_repository.save_experiment(exp)
        print(f"[MonteCarloEngine] Created experiment: {exp.experiment_id}")
        
        return exp
    
    # ===========================================
    # Run Experiment
    # ===========================================
    
    def run_experiment(
        self,
        experiment_id: str,
        base_returns: Optional[List[float]] = None,
        initial_capital: float = 100000.0
    ) -> MonteCarloExperiment:
        """
        Run Monte Carlo experiment.
        
        Generates all paths and calculates metrics.
        """
        exp = mc_repository.get_experiment(experiment_id)
        if not exp:
            raise ValueError(f"Experiment {experiment_id} not found")
        
        # Update status
        exp.status = ExperimentStatus.RUNNING
        exp.started_at = datetime.now(timezone.utc)
        exp.completed_paths = 0
        mc_repository.save_experiment(exp)
        
        # Clear previous paths
        mc_repository.clear_paths(experiment_id)
        
        # Get or create base returns
        if base_returns is None:
            # Try to load from portfolio simulation
            base_returns = self._get_portfolio_returns(exp.portfolio_simulation_id)
        
        if not base_returns:
            # Use synthetic returns for testing
            base_returns = MonteCarloPathGenerator.create_synthetic_returns(
                mean=0.0005,
                std=0.02,
                num_days=252
            )
        
        # Create path generator
        generator = MonteCarloPathGenerator(
            base_returns=base_returns,
            initial_price=initial_capital
        )
        
        try:
            # Generate all paths
            for i in range(exp.num_paths):
                path_id = f"mcp_{experiment_id[:8]}_{i:04d}"
                
                # Generate market path
                market_path = generator.generate_path(
                    horizon_days=exp.horizon_days,
                    generator_type=exp.generator_type,
                    path_id=path_id,
                    noise_std=exp.noise_std,
                    crash_probability=exp.crash_probability,
                    crash_severity_min=exp.crash_severity_min,
                    crash_severity_max=exp.crash_severity_max
                )
                
                # Simulate portfolio on this path
                mc_path = self._simulate_portfolio_on_path(
                    experiment_id=experiment_id,
                    path_index=i,
                    market_path=market_path,
                    initial_capital=initial_capital
                )
                
                # Save path
                mc_repository.save_path(mc_path)
                
                # Update progress
                exp.completed_paths = i + 1
                
                # Log progress every 100 paths
                if (i + 1) % 100 == 0:
                    print(f"[MonteCarloEngine] Progress: {i + 1}/{exp.num_paths}")
            
            # Mark complete
            exp.status = ExperimentStatus.COMPLETED
            exp.completed_at = datetime.now(timezone.utc)
            
        except Exception as e:
            exp.status = ExperimentStatus.FAILED
            print(f"[MonteCarloEngine] Experiment failed: {e}")
        
        mc_repository.save_experiment(exp)
        return exp
    
    def _get_portfolio_returns(self, simulation_id: str) -> List[float]:
        """Get historical returns from portfolio simulation"""
        try:
            from ..portfolio.portfolio_repository import portfolio_repository
            
            states = portfolio_repository.get_state_history(simulation_id, 365)
            if len(states) < 2:
                return []
            
            states = sorted(states, key=lambda s: s.timestamp)
            returns = []
            
            for i in range(1, len(states)):
                prev_eq = states[i - 1].equity_usd
                curr_eq = states[i].equity_usd
                if prev_eq > 0:
                    ret = (curr_eq - prev_eq) / prev_eq
                    returns.append(ret)
            
            return returns
            
        except Exception as e:
            print(f"[MonteCarloEngine] Could not load portfolio returns: {e}")
            return []
    
    def _simulate_portfolio_on_path(
        self,
        experiment_id: str,
        path_index: int,
        market_path: MarketPath,
        initial_capital: float
    ) -> MonteCarloPath:
        """
        Simulate portfolio performance on a market path.
        
        For v1: Uses simple price-based simulation.
        Future: Can integrate with actual strategy signals.
        """
        # Calculate equity curve from price path
        equity_curve = market_path.prices
        
        initial_equity = equity_curve[0]
        final_equity = equity_curve[-1]
        
        # Calculate returns
        total_return_usd = final_equity - initial_equity
        total_return_pct = total_return_usd / initial_equity if initial_equity > 0 else 0
        
        # Calculate drawdown
        max_dd_pct, max_dd_usd = self._calculate_max_drawdown(equity_curve)
        
        # Calculate metrics
        daily_returns = market_path.returns
        sharpe = self._calculate_sharpe(daily_returns)
        sortino = self._calculate_sortino(daily_returns)
        volatility = self._calculate_volatility(daily_returns)
        
        # Calmar ratio
        calmar = (total_return_pct * 365 / len(daily_returns)) / max_dd_pct if max_dd_pct > 0 else 0
        
        # Sample equity curve (reduce storage)
        sampled_curve = self._sample_equity_curve(equity_curve, max_points=50)
        
        return MonteCarloPath(
            path_id=market_path.path_id,
            experiment_id=experiment_id,
            path_index=path_index,
            initial_equity=initial_equity,
            final_equity=final_equity,
            total_return_usd=total_return_usd,
            total_return_pct=total_return_pct,
            max_drawdown_pct=max_dd_pct,
            max_drawdown_usd=max_dd_usd,
            sharpe_ratio=sharpe,
            sortino_ratio=sortino,
            calmar_ratio=calmar,
            volatility=volatility,
            had_crash=market_path.had_crash,
            crash_magnitude=market_path.crash_magnitude,
            recovery_days=market_path.recovery_day - market_path.crash_day if market_path.had_crash else 0,
            equity_curve=sampled_curve
        )
    
    def _calculate_max_drawdown(self, equity_curve: List[float]) -> tuple:
        """Calculate maximum drawdown"""
        if not equity_curve:
            return 0.0, 0.0
        
        peak = equity_curve[0]
        max_dd_pct = 0.0
        max_dd_usd = 0.0
        
        for equity in equity_curve:
            if equity > peak:
                peak = equity
            
            dd_usd = peak - equity
            dd_pct = dd_usd / peak if peak > 0 else 0
            
            if dd_pct > max_dd_pct:
                max_dd_pct = dd_pct
                max_dd_usd = dd_usd
        
        return max_dd_pct, max_dd_usd
    
    def _calculate_sharpe(
        self,
        returns: List[float],
        risk_free_rate: float = 0.02 / 252
    ) -> float:
        """Calculate Sharpe ratio"""
        if len(returns) < 2:
            return 0.0
        
        mean_return = sum(returns) / len(returns)
        excess_return = mean_return - risk_free_rate
        
        std = self._calculate_std(returns)
        if std == 0:
            return 0.0
        
        return excess_return / std * math.sqrt(252)
    
    def _calculate_sortino(
        self,
        returns: List[float],
        risk_free_rate: float = 0.02 / 252
    ) -> float:
        """Calculate Sortino ratio"""
        if len(returns) < 2:
            return 0.0
        
        mean_return = sum(returns) / len(returns)
        excess_return = mean_return - risk_free_rate
        
        downside_returns = [min(0, r) for r in returns]
        downside_std = self._calculate_std(downside_returns)
        
        if downside_std == 0:
            return 0.0
        
        return excess_return / downside_std * math.sqrt(252)
    
    def _calculate_volatility(self, returns: List[float]) -> float:
        """Calculate annualized volatility"""
        if len(returns) < 2:
            return 0.0
        return self._calculate_std(returns) * math.sqrt(252)
    
    def _calculate_std(self, values: List[float]) -> float:
        """Calculate standard deviation"""
        if len(values) < 2:
            return 0.0
        mean = sum(values) / len(values)
        variance = sum((x - mean) ** 2 for x in values) / (len(values) - 1)
        return math.sqrt(variance)
    
    def _sample_equity_curve(
        self,
        curve: List[float],
        max_points: int = 50
    ) -> List[float]:
        """Sample equity curve to reduce storage"""
        if len(curve) <= max_points:
            return curve
        
        step = len(curve) // max_points
        sampled = [curve[i] for i in range(0, len(curve), step)]
        
        # Always include last point
        if sampled[-1] != curve[-1]:
            sampled.append(curve[-1])
        
        return sampled
    
    # ===========================================
    # Get Results
    # ===========================================
    
    def get_experiment(self, experiment_id: str) -> Optional[MonteCarloExperiment]:
        """Get experiment by ID"""
        return mc_repository.get_experiment(experiment_id)
    
    def get_paths(
        self,
        experiment_id: str,
        limit: int = 100
    ) -> List[MonteCarloPath]:
        """Get paths for experiment"""
        paths = mc_repository.get_paths(experiment_id)
        return paths[:limit]
    
    def list_experiments(self, limit: int = 50) -> List[MonteCarloExperiment]:
        """List all experiments"""
        return mc_repository.list_experiments(limit)
    
    # ===========================================
    # Health
    # ===========================================
    
    def get_health(self) -> Dict[str, Any]:
        """Get service health"""
        return {
            "service": "MonteCarloSimulationEngine",
            "status": "healthy",
            "version": "s5",
            "experiments_count": len(mc_repository._experiments)
        }


# Global singleton
mc_simulation_engine = MonteCarloSimulationEngine()
