"""
Health Analyzer (STR4)
======================

Strategy health evaluation engine.

Health Status:
- HEALTHY: All normal
- WARNING: Minor deviations  
- DEGRADED: Needs attention
- CRITICAL: Manual intervention needed

Rules:
- drawdown > 8% → WARNING
- drawdown > 12% → DEGRADED
- daily_loss > 5% → CRITICAL
- switches_24h > 5 → WARNING
- switches_24h > 10 → DEGRADED
- consecutive_losses >= 3 → WARNING
- consecutive_losses >= 5 → DEGRADED
"""

import threading
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional, Tuple

from .diagnostics_types import (
    HealthStatus,
    StrategyHealthState,
    StrategyWarning,
    WarningType,
    WarningSeverity
)


class HealthAnalyzer:
    """
    Strategy health evaluation engine.
    
    Analyzes multiple metrics to determine overall health.
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
        
        # Thresholds
        self._thresholds = {
            # Drawdown thresholds
            "drawdown_warning": 0.08,      # 8%
            "drawdown_degraded": 0.12,     # 12%
            "drawdown_critical": 0.18,     # 18%
            
            # Daily loss thresholds
            "daily_loss_warning": 0.03,    # 3%
            "daily_loss_degraded": 0.04,   # 4%
            "daily_loss_critical": 0.05,   # 5%
            
            # Switch frequency thresholds
            "switches_warning": 5,
            "switches_degraded": 10,
            "switches_critical": 15,
            
            # Consecutive losses thresholds
            "losses_warning": 3,
            "losses_degraded": 5,
            "losses_critical": 7,
            
            # Win rate thresholds
            "win_rate_warning": 0.40,
            "win_rate_degraded": 0.30,
            
            # Exposure thresholds
            "exposure_warning": 0.50,
            "exposure_degraded": 0.70,
            "exposure_critical": 0.85
        }
        
        self._initialized = True
        print("[HealthAnalyzer] Initialized")
    
    # ===========================================
    # Main Health Evaluation
    # ===========================================
    
    def evaluate_health(
        self,
        drawdown_pct: float = 0.0,
        daily_loss_pct: float = 0.0,
        switches_last_24h: int = 0,
        consecutive_losses: int = 0,
        win_rate: float = 0.5,
        exposure_pct: float = 0.0
    ) -> Tuple[StrategyHealthState, List[StrategyWarning]]:
        """
        Evaluate overall strategy health.
        
        Returns:
            Tuple of (HealthState, List of Warnings)
        """
        warnings: List[StrategyWarning] = []
        checks = {
            "drawdown": "PASS",
            "loss_limit": "PASS",
            "stability": "PASS",
            "performance": "PASS"
        }
        
        # Track worst status
        worst_status = HealthStatus.HEALTHY
        status_reasons = []
        
        # ===========================================
        # Check Drawdown
        # ===========================================
        dd_status, dd_check, dd_warning = self._check_drawdown(drawdown_pct)
        checks["drawdown"] = dd_check
        if dd_warning:
            warnings.append(dd_warning)
        if dd_status.value > worst_status.value:
            worst_status = dd_status
            status_reasons.append(f"Drawdown {drawdown_pct*100:.1f}%")
        
        # ===========================================
        # Check Daily Loss
        # ===========================================
        loss_status, loss_check, loss_warning = self._check_daily_loss(daily_loss_pct)
        checks["loss_limit"] = loss_check
        if loss_warning:
            warnings.append(loss_warning)
        if loss_status.value > worst_status.value:
            worst_status = loss_status
            status_reasons.append(f"Daily loss {daily_loss_pct*100:.1f}%")
        
        # ===========================================
        # Check Stability (switch frequency)
        # ===========================================
        stab_status, stab_check, stab_warning = self._check_stability(switches_last_24h)
        checks["stability"] = stab_check
        if stab_warning:
            warnings.append(stab_warning)
        if stab_status.value > worst_status.value:
            worst_status = stab_status
            status_reasons.append(f"{switches_last_24h} switches in 24h")
        
        # ===========================================
        # Check Performance (consecutive losses)
        # ===========================================
        perf_status, perf_check, perf_warnings = self._check_performance(
            consecutive_losses, win_rate
        )
        checks["performance"] = perf_check
        warnings.extend(perf_warnings)
        if perf_status.value > worst_status.value:
            worst_status = perf_status
            if consecutive_losses >= 3:
                status_reasons.append(f"{consecutive_losses} losses in row")
        
        # ===========================================
        # Check Exposure
        # ===========================================
        exp_warning = self._check_exposure(exposure_pct)
        if exp_warning:
            warnings.append(exp_warning)
        
        # Build health state
        health = StrategyHealthState(
            status=worst_status,
            status_reason="; ".join(status_reasons) if status_reasons else "All metrics normal",
            switches_last_24h=switches_last_24h,
            consecutive_losses=consecutive_losses,
            daily_pnl_pct=-daily_loss_pct,  # Convert loss to PnL
            drawdown_pct=drawdown_pct,
            drawdown_check=checks["drawdown"],
            loss_limit_check=checks["loss_limit"],
            stability_check=checks["stability"],
            performance_check=checks["performance"],
            active_warnings_count=len(warnings),
            evaluated_at=datetime.now(timezone.utc)
        )
        
        return health, warnings
    
    # ===========================================
    # Individual Checks
    # ===========================================
    
    def _check_drawdown(
        self, 
        drawdown_pct: float
    ) -> Tuple[HealthStatus, str, Optional[StrategyWarning]]:
        """Check drawdown against thresholds"""
        
        if drawdown_pct >= self._thresholds["drawdown_critical"]:
            return (
                HealthStatus.CRITICAL,
                "FAIL",
                StrategyWarning(
                    warning_type=WarningType.HIGH_DRAWDOWN,
                    severity=WarningSeverity.CRITICAL,
                    message=f"Critical drawdown: {drawdown_pct*100:.1f}%",
                    related_metric="drawdown_pct",
                    current_value=drawdown_pct,
                    threshold_value=self._thresholds["drawdown_critical"]
                )
            )
        
        if drawdown_pct >= self._thresholds["drawdown_degraded"]:
            return (
                HealthStatus.DEGRADED,
                "FAIL",
                StrategyWarning(
                    warning_type=WarningType.HIGH_DRAWDOWN,
                    severity=WarningSeverity.WARNING,
                    message=f"High drawdown: {drawdown_pct*100:.1f}%",
                    related_metric="drawdown_pct",
                    current_value=drawdown_pct,
                    threshold_value=self._thresholds["drawdown_degraded"]
                )
            )
        
        if drawdown_pct >= self._thresholds["drawdown_warning"]:
            return (
                HealthStatus.WARNING,
                "WARNING",
                StrategyWarning(
                    warning_type=WarningType.HIGH_DRAWDOWN,
                    severity=WarningSeverity.INFO,
                    message=f"Elevated drawdown: {drawdown_pct*100:.1f}%",
                    related_metric="drawdown_pct",
                    current_value=drawdown_pct,
                    threshold_value=self._thresholds["drawdown_warning"]
                )
            )
        
        return (HealthStatus.HEALTHY, "PASS", None)
    
    def _check_daily_loss(
        self, 
        daily_loss_pct: float
    ) -> Tuple[HealthStatus, str, Optional[StrategyWarning]]:
        """Check daily loss against thresholds"""
        
        if daily_loss_pct >= self._thresholds["daily_loss_critical"]:
            return (
                HealthStatus.CRITICAL,
                "FAIL",
                StrategyWarning(
                    warning_type=WarningType.LOSS_LIMIT_BREACH,
                    severity=WarningSeverity.CRITICAL,
                    message=f"Daily loss limit breached: {daily_loss_pct*100:.1f}%",
                    related_metric="daily_loss_pct",
                    current_value=daily_loss_pct,
                    threshold_value=self._thresholds["daily_loss_critical"]
                )
            )
        
        if daily_loss_pct >= self._thresholds["daily_loss_degraded"]:
            return (
                HealthStatus.DEGRADED,
                "WARNING",
                StrategyWarning(
                    warning_type=WarningType.LOSS_LIMIT_NEAR,
                    severity=WarningSeverity.WARNING,
                    message=f"Approaching daily loss limit: {daily_loss_pct*100:.1f}%",
                    related_metric="daily_loss_pct",
                    current_value=daily_loss_pct,
                    threshold_value=self._thresholds["daily_loss_degraded"]
                )
            )
        
        if daily_loss_pct >= self._thresholds["daily_loss_warning"]:
            return (
                HealthStatus.WARNING,
                "WARNING",
                StrategyWarning(
                    warning_type=WarningType.LOSS_LIMIT_NEAR,
                    severity=WarningSeverity.INFO,
                    message=f"Daily loss elevated: {daily_loss_pct*100:.1f}%",
                    related_metric="daily_loss_pct",
                    current_value=daily_loss_pct,
                    threshold_value=self._thresholds["daily_loss_warning"]
                )
            )
        
        return (HealthStatus.HEALTHY, "PASS", None)
    
    def _check_stability(
        self, 
        switches_24h: int
    ) -> Tuple[HealthStatus, str, Optional[StrategyWarning]]:
        """Check profile stability (switch frequency)"""
        
        if switches_24h >= self._thresholds["switches_critical"]:
            return (
                HealthStatus.CRITICAL,
                "FAIL",
                StrategyWarning(
                    warning_type=WarningType.PROFILE_UNSTABLE,
                    severity=WarningSeverity.CRITICAL,
                    message=f"Excessive profile switching: {switches_24h} in 24h",
                    related_metric="switches_24h",
                    current_value=switches_24h,
                    threshold_value=self._thresholds["switches_critical"]
                )
            )
        
        if switches_24h >= self._thresholds["switches_degraded"]:
            return (
                HealthStatus.DEGRADED,
                "WARNING",
                StrategyWarning(
                    warning_type=WarningType.TOO_MANY_SWITCHES,
                    severity=WarningSeverity.WARNING,
                    message=f"High switch frequency: {switches_24h} in 24h",
                    related_metric="switches_24h",
                    current_value=switches_24h,
                    threshold_value=self._thresholds["switches_degraded"]
                )
            )
        
        if switches_24h >= self._thresholds["switches_warning"]:
            return (
                HealthStatus.WARNING,
                "WARNING",
                StrategyWarning(
                    warning_type=WarningType.TOO_MANY_SWITCHES,
                    severity=WarningSeverity.INFO,
                    message=f"Multiple profile switches: {switches_24h} in 24h",
                    related_metric="switches_24h",
                    current_value=switches_24h,
                    threshold_value=self._thresholds["switches_warning"]
                )
            )
        
        return (HealthStatus.HEALTHY, "PASS", None)
    
    def _check_performance(
        self, 
        consecutive_losses: int,
        win_rate: float
    ) -> Tuple[HealthStatus, str, List[StrategyWarning]]:
        """Check performance metrics"""
        warnings = []
        worst_status = HealthStatus.HEALTHY
        check = "PASS"
        
        # Check consecutive losses
        if consecutive_losses >= self._thresholds["losses_critical"]:
            worst_status = HealthStatus.CRITICAL
            check = "FAIL"
            warnings.append(StrategyWarning(
                warning_type=WarningType.CONSECUTIVE_LOSSES,
                severity=WarningSeverity.CRITICAL,
                message=f"Critical losing streak: {consecutive_losses} in row",
                related_metric="consecutive_losses",
                current_value=consecutive_losses,
                threshold_value=self._thresholds["losses_critical"]
            ))
        elif consecutive_losses >= self._thresholds["losses_degraded"]:
            worst_status = HealthStatus.DEGRADED
            check = "WARNING"
            warnings.append(StrategyWarning(
                warning_type=WarningType.CONSECUTIVE_LOSSES,
                severity=WarningSeverity.WARNING,
                message=f"Significant losing streak: {consecutive_losses} in row",
                related_metric="consecutive_losses",
                current_value=consecutive_losses,
                threshold_value=self._thresholds["losses_degraded"]
            ))
        elif consecutive_losses >= self._thresholds["losses_warning"]:
            if worst_status == HealthStatus.HEALTHY:
                worst_status = HealthStatus.WARNING
                check = "WARNING"
            warnings.append(StrategyWarning(
                warning_type=WarningType.CONSECUTIVE_LOSSES,
                severity=WarningSeverity.INFO,
                message=f"Losing streak: {consecutive_losses} in row",
                related_metric="consecutive_losses",
                current_value=consecutive_losses,
                threshold_value=self._thresholds["losses_warning"]
            ))
        
        # Check win rate
        if win_rate <= self._thresholds["win_rate_degraded"]:
            if worst_status.value < HealthStatus.DEGRADED.value:
                worst_status = HealthStatus.DEGRADED
                check = "WARNING"
            warnings.append(StrategyWarning(
                warning_type=WarningType.LOW_WIN_RATE,
                severity=WarningSeverity.WARNING,
                message=f"Very low win rate: {win_rate*100:.1f}%",
                related_metric="win_rate",
                current_value=win_rate,
                threshold_value=self._thresholds["win_rate_degraded"]
            ))
        elif win_rate <= self._thresholds["win_rate_warning"]:
            if worst_status == HealthStatus.HEALTHY:
                worst_status = HealthStatus.WARNING
                check = "WARNING"
            warnings.append(StrategyWarning(
                warning_type=WarningType.LOW_WIN_RATE,
                severity=WarningSeverity.INFO,
                message=f"Low win rate: {win_rate*100:.1f}%",
                related_metric="win_rate",
                current_value=win_rate,
                threshold_value=self._thresholds["win_rate_warning"]
            ))
        
        return (worst_status, check, warnings)
    
    def _check_exposure(
        self, 
        exposure_pct: float
    ) -> Optional[StrategyWarning]:
        """Check exposure levels"""
        
        if exposure_pct >= self._thresholds["exposure_critical"]:
            return StrategyWarning(
                warning_type=WarningType.HIGH_EXPOSURE,
                severity=WarningSeverity.CRITICAL,
                message=f"Critical exposure level: {exposure_pct*100:.1f}%",
                related_metric="exposure_pct",
                current_value=exposure_pct,
                threshold_value=self._thresholds["exposure_critical"]
            )
        
        if exposure_pct >= self._thresholds["exposure_degraded"]:
            return StrategyWarning(
                warning_type=WarningType.HIGH_EXPOSURE,
                severity=WarningSeverity.WARNING,
                message=f"High exposure: {exposure_pct*100:.1f}%",
                related_metric="exposure_pct",
                current_value=exposure_pct,
                threshold_value=self._thresholds["exposure_degraded"]
            )
        
        if exposure_pct >= self._thresholds["exposure_warning"]:
            return StrategyWarning(
                warning_type=WarningType.HIGH_EXPOSURE,
                severity=WarningSeverity.INFO,
                message=f"Elevated exposure: {exposure_pct*100:.1f}%",
                related_metric="exposure_pct",
                current_value=exposure_pct,
                threshold_value=self._thresholds["exposure_warning"]
            )
        
        return None
    
    # ===========================================
    # Threshold Management
    # ===========================================
    
    def get_thresholds(self) -> Dict[str, Any]:
        """Get current thresholds"""
        return self._thresholds.copy()
    
    def update_threshold(self, key: str, value: float) -> bool:
        """Update a threshold value"""
        if key in self._thresholds:
            self._thresholds[key] = value
            return True
        return False
    
    # ===========================================
    # Health
    # ===========================================
    
    def get_health(self) -> Dict[str, Any]:
        """Get analyzer health"""
        return {
            "service": "HealthAnalyzer",
            "status": "healthy",
            "version": "str4",
            "thresholds_count": len(self._thresholds)
        }


# Global singleton
health_analyzer = HealthAnalyzer()
