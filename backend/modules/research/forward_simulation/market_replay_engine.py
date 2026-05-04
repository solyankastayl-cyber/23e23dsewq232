"""
Market Replay Engine
====================

Candle-by-candle market replay (PHASE 2.3)
"""

import time
import random
import math
from typing import Dict, List, Optional, Any, Generator

from .forward_types import Candle, MarketScenario


class MarketReplayEngine:
    """
    Replays market data candle by candle.
    
    Generates or loads historical candles and
    yields them one at a time to simulate real-time market.
    """
    
    def __init__(self):
        # Scenario parameters
        self._scenarios = {
            MarketScenario.BTC_2017_BULL: {
                "base_price": 1000,
                "end_price": 19000,
                "volatility": 0.04,
                "trend": 0.015,
                "regime_sequence": ["TRENDING", "TRENDING", "HIGH_VOLATILITY"]
            },
            MarketScenario.BTC_2018_BEAR: {
                "base_price": 19000,
                "end_price": 3200,
                "volatility": 0.05,
                "trend": -0.012,
                "regime_sequence": ["HIGH_VOLATILITY", "TRENDING", "RANGE"]
            },
            MarketScenario.BTC_2020_CRASH: {
                "base_price": 10000,
                "end_price": 4000,
                "volatility": 0.08,
                "trend": -0.025,
                "regime_sequence": ["HIGH_VOLATILITY", "HIGH_VOLATILITY", "RANGE"]
            },
            MarketScenario.BTC_2021_BULL: {
                "base_price": 10000,
                "end_price": 69000,
                "volatility": 0.05,
                "trend": 0.018,
                "regime_sequence": ["TRENDING", "HIGH_VOLATILITY", "TRENDING"]
            },
            MarketScenario.BTC_2022_BEAR: {
                "base_price": 69000,
                "end_price": 16000,
                "volatility": 0.04,
                "trend": -0.01,
                "regime_sequence": ["TRENDING", "HIGH_VOLATILITY", "RANGE"]
            },
            MarketScenario.ETH_2021_DEFI: {
                "base_price": 700,
                "end_price": 4800,
                "volatility": 0.06,
                "trend": 0.016,
                "regime_sequence": ["TRENDING", "HIGH_VOLATILITY", "TRENDING"]
            }
        }
        
        print("[MarketReplayEngine] Initialized (PHASE 2.3)")
    
    def generate_candles(
        self,
        scenario: MarketScenario,
        count: int = 500,
        timeframe: str = "4h"
    ) -> List[Candle]:
        """
        Generate synthetic candles for a scenario.
        """
        
        params = self._scenarios.get(scenario)
        if not params:
            # Default/custom scenario
            params = {
                "base_price": 40000,
                "end_price": 45000,
                "volatility": 0.03,
                "trend": 0.002,
                "regime_sequence": ["RANGE", "TRENDING", "RANGE"]
            }
        
        candles = []
        price = params["base_price"]
        
        # Timeframe to milliseconds
        tf_ms = self._timeframe_to_ms(timeframe)
        base_timestamp = int(time.time() * 1000) - (count * tf_ms)
        
        for i in range(count):
            # Determine current regime phase
            phase = min(2, i * 3 // count)
            regime = params["regime_sequence"][phase]
            
            # Adjust volatility by regime
            vol = params["volatility"]
            if regime == "HIGH_VOLATILITY":
                vol *= 1.5
            elif regime == "LOW_VOLATILITY":
                vol *= 0.5
            elif regime == "RANGE":
                vol *= 0.8
            
            # Generate OHLCV
            change = random.gauss(params["trend"], vol)
            
            open_price = price
            close_price = price * (1 + change)
            
            # High/Low based on volatility
            high_mult = 1 + abs(random.gauss(0, vol * 0.5))
            low_mult = 1 - abs(random.gauss(0, vol * 0.5))
            
            if change > 0:
                high_price = close_price * high_mult
                low_price = open_price * low_mult
            else:
                high_price = open_price * high_mult
                low_price = close_price * low_mult
            
            # Ensure high >= max(open, close) and low <= min(open, close)
            high_price = max(high_price, open_price, close_price)
            low_price = min(low_price, open_price, close_price)
            
            volume = random.uniform(100, 1000) * (price / 10000)
            
            candles.append(Candle(
                timestamp=base_timestamp + (i * tf_ms),
                open=open_price,
                high=high_price,
                low=low_price,
                close=close_price,
                volume=volume
            ))
            
            price = close_price
        
        return candles
    
    def replay(
        self,
        candles: List[Candle],
        delay_ms: int = 0
    ) -> Generator[Candle, None, None]:
        """
        Yield candles one by one, simulating real-time feed.
        """
        for candle in candles:
            if delay_ms > 0:
                time.sleep(delay_ms / 1000)
            yield candle
    
    def get_current_regime(
        self,
        candles: List[Candle],
        lookback: int = 20
    ) -> str:
        """
        Determine current market regime from recent candles.
        """
        
        if len(candles) < lookback:
            return "RANGE"
        
        recent = candles[-lookback:]
        
        # Calculate returns
        returns = []
        for i in range(1, len(recent)):
            r = (recent[i].close - recent[i-1].close) / recent[i-1].close
            returns.append(r)
        
        # Volatility
        avg_return = sum(returns) / len(returns)
        variance = sum((r - avg_return) ** 2 for r in returns) / len(returns)
        volatility = math.sqrt(variance)
        
        # Trend strength (simple linear regression slope)
        prices = [c.close for c in recent]
        n = len(prices)
        x_sum = sum(range(n))
        y_sum = sum(prices)
        xy_sum = sum(i * p for i, p in enumerate(prices))
        x2_sum = sum(i ** 2 for i in range(n))
        
        slope = (n * xy_sum - x_sum * y_sum) / (n * x2_sum - x_sum ** 2) if (n * x2_sum - x_sum ** 2) != 0 else 0
        trend_strength = abs(slope / prices[0]) if prices[0] != 0 else 0
        
        # Range detection (price oscillation)
        high = max(prices)
        low = min(prices)
        range_pct = (high - low) / low if low > 0 else 0
        
        # Determine regime
        if volatility > 0.04:
            return "HIGH_VOLATILITY"
        elif volatility < 0.015:
            return "LOW_VOLATILITY"
        elif trend_strength > 0.003:
            return "TRENDING"
        elif range_pct < 0.08:
            return "RANGE"
        else:
            return "TRANSITION"
    
    def calculate_indicators(
        self,
        candles: List[Candle]
    ) -> Dict[str, float]:
        """
        Calculate basic indicators from candles.
        """
        
        if len(candles) < 20:
            return {}
        
        closes = [c.close for c in candles]
        
        # SMA 20
        sma20 = sum(closes[-20:]) / 20
        
        # SMA 50 (if available)
        sma50 = sum(closes[-50:]) / 50 if len(closes) >= 50 else sma20
        
        # RSI 14
        rsi = self._calculate_rsi(closes, 14)
        
        # ATR 14
        atr = self._calculate_atr(candles, 14)
        
        # MACD
        macd, signal, hist = self._calculate_macd(closes)
        
        return {
            "sma20": sma20,
            "sma50": sma50,
            "rsi": rsi,
            "atr": atr,
            "macd": macd,
            "macdSignal": signal,
            "macdHist": hist,
            "close": closes[-1]
        }
    
    def _calculate_rsi(self, prices: List[float], period: int = 14) -> float:
        """Calculate RSI"""
        if len(prices) < period + 1:
            return 50.0
        
        gains = []
        losses = []
        
        for i in range(1, len(prices)):
            change = prices[i] - prices[i-1]
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
        rsi = 100 - (100 / (1 + rs))
        
        return rsi
    
    def _calculate_atr(self, candles: List[Candle], period: int = 14) -> float:
        """Calculate ATR"""
        if len(candles) < period + 1:
            return 0.0
        
        true_ranges = []
        for i in range(1, len(candles)):
            high = candles[i].high
            low = candles[i].low
            prev_close = candles[i-1].close
            
            tr = max(
                high - low,
                abs(high - prev_close),
                abs(low - prev_close)
            )
            true_ranges.append(tr)
        
        atr = sum(true_ranges[-period:]) / period
        return atr
    
    def _calculate_macd(
        self,
        prices: List[float],
        fast: int = 12,
        slow: int = 26,
        signal: int = 9
    ):
        """Calculate MACD"""
        if len(prices) < slow:
            return 0.0, 0.0, 0.0
        
        # EMA calculation
        def ema(data, period):
            if len(data) < period:
                return data[-1]
            multiplier = 2 / (period + 1)
            ema_val = sum(data[:period]) / period
            for price in data[period:]:
                ema_val = (price - ema_val) * multiplier + ema_val
            return ema_val
        
        ema_fast = ema(prices, fast)
        ema_slow = ema(prices, slow)
        
        macd_line = ema_fast - ema_slow
        
        # Simple signal line approximation
        signal_line = macd_line * 0.9
        histogram = macd_line - signal_line
        
        return macd_line, signal_line, histogram
    
    def _timeframe_to_ms(self, tf: str) -> int:
        """Convert timeframe string to milliseconds"""
        multipliers = {
            "1m": 60 * 1000,
            "5m": 5 * 60 * 1000,
            "15m": 15 * 60 * 1000,
            "1h": 60 * 60 * 1000,
            "4h": 4 * 60 * 60 * 1000,
            "1d": 24 * 60 * 60 * 1000
        }
        return multipliers.get(tf.lower(), 4 * 60 * 60 * 1000)
    
    def get_scenario_info(self, scenario: MarketScenario) -> Dict[str, Any]:
        """Get info about a scenario"""
        params = self._scenarios.get(scenario, {})
        return {
            "scenario": scenario.value,
            "basePrice": params.get("base_price", 40000),
            "endPrice": params.get("end_price", 45000),
            "volatility": params.get("volatility", 0.03),
            "trend": params.get("trend", 0.002),
            "regimes": params.get("regime_sequence", ["RANGE"])
        }


# Global singleton
market_replay_engine = MarketReplayEngine()
