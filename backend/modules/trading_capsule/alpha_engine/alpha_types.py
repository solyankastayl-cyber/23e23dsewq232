"""
Alpha Engine Types
==================

Типы данных для Alpha Engine.
"""

from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime


class AlphaDirection(str, Enum):
    """Направление alpha-сигнала"""
    LONG = "LONG"
    SHORT = "SHORT"
    NEUTRAL = "NEUTRAL"


class AlphaRegimeRelevance(str, Enum):
    """Релевантность alpha в текущем режиме"""
    TRENDING = "TRENDING"
    RANGING = "RANGING"
    VOLATILE = "VOLATILE"
    COMPRESSION = "COMPRESSION"
    EXPANSION = "EXPANSION"
    ALL = "ALL"


class AlphaResult(BaseModel):
    """Результат расчёта одного alpha-фактора"""
    alpha_id: str = Field(..., description="ID alpha-фактора")
    alpha_name: str = Field(..., description="Название alpha")
    direction: AlphaDirection = Field(..., description="Направление сигнала")
    strength: float = Field(..., ge=0.0, le=1.0, description="Сила сигнала 0-1")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Уверенность 0-1")
    regime_relevance: AlphaRegimeRelevance = Field(..., description="Релевантность режиму")
    raw_value: float = Field(default=0.0, description="Сырое значение индикатора")
    normalized_value: float = Field(default=0.0, description="Нормализованное значение -1 до 1")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Дополнительные данные")
    computed_at: datetime = Field(default_factory=datetime.utcnow)


class AlphaSummary(BaseModel):
    """Агрегированный результат всех alpha-факторов"""
    symbol: str = Field(..., description="Торговый символ")
    timeframe: str = Field(default="1h", description="Таймфрейм")
    
    # Агрегированные метрики
    alpha_bias: AlphaDirection = Field(..., description="Итоговое направление")
    alpha_confidence: float = Field(..., ge=0.0, le=1.0, description="Итоговая уверенность")
    alpha_strength: float = Field(..., ge=0.0, le=1.0, description="Итоговая сила")
    
    # Отдельные компоненты (нормализованные 0-1)
    trend_strength: float = Field(default=0.0, ge=0.0, le=1.0)
    trend_acceleration: float = Field(default=0.0, ge=0.0, le=1.0)
    trend_exhaustion: float = Field(default=0.0, ge=0.0, le=1.0)
    breakout_pressure: float = Field(default=0.0, ge=0.0, le=1.0)
    volatility_compression: float = Field(default=0.0, ge=0.0, le=1.0)
    volatility_expansion: float = Field(default=0.0, ge=0.0, le=1.0)
    reversal_pressure: float = Field(default=0.0, ge=0.0, le=1.0)
    volume_confirmation: float = Field(default=0.0, ge=0.0, le=1.0)
    volume_anomaly: float = Field(default=0.0, ge=0.0, le=1.0)
    liquidity_sweep: float = Field(default=0.0, ge=0.0, le=1.0)
    
    # Статистика
    alphas_count: int = Field(default=0, description="Количество alpha в расчёте")
    long_signals: int = Field(default=0, description="Количество LONG сигналов")
    short_signals: int = Field(default=0, description="Количество SHORT сигналов")
    neutral_signals: int = Field(default=0, description="Количество NEUTRAL сигналов")
    
    # Детали
    alpha_results: List[AlphaResult] = Field(default_factory=list, description="Результаты по каждому alpha")
    notes: List[str] = Field(default_factory=list, description="Комментарии")
    
    computed_at: datetime = Field(default_factory=datetime.utcnow)


class AlphaSnapshot(BaseModel):
    """Снимок alpha состояния для хранения"""
    id: str = Field(default="", description="Уникальный ID снимка")
    symbol: str
    timeframe: str = "1h"
    summary: AlphaSummary
    market_price: float = Field(default=0.0, description="Цена на момент расчёта")
    regime: str = Field(default="UNKNOWN", description="Текущий режим рынка")
    created_at: datetime = Field(default_factory=datetime.utcnow)


class AlphaHistoryQuery(BaseModel):
    """Запрос истории alpha"""
    symbol: str
    timeframe: str = "1h"
    limit: int = Field(default=100, ge=1, le=1000)
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    alpha_id: Optional[str] = None


class AlphaConfig(BaseModel):
    """Конфигурация Alpha Engine"""
    enabled: bool = True
    version: str = "phase_3.5.1"
    
    # Веса для агрегации
    weights: Dict[str, float] = Field(default_factory=lambda: {
        "trend_strength_alpha": 1.2,
        "trend_acceleration_alpha": 1.0,
        "trend_exhaustion_alpha": 0.8,
        "breakout_pressure_alpha": 1.3,
        "volatility_compression_alpha": 0.9,
        "volatility_expansion_alpha": 0.9,
        "reversal_pressure_alpha": 1.1,
        "volume_confirmation_alpha": 1.0,
        "volume_anomaly_alpha": 0.7,
        "liquidity_sweep_alpha": 0.8
    })
    
    # Пороги
    thresholds: Dict[str, float] = Field(default_factory=lambda: {
        "min_confidence": 0.3,
        "strong_signal": 0.7,
        "weak_signal": 0.4
    })
