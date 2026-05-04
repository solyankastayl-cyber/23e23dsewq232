"""
MomentumPredictionEngine - PRODUCTION grade.
=============================================
Production logic (when `_raw_data.rsi_series` and `macd_series` available):
  * MACD histogram slope (last 5 bars)
  * Acceleration (second derivative of histogram)
  * Persistence count (consecutive bars on the same side of zero)
  * RSI vs midline + over-extension
  * Bullish / bearish DIVERGENCE (price pivot vs RSI/MACD pivot)
  * Exhaustion: extreme RSI + decelerating histogram

Neutral if no momentum direction can be established.
"""

from typing import Any, Dict, List, Optional, Tuple

from modules.ta_prediction_intelligence.types import (
    EngineContribution,
    PredictionBias,
    PredictionHorizon,
    TAEngineName,
)

SLOPE_LOOKBACK = 5      # bars for slope calculation
DIVERGENCE_LOOKBACK = 30  # bars for divergence search


class MomentumPredictionEngine:
    def analyze(self, setup: Dict[str, Any]) -> EngineContribution:
        raw = setup.get("_raw_data")
        if raw and raw.get("rsi_series") and raw.get("macd_series"):
            return self._analyze_production(raw)
        return self._analyze_summary(setup)

    # ----------------------------------------------------------------- production
    def _analyze_production(self, raw: Dict[str, Any]) -> EngineContribution:
        rsi_series: List[Dict[str, Any]] = raw.get("rsi_series") or []
        macd_series: List[Dict[str, Any]] = raw.get("macd_series") or []
        candles: List[Dict[str, Any]] = raw.get("candles") or []
        if len(rsi_series) < SLOPE_LOOKBACK + 1 or len(macd_series) < SLOPE_LOOKBACK + 1:
            return self._empty("insufficient_indicator_history")

        rsi_vals = [s["value"] for s in rsi_series if s.get("value") is not None]
        macd_hist_vals = [s["value"] for s in macd_series if s.get("value") is not None]
        if len(rsi_vals) < SLOPE_LOOKBACK + 1 or len(macd_hist_vals) < SLOPE_LOOKBACK + 1:
            return self._empty("sparse_indicator_values")

        rsi_last = rsi_vals[-1]
        hist_last = macd_hist_vals[-1]

        # Slope of MACD histogram (linear: last - first over the window).
        slope_window = macd_hist_vals[-SLOPE_LOOKBACK:]
        macd_slope = (slope_window[-1] - slope_window[0]) / SLOPE_LOOKBACK
        # Acceleration = slope of slope (use last 3 deltas)
        deltas = [slope_window[i] - slope_window[i - 1] for i in range(1, len(slope_window))]
        if len(deltas) >= 3:
            macd_accel = deltas[-1] - deltas[-3]
        else:
            macd_accel = 0.0

        # Persistence: how many bars in a row hist had same sign
        persistence = 0
        last_sign = 1 if hist_last > 0 else -1 if hist_last < 0 else 0
        for v in reversed(macd_hist_vals):
            sign = 1 if v > 0 else -1 if v < 0 else 0
            if sign == last_sign and sign != 0:
                persistence += 1
            else:
                break

        # ── Divergence detection ──
        bullish_div, bearish_div = self._detect_divergence(
            candles, rsi_vals, macd_hist_vals, lookback=DIVERGENCE_LOOKBACK
        )

        # ── Bias decision ──
        bull_score = 0.0
        bear_score = 0.0
        drivers: List[str] = []
        risks: List[str] = []

        # MACD histogram side
        if hist_last > 0:
            bull_score += 0.30
            drivers.append("macd_hist_positive")
        elif hist_last < 0:
            bear_score += 0.30
            drivers.append("macd_hist_negative")

        # MACD slope (rising hist = bullish momentum acceleration)
        if macd_slope > 0:
            bull_score += 0.25
            drivers.append("macd_hist_rising")
        elif macd_slope < 0:
            bear_score += 0.25
            drivers.append("macd_hist_falling")

        # RSI midline
        if rsi_last > 55:
            bull_score += 0.15
            drivers.append(f"rsi_above_midline_{rsi_last:.1f}")
        elif rsi_last < 45:
            bear_score += 0.15
            drivers.append(f"rsi_below_midline_{rsi_last:.1f}")

        # Persistence bonus
        if persistence >= 4:
            drivers.append(f"momentum_persistence_{persistence}")
            if last_sign > 0:
                bull_score += 0.10
            elif last_sign < 0:
                bear_score += 0.10

        # Divergence (HIGH PRIORITY: it overrides direction)
        if bullish_div:
            drivers.append("bullish_divergence")
            bull_score += 0.35
            bear_score *= 0.5  # divergence weakens prevailing bear momentum
            risks.append("momentum_divergence_bearish_to_bullish")
        if bearish_div:
            drivers.append("bearish_divergence")
            bear_score += 0.35
            bull_score *= 0.5
            risks.append("momentum_divergence_bullish_to_bearish")

        # Exhaustion / over-extension
        exhaustion = False
        if rsi_last > 75 and macd_slope <= 0:
            risks.append("bullish_exhaustion_rsi_overbought_decelerating")
            exhaustion = True
            bull_score *= 0.7
        elif rsi_last < 25 and macd_slope >= 0:
            risks.append("bearish_exhaustion_rsi_oversold_decelerating")
            exhaustion = True
            bear_score *= 0.7

        total = bull_score + bear_score
        if total <= 0:
            return self._empty("momentum_neutral")

        if bull_score > bear_score:
            bias = PredictionBias.BULLISH
            confidence = bull_score / total
        elif bear_score > bull_score:
            bias = PredictionBias.BEARISH
            confidence = bear_score / total
        else:
            bias = PredictionBias.NEUTRAL
            confidence = 0.0

        # Cap confidence by signal strength magnitude
        confidence = round(min(1.0, max(0.0, confidence * min(1.0, total))), 4)

        # Momentum state classification
        if bullish_div or bearish_div:
            momentum_state = "divergence"
        elif exhaustion:
            momentum_state = "exhaustion"
        elif macd_accel > 0 and macd_slope > 0:
            momentum_state = "accelerating_up"
        elif macd_accel < 0 and macd_slope < 0:
            momentum_state = "accelerating_down"
        elif macd_slope > 0:
            momentum_state = "rising"
        elif macd_slope < 0:
            momentum_state = "falling"
        else:
            momentum_state = "flat"
        drivers.append(f"momentum_state_{momentum_state}")

        # Quality: how clean is momentum read (sign of hist + agreeing slope + RSI alignment)
        agreement = 0.0
        if (hist_last > 0 and macd_slope > 0 and rsi_last > 50):
            agreement = 1.0
        elif (hist_last < 0 and macd_slope < 0 and rsi_last < 50):
            agreement = 1.0
        elif (hist_last > 0 and macd_slope > 0) or (hist_last < 0 and macd_slope < 0):
            agreement = 0.66
        else:
            agreement = 0.33
        quality = round(agreement, 4)

        expected_move_pct = round(min(0.025, confidence * 0.020), 6)

        return EngineContribution(
            engine=TAEngineName.MOMENTUM.value,
            bias=bias,
            score=round(confidence, 4),
            confidence=confidence,
            expected_move_pct=expected_move_pct,
            quality=quality,
            horizon=PredictionHorizon.H1.value,
            drivers=drivers,
            risks=risks,
            raw={
                "rsi_last": rsi_last,
                "macd_hist_last": hist_last,
                "macd_slope": macd_slope,
                "macd_accel": macd_accel,
                "persistence": persistence,
                "bullish_divergence": bullish_div,
                "bearish_divergence": bearish_div,
                "momentum_state": momentum_state,
                "bull_score": round(bull_score, 4),
                "bear_score": round(bear_score, 4),
            },
        )

    # ----------------------------------------------------------------- summary fallback
    def _analyze_summary(self, setup: Dict[str, Any]) -> EngineContribution:
        ta_context = setup.get("ta_context", {}) or {}
        indicators = ta_context.get("indicators", {}) or setup.get("indicators", {}) or {}
        signals = indicators.get("signals") or []
        bull = bear = total = 0.0
        for s in signals:
            d = str(s.get("direction") or s.get("bias") or "").lower()
            w = float(s.get("weight") or s.get("confidence") or 1)
            total += abs(w)
            if d in ("bullish", "long", "up"):
                bull += w
            elif d in ("bearish", "short", "down"):
                bear += w
        if total <= 0:
            return self._empty("summary_no_indicator_signals")
        bias = (
            PredictionBias.BULLISH if bull > bear
            else PredictionBias.BEARISH if bear > bull
            else PredictionBias.NEUTRAL
        )
        confidence = abs(bull - bear) / total if bias != PredictionBias.NEUTRAL else 0.0
        expected_move_pct = min(0.025, confidence * 0.018)
        return EngineContribution(
            engine=TAEngineName.MOMENTUM.value,
            bias=bias,
            score=round(confidence, 4),
            confidence=round(confidence, 4),
            expected_move_pct=round(expected_move_pct, 6),
            quality=round(confidence * 0.5, 4),
            horizon=PredictionHorizon.H1.value,
            drivers=[f"summary_indicator_signals_{len(signals)}"],
            risks=["summary_mode_no_full_series"],
            raw={"mode": "summary", "bullish_weight": bull, "bearish_weight": bear},
        )

    # ----------------------------------------------------------------- divergence helper
    def _detect_divergence(
        self,
        candles: List[Dict[str, Any]],
        rsi_vals: List[float],
        macd_hist_vals: List[float],
        lookback: int,
    ) -> Tuple[bool, bool]:
        """
        Returns (bullish_div, bearish_div).
        Bullish: price LL but RSI HL.
        Bearish: price HH but RSI LH.
        Uses last two extreme points within the lookback window.
        """
        if not candles:
            return False, False
        n = min(lookback, len(candles), len(rsi_vals))
        if n < 10:
            return False, False
        closes = [float(c.get("close") or 0) for c in candles[-n:]]
        rsi_window = rsi_vals[-n:]

        # Find last two local extremes in price (3-bar window)
        def local_extremes(arr: List[float], is_high: bool) -> List[Tuple[int, float]]:
            out: List[Tuple[int, float]] = []
            for i in range(2, len(arr) - 2):
                if is_high and arr[i] >= arr[i - 1] and arr[i] >= arr[i + 1] and arr[i] > arr[i - 2] and arr[i] > arr[i + 2]:
                    out.append((i, arr[i]))
                elif not is_high and arr[i] <= arr[i - 1] and arr[i] <= arr[i + 1] and arr[i] < arr[i - 2] and arr[i] < arr[i + 2]:
                    out.append((i, arr[i]))
            return out

        price_highs = local_extremes(closes, is_high=True)
        price_lows = local_extremes(closes, is_high=False)

        bearish_div = False
        bullish_div = False
        if len(price_highs) >= 2:
            (i1, p1), (i2, p2) = price_highs[-2], price_highs[-1]
            if p2 > p1 and rsi_window[i2] < rsi_window[i1]:
                bearish_div = True
        if len(price_lows) >= 2:
            (i1, p1), (i2, p2) = price_lows[-2], price_lows[-1]
            if p2 < p1 and rsi_window[i2] > rsi_window[i1]:
                bullish_div = True
        return bullish_div, bearish_div

    # ----------------------------------------------------------------- helpers
    def _empty(self, reason: Optional[str] = None) -> EngineContribution:
        return EngineContribution(
            engine=TAEngineName.MOMENTUM.value,
            bias=PredictionBias.NEUTRAL,
            score=0.0, confidence=0.0, expected_move_pct=0.0, quality=0.0,
            horizon=PredictionHorizon.H1.value,
            drivers=[], risks=[reason] if reason else [], raw={"reason": reason} if reason else {},
        )
