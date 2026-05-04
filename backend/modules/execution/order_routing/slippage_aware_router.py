"""
Slippage-Aware Router - PHASE 5.3
=================================

Routes orders with awareness of historical slippage profiles.
"""

from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta

from .routing_types import (
    RoutingRequest,
    RoutingDecision,
    VenueScore,
    RoutingPolicy,
    VenueStatus
)
from .venue_selector import get_venue_selector

import sys
sys.path.append('/app/backend')
from modules.execution.slippage.slippage_engine import get_slippage_engine


class SlippageAwareRouter:
    """
    Routes orders with slippage awareness.
    
    Uses historical slippage data to:
    - Avoid venues with poor execution quality
    - Predict expected slippage
    - Adjust routing based on order size
    """
    
    # Slippage thresholds
    MAX_ACCEPTABLE_SLIPPAGE_BPS = 50.0
    WARNING_SLIPPAGE_BPS = 20.0
    
    def __init__(self):
        self._venue_selector = get_venue_selector()
        self._slippage_engine = get_slippage_engine()
        
        # Historical performance cache
        self._venue_performance: Dict[str, Dict] = {}
    
    def route_with_slippage_awareness(
        self,
        request: RoutingRequest
    ) -> RoutingDecision:
        """
        Make routing decision with slippage awareness.
        
        Args:
            request: Routing request
            
        Returns:
            Routing decision with slippage-adjusted selection
        """
        symbol = request.symbol
        side = request.side
        size = request.size
        
        # Get venue scores
        selected, all_scores = self._venue_selector.select_venue(
            request,
            RoutingPolicy.LOW_SLIPPAGE if request.max_slippage_bps < 30 else request.policy
        )
        
        # Enhance with slippage analysis
        enhanced_scores = self._enhance_with_slippage(all_scores, symbol, side, size)
        
        # Re-select if slippage data changes ranking
        if enhanced_scores:
            best = self._select_best_slippage_venue(enhanced_scores, request)
            if best and best.exchange != selected.exchange:
                # Slippage data suggests different venue
                if best.expected_slippage_bps < selected.expected_slippage_bps * 0.8:
                    selected = best
        
        # Build decision
        decision = RoutingDecision(
            request_id=request.client_id or f"REQ_{datetime.utcnow().timestamp()}",
            symbol=symbol,
            side=side,
            size=size,
            selected_exchange=selected.exchange,
            selected_order_type=request.order_type,
            expected_price=selected.price,
            expected_slippage_bps=selected.expected_slippage_bps + selected.historical_slippage_bps,
            expected_fee=selected.estimated_fee,
            confidence=self._calculate_slippage_confidence(selected),
            routing_reason=self._build_routing_reason(selected, request),
            alternative_venues=[s.exchange for s in all_scores if s.exchange != selected.exchange],
            venue_scores=all_scores,
            policy_used=request.policy
        )
        
        return decision
    
    def get_slippage_profile(
        self,
        exchange: str,
        symbol: str
    ) -> Dict:
        """Get slippage profile for exchange/symbol"""
        stats = self._slippage_engine.get_slippage_stats(exchange, symbol)
        
        if not stats:
            return {
                "exchange": exchange,
                "symbol": symbol,
                "has_data": False,
                "avg_slippage_bps": 0,
                "max_slippage_bps": 0,
                "fill_rate": 1.0,
                "sample_count": 0
            }
        
        return {
            "exchange": exchange,
            "symbol": symbol,
            "has_data": True,
            "avg_slippage_bps": stats.get("avg_slippage_bps", 0),
            "max_slippage_bps": stats.get("max_slippage_bps", 0),
            "min_slippage_bps": stats.get("min_slippage_bps", 0),
            "fill_rate": stats.get("fill_rate", 1.0),
            "sample_count": stats.get("sample_count", 0),
            "recent_trend": stats.get("trend", "STABLE")
        }
    
    def predict_slippage(
        self,
        exchange: str,
        symbol: str,
        side: str,
        size: float
    ) -> Dict:
        """Predict slippage for an order"""
        # Get slippage estimate from engine
        estimate = self._slippage_engine.estimate_slippage(
            exchange, symbol, side, size
        )
        
        # Get profile for context
        profile = self.get_slippage_profile(exchange, symbol)
        
        return {
            "exchange": exchange,
            "symbol": symbol,
            "side": side,
            "size": size,
            "predicted_slippage_bps": estimate.get("expected_slippage_bps", 0) if estimate else 0,
            "confidence": estimate.get("confidence", 0.5) if estimate else 0.5,
            "historical_avg_bps": profile.get("avg_slippage_bps", 0),
            "warning": self._get_slippage_warning(estimate, profile),
            "recommendation": self._get_slippage_recommendation(estimate, profile)
        }
    
    def should_avoid_venue(
        self,
        exchange: str,
        symbol: str,
        max_acceptable_slippage: float = None
    ) -> Tuple[bool, str]:
        """
        Check if venue should be avoided due to slippage.
        
        Returns:
            Tuple of (should_avoid, reason)
        """
        max_slip = max_acceptable_slippage or self.MAX_ACCEPTABLE_SLIPPAGE_BPS
        profile = self.get_slippage_profile(exchange, symbol)
        
        if not profile.get("has_data"):
            return False, "No historical data"
        
        avg_slip = profile.get("avg_slippage_bps", 0)
        max_hist_slip = profile.get("max_slippage_bps", 0)
        fill_rate = profile.get("fill_rate", 1.0)
        
        # Check conditions for avoidance
        if avg_slip > max_slip:
            return True, f"Average slippage ({avg_slip:.1f} bps) exceeds threshold ({max_slip} bps)"
        
        if max_hist_slip > max_slip * 2:
            return True, f"Maximum slippage ({max_hist_slip:.1f} bps) is too high"
        
        if fill_rate < 0.8:
            return True, f"Fill rate ({fill_rate:.0%}) is below acceptable level"
        
        return False, "Venue acceptable"
    
    # ============================================
    # Private Methods
    # ============================================
    
    def _enhance_with_slippage(
        self,
        scores: List[VenueScore],
        symbol: str,
        side: str,
        size: float
    ) -> List[VenueScore]:
        """Enhance venue scores with slippage data"""
        enhanced = []
        
        for score in scores:
            # Get slippage prediction
            prediction = self.predict_slippage(
                score.exchange, symbol, side, size
            )
            
            # Update score with prediction
            predicted_slip = prediction.get("predicted_slippage_bps", 0)
            if predicted_slip > 0:
                # Weight current estimate with prediction
                score.expected_slippage_bps = (
                    score.expected_slippage_bps * 0.6 +
                    predicted_slip * 0.4
                )
            
            # Recalculate total score
            score.total_score = self._recalculate_score_with_slippage(score)
            enhanced.append(score)
        
        return enhanced
    
    def _recalculate_score_with_slippage(self, score: VenueScore) -> float:
        """Recalculate total score with emphasis on slippage"""
        base_score = score.total_score
        
        # Penalize for high slippage
        slippage_penalty = 0
        total_slippage = score.expected_slippage_bps + score.historical_slippage_bps
        
        if total_slippage > self.MAX_ACCEPTABLE_SLIPPAGE_BPS:
            slippage_penalty = 0.3
        elif total_slippage > self.WARNING_SLIPPAGE_BPS:
            slippage_penalty = 0.15
        elif total_slippage > 10:
            slippage_penalty = 0.05
        
        return max(0.1, base_score - slippage_penalty)
    
    def _select_best_slippage_venue(
        self,
        scores: List[VenueScore],
        request: RoutingRequest
    ) -> Optional[VenueScore]:
        """Select best venue based on slippage optimization"""
        # Filter by max acceptable slippage
        acceptable = [
            s for s in scores
            if (s.expected_slippage_bps + s.historical_slippage_bps) <= request.max_slippage_bps
            and s.health_status in [VenueStatus.OPTIMAL, VenueStatus.AVAILABLE]
        ]
        
        if not acceptable:
            # Return best from all if none meet criteria
            return max(scores, key=lambda s: s.total_score) if scores else None
        
        # Select by lowest combined slippage
        return min(
            acceptable,
            key=lambda s: s.expected_slippage_bps + s.historical_slippage_bps
        )
    
    def _calculate_slippage_confidence(self, score: VenueScore) -> float:
        """Calculate confidence based on slippage expectations"""
        total_slippage = score.expected_slippage_bps + score.historical_slippage_bps
        
        if total_slippage < 5:
            return 0.95
        elif total_slippage < 15:
            return 0.85
        elif total_slippage < 30:
            return 0.70
        elif total_slippage < 50:
            return 0.55
        else:
            return 0.40
    
    def _build_routing_reason(
        self,
        selected: VenueScore,
        request: RoutingRequest
    ) -> str:
        """Build human-readable routing reason"""
        reasons = []
        
        # Price advantage
        reasons.append(f"Best price available at ${selected.price:.2f}")
        
        # Slippage
        total_slip = selected.expected_slippage_bps + selected.historical_slippage_bps
        if total_slip < 10:
            reasons.append("excellent slippage profile")
        elif total_slip < 30:
            reasons.append("acceptable slippage")
        else:
            reasons.append(f"expected slippage {total_slip:.1f} bps")
        
        # Health
        if selected.health_status == VenueStatus.OPTIMAL:
            reasons.append("exchange fully operational")
        elif selected.health_status == VenueStatus.DEGRADED:
            reasons.append("exchange slightly degraded")
        
        # Liquidity
        if selected.liquidity_score > 0.9:
            reasons.append("high liquidity")
        elif selected.liquidity_score < 0.5:
            reasons.append("limited liquidity")
        
        return "; ".join(reasons)
    
    def _get_slippage_warning(self, estimate: Dict, profile: Dict) -> Optional[str]:
        """Get warning message if slippage is concerning"""
        if not estimate:
            return None
        
        predicted = estimate.get("expected_slippage_bps", 0)
        historical = profile.get("avg_slippage_bps", 0)
        
        if predicted > self.MAX_ACCEPTABLE_SLIPPAGE_BPS:
            return f"WARNING: Expected slippage ({predicted:.1f} bps) is very high"
        elif predicted > self.WARNING_SLIPPAGE_BPS:
            return f"CAUTION: Expected slippage ({predicted:.1f} bps) is elevated"
        elif historical > self.WARNING_SLIPPAGE_BPS:
            return f"NOTE: Historical slippage ({historical:.1f} bps) has been elevated"
        
        return None
    
    def _get_slippage_recommendation(self, estimate: Dict, profile: Dict) -> str:
        """Get recommendation based on slippage analysis"""
        if not estimate:
            return "Proceed with standard execution"
        
        predicted = estimate.get("expected_slippage_bps", 0)
        
        if predicted < 5:
            return "Optimal conditions for execution"
        elif predicted < 15:
            return "Good conditions, proceed normally"
        elif predicted < 30:
            return "Consider using limit orders"
        elif predicted < 50:
            return "Consider splitting order or using TWAP"
        else:
            return "High slippage expected - consider alternative venue or timing"


# Global instance
_slippage_router: Optional[SlippageAwareRouter] = None


def get_slippage_router() -> SlippageAwareRouter:
    """Get or create global slippage-aware router"""
    global _slippage_router
    if _slippage_router is None:
        _slippage_router = SlippageAwareRouter()
    return _slippage_router
