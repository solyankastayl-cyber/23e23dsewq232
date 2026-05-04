"""
Readiness Rules
===============

Phase 2.9: State determination logic.

States:
  - READY: System is healthy, execution fully allowed
  - LIMITED: System has warnings, execution restricted
  - BLOCKED: System critical, execution prohibited

Rules:
  1. BLOCKED takes precedence (safety first)
  2. LIMITED if warnings present
  3. READY only if truly healthy
"""

import logging
from typing import Dict, Any, List
from enum import Enum

logger = logging.getLogger(__name__)


class ReadinessState(str, Enum):
    """Execution readiness states."""
    READY = "ready"
    LIMITED = "limited"
    BLOCKED = "blocked"


# Thresholds
BLOCKED_WINRATE_THRESHOLD = 0.45
BLOCKED_MIN_TRADES = 30

LIMITED_WARNING_ALERTS_THRESHOLD = 3


class ReadinessRules:
    """
    Determines execution readiness state from system health.
    
    Priority:
      1. BLOCKED (critical conditions)
      2. LIMITED (warning conditions)
      3. READY (healthy)
    """
    
    @staticmethod
    def evaluate_state(
        health_status: str,
        critical_alerts: int,
        warning_alerts: int,
        winrate: float,
        total_trades: int,
        constraint_mode: str
    ) -> ReadinessState:
        """
        Evaluate readiness state from system metrics.
        
        Args:
            health_status: "healthy" | "warning" | "critical"
            critical_alerts: Count of critical alerts
            warning_alerts: Count of warning alerts
            winrate: Overall winrate (0-1)
            total_trades: Total resolved trades
            constraint_mode: "neutral" | "defensive" | "aggressive"
        
        Returns:
            ReadinessState (READY | LIMITED | BLOCKED)
        """
        # BLOCKED rules (highest priority)
        if health_status == "critical":
            logger.info("[ReadinessRules] BLOCKED: health status is critical")
            return ReadinessState.BLOCKED
        
        if critical_alerts > 0:
            logger.info(f"[ReadinessRules] BLOCKED: {critical_alerts} critical alerts active")
            return ReadinessState.BLOCKED
        
        # Winrate check (only if enough trades)
        if total_trades >= BLOCKED_MIN_TRADES:
            if winrate < BLOCKED_WINRATE_THRESHOLD:
                logger.info(
                    f"[ReadinessRules] BLOCKED: winrate {winrate:.2%} below "
                    f"threshold {BLOCKED_WINRATE_THRESHOLD:.0%} ({total_trades} trades)"
                )
                return ReadinessState.BLOCKED
        
        # LIMITED rules (medium priority)
        if health_status == "warning":
            logger.info("[ReadinessRules] LIMITED: health status is warning")
            return ReadinessState.LIMITED
        
        if warning_alerts >= LIMITED_WARNING_ALERTS_THRESHOLD:
            logger.info(
                f"[ReadinessRules] LIMITED: {warning_alerts} warning alerts "
                f"(threshold: {LIMITED_WARNING_ALERTS_THRESHOLD})"
            )
            return ReadinessState.LIMITED
        
        if constraint_mode == "defensive":
            logger.info("[ReadinessRules] LIMITED: constraints in defensive mode")
            return ReadinessState.LIMITED
        
        # READY (default if no blocking/limiting conditions)
        logger.info("[ReadinessRules] READY: system is healthy")
        return ReadinessState.READY
    
    @staticmethod
    def map_state_to_execution_config(state: ReadinessState) -> Dict[str, Any]:
        """
        Map readiness state to execution configuration.
        
        Args:
            state: ReadinessState
        
        Returns:
            {
                "enabled": bool,
                "max_positions": int,
                "allowed_clusters": List[str],
                "allowed_timeframes": List[str]
            }
        """
        if state == ReadinessState.READY:
            return {
                "enabled": True,
                "max_positions": 5,
                "allowed_clusters": ["majors", "alts"],
                "allowed_timeframes": ["1h", "4h", "1d"],
                "mode": "full"
            }
        
        elif state == ReadinessState.LIMITED:
            return {
                "enabled": True,
                "max_positions": 1,
                "allowed_clusters": ["majors"],  # Only majors in limited mode
                "allowed_timeframes": ["4h", "1d"],  # Only higher timeframes
                "mode": "restricted"
            }
        
        elif state == ReadinessState.BLOCKED:
            return {
                "enabled": False,
                "max_positions": 0,
                "allowed_clusters": [],
                "allowed_timeframes": [],
                "mode": "disabled"
            }
        
        # Fallback (should never reach)
        logger.error(f"[ReadinessRules] Unknown state: {state}, defaulting to BLOCKED")
        return ReadinessRules.map_state_to_execution_config(ReadinessState.BLOCKED)
    
    @staticmethod
    def build_reason(
        state: ReadinessState,
        health_status: str,
        critical_alerts: int,
        warning_alerts: int,
        winrate: float,
        total_trades: int
    ) -> str:
        """
        Build human-readable reason for current state.
        
        Args:
            state: Current readiness state
            health_status: Health status string
            critical_alerts: Count of critical alerts
            warning_alerts: Count of warning alerts
            winrate: Overall winrate
            total_trades: Total trades
        
        Returns:
            Human-readable reason string
        """
        if state == ReadinessState.BLOCKED:
            reasons = []
            
            if health_status == "critical":
                reasons.append("health status is critical")
            
            if critical_alerts > 0:
                reasons.append(f"{critical_alerts} critical alert(s) active")
            
            if total_trades >= BLOCKED_MIN_TRADES and winrate < BLOCKED_WINRATE_THRESHOLD:
                reasons.append(f"winrate {winrate:.2%} below threshold")
            
            return "Execution BLOCKED: " + ", ".join(reasons)
        
        elif state == ReadinessState.LIMITED:
            reasons = []
            
            if health_status == "warning":
                reasons.append("health status is warning")
            
            if warning_alerts >= LIMITED_WARNING_ALERTS_THRESHOLD:
                reasons.append(f"{warning_alerts} warning alert(s)")
            
            return "Execution LIMITED: " + ", ".join(reasons) + " (majors only, reduced positions)"
        
        elif state == ReadinessState.READY:
            return f"System healthy ({winrate:.2%} winrate, {total_trades} trades), execution fully enabled"
        
        return "Unknown state"
