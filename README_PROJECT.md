# Trading Terminal — Quick Reference

A FastAPI + React + MongoDB live trading terminal with regime-gated SimpleMA
strategy, automated TP/SL/Time exits, and a strict R&D cadence:
*"every architectural change is decided after a forensic on real trades"*.

---

## TL;DR — current phase

The system is in **Phase LIVE-2H** (baseline regression).
Read [`PHASE_STATE.md`](./PHASE_STATE.md) for the canonical state document.

Latest result: **clean N=13, WR=53.8%, Avg PnL=+0.006%**. Baseline
tentatively recovered, awaiting architect's next directive.

---

## Quick start (fresh deploy / fork)

```bash
# Restore the LIVE-2H state and start observers + watchdog.
bash /app/scripts/bootstrap_live2h.sh

# One-shot status snapshot
python3 /app/scripts/observe_live2h.py

# Full forensic on every closed trade (read-only)
python3 /app/scripts/forensic_v2_mfe_mae.py
```

If something hits an unexpected state, read:

```bash
cat /app/PHASE_STATE.md
```

---

## Architecture

```
backend/                          FastAPI app
├── server.py                     # entry point; spawns daemons in lifespan
└── modules/
    ├── signal_generator/         # SIMPLE_MA — emits BUY/SELL signals
    ├── regime/                   # EMA20/50 detector + control flags
    ├── execution/bridge.py       # gates signals, routes to exec queue
    ├── positions/
    │   ├── mark_price_updater.py # daemon: refresh mark + PnL every 8s
    │   └── position_exit_manager.py  # daemon: enforce TP/SL/Time
    └── trading_cases/            # MongoDB-backed case repository

frontend/                         React + Tailwind UI
└── src/components/terminal/      # CaseRailCompact, PnL, charts

scripts/                          R&D / live observation tooling
├── bootstrap_live2h.sh           # one-shot deploy/resume entry
├── restore_snapshot.py           # load JSONL → Mongo
├── snapshot_live2h.py            # capture current LIVE-2H state
├── observe_live2h.py             # 60s polling status
├── watchdog_live2h_v2.py         # early-pattern alarms (3xSL / 3xTP / pause)
├── forensic_mfe_mae.py           # v1: MFE/MAE per closed case
└── forensic_v2_mfe_mae.py        # v2: + MFE(t) timeline per case

data_snapshots/
├── latest/                       # base DB snapshot (pre-LIVE-2H)
└── live2h/                       # overlay snapshot (current phase)
```

---

## Phase glossary

| Phase | TP/SL | Gates | WR | Avg PnL% | Verdict |
|---|---|---|---|---|---|
| LIVE-2 | ±0.30% | OFF | 53.8% | +0.0514 | original baseline (worked) |
| LIVE-2D | ±0.15% | ON | 31.8% | -0.0437 | tightening killed edge |
| LIVE-2H | ±0.30% | OFF | 53.8% | +0.0059 | **current** — baseline regression test |

---

## Process discipline

This project follows a strict *architect-led* R&D loop:

1. **No code changes without forensic justification.** Every modification of
   `SimpleMA`, `RegimeDetector`, or exit thresholds is preceded by a
   read-only diagnostic on closed trades.
2. **PnL is the only source of truth.** All hypotheses are tested
   against the `trading_cases.realized_pnl_pct` column with explicit
   N, WR, MFE, MAE.
3. **Phase tagging.** Every change of TP/SL/gate state earns a new
   phase tag (`LIVE2_*`, `LIVE2D_*`, `LIVE2H_*`) so historical samples
   stay separable.

---

## Key environment variables

```bash
MONGO_URL=mongodb://localhost:27017
DB_NAME=trading_os                 # canonical DB
REACT_APP_BACKEND_URL=…            # set in frontend/.env (managed)
```

---

## Restore from snapshot manually

```bash
# Restore base (only into empty collections)
python3 scripts/restore_snapshot.py \
    --snapshot data_snapshots/latest --mode base

# Overlay LIVE-2H state (regime_controls + trades)
python3 scripts/restore_snapshot.py \
    --snapshot data_snapshots/live2h --mode overlay

# Take a fresh snapshot of the current state
python3 scripts/snapshot_live2h.py
```
