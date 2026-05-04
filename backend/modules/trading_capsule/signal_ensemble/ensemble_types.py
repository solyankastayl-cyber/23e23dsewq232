"""
Ensemble Types
==============

Типы данных для Signal Ensemble Engine.
"""

from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime


class SignalDirection(str, Enum):
    """Направление финального сигнала"""
    LONG = "LONG"
    SHORT = "SHORT"
    NEUTRAL = "NEUTRAL"


class SignalQuality(str, Enum):
    """Качество сигнала"""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    PREMIUM = "PREMIUM"


class AlphaContribution(BaseModel):
    """Вклад отдельного alpha в финальный сигнал"""
    alpha_id: str
    alpha_name: str
    direction: str
    raw_strength: float = Field(ge=0.0, le=1.0)
    raw_confidence: float = Field(ge=0.0, le=1.0)
    weight: float = Field(ge=0.0, le=3.0)
    weighted_score: float
    contribution_pct: float = Field(ge=0.0, le=100.0, description="% вклада в финальный сигнал")
    regime_aligned: bool = True
    in_conflict: bool = False


class ConflictReport(BaseModel):
    """Отчёт о конфликтах сигналов"""
    has_conflict: bool = False
    conflict_severity: float = Field(default=0.0, ge=0.0, le=1.0, description="0=нет, 1=критический")
    conflicting_alphas: List[Dict[str, Any]] = Field(default_factory=list)
    resolution_action: str = Field(default="NONE", description="NONE/REDUCE_CONFIDENCE/NEUTRAL/SPLIT")
    confidence_penalty: float = Field(default=0.0, ge=0.0, le=1.0)
    notes: List[str] = Field(default_factory=list)


class EnsembleSignal(BaseModel):
    """Единичный ensemble сигнал"""
    direction: SignalDirection
    strength: float = Field(ge=0.0, le=1.0, description="Сила сигнала 0-1")
    confidence: float = Field(ge=0.0, le=1.0, description="Уверенность 0-1")
    quality: SignalQuality
    
    # Scores по направлениям
    long_score: float = Field(default=0.0, ge=0.0)
    short_score: float = Field(default=0.0, ge=0.0)
    neutral_score: float = Field(default=0.0, ge=0.0)
    
    # Метаданные
    dominant_alpha: str = Field(default="", description="Alpha с наибольшим вкладом")
    supporting_alphas: List[str] = Field(default_factory=list)
    opposing_alphas: List[str] = Field(default_factory=list)


class EnsembleResult(BaseModel):
    """Полный результат ensemble"""
    symbol: str
    timeframe: str = "1h"
    
    # Финальный сигнал
    signal: EnsembleSignal
    
    # Детализация
    alpha_contributions: List[AlphaContribution] = Field(default_factory=list)
    conflict_report: ConflictReport = Field(default_factory=ConflictReport)
    
    # Контекст
    regime: str = Field(default="UNKNOWN")
    market_context: Dict[str, Any] = Field(default_factory=dict)
    
    # Рекомендации
    recommendation: str = Field(default="", description="Текстовая рекомендация")
    action_score: float = Field(default=0.0, ge=0.0, le=1.0, description="Рекомендуемый размер позиции 0-1")
    
    # Статистика
    total_alphas: int = 0
    aligned_alphas: int = 0
    opposing_alphas: int = 0
    neutral_alphas: int = 0
    
    # Метки
    notes: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    
    computed_at: datetime = Field(default_factory=datetime.utcnow)


class EnsembleSnapshot(BaseModel):
    """Снимок ensemble для хранения"""
    id: str = ""
    symbol: str
    timeframe: str = "1h"
    result: EnsembleResult
    market_price: float = 0.0
    created_at: datetime = Field(default_factory=datetime.utcnow)


class EnsembleConfig(BaseModel):
    """Конфигурация Ensemble Engine"""
    enabled: bool = True
    version: str = "phase_3.5.2"
    
    # Пороги
    min_confidence_threshold: float = 0.3
    strong_signal_threshold: float = 0.7
    conflict_threshold: float = 0.4
    
    # Качество сигнала
    quality_thresholds: Dict[str, float] = Field(default_factory=lambda: {
        "PREMIUM": 0.8,
        "HIGH": 0.65,
        "MEDIUM": 0.45,
        "LOW": 0.0
    })
    
    # Режимы
    regime_boost: Dict[str, float] = Field(default_factory=lambda: {
        "TRENDING": 1.15,
        "RANGING": 0.9,
        "VOLATILE": 0.85,
        "COMPRESSION": 1.1,
        "EXPANSION": 1.0
    })


class EnsembleHistoryQuery(BaseModel):
    """Запрос истории ensemble"""
    symbol: str
    timeframe: str = "1h"
    limit: int = Field(default=100, ge=1, le=1000)
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    direction: Optional[SignalDirection] = None
    min_quality: Optional[SignalQuality] = None
