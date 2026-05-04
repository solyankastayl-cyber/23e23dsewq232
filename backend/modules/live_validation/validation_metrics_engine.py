"""
Validation Metrics Engine - Computes aggregate validation metrics
"""
from typing import List, Dict, Optional
from collections import defaultdict


class ValidationMetricsEngine:
    """
    Computes aggregated metrics from validation results.
    
    Key metrics:
    - Win rate (live, not backtest)
    - Profit factor (live)
    - Expectancy
    - Wrong early rate
    - Entry drift
    """
    
    def build_metrics(self, results: List[dict], symbol: Optional[str] = None) -> dict:
        """Build aggregated metrics from validation results"""
        
        if symbol:
            results = [r for r in results if r.get("symbol") == symbol]
        
        n = len(results)
        
        if n == 0:
            return self._empty_metrics()
        
        # Categorize results
        wins = [x for x in results if x.get("result") == "WIN"]
        losses = [x for x in results if x.get("result") == "LOSS"]
        expired = [x for x in results if x.get("result") == "EXPIRED"]
        missed = [x for x in results if x.get("result") == "MISSED"]
        open_trades = [x for x in results if x.get("result") == "OPEN"]
        
        # Core metrics
        completed = wins + losses  # Only count completed trades for PF
        n_completed = len(completed)
        
        gross_profit = sum(float(x.get("pnl", 0)) for x in wins)
        gross_loss = abs(sum(float(x.get("pnl", 0)) for x in losses))
        
        total_pnl = sum(float(x.get("pnl", 0)) for x in completed)
        expectancy = total_pnl / n_completed if n_completed > 0 else 0.0
        
        pf = gross_profit / gross_loss if gross_loss > 0 else None
        
        # Rates
        win_rate = len(wins) / n_completed if n_completed > 0 else 0.0
        stop_rate = len(losses) / n if n > 0 else 0.0
        target_rate = len(wins) / n if n > 0 else 0.0
        expired_rate = len(expired) / n if n > 0 else 0.0
        missed_rate = len(missed) / n if n > 0 else 0.0
        
        # Wrong early
        wrong_early_count = sum(1 for x in results if x.get("wrong_early", False))
        wrong_early_rate = wrong_early_count / n if n > 0 else 0.0
        
        # Drift
        drifts = [float(x.get("drift_bps", 0)) for x in results if x.get("entry_reached", False)]
        avg_drift = sum(drifts) / len(drifts) if drifts else 0.0
        
        # Timing metrics
        entry_times = [x.get("time_to_entry_ms") for x in results if x.get("time_to_entry_ms") is not None]
        trade_times = [x.get("time_in_trade_ms") for x in results if x.get("time_in_trade_ms") is not None]
        
        avg_time_to_entry = sum(entry_times) / len(entry_times) if entry_times else 0.0
        avg_time_in_trade = sum(trade_times) / len(trade_times) if trade_times else 0.0
        
        # RR achieved
        rr_achieved = []
        for r in completed:
            entry = r.get("actual_entry")
            exit_price = r.get("actual_exit")
            if entry and exit_price:
                # TODO: Need planned stop to calculate actual RR
                pass
        avg_rr_achieved = sum(rr_achieved) / len(rr_achieved) if rr_achieved else 0.0
        
        # Direction breakdown
        long_results = [x for x in completed if x.get("direction") == "LONG" or 
                       (x.get("shadow_id") and self._get_direction(x) == "LONG")]
        short_results = [x for x in completed if x.get("direction") == "SHORT" or
                        (x.get("shadow_id") and self._get_direction(x) == "SHORT")]
        
        long_wins = [x for x in long_results if x.get("result") == "WIN"]
        short_wins = [x for x in short_results if x.get("result") == "WIN"]
        
        long_win_rate = len(long_wins) / len(long_results) if long_results else 0.0
        short_win_rate = len(short_wins) / len(short_results) if short_results else 0.0
        
        # Entry mode breakdown
        entry_mode_breakdown = self._compute_entry_mode_breakdown(results)
        
        # Period
        timestamps = [x.get("validated_at", "") for x in results if x.get("validated_at")]
        period_start = min(timestamps) if timestamps else ""
        period_end = max(timestamps) if timestamps else ""
        
        return {
            "trades": n,
            "completed_trades": n_completed,
            "open_trades": len(open_trades),
            
            "win_rate": round(win_rate, 4),
            "profit_factor": round(pf, 4) if pf is not None else None,
            "expectancy": round(expectancy, 4),
            
            "stop_rate": round(stop_rate, 4),
            "target_rate": round(target_rate, 4),
            "expired_rate": round(expired_rate, 4),
            "missed_rate": round(missed_rate, 4),
            
            "wrong_early_rate": round(wrong_early_rate, 4),
            "avg_drift_bps": round(avg_drift, 4),
            
            "avg_rr_achieved": round(avg_rr_achieved, 4),
            "avg_time_to_entry_ms": round(avg_time_to_entry, 2),
            "avg_time_in_trade_ms": round(avg_time_in_trade, 2),
            
            "long_win_rate": round(long_win_rate, 4),
            "short_win_rate": round(short_win_rate, 4),
            
            "entry_mode_breakdown": entry_mode_breakdown,
            
            "gross_profit": round(gross_profit, 4),
            "gross_loss": round(gross_loss, 4),
            "total_pnl": round(total_pnl, 4),
            
            "period_start": period_start,
            "period_end": period_end,
        }
    
    def build_symbol_breakdown(self, results: List[dict]) -> Dict[str, dict]:
        """Build metrics breakdown by symbol"""
        symbols = set(r.get("symbol") for r in results if r.get("symbol"))
        return {symbol: self.build_metrics(results, symbol=symbol) for symbol in symbols}
    
    def _empty_metrics(self) -> dict:
        return {
            "trades": 0,
            "completed_trades": 0,
            "open_trades": 0,
            "win_rate": 0.0,
            "profit_factor": None,
            "expectancy": 0.0,
            "stop_rate": 0.0,
            "target_rate": 0.0,
            "expired_rate": 0.0,
            "missed_rate": 0.0,
            "wrong_early_rate": 0.0,
            "avg_drift_bps": 0.0,
            "avg_rr_achieved": 0.0,
            "avg_time_to_entry_ms": 0.0,
            "avg_time_in_trade_ms": 0.0,
            "long_win_rate": 0.0,
            "short_win_rate": 0.0,
            "entry_mode_breakdown": {},
            "gross_profit": 0.0,
            "gross_loss": 0.0,
            "total_pnl": 0.0,
            "period_start": "",
            "period_end": "",
        }
    
    def _get_direction(self, result: dict) -> str:
        """Helper to get direction - may need to look up from shadow trade"""
        return result.get("direction", "UNKNOWN")
    
    def _compute_entry_mode_breakdown(self, results: List[dict]) -> dict:
        """Compute win rate breakdown by entry mode"""
        mode_results = defaultdict(list)
        
        for r in results:
            mode = r.get("entry_mode", "UNKNOWN")
            if r.get("result") in ["WIN", "LOSS"]:
                mode_results[mode].append(r)
        
        breakdown = {}
        for mode, mode_trades in mode_results.items():
            wins = [x for x in mode_trades if x.get("result") == "WIN"]
            win_rate = len(wins) / len(mode_trades) if mode_trades else 0.0
            breakdown[mode] = {
                "trades": len(mode_trades),
                "wins": len(wins),
                "win_rate": round(win_rate, 4),
            }
        
        return breakdown
