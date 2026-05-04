"""
PHASE 4.1 — Wrong Early Aggregator

Aggregates wrong early data to answer:
- Which reasons are most frequent?
- Which symbols have most early entries?
- Which timeframes are problematic?
- What's the PnL impact by reason?
"""

from typing import Dict, List, Optional
from collections import defaultdict

from .wrong_early_taxonomy import WRONG_EARLY_REASONS, REASON_SEVERITY, REASON_SUGGESTED_FIX


class WrongEarlyAggregator:
    """
    Aggregates wrong early records for analysis.
    
    Provides:
    - Summary by reason
    - Summary by symbol
    - Summary by timeframe
    - PnL impact analysis
    - Trend analysis
    """
    
    def summarize(self, records: List[Dict]) -> Dict:
        """
        Create comprehensive summary of wrong early records.
        
        Args:
            records: List of classification records
        
        Returns:
            Summary with distributions and insights
        """
        if not records:
            return {
                "total_wrong_early": 0,
                "by_reason": {},
                "distribution": {},
                "by_symbol": {},
                "by_timeframe": {},
                "by_severity": {},
                "pnl_by_reason": {},
                "top_issues": [],
                "actionable_insights": []
            }
        
        total = len(records)
        
        # Count by reason
        by_reason = defaultdict(int)
        for r in records:
            by_reason[r.get("reason", "unknown")] += 1
        
        # Distribution (percentages)
        distribution = {
            k: round(v / total, 4) for k, v in by_reason.items()
        }
        
        # By symbol
        by_symbol = defaultdict(int)
        for r in records:
            by_symbol[r.get("symbol", "UNKNOWN")] += 1
        
        # By timeframe
        by_timeframe = defaultdict(int)
        for r in records:
            by_timeframe[r.get("timeframe", "UNKNOWN")] += 1
        
        # By severity
        by_severity = defaultdict(int)
        for r in records:
            by_severity[r.get("severity", "low")] += 1
        
        # PnL by reason
        pnl_by_reason = defaultdict(float)
        for r in records:
            reason = r.get("reason", "unknown")
            pnl = r.get("pnl", 0)
            pnl_by_reason[reason] += pnl
        
        # Top issues (sorted by count)
        top_issues = sorted(
            [
                {
                    "reason": reason,
                    "count": count,
                    "percentage": round(count / total * 100, 1),
                    "severity": REASON_SEVERITY.get(reason, "low"),
                    "pnl_impact": round(pnl_by_reason.get(reason, 0), 4),
                    "suggested_fix": REASON_SUGGESTED_FIX.get(reason, "Manual review")
                }
                for reason, count in by_reason.items()
            ],
            key=lambda x: (-x["count"], -abs(x["pnl_impact"]))
        )[:10]
        
        # Generate actionable insights
        actionable_insights = self._generate_insights(top_issues, total, by_severity)
        
        return {
            "total_wrong_early": total,
            "by_reason": dict(by_reason),
            "distribution": distribution,
            "by_symbol": dict(sorted(by_symbol.items(), key=lambda x: -x[1])[:20]),
            "by_timeframe": dict(by_timeframe),
            "by_severity": dict(by_severity),
            "pnl_by_reason": {k: round(v, 4) for k, v in pnl_by_reason.items()},
            "top_issues": top_issues,
            "actionable_insights": actionable_insights
        }
    
    def summarize_by_symbol(self, records: List[Dict]) -> Dict[str, Dict]:
        """Get summary broken down by symbol."""
        by_symbol = defaultdict(list)
        for r in records:
            by_symbol[r.get("symbol", "UNKNOWN")].append(r)
        
        return {
            symbol: self.summarize(recs)
            for symbol, recs in by_symbol.items()
        }
    
    def summarize_by_timeframe(self, records: List[Dict]) -> Dict[str, Dict]:
        """Get summary broken down by timeframe."""
        by_tf = defaultdict(list)
        for r in records:
            by_tf[r.get("timeframe", "UNKNOWN")].append(r)
        
        return {
            tf: self.summarize(recs)
            for tf, recs in by_tf.items()
        }
    
    def get_reason_details(self, records: List[Dict], reason: str) -> Dict:
        """Get detailed analysis for a specific reason."""
        filtered = [r for r in records if r.get("reason") == reason]
        
        if not filtered:
            return {"count": 0, "reason": reason, "records": []}
        
        # By symbol for this reason
        by_symbol = defaultdict(int)
        for r in filtered:
            by_symbol[r.get("symbol", "UNKNOWN")] += 1
        
        # By direction
        by_direction = defaultdict(int)
        for r in filtered:
            by_direction[r.get("direction", "UNKNOWN")] += 1
        
        # Average confidence
        avg_confidence = sum(r.get("confidence", 0) for r in filtered) / len(filtered)
        
        # Total PnL
        total_pnl = sum(r.get("pnl", 0) for r in filtered)
        
        return {
            "reason": reason,
            "count": len(filtered),
            "severity": REASON_SEVERITY.get(reason, "low"),
            "suggested_fix": REASON_SUGGESTED_FIX.get(reason, "Manual review"),
            "by_symbol": dict(by_symbol),
            "by_direction": dict(by_direction),
            "avg_confidence": round(avg_confidence, 3),
            "total_pnl": round(total_pnl, 4),
            "avg_pnl": round(total_pnl / len(filtered), 4),
            "sample_records": filtered[:5]
        }
    
    def get_unknown_rate(self, records: List[Dict]) -> float:
        """Get percentage of records classified as 'unknown'."""
        if not records:
            return 0.0
        
        unknown_count = sum(1 for r in records if r.get("reason") == "unknown")
        return round(unknown_count / len(records), 4)
    
    def _generate_insights(
        self,
        top_issues: List[Dict],
        total: int,
        by_severity: Dict[str, int]
    ) -> List[str]:
        """Generate actionable insights from analysis."""
        insights = []
        
        if not top_issues:
            return ["No wrong early entries recorded yet"]
        
        # Top issue insight
        top = top_issues[0]
        insights.append(
            f"Top issue: {top['reason']} ({top['percentage']}% of early entries). "
            f"Fix: {top['suggested_fix']}"
        )
        
        # Severity insight
        high_severity = by_severity.get("high", 0)
        high_pct = round(high_severity / total * 100, 1) if total > 0 else 0
        if high_pct > 50:
            insights.append(
                f"Critical: {high_pct}% of early entries are high-severity. "
                "Prioritize structural fixes over timing tweaks."
            )
        
        # Breakout-related insight
        breakout_issues = ["breakout_not_confirmed", "trigger_touched_but_not_accepted"]
        breakout_count = sum(
            issue["count"] for issue in top_issues if issue["reason"] in breakout_issues
        )
        breakout_pct = round(breakout_count / total * 100, 1) if total > 0 else 0
        if breakout_pct > 30:
            insights.append(
                f"Breakout timing issues account for {breakout_pct}% of problems. "
                "Consider enter_on_close or wait_retest modes."
            )
        
        # Extension chasing insight
        for issue in top_issues:
            if issue["reason"] == "entered_on_extension" and issue["percentage"] > 15:
                insights.append(
                    f"Extension chasing at {issue['percentage']}%. "
                    "Add strict extension filter (max 1.5 ATR from trigger)."
                )
                break
        
        # LTF conflict insight
        for issue in top_issues:
            if issue["reason"] == "ltf_conflict" and issue["percentage"] > 10:
                insights.append(
                    f"LTF conflicts at {issue['percentage']}%. "
                    "Consider adding lower timeframe alignment check."
                )
                break
        
        return insights[:5]  # Max 5 insights
