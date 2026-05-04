"""
Combined Analysis Service — joins TA + Prediction + Hypothesis.

Architecture:
    CombinedAnalysisService.get_combined(symbol, tf)
        ├── _fetch_ta(symbol, tf)            → returns ta block or None
        ├── _fetch_prediction(symbol, tf)    → returns prediction block or None
        ├── _fetch_best_hypothesis(symbol, tf) → returns hypothesis block or None
        └── _build_combined(ta, pred, hypo)  → final agreement + verdicts

NO HTTP self-calls — every source is invoked in-process via its service module.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple


# ════════════════════════════════════════════════════════════════════════════
# DIRECTION NORMALIZATION
# ════════════════════════════════════════════════════════════════════════════

def normalize_direction(x: Any) -> str:
    """
    Map any provider's direction tag → {bullish, bearish, neutral}.

    Accepts: "bullish"/"long"/"up"/"LONG", "bearish"/"short"/"down"/"SHORT",
    anything else → "neutral".
    """
    if x is None:
        return "neutral"
    s = str(x).strip().lower()
    if s in ("bullish", "long", "up", "buy"):
        return "bullish"
    if s in ("bearish", "short", "down", "sell"):
        return "bearish"
    return "neutral"


def direction_agreement(a: str, b: str) -> float:
    """
    Pairwise direction agreement.

      same non-neutral  → 1.0
      neutral on either → 0.5  (no information, partial agreement)
      opposite          → 0.0
    """
    if a == "neutral" or b == "neutral":
        return 0.5
    if a == b:
        return 1.0
    return 0.0


# ════════════════════════════════════════════════════════════════════════════
# AGREEMENT SCORING (the spec)
# ════════════════════════════════════════════════════════════════════════════

def build_agreement(
    ta_dir: Optional[str],
    pred_dir: Optional[str],
    hypo_dir: Optional[str],
    *,
    ta_conf: float = 0.0,
    pred_conf: float = 0.0,
    hypo_pf: Optional[float] = None,
    hypo_sample_size: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Compute agreement score + per-pair components + final bias.

    Steps (per Pass 3 spec + Pass 3.5 hardening):
      1. Normalize each direction tag.
      2. ta_pred = direction_agreement(ta, pred)
         ta_hypo = direction_agreement(ta, hypo)
         pred_hypo = direction_agreement(pred, hypo)
      3. weighted score = ta_pred*0.4 + ta_hypo*0.4 + pred_hypo*0.2
      4. quality boost from hypothesis profit_factor:
           hypo_quality = min(1.0, PF/3.0)
           score *= (0.5 + 0.5 * hypo_quality)
      5. final bias by weighted vote.

    HARDENING (Pass 3.5):
      H1. Drift sanity — if ta.dir != pred.dir AND neither is neutral
          → cap final score at 0.70 (no "high agreement under conflict").
      H2. Hypothesis sample_size guard — if sample_size < 30
          → hypothesis quality booster is dropped (treat as no hypothesis evidence).

    Honest behaviour: missing pieces stay None and the agreement_score
    drops automatically — nothing is fabricated to keep the number high.
    """
    ta = normalize_direction(ta_dir) if ta_dir is not None else None
    pr = normalize_direction(pred_dir) if pred_dir is not None else None
    hy = normalize_direction(hypo_dir) if hypo_dir is not None else None

    # Pairwise agreement only between sources we actually have.
    pair_components: Dict[str, Optional[float]] = {
        "ta_vs_prediction": direction_agreement(ta, pr) if (ta and pr) else None,
        "ta_vs_hypothesis": direction_agreement(ta, hy) if (ta and hy) else None,
        "prediction_vs_hypothesis": direction_agreement(pr, hy) if (pr and hy) else None,
    }

    # Weighted aggregate over the components that are actually present.
    weights = {"ta_vs_prediction": 0.4, "ta_vs_hypothesis": 0.4, "prediction_vs_hypothesis": 0.2}
    num = 0.0
    den = 0.0
    for k, w in weights.items():
        v = pair_components[k]
        if v is not None:
            num += v * w
            den += w
    raw_agreement = (num / den) if den > 0 else 0.0

    # ─── H2: Hypothesis sample_size guard ──────────────────────────────
    # Hypothesis with too few trades is statistical noise — drop the booster.
    hypo_credible = bool(
        hypo_pf and hypo_pf > 0
        and (hypo_sample_size is None or int(hypo_sample_size) >= 30)
    )
    hypo_below_min = bool(
        hypo_pf and hypo_pf > 0
        and hypo_sample_size is not None
        and int(hypo_sample_size) < 30
    )

    if hypo_credible:
        hypo_quality = min(1.0, float(hypo_pf) / 3.0)
        score = raw_agreement * (0.5 + 0.5 * hypo_quality)
    else:
        score = raw_agreement * 0.75 if hy is None else raw_agreement * 0.85

    score = max(0.0, min(1.0, score))

    # ─── H1: Drift sanity — cap on TA↔Prediction conflict ──────────────
    drift_conflict = False
    if ta and pr and ta != "neutral" and pr != "neutral" and ta != pr:
        drift_conflict = True
        score = min(score, 0.70)

    # ─── Final direction by weighted votes ────────────────────────────────
    votes: List[Tuple[str, float]] = []
    if ta is not None:
        votes.append((ta, max(0.0, min(1.0, float(ta_conf or 0.0)))))
    if pr is not None:
        votes.append((pr, max(0.0, min(1.0, float(pred_conf or 0.0)))))
    if hy is not None and hypo_credible:
        # Cap PF contribution so a 10x PF outlier doesn't dominate the bias
        votes.append((hy, min(2.0, float(hypo_pf)) / 2.0))

    score_map = {"bullish": 0.0, "bearish": 0.0, "neutral": 0.0}
    for d, w in votes:
        score_map[d] = score_map.get(d, 0.0) + w

    if not votes or all(v == 0 for v in score_map.values()):
        final_bias = "neutral"
    else:
        final_bias = max(score_map, key=score_map.get)

    # ─── Confidence of the agreement ──────────────────────────────────────
    confidences = []
    if ta_conf and ta_conf > 0:
        confidences.append(float(ta_conf))
    if pred_conf and pred_conf > 0:
        confidences.append(float(pred_conf))
    if hypo_credible:
        confidences.append(min(1.0, float(hypo_pf) / 3.0))
    final_confidence = round(sum(confidences) / len(confidences), 4) if confidences else 0.0

    return {
        "score": round(score, 4),
        "direction": final_bias,
        "confidence": final_confidence,
        "components": {k: (round(v, 4) if v is not None else None) for k, v in pair_components.items()},
        "votes": [{"direction": d, "weight": round(w, 4)} for d, w in votes],
        "guards": {
            "drift_conflict": drift_conflict,            # H1
            "hypo_below_min_sample": hypo_below_min,      # H2
            "hypo_credible": hypo_credible,
        },
    }


def quality_label(score: float) -> str:
    """Qualitative label per Pass 3 spec."""
    if score > 0.75:
        return "HIGH"
    if score > 0.55:
        return "MEDIUM"
    return "LOW"


# ════════════════════════════════════════════════════════════════════════════
# SOURCE FETCHERS (in-process, NO HTTP loops)
# ════════════════════════════════════════════════════════════════════════════

async def _fetch_ta(symbol: str, timeframe: str) -> Optional[Dict[str, Any]]:
    """
    Get TA signal explanation block.
    Same one /api/v1/signal/explanation returns, but without HTTP roundtrip.
    """
    try:
        from modules.signal_explanation.explainer import get_signal_explainer
        from modules.research_analytics.chart_data import get_chart_data_service
        from modules.research_analytics.patterns import get_pattern_service
        from modules.research_analytics.hypothesis_viz import get_hypothesis_viz_service
        from modules.research_analytics.fractal_viz import get_fractal_viz_service

        chart_data = await get_chart_data_service().get_chart_data(
            symbol=symbol.upper(), timeframe=timeframe, limit=300
        )
        hyp = get_hypothesis_viz_service().build_hypothesis_visualization(
            chart_data.candles, symbol, timeframe
        )
        patterns = get_pattern_service().detect_patterns(chart_data.candles, symbol, timeframe)
        fractal_result = get_fractal_viz_service().find_fractal_matches(
            chart_data.candles, symbol, timeframe
        )

        # Honest: no fabricated alpha/regime score placeholders (Pass 2 discipline).
        hyp_dict = {
            "hypothesis_id": hyp.hypothesis_id,
            "symbol": symbol,
            "timeframe": timeframe,
            "direction": hyp.direction,
            "confidence": hyp.confidence,
            "alpha_score": 0.0,
            "regime_score": 0.0,
            "microstructure_score": 0.0,
            "capital_flow_score": 0.0,
            "fractal_similarity_score": (
                fractal_result.matches[0].similarity if fractal_result.matches else 0.0
            ),
            "alpha_sources": [],
        }
        explanation = get_signal_explainer().explain_hypothesis(
            hypothesis=hyp_dict,
            patterns=[p.model_dump() for p in patterns],
            fractal_matches=[m.model_dump() for m in fractal_result.matches],
        )
        d = explanation.model_dump()
        return {
            "direction": normalize_direction(d.get("direction")),
            "confidence": float(d.get("confidence") or 0.0),
            "strength": d.get("strength"),
            "summary": d.get("summary"),
        }
    except Exception as exc:
        print(f"[CombinedAnalysis] TA fetch failed: {exc}")
        return None


async def _fetch_prediction(symbol: str, timeframe: str) -> Optional[Dict[str, Any]]:
    """
    Pull single-TF forecast from ta_prediction service (Pass 2 build).
    """
    try:
        from modules.ta_prediction.ta_prediction_service import build_ta_single_forecast
        r = await build_ta_single_forecast(symbol=symbol, timeframe=timeframe)
        if not r or not r.get("ok"):
            return None
        targets = r.get("targets") or {}
        return {
            "direction": normalize_direction(r.get("direction")),
            "confidence": float(r.get("confidence") or 0.0),
            "expected_move_pct": targets.get("expected_move_pct"),
            "target_price": targets.get("target_price"),
            "max_upside": targets.get("max_upside"),
            "max_drawdown": targets.get("max_drawdown"),
        }
    except Exception as exc:
        print(f"[CombinedAnalysis] Prediction fetch failed: {exc}")
        return None


def _fetch_best_hypothesis(symbol: str, timeframe: str) -> Optional[Dict[str, Any]]:
    """
    Pick the best evaluated hypothesis applicable to (symbol, tf).

    Strategy:
      * pull all completed results from the repo;
      * filter by hypothesis applicability (timeframe, symbol);
      * sort by profit_factor DESC, win_rate DESC;
      * take #1.

    Returns None when there are no completed runs — Pass 3 forbids
    inventing hypothesis data.
    """
    try:
        from modules.research.hypothesis_engine.hypothesis_repository import (
            HypothesisRepository,
        )
        from modules.research.hypothesis_engine.hypothesis_registry import (
            get_hypothesis_registry,
        )

        repo = HypothesisRepository()
        # Pull everything (limit covers any dataset we'd reasonably hit)
        results: List[Dict[str, Any]] = list(
            repo.db.hypothesis_results.find({}, {"_id": 0}).limit(500)
        )
        if not results:
            return None

        registry = get_hypothesis_registry()
        sym_upper = symbol.upper().replace("USDT", "").replace("USD", "") or "BTC"
        tf_lower = timeframe.lower()

        applicable: List[Tuple[Dict[str, Any], Dict[str, Any]]] = []
        for r in results:
            h_id = r.get("hypothesis_id")
            hdef = registry.get(h_id)
            if not hdef:
                continue
            tfs = [t.lower() for t in (hdef.applicable_timeframes or [])]
            syms = [s.upper() for s in (hdef.applicable_symbols or [])]
            tf_match = (not tfs) or (tf_lower in tfs) or (timeframe.upper() in tfs)
            sym_match = (not syms) or (sym_upper in syms)
            if not (tf_match and sym_match):
                continue
            applicable.append((r, hdef.to_dict()))

        if not applicable:
            return None

        applicable.sort(
            key=lambda pair: (
                float(pair[0].get("profit_factor") or 0.0),
                float(pair[0].get("win_rate") or 0.0),
            ),
            reverse=True,
        )
        result, hdef = applicable[0]

        eo = (hdef.get("expected_outcome") or {})
        return {
            "strategy": hdef.get("hypothesis_id"),
            "name": hdef.get("name"),
            "category": hdef.get("category"),
            "direction": normalize_direction(eo.get("direction")),
            "win_rate": float(result.get("win_rate") or 0.0),
            "profit_factor": float(result.get("profit_factor") or 0.0),
            "expectancy": float(result.get("expectancy") or 0.0),
            "max_drawdown": float(result.get("max_drawdown") or 0.0),
            "sample_size": int(result.get("sample_size") or 0),
            "verdict": result.get("verdict"),
        }
    except Exception as exc:
        print(f"[CombinedAnalysis] Hypothesis fetch failed: {exc}")
        return None


# ════════════════════════════════════════════════════════════════════════════
# COMPOSER
# ════════════════════════════════════════════════════════════════════════════

def build_combined(
    symbol: str,
    timeframe: str,
    ta: Optional[Dict[str, Any]],
    prediction: Optional[Dict[str, Any]],
    hypothesis: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Pure composition. No I/O, no fetchers — easy to unit-test.

    Honors Pass 3 contract + Pass 3.5 hardening:
      * missing pieces → null (preserved)
      * agreement uses only available pieces (degrades cleanly)
      * quality is HONEST (LOW on conflict, MEDIUM on neutral consensus)
      * drift_conflict cap (H1) and hypo sample_size guard (H2) applied
    """
    agreement = build_agreement(
        ta_dir=(ta or {}).get("direction"),
        pred_dir=(prediction or {}).get("direction"),
        hypo_dir=(hypothesis or {}).get("direction"),
        ta_conf=float((ta or {}).get("confidence") or 0.0),
        pred_conf=float((prediction or {}).get("confidence") or 0.0),
        hypo_pf=(hypothesis or {}).get("profit_factor"),
        hypo_sample_size=(hypothesis or {}).get("sample_size"),
    )
    out = {
        "symbol": symbol,
        "timeframe": timeframe.upper(),
        "ta": ta,
        "prediction": prediction,
        "hypothesis": hypothesis,
        "agreement": agreement,
        "final_bias": agreement["direction"],
        "quality": quality_label(agreement["score"]),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    # Run consistency assertions (silent-bug guard). Returns issues list,
    # never raises — so production path is safe even on degraded data.
    out["validation"] = validate_combined(out)
    return out


# ════════════════════════════════════════════════════════════════════════════
# CONSISTENCY GUARDS (Pass 3.5)
# ════════════════════════════════════════════════════════════════════════════

def validate_combined(analysis: Dict[str, Any]) -> Dict[str, Any]:
    """
    Run consistency checks against the assembled combined-analysis dict.

    Returns:
      {
        "ok": bool,         # True if no issues
        "issues": [str],    # human-readable problem list
      }

    NEVER raises. Issues surface in the API payload so monitoring/UI can
    flag inconsistent states without crashing the request.

    Checks:
      C1. ta.direction in {bullish, bearish, neutral}
      C2. 0 <= ta.confidence <= 1
      C3. 0 <= prediction.confidence <= 1 (when prediction present)
      C4. agreement.score in [0..1]
      C5. quality ∈ {HIGH, MEDIUM, LOW}
      C6. final_bias != neutral  ⇒  agreement.score > 0.30
          (high agreement with directional bias must have evidence)
      C7. drift_conflict ⇒ agreement.score <= 0.70 (H1 enforcement)
      C8. hypothesis present with sample_size < 30 ⇒ guards.hypo_below_min_sample True
      C9. quality == HIGH ⇒ agreement.score > 0.75
    """
    issues: List[str] = []

    ta = analysis.get("ta") or {}
    pr = analysis.get("prediction") or {}
    hy = analysis.get("hypothesis")
    agr = analysis.get("agreement") or {}
    final_bias = analysis.get("final_bias")
    quality = analysis.get("quality")

    valid_dirs = {"bullish", "bearish", "neutral"}

    # C1
    if ta:
        if ta.get("direction") not in valid_dirs:
            issues.append(f"C1: ta.direction='{ta.get('direction')}' not in {sorted(valid_dirs)}")
    # C2
    if ta:
        c = ta.get("confidence")
        if c is None or not (0.0 <= float(c) <= 1.0):
            issues.append(f"C2: ta.confidence={c} out of [0..1]")
    # C3
    if pr:
        c = pr.get("confidence")
        if c is None or not (0.0 <= float(c) <= 1.0):
            issues.append(f"C3: prediction.confidence={c} out of [0..1]")
    # C4
    score = agr.get("score")
    if score is None or not (0.0 <= float(score) <= 1.0):
        issues.append(f"C4: agreement.score={score} out of [0..1]")
    # C5
    if quality not in {"HIGH", "MEDIUM", "LOW"}:
        issues.append(f"C5: quality='{quality}' not in [HIGH, MEDIUM, LOW]")
    # C6 — directional bias must have evidence
    if final_bias and final_bias != "neutral" and score is not None and float(score) <= 0.30:
        issues.append(
            f"C6: final_bias='{final_bias}' but agreement.score={score} ≤ 0.30 (directional bias without evidence)"
        )
    # C7 — drift conflict must cap score
    guards = agr.get("guards") or {}
    if guards.get("drift_conflict") and score is not None and float(score) > 0.70:
        issues.append(
            f"C7: drift_conflict True but agreement.score={score} > 0.70 (cap violated)"
        )
    # C8 — hypothesis sample_size flag
    if hy and isinstance(hy.get("sample_size"), (int, float)):
        ss = int(hy["sample_size"])
        if ss < 30 and not guards.get("hypo_below_min_sample"):
            issues.append(f"C8: hypothesis.sample_size={ss} < 30 but guard flag missing")
    # C9 — HIGH quality requires real agreement
    if quality == "HIGH" and (score is None or float(score) <= 0.75):
        issues.append(f"C9: quality=HIGH but agreement.score={score} ≤ 0.75")

    return {"ok": not issues, "issues": issues}


class CombinedAnalysisService:
    """
    Thin orchestration over the in-process fetchers.
    Designed so unit tests can swap fetchers easily.
    """

    async def get_combined(self, symbol: str, timeframe: str) -> Dict[str, Any]:
        sym = (symbol or "BTCUSDT").upper().strip()
        if not sym.endswith("USDT") and not sym.endswith("USD"):
            sym = sym + "USDT"
        tf = (timeframe or "4H").upper()

        ta = await _fetch_ta(sym, tf)
        prediction = await _fetch_prediction(sym, tf)
        hypothesis = _fetch_best_hypothesis(sym, tf)

        return build_combined(sym, tf, ta, prediction, hypothesis)


_singleton: Optional[CombinedAnalysisService] = None


def get_combined_analysis_service() -> CombinedAnalysisService:
    global _singleton
    if _singleton is None:
        _singleton = CombinedAnalysisService()
    return _singleton
