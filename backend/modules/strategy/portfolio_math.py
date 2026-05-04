"""Portfolio Math — V4 Risk Calculations

Portfolio variance, volatility, and risk contribution analysis.
"""

import numpy as np
import logging

logger = logging.getLogger(__name__)


def portfolio_variance(weights: np.ndarray, cov: np.ndarray) -> float:
    """
    Calculate portfolio variance.
    
    Formula: σ²_p = w^T Σ w
    
    Args:
        weights: Portfolio weights (must sum to 1)
        cov: Covariance matrix
    
    Returns:
        Portfolio variance
    """
    if cov.size == 0 or weights.size == 0:
        return 0.0
    
    variance = float(weights.T @ cov @ weights)
    return max(variance, 0.0)  # Prevent negative due to numerical errors


def portfolio_volatility(weights: np.ndarray, cov: np.ndarray) -> float:
    """
    Calculate portfolio volatility (standard deviation).
    
    Formula: σ_p = sqrt(w^T Σ w)
    
    Args:
        weights: Portfolio weights
        cov: Covariance matrix
    
    Returns:
        Portfolio volatility (annualized if returns are daily)
    """
    variance = portfolio_variance(weights, cov)
    return float(np.sqrt(variance))


def marginal_risk_contribution(weights: np.ndarray, cov: np.ndarray) -> np.ndarray:
    """
    Calculate marginal risk contribution (MRC) for each asset.
    
    Formula: MRC_i = (Σ w)_i / σ_p
    
    This tells you how much portfolio risk increases if you add
    a small amount to position i.
    
    Args:
        weights: Portfolio weights
        cov: Covariance matrix
    
    Returns:
        Array of marginal risk contributions
    """
    pvol = portfolio_volatility(weights, cov)
    if pvol <= 0:
        return np.zeros_like(weights)
    
    mrc = (cov @ weights) / pvol
    return mrc


def risk_contributions(weights: np.ndarray, cov: np.ndarray) -> np.ndarray:
    """
    Calculate risk contribution (RC) for each asset.
    
    Formula: RC_i = w_i * MRC_i
    
    This tells you how much each position contributes to total
    portfolio risk.
    
    Args:
        weights: Portfolio weights
        cov: Covariance matrix
    
    Returns:
        Array of risk contributions (sum = portfolio variance)
    """
    mrc = marginal_risk_contribution(weights, cov)
    rc = weights * mrc
    return rc


def risk_contribution_percentages(weights: np.ndarray, cov: np.ndarray) -> np.ndarray:
    """
    Calculate risk contribution as percentage of total risk.
    
    Returns:
        Array of percentages (sum = 1.0)
    """
    rc = risk_contributions(weights, cov)
    total = rc.sum()
    
    if total <= 0:
        return np.zeros_like(weights)
    
    return rc / total


def diversification_ratio(weights: np.ndarray, cov: np.ndarray) -> float:
    """
    Calculate portfolio diversification ratio.
    
    Formula: DR = (weighted avg individual vol) / portfolio vol
    
    DR > 1 means diversification benefit.
    
    Returns:
        Diversification ratio (higher is better)
    """
    pvol = portfolio_volatility(weights, cov)
    if pvol <= 0:
        return 1.0
    
    # Individual volatilities
    individual_vols = np.sqrt(np.diag(cov))
    
    # Weighted average
    weighted_avg_vol = (weights * individual_vols).sum()
    
    return weighted_avg_vol / pvol
