"""
Execution Readiness Service
============================

Phase 2.9: Core service for execution gate.

Features:
  - State evaluation (READY/LIMITED/BLOCKED)
  - Execution config mapping
  - Manual override support (with TTL)
  - Anti-danger guard
  - Decision logging
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime, timezone, timedelta
from motor.motor_asyncio import AsyncIOMotorDatabase

from .readiness_rules import ReadinessRules, ReadinessState

logger = logging.getLogger(__name__)

# Anti-danger guard (absolute minimum winrate)
ANTI_DANGER_WINRATE = 0.3


class ExecutionReadinessService:
    """
    Manages execution readiness determination.
    
    Flow:
      1. Fetch health status
      2. Evaluate state via rules
      3. Check for manual override
      4. Apply anti-danger guard
      5. Map to execution config
      6. Log decision
    """
    
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.rules = ReadinessRules()
        self.collection = db.execution_readiness_decisions
        self.override_collection = db.execution_readiness_overrides
    
    async def get_execution_readiness(
        self,
        experiment_id: str = "market_dynamic"
    ) -> Dict[str, Any]:
        """
        Get current execution readiness.
        
        Args:
            experiment_id: Experiment to check
        
        Returns:
            {
                "state": "ready" | "limited" | "blocked",
                "execution": {
                    "enabled": bool,
                    "max_positions": int,
                    "allowed_clusters": [...]
                },
                "reason": "...",
                "context": {...},
                "override_active": bool
            }
        """
        # Step 1: Fetch system state
        health = await self._fetch_health(experiment_id)
        performance = await self._fetch_performance(experiment_id)
        constraints = await self._fetch_constraints(experiment_id)
        
        # Extract metrics
        health_status = health.get("status", "unknown")
        alert_counts = health.get("alert_counts", {})
        critical_alerts = alert_counts.get("critical", 0)
        warning_alerts = alert_counts.get("warning", 0)
        
        summary = performance.get("summary", {})
        winrate = summary.get("winrate", 0)
        total_trades = summary.get("total_trades", 0)
        
        constraint_mode = constraints.get("mode", "neutral")
        
        # Step 2: Evaluate state
        state = self.rules.evaluate_state(
            health_status=health_status,
            critical_alerts=critical_alerts,
            warning_alerts=warning_alerts,
            winrate=winrate,
            total_trades=total_trades,
            constraint_mode=constraint_mode
        )
        
        # Step 3: Check for manual override
        override = await self._get_active_override(experiment_id)
        override_active = False
        
        if override:
            original_state = state
            state = ReadinessState(override["override_state"])
            override_active = True
            
            logger.info(
                f"[ReadinessService] Override active: {original_state} → {state} "
                f"(expires: {override['expires_at']}, reason: {override['reason']})"
            )
        
        # Step 4: Apply anti-danger guard (even on override)
        if winrate < ANTI_DANGER_WINRATE and total_trades >= 20:
            if state != ReadinessState.BLOCKED:
                logger.warning(
                    f"[ReadinessService] Anti-danger guard triggered: "
                    f"winrate {winrate:.2%} < {ANTI_DANGER_WINRATE:.0%}, forcing BLOCKED"
                )
                state = ReadinessState.BLOCKED
                override_active = False  # Override cancelled by guard
        
        # Step 5: Map to execution config
        execution_config = self.rules.map_state_to_execution_config(state)
        
        # Step 6: Build reason
        reason = self.rules.build_reason(
            state=state,
            health_status=health_status,
            critical_alerts=critical_alerts,
            warning_alerts=warning_alerts,
            winrate=winrate,
            total_trades=total_trades
        )
        
        # Step 7: Log decision
        await self._log_decision(
            experiment_id=experiment_id,
            state=state.value,
            execution_config=execution_config,
            reason=reason,
            override_active=override_active,
            context={
                "health_status": health_status,
                "critical_alerts": critical_alerts,
                "warning_alerts": warning_alerts,
                "winrate": winrate,
                "total_trades": total_trades
            }
        )
        
        return {
            "state": state.value,
            "execution": execution_config,
            "reason": reason,
            "context": {
                "health": health_status,
                "critical_alerts": critical_alerts,
                "warning_alerts": warning_alerts,
                "winrate": round(winrate, 4),
                "total_trades": total_trades,
                "constraint_mode": constraint_mode
            },
            "override_active": override_active,
            "checked_at": datetime.now(timezone.utc).isoformat()
        }
    
    async def set_manual_override(
        self,
        experiment_id: str,
        override_state: str,
        expires_in_minutes: int = 60,
        reason: str = "Manual override"
    ) -> Dict[str, Any]:
        """
        Set manual override for execution readiness.
        
        IMPORTANT: Anti-danger guard still applies.
        
        Args:
            experiment_id: Experiment ID
            override_state: "ready" | "limited" | "blocked"
            expires_in_minutes: TTL in minutes
            reason: Human reason for override
        
        Returns:
            {
                "ok": True,
                "override_id": "...",
                "expires_at": "..."
            }
        """
        # Validate state
        try:
            state = ReadinessState(override_state)
        except ValueError:
            raise ValueError(f"Invalid override_state: {override_state}")
        
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=expires_in_minutes)
        
        # Store override
        override = {
            "experiment_id": experiment_id,
            "override_state": state.value,
            "reason": reason,
            "created_at": datetime.now(timezone.utc),
            "expires_at": expires_at,
            "active": True
        }
        
        result = await self.override_collection.insert_one(override)
        override_id = str(result.inserted_id)
        
        logger.warning(
            f"[ReadinessService] Manual override set: {state.value} "
            f"(expires: {expires_at}, reason: {reason})"
        )
        
        return {
            "ok": True,
            "override_id": override_id,
            "override_state": state.value,
            "expires_at": expires_at.isoformat(),
            "reason": reason
        }
    
    async def clear_override(self, experiment_id: str) -> bool:
        """
        Clear active manual override.
        
        Args:
            experiment_id: Experiment ID
        
        Returns:
            True if cleared, False if no active override
        """
        result = await self.override_collection.update_many(
            {
                "experiment_id": experiment_id,
                "active": True
            },
            {
                "$set": {"active": False}
            }
        )
        
        if result.modified_count > 0:
            logger.info(f"[ReadinessService] Override cleared for {experiment_id}")
            return True
        
        return False
    
    async def _fetch_health(self, experiment_id: str) -> Dict[str, Any]:
        """Fetch health status from HealthService."""
        try:
            from modules.strategy.observability import get_health_service
            
            service = get_health_service(self.db)
            result = await service.get_health_status(experiment_id=experiment_id)
            
            return result
        
        except Exception as e:
            logger.error(f"[ReadinessService] Failed to fetch health: {e}")
            return {
                "status": "unknown",
                "alert_counts": {"info": 0, "warning": 0, "critical": 0}
            }
    
    async def _fetch_performance(self, experiment_id: str) -> Dict[str, Any]:
        """Fetch performance summary."""
        try:
            from modules.strategy.observability.health_service import HealthService
            
            service = HealthService(self.db)
            summary = await service._fetch_performance_summary(experiment_id)
            
            return {"summary": summary}
        
        except Exception as e:
            logger.error(f"[ReadinessService] Failed to fetch performance: {e}")
            return {
                "summary": {
                    "winrate": 0,
                    "total_trades": 0
                }
            }
    
    async def _fetch_constraints(self, experiment_id: str) -> Dict[str, Any]:
        """Fetch current constraint state."""
        try:
            from modules.strategy.observability.health_service import HealthService
            
            service = HealthService(self.db)
            constraints = await service._fetch_constraints_state(experiment_id)
            
            return constraints
        
        except Exception as e:
            logger.error(f"[ReadinessService] Failed to fetch constraints: {e}")
            return {
                "mode": "neutral",
                "max_positions": 3
            }
    
    async def _get_active_override(self, experiment_id: str) -> Optional[Dict[str, Any]]:
        """Get active override if exists and not expired."""
        now = datetime.now(timezone.utc)
        
        override = await self.override_collection.find_one({
            "experiment_id": experiment_id,
            "active": True,
            "expires_at": {"$gt": now}
        })
        
        if override:
            return override
        
        # Clean up expired overrides
        await self.override_collection.update_many(
            {
                "experiment_id": experiment_id,
                "active": True,
                "expires_at": {"$lte": now}
            },
            {"$set": {"active": False}}
        )
        
        return None
    
    async def _log_decision(
        self,
        experiment_id: str,
        state: str,
        execution_config: Dict[str, Any],
        reason: str,
        override_active: bool,
        context: Dict[str, Any]
    ):
        """Log readiness decision for audit trail."""
        try:
            decision = {
                "experiment_id": experiment_id,
                "state": state,
                "execution_config": execution_config,
                "reason": reason,
                "override_active": override_active,
                "context": context,
                "timestamp": datetime.now(timezone.utc)
            }
            
            await self.collection.insert_one(decision)
        
        except Exception as e:
            logger.error(f"[ReadinessService] Failed to log decision: {e}")


# Global singleton
_execution_readiness_service = None


def get_execution_readiness_service(db: AsyncIOMotorDatabase) -> ExecutionReadinessService:
    """Get or create execution readiness service."""
    global _execution_readiness_service
    if _execution_readiness_service is None:
        _execution_readiness_service = ExecutionReadinessService(db)
    return _execution_readiness_service
