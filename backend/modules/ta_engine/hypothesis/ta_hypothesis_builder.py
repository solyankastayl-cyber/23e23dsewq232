"""
TA Hypothesis Builder
======================
Phase 14.2 — Builds unified TA hypothesis from indicators.

Architecture:
    TA Indicators (candles, technicals)
           ↓
    TA Hypothesis Builder
           ↓
    TAHypothesis (unified signal)

This module reads price data and computes:
- Trend signals (MA alignment, price position)
- Momentum signals (RSI, MACD)
- Structure signals (HH/HL, BOS)
- Breakout signals

Then combines them into a single TAHypothesis.
"""

import os
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timezone
import math

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from modules.ta_engine.hypothesis.ta_hypothesis_types import (
    TAHypothesis,
    TADirection,
    MarketRegime,
    SetupType,
    TrendSignal,
    MomentumSignal,
    StructureSignal,
    BreakoutSignal,
)
from modules.ta_engine.hypothesis.ta_hypothesis_rules import (
    CONVICTION_WEIGHTS,
    DRIVER_WEIGHTS,
    TREND_THRESHOLDS,
    MOMENTUM_THRESHOLDS,
    STRUCTURE_THRESHOLDS,
    REGIME_FIT_MATRIX,
    DIRECTION_THRESHOLD,
    SETUP_QUALITY_THRESHOLD,
)

# MongoDB
from pymongo import MongoClient, DESCENDING

MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.environ.get("DB_NAME", "ta_engine")


class TAHypothesisBuilder:
    """
    Builds unified TA hypothesis from market data.
    
    Reads candles and computes:
    - Trend (MA alignment)
    - Momentum (RSI, MACD)
    - Structure (swing analysis)
    - Breakout detection
    
    Returns single TAHypothesis for Trading Layer.
    """
    
    def __init__(self):
        self.client = MongoClient(MONGO_URL)
        self.db = self.client[DB_NAME]
    
    def build(self, symbol: str, timeframe: str = "1d") -> TAHypothesis:
        """
        Build unified TA hypothesis for symbol.
        
        Args:
            symbol: Trading pair (BTC, ETH, SOL)
            timeframe: Candle timeframe
        
        Returns:
            TAHypothesis with all components
        """
        # Get candles
        candles = self._get_candles(symbol, timeframe, limit=200)
        
        if len(candles) < 50:
            return self._empty_hypothesis(symbol)
        
        # Build component signals
        trend_signal = self._compute_trend(candles)
        momentum_signal = self._compute_momentum(candles)
        structure_signal = self._compute_structure(candles)
        breakout_signal = self._compute_breakout(candles)
        
        # Compute drivers
        drivers = self._compute_drivers(
            trend_signal, momentum_signal, structure_signal, breakout_signal
        )
        
        # Compute direction
        direction = self._compute_direction(drivers)
        
        # Detect regime
        regime = self._detect_regime(candles, trend_signal)
        
        # Determine setup type
        setup_type = self._determine_setup_type(
            trend_signal, momentum_signal, structure_signal, breakout_signal
        )
        
        # Compute quality scores
        setup_quality = self._compute_setup_quality(
            trend_signal, momentum_signal, structure_signal, breakout_signal
        )
        trend_strength = trend_signal.strength
        entry_quality = self._compute_entry_quality(candles, trend_signal)
        regime_fit = self._compute_regime_fit(setup_type, regime)
        
        # Compute final conviction
        conviction = self._compute_conviction(
            setup_quality, trend_strength, entry_quality, regime_fit
        )
        
        # Sprint 1: Compute REAL price levels from candle data
        current_price, entry_price, stop_price, target_price = self._compute_price_levels(
            candles, direction, structure_signal, breakout_signal
        )
        
        return TAHypothesis(
            symbol=symbol,
            direction=direction,
            setup_quality=setup_quality,
            setup_type=setup_type,
            trend_strength=trend_strength,
            entry_quality=entry_quality,
            regime_fit=regime_fit,
            conviction=conviction,
            regime=regime,
            current_price=current_price,
            entry_price=entry_price,
            stop_price=stop_price,
            target_price=target_price,
            timeframe=timeframe,
            drivers=drivers,
            trend_signal=trend_signal,
            momentum_signal=momentum_signal,
            structure_signal=structure_signal,
            breakout_signal=breakout_signal,
            timestamp=datetime.now(timezone.utc),
        )
    
    def _get_candles(self, symbol: str, timeframe: str, limit: int) -> List[Dict]:
        """Get candles from MongoDB."""
        cursor = self.db.candles.find(
            {"symbol": symbol, "timeframe": timeframe},
            {"_id": 0}
        ).sort("timestamp", DESCENDING).limit(limit)
        candles = list(cursor)
        return list(reversed(candles))  # Oldest first
    
    def _empty_hypothesis(self, symbol: str) -> TAHypothesis:
        """Return empty hypothesis when data is insufficient."""
        return TAHypothesis(
            symbol=symbol,
            direction=TADirection.NEUTRAL,
            setup_quality=0.0,
            setup_type=SetupType.NO_SETUP,
            trend_strength=0.0,
            entry_quality=0.0,
            regime_fit=0.5,
            conviction=0.0,
            regime=MarketRegime.UNKNOWN,
            drivers={},
        )
    
    # ═══════════════════════════════════════════════════════════════
    # TREND ANALYSIS
    # ═══════════════════════════════════════════════════════════════
    
    def _compute_trend(self, candles: List[Dict]) -> TrendSignal:
        """Compute trend signal from MA analysis."""
        closes = [c["close"] for c in candles]
        
        # Calculate MAs
        ma20 = self._sma(closes, 20)
        ma50 = self._sma(closes, 50)
        ma200 = self._sma(closes, 200) if len(closes) >= 200 else ma50
        
        current_price = closes[-1]
        
        # MA alignment score (-1 to 1)
        alignment_score = 0.0
        if ma20 > ma50:
            alignment_score += 0.5
        else:
            alignment_score -= 0.5
        
        if ma50 > ma200:
            alignment_score += 0.5
        else:
            alignment_score -= 0.5
        
        # Price position relative to MAs
        price_position = 0.0
        if current_price > ma20:
            price_position += 0.33
        if current_price > ma50:
            price_position += 0.33
        if current_price > ma200:
            price_position += 0.34
        
        price_position = price_position * 2 - 1  # Normalize to -1 to 1
        
        # Trend strength (0-1)
        trend_strength = abs(alignment_score)
        
        # Direction
        if alignment_score > TREND_THRESHOLDS["ma_alignment_bullish"]:
            direction = TADirection.LONG
        elif alignment_score < TREND_THRESHOLDS["ma_alignment_bearish"]:
            direction = TADirection.SHORT
        else:
            direction = TADirection.NEUTRAL
        
        return TrendSignal(
            direction=direction,
            strength=trend_strength,
            ma_alignment=alignment_score,
            price_position=price_position,
            confidence=0.8,
        )
    
    # ═══════════════════════════════════════════════════════════════
    # MOMENTUM ANALYSIS
    # ═══════════════════════════════════════════════════════════════
    
    def _compute_momentum(self, candles: List[Dict]) -> MomentumSignal:
        """Compute momentum signal from RSI and MACD."""
        closes = [c["close"] for c in candles]
        
        # RSI
        rsi = self._rsi(closes, 14)
        
        # MACD
        macd_line, signal_line, histogram = self._macd(closes)
        
        # Direction from RSI
        if rsi > MOMENTUM_THRESHOLDS["rsi_bullish"]:
            direction = TADirection.LONG
        elif rsi < MOMENTUM_THRESHOLDS["rsi_bearish"]:
            direction = TADirection.SHORT
        else:
            direction = TADirection.NEUTRAL
        
        # Strength
        if rsi > 70 or rsi < 30:
            strength = 0.9
        elif rsi > 60 or rsi < 40:
            strength = 0.7
        else:
            strength = 0.5
        
        # Divergence detection (simplified)
        divergence = self._detect_divergence(closes, rsi)
        
        return MomentumSignal(
            direction=direction,
            strength=strength,
            rsi_value=rsi,
            macd_histogram=histogram,
            momentum_divergence=divergence,
            confidence=0.75,
        )
    
    # ═══════════════════════════════════════════════════════════════
    # STRUCTURE ANALYSIS
    # ═══════════════════════════════════════════════════════════════
    
    def _compute_structure(self, candles: List[Dict]) -> StructureSignal:
        """Compute market structure signal."""
        highs = [c["high"] for c in candles]
        lows = [c["low"] for c in candles]
        
        # Find swing points (last 20 candles)
        swing_highs = self._find_swing_highs(highs[-20:])
        swing_lows = self._find_swing_lows(lows[-20:])
        
        # Higher highs / higher lows
        higher_highs = False
        higher_lows = False
        
        if len(swing_highs) >= 2:
            higher_highs = swing_highs[-1] > swing_highs[-2]
        
        if len(swing_lows) >= 2:
            higher_lows = swing_lows[-1] > swing_lows[-2]
        
        # BOS and ChoCh detection (simplified)
        recent_bos = self._detect_bos(highs, lows)
        recent_choch = self._detect_choch(highs, lows)
        
        # Structure score
        score = 0.0
        if higher_highs:
            score += 0.25
        if higher_lows:
            score += 0.25
        if higher_highs and higher_lows:
            score += 0.25
        if recent_bos:
            score += 0.25
        
        # Adjust for bearish structure
        if not higher_highs and not higher_lows:
            score = -score if score > 0 else score
        
        # Bias
        if score > STRUCTURE_THRESHOLDS["bullish_structure"]:
            bias = TADirection.LONG
        elif score < STRUCTURE_THRESHOLDS["bearish_structure"]:
            bias = TADirection.SHORT
        else:
            bias = TADirection.NEUTRAL
        
        return StructureSignal(
            bias=bias,
            structure_score=abs(score),
            higher_highs=higher_highs,
            higher_lows=higher_lows,
            recent_bos=recent_bos,
            recent_choch=recent_choch,
            confidence=0.7,
        )
    
    # ═══════════════════════════════════════════════════════════════
    # BREAKOUT ANALYSIS
    # ═══════════════════════════════════════════════════════════════
    
    def _compute_breakout(self, candles: List[Dict]) -> BreakoutSignal:
        """Compute breakout signal."""
        closes = [c["close"] for c in candles]
        highs = [c["high"] for c in candles]
        lows = [c["low"] for c in candles]
        volumes = [c.get("volume", 0) for c in candles]
        
        # Find recent range (last 20 candles)
        range_high = max(highs[-20:])
        range_low = min(lows[-20:])
        current_price = closes[-1]
        
        # Breakout detection
        detected = False
        direction = TADirection.NEUTRAL
        
        if current_price > range_high:
            detected = True
            direction = TADirection.LONG
        elif current_price < range_low:
            detected = True
            direction = TADirection.SHORT
        
        # Breakout strength
        if detected:
            range_size = range_high - range_low
            breakout_distance = abs(current_price - (range_high if direction == TADirection.LONG else range_low))
            strength = min(breakout_distance / max(range_size, 1e-8), 1.0)
        else:
            strength = 0.0
        
        # Volume confirmation
        avg_volume = sum(volumes[-20:]) / 20 if volumes else 0
        current_volume = volumes[-1] if volumes else 0
        volume_confirmation = current_volume > avg_volume * 1.5
        
        # Level quality (how many times tested)
        level_quality = min(self._count_level_tests(highs, lows, range_high, range_low) / 3, 1.0)
        
        return BreakoutSignal(
            detected=detected,
            direction=direction,
            strength=strength,
            volume_confirmation=volume_confirmation,
            level_quality=level_quality,
            confidence=0.7 if detected else 0.5,
        )
    
    # ═══════════════════════════════════════════════════════════════
    # COMPOSITE CALCULATIONS
    # ═══════════════════════════════════════════════════════════════
    
    def _compute_drivers(
        self,
        trend: TrendSignal,
        momentum: MomentumSignal,
        structure: StructureSignal,
        breakout: BreakoutSignal,
    ) -> Dict[str, float]:
        """Compute driver scores for direction."""
        drivers = {}
        
        # Trend score: -1 to 1
        drivers["trend"] = trend.direction.to_numeric() * trend.strength
        
        # Momentum score: -1 to 1
        drivers["momentum"] = momentum.direction.to_numeric() * momentum.strength
        
        # Structure score: -1 to 1
        drivers["structure"] = structure.bias.to_numeric() * structure.structure_score
        
        # Breakout score: -1 to 1
        drivers["breakout"] = breakout.direction.to_numeric() * breakout.strength
        
        return drivers
    
    def _compute_direction(self, drivers: Dict[str, float]) -> TADirection:
        """Compute overall direction from drivers."""
        weighted_score = sum(
            drivers.get(k, 0) * DRIVER_WEIGHTS.get(k, 0)
            for k in DRIVER_WEIGHTS
        )
        
        if weighted_score > DIRECTION_THRESHOLD:
            return TADirection.LONG
        elif weighted_score < -DIRECTION_THRESHOLD:
            return TADirection.SHORT
        return TADirection.NEUTRAL
    
    def _detect_regime(self, candles: List[Dict], trend: TrendSignal) -> MarketRegime:
        """Detect current market regime."""
        closes = [c["close"] for c in candles]
        
        # ATR for volatility
        atr = self._atr(candles, 14)
        avg_price = sum(closes[-14:]) / 14
        volatility = atr / max(avg_price, 1e-8)
        
        # Recent price range
        recent_range = (max(closes[-14:]) - min(closes[-14:])) / max(avg_price, 1e-8)
        
        # Determine regime
        if trend.strength > 0.7 and trend.direction == TADirection.LONG:
            return MarketRegime.TREND_UP
        elif trend.strength > 0.7 and trend.direction == TADirection.SHORT:
            return MarketRegime.TREND_DOWN
        elif volatility > 0.03:
            return MarketRegime.EXPANSION
        elif recent_range < 0.02:
            return MarketRegime.COMPRESSION
        else:
            return MarketRegime.RANGE
    
    def _determine_setup_type(
        self,
        trend: TrendSignal,
        momentum: MomentumSignal,
        structure: StructureSignal,
        breakout: BreakoutSignal,
    ) -> SetupType:
        """Determine type of trading setup."""
        if breakout.detected and breakout.strength > 0.5:
            return SetupType.BREAKOUT
        
        if trend.strength > 0.6:
            if momentum.momentum_divergence:
                return SetupType.REVERSAL
            return SetupType.CONTINUATION
        
        if structure.recent_choch:
            return SetupType.REVERSAL
        
        if structure.structure_score < 0.3 and trend.strength < 0.3:
            return SetupType.RANGE_TRADE
        
        if trend.strength > 0.4 and momentum.strength < 0.5:
            return SetupType.PULLBACK
        
        return SetupType.NO_SETUP
    
    def _compute_setup_quality(
        self,
        trend: TrendSignal,
        momentum: MomentumSignal,
        structure: StructureSignal,
        breakout: BreakoutSignal,
    ) -> float:
        """Compute overall setup quality."""
        quality = 0.0
        
        # Trend alignment
        quality += trend.strength * 0.3
        
        # Structure clarity
        quality += structure.structure_score * 0.25
        
        # Momentum confirmation
        if trend.direction == momentum.direction:
            quality += momentum.strength * 0.25
        else:
            quality += momentum.strength * 0.1
        
        # Breakout bonus
        if breakout.detected:
            quality += breakout.strength * 0.2
        
        return min(quality, 1.0)
    
    def _compute_entry_quality(self, candles: List[Dict], trend: TrendSignal) -> float:
        """Compute entry timing quality."""
        closes = [c["close"] for c in candles]
        
        # Distance from MA20 (pullback entry is better)
        ma20 = self._sma(closes, 20)
        current_price = closes[-1]
        distance = abs(current_price - ma20) / max(ma20, 1e-8)
        
        # Optimal distance is 1-3%
        if 0.01 < distance < 0.03:
            distance_score = 1.0
        elif distance < 0.05:
            distance_score = 0.7
        else:
            distance_score = 0.4
        
        # Volatility consideration
        atr = self._atr(candles, 14)
        volatility = atr / max(closes[-1], 1e-8)
        
        if 0.02 < volatility < 0.04:
            volatility_score = 1.0
        elif volatility < 0.06:
            volatility_score = 0.7
        else:
            volatility_score = 0.4
        
        return (distance_score + volatility_score) / 2
    
    def _compute_regime_fit(self, setup_type: SetupType, regime: MarketRegime) -> float:
        """Compute how well setup fits current regime."""
        fit_matrix = REGIME_FIT_MATRIX.get(setup_type.value, {})
        return fit_matrix.get(regime.value, 0.5)
    
    def _compute_conviction(
        self,
        setup_quality: float,
        trend_strength: float,
        entry_quality: float,
        regime_fit: float,
    ) -> float:
        """Compute final conviction score."""
        return (
            setup_quality * CONVICTION_WEIGHTS["setup_quality"]
            + trend_strength * CONVICTION_WEIGHTS["trend_strength"]
            + entry_quality * CONVICTION_WEIGHTS["entry_quality"]
            + regime_fit * CONVICTION_WEIGHTS["regime_fit"]
        )
    
    # ═══════════════════════════════════════════════════════════════
    # PRICE LEVELS — Sprint 1: Canonical Decision Contract
    # ═══════════════════════════════════════════════════════════════
    
    def _compute_price_levels(
        self,
        candles: List[Dict],
        direction: 'TADirection',
        structure: 'StructureSignal',
        breakout: 'BreakoutSignal',
    ) -> Tuple[float, float, float, float]:
        """
        Compute real entry/stop/target from candle data.
        
        Uses ATR-based stop and R:R ratio for target.
        Returns: (current_price, entry_price, stop_price, target_price)
        """
        closes = [c["close"] for c in candles]
        highs = [c["high"] for c in candles]
        lows = [c["low"] for c in candles]
        
        current_price = closes[-1]
        
        # Compute ATR(14) for stop distance
        atr = self._compute_atr(highs, lows, closes, period=14)
        
        if direction == TADirection.LONG:
            entry_price = current_price
            stop_price = current_price - (atr * 1.5)
            target_price = current_price + (atr * 3.0)  # 2:1 R:R
            
            # Tighten stop to recent swing low if available
            recent_lows = lows[-10:]
            swing_low = min(recent_lows)
            if swing_low < current_price and (current_price - swing_low) < (atr * 2.5):
                stop_price = swing_low - (atr * 0.2)  # buffer below swing
            
        elif direction == TADirection.SHORT:
            entry_price = current_price
            stop_price = current_price + (atr * 1.5)
            target_price = current_price - (atr * 3.0)  # 2:1 R:R
            
            # Tighten stop to recent swing high if available
            recent_highs = highs[-10:]
            swing_high = max(recent_highs)
            if swing_high > current_price and (swing_high - current_price) < (atr * 2.5):
                stop_price = swing_high + (atr * 0.2)  # buffer above swing
        else:
            # NEUTRAL — no trade
            entry_price = current_price
            stop_price = current_price
            target_price = current_price
        
        return (
            round(current_price, 2),
            round(entry_price, 2),
            round(stop_price, 2),
            round(target_price, 2),
        )
    
    def _compute_atr(self, highs: List[float], lows: List[float], closes: List[float], period: int = 14) -> float:
        """Compute Average True Range."""
        if len(highs) < period + 1:
            # Fallback: simple range
            return (max(highs[-period:]) - min(lows[-period:])) / period if highs else 1.0
        
        true_ranges = []
        for i in range(1, len(highs)):
            tr = max(
                highs[i] - lows[i],
                abs(highs[i] - closes[i - 1]),
                abs(lows[i] - closes[i - 1]),
            )
            true_ranges.append(tr)
        
        if len(true_ranges) < period:
            return sum(true_ranges) / len(true_ranges) if true_ranges else 1.0
        
        return sum(true_ranges[-period:]) / period
    
    # ═══════════════════════════════════════════════════════════════
    # TECHNICAL HELPERS
    # ═══════════════════════════════════════════════════════════════
    
    def _sma(self, data: List[float], period: int) -> float:
        """Simple Moving Average."""
        if len(data) < period:
            return sum(data) / len(data) if data else 0
        return sum(data[-period:]) / period
    
    def _ema(self, data: List[float], period: int) -> float:
        """Exponential Moving Average."""
        if not data:
            return 0
        multiplier = 2 / (period + 1)
        ema = data[0]
        for price in data[1:]:
            ema = (price * multiplier) + (ema * (1 - multiplier))
        return ema
    
    def _rsi(self, closes: List[float], period: int = 14) -> float:
        """Relative Strength Index."""
        if len(closes) < period + 1:
            return 50.0
        
        gains = []
        losses = []
        
        for i in range(1, len(closes)):
            change = closes[i] - closes[i-1]
            if change > 0:
                gains.append(change)
                losses.append(0)
            else:
                gains.append(0)
                losses.append(abs(change))
        
        avg_gain = sum(gains[-period:]) / period
        avg_loss = sum(losses[-period:]) / period
        
        if avg_loss == 0:
            return 100.0
        
        rs = avg_gain / avg_loss
        return 100 - (100 / (1 + rs))
    
    def _macd(self, closes: List[float]) -> Tuple[float, float, float]:
        """MACD indicator."""
        if len(closes) < 26:
            return 0, 0, 0
        
        ema12 = self._ema(closes, 12)
        ema26 = self._ema(closes, 26)
        macd_line = ema12 - ema26
        signal_line = self._ema([macd_line], 9)  # Simplified
        histogram = macd_line - signal_line
        
        return macd_line, signal_line, histogram
    
    def _atr(self, candles: List[Dict], period: int = 14) -> float:
        """Average True Range."""
        if len(candles) < period + 1:
            return 0
        
        trs = []
        for i in range(1, len(candles)):
            high = candles[i]["high"]
            low = candles[i]["low"]
            prev_close = candles[i-1]["close"]
            
            tr = max(
                high - low,
                abs(high - prev_close),
                abs(low - prev_close)
            )
            trs.append(tr)
        
        return sum(trs[-period:]) / period
    
    def _find_swing_highs(self, highs: List[float], lookback: int = 3) -> List[float]:
        """Find swing high points."""
        swings = []
        for i in range(lookback, len(highs) - lookback):
            if all(highs[i] > highs[i-j] for j in range(1, lookback + 1)):
                if all(highs[i] > highs[i+j] for j in range(1, min(lookback + 1, len(highs) - i))):
                    swings.append(highs[i])
        return swings
    
    def _find_swing_lows(self, lows: List[float], lookback: int = 3) -> List[float]:
        """Find swing low points."""
        swings = []
        for i in range(lookback, len(lows) - lookback):
            if all(lows[i] < lows[i-j] for j in range(1, lookback + 1)):
                if all(lows[i] < lows[i+j] for j in range(1, min(lookback + 1, len(lows) - i))):
                    swings.append(lows[i])
        return swings
    
    def _detect_bos(self, highs: List[float], lows: List[float]) -> bool:
        """Detect break of structure."""
        if len(highs) < 10:
            return False
        recent_high = max(highs[-10:-1])
        recent_low = min(lows[-10:-1])
        current = highs[-1]
        return current > recent_high or lows[-1] < recent_low
    
    def _detect_choch(self, highs: List[float], lows: List[float]) -> bool:
        """Detect change of character."""
        # Simplified: significant reversal
        if len(highs) < 15:
            return False
        
        prev_trend = highs[-15] - highs[-10]
        current_trend = highs[-5] - highs[-1]
        
        return (prev_trend > 0 and current_trend < 0) or (prev_trend < 0 and current_trend > 0)
    
    def _detect_divergence(self, closes: List[float], rsi: float) -> bool:
        """Detect RSI divergence."""
        if len(closes) < 20:
            return False
        
        # Price making new high but RSI not
        price_higher = closes[-1] > max(closes[-20:-1])
        
        # Simplified divergence check
        if price_higher and rsi < 70:
            return True
        
        price_lower = closes[-1] < min(closes[-20:-1])
        if price_lower and rsi > 30:
            return True
        
        return False
    
    def _count_level_tests(
        self,
        highs: List[float],
        lows: List[float],
        level_high: float,
        level_low: float,
        tolerance: float = 0.01,
    ) -> int:
        """Count how many times price tested a level."""
        tests = 0
        for h, l in zip(highs[-20:], lows[-20:]):
            if abs(h - level_high) / max(level_high, 1e-8) < tolerance:
                tests += 1
            if abs(l - level_low) / max(level_low, 1e-8) < tolerance:
                tests += 1
        return tests


# Singleton
_builder: Optional[TAHypothesisBuilder] = None


def get_hypothesis_builder() -> TAHypothesisBuilder:
    """Get singleton builder instance."""
    global _builder
    if _builder is None:
        _builder = TAHypothesisBuilder()
    return _builder
