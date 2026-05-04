"""
PHASE 9 - Market Microstructure API Routes
==========================================
REST API endpoints for microstructure analysis.

Endpoints:
- GET /api/microstructure/snapshot/{symbol}
- GET /api/microstructure/flow/{symbol}
- GET /api/microstructure/aggressor/{symbol}
- GET /api/microstructure/imbalance/{symbol}
- GET /api/microstructure/timing/{symbol}
- GET /api/microstructure/pressure/{symbol}
- GET /api/microstructure/history/{symbol}
- GET /api/microstructure/signals/{symbol}
- GET /api/microstructure/health
"""

import random
from typing import List, Optional
from datetime import datetime, timezone
from fastapi import APIRouter, Query, HTTPException
from pydantic import BaseModel

from .microstructure_types import (
    FlowState, AggressorSide, TimingSignal, PressureState,
    ImbalanceType, UnifiedMicrostructureSnapshot,
    DEFAULT_MICROSTRUCTURE_CONFIG
)
from .order_flow_engine import OrderFlowEngine, generate_mock_trades
from .aggressor_detector import AggressorDetector
from .micro_imbalance_engine import MicroImbalanceEngine, generate_mock_orderbook_levels
from .execution_timing_engine import ExecutionTimingEngine
from .flow_pressure_engine import FlowPressureEngine
from .microstructure_repository import MicrostructureRepository


router = APIRouter(prefix="/api/market-microstructure", tags=["Market Microstructure"])


# Initialize engines
flow_engine = OrderFlowEngine()
aggressor_detector = AggressorDetector()
imbalance_engine = MicroImbalanceEngine()
timing_engine = ExecutionTimingEngine()
pressure_engine = FlowPressureEngine()
repository = MicrostructureRepository()


# ===== Response Models =====

class FlowResponse(BaseModel):
    symbol: str
    flow_state: str
    buy_flow: float
    sell_flow: float
    net_flow: float
    flow_ratio: float
    aggression_score: float
    burst_detected: bool
    burst_direction: Optional[str]
    flow_persistence: float
    absorption_detected: bool
    computed_at: str


class AggressorResponse(BaseModel):
    symbol: str
    aggressor_side: str
    aggressor_confidence: float
    aggressor_ratio: float
    buy_initiated_pct: float
    sell_initiated_pct: float
    aggressor_shift: bool
    trade_count: int
    computed_at: str


class ImbalanceResponse(BaseModel):
    symbol: str
    micro_imbalance_score: float
    imbalance_type: str
    dominant_micro_side: str
    vacuum_risk: float
    imbalance_strength: float
    top_book_skew: float
    computed_at: str


class TimingResponse(BaseModel):
    symbol: str
    timing_signal: str
    timing_quality: float
    urgency_score: float
    execution_readiness: float
    entry_size_pct: float
    delay_recommendation_ms: int
    notes: List[str]
    computed_at: str


class PressureResponse(BaseModel):
    symbol: str
    flow_pressure_state: str
    pressure_direction: str
    pressure_strength: float
    exhaustion_probability: float
    exhaustion_type: Optional[str]
    building_detected: bool
    absorption_score: float
    fake_push_probability: float
    computed_at: str


class SnapshotResponse(BaseModel):
    symbol: str
    flowState: str
    aggressorRatio: float
    microImbalanceScore: float
    timingSignal: str
    executionReadiness: float
    pressureDirection: str
    pressureStrength: float
    exhaustionProbability: float
    computed_at: str


# ===== API Endpoints =====

@router.get("/health")
async def microstructure_health():
    """Health check for Market Microstructure module."""
    return {
        "status": "healthy",
        "version": "phase9_microstructure_v1",
        "engines": {
            "order_flow": "ready",
            "aggressor_detector": "ready",
            "micro_imbalance": "ready",
            "execution_timing": "ready",
            "flow_pressure": "ready"
        },
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@router.get("/snapshot/{symbol}", response_model=SnapshotResponse)
async def get_microstructure_snapshot(
    symbol: str,
    current_price: float = Query(64000.0, description="Current market price"),
    direction: str = Query("LONG", description="Intended trade direction: LONG or SHORT")
):
    """
    Get unified microstructure snapshot for a symbol.
    
    Combines all microstructure intelligence into a single view.
    """
    try:
        now = datetime.now(timezone.utc)
        
        # Generate mock data
        trades, bid_price, ask_price = generate_mock_trades(current_price)
        bids, asks = generate_mock_orderbook_levels(current_price)
        
        # Analyze flow
        flow = flow_engine.analyze_flow(trades, bid_price, ask_price, symbol)
        
        # Detect aggressor
        aggressor = aggressor_detector.detect_aggressor(trades, bid_price, ask_price, symbol)
        
        # Detect imbalance
        imbalance = imbalance_engine.detect_imbalance(bids, asks, symbol)
        
        # Analyze pressure
        pressure = pressure_engine.analyze_pressure(
            flow, flow_engine.flow_history, 0, 0, symbol
        )
        
        # Calculate timing
        spread_bps = ((ask_price - bid_price) / current_price) * 10000
        timing = timing_engine.calculate_timing(
            flow, aggressor, imbalance, pressure,
            direction.upper(), spread_bps, symbol
        )
        
        # Build unified snapshot
        snapshot = UnifiedMicrostructureSnapshot(
            symbol=symbol,
            timestamp=now,
            flow_state=flow.flow_state,
            aggressor_ratio=aggressor.aggressor_ratio,
            micro_imbalance_score=imbalance.micro_imbalance_score,
            timing_signal=timing.timing_signal,
            execution_readiness=timing.execution_readiness,
            pressure_direction=pressure.pressure_direction,
            pressure_strength=pressure.pressure_strength,
            exhaustion_probability=pressure.exhaustion_probability,
            spread_bps=spread_bps,
            volatility=0.02
        )
        
        # Save to repository
        try:
            repository.save_unified_snapshot(snapshot)
        except Exception:
            pass
        
        return SnapshotResponse(
            symbol=symbol,
            flowState=snapshot.flow_state.value,
            aggressorRatio=round(snapshot.aggressor_ratio, 4),
            microImbalanceScore=round(snapshot.micro_imbalance_score, 4),
            timingSignal=snapshot.timing_signal.value,
            executionReadiness=round(snapshot.execution_readiness, 3),
            pressureDirection=snapshot.pressure_direction,
            pressureStrength=round(snapshot.pressure_strength, 3),
            exhaustionProbability=round(snapshot.exhaustion_probability, 3),
            computed_at=now.isoformat()
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/flow/{symbol}", response_model=FlowResponse)
async def get_order_flow(
    symbol: str,
    current_price: float = Query(64000.0, description="Current market price"),
    bias: str = Query("NEUTRAL", description="Trade bias: BUY, SELL, NEUTRAL")
):
    """
    Get order flow analysis.
    
    Analyzes:
    - Buy/sell flow volumes
    - Aggressive flow detection
    - Burst activity
    - Flow persistence
    """
    try:
        now = datetime.now(timezone.utc)
        
        # Generate mock trades with bias
        trades, bid_price, ask_price = generate_mock_trades(
            current_price, count=50, bias=bias.upper()
        )
        
        # Analyze flow
        flow = flow_engine.analyze_flow(trades, bid_price, ask_price, symbol)
        
        # Save to repository
        try:
            repository.save_order_flow(flow)
        except Exception:
            pass
        
        return FlowResponse(
            symbol=symbol,
            flow_state=flow.flow_state.value,
            buy_flow=round(flow.buy_flow, 2),
            sell_flow=round(flow.sell_flow, 2),
            net_flow=round(flow.net_flow, 2),
            flow_ratio=round(flow.flow_ratio, 4),
            aggression_score=round(flow.aggression_score, 4),
            burst_detected=flow.burst_detected,
            burst_direction=flow.burst_direction,
            flow_persistence=round(flow.flow_persistence, 3),
            absorption_detected=flow.absorption_detected,
            computed_at=now.isoformat()
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/aggressor/{symbol}", response_model=AggressorResponse)
async def get_aggressor(
    symbol: str,
    current_price: float = Query(64000.0, description="Current market price")
):
    """
    Get aggressor side detection.
    
    Determines:
    - Who initiated trades (buyer/seller)
    - Aggressor ratio
    - Recent shifts in aggression
    """
    try:
        now = datetime.now(timezone.utc)
        
        # Generate mock trades
        trades, bid_price, ask_price = generate_mock_trades(current_price)
        
        # Detect aggressor
        aggressor = aggressor_detector.detect_aggressor(
            trades, bid_price, ask_price, symbol
        )
        
        # Save to repository
        try:
            repository.save_aggressor_analysis(aggressor)
        except Exception:
            pass
        
        return AggressorResponse(
            symbol=symbol,
            aggressor_side=aggressor.aggressor_side.value,
            aggressor_confidence=round(aggressor.aggressor_confidence, 3),
            aggressor_ratio=round(aggressor.aggressor_ratio, 4),
            buy_initiated_pct=round(aggressor.buy_initiated_pct, 4),
            sell_initiated_pct=round(aggressor.sell_initiated_pct, 4),
            aggressor_shift=aggressor.aggressor_shift,
            trade_count=aggressor.trade_count,
            computed_at=now.isoformat()
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/imbalance/{symbol}", response_model=ImbalanceResponse)
async def get_micro_imbalance(
    symbol: str,
    current_price: float = Query(64000.0, description="Current market price"),
    bias: str = Query("NEUTRAL", description="Book bias: BUY, SELL, NEUTRAL")
):
    """
    Get micro-imbalance analysis.
    
    Detects:
    - Short-lived bid/ask dominance
    - Liquidity vacuums
    - Top-of-book skew
    """
    try:
        now = datetime.now(timezone.utc)
        
        # Generate mock orderbook
        bids, asks = generate_mock_orderbook_levels(
            current_price, levels=20, bias=bias.upper()
        )
        
        # Detect imbalance
        imbalance = imbalance_engine.detect_imbalance(bids, asks, symbol)
        
        # Save to repository
        try:
            repository.save_micro_imbalance(imbalance)
        except Exception:
            pass
        
        return ImbalanceResponse(
            symbol=symbol,
            micro_imbalance_score=round(imbalance.micro_imbalance_score, 4),
            imbalance_type=imbalance.imbalance_type.value,
            dominant_micro_side=imbalance.dominant_micro_side,
            vacuum_risk=round(imbalance.vacuum_risk, 3),
            imbalance_strength=round(imbalance.imbalance_strength, 3),
            top_book_skew=round(imbalance.top_book_skew, 4),
            computed_at=now.isoformat()
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/timing/{symbol}", response_model=TimingResponse)
async def get_execution_timing(
    symbol: str,
    current_price: float = Query(64000.0, description="Current market price"),
    direction: str = Query("LONG", description="Intended direction: LONG or SHORT")
):
    """
    Get execution timing recommendation.
    
    Recommends:
    - Enter now / wait / partial / exit
    - Entry size percentage
    - Delay recommendation
    """
    try:
        now = datetime.now(timezone.utc)
        
        # Generate mock data
        trades, bid_price, ask_price = generate_mock_trades(current_price)
        bids, asks = generate_mock_orderbook_levels(current_price)
        
        # Get all analyses
        flow = flow_engine.analyze_flow(trades, bid_price, ask_price, symbol)
        aggressor = aggressor_detector.detect_aggressor(trades, bid_price, ask_price, symbol)
        imbalance = imbalance_engine.detect_imbalance(bids, asks, symbol)
        pressure = pressure_engine.analyze_pressure(
            flow, flow_engine.flow_history, 0, 0, symbol
        )
        
        # Calculate timing
        spread_bps = ((ask_price - bid_price) / current_price) * 10000
        timing = timing_engine.calculate_timing(
            flow, aggressor, imbalance, pressure,
            direction.upper(), spread_bps, symbol
        )
        
        # Save to repository
        try:
            repository.save_timing_signal(timing)
        except Exception:
            pass
        
        return TimingResponse(
            symbol=symbol,
            timing_signal=timing.timing_signal.value,
            timing_quality=round(timing.timing_quality, 3),
            urgency_score=round(timing.urgency_score, 3),
            execution_readiness=round(timing.execution_readiness, 3),
            entry_size_pct=round(timing.entry_size_pct, 1),
            delay_recommendation_ms=timing.delay_recommendation_ms,
            notes=timing.notes,
            computed_at=now.isoformat()
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/pressure/{symbol}", response_model=PressureResponse)
async def get_flow_pressure(
    symbol: str,
    current_price: float = Query(64000.0, description="Current market price")
):
    """
    Get flow pressure analysis.
    
    Detects:
    - Building pressure (buy/sell)
    - Exhaustion signals
    - Absorption patterns
    - Fake pushes
    """
    try:
        now = datetime.now(timezone.utc)
        
        # Generate mock trades and analyze flow
        trades, bid_price, ask_price = generate_mock_trades(current_price)
        flow = flow_engine.analyze_flow(trades, bid_price, ask_price, symbol)
        
        # Analyze pressure
        pressure = pressure_engine.analyze_pressure(
            flow, flow_engine.flow_history,
            price_change_pct=random.uniform(-0.5, 0.5),
            volume_change_pct=random.uniform(-0.3, 0.5),
            symbol=symbol
        )
        
        # Save to repository
        try:
            repository.save_flow_pressure(pressure)
        except Exception:
            pass
        
        return PressureResponse(
            symbol=symbol,
            flow_pressure_state=pressure.flow_pressure_state.value,
            pressure_direction=pressure.pressure_direction,
            pressure_strength=round(pressure.pressure_strength, 3),
            exhaustion_probability=round(pressure.exhaustion_probability, 3),
            exhaustion_type=pressure.exhaustion_type,
            building_detected=pressure.building_detected,
            absorption_score=round(pressure.absorption_score, 3),
            fake_push_probability=round(pressure.fake_push_probability, 3),
            computed_at=now.isoformat()
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history/{symbol}")
async def get_microstructure_history(
    symbol: str,
    hours_back: int = Query(1, description="Hours to look back"),
    limit: int = Query(50, description="Maximum records")
):
    """
    Get historical microstructure snapshots.
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


@router.get("/signals/{symbol}")
async def get_timing_signals(
    symbol: str,
    hours_back: int = Query(1, description="Hours to look back"),
    limit: int = Query(20, description="Maximum records")
):
    """
    Get historical timing signals.
    """
    try:
        signals = repository.get_timing_signals(symbol, hours_back, limit)
        
        # Get summary
        timing_summary = timing_engine.get_timing_summary()
        
        return {
            "symbol": symbol,
            "hours_back": hours_back,
            "count": len(signals),
            "signals": signals,
            "summary": timing_summary,
            "retrieved_at": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats")
async def get_microstructure_stats():
    """Get repository and engine statistics."""
    try:
        repo_stats = repository.get_stats()
        
        return {
            "repository": repo_stats,
            "engines": {
                "order_flow": "active",
                "aggressor_detector": "active",
                "micro_imbalance": "active",
                "execution_timing": "active",
                "flow_pressure": "active"
            },
            "config": DEFAULT_MICROSTRUCTURE_CONFIG,
            "summaries": {
                "flow_trend": flow_engine.get_flow_trend(),
                "aggressor_trend": aggressor_detector.get_aggressor_trend(),
                "imbalance_summary": imbalance_engine.get_imbalance_summary(),
                "timing_summary": timing_engine.get_timing_summary(),
                "pressure_summary": pressure_engine.get_pressure_summary()
            },
            "retrieved_at": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
