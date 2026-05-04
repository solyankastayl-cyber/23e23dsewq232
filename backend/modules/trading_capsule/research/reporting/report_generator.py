"""
Report Generator (S2.5)
=======================

Main service for generating research reports.

Collects data from:
- Experiment Manager (S2.1)
- Ranking Engine (S2.4)
- Robustness Analyzer (S2.6C)
- Strategy Selector (S3.1)

Produces comprehensive ResearchReport.
"""

from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
import threading

from .report_types import (
    ResearchReport,
    LeaderboardEntry,
    WalkForwardAnalysis,
    StrategyDiagnostics,
    AllocationReadiness,
    ReportWarning,
    WarningLevel,
    RobustnessVerdict
)


# ===========================================
# Thresholds for warnings/allocation
# ===========================================

WARNING_THRESHOLDS = {
    "LOW_SAMPLE_SIZE": 30,           # trades < 30
    "HIGH_DRAWDOWN": 0.30,           # max_dd > 30%
    "LOW_SHARPE": 0.5,               # sharpe < 0.5
    "HIGH_VOLATILITY": 0.50,         # volatility > 50%
    "LOW_WIN_RATE": 0.40,            # win_rate < 40%
    "NEGATIVE_EXPECTANCY": 0,        # expectancy <= 0
}

ALLOCATION_THRESHOLDS = {
    "MIN_RANKING_SCORE": 0.40,
    "MIN_ROBUSTNESS_SCORE": 0.45,
    "MAX_DRAWDOWN": 0.35,
    "MIN_TRADES": 20,
}


class ReportGenerator:
    """
    Generates research reports from experiment data.
    
    Thread-safe singleton.
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        # Report cache
        self._reports: Dict[str, ResearchReport] = {}
        
        self._initialized = True
        print("[ReportGenerator] Initialized")
    
    # ===========================================
    # Generate Report
    # ===========================================
    
    def generate_report(
        self,
        experiment_id: str,
        walkforward_experiment_id: Optional[str] = None
    ) -> ResearchReport:
        """
        Generate comprehensive research report.
        
        Args:
            experiment_id: Research experiment ID
            walkforward_experiment_id: Optional WF experiment ID
            
        Returns:
            ResearchReport
        """
        report = ResearchReport(
            experiment_id=experiment_id,
            walkforward_experiment_id=walkforward_experiment_id or ""
        )
        
        # 1. Collect experiment summary
        self._populate_experiment_summary(report)
        
        # 2. Build leaderboard
        self._populate_leaderboard(report)
        
        # 3. Add walk-forward analysis (if available)
        if walkforward_experiment_id:
            self._populate_walkforward_analysis(report, walkforward_experiment_id)
        
        # 4. Build strategy diagnostics
        self._populate_strategy_diagnostics(report)
        
        # 5. Generate warnings
        self._generate_warnings(report)
        
        # 6. Calculate allocation readiness
        self._calculate_allocation_readiness(report, walkforward_experiment_id)
        
        # Cache report
        self._reports[experiment_id] = report
        
        print(f"[ReportGenerator] Generated report for experiment: {experiment_id}")
        print(f"[ReportGenerator] Winner: {report.winner_strategy_id}, " +
              f"Eligible for allocation: {report.total_eligible_for_allocation}")
        
        return report
    
    # ===========================================
    # Populate Experiment Summary
    # ===========================================
    
    def _populate_experiment_summary(self, report: ResearchReport):
        """Populate experiment summary from experiment manager"""
        try:
            from ..experiment_manager import experiment_manager
            
            experiment = experiment_manager.get_experiment(report.experiment_id)
            if not experiment:
                return
            
            report.experiment_name = experiment.name
            report.asset = experiment.asset
            report.timeframe = experiment.timeframe
            report.start_date = experiment.start_date
            report.end_date = experiment.end_date
            report.initial_capital_usd = experiment.initial_capital_usd
            report.strategies_tested = len(experiment.strategies)
            
            report.winner_strategy_id = experiment.winner_strategy_id
            report.winner_score = experiment.winner_composite_score
            
        except Exception as e:
            print(f"[ReportGenerator] Error populating summary: {e}")
    
    # ===========================================
    # Populate Leaderboard
    # ===========================================
    
    def _populate_leaderboard(self, report: ResearchReport):
        """Populate leaderboard from ranking engine"""
        try:
            from ..ranking_engine import ranking_engine
            
            leaderboard = ranking_engine.get_leaderboard(report.experiment_id)
            if not leaderboard:
                return
            
            for entry in leaderboard.entries:
                raw = entry.raw_metrics
                
                lb_entry = LeaderboardEntry(
                    rank=entry.rank,
                    strategy_id=entry.strategy_id,
                    sharpe_ratio=raw.get("sharpe_ratio", 0),
                    sortino_ratio=raw.get("sortino_ratio", 0),
                    profit_factor=raw.get("profit_factor", 0),
                    calmar_ratio=raw.get("calmar_ratio", 0),
                    max_drawdown_pct=raw.get("max_drawdown_pct", 0),
                    win_rate=raw.get("win_rate", 0),
                    trades_count=raw.get("trades_count", 0),
                    composite_score=entry.composite_score,
                    is_winner=(entry.rank == 1)
                )
                report.leaderboard.append(lb_entry)
            
            # Update winner info if not set
            if leaderboard.winner_strategy_id and not report.winner_strategy_id:
                report.winner_strategy_id = leaderboard.winner_strategy_id
                report.winner_score = leaderboard.winner_score
                
        except Exception as e:
            print(f"[ReportGenerator] Error populating leaderboard: {e}")
    
    # ===========================================
    # Populate Walk-Forward Analysis
    # ===========================================
    
    def _populate_walkforward_analysis(
        self,
        report: ResearchReport,
        wf_experiment_id: str
    ):
        """Populate walk-forward analysis from robustness analyzer"""
        try:
            from ..walkforward.robustness_analyzer import robustness_analyzer
            
            results = robustness_analyzer.get_results(wf_experiment_id)
            if not results:
                return
            
            report.has_walkforward_data = True
            
            for r in results.strategy_results:
                # Map verdict
                verdict = RobustnessVerdict.UNKNOWN
                try:
                    verdict = RobustnessVerdict(r.verdict.value)
                except:
                    pass
                
                wf = WalkForwardAnalysis(
                    strategy_id=r.strategy_id,
                    verdict=verdict,
                    robustness_score=r.robustness_score,
                    stability_score=r.stability_score,
                    degradation_score=r.degradation_score,
                    avg_train_sharpe=r.avg_train_sharpe,
                    avg_test_sharpe=r.avg_test_sharpe,
                    sharpe_degradation_pct=r.avg_sharpe_degradation * 100,
                    windows_analyzed=r.windows_count,
                    valid_windows=r.valid_windows,
                    verdict_reasons=r.verdict_reasons
                )
                report.walkforward_analyses.append(wf)
                
        except Exception as e:
            print(f"[ReportGenerator] Error populating WF analysis: {e}")
    
    # ===========================================
    # Populate Strategy Diagnostics
    # ===========================================
    
    def _populate_strategy_diagnostics(self, report: ResearchReport):
        """Build detailed diagnostics for each strategy"""
        try:
            from ..ranking_engine import ranking_engine
            
            leaderboard = ranking_engine.get_leaderboard(report.experiment_id)
            if not leaderboard:
                return
            
            for entry in leaderboard.entries:
                raw = entry.raw_metrics
                
                diag = StrategyDiagnostics(
                    strategy_id=entry.strategy_id,
                    
                    # Performance
                    sharpe_ratio=raw.get("sharpe_ratio", 0),
                    sortino_ratio=raw.get("sortino_ratio", 0),
                    profit_factor=raw.get("profit_factor", 0),
                    expectancy=raw.get("expectancy", 0),
                    
                    # Risk
                    max_drawdown_pct=raw.get("max_drawdown_pct", 0),
                    calmar_ratio=raw.get("calmar_ratio", 0),
                    recovery_factor=raw.get("recovery_factor", 0),
                    volatility_annual=raw.get("volatility_annual", 0),
                    
                    # Trade stats
                    trades_count=raw.get("trades_count", 0),
                    win_rate=raw.get("win_rate", 0),
                    
                    # Returns
                    total_return_pct=raw.get("total_return_pct", 0),
                    annual_return_pct=raw.get("annual_return_pct", 0),
                    
                    # Warnings from ranking
                    warnings=entry.warnings.copy()
                )
                
                # Set quality flags
                diag.has_valid_metrics = "INVALID_METRICS" not in entry.warnings
                diag.has_sufficient_trades = diag.trades_count >= WARNING_THRESHOLDS["LOW_SAMPLE_SIZE"]
                diag.has_acceptable_drawdown = diag.max_drawdown_pct <= WARNING_THRESHOLDS["HIGH_DRAWDOWN"] * 100
                
                report.strategy_diagnostics.append(diag)
                
        except Exception as e:
            print(f"[ReportGenerator] Error populating diagnostics: {e}")
    
    # ===========================================
    # Generate Warnings
    # ===========================================
    
    def _generate_warnings(self, report: ResearchReport):
        """Generate warnings based on strategy diagnostics"""
        for diag in report.strategy_diagnostics:
            # Low sample size
            if diag.trades_count < WARNING_THRESHOLDS["LOW_SAMPLE_SIZE"]:
                report.warnings.append(ReportWarning(
                    code="LOW_SAMPLE_SIZE",
                    level=WarningLevel.WARNING,
                    strategy_id=diag.strategy_id,
                    message=f"Low trade count ({diag.trades_count}). Results may not be statistically significant."
                ))
            
            # High drawdown
            if diag.max_drawdown_pct > WARNING_THRESHOLDS["HIGH_DRAWDOWN"] * 100:
                report.warnings.append(ReportWarning(
                    code="HIGH_DRAWDOWN",
                    level=WarningLevel.WARNING,
                    strategy_id=diag.strategy_id,
                    message=f"High max drawdown ({diag.max_drawdown_pct:.1f}%). Consider risk management adjustments."
                ))
            
            # Low sharpe
            if diag.sharpe_ratio < WARNING_THRESHOLDS["LOW_SHARPE"] and diag.sharpe_ratio > 0:
                report.warnings.append(ReportWarning(
                    code="LOW_SHARPE",
                    level=WarningLevel.INFO,
                    strategy_id=diag.strategy_id,
                    message=f"Below-target Sharpe ratio ({diag.sharpe_ratio:.2f})."
                ))
            
            # Low win rate
            if diag.win_rate > 0 and diag.win_rate < WARNING_THRESHOLDS["LOW_WIN_RATE"]:
                report.warnings.append(ReportWarning(
                    code="LOW_WIN_RATE",
                    level=WarningLevel.INFO,
                    strategy_id=diag.strategy_id,
                    message=f"Low win rate ({diag.win_rate*100:.1f}%)."
                ))
            
            # Invalid metrics
            if not diag.has_valid_metrics:
                report.warnings.append(ReportWarning(
                    code="INVALID_METRICS",
                    level=WarningLevel.CRITICAL,
                    strategy_id=diag.strategy_id,
                    message="Invalid or missing metrics data."
                ))
        
        # Walk-forward specific warnings
        for wf in report.walkforward_analyses:
            if wf.verdict == RobustnessVerdict.OVERFIT:
                report.warnings.append(ReportWarning(
                    code="OVERFIT",
                    level=WarningLevel.CRITICAL,
                    strategy_id=wf.strategy_id,
                    message=f"Strategy appears overfitted. Train Sharpe: {wf.avg_train_sharpe:.2f} -> Test: {wf.avg_test_sharpe:.2f}"
                ))
            elif wf.verdict == RobustnessVerdict.UNSTABLE:
                report.warnings.append(ReportWarning(
                    code="UNSTABLE",
                    level=WarningLevel.WARNING,
                    strategy_id=wf.strategy_id,
                    message="High variance across walk-forward windows."
                ))
    
    # ===========================================
    # Calculate Allocation Readiness
    # ===========================================
    
    def _calculate_allocation_readiness(
        self,
        report: ResearchReport,
        walkforward_experiment_id: Optional[str] = None
    ):
        """
        Calculate allocation readiness for each strategy.
        
        This bridges Research (S2) to Allocation (S3).
        """
        # Get ranking data
        ranking_data = {}
        try:
            from ..ranking_engine import ranking_engine
            leaderboard = ranking_engine.get_leaderboard(report.experiment_id)
            if leaderboard:
                for entry in leaderboard.entries:
                    ranking_data[entry.strategy_id] = entry.composite_score
        except:
            pass
        
        # Get walk-forward data
        wf_data = {}
        try:
            if walkforward_experiment_id:
                from ..walkforward.robustness_analyzer import robustness_analyzer
                results = robustness_analyzer.get_results(walkforward_experiment_id)
                if results:
                    for r in results.strategy_results:
                        wf_data[r.strategy_id] = {
                            "robustness_score": r.robustness_score,
                            "verdict": r.verdict.value
                        }
        except:
            pass
        
        # Calculate allocation readiness for each strategy
        eligible_count = 0
        
        for diag in report.strategy_diagnostics:
            strategy_id = diag.strategy_id
            
            readiness = AllocationReadiness(
                strategy_id=strategy_id,
                ranking_score=ranking_data.get(strategy_id, 0),
                robustness_score=wf_data.get(strategy_id, {}).get("robustness_score", 0.5)
            )
            
            # Check ranking threshold
            readiness.passes_ranking_threshold = (
                readiness.ranking_score >= ALLOCATION_THRESHOLDS["MIN_RANKING_SCORE"]
            )
            
            # Check robustness
            wf_verdict = wf_data.get(strategy_id, {}).get("verdict", "UNKNOWN")
            readiness.passes_robustness_check = (
                wf_verdict not in ["OVERFIT", "UNSTABLE"] and
                readiness.robustness_score >= ALLOCATION_THRESHOLDS["MIN_ROBUSTNESS_SCORE"]
            )
            
            # Check risk (drawdown)
            dd_pct = diag.max_drawdown_pct / 100 if diag.max_drawdown_pct > 1 else diag.max_drawdown_pct
            readiness.passes_risk_check = (
                dd_pct <= ALLOCATION_THRESHOLDS["MAX_DRAWDOWN"]
            )
            
            # Check sample size
            readiness.passes_sample_size_check = (
                diag.trades_count >= ALLOCATION_THRESHOLDS["MIN_TRADES"] or
                diag.trades_count == 0  # Allow if trades_count not populated
            )
            
            # Overall eligibility
            readiness.eligible_for_allocation = (
                readiness.passes_ranking_threshold and
                readiness.passes_robustness_check and
                readiness.passes_risk_check and
                readiness.passes_sample_size_check
            )
            
            # Calculate combined score
            readiness.combined_score = (
                readiness.ranking_score * 0.5 +
                readiness.robustness_score * 0.5
            )
            
            # Set rejection reason if not eligible
            if not readiness.eligible_for_allocation:
                if not readiness.passes_ranking_threshold:
                    readiness.rejection_reason = "LOW_RANKING_SCORE"
                elif not readiness.passes_robustness_check:
                    if wf_verdict == "OVERFIT":
                        readiness.rejection_reason = "OVERFIT"
                    elif wf_verdict == "UNSTABLE":
                        readiness.rejection_reason = "UNSTABLE"
                    else:
                        readiness.rejection_reason = "LOW_ROBUSTNESS_SCORE"
                elif not readiness.passes_risk_check:
                    readiness.rejection_reason = "HIGH_DRAWDOWN"
                elif not readiness.passes_sample_size_check:
                    readiness.rejection_reason = "LOW_SAMPLE_SIZE"
            
            # Calculate recommended weight (simplified)
            if readiness.eligible_for_allocation:
                # Base weight on combined score
                readiness.recommended_weight = min(
                    0.35,  # Max weight
                    readiness.combined_score * 0.5
                )
                eligible_count += 1
            else:
                readiness.recommended_weight = 0.0
            
            # Risk adjustment (lower weight for higher drawdown)
            if dd_pct > 0:
                readiness.risk_adjustment_factor = max(0.5, 1.0 - dd_pct)
            
            report.allocation_candidates.append(readiness)
        
        report.total_eligible_for_allocation = eligible_count
    
    # ===========================================
    # Get Report
    # ===========================================
    
    def get_report(
        self,
        experiment_id: str,
        walkforward_experiment_id: Optional[str] = None
    ) -> Optional[ResearchReport]:
        """
        Get report from cache or generate new one.
        """
        if experiment_id in self._reports:
            return self._reports[experiment_id]
        
        return self.generate_report(experiment_id, walkforward_experiment_id)
    
    # ===========================================
    # Get Sections
    # ===========================================
    
    def get_leaderboard(
        self,
        experiment_id: str
    ) -> List[LeaderboardEntry]:
        """Get just the leaderboard section"""
        report = self.get_report(experiment_id)
        return report.leaderboard if report else []
    
    def get_diagnostics(
        self,
        experiment_id: str
    ) -> List[StrategyDiagnostics]:
        """Get just the diagnostics section"""
        report = self.get_report(experiment_id)
        return report.strategy_diagnostics if report else []
    
    def get_allocation_candidates(
        self,
        experiment_id: str,
        walkforward_experiment_id: Optional[str] = None
    ) -> List[AllocationReadiness]:
        """Get allocation candidates"""
        report = self.get_report(experiment_id, walkforward_experiment_id)
        return report.allocation_candidates if report else []
    
    # ===========================================
    # Cache Management
    # ===========================================
    
    def invalidate_cache(self, experiment_id: str):
        """Invalidate cached report"""
        self._reports.pop(experiment_id, None)
    
    def clear_cache(self) -> int:
        """Clear all cached reports"""
        count = len(self._reports)
        self._reports.clear()
        return count


# Global singleton
report_generator = ReportGenerator()
