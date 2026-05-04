# TA Prediction Intelligence — Architecture Map (for next R&D)

> Created: 2026-05-04
> Purpose: Canonical map of the TA (Technical Analysis) block for the upcoming
> R&D iteration. **Target of work: TA prediction logic, NOT trading/execution.**

---

## 1) Module layout

```
backend/modules/ta_prediction_intelligence/
├── ta_prediction_routes.py          # REST entry point for prediction surface
│                                      (/api/ta-prediction-intelligence/*)
├── ta_prediction_service.py         # top-level orchestrator
├── ta_prediction_aggregator.py      # combines signals from engines
├── ta_prediction_conflict_resolver.py # resolves bull/bear conflicts
├── step7_pipeline.py                # Step 7: probability calibration
├── live_adapter.py                  # TA Engine ↔ predictions bridge
├── repository.py                    # Mongo persistence
├── types.py                         # Pydantic models / contracts
├── engine_interactions.py           # Step 6: engine interaction modeling
│
├── engines/                         # Per-domain prediction engines (Step ≤6)
│   ├── level_zone_prediction_engine.py
│   ├── momentum_prediction_engine.py
│   ├── pattern_prediction_engine.py
│   ├── structure_prediction_engine.py
│   └── volatility_prediction_engine.py
│
├── calibration/                     # Step 7 calibration store
│   ├── calibration_engine.py
│   └── calibration_store.py
│
├── decision_intelligence/           # Step 12 decision layer
│   ├── alignment_engine.py
│   ├── decision_builder.py
│   ├── decision_classifier.py
│   ├── dominance_engine.py
│   ├── risk_engine.py
│   ├── scenario_selector.py
│   └── types.py
│
├── scenarios/                       # Step 12 winning scenario builder
│   ├── scenario_builder.py
│   ├── scenario_calibration_adjuster.py
│   └── scenario_interaction_adjuster.py
│
├── learning/                        # Step 8: features + ring buffer
│   ├── dataset_builder.py
│   ├── feature_builder.py
│   ├── feature_hash.py
│   ├── feature_schema.py            # 82 features v1
│   ├── price_action.py
│   ├── state_machine.py
│   ├── temporal_buffer.py
│   └── trainer_contracts.py
├── learning_routes.py               # /api/ta-prediction-intelligence/{features,buffer,dataset}
│
├── debug/                           # Step 9: debug/tracing layer
│   ├── metrics.py
│   ├── repository.py
│   ├── root_cause.py
│   ├── service.py
│   └── taxonomy.py
├── debug_routes.py                  # /api/ta-prediction-intelligence/debug/*
│
├── data_health/                     # Step 11: data-health gate
│   ├── drift_checks.py
│   ├── health_checks.py
│   ├── health_routes.py
│   ├── health_service.py
│   ├── trust_score.py
│   └── types.py
│
├── ml_readiness/                    # Gate for ML training (n_evaluated ≥ 500)
│   ├── readiness_metrics.py
│   ├── readiness_routes.py
│   ├── readiness_score.py
│   ├── readiness_service.py
│   └── types.py
│
├── temporal_intelligence/           # Step 10: dataset builder + temporal context
│   ├── persistence.py
│   ├── regime_memory.py
│   ├── sequence_patterns.py
│   ├── state_evolution.py
│   ├── temporal_context_builder.py
│   ├── transition_pressure.py
│   └── types.py
│
├── root_cause_aggregator/           # Aggregated weakness diagnostics
│   ├── aggregator_service.py
│   ├── cohort_builder.py
│   ├── concentration.py
│   ├── root_cause_routes.py
│   ├── stability.py
│   └── weakness_detector.py
│
├── simulation/                      # Backtesting / replay
│   ├── no_lookahead.py
│   ├── replay_engine.py
│   ├── simulation_repository.py
│   ├── simulation_routes.py
│   └── simulation_service.py
│
└── evaluation/
    └── ta_prediction_outcome_worker.py   # resolves pending→evaluated
```

---

## 2) REST entry points (top level — `/api/ta-prediction-intelligence/*`)

### Core prediction surface (`ta_prediction_routes.py`)
| Method | Path | Purpose |
|---|---|---|
| GET | `/health` | liveness of the TA prediction subsystem |
| GET | `/live` | current live prediction (carries Step 6/7/8/10/12 fields) |
| POST | `/from-setup` | build prediction from a TA setup payload |
| POST | `/from-typed` | build prediction from a typed input (Pydantic) |
| GET | `/history` | paginated prediction history (pending/evaluated) |
| GET | `/calibration` | current Step-7 buckets |
| GET | `/calibration/diagnostics` | calibration quality summary (Brier, N) |
| POST | `/calibration/rebuild` | recompute all buckets from history |
| GET | `/outcome_worker/status` | Step-7/8 worker liveness + stats |

### Learning (`learning_routes.py`)
| Method | Path | Purpose |
|---|---|---|
| GET | `/features/schema` | Step-8 feature v1 schema (82 features) |
| GET | `/features/preview` | preview features for a symbol/bar |
| GET | `/buffer/status` | Step-8 ring-buffer status |
| GET | `/dataset/preview` | Step-10 dataset preview |
| GET | `/dataset/stats` | dataset counters (scanned / written / failed) |
| POST | `/dataset/rebuild` | rebuild Step-10 dataset from history |

### Debug layer (`debug_routes.py`)
| Method | Path | Purpose |
|---|---|---|
| GET | `/debug/preview` | summary of debug envelope for recent predictions |
| GET | `/debug/stats` | taxonomy stats |
| GET | `/debug/case/{prediction_id}` | full debug trace for one prediction |
| POST | `/debug/rebuild` | recompute debug for existing predictions |

### Other surfaces (mounted under the same prefix or siblings)
- `data_health/health_routes.py` — trust score, drift checks
- `ml_readiness/readiness_routes.py` — ML gate (n_evaluated ≥ 500)
- `root_cause_aggregator/root_cause_routes.py` — cohort-level weakness analysis
- `simulation/simulation_routes.py` — replay / backtest engine

---

## 3) Pipeline — Step 6 → 7 → 8/9 → 10 → 11 → 12

| Step | Name | Responsibility | Primary code |
|---|---|---|---|
| 6 | Engine Interactions | Pair-wise score modelling across engines | `engine_interactions.py`, `engines/` |
| 7 | Calibration | Probability calibration per bucket (`interaction_type`, `dominant_engine`, `symbol_tf`, `symbol_tf_interaction`) | `step7_pipeline.py`, `calibration/` |
| 8 | Features v1 + Buffer | 82 features, deterministic hashes, ring buffer | `learning/`, `learning_routes.py` |
| 9 | Debug Layer | Trace envelope + taxonomy + root cause | `debug/`, `debug_routes.py` |
| 10 | Dataset Builder | Temporal context → ML-ready dataset | `temporal_intelligence/`, `learning/dataset_builder.py` |
| 11 | Data Health Gate | Trust score, drift checks, n≥500 gate | `data_health/`, `ml_readiness/` |
| 12 | Decision Intelligence | Winning scenario → final decision (primary, strength, conf) | `decision_intelligence/`, `scenarios/` |

Supplementary:
- `evaluation/ta_prediction_outcome_worker.py` — pending → evaluated transitions
  (inputs for Step 7 calibration).
- `root_cause_aggregator/` — post-hoc weakness analysis / cohorts.
- `simulation/` — replay engine with no-lookahead guards (for future backtests).

---

## 4) Persistence (MongoDB — `trading_os`)

| Collection | Owner step | Contents |
|---|---|---|
| `ta_prediction_history` | Steps 6–12 | envelope per prediction (includes features_v1, calibration, debug, decision) |
| `ta_prediction_temporal_buffer` | Step 8 | ring buffer of recent predictions (stable shape) |
| `ta_prediction_calibration` | Step 7 | bucket counters and Brier metrics |
| `ta_prediction_dataset` | Step 10 | ML-ready records |
| `ta_prediction_debug_*` | Step 9 | debug envelopes + taxonomy |
| `ta_data_health_*` | Step 11 | trust score / drift / qualification |

Current DB state (restored from `data_snapshots`):
- `ta_prediction_history`: 43 records (5 pending, 43 evaluated in history counters).
- `ta_prediction_temporal_buffer`: 18 records.
- Calibration buckets are rebuilt on demand (`POST /calibration/rebuild`).

---

## 5) Invariants — MUST NOT break (from `plan_project.md`, `PHASE_STATE.md`)

❌ Do NOT change `SimpleMA` entry logic
❌ Do NOT add new strategies
❌ Do NOT reactivate regime gates without architect's approval
❌ Do NOT change calibration / aggregator / conflict logic without forensic
❌ Do NOT add ML before the `n_evaluated ≥ 500` gate passes
❌ Do NOT touch UI tabs `Decisions` / `Prediction overlay` (paused by design)
❌ Do NOT modify deterministic shape of `features_v1` (hashes would break)

---

## 6) Safe extension surface for next R&D (architect-approved shape)

✅ **Read-only diagnostic endpoints** (new paths under the existing prefix).
✅ **New bucket groupings or metrics** for calibration (e.g. add `session_of_day`,
   `regime`, `volatility_regime`) **without altering upstream semantics**.
✅ **Dataset-stats monitoring** enrichments (drift, coverage, recency) — new
   summaries only, no schema change.
✅ **Trust score refinements** in `data_health/` (additional checks; score
   computation can add fields but must remain backward compatible).
✅ **New forensic reports** (e.g. `forensic_v3_...py`) following the v2 pattern.
✅ **New POC tests** (`poc_step*_...py`) to extend regression coverage.
✅ **Debug layer additions** — new taxonomy buckets, new root-cause detectors,
   provided they are additive.

**Risky (approval required before touching)**
- engines/*, aggregator, conflict resolver, feature schema, decision builder.

---

## 7) Current forensic baseline (for reference)

Latest `forensic_v2_mfe_mae.py` run (2026-05-04):
- Total real closed trades: 63.
- Per-regime MFE/MAE and time-to-reach stats are written to
  `/tmp/forensic_v2_mfe_mae.jsonl` and `/tmp/forensic_v2_report.md`.

POC regression (all passing except expected Step-7 "outcome produced" cases,
which require fresh evaluations):
- `poc_step7_calibration.py`: **10/12** (2 expected fails on fresh DB)
- `poc_step8_features.py`: **13/13** ✅
- `poc_step10_dataset.py`: **11/11** ✅
- `poc_step12_decision.py`: **12/12** ✅

---

## 8) Next R&D step — open question for architect

The architect has signalled: the next iteration targets the **TA block**, not
trading/execution. Candidate directions (all safe-surface):

1. **Expand calibration dimensions.** Add `session_of_day` × `symbol_tf` as a
   new bucket family; emit it via `GET /calibration/diagnostics` alongside
   existing buckets. Zero impact on production shape.
2. **Data-health gate v2.** Surface per-engine trust scores (currently only
   composite exists) so weak engines can be pinpointed before they hurt
   aggregation.
3. **Dataset recency monitor.** Track staleness of features_v1 records; fire a
   `gate: DATASET_STALE` when >X% of the last N records are older than T.
4. **Winning-scenario drill-down.** Extend `decision_intelligence`'s diagnostic
   endpoint to return _why_ a scenario won (dominance vs alignment vs risk)
   without changing the decision itself.

Pending architect selection.
