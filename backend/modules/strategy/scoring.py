"""Signal Scoring Engine — Alpha + Execution + Regime

Week 4: Strategy Allocator V2

Scoring formula:
score = alpha * 0.4 + performance * 0.4 + execution * 0.2
score *= regime_bonus
"""

from typing import Dict, Any
from .types import Signal, StrategyStats


def score_signal(
    signal: Signal,
    stats: StrategyStats,
    execution: Dict[str, Any],
    regime: str
) -> float:
    """
    Calculate signal score (0..1).
    
    Args:
        signal: Trading signal
        stats: Strategy performance stats
        execution: {slippage_bps, latency_ms}
        regime: "trend" | "chop" | "high_vol"
    
    Returns:
        Score 0..1 (higher is better)
    """
    # 1. Alpha (signal quality)
    alpha = signal.confidence
    
    # 2. Strategy performance (handle both dict and object)
    if isinstance(stats, dict):
        win_rate = stats.get("win_rate", 0.5)
        sharpe = stats.get("sharpe", 0.0)
        recent_pnl = stats.get("recent_pnl", 0.0)
    else:
        win_rate = getattr(stats, "win_rate", 0.5)
        sharpe = getattr(stats, "sharpe", 0.0)
        recent_pnl = getattr(stats, "recent_pnl", 0.0)
    
    perf = (
        win_rate * 0.4 +
        max(sharpe, 0) * 0.3 +
        max(recent_pnl, 0) * 0.3
    )
    
    # 3. Execution penalty
    # slippage_bps: 0-20 (0 = best, 20 = worst)
    slippage_bps = execution.get("slippage_bps", 5)
    exec_penalty = min(slippage_bps / 20, 1.0)  # normalize to 0..1
    exec_score = 1 - exec_penalty
    
    # 4. Regime fit bonus/penalty
    regime_bonus = get_regime_bonus(signal.source, regime)
    
    # Combine
    score = (
        alpha * 0.4 +
        perf * 0.4 +
        exec_score * 0.2
    )
    score *= regime_bonus
    
    # Clamp to [0, 1]
    return max(min(score, 1.0), 0.0)


def get_regime_bonus(strategy_name: str, regime: str) -> float:
    """
    Get regime fit bonus/penalty.
    
    Args:
        strategy_name: Name of strategy
        regime: Current market regime
    
    Returns:
        Multiplier (0.6 - 1.5)
    """
    # Regime fit matrix
    # trend strategies work well in trend, poorly in chop
    # mean reversion works well in chop, poorly in trend
    
    if regime == "chop":
        if "trend" in strategy_name.lower():
            return 0.6  # penalty
        if "mean" in strategy_name.lower() or "reversion" in strategy_name.lower():
            return 1.3  # bonus
    
    if regime == "trend":
        if "trend" in strategy_name.lower():
            return 1.5  # strong bonus
        if "mean" in strategy_name.lower():
            return 0.7  # penalty
    
    if regime == "high_vol":
        # Most strategies struggle in high vol
        return 0.8
    
    # Default: neutral
    return 1.0
