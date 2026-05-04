"""
Routing Engine - PHASE 5.3
==========================

Main orchestrator for order routing decisions.
"""

from typing import Dict, List, Optional, Any
from datetime import datetime
import uuid

from .routing_types import (
    RoutingRequest,
    RoutingDecision,
    ExecutionPlan,
    VenueScore,
    VenueAnalysis,
    RoutingEvent,
    RoutingPolicy,
    RoutingUrgency,
    VenueStatus
)
from .venue_selector import get_venue_selector
from .execution_plan_builder import get_plan_builder
from .slippage_aware_router import get_slippage_router

import sys
sys.path.append('/app/backend')
from modules.execution.failover.failover_engine import get_failover_engine


class RoutingEngine:
    """
    Main order routing engine.
    
    Responsibilities:
    - Evaluate routing options
    - Make routing decisions
    - Build execution plans
    - Apply failover-aware routing
    - Log routing events
    """
    
    def __init__(self):
        self._venue_selector = get_venue_selector()
        self._plan_builder = get_plan_builder()
        self._slippage_router = get_slippage_router()
        self._failover_engine = get_failover_engine()
        
        # Event log
        self._events: List[RoutingEvent] = []
        self._max_events = 1000
        
        # Routing statistics
        self._stats = {
            "total_requests": 0,
            "decisions_made": 0,
            "plans_created": 0,
            "failover_routes": 0,
            "by_exchange": {},
            "by_policy": {}
        }
    
    # ============================================
    # Main Routing Methods
    # ============================================
    
    def evaluate(self, request: RoutingRequest) -> RoutingDecision:
        """
        Evaluate routing options and make decision.
        
        Args:
            request: Routing request
            
        Returns:
            Routing decision
        """
        self._stats["total_requests"] += 1
        
        # Check failover status first
        failover_exchange = self._check_failover_routing(request)
        if failover_exchange:
            request.preferred_exchange = failover_exchange
            self._stats["failover_routes"] += 1
        
        # Get routing decision based on urgency
        if request.urgency == RoutingUrgency.IMMEDIATE:
            decision = self._route_immediate(request)
        elif request.urgency == RoutingUrgency.HIGH:
            decision = self._route_fast(request)
        else:
            decision = self._route_optimal(request)
        
        # Log event
        self._log_decision(decision, request)
        
        # Update stats
        self._stats["decisions_made"] += 1
        ex = decision.selected_exchange
        self._stats["by_exchange"][ex] = self._stats["by_exchange"].get(ex, 0) + 1
        pol = decision.policy_used.value
        self._stats["by_policy"][pol] = self._stats["by_policy"].get(pol, 0) + 1
        
        return decision
    
    def create_plan(
        self,
        request: RoutingRequest,
        force_split: bool = False
    ) -> ExecutionPlan:
        """
        Create execution plan for order.
        
        Args:
            request: Routing request
            force_split: Force split execution
            
        Returns:
            Execution plan
        """
        plan = self._plan_builder.build_plan(request, force_split)
        
        # Log event
        self._log_plan_created(plan, request)
        
        self._stats["plans_created"] += 1
        
        return plan
    
    def get_venue_analysis(
        self,
        symbol: str,
        size: float,
        side: str
    ) -> Dict[str, VenueAnalysis]:
        """Get detailed analysis for all venues"""
        return self._venue_selector.get_all_venue_analyses(symbol, size, side)
    
    def get_best_venues(
        self,
        symbol: str,
        side: str,
        size: float,
        top_n: int = 3
    ) -> List[VenueScore]:
        """Get top N venues for order"""
        request = RoutingRequest(
            symbol=symbol,
            side=side,
            size=size
        )
        
        _, all_scores = self._venue_selector.select_venue(
            request, RoutingPolicy.BEST_EXECUTION
        )
        
        # Sort by total score
        sorted_scores = sorted(all_scores, key=lambda s: s.total_score, reverse=True)
        
        return sorted_scores[:top_n]
    
    def predict_execution(
        self,
        request: RoutingRequest
    ) -> Dict:
        """Predict execution outcome"""
        # Get decision
        decision = self.evaluate(request)
        
        # Get slippage prediction
        slippage_pred = self._slippage_router.predict_slippage(
            decision.selected_exchange,
            request.symbol,
            request.side,
            request.size
        )
        
        return {
            "symbol": request.symbol,
            "side": request.side,
            "size": request.size,
            "selected_venue": decision.selected_exchange,
            "expected_price": decision.expected_price,
            "expected_total_usd": round(request.size * decision.expected_price, 2),
            "expected_slippage_bps": decision.expected_slippage_bps,
            "expected_slippage_usd": round(
                request.size * decision.expected_price * decision.expected_slippage_bps / 10000, 2
            ),
            "expected_fee_usd": decision.expected_fee,
            "confidence": decision.confidence,
            "routing_reason": decision.routing_reason,
            "slippage_warning": slippage_pred.get("warning"),
            "recommendation": slippage_pred.get("recommendation"),
            "timestamp": datetime.utcnow().isoformat()
        }
    
    # ============================================
    # Failover-Aware Routing
    # ============================================
    
    def _check_failover_routing(self, request: RoutingRequest) -> Optional[str]:
        """
        Check if failover routing should be applied.
        
        Returns:
            Alternative exchange if failover needed, None otherwise
        """
        # Get system status
        system_status = self._failover_engine.get_system_status()
        
        if system_status.get("system_status") in ["FAILOVER", "EMERGENCY"]:
            # Find healthy alternative
            for exchange in ["BINANCE", "BYBIT", "OKX"]:
                if exchange in request.excluded_exchanges:
                    continue
                    
                ex_status = self._failover_engine.get_exchange_status(exchange)
                health = ex_status.get("health", {})
                if health.get("status") == "NORMAL" and health.get("health_score", 0) > 0.8:
                    self._log_failover(request, exchange, system_status.get("system_status"))
                    return exchange
        
        # Check preferred exchange health
        if request.preferred_exchange:
            pref_status = self._failover_engine.get_exchange_status(request.preferred_exchange)
            pref_health = pref_status.get("health", {})
            
            if pref_health.get("status") in ["DEGRADED", "FAILOVER", "EMERGENCY", "OFFLINE"]:
                # Find alternative
                for exchange in ["BINANCE", "BYBIT", "OKX"]:
                    if exchange == request.preferred_exchange:
                        continue
                    if exchange in request.excluded_exchanges:
                        continue
                    
                    ex_status = self._failover_engine.get_exchange_status(exchange)
                    ex_health = ex_status.get("health", {})
                    if ex_health.get("status") == "NORMAL":
                        self._log_failover(
                            request, exchange,
                            f"Preferred {request.preferred_exchange} is {pref_health.get('status')}"
                        )
                        return exchange
        
        return None
    
    # ============================================
    # Routing Strategies
    # ============================================
    
    def _route_immediate(self, request: RoutingRequest) -> RoutingDecision:
        """Route for immediate execution - fastest healthy venue"""
        # Get venue with best health and lowest latency
        request.policy = RoutingPolicy.SAFEST_VENUE
        selected, all_scores = self._venue_selector.select_venue(request)
        
        return self._build_decision(selected, all_scores, request, "Immediate execution")
    
    def _route_fast(self, request: RoutingRequest) -> RoutingDecision:
        """Route for fast execution - balance speed and price"""
        request.policy = RoutingPolicy.BEST_EXECUTION
        selected, all_scores = self._venue_selector.select_venue(request)
        
        return self._build_decision(selected, all_scores, request, "Fast execution")
    
    def _route_optimal(self, request: RoutingRequest) -> RoutingDecision:
        """Route for optimal execution - use slippage-aware router"""
        decision = self._slippage_router.route_with_slippage_awareness(request)
        return decision
    
    def _build_decision(
        self,
        selected: VenueScore,
        all_scores: List[VenueScore],
        request: RoutingRequest,
        reason_prefix: str
    ) -> RoutingDecision:
        """Build routing decision"""
        return RoutingDecision(
            request_id=request.client_id or f"REQ_{uuid.uuid4().hex[:12]}",
            symbol=request.symbol,
            side=request.side,
            size=request.size,
            selected_exchange=selected.exchange,
            selected_order_type=request.order_type,
            expected_price=selected.price,
            expected_slippage_bps=selected.expected_slippage_bps + selected.historical_slippage_bps,
            expected_fee=selected.estimated_fee,
            confidence=min(1.0, selected.total_score + 0.1),
            routing_reason=f"{reason_prefix}: {selected.exchange} selected with score {selected.total_score:.2f}",
            alternative_venues=[s.exchange for s in all_scores if s.exchange != selected.exchange],
            venue_scores=all_scores,
            policy_used=request.policy
        )
    
    # ============================================
    # Event Logging
    # ============================================
    
    def _log_decision(self, decision: RoutingDecision, request: RoutingRequest) -> None:
        """Log routing decision event"""
        event = RoutingEvent(
            event_type="ROUTING_DECISION_MADE",
            request_id=decision.request_id,
            symbol=decision.symbol,
            selected_exchange=decision.selected_exchange,
            reason=decision.routing_reason,
            metrics={
                "expected_price": decision.expected_price,
                "expected_slippage_bps": decision.expected_slippage_bps,
                "confidence": decision.confidence,
                "policy": decision.policy_used.value
            }
        )
        self._add_event(event)
    
    def _log_plan_created(self, plan: ExecutionPlan, request: RoutingRequest) -> None:
        """Log plan created event"""
        event = RoutingEvent(
            event_type="EXECUTION_PLAN_CREATED",
            request_id=request.client_id or plan.plan_id,
            symbol=plan.symbol,
            reason=f"Created {plan.execution_mode.value} plan with {len(plan.legs)} legs",
            metrics={
                "total_size": plan.total_size,
                "estimated_avg_price": plan.estimated_avg_price,
                "estimated_slippage_bps": plan.estimated_slippage_bps,
                "legs": len(plan.legs),
                "venues": [leg.exchange for leg in plan.legs]
            }
        )
        self._add_event(event)
    
    def _log_failover(
        self,
        request: RoutingRequest,
        new_exchange: str,
        reason: str
    ) -> None:
        """Log failover routing event"""
        event = RoutingEvent(
            event_type="FAILOVER_ROUTE_APPLIED",
            request_id=request.client_id or f"REQ_{uuid.uuid4().hex[:8]}",
            symbol=request.symbol,
            selected_exchange=new_exchange,
            rejected_exchanges=[request.preferred_exchange] if request.preferred_exchange else [],
            reason=f"Failover applied: {reason}",
            metrics={"original_exchange": request.preferred_exchange}
        )
        self._add_event(event)
    
    def _add_event(self, event: RoutingEvent) -> None:
        """Add event to log"""
        self._events.append(event)
        if len(self._events) > self._max_events:
            self._events = self._events[-self._max_events:]
    
    # ============================================
    # Status and Statistics
    # ============================================
    
    def get_routing_events(self, limit: int = 50) -> List[Dict]:
        """Get recent routing events"""
        events = self._events[-limit:]
        return [e.dict() for e in reversed(events)]
    
    def get_routing_stats(self) -> Dict:
        """Get routing statistics"""
        return {
            **self._stats,
            "events_logged": len(self._events),
            "timestamp": datetime.utcnow().isoformat()
        }
    
    def get_available_policies(self) -> List[Dict]:
        """Get available routing policies"""
        return [
            {
                "policy": RoutingPolicy.BEST_PRICE.value,
                "description": "Route to venue with best price"
            },
            {
                "policy": RoutingPolicy.BEST_EXECUTION.value,
                "description": "Optimize for overall execution quality (price + slippage + liquidity)"
            },
            {
                "policy": RoutingPolicy.SAFEST_VENUE.value,
                "description": "Route to most reliable venue"
            },
            {
                "policy": RoutingPolicy.LOW_SLIPPAGE.value,
                "description": "Minimize expected slippage"
            },
            {
                "policy": RoutingPolicy.LOWEST_FEE.value,
                "description": "Route to venue with lowest fees"
            },
            {
                "policy": RoutingPolicy.SPLIT_ORDER.value,
                "description": "Split order across multiple venues"
            }
        ]


# Global instance
_routing_engine: Optional[RoutingEngine] = None


def get_routing_engine() -> RoutingEngine:
    """Get or create global routing engine"""
    global _routing_engine
    if _routing_engine is None:
        _routing_engine = RoutingEngine()
    return _routing_engine
