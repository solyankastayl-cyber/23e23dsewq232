"""
Risk Budget Engine

PHASE 38.5 — Risk Budget Engine

Core engine for risk-based capital allocation.

Key features:
1. Risk budget distribution (not capital)
2. Volatility targeting: position_size = risk_budget / asset_volatility
3. Risk contribution: weight * volatility * correlation_adjustment
4. Integration with Portfolio Manager and Execution Brain

Professional fund approach:
- Allocate RISK, not capital
- Equal risk != equal capital
- Volatility-adjusted position sizing
"""

import math
import hashlib
from typing import Optional, Dict, List, Tuple
from datetime import datetime, timezone
from collections import defaultdict

from .risk_budget_types import (
    RiskBudget,
    PositionRisk,
    PortfolioRiskBudget,
    RiskBudgetAllocationRequest,
    VolatilityTargetRequest,
    VolatilityTargetResponse,
    RiskContributionResult,
    RiskRebalanceResult,
    RiskBudgetHistoryEntry,
    DEFAULT_RISK_BUDGETS,
    PORTFOLIO_RISK_LIMITS,
    VOLATILITY_PARAMS,
    RISK_CONTRIBUTION_LIMITS,
)


# ══════════════════════════════════════════════════════════════
# Risk Budget Engine
# ══════════════════════════════════════════════════════════════

class RiskBudgetEngine:
    """
    Risk Budget Engine — PHASE 38.5
    
    Manages risk-based capital allocation.
    
    Key formulas:
    - position_size = risk_budget / asset_volatility
    - risk_contribution = weight * volatility * correlation_adjustment
    - Σ risk_contribution ≤ portfolio_risk_limit
    """
    
    def __init__(self, total_capital: float = 1000000.0):
        self._capital = total_capital
        self._strategy_budgets: Dict[str, RiskBudget] = {}
        self._position_risks: Dict[str, PositionRisk] = {}
        self._volatility_cache: Dict[str, float] = {}
        self._correlation_cache: Dict[str, Dict[str, float]] = {}
        self._history: List[RiskBudgetHistoryEntry] = []
        
        # Target volatility
        self._target_volatility = VOLATILITY_PARAMS["TARGET_VOLATILITY"]
        
        # Initialize default strategy budgets
        self._init_default_budgets()
    
    def _init_default_budgets(self):
        """Initialize default risk budgets for strategies."""
        for strategy, risk_target in DEFAULT_RISK_BUDGETS.items():
            self._strategy_budgets[strategy] = RiskBudget(
                strategy=strategy,
                strategy_type=self._map_strategy_type(strategy),
                risk_target=risk_target,
            )
    
    def _map_strategy_type(self, strategy: str) -> str:
        """Map strategy name to type."""
        mapping = {
            "TREND_FOLLOWING": "TREND_FOLLOWING",
            "MEAN_REVERSION": "MEAN_REVERSION",
            "BREAKOUT": "BREAKOUT",
            "VOLATILITY": "VOLATILITY",
            "MOMENTUM": "MOMENTUM",
            "STATISTICAL_ARB": "STATISTICAL_ARB",
        }
        return mapping.get(strategy, "MOMENTUM")
    
    # ═══════════════════════════════════════════════════════════
    # 1. Risk Budget Allocation
    # ═══════════════════════════════════════════════════════════
    
    def allocate_risk_budgets(
        self,
        request: RiskBudgetAllocationRequest,
    ) -> Dict[str, RiskBudget]:
        """
        Allocate risk budgets to strategies.
        
        Methods:
        - EQUAL_RISK: Equal risk per strategy
        - VOLATILITY_WEIGHTED: Inverse volatility weighting
        - PERFORMANCE_WEIGHTED: Based on recent performance
        - CUSTOM: Custom allocations
        """
        n_strategies = len(request.strategies)
        
        if n_strategies == 0:
            return {}
        
        allocations: Dict[str, float] = {}
        
        if request.method == "EQUAL_RISK":
            # Equal risk allocation
            equal_allocation = 1.0 / n_strategies
            for strategy in request.strategies:
                allocations[strategy] = min(
                    equal_allocation,
                    request.max_single_strategy_risk
                )
        
        elif request.method == "VOLATILITY_WEIGHTED":
            # Inverse volatility weighting
            volatilities = {}
            total_inv_vol = 0.0
            
            for strategy in request.strategies:
                vol = self._get_strategy_volatility(strategy)
                volatilities[strategy] = vol
                total_inv_vol += 1 / max(vol, 0.01)
            
            for strategy in request.strategies:
                inv_vol = 1 / max(volatilities[strategy], 0.01)
                allocations[strategy] = min(
                    inv_vol / total_inv_vol,
                    request.max_single_strategy_risk
                )
        
        elif request.method == "PERFORMANCE_WEIGHTED":
            # Performance-weighted allocation
            performances = {}
            total_perf = 0.0
            
            for strategy in request.strategies:
                perf = self._get_strategy_performance(strategy)
                performances[strategy] = max(perf, 0.1)  # Min 10%
                total_perf += performances[strategy]
            
            for strategy in request.strategies:
                allocations[strategy] = min(
                    performances[strategy] / total_perf,
                    request.max_single_strategy_risk
                )
        
        elif request.method == "CUSTOM" and request.custom_allocations:
            # Custom allocations
            total = sum(request.custom_allocations.values())
            for strategy in request.strategies:
                raw = request.custom_allocations.get(strategy, 0.0)
                allocations[strategy] = min(
                    raw / total if total > 0 else 0.0,
                    request.max_single_strategy_risk
                )
        
        # Normalize to ensure sum = 1
        total_alloc = sum(allocations.values())
        if total_alloc > 0:
            for strategy in allocations:
                allocations[strategy] /= total_alloc
        
        # Apply minimum threshold
        for strategy in allocations:
            if allocations[strategy] < request.min_single_strategy_risk:
                allocations[strategy] = request.min_single_strategy_risk
        
        # Renormalize after applying minimums
        total_alloc = sum(allocations.values())
        if total_alloc > 1:
            for strategy in allocations:
                allocations[strategy] /= total_alloc
        
        # Create/update risk budgets
        for strategy, risk_target in allocations.items():
            if strategy not in self._strategy_budgets:
                self._strategy_budgets[strategy] = RiskBudget(
                    strategy=strategy,
                    strategy_type=self._map_strategy_type(strategy),
                    risk_target=risk_target,
                )
            else:
                self._strategy_budgets[strategy].risk_target = risk_target
            
            # Calculate max capital from risk budget
            self._strategy_budgets[strategy].max_capital = self._calculate_max_capital_from_risk(
                risk_target,
                self._get_strategy_volatility(strategy),
            )
        
        return self._strategy_budgets.copy()
    
    def get_strategy_risk_budget(self, strategy: str) -> Optional[RiskBudget]:
        """Get risk budget for a specific strategy."""
        return self._strategy_budgets.get(strategy)
    
    def get_all_risk_budgets(self) -> Dict[str, RiskBudget]:
        """Get all strategy risk budgets."""
        return self._strategy_budgets.copy()
    
    def set_strategy_risk_budget(
        self,
        strategy: str,
        risk_target: float,
        volatility: Optional[float] = None,
    ) -> RiskBudget:
        """Set risk budget for a strategy."""
        # Validate
        risk_target = min(risk_target, PORTFOLIO_RISK_LIMITS["MAX_STRATEGY_RISK"])
        risk_target = max(risk_target, PORTFOLIO_RISK_LIMITS["MIN_STRATEGY_RISK"])
        
        vol = volatility if volatility else self._get_strategy_volatility(strategy)
        
        budget = RiskBudget(
            strategy=strategy,
            strategy_type=self._map_strategy_type(strategy),
            risk_target=risk_target,
            volatility=vol,
            max_capital=self._calculate_max_capital_from_risk(risk_target, vol),
        )
        
        self._strategy_budgets[strategy] = budget
        return budget
    
    # ═══════════════════════════════════════════════════════════
    # 2. Volatility Targeting
    # ═══════════════════════════════════════════════════════════
    
    def compute_volatility_target_size(
        self,
        request: VolatilityTargetRequest,
    ) -> VolatilityTargetResponse:
        """
        Compute volatility-targeted position size.
        
        Formula:
        vol_scaled_size = base_size * (target_vol / asset_vol)
        
        This ensures each position contributes equally to risk.
        """
        symbol = request.symbol.upper()
        strategy = request.strategy
        
        # Get asset volatility
        asset_vol = self._get_asset_volatility(symbol)
        asset_vol_annualized = asset_vol * math.sqrt(252)
        
        # Target volatility
        target_vol = request.target_volatility or self._target_volatility
        
        # Volatility ratio
        vol_ratio = target_vol / max(asset_vol_annualized, VOLATILITY_PARAMS["MIN_VOLATILITY"])
        vol_ratio = min(vol_ratio, 2.0)  # Cap at 2x
        
        # Vol-scaled size
        vol_scaled_size = request.base_size_usd * vol_ratio
        size_reduction = 1 - (vol_scaled_size / request.base_size_usd) if request.base_size_usd > 0 else 0
        
        # Check against strategy risk budget
        budget = self._strategy_budgets.get(strategy)
        
        if budget:
            remaining_budget = budget.risk_target - budget.risk_used
            max_from_budget = self._calculate_max_capital_from_risk(remaining_budget, asset_vol_annualized)
            within_budget = vol_scaled_size <= max_from_budget
            
            if not within_budget:
                vol_scaled_size = max_from_budget
        else:
            remaining_budget = 0.0
            within_budget = True
        
        # Final size after all adjustments
        final_size = max(vol_scaled_size, 0.0)
        
        # Determine reason
        if vol_ratio < 1.0:
            reason = f"Reduced {(1-vol_ratio)*100:.0f}% due to high volatility ({asset_vol_annualized*100:.1f}% vs {target_vol*100:.0f}% target)"
        elif vol_ratio > 1.0:
            reason = f"Scaled up due to low volatility (capped at {vol_ratio:.1f}x)"
        else:
            reason = "On target volatility"
        
        if not within_budget:
            reason += f" (capped by risk budget: {remaining_budget*100:.1f}% remaining)"
        
        return VolatilityTargetResponse(
            symbol=symbol,
            strategy=strategy,
            base_size_usd=request.base_size_usd,
            asset_volatility=round(asset_vol, 6),
            asset_volatility_annualized=round(asset_vol_annualized, 4),
            target_volatility=target_vol,
            volatility_ratio=round(vol_ratio, 4),
            vol_scaled_size_usd=round(vol_scaled_size, 2),
            size_reduction_pct=round(max(size_reduction, 0), 4),
            strategy_risk_budget=budget.risk_target if budget else 0.0,
            risk_budget_remaining=remaining_budget if budget else 0.0,
            within_budget=within_budget,
            final_size_usd=round(final_size, 2),
            reason=reason,
        )
    
    def get_vol_scale_factor(self) -> float:
        """
        Get global volatility scale factor.
        
        Factor = target_vol / current_portfolio_vol
        
        Used to scale all positions.
        """
        current_vol = self._calculate_portfolio_volatility()
        
        if current_vol < VOLATILITY_PARAMS["MIN_VOLATILITY"]:
            return 1.0
        
        factor = self._target_volatility / current_vol
        
        # Cap between 0.5x and 2.0x
        return max(min(factor, 2.0), 0.5)
    
    # ═══════════════════════════════════════════════════════════
    # 3. Risk Contribution Calculation
    # ═══════════════════════════════════════════════════════════
    
    def calculate_risk_contribution(
        self,
        symbol: str,
        strategy: str,
        position_size_usd: float,
    ) -> RiskContributionResult:
        """
        Calculate risk contribution of a position.
        
        Formula:
        risk_contribution = weight * volatility * correlation_adjustment
        
        Where:
        - weight = position_size / total_capital
        - volatility = asset volatility (annualized)
        - correlation_adjustment = sqrt(1 + avg_correlation)
        """
        symbol = symbol.upper()
        
        # Weight
        weight = position_size_usd / self._capital if self._capital > 0 else 0
        
        # Asset volatility
        vol = self._get_asset_volatility(symbol)
        vol_annualized = vol * math.sqrt(252)
        
        # Correlation adjustment
        avg_corr = self._get_avg_correlation_with_portfolio(symbol)
        corr_adj = math.sqrt(1 + max(avg_corr, 0))  # Penalize positive correlation
        
        # Risk contribution
        risk_contribution = weight * vol_annualized * corr_adj
        
        # Portfolio total risk (for percentage)
        total_risk = self._calculate_portfolio_risk()
        risk_contribution_pct = risk_contribution / total_risk if total_risk > 0 else 0
        
        # Marginal risk (derivative of portfolio risk w.r.t. position)
        marginal_risk = vol_annualized * corr_adj
        
        # Impact on portfolio risk
        impact = risk_contribution / (total_risk + risk_contribution) if (total_risk + risk_contribution) > 0 else 0
        
        return RiskContributionResult(
            symbol=symbol,
            strategy=strategy,
            weight=round(weight, 4),
            volatility=round(vol_annualized, 4),
            correlation_adjustment=round(corr_adj, 4),
            risk_contribution=round(risk_contribution, 6),
            risk_contribution_pct=round(risk_contribution_pct, 4),
            marginal_risk=round(marginal_risk, 6),
            impact_on_portfolio_risk=round(impact, 4),
        )
    
    def add_position_risk(
        self,
        symbol: str,
        strategy: str,
        position_size_usd: float,
    ) -> PositionRisk:
        """Add position and track its risk contribution."""
        symbol = symbol.upper()
        
        # Calculate contribution
        contrib = self.calculate_risk_contribution(symbol, strategy, position_size_usd)
        
        # Get budget
        budget = self._strategy_budgets.get(strategy)
        risk_budget_used = 0.0
        max_size = 0.0
        within_budget = True
        
        if budget:
            # Update budget used
            risk_budget_used = contrib.risk_contribution
            budget.risk_used = min(budget.risk_used + risk_budget_used, 1.0)
            budget.risk_contribution = contrib.risk_contribution_pct
            budget.position_count += 1
            budget.is_over_budget = budget.risk_used > budget.risk_target
            
            within_budget = not budget.is_over_budget
            max_size = max(self._calculate_max_capital_from_risk(
                budget.risk_target - budget.risk_used,
                contrib.volatility,
            ), 0.0)
        
        # Create position risk entry
        position_risk = PositionRisk(
            symbol=symbol,
            strategy=strategy,
            position_size_usd=position_size_usd,
            weight=contrib.weight,
            asset_volatility=contrib.volatility / math.sqrt(252),  # Daily
            volatility_annualized=contrib.volatility,
            risk_contribution=contrib.risk_contribution,
            marginal_risk=contrib.marginal_risk,
            avg_correlation=self._get_avg_correlation_with_portfolio(symbol),
            correlation_adjustment=contrib.correlation_adjustment,
            risk_budget_used=risk_budget_used,
            max_size_from_risk_budget=max_size,
            is_within_budget=within_budget,
        )
        
        self._position_risks[symbol] = position_risk
        
        return position_risk
    
    def remove_position_risk(self, symbol: str) -> bool:
        """Remove position from risk tracking."""
        symbol = symbol.upper()
        
        if symbol not in self._position_risks:
            return False
        
        position = self._position_risks.pop(symbol)
        
        # Update strategy budget
        budget = self._strategy_budgets.get(position.strategy)
        if budget:
            budget.risk_used = max(budget.risk_used - position.risk_budget_used, 0)
            budget.position_count = max(budget.position_count - 1, 0)
            budget.is_over_budget = budget.risk_used > budget.risk_target
        
        return True
    
    def check_portfolio_risk_limit(self) -> Tuple[bool, float, str]:
        """
        Check if portfolio risk is within limit.
        
        Returns: (within_limit, current_risk, message)
        """
        total_risk = sum(p.risk_contribution for p in self._position_risks.values())
        limit = PORTFOLIO_RISK_LIMITS["MAX_TOTAL_RISK"]
        
        within_limit = total_risk <= limit
        
        if within_limit:
            message = f"Portfolio risk ({total_risk*100:.1f}%) within limit ({limit*100:.0f}%)"
        else:
            excess = total_risk - limit
            message = f"Portfolio risk ({total_risk*100:.1f}%) exceeds limit by {excess*100:.1f}%"
        
        return within_limit, round(total_risk, 4), message
    
    # ═══════════════════════════════════════════════════════════
    # 4. Risk Rebalancing
    # ═══════════════════════════════════════════════════════════
    
    def check_rebalance_needed(self) -> Tuple[bool, str]:
        """Check if risk rebalancing is needed."""
        # Check portfolio risk limit
        within_limit, total_risk, _ = self.check_portfolio_risk_limit()
        
        if not within_limit:
            return True, "Portfolio risk exceeds limit"
        
        # Check strategy budgets
        for strategy, budget in self._strategy_budgets.items():
            if budget.is_over_budget:
                return True, f"Strategy {strategy} exceeds risk budget"
        
        # Check concentration
        if self._position_risks:
            max_contrib = max(p.risk_contribution for p in self._position_risks.values())
            if max_contrib > RISK_CONTRIBUTION_LIMITS["MAX_SINGLE_CONTRIBUTION"]:
                return True, "Single position contributes too much risk"
        
        return False, "Risk budgets within targets"
    
    def rebalance_risk(self) -> RiskRebalanceResult:
        """
        Rebalance portfolio to match risk budgets.
        
        Reduces positions that exceed risk allocation.
        """
        result = RiskRebalanceResult()
        
        # Check if rebalance needed
        needs_rebalance, reason = self.check_rebalance_needed()
        
        if not needs_rebalance:
            result.triggered = False
            result.reason = "No rebalancing needed"
            return result
        
        result.triggered = True
        result.reason = reason
        
        # Current state
        result.risk_before = sum(p.risk_contribution for p in self._position_risks.values())
        result.strategy_risks_before = {
            s: b.risk_used for s, b in self._strategy_budgets.items()
        }
        
        # Calculate global scale factor if over limit
        limit = PORTFOLIO_RISK_LIMITS["MAX_TOTAL_RISK"]
        if result.risk_before > limit:
            result.global_scale_factor = limit / result.risk_before
        else:
            result.global_scale_factor = 1.0
        
        # Per-strategy scale factors
        for strategy, budget in self._strategy_budgets.items():
            if budget.risk_used > budget.risk_target:
                scale = budget.risk_target / budget.risk_used
                result.strategy_scale_factors[strategy] = round(scale, 4)
                
                result.strategies_to_reduce.append({
                    "strategy": strategy,
                    "current_risk": round(budget.risk_used, 4),
                    "target_risk": round(budget.risk_target, 4),
                    "scale_factor": round(scale, 4),
                })
            elif budget.risk_used < budget.risk_target * 0.8:  # Below 80% of target
                headroom = budget.risk_target - budget.risk_used
                result.strategies_to_increase.append({
                    "strategy": strategy,
                    "current_risk": round(budget.risk_used, 4),
                    "target_risk": round(budget.risk_target, 4),
                    "headroom": round(headroom, 4),
                })
        
        # Positions to scale
        for symbol, position in self._position_risks.items():
            strategy_scale = result.strategy_scale_factors.get(position.strategy, 1.0)
            combined_scale = min(result.global_scale_factor, strategy_scale)
            
            if combined_scale < 1.0:
                new_size = position.position_size_usd * combined_scale
                result.positions_to_scale.append({
                    "symbol": symbol,
                    "strategy": position.strategy,
                    "current_size": round(position.position_size_usd, 2),
                    "new_size": round(new_size, 2),
                    "scale_factor": round(combined_scale, 4),
                    "reduction_usd": round(position.position_size_usd - new_size, 2),
                })
                
                result.capital_freed += position.position_size_usd - new_size
        
        # Project after state
        result.risk_after = result.risk_before * result.global_scale_factor
        result.strategy_risks_after = {
            s: min(b.risk_used * result.strategy_scale_factors.get(s, 1.0), b.risk_target)
            for s, b in self._strategy_budgets.items()
        }
        
        result.risk_reduction = result.risk_before - result.risk_after
        result.capital_freed = round(result.capital_freed, 2)
        
        return result
    
    # ═══════════════════════════════════════════════════════════
    # 5. Portfolio Risk Budget State
    # ═══════════════════════════════════════════════════════════
    
    def get_portfolio_risk_budget(self) -> PortfolioRiskBudget:
        """Get complete portfolio risk budget state."""
        # Total risk
        total_risk = sum(p.risk_contribution for p in self._position_risks.values())
        limit = PORTFOLIO_RISK_LIMITS["MAX_TOTAL_RISK"]
        utilization = total_risk / limit if limit > 0 else 0
        
        # Portfolio volatility
        current_vol = self._calculate_portfolio_volatility()
        vol_ratio = current_vol / self._target_volatility if self._target_volatility > 0 else 0
        vol_scale = self._target_volatility / current_vol if current_vol > 0 else 1.0
        vol_scale = max(min(vol_scale, 2.0), 0.5)
        
        # Risk decomposition
        systematic = total_risk * 0.6  # Simplified: 60% systematic
        idiosyncratic = total_risk * 0.4
        
        # Risk state
        if total_risk > limit * 1.2:
            risk_state = "CRITICAL"
        elif total_risk > limit:
            risk_state = "OVER_BUDGET"
        elif total_risk > limit * 0.9:
            risk_state = "ON_TARGET"
        else:
            risk_state = "UNDER_BUDGET"
        
        # Needs rebalance
        needs_rebalance, _ = self.check_rebalance_needed()
        
        # Warnings
        warnings = []
        if risk_state in ("OVER_BUDGET", "CRITICAL"):
            warnings.append(f"Portfolio risk ({total_risk*100:.1f}%) exceeds limit ({limit*100:.0f}%)")
        
        for strategy, budget in self._strategy_budgets.items():
            if budget.is_over_budget:
                warnings.append(f"Strategy {strategy} over budget ({budget.risk_used*100:.1f}% vs {budget.risk_target*100:.0f}%)")
        
        # Check concentration
        if self._position_risks:
            max_contrib = max(p.risk_contribution for p in self._position_risks.values())
            if max_contrib > RISK_CONTRIBUTION_LIMITS["CONCENTRATION_THRESHOLD"]:
                max_symbol = max(self._position_risks.items(), key=lambda x: x[1].risk_contribution)[0]
                warnings.append(f"Position {max_symbol} has high risk concentration ({max_contrib*100:.1f}%)")
        
        # Capital at risk
        risk_capital = self._capital * total_risk
        
        # Create state
        state = PortfolioRiskBudget(
            total_risk=round(total_risk, 4),
            total_risk_limit=limit,
            risk_utilization=round(utilization, 4),
            strategy_budgets=list(self._strategy_budgets.values()),
            strategy_count=len(self._strategy_budgets),
            position_risks=list(self._position_risks.values()),
            position_count=len(self._position_risks),
            systematic_risk=round(systematic, 4),
            idiosyncratic_risk=round(idiosyncratic, 4),
            target_volatility=self._target_volatility,
            current_volatility=round(current_vol, 4),
            volatility_ratio=round(vol_ratio, 4),
            vol_scale_factor=round(vol_scale, 4),
            total_capital=self._capital,
            risk_capital=round(risk_capital, 2),
            risk_state=risk_state,
            needs_rebalance=needs_rebalance,
            warnings=warnings,
        )
        
        # Save to history
        self._save_history(state)
        
        return state
    
    def _save_history(self, state: PortfolioRiskBudget):
        """Save state to history."""
        entry = RiskBudgetHistoryEntry(
            total_risk=state.total_risk,
            risk_limit=state.total_risk_limit,
            risk_utilization=state.risk_utilization,
            strategy_count=state.strategy_count,
            position_count=state.position_count,
            current_volatility=state.current_volatility,
            target_volatility=state.target_volatility,
            vol_scale_factor=state.vol_scale_factor,
            risk_state=state.risk_state,
        )
        
        self._history.append(entry)
        
        # Keep last 1000 entries
        if len(self._history) > 1000:
            self._history = self._history[-1000:]
    
    def get_history(self, limit: int = 100) -> List[RiskBudgetHistoryEntry]:
        """Get risk budget history."""
        return self._history[-limit:]
    
    # ═══════════════════════════════════════════════════════════
    # 6. Integration with Portfolio Manager
    # ═══════════════════════════════════════════════════════════
    
    def validate_position_for_risk_budget(
        self,
        symbol: str,
        strategy: str,
        size_usd: float,
    ) -> Tuple[bool, str, float]:
        """
        Validate position against risk budget.
        
        Returns: (approved, message, adjusted_size)
        """
        symbol = symbol.upper()
        
        # Get strategy budget
        budget = self._strategy_budgets.get(strategy)
        
        if not budget:
            return True, "No budget constraint for strategy", size_usd
        
        # Calculate risk contribution
        contrib = self.calculate_risk_contribution(symbol, strategy, size_usd)
        
        # Check if within budget
        remaining = budget.risk_target - budget.risk_used
        
        if contrib.risk_contribution <= remaining:
            return True, "Within risk budget", size_usd
        
        # Calculate adjusted size
        if contrib.risk_contribution > 0:
            scale = remaining / contrib.risk_contribution
            adjusted_size = size_usd * scale
            
            return False, f"Reduced to fit risk budget (scale: {scale:.2f})", round(adjusted_size, 2)
        
        return False, "Cannot allocate - risk budget exhausted", 0.0
    
    def get_execution_constraints_for_risk(
        self,
        symbol: str,
        strategy: str,
    ) -> Dict:
        """
        Get risk-based constraints for execution.
        
        Returns limits based on risk budget.
        """
        symbol = symbol.upper()
        
        # Get strategy budget
        budget = self._strategy_budgets.get(strategy)
        
        if not budget:
            return {
                "symbol": symbol,
                "strategy": strategy,
                "has_budget": False,
                "max_size_usd": self._capital * 0.10,  # Default 10%
                "risk_budget_remaining": 1.0,
            }
        
        # Remaining budget
        remaining = max(budget.risk_target - budget.risk_used, 0)
        
        # Max size from remaining budget
        vol = self._get_asset_volatility(symbol) * math.sqrt(252)
        max_size = self._calculate_max_capital_from_risk(remaining, vol)
        
        return {
            "symbol": symbol,
            "strategy": strategy,
            "has_budget": True,
            "risk_budget_total": round(budget.risk_target, 4),
            "risk_budget_used": round(budget.risk_used, 4),
            "risk_budget_remaining": round(remaining, 4),
            "max_size_usd": round(max_size, 2),
            "asset_volatility": round(vol, 4),
            "vol_scale_factor": round(self.get_vol_scale_factor(), 4),
        }
    
    # ═══════════════════════════════════════════════════════════
    # 7. Integration with Execution Brain
    # ═══════════════════════════════════════════════════════════
    
    def adjust_size_for_execution(
        self,
        symbol: str,
        strategy: str,
        base_size_usd: float,
        current_price: float,
    ) -> Dict:
        """
        Adjust position size for execution brain.
        
        Applies:
        1. Volatility targeting
        2. Risk budget constraint
        3. Portfolio risk limit
        """
        symbol = symbol.upper()
        
        # Step 1: Volatility targeting
        vol_request = VolatilityTargetRequest(
            symbol=symbol,
            strategy=strategy,
            direction="LONG",  # Direction doesn't affect vol calc
            base_size_usd=base_size_usd,
        )
        vol_response = self.compute_volatility_target_size(vol_request)
        
        size_after_vol = vol_response.vol_scaled_size_usd
        
        # Step 2: Risk budget constraint
        approved, msg, size_after_budget = self.validate_position_for_risk_budget(
            symbol, strategy, size_after_vol
        )
        
        # Step 3: Portfolio risk limit
        within_limit, total_risk, _ = self.check_portfolio_risk_limit()
        
        if not within_limit:
            # Scale down proportionally
            limit = PORTFOLIO_RISK_LIMITS["MAX_TOTAL_RISK"]
            scale = limit / total_risk
            final_size = size_after_budget * scale
        else:
            final_size = size_after_budget
        
        return {
            "symbol": symbol,
            "strategy": strategy,
            "base_size_usd": base_size_usd,
            "vol_adjusted_size_usd": round(size_after_vol, 2),
            "budget_adjusted_size_usd": round(size_after_budget, 2),
            "final_size_usd": round(final_size, 2),
            "total_reduction_pct": round(1 - final_size / base_size_usd, 4) if base_size_usd > 0 else 0,
            "adjustments": {
                "volatility_scaling": vol_response.volatility_ratio < 1.0,
                "risk_budget_constraint": not approved,
                "portfolio_risk_limit": not within_limit,
            },
            "reason": msg,
        }
    
    # ═══════════════════════════════════════════════════════════
    # Helper Methods
    # ═══════════════════════════════════════════════════════════
    
    def _get_asset_volatility(self, symbol: str) -> float:
        """Get asset volatility (daily)."""
        if symbol in self._volatility_cache:
            return self._volatility_cache[symbol]
        
        # Try from database
        try:
            from core.database import get_database
            db = get_database()
            if db:
                candles = list(db.candles.find(
                    {"symbol": symbol},
                    {"_id": 0, "close": 1}
                ).sort("timestamp", -1).limit(VOLATILITY_PARAMS["LOOKBACK_DAYS"] + 1))
                
                if len(candles) >= 2:
                    returns = []
                    for i in range(len(candles) - 1):
                        ret = (candles[i]["close"] - candles[i + 1]["close"]) / candles[i + 1]["close"]
                        returns.append(ret)
                    
                    mean = sum(returns) / len(returns)
                    variance = sum((r - mean) ** 2 for r in returns) / len(returns)
                    vol = math.sqrt(variance)
                    
                    # Clamp
                    vol = max(min(vol, VOLATILITY_PARAMS["MAX_VOLATILITY"] / math.sqrt(252)),
                             VOLATILITY_PARAMS["MIN_VOLATILITY"] / math.sqrt(252))
                    
                    self._volatility_cache[symbol] = vol
                    return vol
        except Exception:
            pass
        
        # Default based on asset type
        defaults = {
            "BTC": 0.035,   # ~55% annualized
            "ETH": 0.045,   # ~70% annualized
            "SOL": 0.055,   # ~85% annualized
            "SPX": 0.012,   # ~19% annualized
            "DXY": 0.005,   # ~8% annualized
        }
        
        vol = defaults.get(symbol, 0.02)
        self._volatility_cache[symbol] = vol
        return vol
    
    def _get_strategy_volatility(self, strategy: str) -> float:
        """Get strategy volatility (annualized)."""
        # Different strategies have different volatility profiles
        defaults = {
            "TREND_FOLLOWING": 0.20,
            "MEAN_REVERSION": 0.12,
            "BREAKOUT": 0.25,
            "VOLATILITY": 0.30,
            "MOMENTUM": 0.18,
            "STATISTICAL_ARB": 0.08,
        }
        return defaults.get(strategy, 0.15)
    
    def _get_strategy_performance(self, strategy: str) -> float:
        """Get strategy recent performance (0-1)."""
        budget = self._strategy_budgets.get(strategy)
        if budget and budget.sharpe_ratio > 0:
            return min(budget.sharpe_ratio / 3, 1.0)  # Normalize Sharpe
        return 0.5  # Default neutral
    
    def _get_avg_correlation_with_portfolio(self, symbol: str) -> float:
        """Get average correlation of symbol with existing positions."""
        if not self._position_risks or symbol in self._position_risks:
            return 0.0
        
        # Check cache
        if symbol in self._correlation_cache:
            correlations = self._correlation_cache[symbol]
            if correlations:
                return sum(correlations.values()) / len(correlations)
        
        # Calculate from returns
        total_corr = 0.0
        count = 0
        
        for existing_symbol in self._position_risks:
            corr = self._calculate_correlation(symbol, existing_symbol)
            total_corr += corr
            count += 1
            
            # Cache
            if symbol not in self._correlation_cache:
                self._correlation_cache[symbol] = {}
            self._correlation_cache[symbol][existing_symbol] = corr
        
        return total_corr / count if count > 0 else 0.0
    
    def _calculate_correlation(self, symbol1: str, symbol2: str) -> float:
        """Calculate correlation between two symbols."""
        try:
            from core.database import get_database
            db = get_database()
            if db:
                candles1 = list(db.candles.find(
                    {"symbol": symbol1}, {"_id": 0, "close": 1}
                ).sort("timestamp", -1).limit(30))
                
                candles2 = list(db.candles.find(
                    {"symbol": symbol2}, {"_id": 0, "close": 1}
                ).sort("timestamp", -1).limit(30))
                
                if len(candles1) >= 10 and len(candles2) >= 10:
                    n = min(len(candles1), len(candles2)) - 1
                    
                    returns1 = [(candles1[i]["close"] - candles1[i+1]["close"]) / candles1[i+1]["close"]
                               for i in range(n)]
                    returns2 = [(candles2[i]["close"] - candles2[i+1]["close"]) / candles2[i+1]["close"]
                               for i in range(n)]
                    
                    mean1 = sum(returns1) / n
                    mean2 = sum(returns2) / n
                    
                    cov = sum((returns1[i] - mean1) * (returns2[i] - mean2) for i in range(n)) / n
                    var1 = sum((r - mean1) ** 2 for r in returns1) / n
                    var2 = sum((r - mean2) ** 2 for r in returns2) / n
                    
                    if var1 > 0 and var2 > 0:
                        corr = cov / math.sqrt(var1 * var2)
                        return max(min(corr, 1.0), -1.0)
        except Exception:
            pass
        
        # Default based on asset similarity
        seed = hash(symbol1 + symbol2)
        import random
        random.seed(seed)
        return round(random.uniform(0.2, 0.6), 2)
    
    def _calculate_portfolio_volatility(self) -> float:
        """Calculate portfolio volatility."""
        if not self._position_risks:
            return 0.0
        
        # Simplified: weighted average of asset volatilities
        total_vol = 0.0
        total_weight = 0.0
        
        for position in self._position_risks.values():
            total_vol += position.weight * position.volatility_annualized
            total_weight += position.weight
        
        return total_vol / total_weight if total_weight > 0 else 0.0
    
    def _calculate_portfolio_risk(self) -> float:
        """Calculate total portfolio risk."""
        return sum(p.risk_contribution for p in self._position_risks.values())
    
    def _calculate_max_capital_from_risk(
        self,
        risk_budget: float,
        volatility: float,
    ) -> float:
        """
        Calculate max capital from risk budget.
        
        Formula: max_capital = (risk_budget * total_capital) / volatility
        """
        if volatility <= 0:
            volatility = VOLATILITY_PARAMS["MIN_VOLATILITY"]
        
        return (risk_budget * self._capital) / volatility


# ══════════════════════════════════════════════════════════════
# Singleton
# ══════════════════════════════════════════════════════════════

_risk_budget_engine: Optional[RiskBudgetEngine] = None


def get_risk_budget_engine() -> RiskBudgetEngine:
    """Get singleton instance of RiskBudgetEngine."""
    global _risk_budget_engine
    if _risk_budget_engine is None:
        _risk_budget_engine = RiskBudgetEngine()
    return _risk_budget_engine
