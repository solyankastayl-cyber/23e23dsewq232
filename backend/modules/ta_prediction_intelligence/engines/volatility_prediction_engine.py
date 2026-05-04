"""
VolatilityPredictionEngine - PRODUCTION grade.
=============================================
** DIRECTION-NEUTRAL by design. ** It contributes magnitude, never direction.

Production logic (when `_raw_data.candles` available):
  * Compute true ATR(14) series from candles.
  * Compression detected when ATR(14) of last 5 bars < ATR(14) of bars[-20:-5] * 0.85
  * Expansion detected when last bar's range > 1.5x ATR(14)
  * Breakout energy: ratio of recent ATR contraction depth
  * expected_move_pct = ATR(14) latest * 1.5  (envelope), capped at 5%

Fallback (summary): legacy compression/expansion booleans from setup.
"""

from typing import Any, Dict, List, Optional

from modules.ta_prediction_intelligence.types import (
    EngineContribution,
    PredictionBias,
    PredictionHorizon,
    TAEngineName,
)

ATR_PERIOD = 14


class VolatilityPredictionEngine:
    def analyze(self, setup: Dict[str, Any]) -> EngineContribution:
        raw = setup.get("_raw_data")
        if raw and raw.get("candles"):
            return self._analyze_production(raw)
        return self._analyze_summary(setup)

    # ----------------------------------------------------------------- production
    def _analyze_production(self, raw: Dict[str, Any]) -> EngineContribution:
        candles: List[Dict[str, Any]] = raw.get("candles") or []
        if len(candles) < ATR_PERIOD + 25:
            return self._fallback_from_atr_pct(raw)

        atr_series = self._compute_atr_series(candles, ATR_PERIOD)
        if not atr_series:
            return self._fallback_from_atr_pct(raw)

        last_close = float(candles[-1].get("close") or 0)
        atr_last = atr_series[-1]
        atr_pct = atr_last / last_close if last_close > 0 else 0.0

        # Recent vs older ATR average
        recent_avg = sum(atr_series[-5:]) / 5
        older_avg = sum(atr_series[-20:-5]) / 15 if len(atr_series) >= 20 else recent_avg
        compression_ratio = recent_avg / older_avg if older_avg > 0 else 1.0
        compression = compression_ratio < 0.85
        expansion = compression_ratio > 1.20

        # Last-bar range vs ATR
        last_range = float(candles[-1].get("high") or 0) - float(candles[-1].get("low") or 0)
        last_range_to_atr = last_range / atr_last if atr_last > 0 else 0.0
        explosive_bar = last_range_to_atr > 1.5

        # Breakout energy: how depressed is recent ATR (lower => more stored energy)
        breakout_energy = max(0.0, min(1.0, 1.0 - compression_ratio)) if compression else 0.0

        # quality / confidence
        if compression:
            confidence = round(min(1.0, breakout_energy * 0.9 + 0.1), 4)
            state = "compression"
        elif explosive_bar:
            confidence = round(min(1.0, last_range_to_atr / 2.5), 4)
            state = "expansion"
        elif expansion:
            confidence = round(min(1.0, (compression_ratio - 1.0) * 1.5), 4)
            state = "expansion"
        else:
            confidence = 0.10  # known but low-conviction state
            state = "normal"

        # Expected move envelope, capped at 5%.
        expected_move_pct = round(min(0.050, atr_pct * 1.5), 6)

        drivers: List[str] = [f"atr_pct_{atr_pct:.4f}", f"volatility_state_{state}"]
        if compression:
            drivers.append("breakout_energy_building")
            drivers.append(f"compression_ratio_{compression_ratio:.2f}")
        if explosive_bar:
            drivers.append(f"explosive_bar_range_to_atr_{last_range_to_atr:.2f}")

        risks: List[str] = ["direction_unknown"]
        if state == "normal":
            risks.append("no_volatility_edge")

        # quality = how clear is the volatility regime (compression/expansion both clear)
        quality = round(min(1.0, abs(compression_ratio - 1.0) * 1.5), 4)

        return EngineContribution(
            engine=TAEngineName.VOLATILITY.value,
            bias=PredictionBias.NEUTRAL,
            score=round(confidence, 4),
            confidence=confidence,
            expected_move_pct=expected_move_pct,
            quality=quality,
            horizon=PredictionHorizon.H6.value,
            drivers=drivers,
            risks=risks,
            raw={
                "atr_last": atr_last, "atr_pct": atr_pct,
                "compression_ratio": round(compression_ratio, 4),
                "compression": compression, "expansion": expansion,
                "explosive_bar": explosive_bar,
                "last_range_to_atr": round(last_range_to_atr, 4),
                "breakout_energy": round(breakout_energy, 4),
                "state": state,
            },
        )

    # ----------------------------------------------------------------- ATR-only fallback
    def _fallback_from_atr_pct(self, raw: Dict[str, Any]) -> EngineContribution:
        atr_pct = raw.get("atr_pct")
        if not atr_pct:
            return self._empty("insufficient_volatility_data")
        expected_move_pct = round(min(0.050, float(atr_pct) * 1.5), 6)
        return EngineContribution(
            engine=TAEngineName.VOLATILITY.value,
            bias=PredictionBias.NEUTRAL,
            score=0.0,
            confidence=0.10,
            expected_move_pct=expected_move_pct,
            quality=0.20,
            horizon=PredictionHorizon.H6.value,
            drivers=["atr_only_envelope"],
            risks=["direction_unknown", "limited_history"],
            raw={"atr_pct": atr_pct, "mode": "atr_pct_only"},
        )

    # ----------------------------------------------------------------- summary fallback
    def _analyze_summary(self, setup: Dict[str, Any]) -> EngineContribution:
        volatility = setup.get("volatility") or (setup.get("ta_context") or {}).get("volatility") or {}
        compression = bool(volatility.get("compression"))
        expansion = bool(volatility.get("expansion"))
        atr_pct = volatility.get("atr_pct")
        confidence = 0.0
        expected_move_pct = 0.0
        drivers: List[str] = []
        if compression:
            confidence = 0.30
            expected_move_pct = 0.020
            drivers.append("summary_compression")
        elif expansion:
            confidence = 0.25
            expected_move_pct = 0.025
            drivers.append("summary_expansion")
        elif atr_pct:
            expected_move_pct = round(min(0.050, float(atr_pct) * 1.5), 6)
            confidence = 0.10
            drivers.append("summary_atr_only")
        return EngineContribution(
            engine=TAEngineName.VOLATILITY.value,
            bias=PredictionBias.NEUTRAL,
            score=round(confidence, 4),
            confidence=round(confidence, 4),
            expected_move_pct=round(expected_move_pct, 6),
            quality=round(confidence * 0.5, 4),
            horizon=PredictionHorizon.H6.value,
            drivers=drivers,
            risks=["direction_unknown", "summary_mode"],
            raw={"compression": compression, "expansion": expansion, "atr_pct": atr_pct,
                 "mode": "summary"},
        )

    # ----------------------------------------------------------------- ATR computation
    @staticmethod
    def _compute_atr_series(candles: List[Dict[str, Any]], period: int) -> List[float]:
        if len(candles) < period + 1:
            return []
        trs: List[float] = []
        prev_close: Optional[float] = None
        for c in candles:
            try:
                hi = float(c.get("high") or 0)
                lo = float(c.get("low") or 0)
                close = float(c.get("close") or 0)
            except Exception:
                continue
            if prev_close is None:
                tr = hi - lo
            else:
                tr = max(hi - lo, abs(hi - prev_close), abs(lo - prev_close))
            trs.append(tr)
            prev_close = close
        if len(trs) < period:
            return []
        # Wilder's smoothing
        atr: List[float] = []
        first = sum(trs[:period]) / period
        atr.append(first)
        for i in range(period, len(trs)):
            new = (atr[-1] * (period - 1) + trs[i]) / period
            atr.append(new)
        return atr

    def _empty(self, reason: Optional[str] = None) -> EngineContribution:
        return EngineContribution(
            engine=TAEngineName.VOLATILITY.value,
            bias=PredictionBias.NEUTRAL,
            score=0.0, confidence=0.0, expected_move_pct=0.0, quality=0.0,
            horizon=PredictionHorizon.H6.value,
            drivers=[], risks=[reason] if reason else [], raw={"reason": reason} if reason else {},
        )
