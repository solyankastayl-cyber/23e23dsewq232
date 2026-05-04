"""
Scheduler Jobs
===============
Job execution logic for V2 Validation Scheduler.

Jobs:
1. Shadow Trade Creation - Auto-create shadow trades from terminal decisions
2. Validation Run - Execute validation on pending/active shadow trades  
3. Alpha Cycle - Run AF3 + AF4 and submit actions to TT5 Control
"""

from typing import Dict, Any, List
from datetime import datetime, timezone
from .scheduler_config import SCHEDULER_CONFIG


class SchedulerJobs:
    """Executes scheduled jobs for continuous adaptive loop."""
    
    def __init__(
        self,
        validation_engine,
        validation_bridge_engine,
        entry_mode_engine,
        control_engine,
    ):
        """
        Initialize scheduler jobs with required engine references.
        
        Args:
            validation_engine: V1 ValidationEngine for shadow trades and validation
            validation_bridge_engine: AF3 ValidationBridgeEngine  
            entry_mode_engine: AF4 EntryModeAdaptationEngine
            control_engine: TT5 ControlEngine
        """
        self.validation = validation_engine
        self.af3 = validation_bridge_engine
        self.af4 = entry_mode_engine
        self.control = control_engine
        
        # Job statistics
        self.stats = {
            "shadow_creation_runs": 0,
            "validation_runs": 0,
            "alpha_cycle_runs": 0,
            "total_shadows_created": 0,
            "total_actions_submitted": 0,
            "last_error": None,
        }
    
    def run_shadow_creation(self) -> Dict[str, Any]:
        """
        Create shadow trades from recent terminal decisions.
        
        Currently creates manual shadow trades for testing.
        In production, this would query terminal_service.get_recent_decisions()
        and create shadow trades from GO_FULL/GO_REDUCED decisions.
        
        Returns:
            Dict with created count and shadow trade IDs
        """
        try:
            max_shadows = SCHEDULER_CONFIG["max_shadow_per_cycle"]
            
            # For now, we don't create shadow trades automatically
            # This requires terminal decision integration
            # In production:
            # decisions = self.terminal.get_recent_decisions()
            # created = []
            # for d in decisions[:max_shadows]:
            #     if d["action"] in ["GO_FULL", "GO_REDUCED"]:
            #         shadow = self.validation.create_shadow_trade(d)
            #         created.append(shadow)
            
            created = []
            
            self.stats["shadow_creation_runs"] += 1
            self.stats["total_shadows_created"] += len(created)
            
            return {
                "ok": True,
                "created": len(created),
                "shadow_ids": [s.get("shadow_id") for s in created],
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            
        except Exception as e:
            self.stats["last_error"] = {"job": "shadow_creation", "error": str(e), "timestamp": datetime.now(timezone.utc).isoformat()}
            return {"ok": False, "error": str(e)}
    
    def run_validation(self) -> Dict[str, Any]:
        """
        Run validation on all pending/active shadow trades.
        
        Currently a no-op as validation requires market data.
        In production, this would fetch market paths and validate shadows.
        
        Returns:
            Dict with validation results count
        """
        try:
            # For now, validation requires manual market data
            # In production with live data feed:
            # pending = self.validation.get_pending_trades()
            # active = self.validation.get_active_trades()
            # results = []
            # for shadow in pending + active:
            #     market_path = fetch_market_path(shadow)
            #     result = self.validation.validate_shadow_trade(shadow["shadow_id"], market_path)
            #     results.append(result)
            
            results = []
            
            self.stats["validation_runs"] += 1
            
            return {
                "ok": True,
                "validated": len(results),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            
        except Exception as e:
            self.stats["last_error"] = {"job": "validation", "error": str(e), "timestamp": datetime.now(timezone.utc).isoformat()}
            return {"ok": False, "error": str(e)}
    
    def run_alpha_cycle(self) -> Dict[str, Any]:
        """
        Run full alpha cycle: AF3 + AF4 + submit actions to Control.
        
        This is the core adaptive intelligence loop:
        1. AF3 evaluates symbol-level edge truth
        2. AF4 evaluates entry-mode edge truth
        3. Merge actions from both
        4. Submit to TT5 Control for governance
        
        Returns:
            Dict with cycle results
        """
        try:
            # Load validation data
            from modules.live_validation.validation_routes import _repo as validation_repo
            
            shadow_trades = validation_repo.list_shadow_trades(limit=500)
            validation_results = validation_repo.list_validation_results(limit=500)
            
            # Run AF3 - Symbol Truth
            af3_result = self.af3.run_full_evaluation()
            af3_actions = af3_result.get("actions", [])
            
            # Run AF4 - Entry Mode Truth
            af4_result = self.af4.run(shadow_trades, validation_results)
            af4_actions = af4_result.get("actions", [])
            
            # Merge actions
            all_actions = af3_actions + af4_actions
            
            # Submit to TT5 Control
            control_result = self.control.ingest_alpha_actions(all_actions)
            
            self.stats["alpha_cycle_runs"] += 1
            self.stats["total_actions_submitted"] += len(all_actions)
            
            return {
                "ok": True,
                "af3_symbols": len(af3_result.get("truths", [])),
                "af3_actions": len(af3_actions),
                "af4_entry_modes": len(af4_result.get("evaluations", [])),
                "af4_actions": len(af4_actions),
                "total_actions": len(all_actions),
                "control_result": control_result,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            
        except Exception as e:
            self.stats["last_error"] = {"job": "alpha_cycle", "error": str(e), "timestamp": datetime.now(timezone.utc).isoformat()}
            return {"ok": False, "error": str(e)}
    
    def get_stats(self) -> Dict[str, Any]:
        """Get job execution statistics."""
        return self.stats.copy()
