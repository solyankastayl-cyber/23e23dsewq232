"""
PHASE 6.3 - Risk of Ruin Calculator
=====================================
Calculates probability of account loss at various thresholds.
"""

import math
from typing import Dict, List, Optional, Tuple
import statistics

from .monte_types import EquityCurve, RiskOfRuinMetrics


class RiskOfRuinCalculator:
    """
    Calculates risk of ruin probabilities.
    """
    
    def __init__(self, initial_capital: float = 100000.0):
        self.initial_capital = initial_capital
    
    def calculate(
        self,
        curves: List[EquityCurve]
    ) -> RiskOfRuinMetrics:
        """
        Calculate risk of ruin metrics from equity curves.
        """
        if not curves:
            return RiskOfRuinMetrics(
                prob_loss_30pct=0, prob_loss_50pct=0,
                prob_loss_80pct=0, prob_loss_100pct=0,
                expected_loss_if_ruin=0
            )
        
        n = len(curves)
        
        # Count curves that hit various loss levels
        loss_30_count = 0
        loss_50_count = 0
        loss_80_count = 0
        loss_100_count = 0
        
        # Track losses for expected loss calculation
        losses_if_ruin = []
        time_to_ruin = []
        
        for curve in curves:
            min_equity = curve.min_equity
            max_loss = 1 - (min_equity / self.initial_capital)
            
            if max_loss >= 0.30:
                loss_30_count += 1
                losses_if_ruin.append(max_loss)
                
                # Find time to hit 30% loss
                for i, eq in enumerate(curve.equity_values):
                    if eq <= self.initial_capital * 0.70:
                        time_to_ruin.append(i)
                        break
            
            if max_loss >= 0.50:
                loss_50_count += 1
            
            if max_loss >= 0.80:
                loss_80_count += 1
            
            if max_loss >= 0.99:  # Near total wipeout
                loss_100_count += 1
        
        # Calculate probabilities
        prob_30 = loss_30_count / n
        prob_50 = loss_50_count / n
        prob_80 = loss_80_count / n
        prob_100 = loss_100_count / n
        
        # Expected loss if ruin
        expected_loss = statistics.mean(losses_if_ruin) if losses_if_ruin else 0
        
        # Median time to ruin
        median_time = int(statistics.median(time_to_ruin)) if time_to_ruin else None
        
        return RiskOfRuinMetrics(
            prob_loss_30pct=prob_30,
            prob_loss_50pct=prob_50,
            prob_loss_80pct=prob_80,
            prob_loss_100pct=prob_100,
            expected_loss_if_ruin=expected_loss,
            median_time_to_ruin=median_time
        )
    
    def calculate_kelly_criterion(
        self,
        win_rate: float,
        avg_win: float,
        avg_loss: float
    ) -> float:
        """
        Calculate Kelly Criterion for optimal position sizing.
        
        Kelly % = W - [(1-W) / R]
        where W = win probability, R = win/loss ratio
        """
        if avg_loss == 0:
            return 0
        
        win_loss_ratio = abs(avg_win / avg_loss)
        kelly = win_rate - ((1 - win_rate) / win_loss_ratio)
        
        # Clamp between 0 and 1
        return max(0, min(1, kelly))
    
    def calculate_fractional_kelly(
        self,
        win_rate: float,
        avg_win: float,
        avg_loss: float,
        fraction: float = 0.5
    ) -> float:
        """
        Calculate fractional Kelly (more conservative).
        """
        full_kelly = self.calculate_kelly_criterion(win_rate, avg_win, avg_loss)
        return full_kelly * fraction
    
    def theoretical_risk_of_ruin(
        self,
        win_rate: float,
        avg_win: float,
        avg_loss: float,
        risk_per_trade: float = 0.02
    ) -> float:
        """
        Calculate theoretical risk of ruin using formula.
        
        R = ((1-A)/((1+A)))^U
        where A = edge, U = units available
        """
        # Calculate edge
        edge = (win_rate * avg_win) - ((1 - win_rate) * abs(avg_loss))
        
        if edge <= 0:
            return 1.0  # Negative edge = guaranteed ruin
        
        # Units available = 1 / risk_per_trade
        units = 1 / risk_per_trade if risk_per_trade > 0 else 50
        
        # Calculate A (normalized edge)
        total_return = win_rate * avg_win + (1 - win_rate) * (-abs(avg_loss))
        a = total_return / risk_per_trade if risk_per_trade > 0 else 0
        
        if a >= 1:
            return 0.0  # Very high edge = near zero ruin
        
        if a <= -1:
            return 1.0  # Very negative edge = certain ruin
        
        # Risk of ruin formula
        try:
            ror = ((1 - a) / (1 + a)) ** units
            return min(1.0, max(0.0, ror))
        except (ValueError, OverflowError):
            return 0.5
    
    def calculate_var(
        self,
        curves: List[EquityCurve],
        confidence: float = 0.95
    ) -> float:
        """
        Calculate Value at Risk at given confidence level.
        """
        if not curves:
            return 0.0
        
        returns = sorted([c.final_return for c in curves])
        idx = int((1 - confidence) * len(returns))
        
        return abs(returns[idx]) if idx < len(returns) else 0.0
    
    def calculate_cvar(
        self,
        curves: List[EquityCurve],
        confidence: float = 0.95
    ) -> float:
        """
        Calculate Conditional VaR (Expected Shortfall).
        Average loss in worst (1-confidence)% of cases.
        """
        if not curves:
            return 0.0
        
        returns = sorted([c.final_return for c in curves])
        cutoff_idx = int((1 - confidence) * len(returns))
        
        if cutoff_idx == 0:
            cutoff_idx = 1
        
        worst_returns = returns[:cutoff_idx]
        
        return abs(statistics.mean(worst_returns)) if worst_returns else 0.0
