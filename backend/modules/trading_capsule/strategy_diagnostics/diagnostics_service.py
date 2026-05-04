"""
Strategy Diagnostics Service (STR4)
===================================

Main service for Strategy Diagnostics.

Integrates:
- Health Analyzer
- Performance Aggregator
- Risk Aggregator
- STR1 (Profiles)
- STR2 (Configs)
- STR3 (Switching)

Provides:
- Full diagnostics snapshot
- Strategy state
- Health evaluation
- Performance summary
- Risk summary
- Dashboard data
"""

import threading
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional

from .diagnostics_types import (
    StrategyState,
    StrategyHealthState,
    PerformanceSummary,
    RiskSummary,
    StrategyDiagnosticsSnapshot,
    StrategyWarning,
    SwitchTrace,
    HealthStatus
)
from .health_analyzer import health_analyzer
from .performance_aggregator import performance_aggregator
from .risk_aggregator import risk_aggregator


class StrategyDiagnosticsService:
    """
    Main Strategy Diagnostics Service.
    
    Coordinates all diagnostics components and provides
    unified access to strategy observability.
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
        
        # Snapshot history
        self._snapshots: List[StrategyDiagnosticsSnapshot] = []
        self._max_snapshots = 100
        
        # Active warnings
        self._active_warnings: List[StrategyWarning] = []
        
        # Switch history (local cache from STR3)
        self._switch_history: List[SwitchTrace] = []
        
        self._initialized = True
        print("[StrategyDiagnosticsService] Initialized")
    
    # ===========================================
    # Full Diagnostics Snapshot
    # ===========================================
    
    def get_diagnostics(
        self,
        include_history: bool = True
    ) -> StrategyDiagnosticsSnapshot:
        """
        Get full diagnostics snapshot.
        
        Aggregates all diagnostics components.
        """
        # Get state
        state = self.get_strategy_state()
        
        # Get performance
        performance = performance_aggregator.get_performance_summary()
        
        # Get risk
        risk = risk_aggregator.get_risk_summary()
        
        # Get health (with warnings)
        health, new_warnings = health_analyzer.evaluate_health(
            drawdown_pct=risk.current_drawdown_pct,
            daily_loss_pct=risk.daily_loss_pct,
            switches_last_24h=self._count_switches_last_24h(),
            consecutive_losses=performance_aggregator.get_consecutive_losses(),
            win_rate=performance.win_rate,
            exposure_pct=risk.total_exposure_pct
        )
        
        # Merge warnings
        self._merge_warnings(new_warnings)
        
        # Get recent switches
        recent_switches = self._switch_history[-10:] if include_history else []
        
        # Build snapshot
        snapshot = StrategyDiagnosticsSnapshot(
            state=state,
            health=health,
            performance=performance,
            risk=risk,
            warnings=[w for w in self._active_warnings if w.is_active],
            recent_switches=recent_switches
        )
        
        # Store snapshot
        self._snapshots.append(snapshot)
        if len(self._snapshots) > self._max_snapshots:
            self._snapshots = self._snapshots[-self._max_snapshots:]
        
        return snapshot
    
    # ===========================================
    # Strategy State
    # ===========================================
    
    def get_strategy_state(self) -> StrategyState:
        """
        Get current strategy state.
        
        Pulls data from STR3 (switch service).
        """
        state = StrategyState()
        
        try:
            from ..strategy_switch import strategy_switch_service
            
            active_state = strategy_switch_service.get_active_state()
            state.active_profile = active_state.profile_mode
            state.active_profile_id = active_state.profile_id
            state.active_config_id = active_state.config_id
            state.activation_source = active_state.activation_trigger_type.value
            state.activation_reason = active_state.activation_reason
            state.activated_at = active_state.activated_at
            state.activated_by = active_state.activated_by
            state.triggered_policy_id = active_state.activated_by_policy_id
            
            # Calculate duration
            if active_state.activated_at:
                duration = datetime.now(timezone.utc) - active_state.activated_at
                state.active_duration_minutes = duration.total_seconds() / 60
                
        except ImportError:
            # STR3 not available, use defaults
            pass
        except Exception as e:
            print(f"[DiagnosticsService] Error getting state: {e}")
        
        return state
    
    # ===========================================
    # Health
    # ===========================================
    
    def get_health_status(self) -> StrategyHealthState:
        """Get current health evaluation"""
        risk = risk_aggregator.get_risk_summary()
        performance = performance_aggregator.get_performance_summary()
        
        health, warnings = health_analyzer.evaluate_health(
            drawdown_pct=risk.current_drawdown_pct,
            daily_loss_pct=risk.daily_loss_pct,
            switches_last_24h=self._count_switches_last_24h(),
            consecutive_losses=performance_aggregator.get_consecutive_losses(),
            win_rate=performance.win_rate,
            exposure_pct=risk.total_exposure_pct
        )
        
        self._merge_warnings(warnings)
        return health
    
    # ===========================================
    # Performance
    # ===========================================
    
    def get_performance(self) -> PerformanceSummary:
        """Get performance summary"""
        return performance_aggregator.get_performance_summary()
    
    # ===========================================
    # Risk
    # ===========================================
    
    def get_risk(self) -> RiskSummary:
        """Get risk summary"""
        return risk_aggregator.get_risk_summary()
    
    # ===========================================
    # Warnings
    # ===========================================
    
    def get_warnings(self, active_only: bool = True) -> List[StrategyWarning]:
        """Get warnings"""
        if active_only:
            return [w for w in self._active_warnings if w.is_active]
        return self._active_warnings
    
    def acknowledge_warning(self, warning_id: str, acknowledged_by: str) -> bool:
        """Acknowledge a warning"""
        for warning in self._active_warnings:
            if warning.warning_id == warning_id:
                warning.acknowledged = True
                warning.acknowledged_by = acknowledged_by
                warning.acknowledged_at = datetime.now(timezone.utc)
                return True
        return False
    
    def resolve_warning(self, warning_id: str) -> bool:
        """Resolve a warning"""
        for warning in self._active_warnings:
            if warning.warning_id == warning_id:
                warning.is_active = False
                warning.resolved_at = datetime.now(timezone.utc)
                return True
        return False
    
    def _merge_warnings(self, new_warnings: List[StrategyWarning]) -> None:
        """Merge new warnings with existing"""
        for new_warning in new_warnings:
            # Check if same type warning already exists
            existing = next(
                (w for w in self._active_warnings 
                 if w.warning_type == new_warning.warning_type and w.is_active),
                None
            )
            
            if existing:
                # Update existing warning
                existing.current_value = new_warning.current_value
                existing.message = new_warning.message
            else:
                # Add new warning
                self._active_warnings.append(new_warning)
        
        # Resolve warnings that are no longer triggered
        new_types = {w.warning_type for w in new_warnings}
        for warning in self._active_warnings:
            if warning.is_active and warning.warning_type not in new_types:
                # Check if condition is resolved
                if not self._is_warning_still_valid(warning):
                    warning.is_active = False
                    warning.resolved_at = datetime.now(timezone.utc)
    
    def _is_warning_still_valid(self, warning: StrategyWarning) -> bool:
        """Check if warning is still valid based on current metrics"""
        # This is a simplified check - in production would re-evaluate conditions
        return warning.is_active
    
    # ===========================================
    # Switch History
    # ===========================================
    
    def get_switch_history(self, limit: int = 50) -> List[SwitchTrace]:
        """Get switch history"""
        # Try to sync from STR3
        self._sync_switch_history()
        return list(reversed(self._switch_history[-limit:]))
    
    def _sync_switch_history(self) -> None:
        """Sync switch history from STR3"""
        try:
            from ..strategy_switch import strategy_switch_service
            
            events = strategy_switch_service.get_switch_history(50)
            self._switch_history = [
                SwitchTrace(
                    event_id=e.event_id,
                    from_profile=e.from_profile,
                    to_profile=e.to_profile,
                    reason=e.reason,
                    trigger_type=e.trigger_type.value,
                    policy_id=e.triggered_by_policy_id,
                    timestamp=e.timestamp
                )
                for e in events
            ]
        except ImportError:
            pass
        except Exception as e:
            print(f"[DiagnosticsService] Error syncing switches: {e}")
    
    def _count_switches_last_24h(self) -> int:
        """Count switches in last 24 hours"""
        self._sync_switch_history()
        cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
        return sum(
            1 for s in self._switch_history 
            if s.timestamp and s.timestamp >= cutoff
        )
    
    # ===========================================
    # Dashboard
    # ===========================================
    
    def get_dashboard(self) -> Dict[str, Any]:
        """Get dashboard data (compact format)"""
        snapshot = self.get_diagnostics(include_history=False)
        return snapshot.to_dashboard_dict()
    
    # ===========================================
    # Data Updates (from external sources)
    # ===========================================
    
    def update_from_trade(self, trade: Dict[str, Any]) -> None:
        """Update metrics from a new trade"""
        performance_aggregator.add_trade(trade)
    
    def update_from_portfolio(self, portfolio_state: Dict[str, Any]) -> None:
        """Update metrics from portfolio state"""
        risk_aggregator.get_risk_summary(portfolio_state=portfolio_state)
    
    def update_from_monte_carlo(self, mc_results: Dict[str, Any]) -> None:
        """Update VaR from Monte Carlo results"""
        risk_aggregator.get_risk_summary(monte_carlo_results=mc_results)
    
    # ===========================================
    # Snapshot History
    # ===========================================
    
    def get_snapshot_history(self, limit: int = 10) -> List[StrategyDiagnosticsSnapshot]:
        """Get historical snapshots"""
        return list(reversed(self._snapshots[-limit:]))
    
    # ===========================================
    # Health Check
    # ===========================================
    
    def get_service_health(self) -> Dict[str, Any]:
        """Get service health"""
        return {
            "module": "Strategy Diagnostics Service",
            "phase": "STR4",
            "status": "healthy",
            "components": {
                "health_analyzer": health_analyzer.get_health(),
                "performance_aggregator": performance_aggregator.get_health(),
                "risk_aggregator": risk_aggregator.get_health()
            },
            "metrics": {
                "snapshots_stored": len(self._snapshots),
                "active_warnings": len([w for w in self._active_warnings if w.is_active]),
                "switches_tracked": len(self._switch_history)
            }
        }


# Global singleton
strategy_diagnostics_service = StrategyDiagnosticsService()
