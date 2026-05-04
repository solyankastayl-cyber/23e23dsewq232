"""
Stage A — Branches Health Aggregator.

Exposes:
    GET /api/admin/branches/health   → per-branch alive/dead/freshness/last_payload
    GET /api/admin/branches/summary  → compact one-shot summary (Pass/Fail per branch)

It calls the existing /health (or fallback /summary) endpoint of each
restored branch by importing its handler directly (no HTTP self-loop),
so it is safe to call even on cold start.

NO writes. NO execution. NO aggregator participation.
"""

from __future__ import annotations

import asyncio
import inspect
import time
from datetime import datetime, timezone
from typing import Any, Awaitable, Callable, Dict, List, Optional

from fastapi import APIRouter, Query

router = APIRouter(prefix="/api/admin/branches", tags=["stage-a-visibility"])


# ---------------------------------------------------------------------------
# Branch registry
# ---------------------------------------------------------------------------
# Each branch is described by:
#   id            — short unique id (machine-readable)
#   label         — human label
#   prefix        — public HTTP prefix
#   loader        — callable that returns ([health_callable, summary_callable])
#                   each callable can be sync or async; takes no args.
# A branch is considered "alive" if at least one of these calls succeeds
# and returns a non-empty payload. We never raise — we only report.
# ---------------------------------------------------------------------------

def _safe(fn_loader: Callable[[], Any], symbol: Optional[str] = None) -> Dict[str, Any]:
    """Invoke a route handler safely. Returns {ok, latency_ms, payload, error}."""
    started = time.perf_counter()
    try:
        callable_ = fn_loader()
        if callable_ is None:
            return {"ok": False, "latency_ms": 0, "payload": None, "error": "handler-not-found"}
        # Pass symbol if the handler accepts one
        sig_params: List[str] = []
        try:
            sig_params = list(inspect.signature(callable_).parameters.keys())
        except (TypeError, ValueError):
            sig_params = []
        kwargs: Dict[str, Any] = {}
        if symbol is not None:
            for cand in ("symbol", "asset"):
                if cand in sig_params:
                    kwargs[cand] = symbol
                    break
        # Required-but-no-default args: try to fill with sane defaults
        try:
            sig = inspect.signature(callable_)
            for name, p in sig.parameters.items():
                if p.default is inspect._empty and name not in kwargs and name != "self":
                    if name in ("symbols",):
                        kwargs[name] = "BTCUSDT"
                    elif name in ("timeframe", "tf"):
                        kwargs[name] = "1h"
        except (TypeError, ValueError):
            pass
        result = callable_(**kwargs) if kwargs else callable_()
        if asyncio.iscoroutine(result):
            result = asyncio.get_event_loop().run_until_complete(result)
        latency_ms = round((time.perf_counter() - started) * 1000, 1)
        ok = bool(result)
        return {"ok": ok, "latency_ms": latency_ms, "payload": result, "error": None}
    except Exception as e:  # pragma: no cover — diagnostic surface
        latency_ms = round((time.perf_counter() - started) * 1000, 1)
        return {
            "ok": False,
            "latency_ms": latency_ms,
            "payload": None,
            "error": f"{type(e).__name__}: {e}",
        }


async def _safe_async(fn_loader: Callable[[], Any], symbol: Optional[str] = None) -> Dict[str, Any]:
    """Async variant — preferred path."""
    started = time.perf_counter()
    try:
        callable_ = fn_loader()
        if callable_ is None:
            return {"ok": False, "latency_ms": 0, "payload": None, "error": "handler-not-found"}
        sig_params: List[str] = []
        try:
            sig_params = list(inspect.signature(callable_).parameters.keys())
        except (TypeError, ValueError):
            sig_params = []
        kwargs: Dict[str, Any] = {}
        if symbol is not None:
            for cand in ("symbol", "asset"):
                if cand in sig_params:
                    kwargs[cand] = symbol
                    break
        try:
            sig = inspect.signature(callable_)
            for name, p in sig.parameters.items():
                if p.default is inspect._empty and name not in kwargs and name != "self":
                    if name in ("symbols",):
                        kwargs[name] = "BTCUSDT"
                    elif name in ("timeframe", "tf"):
                        kwargs[name] = "1h"
        except (TypeError, ValueError):
            pass
        result = callable_(**kwargs) if kwargs else callable_()
        if asyncio.iscoroutine(result):
            result = await result
        latency_ms = round((time.perf_counter() - started) * 1000, 1)
        ok = bool(result)
        return {"ok": ok, "latency_ms": latency_ms, "payload": result, "error": None}
    except Exception as e:
        latency_ms = round((time.perf_counter() - started) * 1000, 1)
        return {
            "ok": False,
            "latency_ms": latency_ms,
            "payload": None,
            "error": f"{type(e).__name__}: {e}",
        }


# ---------------------------------------------------------------------------
# Branch loaders — each returns (health_handler, summary_handler) lazily.
# Lazy import so a failure in one branch does not break the aggregator.
# ---------------------------------------------------------------------------

def _exchange_intel_health() -> Optional[Callable[..., Any]]:
    try:
        from modules.exchange_intelligence import exchange_intel_routes as m
        # No dedicated /health on this branch — engines/status is the closest.
        # The handler name in routes is the function decorated with /engines/status.
        # Attribute name maps to 'engines_status' or whatever the function defines.
        for name in ("engines_status", "get_engines_status", "engine_status"):
            fn = getattr(m, name, None)
            if fn is not None:
                return fn
        # Fallback: introspect router
        try:
            for r in m.router.routes:
                if r.path.endswith("/engines/status"):
                    return r.endpoint
        except Exception:
            pass
        return None
    except Exception:
        return None


def _exchange_intel_summary() -> Optional[Callable[..., Any]]:
    try:
        from modules.exchange_intelligence import exchange_intel_routes as m
        return getattr(m, "get_exchange_context", None) or getattr(m, "get_batch_context", None)
    except Exception:
        return None


def _asset_fractal_health() -> Optional[Callable[..., Any]]:
    try:
        from modules.fractal_intelligence import asset_fractal_routes as m
        return getattr(m, "get_asset_fractal_health", None)
    except Exception:
        return None


def _asset_fractal_summary() -> Optional[Callable[..., Any]]:
    try:
        from modules.fractal_intelligence import asset_fractal_routes as m
        return getattr(m, "get_summary", None)
    except Exception:
        return None


def _fractal_context_health() -> Optional[Callable[..., Any]]:
    try:
        from modules.fractal_intelligence import fractal_context_routes as m
        return getattr(m, "get_fractal_health", None) or getattr(m, "health", None)
    except Exception:
        return None


def _fractal_context_summary() -> Optional[Callable[..., Any]]:
    try:
        from modules.fractal_intelligence import fractal_context_routes as m
        return getattr(m, "get_fractal_summary", None) or getattr(m, "summary", None)
    except Exception:
        return None


def _macro_fractal_health() -> Optional[Callable[..., Any]]:
    try:
        from modules.macro_fractal_brain import macro_fractal_routes as m
        return getattr(m, "health", None) or getattr(m, "get_health", None)
    except Exception:
        return None


def _macro_fractal_summary() -> Optional[Callable[..., Any]]:
    try:
        from modules.macro_fractal_brain import macro_fractal_routes as m
        return getattr(m, "summary", None) or getattr(m, "get_summary", None)
    except Exception:
        return None


def _cross_asset_health() -> Optional[Callable[..., Any]]:
    try:
        from modules.cross_asset_intelligence import cross_asset_routes as m
        return getattr(m, "health", None) or getattr(m, "get_health", None)
    except Exception:
        return None


def _cross_asset_summary() -> Optional[Callable[..., Any]]:
    try:
        from modules.cross_asset_intelligence import cross_asset_routes as m
        return getattr(m, "summary", None) or getattr(m, "get_summary", None)
    except Exception:
        return None


# Also include the LIVE branch (fractal_market_intelligence) and TA Engine
# so the visibility panel covers all 3 branches the architect mentioned.

def _fractal_market_health() -> Optional[Callable[..., Any]]:
    # No /health endpoint on this branch. Skip — summary is the alive proxy.
    return None


def _fractal_market_summary() -> Optional[Callable[..., Any]]:
    try:
        from modules.fractal_market_intelligence import fractal_routes as m
        return getattr(m, "get_fractal_summary", None)
    except Exception:
        return None


def _ta_engine_health() -> Optional[Callable[..., Any]]:
    try:
        from modules.ta_engine import ta_routes as m
        return getattr(m, "get_ta_status", None)
    except Exception:
        return None


def _ta_engine_summary() -> Optional[Callable[..., Any]]:
    try:
        from modules.ta_engine import ta_routes as m
        return getattr(m, "get_indicator_registry", None) or getattr(m, "get_pattern_registry", None)
    except Exception:
        return None


def _ta_pi_health() -> Optional[Callable[..., Any]]:
    try:
        from modules.ta_prediction_intelligence import ta_prediction_routes as m
        return getattr(m, "health", None)
    except Exception:
        return None


def _ta_pi_summary() -> Optional[Callable[..., Any]]:
    try:
        from modules.ta_prediction_intelligence import ta_prediction_routes as m
        return getattr(m, "outcome_worker_status", None) or getattr(m, "get_calibration", None)
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------
BRANCHES: List[Dict[str, Any]] = [
    # --- Stage A NEW restored ---
    {
        "id": "exchange_intelligence",
        "label": "Exchange Intelligence (funding/OI/liq/flow/volume)",
        "prefix": "/api/exchange-intelligence",
        "category": "stage_a_restored",
        "health_loader": _exchange_intel_health,
        "summary_loader": _exchange_intel_summary,
    },
    {
        "id": "fractal_assets",
        "label": "Fractal — Asset (BTC/SPX/DXY)",
        "prefix": "/api/v1/fractal-assets",
        "category": "stage_a_restored",
        "health_loader": _asset_fractal_health,
        "summary_loader": _asset_fractal_summary,
    },
    {
        "id": "fractal_intelligence",
        "label": "Fractal — Context",
        "prefix": "/api/v1/fractal-intelligence",
        "category": "stage_a_restored",
        "health_loader": _fractal_context_health,
        "summary_loader": _fractal_context_summary,
    },
    {
        "id": "macro_fractal",
        "label": "Macro-Fractal Brain",
        "prefix": "/api/v1/macro-fractal",
        "category": "stage_a_restored",
        "health_loader": _macro_fractal_health,
        "summary_loader": _macro_fractal_summary,
    },
    {
        "id": "cross_asset",
        "label": "Cross-Asset Intelligence",
        "prefix": "/api/v1/cross-asset",
        "category": "stage_a_restored",
        "health_loader": _cross_asset_health,
        "summary_loader": _cross_asset_summary,
    },
    # --- Already live (for completeness on the panel) ---
    {
        "id": "fractal_market",
        "label": "Fractal Market (live)",
        "prefix": "/api/fractal",
        "category": "live",
        "health_loader": _fractal_market_health,
        "summary_loader": _fractal_market_summary,
    },
    {
        "id": "ta_engine",
        "label": "TA Engine (live)",
        "prefix": "/api/ta",
        "category": "live",
        "health_loader": _ta_engine_health,
        "summary_loader": _ta_engine_summary,
    },
    {
        "id": "ta_prediction_intelligence",
        "label": "TA Prediction Intelligence (live)",
        "prefix": "/api/ta-prediction-intelligence",
        "category": "live",
        "health_loader": _ta_pi_health,
        "summary_loader": _ta_pi_summary,
    },
]


# ---------------------------------------------------------------------------
# Cache (60s TTL) so admin UI polling does not hammer downstream engines.
# ---------------------------------------------------------------------------
_CACHE: Dict[str, Any] = {"ts": 0.0, "data": None, "symbol": None}
_CACHE_TTL_S = 60


async def _probe_branch(branch: Dict[str, Any], symbol: Optional[str]) -> Dict[str, Any]:
    """Probe one branch; non-throwing."""
    h_loader = branch.get("health_loader")
    s_loader = branch.get("summary_loader")

    health = await _safe_async(h_loader, symbol=None) if h_loader else {"ok": False, "error": "no-health-loader"}
    summary = await _safe_async(s_loader, symbol=symbol) if s_loader else {"ok": False, "error": "no-summary-loader"}

    alive = bool(health.get("ok") or summary.get("ok"))
    last_payload: Any = None
    for cand in (health.get("payload"), summary.get("payload")):
        if cand:
            last_payload = cand
            break

    # Try to extract freshness if payload contains a timestamp/computed_at field
    freshness_iso: Optional[str] = None
    age_seconds: Optional[int] = None
    if isinstance(last_payload, dict):
        for k in ("computed_at", "timestamp", "as_of", "updated_at", "ts"):
            v = last_payload.get(k)
            if v:
                freshness_iso = str(v)
                break

    return {
        "id": branch["id"],
        "label": branch["label"],
        "prefix": branch["prefix"],
        "category": branch["category"],
        "alive": alive,
        "health": {
            "ok": health.get("ok"),
            "latency_ms": health.get("latency_ms"),
            "error": health.get("error"),
        },
        "summary": {
            "ok": summary.get("ok"),
            "latency_ms": summary.get("latency_ms"),
            "error": summary.get("error"),
        },
        "freshness_iso": freshness_iso,
        "age_seconds": age_seconds,
        "last_payload": last_payload,
    }


# ---------------------------------------------------------------------------
# Public endpoints
# ---------------------------------------------------------------------------

@router.get("/health")
async def branches_health(
    symbol: str = Query("BTCUSDT", description="Probe symbol"),
    refresh: bool = Query(False, description="Force cache bypass"),
) -> Dict[str, Any]:
    """
    Aggregated health snapshot for all restored branches.

    Read-only: it never writes to Mongo, never invokes execution, never
    affects the prediction aggregator. Cached for 60s by symbol.
    """
    now = time.time()
    if (
        not refresh
        and _CACHE["data"] is not None
        and _CACHE["symbol"] == symbol
        and (now - _CACHE["ts"]) < _CACHE_TTL_S
    ):
        return _CACHE["data"]

    results: List[Dict[str, Any]] = []
    for branch in BRANCHES:
        res = await _probe_branch(branch, symbol=symbol)
        results.append(res)

    alive_n = sum(1 for r in results if r["alive"])
    total_n = len(results)
    snapshot = {
        "ok": True,
        "stage": "A",
        "purpose": "READ-ONLY visibility — no execution, no aggregator participation",
        "computed_at": datetime.now(timezone.utc).isoformat(),
        "symbol": symbol,
        "branches_total": total_n,
        "branches_alive": alive_n,
        "branches_dead": total_n - alive_n,
        "branches": results,
    }
    _CACHE["ts"] = now
    _CACHE["data"] = snapshot
    _CACHE["symbol"] = symbol
    return snapshot


@router.get("/summary")
async def branches_summary(
    symbol: str = Query("BTCUSDT", description="Probe symbol"),
) -> Dict[str, Any]:
    """
    Minimal Pass/Fail summary: one row per branch, no payloads.
    Suitable for top-line ops dashboards.
    """
    full = await branches_health(symbol=symbol)
    rows: List[Dict[str, Any]] = []
    for b in full["branches"]:
        rows.append(
            {
                "id": b["id"],
                "label": b["label"],
                "prefix": b["prefix"],
                "category": b["category"],
                "alive": b["alive"],
                "health_ok": b["health"]["ok"],
                "summary_ok": b["summary"]["ok"],
                "latency_ms": (b["health"]["latency_ms"] or 0) + (b["summary"]["latency_ms"] or 0),
                "error": b["health"]["error"] or b["summary"]["error"],
                "freshness_iso": b["freshness_iso"],
            }
        )
    return {
        "ok": True,
        "stage": "A",
        "computed_at": full["computed_at"],
        "symbol": symbol,
        "branches_total": full["branches_total"],
        "branches_alive": full["branches_alive"],
        "branches_dead": full["branches_dead"],
        "rows": rows,
    }
