"""
StructurePredictionEngine - PRODUCTION grade.
=============================================
Reads `setup["_raw_data"]` (candles + pivot_highs + pivot_lows) when present.
Falls back to summary fields (structure_context.metadata) when absent.

Production logic:
  * HH / HL / LH / LL count from last K pivots
  * BOS detection - latest close breaks last pivot high (uptrend continuation)
                  or last pivot low (downtrend continuation)
  * CHoCH detection - first counter-trend break of structure
  * Trend phase - impulse vs correction (current candle vs trend direction)
  * Trend age - bars since last reversal
  * Maturity risk - many HH/HL in a row marks late-stage trend

Honest rule: if too few pivots to compute structure, confidence = 0.
"""

from typing import Any, Dict, List, Optional, Tuple

from modules.ta_prediction_intelligence.types import (
    EngineContribution,
    PredictionBias,
    PredictionHorizon,
    TAEngineName,
)

MIN_PIVOTS = 4         # need at least 2 highs + 2 lows to read structure
LOOKBACK = 6           # consider last 6 pivots of each type
MATURITY_THRESHOLD = 5  # >= 5 monotonic HH/HL or LL/LH = late-stage


class StructurePredictionEngine:
    def analyze(self, setup: Dict[str, Any]) -> EngineContribution:
        raw = setup.get("_raw_data")
        if raw and raw.get("pivot_highs") and raw.get("pivot_lows"):
            return self._analyze_production(raw, setup)
        return self._analyze_summary(setup)

    # ----------------------------------------------------------------- production
    def _analyze_production(self, raw: Dict[str, Any], setup: Dict[str, Any]) -> EngineContribution:
        ph: List[Tuple[int, float]] = raw.get("pivot_highs") or []
        pl: List[Tuple[int, float]] = raw.get("pivot_lows") or []
        candles: List[Dict[str, Any]] = raw.get("candles") or []
        price: float = float(raw.get("current_price") or (candles[-1].get("close") if candles else 0))

        if len(ph) + len(pl) < MIN_PIVOTS:
            return self._empty(reason="insufficient_pivots")

        # Last K of each
        ph = ph[-LOOKBACK:]
        pl = pl[-LOOKBACK:]

        # HH/LH counters from highs sequence
        hh = lh = 0
        for i in range(1, len(ph)):
            if ph[i][1] > ph[i - 1][1]:
                hh += 1
            elif ph[i][1] < ph[i - 1][1]:
                lh += 1
        hl = ll = 0
        for i in range(1, len(pl)):
            if pl[i][1] > pl[i - 1][1]:
                hl += 1
            elif pl[i][1] < pl[i - 1][1]:
                ll += 1

        # Net structure score
        bull_struct = hh + hl   # higher highs and higher lows
        bear_struct = lh + ll

        # BOS / CHoCH detection on the latest pivot break
        last_ph_price = ph[-1][1] if ph else None
        last_pl_price = pl[-1][1] if pl else None
        bos_bull = last_ph_price is not None and price > last_ph_price
        bos_bear = last_pl_price is not None and price < last_pl_price

        # Determine trend direction from net structure
        if bull_struct > bear_struct:
            trend_dir = "bullish"
        elif bear_struct > bull_struct:
            trend_dir = "bearish"
        else:
            trend_dir = "neutral"

        # CHoCH: BOS in the OPPOSITE direction of current trend
        choch = (trend_dir == "bullish" and bos_bear) or (trend_dir == "bearish" and bos_bull)

        # Phase: are we in impulse (trending direction) or correction
        last_close = float(candles[-1].get("close")) if candles else price
        prev_close = float(candles[-2].get("close")) if len(candles) >= 2 else last_close
        recent_dir = "bullish" if last_close > prev_close else "bearish" if last_close < prev_close else "neutral"
        if trend_dir == "neutral":
            phase = "range"
        elif recent_dir == trend_dir:
            phase = "impulse"
        else:
            phase = "correction"

        # Trend age: bars since the structure aligned (use index of first matching pivot)
        all_pivots = sorted([(i, "H") for i, _ in ph] + [(i, "L") for i, _ in pl])
        trend_age_bars = (len(candles) - all_pivots[0][0]) if all_pivots else 0

        # Maturity flag
        maturity = max(hh + hl, lh + ll) >= MATURITY_THRESHOLD

        # ── Bias / confidence ──
        if choch:
            bias = PredictionBias.BEARISH if trend_dir == "bullish" else PredictionBias.BULLISH
        elif trend_dir == "bullish":
            bias = PredictionBias.BULLISH
        elif trend_dir == "bearish":
            bias = PredictionBias.BEARISH
        else:
            bias = PredictionBias.NEUTRAL

        total_struct = bull_struct + bear_struct
        imbalance = abs(bull_struct - bear_struct) / total_struct if total_struct > 0 else 0.0
        bos_bonus = 0.10 if (bos_bull or bos_bear) else 0.0
        choch_penalty = 0.10 if choch else 0.0  # CHoCH is a *new* signal but flips the bias
        confidence = min(1.0, max(0.0, 0.20 + imbalance * 0.60 + bos_bonus - choch_penalty))
        if maturity:
            confidence *= 0.85  # late-stage trend - haircut

        # quality = how clean is the structure read (independent of direction)
        quality = min(1.0, (len(ph) + len(pl)) / (2 * LOOKBACK)) * (0.5 + imbalance * 0.5)

        # expected_move: scales with confidence and the imbalance
        expected_move_pct = round(min(0.040, confidence * 0.030), 6)

        # ── Drivers / risks ──
        drivers: List[str] = []
        if hh >= 2:
            drivers.append(f"higher_highs_{hh}")
        if hl >= 2:
            drivers.append(f"higher_lows_{hl}")
        if lh >= 2:
            drivers.append(f"lower_highs_{lh}")
        if ll >= 2:
            drivers.append(f"lower_lows_{ll}")
        if bos_bull:
            drivers.append("bos_bullish")
        if bos_bear:
            drivers.append("bos_bearish")
        if phase != "range":
            drivers.append(f"phase_{phase}")

        risks: List[str] = []
        if choch:
            risks.append("choch_trend_reversal_signal")
        if maturity:
            risks.append("late_trend_maturity")
        if phase == "correction":
            risks.append("counter_trend_correction")
        if quality < 0.3:
            risks.append("weak_structure_clarity")

        return EngineContribution(
            engine=TAEngineName.STRUCTURE.value,
            bias=bias,
            score=round(imbalance, 4),
            confidence=round(confidence, 4),
            expected_move_pct=expected_move_pct,
            quality=round(quality, 4),
            horizon=PredictionHorizon.H3.value,
            drivers=drivers,
            risks=risks,
            raw={
                "hh": hh, "hl": hl, "lh": lh, "ll": ll,
                "bull_struct": bull_struct, "bear_struct": bear_struct,
                "bos_bull": bos_bull, "bos_bear": bos_bear,
                "choch": choch,
                "trend_dir": trend_dir, "phase": phase,
                "trend_age_bars": trend_age_bars, "maturity": maturity,
                "last_pivot_high": last_ph_price,
                "last_pivot_low": last_pl_price,
            },
        )

    # ----------------------------------------------------------------- summary fallback
    def _analyze_summary(self, setup: Dict[str, Any]) -> EngineContribution:
        structure = (
            setup.get("structure_context")
            or (setup.get("render_plan") or {}).get("structure")
            or setup.get("structure")
            or {}
        )
        decision = setup.get("decision", {}) or {}
        metadata = structure.get("metadata", {}) or {}

        bullish_score = float(metadata.get("bullish_score") or 0)
        bearish_score = float(metadata.get("bearish_score") or 0)
        bos_count = int(metadata.get("bos_count") or 0)
        choch_count = int(metadata.get("choch_count") or 0)

        if bullish_score == 0 and bearish_score == 0 and bos_count == 0 and choch_count == 0:
            return self._empty(reason="no_summary_structure_data")

        if bullish_score > bearish_score:
            bias = PredictionBias.BULLISH
        elif bearish_score > bullish_score:
            bias = PredictionBias.BEARISH
        else:
            structure_bias = (structure.get("structure_bias") or decision.get("bias") or "neutral")
            bias = self._normalize_bias(str(structure_bias))

        total = bullish_score + bearish_score
        imbalance = abs(bullish_score - bearish_score) / total if total > 0 else 0.0
        confidence = min(1.0, 0.25 + imbalance * 0.55 + min(bos_count + choch_count, 4) * 0.05)
        quality = imbalance
        expected_move_pct = min(0.035, confidence * 0.025)

        drivers: List[str] = []
        if bullish_score or bearish_score:
            drivers.append(f"structure_score_bull_{bullish_score:.0f}_bear_{bearish_score:.0f}")
        if bos_count:
            drivers.append(f"bos_events_{bos_count}")
        if choch_count:
            drivers.append(f"choch_events_{choch_count}")

        risks: List[str] = ["summary_mode_no_pivot_data"]
        if choch_count:
            risks.append("choch_can_signal_transition")

        return EngineContribution(
            engine=TAEngineName.STRUCTURE.value,
            bias=bias,
            score=round(imbalance, 4),
            confidence=round(confidence, 4),
            expected_move_pct=round(expected_move_pct, 6),
            quality=round(quality, 4),
            horizon=PredictionHorizon.H3.value,
            drivers=drivers,
            risks=risks,
            raw={
                "mode": "summary",
                "bullish_score": bullish_score,
                "bearish_score": bearish_score,
                "bos_count": bos_count,
                "choch_count": choch_count,
            },
        )

    # ----------------------------------------------------------------- helpers
    def _empty(self, *, reason: Optional[str] = None) -> EngineContribution:
        return EngineContribution(
            engine=TAEngineName.STRUCTURE.value,
            bias=PredictionBias.NEUTRAL,
            score=0.0, confidence=0.0, expected_move_pct=0.0, quality=0.0,
            horizon=PredictionHorizon.H3.value,
            drivers=[], risks=[reason] if reason else [],
            raw={"reason": reason} if reason else {},
        )

    @staticmethod
    def _normalize_bias(value: str) -> PredictionBias:
        v = (value or "").lower()
        if v in ("bullish", "long", "up"):
            return PredictionBias.BULLISH
        if v in ("bearish", "short", "down"):
            return PredictionBias.BEARISH
        return PredictionBias.NEUTRAL
