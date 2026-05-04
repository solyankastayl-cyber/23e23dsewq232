"""
PHASE 2.9.1 — Calibration Matrix

Multi-dimensional performance matrix across:
- Asset (symbol)
- Cluster
- Timeframe
- Regime
- Strategy / Setup Type

Metrics per cell:
- win_rate
- profit_factor
- expectancy
- drawdown
- sample_size
- wrong_early_rate
- tradeability_rate
- stability_score
"""

from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
import math


@dataclass
class MatrixCell:
    """Single cell in calibration matrix."""
    trades: int = 0
    wins: int = 0
    losses: int = 0
    gross_profit: float = 0.0
    gross_loss: float = 0.0
    total_pnl: float = 0.0
    wrong_early: int = 0
    late_entry: int = 0
    tradeable: int = 0
    pnls: List[float] = None
    
    def __post_init__(self):
        if self.pnls is None:
            self.pnls = []


class CalibrationMatrix:
    """
    Multi-dimensional performance matrix for calibration.
    
    Keys: (symbol, cluster, timeframe, regime, strategy)
    Values: performance metrics
    """
    
    def build(self, trades: List[Dict]) -> Dict[Tuple, Dict]:
        """
        Build calibration matrix from trades.
        
        Args:
            trades: List of trade dicts with:
                - symbol
                - cluster
                - timeframe
                - regime
                - strategy (optional)
                - pnl
                - win (bool)
                - wrong_early (bool, optional)
                - late_entry (bool, optional)
                - tradeable (bool, optional)
        
        Returns:
            Matrix dict: {(symbol, cluster, timeframe, regime, strategy): metrics}
        """
        matrix: Dict[Tuple, MatrixCell] = {}
        
        for t in trades:
            key = self._extract_key(t)
            
            if key not in matrix:
                matrix[key] = MatrixCell()
            
            cell = matrix[key]
            pnl = t.get("pnl", 0)
            
            cell.trades += 1
            cell.total_pnl += pnl
            cell.pnls.append(pnl)
            
            # Win/Loss tracking
            if t.get("win", pnl > 0):
                cell.wins += 1
                cell.gross_profit += max(0, pnl)
            else:
                cell.losses += 1
                cell.gross_loss += abs(min(0, pnl))
            
            # Error tracking
            if t.get("wrong_early", False):
                cell.wrong_early += 1
            
            if t.get("late_entry", False):
                cell.late_entry += 1
            
            if t.get("tradeable", True):
                cell.tradeable += 1
        
        # Convert to final metrics
        return {key: self._compute_metrics(cell) for key, cell in matrix.items()}
    
    def _extract_key(self, trade: Dict) -> Tuple:
        """Extract matrix key from trade."""
        return (
            trade.get("symbol", "UNKNOWN"),
            trade.get("cluster", "other"),
            trade.get("timeframe", "4H"),
            trade.get("regime", "unknown"),
            trade.get("strategy", "default")
        )
    
    def _compute_metrics(self, cell: MatrixCell) -> Dict:
        """Compute all metrics for a matrix cell."""
        trades = cell.trades
        wins = cell.wins
        losses = cell.losses
        
        # Basic rates
        win_rate = wins / trades if trades > 0 else 0
        
        # Profit Factor
        if cell.gross_loss > 0:
            profit_factor = cell.gross_profit / cell.gross_loss
        elif cell.gross_profit > 0:
            profit_factor = float("inf")
        else:
            profit_factor = 0
        
        # Expectancy
        avg_win = cell.gross_profit / wins if wins > 0 else 0
        avg_loss = cell.gross_loss / losses if losses > 0 else 0
        expectancy = win_rate * avg_win - (1 - win_rate) * avg_loss
        
        # Drawdown (max cumulative loss from peak)
        drawdown = self._compute_drawdown(cell.pnls)
        
        # Wrong Early Rate
        wrong_early_rate = cell.wrong_early / trades if trades > 0 else 0
        
        # Tradeability Rate
        tradeability_rate = cell.tradeable / trades if trades > 0 else 1
        
        # Stability Score (inverse of PnL variance)
        stability = self._compute_stability(cell.pnls)
        
        return {
            "trades": trades,
            "wins": wins,
            "losses": losses,
            "win_rate": round(win_rate, 4),
            "profit_factor": round(profit_factor, 4) if profit_factor != float("inf") else "inf",
            "expectancy": round(expectancy, 4),
            "total_pnl": round(cell.total_pnl, 2),
            "avg_pnl": round(cell.total_pnl / trades, 2) if trades > 0 else 0,
            "avg_win": round(avg_win, 2),
            "avg_loss": round(avg_loss, 2),
            "drawdown": round(drawdown, 4),
            "wrong_early_rate": round(wrong_early_rate, 4),
            "tradeability_rate": round(tradeability_rate, 4),
            "stability_score": round(stability, 4),
            "sample_size": trades
        }
    
    def _compute_drawdown(self, pnls: List[float]) -> float:
        """Compute maximum drawdown from PnL series."""
        if not pnls:
            return 0
        
        cumulative = 0
        peak = 0
        max_dd = 0
        
        for pnl in pnls:
            cumulative += pnl
            if cumulative > peak:
                peak = cumulative
            dd = peak - cumulative
            if dd > max_dd:
                max_dd = dd
        
        return max_dd / peak if peak > 0 else 0
    
    def _compute_stability(self, pnls: List[float]) -> float:
        """
        Compute stability score.
        
        Higher = more stable (lower variance).
        Range: 0-1
        """
        if len(pnls) < 2:
            return 0.5
        
        mean = sum(pnls) / len(pnls)
        variance = sum((p - mean) ** 2 for p in pnls) / len(pnls)
        std = math.sqrt(variance)
        
        # Normalize: lower std = higher stability
        # Use coefficient of variation
        cv = std / abs(mean) if mean != 0 else 1
        
        # Convert to 0-1 score (lower CV = higher stability)
        stability = 1 / (1 + cv)
        
        return stability
    
    def aggregate_by(self, matrix: Dict, dimension: str) -> Dict:
        """
        Aggregate matrix by single dimension.
        
        Args:
            matrix: Full calibration matrix
            dimension: 'symbol', 'cluster', 'timeframe', 'regime', 'strategy'
        
        Returns:
            Aggregated metrics per dimension value
        """
        dim_index = {
            "symbol": 0,
            "cluster": 1,
            "timeframe": 2,
            "regime": 3,
            "strategy": 4
        }
        
        idx = dim_index.get(dimension, 0)
        
        aggregated: Dict[str, List[Dict]] = {}
        
        for key, metrics in matrix.items():
            dim_value = key[idx]
            if dim_value not in aggregated:
                aggregated[dim_value] = []
            aggregated[dim_value].append(metrics)
        
        # Combine metrics for each dimension value
        result = {}
        for dim_value, metrics_list in aggregated.items():
            combined = self._combine_metrics(metrics_list)
            result[dim_value] = combined
        
        return result
    
    def _combine_metrics(self, metrics_list: List[Dict]) -> Dict:
        """Combine multiple metric dicts into one."""
        if not metrics_list:
            return {}
        
        total_trades = sum(m["trades"] for m in metrics_list)
        total_wins = sum(m["wins"] for m in metrics_list)
        total_losses = sum(m["losses"] for m in metrics_list)
        total_pnl = sum(m["total_pnl"] for m in metrics_list)
        total_gross_profit = sum(m["avg_win"] * m["wins"] for m in metrics_list)
        total_gross_loss = sum(m["avg_loss"] * m["losses"] for m in metrics_list)
        
        win_rate = total_wins / total_trades if total_trades > 0 else 0
        
        if total_gross_loss > 0:
            pf = total_gross_profit / total_gross_loss
        elif total_gross_profit > 0:
            pf = float("inf")
        else:
            pf = 0
        
        # Compute expectancy
        avg_win = total_gross_profit / total_wins if total_wins > 0 else 0
        avg_loss = total_gross_loss / total_losses if total_losses > 0 else 0
        expectancy = win_rate * avg_win - (1 - win_rate) * avg_loss
        
        avg_stability = sum(m["stability_score"] for m in metrics_list) / len(metrics_list)
        avg_wrong_early = sum(m["wrong_early_rate"] * m["trades"] for m in metrics_list) / total_trades if total_trades > 0 else 0
        
        return {
            "trades": total_trades,
            "wins": total_wins,
            "losses": total_losses,
            "win_rate": round(win_rate, 4),
            "profit_factor": round(pf, 4) if pf != float("inf") else "inf",
            "expectancy": round(expectancy, 4),
            "total_pnl": round(total_pnl, 2),
            "avg_pnl": round(total_pnl / total_trades, 2) if total_trades > 0 else 0,
            "avg_win": round(avg_win, 2),
            "avg_loss": round(avg_loss, 2),
            "stability_score": round(avg_stability, 4),
            "wrong_early_rate": round(avg_wrong_early, 4),
            "sample_size": total_trades
        }
