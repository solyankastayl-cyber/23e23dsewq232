"""
LevelZonePredictionEngine - PRODUCTION grade.
=============================================
Production logic (when `_raw_data` available):
  * Uses pattern_service.detect_support_resistance under the hood, but
    enriches each level with: touch_count, freshness (bars since last touch),
    proximity to current price.
  * Computes three scenario probabilities for the dominant nearby level:
      bounce_probability       (price holds, reverses)
      breakout_probability     (price breaks through with energy)
      sweep_probability        (price wicks beyond and reclaims = liquidity grab)
  * Final bias derived from which scenario dominates.

Fallback (summary): legacy nearest-level proximity logic.
"""

from typing import Any, Dict, Iterable, List, Optional, Tuple

from modules.ta_prediction_intelligence.types import (
    EngineContribution,
    PredictionBias,
    PredictionHorizon,
    TAEngineName,
)


class LevelZonePredictionEngine:
    PROXIMITY_RADIUS_PCT = 0.030  # within 3% counts as "near"
    TOUCH_TOLERANCE_PCT = 0.0035  # 0.35% tolerance for counting a touch

    def analyze(self, setup: Dict[str, Any]) -> EngineContribution:
        raw = setup.get("_raw_data")
        if raw and raw.get("candles"):
            return self._analyze_production(raw)
        return self._analyze_summary(setup)

    # ----------------------------------------------------------------- production
    def _analyze_production(self, raw: Dict[str, Any]) -> EngineContribution:
        candles: List[Dict[str, Any]] = raw.get("candles") or []
        price: float = float(raw.get("current_price") or 0)
        atr_pct: Optional[float] = raw.get("atr_pct")
        if not candles or price <= 0:
            return self._empty("no_price_or_candles")

        # Re-derive support/resistance with touch enrichment.
        levels = self._derive_levels_with_touches(candles, price)
        if not levels:
            return self._empty("no_levels_detected")

        # Pick nearest support BELOW and nearest resistance ABOVE.
        sup = max((lv for lv in levels if lv["type"] == "support" and lv["price"] < price),
                  key=lambda lv: lv["price"], default=None)
        res = min((lv for lv in levels if lv["type"] == "resistance" and lv["price"] > price),
                  key=lambda lv: lv["price"], default=None)
        if not sup and not res:
            return self._empty("no_nearby_levels")

        # Distance % to each side
        d_sup = (price - sup["price"]) / price if sup else None
        d_res = (res["price"] - price) / price if res else None

        # Pick the dominant nearby level
        nearer, side, dist = self._pick_nearer(sup, res, d_sup, d_res)
        if nearer is None:
            return self._empty("no_levels_within_radius")

        # Strength: more touches + freshness => stronger level
        touch_count = int(nearer.get("touch_count") or 0)
        freshness_bars = nearer.get("freshness_bars")  # smaller = fresher
        strength_norm = min(1.0, touch_count / 5.0)
        # Freshness penalty: very stale levels (>50 bars) lose strength.
        if isinstance(freshness_bars, int):
            if freshness_bars > 50:
                strength_norm *= 0.6
            elif freshness_bars > 100:
                strength_norm *= 0.3

        # Proximity factor (closer => stronger pull). Use ATR-aware radius if known.
        radius = atr_pct * 2.0 if (atr_pct and atr_pct > 0) else self.PROXIMITY_RADIUS_PCT
        proximity = max(0.0, 1.0 - min(dist / radius, 1.0)) if radius > 0 else 0.0

        # Three scenario probabilities (heuristic, sum-normalised).
        # Bounce: strong level, close but not touching, room for reversal.
        # Breakout: weak level (low touches) OR very close, recent direction agrees.
        # Sweep: very close, level is fresh and strong (liquidity above)
        bounce_p = strength_norm * proximity * 0.9
        breakout_p = (1.0 - strength_norm) * proximity * 0.7 + 0.10
        sweep_p = strength_norm * proximity * 0.4
        # Recent direction adjustment (last 3 candles)
        recent_dir = self._recent_direction(candles, lookback=3)
        if side == "resistance":
            if recent_dir == "bullish":
                breakout_p *= 1.3
                bounce_p *= 0.8
            elif recent_dir == "bearish":
                bounce_p *= 1.2
        else:  # support
            if recent_dir == "bearish":
                breakout_p *= 1.3  # breakout DOWN through support
                bounce_p *= 0.8
            elif recent_dir == "bullish":
                bounce_p *= 1.2

        total_p = bounce_p + breakout_p + sweep_p
        if total_p <= 0:
            return self._empty("degenerate_probabilities")
        bounce_p, breakout_p, sweep_p = (bounce_p / total_p, breakout_p / total_p, sweep_p / total_p)

        # Decide zone_action and bias
        max_prob = max(bounce_p, breakout_p, sweep_p)
        if max_prob == bounce_p:
            if side == "resistance":
                zone_action = "resistance_rejection"
                bias = PredictionBias.BEARISH
            else:
                zone_action = "support_bounce"
                bias = PredictionBias.BULLISH
        elif max_prob == breakout_p:
            if side == "resistance":
                zone_action = "resistance_breakout"
                bias = PredictionBias.BULLISH
            else:
                zone_action = "support_breakdown"
                bias = PredictionBias.BEARISH
        else:
            # Sweep: short-term reversal AFTER the wick
            if side == "resistance":
                zone_action = "sweep_above_then_reject"
                bias = PredictionBias.BEARISH
            else:
                zone_action = "sweep_below_then_bounce"
                bias = PredictionBias.BULLISH

        confidence = round(min(1.0, max_prob * 0.95), 4)
        quality = round(strength_norm * 0.6 + proximity * 0.4, 4)
        # expected_move: the distance the level offers as the next leg
        expected_move_pct = round(min(0.030, dist + (atr_pct or 0.005)), 6)

        drivers: List[str] = [
            f"price_near_{side}",
            f"touch_count_{touch_count}",
            f"zone_action_{zone_action}",
        ]
        if isinstance(freshness_bars, int):
            drivers.append(f"freshness_{freshness_bars}_bars")

        risks: List[str] = []
        if breakout_p > 0.30 and zone_action.endswith("_rejection"):
            risks.append("breakout_alternative_active")
        if sweep_p > 0.20:
            risks.append("sweep_scenario_possible")
        if quality < 0.3:
            risks.append("weak_level_quality")

        return EngineContribution(
            engine=TAEngineName.LEVEL_ZONE.value,
            bias=bias,
            score=round(max_prob, 4),
            confidence=confidence,
            expected_move_pct=expected_move_pct,
            quality=quality,
            horizon=PredictionHorizon.H3.value,
            drivers=drivers,
            risks=risks,
            raw={
                "price": price, "side": side, "distance_pct": round(dist, 6),
                "level_price": nearer["price"],
                "touch_count": touch_count, "freshness_bars": freshness_bars,
                "bounce_p": round(bounce_p, 4),
                "breakout_p": round(breakout_p, 4),
                "sweep_p": round(sweep_p, 4),
                "recent_direction": recent_dir,
                "zone_action": zone_action,
            },
        )

    # ----------------------------------------------------------------- summary fallback
    def _analyze_summary(self, setup: Dict[str, Any]) -> EngineContribution:
        render = setup.get("render_plan", {}) or {}
        levels = render.get("levels") or setup.get("levels") or {}
        decision = setup.get("decision", {}) or {}
        price = self._get_price(setup)
        if not price:
            return self._empty("no_price")

        support = self._extract_level(levels, ["support", "support_zone", "nearest_support"])
        resistance = self._extract_level(levels, ["resistance", "resistance_zone", "nearest_resistance"])
        if not support and not resistance:
            return self._empty("no_levels")

        d_sup = abs(price - support) / price if support else None
        d_res = abs(resistance - price) / price if resistance else None
        bias = PredictionBias.NEUTRAL
        confidence = 0.0
        drivers: List[str] = []
        risks: List[str] = ["summary_mode_no_touch_history"]

        if d_sup is not None and (d_res is None or d_sup < d_res):
            bias = PredictionBias.BULLISH
            confidence = max(0.0, 1.0 - min(d_sup / 0.03, 1.0))
            drivers.append("near_support")
        elif d_res is not None:
            bias = PredictionBias.BEARISH
            confidence = max(0.0, 1.0 - min(d_res / 0.03, 1.0))
            drivers.append("near_resistance")
        if decision.get("bias") in ("bullish", "bearish") and str(decision.get("bias")) != bias.value:
            risks.append("level_pressure_conflicts_with_decision_bias")

        expected_move_pct = min(0.025, confidence * 0.02)
        return EngineContribution(
            engine=TAEngineName.LEVEL_ZONE.value,
            bias=bias,
            score=round(confidence, 4),
            confidence=round(confidence, 4),
            expected_move_pct=round(expected_move_pct, 6),
            quality=round(confidence * 0.5, 4),
            horizon=PredictionHorizon.H3.value,
            drivers=drivers,
            risks=risks,
            raw={"mode": "summary", "price": price, "support": support,
                 "resistance": resistance, "dist_support": d_sup, "dist_resistance": d_res},
        )

    # ----------------------------------------------------------------- helpers
    def _derive_levels_with_touches(
        self, candles: List[Dict[str, Any]], price: float
    ) -> List[Dict[str, Any]]:
        """Re-detect S/R via pattern_service and enrich each level with touch data."""
        out: List[Dict[str, Any]] = []
        try:
            from modules.research_analytics.patterns import get_pattern_service

            ps = get_pattern_service()
            sr = ps.detect_support_resistance(candles) or []
        except Exception:
            sr = []

        if not sr:
            return out

        n = len(candles)
        for lvl in sr:
            ltype = getattr(lvl, "type", None)
            lprice = getattr(lvl, "price", None)
            if ltype is None or lprice is None:
                continue
            lprice_f = float(lprice)
            tol = lprice_f * self.TOUCH_TOLERANCE_PCT
            touches: List[int] = []
            for i, c in enumerate(candles):
                hi = float(c.get("high") or 0)
                lo = float(c.get("low") or 0)
                if abs(hi - lprice_f) <= tol or abs(lo - lprice_f) <= tol:
                    touches.append(i)
            freshness_bars = (n - 1 - touches[-1]) if touches else None
            out.append({
                "type": ltype,
                "price": lprice_f,
                "touch_count": len(touches),
                "freshness_bars": freshness_bars,
                "strength": getattr(lvl, "strength", None),
            })
        return out

    def _pick_nearer(
        self,
        sup: Optional[Dict[str, Any]],
        res: Optional[Dict[str, Any]],
        d_sup: Optional[float],
        d_res: Optional[float],
    ) -> Tuple[Optional[Dict[str, Any]], str, float]:
        # Nearer side wins.
        candidates = []
        if sup and d_sup is not None and d_sup <= self.PROXIMITY_RADIUS_PCT * 1.5:
            candidates.append((sup, "support", d_sup))
        if res and d_res is not None and d_res <= self.PROXIMITY_RADIUS_PCT * 1.5:
            candidates.append((res, "resistance", d_res))
        if not candidates:
            return None, "", 0.0
        candidates.sort(key=lambda x: x[2])
        return candidates[0]

    @staticmethod
    def _recent_direction(candles: List[Dict[str, Any]], lookback: int = 3) -> str:
        if len(candles) < lookback + 1:
            return "neutral"
        first = float(candles[-lookback - 1].get("close") or 0)
        last = float(candles[-1].get("close") or 0)
        if last > first * 1.001:
            return "bullish"
        if last < first * 0.999:
            return "bearish"
        return "neutral"

    def _empty(self, reason: Optional[str] = None) -> EngineContribution:
        return EngineContribution(
            engine=TAEngineName.LEVEL_ZONE.value,
            bias=PredictionBias.NEUTRAL,
            score=0.0, confidence=0.0, expected_move_pct=0.0, quality=0.0,
            horizon=PredictionHorizon.H3.value,
            drivers=[], risks=[reason] if reason else [], raw={"reason": reason} if reason else {},
        )

    def _get_price(self, setup: Dict[str, Any]) -> Optional[float]:
        for path in [("price",), ("current_price",), ("market", "price"), ("summary", "price")]:
            cur: Any = setup
            ok = True
            for key in path:
                if not isinstance(cur, dict) or key not in cur:
                    ok = False
                    break
                cur = cur[key]
            if ok:
                try:
                    return float(cur)
                except Exception:
                    pass
        return None

    def _extract_level(self, levels: Dict[str, Any], keys: Iterable[str]) -> Optional[float]:
        for k in keys:
            v = levels.get(k)
            if isinstance(v, dict):
                v = v.get("price") or v.get("value") or v.get("mid")
            if isinstance(v, list) and v:
                first = v[0]
                if isinstance(first, dict):
                    v = first.get("price") or first.get("value") or first.get("mid")
                else:
                    v = first
            try:
                if v is not None:
                    return float(v)
            except Exception:
                continue
        return None
