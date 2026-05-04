"""
Microstructure Intelligence v2 — Snapshot Engine

Core logic for microstructure snapshot calculation.

Features:
- Spread calculation (bps)
- Depth scoring
- Imbalance scoring
- Pressure metrics (liquidation, funding, OI)
- State classification (liquidity, pressure, microstructure)
"""

from typing import Optional, Dict
from datetime import datetime
import random

from .microstructure_types import (
    MicrostructureSnapshot,
    MicrostructureSummary,
    OrderbookData,
    ExchangeData,
    LiquidityState,
    PressureState,
    MicrostructureState,
    DEPTH_DEEP_THRESHOLD,
    DEPTH_NORMAL_THRESHOLD,
    SPREAD_LOW_THRESHOLD,
    SPREAD_HIGH_THRESHOLD,
    IMBALANCE_THRESHOLD,
    PRESSURE_HIGH_THRESHOLD,
    PRESSURE_EXTREME_THRESHOLD,
    CONF_WEIGHT_SPREAD,
    CONF_WEIGHT_DEPTH,
    CONF_WEIGHT_IMBALANCE,
    CONF_WEIGHT_LIQUIDATION,
    CONF_WEIGHT_OI,
)


class MicrostructureSnapshotEngine:
    """
    Microstructure Snapshot Engine.
    
    Builds unified microstructure snapshot from orderbook and exchange data.
    """
    
    def __init__(self):
        self._current_snapshots: Dict[str, MicrostructureSnapshot] = {}
    
    # ═══════════════════════════════════════════════════════════
    # Core Metric Calculations
    # ═══════════════════════════════════════════════════════════
    
    def calculate_spread_bps(
        self,
        best_bid: float,
        best_ask: float,
    ) -> float:
        """
        Calculate spread in basis points.
        
        Formula: ((ask - bid) / mid_price) * 10000
        """
        if best_bid <= 0 or best_ask <= 0:
            return 0.0
        
        mid_price = (best_bid + best_ask) / 2
        spread = best_ask - best_bid
        spread_bps = (spread / mid_price) * 10000
        
        return round(max(spread_bps, 0.0), 2)
    
    def calculate_depth_score(
        self,
        total_depth: float,
        depth_reference: float,
    ) -> float:
        """
        Calculate normalized depth score.
        
        Formula: min(total_depth / reference, 1.0)
        """
        if depth_reference <= 0:
            return 0.5
        
        score = total_depth / depth_reference
        return round(min(max(score, 0.0), 1.0), 4)
    
    def calculate_imbalance_score(
        self,
        bid_volume: float,
        ask_volume: float,
    ) -> float:
        """
        Calculate bid/ask imbalance score.
        
        Formula: (bid_volume - ask_volume) / (bid_volume + ask_volume)
        Range: -1 to +1
        """
        total = bid_volume + ask_volume
        if total <= 0:
            return 0.0
        
        imbalance = (bid_volume - ask_volume) / total
        return round(min(max(imbalance, -1.0), 1.0), 4)
    
    # ═══════════════════════════════════════════════════════════
    # Pressure Calculations
    # ═══════════════════════════════════════════════════════════
    
    def calculate_liquidation_pressure(
        self,
        liquidation_long: float,
        liquidation_short: float,
    ) -> float:
        """
        Calculate liquidation pressure.
        
        Positive = shorts squeezed (bullish)
        Negative = longs flushed (bearish)
        Range: -1 to +1
        """
        total = liquidation_long + liquidation_short
        if total <= 0:
            return 0.0
        
        # Shorts getting liquidated = bullish pressure
        # Longs getting liquidated = bearish pressure
        pressure = (liquidation_short - liquidation_long) / total
        return round(min(max(pressure, -1.0), 1.0), 4)
    
    def calculate_funding_pressure(
        self,
        funding_rate: float,
    ) -> float:
        """
        Calculate funding pressure.
        
        Positive = overcrowded longs
        Negative = overcrowded shorts
        Range: -1 to +1
        """
        # Normalize funding rate (typically -0.01 to +0.01)
        # Scale by 100 to get -1 to +1 range
        pressure = funding_rate * 100
        return round(min(max(pressure, -1.0), 1.0), 4)
    
    def calculate_oi_pressure(
        self,
        oi_current: float,
        oi_previous: float,
    ) -> float:
        """
        Calculate OI pressure.
        
        Positive = OI increasing (new positions)
        Negative = OI decreasing (closing positions)
        Range: -1 to +1
        """
        if oi_previous <= 0:
            return 0.0
        
        change_pct = (oi_current - oi_previous) / oi_previous
        # Normalize to -1 to +1 (cap at 10% change)
        pressure = change_pct / 0.10
        return round(min(max(pressure, -1.0), 1.0), 4)
    
    # ═══════════════════════════════════════════════════════════
    # State Classifications
    # ═══════════════════════════════════════════════════════════
    
    def classify_liquidity_state(
        self,
        depth_score: float,
        spread_bps: float,
    ) -> LiquidityState:
        """
        Classify liquidity state.
        
        DEEP: depth >= 0.70 and spread low
        NORMAL: depth 0.40-0.70
        THIN: depth < 0.40 or spread high
        """
        if spread_bps > SPREAD_HIGH_THRESHOLD:
            return "THIN"
        
        if depth_score >= DEPTH_DEEP_THRESHOLD and spread_bps <= SPREAD_LOW_THRESHOLD:
            return "DEEP"
        
        if depth_score >= DEPTH_NORMAL_THRESHOLD:
            return "NORMAL"
        
        return "THIN"
    
    def classify_pressure_state(
        self,
        imbalance_score: float,
    ) -> PressureState:
        """
        Classify pressure state.
        
        BUY_PRESSURE: imbalance > 0.15
        SELL_PRESSURE: imbalance < -0.15
        BALANCED: otherwise
        """
        if imbalance_score > IMBALANCE_THRESHOLD:
            return "BUY_PRESSURE"
        elif imbalance_score < -IMBALANCE_THRESHOLD:
            return "SELL_PRESSURE"
        else:
            return "BALANCED"
    
    def classify_microstructure_state(
        self,
        liquidity_state: LiquidityState,
        pressure_state: PressureState,
        liquidation_pressure: float,
        funding_pressure: float,
        oi_pressure: float,
    ) -> MicrostructureState:
        """
        Classify overall microstructure state.
        
        SUPPORTIVE: DEEP liquidity, orderly pressure
        NEUTRAL: NORMAL liquidity, BALANCED pressure
        FRAGILE: THIN liquidity, moderate stress
        STRESSED: THIN liquidity + high stress
        """
        # Calculate stress level
        stress = (
            abs(liquidation_pressure) +
            abs(funding_pressure) +
            abs(oi_pressure)
        ) / 3
        
        # Check for STRESSED
        if liquidity_state == "THIN":
            if stress >= PRESSURE_HIGH_THRESHOLD:
                return "STRESSED"
            else:
                return "FRAGILE"
        
        # Check for SUPPORTIVE
        if liquidity_state == "DEEP":
            if stress < PRESSURE_HIGH_THRESHOLD:
                return "SUPPORTIVE"
        
        # Check for NEUTRAL
        if liquidity_state == "NORMAL" and pressure_state == "BALANCED":
            return "NEUTRAL"
        
        # Default based on liquidity
        if liquidity_state == "DEEP":
            return "SUPPORTIVE"
        elif liquidity_state == "NORMAL":
            return "NEUTRAL"
        else:
            return "FRAGILE"
    
    # ═══════════════════════════════════════════════════════════
    # Confidence Calculation
    # ═══════════════════════════════════════════════════════════
    
    def calculate_confidence(
        self,
        spread_bps: float,
        depth_score: float,
        imbalance_score: float,
        liquidation_pressure: float,
        oi_pressure: float,
    ) -> float:
        """
        Calculate snapshot confidence.
        
        Formula:
        0.25 * (1 - normalized_spread) +
        0.25 * depth_score +
        0.20 * abs(imbalance_score) +
        0.15 * abs(liquidation_pressure) +
        0.15 * abs(oi_pressure)
        """
        # Normalize spread (lower is better)
        normalized_spread = min(spread_bps / 20.0, 1.0)
        spread_component = 1.0 - normalized_spread
        
        confidence = (
            CONF_WEIGHT_SPREAD * spread_component +
            CONF_WEIGHT_DEPTH * depth_score +
            CONF_WEIGHT_IMBALANCE * abs(imbalance_score) +
            CONF_WEIGHT_LIQUIDATION * abs(liquidation_pressure) +
            CONF_WEIGHT_OI * abs(oi_pressure)
        )
        
        return round(min(max(confidence, 0.0), 1.0), 4)
    
    # ═══════════════════════════════════════════════════════════
    # Reason Generation
    # ═══════════════════════════════════════════════════════════
    
    def generate_reason(
        self,
        liquidity_state: LiquidityState,
        pressure_state: PressureState,
        microstructure_state: MicrostructureState,
        liquidation_pressure: float,
    ) -> str:
        """Generate human-readable reason for microstructure state."""
        liquidity_desc = {
            "DEEP": "deep orderbook",
            "NORMAL": "normal orderbook depth",
            "THIN": "thin orderbook",
        }[liquidity_state]
        
        pressure_desc = {
            "BUY_PRESSURE": "buy imbalance",
            "SELL_PRESSURE": "sell imbalance",
            "BALANCED": "balanced flow",
        }[pressure_state]
        
        liq_level = "manageable" if abs(liquidation_pressure) < 0.5 else "elevated"
        
        if microstructure_state == "SUPPORTIVE":
            return f"{liquidity_desc} with mild {pressure_desc} and {liq_level} liquidation pressure"
        elif microstructure_state == "NEUTRAL":
            return f"{liquidity_desc} with {pressure_desc} and stable market conditions"
        elif microstructure_state == "FRAGILE":
            return f"{liquidity_desc} creating fragile conditions despite {pressure_desc}"
        else:  # STRESSED
            return f"{liquidity_desc} under stress with {pressure_desc} and elevated liquidation activity"
    
    # ═══════════════════════════════════════════════════════════
    # Main Snapshot Build
    # ═══════════════════════════════════════════════════════════
    
    def build_snapshot(
        self,
        symbol: str,
        orderbook: OrderbookData,
        exchange: ExchangeData,
    ) -> MicrostructureSnapshot:
        """
        Build microstructure snapshot from raw data.
        """
        # Calculate core metrics
        spread_bps = self.calculate_spread_bps(
            orderbook.best_bid,
            orderbook.best_ask,
        )
        
        depth_score = self.calculate_depth_score(
            orderbook.total_depth,
            orderbook.depth_reference,
        )
        
        imbalance_score = self.calculate_imbalance_score(
            orderbook.bid_volume,
            orderbook.ask_volume,
        )
        
        # Calculate pressure metrics
        liquidation_pressure = self.calculate_liquidation_pressure(
            exchange.liquidation_long,
            exchange.liquidation_short,
        )
        
        funding_pressure = self.calculate_funding_pressure(
            exchange.funding_rate,
        )
        
        oi_pressure = self.calculate_oi_pressure(
            exchange.oi_current,
            exchange.oi_previous,
        )
        
        # Classify states
        liquidity_state = self.classify_liquidity_state(depth_score, spread_bps)
        pressure_state = self.classify_pressure_state(imbalance_score)
        microstructure_state = self.classify_microstructure_state(
            liquidity_state,
            pressure_state,
            liquidation_pressure,
            funding_pressure,
            oi_pressure,
        )
        
        # Calculate confidence
        confidence = self.calculate_confidence(
            spread_bps,
            depth_score,
            imbalance_score,
            liquidation_pressure,
            oi_pressure,
        )
        
        # Generate reason
        reason = self.generate_reason(
            liquidity_state,
            pressure_state,
            microstructure_state,
            liquidation_pressure,
        )
        
        snapshot = MicrostructureSnapshot(
            symbol=symbol,
            spread_bps=spread_bps,
            depth_score=depth_score,
            imbalance_score=imbalance_score,
            liquidation_pressure=liquidation_pressure,
            funding_pressure=funding_pressure,
            oi_pressure=oi_pressure,
            liquidity_state=liquidity_state,
            pressure_state=pressure_state,
            microstructure_state=microstructure_state,
            confidence=confidence,
            reason=reason,
        )
        
        self._current_snapshots[symbol] = snapshot
        return snapshot
    
    # ═══════════════════════════════════════════════════════════
    # Simulated Snapshot (for testing)
    # ═══════════════════════════════════════════════════════════
    
    def build_snapshot_simulated(
        self,
        symbol: str = "BTC",
    ) -> MicrostructureSnapshot:
        """
        Build snapshot using simulated data.
        
        For testing when real exchange data is not available.
        """
        # Generate realistic mock orderbook data
        price = 42000.0 + random.uniform(-1000, 1000)
        spread = random.uniform(0.5, 10.0)  # 0.5-10 bps
        
        orderbook = OrderbookData(
            best_bid=price - spread / 2,
            best_ask=price + spread / 2,
            bid_volume=random.uniform(50000, 200000),
            ask_volume=random.uniform(50000, 200000),
            total_depth=random.uniform(300000, 1200000),
            depth_reference=1000000.0,
        )
        
        # Generate realistic mock exchange data
        exchange = ExchangeData(
            liquidation_long=random.uniform(0, 5000000),
            liquidation_short=random.uniform(0, 5000000),
            funding_rate=random.uniform(-0.005, 0.005),
            oi_current=random.uniform(800000000, 1200000000),
            oi_previous=random.uniform(800000000, 1200000000),
        )
        
        return self.build_snapshot(symbol, orderbook, exchange)
    
    # ═══════════════════════════════════════════════════════════
    # Accessors
    # ═══════════════════════════════════════════════════════════
    
    def get_snapshot(
        self,
        symbol: str,
    ) -> Optional[MicrostructureSnapshot]:
        """Get cached snapshot for symbol."""
        return self._current_snapshots.get(symbol)
    
    def get_all_snapshots(self) -> Dict[str, MicrostructureSnapshot]:
        """Get all cached snapshots."""
        return self._current_snapshots.copy()


# Singleton
_engine: Optional[MicrostructureSnapshotEngine] = None


def get_microstructure_snapshot_engine() -> MicrostructureSnapshotEngine:
    """Get singleton instance of MicrostructureSnapshotEngine."""
    global _engine
    if _engine is None:
        _engine = MicrostructureSnapshotEngine()
    return _engine
