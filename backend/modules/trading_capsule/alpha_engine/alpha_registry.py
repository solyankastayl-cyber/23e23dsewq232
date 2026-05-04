"""
Alpha Registry
==============

Реестр и реализация 10 alpha-факторов.
Каждый alpha - отдельный модуль с единым интерфейсом.
"""

import math
import random
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime

from .alpha_types import AlphaResult, AlphaDirection, AlphaRegimeRelevance


class BaseAlpha:
    """Базовый класс для alpha-фактора"""
    
    alpha_id: str = "base_alpha"
    alpha_name: str = "Base Alpha"
    description: str = "Base alpha factor"
    regime_relevance: AlphaRegimeRelevance = AlphaRegimeRelevance.ALL
    
    def compute(self, market_data: Dict[str, Any]) -> AlphaResult:
        """Вычисление alpha. Переопределяется в наследниках."""
        raise NotImplementedError


# ============================================
# 1. Trend Strength Alpha
# ============================================
class TrendStrengthAlpha(BaseAlpha):
    """
    Измеряет силу текущего тренда.
    Использует ADX-подобную логику + MA slopes.
    """
    alpha_id = "trend_strength_alpha"
    alpha_name = "Trend Strength"
    description = "Measures current trend strength using ADX-like calculation"
    regime_relevance = AlphaRegimeRelevance.TRENDING
    
    def compute(self, market_data: Dict[str, Any]) -> AlphaResult:
        prices = market_data.get("close", [])
        highs = market_data.get("high", [])
        lows = market_data.get("low", [])
        
        if len(prices) < 20:
            return self._neutral_result()
        
        # Simplified ADX-like calculation
        # Trend direction from MA
        ma_20 = sum(prices[-20:]) / 20
        ma_50 = sum(prices[-50:]) / 50 if len(prices) >= 50 else ma_20
        current_price = prices[-1]
        
        # Direction
        if current_price > ma_20 > ma_50:
            direction = AlphaDirection.LONG
            trend_score = min(1.0, (current_price - ma_50) / ma_50 * 10)
        elif current_price < ma_20 < ma_50:
            direction = AlphaDirection.SHORT
            trend_score = min(1.0, (ma_50 - current_price) / ma_50 * 10)
        else:
            direction = AlphaDirection.NEUTRAL
            trend_score = 0.3
        
        # Calculate directional movement
        plus_dm = sum(max(0, highs[i] - highs[i-1]) for i in range(-14, 0)) / 14
        minus_dm = sum(max(0, lows[i-1] - lows[i]) for i in range(-14, 0)) / 14
        
        dm_ratio = plus_dm / (plus_dm + minus_dm + 0.0001)
        
        strength = abs(dm_ratio - 0.5) * 2  # 0-1
        confidence = min(1.0, trend_score * 1.2)
        
        return AlphaResult(
            alpha_id=self.alpha_id,
            alpha_name=self.alpha_name,
            direction=direction,
            strength=round(strength, 4),
            confidence=round(confidence, 4),
            regime_relevance=self.regime_relevance,
            raw_value=dm_ratio,
            normalized_value=round((dm_ratio - 0.5) * 2, 4),
            metadata={"ma_20": ma_20, "ma_50": ma_50, "plus_dm": plus_dm, "minus_dm": minus_dm}
        )
    
    def _neutral_result(self) -> AlphaResult:
        return AlphaResult(
            alpha_id=self.alpha_id,
            alpha_name=self.alpha_name,
            direction=AlphaDirection.NEUTRAL,
            strength=0.0,
            confidence=0.0,
            regime_relevance=self.regime_relevance
        )


# ============================================
# 2. Trend Acceleration Alpha
# ============================================
class TrendAccelerationAlpha(BaseAlpha):
    """
    Измеряет ускорение тренда.
    Вторая производная цены.
    """
    alpha_id = "trend_acceleration_alpha"
    alpha_name = "Trend Acceleration"
    description = "Measures trend acceleration (second derivative of price)"
    regime_relevance = AlphaRegimeRelevance.TRENDING
    
    def compute(self, market_data: Dict[str, Any]) -> AlphaResult:
        prices = market_data.get("close", [])
        
        if len(prices) < 30:
            return self._neutral_result()
        
        # First derivative (momentum)
        momentum_short = (prices[-1] - prices[-5]) / prices[-5] * 100
        momentum_long = (prices[-5] - prices[-15]) / prices[-15] * 100
        
        # Second derivative (acceleration)
        acceleration = momentum_short - momentum_long
        
        # Direction
        if acceleration > 0.5:
            direction = AlphaDirection.LONG
        elif acceleration < -0.5:
            direction = AlphaDirection.SHORT
        else:
            direction = AlphaDirection.NEUTRAL
        
        # Normalize acceleration to 0-1 strength
        strength = min(1.0, abs(acceleration) / 3)
        confidence = min(1.0, strength * 1.1)
        
        return AlphaResult(
            alpha_id=self.alpha_id,
            alpha_name=self.alpha_name,
            direction=direction,
            strength=round(strength, 4),
            confidence=round(confidence, 4),
            regime_relevance=self.regime_relevance,
            raw_value=acceleration,
            normalized_value=round(max(-1, min(1, acceleration / 3)), 4),
            metadata={"momentum_short": momentum_short, "momentum_long": momentum_long}
        )
    
    def _neutral_result(self) -> AlphaResult:
        return AlphaResult(
            alpha_id=self.alpha_id,
            alpha_name=self.alpha_name,
            direction=AlphaDirection.NEUTRAL,
            strength=0.0,
            confidence=0.0,
            regime_relevance=self.regime_relevance
        )


# ============================================
# 3. Trend Exhaustion Alpha
# ============================================
class TrendExhaustionAlpha(BaseAlpha):
    """
    Детектирует истощение тренда.
    RSI extremes + divergence signals.
    """
    alpha_id = "trend_exhaustion_alpha"
    alpha_name = "Trend Exhaustion"
    description = "Detects trend exhaustion via RSI extremes and divergences"
    regime_relevance = AlphaRegimeRelevance.TRENDING
    
    def compute(self, market_data: Dict[str, Any]) -> AlphaResult:
        prices = market_data.get("close", [])
        
        if len(prices) < 20:
            return self._neutral_result()
        
        # Calculate RSI
        gains = []
        losses = []
        for i in range(-14, 0):
            change = prices[i] - prices[i-1]
            if change > 0:
                gains.append(change)
                losses.append(0)
            else:
                gains.append(0)
                losses.append(abs(change))
        
        avg_gain = sum(gains) / 14
        avg_loss = sum(losses) / 14
        
        if avg_loss == 0:
            rsi = 100
        else:
            rs = avg_gain / avg_loss
            rsi = 100 - (100 / (1 + rs))
        
        # Check for exhaustion
        if rsi > 75:
            direction = AlphaDirection.SHORT  # Bearish exhaustion
            exhaustion = (rsi - 75) / 25
        elif rsi < 25:
            direction = AlphaDirection.LONG  # Bullish exhaustion
            exhaustion = (25 - rsi) / 25
        else:
            direction = AlphaDirection.NEUTRAL
            exhaustion = 0.2
        
        strength = min(1.0, exhaustion)
        confidence = min(1.0, exhaustion * 0.9)
        
        return AlphaResult(
            alpha_id=self.alpha_id,
            alpha_name=self.alpha_name,
            direction=direction,
            strength=round(strength, 4),
            confidence=round(confidence, 4),
            regime_relevance=self.regime_relevance,
            raw_value=rsi,
            normalized_value=round((rsi - 50) / 50, 4),
            metadata={"rsi": rsi, "exhaustion_level": exhaustion}
        )
    
    def _neutral_result(self) -> AlphaResult:
        return AlphaResult(
            alpha_id=self.alpha_id,
            alpha_name=self.alpha_name,
            direction=AlphaDirection.NEUTRAL,
            strength=0.0,
            confidence=0.0,
            regime_relevance=self.regime_relevance
        )


# ============================================
# 4. Breakout Pressure Alpha
# ============================================
class BreakoutPressureAlpha(BaseAlpha):
    """
    Измеряет давление на breakout.
    Compression near key levels + volume buildup.
    """
    alpha_id = "breakout_pressure_alpha"
    alpha_name = "Breakout Pressure"
    description = "Measures pressure for breakout via compression and volume"
    regime_relevance = AlphaRegimeRelevance.COMPRESSION
    
    def compute(self, market_data: Dict[str, Any]) -> AlphaResult:
        prices = market_data.get("close", [])
        highs = market_data.get("high", [])
        lows = market_data.get("low", [])
        volumes = market_data.get("volume", [])
        
        if len(prices) < 20:
            return self._neutral_result()
        
        # Calculate range compression
        recent_range = max(highs[-10:]) - min(lows[-10:])
        older_range = max(highs[-20:-10]) - min(lows[-20:-10])
        
        compression_ratio = recent_range / (older_range + 0.0001)
        
        # Volume buildup
        recent_vol = sum(volumes[-5:]) / 5 if volumes else 1
        older_vol = sum(volumes[-15:-5]) / 10 if volumes and len(volumes) >= 15 else 1
        vol_ratio = recent_vol / (older_vol + 0.0001)
        
        # Current position in range
        current = prices[-1]
        range_high = max(highs[-10:])
        range_low = min(lows[-10:])
        position = (current - range_low) / (range_high - range_low + 0.0001)
        
        # Direction based on position in range
        if position > 0.7 and compression_ratio < 0.7:
            direction = AlphaDirection.LONG
            pressure = (1 - compression_ratio) * vol_ratio
        elif position < 0.3 and compression_ratio < 0.7:
            direction = AlphaDirection.SHORT
            pressure = (1 - compression_ratio) * vol_ratio
        else:
            direction = AlphaDirection.NEUTRAL
            pressure = 0.3
        
        strength = min(1.0, pressure)
        confidence = min(1.0, strength * 0.85)
        
        return AlphaResult(
            alpha_id=self.alpha_id,
            alpha_name=self.alpha_name,
            direction=direction,
            strength=round(strength, 4),
            confidence=round(confidence, 4),
            regime_relevance=self.regime_relevance,
            raw_value=compression_ratio,
            normalized_value=round(1 - compression_ratio, 4),
            metadata={
                "compression_ratio": compression_ratio,
                "vol_ratio": vol_ratio,
                "range_position": position
            }
        )
    
    def _neutral_result(self) -> AlphaResult:
        return AlphaResult(
            alpha_id=self.alpha_id,
            alpha_name=self.alpha_name,
            direction=AlphaDirection.NEUTRAL,
            strength=0.0,
            confidence=0.0,
            regime_relevance=self.regime_relevance
        )


# ============================================
# 5. Volatility Compression Alpha
# ============================================
class VolatilityCompressionAlpha(BaseAlpha):
    """
    Измеряет сжатие волатильности.
    Bollinger Band squeeze, ATR contraction.
    """
    alpha_id = "volatility_compression_alpha"
    alpha_name = "Volatility Compression"
    description = "Measures volatility compression via ATR and BB squeeze"
    regime_relevance = AlphaRegimeRelevance.COMPRESSION
    
    def compute(self, market_data: Dict[str, Any]) -> AlphaResult:
        prices = market_data.get("close", [])
        highs = market_data.get("high", [])
        lows = market_data.get("low", [])
        
        if len(prices) < 30:
            return self._neutral_result()
        
        # Calculate ATR
        tr_list = []
        for i in range(-14, 0):
            tr = max(
                highs[i] - lows[i],
                abs(highs[i] - prices[i-1]),
                abs(lows[i] - prices[i-1])
            )
            tr_list.append(tr)
        
        current_atr = sum(tr_list) / 14
        
        # Historical ATR
        tr_hist = []
        for i in range(-28, -14):
            tr = max(
                highs[i] - lows[i],
                abs(highs[i] - prices[i-1]),
                abs(lows[i] - prices[i-1])
            )
            tr_hist.append(tr)
        
        historical_atr = sum(tr_hist) / 14
        
        # Compression ratio
        compression = current_atr / (historical_atr + 0.0001)
        
        # BB width
        ma_20 = sum(prices[-20:]) / 20
        std_dev = math.sqrt(sum((p - ma_20) ** 2 for p in prices[-20:]) / 20)
        bb_width = (std_dev * 4) / ma_20
        
        # Strong compression = potential breakout
        if compression < 0.7 and bb_width < 0.04:
            direction = AlphaDirection.NEUTRAL  # No direction yet, just compression
            strength = 1 - compression
        else:
            direction = AlphaDirection.NEUTRAL
            strength = max(0, 1 - compression)
        
        confidence = min(1.0, strength * 0.8)
        
        return AlphaResult(
            alpha_id=self.alpha_id,
            alpha_name=self.alpha_name,
            direction=direction,
            strength=round(strength, 4),
            confidence=round(confidence, 4),
            regime_relevance=self.regime_relevance,
            raw_value=compression,
            normalized_value=round(1 - compression, 4),
            metadata={
                "atr_ratio": compression,
                "bb_width": bb_width,
                "current_atr": current_atr
            }
        )
    
    def _neutral_result(self) -> AlphaResult:
        return AlphaResult(
            alpha_id=self.alpha_id,
            alpha_name=self.alpha_name,
            direction=AlphaDirection.NEUTRAL,
            strength=0.0,
            confidence=0.0,
            regime_relevance=self.regime_relevance
        )


# ============================================
# 6. Volatility Expansion Alpha
# ============================================
class VolatilityExpansionAlpha(BaseAlpha):
    """
    Измеряет расширение волатильности.
    Breakout confirmation signal.
    """
    alpha_id = "volatility_expansion_alpha"
    alpha_name = "Volatility Expansion"
    description = "Measures volatility expansion for breakout confirmation"
    regime_relevance = AlphaRegimeRelevance.EXPANSION
    
    def compute(self, market_data: Dict[str, Any]) -> AlphaResult:
        prices = market_data.get("close", [])
        highs = market_data.get("high", [])
        lows = market_data.get("low", [])
        
        if len(prices) < 30:
            return self._neutral_result()
        
        # Calculate recent ATR
        tr_recent = []
        for i in range(-7, 0):
            tr = max(
                highs[i] - lows[i],
                abs(highs[i] - prices[i-1]),
                abs(lows[i] - prices[i-1])
            )
            tr_recent.append(tr)
        
        recent_atr = sum(tr_recent) / 7
        
        # Historical ATR
        tr_hist = []
        for i in range(-21, -7):
            tr = max(
                highs[i] - lows[i],
                abs(highs[i] - prices[i-1]),
                abs(lows[i] - prices[i-1])
            )
            tr_hist.append(tr)
        
        historical_atr = sum(tr_hist) / 14
        
        # Expansion ratio
        expansion = recent_atr / (historical_atr + 0.0001)
        
        # Direction based on price movement
        price_change = (prices[-1] - prices[-7]) / prices[-7] * 100
        
        if expansion > 1.3 and price_change > 1:
            direction = AlphaDirection.LONG
            strength = min(1.0, (expansion - 1) * 2)
        elif expansion > 1.3 and price_change < -1:
            direction = AlphaDirection.SHORT
            strength = min(1.0, (expansion - 1) * 2)
        else:
            direction = AlphaDirection.NEUTRAL
            strength = max(0, expansion - 1)
        
        confidence = min(1.0, strength * 0.9)
        
        return AlphaResult(
            alpha_id=self.alpha_id,
            alpha_name=self.alpha_name,
            direction=direction,
            strength=round(strength, 4),
            confidence=round(confidence, 4),
            regime_relevance=self.regime_relevance,
            raw_value=expansion,
            normalized_value=round(min(1, expansion - 1), 4),
            metadata={
                "expansion_ratio": expansion,
                "price_change_pct": price_change
            }
        )
    
    def _neutral_result(self) -> AlphaResult:
        return AlphaResult(
            alpha_id=self.alpha_id,
            alpha_name=self.alpha_name,
            direction=AlphaDirection.NEUTRAL,
            strength=0.0,
            confidence=0.0,
            regime_relevance=self.regime_relevance
        )


# ============================================
# 7. Reversal Pressure Alpha
# ============================================
class ReversalPressureAlpha(BaseAlpha):
    """
    Измеряет давление на разворот.
    Divergences + exhaustion patterns.
    """
    alpha_id = "reversal_pressure_alpha"
    alpha_name = "Reversal Pressure"
    description = "Measures reversal pressure via divergences and patterns"
    regime_relevance = AlphaRegimeRelevance.TRENDING
    
    def compute(self, market_data: Dict[str, Any]) -> AlphaResult:
        prices = market_data.get("close", [])
        
        if len(prices) < 30:
            return self._neutral_result()
        
        # Price trend
        price_slope = (prices[-1] - prices[-20]) / prices[-20] * 100
        
        # Calculate momentum (simplified)
        momentum_recent = prices[-1] - prices[-5]
        momentum_older = prices[-15] - prices[-20]
        
        # Divergence detection
        price_higher = prices[-1] > prices[-15]
        momentum_lower = momentum_recent < momentum_older
        
        price_lower = prices[-1] < prices[-15]
        momentum_higher = momentum_recent > momentum_older
        
        # Bearish divergence
        if price_higher and momentum_lower:
            direction = AlphaDirection.SHORT
            divergence_strength = abs(momentum_older - momentum_recent) / (abs(momentum_older) + 0.0001)
        # Bullish divergence
        elif price_lower and momentum_higher:
            direction = AlphaDirection.LONG
            divergence_strength = abs(momentum_recent - momentum_older) / (abs(momentum_older) + 0.0001)
        else:
            direction = AlphaDirection.NEUTRAL
            divergence_strength = 0.2
        
        strength = min(1.0, divergence_strength)
        confidence = min(1.0, strength * 0.75)
        
        return AlphaResult(
            alpha_id=self.alpha_id,
            alpha_name=self.alpha_name,
            direction=direction,
            strength=round(strength, 4),
            confidence=round(confidence, 4),
            regime_relevance=self.regime_relevance,
            raw_value=divergence_strength,
            normalized_value=round(divergence_strength if direction == AlphaDirection.LONG else -divergence_strength, 4),
            metadata={
                "price_slope": price_slope,
                "momentum_recent": momentum_recent,
                "momentum_older": momentum_older,
                "divergence_type": "bearish" if direction == AlphaDirection.SHORT else "bullish" if direction == AlphaDirection.LONG else "none"
            }
        )
    
    def _neutral_result(self) -> AlphaResult:
        return AlphaResult(
            alpha_id=self.alpha_id,
            alpha_name=self.alpha_name,
            direction=AlphaDirection.NEUTRAL,
            strength=0.0,
            confidence=0.0,
            regime_relevance=self.regime_relevance
        )


# ============================================
# 8. Volume Confirmation Alpha
# ============================================
class VolumeConfirmationAlpha(BaseAlpha):
    """
    Подтверждение движения объёмом.
    Volume confirms price direction.
    """
    alpha_id = "volume_confirmation_alpha"
    alpha_name = "Volume Confirmation"
    description = "Confirms price movement with volume analysis"
    regime_relevance = AlphaRegimeRelevance.ALL
    
    def compute(self, market_data: Dict[str, Any]) -> AlphaResult:
        prices = market_data.get("close", [])
        volumes = market_data.get("volume", [])
        
        if len(prices) < 20 or not volumes or len(volumes) < 20:
            return self._neutral_result()
        
        # Price direction
        price_change = (prices[-1] - prices[-5]) / prices[-5] * 100
        
        # Volume analysis
        recent_vol = sum(volumes[-5:]) / 5
        avg_vol = sum(volumes[-20:]) / 20
        vol_ratio = recent_vol / (avg_vol + 0.0001)
        
        # Confirmation logic
        if price_change > 0.5 and vol_ratio > 1.2:
            direction = AlphaDirection.LONG
            confirmation = min(1.0, vol_ratio - 1)
        elif price_change < -0.5 and vol_ratio > 1.2:
            direction = AlphaDirection.SHORT
            confirmation = min(1.0, vol_ratio - 1)
        elif abs(price_change) > 1 and vol_ratio < 0.8:
            # Weak move without volume - potential reversal
            direction = AlphaDirection.LONG if price_change < 0 else AlphaDirection.SHORT
            confirmation = 0.3
        else:
            direction = AlphaDirection.NEUTRAL
            confirmation = 0.2
        
        strength = min(1.0, confirmation)
        confidence = min(1.0, strength * vol_ratio * 0.5)
        
        return AlphaResult(
            alpha_id=self.alpha_id,
            alpha_name=self.alpha_name,
            direction=direction,
            strength=round(strength, 4),
            confidence=round(confidence, 4),
            regime_relevance=self.regime_relevance,
            raw_value=vol_ratio,
            normalized_value=round(min(1, vol_ratio - 1), 4),
            metadata={
                "vol_ratio": vol_ratio,
                "price_change_pct": price_change,
                "recent_vol": recent_vol,
                "avg_vol": avg_vol
            }
        )
    
    def _neutral_result(self) -> AlphaResult:
        return AlphaResult(
            alpha_id=self.alpha_id,
            alpha_name=self.alpha_name,
            direction=AlphaDirection.NEUTRAL,
            strength=0.0,
            confidence=0.0,
            regime_relevance=self.regime_relevance
        )


# ============================================
# 9. Volume Anomaly Alpha
# ============================================
class VolumeAnomalyAlpha(BaseAlpha):
    """
    Детектирует аномальный объём.
    Unusual volume spikes that precede moves.
    """
    alpha_id = "volume_anomaly_alpha"
    alpha_name = "Volume Anomaly"
    description = "Detects unusual volume spikes"
    regime_relevance = AlphaRegimeRelevance.ALL
    
    def compute(self, market_data: Dict[str, Any]) -> AlphaResult:
        prices = market_data.get("close", [])
        volumes = market_data.get("volume", [])
        
        if len(prices) < 30 or not volumes or len(volumes) < 30:
            return self._neutral_result()
        
        # Calculate volume statistics
        vol_mean = sum(volumes[-30:]) / 30
        vol_std = math.sqrt(sum((v - vol_mean) ** 2 for v in volumes[-30:]) / 30)
        
        current_vol = volumes[-1]
        z_score = (current_vol - vol_mean) / (vol_std + 0.0001)
        
        # Detect anomaly (z > 2 is significant)
        if z_score > 2:
            # Volume spike detected
            price_change = (prices[-1] - prices[-2]) / prices[-2] * 100
            
            if price_change > 0:
                direction = AlphaDirection.LONG
            elif price_change < 0:
                direction = AlphaDirection.SHORT
            else:
                direction = AlphaDirection.NEUTRAL
            
            anomaly_strength = min(1.0, (z_score - 1) / 3)
        else:
            direction = AlphaDirection.NEUTRAL
            anomaly_strength = max(0, z_score / 2)
        
        strength = round(anomaly_strength, 4)
        confidence = min(1.0, strength * 0.7)
        
        return AlphaResult(
            alpha_id=self.alpha_id,
            alpha_name=self.alpha_name,
            direction=direction,
            strength=strength,
            confidence=round(confidence, 4),
            regime_relevance=self.regime_relevance,
            raw_value=z_score,
            normalized_value=round(min(1, z_score / 3), 4),
            metadata={
                "z_score": z_score,
                "current_vol": current_vol,
                "vol_mean": vol_mean,
                "vol_std": vol_std
            }
        )
    
    def _neutral_result(self) -> AlphaResult:
        return AlphaResult(
            alpha_id=self.alpha_id,
            alpha_name=self.alpha_name,
            direction=AlphaDirection.NEUTRAL,
            strength=0.0,
            confidence=0.0,
            regime_relevance=self.regime_relevance
        )


# ============================================
# 10. Liquidity Sweep Alpha
# ============================================
class LiquiditySweepAlpha(BaseAlpha):
    """
    Детектирует sweep ликвидности.
    Stop hunt patterns at key levels.
    """
    alpha_id = "liquidity_sweep_alpha"
    alpha_name = "Liquidity Sweep"
    description = "Detects liquidity sweeps at key levels"
    regime_relevance = AlphaRegimeRelevance.ALL
    
    def compute(self, market_data: Dict[str, Any]) -> AlphaResult:
        prices = market_data.get("close", [])
        highs = market_data.get("high", [])
        lows = market_data.get("low", [])
        
        if len(prices) < 30:
            return self._neutral_result()
        
        # Find recent swing highs/lows
        recent_high = max(highs[-20:-5])
        recent_low = min(lows[-20:-5])
        
        current_high = highs[-1]
        current_low = lows[-1]
        current_close = prices[-1]
        
        # Detect sweep
        sweep_high = current_high > recent_high and current_close < recent_high
        sweep_low = current_low < recent_low and current_close > recent_low
        
        if sweep_high:
            # Bearish sweep (stop hunt above, reversal down)
            direction = AlphaDirection.SHORT
            sweep_magnitude = (current_high - recent_high) / recent_high * 100
            strength = min(1.0, sweep_magnitude * 2)
        elif sweep_low:
            # Bullish sweep (stop hunt below, reversal up)
            direction = AlphaDirection.LONG
            sweep_magnitude = (recent_low - current_low) / recent_low * 100
            strength = min(1.0, sweep_magnitude * 2)
        else:
            direction = AlphaDirection.NEUTRAL
            sweep_magnitude = 0
            strength = 0.1
        
        confidence = min(1.0, strength * 0.8)
        
        return AlphaResult(
            alpha_id=self.alpha_id,
            alpha_name=self.alpha_name,
            direction=direction,
            strength=round(strength, 4),
            confidence=round(confidence, 4),
            regime_relevance=self.regime_relevance,
            raw_value=sweep_magnitude,
            normalized_value=round(sweep_magnitude / 2, 4) if direction == AlphaDirection.LONG else round(-sweep_magnitude / 2, 4),
            metadata={
                "recent_high": recent_high,
                "recent_low": recent_low,
                "sweep_type": "high_sweep" if sweep_high else "low_sweep" if sweep_low else "none",
                "sweep_magnitude": sweep_magnitude
            }
        )
    
    def _neutral_result(self) -> AlphaResult:
        return AlphaResult(
            alpha_id=self.alpha_id,
            alpha_name=self.alpha_name,
            direction=AlphaDirection.NEUTRAL,
            strength=0.0,
            confidence=0.0,
            regime_relevance=self.regime_relevance
        )


# ============================================
# Alpha Registry
# ============================================
class AlphaRegistry:
    """
    Реестр всех alpha-факторов.
    Singleton pattern для глобального доступа.
    """
    
    _instance: Optional['AlphaRegistry'] = None
    
    def __init__(self):
        self._alphas: Dict[str, BaseAlpha] = {}
        self._register_default_alphas()
    
    @classmethod
    def get_instance(cls) -> 'AlphaRegistry':
        if cls._instance is None:
            cls._instance = AlphaRegistry()
        return cls._instance
    
    def _register_default_alphas(self):
        """Регистрация 10 стандартных alpha-факторов"""
        default_alphas = [
            TrendStrengthAlpha(),
            TrendAccelerationAlpha(),
            TrendExhaustionAlpha(),
            BreakoutPressureAlpha(),
            VolatilityCompressionAlpha(),
            VolatilityExpansionAlpha(),
            ReversalPressureAlpha(),
            VolumeConfirmationAlpha(),
            VolumeAnomalyAlpha(),
            LiquiditySweepAlpha()
        ]
        
        for alpha in default_alphas:
            self._alphas[alpha.alpha_id] = alpha
    
    def register(self, alpha: BaseAlpha):
        """Регистрация нового alpha"""
        self._alphas[alpha.alpha_id] = alpha
    
    def get(self, alpha_id: str) -> Optional[BaseAlpha]:
        """Получение alpha по ID"""
        return self._alphas.get(alpha_id)
    
    def get_all(self) -> List[BaseAlpha]:
        """Получение всех alpha"""
        return list(self._alphas.values())
    
    def get_ids(self) -> List[str]:
        """Получение всех ID"""
        return list(self._alphas.keys())
    
    def compute_all(self, market_data: Dict[str, Any]) -> List[AlphaResult]:
        """Вычисление всех alpha"""
        results = []
        for alpha in self._alphas.values():
            try:
                result = alpha.compute(market_data)
                results.append(result)
            except Exception as e:
                # Return neutral on error
                results.append(AlphaResult(
                    alpha_id=alpha.alpha_id,
                    alpha_name=alpha.alpha_name,
                    direction=AlphaDirection.NEUTRAL,
                    strength=0.0,
                    confidence=0.0,
                    regime_relevance=alpha.regime_relevance,
                    metadata={"error": str(e)}
                ))
        return results
    
    def get_registry_info(self) -> Dict[str, Any]:
        """Информация о реестре"""
        return {
            "total_alphas": len(self._alphas),
            "alphas": [
                {
                    "id": a.alpha_id,
                    "name": a.alpha_name,
                    "description": a.description,
                    "regime_relevance": a.regime_relevance.value
                }
                for a in self._alphas.values()
            ]
        }


def get_alpha_registry() -> AlphaRegistry:
    """Получение singleton экземпляра реестра"""
    return AlphaRegistry.get_instance()
