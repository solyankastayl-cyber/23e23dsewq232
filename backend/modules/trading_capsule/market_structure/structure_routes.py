"""
Market Structure API Routes
===========================

REST API endpoints для Market Structure Engine.

Endpoints:
- POST /api/market-structure/analyze - полный анализ структуры
- GET /api/market-structure/symbol/{symbol} - структура по символу
- GET /api/market-structure/liquidity - зоны ликвидности
- GET /api/market-structure/imbalances - зоны дисбаланса
- GET /api/market-structure/history - история структуры
"""

import uuid
import random
from typing import Dict, List, Any, Optional
from datetime import datetime
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from .structure_types import (
    TrendStructure,
    StructureEventType,
    LiquidityZoneType,
    ImbalanceType,
    SRType,
    MarketStructureResult,
    StructureSnapshot,
    StructureHistoryQuery
)
from .structure_detector import StructureDetector
from .liquidity_detector import LiquidityDetector
from .imbalance_detector import ImbalanceDetector
from .support_resistance_engine import SupportResistanceEngine
from .structure_repository import StructureRepository


router = APIRouter(prefix="/api/market-structure", tags=["Market Structure"])

# Initialize components
structure_detector = StructureDetector()
liquidity_detector = LiquidityDetector()
imbalance_detector = ImbalanceDetector()
sr_engine = SupportResistanceEngine()
repository = StructureRepository()


# ============================================
# Request/Response Models
# ============================================

class StructureAnalyzeRequest(BaseModel):
    """Запрос на анализ структуры"""
    symbol: str = Field(..., description="Trading symbol")
    timeframe: str = Field(default="1h", description="Timeframe")
    opens: List[float] = Field(default_factory=list)
    highs: List[float] = Field(default_factory=list)
    lows: List[float] = Field(default_factory=list)
    closes: List[float] = Field(default_factory=list)
    current_price: float = Field(default=0.0)


class StructureResponse(BaseModel):
    """Ответ с результатом анализа"""
    symbol: str
    timeframe: str
    trend_structure: str
    structure_confidence: float
    bos_count: int
    choch_count: int
    active_liquidity_zones: int
    active_imbalances: int
    nearest_support: Optional[float]
    nearest_resistance: Optional[float]
    structure_bias: str
    key_levels: List[float]
    notes: List[str]
    computed_at: str


# ============================================
# Mock Data Generator
# ============================================

def generate_mock_ohlc(symbol: str = "BTCUSDT", count: int = 100) -> Dict[str, Any]:
    """Generate mock OHLC data"""
    base_price = 45000 if "BTC" in symbol else 2500 if "ETH" in symbol else 100
    
    opens = []
    highs = []
    lows = []
    closes = []
    
    price = base_price
    for i in range(count):
        o = price
        change = random.uniform(-0.02, 0.02)
        c = price * (1 + change)
        h = max(o, c) * (1 + random.uniform(0, 0.01))
        l = min(o, c) * (1 - random.uniform(0, 0.01))
        
        opens.append(o)
        highs.append(h)
        lows.append(l)
        closes.append(c)
        
        price = c
    
    return {
        "opens": opens,
        "highs": highs,
        "lows": lows,
        "closes": closes,
        "current_price": closes[-1]
    }


# ============================================
# API Endpoints
# ============================================

@router.get("/health")
async def structure_health():
    """Health check"""
    return {
        "status": "healthy",
        "version": "phase_3.5.3",
        "components": ["structure_detector", "liquidity_detector", "imbalance_detector", "sr_engine"],
        "timestamp": datetime.utcnow().isoformat()
    }


@router.get("/stats")
async def structure_stats():
    """Статистика"""
    repo_stats = repository.get_stats()
    
    return {
        "engine_version": "phase_3.5.3",
        "repository": repo_stats
    }


@router.post("/analyze", response_model=StructureResponse)
async def analyze_structure(request: StructureAnalyzeRequest):
    """
    Полный анализ структуры рынка.
    
    Включает:
    - BOS/CHOCH детекцию
    - Liquidity zones
    - Imbalances (FVG, Order Blocks)
    - Support/Resistance clusters
    """
    # Use provided data or generate mock
    if request.highs and len(request.highs) >= 30:
        opens = request.opens or request.closes
        highs = request.highs
        lows = request.lows
        closes = request.closes
        current_price = request.current_price or closes[-1]
    else:
        mock = generate_mock_ohlc(request.symbol)
        opens = mock["opens"]
        highs = mock["highs"]
        lows = mock["lows"]
        closes = mock["closes"]
        current_price = mock["current_price"]
    
    # Detect structure
    structure_result = structure_detector.detect(highs, lows, closes)
    
    # Extract swing points for other detectors
    swing_highs = [(e.candle_index, e.price) for e in structure_result["swing_points"] 
                   if e.event_type == StructureEventType.SWING_HIGH]
    swing_lows = [(e.candle_index, e.price) for e in structure_result["swing_points"] 
                  if e.event_type == StructureEventType.SWING_LOW]
    
    # Detect liquidity
    liquidity_result = liquidity_detector.detect(
        highs, lows, closes, swing_highs, swing_lows
    )
    
    # Detect imbalances
    imbalance_result = imbalance_detector.detect(opens, highs, lows, closes)
    
    # Analyze S/R
    sr_result = sr_engine.analyze(
        highs, lows, closes, current_price,
        swing_highs, swing_lows,
        liquidity_result["liquidity_zones"],
        imbalance_result["imbalances"]
    )
    
    # Build full result
    trend = structure_result["trend_structure"]
    
    # Determine bias
    if trend == TrendStructure.BULLISH:
        bias = "BULLISH"
    elif trend == TrendStructure.BEARISH:
        bias = "BEARISH"
    else:
        bias = "NEUTRAL"
    
    # Generate notes
    notes = []
    if structure_result["bos_count"] > 0:
        notes.append(f"{structure_result['bos_count']} BOS events detected")
    if structure_result["choch_count"] > 0:
        notes.append(f"{structure_result['choch_count']} CHOCH events - potential trend change")
    if liquidity_result["liquidity_sweeps"]:
        notes.append(f"{len(liquidity_result['liquidity_sweeps'])} liquidity sweeps detected")
    if imbalance_result["active_imbalances"] > 0:
        notes.append(f"{imbalance_result['active_imbalances']} active imbalance zones")
    
    # Warnings
    warnings = []
    if trend == TrendStructure.TRANSITIONING:
        warnings.append("Structure transitioning - exercise caution")
    
    result = MarketStructureResult(
        symbol=request.symbol,
        timeframe=request.timeframe,
        trend_structure=trend,
        structure_confidence=structure_result["structure_confidence"],
        bos_events=structure_result["bos_events"],
        choch_events=structure_result["choch_events"],
        swing_points=structure_result["swing_points"],
        liquidity_zones=liquidity_result["liquidity_zones"],
        liquidity_sweeps=liquidity_result["liquidity_sweeps"],
        imbalances=imbalance_result["imbalances"],
        support_clusters=sr_result["support_clusters"],
        resistance_clusters=sr_result["resistance_clusters"],
        bos_count=structure_result["bos_count"],
        choch_count=structure_result["choch_count"],
        active_liquidity_zones=liquidity_result["active_zones"],
        active_imbalances=imbalance_result["active_imbalances"],
        current_price=current_price,
        nearest_support=sr_result["nearest_support"],
        nearest_resistance=sr_result["nearest_resistance"],
        structure_bias=bias,
        key_levels=sr_result["key_levels"],
        notes=notes,
        warnings=warnings
    )
    
    # Save snapshot
    snapshot = StructureSnapshot(
        id=str(uuid.uuid4()),
        symbol=request.symbol,
        timeframe=request.timeframe,
        result=result,
        market_price=current_price,
        created_at=datetime.utcnow()
    )
    
    try:
        repository.save_snapshot(snapshot)
    except Exception as e:
        print(f"[Structure] Failed to save snapshot: {e}")
    
    return StructureResponse(
        symbol=result.symbol,
        timeframe=result.timeframe,
        trend_structure=result.trend_structure.value,
        structure_confidence=result.structure_confidence,
        bos_count=result.bos_count,
        choch_count=result.choch_count,
        active_liquidity_zones=result.active_liquidity_zones,
        active_imbalances=result.active_imbalances,
        nearest_support=result.nearest_support,
        nearest_resistance=result.nearest_resistance,
        structure_bias=result.structure_bias,
        key_levels=result.key_levels,
        notes=result.notes,
        computed_at=result.computed_at.isoformat()
    )


@router.get("/symbol/{symbol}")
async def get_structure_for_symbol(
    symbol: str,
    timeframe: str = Query(default="1h"),
    fresh: bool = Query(default=False)
):
    """Получение структуры для символа"""
    
    if not fresh:
        snapshot = repository.get_snapshot(symbol, timeframe)
        if snapshot:
            result = snapshot.get("result", {})
            return {
                "symbol": symbol,
                "timeframe": timeframe,
                "cached": True,
                "trend_structure": result.get("trend_structure", "NEUTRAL"),
                "structure_confidence": result.get("structure_confidence", 0),
                "bos_count": result.get("bos_count", 0),
                "choch_count": result.get("choch_count", 0),
                "structure_bias": result.get("structure_bias", "NEUTRAL"),
                "key_levels": result.get("key_levels", []),
                "created_at": snapshot.get("created_at")
            }
    
    # Generate fresh
    mock = generate_mock_ohlc(symbol)
    request = StructureAnalyzeRequest(
        symbol=symbol,
        timeframe=timeframe,
        opens=mock["opens"],
        highs=mock["highs"],
        lows=mock["lows"],
        closes=mock["closes"],
        current_price=mock["current_price"]
    )
    
    response = await analyze_structure(request)
    
    return {
        "symbol": symbol,
        "timeframe": timeframe,
        "cached": False,
        "trend_structure": response.trend_structure,
        "structure_confidence": response.structure_confidence,
        "bos_count": response.bos_count,
        "choch_count": response.choch_count,
        "structure_bias": response.structure_bias,
        "key_levels": response.key_levels,
        "notes": response.notes
    }


@router.get("/liquidity")
async def get_liquidity_zones(
    symbol: str = Query(default="BTCUSDT"),
    timeframe: str = Query(default="1h")
):
    """Получение зон ликвидности"""
    mock = generate_mock_ohlc(symbol)
    
    # Get swing points first
    structure_result = structure_detector.detect(
        mock["highs"], mock["lows"], mock["closes"]
    )
    
    swing_highs = [(e.candle_index, e.price) for e in structure_result["swing_points"] 
                   if e.event_type == StructureEventType.SWING_HIGH]
    swing_lows = [(e.candle_index, e.price) for e in structure_result["swing_points"] 
                  if e.event_type == StructureEventType.SWING_LOW]
    
    # Detect liquidity
    result = liquidity_detector.detect(
        mock["highs"], mock["lows"], mock["closes"],
        swing_highs, swing_lows
    )
    
    return {
        "symbol": symbol,
        "timeframe": timeframe,
        "liquidity_zones": [
            {
                "zone_type": z.zone_type.value,
                "price_level": z.price_level,
                "price_low": z.price_low,
                "price_high": z.price_high,
                "strength": z.strength,
                "touch_count": z.touch_count,
                "swept": z.swept,
                "notes": z.notes
            }
            for z in result["liquidity_zones"]
        ],
        "liquidity_sweeps": [
            {
                "direction": s.direction,
                "sweep_price": s.sweep_price,
                "return_price": s.return_price,
                "zone_swept": s.zone_swept.value,
                "strength": s.strength,
                "reversal_confirmed": s.reversal_confirmed
            }
            for s in result["liquidity_sweeps"]
        ],
        "active_zones": result["active_zones"]
    }


@router.get("/imbalances")
async def get_imbalances(
    symbol: str = Query(default="BTCUSDT"),
    timeframe: str = Query(default="1h")
):
    """Получение зон дисбаланса"""
    mock = generate_mock_ohlc(symbol)
    
    result = imbalance_detector.detect(
        mock["opens"], mock["highs"], mock["lows"], mock["closes"]
    )
    
    return {
        "symbol": symbol,
        "timeframe": timeframe,
        "imbalances": [
            {
                "type": i.imbalance_type.value,
                "high": i.high,
                "low": i.low,
                "midpoint": i.midpoint,
                "strength": i.strength,
                "filled_pct": i.filled_pct,
                "active": i.active,
                "notes": i.notes
            }
            for i in result["imbalances"]
        ],
        "active_imbalances": result["active_imbalances"]
    }


@router.get("/support-resistance")
async def get_support_resistance(
    symbol: str = Query(default="BTCUSDT"),
    timeframe: str = Query(default="1h")
):
    """Получение S/R кластеров"""
    mock = generate_mock_ohlc(symbol)
    current_price = mock["current_price"]
    
    # Get swing points
    structure_result = structure_detector.detect(
        mock["highs"], mock["lows"], mock["closes"]
    )
    
    swing_highs = [(e.candle_index, e.price) for e in structure_result["swing_points"] 
                   if e.event_type == StructureEventType.SWING_HIGH]
    swing_lows = [(e.candle_index, e.price) for e in structure_result["swing_points"] 
                  if e.event_type == StructureEventType.SWING_LOW]
    
    result = sr_engine.analyze(
        mock["highs"], mock["lows"], mock["closes"],
        current_price, swing_highs, swing_lows
    )
    
    return {
        "symbol": symbol,
        "timeframe": timeframe,
        "current_price": current_price,
        "support_clusters": [
            {
                "price_center": c.price_center,
                "price_low": c.price_low,
                "price_high": c.price_high,
                "strength": c.strength,
                "sources": c.sources,
                "source_count": c.source_count
            }
            for c in result["support_clusters"]
        ],
        "resistance_clusters": [
            {
                "price_center": c.price_center,
                "price_low": c.price_low,
                "price_high": c.price_high,
                "strength": c.strength,
                "sources": c.sources,
                "source_count": c.source_count
            }
            for c in result["resistance_clusters"]
        ],
        "nearest_support": result["nearest_support"],
        "nearest_resistance": result["nearest_resistance"],
        "key_levels": result["key_levels"]
    }


@router.get("/history")
async def get_structure_history(
    symbol: str = Query(default="BTCUSDT"),
    timeframe: str = Query(default="1h"),
    structure_type: Optional[str] = Query(default=None),
    limit: int = Query(default=100, ge=1, le=1000)
):
    """Получение истории структуры"""
    query = StructureHistoryQuery(
        symbol=symbol,
        timeframe=timeframe,
        limit=limit
    )
    
    if structure_type:
        try:
            query.structure_type = TrendStructure(structure_type)
        except ValueError:
            pass
    
    history = repository.get_history(query)
    
    return {
        "symbol": symbol,
        "timeframe": timeframe,
        "count": len(history),
        "history": history
    }


# ============================================
# Batch Operations
# ============================================

class BatchStructureRequest(BaseModel):
    """Batch запрос"""
    symbols: List[str] = Field(default=["BTCUSDT", "ETHUSDT"])
    timeframe: str = Field(default="1h")


@router.post("/batch")
async def batch_analyze(request: BatchStructureRequest):
    """Batch анализ структуры"""
    results = []
    
    for symbol in request.symbols[:10]:
        mock = generate_mock_ohlc(symbol)
        
        structure_result = structure_detector.detect(
            mock["highs"], mock["lows"], mock["closes"]
        )
        
        trend = structure_result["trend_structure"]
        
        results.append({
            "symbol": symbol,
            "trend_structure": trend.value,
            "structure_confidence": structure_result["structure_confidence"],
            "bos_count": structure_result["bos_count"],
            "choch_count": structure_result["choch_count"],
            "bias": "BULLISH" if trend == TrendStructure.BULLISH else "BEARISH" if trend == TrendStructure.BEARISH else "NEUTRAL"
        })
    
    return {
        "timeframe": request.timeframe,
        "count": len(results),
        "results": results,
        "computed_at": datetime.utcnow().isoformat()
    }
