"""
PHASE 13.8 — Exchange Liquidation Engine
==========================================
Detects liquidation zones, cascade probability, trapped positions.

Output: LiquidationSignal
"""

import math
from datetime import datetime, timezone
from typing import List, Dict, Optional

from .exchange_intel_types import LiquidationSignal, LiquidationRisk
from .exchange_intel_repository import ExchangeIntelRepository


# ── Thresholds ──────────────────────────────────

CASCADE_HIGH = 0.6
CASCADE_ELEVATED = 0.35
TRAPPED_HIGH = 0.15           # 15% of OI in danger zone
LIQ_ZONE_PCT = 0.03           # 3% from current price


class ExchangeLiquidationEngine:
    """Computes liquidation risk and cascade probability."""

    def __init__(self, repo: Optional[ExchangeIntelRepository] = None):
        self.repo = repo or ExchangeIntelRepository()

    def compute(self, symbol: str, exchange_data: Optional[Dict] = None) -> LiquidationSignal:
        now = datetime.now(timezone.utc)

        current_price = 0.0
        long_liq_zone = 0.0
        short_liq_zone = 0.0
        trapped_longs = 0.0
        trapped_shorts = 0.0
        net_liq_flow = 0.0

        if exchange_data:
            current_price = exchange_data.get("price", 0.0)
            long_liq_zone = exchange_data.get("long_liq_zone", 0.0)
            short_liq_zone = exchange_data.get("short_liq_zone", 0.0)
            trapped_longs = exchange_data.get("trapped_longs_pct", 0.0)
            trapped_shorts = exchange_data.get("trapped_shorts_pct", 0.0)
            net_liq_flow = exchange_data.get("net_liq_flow", 0.0)
        else:
            liq_data = self.repo.get_liquidation_data(symbol, limit=100)
            candles = self.repo.get_candles(symbol, "1d", limit=30)

            if candles:
                current_price = candles[-1].get("close", 0.0)

            if liq_data and current_price > 0:
                long_liq_zone, short_liq_zone, trapped_longs, trapped_shorts, net_liq_flow = (
                    self._analyze_liquidations(liq_data, current_price)
                )
            elif candles and current_price > 0:
                derived = self._derive_from_candles(candles, current_price)
                long_liq_zone = derived["long_liq_zone"]
                short_liq_zone = derived["short_liq_zone"]
                trapped_longs = derived["trapped_longs"]
                trapped_shorts = derived["trapped_shorts"]
                net_liq_flow = derived["net_liq_flow"]

        # Cascade probability
        cascade_prob = self._compute_cascade_probability(
            trapped_longs, trapped_shorts, net_liq_flow, current_price,
            long_liq_zone, short_liq_zone
        )

        # Risk level
        risk = self._classify_risk(cascade_prob, trapped_longs, trapped_shorts)

        # Confidence
        has_real_data = bool(exchange_data) or bool(self.repo.get_liquidation_data(symbol, limit=1))
        confidence = 0.8 if has_real_data else 0.5

        # Drivers
        drivers = []
        if cascade_prob > CASCADE_HIGH:
            drivers.append("cascade_imminent")
        elif cascade_prob > CASCADE_ELEVATED:
            drivers.append("cascade_elevated")
        if trapped_longs > TRAPPED_HIGH:
            drivers.append("trapped_longs_high")
        if trapped_shorts > TRAPPED_HIGH:
            drivers.append("trapped_shorts_high")
        if current_price > 0:
            to_long_liq = abs(current_price - long_liq_zone) / current_price if long_liq_zone > 0 else 1.0
            to_short_liq = abs(short_liq_zone - current_price) / current_price if short_liq_zone > 0 else 1.0
            if to_long_liq < LIQ_ZONE_PCT:
                drivers.append("near_long_liquidation_zone")
            if to_short_liq < LIQ_ZONE_PCT:
                drivers.append("near_short_liquidation_zone")

        return LiquidationSignal(
            symbol=symbol,
            timestamp=now,
            long_liq_zone=long_liq_zone,
            short_liq_zone=short_liq_zone,
            cascade_probability=cascade_prob,
            trapped_longs_pct=trapped_longs,
            trapped_shorts_pct=trapped_shorts,
            liquidation_risk=risk,
            net_liq_flow=net_liq_flow,
            confidence=confidence,
            drivers=drivers,
        )

    def _analyze_liquidations(
        self, liq_data: List[Dict], current_price: float
    ) -> tuple:
        """Analyze real liquidation data."""
        long_volume = 0.0
        short_volume = 0.0

        for liq in liq_data:
            side = liq.get("side", "").upper()
            size = liq.get("size", liq.get("quantity", 0.0))
            if side == "LONG":
                long_volume += size
            elif side == "SHORT":
                short_volume += size

        total = long_volume + short_volume
        net_flow = (long_volume - short_volume) / max(total, 1e-8)

        # Estimated liquidation zones
        long_liq = current_price * (1 - LIQ_ZONE_PCT * 1.5)
        short_liq = current_price * (1 + LIQ_ZONE_PCT * 1.5)

        trapped_longs = min(long_volume / max(total, 1e-8), 0.5)
        trapped_shorts = min(short_volume / max(total, 1e-8), 0.5)

        return long_liq, short_liq, trapped_longs, trapped_shorts, net_flow

    def _derive_from_candles(self, candles: List[Dict], price: float) -> Dict:
        """Derive liquidation zones from price structure."""
        if not candles or price <= 0:
            return {
                "long_liq_zone": 0, "short_liq_zone": 0,
                "trapped_longs": 0, "trapped_shorts": 0, "net_liq_flow": 0,
            }

        recent = candles[-14:]
        lows = [c["low"] for c in recent if c.get("low", 0) > 0]
        highs = [c["high"] for c in recent if c.get("high", 0) > 0]

        # Support/resistance as liquidation zones
        long_liq = min(lows) if lows else price * 0.95
        short_liq = max(highs) if highs else price * 1.05

        # Price position relative to range
        price_range = short_liq - long_liq
        if price_range > 0:
            position_in_range = (price - long_liq) / price_range
            trapped_longs = max(0, 1 - position_in_range) * 0.15
            trapped_shorts = max(0, position_in_range) * 0.15
        else:
            trapped_longs = 0.05
            trapped_shorts = 0.05

        # Recent momentum as flow proxy
        if len(recent) >= 3:
            recent_change = (recent[-1]["close"] - recent[-3]["close"]) / max(recent[-3]["close"], 1e-8)
            net_flow = -recent_change  # Price drop = long liquidations
        else:
            net_flow = 0.0

        return {
            "long_liq_zone": long_liq,
            "short_liq_zone": short_liq,
            "trapped_longs": trapped_longs,
            "trapped_shorts": trapped_shorts,
            "net_liq_flow": net_flow,
        }

    def _compute_cascade_probability(
        self, trapped_l: float, trapped_s: float, net_flow: float,
        price: float, long_zone: float, short_zone: float
    ) -> float:
        """Cascade = trapped positions + proximity to zone + flow acceleration."""
        trapped_component = min((trapped_l + trapped_s) / 0.3, 1.0)

        proximity = 0.0
        if price > 0 and long_zone > 0 and short_zone > 0:
            to_long = abs(price - long_zone) / price
            to_short = abs(short_zone - price) / price
            nearest = min(to_long, to_short)
            proximity = max(0, 1.0 - nearest / LIQ_ZONE_PCT)

        flow_component = min(abs(net_flow) / 0.5, 1.0)

        raw = 0.35 * trapped_component + 0.40 * proximity + 0.25 * flow_component
        return min(max(raw, 0.0), 1.0)

    def _classify_risk(self, cascade: float, trapped_l: float, trapped_s: float) -> LiquidationRisk:
        if cascade > CASCADE_HIGH:
            return LiquidationRisk.CASCADE_IMMINENT
        if cascade > CASCADE_ELEVATED or max(trapped_l, trapped_s) > TRAPPED_HIGH:
            return LiquidationRisk.ELEVATED
        if cascade > 0.15:
            return LiquidationRisk.NORMAL
        return LiquidationRisk.LOW
