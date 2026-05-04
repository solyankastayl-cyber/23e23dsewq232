"""
Execution Intent Builder
========================

Builds normalized execution intent from Final Gate result.
"""

from typing import Dict, Any
from .routing_models import ExecutionIntent


class ExecutionIntentBuilder:
    """Builds execution intent from gate result and execution plan."""
    
    def build(
        self, 
        symbol: str, 
        timeframe: str, 
        gate_result: Dict[str, Any], 
        execution_plan: Dict[str, Any],
        trace_id: str = None  # P0.7.1: Audit trace ID
    ) -> ExecutionIntent:
        """Build execution intent."""
        
        # If blocked by Final Gate
        if gate_result.get("blocked"):
            return ExecutionIntent(
                symbol=symbol,
                timeframe=timeframe,
                action="BLOCK",
                side=execution_plan.get("side", "NONE"),
                size=0.0,
                mode="BLOCKED",
                entry=None,
                stop=None,
                target=None,
                blocked=True,
                block_reason=gate_result.get("block_reason"),
                trace_id=trace_id  # P0.7.1
            )
        
        # Get enforced decision
        enforced = gate_result.get("decision_enforced") or {}
        
        # Calculate final size
        requested_size = float(execution_plan.get("size", 0.0) or 0.0)
        size_multiplier = float(gate_result.get("size_multiplier", 1.0) or 1.0)
        final_size = round(requested_size * size_multiplier, 8)
        
        # Get mode (forced mode takes priority)
        mode = (
            gate_result.get("forced_execution_mode") 
            or execution_plan.get("mode") 
            or enforced.get("mode")
            or enforced.get("forced_mode") 
            or "PASSIVE"
        )
        
        # Determine side
        side = (
            execution_plan.get("side")
            or enforced.get("direction")
            or "NONE"
        )
        
        return ExecutionIntent(
            symbol=symbol,
            timeframe=timeframe,
            action=gate_result.get("final_action", "ALLOW"),
            side=side,
            size=final_size,
            mode=mode,
            entry=execution_plan.get("entry"),
            stop=execution_plan.get("stop"),
            target=execution_plan.get("target"),
            blocked=False,
            block_reason=None,
            strategy_id=execution_plan.get("strategy_id", "default"),  # ORCH-7 PHASE 3
            trace_id=trace_id  # P0.7.1
        )
