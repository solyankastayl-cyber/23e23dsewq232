"""Covariance & Correlation Matrix — V4 Portfolio Math

Calculates covariance and correlation from historical price data.
"""

import numpy as np
import logging

logger = logging.getLogger(__name__)


def log_returns(prices: list[float]) -> np.ndarray:
    """
    Calculate log returns from price series.
    
    Formula: r_t = ln(P_t / P_{t-1})
    
    Args:
        prices: List of prices
    
    Returns:
        Array of log returns
    """
    prices = np.array(prices, dtype=float)
    if len(prices) < 2:
        return np.array([])
    return np.diff(np.log(prices))


def build_returns_matrix(price_map: dict[str, list[float]]) -> tuple[list[str], np.ndarray]:
    """
    Build aligned returns matrix from price history.
    
    Args:
        price_map: {symbol: [price1, price2, ...]}
    
    Returns:
        (symbols, returns_matrix) where returns_matrix is 2D array
    """
    symbols = list(price_map.keys())
    returns_list = []
    
    for s in symbols:
        r = log_returns(price_map[s])
        returns_list.append(r)
    
    if not returns_list:
        return [], np.array([])
    
    # Align to minimum length
    min_len = min(len(r) for r in returns_list)
    if min_len == 0:
        return symbols, np.array([])
    
    aligned = np.array([r[-min_len:] for r in returns_list])
    return symbols, aligned


def covariance_matrix(price_map: dict[str, list[float]]) -> tuple[list[str], np.ndarray]:
    """
    Calculate covariance matrix.
    
    Args:
        price_map: {symbol: price_history}
    
    Returns:
        (symbols, covariance_matrix)
    """
    symbols, aligned = build_returns_matrix(price_map)
    if aligned.size == 0:
        logger.warning("[Covariance] Empty returns matrix")
        return symbols, np.array([])
    
    cov = np.cov(aligned)
    logger.info(f"[Covariance] Computed {len(symbols)}x{len(symbols)} matrix")
    return symbols, cov


def correlation_matrix(price_map: dict[str, list[float]]) -> tuple[list[str], np.ndarray]:
    """
    Calculate correlation matrix.
    
    Args:
        price_map: {symbol: price_history}
    
    Returns:
        (symbols, correlation_matrix)
    """
    symbols, aligned = build_returns_matrix(price_map)
    if aligned.size == 0:
        logger.warning("[Correlation] Empty returns matrix")
        return symbols, np.array([])
    
    corr = np.corrcoef(aligned)
    logger.info(f"[Correlation] Computed {len(symbols)}x{len(symbols)} matrix")
    return symbols, corr


def get_correlation(symbol1: str, symbol2: str, corr_matrix: np.ndarray, symbols: list[str]) -> float:
    """
    Get correlation between two symbols.
    
    Returns:
        Correlation coefficient (-1..1) or 0 if not found
    """
    try:
        idx1 = symbols.index(symbol1)
        idx2 = symbols.index(symbol2)
        return float(corr_matrix[idx1, idx2])
    except (ValueError, IndexError):
        return 0.0
