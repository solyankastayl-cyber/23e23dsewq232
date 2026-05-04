"""
PHASE 13.8 — Derivatives Pressure Engine
==========================================
Analyzes long/short ratio, leverage, squeeze conditions, perp premium.

Output: DerivativesPressureSignal
"""

import math
from datetime import datetime, timezone
from typing import List, Dict, Optional

from .exchange_intel_types import DerivativesPressureSignal, DerivativesPressure
from .exchange_intel_repository import ExchangeIntelRepository


# ── Thresholds ──────────────────────────────────

LS_RATIO_EXTREME = 2.0       # >2 or <0.5 = extreme imbalance
LS_RATIO_ELEVATED = 1.5
LEVERAGE_HIGH = 0.7
SQUEEZE_HIGH = 0.6
PREMIUM_EXTREME = 0.003      # 0.3% perp premium


class DerivativesPressureEngine:
    """Computes derivatives market pressure."""

    def __init__(self, repo: Optional[ExchangeIntelRepository] = None):
        self.repo = repo or ExchangeIntelRepository()

    def compute(self, symbol: str, exchange_data: Optional[Dict] = None) -> DerivativesPressureSignal:
        now = datetime.now(timezone.utc)

        long_short_ratio = 1.0
        leverage_index = 0.3
        perp_premium = 0.0

        if exchange_data:
            long_short_ratio = exchange_data.get("long_short_ratio", 1.0)
            leverage_index = exchange_data.get("leverage_index", 0.3)
            perp_premium = exchange_data.get("perp_premium", 0.0)
        else:
            snapshot = self.repo.get_symbol_snapshot(symbol)
            if snapshot:
                long_short_ratio = snapshot.get("long_short_ratio", 1.0)
                leverage_index = snapshot.get("leverage_index", 0.3)
                perp_premium = snapshot.get("perp_premium", 0.0)
            else:
                candles = self.repo.get_candles(symbol, "1d", limit=14)
                if len(candles) >= 7:
                    derived = self._derive_from_candles(candles)
                    long_short_ratio = derived["long_short_ratio"]
                    leverage_index = derived["leverage_index"]
                    perp_premium = derived["perp_premium"]

        # Squeeze probability
        squeeze_prob = self._compute_squeeze_probability(
            long_short_ratio, leverage_index, perp_premium
        )

        # Classify state
        state = self._classify_state(long_short_ratio, leverage_index, squeeze_prob)

        # Confidence
        confidence = 0.5 if exchange_data is None and not self.repo.get_symbol_snapshot(symbol) else 0.8

        # Drivers
        drivers = []
        if long_short_ratio > LS_RATIO_EXTREME:
            drivers.append("extreme_long_bias")
        elif long_short_ratio < 1.0 / LS_RATIO_EXTREME:
            drivers.append("extreme_short_bias")
        elif long_short_ratio > LS_RATIO_ELEVATED:
            drivers.append("elevated_long_bias")
        elif long_short_ratio < 1.0 / LS_RATIO_ELEVATED:
            drivers.append("elevated_short_bias")

        if leverage_index > LEVERAGE_HIGH:
            drivers.append("high_leverage")
        if squeeze_prob > SQUEEZE_HIGH:
            side = "short" if long_short_ratio > 1.0 else "long"
            drivers.append(f"{side}_squeeze_risk")
        if abs(perp_premium) > PREMIUM_EXTREME:
            drivers.append("perp_premium_extreme")

        return DerivativesPressureSignal(
            symbol=symbol,
            timestamp=now,
            long_short_ratio=long_short_ratio,
            leverage_index=leverage_index,
            squeeze_probability=squeeze_prob,
            pressure_state=state,
            perp_premium=perp_premium,
            confidence=confidence,
            drivers=drivers,
        )

    def _compute_squeeze_probability(
        self, ls_ratio: float, leverage: float, premium: float
    ) -> float:
        """
        Squeeze probability: imbalanced positioning + high leverage + premium divergence.
        """
        imbalance = abs(ls_ratio - 1.0) / (LS_RATIO_EXTREME - 1.0)
        imbalance = min(imbalance, 1.0)

        leverage_component = min(leverage / LEVERAGE_HIGH, 1.0)
        premium_component = min(abs(premium) / PREMIUM_EXTREME, 1.0)

        raw = 0.45 * imbalance + 0.35 * leverage_component + 0.20 * premium_component
        return min(max(raw, 0.0), 1.0)

    def _classify_state(
        self, ls_ratio: float, leverage: float, squeeze_prob: float
    ) -> DerivativesPressure:
        if squeeze_prob > SQUEEZE_HIGH:
            if ls_ratio > 1.0:
                return DerivativesPressure.SHORT_SQUEEZE
            return DerivativesPressure.LONG_SQUEEZE
        if leverage > LEVERAGE_HIGH:
            return DerivativesPressure.LEVERAGE_EXCESS
        return DerivativesPressure.BALANCED

    def _derive_from_candles(self, candles: List[Dict]) -> Dict:
        """Derive derivatives proxies from candles."""
        if len(candles) < 7:
            return {"long_short_ratio": 1.0, "leverage_index": 0.3, "perp_premium": 0.0}

        recent = candles[-7:]
        up_days = sum(1 for c in recent if c["close"] > c["open"])
        down_days = len(recent) - up_days

        ls_proxy = (up_days + 0.5) / (down_days + 0.5)

        # Volatility as leverage proxy
        returns = []
        for i in range(1, len(recent)):
            prev_close = recent[i - 1]["close"]
            if prev_close > 0:
                returns.append(abs(recent[i]["close"] - prev_close) / prev_close)
        avg_return = sum(returns) / max(len(returns), 1)
        leverage_proxy = min(avg_return / 0.05, 1.0)

        # Premium proxy from close vs high/low midpoint
        last = recent[-1]
        mid = (last["high"] + last["low"]) / 2
        premium_proxy = (last["close"] - mid) / max(mid, 1e-8)

        return {
            "long_short_ratio": ls_proxy,
            "leverage_index": leverage_proxy,
            "perp_premium": premium_proxy,
        }
