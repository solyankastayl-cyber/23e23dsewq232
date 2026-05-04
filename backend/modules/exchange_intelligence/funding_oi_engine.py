"""
PHASE 13.8 — Funding & OI Engine
==================================
Analyzes funding rate + open interest for crowding and pressure signals.

Data sources:
 - exchange_funding_context (from TS FundingService)
 - exchange_oi_snapshots (from TS exchange data)
 - candles (for price context)

Output: FundingOISignal
"""

import math
from datetime import datetime, timezone
from typing import List, Dict, Optional

from .exchange_intel_types import FundingOISignal, FundingState, OIPressureState
from .exchange_intel_repository import ExchangeIntelRepository


# ── Thresholds ──────────────────────────────────

FUNDING_EXTREME = 0.05       # 5% annualized = extreme
FUNDING_CROWDED = 0.02       # 2% annualized = crowded
OI_EXPAND_THRESHOLD = 0.05   # 5% OI growth = expansion
OI_CONTRACT_THRESHOLD = -0.05
CROWDING_HIGH = 0.7
DIVERGENCE_THRESHOLD = 0.03


class FundingOIEngine:
    """Computes funding + OI pressure signals."""

    def __init__(self, repo: Optional[ExchangeIntelRepository] = None):
        self.repo = repo or ExchangeIntelRepository()

    def compute(self, symbol: str, exchange_data: Optional[Dict] = None) -> FundingOISignal:
        """
        Compute funding/OI signal.
        If exchange_data is provided, uses it directly.
        Otherwise reads from MongoDB.
        """
        now = datetime.now(timezone.utc)

        # Try to get real exchange data
        funding_rate = 0.0
        oi_value = 0.0
        oi_change_pct = 0.0

        if exchange_data:
            funding_rate = exchange_data.get("funding_rate", 0.0)
            oi_value = exchange_data.get("oi_value", 0.0)
            oi_change_pct = exchange_data.get("oi_change_pct", 0.0)
        else:
            funding_data = self.repo.get_funding_data(symbol, limit=10)
            oi_data = self.repo.get_oi_data(symbol, limit=10)

            if funding_data:
                latest = funding_data[-1]
                funding_rate = latest.get("funding_rate", latest.get("rate", 0.0))

            if oi_data:
                latest_oi = oi_data[-1]
                oi_value = latest_oi.get("oi_usd", latest_oi.get("value", 0.0))
                if len(oi_data) >= 2:
                    prev_oi = oi_data[-2].get("oi_usd", oi_data[-2].get("value", 1.0))
                    if prev_oi > 0:
                        oi_change_pct = (oi_value - prev_oi) / prev_oi

            # Fallback: derive from candle data
            if funding_rate == 0.0 and oi_value == 0.0:
                candles = self.repo.get_candles(symbol, "1d", limit=30)
                if len(candles) >= 2:
                    signal = self._derive_from_candles(candles)
                    funding_rate = signal["funding_rate"]
                    oi_value = signal["oi_value"]
                    oi_change_pct = signal["oi_change_pct"]

        # Compute annualized funding
        funding_annualized = funding_rate * 3 * 365  # 8h funding * 3 * 365

        # Classify funding state
        funding_state = self._classify_funding(funding_annualized)

        # Classify OI pressure
        oi_pressure = self._classify_oi(oi_change_pct)

        # Crowding risk
        crowding_risk = self._compute_crowding_risk(funding_annualized, oi_change_pct)

        # Divergence: OI expanding but funding extreme (crowding into one side)
        divergence = self._detect_divergence(funding_annualized, oi_change_pct)

        # Confidence based on data availability
        confidence = 0.5 if funding_rate == 0.0 and oi_value == 0.0 else 0.8

        # Drivers
        drivers = []
        if abs(funding_annualized) > FUNDING_EXTREME:
            side = "long" if funding_annualized > 0 else "short"
            drivers.append(f"extreme_funding_{side}")
        if abs(funding_annualized) > FUNDING_CROWDED:
            drivers.append("crowded_positioning")
        if oi_change_pct > OI_EXPAND_THRESHOLD:
            drivers.append("oi_expanding")
        elif oi_change_pct < OI_CONTRACT_THRESHOLD:
            drivers.append("oi_contracting")
        if divergence:
            drivers.append("funding_oi_divergence")

        return FundingOISignal(
            symbol=symbol,
            timestamp=now,
            funding_rate=funding_rate,
            funding_annualized=funding_annualized,
            funding_state=funding_state,
            oi_value=oi_value,
            oi_change_pct=oi_change_pct,
            oi_pressure=oi_pressure,
            crowding_risk=crowding_risk,
            funding_oi_divergence=divergence,
            confidence=confidence,
            drivers=drivers,
        )

    def _classify_funding(self, ann: float) -> FundingState:
        if ann > FUNDING_EXTREME:
            return FundingState.EXTREME_LONG
        elif ann > FUNDING_CROWDED:
            return FundingState.LONG_CROWDED
        elif ann < -FUNDING_EXTREME:
            return FundingState.EXTREME_SHORT
        elif ann < -FUNDING_CROWDED:
            return FundingState.SHORT_CROWDED
        return FundingState.NEUTRAL

    def _classify_oi(self, change: float) -> OIPressureState:
        if change > OI_EXPAND_THRESHOLD:
            return OIPressureState.EXPANDING
        elif change < OI_CONTRACT_THRESHOLD:
            return OIPressureState.CONTRACTING
        return OIPressureState.STABLE

    def _compute_crowding_risk(self, funding_ann: float, oi_change: float) -> float:
        """
        Crowding risk: high funding + expanding OI = everyone on same side.
        """
        funding_component = min(abs(funding_ann) / FUNDING_EXTREME, 1.0)
        oi_component = max(oi_change / OI_EXPAND_THRESHOLD, 0.0) if oi_change > 0 else 0.0
        raw = 0.6 * funding_component + 0.4 * oi_component
        return min(max(raw, 0.0), 1.0)

    def _detect_divergence(self, funding_ann: float, oi_change: float) -> bool:
        """Divergence: OI expanding but extreme funding = unsustainable crowding."""
        return (
            abs(funding_ann) > FUNDING_CROWDED
            and oi_change > DIVERGENCE_THRESHOLD
        )

    def _derive_from_candles(self, candles: List[Dict]) -> Dict:
        """
        Derive proxy funding/OI from candle data.
        Uses volume patterns and price momentum as proxies.
        """
        if len(candles) < 7:
            return {"funding_rate": 0.0, "oi_value": 0.0, "oi_change_pct": 0.0}

        recent = candles[-7:]
        older = candles[-14:-7] if len(candles) >= 14 else candles[:7]

        # Price momentum as funding proxy
        price_change = (recent[-1]["close"] - recent[0]["close"]) / max(recent[0]["close"], 1e-8)
        funding_proxy = price_change * 0.001  # Scale to 8h funding range

        # Volume trend as OI proxy
        recent_vol = sum(c.get("volume", 0) for c in recent) / len(recent)
        older_vol = sum(c.get("volume", 0) for c in older) / max(len(older), 1)
        oi_proxy_change = (recent_vol - older_vol) / max(older_vol, 1e-8)

        return {
            "funding_rate": funding_proxy,
            "oi_value": recent_vol * recent[-1].get("close", 0),
            "oi_change_pct": oi_proxy_change,
        }
