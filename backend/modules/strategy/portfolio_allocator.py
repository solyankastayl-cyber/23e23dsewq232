"""
Portfolio Allocator
===================

Phase 2.4: Allocates signals within constraints.

NOT "top N" selection.
System decides how many positions to take (0..max) based on:
- Signal score thresholds
- Position limits (total, per-cluster, per-symbol)
- Risk budget

Architecture:
  Filter → Apply Constraints → Select Valid Set
"""

import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)


def filter_signals(
    ranked_signals: List[Dict[str, Any]],
    min_signal_score: float = 0.55,
    max_spread_bps: float = 500.0,
    min_volume: float = 100_000.0
) -> tuple[List[Dict[str, Any]], Dict[str, int]]:
    """
    Filter out low-quality signals.
    
    Args:
        ranked_signals: Sorted by score (descending)
        min_signal_score: Minimum score threshold
        max_spread_bps: Maximum spread in basis points
        min_volume: Minimum 24h volume in USD
        
    Returns:
        (filtered_signals, rejected_counts)
    """
    filtered = []
    rejected = {
        "low_score": 0,
        "high_spread": 0,
        "low_volume": 0,
    }
    
    for signal in ranked_signals:
        # Check score
        if signal.get("score", 0) < min_signal_score:
            rejected["low_score"] += 1
            continue
        
        # Check spread
        if signal.get("spread_bps", 0) > max_spread_bps:
            rejected["high_spread"] += 1
            continue
        
        # Check volume
        if signal.get("volume_24h", 0) < min_volume:
            rejected["low_volume"] += 1
            continue
        
        filtered.append(signal)
    
    logger.info(
        f"[Filter] {len(filtered)}/{len(ranked_signals)} passed filters, "
        f"rejected: {sum(rejected.values())}"
    )
    
    return filtered, rejected


def get_cluster(symbol: str) -> str:
    """
    Classify symbol into cluster.
    
    Simple classification:
    - majors: BTC, ETH
    - alt_l1: SOL, BNB, ADA, AVAX
    - defi: LINK, etc.
    - other
    """
    if symbol in ["BTCUSDT", "ETHUSDT"]:
        return "majors"
    elif symbol in ["SOLUSDT", "BNBUSDT", "ADAUSDT", "AVAXUSDT"]:
        return "alt_l1"
    elif symbol in ["LINKUSDT", "UNIUSDT", "AAVEUSDT"]:
        return "defi"
    else:
        return "other"


def allocate_signals(
    filtered_signals: List[Dict[str, Any]],
    max_open_positions: int = 5,
    max_per_cluster: int = 2,
    max_per_symbol: int = 1,
    max_total_risk: float = 0.30,
    default_risk_cost: float = 0.05
) -> tuple[List[Dict[str, Any]], Dict[str, int]]:
    """
    Allocate signals within constraints.
    
    System decides how many to select (0..max_open_positions).
    
    Args:
        filtered_signals: Pre-filtered signals (sorted by score)
        max_open_positions: Maximum total positions
        max_per_cluster: Maximum positions per cluster
        max_per_symbol: Maximum positions per symbol
        max_total_risk: Maximum total risk budget (0.0-1.0)
        default_risk_cost: Risk cost per position if not specified
        
    Returns:
        (selected_signals, rejection_reasons)
    """
    selected = []
    cluster_counts = {}
    symbol_counts = {}
    used_risk = 0.0
    
    rejected = {
        "max_positions": 0,
        "cluster_limit": 0,
        "symbol_limit": 0,
        "risk_limit": 0,
    }
    
    for signal in filtered_signals:
        symbol = signal["symbol"]
        cluster = get_cluster(symbol)
        risk_cost = signal.get("risk_cost", default_risk_cost)
        
        # Constraint 1: Max total positions
        if len(selected) >= max_open_positions:
            rejected["max_positions"] += 1
            continue
        
        # Constraint 2: Max per cluster
        if cluster_counts.get(cluster, 0) >= max_per_cluster:
            rejected["cluster_limit"] += 1
            continue
        
        # Constraint 3: Max per symbol
        if symbol_counts.get(symbol, 0) >= max_per_symbol:
            rejected["symbol_limit"] += 1
            continue
        
        # Constraint 4: Risk budget
        if used_risk + risk_cost > max_total_risk:
            rejected["risk_limit"] += 1
            continue
        
        # All constraints passed - select signal
        selected_signal = {
            **signal,
            "cluster": cluster,
            "risk_cost": risk_cost,
            "reason_selected": "passed_constraints",
        }
        
        selected.append(selected_signal)
        cluster_counts[cluster] = cluster_counts.get(cluster, 0) + 1
        symbol_counts[symbol] = symbol_counts.get(symbol, 0) + 1
        used_risk += risk_cost
    
    logger.info(
        f"[Allocator] Selected {len(selected)}/{len(filtered_signals)} signals, "
        f"risk_used={used_risk:.2f}/{max_total_risk:.2f}"
    )
    
    return selected, rejected


def get_cluster_distribution(selected_signals: List[Dict[str, Any]]) -> Dict[str, int]:
    """Get distribution of signals across clusters."""
    distribution = {}
    for signal in selected_signals:
        cluster = signal.get("cluster", "unknown")
        distribution[cluster] = distribution.get(cluster, 0) + 1
    return distribution
