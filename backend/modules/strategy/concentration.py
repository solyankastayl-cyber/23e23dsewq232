"""Concentration Limits — Portfolio risk constraints

Prevent over-concentration in symbols, strategies, or sectors.
"""

from typing import Tuple
import logging

logger = logging.getLogger(__name__)


def check_concentration_limits(
    symbol: str,
    strategy: str,
    proposed_size_usd: float,
    portfolio: dict,
    strategy_capital_map: dict,
    symbol_capital_map: dict,
    equity: float,
    max_symbol_pct: float = 0.20,
    max_strategy_pct: float = 0.35,
    max_total_heat: float = 0.70
) -> Tuple[bool, str]:
    """
    Check if proposed position violates concentration limits.
    
    Args:
        symbol: Symbol to check
        strategy: Strategy name
        proposed_size_usd: Proposed position size in USD
        portfolio: Current portfolio state
        strategy_capital_map: Current capital per strategy
        symbol_capital_map: Current capital per symbol
        equity: Total equity
        max_symbol_pct: Max % of equity per symbol (default 20%)
        max_strategy_pct: Max % of equity per strategy (default 35%)
        max_total_heat: Max total heat (default 70%)
    
    Returns:
        (ok: bool, reason: str)
    """
    symbol_cap = equity * max_symbol_pct
    strategy_cap = equity * max_strategy_pct
    total_heat_cap = equity * max_total_heat
    
    # Check symbol concentration
    current_symbol_capital = symbol_capital_map.get(symbol, 0.0)
    if current_symbol_capital + proposed_size_usd > symbol_cap:
        logger.warning(
            f"[Concentration] Symbol limit exceeded: {symbol} "
            f"(current={current_symbol_capital:.2f}, proposed={proposed_size_usd:.2f}, cap={symbol_cap:.2f})"
        )
        return False, f"SYMBOL_CONCENTRATION_LIMIT:{symbol}"
    
    # Check strategy concentration
    current_strategy_capital = strategy_capital_map.get(strategy, 0.0)
    if current_strategy_capital + proposed_size_usd > strategy_cap:
        logger.warning(
            f"[Concentration] Strategy limit exceeded: {strategy} "
            f"(current={current_strategy_capital:.2f}, proposed={proposed_size_usd:.2f}, cap={strategy_cap:.2f})"
        )
        return False, f"STRATEGY_CONCENTRATION_LIMIT:{strategy}"
    
    # Check total heat
    gross_exposure = portfolio.get('gross_exposure', 0.0)
    if gross_exposure + proposed_size_usd > total_heat_cap:
        logger.warning(
            f"[Concentration] Total heat limit exceeded: "
            f"(current={gross_exposure:.2f}, proposed={proposed_size_usd:.2f}, cap={total_heat_cap:.2f})"
        )
        return False, "TOTAL_HEAT_LIMIT"
    
    return True, "OK"


def calculate_concentration_score(
    symbol_capital_map: dict,
    strategy_capital_map: dict,
    equity: float
) -> float:
    """
    Calculate overall concentration score (0..1).
    
    Lower is better (more diversified).
    
    Returns:
        Concentration score (0 = perfect diversification, 1 = max concentration)
    """
    if equity <= 0:
        return 0.0
    
    # Symbol concentration (Herfindahl index)
    symbol_shares = [v / equity for v in symbol_capital_map.values() if v > 0]
    symbol_hhi = sum(s**2 for s in symbol_shares)
    
    # Strategy concentration
    strategy_shares = [v / equity for v in strategy_capital_map.values() if v > 0]
    strategy_hhi = sum(s**2 for s in strategy_shares)
    
    # Average concentration
    concentration = (symbol_hhi + strategy_hhi) / 2
    
    return min(concentration, 1.0)
