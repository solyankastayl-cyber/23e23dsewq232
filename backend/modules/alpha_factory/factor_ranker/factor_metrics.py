"""
PHASE 13.4 - Factor Metrics
============================
Core metrics for factor evaluation.

Metrics:
- IC (Information Coefficient): corr(factor, future_returns)
- Sharpe Ratio: mean(returns) / std(returns)
- Stability: consistency of IC over time
- Decay: how quickly factor edge decays
- Regime Consistency: stability across market regimes
"""

from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
import math
import random


@dataclass
class MetricsResult:
    """Factor metrics result."""
    factor_id: str
    
    # Core metrics
    ic: float = 0.0                    # Information Coefficient
    ic_rank: float = 0.0               # IC percentile rank
    sharpe: float = 0.0                # Sharpe Ratio
    stability: float = 0.0             # Stability score (0-1)
    decay_score: float = 0.0           # Decay score (lower is better)
    regime_consistency: float = 0.0    # Regime consistency (0-1)
    
    # Composite
    composite_score: float = 0.0       # Weighted composite score
    
    # Verdict
    verdict: str = "PENDING"           # ELITE, STRONG, PROMISING, WEAK, REJECTED
    approved: bool = False
    
    # Details
    ic_by_regime: Dict[str, float] = field(default_factory=dict)
    ic_decay_curve: List[float] = field(default_factory=list)
    rolling_ic: List[float] = field(default_factory=list)
    rolling_sharpe: List[float] = field(default_factory=list)
    
    # Metadata
    evaluated_at: Optional[datetime] = None
    samples_used: int = 0
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "factor_id": self.factor_id,
            "ic": self.ic,
            "ic_rank": self.ic_rank,
            "sharpe": self.sharpe,
            "stability": self.stability,
            "decay_score": self.decay_score,
            "regime_consistency": self.regime_consistency,
            "composite_score": self.composite_score,
            "verdict": self.verdict,
            "approved": self.approved,
            "ic_by_regime": self.ic_by_regime,
            "ic_decay_curve": self.ic_decay_curve,
            "rolling_ic": self.rolling_ic[-10:] if self.rolling_ic else [],  # Last 10
            "rolling_sharpe": self.rolling_sharpe[-10:] if self.rolling_sharpe else [],
            "evaluated_at": self.evaluated_at.isoformat() if self.evaluated_at else None,
            "samples_used": self.samples_used
        }


class FactorMetrics:
    """
    Factor metrics calculator.
    
    Computes IC, Sharpe, Stability, Decay, and Regime Consistency.
    """
    
    # Thresholds - calibrated for realistic approval rates
    IC_ELITE = 0.040
    IC_STRONG = 0.030
    IC_PROMISING = 0.020
    IC_WEAK = 0.010
    
    SHARPE_ELITE = 1.0
    SHARPE_STRONG = 0.6
    SHARPE_PROMISING = 0.35
    SHARPE_WEAK = 0.2
    
    STABILITY_ELITE = 0.65
    STABILITY_STRONG = 0.50
    STABILITY_PROMISING = 0.35
    
    # Regimes
    REGIMES = ["TRENDING_UP", "TRENDING_DOWN", "RANGE", "HIGH_VOL", "LOW_VOL"]
    
    @staticmethod
    def correlation(x: List[float], y: List[float]) -> float:
        """
        Calculate Pearson correlation coefficient.
        """
        n = min(len(x), len(y))
        if n < 2:
            return 0.0
        
        x = x[:n]
        y = y[:n]
        
        mean_x = sum(x) / n
        mean_y = sum(y) / n
        
        cov = sum((xi - mean_x) * (yi - mean_y) for xi, yi in zip(x, y)) / n
        std_x = math.sqrt(sum((xi - mean_x) ** 2 for xi in x) / n)
        std_y = math.sqrt(sum((yi - mean_y) ** 2 for yi in y) / n)
        
        if std_x == 0 or std_y == 0:
            return 0.0
        
        return cov / (std_x * std_y)
    
    @staticmethod
    def sharpe_ratio(returns: List[float], risk_free: float = 0.0) -> float:
        """
        Calculate Sharpe Ratio.
        """
        if len(returns) < 2:
            return 0.0
        
        mean_return = sum(returns) / len(returns) - risk_free
        std_return = math.sqrt(sum((r - sum(returns)/len(returns)) ** 2 for r in returns) / len(returns))
        
        if std_return == 0:
            return 0.0
        
        # Annualize (assuming daily data)
        return (mean_return / std_return) * math.sqrt(252)
    
    @staticmethod
    def rolling_metric(
        values: List[float],
        metric_func,
        window: int = 60
    ) -> List[float]:
        """
        Calculate rolling metric.
        """
        results = []
        for i in range(window, len(values)):
            window_values = values[i-window:i]
            results.append(metric_func(window_values))
        return results
    
    @classmethod
    def calculate_ic(
        cls,
        factor_values: List[float],
        future_returns: List[float],
        lag: int = 1
    ) -> float:
        """
        Calculate Information Coefficient.
        
        IC = corr(factor_t, returns_t+lag)
        """
        if len(factor_values) < lag + 10:
            return 0.0
        
        # Align: factor[:-lag] with returns[lag:]
        factor_aligned = factor_values[:-lag] if lag > 0 else factor_values
        returns_aligned = future_returns[lag:] if lag > 0 else future_returns
        
        return cls.correlation(factor_aligned, returns_aligned)
    
    @classmethod
    def calculate_rolling_ic(
        cls,
        factor_values: List[float],
        future_returns: List[float],
        window: int = 60,
        lag: int = 1
    ) -> List[float]:
        """
        Calculate rolling IC.
        """
        results = []
        n = min(len(factor_values), len(future_returns))
        
        for i in range(window + lag, n):
            factor_window = factor_values[i-window-lag:i-lag]
            returns_window = future_returns[i-window:i]
            ic = cls.correlation(factor_window, returns_window)
            results.append(ic)
        
        return results
    
    @classmethod
    def calculate_stability(
        cls,
        rolling_ic: List[float]
    ) -> float:
        """
        Calculate stability score based on rolling IC.
        
        Higher stability = more consistent IC over time.
        """
        if len(rolling_ic) < 5:
            return 0.5
        
        # Count positive IC periods
        positive_ratio = sum(1 for ic in rolling_ic if ic > 0) / len(rolling_ic)
        
        # Calculate IC volatility
        mean_ic = sum(rolling_ic) / len(rolling_ic)
        ic_vol = math.sqrt(sum((ic - mean_ic) ** 2 for ic in rolling_ic) / len(rolling_ic))
        
        # Stability = high positive ratio + low volatility
        vol_penalty = min(1.0, ic_vol / 0.05)  # Penalize high volatility
        
        stability = (positive_ratio * 0.6 + (1 - vol_penalty) * 0.4)
        return max(0.0, min(1.0, stability))
    
    @classmethod
    def calculate_decay(
        cls,
        factor_values: List[float],
        future_returns: List[float],
        lags: List[int] = None
    ) -> Tuple[float, List[float]]:
        """
        Calculate IC decay across different lags.
        
        Returns:
            (decay_score, ic_curve)
        """
        lags = lags or [1, 2, 5, 10, 20]
        ic_curve = []
        
        for lag in lags:
            ic = cls.calculate_ic(factor_values, future_returns, lag)
            ic_curve.append(ic)
        
        if len(ic_curve) < 2 or ic_curve[0] == 0:
            return 0.5, ic_curve
        
        # Decay score = how much IC drops from lag 1 to lag 10
        initial_ic = abs(ic_curve[0])
        final_ic = abs(ic_curve[-1]) if ic_curve else 0
        
        if initial_ic > 0:
            decay_ratio = 1 - (final_ic / initial_ic)
            decay_score = max(0.0, min(1.0, decay_ratio))
        else:
            decay_score = 0.5
        
        return decay_score, ic_curve
    
    @classmethod
    def calculate_regime_consistency(
        cls,
        ic_by_regime: Dict[str, float]
    ) -> float:
        """
        Calculate regime consistency.
        
        High consistency = similar IC across regimes.
        """
        if not ic_by_regime:
            return 0.5
        
        ics = list(ic_by_regime.values())
        if len(ics) < 2:
            return 0.5
        
        # Count regimes with positive IC
        positive_regimes = sum(1 for ic in ics if ic > 0)
        positive_ratio = positive_regimes / len(ics)
        
        # Calculate IC variance across regimes
        mean_ic = sum(ics) / len(ics)
        ic_variance = sum((ic - mean_ic) ** 2 for ic in ics) / len(ics)
        ic_std = math.sqrt(ic_variance)
        
        # Low variance = high consistency
        variance_penalty = min(1.0, ic_std / 0.03)
        
        consistency = (positive_ratio * 0.7 + (1 - variance_penalty) * 0.3)
        return max(0.0, min(1.0, consistency))
    
    @classmethod
    def calculate_composite_score(
        cls,
        ic: float,
        sharpe: float,
        stability: float,
        regime_consistency: float,
        decay_score: float
    ) -> float:
        """
        Calculate composite score.
        
        score = 0.35*IC + 0.25*Sharpe + 0.20*Stability + 0.10*Regime - 0.10*Decay
        """
        # Normalize IC to 0-1 scale (assuming max IC ~0.1)
        ic_normalized = min(1.0, abs(ic) / 0.10)
        
        # Normalize Sharpe to 0-1 scale (assuming max Sharpe ~3.0)
        sharpe_normalized = min(1.0, max(0.0, sharpe) / 3.0)
        
        score = (
            0.35 * ic_normalized +
            0.25 * sharpe_normalized +
            0.20 * stability +
            0.10 * regime_consistency -
            0.10 * decay_score
        )
        
        return max(0.0, min(1.0, score))
    
    @classmethod
    def determine_verdict(
        cls,
        ic: float,
        sharpe: float,
        stability: float,
        composite_score: float
    ) -> Tuple[str, bool]:
        """
        Determine factor verdict.
        
        Returns:
            (verdict, approved)
        """
        # ELITE: Top 2%
        if (abs(ic) >= cls.IC_ELITE and 
            sharpe >= cls.SHARPE_ELITE and 
            stability >= cls.STABILITY_ELITE):
            return "ELITE", True
        
        # STRONG: Top 10%
        if (abs(ic) >= cls.IC_STRONG and 
            sharpe >= cls.SHARPE_STRONG and 
            stability >= cls.STABILITY_STRONG):
            return "STRONG", True
        
        # PROMISING: Top 25%
        if (abs(ic) >= cls.IC_PROMISING and 
            sharpe >= cls.SHARPE_PROMISING and 
            stability >= cls.STABILITY_PROMISING):
            return "PROMISING", True
        
        # WEAK: Bottom 50%
        if abs(ic) >= cls.IC_WEAK or composite_score >= 0.25:
            return "WEAK", False
        
        # REJECTED: Fails all thresholds
        return "REJECTED", False
