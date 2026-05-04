"""
Stage B — Forensic #1: Exchange Intelligence alpha test.

Goal (architect directive):
    Prove or kill — does Exchange Intelligence carry predictive value
    above the baseline SimpleMA regime filter?

Method (pure READ-ONLY):
    1. Take closed trading_cases (realized_pnl_pct != null).
    2. Dedup by 10-minute windows → ONE trade per market moment.
    3. For each unique moment, fetch OKX public futures data at opened_at:
       - funding_rate (nearest 8h fixing)
       - long/short account ratio (5m bar)
       - OI change % (5m bar vs 15 min earlier)
       - candle volume_ratio (current 5m vs 20-bar avg)
       - taker buy/sell imbalance (5m bar)
    4. Compute per-feature diagnostics:
       - Spearman rank correlation vs realized_pnl_pct
       - Bucket test (tertiles → avg PnL%, WR per bucket)
       - Simple-rule test (sign / threshold based)
    5. Emit verdict per feature:
       - ALPHA:      |spearman| >= 0.30 AND top-bottom bucket spread >= 0.50% abs
       - RESERVE:    0.15 <= |spearman| < 0.30 OR monotonic buckets but small spread
       - NO_ALPHA:   |spearman| < 0.15

    Sample size is intentionally tiny (8–20). Any verdict is SUGGESTIVE,
    not proof. We explicitly document N and flag low-N warnings. Architect
    decides follow-up (connect to pipeline / reserve / discard).

Output:
    /tmp/forensic_stage_b_exchange.jsonl   (one row per joined trade)
    /tmp/forensic_stage_b_exchange.md      (human-readable report)

NO writes to Mongo. NO calls to execution / aggregator / decision pipeline.
NO code in trading modules touched.
"""
from __future__ import annotations

import json
import math
import os
import statistics
import sys
import time
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from pymongo import MongoClient
from bson import ObjectId

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.environ.get("DB_NAME", "trading_os")

DEDUP_WINDOW_S = 10 * 60     # one trade per 10-min window
MAX_SAMPLE = 20              # hard cap (architect directive: 8-20 unique moments)
MIN_SAMPLE = 8

# OKX data availability (measured empirically 2026-05-04):
#   - L/S ratio: last ~3 days on 5m
#   - funding:   30+ days
#   - candles:   30+ days
# We keep a short slack for safety.
OKX_LS_RATIO_MAX_AGE_S = 3 * 24 * 3600 - 30 * 60  # ~2d 23h30m

UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"
OKX = "https://www.okx.com"


def http_json(url: str, timeout: int = 10) -> Optional[Dict[str, Any]]:
    try:
        req = urllib.request.Request(
            url, headers={"User-Agent": UA, "Accept": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read())
    except Exception as e:
        print(f"  [http] {url[:90]}… → {type(e).__name__}: {e}", file=sys.stderr)
        return None


# ---------------------------------------------------------------------------
# 1. Trades from Mongo
# ---------------------------------------------------------------------------

def load_closed_trades() -> List[Dict[str, Any]]:
    cli = MongoClient(MONGO_URL, serverSelectionTimeoutMS=5000)
    col = cli[DB_NAME]["trading_cases"]
    docs = list(
        col.find(
            {"realized_pnl_pct": {"$ne": None}},
            {
                "_id": 0,
                "case_id": 1,
                "symbol": 1,
                "side": 1,
                "strategy": 1,
                "opened_at": 1,
                "closed_at": 1,
                "entry_price": 1,
                "exit_price": 1,
                "realized_pnl_pct": 1,
                "exit_rule": 1,
                "experiment_id": 1,
            },
        )
    )
    # Normalise timestamps to UTC ms int.
    out = []
    for d in docs:
        ts = d.get("opened_at")
        if isinstance(ts, datetime):
            ms = int(ts.replace(tzinfo=timezone.utc).timestamp() * 1000)
        elif isinstance(ts, str):
            try:
                ms = int(datetime.fromisoformat(ts.replace("Z", "+00:00")).timestamp() * 1000)
            except Exception:
                continue
        else:
            continue
        d["opened_at_ms"] = ms
        out.append(d)
    out.sort(key=lambda d: d["opened_at_ms"])
    return out


def dedup_by_window(trades: List[Dict[str, Any]], window_s: int) -> List[Dict[str, Any]]:
    """Keep the first trade per (symbol, window)."""
    seen: Dict[Tuple[str, int], Dict[str, Any]] = {}
    for t in trades:
        key = (t["symbol"], t["opened_at_ms"] // (window_s * 1000))
        if key not in seen:
            seen[key] = t
    return sorted(seen.values(), key=lambda d: d["opened_at_ms"])


# ---------------------------------------------------------------------------
# 2. OKX feature fetchers
# ---------------------------------------------------------------------------

SYMBOL_TO_OKX_INST = {"BTCUSDT": "BTC-USDT-SWAP", "ETHUSDT": "ETH-USDT-SWAP"}
SYMBOL_TO_OKX_CCY = {"BTCUSDT": "BTC", "ETHUSDT": "ETH"}


def fetch_funding_rate_at(symbol: str, ts_ms: int) -> Optional[float]:
    """Nearest realised 8h funding rate at or before ts_ms."""
    inst = SYMBOL_TO_OKX_INST.get(symbol)
    if not inst:
        return None
    url = f"{OKX}/api/v5/public/funding-rate-history?instId={inst}&after={ts_ms}&limit=3"
    d = http_json(url)
    if not d or not d.get("data"):
        return None
    # pick the one closest-yet-<=ts_ms
    best: Optional[Tuple[int, float]] = None
    for rec in d["data"]:
        ft = int(rec.get("fundingTime") or 0)
        if ft and ft <= ts_ms:
            try:
                rate = float(rec.get("realizedRate") or rec.get("fundingRate"))
            except (TypeError, ValueError):
                continue
            if best is None or ft > best[0]:
                best = (ft, rate)
    return best[1] if best else None


def fetch_ls_ratio_at(symbol: str, ts_ms: int) -> Optional[float]:
    """Long/short account ratio, 5m bar nearest to ts_ms.  None if out-of-window."""
    ccy = SYMBOL_TO_OKX_CCY.get(symbol)
    if not ccy:
        return None
    now = int(time.time() * 1000)
    if now - ts_ms > OKX_LS_RATIO_MAX_AGE_S * 1000:
        return None  # outside OKX rubik stats availability
    # begin = window start; OKX returns data newest-first starting at `begin`
    begin = ts_ms - 20 * 60 * 1000  # 20 min before
    url = (
        f"{OKX}/api/v5/rubik/stat/contracts/long-short-account-ratio"
        f"?ccy={ccy}&period=5m&begin={begin}&limit=10"
    )
    d = http_json(url)
    if not d or not d.get("data"):
        return None
    # rows: [ts, ratio]; pick the one <= ts_ms and closest
    best: Optional[Tuple[int, float]] = None
    for row in d["data"]:
        try:
            rts = int(row[0])
            ratio = float(row[1])
        except (TypeError, ValueError, IndexError):
            continue
        if rts <= ts_ms:
            if best is None or rts > best[0]:
                best = (rts, ratio)
    return best[1] if best else None


def fetch_oi_at(symbol: str, ts_ms: int) -> Optional[Tuple[float, float]]:
    """Returns (oi_at_ts, oi_change_pct_15m).  None if out-of-window."""
    ccy = SYMBOL_TO_OKX_CCY.get(symbol)
    if not ccy:
        return None
    now = int(time.time() * 1000)
    if now - ts_ms > OKX_LS_RATIO_MAX_AGE_S * 1000:
        return None
    begin = ts_ms - 30 * 60 * 1000
    url = (
        f"{OKX}/api/v5/rubik/stat/contracts/open-interest-volume"
        f"?ccy={ccy}&period=5m&begin={begin}&limit=20"
    )
    d = http_json(url)
    if not d or not d.get("data"):
        return None
    # rows: [ts, oi_usd, vol_usd]  newest-first
    rows: List[Tuple[int, float, float]] = []
    for row in d["data"]:
        try:
            rts = int(row[0])
            oi = float(row[1])
            vol = float(row[2])
            rows.append((rts, oi, vol))
        except (TypeError, ValueError, IndexError):
            continue
    if not rows:
        return None
    rows.sort()  # ascending
    # OI at ts
    at = next((r for r in reversed(rows) if r[0] <= ts_ms), None)
    at_15m = next((r for r in reversed(rows) if r[0] <= ts_ms - 15 * 60 * 1000), None)
    if not at or not at_15m or at_15m[1] == 0:
        return None
    oi_change_pct = (at[1] - at_15m[1]) / at_15m[1] * 100.0
    return (at[1], oi_change_pct)


def fetch_taker_flow_at(symbol: str, ts_ms: int) -> Optional[float]:
    """Returns taker buy / (buy+sell) ratio on 5m at ts_ms.  0..1."""
    ccy = SYMBOL_TO_OKX_CCY.get(symbol)
    if not ccy:
        return None
    now = int(time.time() * 1000)
    if now - ts_ms > OKX_LS_RATIO_MAX_AGE_S * 1000:
        return None
    begin = ts_ms - 20 * 60 * 1000
    url = (
        f"{OKX}/api/v5/rubik/stat/taker-volume"
        f"?ccy={ccy}&instType=CONTRACTS&period=5m&begin={begin}&limit=10"
    )
    d = http_json(url)
    if not d or not d.get("data"):
        return None
    rows = d["data"]
    # rows: [ts, sell_volume, buy_volume]
    best = None
    for row in rows:
        try:
            rts = int(row[0])
            sell_v = float(row[1])
            buy_v = float(row[2])
        except (TypeError, ValueError, IndexError):
            continue
        if rts <= ts_ms:
            if best is None or rts > best[0]:
                total = sell_v + buy_v
                ratio = buy_v / total if total > 0 else 0.5
                best = (rts, ratio)
    return best[1] if best else None


def fetch_candle_context_at(symbol: str, ts_ms: int) -> Optional[Dict[str, float]]:
    """5m candle at ts_ms + volume ratio vs last-20 avg."""
    inst = SYMBOL_TO_OKX_INST.get(symbol)
    if not inst:
        return None
    # `after` = get candles older than this ts
    after = ts_ms + 10 * 60 * 1000  # just after the anchor
    url = f"{OKX}/api/v5/market/history-candles?instId={inst}&bar=5m&after={after}&limit=30"
    d = http_json(url)
    if not d or not d.get("data"):
        return None
    rows = d["data"]  # newest first
    # pick candle closest to and <= ts_ms
    chosen = None
    for r in rows:
        try:
            rts = int(r[0])
        except (TypeError, ValueError):
            continue
        if rts <= ts_ms:
            chosen = r
            break
    if chosen is None:
        return None
    try:
        o, h, l, c = float(chosen[1]), float(chosen[2]), float(chosen[3]), float(chosen[4])
        v = float(chosen[5])
    except (TypeError, ValueError, IndexError):
        return None
    vols = []
    for r in rows[rows.index(chosen) + 1 : rows.index(chosen) + 21]:
        try:
            vols.append(float(r[5]))
        except (TypeError, ValueError, IndexError):
            continue
    avg_v = statistics.mean(vols) if vols else v
    vol_ratio = v / avg_v if avg_v > 0 else 1.0
    body = abs(c - o)
    rng = h - l if h > l else 1e-9
    body_frac = body / rng
    return {
        "candle_return_pct": (c - o) / o * 100.0,
        "candle_volume_ratio": vol_ratio,
        "candle_body_frac": body_frac,
        "candle_high_pct": (h - o) / o * 100.0,
        "candle_low_pct": (l - o) / o * 100.0,
    }


# ---------------------------------------------------------------------------
# 3. Statistical helpers
# ---------------------------------------------------------------------------

def spearman(x: List[float], y: List[float]) -> Optional[float]:
    if len(x) < 4 or len(x) != len(y):
        return None

    def rank(a: List[float]) -> List[float]:
        order = sorted(range(len(a)), key=lambda i: a[i])
        r = [0.0] * len(a)
        i = 0
        while i < len(a):
            j = i
            while j + 1 < len(a) and a[order[j + 1]] == a[order[i]]:
                j += 1
            avg = (i + j) / 2 + 1
            for k in range(i, j + 1):
                r[order[k]] = avg
            i = j + 1
        return r

    rx = rank(x)
    ry = rank(y)
    mx = statistics.mean(rx)
    my = statistics.mean(ry)
    num = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    den_x = math.sqrt(sum((a - mx) ** 2 for a in rx))
    den_y = math.sqrt(sum((b - my) ** 2 for b in ry))
    if den_x == 0 or den_y == 0:
        return None
    return round(num / (den_x * den_y), 4)


def tertile_split(values: List[float], pnls: List[float]) -> Dict[str, Dict[str, Any]]:
    if len(values) < 6:
        return {"_warn": "not-enough-data-for-tertiles"}
    paired = sorted(zip(values, pnls), key=lambda p: p[0])
    n = len(paired)
    low = paired[: n // 3]
    mid = paired[n // 3 : 2 * n // 3]
    high = paired[2 * n // 3 :]

    def stats(group):
        if not group:
            return {"n": 0}
        p = [g[1] for g in group]
        wins = sum(1 for v in p if v > 0)
        return {
            "n": len(group),
            "avg_pnl_pct": round(statistics.mean(p), 4),
            "median_pnl_pct": round(statistics.median(p), 4),
            "win_rate": round(wins / len(p), 3),
            "value_range": [round(group[0][0], 6), round(group[-1][0], 6)],
        }

    return {"low": stats(low), "mid": stats(mid), "high": stats(high)}


def rule_test(pred_fn, values: List[float], pnls: List[float], label: str) -> Dict[str, Any]:
    match = [p for v, p in zip(values, pnls) if pred_fn(v)]
    nomatch = [p for v, p in zip(values, pnls) if not pred_fn(v)]
    if not match:
        return {"rule": label, "n_match": 0, "n_nomatch": len(nomatch), "match_avg": None}
    return {
        "rule": label,
        "n_match": len(match),
        "n_nomatch": len(nomatch),
        "match_avg_pnl_pct": round(statistics.mean(match), 4),
        "nomatch_avg_pnl_pct": round(statistics.mean(nomatch), 4) if nomatch else None,
        "match_wr": round(sum(1 for p in match if p > 0) / len(match), 3),
        "spread_pct": round(
            statistics.mean(match) - (statistics.mean(nomatch) if nomatch else 0.0), 4
        ),
    }


def classify_verdict(spearman_val: Optional[float], buckets: Dict[str, Any]) -> Tuple[str, str]:
    if spearman_val is None:
        return ("INCONCLUSIVE", "spearman could not be computed (n<4)")
    s = abs(spearman_val)
    # Extract bucket stats safely.
    try:
        lo = buckets["low"]["avg_pnl_pct"]
        mi = buckets["mid"]["avg_pnl_pct"]
        hi = buckets["high"]["avg_pnl_pct"]
    except Exception:
        lo = mi = hi = None

    if lo is not None:
        # Spread: use max-min across three buckets (captures non-linear signals too).
        bucket_vals = [lo, mi, hi]
        spread = max(bucket_vals) - min(bucket_vals)
        monotonic_up = lo <= mi <= hi
        monotonic_dn = lo >= mi >= hi
        monotonic = monotonic_up or monotonic_dn
    else:
        spread = 0.0
        monotonic = False

    # Tier 1 — strong: monotonic & large ρ & large spread
    if s >= 0.30 and spread >= 0.50 and monotonic:
        return (
            "ALPHA",
            f"|ρ|={s:.2f} ≥ 0.30, spread={spread:.2f}% ≥ 0.50%, monotonic buckets",
        )
    # Tier 2 — non-linear alpha: strong ρ but buckets non-monotonic (needs rule test)
    if s >= 0.30 and spread >= 0.30:
        return (
            "ALPHA_NONLINEAR",
            f"|ρ|={s:.2f} ≥ 0.30, spread={spread:.2f}%, monotonic={monotonic} — inspect rule tests",
        )
    # Tier 3 — reserve: decent ρ or decent spread
    if s >= 0.15 and s < 0.30:
        return (
            "RESERVE",
            f"|ρ|={s:.2f} weak-suggestive, spread={spread:.2f}%, monotonic={monotonic}",
        )
    if monotonic and spread >= 0.30:
        return (
            "RESERVE",
            f"|ρ|={s:.2f}, monotonic buckets, spread={spread:.2f}% — directional but weak ρ",
        )
    return (
        "NO_ALPHA",
        f"|ρ|={s:.2f}, spread={spread:.2f}%, monotonic={monotonic} — no significant pattern",
    )


# ---------------------------------------------------------------------------
# 4. Main
# ---------------------------------------------------------------------------

def main() -> int:
    print("═" * 72)
    print(" STAGE B — Forensic #1: Exchange Intelligence (read-only)")
    print("═" * 72)

    trades_all = load_closed_trades()
    print(f"\n[load] closed trading_cases: {len(trades_all)}")
    if not trades_all:
        print("No closed trades → aborting.")
        return 1
    t0 = trades_all[0]["opened_at_ms"]
    t1 = trades_all[-1]["opened_at_ms"]
    print(
        f"       span {datetime.fromtimestamp(t0/1000, timezone.utc):%Y-%m-%d %H:%M} → "
        f"{datetime.fromtimestamp(t1/1000, timezone.utc):%Y-%m-%d %H:%M} UTC"
    )

    # Only keep trades within OKX rubik stats window (last ~3 days).
    now_ms = int(time.time() * 1000)
    window_start = now_ms - OKX_LS_RATIO_MAX_AGE_S * 1000
    candidates = [t for t in trades_all if t["opened_at_ms"] >= window_start]
    print(
        f"[window] after OKX-rubik cutoff ({datetime.fromtimestamp(window_start/1000, timezone.utc):%Y-%m-%d %H:%M} UTC): "
        f"{len(candidates)} / {len(trades_all)}"
    )

    deduped = dedup_by_window(candidates, DEDUP_WINDOW_S)
    print(f"[dedup] one per {DEDUP_WINDOW_S//60}-min window: {len(deduped)} unique moments")
    if len(deduped) < MIN_SAMPLE:
        print(f"⚠️  below MIN_SAMPLE={MIN_SAMPLE}. Proceeding anyway for directional look.")

    if len(deduped) > MAX_SAMPLE:
        # Keep most recent.
        deduped = deduped[-MAX_SAMPLE:]
        print(f"[cap] kept last {MAX_SAMPLE}")

    # Fetch features
    rows: List[Dict[str, Any]] = []
    print(f"\n[fetch] pulling OKX features for {len(deduped)} moments …")
    for idx, t in enumerate(deduped, 1):
        sym, ts_ms = t["symbol"], t["opened_at_ms"]
        funding = fetch_funding_rate_at(sym, ts_ms)
        time.sleep(0.15)
        ls = fetch_ls_ratio_at(sym, ts_ms)
        time.sleep(0.15)
        oi = fetch_oi_at(sym, ts_ms)
        time.sleep(0.15)
        flow = fetch_taker_flow_at(sym, ts_ms)
        time.sleep(0.15)
        cctx = fetch_candle_context_at(sym, ts_ms) or {}
        row = {
            "case_id": t["case_id"],
            "symbol": sym,
            "side": t["side"],
            "opened_at_ms": ts_ms,
            "opened_at_iso": datetime.fromtimestamp(ts_ms / 1000, timezone.utc).isoformat(),
            "realized_pnl_pct": t["realized_pnl_pct"],
            "exit_rule": t.get("exit_rule"),
            "funding_rate": funding,
            "ls_ratio": ls,
            "oi_at": oi[0] if oi else None,
            "oi_change_pct_15m": oi[1] if oi else None,
            "taker_buy_ratio": flow,
            **cctx,
        }
        rows.append(row)
        fr = f"{funding:.5f}" if funding is not None else "—"
        lsr = f"{ls:.3f}" if ls is not None else "—"
        oich = f"{oi[1]:+.3f}%" if oi else "—"
        flw = f"{flow:.3f}" if flow is not None else "—"
        print(
            f"   [{idx:2d}/{len(deduped)}] {sym:7s} {t['side']:5s} "
            f"pnl={t['realized_pnl_pct']:+.3f}% funding={fr} ls={lsr} oi15m={oich} flow={flw}"
        )

    # Persist raw
    jsonl_path = "/tmp/forensic_stage_b_exchange.jsonl"
    with open(jsonl_path, "w") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")
    print(f"\n[persist] {jsonl_path} written")

    # Analysis
    pnls = [r["realized_pnl_pct"] for r in rows]

    def feature_values(name: str) -> Tuple[List[float], List[float]]:
        xs, ys = [], []
        for r in rows:
            v = r.get(name)
            if v is None:
                continue
            xs.append(float(v))
            ys.append(r["realized_pnl_pct"])
        return xs, ys

    features = [
        ("funding_rate", "Funding rate (8h realised)"),
        ("ls_ratio", "Long/Short account ratio"),
        ("oi_change_pct_15m", "OI change % (15m)"),
        ("taker_buy_ratio", "Taker buy/total ratio (5m)"),
        ("candle_volume_ratio", "5m volume / 20-bar avg"),
        ("candle_return_pct", "5m candle return %"),
        ("candle_body_frac", "5m body / range"),
    ]

    analysis: Dict[str, Any] = {
        "computed_at": datetime.now(timezone.utc).isoformat(),
        "n_total_closed": len(trades_all),
        "n_in_window": len(candidates),
        "n_deduped": len(deduped),
        "n_evaluated": len(rows),
        "sample_caveat": (
            f"N={len(rows)} is intentionally small (architect directive 8-20). "
            "Any verdict is SUGGESTIVE, not proof."
        ),
        "features": {},
        "slices": {},
    }

    for key, label in features:
        xs, ys = feature_values(key)
        r = spearman(xs, ys) if len(xs) >= 4 else None
        buckets = tertile_split(xs, ys) if len(xs) >= 6 else {"_warn": f"n={len(xs)} <6"}
        rules: List[Dict[str, Any]] = []
        if xs:
            # Simple sign / threshold rules per feature.
            if key == "funding_rate":
                rules.append(rule_test(lambda v: v > 0.00005, xs, ys, "funding > +0.00005 (longs pay)"))
                rules.append(rule_test(lambda v: v < -0.00005, xs, ys, "funding < -0.00005 (shorts pay)"))
            elif key == "ls_ratio":
                rules.append(rule_test(lambda v: v > 1.2, xs, ys, "L/S > 1.2 (longs crowded)"))
                rules.append(rule_test(lambda v: v < 0.9, xs, ys, "L/S < 0.9 (shorts crowded)"))
            elif key == "oi_change_pct_15m":
                rules.append(rule_test(lambda v: v > 1.0, xs, ys, "OI +1% in 15m (expansion)"))
                rules.append(rule_test(lambda v: v < -1.0, xs, ys, "OI -1% in 15m (contraction)"))
                rules.append(rule_test(lambda v: v > 0, xs, ys, "OI expanding (>0%)"))
                rules.append(rule_test(lambda v: v < 0, xs, ys, "OI contracting (<0%)"))
            elif key == "taker_buy_ratio":
                rules.append(rule_test(lambda v: v > 0.55, xs, ys, "buy_ratio > 0.55 (aggressive buying)"))
                rules.append(rule_test(lambda v: v < 0.45, xs, ys, "buy_ratio < 0.45 (aggressive selling)"))
                rules.append(rule_test(lambda v: v > 0.50, xs, ys, "buy_ratio > 0.50 (net buy)"))
                rules.append(rule_test(lambda v: v < 0.50, xs, ys, "buy_ratio < 0.50 (net sell)"))
            elif key == "candle_volume_ratio":
                rules.append(rule_test(lambda v: v > 1.5, xs, ys, "volume > 1.5× avg (spike)"))
                rules.append(rule_test(lambda v: v < 0.5, xs, ys, "volume < 0.5× avg (dry)"))
        verdict, verdict_reason = classify_verdict(
            r, buckets if isinstance(buckets, dict) and "low" in buckets else {}
        )
        analysis["features"][key] = {
            "label": label,
            "n": len(xs),
            "spearman_rho": r,
            "buckets": buckets,
            "rules": rules,
            "verdict": verdict,
            "verdict_reason": verdict_reason,
        }

    # ──────────────────────────────────────────────────────────────────
    # Slices: per-symbol and per-side breakdown for the 2-3 most
    # promising features. Critical because L/S ratio is strongly
    # per-asset bimodal (BTC ~0.65 vs ETH ~1.15), so aggregate is
    # confounded.
    # ──────────────────────────────────────────────────────────────────
    def slice_rows(pred) -> Tuple[int, float, float]:
        sub = [r for r in rows if pred(r)]
        if not sub:
            return (0, 0.0, 0.0)
        p = [r["realized_pnl_pct"] for r in sub]
        wr = sum(1 for v in p if v > 0) / len(p)
        return (len(sub), statistics.mean(p), wr)

    analysis["slices"]["by_symbol"] = {
        sym: dict(zip(["n", "avg_pnl_pct", "win_rate"], slice_rows(lambda r, s=sym: r["symbol"] == s)))
        for sym in ("BTCUSDT", "ETHUSDT")
    }
    analysis["slices"]["by_side"] = {
        side: dict(zip(["n", "avg_pnl_pct", "win_rate"], slice_rows(lambda r, s=side: r["side"] == s)))
        for side in ("LONG", "SHORT")
    }

    # Per (symbol, feature) correlation — isolate confounding
    analysis["slices"]["per_symbol_feature_rho"] = {}
    for sym in ("BTCUSDT", "ETHUSDT"):
        sym_rows = [r for r in rows if r["symbol"] == sym]
        if len(sym_rows) < 4:
            continue
        pnls_s = [r["realized_pnl_pct"] for r in sym_rows]
        f_rho: Dict[str, Optional[float]] = {}
        for key, _ in features:
            vals = [r[key] for r in sym_rows if r.get(key) is not None]
            pnl_paired = [r["realized_pnl_pct"] for r in sym_rows if r.get(key) is not None]
            if len(vals) >= 4:
                f_rho[key] = spearman(vals, pnl_paired)
            else:
                f_rho[key] = None
        analysis["slices"]["per_symbol_feature_rho"][sym] = {"n": len(sym_rows), "rho": f_rho}

    # Overall summary
    analysis["summary"] = {
        "alpha": [k for k, v in analysis["features"].items() if v["verdict"] == "ALPHA"],
        "alpha_nonlinear": [k for k, v in analysis["features"].items() if v["verdict"] == "ALPHA_NONLINEAR"],
        "reserve": [k for k, v in analysis["features"].items() if v["verdict"] == "RESERVE"],
        "no_alpha": [k for k, v in analysis["features"].items() if v["verdict"] == "NO_ALPHA"],
        "inconclusive": [k for k, v in analysis["features"].items() if v["verdict"] == "INCONCLUSIVE"],
    }

    # Markdown report
    md = render_markdown(analysis, rows)
    md_path = "/tmp/forensic_stage_b_exchange.md"
    with open(md_path, "w") as f:
        f.write(md)
    print(f"[persist] {md_path} written\n")

    # Console summary
    print("─" * 72)
    print(" VERDICT per feature")
    print("─" * 72)
    for key, v in analysis["features"].items():
        print(
            f"  {v['verdict']:13s}  {key:24s}  ρ={v['spearman_rho']}  n={v['n']}  — {v['label']}"
        )
    print()
    print(f"  ALPHA            : {analysis['summary']['alpha'] or 'none'}")
    print(f"  ALPHA_NONLINEAR  : {analysis['summary']['alpha_nonlinear'] or 'none'}")
    print(f"  RESERVE          : {analysis['summary']['reserve'] or 'none'}")
    print(f"  NO_ALPHA         : {analysis['summary']['no_alpha'] or 'none'}")
    print(f"  INCONCLUSIVE     : {analysis['summary']['inconclusive'] or 'none'}")
    print()
    print("─" * 72)
    print(" Slices")
    print("─" * 72)
    for sym, v in analysis["slices"]["by_symbol"].items():
        print(f"  by_symbol  {sym:8s}  n={v['n']:2d}  avg_pnl={v['avg_pnl_pct']:+.3f}%  WR={v['win_rate']:.2f}")
    for side, v in analysis["slices"]["by_side"].items():
        print(f"  by_side    {side:8s}  n={v['n']:2d}  avg_pnl={v['avg_pnl_pct']:+.3f}%  WR={v['win_rate']:.2f}")
    for sym, blk in analysis["slices"]["per_symbol_feature_rho"].items():
        print(f"  ρ per {sym:7s}  (n={blk['n']})")
        for k, rho in blk["rho"].items():
            print(f"      {k:24s}  ρ={rho}")
    print()
    print("═" * 72)
    print(f" N_evaluated = {len(rows)}. Sample is small by design — results")
    print(" are SUGGESTIVE, not proof. Decide next action with architect.")
    print("═" * 72)
    return 0


def render_markdown(analysis: Dict[str, Any], rows: List[Dict[str, Any]]) -> str:
    lines: List[str] = []
    lines.append("# Stage B — Forensic #1: Exchange Intelligence\n")
    lines.append(f"_Generated: {analysis['computed_at']}_\n")
    lines.append("## Scope")
    lines.append(
        f"- closed trading_cases scanned: **{analysis['n_total_closed']}**\n"
        f"- within OKX rubik-stats window (~3d): **{analysis['n_in_window']}**\n"
        f"- after 10-min dedup: **{analysis['n_deduped']}**\n"
        f"- evaluated (with fetched features): **{analysis['n_evaluated']}**\n"
    )
    lines.append(f"> {analysis['sample_caveat']}\n")

    lines.append("## Verdicts\n")
    lines.append("| Feature | N | Spearman ρ | Verdict | Reason |")
    lines.append("|---|---|---|---|---|")
    for key, v in analysis["features"].items():
        lines.append(
            f"| `{key}` | {v['n']} | {v['spearman_rho']} | **{v['verdict']}** | {v['verdict_reason']} |"
        )
    lines.append("")

    # Slices section — critical for confounding (BTC vs ETH on L/S ratio etc.)
    sl = analysis.get("slices", {})
    if sl:
        lines.append("## Slices\n")
        lines.append("**By symbol:**\n")
        lines.append("| Symbol | N | Avg PnL% | WR |")
        lines.append("|---|---|---|---|")
        for sym, v in sl.get("by_symbol", {}).items():
            lines.append(
                f"| {sym} | {v['n']} | {v['avg_pnl_pct']:+.3f} | {v['win_rate']:.2f} |"
            )
        lines.append("\n**By side:**\n")
        lines.append("| Side | N | Avg PnL% | WR |")
        lines.append("|---|---|---|---|")
        for side, v in sl.get("by_side", {}).items():
            lines.append(
                f"| {side} | {v['n']} | {v['avg_pnl_pct']:+.3f} | {v['win_rate']:.2f} |"
            )

        rho_sym = sl.get("per_symbol_feature_rho", {})
        if rho_sym:
            lines.append("\n**Per-symbol Spearman ρ (deconfounded):**\n")
            sym_keys = list(rho_sym.keys())
            lines.append(
                "| Feature | "
                + " | ".join(f"{s} (n={rho_sym[s]['n']})" for s in sym_keys)
                + " |"
            )
            lines.append("|---|" + "---|" * len(sym_keys))
            for fkey, _ in [(k, v) for k, v in analysis["features"].items()]:
                row = [f"`{fkey}`"]
                for s in sym_keys:
                    row.append(str(rho_sym[s]["rho"].get(fkey)))
                lines.append("| " + " | ".join(row) + " |")
        lines.append("")

    lines.append("## Per-feature detail\n")
    for key, v in analysis["features"].items():
        lines.append(f"### `{key}` — {v['label']}\n")
        lines.append(f"- n = {v['n']}, Spearman ρ = **{v['spearman_rho']}**")
        lines.append(f"- verdict: **{v['verdict']}** — {v['verdict_reason']}\n")
        b = v["buckets"]
        if isinstance(b, dict) and "low" in b:
            lines.append("**Tertile buckets:**\n")
            lines.append("| Bucket | N | Avg PnL% | Median | WR | Value range |")
            lines.append("|---|---|---|---|---|---|")
            for gname in ("low", "mid", "high"):
                g = b.get(gname, {})
                if g.get("n"):
                    lines.append(
                        f"| {gname} | {g['n']} | {g['avg_pnl_pct']} | {g['median_pnl_pct']} | "
                        f"{g['win_rate']} | {g['value_range']} |"
                    )
            lines.append("")
        if v.get("rules"):
            lines.append("**Rule tests:**\n")
            for r in v["rules"]:
                if r.get("n_match"):
                    lines.append(
                        f"- `{r['rule']}` → n_match={r['n_match']}, avg PnL%={r.get('match_avg_pnl_pct')}, "
                        f"WR={r.get('match_wr')}, spread vs rest={r.get('spread_pct')}%"
                    )
                else:
                    lines.append(f"- `{r['rule']}` → no matches")
            lines.append("")

    lines.append("## Trade sample (raw joined)\n")
    lines.append(
        "| case_id | symbol | side | pnl% | funding | L/S | OI Δ15m% | buy_ratio | vol_ratio | exit |"
    )
    lines.append("|---|---|---|---|---|---|---|---|---|---|")
    for r in rows:
        lines.append(
            f"| {r['case_id'][:14]}… | {r['symbol']} | {r['side']} | {r['realized_pnl_pct']:+.3f} | "
            f"{r.get('funding_rate') or '—'} | {r.get('ls_ratio') or '—'} | "
            f"{r.get('oi_change_pct_15m') or '—'} | {r.get('taker_buy_ratio') or '—'} | "
            f"{r.get('candle_volume_ratio') or '—'} | {r.get('exit_rule') or '—'} |"
        )
    lines.append("")
    return "\n".join(lines)


if __name__ == "__main__":
    sys.exit(main())
