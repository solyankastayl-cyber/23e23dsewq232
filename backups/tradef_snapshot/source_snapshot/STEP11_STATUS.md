# STEP 11 — Status Tracker

> Single source of truth for the trainer build trigger. Updated only when
> the architect issues `CHECK STATS` or the gate state transitions.

---

## Current status: **READY FOR BUILD STEP 11 v1 (WHEN GATE GREEN)**

Approved on 2026-04-29 after architect review of:
- `/app/memory/STEP11_TRAINER_SPEC.md` (v1.1.0-design)
- `/app/backend/modules/ta_prediction_intelligence/learning/trainer_contracts.py`

All 6 architectural patches landed and verified:
1. Label definition contract (ε threshold + neutral drop)
2. Class imbalance handling (1/freq weights, mandatory)
3. Baseline comparison (majority + random + δ floor)
4. Confidence buckets + monotonicity test
5. Deterministic `model_id` formula
6. `dataset_snapshot_hash` mandatory + persisted everywhere

---

## Build trigger (BOTH conditions required)

```
TRIGGER for BUILD STEP 11 v1:
    live_evaluated >= 500 per (symbol, tf)        # at least one tracked pair
AND
    debug shows >=1 dominant root cause (>30-40%) # signal that errors are not random
```

Gate is read **only** from `live_evaluated` (live ML-readiness).
Simulation counts are observability only — they NEVER unlock the gate.

---

## Forbidden until trigger fires

- ❌ Writing any training code (`learning/trainer.py`, `learning/training_routes.py`, etc.)
- ❌ Adding `lightgbm` / `joblib` / `boto3` / `numpy` / `sklearn` / `pandas`
   to backend imports for the trainer path
- ❌ Removing or weakening any `NotImplementedError` in `trainer_contracts.py`
- ❌ Opening `POST /api/ta-prediction-intelligence/training/train`
- ❌ Creating the `ta_model_registry` Mongo collection ahead of time

---

## Allowed in parallel (optional, non-blocking)

- ✅ UI for ML readiness (read-only dashboard over `/ml-readiness/details`)
- ✅ UI for simulation replay (read-only, sim-only paths)
- ✅ Monitoring / alerts (observation, no mutation)
- ✅ Continuing to ingest live data so the gate eventually flips green

---

## Health of the upstream pipeline (architect's "9 green checks")

| Layer | Status |
|---|---|
| Data pipeline | ✅ trustworthy |
| Features (Step 8) | ✅ deterministic |
| Evaluation (Step 7 + outcome worker) | ✅ correct |
| Debug Layer | ✅ explains errors |
| Data Health | ✅ guards integrity |
| ML Readiness | ✅ honest gate |
| Root-Cause Aggregator | ✅ finds patterns |
| Simulation Engine | ✅ safe replay |
| Trainer Spec (Step 11) | ✅ COMPLETE (v1.1) |
| Live data | ⛔ accumulating |

---

## Next agent commands recognised

| Command | Action |
|---|---|
| `CHECK STATS` | Read-only snapshot: gate counts per pair + root-cause concentration + sim observability counts. No interpretation, no recommendations. |
| `BUILD STEP 11 v1` | Only valid AFTER gate green AND >=1 dominant root cause. Triggers implementation per SPEC v1.1. |
| `PATCH STEP 11 SPEC` | Re-open the design phase for amendments. |

Anything else → maintain status quo, no code changes.
