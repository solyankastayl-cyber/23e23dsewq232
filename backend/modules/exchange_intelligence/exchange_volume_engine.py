"""
PHASE 13.8 — Exchange Volume Engine
=====================================
Analyzes volume anomalies, breakout confirmation, exhaustion detection.

Output: VolumeContextSignal
"""

import math
from datetime import datetime, timezone
from typing import List, Dict, Optional

from .exchange_intel_types import VolumeContextSignal, VolumeState
from .exchange_intel_repository import ExchangeIntelRepository


# ── Thresholds ──────────────────────────────────

VOLUME_BREAKOUT_RATIO = 2.0   # 2x avg = breakout volume
VOLUME_CLIMAX_RATIO = 3.0     # 3x avg = climax
VOLUME_LOW_RATIO = 0.5        # <50% avg = abnormally low
EXHAUSTION_BARS = 3            # consecutive high vol + declining price = exhaustion
ANOMALY_ZSCORE = 2.0


class ExchangeVolumeEngine:
    """Computes volume context signals."""

    def __init__(self, repo: Optional[ExchangeIntelRepository] = None):
        self.repo = repo or ExchangeIntelRepository()

    def compute(self, symbol: str, exchange_data: Optional[Dict] = None) -> VolumeContextSignal:
        now = datetime.now(timezone.utc)

        if exchange_data:
            return self._from_exchange_data(symbol, exchange_data, now)

        candles = self.repo.get_candles(symbol, "1d", limit=60)
        if len(candles) < 10:
            return self._empty_signal(symbol, now)

        return self._from_candles(symbol, candles, now)

    def _from_candles(self, symbol: str, candles: List[Dict], now: datetime) -> VolumeContextSignal:
        volumes = [c.get("volume", 0) for c in candles]
        closes = [c.get("close", 0) for c in candles]

        # Moving average volume (20-period)
        lookback = min(20, len(volumes) - 1)
        avg_vol = sum(volumes[-lookback - 1:-1]) / max(lookback, 1)
        current_vol = volumes[-1]

        # Volume ratio
        vol_ratio = current_vol / max(avg_vol, 1e-8)

        # Buy volume proxy
        buy_vol_pct = self._estimate_buy_volume(candles[-5:])

        # Volume trend (last 5 vs prior 5)
        if len(volumes) >= 10:
            recent_avg = sum(volumes[-5:]) / 5
            prior_avg = sum(volumes[-10:-5]) / 5
            if prior_avg > 0:
                trend_ratio = recent_avg / prior_avg
                if trend_ratio > 1.2:
                    trend = "INCREASING"
                elif trend_ratio < 0.8:
                    trend = "DECREASING"
                else:
                    trend = "FLAT"
            else:
                trend = "FLAT"
        else:
            trend = "FLAT"

        # Anomaly score (z-score based)
        anomaly = self._compute_anomaly_score(volumes)

        # Classify state
        state = self._classify_state(vol_ratio, candles, closes)

        # Confidence
        confidence = min(0.5 + len(candles) / 100, 0.85)

        # Drivers
        drivers = []
        if vol_ratio > VOLUME_CLIMAX_RATIO:
            drivers.append("volume_climax")
        elif vol_ratio > VOLUME_BREAKOUT_RATIO:
            drivers.append("volume_breakout")
        elif vol_ratio < VOLUME_LOW_RATIO:
            drivers.append("volume_drought")

        if state == VolumeState.EXHAUSTION:
            drivers.append("exhaustion_pattern")
        if anomaly > 0.7:
            drivers.append("volume_anomaly")
        if trend == "INCREASING":
            drivers.append("volume_trend_up")
        elif trend == "DECREASING":
            drivers.append("volume_trend_down")

        return VolumeContextSignal(
            symbol=symbol,
            timestamp=now,
            volume_24h=current_vol,
            volume_ratio=vol_ratio,
            volume_state=state,
            buy_volume_pct=buy_vol_pct,
            volume_trend=trend,
            anomaly_score=anomaly,
            confidence=confidence,
            drivers=drivers,
        )

    def _from_exchange_data(self, symbol: str, data: Dict, now: datetime) -> VolumeContextSignal:
        vol_ratio = data.get("volume_ratio", 1.0)
        state_str = data.get("volume_state", "NORMAL")
        try:
            state = VolumeState(state_str)
        except ValueError:
            state = VolumeState.NORMAL

        return VolumeContextSignal(
            symbol=symbol,
            timestamp=now,
            volume_24h=data.get("volume_24h", 0),
            volume_ratio=vol_ratio,
            volume_state=state,
            buy_volume_pct=data.get("buy_volume_pct", 0.5),
            volume_trend=data.get("volume_trend", "FLAT"),
            anomaly_score=data.get("anomaly_score", 0.0),
            confidence=0.8,
            drivers=data.get("drivers", []),
        )

    def _estimate_buy_volume(self, candles: List[Dict]) -> float:
        """Estimate buy volume from candle structure."""
        if not candles:
            return 0.5
        buy_volume = 0.0
        total_volume = 0.0
        for c in candles:
            vol = c.get("volume", 0)
            total_volume += vol
            bar_range = c["high"] - c["low"]
            if bar_range > 0:
                buy_pct = (c["close"] - c["low"]) / bar_range
                buy_volume += vol * buy_pct
            else:
                buy_volume += vol * 0.5
        return buy_volume / max(total_volume, 1e-8)

    def _compute_anomaly_score(self, volumes: List[float]) -> float:
        """Z-score based anomaly detection."""
        if len(volumes) < 10:
            return 0.0
        baseline = volumes[:-1]
        current = volumes[-1]
        mean = sum(baseline) / len(baseline)
        std = max((sum((v - mean) ** 2 for v in baseline) / len(baseline)) ** 0.5, 1e-8)
        z = abs(current - mean) / std
        return min(z / ANOMALY_ZSCORE, 1.0)

    def _classify_state(
        self, vol_ratio: float, candles: List[Dict], closes: List[float]
    ) -> VolumeState:
        # Exhaustion: high volume + momentum reversal
        if vol_ratio > VOLUME_BREAKOUT_RATIO and len(candles) >= EXHAUSTION_BARS:
            recent = candles[-EXHAUSTION_BARS:]
            high_vol_count = sum(
                1 for c in recent
                if c.get("volume", 0) > sum(cc.get("volume", 0) for cc in candles[-20:-3]) / max(len(candles) - EXHAUSTION_BARS, 1) * 1.5
            )
            if high_vol_count >= 2:
                price_direction = recent[-1]["close"] - recent[0]["open"]
                prev_direction = candles[-EXHAUSTION_BARS - 1]["close"] - candles[-EXHAUSTION_BARS - 1]["open"] if len(candles) > EXHAUSTION_BARS else 0
                if prev_direction != 0 and price_direction * prev_direction < 0:
                    return VolumeState.EXHAUSTION

        if vol_ratio > VOLUME_CLIMAX_RATIO:
            return VolumeState.CLIMAX
        if vol_ratio > VOLUME_BREAKOUT_RATIO:
            return VolumeState.BREAKOUT_CONFIRMED
        if vol_ratio > 1.5:
            return VolumeState.ABNORMAL_HIGH
        if vol_ratio < VOLUME_LOW_RATIO:
            return VolumeState.ABNORMAL_LOW
        return VolumeState.NORMAL

    def _empty_signal(self, symbol: str, now: datetime) -> VolumeContextSignal:
        return VolumeContextSignal(
            symbol=symbol,
            timestamp=now,
            volume_24h=0,
            volume_ratio=1.0,
            volume_state=VolumeState.NORMAL,
            buy_volume_pct=0.5,
            volume_trend="FLAT",
            anomaly_score=0.0,
            confidence=0.3,
            drivers=["insufficient_data"],
        )
