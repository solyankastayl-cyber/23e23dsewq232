#!/usr/bin/env python3
"""
forensic_live3b_conf_buckets.py — Phase LIVE-3b read-only forensic.

Goal: measure whether adjusted_confidence (from LIVE-3a layer) actually ranks
trades by realised PnL. If buckets show monotonic improvement (lower conf →
worse PnL, higher conf → better PnL), the layer carries signal. If buckets
look identical, the layer is noise.

Two correlated views are emitted:

  * NATIVE  — use payload.adjusted_confidence + payload.regime_at_entry
              from execution_jobs (joined to trading_cases via decision_id).
              Available only for trades created AFTER LIVE-3a deploy.
              N=0 immediately after deploy and grows over time.

  * RETRO   — reconstruct adjusted_confidence from `side` only, using the
              same multiplier defaults as bridge.py (`short_side_multiplier`
              =0.80, `long_uptrend_multiplier`=0.85). Historical regime is NOT
              stored, so the retro view collapses to 2 effective buckets:
                LONG (any regime != UPTREND known) → 0.60
                SHORT                              → 0.48
              This is honestly weaker than native — it's a side-only proxy.

Statistical guards (don't lie about the data):
  * Per-bucket N, WR, avg_pnl, median_pnl, sum_pnl, MFE/MAE not computed here.
  * Wilson 95% CI for WR.
  * INSUFFICIENT label when N<10 in a bucket.
  * NO_CONCLUSION label for the entire view when total N<20.
  * Optional: filter by phase_tag (LIVE-2H clean subset).
  * Optional: exclude sandbox-pause artefacts from PHASE_STATE.md.
  * Read-only against MongoDB. Writes only:
        /tmp/forensic_live3b_report.md
        /tmp/forensic_live3b.jsonl

Usage:
  python3 /app/scripts/forensic_live3b_conf_buckets.py
  python3 /app/scripts/forensic_live3b_conf_buckets.py --phase LIVE-2H
  python3 /app/scripts/forensic_live3b_conf_buckets.py --strategy SIMPLE_MA \
      --exclude-pause-artefacts --min-n 10
"""
from __future__ import annotations

import argparse
import json
import math
import os
import statistics
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from pymongo import MongoClient

# ---------------------------------------------------------------------------
# Defaults — must match modules/execution/bridge.py:_CONF_ADJ_DEFAULTS
# ---------------------------------------------------------------------------
SHORT_SIDE_MULT = 0.80
LONG_UPTREND_MULT = 0.85
BASE_CONF = 0.60  # SimpleMA flat upstream confidence

# Bucket bounds: [lower, upper). Final bucket is open-ended at top.
BUCKETS: List[Tuple[float, float, str]] = [
    (0.00, 0.45, "<0.45"),
    (0.45, 0.50, "[0.45-0.50)"),
    (0.50, 0.55, "[0.50-0.55)"),
    (0.55, 0.60, "[0.55-0.60)"),
    (0.60, 1.01, "[0.60+]"),
]

MIN_BUCKET_N = 10
MIN_TOTAL_N = 20

PAUSE_ARTEFACTS = {"case-3cbabe9b6d08", "case-e9c8f0d50298"}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _bucket_label(value: float) -> str:
    for lo, hi, label in BUCKETS:
        if lo <= value < hi:
            return label
    return BUCKETS[-1][2]


def _adjust_retro(side: str, regime: Optional[str] = None) -> Tuple[float, Dict[str, Any]]:
    """Reconstruct adjusted_confidence purely from side (and regime if known).
    Mirrors bridge.py:_adjust_confidence math with defaults.
    """
    side_u = (side or "").upper()
    is_short = side_u in ("SELL", "SHORT")
    is_long = side_u in ("BUY", "LONG")

    side_mult = SHORT_SIDE_MULT if is_short else 1.0
    regime_u = (regime or "").upper() if regime else None
    regime_mult = LONG_UPTREND_MULT if (is_long and regime_u == "UPTREND") else 1.0

    adj = max(0.05, min(BASE_CONF * side_mult * regime_mult, 0.95))
    return adj, {
        "base": BASE_CONF,
        "side_multiplier": side_mult,
        "regime_multiplier": regime_mult,
        "adjusted": round(adj, 4),
        "regime_observed": regime_u,
    }


def _wilson_interval(wins: int, n: int, z: float = 1.96) -> Tuple[float, float]:
    if n == 0:
        return (0.0, 0.0)
    p = wins / n
    denom = 1 + z * z / n
    centre = p + z * z / (2 * n)
    margin = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    lo = (centre - margin) / denom
    hi = (centre + margin) / denom
    return (max(0.0, lo), min(1.0, hi))


# ---------------------------------------------------------------------------
# Data load
# ---------------------------------------------------------------------------
def _load_closed_cases(
    db, strategy: Optional[str], exclude_artefacts: bool
) -> List[Dict[str, Any]]:
    q: Dict[str, Any] = {"status": "CLOSED", "realized_pnl_pct": {"$ne": None}}
    if strategy:
        q["strategy"] = strategy
    if exclude_artefacts:
        q["case_id"] = {"$nin": list(PAUSE_ARTEFACTS)}

    proj = {
        "_id": 0,
        "case_id": 1, "side": 1, "strategy": 1, "symbol": 1,
        "opened_at": 1, "closed_at": 1, "realized_pnl_pct": 1,
        "decision_id": 1, "experiment_id": 1, "phase_tag": 1,
    }
    return list(db["trading_cases"].find(q, proj).sort("opened_at", 1))


def _load_phase_map(db, case_ids: List[str]) -> Dict[str, str]:
    """case_id → phase tag derived from latest POSITION_CLOSED event.

    The `phase` field in position_exit_events only carries the broad family
    ('LIVE-2'). The fine-grained sub-phase (LIVE-2 / LIVE-2D / LIVE-2H) is
    encoded in `close_reason`:
        LIVE2_*   → LIVE-2  (pre-tightening baseline)
        LIVE2D_*  → LIVE-2D (TP/SL ±0.15% experiment, edge destroyed)
        LIVE2H_*  → LIVE-2H (TP/SL ±0.30% baseline regression — current)
    """
    if not case_ids:
        return {}

    def _derive(reason: Optional[str], fallback: Optional[str]) -> str:
        r = (reason or "").upper()
        if r.startswith("LIVE2H"):
            return "LIVE-2H"
        if r.startswith("LIVE2D"):
            return "LIVE-2D"
        if r.startswith("LIVE2_"):
            return "LIVE-2"
        return fallback or "UNKNOWN"

    out: Dict[str, str] = {}
    cur = db["position_exit_events"].find(
        {"case_id": {"$in": case_ids}, "event": "POSITION_CLOSED"},
        {"_id": 0, "case_id": 1, "phase": 1, "closed_at": 1, "rule": 1, "close_reason": 1},
    ).sort("closed_at", -1)
    for ev in cur:
        cid = ev.get("case_id")
        if cid and cid not in out:
            out[cid] = _derive(ev.get("close_reason"), ev.get("phase"))
    return out


def _load_native_payload_map(db, decision_ids: List[str]) -> Dict[str, Dict[str, Any]]:
    """decision_id → {adjusted_confidence, base_confidence, regime_at_entry,
    confidence_breakdown}. Read from execution_jobs.payload. Empty for trades
    created before LIVE-3a deploy.
    """
    if not decision_ids:
        return {}
    cur = db["execution_jobs"].find(
        {
            "payload.decision_id": {"$in": decision_ids},
            "payload.adjusted_confidence": {"$exists": True},
        },
        {
            "_id": 0,
            "payload.decision_id": 1,
            "payload.adjusted_confidence": 1,
            "payload.base_confidence": 1,
            "payload.regime_at_entry": 1,
            "payload.confidence_breakdown": 1,
        },
    )
    out: Dict[str, Dict[str, Any]] = {}
    for j in cur:
        p = j.get("payload") or {}
        did = p.get("decision_id")
        if did:
            out[did] = {
                "adjusted_confidence": p.get("adjusted_confidence"),
                "base_confidence": p.get("base_confidence"),
                "regime_at_entry": p.get("regime_at_entry"),
                "confidence_breakdown": p.get("confidence_breakdown"),
            }
    return out


# ---------------------------------------------------------------------------
# Bucketing
# ---------------------------------------------------------------------------
def _bucket(rows: List[Dict[str, Any]], min_n: int) -> List[Dict[str, Any]]:
    """Return bucket summaries (in BUCKETS order)."""
    by_label: Dict[str, List[Dict[str, Any]]] = {b[2]: [] for b in BUCKETS}
    for r in rows:
        by_label[r["bucket"]].append(r)

    summary = []
    for _, _, label in BUCKETS:
        members = by_label[label]
        n = len(members)
        if n == 0:
            summary.append(
                {"bucket": label, "n": 0, "wins": 0, "wr": None,
                 "wr_ci_lo": None, "wr_ci_hi": None,
                 "avg_pnl": None, "median_pnl": None, "sum_pnl": None,
                 "long_n": 0, "short_n": 0, "insufficient": True}
            )
            continue
        pnls = [r["realized_pnl_pct"] for r in members]
        wins = sum(1 for p in pnls if p > 0)
        long_n = sum(1 for r in members if r["side"].upper() in ("LONG", "BUY"))
        short_n = sum(1 for r in members if r["side"].upper() in ("SHORT", "SELL"))
        wr = wins / n
        ci_lo, ci_hi = _wilson_interval(wins, n)
        summary.append({
            "bucket": label,
            "n": n, "wins": wins, "wr": round(wr, 4),
            "wr_ci_lo": round(ci_lo, 4), "wr_ci_hi": round(ci_hi, 4),
            "avg_pnl": round(statistics.mean(pnls), 4),
            "median_pnl": round(statistics.median(pnls), 4),
            "sum_pnl": round(sum(pnls), 4),
            "long_n": long_n, "short_n": short_n,
            "insufficient": n < min_n,
        })
    return summary


def _by_side(rows: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    out: Dict[str, Dict[str, Any]] = {}
    for side_label in ("LONG", "SHORT"):
        canon = ("LONG", "BUY") if side_label == "LONG" else ("SHORT", "SELL")
        members = [r for r in rows if r["side"].upper() in canon]
        n = len(members)
        if n == 0:
            out[side_label] = {"n": 0}
            continue
        pnls = [r["realized_pnl_pct"] for r in members]
        wins = sum(1 for p in pnls if p > 0)
        ci_lo, ci_hi = _wilson_interval(wins, n)
        out[side_label] = {
            "n": n, "wins": wins,
            "wr": round(wins / n, 4),
            "wr_ci": [round(ci_lo, 4), round(ci_hi, 4)],
            "avg_pnl": round(statistics.mean(pnls), 4),
            "median_pnl": round(statistics.median(pnls), 4),
        }
    return out


def _by_phase(rows: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    out: Dict[str, Dict[str, Any]] = {}
    phases = sorted({r.get("phase") or "UNKNOWN" for r in rows})
    for phase in phases:
        members = [r for r in rows if (r.get("phase") or "UNKNOWN") == phase]
        n = len(members)
        pnls = [r["realized_pnl_pct"] for r in members]
        wins = sum(1 for p in pnls if p > 0)
        ci_lo, ci_hi = _wilson_interval(wins, n)
        out[phase] = {
            "n": n, "wins": wins,
            "wr": round(wins / n, 4) if n else None,
            "wr_ci": [round(ci_lo, 4), round(ci_hi, 4)],
            "avg_pnl": round(statistics.mean(pnls), 4) if pnls else None,
            "median_pnl": round(statistics.median(pnls), 4) if pnls else None,
        }
    return out


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------
def _fmt_pnl(value: Optional[float]) -> str:
    """realized_pnl_pct is stored in raw percent units (e.g. 0.0952 == 0.0952%)."""
    if value is None:
        return "—"
    return f"{value:+.4f}%"


def _fmt_wr(b: Dict[str, Any]) -> str:
    if b.get("wr") is None:
        return "—"
    return (
        f"{b['wr'] * 100:5.1f}%  "
        f"[{b['wr_ci_lo'] * 100:.1f}, {b['wr_ci_hi'] * 100:.1f}]"
    )


def _bucket_table(title: str, view: str, summary: List[Dict[str, Any]],
                  total_n: int) -> str:
    lines: List[str] = []
    lines.append(f"### {title}  (view={view}, total N={total_n})")
    if total_n < MIN_TOTAL_N:
        lines.append(
            f"\n> ⚠ NO_CONCLUSION: total N={total_n} < {MIN_TOTAL_N}. "
            "Numbers are descriptive, not statistically significant."
        )
    lines.append("")
    lines.append(
        "| bucket       | N  | LONG | SHORT | WR     | WR 95% CI       "
        "| avg PnL    | median PnL | sum PnL  | flag |"
    )
    lines.append(
        "|--------------|----|------|-------|--------|------------------"
        "|------------|------------|----------|------|"
    )
    for b in summary:
        if b["n"] == 0:
            lines.append(
                f"| {b['bucket']:<12} |  0 |   0  |   0   | —      | —"
                f"               | —          | —          | —        | EMPTY |"
            )
            continue
        flag = "INSUFFICIENT" if b["insufficient"] else "ok"
        lines.append(
            f"| {b['bucket']:<12} | {b['n']:>2} | {b['long_n']:>4} | "
            f"{b['short_n']:>5} | {b['wr'] * 100:5.1f}% | "
            f"[{b['wr_ci_lo']*100:5.1f}, {b['wr_ci_hi']*100:5.1f}]"
            f" | {_fmt_pnl(b['avg_pnl'])} | {_fmt_pnl(b['median_pnl'])} | "
            f"{_fmt_pnl(b['sum_pnl'])} | {flag} |"
        )
    return "\n".join(lines)


def _side_table(by_side: Dict[str, Dict[str, Any]]) -> str:
    lines = ["### Per-side sanity"]
    lines.append("")
    lines.append("| side  | N  | WR     | WR 95% CI         | avg PnL    | median PnL |")
    lines.append("|-------|----|--------|-------------------|------------|------------|")
    for side in ("LONG", "SHORT"):
        b = by_side.get(side, {})
        if not b or b.get("n", 0) == 0:
            lines.append(f"| {side:<5} |  0 | —      | —                 | —          | —          |")
            continue
        lo, hi = b.get("wr_ci", [0.0, 0.0])
        lines.append(
            f"| {side:<5} | {b['n']:>2} | {b['wr'] * 100:5.1f}% | "
            f"[{lo * 100:5.1f}, {hi * 100:5.1f}] | "
            f"{_fmt_pnl(b['avg_pnl'])} | {_fmt_pnl(b['median_pnl'])} |"
        )
    return "\n".join(lines)


def _phase_table(by_phase: Dict[str, Dict[str, Any]]) -> str:
    lines = ["### Per-phase breakdown"]
    lines.append("")
    lines.append("| phase     | N  | WR     | WR 95% CI         | avg PnL    | median PnL |")
    lines.append("|-----------|----|--------|-------------------|------------|------------|")
    for phase, b in by_phase.items():
        if b["n"] == 0:
            continue
        lo, hi = b.get("wr_ci", [0.0, 0.0])
        lines.append(
            f"| {phase:<9} | {b['n']:>2} | {b['wr'] * 100:5.1f}% | "
            f"[{lo * 100:5.1f}, {hi * 100:5.1f}] | "
            f"{_fmt_pnl(b['avg_pnl'])} | {_fmt_pnl(b['median_pnl'])} |"
        )
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--strategy", default="SIMPLE_MA",
                        help="filter by strategy name (default SIMPLE_MA)")
    parser.add_argument("--phase", default=None,
                        help="filter to specific phase (e.g. LIVE-2H)")
    parser.add_argument("--exclude-pause-artefacts", action="store_true",
                        help="drop sandbox-pause artefacts from PHASE_STATE.md")
    parser.add_argument("--min-n", type=int, default=MIN_BUCKET_N,
                        help=f"min N per bucket to mark as ok (default {MIN_BUCKET_N})")
    args = parser.parse_args()

    min_n = args.min_n

    mongo_url = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
    db_name = os.environ.get("DB_NAME", "trading_os")
    client = MongoClient(mongo_url, serverSelectionTimeoutMS=3000)
    db = client[db_name]

    print(f"[forensic-live3b] DB={db_name}")
    cases = _load_closed_cases(db, args.strategy, args.exclude_pause_artefacts)
    print(f"[forensic-live3b] loaded {len(cases)} closed cases (strategy={args.strategy})")

    # join phase
    phase_map = _load_phase_map(db, [c["case_id"] for c in cases])
    for c in cases:
        c["phase"] = phase_map.get(c["case_id"])

    if args.phase:
        cases = [c for c in cases if c.get("phase") == args.phase]
        print(f"[forensic-live3b] after phase filter '{args.phase}': N={len(cases)}")

    # native payload (LIVE-3a populated execution_jobs)
    native_map = _load_native_payload_map(
        db, [c["decision_id"] for c in cases if c.get("decision_id")]
    )
    print(f"[forensic-live3b] native payload coverage: "
          f"{len(native_map)}/{len(cases)}")

    # bucket assignments — both views
    rows_native: List[Dict[str, Any]] = []
    rows_retro: List[Dict[str, Any]] = []

    for c in cases:
        side = c["side"]
        pnl = c.get("realized_pnl_pct")
        if pnl is None:
            continue

        # NATIVE
        native = native_map.get(c.get("decision_id") or "")
        if native and native.get("adjusted_confidence") is not None:
            adj_n = float(native["adjusted_confidence"])
            rows_native.append({
                "case_id": c["case_id"], "side": side, "phase": c.get("phase"),
                "realized_pnl_pct": pnl,
                "adjusted_confidence": adj_n,
                "regime_at_entry": native.get("regime_at_entry"),
                "bucket": _bucket_label(adj_n),
                "source": "native",
            })

        # RETRO (always — proxy)
        adj_r, breakdown = _adjust_retro(side, regime=None)  # regime unknown
        rows_retro.append({
            "case_id": c["case_id"], "side": side, "phase": c.get("phase"),
            "realized_pnl_pct": pnl,
            "adjusted_confidence": adj_r,
            "regime_at_entry": None,
            "breakdown": breakdown,
            "bucket": _bucket_label(adj_r),
            "source": "retro",
        })

    # write per-trade jsonl
    out_jsonl = "/tmp/forensic_live3b.jsonl"
    with open(out_jsonl, "w", encoding="utf-8") as fh:
        for r in rows_native + rows_retro:
            fh.write(json.dumps(r, default=str) + "\n")

    # summaries
    summary_native = _bucket(rows_native, min_n)
    summary_retro = _bucket(rows_retro, min_n)
    side_native = _by_side(rows_native)
    side_retro = _by_side(rows_retro)
    phase_retro = _by_phase(rows_retro)

    # report
    now = datetime.now(timezone.utc).isoformat()
    title = (
        f"# LIVE-3b — Confidence Bucket Forensic\n\n"
        f"_generated {now}; strategy={args.strategy}; "
        f"phase_filter={args.phase or 'ALL'}; "
        f"exclude_pause_artefacts={args.exclude_pause_artefacts}; "
        f"min_bucket_n={min_n}_\n"
    )
    parts: List[str] = [title]

    parts.append("## NATIVE view (uses payload.adjusted_confidence)")
    parts.append(
        "Honest caveat: native field exists only for trades created after the "
        "LIVE-3a deploy. Until enough trades accumulate (target N≥20), this "
        "view is **NO_CONCLUSION** by construction."
    )
    parts.append("")
    parts.append(_bucket_table("Confidence buckets — NATIVE",
                               "native", summary_native, len(rows_native)))
    parts.append("")
    parts.append(_side_table(side_native))

    parts.append("\n## RETRO view (side-only reconstruction)")
    parts.append(
        "Honest caveat: this collapses 5 buckets into 2 effective values "
        f"(LONG → {BASE_CONF}, SHORT → {round(BASE_CONF * SHORT_SIDE_MULT, 2)}) "
        "because historical `regime_at_entry` was not stored. It cannot test "
        "the LONG/UPTREND penalty hypothesis. It can only test the side-only "
        "ranking signal."
    )
    parts.append("")
    parts.append(_bucket_table("Confidence buckets — RETRO",
                               "retro", summary_retro, len(rows_retro)))
    parts.append("")
    parts.append(_side_table(side_retro))
    parts.append("")
    parts.append(_phase_table(phase_retro))

    parts.append("\n## How to read this")
    parts.append(
        "- If RETRO buckets show monotonic improvement (lower→worse, higher→"
        "better) AND CIs don't overlap, the side multiplier carries signal.\n"
        "- If RETRO is monotonic but CIs overlap, the layer is suggestive but "
        "needs more N before tightening the gate.\n"
        "- If RETRO is flat or inverted, the side multiplier alone is not "
        "enough — need next slice (volatility / time-of-day / signal "
        "strength) before tightening.\n"
        "- NATIVE view supersedes RETRO once N≥20."
    )
    parts.append(
        "\n**Strict rule:** do NOT change `min_adjusted_confidence` "
        "based on this report alone unless RETRO total N≥20 AND lowest "
        "bucket WR is at least 10pp below the highest bucket WR with "
        "non-overlapping Wilson CIs."
    )

    report = "\n".join(parts)
    out_md = "/tmp/forensic_live3b_report.md"
    with open(out_md, "w", encoding="utf-8") as fh:
        fh.write(report)

    # stdout digest
    print()
    print("=" * 78)
    print("LIVE-3b CONFIDENCE BUCKET FORENSIC — digest")
    print("=" * 78)
    print(f"strategy={args.strategy} phase={args.phase or 'ALL'} "
          f"exclude_artefacts={args.exclude_pause_artefacts}")
    print(f"NATIVE rows={len(rows_native)}   RETRO rows={len(rows_retro)}")
    print()
    print("--- RETRO buckets ---")
    for b in summary_retro:
        if b["n"] == 0:
            continue
        flag = "INSUFFICIENT" if b["insufficient"] else "ok"
        print(
            f"  {b['bucket']:<12}  N={b['n']:<2}  "
            f"L={b['long_n']:<2}  S={b['short_n']:<2}  "
            f"WR={b['wr'] * 100:5.1f}%  "
            f"CI=[{b['wr_ci_lo'] * 100:5.1f},{b['wr_ci_hi'] * 100:5.1f}]  "
            f"avg={b['avg_pnl']:+.4f}%  "
            f"med={b['median_pnl']:+.4f}%  "
            f"[{flag}]"
        )
    print()
    print(f"report  → {out_md}")
    print(f"per-trade → {out_jsonl}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
