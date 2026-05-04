"""
PHASE 25.1 — Macro Context Types

Core data models for Macro Intelligence layer.
This module is INDEPENDENT from TA / Exchange / Fractal.

Macro Context provides market regime intelligence based on:
- Inflation
- Rates
- Labor market
- Growth
- Liquidity
- Consumer sentiment
- Credit conditions
"""

from pydantic import BaseModel, Field
from typing import Literal, Optional, Dict
from datetime import datetime


# ══════════════════════════════════════════════════════════════
# Macro State Enum Values
# ══════════════════════════════════════════════════════════════

MacroStateType = Literal[
    "RISK_ON",      # Bullish equities, expanding liquidity
    "RISK_OFF",     # Bearish equities, strong USD
    "NEUTRAL",      # No clear macro direction
    "TIGHTENING",   # High rates, high inflation, contracting liquidity
    "EASING",       # Low rates, expanding liquidity
    "STAGFLATION",  # High inflation + weak growth
    "UNKNOWN",      # Insufficient data
]

BiasType = Literal["BULLISH", "BEARISH", "NEUTRAL"]
LiquidityStateType = Literal["EXPANDING", "STABLE", "CONTRACTING", "UNKNOWN"]
ContextStateType = Literal["SUPPORTIVE", "MIXED", "CONFLICTED", "BLOCKED"]


# ══════════════════════════════════════════════════════════════
# Input Contract
# ══════════════════════════════════════════════════════════════

class MacroInput(BaseModel):
    """
    Normalized macro input signals.
    
    All values should be in range [-1.0, +1.0]:
    - -1 = bearish / tightening / contraction pressure
    -  0 = neutral
    - +1 = bullish / easing / expansion pressure
    """
    
    # Inflation & Rates
    inflation_signal: float = Field(
        default=0.0, ge=-1.0, le=1.0,
        description="Inflation pressure: +1 = high inflation, -1 = deflation"
    )
    rates_signal: float = Field(
        default=0.0, ge=-1.0, le=1.0,
        description="Rate pressure: +1 = hawkish/rising, -1 = dovish/falling"
    )
    
    # Labor Market
    labor_market_signal: float = Field(
        default=0.0, ge=-1.0, le=1.0,
        description="Labor strength: +1 = strong labor, -1 = weak labor"
    )
    unemployment_signal: float = Field(
        default=0.0, ge=-1.0, le=1.0,
        description="Unemployment: +1 = improving (falling), -1 = worsening (rising)"
    )
    
    # Housing
    housing_signal: float = Field(
        default=0.0, ge=-1.0, le=1.0,
        description="Housing: +1 = strong housing, -1 = weak housing"
    )
    
    # Growth & Economy
    growth_signal: float = Field(
        default=0.0, ge=-1.0, le=1.0,
        description="GDP growth: +1 = strong growth, -1 = contraction"
    )
    
    # Liquidity & Credit
    liquidity_signal: float = Field(
        default=0.0, ge=-1.0, le=1.0,
        description="Liquidity: +1 = expanding, -1 = contracting"
    )
    credit_signal: float = Field(
        default=0.0, ge=-1.0, le=1.0,
        description="Credit conditions: +1 = easy credit, -1 = tight credit"
    )
    
    # Consumer
    consumer_signal: float = Field(
        default=0.0, ge=-1.0, le=1.0,
        description="Consumer sentiment: +1 = bullish consumer, -1 = bearish"
    )
    
    # Metadata
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    source: str = Field(default="manual", description="Data source identifier")
    
    def get_all_signals(self) -> Dict[str, float]:
        """Return all signals as dict."""
        return {
            "inflation": self.inflation_signal,
            "rates": self.rates_signal,
            "labor_market": self.labor_market_signal,
            "unemployment": self.unemployment_signal,
            "housing": self.housing_signal,
            "growth": self.growth_signal,
            "liquidity": self.liquidity_signal,
            "credit": self.credit_signal,
            "consumer": self.consumer_signal,
        }
    
    def count_non_zero(self) -> int:
        """Count how many signals have non-zero values."""
        signals = self.get_all_signals()
        return sum(1 for v in signals.values() if abs(v) > 0.01)


# ══════════════════════════════════════════════════════════════
# Output Contract - MacroContext
# ══════════════════════════════════════════════════════════════

class MacroContext(BaseModel):
    """
    Main contract for Macro Intelligence layer.
    
    This is the ONLY interface through which other system modules
    interact with macro intelligence.
    
    Key principle: Macro Context is CONTEXT INTELLIGENCE, not signal override.
    It should influence confidence/regime, NOT change direction.
    """
    
    # Core classification
    macro_state: MacroStateType = Field(
        description="Overall macro regime classification"
    )
    
    # Directional biases
    usd_bias: BiasType = Field(
        description="USD directional bias based on rates, inflation, credit"
    )
    equity_bias: BiasType = Field(
        description="Equity directional bias based on growth, liquidity, consumer"
    )
    liquidity_state: LiquidityStateType = Field(
        description="Liquidity regime classification"
    )
    
    # Quality metrics
    confidence: float = Field(
        ge=0.0, le=1.0,
        description="Signal strength: avg of abs(all inputs)"
    )
    reliability: float = Field(
        ge=0.0, le=1.0,
        description="Signal consistency: 1 - stddev of inputs"
    )
    
    # Computed strength
    macro_strength: float = Field(
        ge=0.0, le=1.0,
        description="Combined quality: 0.5 * confidence + 0.5 * reliability"
    )
    
    # Context state
    context_state: ContextStateType = Field(
        description="Overall context classification for system integration"
    )
    
    # Explainability
    reason: str = Field(
        description="Human-readable explanation of macro context"
    )
    
    # Metadata
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    version: str = Field(default="25.1.0")


# ══════════════════════════════════════════════════════════════
# Summary Contract (compact)
# ══════════════════════════════════════════════════════════════

class MacroContextSummary(BaseModel):
    """Compact summary for quick access."""
    macro_state: MacroStateType
    usd_bias: BiasType
    equity_bias: BiasType
    liquidity_state: LiquidityStateType
    confidence: float
    reliability: float
    context_state: ContextStateType


# ══════════════════════════════════════════════════════════════
# Health Status
# ══════════════════════════════════════════════════════════════

class MacroHealthStatus(BaseModel):
    """Health check response for macro context module."""
    status: Literal["OK", "DEGRADED", "ERROR"] = Field(
        description="Overall health status"
    )
    has_inputs: bool = Field(
        description="Whether macro inputs are available"
    )
    input_count: int = Field(
        description="Number of non-zero input signals"
    )
    context_state: ContextStateType = Field(
        description="Current context state"
    )
    last_update: Optional[datetime] = Field(
        default=None,
        description="Last update timestamp"
    )
