"""
PHASE 10 - Risk Parity Engine
==============================
Allocates capital so each strategy contributes equal risk.

Example:
  Strategy A volatility = 10%
  Strategy B volatility = 20%
  
  Risk Parity Allocation:
    A = 66% (higher allocation to lower vol)
    B = 34% (lower allocation to higher vol)
"""

import math
from typing import List, Dict, Optional
from datetime import datetime, timezone

from .portfolio_types import (
    StrategyMetrics, RiskParityResult, DEFAULT_PORTFOLIO_CONFIG
)


class RiskParityEngine:
    """
    Risk Parity Allocation Engine
    
    Ensures each strategy contributes equally to portfolio risk,
    regardless of individual strategy volatility.
    """
    
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or DEFAULT_PORTFOLIO_CONFIG
        self.history: List[RiskParityResult] = []
        self.max_history = 100
    
    def calculate_risk_parity(
        self,
        strategies: List[StrategyMetrics],
        correlation_matrix: Optional[Dict[str, Dict[str, float]]] = None
    ) -> RiskParityResult:
        """
        Calculate risk parity allocations.
        
        Args:
            strategies: List of strategy metrics
            correlation_matrix: Optional correlation matrix between strategies
            
        Returns:
            RiskParityResult with allocations
        """
        now = datetime.now(timezone.utc)
        
        if not strategies:
            return self._empty_result(now)
        
        # Filter active strategies
        active = [s for s in strategies if s.active and s.volatility > 0]
        
        if not active:
            return self._empty_result(now)
        
        # If no correlation matrix, assume uncorrelated
        if correlation_matrix is None:
            correlation_matrix = self._create_identity_correlation(active)
        
        # Calculate inverse volatility weights (simple risk parity)
        inv_vols = {s.strategy_id: 1.0 / s.volatility for s in active}
        total_inv_vol = sum(inv_vols.values())
        
        # Initial weights from inverse volatility
        weights = {sid: iv / total_inv_vol for sid, iv in inv_vols.items()}
        
        # Iterative refinement using Newton-Raphson
        weights, converged, iterations = self._refine_weights(
            active, weights, correlation_matrix
        )
        
        # Apply constraints
        weights = self._apply_constraints(weights)
        
        # Calculate risk contributions
        risk_contribs = self._calculate_risk_contributions(
            active, weights, correlation_matrix
        )
        
        # Calculate total portfolio risk
        portfolio_risk = self._calculate_portfolio_risk(
            active, weights, correlation_matrix
        )
        
        # Calculate risk concentration (Herfindahl index)
        risk_concentration = sum(rc ** 2 for rc in risk_contribs.values())
        
        result = RiskParityResult(
            timestamp=now,
            allocations=weights,
            total_portfolio_risk=portfolio_risk,
            risk_contributions=risk_contribs,
            risk_concentration=risk_concentration,
            converged=converged,
            iterations=iterations
        )
        
        self._add_to_history(result)
        
        return result
    
    def _refine_weights(
        self,
        strategies: List[StrategyMetrics],
        initial_weights: Dict[str, float],
        correlation_matrix: Dict[str, Dict[str, float]],
        max_iterations: int = 50,
        tolerance: float = 1e-6
    ) -> tuple:
        """Iteratively refine weights to achieve risk parity."""
        weights = initial_weights.copy()
        n = len(strategies)
        target_risk = 1.0 / n  # Equal risk contribution
        
        converged = False
        iterations = 0
        
        for iteration in range(max_iterations):
            iterations = iteration + 1
            
            # Calculate current risk contributions
            risk_contribs = self._calculate_risk_contributions(
                strategies, weights, correlation_matrix
            )
            
            # Check convergence
            max_deviation = max(
                abs(rc - target_risk) for rc in risk_contribs.values()
            )
            
            if max_deviation < tolerance:
                converged = True
                break
            
            # Adjust weights based on risk contribution deviation
            new_weights = {}
            for s in strategies:
                sid = s.strategy_id
                current_rc = risk_contribs.get(sid, target_risk)
                
                # Adjust weight: decrease if contributing too much risk
                if current_rc > 0:
                    adjustment = target_risk / current_rc
                else:
                    adjustment = 1.0
                
                # Damped adjustment to prevent oscillation
                damping = 0.3
                new_weights[sid] = weights[sid] * (1 - damping + damping * adjustment)
            
            # Normalize weights
            total = sum(new_weights.values())
            weights = {sid: w / total for sid, w in new_weights.items()}
        
        return weights, converged, iterations
    
    def _calculate_risk_contributions(
        self,
        strategies: List[StrategyMetrics],
        weights: Dict[str, float],
        correlation_matrix: Dict[str, Dict[str, float]]
    ) -> Dict[str, float]:
        """Calculate risk contribution of each strategy."""
        n = len(strategies)
        if n == 0:
            return {}
        
        # Calculate marginal contributions to portfolio variance
        marginal_contribs = {}
        portfolio_var = 0.0
        
        for i, si in enumerate(strategies):
            wi = weights.get(si.strategy_id, 0)
            
            # Calculate contribution to portfolio variance
            contrib = 0.0
            for j, sj in enumerate(strategies):
                wj = weights.get(sj.strategy_id, 0)
                corr = correlation_matrix.get(si.strategy_id, {}).get(sj.strategy_id, 0)
                if i == j:
                    corr = 1.0
                
                contrib += wj * si.volatility * sj.volatility * corr
            
            marginal_contribs[si.strategy_id] = wi * contrib
            portfolio_var += wi * contrib
        
        # Normalize to get risk contribution percentages
        if portfolio_var > 0:
            risk_contribs = {
                sid: mc / portfolio_var for sid, mc in marginal_contribs.items()
            }
        else:
            risk_contribs = {sid: 1.0 / n for sid in marginal_contribs.keys()}
        
        return risk_contribs
    
    def _calculate_portfolio_risk(
        self,
        strategies: List[StrategyMetrics],
        weights: Dict[str, float],
        correlation_matrix: Dict[str, Dict[str, float]]
    ) -> float:
        """Calculate total portfolio volatility."""
        variance = 0.0
        
        for si in strategies:
            wi = weights.get(si.strategy_id, 0)
            
            for sj in strategies:
                wj = weights.get(sj.strategy_id, 0)
                
                if si.strategy_id == sj.strategy_id:
                    corr = 1.0
                else:
                    corr = correlation_matrix.get(si.strategy_id, {}).get(sj.strategy_id, 0)
                
                variance += wi * wj * si.volatility * sj.volatility * corr
        
        return math.sqrt(max(0, variance))
    
    def _apply_constraints(self, weights: Dict[str, float]) -> Dict[str, float]:
        """Apply min/max weight constraints."""
        max_weight = self.config["max_strategy_weight"]
        min_weight = self.config["min_strategy_weight"]
        
        constrained = {}
        
        for sid, w in weights.items():
            constrained[sid] = max(min_weight, min(max_weight, w))
        
        # Renormalize
        total = sum(constrained.values())
        if total > 0:
            constrained = {sid: w / total for sid, w in constrained.items()}
        
        return constrained
    
    def _create_identity_correlation(
        self,
        strategies: List[StrategyMetrics]
    ) -> Dict[str, Dict[str, float]]:
        """Create identity correlation matrix (uncorrelated strategies)."""
        matrix = {}
        for si in strategies:
            matrix[si.strategy_id] = {}
            for sj in strategies:
                if si.strategy_id == sj.strategy_id:
                    matrix[si.strategy_id][sj.strategy_id] = 1.0
                else:
                    matrix[si.strategy_id][sj.strategy_id] = 0.0
        return matrix
    
    def _empty_result(self, timestamp: datetime) -> RiskParityResult:
        """Return empty result."""
        return RiskParityResult(
            timestamp=timestamp,
            allocations={},
            total_portfolio_risk=0,
            risk_contributions={},
            risk_concentration=0,
            converged=True,
            iterations=0
        )
    
    def _add_to_history(self, result: RiskParityResult):
        """Add result to history."""
        self.history.append(result)
        if len(self.history) > self.max_history:
            self.history = self.history[-self.max_history:]
    
    def get_allocation_summary(self) -> Dict:
        """Get summary of risk parity allocations."""
        if not self.history:
            return {"summary": "NO_HISTORY"}
        
        recent = self.history[-1]
        
        return {
            "allocations": recent.allocations,
            "portfolio_risk": round(recent.total_portfolio_risk, 4),
            "risk_concentration": round(recent.risk_concentration, 4),
            "converged": recent.converged,
            "timestamp": recent.timestamp.isoformat() if recent.timestamp else None
        }
