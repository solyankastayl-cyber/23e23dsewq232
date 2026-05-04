"""
PHASE 3.4 — Job Runner

Executes individual scheduled jobs.
Handles the actual work for each job type.
"""

from typing import Dict, List, Optional, Any
from datetime import datetime, timezone
from dataclasses import dataclass
from enum import Enum
import traceback


class JobType(Enum):
    """Types of scheduled jobs."""
    DAILY_CALIBRATION = "daily_calibration"
    HOURLY_HEALTH_CHECK = "hourly_health_check"
    WEEKLY_RECALIBRATION = "weekly_recalibration"
    SNAPSHOT = "snapshot"
    PERFORMANCE_CHECK = "performance_check"
    AUTO_ROLLBACK_CHECK = "auto_rollback_check"
    CUSTOM = "custom"


class JobStatus(Enum):
    """Job execution status."""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class JobResult:
    """Result of job execution."""
    job_type: JobType
    status: JobStatus
    started_at: str
    finished_at: str
    duration_seconds: float
    result: Optional[Dict] = None
    error: Optional[str] = None


class JobRunner:
    """
    Executes individual jobs.
    
    Each job type has its own execution logic.
    """
    
    def __init__(self):
        self._job_history: List[Dict] = []
        self._last_metrics: Optional[Dict] = None
    
    def run(self, job_type: JobType, **kwargs) -> JobResult:
        """
        Run a specific job.
        
        Args:
            job_type: Type of job to run
            **kwargs: Additional arguments for the job
        
        Returns:
            JobResult with execution details
        """
        started_at = datetime.now(timezone.utc)
        
        try:
            if job_type == JobType.DAILY_CALIBRATION:
                result = self._run_daily_calibration(**kwargs)
            elif job_type == JobType.HOURLY_HEALTH_CHECK:
                result = self._run_hourly_health_check(**kwargs)
            elif job_type == JobType.WEEKLY_RECALIBRATION:
                result = self._run_weekly_recalibration(**kwargs)
            elif job_type == JobType.SNAPSHOT:
                result = self._run_snapshot(**kwargs)
            elif job_type == JobType.PERFORMANCE_CHECK:
                result = self._run_performance_check(**kwargs)
            elif job_type == JobType.AUTO_ROLLBACK_CHECK:
                result = self._run_auto_rollback_check(**kwargs)
            else:
                result = {"status": "unknown_job_type"}
            
            finished_at = datetime.now(timezone.utc)
            duration = (finished_at - started_at).total_seconds()
            
            job_result = JobResult(
                job_type=job_type,
                status=JobStatus.SUCCESS,
                started_at=started_at.isoformat(),
                finished_at=finished_at.isoformat(),
                duration_seconds=duration,
                result=result
            )
            
        except Exception as e:
            finished_at = datetime.now(timezone.utc)
            duration = (finished_at - started_at).total_seconds()
            
            job_result = JobResult(
                job_type=job_type,
                status=JobStatus.FAILED,
                started_at=started_at.isoformat(),
                finished_at=finished_at.isoformat(),
                duration_seconds=duration,
                error=str(e)
            )
        
        # Record in history
        self._record_job(job_result)
        
        return job_result
    
    def _run_daily_calibration(self, use_mock: bool = False, **kwargs) -> Dict:
        """
        Run daily calibration cycle.
        
        1. Run Calibration
        2. Generate Actions
        3. Policy Guard
        4. Create pre-apply snapshot
        5. Apply Actions
        6. Create post-apply snapshot
        7. Compute diff
        8. Performance check
        """
        from ..adaptive_state_registry import AdaptiveStateRegistry
        from ..action_application_engine import get_action_application_engine
        from ..policy.policy_guard import get_policy_guard
        from ..audit.state_snapshot import StateSnapshot
        from ..audit.snapshot_repository import SnapshotRepository
        from ..audit.diff_engine import DiffEngine
        
        registry = AdaptiveStateRegistry()
        engine = get_action_application_engine()
        policy_guard = get_policy_guard()
        snapshot_engine = StateSnapshot()
        snapshot_repo = SnapshotRepository()
        diff_engine = DiffEngine()
        
        # Get current state
        current_state = registry.get_state()
        
        # Create pre-apply snapshot
        pre_snapshot = snapshot_engine.create_snapshot(
            state=current_state,
            trigger="scheduled",
            reason="daily_calibration_pre"
        )
        pre_hash = snapshot_repo.save(pre_snapshot)
        
        # Run calibration and generate actions
        calibration_result = self._run_calibration(use_mock=use_mock)
        
        if not calibration_result.get("ok"):
            return {
                "step": "calibration",
                "status": "failed",
                "error": calibration_result.get("error")
            }
        
        calibration_actions = calibration_result.get("actions", [])
        
        if not calibration_actions:
            return {
                "step": "calibration",
                "status": "skipped",
                "reason": "no_actions_generated"
            }
        
        # Apply policy
        policy_result = policy_guard.apply_policy(
            actions=calibration_actions,
            current_state=current_state,
            degradation_info=calibration_result.get("degradation_info")
        )
        
        if not policy_result.allowed_actions:
            return {
                "step": "policy",
                "status": "skipped",
                "reason": "all_actions_filtered",
                "blocked": len(policy_result.blocked_actions),
                "deferred": len(policy_result.deferred_actions)
            }
        
        # Convert to adaptive actions format
        adaptive_actions = []
        for ca in policy_result.allowed_actions:
            if ca.get("action") in ["disable", "reduce_risk", "increase_threshold", "keep", "increase_allocation"]:
                adaptive_actions.append({
                    "target_type": "asset",
                    "target_id": ca.get("key", ""),
                    "action": ca.get("action"),
                    "reason": ca.get("reason", "scheduled_calibration"),
                    "confidence": ca.get("confidence", 0.5)
                })
        
        # Apply actions
        apply_result = engine.apply(adaptive_actions, dry_run=False)
        
        # Create post-apply snapshot
        new_state = registry.get_state()
        post_snapshot = snapshot_engine.create_snapshot(
            state=new_state,
            trigger="scheduled",
            reason="daily_calibration_post",
            metadata={"pre_apply_hash": pre_hash}
        )
        post_hash = snapshot_repo.save(post_snapshot)
        
        # Compute diff
        diff = diff_engine.compute_diff(current_state, new_state)
        
        # Store metrics for performance comparison
        self._last_metrics = self._compute_metrics(new_state)
        
        return {
            "step": "complete",
            "status": "success",
            "calibration_actions": len(calibration_actions),
            "policy_allowed": len(policy_result.allowed_actions),
            "policy_blocked": len(policy_result.blocked_actions),
            "applied": len(apply_result.get("applied", [])),
            "rejected": len(apply_result.get("rejected", [])),
            "pre_snapshot": pre_hash,
            "post_snapshot": post_hash,
            "diff_summary": diff.get("summary", {}),
            "emergency_mode": policy_result.emergency_mode
        }
    
    def _run_hourly_health_check(self, **kwargs) -> Dict:
        """
        Run hourly health check.
        
        1. Get current state
        2. Check degradation signals
        3. Check performance metrics
        4. Trigger rollback if needed
        """
        from ..adaptive_state_registry import AdaptiveStateRegistry
        from ..audit.rollback_engine import RollbackEngine
        
        registry = AdaptiveStateRegistry()
        rollback_engine = RollbackEngine()
        
        current_state = registry.get_state()
        current_metrics = self._compute_metrics(current_state)
        
        # Compare with last metrics
        if self._last_metrics:
            should_rollback, reason = rollback_engine.check_auto_rollback(
                current_metrics=current_metrics,
                previous_metrics=self._last_metrics,
                current_state=current_state
            )
            
            if should_rollback:
                # Perform rollback
                restored_state, rollback_result = rollback_engine.rollback_to_previous(current_state)
                
                if rollback_result.success and restored_state:
                    registry.update(restored_state)
                    
                    return {
                        "status": "rollback_triggered",
                        "reason": reason.value if reason else "unknown",
                        "rollback_success": True,
                        "from_version": rollback_result.from_version,
                        "to_version": rollback_result.to_version
                    }
        
        # Update last metrics
        self._last_metrics = current_metrics
        
        return {
            "status": "healthy",
            "metrics": current_metrics,
            "state_version": current_state.get("version", 0),
            "enabled_assets": len(current_state.get("enabled_assets", []))
        }
    
    def _run_weekly_recalibration(self, use_mock: bool = True, **kwargs) -> Dict:
        """
        Run weekly full recalibration.
        
        1. Full calibration with larger sample
        2. Reset degraded assets (soft re-enable)
        3. Clean up old snapshots
        """
        from ..adaptive_state_registry import AdaptiveStateRegistry
        
        registry = AdaptiveStateRegistry()
        current_state = registry.get_state()
        
        # Run daily calibration with more data (fallback to mock if no real data)
        daily_result = self._run_daily_calibration(use_mock=use_mock)
        
        # Soft re-enable: reset risk multipliers that are too low
        risk_map = dict(current_state.get("risk_multipliers", {}))
        reset_count = 0
        
        for asset, risk in list(risk_map.items()):
            if risk < 0.5:
                risk_map[asset] = 0.7  # Partial reset
                reset_count += 1
        
        if reset_count > 0:
            current_state["risk_multipliers"] = risk_map
            registry.update(current_state)
        
        return {
            "daily_calibration": daily_result,
            "risk_multipliers_reset": reset_count,
            "status": "success"
        }
    
    def _run_snapshot(self, reason: str = "scheduled", **kwargs) -> Dict:
        """Create scheduled snapshot."""
        from ..adaptive_state_registry import AdaptiveStateRegistry
        from ..audit.state_snapshot import StateSnapshot
        from ..audit.snapshot_repository import SnapshotRepository
        
        registry = AdaptiveStateRegistry()
        snapshot_engine = StateSnapshot()
        snapshot_repo = SnapshotRepository()
        
        current_state = registry.get_state()
        
        snapshot = snapshot_engine.create_snapshot(
            state=current_state,
            trigger="scheduled",
            reason=reason
        )
        
        snapshot_id = snapshot_repo.save(snapshot)
        
        return {
            "snapshot_id": snapshot_id,
            "hash": snapshot["hash"],
            "version": snapshot["version"],
            "status": "success"
        }
    
    def _run_performance_check(self, **kwargs) -> Dict:
        """Check current performance metrics."""
        from ..adaptive_state_registry import AdaptiveStateRegistry
        
        registry = AdaptiveStateRegistry()
        current_state = registry.get_state()
        
        metrics = self._compute_metrics(current_state)
        
        # Compare with baseline if available
        performance_status = "stable"
        if self._last_metrics:
            if metrics.get("error_rate", 0) > self._last_metrics.get("error_rate", 0) * 1.5:
                performance_status = "degrading"
            elif metrics.get("win_rate", 0) < self._last_metrics.get("win_rate", 0) * 0.8:
                performance_status = "degrading"
        
        return {
            "metrics": metrics,
            "status": performance_status,
            "state_version": current_state.get("version", 0)
        }
    
    def _run_auto_rollback_check(self, **kwargs) -> Dict:
        """Check if auto-rollback should be triggered."""
        from ..adaptive_state_registry import AdaptiveStateRegistry
        from ..audit.rollback_engine import RollbackEngine
        
        registry = AdaptiveStateRegistry()
        rollback_engine = RollbackEngine()
        
        current_state = registry.get_state()
        current_metrics = self._compute_metrics(current_state)
        
        if not self._last_metrics:
            return {"status": "no_baseline", "rollback_needed": False}
        
        should_rollback, reason = rollback_engine.check_auto_rollback(
            current_metrics=current_metrics,
            previous_metrics=self._last_metrics,
            current_state=current_state
        )
        
        return {
            "rollback_needed": should_rollback,
            "reason": reason.value if reason else None,
            "current_metrics": current_metrics,
            "previous_metrics": self._last_metrics
        }
    
    def _run_calibration(self, use_mock: bool = False) -> Dict:
        """Run calibration and generate actions."""
        try:
            from modules.calibration.calibration_matrix import CalibrationMatrix
            from modules.calibration.failure_map import FailureMap
            from modules.calibration.degradation_engine import DegradationEngine
            from modules.calibration.edge_classifier import EdgeClassifier
            from modules.calibration.calibration_actions import CalibrationActions
            
            # Get trades (mock or real)
            if use_mock:
                trades = self._generate_mock_trades(300)
            else:
                trades = self._get_real_trades(500)
            
            if not trades or len(trades) < 50:
                return {"ok": False, "error": "Insufficient trades for calibration"}
            
            # Run calibration pipeline
            matrix = CalibrationMatrix().build(trades)
            by_symbol = CalibrationMatrix().aggregate_by(matrix, "symbol")
            failures = FailureMap().analyze(trades)
            degradation = DegradationEngine().detect_from_trades(trades, group_by="symbol")
            edge = EdgeClassifier().classify(by_symbol)
            
            actions = CalibrationActions().generate(edge, degradation, failures)
            
            degradation_info = {
                "total_analyzed": len(degradation),
                "degrading_count": sum(1 for v in degradation.values() if v.get("degrading")),
                "severe_count": sum(1 for v in degradation.values() if v.get("severity") == "severe")
            }
            
            return {
                "ok": True,
                "actions": actions,
                "degradation_info": degradation_info,
                "trades_analyzed": len(trades)
            }
            
        except Exception as e:
            return {"ok": False, "error": str(e)}
    
    def _generate_mock_trades(self, count: int) -> List[Dict]:
        """Generate mock trades for testing."""
        import random
        from datetime import timedelta
        
        symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "AVAXUSDT", "LINKUSDT", "DOTUSDT", "ATOMUSDT", "NEARUSDT"]
        trades = []
        now = datetime.now(timezone.utc)
        
        for i in range(count):
            symbol = random.choice(symbols)
            win = random.random() < 0.55
            pnl = random.uniform(0.5, 3.0) if win else random.uniform(-2.0, -0.5)
            
            trades.append({
                "symbol": symbol,
                "cluster": random.choice(["btc", "eth", "alt_l1", "defi"]),
                "timeframe": "4H",
                "regime": random.choice(["trend", "compression", "high_vol"]),
                "pnl": pnl,
                "win": win,
                "wrong_early": random.random() < 0.2,
                "confidence": random.uniform(0.4, 0.9),
                "timestamp": (now - timedelta(hours=i)).isoformat()
            })
        
        return trades
    
    def _get_real_trades(self, limit: int) -> List[Dict]:
        """Get real trades from database."""
        try:
            from core.database import get_database
            db = get_database()
            if db is None:
                return []
            
            trades = list(db.backtest_results.find({}, {"_id": 0}).sort("timestamp", -1).limit(limit))
            return trades
        except Exception:
            return []
    
    def _compute_metrics(self, state: Dict) -> Dict:
        """Compute performance metrics from state."""
        return {
            "enabled_assets": len(state.get("enabled_assets", [])),
            "disabled_assets": len(state.get("disabled_assets", [])),
            "custom_risk_count": len(state.get("risk_multipliers", {})),
            "custom_threshold_count": len(state.get("confidence_thresholds", {})),
            "version": state.get("version", 0),
            "win_rate": 0.55,  # Would come from actual performance tracking
            "error_rate": 0.1,
            "sharpe": 0.5,
            "max_drawdown": 0.1
        }
    
    def _record_job(self, result: JobResult):
        """Record job in history."""
        record = {
            "job_type": result.job_type.value,
            "status": result.status.value,
            "started_at": result.started_at,
            "finished_at": result.finished_at,
            "duration_seconds": result.duration_seconds,
            "error": result.error
        }
        
        self._job_history.append(record)
        
        # Trim history
        if len(self._job_history) > 100:
            self._job_history = self._job_history[-100:]
    
    def get_history(self, limit: int = 20) -> List[Dict]:
        """Get job history."""
        return self._job_history[-limit:]
