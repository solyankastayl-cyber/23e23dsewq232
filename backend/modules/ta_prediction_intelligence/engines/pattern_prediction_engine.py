"""
PatternPredictionEngine - PRODUCTION grade.
=============================================
Production logic (when `_raw_data.candles` available, plus pattern_service):
  * Re-detect patterns from raw candles for richest output (lifecycle, points)
  * Compute completion_pct from pattern lifecycle (forming/developing/active/confirmed)
  * Compute symmetry score for symmetric patterns
  * Volume confirmation: did breakout candle have above-average volume?
  * Alternative pattern conflict: count alternatives with OPPOSITE direction
  * quality = pattern textbook-cleanness, independent of direction confidence

Fallback (summary): legacy primary-pattern lookup from setup dict.
"""

from typing import Any, Dict, List, Optional

from modules.ta_prediction_intelligence.types import (
    EngineContribution,
    PredictionBias,
    PredictionHorizon,
    TAEngineName,
)


class PatternPredictionEngine:
    REVERSAL_BEARISH = {"head_and_shoulders", "double_top", "rising_wedge"}
    REVERSAL_BULLISH = {"inverse_head_and_shoulders", "double_bottom", "falling_wedge"}
    CONTINUATION_BULLISH = {"bull_flag", "ascending_triangle", "cup_and_handle"}
    CONTINUATION_BEARISH = {"bear_flag", "descending_triangle"}

    LIFECYCLE_COMPLETION: Dict[str, float] = {
        "forming": 0.30,
        "developing": 0.55,
        "active": 0.80,
        "confirmed": 0.95,
    }

    def analyze(self, setup: Dict[str, Any]) -> EngineContribution:
        raw = setup.get("_raw_data")
        if raw and raw.get("candles"):
            return self._analyze_production(raw)
        return self._analyze_summary(setup)

    # ----------------------------------------------------------------- production
    def _analyze_production(self, raw: Dict[str, Any]) -> EngineContribution:
        candles: List[Dict[str, Any]] = raw.get("candles") or []
        if len(candles) < 30:
            return self._empty("insufficient_candles")
        try:
            from modules.research_analytics.patterns import get_pattern_service
            ps = get_pattern_service()
            detected = ps.detect_patterns(candles, "", "") or []
        except Exception:
            detected = []
        if not detected:
            return self._empty("no_patterns_detected")

        # Pick pattern with the highest confidence as primary
        primary = max(detected, key=lambda p: float(getattr(p, "confidence", 0) or 0))
        primary_name = str(getattr(primary, "pattern_type", "") or getattr(primary, "name", "")).lower()
        primary_conf_raw = float(getattr(primary, "confidence", 0) or 0)
        primary_lifecycle = str(getattr(primary, "lifecycle", "") or getattr(primary, "status", "")).lower()
        primary_dir_explicit = str(getattr(primary, "direction", "") or "").lower()

        bias = self._bias_from_name(primary_name)
        if bias == PredictionBias.NEUTRAL and primary_dir_explicit in ("bullish", "bearish"):
            bias = PredictionBias(primary_dir_explicit)
        if bias == PredictionBias.NEUTRAL:
            return self._empty(f"unknown_pattern_{primary_name or 'no_name'}")

        # Completion from lifecycle
        completion = self.LIFECYCLE_COMPLETION.get(primary_lifecycle, 0.5)

        # Volume confirmation: last bar volume vs 20-bar avg
        vols = [float(c.get("volume") or 0) for c in candles[-21:]]
        avg_vol = sum(vols[:-1]) / 20 if len(vols) > 1 and sum(vols[:-1]) > 0 else 0.0
        last_vol = vols[-1] if vols else 0.0
        volume_confirms = (avg_vol > 0 and last_vol > avg_vol * 1.3)

        # Alternative pattern conflict
        alternatives = [p for p in detected if p is not primary]
        opposite_count = 0
        same_count = 0
        for alt in alternatives:
            alt_bias = self._bias_from_name(
                str(getattr(alt, "pattern_type", "") or getattr(alt, "name", "")).lower()
            )
            alt_dir_explicit = str(getattr(alt, "direction", "") or "").lower()
            if alt_bias == PredictionBias.NEUTRAL and alt_dir_explicit in ("bullish", "bearish"):
                alt_bias = PredictionBias(alt_dir_explicit)
            if alt_bias == bias:
                same_count += 1
            elif alt_bias != PredictionBias.NEUTRAL:
                opposite_count += 1

        # Quality components
        normalised_conf = primary_conf_raw if primary_conf_raw <= 1 else primary_conf_raw / 100.0
        normalised_conf = max(0.0, min(1.0, normalised_conf))
        symmetry = self._symmetry_score(primary)

        quality = round(
            min(1.0, max(0.0,
                completion * 0.45 + symmetry * 0.20 + (0.20 if volume_confirms else 0.0)
                + normalised_conf * 0.15)),
            4,
        )

        # Confidence: pattern detector raw conf, scaled by completion, dampened by alts
        confidence = normalised_conf * (0.6 + completion * 0.4)
        if volume_confirms:
            confidence = min(1.0, confidence * 1.10)
        if opposite_count > 0:
            confidence *= max(0.4, 1.0 - opposite_count * 0.20)
        confidence = round(min(1.0, max(0.0, confidence)), 4)

        expected_move_pct = round(min(0.05, confidence * 0.035), 6)

        # Drivers / risks
        drivers: List[str] = [
            f"primary_pattern_{primary_name}",
            f"lifecycle_{primary_lifecycle or 'unknown'}",
            f"completion_{int(completion * 100)}_pct",
        ]
        if volume_confirms:
            drivers.append("volume_confirmation")
        if same_count:
            drivers.append(f"agreeing_alternatives_{same_count}")

        risks: List[str] = []
        if opposite_count:
            risks.append(f"opposing_alternative_patterns_{opposite_count}")
        if not volume_confirms and primary_lifecycle == "confirmed":
            risks.append("breakout_lacks_volume")
        if symmetry < 0.4:
            risks.append("poor_symmetry")
        if completion < 0.5:
            risks.append("pattern_still_forming")

        return EngineContribution(
            engine=TAEngineName.PATTERN.value,
            bias=bias,
            score=round(confidence, 4),
            confidence=confidence,
            expected_move_pct=expected_move_pct,
            quality=quality,
            horizon=PredictionHorizon.H6.value,
            drivers=drivers,
            risks=risks,
            raw={
                "primary": {
                    "name": primary_name,
                    "confidence": normalised_conf,
                    "lifecycle": primary_lifecycle,
                    "direction": primary_dir_explicit,
                },
                "completion": completion,
                "symmetry": symmetry,
                "volume_confirms": volume_confirms,
                "alternatives_count": len(alternatives),
                "opposite_count": opposite_count,
                "same_count": same_count,
            },
        )

    # ----------------------------------------------------------------- summary fallback
    def _analyze_summary(self, setup: Dict[str, Any]) -> EngineContribution:
        render = setup.get("render_plan", {}) or {}
        patterns = render.get("patterns", {}) or {}
        primary = patterns.get("primary") or setup.get("primary_pattern") or {}
        if not primary:
            return self._empty("no_pattern")
        name = str(primary.get("name") or primary.get("type") or "").lower()
        bias = self._bias_from_name(name)
        if bias == PredictionBias.NEUTRAL:
            return self._empty("unknown_pattern_in_summary")
        cf = self._normalize_confidence(primary.get("confidence") or primary.get("score") or 0)
        lifecycle = str(primary.get("lifecycle") or primary.get("status") or "").lower()
        completion = self.LIFECYCLE_COMPLETION.get(lifecycle, 0.5)
        confidence = round(min(1.0, cf * (0.6 + completion * 0.4)), 4)
        expected_move_pct = round(min(0.05, confidence * 0.035), 6)
        return EngineContribution(
            engine=TAEngineName.PATTERN.value,
            bias=bias,
            score=confidence, confidence=confidence,
            expected_move_pct=expected_move_pct,
            quality=round(completion * 0.6, 4),
            horizon=PredictionHorizon.H6.value,
            drivers=[f"summary_pattern_{name}", f"lifecycle_{lifecycle or 'unknown'}"],
            risks=["summary_mode_no_volume_check"],
            raw={"mode": "summary", "primary": primary},
        )

    # ----------------------------------------------------------------- helpers
    def _bias_from_name(self, name: str) -> PredictionBias:
        if name in self.REVERSAL_BULLISH or name in self.CONTINUATION_BULLISH:
            return PredictionBias.BULLISH
        if name in self.REVERSAL_BEARISH or name in self.CONTINUATION_BEARISH:
            return PredictionBias.BEARISH
        return PredictionBias.NEUTRAL

    def _normalize_confidence(self, value: Any) -> float:
        try:
            v = float(value)
        except Exception:
            return 0.0
        if v > 1:
            v = v / 100
        return max(0.0, min(1.0, v))

    def _symmetry_score(self, pattern: Any) -> float:
        """
        Compute a 0..1 symmetry estimate from pattern points (if available).
        For two-shoulder patterns: how close shoulder heights are to each other.
        Falls back to 0.5 (neutral) if not computable.
        """
        try:
            points = getattr(pattern, "points", None) or []
            if len(points) >= 4:
                # Use the first and last point heights as proxy.
                first = float(getattr(points[0], "price", 0) or 0)
                last = float(getattr(points[-1], "price", 0) or 0)
                if first > 0 and last > 0:
                    diff = abs(first - last) / max(first, last)
                    return max(0.0, min(1.0, 1.0 - diff * 5.0))
        except Exception:
            pass
        return 0.5

    def _empty(self, reason: Optional[str] = None) -> EngineContribution:
        return EngineContribution(
            engine=TAEngineName.PATTERN.value,
            bias=PredictionBias.NEUTRAL,
            score=0.0, confidence=0.0, expected_move_pct=0.0, quality=0.0,
            horizon=PredictionHorizon.H6.value,
            drivers=[], risks=[reason] if reason else [], raw={"reason": reason} if reason else {},
        )
