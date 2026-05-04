"""
Execution Controller - ORCH-2 + ORCH-4 + ORCH-5 + ORCH-6
========================================================

Main orchestrator for execution intent building and routing.

ORCH-4 Upgrade:
- Replaced OrderRouter with ExchangeRouter (real exchange routing)
- Added OrderManager for order registry
- Supports paper trading and binance routing

ORCH-5 Upgrade:
- Added ExecutionSync for order lifecycle
- Processes fills and creates positions
- Returns lifecycle updates in response

ORCH-6 Upgrade:
- Added LifecycleController for action dispatching
- Added LifecycleOrchestrator for continuous brain
- Supports cancel/replace/reduce/close/trail operations
"""

from typing import Dict, Any
from .execution_intent_builder import ExecutionIntentBuilder
from ...execution_live import ExchangeRouter, OrderManager, ExecutionSync
from ...execution_live.lifecycle_control import LifecycleController, LifecycleOrchestrator


class ExecutionController:
    """Main execution controller (ORCH-2 + ORCH-4 + ORCH-5 + ORCH-6)."""
    
    def __init__(self, route_type: str = "simulation"):
        self.intent_builder = ExecutionIntentBuilder()
        self.router = ExchangeRouter()
        self.order_manager = OrderManager()
        self.execution_sync = ExecutionSync(self.order_manager)
        
        # ORCH-6: Lifecycle control
        self.lifecycle_controller = LifecycleController(
            self.order_manager,
            self.execution_sync.position_engine,
        )
        
        self.lifecycle_orchestrator = LifecycleOrchestrator(
            self.lifecycle_controller,
            self.order_manager,
            self.execution_sync.position_engine,
        )
    
    async def run(
        self, 
        symbol: str, 
        timeframe: str, 
        gate_result: Dict[str, Any], 
        execution_plan: Dict[str, Any],
        market_state: Dict[str, Any] = None,  # ORCH-6: New parameter
        trace_id: str = None,  # P1.3.1: NEW parameter for shadow integration
    ) -> Dict[str, Any]:
        """
        Run execution control pipeline.
        
        P1.3.1C: ASYNC REFACTORED для shadow integration.
        """
        # Build normalized intent
        intent = self.intent_builder.build(
            symbol=symbol,
            timeframe=timeframe,
            gate_result=gate_result,
            execution_plan=execution_plan,
        )
        
        intent_dict = intent.to_dict()
        intent_dict["route_type"] = execution_plan.get("route_type", "paper")
        
        # ========================================
        # P1.3.3 — ROUTING CONTROL PLANE
        # ========================================
        # Deterministic canary routing with kill switch + health gate
        try:
            from ...execution_reality.integration import (
                get_execution_queue_integration_service
            )
            from ...execution_reality.integration.execution_routing_policy import (
                make_routing_decision,
                get_routing_policy
            )
            from ...execution_reality.integration.execution_routing_stats import (
                increment_routing_stat
            )
            
            integration_service = get_execution_queue_integration_service()
            routing_policy = get_routing_policy()
            
            # P1.3.3: Make routing decision (DETERMINISTIC)
            # CRITICAL: Kill switch is FIRST CHECK inside make_routing_decision
            routing_decision = make_routing_decision(
                policy=routing_policy,
                trace_id=trace_id,
                symbol=symbol,
                order_type=execution_plan.get("mode", "MARKET"),
                account_id=execution_plan.get("account_id", "default"),
                queue_healthy=True  # TODO: implement queue health service
            )
            
            import logging
            logger = logging.getLogger(__name__)
            
            logger.info(
                f"[P1.3.3 Routing] Decision: trace_id={trace_id[:16]}..., "
                f"route_to_queue={routing_decision.route_to_queue}, "
                f"execute_legacy={routing_decision.execute_legacy}, "
                f"reason={routing_decision.reason}"
            )
            
            # Define direct submit callable (async wrapper для legacy path)
            async def _direct_submit_callable():
                # Route intent through ExchangeRouter (legacy path)
                routing_result = self.router.route(intent_dict)
                return routing_result
            
            routing = None
            
            # P1.3.3: Routing logic based on decision
            if routing_decision.route_to_queue and integration_service:
                # Queue path (canary or shadow)
                try:
                    integration_result = await integration_service.handle_approved_decision(
                        symbol=symbol,
                        gate_result=gate_result,
                        execution_plan=execution_plan,
                        trace_id=trace_id,
                        direct_submit_callable=_direct_submit_callable
                    )
                    
                    logger.info(
                        f"[P1.3.3] Queue dispatch: dispatched={integration_result.get('dispatchResult', {}).get('dispatched')}"
                    )
                    
                    # Increment queue stat
                    increment_routing_stat("queue_executions")
                    
                    # If legacy also executed (SHADOW mode)
                    if routing_decision.execute_legacy:
                        routing = integration_result.get('legacyResult')
                        increment_routing_stat("legacy_executions")
                    else:
                        # Queue-only (CANARY selected or QUEUE_ONLY mode)
                        if integration_result.get('legacySubmitExecuted'):
                            # Unexpected: legacy executed despite queue-only decision
                            logger.warning(
                                f"[P1.3.3] Unexpected legacy execution in queue-only mode"
                            )
                            routing = integration_result.get('legacyResult')
                        else:
                            # Queue stub (worker will process)
                            routing = {
                                "accepted": True,
                                "order_id": f"queue-{integration_result.get('dispatchResult', {}).get('jobId', 'unknown')[:8]}",
                                "status": "QUEUED",
                                "route_type": "execution_queue",
                                "message": "Job enqueued (canary routing)"
                            }
                
                except Exception as queue_error:
                    # CRITICAL: Queue failure → FALLBACK to legacy
                    logger.error(
                        f"❌ [P1.3.3 FALLBACK] Queue failed, executing legacy: {queue_error}",
                        exc_info=True
                    )
                    
                    increment_routing_stat("fallbacks")
                    
                    # Execute legacy as fallback
                    routing = await _direct_submit_callable()
                    increment_routing_stat("legacy_executions")
            
            elif routing_decision.execute_legacy:
                # Legacy-only path (LEGACY_ONLY mode or canary not selected)
                routing = await _direct_submit_callable()
                increment_routing_stat("legacy_executions")
            
            else:
                # Should not reach (safety fallback)
                logger.warning(
                    f"[P1.3.3] No routing path selected, falling back to legacy"
                )
                routing = await _direct_submit_callable()
                increment_routing_stat("legacy_executions")
                increment_routing_stat("fallbacks")
        
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"[P1.3.1C Shadow] Integration error: {e}", exc_info=True)
            # Fallback to legacy path on error
            routing = self.router.route(intent_dict)
        
        # Register order if routing succeeded
        if routing.get("accepted") and routing.get("order_id"):
            initial_status = "PLACED" if routing["status"] == "FILLED" else routing["status"]
            
            self.order_manager.register({
                "order_id": routing["order_id"],
                "exchange_order_id": routing.get("exchange_order_id"),
                "symbol": intent.symbol,
                "timeframe": timeframe,
                "side": intent.side,
                "size": intent.size,
                "entry": intent.entry,
                "stop": intent.stop,
                "target": intent.target,
                "mode": intent.mode,
                "route_type": routing["route_type"],
                "status": initial_status,
                "filled_qty": 0.0,
                "remaining_qty": intent.size,
            })
        
        # ORCH-5: Sync order lifecycle and process fills
        sync_result = self.execution_sync.sync()
        
        # ORCH-6: Run lifecycle orchestrator
        lifecycle_result = self.lifecycle_orchestrator.run(market_state=market_state or {})
        
        return {
            "intent": intent_dict,
            "routing": routing,
            "lifecycle": sync_result,
            "lifecycle_control": lifecycle_result,  # ORCH-6
            "orders": self.order_manager.list_all(),
        }

