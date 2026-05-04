"""
Orderbook Pressure Map — Engine

PHASE 28.3 — Core logic for orderbook pressure detection.

Features:
- Bid/ask pressure calculation (weighted by distance)
- Net pressure and pressure bias
- Absorption zone detection
- Sweep risk assessment
- Integration with MicrostructureSnapshot and LiquidityVacuumState
"""

from typing import Optional, Dict, List, Tuple
from datetime import datetime
import random
import statistics

from .orderbook_pressure_types import (
    OrderbookPressureMap,
    OrderbookPressureLevel,
    OrderbookPressureInput,
    MicrostructurePressureContext,
    PressureBias,
    AbsorptionZone,
    SweepRisk,
    PressureState,
    BIAS_THRESHOLD,
    WALL_SIZE_MULTIPLIER,
    ABSORPTION_DISTANCE_THRESHOLD_BPS,
    SWEEP_WEIGHT_NET_PRESSURE,
    SWEEP_WEIGHT_VACUUM,
    SWEEP_WEIGHT_DEPTH,
    CONF_WEIGHT_NET_PRESSURE,
    CONF_WEIGHT_DEPTH,
    CONF_WEIGHT_SWEEP,
    CONF_WEIGHT_ABSORPTION,
    SWEEP_PROB_HIGH,
    SWEEP_PROB_MODERATE,
)

from .microstructure_snapshot_engine import get_microstructure_snapshot_engine
from .liquidity_vacuum_engine import get_liquidity_vacuum_engine


class OrderbookPressureEngine:
    """
    Orderbook Pressure Map Engine.
    
    Builds pressure map from orderbook levels and context.
    """
    
    def __init__(self):
        self._current_maps: Dict[str, OrderbookPressureMap] = {}
    
    # ═══════════════════════════════════════════════════════════
    # Pressure Calculations
    # ═══════════════════════════════════════════════════════════
    
    def calculate_bid_pressure(
        self,
        levels: List[OrderbookPressureLevel],
    ) -> float:
        """
        Calculate weighted bid pressure.
        
        Formula: sum(size_i / (1 + distance_bps_i))
        Closer levels have more weight.
        """
        if not levels:
            return 0.0
        
        total_pressure = 0.0
        for level in levels:
            weight = 1.0 / (1.0 + level.distance_bps)
            total_pressure += level.size * weight
        
        # Normalize to 0-1 range
        max_possible = sum(lv.size for lv in levels)
        if max_possible <= 0:
            return 0.0
        
        return round(min(total_pressure / max_possible, 1.0), 4)
    
    def calculate_ask_pressure(
        self,
        levels: List[OrderbookPressureLevel],
    ) -> float:
        """
        Calculate weighted ask pressure.
        
        Same formula as bid pressure.
        """
        return self.calculate_bid_pressure(levels)
    
    def calculate_net_pressure(
        self,
        bid_pressure: float,
        ask_pressure: float,
    ) -> float:
        """
        Calculate net pressure.
        
        Formula: (bid - ask) / (bid + ask)
        Range: -1 to +1
        """
        total = bid_pressure + ask_pressure
        if total <= 0:
            return 0.0
        
        net = (bid_pressure - ask_pressure) / total
        return round(min(max(net, -1.0), 1.0), 4)
    
    # ═══════════════════════════════════════════════════════════
    # Classifications
    # ═══════════════════════════════════════════════════════════
    
    def classify_pressure_bias(
        self,
        net_pressure: float,
    ) -> PressureBias:
        """
        Classify pressure bias.
        
        BID_DOMINANT: net > 0.15
        ASK_DOMINANT: net < -0.15
        BALANCED: otherwise
        """
        if net_pressure > BIAS_THRESHOLD:
            return "BID_DOMINANT"
        elif net_pressure < -BIAS_THRESHOLD:
            return "ASK_DOMINANT"
        else:
            return "BALANCED"
    
    def detect_absorption_zone(
        self,
        bid_levels: List[OrderbookPressureLevel],
        ask_levels: List[OrderbookPressureLevel],
        pressure_bias: PressureBias,
    ) -> AbsorptionZone:
        """
        Detect absorption zones.
        
        BID_ABSORPTION: large bid wall near mid, absorbing sell pressure
        ASK_ABSORPTION: large ask wall near mid, absorbing buy pressure
        NONE: no clear absorption
        """
        bid_wall = self._find_wall(bid_levels)
        ask_wall = self._find_wall(ask_levels)
        
        bid_wall_near = bid_wall is not None and bid_wall.distance_bps <= ABSORPTION_DISTANCE_THRESHOLD_BPS
        ask_wall_near = ask_wall is not None and ask_wall.distance_bps <= ABSORPTION_DISTANCE_THRESHOLD_BPS
        
        # If both walls exist, pick the stronger one based on size
        if bid_wall_near and ask_wall_near:
            if bid_wall.size > ask_wall.size:
                return "BID_ABSORPTION"
            else:
                return "ASK_ABSORPTION"
        
        # BID_ABSORPTION: bid wall absorbing, ask not dominant
        if bid_wall_near and pressure_bias != "ASK_DOMINANT":
            return "BID_ABSORPTION"
        
        # ASK_ABSORPTION: ask wall absorbing, bid not dominant
        if ask_wall_near and pressure_bias != "BID_DOMINANT":
            return "ASK_ABSORPTION"
        
        return "NONE"
    
    def _find_wall(
        self,
        levels: List[OrderbookPressureLevel],
    ) -> Optional[OrderbookPressureLevel]:
        """Find wall (large order) in levels."""
        if not levels:
            return None
        
        sizes = [lv.size for lv in levels]
        if len(sizes) < 2:
            return levels[0] if levels else None
        
        median_size = statistics.median(sizes)
        threshold = median_size * WALL_SIZE_MULTIPLIER
        
        for level in levels:
            if level.size >= threshold:
                return level
        
        return None
    
    def assess_sweep_risk(
        self,
        pressure_bias: PressureBias,
        bid_levels: List[OrderbookPressureLevel],
        ask_levels: List[OrderbookPressureLevel],
        vacuum_direction: str,
    ) -> SweepRisk:
        """
        Assess sweep risk.
        
        UP: bid dominant + thin asks + possible vacuum above
        DOWN: ask dominant + thin bids + possible vacuum below
        NONE: otherwise
        """
        bid_depth = sum(lv.size for lv in bid_levels) if bid_levels else 0
        ask_depth = sum(lv.size for lv in ask_levels) if ask_levels else 0
        
        # Thin threshold (relative)
        total_depth = bid_depth + ask_depth
        if total_depth <= 0:
            return "NONE"
        
        bid_ratio = bid_depth / total_depth
        ask_ratio = ask_depth / total_depth
        
        # UP: bid dominant, asks thin, vacuum UP possible
        if pressure_bias == "BID_DOMINANT":
            if ask_ratio < 0.4 or vacuum_direction == "UP":
                return "UP"
        
        # DOWN: ask dominant, bids thin, vacuum DOWN possible
        if pressure_bias == "ASK_DOMINANT":
            if bid_ratio < 0.4 or vacuum_direction == "DOWN":
                return "DOWN"
        
        return "NONE"
    
    # ═══════════════════════════════════════════════════════════
    # Probability & State
    # ═══════════════════════════════════════════════════════════
    
    def calculate_sweep_probability(
        self,
        net_pressure: float,
        vacuum_probability: float,
        depth_score: float,
    ) -> float:
        """
        Calculate sweep probability.
        
        Formula:
        0.40 * abs(net_pressure) +
        0.30 * vacuum_probability +
        0.30 * (1 - depth_score)
        """
        prob = (
            SWEEP_WEIGHT_NET_PRESSURE * abs(net_pressure) +
            SWEEP_WEIGHT_VACUUM * vacuum_probability +
            SWEEP_WEIGHT_DEPTH * (1 - depth_score)
        )
        return round(min(max(prob, 0.0), 1.0), 4)
    
    def classify_pressure_state(
        self,
        pressure_bias: PressureBias,
        absorption_zone: AbsorptionZone,
        sweep_risk: SweepRisk,
        sweep_probability: float,
        depth_score: float,
    ) -> PressureState:
        """
        Classify overall pressure state.
        
        SUPPORTIVE: directional bias + absorption + aligned sweep
        NEUTRAL: balanced + no absorption + low sweep
        FRAGILE: pressure exists but thin liquidity
        STRESSED: strong imbalance + thin liquidity + high sweep
        """
        # STRESSED: high sweep probability + thin liquidity
        if sweep_probability >= SWEEP_PROB_HIGH and depth_score < 0.5:
            return "STRESSED"
        
        # FRAGILE: moderate sweep + thin liquidity
        if sweep_probability >= SWEEP_PROB_MODERATE and depth_score < 0.5:
            return "FRAGILE"
        
        # SUPPORTIVE: directional + absorption present + aligned
        if pressure_bias != "BALANCED" and absorption_zone != "NONE":
            # Check if absorption aligns with bias
            if (pressure_bias == "BID_DOMINANT" and absorption_zone == "BID_ABSORPTION") or \
               (pressure_bias == "ASK_DOMINANT" and absorption_zone == "ASK_ABSORPTION"):
                return "SUPPORTIVE"
        
        # SUPPORTIVE: directional with low sweep
        if pressure_bias != "BALANCED" and sweep_probability < SWEEP_PROB_MODERATE:
            return "SUPPORTIVE"
        
        # NEUTRAL: balanced with no major risks
        if pressure_bias == "BALANCED" and absorption_zone == "NONE" and sweep_probability < SWEEP_PROB_MODERATE:
            return "NEUTRAL"
        
        # Default to NEUTRAL
        return "NEUTRAL"
    
    # ═══════════════════════════════════════════════════════════
    # Confidence
    # ═══════════════════════════════════════════════════════════
    
    def calculate_confidence(
        self,
        net_pressure: float,
        depth_score: float,
        sweep_probability: float,
        absorption_zone: AbsorptionZone,
    ) -> float:
        """
        Calculate confidence in pressure map.
        
        Formula:
        0.35 * abs(net_pressure) +
        0.25 * depth_score +
        0.20 * sweep_probability +
        0.20 * absorption_strength
        """
        absorption_strength = 1.0 if absorption_zone != "NONE" else 0.0
        
        conf = (
            CONF_WEIGHT_NET_PRESSURE * abs(net_pressure) +
            CONF_WEIGHT_DEPTH * depth_score +
            CONF_WEIGHT_SWEEP * sweep_probability +
            CONF_WEIGHT_ABSORPTION * absorption_strength
        )
        return round(min(max(conf, 0.0), 1.0), 4)
    
    # ═══════════════════════════════════════════════════════════
    # Reason Generation
    # ═══════════════════════════════════════════════════════════
    
    def generate_reason(
        self,
        pressure_bias: PressureBias,
        absorption_zone: AbsorptionZone,
        sweep_risk: SweepRisk,
        pressure_state: PressureState,
    ) -> str:
        """Generate human-readable reason for pressure state."""
        
        bias_desc = {
            "BID_DOMINANT": "bid side dominates near mid",
            "ASK_DOMINANT": "ask side dominates near mid",
            "BALANCED": "balanced pressure on both sides",
        }[pressure_bias]
        
        absorption_desc = {
            "BID_ABSORPTION": "with visible bid absorption",
            "ASK_ABSORPTION": "with visible ask absorption",
            "NONE": "without clear absorption",
        }[absorption_zone]
        
        sweep_desc = {
            "UP": "and elevated upside sweep setup",
            "DOWN": "and elevated downside sweep setup",
            "NONE": "and low sweep risk",
        }[sweep_risk]
        
        return f"{bias_desc} {absorption_desc} {sweep_desc}"
    
    # ═══════════════════════════════════════════════════════════
    # Main Build
    # ═══════════════════════════════════════════════════════════
    
    def build_pressure_map(
        self,
        symbol: str,
        orderbook: OrderbookPressureInput,
        context: MicrostructurePressureContext,
    ) -> OrderbookPressureMap:
        """
        Build orderbook pressure map from orderbook and context.
        """
        # Calculate pressures
        bid_pressure = self.calculate_bid_pressure(orderbook.bids)
        ask_pressure = self.calculate_ask_pressure(orderbook.asks)
        net_pressure = self.calculate_net_pressure(bid_pressure, ask_pressure)
        
        # Classifications
        pressure_bias = self.classify_pressure_bias(net_pressure)
        absorption_zone = self.detect_absorption_zone(
            orderbook.bids, orderbook.asks, pressure_bias
        )
        sweep_risk = self.assess_sweep_risk(
            pressure_bias,
            orderbook.bids,
            orderbook.asks,
            context.vacuum_direction,
        )
        
        # Probabilities
        sweep_probability = self.calculate_sweep_probability(
            net_pressure,
            context.vacuum_probability,
            context.depth_score,
        )
        
        # State
        pressure_state = self.classify_pressure_state(
            pressure_bias,
            absorption_zone,
            sweep_risk,
            sweep_probability,
            context.depth_score,
        )
        
        # Confidence
        confidence = self.calculate_confidence(
            net_pressure,
            context.depth_score,
            sweep_probability,
            absorption_zone,
        )
        
        # Reason
        reason = self.generate_reason(
            pressure_bias,
            absorption_zone,
            sweep_risk,
            pressure_state,
        )
        
        pressure_map = OrderbookPressureMap(
            symbol=symbol,
            bid_pressure=bid_pressure,
            ask_pressure=ask_pressure,
            net_pressure=net_pressure,
            pressure_bias=pressure_bias,
            absorption_zone=absorption_zone,
            sweep_risk=sweep_risk,
            sweep_probability=sweep_probability,
            pressure_state=pressure_state,
            confidence=confidence,
            reason=reason,
        )
        
        self._current_maps[symbol] = pressure_map
        return pressure_map
    
    # ═══════════════════════════════════════════════════════════
    # Simulated Build
    # ═══════════════════════════════════════════════════════════
    
    def build_pressure_map_simulated(
        self,
        symbol: str = "BTC",
    ) -> OrderbookPressureMap:
        """
        Build pressure map using simulated data.
        """
        base_price = {"BTC": 42000.0, "ETH": 2200.0, "SOL": 120.0}.get(symbol, 1000.0)
        mid_price = base_price + random.uniform(-500, 500)
        
        # Generate bid levels
        bids = []
        price = mid_price
        for i in range(20):
            gap_pct = random.uniform(0.0001, 0.0005)
            price = price * (1 - gap_pct)
            distance_bps = (mid_price - price) / mid_price * 10000
            size = random.uniform(50000, 300000)
            
            # Occasional large orders (walls)
            if random.random() < 0.12:
                size *= random.uniform(3, 5)
            
            bids.append(OrderbookPressureLevel(
                price=price,
                size=size,
                distance_bps=distance_bps,
            ))
        
        # Generate ask levels
        asks = []
        price = mid_price
        for i in range(20):
            gap_pct = random.uniform(0.0001, 0.0005)
            price = price * (1 + gap_pct)
            distance_bps = (price - mid_price) / mid_price * 10000
            size = random.uniform(50000, 300000)
            
            if random.random() < 0.12:
                size *= random.uniform(3, 5)
            
            asks.append(OrderbookPressureLevel(
                price=price,
                size=size,
                distance_bps=distance_bps,
            ))
        
        orderbook = OrderbookPressureInput(
            bids=bids,
            asks=asks,
            mid_price=mid_price,
        )
        
        # Get context from existing engines
        ms_engine = get_microstructure_snapshot_engine()
        vacuum_engine = get_liquidity_vacuum_engine()
        
        ms_snapshot = ms_engine.get_snapshot(symbol)
        vacuum_state = vacuum_engine.get_vacuum_state(symbol)
        
        if ms_snapshot and vacuum_state:
            context = MicrostructurePressureContext(
                depth_score=ms_snapshot.depth_score,
                imbalance_score=ms_snapshot.imbalance_score,
                spread_bps=ms_snapshot.spread_bps,
                vacuum_probability=vacuum_state.vacuum_probability,
                vacuum_direction=vacuum_state.vacuum_direction,
                liquidity_state=vacuum_state.liquidity_state,
            )
        else:
            context = MicrostructurePressureContext(
                depth_score=random.uniform(0.3, 0.9),
                imbalance_score=random.uniform(-0.3, 0.3),
                spread_bps=random.uniform(1.0, 10.0),
                vacuum_probability=random.uniform(0.2, 0.7),
                vacuum_direction=random.choice(["UP", "DOWN", "NONE"]),
                liquidity_state=random.choice(["NORMAL", "THIN_ZONE", "VACUUM"]),
            )
        
        return self.build_pressure_map(symbol, orderbook, context)
    
    # ═══════════════════════════════════════════════════════════
    # Accessors
    # ═══════════════════════════════════════════════════════════
    
    def get_pressure_map(
        self,
        symbol: str,
    ) -> Optional[OrderbookPressureMap]:
        """Get cached pressure map for symbol."""
        return self._current_maps.get(symbol)
    
    def get_all_pressure_maps(self) -> Dict[str, OrderbookPressureMap]:
        """Get all cached pressure maps."""
        return self._current_maps.copy()


# Singleton
_engine: Optional[OrderbookPressureEngine] = None


def get_orderbook_pressure_engine() -> OrderbookPressureEngine:
    """Get singleton instance of OrderbookPressureEngine."""
    global _engine
    if _engine is None:
        _engine = OrderbookPressureEngine()
    return _engine
