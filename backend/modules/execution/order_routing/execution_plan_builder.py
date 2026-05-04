"""
Execution Plan Builder - PHASE 5.3
==================================

Builds execution plans for large orders, including multi-venue splits.
"""

from typing import Dict, List, Optional, Tuple
from datetime import datetime
import uuid

from .routing_types import (
    RoutingRequest,
    ExecutionPlan,
    ExecutionLeg,
    ExecutionMode,
    VenueScore,
    RoutingPolicy
)
from .venue_selector import get_venue_selector

import sys
sys.path.append('/app/backend')
from modules.market_data.market_data_engine import get_market_data_engine


class ExecutionPlanBuilder:
    """
    Builds execution plans for orders.
    
    Supports:
    - Single venue execution
    - Split execution across venues
    - TWAP/VWAP scheduling (future)
    - Iceberg orders (future)
    """
    
    # Thresholds for splitting
    LIQUIDITY_THRESHOLD_PCT = 10.0  # Split if size > X% of top-of-book
    MIN_SPLIT_SIZE_USD = 1000.0     # Minimum USD value for split leg
    MAX_VENUES = 3                   # Max venues for split
    
    def __init__(self):
        self._venue_selector = get_venue_selector()
        self._market_engine = get_market_data_engine()
    
    def build_plan(
        self,
        request: RoutingRequest,
        force_split: bool = False
    ) -> ExecutionPlan:
        """
        Build execution plan for order.
        
        Args:
            request: Routing request
            force_split: Force split even if not needed
            
        Returns:
            Execution plan
        """
        plan_id = f"PLAN_{uuid.uuid4().hex[:12]}"
        
        # Analyze all venues
        analyses = self._venue_selector.get_all_venue_analyses(
            request.symbol,
            request.size,
            request.side
        )
        
        if not analyses:
            raise ValueError(f"No venues available for {request.symbol}")
        
        # Calculate total available liquidity
        total_liquidity = sum(
            a.can_fill_size for a in analyses.values()
            if a.recommended
        )
        
        # Determine if split is needed
        should_split = force_split or self._should_split(
            request, analyses, total_liquidity
        )
        
        if should_split:
            return self._build_split_plan(plan_id, request, analyses)
        else:
            return self._build_single_plan(plan_id, request)
    
    def _should_split(
        self,
        request: RoutingRequest,
        analyses: Dict,
        total_liquidity: float
    ) -> bool:
        """Determine if order should be split"""
        # Check if size exceeds threshold of best venue's liquidity
        best_venue = max(
            analyses.values(),
            key=lambda a: a.can_fill_size if a.recommended else 0
        )
        
        if best_venue.can_fill_size <= 0:
            return False
        
        liquidity_pct = (request.size / best_venue.can_fill_size) * 100
        
        # Split if:
        # 1. Size > threshold % of best venue liquidity
        # 2. Expected slippage would be high
        # 3. Policy is SPLIT_ORDER
        
        if request.policy == RoutingPolicy.SPLIT_ORDER:
            return True
        
        if liquidity_pct > self.LIQUIDITY_THRESHOLD_PCT:
            return True
        
        if best_venue.slippage_for_size_bps > request.max_slippage_bps:
            return True
        
        return False
    
    def _build_single_plan(
        self,
        plan_id: str,
        request: RoutingRequest
    ) -> ExecutionPlan:
        """Build plan for single venue execution"""
        # Select best venue
        selected, all_scores = self._venue_selector.select_venue(request, request.policy)
        
        # Build single leg
        leg = ExecutionLeg(
            exchange=selected.exchange,
            size=request.size,
            percentage=100.0,
            order_type=request.order_type,
            limit_price=request.limit_price,
            expected_price=selected.price,
            expected_slippage_bps=selected.expected_slippage_bps,
            priority=1
        )
        
        plan = ExecutionPlan(
            plan_id=plan_id,
            symbol=request.symbol,
            side=request.side,
            total_size=request.size,
            legs=[leg],
            estimated_avg_price=selected.price,
            estimated_total_cost=request.size * selected.price,
            estimated_slippage_bps=selected.expected_slippage_bps,
            estimated_fees=selected.estimated_fee,
            execution_mode=ExecutionMode.SINGLE,
            estimated_duration_ms=100
        )
        
        return plan
    
    def _build_split_plan(
        self,
        plan_id: str,
        request: RoutingRequest,
        analyses: Dict
    ) -> ExecutionPlan:
        """Build plan for split execution across venues"""
        # Sort venues by recommendation and liquidity
        sorted_venues = sorted(
            [(ex, a) for ex, a in analyses.items() if a.recommended],
            key=lambda x: x[1].can_fill_size,
            reverse=True
        )
        
        if not sorted_venues:
            # Fall back to single venue if no recommended
            return self._build_single_plan(plan_id, request)
        
        # Calculate split allocation
        remaining_size = request.size
        legs = []
        total_weighted_price = 0.0
        total_slippage = 0.0
        total_fees = 0.0
        priority = 1
        
        for exchange, analysis in sorted_venues[:self.MAX_VENUES]:
            if remaining_size <= 0:
                break
            
            # Allocate based on liquidity
            available = analysis.can_fill_size
            allocation = min(remaining_size, available * 0.8)  # Take 80% of available
            
            # Check minimum size
            price = analysis.best_ask if request.side == "BUY" else analysis.best_bid
            if price > 0 and allocation * price < self.MIN_SPLIT_SIZE_USD:
                continue
            
            leg = ExecutionLeg(
                exchange=exchange,
                size=allocation,
                percentage=round((allocation / request.size) * 100, 2),
                order_type=request.order_type,
                limit_price=request.limit_price,
                expected_price=price,
                expected_slippage_bps=analysis.slippage_for_size_bps * (allocation / analysis.can_fill_size),
                priority=priority
            )
            legs.append(leg)
            
            # Update totals
            remaining_size -= allocation
            total_weighted_price += price * allocation
            total_slippage += leg.expected_slippage_bps * (allocation / request.size)
            total_fees += allocation * price * self._venue_selector.DEFAULT_FEES.get(exchange, 0.0005)
            priority += 1
        
        # If we couldn't allocate all, add remainder to first venue
        if remaining_size > 0 and legs:
            legs[0].size += remaining_size
            legs[0].percentage = round((legs[0].size / request.size) * 100, 2)
        
        # Calculate averages
        filled_size = sum(leg.size for leg in legs)
        avg_price = total_weighted_price / filled_size if filled_size > 0 else 0
        
        plan = ExecutionPlan(
            plan_id=plan_id,
            symbol=request.symbol,
            side=request.side,
            total_size=request.size,
            legs=legs,
            estimated_avg_price=round(avg_price, 2),
            estimated_total_cost=round(filled_size * avg_price, 2),
            estimated_slippage_bps=round(total_slippage, 2),
            estimated_fees=round(total_fees, 4),
            execution_mode=ExecutionMode.SPLIT,
            estimated_duration_ms=len(legs) * 150  # ~150ms per leg
        )
        
        return plan
    
    def estimate_execution(
        self,
        plan: ExecutionPlan
    ) -> Dict:
        """Estimate execution outcome for a plan"""
        total_value = plan.estimated_total_cost
        
        return {
            "plan_id": plan.plan_id,
            "execution_mode": plan.execution_mode.value,
            "num_legs": len(plan.legs),
            "venues": [leg.exchange for leg in plan.legs],
            "total_size": plan.total_size,
            "estimated_avg_price": plan.estimated_avg_price,
            "estimated_total_cost_usd": total_value,
            "estimated_slippage_bps": plan.estimated_slippage_bps,
            "estimated_slippage_usd": round(total_value * plan.estimated_slippage_bps / 10000, 2),
            "estimated_fees_usd": plan.estimated_fees,
            "estimated_duration_ms": plan.estimated_duration_ms,
            "confidence": self._calculate_confidence(plan)
        }
    
    def _calculate_confidence(self, plan: ExecutionPlan) -> float:
        """Calculate confidence score for plan"""
        # Base confidence
        confidence = 0.8
        
        # Adjust for slippage
        if plan.estimated_slippage_bps > 50:
            confidence -= 0.2
        elif plan.estimated_slippage_bps > 20:
            confidence -= 0.1
        
        # Adjust for number of legs (more legs = more complexity)
        confidence -= (len(plan.legs) - 1) * 0.05
        
        return max(0.3, min(1.0, round(confidence, 2)))


# Global instance
_plan_builder: Optional[ExecutionPlanBuilder] = None


def get_plan_builder() -> ExecutionPlanBuilder:
    """Get or create global plan builder"""
    global _plan_builder
    if _plan_builder is None:
        _plan_builder = ExecutionPlanBuilder()
    return _plan_builder
