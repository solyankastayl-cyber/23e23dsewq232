"""
Paper Auto Runner
==================

Phase 3.0B: Controlled autonomy loop.

Responsibilities:
  - Run every 10 minutes (not 5!)
  - Check all guards via AutoRunnerRules
  - If allowed → call paper_bridge_service.run_once()
  - Log all decisions to audit
  - Track metrics for monitoring
  - Graceful start/stop via asyncio lifecycle

CRITICAL:
  This layer does NOT contain execution logic.
  Execution logic stays in paper_bridge_service.
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Dict, Any

logger = logging.getLogger(__name__)


class PaperAutoRunner:
    """
    Controlled autonomy loop for paper execution.
    
    Runs every 10 minutes:
      1. Fetch readiness report
      2. Fetch execution quality report
      3. Check open positions count
      4. Evaluate all guards
      5. If allowed → run_once()
      6. Log decision + metrics
    
    Guards:
      - Paused check
      - Auto-disabled check
      - Readiness (must be READY)
      - Execution quality (must be > -0.002)
      - Position limit (max 3)
      - Rate limit (max 4/hour)
    """
    
    def __init__(
        self,
        paper_bridge_service,
        readiness_service,
        execution_quality_service,
        paper_position_repo,
        audit_logger,
        state,
        rules,
        interval_seconds: int = 600  # 10 min
    ):
        """
        Initialize auto runner.
        
        Args:
            paper_bridge_service: Paper execution bridge
            readiness_service: Execution readiness service
            execution_quality_service: Execution quality service
            paper_position_repo: Paper positions repository
            audit_logger: Audit logger
            state: AutoRunnerState instance
            rules: AutoRunnerRules instance
            interval_seconds: Loop interval (default: 600 = 10 min)
        """
        self.paper_bridge_service = paper_bridge_service
        self.readiness_service = readiness_service
        self.execution_quality_service = execution_quality_service
        self.paper_position_repo = paper_position_repo
        self.audit_logger = audit_logger
        self.state = state
        self.rules = rules
        self.interval_seconds = interval_seconds
        
        self._running = False
        
        logger.info(
            f"[PaperAutoRunner] Initialized: interval={interval_seconds}s "
            f"({interval_seconds // 60} minutes)"
        )
    
    async def run_once(self) -> Dict[str, Any]:
        """
        Execute one controlled run.
        
        Flow:
          1. Gather reports (readiness, execution_quality, open_positions)
          2. Evaluate guards
          3. If blocked → log + return skip
          4. If allowed → run_once() + register run + log
        
        Returns:
            {
                "ok": bool,
                "executed": bool,
                "reason": str,
                "metrics": {...},
                "bridge_result": {...} (if executed)
            }
        """
        now = datetime.now(timezone.utc)
        
        logger.info("[PaperAutoRunner] Starting controlled run...")
        
        # 1. Gather reports
        try:
            readiness = await self.readiness_service.get_execution_readiness("market_dynamic")
            execution_quality = await self.execution_quality_service.get_execution_quality(
                experiment_id="market_dynamic",
                horizon="24h"
            )
            open_positions = await self.paper_position_repo.count_open_positions("market_dynamic")
        except Exception as e:
            logger.error(f"[PaperAutoRunner] Error gathering reports: {e}")
            
            await self.audit_logger.log({
                "experiment_id": "market_dynamic",
                "decision": "AUTO_RUN_ERROR",
                "reason": f"report_gathering_failed: {e}",
                "timestamp": now.isoformat(),
            })
            
            return {
                "ok": False,
                "executed": False,
                "reason": f"report_gathering_failed: {e}"
            }
        
        # 2. Evaluate guards
        decision = self.rules.evaluate(
            now=now,
            state=self.state,
            readiness_report=readiness,
            execution_quality_report=execution_quality,
            open_positions_count=open_positions
        )
        
        # 3. If blocked → hard safety auto-disable
        if not decision["allowed"]:
            reason = decision["reason"]
            
            # Hard safety: auto-disable if execution quality too low
            if "execution_quality_too_low" in reason:
                self.state.disable(reason)
                logger.error(f"[PaperAutoRunner] HARD SAFETY TRIGGERED: {reason}")
            
            # Log skip decision
            await self.audit_logger.log({
                "experiment_id": "market_dynamic",
                "decision": "AUTO_RUN_SKIPPED",
                "reason": reason,
                "guards": decision.get("guards", {}),
                "timestamp": now.isoformat(),
            })
            
            logger.warning(f"[PaperAutoRunner] Run skipped: {reason}")
            
            return {
                "ok": True,
                "executed": False,
                "reason": reason,
                "readiness": readiness.get("state"),
                "open_positions": open_positions,
                "guards": decision.get("guards", {})
            }
        
        # 4. All guards passed → execute
        try:
            result = await self.paper_bridge_service.run_once()
            self.state.register_run(now)
            
            # Log success
            await self.audit_logger.log({
                "experiment_id": "market_dynamic",
                "decision": "AUTO_RUN_EXECUTED",
                "reason": "scheduler_run_success",
                "result": {
                    "executed": result.get("executed", 0),
                    "signals_in": result.get("signals_in", 0),
                    "rejected": result.get("rejected", 0)
                },
                "timestamp": now.isoformat(),
            })
            
            logger.info(
                f"[PaperAutoRunner] Run executed successfully: "
                f"signals_in={result.get('signals_in', 0)}, "
                f"executed={result.get('executed', 0)}, "
                f"rejected={result.get('rejected', 0)}"
            )
            
            # Return with monitoring metrics
            return {
                "ok": True,
                "executed": True,
                "reason": "scheduler_run_success",
                "metrics": {
                    "execution_quality": (
                        execution_quality
                        .get("summary", {})
                        .get("execution_quality")
                    ),
                    "open_positions": open_positions,
                    "cooldown_miss_rate": (
                        execution_quality
                        .get("frictions", {})
                        .get("cooldown_miss_rate")
                    ),
                    "readiness_state": readiness.get("state"),
                },
                "bridge_result": result
            }
        
        except Exception as e:
            logger.error(f"[PaperAutoRunner] Execution error: {e}", exc_info=True)
            
            await self.audit_logger.log({
                "experiment_id": "market_dynamic",
                "decision": "AUTO_RUN_ERROR",
                "reason": f"execution_failed: {e}",
                "timestamp": now.isoformat(),
            })
            
            return {
                "ok": False,
                "executed": False,
                "reason": f"execution_failed: {e}"
            }
    
    async def loop_forever(self):
        """
        Main controlled loop.
        
        Runs every interval_seconds until stopped.
        """
        self._running = True
        logger.info(
            f"[PaperAutoRunner] Starting loop: "
            f"interval={self.interval_seconds}s ({self.interval_seconds // 60} min)"
        )
        
        while self._running:
            try:
                await self.run_once()
            except Exception as e:
                logger.error(
                    f"[PaperAutoRunner] Unexpected error in loop: {e}",
                    exc_info=True
                )
                
                await self.audit_logger.log({
                    "experiment_id": "market_dynamic",
                    "decision": "AUTO_RUN_LOOP_ERROR",
                    "reason": str(e),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                })
            
            # Sleep interval
            await asyncio.sleep(self.interval_seconds)
        
        logger.info("[PaperAutoRunner] Loop stopped")
    
    def stop(self):
        """Stop the controlled loop."""
        logger.info("[PaperAutoRunner] Stopping...")
        self._running = False
