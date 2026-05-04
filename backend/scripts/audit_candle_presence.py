#!/usr/bin/env python3
"""
Phase R.2.2 — audit_candle_presence.py  (forensic, read-only)
=============================================================

Goal:
  For a set of (boundary_ts, symbol, timeframe) triples — verify whether
  the boundary candle is actually available across the freshness chain:

    1. Provider (live Binance US klines HTTP fetch, bypasses cache)
    2. Provider cache (modules.scanner.market_data.binance_provider._cache)
    3. Consumer's selected_closed_ts semantics (candles[-2].time)

Produces a grep-friendly table, one row per (symbol, tf, boundary):

  symbol    tf   boundary_utc   in_provider  in_cache  cache_age_sec  selected_closed_ts  verdict

Verdicts:
  OK                        — provider has boundary candle AND consumer would select it
  PROVIDER_MISSING          — provider doesn't see boundary candle at all
  CACHE_STALE_PROVIDER_OK   — provider has it live, but cache copy doesn't (TTL problem)
  CONSUMER_WRONG_SELECTION  — provider has it, cache has it, but consumer's candles[-2]
                              would NOT return the boundary candle
  AMBIGUOUS                 — unexpected shape; see raw for debugging

Usage:
    python3 /app/backend/scripts/audit_candle_presence.py                 # default universe+boundaries
    python3 /app/backend/scripts/audit_candle_presence.py --boundaries 12:00,13:00,14:00
    python3 /app/backend/scripts/audit_candle_presence.py --json

No changes to detectors/generators/router/validator/provider/cache/state.
Pure read-only forensic.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Tuple

# Repo boot
sys.path.insert(0, "/app/backend")

try:
    from dotenv import load_dotenv
    load_dotenv("/app/backend/.env")
except Exception:
    pass

# Lazy imports — don't want side effects on import
from modules.scanner.market_data import binance_provider as _bp
from modules.scanner.market_data.binance_provider import (
    BinanceProvider,
    get_market_data_provider,
    _cache as _PROVIDER_CACHE,
    _CACHE_TTL as _PROVIDER_CACHE_TTL,
    _normalize_symbol,
)

# -----------------------------------------------------------------------
# Defaults: same universe as discovery_matrix_live + phase_c truth lane
# -----------------------------------------------------------------------
_DEFAULT_SYMBOLS = [
    "BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT", "DOGEUSDT",
    "ADAUSDT", "AVAXUSDT", "LINKUSDT", "TRXUSDT", "DOTUSDT", "MATICUSDT",
    "LTCUSDT", "UNIUSDT", "ATOMUSDT", "ETCUSDT", "XLMUSDT", "FILUSDT",
    "APTUSDT", "NEARUSDT", "ICPUSDT", "INJUSDT", "SUIUSDT", "TIAUSDT",
    "ARBUSDT", "OPUSDT", "SEIUSDT", "AAVEUSDT", "HBARUSDT", "ALGOUSDT",
]
_DEFAULT_TFS = ["1H", "4H"]
_TF_SECONDS = {"1H": 3600, "4H": 14400, "1D": 86400}


# -----------------------------------------------------------------------
# Boundary resolution
# -----------------------------------------------------------------------
def _parse_boundaries(arg: Optional[str]) -> List[int]:
    """
    Parse boundary argument.

    If arg is None: produce 4 nearest past 1H boundaries (for 1H) and
    the most recent 4H boundary. We'll actually let the caller evaluate
    both TFs against the same timestamps; mismatched TF/boundary pairs
    are simply reported with verdict=N/A when boundary isn't aligned.

    Accepted format:
        --boundaries 12:00,13:00,14:00    (today UTC)
        --boundaries 2026-04-23T12:00Z    (explicit)
    """
    now = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
    if arg is None:
        # Default: last 4 hourly boundaries (covers 1H and 4H alignment)
        bounds = [now - timedelta(hours=i) for i in range(1, 5)]
        return [int(b.timestamp()) for b in bounds]
    out: List[int] = []
    for part in arg.split(","):
        p = part.strip()
        if not p:
            continue
        if "T" in p:
            try:
                dt = datetime.fromisoformat(p.replace("Z", "+00:00"))
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                out.append(int(dt.timestamp()))
            except Exception as e:
                print(f"[WARN] cannot parse boundary {p}: {e}")
        else:
            # HH:MM today UTC
            try:
                hh, mm = p.split(":")
                today = datetime.now(timezone.utc).replace(
                    hour=int(hh), minute=int(mm),
                    second=0, microsecond=0,
                )
                out.append(int(today.timestamp()))
            except Exception as e:
                print(f"[WARN] cannot parse boundary {p}: {e}")
    return out


def _fmt_ts(ts: Optional[int]) -> str:
    if ts is None:
        return "-"
    try:
        return datetime.fromtimestamp(int(ts), tz=timezone.utc).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        )
    except Exception:
        return str(ts)


# -----------------------------------------------------------------------
# Live provider fetch (bypasses cache — constructs fresh instance and
# uses internal _fetch directly, which does NOT touch the singleton cache)
# -----------------------------------------------------------------------
def _live_fetch(
    provider: BinanceProvider,
    symbol: str,
    timeframe: str,
    limit: int = 200,
) -> List[Dict[str, Any]]:
    """
    Direct HTTP fetch — bypasses cache entirely.

    Implemented by calling _fetch() (low-level) with the mapped interval,
    not get_candles() (which consults cache first).
    """
    from modules.scanner.market_data.binance_provider import _TF_MAP
    interval = _TF_MAP.get(timeframe.upper())
    if not interval:
        return []
    # _rate_limit is fine — it only throttles us, no cache interaction
    provider._rate_limit()
    return provider._fetch(_normalize_symbol(symbol), interval, limit)


def _peek_cache(symbol: str, timeframe: str) -> Tuple[bool, Optional[int], List[Dict[str, Any]]]:
    """
    Peek cache without mutating it.

    Returns: (hit, age_sec, candles_if_present)
    """
    key = f"{_normalize_symbol(symbol)}:{timeframe.upper()}"
    entry = _PROVIDER_CACHE.get(key)
    if not entry or not isinstance(entry, tuple) or len(entry) < 2:
        return False, None, []
    ts, data = entry
    age = int(time.time() - ts)
    # Honor TTL semantics — if age > TTL the cache layer will treat this
    # as a miss on next call, so surface that as "not hit".
    if age >= _PROVIDER_CACHE_TTL:
        return False, age, data if isinstance(data, list) else []
    return True, age, data if isinstance(data, list) else []


# -----------------------------------------------------------------------
# Presence check for a single (symbol, tf, boundary)
# -----------------------------------------------------------------------
def _candle_at(candles: List[Dict[str, Any]], boundary_ts: int) -> Optional[Dict[str, Any]]:
    """Find the candle whose open_time (= candle['time']) == boundary_ts."""
    for c in candles:
        t = c.get("time")
        if t is None:
            continue
        try:
            if int(t) == int(boundary_ts):
                return c
        except Exception:
            continue
    return None


def _selected_closed_ts_of(candles: List[Dict[str, Any]]) -> Optional[int]:
    """
    Mirror consumer's selection rule:
        Phase C.3d: latest = candles[-2] if len(candles) >= 2 else candles[-1]
    """
    if not candles:
        return None
    if len(candles) >= 2:
        c = candles[-2]
    else:
        c = candles[-1]
    if isinstance(c, dict):
        t = c.get("time")
        try:
            return int(t) if t is not None else None
        except Exception:
            return None
    return None


def _verdict(
    provider_has: bool,
    cache_has: bool,
    cache_hit_fresh: bool,
    selected_ts: Optional[int],
    boundary_ts: int,
    tf: str,
) -> str:
    """
    Decide which layer is responsible.

    Note: a boundary_ts aligned to 1H may not be aligned to 4H. In that case
    the 4H candle at boundary_ts simply doesn't exist — that's not a failure.
    We mark those as N/A_NOT_ALIGNED.
    """
    tf_sec = _TF_SECONDS.get(tf.upper(), 0)
    if tf_sec > 0 and (boundary_ts % tf_sec) != 0:
        return "N/A_NOT_ALIGNED"

    if not provider_has:
        return "PROVIDER_MISSING"
    # Provider has it.
    if cache_hit_fresh:
        if cache_has:
            # Cache is fresh AND has boundary candle — good. Check consumer.
            if selected_ts is None:
                return "AMBIGUOUS"
            if selected_ts == boundary_ts:
                return "OK"
            if selected_ts > boundary_ts:
                # Consumer would select a newer candle — that's fine for
                # THIS boundary (which is in the past). This means the
                # engine should already have advanced past this boundary.
                return "OK_ADVANCED"
            # selected_ts < boundary_ts — consumer lagging behind
            return "CONSUMER_WRONG_SELECTION"
        # Cache fresh but boundary candle missing from cached payload.
        return "CACHE_STALE_PROVIDER_OK"
    # Cache is not fresh (expired / absent) — next call would re-fetch.
    # This is actually healthy: fresh fetch will get provider data.
    # So report based on provider only.
    if selected_ts is None:
        return "AMBIGUOUS"
    return "OK_CACHE_EXPIRED"


# -----------------------------------------------------------------------
# Main audit
# -----------------------------------------------------------------------
def audit(
    symbols: List[str],
    timeframes: List[str],
    boundaries: List[int],
    as_json: bool,
) -> int:
    provider = get_market_data_provider()
    rows: List[Dict[str, Any]] = []

    now_utc = datetime.now(timezone.utc)
    print("=" * 110)
    print(
        f"audit_candle_presence.py — NOW={now_utc.strftime('%Y-%m-%dT%H:%M:%SZ')} "
        f"| symbols={len(symbols)} | tfs={timeframes} | boundaries={[_fmt_ts(b) for b in boundaries]}"
    )
    print(f"provider_cache_ttl={_PROVIDER_CACHE_TTL}s  cache_entries={len(_PROVIDER_CACHE)}")
    print("=" * 110)

    # Snapshot current cache state (do NOT mutate)
    cache_snapshot: Dict[str, Tuple[bool, Optional[int], List[Dict[str, Any]]]] = {}
    for sym in symbols:
        for tf in timeframes:
            cache_snapshot[(sym, tf)] = _peek_cache(sym, tf)

    # Live-fetch each (symbol, tf) ONCE — cache-bypass. This costs one HTTP
    # per pair; universe of 30 × 2 = 60 calls × 100ms rate limit = ~6s.
    live_fetched: Dict[Tuple[str, str], List[Dict[str, Any]]] = {}
    for sym in symbols:
        for tf in timeframes:
            try:
                live = _live_fetch(provider, sym, tf, limit=200)
            except Exception as e:
                live = []
                print(f"[WARN] live fetch failed for {sym}:{tf}: {e}")
            live_fetched[(sym, tf)] = live

    # Header
    hdr = f"{'symbol':<10} {'tf':<3} {'boundary_utc':<21} {'in_prov':<8} {'in_cache':<9} {'cache_age':<10} {'cache_ttl_ok':<13} {'selected_closed_ts':<21} {'verdict':<28}"
    print(hdr)
    print("-" * len(hdr))

    for sym in symbols:
        for tf in timeframes:
            live = live_fetched.get((sym, tf), [])
            cache_hit_fresh, cache_age, cache_candles = cache_snapshot.get((sym, tf), (False, None, []))
            selected_ts = _selected_closed_ts_of(live)
            for b_ts in boundaries:
                prov_candle = _candle_at(live, b_ts)
                cache_candle = _candle_at(cache_candles, b_ts)
                provider_has = prov_candle is not None
                cache_has = cache_candle is not None
                v = _verdict(
                    provider_has=provider_has,
                    cache_has=cache_has,
                    cache_hit_fresh=cache_hit_fresh,
                    selected_ts=selected_ts,
                    boundary_ts=b_ts,
                    tf=tf,
                )
                row = {
                    "symbol": sym,
                    "tf": tf,
                    "boundary_ts": b_ts,
                    "boundary_utc": _fmt_ts(b_ts),
                    "in_provider": provider_has,
                    "in_cache": cache_has,
                    "cache_age_sec": cache_age,
                    "cache_fresh_ttl": cache_hit_fresh,
                    "selected_closed_ts": selected_ts,
                    "selected_closed_utc": _fmt_ts(selected_ts),
                    "verdict": v,
                }
                rows.append(row)
                print(
                    f"{sym:<10} {tf:<3} {row['boundary_utc']:<21} "
                    f"{str(provider_has):<8} {str(cache_has):<9} "
                    f"{str(cache_age if cache_age is not None else '-'):<10} "
                    f"{str(cache_hit_fresh):<13} "
                    f"{row['selected_closed_utc']:<21} {v:<28}"
                )

    # Summary
    print("-" * len(hdr))
    summary: Dict[str, int] = {}
    for r in rows:
        summary[r["verdict"]] = summary.get(r["verdict"], 0) + 1
    print("VERDICT SUMMARY:")
    for v, n in sorted(summary.items(), key=lambda x: (-x[1], x[0])):
        print(f"  {v:<28} {n}")

    if as_json:
        print()
        print("JSON DUMP:")
        print(json.dumps({"rows": rows, "summary": summary, "now": now_utc.isoformat()}, indent=2))

    # Exit code: 0 if no "bad" verdicts, 1 otherwise.
    bad = {"PROVIDER_MISSING", "CACHE_STALE_PROVIDER_OK", "CONSUMER_WRONG_SELECTION", "AMBIGUOUS"}
    has_bad = any(r["verdict"] in bad for r in rows)
    return 1 if has_bad else 0


def main() -> int:
    p = argparse.ArgumentParser(description="Phase R.2.2 — Freshness chain audit")
    p.add_argument(
        "--symbols",
        default=",".join(_DEFAULT_SYMBOLS),
        help="Comma-separated symbols (default: discovery universe, 30 syms)",
    )
    p.add_argument(
        "--timeframes",
        default=",".join(_DEFAULT_TFS),
        help="Comma-separated timeframes (default: 1H,4H)",
    )
    p.add_argument(
        "--boundaries",
        default=None,
        help="Comma-separated boundary times HH:MM (today UTC) or ISO. Default: last 4 hourly boundaries.",
    )
    p.add_argument(
        "--json",
        action="store_true",
        help="Also dump rows as JSON at end",
    )
    args = p.parse_args()

    symbols = [s.strip().upper() for s in args.symbols.split(",") if s.strip()]
    timeframes = [t.strip().upper() for t in args.timeframes.split(",") if t.strip()]
    boundaries = _parse_boundaries(args.boundaries)
    if not boundaries:
        print("[ERROR] No boundaries resolved.")
        return 2

    return audit(symbols, timeframes, boundaries, as_json=args.json)


if __name__ == "__main__":
    sys.exit(main())
