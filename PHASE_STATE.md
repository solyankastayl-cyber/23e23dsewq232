# PHASE_STATE.md — Trading Terminal — current phase

> **This file is the canonical source of truth for the project's current R&D phase.**
> When resuming work, read this first.

---

## Current phase: **LIVE-2H** (baseline regression)

**Started**: 2026-04-25 14:41 UTC
**Architect verdict (last)**: baseline tentatively recovered (N=13)

### Configuration

| Parameter | Value | Where |
|---|---|---|
| Take-profit (TP) | **+0.30%** | `backend/modules/positions/position_exit_manager.py` (`TP_PCT`) |
| Stop-loss (SL) | **−0.30%** | `backend/modules/positions/position_exit_manager.py` (`SL_PCT`) |
| Time exit | 30 min | `backend/modules/positions/position_exit_manager.py` (`TIME_EXIT_MIN`) |
| Phase tag | `LIVE2H_*_030` | hardcoded in `_evaluate_exit()` |
| `regime_controls.long_uptrend_only` | **False** (disabled) | MongoDB `trading_os.regime_controls` |
| `regime_controls.short_downtrend_only` | **False** (disabled) | MongoDB `trading_os.regime_controls` |
| `regime_controls.short_trading_enabled` | True | MongoDB |
| Strategy | `SIMPLE_MA` (unchanged) | `backend/modules/signal_generator/simple_ma.py` |
| Regime detector | EMA20/50 on 1h (unchanged, **bypassed** by gates-off) | `backend/modules/regime/market_regime.py` |

### Why this configuration

Forensic on 48 historical trades (`forensic_mfe_mae.py`) revealed:

1. Tightening TP/SL from ±0.30% → ±0.15% (LIVE-2D) destroyed positive
   edge — WR fell 53.8% → 31.8%, Avg PnL flipped +0.05% → −0.03%.
2. The regime gate was **inverted**: LONG in UPTREND yielded WR=31% vs
   LONG in DOWNTREND/RANGE yielded WR=50%.

Architect directive: **revert to baseline (TP/SL=±0.30%, gates OFF), keep
SimpleMA untouched, observe live for clean N≥10 to verify baseline edge.**

---

## Latest data (LIVE-2H clean subset)

```
N_clean       = 13
N_excluded    = 2  (sandbox-pause artefacts: case-3cbabe9b6d08, case-e9c8f0d50298)
WR            = 53.8%   (7W / 6L)
Avg PnL%      = +0.0059
Sum PnL%      = +0.0761
Avg MFE%      = +0.0677
Avg MAE%      = +0.0600
Exit rule mix = 13× TIME_EXIT, 0× TP, 0× SL
```

**Per-side**:

| Side | N | WR | Avg PnL% |
|---|---|---|---|
| LONG | 10 | 60.0% | +0.0060 |
| SHORT | 3 | 33.3% | +0.0054 |

**Verdict (per architect's PASS/FAIL framework)**:
- ✅ WR ≥ 45-50% → 53.8% PASS
- ✅ Avg PnL ≥ 0 → +0.0059% PASS (barely)
- ⚠️ TP ≥ SL → 0/0 — neither dominates (extreme FLAT_NO_MOVE market)

**Caveat**: 11/13 trades classified as FLAT_NO_MOVE (MFE never reached
0.10%). The system is profitable in this regime only because TIME_EXIT
is randomly slightly positive on average. The market itself is the
bottleneck — bands of ±0.30% are unreachable in the current 30-min
volatility envelope.

---

## Pending tasks (in priority order)

| ID | Task | Status |
|---|---|---|
| **A** | Restore baseline (TP/SL=±0.30%, gates OFF, SimpleMA untouched) | ✅ DONE |
| **C** | MFE(t) timeline forensic on TIME_KILL cluster | ✅ DONE |
| **NEXT-1** | Decide: enrich with longer TIME (60-90m) for the 33% RISING_LINEAR cluster vs add activity filter (skip entries when 1m volatility < threshold) | 🟡 BLOCKED on architect |
| **NEXT-2** | Re-run forensic_v2 once N_clean reaches 25-30 to derive stable per-side and per-regime edge | 🟢 PENDING (auto: keep observer running) |

**Strict prohibitions** still in force:
- ❌ Do NOT change SimpleMA entry logic
- ❌ Do NOT add new strategies
- ❌ Do NOT reactivate regime gates without architect's approval
- ❌ Do NOT touch UI (Decisions tab / Prediction overlay paused)

---

## Quick start (after fresh deploy / fork resume)

```bash
# 1. Restore environment + LIVE-2H state + start observers
bash /app/scripts/bootstrap_live2h.sh

# 2. Verify
python3 /app/scripts/observe_live2h.py             # snapshot
cat /app/PHASE_STATE.md                            # this file

# 3. Run forensic at any point (pure read-only)
python3 /app/scripts/forensic_v2_mfe_mae.py
cat /tmp/forensic_v2_report.md
```

If a fresh fork has an empty database, the bootstrap will:
1. Restore base data from `data_snapshots/latest/` (only if Mongo is empty).
2. Overlay LIVE-2H specific docs from `data_snapshots/live2h/`.
3. Restart backend so `position_exit_manager` reloads TP/SL=0.30%.
4. Start observer + watchdog v2 in background.

---

## Files added during LIVE-2H phase

```
scripts/
├── bootstrap_live2h.sh         # one-shot deploy / resume entrypoint
├── restore_snapshot.py         # used by bootstrap to load JSONL → Mongo
├── snapshot_live2h.py          # take a fresh LIVE-2H snapshot
├── observe_live2h.py           # snapshot every 60s → /tmp
├── watchdog_live2h_v2.py       # detects 3xSL / 3xTP / sandbox pause; auto-stops at clean N≥10
├── watchdog_live2h.py          # v1, kept for reference
├── forensic_mfe_mae.py         # v1 forensic (MFE/MAE per closed trade)
└── forensic_v2_mfe_mae.py      # v2 with MFE(t) timeline 1/5/10/20/30 min

data_snapshots/
├── latest/                     # base snapshot (pre-LIVE-2H, ~6 MB)
└── live2h/                     # overlay: regime_controls + LIVE-2H trades + audit
    ├── manifest.json
    ├── regime_controls.jsonl   # 4 docs (gates OFF state)
    ├── trading_cases.jsonl     # 15 LIVE-2H docs (13 clean + 2 excluded)
    ├── regime_guard_events.jsonl
    └── position_exit_events.jsonl
```

---

## Modified files during LIVE-2H phase

| File | Change |
|---|---|
| `backend/modules/positions/position_exit_manager.py` | TP/SL: ±0.15% → ±0.30%; phase tag → `LIVE2H_*_030` |

**No other production code was touched.** `SimpleMA`, `RegimeDetector`,
`ExecutionBridge`, `MarkUpdater` remain bit-identical to the start of the
phase.
