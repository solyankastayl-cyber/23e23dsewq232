"""
Ensemble Weights
================

Веса для каждого alpha-фактора в ensemble.
Позволяет настраивать влияние каждого alpha на финальный сигнал.
"""

from typing import Dict, Optional
from pydantic import BaseModel, Field


class EnsembleWeights(BaseModel):
    """
    Веса alpha-факторов для ensemble.
    
    Веса определяют влияние каждого alpha на финальный сигнал.
    weight > 1.0 = усиленное влияние
    weight < 1.0 = ослабленное влияние
    weight = 0.0 = alpha игнорируется
    """
    
    # Trend alphas
    trend_strength_alpha: float = Field(default=1.2, ge=0.0, le=3.0, 
        description="Сила тренда - важный фактор")
    trend_acceleration_alpha: float = Field(default=1.0, ge=0.0, le=3.0,
        description="Ускорение тренда")
    trend_exhaustion_alpha: float = Field(default=0.9, ge=0.0, le=3.0,
        description="Истощение тренда - контр-сигнал")
    
    # Breakout alphas
    breakout_pressure_alpha: float = Field(default=1.3, ge=0.0, le=3.0,
        description="Давление на breakout - высокий приоритет")
    
    # Volatility alphas
    volatility_compression_alpha: float = Field(default=1.0, ge=0.0, le=3.0,
        description="Сжатие волатильности")
    volatility_expansion_alpha: float = Field(default=0.9, ge=0.0, le=3.0,
        description="Расширение волатильности")
    
    # Reversal alphas
    reversal_pressure_alpha: float = Field(default=0.85, ge=0.0, le=3.0,
        description="Давление на разворот - осторожно")
    
    # Volume alphas
    volume_confirmation_alpha: float = Field(default=1.1, ge=0.0, le=3.0,
        description="Подтверждение объёмом")
    volume_anomaly_alpha: float = Field(default=0.8, ge=0.0, le=3.0,
        description="Аномалия объёма")
    
    # Liquidity alphas
    liquidity_sweep_alpha: float = Field(default=0.75, ge=0.0, le=3.0,
        description="Sweep ликвидности - рискованный сигнал")
    
    def get_weight(self, alpha_id: str) -> float:
        """Получить вес по ID alpha"""
        return getattr(self, alpha_id, 1.0)
    
    def get_all_weights(self) -> Dict[str, float]:
        """Получить все веса как словарь"""
        return {
            "trend_strength_alpha": self.trend_strength_alpha,
            "trend_acceleration_alpha": self.trend_acceleration_alpha,
            "trend_exhaustion_alpha": self.trend_exhaustion_alpha,
            "breakout_pressure_alpha": self.breakout_pressure_alpha,
            "volatility_compression_alpha": self.volatility_compression_alpha,
            "volatility_expansion_alpha": self.volatility_expansion_alpha,
            "reversal_pressure_alpha": self.reversal_pressure_alpha,
            "volume_confirmation_alpha": self.volume_confirmation_alpha,
            "volume_anomaly_alpha": self.volume_anomaly_alpha,
            "liquidity_sweep_alpha": self.liquidity_sweep_alpha
        }
    
    def adjust_for_regime(self, regime: str) -> 'EnsembleWeights':
        """
        Корректировка весов под текущий режим рынка.
        
        TRENDING: усиливаем trend alphas
        RANGING: усиливаем reversal alphas
        VOLATILE: уменьшаем все веса
        COMPRESSION: усиливаем breakout
        """
        adjusted = self.model_copy()
        
        if regime == "TRENDING" or regime == "TREND_UP" or regime == "TREND_DOWN":
            adjusted.trend_strength_alpha *= 1.2
            adjusted.trend_acceleration_alpha *= 1.15
            adjusted.reversal_pressure_alpha *= 0.7
            adjusted.breakout_pressure_alpha *= 1.1
            
        elif regime == "RANGING" or regime == "RANGE":
            adjusted.reversal_pressure_alpha *= 1.3
            adjusted.trend_strength_alpha *= 0.8
            adjusted.breakout_pressure_alpha *= 0.85
            adjusted.volatility_compression_alpha *= 1.2
            
        elif regime == "VOLATILE" or regime == "EXPANSION":
            adjusted.trend_strength_alpha *= 0.9
            adjusted.volatility_expansion_alpha *= 1.2
            adjusted.liquidity_sweep_alpha *= 1.1
            
        elif regime == "COMPRESSION":
            adjusted.breakout_pressure_alpha *= 1.4
            adjusted.volatility_compression_alpha *= 1.3
            adjusted.trend_strength_alpha *= 0.9
        
        return adjusted


# Preset конфигурации весов
WEIGHT_PRESETS = {
    "default": EnsembleWeights(),
    
    "aggressive": EnsembleWeights(
        trend_strength_alpha=1.4,
        breakout_pressure_alpha=1.5,
        reversal_pressure_alpha=0.6,
        liquidity_sweep_alpha=0.9
    ),
    
    "conservative": EnsembleWeights(
        trend_strength_alpha=1.0,
        breakout_pressure_alpha=0.9,
        reversal_pressure_alpha=1.1,
        volume_confirmation_alpha=1.3,
        liquidity_sweep_alpha=0.5
    ),
    
    "trend_following": EnsembleWeights(
        trend_strength_alpha=1.5,
        trend_acceleration_alpha=1.3,
        trend_exhaustion_alpha=0.6,
        reversal_pressure_alpha=0.5,
        breakout_pressure_alpha=1.2
    ),
    
    "mean_reversion": EnsembleWeights(
        trend_strength_alpha=0.7,
        trend_exhaustion_alpha=1.4,
        reversal_pressure_alpha=1.5,
        liquidity_sweep_alpha=1.2,
        breakout_pressure_alpha=0.6
    )
}


def get_default_weights() -> EnsembleWeights:
    """Получить дефолтные веса"""
    return EnsembleWeights()


def get_weights_preset(preset: str) -> EnsembleWeights:
    """Получить preset весов"""
    return WEIGHT_PRESETS.get(preset, EnsembleWeights())
