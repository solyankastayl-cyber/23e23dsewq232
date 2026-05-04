"""
Slippage Engine API Routes
==========================

REST API для Slippage Engine.

Endpoints:
- POST /api/slippage/analyze - полный анализ исполнения
- GET /api/slippage/order/{order_id} - данные по ордеру
- GET /api/slippage/symbol/{symbol} - статистика по символу
- GET /api/slippage/exchange/{exchange} - статистика по бирже
- GET /api/slippage/history - история исполнения
- GET /api/slippage/stats - общая статистика
"""

import uuid
import random
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from .slippage_types import (
    SlippageResult,
    LatencyMetrics,
    FillAnalysis,
    LiquidityImpactResult,
    ExecutionAnalysis,
    ExecutionSnapshot,
    ExecutionHistoryQuery,
    ExecutionGrade,
    SlippageDirection,
    FillQuality,
    LiquidityImpact
)
from .slippage_calculator import SlippageCalculator
from .execution_latency_tracker import ExecutionLatencyTracker
from .fill_quality_analyzer import FillQualityAnalyzer
from .liquidity_impact_engine import LiquidityImpactEngine
from .slippage_repository import SlippageRepository


router = APIRouter(prefix="/api/slippage", tags=["Slippage Engine"])

# Initialize
slippage_calc = SlippageCalculator()
latency_tracker = ExecutionLatencyTracker()
fill_analyzer = FillQualityAnalyzer()
liquidity_engine = LiquidityImpactEngine()
repository = SlippageRepository()


# ============================================
# Request Models
# ============================================

class ExecutionAnalyzeRequest(BaseModel):
    """Запрос на анализ исполнения"""
    order_id: str = Field(default="", description="Order ID")
    symbol: str = Field(default="BTCUSDT")
    exchange: str = Field(default="BINANCE")
    side: str = Field(default="BUY", description="BUY or SELL")
    order_type: str = Field(default="MARKET")
    
    # Prices
    expected_price: float = Field(default=0.0)
    executed_price: float = Field(default=0.0)
    
    # Quantities
    total_quantity: float = Field(default=0.0)
    filled_quantity: float = Field(default=0.0)
    
    # Fills
    fills: List[Dict[str, Any]] = Field(default_factory=list)
    
    # Timestamps (ISO format strings)
    order_sent_time: Optional[str] = None
    exchange_ack_time: Optional[str] = None
    first_fill_time: Optional[str] = None
    last_fill_time: Optional[str] = None
    
    # Market data
    market_depth: float = Field(default=0.0)
    spread_before: float = Field(default=0.0)
    spread_after: float = Field(default=0.0)
    price_before: float = Field(default=0.0)
    price_after: float = Field(default=0.0)


class ExecutionResponse(BaseModel):
    """Ответ с анализом"""
    order_id: str
    symbol: str
    exchange: str
    side: str
    expected_price: float
    executed_price: float
    slippage_percent: float
    slippage_bps: float
    slippage_direction: str
    execution_latency_ms: float
    latency_grade: str
    fill_quality: str
    fill_rate: float
    liquidity_impact: str
    execution_score: float
    execution_grade: str
    recommendations: List[str]
    warnings: List[str]
    computed_at: str


class SlippageEstimateRequest(BaseModel):
    """Запрос оценки slippage"""
    symbol: str = "BTCUSDT"
    side: str = "BUY"
    quantity: float = 1.0
    current_price: float = 45000.0
    volatility: float = 0.02
    liquidity_factor: float = 0.8


# ============================================
# Helper Functions
# ============================================

def parse_datetime(dt_str: Optional[str]) -> Optional[datetime]:
    """Parse datetime from string"""
    if not dt_str:
        return None
    try:
        return datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
    except ValueError:
        return None


def generate_mock_execution(symbol: str, side: str = "BUY") -> ExecutionAnalyzeRequest:
    """Generate mock execution data"""
    base_price = 45000 if "BTC" in symbol else 2500 if "ETH" in symbol else 100
    
    slippage = random.uniform(-0.05, 0.15)  # -0.05% to 0.15%
    expected = base_price
    executed = base_price * (1 + slippage / 100)
    
    quantity = random.uniform(0.1, 2.0)
    
    now = datetime.utcnow()
    
    return ExecutionAnalyzeRequest(
        order_id=str(uuid.uuid4()),
        symbol=symbol,
        exchange=random.choice(["BINANCE", "BYBIT", "OKX"]),
        side=side,
        expected_price=expected,
        executed_price=executed,
        total_quantity=quantity,
        filled_quantity=quantity * random.uniform(0.95, 1.0),
        fills=[
            {"quantity": quantity * 0.4, "price": executed * 0.999},
            {"quantity": quantity * 0.35, "price": executed},
            {"quantity": quantity * 0.25, "price": executed * 1.001}
        ],
        order_sent_time=(now - timedelta(milliseconds=200)).isoformat(),
        exchange_ack_time=(now - timedelta(milliseconds=150)).isoformat(),
        first_fill_time=(now - timedelta(milliseconds=100)).isoformat(),
        last_fill_time=now.isoformat(),
        price_before=expected,
        price_after=executed
    )


def calculate_execution_score(
    slippage: SlippageResult,
    latency: LatencyMetrics,
    fill: FillAnalysis,
    liquidity: LiquidityImpactResult
) -> tuple:
    """Calculate overall execution score and grade"""
    score = 0.0
    
    # Slippage component (40%)
    slippage_score = 1.0
    if slippage.slippage_bps > 50:
        slippage_score = 0.2
    elif slippage.slippage_bps > 20:
        slippage_score = 0.5
    elif slippage.slippage_bps > 10:
        slippage_score = 0.7
    elif slippage.slippage_bps > 5:
        slippage_score = 0.85
    
    if slippage.is_favorable:
        slippage_score = min(1.0, slippage_score + 0.1)
    
    score += slippage_score * 0.4
    
    # Latency component (20%)
    latency_score = {"FAST": 1.0, "NORMAL": 0.8, "SLOW": 0.5, "TIMEOUT": 0.2}.get(
        latency.latency_grade, 0.5
    )
    score += latency_score * 0.2
    
    # Fill quality component (25%)
    fill_score = {
        FillQuality.EXCELLENT: 1.0,
        FillQuality.GOOD: 0.85,
        FillQuality.FAIR: 0.6,
        FillQuality.POOR: 0.3,
        FillQuality.FAILED: 0.0
    }.get(fill.fill_quality, 0.5)
    fill_score *= fill.fill_rate
    score += fill_score * 0.25
    
    # Liquidity impact component (15%)
    score += liquidity.execution_efficiency * 0.15
    
    # Determine grade
    if score >= 0.9:
        grade = ExecutionGrade.A_PLUS
    elif score >= 0.8:
        grade = ExecutionGrade.A
    elif score >= 0.65:
        grade = ExecutionGrade.B
    elif score >= 0.5:
        grade = ExecutionGrade.C
    elif score >= 0.35:
        grade = ExecutionGrade.D
    else:
        grade = ExecutionGrade.F
    
    return round(score, 4), grade


# ============================================
# API Endpoints
# ============================================

@router.get("/health")
async def slippage_health():
    return {
        "status": "healthy",
        "version": "phase_4.3",
        "components": ["slippage_calculator", "latency_tracker", "fill_analyzer", "liquidity_engine"],
        "timestamp": datetime.utcnow().isoformat()
    }


@router.get("/stats")
async def slippage_stats(
    symbol: Optional[str] = Query(default=None),
    exchange: Optional[str] = Query(default=None)
):
    """Статистика исполнения"""
    stats = repository.get_stats(symbol, exchange)
    
    return {
        "version": "phase_4.3",
        "filters": {"symbol": symbol, "exchange": exchange},
        "stats": stats
    }


@router.post("/analyze", response_model=ExecutionResponse)
async def analyze_execution(request: ExecutionAnalyzeRequest):
    """
    Полный анализ исполнения ордера.
    """
    # Generate mock if no data
    if request.expected_price <= 0:
        request = generate_mock_execution(request.symbol, request.side)
    
    order_id = request.order_id or str(uuid.uuid4())
    
    # Parse timestamps
    order_sent = parse_datetime(request.order_sent_time) or datetime.utcnow() - timedelta(milliseconds=200)
    exchange_ack = parse_datetime(request.exchange_ack_time)
    first_fill = parse_datetime(request.first_fill_time)
    last_fill = parse_datetime(request.last_fill_time)
    
    # 1. Calculate slippage
    if request.fills:
        slippage = slippage_calc.calculate_from_fills(
            request.expected_price, request.fills, request.side
        )
    else:
        slippage = slippage_calc.calculate(
            request.expected_price, request.executed_price, request.side
        )
    
    # 2. Track latency
    latency = latency_tracker.track(order_sent, exchange_ack, first_fill, last_fill)
    
    # 3. Analyze fills
    if request.fills:
        fill_analysis = fill_analyzer.analyze(request.total_quantity, request.fills)
    else:
        fill_analysis = fill_analyzer.analyze_partial(
            request.total_quantity, request.filled_quantity, 
            len(request.fills) if request.fills else 1
        )
    
    # 4. Analyze liquidity impact
    liquidity_impact = liquidity_engine.analyze(
        order_size=request.total_quantity,
        executed_price=request.executed_price,
        market_depth=request.market_depth,
        spread_before=request.spread_before,
        spread_after=request.spread_after,
        price_before=request.price_before,
        price_after=request.price_after,
        side=request.side
    )
    
    # 5. Calculate overall score
    score, grade = calculate_execution_score(slippage, latency, fill_analysis, liquidity_impact)
    
    # 6. Generate recommendations
    recommendations = []
    warnings = []
    
    if slippage.slippage_bps > 20:
        recommendations.append("Consider using limit orders to reduce slippage")
    if latency.latency_grade == "SLOW":
        recommendations.append("Check network connection or consider co-location")
    if fill_analysis.fragmentation_score > 0.5:
        recommendations.append("Consider TWAP execution for large orders")
    if liquidity_impact.impact_level in [LiquidityImpact.HIGH, LiquidityImpact.SEVERE]:
        recommendations.append("Split order into smaller chunks")
        warnings.append("High market impact detected")
    
    if not slippage.is_favorable and slippage.slippage_bps > 10:
        warnings.append(f"Unfavorable slippage: {slippage.slippage_bps:.2f} bps")
    
    # Build analysis
    analysis = ExecutionAnalysis(
        order_id=order_id,
        symbol=request.symbol,
        exchange=request.exchange,
        side=request.side,
        slippage=slippage,
        latency=latency,
        fill_analysis=fill_analysis,
        liquidity_impact=liquidity_impact,
        execution_score=score,
        execution_grade=grade,
        market_conditions="NORMAL",
        order_type=request.order_type,
        recommendations=recommendations,
        warnings=warnings
    )
    
    # Save
    snapshot = ExecutionSnapshot(
        id=str(uuid.uuid4()),
        order_id=order_id,
        symbol=request.symbol,
        exchange=request.exchange,
        analysis=analysis,
        created_at=datetime.utcnow()
    )
    
    try:
        repository.save(snapshot)
    except Exception as e:
        print(f"[Slippage] Failed to save: {e}")
    
    return ExecutionResponse(
        order_id=order_id,
        symbol=request.symbol,
        exchange=request.exchange,
        side=request.side,
        expected_price=slippage.expected_price,
        executed_price=slippage.executed_price,
        slippage_percent=slippage.slippage_percent,
        slippage_bps=slippage.slippage_bps,
        slippage_direction=slippage.direction.value,
        execution_latency_ms=latency.total_latency_ms,
        latency_grade=latency.latency_grade,
        fill_quality=fill_analysis.fill_quality.value,
        fill_rate=fill_analysis.fill_rate,
        liquidity_impact=liquidity_impact.impact_level.value,
        execution_score=score,
        execution_grade=grade.value,
        recommendations=recommendations,
        warnings=warnings,
        computed_at=datetime.utcnow().isoformat()
    )


@router.get("/order/{order_id}")
async def get_order_analysis(order_id: str):
    """Получить анализ по order_id"""
    data = repository.get_by_order_id(order_id)
    if not data:
        raise HTTPException(status_code=404, detail=f"Order {order_id} not found")
    return data


@router.get("/symbol/{symbol}")
async def get_symbol_stats(
    symbol: str,
    limit: int = Query(default=50, ge=1, le=200)
):
    """Статистика по символу"""
    history = repository.get_by_symbol(symbol, limit)
    stats = repository.get_stats(symbol=symbol)
    
    return {
        "symbol": symbol,
        "stats": stats,
        "recent_count": len(history),
        "recent": history[:10]
    }


@router.get("/exchange/{exchange}")
async def get_exchange_stats(
    exchange: str,
    limit: int = Query(default=50, ge=1, le=200)
):
    """Статистика по бирже"""
    history = repository.get_by_exchange(exchange, limit)
    stats = repository.get_stats(exchange=exchange)
    
    return {
        "exchange": exchange,
        "stats": stats,
        "recent_count": len(history),
        "recent": history[:10]
    }


@router.get("/exchange-comparison")
async def compare_exchanges():
    """Сравнение бирж"""
    comparison = repository.get_exchange_comparison()
    return {
        "comparison": comparison,
        "timestamp": datetime.utcnow().isoformat()
    }


@router.get("/history")
async def get_history(
    symbol: Optional[str] = Query(default=None),
    exchange: Optional[str] = Query(default=None),
    min_grade: Optional[str] = Query(default=None),
    limit: int = Query(default=100, ge=1, le=1000)
):
    """История исполнения"""
    query = ExecutionHistoryQuery(
        symbol=symbol,
        exchange=exchange,
        limit=limit
    )
    
    if min_grade:
        try:
            query.min_grade = ExecutionGrade(min_grade)
        except ValueError:
            pass
    
    history = repository.get_history(query)
    
    return {
        "filters": {"symbol": symbol, "exchange": exchange, "min_grade": min_grade},
        "count": len(history),
        "history": history
    }


@router.post("/estimate")
async def estimate_slippage(request: SlippageEstimateRequest):
    """Оценить slippage до исполнения"""
    estimate = slippage_calc.estimate_slippage(
        symbol=request.symbol,
        side=request.side,
        quantity=request.quantity,
        current_price=request.current_price,
        volatility=request.volatility,
        liquidity_factor=request.liquidity_factor
    )
    
    # Also estimate impact
    impact_estimate = liquidity_engine.estimate_impact(
        order_size=request.quantity,
        current_price=request.current_price,
        volatility=request.volatility
    )
    
    return {
        "slippage_estimate": estimate,
        "impact_estimate": impact_estimate,
        "timestamp": datetime.utcnow().isoformat()
    }


# ============================================
# Batch
# ============================================

class BatchAnalyzeRequest(BaseModel):
    """Batch запрос"""
    orders: List[ExecutionAnalyzeRequest] = Field(default_factory=list)


@router.post("/batch")
async def batch_analyze(request: BatchAnalyzeRequest):
    """Batch анализ"""
    results = []
    
    for order in request.orders[:20]:  # Limit 20
        if order.expected_price <= 0:
            order = generate_mock_execution(order.symbol, order.side)
        
        response = await analyze_execution(order)
        results.append({
            "order_id": response.order_id,
            "symbol": response.symbol,
            "slippage_bps": response.slippage_bps,
            "execution_score": response.execution_score,
            "execution_grade": response.execution_grade
        })
    
    return {
        "count": len(results),
        "results": results,
        "timestamp": datetime.utcnow().isoformat()
    }
