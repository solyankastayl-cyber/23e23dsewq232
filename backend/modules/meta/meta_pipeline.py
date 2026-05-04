"""
Meta Pipeline (Pass 5)

Single source of truth that turns (symbol, timeframe) into a final
shadow-mode decision. Used by BOTH:
  * /api/meta/score        (ad-hoc HTTP endpoint, source="manual")
  * shadow_scheduler       (forward-test loop, source="scheduler")

Architecture:

    combined_analysis_service.get_combined()
            │
            ▼
    build_meta_decision()                 ← Meta core math (untouched)
            │
            ▼
    derive_regime() + apply_policy()      ← per-(sym, tf) overlay
            │
            ▼
    should_skip(regime, score, quality)   ← universal hard filter
            │
            ▼
    final decision dict
            │
            ▼
    (caller decides whether to write a shadow record)

NOTHING in this module calls an exchange or places an order.
"""

from __future__ import annotations

import asyncio
from typing import Any, Dict, Optional, Tuple

import httpx

from modules.analysis.combined_analysis_service import get_combined_analysis_service
from modules.meta.market_regime_service import compute_market_regime
from modules.meta.meta_scoring_engine import build_meta_decision
from modules.meta.policy_registry import (
    apply_policy,
    derive_regime,
    resolve_policy,
    should_skip,
)


async def fetch_system_health() -> Dict[str, Any]:
    """
    Pull canonical system_health from the in-app endpoint.
    On any failure → conservative WARNING default.
    """
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            r = await client.get("http://localhost:8001/api/system/health")
            if r.status_code == 200:
                return r.json()
    except Exception:
        pass
    return {"status": "WARNING", "reason": "health endpoint unavailable"}


def extract_current_price(analysis: Optional[Dict[str, Any]]) -> Optional[float]:
    """Best-effort price extraction without trusting any specific provider shape."""
    if not analysis:
        return None
    for path in (
        ("ta", "current_price"),
        ("ta", "price"),
        ("prediction", "current_price"),
        ("prediction", "spot_price"),
    ):
        node: Any = analysis
        ok = True
        for k in path:
            if not isinstance(node, dict) or k not in node:
                ok = False
                break
            node = node[k]
        if ok:
            try:
                return float(node)
            except (TypeError, ValueError):
                continue
    for k in ("current_price", "price", "spot_price"):
        v = analysis.get(k)
        if v is not None:
            try:
                return float(v)
            except (TypeError, ValueError):
                pass
    return None


def build_snapshot(
    analysis: Optional[Dict[str, Any]],
    decision: Dict[str, Any],
    *,
    current_price: Optional[float] = None,
) -> Dict[str, Any]:
    """Compact snapshot inserted into the shadow record for transparency."""
    a = analysis or {}
    return {
        "ta": a.get("ta"),
        "prediction": a.get("prediction"),
        "agreement_score": (a.get("agreement") or {}).get("score"),
        "quality": decision.get("quality"),
        "current_price": current_price,
    }


async def compute_decision(
    symbol: str,
    timeframe: str,
    *,
    health: Optional[Dict[str, Any]] = None,
) -> Tuple[Dict[str, Any], Dict[str, Any], Any]:
    """
    Full meta pipeline. Returns: (final_decision, analysis, policy).

    final_decision contains everything callers need:
      * strategy_score / allocation / final_bias
      * regime / score_regime / market_regime
      * policy / should_trade / skip_reason / reason
      * analysis_snapshot / health_snapshot

    Phase 6 / P0 contract:
      * `score_regime`  — band derived from strategy_score (uncertain | balanced | overheated).
                          This is the EXISTING universal toxic filter input.
      * `market_regime` — independent context from regime_detector
                          ({label, confidence, model_name, raw, reason}).
                          Used ONLY to route policy. NEVER mutates
                          ta.confidence / prediction.confidence / agreement.score.
    """
    # 1. Single-truth analysis  +  market regime  (parallel where possible)
    combined_service = get_combined_analysis_service()
    analysis_task = asyncio.create_task(
        combined_service.get_combined(symbol=symbol, timeframe=timeframe)
    )
    market_regime_task = asyncio.create_task(
        compute_market_regime(symbol=symbol, timeframe=timeframe)
    )
    analysis = await analysis_task
    market_regime = await market_regime_task

    # 2. Health (caller may pre-fetch to avoid duplicate work)
    if health is None:
        health = await fetch_system_health()

    # 3. Core math (UNCHANGED Pass 4 contract)
    decision = build_meta_decision(analysis=analysis, health=health)

    # 4. score_regime — keep the existing universal regime label intact.
    score_regime = derive_regime(decision.get("strategy_score"))
    decision["regime"] = score_regime          # back-compat field used everywhere
    decision["score_regime"] = score_regime    # explicit alias for clarity

    # 5. Per-(sym, tf, market_regime) policy resolution.
    market_regime_label = market_regime.get("label") if isinstance(market_regime, dict) else None
    policy = resolve_policy(symbol, timeframe, market_regime=market_regime_label)
    decision = apply_policy(decision, policy)

    # 6. Stamp market_regime AFTER apply_policy so it cannot be silently
    #    dropped by overlay code. apply_policy never reads/writes this field.
    decision["market_regime"] = market_regime

    # 7. Universal hard skip ladder (LOW > score=0 > balanced) — UNCHANGED.
    #    market_regime intentionally has NO power here.
    skip, skip_reason = should_skip(
        regime=decision.get("regime"),
        score=decision.get("strategy_score"),
        quality=decision.get("quality"),
    )
    if skip:
        decision["allocation"] = 0.0
        decision["should_trade"] = False
        decision["skip_reason"] = skip_reason
        decision["reason"] = f"SKIP: {skip_reason}"
    else:
        decision["skip_reason"] = None

    # 8. Transparency
    decision["analysis_snapshot"] = {
        "agreement_score": (analysis.get("agreement") or {}).get("score") if analysis else None,
        "agreement_components": (analysis.get("agreement") or {}).get("components") if analysis else None,
        "agreement_guards": (analysis.get("agreement") or {}).get("guards") if analysis else None,
        "validation": (analysis or {}).get("validation"),
    }
    decision["health_snapshot"] = {
        "status_raw": health.get("status"),
        "services": health.get("services"),
    }

    return decision, (analysis or {}), policy
