"""
Market Structure Types
======================

Типы данных для Market Structure Engine.
"""

from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime


class TrendStructure(str, Enum):
    """Структура тренда"""
    BULLISH = "BULLISH"
    BEARISH = "BEARISH"
    NEUTRAL = "NEUTRAL"
    TRANSITIONING = "TRANSITIONING"


class StructureEventType(str, Enum):
    """Тип структурного события"""
    BOS_BULLISH = "BOS_BULLISH"      # Break of Structure вверх
    BOS_BEARISH = "BOS_BEARISH"      # Break of Structure вниз
    CHOCH_BULLISH = "CHOCH_BULLISH"  # Change of Character на бычий
    CHOCH_BEARISH = "CHOCH_BEARISH"  # Change of Character на медвежий
    SWING_HIGH = "SWING_HIGH"        # Свинг хай
    SWING_LOW = "SWING_LOW"          # Свинг лоу


class StructureEvent(BaseModel):
    """Структурное событие (BOS/CHOCH)"""
    event_type: StructureEventType
    price: float
    timestamp: datetime
    candle_index: int = 0
    strength: float = Field(default=0.5, ge=0.0, le=1.0, description="Сила события")
    confirmed: bool = True
    previous_swing: Optional[float] = None
    notes: str = ""


class LiquidityZoneType(str, Enum):
    """Тип зоны ликвидности"""
    EQUAL_HIGHS = "EQUAL_HIGHS"
    EQUAL_LOWS = "EQUAL_LOWS"
    RANGE_HIGH = "RANGE_HIGH"
    RANGE_LOW = "RANGE_LOW"
    STOP_HUNT_HIGH = "STOP_HUNT_HIGH"
    STOP_HUNT_LOW = "STOP_HUNT_LOW"


class LiquidityZone(BaseModel):
    """Зона ликвидности"""
    zone_type: LiquidityZoneType
    price_level: float
    price_low: float = 0.0
    price_high: float = 0.0
    strength: float = Field(default=0.5, ge=0.0, le=1.0)
    touch_count: int = 1
    last_touched: Optional[datetime] = None
    swept: bool = False
    notes: str = ""


class LiquiditySweep(BaseModel):
    """Sweep ликвидности"""
    direction: str = Field(description="UP или DOWN")
    sweep_price: float
    return_price: float
    zone_swept: LiquidityZoneType
    strength: float = Field(default=0.6, ge=0.0, le=1.0)
    timestamp: datetime
    candle_index: int = 0
    reversal_confirmed: bool = False
    notes: str = ""


class ImbalanceType(str, Enum):
    """Тип дисбаланса"""
    BULLISH_FVG = "BULLISH_FVG"  # Fair Value Gap вверх
    BEARISH_FVG = "BEARISH_FVG"  # Fair Value Gap вниз
    BULLISH_OB = "BULLISH_OB"    # Order Block бычий
    BEARISH_OB = "BEARISH_OB"    # Order Block медвежий


class Imbalance(BaseModel):
    """Зона дисбаланса / FVG"""
    imbalance_type: ImbalanceType
    high: float
    low: float
    midpoint: float = 0.0
    strength: float = Field(default=0.5, ge=0.0, le=1.0)
    filled_pct: float = Field(default=0.0, ge=0.0, le=100.0, description="% заполнения")
    timestamp: datetime
    candle_index: int = 0
    active: bool = True
    notes: str = ""


class SRType(str, Enum):
    """Тип поддержки/сопротивления"""
    SUPPORT = "SUPPORT"
    RESISTANCE = "RESISTANCE"
    PIVOT = "PIVOT"


class SRCluster(BaseModel):
    """Кластер поддержки/сопротивления"""
    sr_type: SRType
    price_center: float
    price_low: float
    price_high: float
    strength: float = Field(default=0.5, ge=0.0, le=1.0)
    touch_count: int = 1
    source_count: int = 1  # Сколько источников формируют кластер
    sources: List[str] = Field(default_factory=list, description="Источники: swing, fib, round, volume")
    last_tested: Optional[datetime] = None
    broken: bool = False
    notes: str = ""


class MarketStructureResult(BaseModel):
    """Полный результат анализа структуры"""
    symbol: str
    timeframe: str = "1h"
    
    # Общая структура
    trend_structure: TrendStructure
    structure_confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    
    # События
    bos_events: List[StructureEvent] = Field(default_factory=list)
    choch_events: List[StructureEvent] = Field(default_factory=list)
    swing_points: List[StructureEvent] = Field(default_factory=list)
    
    # Ликвидность
    liquidity_zones: List[LiquidityZone] = Field(default_factory=list)
    liquidity_sweeps: List[LiquiditySweep] = Field(default_factory=list)
    
    # Дисбалансы
    imbalances: List[Imbalance] = Field(default_factory=list)
    
    # Support/Resistance
    support_clusters: List[SRCluster] = Field(default_factory=list)
    resistance_clusters: List[SRCluster] = Field(default_factory=list)
    
    # Статистика
    bos_count: int = 0
    choch_count: int = 0
    active_liquidity_zones: int = 0
    active_imbalances: int = 0
    
    # Контекст
    current_price: float = 0.0
    nearest_support: Optional[float] = None
    nearest_resistance: Optional[float] = None
    
    # Рекомендации
    structure_bias: str = Field(default="NEUTRAL", description="BULLISH/BEARISH/NEUTRAL")
    key_levels: List[float] = Field(default_factory=list)
    notes: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    
    computed_at: datetime = Field(default_factory=datetime.utcnow)


class StructureSnapshot(BaseModel):
    """Снимок структуры для хранения"""
    id: str = ""
    symbol: str
    timeframe: str = "1h"
    result: MarketStructureResult
    market_price: float = 0.0
    created_at: datetime = Field(default_factory=datetime.utcnow)


class StructureHistoryQuery(BaseModel):
    """Запрос истории структуры"""
    symbol: str
    timeframe: str = "1h"
    limit: int = Field(default=100, ge=1, le=1000)
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    structure_type: Optional[TrendStructure] = None
