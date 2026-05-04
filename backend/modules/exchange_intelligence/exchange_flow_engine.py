"""
PHASE 13.8 — Exchange Flow Engine
===================================
Analyzes taker buy/sell imbalance, aggressive flow, absorption detection.

Output: ExchangeFlowSignal
"""

from datetime import datetime, timezone
from typing import List, Dict, Optional

from .exchange_intel_types import ExchangeFlowSignal, FlowDirection
from .exchange_intel_repository import ExchangeIntelRepository


# ── Thresholds ──────────────────────────────────

AGGRESSIVE_THRESHOLD = 0.3    # ±0.3 on -1 to 1 scale
ABSORPTION_VOL_RATIO = 1.5    # Volume spike without price move


class ExchangeFlowEngine:
    """Computes order flow pressure signals."""

    def __init__(self, repo: Optional[ExchangeIntelRepository] = None):
        self.repo = repo or ExchangeIntelRepository()

    def compute(self, symbol: str, exchange_data: Optional[Dict] = None) -> ExchangeFlowSignal:
        now = datetime.now(timezone.utc)

        taker_buy_ratio = 0.5
        aggressive_flow = 0.0
        absorption = False

        if exchange_data:
            taker_buy_ratio = exchange_data.get("taker_buy_ratio", 0.5)
            aggressive_flow = exchange_data.get("aggressive_flow", 0.0)
            absorption = exchange_data.get("absorption_detected", False)
        else:
            flow_data = self.repo.get_orderflow_data(symbol, limit=20)
            if flow_data:
                taker_buy_ratio, aggressive_flow, absorption = (
                    self._analyze_flow_data(flow_data)
                )
            else:
                candles = self.repo.get_candles(symbol, "1d", limit=14)
                if len(candles) >= 5:
                    derived = self._derive_from_candles(candles)
                    taker_buy_ratio = derived["taker_buy_ratio"]
                    aggressive_flow = derived["aggressive_flow"]
                    absorption = derived["absorption"]

        # Classify direction
        direction = self._classify_direction(taker_buy_ratio, aggressive_flow, absorption)

        # Flow intensity (0-1)
        intensity = min(abs(aggressive_flow) / AGGRESSIVE_THRESHOLD, 1.0)
        if absorption:
            intensity = max(intensity, 0.6)

        # Confidence
        has_real_data = bool(exchange_data) or bool(self.repo.get_orderflow_data(symbol, limit=1))
        confidence = 0.8 if has_real_data else 0.5

        # Drivers
        drivers = []
        if abs(aggressive_flow) > AGGRESSIVE_THRESHOLD:
            side = "buy" if aggressive_flow > 0 else "sell"
            drivers.append(f"aggressive_{side}_flow")
        if taker_buy_ratio > 0.6:
            drivers.append("taker_buy_dominant")
        elif taker_buy_ratio < 0.4:
            drivers.append("taker_sell_dominant")
        if absorption:
            drivers.append("absorption_detected")

        return ExchangeFlowSignal(
            symbol=symbol,
            timestamp=now,
            taker_buy_ratio=taker_buy_ratio,
            aggressive_flow=aggressive_flow,
            absorption_detected=absorption,
            flow_direction=direction,
            flow_intensity=intensity,
            confidence=confidence,
            drivers=drivers,
        )

    def _analyze_flow_data(self, flow_data: List[Dict]) -> tuple:
        """Analyze real trade flow data."""
        total_buy = 0.0
        total_sell = 0.0

        for flow in flow_data:
            buy = flow.get("taker_buy_volume", flow.get("buy_volume", 0))
            sell = flow.get("taker_sell_volume", flow.get("sell_volume", 0))
            total_buy += buy
            total_sell += sell

        total = total_buy + total_sell
        taker_ratio = total_buy / max(total, 1e-8)

        # Aggressive flow: normalized imbalance
        aggressive = (total_buy - total_sell) / max(total, 1e-8)

        # Absorption: high volume but small price move
        absorption = False
        if len(flow_data) >= 3:
            recent_vol = sum(
                f.get("total_volume", f.get("volume", 0)) for f in flow_data[-3:]
            )
            older_vol = sum(
                f.get("total_volume", f.get("volume", 0)) for f in flow_data[:-3]
            ) / max(len(flow_data) - 3, 1)
            if older_vol > 0 and recent_vol / older_vol > ABSORPTION_VOL_RATIO:
                price_moves = [abs(f.get("price_change", 0)) for f in flow_data[-3:]]
                avg_move = sum(price_moves) / max(len(price_moves), 1)
                if avg_move < 0.005:  # Less than 0.5% move despite volume spike
                    absorption = True

        return taker_ratio, aggressive, absorption

    def _derive_from_candles(self, candles: List[Dict]) -> Dict:
        """Derive flow proxies from candles."""
        if len(candles) < 5:
            return {"taker_buy_ratio": 0.5, "aggressive_flow": 0.0, "absorption": False}

        recent = candles[-5:]

        # Buy pressure proxy: close > open days / total
        buy_bars = sum(1 for c in recent if c["close"] > c["open"])
        taker_proxy = buy_bars / len(recent)

        # Aggressive flow from volume-weighted direction
        flow_sum = 0.0
        vol_sum = 0.0
        for c in recent:
            vol = c.get("volume", 0)
            direction = 1 if c["close"] > c["open"] else -1
            body_ratio = abs(c["close"] - c["open"]) / max(c["high"] - c["low"], 1e-8)
            flow_sum += direction * body_ratio * vol
            vol_sum += vol

        aggressive_proxy = flow_sum / max(vol_sum, 1e-8)

        # Absorption: volume spike + small body
        absorption = False
        if len(candles) >= 10:
            avg_vol = sum(c.get("volume", 0) for c in candles[-10:-5]) / 5
            last_vol = recent[-1].get("volume", 0)
            last_body = abs(recent[-1]["close"] - recent[-1]["open"])
            last_range = recent[-1]["high"] - recent[-1]["low"]
            if avg_vol > 0 and last_vol > avg_vol * ABSORPTION_VOL_RATIO:
                if last_range > 0 and last_body / last_range < 0.3:
                    absorption = True

        return {
            "taker_buy_ratio": taker_proxy,
            "aggressive_flow": aggressive_proxy,
            "absorption": absorption,
        }

    def _classify_direction(
        self, taker_ratio: float, aggressive: float, absorption: bool
    ) -> FlowDirection:
        if absorption:
            if taker_ratio > 0.5:
                return FlowDirection.ABSORPTION_BUY
            return FlowDirection.ABSORPTION_SELL
        if aggressive > AGGRESSIVE_THRESHOLD:
            return FlowDirection.AGGRESSIVE_BUY
        if aggressive < -AGGRESSIVE_THRESHOLD:
            return FlowDirection.AGGRESSIVE_SELL
        return FlowDirection.BALANCED
