"""
Metrics Calculators (S1.4B/S1.4C)
==================================

Separate calculator functions for performance and risk metrics.
Pure functions - no side effects, easy to test.

Metrics:
- Sharpe Ratio (from equity returns)
- Sortino Ratio (from equity returns, only downside deviation)
- Profit Factor (from trades)
- Expectancy (from trades)
- Max Drawdown (from equity curve)
- Calmar Ratio (annual return / max drawdown)
- Recovery Factor (net profit / max drawdown)
"""

import math
from typing import List, Optional, Tuple
from dataclasses import dataclass


# ===========================================
# Constants
# ===========================================

MIN_STD_THRESHOLD = 1e-9
DEFAULT_TRADING_DAYS_PER_YEAR = 365  # Crypto trades 24/7


# ===========================================
# Return Calculations
# ===========================================

def calculate_returns_from_equity(
    equity_values: List[float]
) -> List[float]:
    """
    Calculate period returns from equity curve.
    
    Args:
        equity_values: List of equity values (e.g., [1000, 1010, 1005, 1020])
        
    Returns:
        List of returns (e.g., [0.01, -0.00495, 0.0149])
    """
    if len(equity_values) < 2:
        return []
    
    returns = []
    for i in range(1, len(equity_values)):
        prev = equity_values[i - 1]
        curr = equity_values[i]
        
        if prev > 0:
            r = (curr - prev) / prev
            returns.append(r)
    
    return returns


def calculate_mean_return(returns: List[float]) -> float:
    """Calculate mean of returns"""
    if not returns:
        return 0.0
    return sum(returns) / len(returns)


def calculate_std_deviation(returns: List[float]) -> float:
    """
    Calculate standard deviation of returns.
    Uses sample std dev (n-1 denominator).
    """
    if len(returns) < 2:
        return 0.0
    
    mean = calculate_mean_return(returns)
    variance = sum((r - mean) ** 2 for r in returns) / (len(returns) - 1)
    return math.sqrt(variance)


def calculate_downside_deviation(
    returns: List[float],
    target_return: float = 0.0
) -> float:
    """
    Calculate downside deviation (only returns below target).
    
    Args:
        returns: List of returns
        target_return: Target return threshold (default 0)
        
    Returns:
        Downside deviation
    """
    if len(returns) < 2:
        return 0.0
    
    downside_returns = [r for r in returns if r < target_return]
    
    if not downside_returns:
        return 0.0
    
    # Downside variance uses all returns in denominator
    downside_variance = sum(
        (r - target_return) ** 2 for r in downside_returns
    ) / len(returns)
    
    return math.sqrt(downside_variance)


# ===========================================
# Sharpe Ratio (S1.4B)
# ===========================================

def calculate_sharpe_ratio(
    equity_values: List[float],
    risk_free_rate: float = 0.0,
    trading_days_per_year: int = DEFAULT_TRADING_DAYS_PER_YEAR
) -> float:
    """
    Calculate Sharpe Ratio from equity curve.
    
    Sharpe = (mean_return - risk_free_rate) / std_dev * sqrt(trading_days)
    
    Args:
        equity_values: List of equity values over time
        risk_free_rate: Annual risk-free rate (default 0 for crypto)
        trading_days_per_year: Days per year for annualization
        
    Returns:
        Annualized Sharpe Ratio
    """
    returns = calculate_returns_from_equity(equity_values)
    
    if len(returns) < 2:
        return 0.0
    
    # Daily risk-free rate
    daily_rf = risk_free_rate / trading_days_per_year
    
    # Excess returns
    excess_returns = [r - daily_rf for r in returns]
    
    mean_excess = calculate_mean_return(excess_returns)
    std_dev = calculate_std_deviation(excess_returns)
    
    if std_dev < MIN_STD_THRESHOLD:
        return 0.0
    
    # Daily Sharpe
    daily_sharpe = mean_excess / std_dev
    
    # Annualize
    annualized_sharpe = daily_sharpe * math.sqrt(trading_days_per_year)
    
    return annualized_sharpe


# ===========================================
# Sortino Ratio (S1.4B)
# ===========================================

def calculate_sortino_ratio(
    equity_values: List[float],
    risk_free_rate: float = 0.0,
    trading_days_per_year: int = DEFAULT_TRADING_DAYS_PER_YEAR
) -> float:
    """
    Calculate Sortino Ratio from equity curve.
    
    Sortino = (mean_return - risk_free_rate) / downside_deviation * sqrt(trading_days)
    
    Only penalizes downside volatility (negative returns).
    
    Args:
        equity_values: List of equity values over time
        risk_free_rate: Annual risk-free rate
        trading_days_per_year: Days per year for annualization
        
    Returns:
        Annualized Sortino Ratio
    """
    returns = calculate_returns_from_equity(equity_values)
    
    if len(returns) < 2:
        return 0.0
    
    # Daily risk-free rate
    daily_rf = risk_free_rate / trading_days_per_year
    
    # Mean return
    mean_return = calculate_mean_return(returns)
    excess_return = mean_return - daily_rf
    
    # Downside deviation
    downside_returns = [r for r in returns if r < daily_rf]
    
    if not downside_returns:
        # No negative returns - excellent performance
        return 99.99 if excess_return > 0 else 0.0
    
    downside_variance = sum(
        (r - daily_rf) ** 2 for r in downside_returns
    ) / len(returns)
    downside_dev = math.sqrt(downside_variance)
    
    if downside_dev < MIN_STD_THRESHOLD:
        return 0.0
    
    # Daily Sortino
    daily_sortino = excess_return / downside_dev
    
    # Annualize
    return daily_sortino * math.sqrt(trading_days_per_year)


# ===========================================
# Profit Factor (S1.4B) - from trades
# ===========================================

def calculate_profit_factor(
    gross_profit: float,
    gross_loss: float
) -> float:
    """
    Calculate Profit Factor.
    
    Profit Factor = sum(winning_trades) / abs(sum(losing_trades))
    
    Args:
        gross_profit: Total profit from winning trades
        gross_loss: Total loss from losing trades (as positive value)
        
    Returns:
        Profit Factor (> 1 is profitable)
    """
    if gross_loss <= 0:
        return float('inf') if gross_profit > 0 else 0.0
    
    return gross_profit / gross_loss


def calculate_profit_factor_from_pnls(pnl_list: List[float]) -> float:
    """
    Calculate Profit Factor from list of PnL values.
    
    Args:
        pnl_list: List of net PnL values per trade
        
    Returns:
        Profit Factor
    """
    if not pnl_list:
        return 0.0
    
    gross_profit = sum(p for p in pnl_list if p > 0)
    gross_loss = abs(sum(p for p in pnl_list if p < 0))
    
    return calculate_profit_factor(gross_profit, gross_loss)


# ===========================================
# Expectancy (S1.4B) - from trades
# ===========================================

def calculate_expectancy(
    win_rate: float,
    avg_win: float,
    avg_loss: float
) -> float:
    """
    Calculate Expectancy.
    
    Expectancy = (win_rate * avg_win) - ((1 - win_rate) * avg_loss)
    
    Shows expected profit per trade.
    
    Args:
        win_rate: Probability of winning (0-1)
        avg_win: Average winning trade value (positive)
        avg_loss: Average losing trade value (positive)
        
    Returns:
        Expected value per trade
    """
    return (win_rate * avg_win) - ((1 - win_rate) * avg_loss)


def calculate_expectancy_from_trades(
    winning_pnls: List[float],
    losing_pnls: List[float]
) -> float:
    """
    Calculate Expectancy from trade PnL lists.
    
    Args:
        winning_pnls: List of positive PnL values
        losing_pnls: List of negative PnL values
        
    Returns:
        Expected value per trade
    """
    total_trades = len(winning_pnls) + len(losing_pnls)
    
    if total_trades == 0:
        return 0.0
    
    win_rate = len(winning_pnls) / total_trades
    
    avg_win = sum(winning_pnls) / len(winning_pnls) if winning_pnls else 0
    avg_loss = abs(sum(losing_pnls) / len(losing_pnls)) if losing_pnls else 0
    
    return calculate_expectancy(win_rate, avg_win, avg_loss)


# ===========================================
# Average Trade Return (S1.4B)
# ===========================================

def calculate_avg_trade_return(
    total_pnl: float,
    trades_count: int
) -> float:
    """
    Calculate average return per trade.
    
    Args:
        total_pnl: Total net PnL
        trades_count: Number of trades
        
    Returns:
        Average PnL per trade
    """
    if trades_count <= 0:
        return 0.0
    
    return total_pnl / trades_count


# ===========================================
# Max Drawdown (S1.4C)
# ===========================================

def calculate_max_drawdown(
    equity_values: List[float]
) -> Tuple[float, int, int]:
    """
    Calculate Maximum Drawdown from equity curve.
    
    Max Drawdown = (peak - trough) / peak
    
    Args:
        equity_values: List of equity values
        
    Returns:
        Tuple of (max_drawdown_pct, peak_index, trough_index)
    """
    if len(equity_values) < 2:
        return 0.0, 0, 0
    
    peak = equity_values[0]
    peak_idx = 0
    max_dd = 0.0
    max_dd_peak_idx = 0
    max_dd_trough_idx = 0
    
    for i, value in enumerate(equity_values):
        if value > peak:
            peak = value
            peak_idx = i
        
        if peak > 0:
            dd = (peak - value) / peak
            if dd > max_dd:
                max_dd = dd
                max_dd_peak_idx = peak_idx
                max_dd_trough_idx = i
    
    return max_dd, max_dd_peak_idx, max_dd_trough_idx


def calculate_max_drawdown_value(equity_values: List[float]) -> float:
    """
    Calculate Maximum Drawdown percentage.
    
    Args:
        equity_values: List of equity values
        
    Returns:
        Max drawdown as decimal (e.g., 0.15 for 15%)
    """
    max_dd, _, _ = calculate_max_drawdown(equity_values)
    return max_dd


# ===========================================
# Average Drawdown (S1.4C)
# ===========================================

def calculate_avg_drawdown(
    equity_values: List[float]
) -> float:
    """
    Calculate Average Drawdown from equity curve.
    
    Mean of all drawdown values (when in drawdown).
    
    Args:
        equity_values: List of equity values
        
    Returns:
        Average drawdown as decimal
    """
    if len(equity_values) < 2:
        return 0.0
    
    peak = equity_values[0]
    drawdowns = []
    
    for value in equity_values:
        if value > peak:
            peak = value
        
        if peak > 0:
            dd = (peak - value) / peak
            if dd > 0:
                drawdowns.append(dd)
    
    if not drawdowns:
        return 0.0
    
    return sum(drawdowns) / len(drawdowns)


# ===========================================
# Drawdown Duration (S1.4C)
# ===========================================

def calculate_max_drawdown_duration(
    equity_values: List[float]
) -> int:
    """
    Calculate Maximum Drawdown Duration (bars to recovery).
    
    Args:
        equity_values: List of equity values
        
    Returns:
        Number of periods in longest drawdown
    """
    if len(equity_values) < 2:
        return 0
    
    peak = equity_values[0]
    current_duration = 0
    max_duration = 0
    
    for value in equity_values:
        if value >= peak:
            # New high or recovery
            peak = value
            max_duration = max(max_duration, current_duration)
            current_duration = 0
        else:
            # In drawdown
            current_duration += 1
    
    # Check if still in drawdown at end
    max_duration = max(max_duration, current_duration)
    
    return max_duration


# ===========================================
# Recovery Factor (S1.4C)
# ===========================================

def calculate_recovery_factor(
    net_profit: float,
    max_drawdown_value: float
) -> float:
    """
    Calculate Recovery Factor.
    
    Recovery Factor = Net Profit / Max Drawdown
    
    Shows how efficiently the strategy recovers from drawdowns.
    
    Args:
        net_profit: Total net profit (absolute value)
        max_drawdown_value: Max drawdown (absolute value, not percentage)
        
    Returns:
        Recovery Factor
    """
    if max_drawdown_value <= 0:
        return float('inf') if net_profit > 0 else 0.0
    
    return net_profit / max_drawdown_value


def calculate_recovery_factor_from_equity(
    equity_values: List[float],
    initial_capital: float
) -> float:
    """
    Calculate Recovery Factor from equity curve.
    
    Args:
        equity_values: List of equity values
        initial_capital: Starting capital
        
    Returns:
        Recovery Factor
    """
    if len(equity_values) < 2 or initial_capital <= 0:
        return 0.0
    
    final_equity = equity_values[-1]
    net_profit = final_equity - initial_capital
    
    # Calculate max drawdown in absolute terms
    max_dd_pct = calculate_max_drawdown_value(equity_values)
    
    # Convert percentage to value at the point of max drawdown
    # Find peak value
    peak = max(equity_values)
    max_dd_value = peak * max_dd_pct
    
    return calculate_recovery_factor(net_profit, max_dd_value)


# ===========================================
# Calmar Ratio (S1.4C)
# ===========================================

def calculate_calmar_ratio(
    annual_return: float,
    max_drawdown: float
) -> float:
    """
    Calculate Calmar Ratio.
    
    Calmar = Annual Return / Max Drawdown
    
    Often preferred over Sharpe for trading strategies.
    
    Args:
        annual_return: Annualized return (as decimal, e.g., 0.20 for 20%)
        max_drawdown: Maximum drawdown (as decimal, e.g., 0.10 for 10%)
        
    Returns:
        Calmar Ratio
    """
    if max_drawdown <= 0:
        return float('inf') if annual_return > 0 else 0.0
    
    return annual_return / max_drawdown


def calculate_calmar_ratio_from_equity(
    equity_values: List[float],
    trading_days: int,
    trading_days_per_year: int = DEFAULT_TRADING_DAYS_PER_YEAR
) -> float:
    """
    Calculate Calmar Ratio from equity curve.
    
    Args:
        equity_values: List of equity values
        trading_days: Number of days in simulation
        trading_days_per_year: Days per year for annualization
        
    Returns:
        Calmar Ratio
    """
    if len(equity_values) < 2 or trading_days <= 0:
        return 0.0
    
    initial = equity_values[0]
    final = equity_values[-1]
    
    if initial <= 0:
        return 0.0
    
    # Total return
    total_return = (final - initial) / initial
    
    # Years
    years = trading_days / trading_days_per_year
    
    if years <= 0:
        return 0.0
    
    # Annual return (CAGR)
    try:
        annual_return = (1 + total_return) ** (1 / years) - 1
    except (ValueError, ZeroDivisionError):
        annual_return = 0.0
    
    # Max drawdown
    max_dd = calculate_max_drawdown_value(equity_values)
    
    return calculate_calmar_ratio(annual_return, max_dd)


# ===========================================
# Volatility (S1.4B)
# ===========================================

def calculate_volatility(
    equity_values: List[float],
    trading_days_per_year: int = DEFAULT_TRADING_DAYS_PER_YEAR
) -> float:
    """
    Calculate annualized volatility from equity curve.
    
    Volatility = StdDev(returns) * sqrt(trading_days_per_year)
    
    Args:
        equity_values: List of equity values
        trading_days_per_year: Days per year for annualization
        
    Returns:
        Annualized volatility as decimal
    """
    returns = calculate_returns_from_equity(equity_values)
    
    if len(returns) < 2:
        return 0.0
    
    std_dev = calculate_std_deviation(returns)
    
    return std_dev * math.sqrt(trading_days_per_year)


# ===========================================
# CAGR (S1.4B)
# ===========================================

def calculate_cagr(
    initial_value: float,
    final_value: float,
    years: float
) -> float:
    """
    Calculate Compound Annual Growth Rate.
    
    CAGR = (Final/Initial)^(1/years) - 1
    
    Args:
        initial_value: Starting value
        final_value: Ending value
        years: Number of years
        
    Returns:
        CAGR as decimal (e.g., 0.15 for 15%)
    """
    if initial_value <= 0 or final_value <= 0 or years <= 0:
        return 0.0
    
    try:
        cagr = (final_value / initial_value) ** (1 / years) - 1
        return cagr
    except (ValueError, ZeroDivisionError):
        return 0.0
