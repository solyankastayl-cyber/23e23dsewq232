"""
Venue Selector - PHASE 5.3
==========================

Selects the best venue for order execution based on multiple criteria.
"""

from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import statistics

from .routing_types import (
    RoutingRequest,
    VenueScore,
    VenueAnalysis,
    VenueStatus,
    RoutingPolicy
)

# Import dependencies from other modules
import sys
sys.path.append('/app/backend')

from modules.market_data.market_data_engine import get_market_data_engine
from modules.execution.failover.failover_engine import get_failover_engine
from modules.execution.slippage.slippage_engine import get_slippage_engine


class VenueSelector:
    """
    Selects optimal venue for order execution.
    
    Criteria:
    - Best price (bid for sell, ask for buy)
    - Spread
    - Available liquidity
    - Expected slippage
    - Exchange health/failover status
    - Historical execution quality
    """
    
    # Supported exchanges
    SUPPORTED_EXCHANGES = ["BINANCE", "BYBIT", "OKX"]
    
    # Default fee rates (can be overridden)
    DEFAULT_FEES = {
        "BINANCE": 0.0004,  # 0.04%
        "BYBIT": 0.0006,    # 0.06%
        "OKX": 0.0005       # 0.05%
    }
    
    # Weight factors for scoring
    SCORE_WEIGHTS = {
        "price": 0.30,
        "spread": 0.10,
        "liquidity": 0.20,
        "slippage": 0.20,
        "health": 0.15,
        "fee": 0.05
    }
    
    def __init__(self):
        self._market_engine = get_market_data_engine()
        self._failover_engine = get_failover_engine()
        self._slippage_engine = get_slippage_engine()
        
        # Cache for venue scores
        self._score_cache: Dict[str, Dict[str, VenueScore]] = {}
        self._cache_ttl = timedelta(seconds=5)
        self._cache_time: Dict[str, datetime] = {}
    
    def select_venue(
        self,
        request: RoutingRequest,
        policy: RoutingPolicy = RoutingPolicy.BEST_EXECUTION
    ) -> Tuple[VenueScore, List[VenueScore]]:
        """
        Select best venue for the order.
        
        Args:
            request: Routing request
            policy: Routing policy to apply
            
        Returns:
            Tuple of (selected venue score, all venue scores)
        """
        # Get scores for all venues
        all_scores = self._score_all_venues(request)
        
        if not all_scores:
            raise ValueError(f"No available venues for {request.symbol}")
        
        # Filter by health status
        available_scores = [
            s for s in all_scores
            if s.health_status in [VenueStatus.OPTIMAL, VenueStatus.AVAILABLE]
        ]
        
        # If no healthy venues, use degraded with warning
        if not available_scores:
            available_scores = [
                s for s in all_scores
                if s.health_status == VenueStatus.DEGRADED
            ]
        
        if not available_scores:
            raise ValueError(f"No healthy venues for {request.symbol}")
        
        # Apply policy-specific selection
        selected = self._apply_policy(available_scores, policy)
        
        return selected, all_scores
    
    def analyze_venue(
        self,
        exchange: str,
        symbol: str,
        size: float,
        side: str
    ) -> VenueAnalysis:
        """
        Analyze a specific venue for order.
        
        Args:
            exchange: Exchange name
            symbol: Trading symbol
            size: Order size
            side: BUY/SELL
            
        Returns:
            Detailed venue analysis
        """
        # Get market data
        orderbook = self._market_engine.get_live_orderbook(exchange, symbol)
        ticker = self._market_engine.get_live_ticker(exchange, symbol)
        
        # Get failover status
        failover_status = self._failover_engine.get_exchange_status(exchange)
        health_score = failover_status.get("health_score", 1.0)
        system_status = failover_status.get("status", "NORMAL")
        
        # Get slippage estimate
        slippage_estimate = self._slippage_engine.estimate_slippage(
            exchange, symbol, side, size
        )
        
        # Build analysis
        analysis = VenueAnalysis(
            exchange=exchange,
            symbol=symbol,
            venue_status=self._map_health_to_status(health_score),
            health_score=health_score,
            failover_status=system_status
        )
        
        if orderbook:
            analysis.best_bid = orderbook.best_bid
            analysis.best_ask = orderbook.best_ask
            analysis.mid_price = orderbook.mid_price
            analysis.spread_bps = orderbook.spread_bps
            analysis.bid_depth_usd = orderbook.bid_depth * orderbook.mid_price
            analysis.ask_depth_usd = orderbook.ask_depth * orderbook.mid_price
            analysis.depth_imbalance = orderbook.imbalance
            
            # Calculate slippage for order size
            analysis.slippage_for_size_bps = self._estimate_depth_slippage(
                orderbook, size, side
            )
            
            # Check if can fill
            available = orderbook.ask_depth if side == "BUY" else orderbook.bid_depth
            analysis.can_fill_size = min(size, available)
        
        if slippage_estimate:
            analysis.avg_slippage_bps = slippage_estimate.get("avg_slippage_bps", 0)
        
        # Determine recommendation
        if analysis.health_score < 0.5:
            analysis.recommended = False
            analysis.rejection_reason = "Exchange health too low"
        elif analysis.can_fill_size < size * 0.5:
            analysis.recommended = False
            analysis.rejection_reason = "Insufficient liquidity"
        elif analysis.slippage_for_size_bps > 100:
            analysis.recommended = False
            analysis.rejection_reason = "Expected slippage too high"
        
        return analysis
    
    def get_all_venue_analyses(
        self,
        symbol: str,
        size: float,
        side: str
    ) -> Dict[str, VenueAnalysis]:
        """Get analyses for all supported venues"""
        analyses = {}
        for exchange in self.SUPPORTED_EXCHANGES:
            try:
                analyses[exchange] = self.analyze_venue(exchange, symbol, size, side)
            except Exception as e:
                print(f"Error analyzing {exchange}: {e}")
        return analyses
    
    # ============================================
    # Private Methods
    # ============================================
    
    def _score_all_venues(self, request: RoutingRequest) -> List[VenueScore]:
        """Score all venues for the request"""
        symbol = request.symbol
        side = request.side
        size = request.size
        
        scores = []
        
        for exchange in self.SUPPORTED_EXCHANGES:
            # Check if excluded
            if exchange in request.excluded_exchanges:
                continue
            if request.allowed_exchanges and exchange not in request.allowed_exchanges:
                continue
            
            try:
                score = self._score_venue(exchange, symbol, side, size)
                scores.append(score)
            except Exception as e:
                print(f"Error scoring {exchange}: {e}")
        
        return scores
    
    def _score_venue(
        self,
        exchange: str,
        symbol: str,
        side: str,
        size: float
    ) -> VenueScore:
        """Calculate score for a single venue"""
        # Check cache
        cache_key = f"{exchange}:{symbol}:{side}"
        if cache_key in self._cache_time:
            if datetime.utcnow() - self._cache_time[cache_key] < self._cache_ttl:
                cached = self._score_cache.get(exchange, {}).get(cache_key)
                if cached:
                    return cached
        
        score = VenueScore(
            exchange=exchange,
            symbol=symbol
        )
        
        # Get market data
        ticker = self._market_engine.get_live_ticker(exchange, symbol)
        orderbook = self._market_engine.get_live_orderbook(exchange, symbol)
        
        if ticker:
            score.price = ticker.ask if side == "BUY" else ticker.bid
            if ticker.bid > 0 and ticker.ask > 0:
                score.spread_bps = ((ticker.ask - ticker.bid) / ticker.bid) * 10000
        
        if orderbook:
            score.available_liquidity = orderbook.ask_depth if side == "BUY" else orderbook.bid_depth
            score.liquidity_score = min(1.0, score.available_liquidity / max(size, 0.1))
            score.expected_slippage_bps = self._estimate_depth_slippage(orderbook, size, side)
        
        # Get failover status
        failover_status = self._failover_engine.get_exchange_status(exchange)
        score.health_score = failover_status.get("health_score", 1.0)
        score.health_status = self._map_health_to_status(score.health_score)
        score.latency_ms = failover_status.get("latency_ms", 0)
        
        # Get historical slippage
        slippage_data = self._slippage_engine.get_slippage_stats(exchange, symbol)
        score.historical_slippage_bps = slippage_data.get("avg_slippage_bps", 0) if slippage_data else 0
        score.fill_rate = slippage_data.get("fill_rate", 1.0) if slippage_data else 1.0
        
        # Fees
        score.fee_rate = self.DEFAULT_FEES.get(exchange, 0.0005)
        score.estimated_fee = size * score.price * score.fee_rate if score.price else 0
        
        # Calculate total score
        score.total_score = self._calculate_total_score(score, side)
        
        # Cache
        if exchange not in self._score_cache:
            self._score_cache[exchange] = {}
        self._score_cache[exchange][cache_key] = score
        self._cache_time[cache_key] = datetime.utcnow()
        
        return score
    
    def _calculate_total_score(self, score: VenueScore, side: str) -> float:
        """Calculate weighted total score"""
        weights = self.SCORE_WEIGHTS
        
        # Price score (lower is better for buy, higher for sell)
        # Normalize to 0-1 range
        price_score = 0.5  # Default neutral
        if score.price > 0:
            # Will be compared relatively
            price_score = 0.8 if score.spread_bps < 5 else 0.5
        
        # Spread score (lower is better)
        spread_score = max(0, 1 - score.spread_bps / 20)
        
        # Liquidity score (already 0-1)
        liquidity_score = score.liquidity_score
        
        # Slippage score (lower is better)
        expected_slip = score.expected_slippage_bps + score.historical_slippage_bps
        slippage_score = max(0, 1 - expected_slip / 50)
        
        # Health score (already 0-1)
        health_score = score.health_score
        
        # Fee score (lower is better)
        fee_score = max(0, 1 - score.fee_rate * 1000)
        
        total = (
            weights["price"] * price_score +
            weights["spread"] * spread_score +
            weights["liquidity"] * liquidity_score +
            weights["slippage"] * slippage_score +
            weights["health"] * health_score +
            weights["fee"] * fee_score
        )
        
        return round(total, 4)
    
    def _apply_policy(
        self,
        scores: List[VenueScore],
        policy: RoutingPolicy
    ) -> VenueScore:
        """Apply routing policy to select venue"""
        if not scores:
            raise ValueError("No scores to select from")
        
        if policy == RoutingPolicy.BEST_PRICE:
            # Select by best price (lowest for buy)
            return min(scores, key=lambda s: s.price if s.price > 0 else float('inf'))
        
        elif policy == RoutingPolicy.SAFEST_VENUE:
            # Select by highest health score
            return max(scores, key=lambda s: s.health_score)
        
        elif policy == RoutingPolicy.LOW_SLIPPAGE:
            # Select by lowest expected slippage
            return min(scores, key=lambda s: s.expected_slippage_bps + s.historical_slippage_bps)
        
        elif policy == RoutingPolicy.LOWEST_FEE:
            # Select by lowest fee
            return min(scores, key=lambda s: s.fee_rate)
        
        else:  # BEST_EXECUTION (default)
            # Select by highest total score
            return max(scores, key=lambda s: s.total_score)
    
    def _estimate_depth_slippage(
        self,
        orderbook,
        size: float,
        side: str
    ) -> float:
        """Estimate slippage based on orderbook depth"""
        if not orderbook:
            return 0.0
        
        levels = orderbook.asks if side == "BUY" else orderbook.bids
        if not levels:
            return 0.0
        
        remaining = size
        weighted_price = 0.0
        total_filled = 0.0
        
        for level in levels:
            fill = min(remaining, level.size)
            weighted_price += level.price * fill
            total_filled += fill
            remaining -= fill
            if remaining <= 0:
                break
        
        if total_filled == 0:
            return 100.0  # High slippage if can't fill
        
        avg_price = weighted_price / total_filled
        reference_price = levels[0].price
        
        slippage_pct = abs(avg_price - reference_price) / reference_price * 10000
        return round(slippage_pct, 2)
    
    def _map_health_to_status(self, health_score: float) -> VenueStatus:
        """Map health score to venue status"""
        if health_score >= 0.9:
            return VenueStatus.OPTIMAL
        elif health_score >= 0.7:
            return VenueStatus.AVAILABLE
        elif health_score >= 0.5:
            return VenueStatus.DEGRADED
        else:
            return VenueStatus.UNAVAILABLE


# Global instance
_venue_selector: Optional[VenueSelector] = None


def get_venue_selector() -> VenueSelector:
    """Get or create global venue selector"""
    global _venue_selector
    if _venue_selector is None:
        _venue_selector = VenueSelector()
    return _venue_selector
