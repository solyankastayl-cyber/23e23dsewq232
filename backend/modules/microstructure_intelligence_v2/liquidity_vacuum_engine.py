"""
Liquidity Vacuum Detector — Engine

PHASE 28.2 — Core logic for detecting liquidity vacuums.

Features:
- Orderbook gap detection
- Vacuum size calculation
- Vacuum direction determination
- Liquidity wall detection
- Vacuum probability calculation
"""

from typing import Optional, Dict, List, Tuple
from datetime import datetime
import random
import statistics

from .liquidity_vacuum_types import (
    LiquidityVacuumState,
    LiquidityVacuumSummary,
    OrderbookLevel,
    OrderbookLevels,
    OrderbookGap,
    MicrostructureContext,
    VacuumDirection,
    VacuumLiquidityState,
    GAP_ANOMALY_THRESHOLD,
    GAP_NORMAL_THRESHOLD,
    GAP_THIN_THRESHOLD,
    WALL_SIZE_MULTIPLIER,
    VACUUM_WEIGHT_GAP,
    VACUUM_WEIGHT_DEPTH,
    VACUUM_WEIGHT_IMBALANCE,
    CONF_WEIGHT_GAP,
    CONF_WEIGHT_SPREAD,
    CONF_WEIGHT_DEPTH,
)

from .microstructure_snapshot_engine import get_microstructure_snapshot_engine


class LiquidityVacuumEngine:
    """
    Liquidity Vacuum Detection Engine.
    
    Detects thin zones and gaps in orderbook where price can move quickly.
    """
    
    def __init__(self):
        self._current_states: Dict[str, LiquidityVacuumState] = {}
    
    # ═══════════════════════════════════════════════════════════
    # Gap Detection
    # ═══════════════════════════════════════════════════════════
    
    def detect_gaps(
        self,
        levels: List[OrderbookLevel],
        mid_price: float,
        side: str,
    ) -> List[OrderbookGap]:
        """
        Detect gaps between orderbook levels.
        
        Returns list of gaps with size > anomaly threshold.
        """
        if len(levels) < 2 or mid_price <= 0:
            return []
        
        gaps = []
        
        for i in range(len(levels) - 1):
            price_diff = abs(levels[i + 1].price - levels[i].price)
            gap_bps = (price_diff / mid_price) * 10000
            
            if gap_bps >= GAP_ANOMALY_THRESHOLD:
                gaps.append(OrderbookGap(
                    price_start=levels[i].price,
                    price_end=levels[i + 1].price,
                    gap_bps=round(gap_bps, 2),
                    side=side,
                    level_index=i,
                ))
        
        return gaps
    
    def calculate_all_gaps_bps(
        self,
        levels: List[OrderbookLevel],
        mid_price: float,
    ) -> List[float]:
        """Calculate gap in bps between each consecutive level."""
        if len(levels) < 2 or mid_price <= 0:
            return []
        
        gaps = []
        for i in range(len(levels) - 1):
            price_diff = abs(levels[i + 1].price - levels[i].price)
            gap_bps = (price_diff / mid_price) * 10000
            gaps.append(round(gap_bps, 4))
        
        return gaps
    
    def normalize_gap(
        self,
        gap_bps: float,
        max_expected_gap: float = 10.0,
    ) -> float:
        """
        Normalize gap to 0-1 range.
        
        max_expected_gap: maximum gap before capping at 1.0
        """
        if max_expected_gap <= 0:
            return 0.0
        return round(min(gap_bps / max_expected_gap, 1.0), 4)
    
    # ═══════════════════════════════════════════════════════════
    # Vacuum Metrics
    # ═══════════════════════════════════════════════════════════
    
    def calculate_vacuum_size(
        self,
        bid_gaps: List[OrderbookGap],
        ask_gaps: List[OrderbookGap],
    ) -> float:
        """
        Calculate vacuum size as largest gap in bps.
        """
        all_gaps = bid_gaps + ask_gaps
        if not all_gaps:
            return 0.0
        
        return max(g.gap_bps for g in all_gaps)
    
    def determine_vacuum_direction(
        self,
        bid_gaps: List[OrderbookGap],
        ask_gaps: List[OrderbookGap],
    ) -> VacuumDirection:
        """
        Determine vacuum direction based on where largest gap is.
        
        UP: gap above price (asks)
        DOWN: gap below price (bids)
        NONE: no significant gaps
        """
        if not bid_gaps and not ask_gaps:
            return "NONE"
        
        max_bid_gap = max((g.gap_bps for g in bid_gaps), default=0)
        max_ask_gap = max((g.gap_bps for g in ask_gaps), default=0)
        
        if max_ask_gap > max_bid_gap and max_ask_gap >= GAP_ANOMALY_THRESHOLD:
            return "UP"
        elif max_bid_gap > max_ask_gap and max_bid_gap >= GAP_ANOMALY_THRESHOLD:
            return "DOWN"
        elif max_ask_gap >= GAP_ANOMALY_THRESHOLD:
            return "UP"
        elif max_bid_gap >= GAP_ANOMALY_THRESHOLD:
            return "DOWN"
        else:
            return "NONE"
    
    def calculate_orderbook_gap_score(
        self,
        gaps_bps: List[float],
    ) -> float:
        """
        Calculate orderbook gap score.
        
        Formula: max_gap / median_gap (or expected_gap)
        """
        if not gaps_bps:
            return 0.0
        
        max_gap = max(gaps_bps)
        
        if len(gaps_bps) == 1:
            return round(max_gap / GAP_ANOMALY_THRESHOLD, 2)
        
        median_gap = statistics.median(gaps_bps)
        if median_gap <= 0:
            return round(max_gap / GAP_ANOMALY_THRESHOLD, 2)
        
        return round(max_gap / median_gap, 2)
    
    # ═══════════════════════════════════════════════════════════
    # Liquidity Wall Detection
    # ═══════════════════════════════════════════════════════════
    
    def find_liquidity_wall(
        self,
        levels: List[OrderbookLevel],
        mid_price: float,
    ) -> Tuple[Optional[float], float]:
        """
        Find nearest liquidity wall (large order).
        
        Returns: (wall_price, wall_distance_bps)
        """
        if not levels or mid_price <= 0:
            return None, 0.0
        
        sizes = [lv.size for lv in levels]
        if not sizes:
            return None, 0.0
        
        median_size = statistics.median(sizes) if len(sizes) > 1 else sizes[0]
        threshold = median_size * WALL_SIZE_MULTIPLIER
        
        for level in levels:
            if level.size >= threshold:
                distance_bps = abs(level.price - mid_price) / mid_price * 10000
                return level.price, round(distance_bps, 2)
        
        # No wall found - return distance to furthest level
        if levels:
            furthest = levels[-1]
            distance_bps = abs(furthest.price - mid_price) / mid_price * 10000
            return None, round(distance_bps, 2)
        
        return None, 0.0
    
    def calculate_nearest_wall_distance(
        self,
        orderbook: OrderbookLevels,
    ) -> float:
        """
        Find distance to nearest liquidity wall on either side.
        """
        _, bid_wall_dist = self.find_liquidity_wall(
            orderbook.bids, orderbook.mid_price
        )
        _, ask_wall_dist = self.find_liquidity_wall(
            orderbook.asks, orderbook.mid_price
        )
        
        if bid_wall_dist > 0 and ask_wall_dist > 0:
            return min(bid_wall_dist, ask_wall_dist)
        elif bid_wall_dist > 0:
            return bid_wall_dist
        elif ask_wall_dist > 0:
            return ask_wall_dist
        else:
            return 0.0
    
    # ═══════════════════════════════════════════════════════════
    # State Classification
    # ═══════════════════════════════════════════════════════════
    
    def classify_liquidity_state(
        self,
        max_gap_bps: float,
    ) -> VacuumLiquidityState:
        """
        Classify liquidity state based on max gap.
        
        NORMAL: gap < 2 bps
        THIN_ZONE: 2 <= gap < 5 bps
        VACUUM: gap >= 5 bps
        """
        if max_gap_bps >= GAP_THIN_THRESHOLD:
            return "VACUUM"
        elif max_gap_bps >= GAP_NORMAL_THRESHOLD:
            return "THIN_ZONE"
        else:
            return "NORMAL"
    
    # ═══════════════════════════════════════════════════════════
    # Probability & Confidence
    # ═══════════════════════════════════════════════════════════
    
    def calculate_vacuum_probability(
        self,
        normalized_gap: float,
        depth_score: float,
        imbalance_score: float,
    ) -> float:
        """
        Calculate vacuum probability.
        
        Formula:
        0.45 * normalized_gap +
        0.35 * (1 - depth_score) +
        0.20 * abs(imbalance_score)
        """
        prob = (
            VACUUM_WEIGHT_GAP * normalized_gap +
            VACUUM_WEIGHT_DEPTH * (1 - depth_score) +
            VACUUM_WEIGHT_IMBALANCE * abs(imbalance_score)
        )
        return round(min(max(prob, 0.0), 1.0), 4)
    
    def calculate_confidence(
        self,
        normalized_gap: float,
        spread_bps: float,
        depth_score: float,
    ) -> float:
        """
        Calculate confidence in vacuum detection.
        
        Formula:
        0.4 * normalized_gap +
        0.3 * (1 - spread_normalized) +
        0.3 * depth_score
        """
        spread_normalized = min(spread_bps / 20.0, 1.0)
        
        conf = (
            CONF_WEIGHT_GAP * normalized_gap +
            CONF_WEIGHT_SPREAD * (1 - spread_normalized) +
            CONF_WEIGHT_DEPTH * depth_score
        )
        return round(min(max(conf, 0.0), 1.0), 4)
    
    # ═══════════════════════════════════════════════════════════
    # Reason Generation
    # ═══════════════════════════════════════════════════════════
    
    def generate_reason(
        self,
        vacuum_direction: VacuumDirection,
        liquidity_state: VacuumLiquidityState,
        depth_score: float,
        imbalance_score: float,
    ) -> str:
        """Generate human-readable reason for vacuum state."""
        
        direction_desc = {
            "UP": "above price",
            "DOWN": "below price",
            "NONE": "",
        }[vacuum_direction]
        
        state_desc = {
            "NORMAL": "normal liquidity distribution",
            "THIN_ZONE": "thin liquidity zone detected",
            "VACUUM": "large orderbook gap",
        }[liquidity_state]
        
        depth_desc = "weak depth" if depth_score < 0.5 else "adequate depth"
        
        imbalance_desc = ""
        if imbalance_score > 0.15:
            imbalance_desc = "positive imbalance"
        elif imbalance_score < -0.15:
            imbalance_desc = "negative imbalance"
        else:
            imbalance_desc = "balanced flow"
        
        if vacuum_direction == "NONE":
            return f"{state_desc} with {depth_desc} and {imbalance_desc}"
        else:
            return f"{state_desc} {direction_desc} with {depth_desc} and {imbalance_desc}"
    
    # ═══════════════════════════════════════════════════════════
    # Main Build
    # ═══════════════════════════════════════════════════════════
    
    def build_vacuum_state(
        self,
        symbol: str,
        orderbook: OrderbookLevels,
        context: MicrostructureContext,
    ) -> LiquidityVacuumState:
        """
        Build liquidity vacuum state from orderbook and context.
        """
        # Detect gaps on both sides
        bid_gaps = self.detect_gaps(orderbook.bids, orderbook.mid_price, "BID")
        ask_gaps = self.detect_gaps(orderbook.asks, orderbook.mid_price, "ASK")
        
        # Calculate all gaps for scoring
        bid_gaps_bps = self.calculate_all_gaps_bps(orderbook.bids, orderbook.mid_price)
        ask_gaps_bps = self.calculate_all_gaps_bps(orderbook.asks, orderbook.mid_price)
        all_gaps_bps = bid_gaps_bps + ask_gaps_bps
        
        # Vacuum metrics
        vacuum_size = self.calculate_vacuum_size(bid_gaps, ask_gaps)
        vacuum_direction = self.determine_vacuum_direction(bid_gaps, ask_gaps)
        gap_score = self.calculate_orderbook_gap_score(all_gaps_bps)
        
        # Liquidity wall
        wall_distance = self.calculate_nearest_wall_distance(orderbook)
        
        # State classification
        liquidity_state = self.classify_liquidity_state(vacuum_size)
        
        # Probability & Confidence
        normalized_gap = self.normalize_gap(vacuum_size)
        vacuum_probability = self.calculate_vacuum_probability(
            normalized_gap,
            context.depth_score,
            context.imbalance_score,
        )
        confidence = self.calculate_confidence(
            normalized_gap,
            context.spread_bps,
            context.depth_score,
        )
        
        # Reason
        reason = self.generate_reason(
            vacuum_direction,
            liquidity_state,
            context.depth_score,
            context.imbalance_score,
        )
        
        state = LiquidityVacuumState(
            symbol=symbol,
            vacuum_direction=vacuum_direction,
            vacuum_probability=vacuum_probability,
            vacuum_size_bps=vacuum_size,
            nearest_liquidity_wall_distance=wall_distance,
            orderbook_gap_score=gap_score,
            liquidity_state=liquidity_state,
            confidence=confidence,
            reason=reason,
        )
        
        self._current_states[symbol] = state
        return state
    
    # ═══════════════════════════════════════════════════════════
    # Simulated Build (for testing)
    # ═══════════════════════════════════════════════════════════
    
    def build_vacuum_state_simulated(
        self,
        symbol: str = "BTC",
    ) -> LiquidityVacuumState:
        """
        Build vacuum state using simulated data.
        
        For testing when real orderbook data is not available.
        """
        # Base price
        base_price = {"BTC": 42000.0, "ETH": 2200.0, "SOL": 120.0}.get(symbol, 1000.0)
        mid_price = base_price + random.uniform(-500, 500)
        
        # Generate realistic orderbook levels
        bids = []
        asks = []
        
        # Generate bids (descending from mid)
        price = mid_price
        for i in range(20):
            # Random gap with occasional large gaps
            if random.random() < 0.15:
                gap_pct = random.uniform(0.0003, 0.0008)  # Large gap
            else:
                gap_pct = random.uniform(0.00005, 0.0002)  # Normal gap
            
            price = price * (1 - gap_pct)
            size = random.uniform(10000, 200000)
            
            # Occasional large orders (walls)
            if random.random() < 0.1:
                size *= random.uniform(3, 6)
            
            bids.append(OrderbookLevel(price=price, size=size))
        
        # Generate asks (ascending from mid)
        price = mid_price
        for i in range(20):
            if random.random() < 0.15:
                gap_pct = random.uniform(0.0003, 0.0008)
            else:
                gap_pct = random.uniform(0.00005, 0.0002)
            
            price = price * (1 + gap_pct)
            size = random.uniform(10000, 200000)
            
            if random.random() < 0.1:
                size *= random.uniform(3, 6)
            
            asks.append(OrderbookLevel(price=price, size=size))
        
        orderbook = OrderbookLevels(
            bids=bids,
            asks=asks,
            mid_price=mid_price,
        )
        
        # Get context from MicrostructureSnapshot
        ms_engine = get_microstructure_snapshot_engine()
        ms_snapshot = ms_engine.get_snapshot(symbol)
        
        if ms_snapshot:
            context = MicrostructureContext(
                depth_score=ms_snapshot.depth_score,
                imbalance_score=ms_snapshot.imbalance_score,
                spread_bps=ms_snapshot.spread_bps,
            )
        else:
            context = MicrostructureContext(
                depth_score=random.uniform(0.3, 0.9),
                imbalance_score=random.uniform(-0.3, 0.3),
                spread_bps=random.uniform(1.0, 10.0),
            )
        
        return self.build_vacuum_state(symbol, orderbook, context)
    
    # ═══════════════════════════════════════════════════════════
    # Accessors
    # ═══════════════════════════════════════════════════════════
    
    def get_vacuum_state(
        self,
        symbol: str,
    ) -> Optional[LiquidityVacuumState]:
        """Get cached vacuum state for symbol."""
        return self._current_states.get(symbol)
    
    def get_all_vacuum_states(self) -> Dict[str, LiquidityVacuumState]:
        """Get all cached vacuum states."""
        return self._current_states.copy()


# Singleton
_engine: Optional[LiquidityVacuumEngine] = None


def get_liquidity_vacuum_engine() -> LiquidityVacuumEngine:
    """Get singleton instance of LiquidityVacuumEngine."""
    global _engine
    if _engine is None:
        _engine = LiquidityVacuumEngine()
    return _engine
