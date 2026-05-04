"""
Regime Intelligence v2 — Detection Engine

Core logic for market regime detection.

Sources:
- TA Engine (trend)
- Exchange Intelligence (liquidity)
- Fractal Intelligence (alignment)
- Volatility Metrics
- Liquidity Metrics

Classification:
- TRENDING: trend_strength ≥ 0.03, volatility < 0.05
- RANGING: trend_strength < 0.02, volatility < 0.04
- VOLATILE: volatility ≥ 0.06
- ILLIQUID: liquidity_score < 0.30
"""

from typing import Optional, Dict, List
from datetime import datetime
import random

from .regime_types import (
    MarketRegime,
    RegimeType,
    ContextState,
    DominantDriver,
    RegimeInputMetrics,
    TREND_STRONG_THRESHOLD,
    TREND_WEAK_THRESHOLD,
    VOLATILITY_LOW_THRESHOLD,
    VOLATILITY_MEDIUM_THRESHOLD,
    VOLATILITY_HIGH_THRESHOLD,
    LIQUIDITY_LOW_THRESHOLD,
    CONFIDENCE_WEIGHT_TREND,
    CONFIDENCE_WEIGHT_VOLATILITY,
    CONFIDENCE_WEIGHT_LIQUIDITY,
)


class RegimeDetectionEngine:
    """
    Market Regime Detection Engine.
    
    Determines current market state based on:
    - Trend strength
    - Volatility level
    - Liquidity conditions
    - Fractal alignment
    """
    
    def __init__(self):
        self._current_regime: Optional[MarketRegime] = None
        self._metrics_cache: Dict[str, RegimeInputMetrics] = {}
    
    # ═══════════════════════════════════════════════════════════
    # Core Metric Calculations
    # ═══════════════════════════════════════════════════════════
    
    def calculate_trend_strength(
        self,
        ema_50: float,
        ema_200: float,
        price: float,
    ) -> float:
        """
        Calculate trend strength.
        
        Formula: |EMA50 - EMA200| / price
        Returns normalized value 0-1
        """
        if price <= 0:
            return 0.0
        
        raw_strength = abs(ema_50 - ema_200) / price
        
        # Normalize to 0-1 range (cap at 0.10 for normalization)
        normalized = min(raw_strength / 0.10, 1.0)
        return round(normalized, 4)
    
    def calculate_volatility(
        self,
        atr: float,
        price: float,
    ) -> float:
        """
        Calculate volatility level.
        
        Formula: ATR / price
        Returns normalized value 0-1
        """
        if price <= 0:
            return 0.0
        
        raw_volatility = atr / price
        
        # Normalize to 0-1 range (cap at 0.10 for normalization)
        normalized = min(raw_volatility / 0.10, 1.0)
        return round(normalized, 4)
    
    def calculate_liquidity(
        self,
        orderbook_depth: float,
        volume_profile: float,
        spread_inverse: float,
    ) -> float:
        """
        Calculate liquidity score.
        
        Formula: (orderbook_depth + volume_profile + spread_inverse) / 3
        Returns normalized value 0-1
        """
        score = (orderbook_depth + volume_profile + spread_inverse) / 3.0
        return round(min(max(score, 0.0), 1.0), 4)
    
    # ═══════════════════════════════════════════════════════════
    # Regime Classification
    # ═══════════════════════════════════════════════════════════
    
    def classify_regime(
        self,
        trend_strength: float,
        volatility_level: float,
        liquidity_level: float,
    ) -> RegimeType:
        """
        Classify market regime based on metrics.
        
        Priority order:
        1. ILLIQUID: liquidity < 0.30
        2. VOLATILE: volatility ≥ 0.60 (normalized, equals 0.06 raw)
        3. TRENDING: trend ≥ 0.30 (normalized, equals 0.03 raw) AND volatility < 0.50
        4. RANGING: trend < 0.20 (normalized, equals 0.02 raw) AND volatility < 0.40
        """
        # Check ILLIQUID first (most restrictive)
        if liquidity_level < LIQUIDITY_LOW_THRESHOLD:
            return "ILLIQUID"
        
        # Check VOLATILE
        if volatility_level >= VOLATILITY_HIGH_THRESHOLD * 10:  # Normalized threshold
            return "VOLATILE"
        
        # Check TRENDING
        if (trend_strength >= TREND_STRONG_THRESHOLD * 10 and 
            volatility_level < VOLATILITY_MEDIUM_THRESHOLD * 10):
            return "TRENDING"
        
        # Check RANGING
        if (trend_strength < TREND_WEAK_THRESHOLD * 10 and 
            volatility_level < VOLATILITY_LOW_THRESHOLD * 10):
            return "RANGING"
        
        # Default: determine by strongest signal
        if volatility_level > trend_strength:
            return "VOLATILE"
        elif trend_strength >= 0.20:
            return "TRENDING"
        else:
            return "RANGING"
    
    # ═══════════════════════════════════════════════════════════
    # Confidence & Attribution
    # ═══════════════════════════════════════════════════════════
    
    def calculate_regime_confidence(
        self,
        trend_strength: float,
        volatility_level: float,
        liquidity_level: float,
    ) -> float:
        """
        Calculate regime confidence.
        
        Formula: 0.4 * trend + 0.3 * volatility_score + 0.3 * liquidity
        """
        # Volatility score is inverse (lower volatility = higher confidence for trending)
        volatility_score = 1.0 - volatility_level
        
        confidence = (
            CONFIDENCE_WEIGHT_TREND * trend_strength +
            CONFIDENCE_WEIGHT_VOLATILITY * volatility_score +
            CONFIDENCE_WEIGHT_LIQUIDITY * liquidity_level
        )
        
        return round(min(max(confidence, 0.0), 1.0), 4)
    
    def detect_dominant_driver(
        self,
        trend_strength: float,
        volatility_level: float,
        liquidity_level: float,
        fractal_alignment: float = 0.5,
    ) -> DominantDriver:
        """
        Detect which factor is driving the regime.
        
        Returns the factor with maximum influence.
        """
        scores = {
            "TREND": trend_strength,
            "VOLATILITY": volatility_level,
            "LIQUIDITY": 1.0 - liquidity_level,  # Low liquidity = high driver
            "FRACTAL": fractal_alignment,
        }
        
        dominant = max(scores, key=scores.get)
        return dominant
    
    def determine_context_state(
        self,
        trend_strength: float,
        volatility_level: float,
        liquidity_level: float,
    ) -> ContextState:
        """
        Determine context state.
        
        SUPPORTIVE: Good trend, low volatility, high liquidity
        CONFLICTED: Mixed signals
        NEUTRAL: No strong signals
        """
        positive_signals = 0
        negative_signals = 0
        
        # Trend analysis
        if trend_strength >= 0.30:
            positive_signals += 1
        elif trend_strength < 0.10:
            negative_signals += 1
        
        # Volatility analysis
        if volatility_level < 0.30:
            positive_signals += 1
        elif volatility_level >= 0.60:
            negative_signals += 1
        
        # Liquidity analysis
        if liquidity_level >= 0.60:
            positive_signals += 1
        elif liquidity_level < 0.30:
            negative_signals += 1
        
        if positive_signals >= 2 and negative_signals == 0:
            return "SUPPORTIVE"
        elif negative_signals >= 2 or (positive_signals > 0 and negative_signals > 0):
            return "CONFLICTED"
        else:
            return "NEUTRAL"
    
    # ═══════════════════════════════════════════════════════════
    # Main Detection
    # ═══════════════════════════════════════════════════════════
    
    def detect_regime(
        self,
        metrics: RegimeInputMetrics,
        symbol: str = "BTCUSDT",
        timeframe: str = "1H",
    ) -> MarketRegime:
        """
        Detect current market regime from input metrics.
        
        Returns full MarketRegime object.
        """
        # Calculate core metrics
        trend_strength = self.calculate_trend_strength(
            metrics.ema_50,
            metrics.ema_200,
            metrics.price,
        )
        
        volatility_level = self.calculate_volatility(
            metrics.atr,
            metrics.price,
        )
        
        liquidity_level = self.calculate_liquidity(
            metrics.orderbook_depth,
            metrics.volume_profile,
            metrics.spread_inverse,
        )
        
        # Classify
        regime_type = self.classify_regime(
            trend_strength,
            volatility_level,
            liquidity_level,
        )
        
        # Calculate confidence
        confidence = self.calculate_regime_confidence(
            trend_strength,
            volatility_level,
            liquidity_level,
        )
        
        # Detect dominant driver
        dominant = self.detect_dominant_driver(
            trend_strength,
            volatility_level,
            liquidity_level,
            metrics.fractal_alignment,
        )
        
        # Determine context
        context = self.determine_context_state(
            trend_strength,
            volatility_level,
            liquidity_level,
        )
        
        regime = MarketRegime(
            regime_type=regime_type,
            trend_strength=trend_strength,
            volatility_level=volatility_level,
            liquidity_level=liquidity_level,
            regime_confidence=confidence,
            dominant_driver=dominant,
            context_state=context,
            symbol=symbol,
            timeframe=timeframe,
        )
        
        self._current_regime = regime
        return regime
    
    # ═══════════════════════════════════════════════════════════
    # Simulated Detection (for testing without real data)
    # ═══════════════════════════════════════════════════════════
    
    def detect_regime_simulated(
        self,
        symbol: str = "BTCUSDT",
        timeframe: str = "1H",
    ) -> MarketRegime:
        """
        Detect regime using simulated/mock data.
        
        For testing when real market data is not available.
        """
        # Generate realistic mock metrics
        price = 42000.0 + random.uniform(-2000, 2000)
        ema_50 = price * (1 + random.uniform(-0.02, 0.02))
        ema_200 = price * (1 + random.uniform(-0.04, 0.04))
        atr = price * random.uniform(0.01, 0.05)
        
        metrics = RegimeInputMetrics(
            price=price,
            ema_50=ema_50,
            ema_200=ema_200,
            atr=atr,
            orderbook_depth=random.uniform(0.4, 0.9),
            volume_profile=random.uniform(0.3, 0.8),
            spread_inverse=random.uniform(0.5, 0.95),
            fractal_alignment=random.uniform(0.3, 0.7),
        )
        
        self._metrics_cache[f"{symbol}_{timeframe}"] = metrics
        return self.detect_regime(metrics, symbol, timeframe)
    
    # ═══════════════════════════════════════════════════════════
    # Accessors
    # ═══════════════════════════════════════════════════════════
    
    @property
    def current_regime(self) -> Optional[MarketRegime]:
        """Get current regime."""
        return self._current_regime
    
    def get_cached_metrics(
        self,
        symbol: str = "BTCUSDT",
        timeframe: str = "1H",
    ) -> Optional[RegimeInputMetrics]:
        """Get cached input metrics."""
        return self._metrics_cache.get(f"{symbol}_{timeframe}")


# Singleton
_engine: Optional[RegimeDetectionEngine] = None


def get_regime_detection_engine() -> RegimeDetectionEngine:
    """Get singleton instance of RegimeDetectionEngine."""
    global _engine
    if _engine is None:
        _engine = RegimeDetectionEngine()
    return _engine
