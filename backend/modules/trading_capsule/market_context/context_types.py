"""
Market Context Types
====================

Типы данных для Advanced Market Context Pack.
"""

from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime


# ============================================
# Funding Context Types
# ============================================

class FundingState(str, Enum):
    """Состояние funding rate"""
    NEUTRAL = "NEUTRAL"
    POSITIVE_MILD = "POSITIVE_MILD"
    POSITIVE_HIGH = "POSITIVE_HIGH"
    POSITIVE_EXTREME = "POSITIVE_EXTREME"
    NEGATIVE_MILD = "NEGATIVE_MILD"
    NEGATIVE_HIGH = "NEGATIVE_HIGH"
    NEGATIVE_EXTREME = "NEGATIVE_EXTREME"


class FundingContext(BaseModel):
    """Контекст funding rate"""
    funding_state: FundingState = FundingState.NEUTRAL
    funding_rate: float = 0.0
    funding_pressure: float = Field(default=0.0, ge=-1.0, le=1.0, description="-1 short pressure, +1 long pressure")
    funding_extreme: bool = False
    funding_acceleration: float = Field(default=0.0, ge=-1.0, le=1.0)
    directional_bias: str = Field(default="NEUTRAL", description="LONG_OVERCROWDED/SHORT_OVERCROWDED/NEUTRAL")
    long_overcrowded: bool = False
    short_overcrowded: bool = False
    confidence_adjustment: float = Field(default=0.0, ge=-0.5, le=0.5, description="Adjustment to signal confidence")
    notes: List[str] = Field(default_factory=list)


# ============================================
# Open Interest Context Types
# ============================================

class OIState(str, Enum):
    """Состояние Open Interest"""
    RISING_WITH_PRICE = "RISING_WITH_PRICE"
    RISING_AGAINST_PRICE = "RISING_AGAINST_PRICE"
    FALLING_WITH_PRICE = "FALLING_WITH_PRICE"
    FALLING_AGAINST_PRICE = "FALLING_AGAINST_PRICE"
    STABLE = "STABLE"
    COLLAPSE = "COLLAPSE"
    SURGE = "SURGE"


class OIContext(BaseModel):
    """Контекст Open Interest"""
    oi_state: OIState = OIState.STABLE
    oi_change_pct: float = 0.0
    oi_pressure: float = Field(default=0.0, ge=-1.0, le=1.0)
    squeeze_probability: float = Field(default=0.0, ge=0.0, le=1.0)
    participation_quality: str = Field(default="NEUTRAL", description="STRONG/WEAK/NEUTRAL")
    price_oi_alignment: bool = True
    short_covering_detected: bool = False
    long_liquidation_detected: bool = False
    confidence_adjustment: float = Field(default=0.0, ge=-0.5, le=0.5)
    notes: List[str] = Field(default_factory=list)


# ============================================
# Volatility Context Types
# ============================================

class VolatilityRegime(str, Enum):
    """Режим волатильности"""
    COMPRESSED = "COMPRESSED"
    EXPANDING = "EXPANDING"
    UNSTABLE = "UNSTABLE"
    EXHAUSTED = "EXHAUSTED"
    NORMAL = "NORMAL"


class VolatilityContext(BaseModel):
    """Контекст волатильности"""
    volatility_regime: VolatilityRegime = VolatilityRegime.NORMAL
    volatility_percentile: float = Field(default=50.0, ge=0.0, le=100.0)
    volatility_pressure: float = Field(default=0.0, ge=-1.0, le=1.0, description="-1 contracting, +1 expanding")
    volatility_quality: str = Field(default="NORMAL", description="CLEAN/CHOPPY/NORMAL")
    expansion_probability: float = Field(default=0.5, ge=0.0, le=1.0)
    breakout_favorable: bool = False
    mean_reversion_favorable: bool = False
    risk_multiplier: float = Field(default=1.0, ge=0.5, le=2.0)
    notes: List[str] = Field(default_factory=list)


# ============================================
# Macro Context Types
# ============================================

class MacroRegime(str, Enum):
    """Макро режим"""
    RISK_ON = "RISK_ON"
    RISK_OFF = "RISK_OFF"
    TRANSITIONING = "TRANSITIONING"
    NEUTRAL = "NEUTRAL"


class RiskEnvironment(str, Enum):
    """Риск среда"""
    CRYPTO_FRIENDLY = "CRYPTO_FRIENDLY"
    CRYPTO_HOSTILE = "CRYPTO_HOSTILE"
    NEUTRAL = "NEUTRAL"


class MacroContext(BaseModel):
    """Контекст макро среды"""
    macro_regime: MacroRegime = MacroRegime.NEUTRAL
    macro_bias: str = Field(default="NEUTRAL", description="BULLISH/BEARISH/NEUTRAL")
    risk_environment: RiskEnvironment = RiskEnvironment.NEUTRAL
    spx_context: str = Field(default="NEUTRAL", description="STRONG/WEAK/NEUTRAL")
    dxy_context: str = Field(default="NEUTRAL", description="STRONG/WEAK/NEUTRAL")
    cross_market_alignment: float = Field(default=0.5, ge=0.0, le=1.0)
    crypto_long_confidence_adj: float = Field(default=0.0, ge=-0.5, le=0.5)
    crypto_short_confidence_adj: float = Field(default=0.0, ge=-0.5, le=0.5)
    notes: List[str] = Field(default_factory=list)


# ============================================
# Volume Profile Context Types
# ============================================

class VolumeProfileBias(str, Enum):
    """Bias по volume profile"""
    NEAR_HIGH_VOLUME_NODE = "NEAR_HIGH_VOLUME_NODE"
    NEAR_LOW_VOLUME_NODE = "NEAR_LOW_VOLUME_NODE"
    IN_ACCEPTANCE_ZONE = "IN_ACCEPTANCE_ZONE"
    NEAR_REJECTION_ZONE = "NEAR_REJECTION_ZONE"
    ABOVE_VALUE_AREA = "ABOVE_VALUE_AREA"
    BELOW_VALUE_AREA = "BELOW_VALUE_AREA"
    NEUTRAL = "NEUTRAL"


class VolumeProfileContext(BaseModel):
    """Контекст Volume Profile"""
    volume_profile_bias: VolumeProfileBias = VolumeProfileBias.NEUTRAL
    poc_price: float = Field(default=0.0, description="Point of Control")
    value_area_high: float = 0.0
    value_area_low: float = 0.0
    acceptance_zone: Optional[tuple] = None
    rejection_zone: Optional[tuple] = None
    node_proximity: str = Field(default="NONE", description="HVN/LVN/NONE")
    price_acceptance: bool = True
    breakout_validation: float = Field(default=0.5, ge=0.0, le=1.0)
    mean_reversion_quality: float = Field(default=0.5, ge=0.0, le=1.0)
    sr_refinement: List[float] = Field(default_factory=list)
    notes: List[str] = Field(default_factory=list)


# ============================================
# Aggregated Context
# ============================================

class MarketContextSnapshot(BaseModel):
    """Полный снимок рыночного контекста"""
    symbol: str
    timeframe: str = "1h"
    
    # Individual contexts
    funding: FundingContext = Field(default_factory=FundingContext)
    oi: OIContext = Field(default_factory=OIContext)
    volatility: VolatilityContext = Field(default_factory=VolatilityContext)
    macro: MacroContext = Field(default_factory=MacroContext)
    volume_profile: VolumeProfileContext = Field(default_factory=VolumeProfileContext)
    
    # Aggregated scores
    context_score: float = Field(default=0.5, ge=0.0, le=1.0, description="Overall context quality")
    long_bias_score: float = Field(default=0.5, ge=0.0, le=1.0)
    short_bias_score: float = Field(default=0.5, ge=0.0, le=1.0)
    
    # Summary
    primary_bias: str = Field(default="NEUTRAL", description="LONG/SHORT/NEUTRAL")
    context_quality: str = Field(default="MEDIUM", description="HIGH/MEDIUM/LOW")
    
    # Adjustments for other systems
    breakout_confidence_adj: float = Field(default=0.0, ge=-0.5, le=0.5)
    mean_reversion_confidence_adj: float = Field(default=0.0, ge=-0.5, le=0.5)
    trend_confidence_adj: float = Field(default=0.0, ge=-0.5, le=0.5)
    
    # Risk
    risk_multiplier: float = Field(default=1.0, ge=0.5, le=2.0)
    
    # Metadata
    warnings: List[str] = Field(default_factory=list)
    notes: List[str] = Field(default_factory=list)
    
    computed_at: datetime = Field(default_factory=datetime.utcnow)


class ContextHistoryQuery(BaseModel):
    """Запрос истории контекста"""
    symbol: str
    timeframe: str = "1h"
    limit: int = Field(default=100, ge=1, le=1000)
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
