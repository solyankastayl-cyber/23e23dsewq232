"""
Lifecycle Orchestrator - ORCH-6

Continuous brain for position and order lifecycle management.
Evaluates market_state every cycle and generates smart actions.

This is NOT single-run - this is event loop brain.
"""

import logging
from typing import Dict, List, Any
from .lifecycle_policy import LifecyclePolicy

logger = logging.getLogger(__name__)


class LifecycleOrchestrator:
    """
    Continuous lifecycle orchestrator.
    
    This is the BRAIN that runs every 3-5 seconds and makes decisions:
    - Which positions to reduce/close
    - Which orders to cancel/replace
    - When to trail stops
    
    Integrates with:
    - LifecyclePolicy (decision layer)
    - AF6 (alpha-driven exits)
    - Market state (price, regime, validation, risk)
    """
    
    def __init__(self, lifecycle_controller, order_manager, position_engine):
        self.lifecycle_controller = lifecycle_controller
        self.order_manager = order_manager
        self.position_engine = position_engine
        self.policy = LifecyclePolicy()
    
    def run(self, market_state: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Run lifecycle cycle.
        
        This is called every 3-5 seconds by continuous loop.
        
        Args:
            market_state: Current market state with:
                - current_price
                - pnl_pct
                - alpha_state (AF6)
                - validation_state
                - regime_state
                - risk_state
                - control flags (cancel_stale_orders, reprice_passive_orders)
        
        Returns:
            Cycle result with actions and results
        """
        market_state = market_state or {}
        actions: List[Dict[str, Any]] = []
        results: List[Dict[str, Any]] = []
        
        logger.debug("[LifecycleOrchestrator] Running cycle...")
        
        # 1. Evaluate all open orders
        for order in self.order_manager.list_open():
            order_actions = self.policy.evaluate_order(order, market_state)
            actions.extend(order_actions)
        
        # 2. Evaluate all open positions
        for pos in self.position_engine.list():
            size = float(pos.get("size", 0.0) or 0.0)
            if size <= 0:
                continue
            
            # Compute PnL for this position
            current_price = market_state.get("current_price")
            if current_price:
                avg_entry = float(pos.get("avg_entry", 0.0) or 0.0)
                side = pos.get("side", "LONG")
                
                if avg_entry > 0:
                    if side == "LONG":
                        pnl_pct = (current_price - avg_entry) / avg_entry
                    else:
                        pnl_pct = (avg_entry - current_price) / avg_entry
                else:
                    pnl_pct = 0.0
                
                # Update market_state with position-specific PnL
                position_market_state = {
                    **market_state,
                    "pnl_pct": pnl_pct,
                }
                
                position_actions = self.policy.evaluate_position(pos, position_market_state)
                actions.extend(position_actions)
        
        # 3. Sort actions by priority (HIGH → MEDIUM → LOW)
        priority_order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
        actions.sort(key=lambda a: priority_order.get(a.get("priority", "LOW"), 2))
        
        # 4. Execute actions
        for action in actions:
            try:
                result = self.lifecycle_controller.dispatch(action)
                results.append({
                    "action": action,
                    "result": result,
                })
            except Exception as e:
                logger.error(f"[LifecycleOrchestrator] Action failed: {e}")
                results.append({
                    "action": action,
                    "result": {"ok": False, "error": str(e)},
                })
        
        logger.info(f"[LifecycleOrchestrator] Cycle complete: {len(actions)} actions, {len(results)} results")
        
        return {
            "actions": actions,
            "results": results,
            "actions_count": len(actions),
            "success_count": sum(1 for r in results if r.get("result", {}).get("ok")),
        }
