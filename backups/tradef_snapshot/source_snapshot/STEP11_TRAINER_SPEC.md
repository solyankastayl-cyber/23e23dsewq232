# STEP 11 — Model Trainer SPEC (v1.1, design-only)

> **Status: DESIGN-ONLY. No training code, no LightGBM calls, no model artifacts.**
> Companion file: `backend/modules/ta_prediction_intelligence/learning/trainer_contracts.py`
> (interfaces only — every method raises `NotImplementedError`).
>
> **Patch v1.1 changelog (2026-04-29):**
> 1. §2.4 — Label definition contract (ε threshold, neutral drop) [architect-required]
> 2. §2.5 — Class imbalance handling (`class_weight=1/freq`) [architect-required]
> 3. §6.5 — Baseline comparison (majority + random + δ floor) [architect-required]
> 4. §6.4 — Confidence buckets pinned to `predict_proba` + monotonicity test [architect-required]
> 5. §1.6 — `model_id` formula made explicit
> 6. §4.2 — `dataset_snapshot_hash` is now mandatory and persisted in both meta.json and Mongo
>
> Authored after architect approval of the 5-decision matrix:
>
> | # | Decision |
> |---|----------|
> | 1 | Format = markdown spec + Pydantic/ABC interface stubs (no helpers) |
> | 2 | Target v1 = `direction_h6` only (binary). secondary targets contracted but disabled |
> | 3 | Split = `time_split + purge_gap` default, `purge_gap = 6` is an INVARIANT |
> | 4 | Storage = Mongo registry (metadata + pointer) + local FS (mandatory) + S3 mirror (feature-flag) |
> | 5 | Train guard = HARD `423 Locked` if gate red. NO overrides, NO `force=true`, NO dev backdoors |

---

## 0. Phase context

Step 11 sits **between** Step 10 (Dataset Builder) and Steps 12+ (Decision
Intelligence / Blend Layer):

```
engines → conflict → interaction → scenario adjustment → calibration →
features (Step 8) → temporal buffer (Step 9) → dataset builder (Step 10) →
MODEL TRAINER (Step 11) ← we are here ←
→ inference (Step 12+) → blend with decision_intelligence → UI
```

**Step 11 produces ONE artefact:** a trained binary classifier for
`direction_h6` plus a deterministic, audited training report. It does NOT
produce inference code, NOT a /predict endpoint, NOT any change to
`decision_intelligence` or `live` response shape.

---

## 1. Hard rules (non-negotiable)

### 1.1 Live-only ML gate
- Training is gated on `live_evaluated >= 500 per (symbol, tf)`.
- `samples_by_source.scoring_basis = "live_evaluated_only"` is the contract.
- Simulation rows (`source="simulation"` in `ta_prediction_history_sim`)
  **NEVER** count toward the gate. Confirmed by Simulation Engine QA
  (`qa_simulation_engine.py`, DoC 8).

### 1.2 No code paths around the gate
- `POST /train` returns `423 Locked` when the gate is red.
- No `?force=true`, no `?dev=true`, no environment toggle, no admin header.
- The gate check is the **first** statement in the route. If it is
  reordered or wrapped, that PR is invalid.

### 1.3 Feature schema lock
- Each model artefact is bound to:
    - `feature_schema_hash` (current value lives in
      `learning/feature_schema.py`)
    - `feature_version` (`"v1"`)
- Loading a model whose schema_hash != current schema_hash MUST raise
  `FeatureSchemaMismatch`. No graceful coercion. No `try/except`.

### 1.4 Determinism
- Training is deterministic given (dataset_snapshot_hash, config, seed).
- `seed = 42` is the v1 default. Configurable but logged.
- Data ordering is sorted by `(symbol, tf, candle_close_ts, sample_id)`
  BEFORE the split. No `random.shuffle`, no `np.random.permutation` without
  `seed`.
- `numpy`, `random`, and (when present) `lightgbm` seeds are set in one
  helper `_set_global_seeds(seed)` (see `trainer_contracts.py`).

### 1.5 Strict separation from Decision Layer
- The trained model produces ONE thing: `predict_proba(direction_h6=1)`.
- It does NOT replace `decision_intelligence`.
- It does NOT mutate `bias`, `confidence`, `scenarios`, `risk_level`,
  `signal_strength`, or `interaction.type`.
- Any future blend MUST be a separate module (Step 13+) explicitly wired
  on top of decision_intelligence; the trainer does not know about it.

### 1.6 Auditability + deterministic `model_id` formula  *(v1.1)*

Every artefact carries:
- `model_id` (sha256 — see formula below)
- `dataset_snapshot_hash` (sha256 over the canonical sample-id list)
- `train_config_hash` (sha256 over the canonical-JSON of `TrainConfig`)
- `feature_schema_hash`
- `created_at`, `created_by_version`, `git_sha` (if available)
- `metrics` (full `EvaluationReport`)

**Pinned formula (v1.1):**
```
dataset_snapshot_hash = sha256("\n".join(sorted(sample_ids)).encode("utf-8")).hexdigest()
train_config_hash     = sha256(canonical_json(train_config).encode("utf-8")).hexdigest()
model_id              = sha256(
    f"step11|{feature_schema_hash}|{dataset_snapshot_hash}|{train_config_hash}".encode("utf-8")
).hexdigest()
```

Where:
- `canonical_json` = `json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)`
  applied to `TrainConfig.model_dump(mode="json")` after coercing enums to
  their string values.
- `"step11|"` namespace prefix prevents accidental collision with hashes
  from other layers (sample_id, feature_hash, etc.).
- All three component hashes are **also** persisted independently in
  `meta.json` and the Mongo registry (§4.2). The composite `model_id` is
  what the artefact directory and registry `_id` use.

Re-running with identical inputs → identical `model_id`.
Re-training in v2 over a drifted dataset → different `model_id`, even if
schema_hash is the same. This is **the** detection mechanism for silent
dataset drift.

---

## 2. Target schema

### 2.1 Targets contracted (Step 10 already produces these)

| Target | Type | v1 Status | Notes |
|---|---|---|---|
| `direction_h6` | binary | **ENABLED** | primary, stable, only target trained in v1 |
| `winning_scenario` | 3-class (`bull`/`base`/`bear`) | **DISABLED** | derived from scenario stack — risk of feedback noise |
| `return_h6` | regression (float) | **DISABLED** | high variance — postponed to v2 after baseline calibrated |
| `direction_h1`, `direction_h3` | binary | **DISABLED** | reserved for future short-horizon models |
| `max_favourable_h6`, `max_adverse_h6` | regression | **DISABLED** | for v2 risk-aware training |

### 2.2 v1 training scope
- **One** model per `(symbol, tf)` pair.
- Tracked pairs read from `ta_prediction_intelligence.ml_readiness.types.TRACKED_PAIRS`
  (currently `ETHUSDT_1H`, `BTCUSDT_1H`, `SOLUSDT_1H`).
- Cross-pair pooling is OUT of scope. v1 = pair-isolated baselines.

### 2.3 Class balance hard guard
- v1 trainer MUST surface `class_balance` in the report (counts, ratios).
- If `min_class_ratio < 0.10` → trainer aborts with `ImbalancedClassesError`.
  No silent SMOTE, no random oversampling. Architect decision required.
- This is the **floor** check. Imbalance handling for `min_class_ratio ∈
  [0.10, 0.50)` is mandatory and described in §2.5.

### 2.4 Label definition contract  *(v1.1, architect-required)*

**Problem prevented:** without an explicit dead-band, samples with
`return_h6 ≈ 0` become noise that the model overfits, inflating accuracy
on meaningless data.

**Hard contract** (mirrored as constants in `trainer_contracts.py`):

```
LABEL_DEFINITION_VERSION = "v1"
LABEL_NEUTRAL_EPSILON    = 0.0005     # = 0.05% absolute return on h6

y_h6 =
    1   if return_h6 >  +LABEL_NEUTRAL_EPSILON
    0   if return_h6 < -LABEL_NEUTRAL_EPSILON
   DROP otherwise (|return_h6| <= LABEL_NEUTRAL_EPSILON)
```

**Rules:**
- The drop happens **before** the train/eval split. Dropped rows are
  reported in `EvaluationReport.label_definition.neutral_dropped_count`.
- `LABEL_NEUTRAL_EPSILON` is an INVARIANT for v1, not a knob. Bumping it
  forces a new `LABEL_DEFINITION_VERSION`, which feeds into the
  `train_config_hash` and therefore the `model_id`. This means a model
  trained under v1 ε cannot be confused with one trained under v2 ε.
- The dataset_builder already stores raw `return_h6`; the trainer is the
  one that applies ε and produces binary labels. The dataset is **never**
  mutated. Drops are tracked, not deleted.
- If after the drop `n_train < 100` or `n_eval < 50` →
  `InsufficientSplitSamplesError`.

**Rationale for ε = 0.0005:** matches the "FLAT_NO_MOVE" heuristic used
in `forensic_v2_mfe_mae.py` (0.10% MFE threshold) at half-magnitude
because `direction_h6` is one-sided (a 0.05% absolute move at h6 is the
minimum that survives bid/ask + commission noise on the venues we use).
Final value reviewed by architect; if changed, bump
`LABEL_DEFINITION_VERSION` and document here.

### 2.5 Class imbalance handling  *(v1.1, architect-required)*

**Problem prevented:** with 70/30 imbalance the model can hit 70%
accuracy by always predicting the majority class. Surface metrics will
show "green" while the model is doing nothing.

**Strategy v1 (mandatory):**

```
for each class c in {0, 1}:
    freq[c] = n_class_c / n_total_train
    w[c]    = 1.0 / max(freq[c], 1e-6)
# normalize so the smallest weight is 1.0:
min_w = min(w.values())
w = {c: w[c] / min_w for c in w}
```

Passed to LightGBM via `class_weight=w` (or its numpy equivalent on
`sample_weight`, depending on the API path the implementation picks).

**Reporting (mandatory in `training_report.json`):**
```
class_weights: { "0": 1.0, "1": 2.33 }
class_freq:    { "0": 0.70, "1": 0.30 }
```

**Forbidden in v1:**
- SMOTE / ADASYN / any synthetic oversampling.
- Random under-sampling of majority class.
- Stratified resampling of the train set.

These alter the empirical distribution and will be revisited only if
`class_weight=balanced` proves insufficient on real metrics.

---

## 3. Train / eval split

### 3.1 Strategies (all contracted, only one default)

| Strategy | When | Notes |
|---|---|---|
| `time_split` | smoke / debug | first 80% / last 20% by `candle_close_ts` |
| `walk_forward` | rigorous CV | `n_folds=5`, each shifted forward by `eval_size` |
| `time_split_purge_gap` | **DEFAULT** | time_split + 6-bar purge between train and eval |

### 3.2 INVARIANTS (cannot be parameter-tweaked)
- `purge_gap = 6` bars (= `h6` horizon). **NOT a parameter.** Hard-coded
  next to the strategy enum, not in user config.
- Eval window is the **last** chronological slice (no future test set).
- No sample appears in both train and eval (asserted post-split).
- No outcome from a train sample can overlap an eval sample's input
  window — this is exactly what the 6-bar purge enforces.
- The neutral-drop from §2.4 happens **before** the split. The split sees
  only the labelled subset.

### 3.3 Failure modes
- Insufficient samples after split (`train_n < 100` or `eval_n < 50`):
  raise `InsufficientSplitSamplesError`. No silent fallback.
- Sample carries `feature_schema_hash != current` → drop with
  `skip="schema_mismatch"` and bump a counter on the report.
  (Mirrors Step 10's behaviour.)

---

## 4. Artefact storage

### 4.1 Layout (mandatory)

```
/app/backend/data/models/
└── <model_id>/
    ├── model.joblib              # serialized estimator (joblib, NOT pickle)
    ├── meta.json                 # full ModelMeta dump
    ├── feature_schema_hash.txt   # bytes of the current schema_hash
    ├── dataset_snapshot.txt      # newline-separated sorted sample_ids
    ├── dataset_snapshot_hash.txt # 64 hex chars + newline
    ├── train_config.json         # canonical-JSON dump of TrainConfig
    └── training_report.json      # EvaluationReport dump
```

- `model_id` is the directory name AND the registry key. It is the sha256
  computed in §1.6.
- Files are written atomically (write to `*.tmp` → `os.replace`).
- A directory whose `model.joblib` is missing or partial is considered
  CORRUPT and is ignored by the loader.
- `dataset_snapshot.txt` is the human-readable manifest;
  `dataset_snapshot_hash.txt` is the cryptographic anchor used by
  `model_id`. Both are written. Never trust one without the other.

### 4.2 Mongo registry (`ta_model_registry`)

Fields stored (metadata + pointer; **never** the model bytes):
```
{
  "_id": <model_id>,
  "model_id": <sha256>,
  "symbol": "BTCUSDT",
  "tf": "1H",
  "target": "direction_h6",
  "label_definition_version": "v1",
  "label_neutral_epsilon": 0.0005,
  "feature_version": "v1",
  "feature_schema_hash": "<64 hex>",
  "dataset_snapshot_id": "<64 hex>",        // alias of dataset_snapshot_hash
  "dataset_snapshot_hash": "<64 hex>",      // canonical name (v1.1)
  "dataset_size": <int>,
  "neutral_dropped_count": <int>,
  "split_strategy": "time_split_purge_gap",
  "purge_gap": 6,
  "seed": 42,
  "trainer_version": "v1",
  "trainer_builder_version": "1.0.0",
  "train_config_hash": "<64 hex>",
  "git_sha": <str|null>,
  "created_at": <ISO8601>,
  "trained_in_ms": <float>,
  "metrics": { ...EvaluationReport },
  "artifact_path": "/app/backend/data/models/<model_id>/",
  "s3_uri": <str|null>,
  "status": "trained" | "deprecated" | "failed",
  "deprecated_at": <ISO8601|null>,
  "notes": <str|null>
}
```

Indexes:
- `unique` on `model_id`
- `unique` on `(symbol, tf, dataset_snapshot_hash, train_config_hash)` —
  duplicate-detection fence
- `(symbol, tf, created_at desc)` for "latest model per pair"
- `(feature_schema_hash, status)` for sweep-after-schema-bump operations

### 4.3 S3 mirror (feature-flagged, OFF by default)
- Enabled iff `ENABLE_MODEL_S3_MIRROR="1"` AND all of
  `MODEL_S3_BUCKET`, `MODEL_S3_PREFIX`, `AWS_REGION` are set.
- When enabled, after a successful local-write and Mongo-upsert, the
  trainer uploads the directory under `s3://<bucket>/<prefix>/<model_id>/`
  and stamps `s3_uri` in the registry doc.
- Upload failures **do not** invalidate the local artefact. They flip
  `s3_status="failed"` on the registry doc, the trainer logs and exits 0.

### 4.4 Loader contract
- `load_model(model_id)` returns `LoadedModel` only if:
    - registry doc exists and `status == "trained"`
    - `feature_schema_hash` equals current schema hash
    - `model.joblib` exists, is non-empty, and unpickles cleanly
    - `dataset_snapshot_hash` matches the file content (re-hashed on load)
- Otherwise raises `ModelLoadError` with explicit reason. No fuzzy
  matching. No "closest model wins."

---

## 5. API contract (HTTP routes)

Prefix: `/api/ta-prediction-intelligence/training/`

All write routes hard-block on the gate (§1.2).

### 5.1 `GET /gate`
Read-only gate inspection.
```json
{
  "ok": true,
  "gate_status": "red|yellow|green",
  "min_required_per_pair": 500,
  "by_pair": {
    "BTCUSDT_1H": {"live_evaluated": 312, "meets_threshold": false},
    "ETHUSDT_1H": {"live_evaluated":  87, "meets_threshold": false},
    "SOLUSDT_1H": {"live_evaluated":   4, "meets_threshold": false}
  },
  "scoring_basis": "live_evaluated_only",
  "sim_counts_observability_only": {
    "BTCUSDT_1H": {"simulation_evaluated": 16}
  }
}
```

- `green`: ≥1 pair meets threshold.
- `yellow`: at least one pair within 80% of threshold.
- `red`: all pairs below 80%.

### 5.2 `POST /train`
Accepts `TrainRequest`:
```json
{ "symbol": "BTCUSDT", "tf": "1H", "split_strategy": "time_split_purge_gap",
  "seed": 42 }
```

Responses:
- `423 Locked` when gate red for this pair:
  ```json
  {
    "ok": false,
    "reason": "ml_gate_not_satisfied",
    "live_evaluated": 312,
    "required": 500,
    "by_pair": {...full gate snapshot...}
  }
  ```
- `200` on success: `EvaluationReport` + `model_id` + `artifact_path`.
- `409 Conflict` if a training run for the same `(symbol, tf,
  dataset_snapshot_hash, train_config_hash)` is already in progress
  (single-flight lock keyed on `model_id`).
- `400` on malformed request.

**Important:** in v1 the route body is implemented as **stub** that
returns 423 unconditionally until the gate-check helper is wired and the
gate is provably green.

### 5.3 `GET /models`
List trained models (registry read).
Filters: `?symbol=&tf=&status=&limit=`.

### 5.4 `GET /models/{model_id}`
Full `ModelMeta` + `EvaluationReport`. Read-only.

### 5.5 `POST /models/{model_id}/deprecate`
Flip `status="deprecated"`. Manual, audit-stamped (`deprecated_at`,
`deprecated_reason`). Does NOT delete the artefact directory.

### 5.6 `DELETE /models/{model_id}`
Not in v1. Out of scope.

---

## 6. Evaluation metrics (mandatory)

### 6.1 Primary
- `direction_accuracy` on the eval window.

### 6.2 Secondary
- `precision`, `recall`, `f1` (per class + macro).
- `confusion_matrix` (2×2 for binary).
- `roc_auc` (full curve thresholds in audit only, scalar in registry).

### 6.3 Critical metrics (THE deciders)
- `accuracy_by_confidence_bucket`: see §6.4 for buckets and pass test.
- `accuracy_by_signal_strength`: cross-tab predictions against the
  decision_intelligence `signal_strength` (`strong/moderate/weak/no_edge`)
  recorded at prediction time. A model that's 60% accurate everywhere is
  worse than one that's 80% accurate where Decision Layer says "strong"
  and 50% on "no_edge". Buckets with `n=0` emit `accuracy=null`.
- `class_balance` (counts + ratios).
- `temporal_drift_eval`: split eval window in half, compare accuracy.
  If `|delta| > 0.10` → flag in report (`temporal_drift_warning=true`).

### 6.4 Confidence definition + bucket pass test  *(v1.1, architect-required)*

**Definition:** confidence is the model's own probability for class 1.
For a binary classifier it is `predict_proba(X)[:, 1]`. For a regression
or non-probabilistic model the `IEvaluator` MUST refuse the run with
`UnsupportedConfidenceError` rather than fabricate one.

**Buckets (pinned, deterministic):**
```
low   :  proba_class_1 ∈ [0.00, 0.55)
mid   :  proba_class_1 ∈ [0.55, 0.70)
high  :  proba_class_1 ∈ [0.70, 1.00]
```

Note: "low" includes the `< 0.50` regime where the model is actively
betting on class 0. We measure accuracy of the **chosen** class
(`argmax(proba)`), not the class-1 probability.

**Pass test (mandatory for shippable model):**
```
accuracy(high) > accuracy(low) + 0.05
```

If the model is well-calibrated, top-bucket accuracy must beat
bottom-bucket accuracy. Failing this test does NOT abort training, but
flips `report.confidence_calibrated_ok = false` and surfaces
`confidence_calibration_warning` at the top of the report. The model is
stored, but the architect must approve any deployment.

### 6.5 Baseline comparison  *(v1.1, architect-required)*

**Problem prevented:** a model with 55% accuracy on a class-balanced set
looks fine until you realise the majority baseline is 54%. Without an
explicit comparison the system is flying blind on whether the model adds
value.

**Mandatory baselines (computed on the SAME eval window):**

| Baseline | Definition |
|---|---|
| `majority` | predict the class with the higher count in **train**; report accuracy on **eval** |
| `random_proportional` | sample predictions with class probabilities = train frequencies, with `seed=baseline_seed`; report accuracy on **eval** |
| `coin_flip` | `0.5/0.5` (informational only; expected acc = 0.5 on balanced data) |

**Minimum delta requirement (pass / fail):**
```
BASELINE_DELTA_MIN = 0.02     # i.e. 2 percentage points

model_passes_baseline_floor =
    direction_accuracy(model) >= direction_accuracy(majority) + 0.02
```

Report fields (mandatory in `training_report.json`):
```
baseline: {
  majority_accuracy:        0.54,
  random_proportional_accuracy: 0.50,
  coin_flip_accuracy:       0.50,
  model_minus_majority_pp:  0.03,
  passes_baseline_floor:    true,
  baseline_seed:            42
}
```

Failure of `passes_baseline_floor` does **not** abort training (the
artefact is still produced for forensics) but flips
`status="failed"` in the registry doc with
`failure_reason="below_baseline_floor"`. Such artefacts are NEVER eligible
for inference loading by `IArtifactStore.load`.

### 6.6 What is NOT a metric in v1
- PnL / Sharpe / win-rate. Trading metrics live in the Trading layer,
  not in Step 11. Step 11 measures **calibration of direction_h6**, full
  stop.

---

## 7. Component breakdown (interfaces locked, code forbidden)

File: `learning/trainer_contracts.py`. Every implementation method raises
`NotImplementedError`. Helpers, fall-throughs, and `pass` stubs are
forbidden.

```
IDatasetSnapshotProvider   # turns the live dataset into a frozen, hashable snapshot
ILabelExtractor            # applies ε + drops neutral; produces y / drop counters  (v1.1)
ISplitter                  # implements time_split / walk_forward / time_split_purge_gap
IClassWeightCalculator     # 1/freq class weights                                    (v1.1)
ITrainer                   # fit() — v1 = LightGBM binary classifier
IBaselineEvaluator         # majority / random / coin_flip baselines                  (v1.1)
IEvaluator                 # produces EvaluationReport (uses IBaselineEvaluator)
IArtifactStore             # local FS read/write (atomic, idempotent)
IModelRegistry             # Mongo read/write + idempotent upsert
ITrainGate                 # the only place that decides red/yellow/green
ITrainOrchestrator         # composes the above; owns no business logic
```

Dataclasses / Pydantic shells (also `NotImplementedError`-bound where
they have methods):
```
TrainConfig
DatasetSnapshot
LabelDefinition          (v1.1)
LabelExtractionResult    (v1.1)
SplitResult
ClassWeights             (v1.1)
TrainArtifact
BaselineMetrics          (v1.1)
EvaluationReport
ClassBalance
ConfusionMatrix
MetricsByBucket
ModelMeta
GateStatus
GateCheckResult
TrainRequest
```

Enums:
```
SplitStrategy        # time_split | walk_forward | time_split_purge_gap
TargetName           # direction_h6 | direction_h3 | direction_h1 | winning_scenario | return_h6
ModelType            # lightgbm_binary  (v1)  | lightgbm_multiclass | lightgbm_regression
GateStatusEnum       # red | yellow | green
ModelStatus          # trained | deprecated | failed
ConfidenceBucket     # low | mid | high                                   (v1.1)
```

---

## 8. Failure modes (explicit)

| Code | Cause | Action |
|---|---|---|
| `MLGateNotSatisfiedError` | live_evaluated < 500 for the pair | 423 Locked |
| `FeatureSchemaMismatch` | dataset / loaded model schema_hash drift | 409 Conflict (do not silently coerce) |
| `InsufficientSplitSamplesError` | post-split train_n<100 or eval_n<50 (incl. after §2.4 drop) | 422 Unprocessable |
| `ImbalancedClassesError` | min_class_ratio<0.10 | 422 Unprocessable, requires architect override (separate ticket) |
| `LabelExtractionError` | y vector length mismatch / non-finite return | 500 internal |
| `UnsupportedConfidenceError` | model has no `predict_proba` | 422 Unprocessable |
| `ConcurrentTrainRunError` | another run on same `model_id` | 409 Conflict |
| `ArtifactWriteError` | FS write failed / partial directory | rollback (delete dir), 500 |
| `RegistryWriteError` | Mongo upsert failed AFTER local write | log, mark `status="failed"`, 500. Local artefact left for forensics. |
| `ModelLoadError` | registry/file/schema/snapshot mismatch on load | raise; no fallback |

---

## 9. Acceptance criteria for v1 (when implementation is allowed)

Before Step 11 can be coded, ALL of:
- ☐ Live gate green for at least one pair (`live_evaluated >= 500`).
- ☐ Step 10 `dataset/stats` shows `persisted_total > 500` for that pair.
- ☐ `feature_schema_hash` has been stable for ≥ 30 days (no breaking
  changes to `feature_schema.py`).
- ☐ Architect ships `BUILD STEP 11 v1` directive.

After implementation, before declaring v1 done:
- ☐ `qa_step11_trainer.py` covers all interfaces, all failure modes,
  determinism, gate hard-block, `§2.4` neutral-drop count > 0 case,
  `§2.5` class_weights logged, `§6.5` baseline pass test, `§6.4`
  confidence monotonicity test.
- ☐ `testing_agent_v3` validates HTTP contract end-to-end.
- ☐ Trained model loads, predicts, and reports metrics on a held-out
  eval window.
- ☐ `accuracy_by_confidence_bucket` passes the §6.4 monotonicity test.
- ☐ `passes_baseline_floor=true` (§6.5).
- ☐ Registry doc + local artefact + S3 mirror (if enabled) all
  consistent. Re-running on identical dataset_snapshot → identical
  `model_id`.

---

## 10. Non-goals (v1)

- Inference endpoint (`POST /predict`).
- Online / streaming training.
- Cross-pair pooling / hierarchical models.
- Auto-retraining / scheduled jobs.
- PnL / trading metrics.
- Blend with `decision_intelligence` (Step 13).
- Model interpretability dashboards.
- A/B / shadow deployment.
- Probability calibration (Platt / isotonic). v1 reports calibration via
  §6.4 but does not patch the model.

Each of these is a separate phase, gated by Step 11 v1 acceptance.

---

## 11. Open questions for the architect

None of these are blocking the SPEC. They surface choices that ought to
be pinned **before** training code is written:

1. `lightgbm` hyper-parameters: do we want a tiny grid search in v1 or a
   single fixed config? (Recommendation: single fixed config in v1;
   tuning is its own phase.)
2. Exact value of `LABEL_NEUTRAL_EPSILON` — `0.0005` is the v1.1 default,
   architect to confirm or adjust before unlocking BUILD.
3. Should we persist `feature_importance_` per model? (Recommendation: yes,
   `training_report.json.feature_importance: {feature_name: gain}`.)
4. Should `accuracy_by_signal_strength` be opt-in (in case a record is
   missing the field)? (Recommendation: emit with `null` buckets, never
   skip the metric.)
5. Baseline floor δ — `0.02` (2pp). Architect to confirm; v2 may need
   per-pair tuning.

---

## 12. Versioning

- `STEP11_TRAINER_SPEC_VERSION = "v1.1.0-design"`
- `LABEL_DEFINITION_VERSION   = "v1"`
- `TRAINER_VERSION            = "v1"`
- `TRAINER_BUILDER_VERSION    = "1.0.0"`

A breaking change (target switch, schema lock loosened, gate moved,
ε changed without bump) bumps MAJOR. Adding a metric or a new model type
bumps MINOR. The patch above is design-only and bumps minor.
