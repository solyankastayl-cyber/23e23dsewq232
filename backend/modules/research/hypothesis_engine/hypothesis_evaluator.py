"""
PHASE 6.1 - Hypothesis Evaluator
=================================
Evaluates hypothesis results and assigns verdicts.
"""

import math
from datetime import datetime, timezone
from typing import Dict, List, Optional
from dataclasses import dataclass

from .hypothesis_types import (
    HypothesisResult, HypothesisVerdict, HypothesisRun,
    VERDICT_THRESHOLDS
)


@dataclass
class TradeMetrics:
    """Trade metrics aggregation"""
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    gross_profit: float = 0.0
    gross_loss: float = 0.0
    returns: List[float] = None
    
    def __post_init__(self):
        if self.returns is None:
            self.returns = []


class HypothesisEvaluator:
    """
    Evaluates hypothesis test results and computes metrics
    """
    
    def __init__(self):
        self.thresholds = VERDICT_THRESHOLDS
    
    def evaluate(
        self,
        hypothesis_id: str,
        run: HypothesisRun,
        triggers: List[Dict]
    ) -> HypothesisResult:
        """
        Evaluate hypothesis run and compute metrics
        """
        
        # Filter valid triggers (exclude INCOMPLETE)
        valid_triggers = [t for t in triggers if t['outcome'] in ['WIN', 'LOSS']]
        
        if not valid_triggers:
            return self._empty_result(hypothesis_id, run.run_id)
        
        # Compute trade metrics
        metrics = self._compute_trade_metrics(valid_triggers)
        
        # Compute statistical metrics
        win_rate = metrics.winning_trades / metrics.total_trades if metrics.total_trades > 0 else 0
        
        profit_factor = (
            abs(metrics.gross_profit / metrics.gross_loss) 
            if metrics.gross_loss != 0 else 0
        )
        
        avg_return = sum(metrics.returns) / len(metrics.returns) if metrics.returns else 0
        
        # Compute expectancy: (win_rate * avg_win) - (loss_rate * avg_loss)
        avg_win = metrics.gross_profit / metrics.winning_trades if metrics.winning_trades > 0 else 0
        avg_loss = abs(metrics.gross_loss / metrics.losing_trades) if metrics.losing_trades > 0 else 0
        loss_rate = 1 - win_rate
        expectancy = (win_rate * avg_win) - (loss_rate * avg_loss)
        
        # Compute max drawdown
        max_drawdown = self._compute_max_drawdown(metrics.returns)
        
        # Compute Sharpe ratio
        sharpe = self._compute_sharpe_ratio(metrics.returns)
        
        # Compute Sortino ratio
        sortino = self._compute_sortino_ratio(metrics.returns)
        
        # Compute confidence score
        confidence = self._compute_confidence_score(
            sample_size=metrics.total_trades,
            win_rate=win_rate,
            profit_factor=profit_factor
        )
        
        # Determine verdict
        verdict, reason = self._determine_verdict(
            win_rate=win_rate,
            profit_factor=profit_factor,
            sample_size=metrics.total_trades,
            confidence=confidence,
            expectancy=expectancy
        )
        
        # Compute regime breakdown
        regime_breakdown = self._compute_regime_breakdown(valid_triggers)
        
        return HypothesisResult(
            hypothesis_id=hypothesis_id,
            run_id=run.run_id,
            win_rate=win_rate,
            profit_factor=profit_factor,
            expectancy=expectancy,
            avg_return=avg_return,
            max_drawdown=max_drawdown,
            sample_size=metrics.total_trades,
            winning_trades=metrics.winning_trades,
            losing_trades=metrics.losing_trades,
            confidence_score=confidence,
            sharpe_ratio=sharpe,
            sortino_ratio=sortino,
            verdict=verdict,
            verdict_reason=reason,
            regime_breakdown=regime_breakdown,
            computed_at=datetime.now(timezone.utc)
        )
    
    def _compute_trade_metrics(self, triggers: List[Dict]) -> TradeMetrics:
        """Compute basic trade metrics"""
        metrics = TradeMetrics()
        
        for trigger in triggers:
            metrics.total_trades += 1
            return_pct = trigger.get('return_pct', 0)
            metrics.returns.append(return_pct)
            
            if trigger['outcome'] == 'WIN':
                metrics.winning_trades += 1
                metrics.gross_profit += return_pct
            else:
                metrics.losing_trades += 1
                metrics.gross_loss += return_pct  # negative value
        
        return metrics
    
    def _compute_max_drawdown(self, returns: List[float]) -> float:
        """Compute maximum drawdown from returns series"""
        if not returns:
            return 0.0
        
        # Compute equity curve
        equity = [100.0]  # Start with 100
        for ret in returns:
            new_equity = equity[-1] * (1 + ret / 100)
            equity.append(new_equity)
        
        # Find max drawdown
        peak = equity[0]
        max_dd = 0.0
        
        for value in equity:
            if value > peak:
                peak = value
            dd = (peak - value) / peak
            if dd > max_dd:
                max_dd = dd
        
        return max_dd
    
    def _compute_sharpe_ratio(self, returns: List[float], risk_free_rate: float = 0.0) -> float:
        """Compute Sharpe ratio"""
        if len(returns) < 2:
            return 0.0
        
        mean_return = sum(returns) / len(returns)
        
        # Standard deviation
        variance = sum((r - mean_return) ** 2 for r in returns) / len(returns)
        std_dev = math.sqrt(variance) if variance > 0 else 0.0001
        
        sharpe = (mean_return - risk_free_rate) / std_dev
        return sharpe
    
    def _compute_sortino_ratio(self, returns: List[float], target_return: float = 0.0) -> float:
        """Compute Sortino ratio (only considers downside volatility)"""
        if len(returns) < 2:
            return 0.0
        
        mean_return = sum(returns) / len(returns)
        
        # Downside deviation
        negative_returns = [r for r in returns if r < target_return]
        if not negative_returns:
            return 10.0  # No negative returns = great ratio
        
        downside_variance = sum((r - target_return) ** 2 for r in negative_returns) / len(negative_returns)
        downside_std = math.sqrt(downside_variance) if downside_variance > 0 else 0.0001
        
        sortino = (mean_return - target_return) / downside_std
        return sortino
    
    def _compute_confidence_score(
        self,
        sample_size: int,
        win_rate: float,
        profit_factor: float
    ) -> float:
        """
        Compute confidence score based on sample size and consistency
        """
        # Sample size factor (more samples = more confidence)
        # 100 samples = 1.0, 50 samples = 0.7, 30 samples = 0.5
        sample_factor = min(1.0, math.log10(sample_size + 1) / 2)
        
        # Win rate factor (consistency)
        # Deviation from 0.5 base rate
        wr_deviation = abs(win_rate - 0.5)
        wr_factor = min(1.0, wr_deviation * 4)  # Max at 25% deviation
        
        # Profit factor bonus
        pf_factor = min(1.0, (profit_factor - 1) / 2) if profit_factor > 1 else 0
        
        # Combined score
        confidence = (sample_factor * 0.4) + (wr_factor * 0.3) + (pf_factor * 0.3)
        
        return min(1.0, max(0.0, confidence))
    
    def _determine_verdict(
        self,
        win_rate: float,
        profit_factor: float,
        sample_size: int,
        confidence: float,
        expectancy: float
    ) -> tuple:
        """Determine verdict based on metrics"""
        
        # Check thresholds from strictest to least strict
        for verdict_name in ["VALID", "PROMISING", "WEAK"]:
            thresholds = self.thresholds[verdict_name]
            
            if (
                win_rate >= thresholds["min_win_rate"] and
                profit_factor >= thresholds["min_profit_factor"] and
                sample_size >= thresholds["min_sample_size"] and
                confidence >= thresholds["min_confidence"]
            ):
                reasons = []
                
                if verdict_name == "VALID":
                    reasons.append(f"Strong edge: WR={win_rate:.1%}, PF={profit_factor:.2f}")
                    reasons.append(f"Sufficient samples: {sample_size}")
                elif verdict_name == "PROMISING":
                    reasons.append(f"Good potential: WR={win_rate:.1%}, PF={profit_factor:.2f}")
                    reasons.append("Needs more validation")
                else:
                    reasons.append(f"Marginal edge: WR={win_rate:.1%}, PF={profit_factor:.2f}")
                    reasons.append("Not recommended for production")
                
                return HypothesisVerdict(verdict_name), "; ".join(reasons)
        
        # Below all thresholds = REJECTED
        return (
            HypothesisVerdict.REJECTED,
            f"No edge found: WR={win_rate:.1%}, PF={profit_factor:.2f}, samples={sample_size}"
        )
    
    def _compute_regime_breakdown(self, triggers: List[Dict]) -> Dict[str, Dict]:
        """Compute metrics breakdown by regime"""
        # Group by simulated regime
        regimes = ["TREND_UP", "TREND_DOWN", "RANGE", "COMPRESSION", "EXPANSION"]
        breakdown = {}
        
        for regime in regimes:
            # Simulate regime assignment (in production, would come from trigger data)
            regime_triggers = [t for i, t in enumerate(triggers) if i % len(regimes) == regimes.index(regime)]
            
            if regime_triggers:
                wins = len([t for t in regime_triggers if t['outcome'] == 'WIN'])
                total = len(regime_triggers)
                
                breakdown[regime] = {
                    "win_rate": wins / total if total > 0 else 0,
                    "trades": total,
                    "avg_return": sum(t['return_pct'] for t in regime_triggers) / total if total > 0 else 0
                }
        
        return breakdown
    
    def _empty_result(self, hypothesis_id: str, run_id: str) -> HypothesisResult:
        """Create empty result when no valid triggers"""
        return HypothesisResult(
            hypothesis_id=hypothesis_id,
            run_id=run_id,
            win_rate=0,
            profit_factor=0,
            expectancy=0,
            avg_return=0,
            max_drawdown=0,
            sample_size=0,
            winning_trades=0,
            losing_trades=0,
            confidence_score=0,
            verdict=HypothesisVerdict.REJECTED,
            verdict_reason="No valid triggers found",
            computed_at=datetime.now(timezone.utc)
        )
    
    def compare_results(self, results: List[HypothesisResult]) -> Dict:
        """Compare multiple hypothesis results"""
        if not results:
            return {"message": "No results to compare"}
        
        # Sort by verdict and metrics
        sorted_results = sorted(
            results,
            key=lambda r: (
                {"VALID": 4, "PROMISING": 3, "WEAK": 2, "REJECTED": 1}.get(r.verdict.value, 0),
                r.profit_factor,
                r.win_rate
            ),
            reverse=True
        )
        
        return {
            "best_hypothesis": sorted_results[0].hypothesis_id if sorted_results else None,
            "ranking": [
                {
                    "rank": i + 1,
                    "hypothesis_id": r.hypothesis_id,
                    "verdict": r.verdict.value,
                    "win_rate": round(r.win_rate, 4),
                    "profit_factor": round(r.profit_factor, 2),
                    "confidence": round(r.confidence_score, 3)
                }
                for i, r in enumerate(sorted_results)
            ],
            "summary": {
                "total_tested": len(results),
                "valid": len([r for r in results if r.verdict == HypothesisVerdict.VALID]),
                "promising": len([r for r in results if r.verdict == HypothesisVerdict.PROMISING]),
                "weak": len([r for r in results if r.verdict == HypothesisVerdict.WEAK]),
                "rejected": len([r for r in results if r.verdict == HypothesisVerdict.REJECTED])
            }
        }
