"""
PHASE 10 - Capital Allocator
=============================
Unified capital allocation combining all engines.

Combines:
- Risk parity
- Volatility targeting
- Drawdown control
- Correlation control
"""

from typing import List, Dict, Optional
from datetime import datetime, timezone

from .portfolio_types import (
    StrategyMetrics, StrategyAllocation, PortfolioState,
    AllocationMethod, DrawdownState, VolatilityRegime,
    RebalanceAction, DEFAULT_PORTFOLIO_CONFIG
)
from .risk_parity_engine import RiskParityEngine
from .volatility_targeting_engine import VolatilityTargetingEngine
from .drawdown_control_engine import DrawdownControlEngine
from .strategy_correlation_engine import StrategyCorrelationEngine


class CapitalAllocator:
    """
    Unified Capital Allocator
    
    Combines risk parity, volatility targeting, drawdown control,
    and correlation control to produce optimal allocations.
    """
    
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or DEFAULT_PORTFOLIO_CONFIG
        
        # Initialize engines
        self.risk_parity = RiskParityEngine(config)
        self.vol_targeting = VolatilityTargetingEngine(config)
        self.drawdown_control = DrawdownControlEngine(config)
        self.correlation = StrategyCorrelationEngine(config)
        
        # History
        self.allocation_history: List[Dict[str, StrategyAllocation]] = []
        self.state_history: List[PortfolioState] = []
        self.max_history = 100
    
    def calculate_allocations(
        self,
        strategies: List[StrategyMetrics],
        current_equity: float,
        portfolio_volatility: float,
        method: AllocationMethod = AllocationMethod.COMPOSITE,
        strategy_returns: Optional[Dict[str, List[float]]] = None
    ) -> Dict[str, StrategyAllocation]:
        """
        Calculate optimal capital allocations.
        
        Args:
            strategies: List of strategy metrics
            current_equity: Current portfolio equity
            portfolio_volatility: Current portfolio volatility
            method: Allocation method to use
            strategy_returns: Optional strategy returns for correlation
            
        Returns:
            Dict of strategy_id -> StrategyAllocation
        """
        now = datetime.now(timezone.utc)
        
        if not strategies:
            return {}
        
        # Step 1: Calculate base allocations (risk parity)
        risk_parity_result = self.risk_parity.calculate_risk_parity(
            strategies,
            correlation_matrix=None  # Will calculate correlation separately
        )
        base_allocations = risk_parity_result.allocations
        
        # Step 2: Calculate correlation adjustments
        corr_matrix = self.correlation.calculate_correlation_matrix(
            strategies, strategy_returns
        )
        corr_adjusted = self.correlation.get_allocation_adjustment(
            base_allocations, corr_matrix
        )
        
        # Step 3: Apply volatility targeting
        vol_target = self.vol_targeting.calculate_volatility_scaling(
            portfolio_volatility
        )
        vol_scalar = vol_target.volatility_scalar
        
        # Step 4: Apply drawdown control
        dd_control = self.drawdown_control.analyze_drawdown(current_equity)
        dd_factor = dd_control.risk_reduction_factor
        
        # Step 5: Combine adjustments
        if method == AllocationMethod.COMPOSITE:
            final_allocations = self._composite_allocation(
                strategies, corr_adjusted, vol_scalar, dd_factor
            )
        elif method == AllocationMethod.RISK_PARITY:
            final_allocations = base_allocations
        elif method == AllocationMethod.VOLATILITY_SCALED:
            final_allocations = {
                sid: w * vol_scalar for sid, w in base_allocations.items()
            }
        else:
            final_allocations = corr_adjusted
        
        # Normalize final allocations
        total = sum(final_allocations.values())
        if total > 0:
            final_allocations = {sid: w / total for sid, w in final_allocations.items()}
        
        # Build StrategyAllocation objects
        result = {}
        for s in strategies:
            sid = s.strategy_id
            target_weight = final_allocations.get(sid, 0)
            current_weight = s.weight
            
            delta = target_weight - current_weight
            risk_contrib = risk_parity_result.risk_contributions.get(sid, 0)
            
            needs_adjustment = abs(delta) > self.config["rebalance_threshold"]
            reason = ""
            if needs_adjustment:
                if delta > 0:
                    reason = f"Increase allocation by {delta*100:.1f}%"
                else:
                    reason = f"Decrease allocation by {abs(delta)*100:.1f}%"
            
            result[sid] = StrategyAllocation(
                strategy_id=sid,
                name=s.name,
                target_weight=target_weight,
                current_weight=current_weight,
                delta=delta,
                risk_contribution=risk_contrib,
                marginal_risk=s.volatility * target_weight,
                min_weight=self.config["min_strategy_weight"],
                max_weight=self.config["max_strategy_weight"],
                needs_adjustment=needs_adjustment,
                adjustment_reason=reason
            )
        
        # Save to history
        self.allocation_history.append(result)
        if len(self.allocation_history) > self.max_history:
            self.allocation_history = self.allocation_history[-self.max_history:]
        
        return result
    
    def _composite_allocation(
        self,
        strategies: List[StrategyMetrics],
        corr_adjusted: Dict[str, float],
        vol_scalar: float,
        dd_factor: float
    ) -> Dict[str, float]:
        """Calculate composite allocation combining all factors."""
        result = {}
        
        # Overall scaling
        overall_scale = vol_scalar * dd_factor
        
        for s in strategies:
            sid = s.strategy_id
            base_weight = corr_adjusted.get(sid, 0)
            
            # Apply overall scaling
            adjusted_weight = base_weight * overall_scale
            
            # Apply constraints
            min_w = self.config["min_strategy_weight"]
            max_w = self.config["max_strategy_weight"]
            adjusted_weight = max(0, min(max_w, adjusted_weight))
            
            # Only apply minimum if strategy was allocated
            if base_weight > 0 and adjusted_weight < min_w:
                adjusted_weight = min_w
            
            result[sid] = adjusted_weight
        
        return result
    
    def get_portfolio_state(
        self,
        strategies: List[StrategyMetrics],
        current_equity: float,
        portfolio_volatility: float
    ) -> PortfolioState:
        """
        Get complete portfolio state snapshot.
        """
        now = datetime.now(timezone.utc)
        
        # Get latest from each engine
        vol_result = self.vol_targeting.calculate_volatility_scaling(
            portfolio_volatility
        )
        dd_result = self.drawdown_control.analyze_drawdown(current_equity)
        
        # Calculate allocations
        allocations = self.calculate_allocations(
            strategies, current_equity, portfolio_volatility
        )
        
        # Build allocation dict
        alloc_dict = {sid: a.target_weight for sid, a in allocations.items()}
        
        # Calculate risk budget used
        risk_budget_used = sum(
            a.risk_contribution for a in allocations.values()
        )
        
        # Determine rebalance recommendation
        needs_rebalance = any(a.needs_adjustment for a in allocations.values())
        if dd_result.drawdown_state == DrawdownState.EMERGENCY:
            rebal_rec = RebalanceAction.URGENT_REBALANCE
        elif dd_result.drawdown_state == DrawdownState.CRITICAL:
            rebal_rec = RebalanceAction.REDUCE_EXPOSURE
        elif needs_rebalance:
            rebal_rec = RebalanceAction.REBALANCE_REQUIRED
        else:
            rebal_rec = RebalanceAction.NO_ACTION
        
        # Calculate portfolio health score
        health_score = self._calculate_health_score(
            dd_result, vol_result, risk_budget_used
        )
        
        state = PortfolioState(
            timestamp=now,
            portfolio_volatility=portfolio_volatility,
            target_volatility=self.config["target_volatility"],
            portfolio_drawdown=dd_result.current_drawdown,
            risk_budget_used=risk_budget_used,
            capital_deployment=dd_result.capital_deployment,
            strategy_allocations=alloc_dict,
            drawdown_state=dd_result.drawdown_state,
            volatility_regime=vol_result.volatility_regime,
            rebalance_recommendation=rebal_rec,
            portfolio_health_score=health_score
        )
        
        # Save to history
        self.state_history.append(state)
        if len(self.state_history) > self.max_history:
            self.state_history = self.state_history[-self.max_history:]
        
        return state
    
    def _calculate_health_score(
        self,
        dd: 'DrawdownControl',
        vol: 'VolatilityTarget',
        risk_used: float
    ) -> float:
        """Calculate overall portfolio health score (0-1)."""
        score = 1.0
        
        # Drawdown penalty
        dd_penalties = {
            DrawdownState.NORMAL: 0,
            DrawdownState.CAUTION: 0.1,
            DrawdownState.WARNING: 0.25,
            DrawdownState.CRITICAL: 0.4,
            DrawdownState.EMERGENCY: 0.6
        }
        score -= dd_penalties.get(dd.drawdown_state, 0)
        
        # Volatility deviation penalty
        vol_dev = abs(vol.current_volatility - vol.target_volatility) / vol.target_volatility
        score -= min(0.2, vol_dev * 0.5)
        
        # Risk budget penalty (too high or too low)
        if risk_used > 1.0:
            score -= (risk_used - 1.0) * 0.3
        elif risk_used < 0.5:
            score -= (0.5 - risk_used) * 0.2
        
        return max(0, min(1, score))
    
    def get_allocation_summary(self) -> Dict:
        """Get summary of current allocations."""
        if not self.allocation_history:
            return {"summary": "NO_ALLOCATIONS"}
        
        recent = self.allocation_history[-1]
        
        allocations = {sid: round(a.target_weight, 4) for sid, a in recent.items()}
        adjustments_needed = sum(1 for a in recent.values() if a.needs_adjustment)
        
        return {
            "allocations": allocations,
            "adjustments_needed": adjustments_needed,
            "total_allocated": round(sum(allocations.values()), 4)
        }
    
    def get_state_summary(self) -> Dict:
        """Get summary of portfolio state."""
        if not self.state_history:
            return {"summary": "NO_STATE"}
        
        recent = self.state_history[-1]
        
        return {
            "portfolio_volatility": round(recent.portfolio_volatility, 4),
            "target_volatility": round(recent.target_volatility, 4),
            "drawdown": round(recent.portfolio_drawdown, 4),
            "drawdown_state": recent.drawdown_state.value,
            "volatility_regime": recent.volatility_regime.value,
            "capital_deployment": round(recent.capital_deployment, 4),
            "health_score": round(recent.portfolio_health_score, 3),
            "rebalance_recommendation": recent.rebalance_recommendation.value
        }
