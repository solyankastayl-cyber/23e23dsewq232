"""
PHASE 8 - Liquidity Intelligence API Routes
=============================================
REST API endpoints for liquidity analysis.

Endpoints:
- GET /api/liquidity/snapshot/{symbol}
- GET /api/liquidity/depth/{symbol}
- GET /api/liquidity/zones/{symbol}
- GET /api/liquidity/stops/{symbol}
- GET /api/liquidity/liquidations/{symbol}
- GET /api/liquidity/sweeps/{symbol}
- GET /api/liquidity/imbalance/{symbol}
- GET /api/liquidity/history/{symbol}
- GET /api/liquidity/health
"""

import random
from typing import List, Optional
from datetime import datetime, timezone
from fastapi import APIRouter, Query, HTTPException
from pydantic import BaseModel

from .liquidity_types import (
    UnifiedLiquiditySnapshot, LiquidityQuality, SweepDirection,
    PostSweepBias, DEFAULT_CONFIG
)
from .orderbook_depth_engine import OrderbookDepthEngine, generate_mock_orderbook
from .liquidity_zone_detector import LiquidityZoneDetector
from .stop_cluster_detector import StopClusterDetector
from .liquidation_zone_detector import LiquidationZoneDetector
from .sweep_probability_engine import SweepProbabilityEngine
from .liquidity_imbalance_engine import LiquidityImbalanceEngine
from .liquidity_repository import LiquidityRepository


router = APIRouter(prefix="/api/liquidity", tags=["Liquidity Intelligence"])


# Initialize engines
depth_engine = OrderbookDepthEngine()
zone_detector = LiquidityZoneDetector()
stop_detector = StopClusterDetector()
liquidation_detector = LiquidationZoneDetector()
sweep_engine = SweepProbabilityEngine()
imbalance_engine = LiquidityImbalanceEngine()
repository = LiquidityRepository()


# ===== Mock Data Generators =====

def generate_mock_price_history(
    current_price: float = 64000.0,
    length: int = 100
) -> tuple:
    """Generate mock price history for testing."""
    prices = []
    highs = []
    lows = []
    
    price = current_price * 0.98  # Start slightly lower
    
    for _ in range(length):
        # Random walk with trend
        change = random.gauss(0, 0.005) * price
        price = price + change
        
        high = price * (1 + random.uniform(0.001, 0.01))
        low = price * (1 - random.uniform(0.001, 0.01))
        
        prices.append(price)
        highs.append(high)
        lows.append(low)
    
    # Ensure last price is near current
    prices[-1] = current_price
    highs[-1] = current_price * 1.002
    lows[-1] = current_price * 0.998
    
    return prices, highs, lows


# ===== Response Models =====

class DepthResponse(BaseModel):
    symbol: str
    bid_depth: float
    ask_depth: float
    depth_imbalance: float
    spread_bps: float
    liquidity_quality: str
    bid_walls: list
    ask_walls: list
    thin_zones: list
    computed_at: str


class ZonesResponse(BaseModel):
    symbol: str
    total_zones: int
    zones_above: int
    zones_below: int
    zones: list
    summary: dict
    computed_at: str


class StopsResponse(BaseModel):
    symbol: str
    total_clusters: int
    long_stop_clusters: int
    short_stop_clusters: int
    clusters: list
    nearest: dict
    computed_at: str


class LiquidationsResponse(BaseModel):
    symbol: str
    total_zones: int
    long_liquidation_zones: int
    short_liquidation_zones: int
    zones: list
    nearest: dict
    computed_at: str


class SweepsResponse(BaseModel):
    symbol: str
    total_signals: int
    dominant_direction: str
    signals: list
    summary: dict
    computed_at: str


class ImbalanceResponse(BaseModel):
    symbol: str
    imbalance_score: float
    dominant_side: str
    volatility_risk: float
    bid_pressure: float
    ask_pressure: float
    trading_signal: dict
    computed_at: str


class SnapshotResponse(BaseModel):
    symbol: str
    current_price: float
    bid_depth: float
    ask_depth: float
    depth_imbalance: float
    nearest_stop_cluster_above: float
    nearest_stop_cluster_below: float
    sweep_probability: float
    sweep_direction: str
    post_sweep_bias: str
    liquidity_quality: str
    cascade_risk: float
    execution_risk: float
    computed_at: str


# ===== API Endpoints =====

@router.get("/health")
async def liquidity_health():
    """Health check for Liquidity Intelligence."""
    return {
        "status": "healthy",
        "version": "phase8_liquidity_v1",
        "engines": {
            "orderbook_depth": "ready",
            "liquidity_zones": "ready",
            "stop_clusters": "ready",
            "liquidation_zones": "ready",
            "sweep_probability": "ready",
            "liquidity_imbalance": "ready"
        },
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@router.get("/snapshot/{symbol}", response_model=SnapshotResponse)
async def get_liquidity_snapshot(
    symbol: str,
    current_price: float = Query(64000.0, description="Current market price")
):
    """
    Get unified liquidity snapshot for a symbol.
    
    Combines all liquidity intelligence into a single view.
    """
    try:
        now = datetime.now(timezone.utc)
        
        # Generate mock data
        bids, asks = generate_mock_orderbook(symbol, current_price)
        prices, highs, lows = generate_mock_price_history(current_price)
        
        # Analyze depth
        depth = depth_engine.analyze_depth(bids, asks, symbol)
        
        # Detect stop clusters
        stops = stop_detector.detect_clusters(prices, current_price, highs, lows, symbol)
        
        # Get nearest stops
        stops_above = [s for s in stops if s.price_level > current_price]
        stops_below = [s for s in stops if s.price_level < current_price]
        
        nearest_above = min(stops_above, key=lambda s: s.price_level).price_level if stops_above else None
        nearest_below = max(stops_below, key=lambda s: s.price_level).price_level if stops_below else None
        
        # Detect liquidation zones
        liquidations = liquidation_detector.detect_zones(prices, current_price, symbol=symbol)
        
        # Get liquidity zones
        zones = zone_detector.detect_zones(depth, prices, current_price)
        
        # Calculate sweep probability
        sweep_signals = sweep_engine.calculate_sweep_signals(
            current_price, stops, zones, "NEUTRAL", symbol
        )
        
        highest_sweep = sweep_engine.get_highest_probability_sweep(sweep_signals)
        
        # Calculate imbalance
        imbalance = imbalance_engine.analyze_imbalance(depth, symbol=symbol)
        
        # Build unified snapshot
        snapshot = UnifiedLiquiditySnapshot(
            symbol=symbol,
            current_price=current_price,
            timestamp=now,
            bid_depth=depth.bid_depth,
            ask_depth=depth.ask_depth,
            depth_imbalance=depth.depth_imbalance,
            nearest_stop_cluster_above=nearest_above,
            nearest_stop_cluster_below=nearest_below,
            sweep_probability=highest_sweep.sweep_probability if highest_sweep else 0.0,
            sweep_direction=highest_sweep.sweep_direction if highest_sweep else None,
            post_sweep_bias=highest_sweep.post_sweep_bias if highest_sweep else None,
            liquidity_quality=depth.liquidity_quality,
            cascade_risk=max((s.cascade_risk for s in stops), default=0),
            execution_risk=imbalance.volatility_risk
        )
        
        # Save to repository
        try:
            repository.save_unified_snapshot(snapshot)
        except Exception:
            pass
        
        return SnapshotResponse(
            symbol=symbol,
            current_price=current_price,
            bid_depth=round(snapshot.bid_depth, 2),
            ask_depth=round(snapshot.ask_depth, 2),
            depth_imbalance=round(snapshot.depth_imbalance, 4),
            nearest_stop_cluster_above=snapshot.nearest_stop_cluster_above or 0,
            nearest_stop_cluster_below=snapshot.nearest_stop_cluster_below or 0,
            sweep_probability=round(snapshot.sweep_probability, 3),
            sweep_direction=snapshot.sweep_direction.value if snapshot.sweep_direction else "NONE",
            post_sweep_bias=snapshot.post_sweep_bias.value if snapshot.post_sweep_bias else "NEUTRAL",
            liquidity_quality=snapshot.liquidity_quality.value,
            cascade_risk=round(snapshot.cascade_risk, 3),
            execution_risk=round(snapshot.execution_risk, 3),
            computed_at=now.isoformat()
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/depth/{symbol}", response_model=DepthResponse)
async def get_orderbook_depth(
    symbol: str,
    current_price: float = Query(64000.0, description="Current market price")
):
    """
    Get orderbook depth analysis.
    
    Analyzes:
    - Bid/ask depth totals
    - Depth imbalance
    - Order walls
    - Thin liquidity zones
    """
    try:
        now = datetime.now(timezone.utc)
        
        # Generate mock orderbook
        bids, asks = generate_mock_orderbook(symbol, current_price)
        
        # Analyze depth
        depth = depth_engine.analyze_depth(bids, asks, symbol)
        
        # Save to repository
        try:
            repository.save_depth_snapshot(depth)
        except Exception:
            pass
        
        return DepthResponse(
            symbol=symbol,
            bid_depth=round(depth.bid_depth, 2),
            ask_depth=round(depth.ask_depth, 2),
            depth_imbalance=round(depth.depth_imbalance, 4),
            spread_bps=round(depth.spread_bps, 2),
            liquidity_quality=depth.liquidity_quality.value,
            bid_walls=[w.to_dict() for w in depth.bid_walls],
            ask_walls=[w.to_dict() for w in depth.ask_walls],
            thin_zones=depth.thin_zones,
            computed_at=now.isoformat()
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/zones/{symbol}", response_model=ZonesResponse)
async def get_liquidity_zones(
    symbol: str,
    current_price: float = Query(64000.0, description="Current market price")
):
    """
    Get detected liquidity zones.
    
    Returns:
    - High liquidity zones
    - Thin liquidity zones
    - Magnet zones
    - Sweep-prone levels
    """
    try:
        now = datetime.now(timezone.utc)
        
        # Generate data
        bids, asks = generate_mock_orderbook(symbol, current_price)
        prices, _, _ = generate_mock_price_history(current_price)
        
        # Analyze depth
        depth = depth_engine.analyze_depth(bids, asks, symbol)
        
        # Detect zones
        zones = zone_detector.detect_zones(depth, prices, current_price)
        
        # Get summary
        summary = zone_detector.get_zone_summary(zones, current_price)
        
        # Save to repository
        try:
            repository.save_liquidity_zones(zones, symbol)
        except Exception:
            pass
        
        zones_above = [z for z in zones if z.mid_price > current_price]
        zones_below = [z for z in zones if z.mid_price < current_price]
        
        return ZonesResponse(
            symbol=symbol,
            total_zones=len(zones),
            zones_above=len(zones_above),
            zones_below=len(zones_below),
            zones=[z.to_dict() for z in zones[:20]],
            summary=summary,
            computed_at=now.isoformat()
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stops/{symbol}", response_model=StopsResponse)
async def get_stop_clusters(
    symbol: str,
    current_price: float = Query(64000.0, description="Current market price")
):
    """
    Get detected stop-loss clusters.
    
    Identifies:
    - Equal highs/lows (likely stops)
    - Range boundaries
    - Swing level stops
    """
    try:
        now = datetime.now(timezone.utc)
        
        # Generate price history
        prices, highs, lows = generate_mock_price_history(current_price)
        
        # Detect clusters
        clusters = stop_detector.detect_clusters(prices, current_price, highs, lows, symbol)
        
        # Get summary and nearest
        summary = stop_detector.get_cluster_summary(clusters, current_price)
        nearest = stop_detector.get_nearest_clusters(clusters, current_price)
        
        # Save to repository
        try:
            repository.save_stop_clusters(clusters, symbol)
        except Exception:
            pass
        
        return StopsResponse(
            symbol=symbol,
            total_clusters=len(clusters),
            long_stop_clusters=summary.get("long_stop_clusters", 0),
            short_stop_clusters=summary.get("short_stop_clusters", 0),
            clusters=[c.to_dict() for c in clusters[:15]],
            nearest=nearest,
            computed_at=now.isoformat()
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/liquidations/{symbol}", response_model=LiquidationsResponse)
async def get_liquidation_zones(
    symbol: str,
    current_price: float = Query(64000.0, description="Current market price")
):
    """
    Get estimated liquidation zones.
    
    Identifies:
    - Trapped long positions (liquidation below)
    - Trapped short positions (liquidation above)
    - High leverage density zones
    """
    try:
        now = datetime.now(timezone.utc)
        
        # Generate price history
        prices, _, _ = generate_mock_price_history(current_price)
        
        # Detect zones
        zones = liquidation_detector.detect_zones(prices, current_price, symbol=symbol)
        
        # Get summary and nearest
        summary = liquidation_detector.get_zone_summary(zones, current_price)
        nearest = liquidation_detector.get_nearest_liquidation_zones(zones, current_price)
        
        # Save to repository
        try:
            repository.save_liquidation_zones(zones, symbol)
        except Exception:
            pass
        
        return LiquidationsResponse(
            symbol=symbol,
            total_zones=len(zones),
            long_liquidation_zones=summary.get("long_liquidation_zones", 0),
            short_liquidation_zones=summary.get("short_liquidation_zones", 0),
            zones=[z.to_dict() for z in zones[:15]],
            nearest=nearest,
            computed_at=now.isoformat()
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sweeps/{symbol}", response_model=SweepsResponse)
async def get_sweep_signals(
    symbol: str,
    current_price: float = Query(64000.0, description="Current market price"),
    price_trend: str = Query("NEUTRAL", description="Price trend: UP, DOWN, NEUTRAL")
):
    """
    Get sweep probability signals.
    
    Predicts:
    - Probability of price sweeping liquidity
    - Sweep direction
    - Post-sweep bias (reversal expectation)
    """
    try:
        now = datetime.now(timezone.utc)
        
        # Generate data
        bids, asks = generate_mock_orderbook(symbol, current_price)
        prices, highs, lows = generate_mock_price_history(current_price)
        
        # Analyze depth and detect clusters
        depth = depth_engine.analyze_depth(bids, asks, symbol)
        stops = stop_detector.detect_clusters(prices, current_price, highs, lows, symbol)
        zones = zone_detector.detect_zones(depth, prices, current_price)
        
        # Calculate sweep signals
        signals = sweep_engine.calculate_sweep_signals(
            current_price, stops, zones, price_trend.upper(), symbol
        )
        
        # Get summary
        summary = sweep_engine.get_sweep_summary(signals, current_price)
        
        # Save to repository
        try:
            repository.save_sweep_signals(signals, symbol)
        except Exception:
            pass
        
        return SweepsResponse(
            symbol=symbol,
            total_signals=len(signals),
            dominant_direction=summary.get("dominant_direction", "NEUTRAL"),
            signals=[s.to_dict() for s in signals[:10]],
            summary=summary,
            computed_at=now.isoformat()
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/imbalance/{symbol}", response_model=ImbalanceResponse)
async def get_liquidity_imbalance(
    symbol: str,
    current_price: float = Query(64000.0, description="Current market price")
):
    """
    Get liquidity imbalance analysis.
    
    Analyzes:
    - Bid/ask dominance
    - Volatility risk
    - One-sided pressure
    """
    try:
        now = datetime.now(timezone.utc)
        
        # Generate orderbook
        bids, asks = generate_mock_orderbook(symbol, current_price)
        
        # Analyze depth
        depth = depth_engine.analyze_depth(bids, asks, symbol)
        
        # Analyze imbalance
        imbalance = imbalance_engine.analyze_imbalance(depth, symbol=symbol)
        
        # Get trading signal
        signal = imbalance_engine.get_trading_signal(imbalance)
        
        # Save to repository
        try:
            repository.save_imbalance(imbalance)
        except Exception:
            pass
        
        return ImbalanceResponse(
            symbol=symbol,
            imbalance_score=round(imbalance.imbalance_score, 4),
            dominant_side=imbalance.dominant_side.value,
            volatility_risk=round(imbalance.volatility_risk, 3),
            bid_pressure=round(imbalance.bid_pressure, 3),
            ask_pressure=round(imbalance.ask_pressure, 3),
            trading_signal=signal,
            computed_at=now.isoformat()
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history/{symbol}")
async def get_liquidity_history(
    symbol: str,
    hours_back: int = Query(24, description="Hours to look back"),
    limit: int = Query(50, description="Maximum records")
):
    """
    Get historical liquidity snapshots.
    """
    try:
        snapshots = repository.get_snapshot_history(symbol, hours_back, limit)
        
        return {
            "symbol": symbol,
            "hours_back": hours_back,
            "count": len(snapshots),
            "snapshots": snapshots,
            "retrieved_at": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats")
async def get_liquidity_stats():
    """Get repository and engine statistics."""
    try:
        repo_stats = repository.get_stats()
        
        return {
            "repository": repo_stats,
            "engines": {
                "orderbook_depth": "active",
                "liquidity_zones": "active",
                "stop_clusters": "active",
                "liquidation_zones": "active",
                "sweep_probability": "active",
                "liquidity_imbalance": "active"
            },
            "config": DEFAULT_CONFIG,
            "retrieved_at": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
