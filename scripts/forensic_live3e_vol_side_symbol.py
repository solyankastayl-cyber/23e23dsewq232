#!/usr/bin/env python3
"""
forensic_live3e_vol_side_symbol.py — Phase LIVE-3e read-only forensic.

Goal (architect directive, 2026-05-03):
    After the LIVE-3d relaxation window (min_adjusted_confidence=0.45),
    surface a 3D pivot  `vol_bucket × side × symbol`  over closed trades,
    with an independent split by post-relaxation confidence tier.

This script is strictly READ-ONLY. It does NOT change controls, does NOT
recommend gate changes, does NOT touch runtime. It only surfaces buckets
and labels each with the proper statistical guard (Wilson 95% CI,
INSUFFICIENT at N<min_n, NO_CONCLUSION at total N<min_total_n).

Dimensions:

    VOLATILITY (1h × 20-bar stdev of pct returns, pre-entry, per symbol):
        LOW   < 0.0015
        MID   0.0015 - 0.0030
        HIGH  >= 0.0030

    SIDE:
        LONG  (case.side in {LONG, BUY})
        SHORT (case.side in {SHORT, SELL})

    SYMBOL:
        BTCUSDT, ETHUSDT, ...

    CONFIDENCE tier (orthogonal split, two independent views):
        POST  (adjusted_confidence in [0.40, 0.50))   — added by LIVE-3d relaxation
        BASE  (adjusted_confidence >= 0.50)           — would have passed 0.50 gate

Data sources (read-only):
    trading_cases      (closed trades with realized_pnl_pct, opened_at, symbol, side,
                        decision_id)
    execution_jobs     (payload.adjusted_confidence / base_confidence /
                        volatility_1h_20 / market_ctx_source), linked by decision_id
    candles            (1h closes per symbol, for fallback volatility computation
                        when execution_jobs.payload.volatility_1h_20 is missing)

Outputs (writes only):
    /tmp/forensic_live3e_report.md
    /tmp/forensic_live3e.jsonl

Usage:
    python3 /app/scripts/forensic_live3e_vol_side_symbol.py
    python3 /app/scripts/forensic_live3e_vol_side_symbol.py --min-n 5 --min-total-n 20
    python3 /app/scripts/forensic_live3e_vol_side_symbol.py --since 2026-05-03T12:00:00Z

The conf-tier split is applied AFTER the main 3D pivot so both total and
conditional views are visible side-by-side.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import statistics
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional, Tuple

from pymongo import MongoClient

# ---------------------------------------------------------------------------
# Buckets
# ---------------------------------------------------------------------------
VOL_BUCKETS: List[Tuple[float, float, str]] = [
    (-1e9, 0.0015, "LOW  (<0.15%)"),
    (0.0015, 0.0030, "MID  [0.15%-0.30%)"),
    (0.0030, 1e9, "HIGH (>=0.30%)"),
]

# Confidence tiers introduced by the LIVE-3d relaxation.
CONF_POST_LO, CONF_POST_HI = 0.40, 0.50
CONF_BASE_LO = 0.50

DEFAULT_MIN_N = 5
DEFAULT_MIN_TOTAL_N = 20

PAUSE_ARTEFACTS = {"case-3cbabe9b6d08", "case-e9c8f0d50298"}


# ---------------------------------------------------------------------------
# Generic helpers
# ---------------------------------------------------------------------------
def _bucket_label(value: Optional[float],
                  buckets: List[Tuple[float, float, str]]) -> str:
    if value is None:
        return "UNKNOWN"
    for lo, hi, label in buckets:
        if lo <= value < hi:
            return label
    return buckets[-1][2]


def _wilson_interval(wins: int, n: int, z: float = 1.96) -> Tuple[float, float]:
    if n == 0:
        return (0.0, 0.0)
    p = wins / n
    denom = 1 + z * z / n
    centre = p + z * z / (2 * n)
    margin = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return (max(0.0, (centre - margin) / denom),
            min(1.0, (centre + margin) / denom))


def _to_dt(value: Any) -> Optional[datetime]:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
    return None


def _norm_side(side: Optional[str]) -> Optional[str]:
    if not isinstance(side, str):
        return None
    s = side.upper().strip()
    if s in ("LONG", "BUY"):
        return "LONG"
    if s in ("SHORT", "SELL"):
        return "SHORT"
    return None


def _conf_tier(conf: Optional[float]) -> Optional[str]:
    if conf is None:
        return None
    try:
        c = float(conf)
    except (TypeError, ValueError):
        return None
    if CONF_POST_LO <= c < CONF_POST_HI:
        return "POST"
    if c >= CONF_BASE_LO:
        return "BASE"
    return None  # below 0.40 — not part of this forensic


# ---------------------------------------------------------------------------
# Data load
# ---------------------------------------------------------------------------
def _load_closed_cases(
    db,
    strategy: Optional[str],
    since: Optional[datetime],
    exclude_artefacts: bool,
) -> List[Dict[str, Any]]:
    q: Dict[str, Any] = {"status": "CLOSED", "realized_pnl_pct": {"$ne": None}}
    if strategy:
        q["strategy"] = strategy
    if exclude_artefacts:
        q["case_id"] = {"$nin": list(PAUSE_ARTEFACTS)}
    if since:
        q["opened_at"] = {"$gte": since}
    proj = {
        "_id": 0, "case_id": 1, "side": 1, "strategy": 1, "symbol": 1,
        "opened_at": 1, "closed_at": 1, "entry_price": 1,
        "realized_pnl_pct": 1, "decision_id": 1,
    }
    return list(db["trading_cases"].find(q, proj).sort("opened_at", 1))


def _load_exec_jobs_by_decision(
    db, decision_ids: List[str]
) -> Dict[str, Dict[str, Any]]:
    """Map decision_id -> payload (most recent if duplicates).

    Only keeps the fields we care about.
    """
    if not decision_ids:
        return {}
    cur = db["execution_jobs"].find(
        {"payload.decision_id": {"$in": decision_ids}},
        {"_id": 0, "created_at": 1, "payload": 1},
    ).sort("created_at", 1)
    out: Dict[str, Dict[str, Any]] = {}
    for ej in cur:
        p = ej.get("payload") or {}
        did = p.get("decision_id")
        if not did:
            continue
        # Latest wins (cursor is sorted ascending, so overwrite).
        out[did] = {
            "base_confidence": p.get("base_confidence"),
            "adjusted_confidence": p.get("adjusted_confidence"),
            "regime_at_entry": p.get("regime_at_entry"),
            "volatility_1h_20": p.get("volatility_1h_20"),
            "ma5_1h": p.get("ma5_1h"),
            "distance_to_ma5_1h": p.get("distance_to_ma5_1h"),
            "market_ctx_source": p.get("market_ctx_source"),
            "market_ctx_candles_used": p.get("market_ctx_candles_used"),
            "symbol": p.get("symbol"),
            "side": p.get("side"),
            "strategy": p.get("strategy"),
        }
    return out


def _load_1h_closes(db, symbol: str) -> List[Tuple[datetime, float]]:
    cur = db["candles"].find(
        {"symbol": symbol, "timeframe": "1h"},
        {"_id": 0, "timestamp": 1, "close": 1},
    )
    rows: List[Tuple[datetime, float]] = []
    for c in cur:
        ts = _to_dt(c.get("timestamp"))
        close = c.get("close")
        if ts is None or close is None:
            continue
        try:
            rows.append((ts, float(close)))
        except (TypeError, ValueError):
            continue
    rows.sort(key=lambda x: x[0])
    return rows


# ---------------------------------------------------------------------------
# Volatility derivation (per symbol, pre-entry, 20-bar 1h stdev of returns)
# ---------------------------------------------------------------------------
def _slice_pre_entry(
    closes: List[Tuple[datetime, float]],
    opened_at: datetime,
    n: int = 20,
) -> List[float]:
    pre = [c for ts, c in closes if ts < opened_at]
    return pre[-n:]


def _volatility_from_window(window: List[float]) -> Optional[float]:
    if len(window) < 6:
        return None
    rets = [
        (window[i] - window[i - 1]) / window[i - 1]
        for i in range(1, len(window))
        if window[i - 1]
    ]
    if len(rets) < 5:
        return None
    try:
        return statistics.pstdev(rets)
    except statistics.StatisticsError:
        return None


def _fallback_volatility(
    case: Dict[str, Any],
    closes_by_sym: Dict[str, List[Tuple[datetime, float]]],
) -> Optional[float]:
    symbol = case.get("symbol")
    opened = _to_dt(case.get("opened_at"))
    if not symbol or opened is None:
        return None
    closes = closes_by_sym.get(symbol)
    if not closes:
        return None
    window = _slice_pre_entry(closes, opened, n=20)
    return _volatility_from_window(window)


# ---------------------------------------------------------------------------
# Metric shaping
# ---------------------------------------------------------------------------
def _make_row(
    case: Dict[str, Any],
    job: Optional[Dict[str, Any]],
    fallback_vol: Optional[float],
) -> Dict[str, Any]:
    side = _norm_side(case.get("side"))

    # Prefer volatility from the execution_jobs payload if it was recorded
    # alongside the live entry (that is what the runtime actually saw).
    vol_payload = None
    if job and job.get("volatility_1h_20") is not None:
        try:
            vol_payload = float(job["volatility_1h_20"])
        except (TypeError, ValueError):
            vol_payload = None
    vol = vol_payload if vol_payload is not None else fallback_vol

    base_conf = None
    adj_conf = None
    regime = None
    src = None
    if job:
        for key_src, key_dst in (
            ("base_confidence", "base_conf"),
            ("adjusted_confidence", "adj_conf"),
        ):
            val = job.get(key_src)
            if val is not None:
                try:
                    if key_dst == "base_conf":
                        base_conf = float(val)
                    else:
                        adj_conf = float(val)
                except (TypeError, ValueError):
                    pass
        regime = job.get("regime_at_entry")
        src = job.get("market_ctx_source")

    return {
        "case_id": case.get("case_id"),
        "symbol": case.get("symbol"),
        "side": side,
        "opened_at": str(case.get("opened_at")),
        "closed_at": str(case.get("closed_at")),
        "entry_price": case.get("entry_price"),
        "realized_pnl_pct": case.get("realized_pnl_pct"),
        "decision_id": case.get("decision_id"),
        "volatility_1h_20": vol,
        "volatility_source": (
            "execution_jobs.payload" if vol_payload is not None
            else ("candles_fallback" if fallback_vol is not None else "unknown")
        ),
        "base_confidence": base_conf,
        "adjusted_confidence": adj_conf,
        "regime_at_entry": regime,
        "market_ctx_source": src,
        "vol_bucket": _bucket_label(vol, VOL_BUCKETS),
        "conf_tier": _conf_tier(adj_conf),
    }


# ---------------------------------------------------------------------------
# 3D aggregation: vol × side × symbol (+ optional conf_tier filter)
# ---------------------------------------------------------------------------
def _aggregate_3d(
    rows: List[Dict[str, Any]],
    conf_tier: Optional[str],
) -> List[Dict[str, Any]]:
    filtered = rows
    if conf_tier is not None:
        filtered = [r for r in rows if r.get("conf_tier") == conf_tier]

    groups: Dict[Tuple[str, str, str], List[Dict[str, Any]]] = {}
    for r in filtered:
        vol_b = r.get("vol_bucket") or "UNKNOWN"
        side = r.get("side") or "UNKNOWN"
        sym = r.get("symbol") or "UNKNOWN"
        groups.setdefault((vol_b, side, sym), []).append(r)

    out: List[Dict[str, Any]] = []
    for (vol_b, side, sym), members in groups.items():
        n = len(members)
        pnls = [r["realized_pnl_pct"] for r in members
                if r.get("realized_pnl_pct") is not None]
        wins = sum(1 for p in pnls if p > 0)
        ci_lo, ci_hi = _wilson_interval(wins, n)
        out.append({
            "vol_bucket": vol_b,
            "side": side,
            "symbol": sym,
            "n": n,
            "wins": wins,
            "wr": round(wins / n, 4) if n else None,
            "wr_ci_lo": round(ci_lo, 4),
            "wr_ci_hi": round(ci_hi, 4),
            "avg_pnl": round(statistics.mean(pnls), 4) if pnls else None,
            "median_pnl": round(statistics.median(pnls), 4) if pnls else None,
            "sum_pnl": round(sum(pnls), 4) if pnls else None,
        })
    # Sort for stable output.
    vol_order = {b[2]: i for i, b in enumerate(VOL_BUCKETS)}
    vol_order["UNKNOWN"] = len(VOL_BUCKETS)
    out.sort(key=lambda x: (
        vol_order.get(x["vol_bucket"], 99),
        x["side"],
        x["symbol"],
    ))
    return out


# ---------------------------------------------------------------------------
# Reporting helpers
# ---------------------------------------------------------------------------
def _fmt_pnl(value: Optional[float]) -> str:
    if value is None:
        return "—"
    return f"{value:+.4f}%"


def _fmt_wr(wr: Optional[float], lo: Optional[float], hi: Optional[float]) -> str:
    if wr is None:
        return "—"
    return f"{wr * 100:5.1f}% [{lo * 100:5.1f}, {hi * 100:5.1f}]"


def _pivot_table_md(title: str, rows: List[Dict[str, Any]],
                    min_n: int, min_total_n: int) -> str:
    total = sum(r["n"] for r in rows)
    out = [f"### {title}", f"_total N={total}; min_bucket_n={min_n}_"]
    if total < min_total_n:
        out.append(
            f"\n> ⚠ NO_CONCLUSION: total N={total} < {min_total_n}. "
            "Numbers descriptive only."
        )
    out.append("")
    if not rows:
        out.append("_(no rows in this tier)_")
        return "\n".join(out)
    out.append(
        "| vol_bucket        | side  | symbol    |  N | W | WR   95% CI              "
        "| avg PnL    | median PnL | flag         |"
    )
    out.append(
        "|-------------------|-------|-----------|----|---|--------------------------"
        "|------------|------------|--------------|"
    )
    for r in rows:
        flag = "INSUFFICIENT" if r["n"] < min_n else "ok"
        out.append(
            f"| {r['vol_bucket']:<17} | {r['side']:<5} | {r['symbol']:<9} | "
            f"{r['n']:>2} | {r['wins']:>1} | "
            f"{_fmt_wr(r['wr'], r['wr_ci_lo'], r['wr_ci_hi']):<24} | "
            f"{_fmt_pnl(r['avg_pnl'])} | {_fmt_pnl(r['median_pnl'])} | "
            f"{flag:<12} |"
        )
    return "\n".join(out)


def _pivot_digest(title: str, rows: List[Dict[str, Any]], min_n: int) -> str:
    lines = [f"--- {title} ---"]
    if not rows:
        lines.append("  (no rows)")
        return "\n".join(lines)
    for r in rows:
        flag = "INSUFFICIENT" if r["n"] < min_n else "ok"
        lines.append(
            f"  {r['vol_bucket']:<18} {r['side']:<5} {r['symbol']:<9} "
            f"N={r['n']:<3} W={r['wins']:<2}  "
            f"WR={(r['wr'] or 0) * 100:5.1f}%  "
            f"CI=[{r['wr_ci_lo'] * 100:5.1f},{r['wr_ci_hi'] * 100:5.1f}]  "
            f"avg={_fmt_pnl(r['avg_pnl']):<10} med={_fmt_pnl(r['median_pnl']):<10} "
            f"[{flag}]"
        )
    return "\n".join(lines)


def _rollup_by_axis(rows: List[Dict[str, Any]], axis: str) -> List[Dict[str, Any]]:
    """Collapse 3D rows along two axes, keeping one."""
    groups: Dict[str, List[Dict[str, Any]]] = {}
    for r in rows:
        groups.setdefault(r.get(axis, "UNKNOWN"), []).append(r)
    out: List[Dict[str, Any]] = []
    for label, members in groups.items():
        n = sum(m["n"] for m in members)
        wins = sum(m["wins"] for m in members)
        # For avg/median we need the raw pnl values — not available after
        # aggregation. We approximate avg by weighted mean of bucket means.
        totals_pnl = sum(
            (m["avg_pnl"] or 0.0) * m["n"]
            for m in members if m["avg_pnl"] is not None
        )
        effective_n = sum(m["n"] for m in members if m["avg_pnl"] is not None)
        avg_pnl = (totals_pnl / effective_n) if effective_n else None
        ci_lo, ci_hi = _wilson_interval(wins, n)
        out.append({
            "axis": axis, "label": label,
            "n": n, "wins": wins,
            "wr": round(wins / n, 4) if n else None,
            "wr_ci_lo": round(ci_lo, 4),
            "wr_ci_hi": round(ci_hi, 4),
            "avg_pnl": round(avg_pnl, 4) if avg_pnl is not None else None,
        })
    out.sort(key=lambda x: (-x["n"], str(x["label"])))
    return out


def _rollup_md(title: str, rows: List[Dict[str, Any]]) -> str:
    out = [f"### {title}", ""]
    out.append(
        "| label                | N  | W  | WR    95% CI            | avg PnL (wtd) |"
    )
    out.append(
        "|----------------------|----|----|-------------------------|---------------|"
    )
    for r in rows:
        out.append(
            f"| {str(r['label']):<20} | {r['n']:>2} | {r['wins']:>2} | "
            f"{_fmt_wr(r['wr'], r['wr_ci_lo'], r['wr_ci_hi']):<23} | "
            f"{_fmt_pnl(r['avg_pnl']):<13} |"
        )
    return "\n".join(out)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def _parse_since(raw: Optional[str]) -> Optional[datetime]:
    if not raw:
        return None
    dt = _to_dt(raw)
    if dt is None:
        raise SystemExit(f"--since: cannot parse '{raw}' as ISO-8601")
    return dt


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--strategy", default="SIMPLE_MA")
    parser.add_argument("--exclude-pause-artefacts", action="store_true")
    parser.add_argument("--since", default=None,
                        help="ISO-8601 lower bound on opened_at (inclusive).")
    parser.add_argument("--min-n", type=int, default=DEFAULT_MIN_N)
    parser.add_argument("--min-total-n", type=int, default=DEFAULT_MIN_TOTAL_N)
    args = parser.parse_args()

    mongo_url = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
    db_name = os.environ.get("DB_NAME", "trading_os")
    client = MongoClient(mongo_url, serverSelectionTimeoutMS=3000)
    db = client[db_name]

    since = _parse_since(args.since)
    cases = _load_closed_cases(db, args.strategy, since,
                               args.exclude_pause_artefacts)
    print(f"[forensic-live3e] DB={db_name} strategy={args.strategy} "
          f"since={since} excl_artefacts={args.exclude_pause_artefacts}")
    print(f"[forensic-live3e] loaded {len(cases)} closed cases")

    decision_ids = [c.get("decision_id") for c in cases if c.get("decision_id")]
    jobs_by_did = _load_exec_jobs_by_decision(db, decision_ids)
    print(f"[forensic-live3e] matched {len(jobs_by_did)} execution_jobs "
          f"via decision_id")

    # Load per-symbol 1h candle series once (only for symbols present in
    # the case set).
    symbols = sorted({c.get("symbol") for c in cases if c.get("symbol")})
    closes_by_sym: Dict[str, List[Tuple[datetime, float]]] = {}
    for sym in symbols:
        closes_by_sym[sym] = _load_1h_closes(db, sym)
    for sym in symbols:
        print(f"[forensic-live3e] candles {sym} 1h: {len(closes_by_sym[sym])}")

    # Build per-trade rows with volatility + confidence + bucket labels.
    rows: List[Dict[str, Any]] = []
    for c in cases:
        did = c.get("decision_id")
        job = jobs_by_did.get(did)
        fallback_vol = _fallback_volatility(c, closes_by_sym)
        row = _make_row(c, job, fallback_vol)
        rows.append(row)

    # Persist per-trade JSONL for inspection.
    out_jsonl = "/tmp/forensic_live3e.jsonl"
    with open(out_jsonl, "w", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r, default=str) + "\n")

    # Pivots: ALL / POST / BASE.
    piv_all = _aggregate_3d(rows, conf_tier=None)
    piv_post = _aggregate_3d(rows, conf_tier="POST")
    piv_base = _aggregate_3d(rows, conf_tier="BASE")

    # 1D roll-ups on ALL tier (weighted).
    roll_sym = _rollup_by_axis(piv_all, "symbol")
    roll_side = _rollup_by_axis(piv_all, "side")
    roll_vol = _rollup_by_axis(piv_all, "vol_bucket")

    # Build markdown.
    now = datetime.now(timezone.utc).isoformat()
    coverage = {
        "rows": len(rows),
        "with_job_payload": sum(1 for r in rows if r["adjusted_confidence"] is not None),
        "with_vol": sum(1 for r in rows if r["volatility_1h_20"] is not None),
        "vol_from_payload": sum(1 for r in rows if r["volatility_source"] == "execution_jobs.payload"),
        "vol_from_candles": sum(1 for r in rows if r["volatility_source"] == "candles_fallback"),
        "vol_missing": sum(1 for r in rows if r["volatility_source"] == "unknown"),
        "post_tier": sum(1 for r in rows if r["conf_tier"] == "POST"),
        "base_tier": sum(1 for r in rows if r["conf_tier"] == "BASE"),
        "tier_unknown": sum(1 for r in rows if r["conf_tier"] is None),
    }

    # --- Data-quality: market_ctx_source distribution (read-only) ----------
    # Shows which upstream provider each live entry actually used. Useful to
    # flag Coinbase-heavy windows (Binance truncation symptom) before
    # interpreting the pivot.
    src_counts: Dict[str, int] = {}
    src_by_symbol: Dict[str, Dict[str, int]] = {}
    for r in rows:
        raw = r.get("market_ctx_source")
        key = raw if isinstance(raw, str) and raw else "missing"
        src_counts[key] = src_counts.get(key, 0) + 1
        sym = r.get("symbol") or "UNKNOWN"
        src_by_symbol.setdefault(sym, {})
        src_by_symbol[sym][key] = src_by_symbol[sym].get(key, 0) + 1
    # Stable sort.
    src_counts_sorted = sorted(
        src_counts.items(), key=lambda kv: (-kv[1], kv[0])
    )
    src_by_symbol_sorted = {
        sym: sorted(d.items(), key=lambda kv: (-kv[1], kv[0]))
        for sym, d in sorted(src_by_symbol.items())
    }
    # -----------------------------------------------------------------------

    parts: List[str] = []
    parts.append(
        f"# LIVE-3e — Forensic: volatility × side × symbol\n\n"
        f"_generated {now}; strategy={args.strategy}; "
        f"since={args.since or 'ALL'}; "
        f"exclude_pause_artefacts={args.exclude_pause_artefacts}; "
        f"min_bucket_n={args.min_n}; min_total_n={args.min_total_n}_\n"
    )
    parts.append(
        "## Honest caveats\n"
        "- **Read-only.** Script does NOT change controls and does NOT "
        "recommend gates.\n"
        "- Volatility source order: (1) `execution_jobs.payload.volatility_1h_20` "
        "if present (it is what runtime saw live), else (2) recomputed from "
        "`candles` 1h slice ending at `opened_at` (20 closes, pstdev of pct "
        "returns). Field `volatility_source` on each row tells which path "
        "was used.\n"
        "- Confidence tier `POST` is `[0.40, 0.50)` (added by LIVE-3d "
        "relaxation); `BASE` is `>= 0.50` (would have passed the 0.50 "
        "gate anyway). Cases without `adjusted_confidence` (legacy / "
        "demo-* seed) are excluded from both tiers and visible only in the "
        "`ALL` view.\n"
        "- Wilson 95% CI on WR. `INSUFFICIENT` when a bucket has N<min_n. "
        "`NO_CONCLUSION` banner on the whole table when total N<min_total_n.\n"
        "- No multi-dimension hypothesis search is performed beyond the "
        "architect-specified pivot.\n"
    )

    parts.append("## Data coverage\n")
    parts.append(
        "| metric                        | count |\n"
        "|-------------------------------|-------|\n"
        f"| rows (closed cases)           | {coverage['rows']} |\n"
        f"| linked execution_jobs payload | {coverage['with_job_payload']} |\n"
        f"| rows with volatility          | {coverage['with_vol']} |\n"
        f"|   └ from payload              | {coverage['vol_from_payload']} |\n"
        f"|   └ from candles fallback     | {coverage['vol_from_candles']} |\n"
        f"|   └ missing                   | {coverage['vol_missing']} |\n"
        f"| conf tier POST [0.40, 0.50)   | {coverage['post_tier']} |\n"
        f"| conf tier BASE [>=0.50]       | {coverage['base_tier']} |\n"
        f"| tier unknown (no adj_conf)    | {coverage['tier_unknown']} |\n"
    )

    # market_ctx_source block
    parts.append("\n## Data quality — `market_ctx_source` distribution\n")
    parts.append(
        "_Which upstream candle provider each live entry actually used. "
        "A high Coinbase share is a symptom of Binance truncation in the "
        "signal runner. `missing` = execution_jobs.payload had no "
        "`market_ctx_source` (legacy/demo) or no payload linked to the "
        "case._\n"
    )
    parts.append("| source               | count |\n|----------------------|-------|")
    for k, v in src_counts_sorted:
        parts.append(f"| {k:<20} | {v:>5} |")
    parts.append("")
    parts.append("### By symbol\n")
    parts.append(
        "| symbol   | source               | count |\n"
        "|----------|----------------------|-------|"
    )
    for sym, items in src_by_symbol_sorted.items():
        for k, v in items:
            parts.append(f"| {sym:<8} | {k:<20} | {v:>5} |")
    parts.append("")

    parts.append(_pivot_table_md(
        "Pivot — ALL trades  (vol_bucket × side × symbol)",
        piv_all, args.min_n, args.min_total_n,
    ))
    parts.append("")
    parts.append(_pivot_table_md(
        "Pivot — POST tier  (adj_conf ∈ [0.40, 0.50))",
        piv_post, args.min_n, args.min_total_n,
    ))
    parts.append("")
    parts.append(_pivot_table_md(
        "Pivot — BASE tier  (adj_conf ≥ 0.50)",
        piv_base, args.min_n, args.min_total_n,
    ))

    parts.append("")
    parts.append("## Rollups (weighted over ALL pivot)\n")
    parts.append(_rollup_md("By symbol", roll_sym))
    parts.append("")
    parts.append(_rollup_md("By side", roll_side))
    parts.append("")
    parts.append(_rollup_md("By vol_bucket", roll_vol))

    parts.append(
        "\n## How to read\n"
        "- A cell is a **candidate edge** only when: N ≥ min_n AND its WR "
        "is ≥10pp away from a peer cell's WR AND Wilson 95% CIs do NOT "
        "overlap.\n"
        "- Compare POST vs BASE cell-by-cell: if POST shows comparable WR "
        "and avg_pnl to BASE in the same (vol, side, symbol) slot, the "
        "relaxation window paid for itself; if POST systematically "
        "under-performs in one slot, that is a candidate for tier-aware "
        "gating.\n"
        "- If `ALL` totals < 20, treat as descriptive only.\n"
    )

    out_md = "/tmp/forensic_live3e_report.md"
    with open(out_md, "w", encoding="utf-8") as fh:
        fh.write("\n".join(parts))

    # Stdout digest.
    print()
    print("=" * 78)
    print("LIVE-3e FORENSIC — digest")
    print("=" * 78)
    print(
        f"rows={coverage['rows']}  with_vol={coverage['with_vol']}  "
        f"POST={coverage['post_tier']}  BASE={coverage['base_tier']}  "
        f"tier_unknown={coverage['tier_unknown']}"
    )
    print(
        "  market_ctx_source: "
        + ", ".join(f"{k}={v}" for k, v in src_counts_sorted)
    )
    print()
    print(_pivot_digest("ALL (vol × side × symbol)", piv_all, args.min_n))
    print()
    print(_pivot_digest("POST tier [0.40, 0.50)", piv_post, args.min_n))
    print()
    print(_pivot_digest("BASE tier [>=0.50]", piv_base, args.min_n))
    print()
    print("Rollups (ALL):")
    print(f"  by symbol: " + ", ".join(
        f"{r['label']} N={r['n']} WR={((r['wr'] or 0) * 100):.1f}%" for r in roll_sym
    ))
    print(f"  by side:   " + ", ".join(
        f"{r['label']} N={r['n']} WR={((r['wr'] or 0) * 100):.1f}%" for r in roll_side
    ))
    print(f"  by vol:    " + ", ".join(
        f"{r['label']} N={r['n']} WR={((r['wr'] or 0) * 100):.1f}%" for r in roll_vol
    ))
    print()
    print(f"report    → {out_md}")
    print(f"per-trade → {out_jsonl}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
