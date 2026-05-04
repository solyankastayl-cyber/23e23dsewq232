"""
Slippage Types
==============

Типы данных для Slippage Engine.
"""

from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime


class SlippageDirection(str, Enum):
    """Направление проскальзывания"""
    FAVORABLE = "FAVORABLE"      # Лучше ожидаемой цены
    UNFAVORABLE = "UNFAVORABLE"  # Хуже ожидаемой цены
    ZERO = "ZERO"                # Без проскальзывания


class FillQuality(str, Enum):
    """Качество заполнения"""
    EXCELLENT = "EXCELLENT"  # Полное заполнение, без fragmentation
    GOOD = "GOOD"            # Минимальная fragmentation
    FAIR = "FAIR"            # Умеренная fragmentation
    POOR = "POOR"            # Высокая fragmentation
    FAILED = "FAILED"        # Не исполнено


class LiquidityImpact(str, Enum):
    """Влияние на ликвидность"""
    NEGLIGIBLE = "NEGLIGIBLE"  # < 0.01%
    LOW = "LOW"                # 0.01-0.05%
    MODERATE = "MODERATE"      # 0.05-0.1%
    HIGH = "HIGH"              # 0.1-0.5%
    SEVERE = "SEVERE"          # > 0.5%


class ExecutionGrade(str, Enum):
    """Общая оценка исполнения"""
    A_PLUS = "A+"
    A = "A"
    B = "B"
    C = "C"
    D = "D"
    F = "F"


class SlippageResult(BaseModel):
    """Результат расчёта проскальзывания"""
    expected_price: float
    executed_price: float
    slippage_absolute: float = Field(description="Абсолютное проскальзывание в цене")
    slippage_bps: float = Field(description="Проскальзывание в базисных пунктах")
    slippage_percent: float = Field(description="Проскальзывание в процентах")
    direction: SlippageDirection
    side: str = Field(default="BUY", description="BUY или SELL")
    is_favorable: bool = False
    notes: str = ""


class LatencyMetrics(BaseModel):
    """Метрики латентности"""
    order_sent_ts: datetime
    exchange_ack_ts: Optional[datetime] = None
    first_fill_ts: Optional[datetime] = None
    last_fill_ts: Optional[datetime] = None
    
    submit_latency_ms: float = Field(default=0.0, description="Время до подтверждения биржи")
    execution_latency_ms: float = Field(default=0.0, description="Время от подтверждения до первого fill")
    total_latency_ms: float = Field(default=0.0, description="Общее время исполнения")
    fill_duration_ms: float = Field(default=0.0, description="Время между первым и последним fill")
    
    latency_grade: str = Field(default="NORMAL", description="FAST/NORMAL/SLOW/TIMEOUT")
    notes: str = ""


class FillAnalysis(BaseModel):
    """Анализ качества заполнения"""
    total_quantity: float
    filled_quantity: float
    fill_count: int = 1
    fills: List[Dict[str, Any]] = Field(default_factory=list, description="Детали fills")
    
    fill_rate: float = Field(default=1.0, ge=0.0, le=1.0, description="% заполнения")
    fill_quality: FillQuality = FillQuality.GOOD
    fragmentation_score: float = Field(default=0.0, ge=0.0, le=1.0, description="0=одно заполнение, 1=много мелких")
    consistency_score: float = Field(default=1.0, ge=0.0, le=1.0, description="Равномерность fills")
    
    average_fill_size: float = 0.0
    largest_fill: float = 0.0
    smallest_fill: float = 0.0
    
    notes: str = ""


class LiquidityImpactResult(BaseModel):
    """Результат анализа влияния на ликвидность"""
    order_size: float
    market_depth_estimate: float = Field(default=0.0, description="Оценка глубины рынка")
    size_vs_depth_ratio: float = Field(default=0.0, description="Размер ордера vs глубина")
    
    spread_before: float = Field(default=0.0, description="Спред до исполнения")
    spread_after: float = Field(default=0.0, description="Спред после исполнения")
    spread_impact: float = Field(default=0.0, description="Изменение спреда")
    
    price_before: float = 0.0
    price_after: float = 0.0
    market_move_percent: float = Field(default=0.0, description="% движения рынка")
    
    impact_level: LiquidityImpact = LiquidityImpact.LOW
    liquidity_score: float = Field(default=1.0, ge=0.0, le=1.0, description="1=отличная ликвидность")
    execution_efficiency: float = Field(default=1.0, ge=0.0, le=1.0)
    
    notes: str = ""


class ExecutionAnalysis(BaseModel):
    """Полный анализ исполнения"""
    order_id: str
    symbol: str
    exchange: str = "BINANCE"
    side: str = "BUY"
    
    # Компоненты
    slippage: SlippageResult
    latency: LatencyMetrics
    fill_analysis: FillAnalysis
    liquidity_impact: LiquidityImpactResult
    
    # Общая оценка
    execution_score: float = Field(default=0.5, ge=0.0, le=1.0)
    execution_grade: ExecutionGrade = ExecutionGrade.B
    
    # Контекст
    market_conditions: str = Field(default="NORMAL", description="NORMAL/VOLATILE/THIN")
    order_type: str = Field(default="MARKET", description="MARKET/LIMIT/STOP")
    
    # Рекомендации
    recommendations: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    
    computed_at: datetime = Field(default_factory=datetime.utcnow)


class ExecutionSnapshot(BaseModel):
    """Снимок для хранения"""
    id: str = ""
    order_id: str
    symbol: str
    exchange: str
    analysis: ExecutionAnalysis
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ExecutionHistoryQuery(BaseModel):
    """Запрос истории"""
    symbol: Optional[str] = None
    exchange: Optional[str] = None
    limit: int = Field(default=100, ge=1, le=1000)
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    min_grade: Optional[ExecutionGrade] = None
