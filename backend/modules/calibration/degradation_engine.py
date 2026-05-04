"""
PHASE 2.9.3 — Degradation Engine

Detects where edge is disappearing:
- Rolling performance comparison
- Win rate decline
- Profit factor decay
- Drawdown increase

Answers: "Where is the system degrading?"
"""

from typing import Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime


@dataclass
class DegradationSignal:
    """Signal indicating degradation in a dimension."""
    key: str
    is_degrading: bool
    trend: float  # Negative = degrading
    severity: str  # "mild", "moderate", "severe"
    metric: str  # Which metric is degrading
    current_value: float
    baseline_value: float


class DegradationEngine:
    """
    Detects performance degradation across dimensions.
    
    Uses rolling windows to compare recent vs historical performance.
    """
    
    def __init__(self, window_size: int = 50, min_samples: int = 20):
        """
        Args:
            window_size: Size of rolling windows
            min_samples: Minimum samples needed per window
        """
        self.window_size = window_size
        self.min_samples = min_samples
    
    def detect(self, historical_stats: Dict[str, List[Dict]]) -> Dict[str, Dict]:
        """
        Detect degradation from historical stats.
        
        Args:
            historical_stats: {key: [list of period stats]}
                Each period stat: {win_rate, pf, drawdown, trades, timestamp}
        
        Returns:
            {key: {degrading, trend, severity, details}}
        """
        degradation = {}
        
        for key, history in historical_stats.items():
            if len(history) < 2:
                degradation[key] = {
                    "degrading": False,
                    "trend": 0,
                    "severity": "none",
                    "reason": "insufficient_data"
                }
                continue
            
            signal = self._analyze_trend(key, history)
            
            degradation[key] = {
                "degrading": signal.is_degrading,
                "trend": round(signal.trend, 4),
                "severity": signal.severity,
                "metric": signal.metric,
                "current": signal.current_value,
                "baseline": signal.baseline_value,
                "samples": len(history)
            }
        
        return degradation
    
    def detect_from_trades(self, trades: List[Dict], group_by: str = "symbol") -> Dict[str, Dict]:
        """
        Detect degradation directly from trades.
        
        Args:
            trades: List of trades with timestamps
            group_by: 'symbol', 'cluster', 'regime'
        
        Returns:
            Degradation signals per group
        """
        # Group trades
        grouped: Dict[str, List[Dict]] = {}
        for t in trades:
            key = t.get(group_by, "unknown")
            if key not in grouped:
                grouped[key] = []
            grouped[key].append(t)
        
        # Convert to historical stats (split into windows)
        historical = {}
        for key, key_trades in grouped.items():
            # Sort by timestamp
            sorted_trades = sorted(key_trades, key=lambda x: x.get("timestamp", ""))
            
            # Split into windows
            windows = []
            for i in range(0, len(sorted_trades), self.window_size):
                window = sorted_trades[i:i + self.window_size]
                if len(window) >= self.min_samples:
                    stats = self._compute_window_stats(window)
                    windows.append(stats)
            
            if len(windows) >= 2:
                historical[key] = windows
        
        return self.detect(historical)
    
    def _compute_window_stats(self, trades: List[Dict]) -> Dict:
        """Compute stats for a window of trades."""
        total = len(trades)
        wins = sum(1 for t in trades if t.get("win", t.get("pnl", 0) > 0))
        
        pnls = [t.get("pnl", 0) for t in trades]
        gross_profit = sum(p for p in pnls if p > 0)
        gross_loss = abs(sum(p for p in pnls if p < 0))
        
        win_rate = wins / total if total > 0 else 0
        pf = gross_profit / gross_loss if gross_loss > 0 else (float("inf") if gross_profit > 0 else 0)
        
        # Compute drawdown
        cumulative = 0
        peak = 0
        max_dd = 0
        for pnl in pnls:
            cumulative += pnl
            peak = max(peak, cumulative)
            max_dd = max(max_dd, peak - cumulative)
        
        drawdown = max_dd / peak if peak > 0 else 0
        
        return {
            "win_rate": win_rate,
            "profit_factor": pf if pf != float("inf") else 10,
            "drawdown": drawdown,
            "trades": total,
            "timestamp": trades[-1].get("timestamp") if trades else None
        }
    
    def _analyze_trend(self, key: str, history: List[Dict]) -> DegradationSignal:
        """Analyze trend in historical stats."""
        # Compare first half vs second half
        mid = len(history) // 2
        if mid == 0:
            mid = 1
        
        early = history[:mid]
        recent = history[mid:]
        
        # Compute averages
        early_wr = sum(h["win_rate"] for h in early) / len(early)
        recent_wr = sum(h["win_rate"] for h in recent) / len(recent)
        
        early_pf = sum(min(h["profit_factor"], 10) for h in early) / len(early)
        recent_pf = sum(min(h["profit_factor"], 10) for h in recent) / len(recent)
        
        early_dd = sum(h["drawdown"] for h in early) / len(early)
        recent_dd = sum(h["drawdown"] for h in recent) / len(recent)
        
        # Find most significant degradation
        wr_trend = recent_wr - early_wr
        pf_trend = recent_pf - early_pf
        dd_trend = recent_dd - early_dd  # Positive = worse
        
        # Determine which metric is degrading most
        degradations = [
            ("win_rate", wr_trend, early_wr, recent_wr),
            ("profit_factor", pf_trend, early_pf, recent_pf),
            ("drawdown", -dd_trend, early_dd, recent_dd)  # Negative trend = degrading
        ]
        
        # Find worst degradation
        worst = min(degradations, key=lambda x: x[1])
        
        metric = worst[0]
        trend = worst[1]
        baseline = worst[2]
        current = worst[3]
        
        # Determine severity
        if trend < -0.2:
            severity = "severe"
        elif trend < -0.1:
            severity = "moderate"
        elif trend < -0.05:
            severity = "mild"
        else:
            severity = "none"
        
        is_degrading = trend < -0.05
        
        return DegradationSignal(
            key=key,
            is_degrading=is_degrading,
            trend=trend,
            severity=severity,
            metric=metric,
            current_value=current,
            baseline_value=baseline
        )
    
    def get_degrading_keys(self, degradation: Dict[str, Dict]) -> List[str]:
        """Get list of keys that are degrading."""
        return [k for k, v in degradation.items() if v.get("degrading", False)]
    
    def get_severe_degradations(self, degradation: Dict[str, Dict]) -> List[str]:
        """Get list of keys with severe degradation."""
        return [k for k, v in degradation.items() if v.get("severity") == "severe"]
