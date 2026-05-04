"""Portfolio Optimizer — V4 Greedy Optimizer

Selects optimal portfolio based on objective function:
- Maximize alpha
- Minimize portfolio volatility
- Minimize execution cost
- Minimize concentration
"""

import numpy as np
import logging
from typing import List, Dict, Any

from .portfolio_math import portfolio_volatility

logger = logging.getLogger(__name__)


class PortfolioOptimizer:
    """Greedy portfolio optimizer.
    
    Objective function:
    maximize: alpha - λ1*pvol - λ2*exec_cost - λ3*concentration
    """
    
    def __init__(
        self,
        vol_penalty: float = 0.35,
        exec_penalty: float = 0.15,
        concentration_penalty: float = 0.20
    ):
        """
        Args:
            vol_penalty: Weight for portfolio volatility penalty
            exec_penalty: Weight for execution cost penalty
            concentration_penalty: Weight for concentration penalty
        """
        self.vol_penalty = vol_penalty
        self.exec_penalty = exec_penalty
        self.concentration_penalty = concentration_penalty
    
    def _candidate_objective(
        self,
        candidate: Dict[str, Any],
        selected: List[Dict[str, Any]],
        symbols: List[str],
        cov: np.ndarray,
    ) -> float:
        """
        Calculate objective value if we add this candidate.
        
        Args:
            candidate: Candidate to evaluate
            selected: Already selected candidates
            symbols: All symbols in covariance matrix
            cov: Covariance matrix
        
        Returns:
            Objective value (higher is better)
        """
        # Alpha (score)
        alpha = float(candidate.get("score", 0.0))
        
        # Execution cost
        exec_quality = candidate.get("execution_quality", {})
        exec_cost = float(exec_quality.get("slippage_bps", 0.0)) / 100.0
        
        # Concentration
        concentration = float(candidate.get("concentration_score", 0.0))
        
        # Portfolio volatility (if we add this candidate)
        temp_portfolio = selected + [candidate]
        
        # Build weight vector
        weights = []
        for s in symbols:
            weight = 0.0
            for d in temp_portfolio:
                if d["symbol"] == s:
                    weight += float(d.get("size_usd", 0.0))
            weights.append(weight)
        
        weights = np.array(weights, dtype=float)
        total = weights.sum()
        
        if total > 0:
            weights = weights / total  # Normalize
        
        # Calculate portfolio vol
        pvol = portfolio_volatility(weights, cov) if cov.size > 0 else 0.0
        
        # Objective function
        objective = (
            alpha
            - self.vol_penalty * pvol
            - self.exec_penalty * exec_cost
            - self.concentration_penalty * concentration
        )
        
        return objective
    
    def optimize(
        self,
        candidates: List[Dict[str, Any]],
        symbols: List[str],
        cov: np.ndarray,
        max_positions: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Select optimal portfolio using greedy algorithm.
        
        Args:
            candidates: List of candidate trades (from AllocatorV3)
            symbols: Symbol list (must match cov matrix)
            cov: Covariance matrix
            max_positions: Max number of positions
        
        Returns:
            Optimized list of trades
        """
        logger.info(
            f"[Optimizer] Starting optimization: {len(candidates)} candidates, "
            f"{len(symbols)} symbols, max_positions={max_positions}"
        )
        
        selected = []
        remaining = candidates[:]
        
        iteration = 0
        while remaining and len(selected) < max_positions:
            iteration += 1
            
            # Score all remaining candidates
            scored = []
            for c in remaining:
                obj = self._candidate_objective(c, selected, symbols, cov)
                scored.append((c, obj))
            
            # Sort by objective (descending)
            scored.sort(key=lambda x: x[1], reverse=True)
            
            best_candidate, best_obj = scored[0]
            
            # If best objective is negative, stop
            if best_obj <= 0:
                logger.info(
                    f"[Optimizer] Stopping: best objective <= 0 ({best_obj:.4f}) at iteration {iteration}"
                )
                break
            
            # Add to selected
            best_candidate["portfolio_objective"] = round(best_obj, 6)
            selected.append(best_candidate)
            
            # Remove from remaining
            remaining = [x for x in remaining if x["symbol"] != best_candidate["symbol"]]
            
            logger.debug(
                f"[Optimizer] Iteration {iteration}: Selected {best_candidate['symbol']} "
                f"with objective {best_obj:.4f}"
            )
        
        logger.info(
            f"[Optimizer] Optimization complete: {len(selected)} positions selected "
            f"from {len(candidates)} candidates in {iteration} iterations"
        )
        
        return selected
