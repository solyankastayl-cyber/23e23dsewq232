"""
Auto Runner Rules
==================

Phase 3.0B: Guard rules for controlled autonomy.

6 Guards:
  1. Paused check (manual control)
  2. Auto-disabled check (hard safety)
  3. Readiness check (must be READY, not LIMITED)
  4. Execution quality check (must be > -0.002)
  5. Position limit check (max 3 open)
  6. Rate limit check (max 4 runs/hour)

All guards must pass for execution to proceed.
"""

import logging
from datetime import datetime
from typing import Dict, Any

logger = logging.getLogger(__name__)


class AutoRunnerRules:
    """
    Evaluates guard rules for controlled autonomy.
    
    Responsibilities:
      - Check all safety guards
      - Return allowed/blocked decision with reason
      - Enforce strict limits (not configurable at runtime)
    """
    
    def __init__(
        self,
        max_runs_per_hour: int = 4,
        max_open_positions: int = 3
    ):
        """
        Initialize rules with limits.
        
        Args:
            max_runs_per_hour: Maximum runs per hour (default: 4)
            max_open_positions: Maximum open positions (default: 3)
        """
        self.max_runs_per_hour = max_runs_per_hour
        self.max_open_positions = max_open_positions
        
        logger.info(
            f"[AutoRunnerRules] Initialized: "
            f"max_runs_per_hour={max_runs_per_hour}, "
            f"max_open_positions={max_open_positions}"
        )
    
    def evaluate(
        self,
        now: datetime,
        state,
        readiness_report: Dict[str, Any],
        execution_quality_report: Dict[str, Any],
        open_positions_count: int
    ) -> Dict[str, Any]:
        """
        Evaluate all guards and return decision.
        
        Args:
            now: Current timestamp
            state: AutoRunnerState instance
            readiness_report: Readiness service report
            execution_quality_report: Execution quality service report
            open_positions_count: Current open positions count
        
        Returns:
            {
                "allowed": bool,
                "reason": str,
                "guards": {
                    "paused": bool,
                    "auto_disabled": bool,
                    "readiness": str,
                    "execution_quality": float,
                    "position_limit": bool,
                    "rate_limit": bool
                }
            }
        """
        guards = {}
        
        # Guard 1: Paused check
        if state.paused:
            logger.warning(f"[AutoRunnerRules] BLOCKED: paused ({state.pause_reason})")
            return {
                "allowed": False,
                "reason": f"paused: {state.pause_reason or 'manual'}",
                "guards": {"paused": True}
            }
        guards["paused"] = False
        
        # Guard 2: Auto-disabled check (hard safety)
        if state.auto_disabled:
            logger.error(
                f"[AutoRunnerRules] BLOCKED: auto_disabled ({state.auto_disabled_reason})"
            )
            return {
                "allowed": False,
                "reason": f"auto_disabled: {state.auto_disabled_reason}",
                "guards": {"auto_disabled": True}
            }
        guards["auto_disabled"] = False
        
        # Guard 3: Readiness check (must be READY, not LIMITED)
        readiness_state = readiness_report.get("state")
        guards["readiness"] = readiness_state
        
        if readiness_state != "ready":
            logger.warning(
                f"[AutoRunnerRules] BLOCKED: readiness_not_ready ({readiness_state})"
            )
            return {
                "allowed": False,
                "reason": f"readiness_not_ready: {readiness_state}",
                "guards": guards
            }
        
        # Guard 4: Execution quality check (hard safety threshold)
        exec_quality = (
            execution_quality_report
            .get("summary", {})
            .get("execution_quality")
        )
        guards["execution_quality"] = exec_quality
        
        if exec_quality is not None and exec_quality < -0.002:
            logger.error(
                f"[AutoRunnerRules] BLOCKED: execution_quality_too_low ({exec_quality:.6f})"
            )
            return {
                "allowed": False,
                "reason": f"execution_quality_too_low: {exec_quality:.6f}",
                "guards": guards
            }
        
        # Guard 5: Position limit check
        guards["open_positions"] = open_positions_count
        guards["position_limit_reached"] = open_positions_count >= self.max_open_positions
        
        if open_positions_count >= self.max_open_positions:
            logger.warning(
                f"[AutoRunnerRules] BLOCKED: open_positions_limit "
                f"({open_positions_count}/{self.max_open_positions})"
            )
            return {
                "allowed": False,
                "reason": (
                    f"open_positions_limit: "
                    f"{open_positions_count}/{self.max_open_positions}"
                ),
                "guards": guards
            }
        
        # Guard 6: Rate limit check
        runs_hour = state.runs_last_hour(now)
        guards["runs_last_hour"] = runs_hour
        guards["rate_limit_reached"] = runs_hour >= self.max_runs_per_hour
        
        if runs_hour >= self.max_runs_per_hour:
            logger.warning(
                f"[AutoRunnerRules] BLOCKED: rate_limited "
                f"({runs_hour}/{self.max_runs_per_hour} runs in last hour)"
            )
            return {
                "allowed": False,
                "reason": (
                    f"rate_limited: "
                    f"{runs_hour}/{self.max_runs_per_hour} runs in last hour"
                ),
                "guards": guards
            }
        
        # All guards passed
        logger.info("[AutoRunnerRules] ALLOWED: all_guards_passed")
        return {
            "allowed": True,
            "reason": "all_guards_passed",
            "guards": guards
        }
