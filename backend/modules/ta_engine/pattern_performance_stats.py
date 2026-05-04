"""
Pattern Performance Stats — Self-Learning Weights
==================================================

Aggregates historical performance to generate adaptive weights.

Key concept:
- Patterns with higher win rates get higher weights
- This creates a self-improving feedback loop

Weight calculation:
- Base weight = 1.0
- Range: 0.7 - 1.3
- Uses Bayesian smoothing for small samples
"""

from typing import Dict, List, Optional


def safe_winrate(wins: int, total: int, prior: float = 0.5) -> float:
    """
    Calculate smoothed win rate using Bayesian smoothing.
    
    This prevents extreme values with small sample sizes.
    
    Formula: (wins + α) / (total + α + β)
    where α = prior * k, β = (1-prior) * k, k = 4
    
    Args:
        wins: Number of wins
        total: Total number of outcomes
        prior: Prior probability (default 0.5 = neutral)
    
    Returns:
        Smoothed win rate [0, 1]
    """
    k = 4  # Strength of prior
    alpha = prior * k
    beta = (1 - prior) * k
    
    return (wins + alpha) / (total + k)


def performance_weight(winrate: float) -> float:
    """
    Convert win rate to weight multiplier.
    
    Base = 1.0 at 50% win rate
    Range: 0.7 (at 0% wr) to 1.3 (at 100% wr)
    
    Formula: 0.7 + (winrate * 0.6)
    """
    return 0.7 + (winrate * 0.6)


def build_performance_stats(setups: List[Dict]) -> Dict[str, Dict]:
    """
    Build performance statistics from historical setups.
    
    Groups by: pattern_type | regime
    
    Args:
        setups: List of closed setup records
    
    Returns:
        {
            "rectangle|range": {"wins": 10, "total": 15, "winrate": 0.67, "weight": 1.1},
            "triangle|trending": {"wins": 8, "total": 12, "winrate": 0.67, "weight": 1.1},
            ...
        }
    """
    stats = {}
    
    for s in setups:
        # Skip active setups
        if s.get("status") == "active":
            continue
        
        pattern_type = s.get("pattern_type", "unknown")
        regime = s.get("regime", "unknown")
        
        # Primary key: pattern_type | regime
        key = f"{pattern_type}|{regime}"
        
        if key not in stats:
            stats[key] = {"wins": 0, "total": 0, "losses": 0}
        
        stats[key]["total"] += 1
        
        if s.get("status") == "win":
            stats[key]["wins"] += 1
        elif s.get("status") == "loss":
            stats[key]["losses"] += 1
    
    # Calculate winrate and weight for each group
    for key in stats:
        w = stats[key]["wins"]
        t = stats[key]["total"]
        
        # Use smoothed winrate
        wr = safe_winrate(w, t)
        stats[key]["winrate"] = round(wr, 3)
        
        # Calculate weight (only if sufficient samples)
        if t >= 5:
            stats[key]["weight"] = round(performance_weight(wr), 3)
        else:
            stats[key]["weight"] = 1.0  # Neutral weight for small samples
        
        stats[key]["sample_size"] = t
    
    return stats


def get_pattern_weight(
    pattern_type: str,
    regime: str,
    performance_stats: Dict[str, Dict],
    default_weight: float = 1.0,
    min_samples: int = 5,
) -> float:
    """
    Get adaptive weight for a pattern based on historical performance.
    
    Args:
        pattern_type: Type of pattern (e.g., "rectangle", "triangle")
        regime: Market regime (e.g., "range", "trending")
        performance_stats: Pre-computed stats from build_performance_stats()
        default_weight: Weight to use if no data available
        min_samples: Minimum samples required to use learned weight
    
    Returns:
        Weight multiplier (0.7 - 1.3)
    """
    key = f"{pattern_type}|{regime}"
    
    if key not in performance_stats:
        return default_weight
    
    stats = performance_stats[key]
    
    # Require minimum samples
    if stats.get("sample_size", 0) < min_samples:
        return default_weight
    
    return stats.get("weight", default_weight)


def compute_confidence_with_performance(
    base_confidence: float,
    pattern_type: str,
    regime: str,
    performance_stats: Dict[str, Dict],
) -> Dict:
    """
    Compute confidence adjusted by historical performance.
    
    Returns:
        {
            "base_confidence": 0.65,
            "performance_weight": 1.12,
            "adjusted_confidence": 0.73,
            "historical_winrate": 0.68,
            "sample_size": 25
        }
    """
    key = f"{pattern_type}|{regime}"
    stats = performance_stats.get(key, {})
    
    # Get weight
    perf_weight = get_pattern_weight(pattern_type, regime, performance_stats)
    
    # Adjust confidence (capped at 0.95)
    adjusted = min(0.95, base_confidence * perf_weight)
    
    return {
        "base_confidence": round(base_confidence, 3),
        "performance_weight": perf_weight,
        "adjusted_confidence": round(adjusted, 3),
        "historical_winrate": stats.get("winrate"),
        "sample_size": stats.get("sample_size", 0),
    }


def compute_probability_with_performance(
    base_probability: Dict,
    pattern_type: str,
    regime: str,
    performance_stats: Dict[str, Dict],
) -> Dict:
    """
    Adjust probability based on historical performance.
    
    If pattern historically performs well in this regime,
    boost the probability in the bias direction.
    """
    if not base_probability:
        return base_probability
    
    key = f"{pattern_type}|{regime}"
    stats = performance_stats.get(key, {})
    
    winrate = stats.get("winrate", 0.5)
    sample_size = stats.get("sample_size", 0)
    
    # Only adjust if we have enough data
    if sample_size < 5:
        return {
            **base_probability,
            "performance_adjusted": False,
        }
    
    # Calculate adjustment factor (0.9 - 1.1)
    # winrate 50% = 1.0, winrate 70% = 1.04, winrate 30% = 0.96
    adjustment = 0.9 + (winrate * 0.2)
    
    # Apply to breakout probability
    breakout_up = base_probability.get("breakout_up", 0.5)
    breakdown = base_probability.get("breakdown", 0.5)
    
    # Adjust based on historical bias
    adjusted_up = min(0.95, breakout_up * adjustment)
    adjusted_down = max(0.05, breakdown * (2 - adjustment))
    
    # Normalize
    total = adjusted_up + adjusted_down
    if total > 0:
        adjusted_up = adjusted_up / total
        adjusted_down = adjusted_down / total
    
    return {
        **base_probability,
        "breakout_up": round(adjusted_up, 2),
        "breakdown": round(adjusted_down, 2),
        "performance_adjusted": True,
        "historical_winrate": round(winrate * 100),
        "sample_size": sample_size,
    }


class PerformanceStatsManager:
    """
    Manages performance stats loading and caching.
    """
    
    def __init__(self, db):
        self.db = db
        self.cache = {}
        self.cache_ttl = 300  # 5 minutes
        self.last_update = {}
    
    def load_stats(self, symbol: str = None, force_refresh: bool = False) -> Dict:
        """Load performance stats, with caching."""
        import time
        
        cache_key = symbol or "global"
        now = time.time()
        
        # Check cache
        if not force_refresh:
            if cache_key in self.cache:
                if now - self.last_update.get(cache_key, 0) < self.cache_ttl:
                    return self.cache[cache_key]
        
        # Load from DB
        if self.db is None:
            return {}
        
        try:
            collection = self.db["pattern_performance"]
            
            query = {"status": {"$in": ["win", "loss"]}}
            if symbol:
                query["symbol"] = symbol
            
            setups = list(collection.find(query, {"_id": 0}).limit(500))
            stats = build_performance_stats(setups)
            
            # Update cache
            self.cache[cache_key] = stats
            self.last_update[cache_key] = now
            
            return stats
            
        except Exception as e:
            print(f"[PerfStats] Error loading: {e}")
            return {}
    
    def get_weight(self, pattern_type: str, regime: str, symbol: str = None) -> float:
        """Get adaptive weight for pattern."""
        stats = self.load_stats(symbol)
        return get_pattern_weight(pattern_type, regime, stats)
    
    def get_summary(self, symbol: str = None) -> Dict:
        """Get summary of all pattern performance."""
        stats = self.load_stats(symbol)
        
        if not stats:
            return {"patterns": [], "total_samples": 0}
        
        patterns = []
        total_samples = 0
        
        for key, data in stats.items():
            pattern_type, regime = key.split("|")
            total_samples += data.get("sample_size", 0)
            
            patterns.append({
                "pattern": pattern_type,
                "regime": regime,
                "winrate": round(data.get("winrate", 0.5) * 100),
                "weight": data.get("weight", 1.0),
                "samples": data.get("sample_size", 0),
            })
        
        # Sort by samples (most data first)
        patterns.sort(key=lambda x: x["samples"], reverse=True)
        
        return {
            "patterns": patterns[:10],  # Top 10
            "total_samples": total_samples,
        }


# Singleton
_stats_manager = None


def get_stats_manager(db=None):
    """Get singleton stats manager."""
    global _stats_manager
    if _stats_manager is None and db is not None:
        _stats_manager = PerformanceStatsManager(db)
    return _stats_manager


__all__ = [
    "safe_winrate",
    "performance_weight",
    "build_performance_stats",
    "get_pattern_weight",
    "compute_confidence_with_performance",
    "compute_probability_with_performance",
    "PerformanceStatsManager",
    "get_stats_manager",
]
