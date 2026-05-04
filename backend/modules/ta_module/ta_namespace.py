"""
ta_namespace.py — Phase A.1 alias layer for TA module canonical API.

Goal
----
Establish a clean module boundary by exposing every TA-related backend route
under a single canonical prefix `/api/ta/*` while keeping legacy routes
working bit-for-bit.

Strategy
--------
We do NOT duplicate handlers, we do NOT touch existing routers, we do NOT
change response shapes. Instead, we install a tiny ASGI-level path-rewriting
middleware that transparently maps incoming `/api/ta/<sub>/...` requests to
the existing canonical paths BEFORE FastAPI routing dispatches them.

Result: one handler, two valid URLs, byte-identical responses.

Mapping (Phase A.1)
-------------------
    /api/ta/runtime/trace/*       → /api/trace/*           (special-case: trace lives at top-level)
    /api/ta/runtime/decisions/*   → /api/runtime/decisions/* (falls out of runtime rule)
    /api/ta/runtime/*             → /api/runtime/*
    /api/ta/analytics/*           → /api/analytics/*
    /api/ta/learning/*            → /api/learning/*
    /api/ta/decisions/*           → /api/decisions/*       (Phase A.1.1 — operator note)

Order matters — most specific rule first.

What we explicitly DO NOT touch
-------------------------------
    /api/ta/research               (existing — TA research engine)
    /api/ta/setup, /api/ta/setup/v2 (existing — TA setup pipeline)
    /api/ta/ideas/*                (existing — TA ideas)
    /api/ta/debug                  (existing)
    /api/ta/indicators/*           (existing)
    /api/ta/confluence             (existing)
    /api/ta-engine/*               (existing — TA engine internals)
    /api/ta-prediction-intelligence/*  (existing — Prediction Intelligence)

These are already canonical and remain canonical. The alias only intercepts
prefixes listed in `TA_ALIAS_RULES`.

Phase A.2+ (NOT in this commit)
-------------------------------
    * service-layer client (services/taService.js)
    * front-end migration to /api/ta/*
    * ta_module sub-routers (analysis, prediction, decision, execution,
      analytics, admin) re-mounted under /api/ta with their own routers
"""

from __future__ import annotations

from typing import Iterable, Tuple
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.types import ASGIApp


# Order-sensitive: the first rule whose `old` prefix matches wins.
# Most-specific rules MUST come first.
TA_ALIAS_RULES: Tuple[Tuple[str, str], ...] = (
    # /api/ta/runtime/trace/...  -> /api/trace/...
    ("/api/ta/runtime/trace/", "/api/trace/"),
    ("/api/ta/runtime/trace",  "/api/trace"),

    # /api/ta/runtime/...        -> /api/runtime/...
    # (this naturally covers /api/ta/runtime/decisions/...)
    ("/api/ta/runtime/", "/api/runtime/"),
    ("/api/ta/runtime",  "/api/runtime"),

    # /api/ta/analytics/...      -> /api/analytics/...
    ("/api/ta/analytics/", "/api/analytics/"),
    ("/api/ta/analytics",  "/api/analytics"),

    # /api/ta/learning/...       -> /api/learning/...
    ("/api/ta/learning/", "/api/learning/"),
    ("/api/ta/learning",  "/api/learning"),

    # /api/ta/decisions/...      -> /api/decisions/...
    # Phase A.1.1 — extends namespace to cover operator-note endpoint
    # (POST /api/decisions/{decision_id}/note). Currently /api/decisions/*
    # contains exactly ONE handler — the operator note. No other routes
    # are accidentally exposed under /api/ta/decisions/*.
    ("/api/ta/decisions/", "/api/decisions/"),
    ("/api/ta/decisions",  "/api/decisions"),
)


def rewrite_ta_path(path: str, rules: Iterable[Tuple[str, str]] = TA_ALIAS_RULES) -> str:
    """
    Apply the FIRST matching alias rule to *path*.

    Returns the original path unchanged if no rule applies.
    Pure function — easy to unit-test.

    Examples
    --------
    >>> rewrite_ta_path("/api/ta/runtime/trace/latest")
    '/api/trace/latest'
    >>> rewrite_ta_path("/api/ta/runtime/decisions/pending")
    '/api/runtime/decisions/pending'
    >>> rewrite_ta_path("/api/ta/analytics/decision-quality")
    '/api/analytics/decision-quality'
    >>> rewrite_ta_path("/api/ta/learning/training-runs")
    '/api/learning/training-runs'
    >>> rewrite_ta_path("/api/ta/research")           # untouched
    '/api/ta/research'
    >>> rewrite_ta_path("/api/runtime/state")         # legacy untouched
    '/api/runtime/state'
    """
    for old, new in rules:
        if path == old or path.startswith(old + "/") or path.startswith(old):
            # Two cases:
            #   1) exact match  → return new
            #   2) prefix match → swap prefix
            if path == old:
                return new
            if path.startswith(old):
                return new + path[len(old):]
    return path


class TANamespaceAliasMiddleware(BaseHTTPMiddleware):
    """
    ASGI middleware that rewrites `/api/ta/<sub>/...` to its legacy canonical
    path BEFORE FastAPI routes the request.

    The middleware is intentionally low-level: it mutates request.scope so the
    downstream handler sees the legacy path and answers exactly as it always
    has. The wire URL the client sent (`/api/ta/...`) is left untouched in any
    response — only routing dispatch is affected.
    """

    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)

    async def dispatch(self, request: Request, call_next):
        # Idempotency guard — if the scope has already been rewritten once
        # (e.g. by a future outer middleware chain), skip to avoid
        # double-rewrites like `/api/ta/ta/runtime/...`.
        if request.scope.get("_ta_namespace_rewritten"):
            return await call_next(request)

        path = request.scope.get("path", "")
        if path.startswith("/api/ta/"):
            # Additional defensive check — catches pathological inputs like
            # `/api/ta/ta/runtime/...` that could arise if a caller
            # accidentally double-prefixes.
            if path.startswith("/api/ta/ta/"):
                return await call_next(request)

            new_path = rewrite_ta_path(path)
            if new_path != path:
                request.scope["path"] = new_path
                request.scope["raw_path"] = new_path.encode("utf-8")
                request.scope["_ta_namespace_rewritten"] = True
        return await call_next(request)


def install_ta_namespace_alias(app) -> None:
    """
    Mount the TA namespace alias middleware on a FastAPI app.

    Idempotent — safe to call once at startup.
    """
    app.add_middleware(TANamespaceAliasMiddleware)
