"""
PHASE 2.9.2 — Failure Map

Analyzes WHY the system loses money:
- wrong_direction: predicted UP, went DOWN (or vice versa)
- wrong_early: direction correct but stopped out before target
- late_entry: entered after optimal point
- low_confidence_fail: low confidence trades that failed
- regime_mismatch: trade in wrong regime
- signal_conflict: conflicting signals at entry

Answers: "Where and why does the system fail?"
"""

from typing import Dict, List
from dataclasses import dataclass, field


@dataclass
class FailureBreakdown:
    """Breakdown of failure types."""
    wrong_direction: int = 0
    wrong_early: int = 0
    late_entry: int = 0
    low_confidence_fail: int = 0
    regime_mismatch: int = 0
    signal_conflict: int = 0
    total_failures: int = 0
    total_trades: int = 0


class FailureMap:
    """
    Analyzes failure patterns in trades.
    
    Provides:
    - Global failure breakdown
    - Per-symbol failure breakdown
    - Per-regime failure breakdown
    - Failure patterns (common combinations)
    """
    
    def analyze(self, trades: List[Dict]) -> Dict:
        """
        Analyze failure patterns in trades.
        
        Args:
            trades: List of trade dicts with:
                - win (bool)
                - wrong_early (bool, optional)
                - late_entry (bool, optional)
                - confidence (float, optional)
                - regime (str, optional)
                - regime_at_entry (str, optional)
                - signal_conflict (bool, optional)
                - symbol (str)
        
        Returns:
            {
                "global": failure breakdown,
                "by_symbol": {symbol: breakdown},
                "by_regime": {regime: breakdown},
                "patterns": common failure patterns
            }
        """
        global_breakdown = FailureBreakdown()
        by_symbol: Dict[str, FailureBreakdown] = {}
        by_regime: Dict[str, FailureBreakdown] = {}
        
        for t in trades:
            is_failure = not t.get("win", t.get("pnl", 0) > 0)
            
            global_breakdown.total_trades += 1
            
            # Track by symbol
            symbol = t.get("symbol", "UNKNOWN")
            if symbol not in by_symbol:
                by_symbol[symbol] = FailureBreakdown()
            by_symbol[symbol].total_trades += 1
            
            # Track by regime
            regime = t.get("regime", "unknown")
            if regime not in by_regime:
                by_regime[regime] = FailureBreakdown()
            by_regime[regime].total_trades += 1
            
            if is_failure:
                self._categorize_failure(t, global_breakdown)
                self._categorize_failure(t, by_symbol[symbol])
                self._categorize_failure(t, by_regime[regime])
        
        # Convert to dicts
        return {
            "global": self._breakdown_to_dict(global_breakdown),
            "by_symbol": {s: self._breakdown_to_dict(b) for s, b in by_symbol.items()},
            "by_regime": {r: self._breakdown_to_dict(b) for r, b in by_regime.items()},
            "patterns": self._find_patterns(trades),
            "summary": self._generate_summary(global_breakdown)
        }
    
    def _categorize_failure(self, trade: Dict, breakdown: FailureBreakdown):
        """Categorize a failed trade."""
        breakdown.total_failures += 1
        
        # Wrong Direction (basic loss without specific cause)
        breakdown.wrong_direction += 1
        
        # Wrong Early
        if trade.get("wrong_early", False):
            breakdown.wrong_early += 1
        
        # Late Entry
        if trade.get("late_entry", False):
            breakdown.late_entry += 1
        
        # Low Confidence Fail
        confidence = trade.get("confidence", 0.5)
        if confidence < 0.5:
            breakdown.low_confidence_fail += 1
        
        # Regime Mismatch
        regime_at_entry = trade.get("regime_at_entry")
        regime_now = trade.get("regime")
        if regime_at_entry and regime_now and regime_at_entry != regime_now:
            breakdown.regime_mismatch += 1
        
        # Signal Conflict
        if trade.get("signal_conflict", False):
            breakdown.signal_conflict += 1
    
    def _breakdown_to_dict(self, breakdown: FailureBreakdown) -> Dict:
        """Convert breakdown to dict with rates."""
        total = breakdown.total_trades
        failures = breakdown.total_failures
        
        return {
            "total_trades": total,
            "total_failures": failures,
            "failure_rate": round(failures / total, 4) if total > 0 else 0,
            "wrong_direction": breakdown.wrong_direction,
            "wrong_direction_rate": round(breakdown.wrong_direction / total, 4) if total > 0 else 0,
            "wrong_early": breakdown.wrong_early,
            "wrong_early_rate": round(breakdown.wrong_early / total, 4) if total > 0 else 0,
            "late_entry": breakdown.late_entry,
            "late_entry_rate": round(breakdown.late_entry / total, 4) if total > 0 else 0,
            "low_confidence_fail": breakdown.low_confidence_fail,
            "low_confidence_fail_rate": round(breakdown.low_confidence_fail / total, 4) if total > 0 else 0,
            "regime_mismatch": breakdown.regime_mismatch,
            "regime_mismatch_rate": round(breakdown.regime_mismatch / total, 4) if total > 0 else 0,
            "signal_conflict": breakdown.signal_conflict,
            "signal_conflict_rate": round(breakdown.signal_conflict / total, 4) if total > 0 else 0,
        }
    
    def _find_patterns(self, trades: List[Dict]) -> List[Dict]:
        """Find common failure patterns (combinations)."""
        patterns = {}
        
        for t in trades:
            if t.get("win", t.get("pnl", 0) > 0):
                continue
            
            # Build pattern signature
            pattern_parts = []
            
            if t.get("wrong_early"):
                pattern_parts.append("wrong_early")
            if t.get("late_entry"):
                pattern_parts.append("late_entry")
            if t.get("confidence", 0.5) < 0.5:
                pattern_parts.append("low_confidence")
            if t.get("signal_conflict"):
                pattern_parts.append("signal_conflict")
            
            regime = t.get("regime", "unknown")
            pattern_parts.append(f"regime:{regime}")
            
            pattern = "+".join(sorted(pattern_parts))
            
            if pattern not in patterns:
                patterns[pattern] = {"count": 0, "examples": []}
            patterns[pattern]["count"] += 1
            
            if len(patterns[pattern]["examples"]) < 3:
                patterns[pattern]["examples"].append({
                    "symbol": t.get("symbol"),
                    "pnl": t.get("pnl"),
                    "confidence": t.get("confidence")
                })
        
        # Sort by frequency
        sorted_patterns = sorted(
            [{"pattern": k, **v} for k, v in patterns.items()],
            key=lambda x: x["count"],
            reverse=True
        )
        
        return sorted_patterns[:10]  # Top 10 patterns
    
    def _generate_summary(self, breakdown: FailureBreakdown) -> Dict:
        """Generate human-readable summary."""
        total = breakdown.total_trades
        failures = breakdown.total_failures
        
        if total == 0:
            return {"status": "no_data"}
        
        failure_rate = failures / total
        
        # Find dominant failure type
        failure_types = {
            "wrong_direction": breakdown.wrong_direction,
            "wrong_early": breakdown.wrong_early,
            "late_entry": breakdown.late_entry,
            "low_confidence": breakdown.low_confidence_fail,
            "regime_mismatch": breakdown.regime_mismatch,
            "signal_conflict": breakdown.signal_conflict
        }
        
        dominant = max(failure_types.items(), key=lambda x: x[1])
        
        return {
            "status": "analyzed",
            "overall_failure_rate": round(failure_rate, 4),
            "dominant_failure_type": dominant[0],
            "dominant_failure_count": dominant[1],
            "dominant_failure_rate": round(dominant[1] / total, 4) if total > 0 else 0,
            "recommendation": self._get_recommendation(dominant[0], failure_rate)
        }
    
    def _get_recommendation(self, dominant_type: str, failure_rate: float) -> str:
        """Get recommendation based on dominant failure type."""
        recommendations = {
            "wrong_direction": "Review signal generation logic; consider tighter filters",
            "wrong_early": "Widen stops or improve entry timing; review volatility model",
            "late_entry": "Improve entry trigger; consider limit orders vs market",
            "low_confidence": "Raise confidence threshold to filter weak setups",
            "regime_mismatch": "Add regime stability check before entry",
            "signal_conflict": "Require signal consensus before entry"
        }
        
        rec = recommendations.get(dominant_type, "Review overall strategy logic")
        
        if failure_rate > 0.6:
            rec += " (CRITICAL: >60% failure rate)"
        elif failure_rate > 0.5:
            rec += " (WARNING: >50% failure rate)"
        
        return rec
