# plan.md — TA Prediction Intelligence — Step 7 COMPLETED (history calibration / ML-ready layer)

## 0) Phase 6 / P3 — Step 6: Interaction-aware Scenarios ✅ COMPLETED (2026-04-27)
(see history below)

## 0.1) Phase 6 / P3 — Step 7: History Calibration / ML-ready layer ✅ COMPLETED (2026-04-27)

**Pipeline:** `engines → conflict → interaction → scenario adjustment → calibration → UI`.
Predictions persist → outcome через N свечей → bucket calibration (hit-rate, brier, Wilson CI)
→ bounded adjustment поверх Step-6 scenarios. Без MetaBrain, без trading, без изменений
в engines/aggregator/conflict_resolver/ScenarioBuilder/interaction_adjuster.

### Что построено (все файлы внутри `modules/ta_prediction_intelligence/`)

| Файл | Роль |
|---|---|
| `repository.py` | `TAPredictionRepository` — persistence: `ta_prediction_history` (prediction record с audit trail), `ta_prediction_calibration_stats`. Индексы: `uniq_prediction_id` sparse, `by_symbol_tf_ts`, `by_state_ts`. Back-compat `save()/recent()` сохранены. |
| `evaluation/ta_prediction_outcome_worker.py` | Async background (60s tick). Для каждого pending: идентифицирует entry candle, ждёт ≥ h6 свечей, считает `return_h1/h3/h6`, `max_favourable/adverse_move_pct`, `winning_scenario` (target/invalidation cross приоритет, иначе ±0.10% порог). Error isolation per-record. Pure helper `evaluate_prediction_with_candles`. |
| `calibration/calibration_engine.py` | Pure aggregation. 4 измерения: `interaction_type`, `dominant_engine`, `symbol_tf`, `symbol_tf_interaction`. Метрики: `n`, `hit_rate`, `avg_predicted`, `calibration_gap`, `brier_score`, `wilson_lower/upper`, `winners`. |
| `calibration/calibration_store.py` | 30-сек TTL кэш + rebuild (`rebuild_from_history`). Не имеет фонового цикла — rebuild только по API. |
| `scenarios/scenario_calibration_adjuster.py` | Pure post-processing поверх Step 6. Bucket ladder: `symbol_tf_interaction → symbol_tf → interaction_type`. Invariants: per-delta cap=0.08, total cap=0.20, floor=0.02, ceil=0.92, renormalise к sum=1.0. `n<30` → **no-op с `applied=false, reason='insufficient_samples'`**. |
| `step7_pipeline.py` | `apply_step7_postprocess(result, source, persist)` — вызов calibration + repository.record_prediction. Mutate-in-place. Никогда не raise. |

### Integration
- `live_adapter.fetch_live_context` — добавлены `last_close`, `last_candle_close_ts` в `_live`; Step 7 вызывается с `persist=True`.
- `TAPredictionService.build_from_setup/build_from_typed_setup` — поддерживают `persist` (default=False для синтетических callers).
- `server.py` lifespan: start/stop `get_outcome_worker()`.

### Новые endpoints (`/api/ta-prediction-intelligence/`)
- `GET  /history?symbol&tf&state&limit` — recent predictions + outcomes + state_counts
- `GET  /calibration?group_by&refresh` — bucket stats для выбранного измерения
- `GET  /calibration/diagnostics` — summary по всем 4 измерениям + полные stats
- `POST /calibration/rebuild` — пересчёт из evaluated records и запись в `ta_prediction_calibration_stats`
- `GET  /outcome_worker/status` — ticks / evaluated / errors / state_counts
- `/health` теперь содержит `step7_entry_points`.
- `/from-typed` + `/from-setup` — добавлен `persist` flag.
- `/live` — в ответе теперь: `prediction_id`, `scenarios_original`, `scenarios_pre_calibration`, `scenarios_calibration{applied,reason,group_by,bucket_key,bucket_n,hit_rate,avg_predicted,calibration_gap,brier_score,raw_deltas,explanation,per_delta_cap,total_delta_cap,prob_floor,prob_ceil,min_samples}`, и сам `scenarios` — calibrated (или равны pre_calibration при skip).

### Frontend (`pages/PredictionPage.jsx`)
- `IntelScenariosCard` принимает `calibration` prop. Справа в header: **двуслойные пилюли** — Step-6 `adjusted by <interaction_type>` + Step-7 `calibrated · <group_by> · n=<N> · brier=<X>` / `not yet calibrated · <reason>`.
- Пояснение Step-7 explanation под header card (когда применено).
- `ScenarioCard` теперь показывает **3-stage deltas** в header: `i:↑/↓Npp` (interaction) и `c:↑/↓Npp` (calibration). Полосы прогресса с двумя теневыми маркерами: `rgba(15,23,42,0.18)` = original, `${color}55` = pre-calibration. Подпись `orig N% → i N% → cal N%`.
- Новая секция **`IntelCalibrationHistoryCard`** ниже Scenarios:
  - State chips (`pending: N`, `evaluated: N`) + кнопка `rebuild calibration`
  - Левая колонка — таблица **Recent predictions** (time/bias/conf/interaction/state/h6/winner)
  - Правая колонка — таблица **Calibration stats** с переключателем `interaction_type / dominant_engine / symbol_tf_interaction` (hit %/predicted %, brier)
  - Строка снизу: **Current call** (например, `no calibration applied — insufficient_samples`).

### Тесты
- `scripts/poc_step7_calibration.py`: **12/12 PASS** (unit math calibration engine, Wilson edge cases, adjuster invariants/skip/caps, outcome worker bullish/flat/not-ready, HTTP smoke live/rebuild/diagnostics/history/worker).
- Backend testing agent (`/app/test_reports/iteration_3.json`): **20/20 PASS**. Покрывает Step-6 non-regression, все Step-7 endpoints, honest skip, determinism, Meta isolation, history persistence.

### Invariants, которые соблюдены
- Scenarios `sum=1.0`, per-scenario `∈ [0.02, 0.92]`, raw deltas cap.
- `n < 30` → calibration **skip** + honest meta.
- engines/aggregator/conflict_resolver/ScenarioBuilder/interaction rules/interaction_adjuster — **не тронуты**.
- combined_analysis / meta_pipeline / policy_registry / shadow_logger / shadow_scheduler — **не тронуты**.
- TA Prediction Intelligence остаётся autonomous, `wired_to_meta=false`.

### Следующий шаг (GATED, не трогаем код)
Накопить evaluated outcomes. Как только `n>=30` в какой-то клетке (symbol_tf_interaction / interaction_type / dominant_engine), calibration_adjuster автоматически начнёт применяться для соответствующих вызовов `/live`. Для агрегирующего пересмотра: `POST /calibration/rebuild`. Архитектор решает, стоит ли расширять правила.

---

## 0.2) Step 8 — Feature System + Step 9 — Hybrid Temporal Buffer ✅ COMPLETED (2026-04-27)

**Architectural lockdown:** ZERO changes to engines / aggregator / conflict_resolver / ScenarioBuilder / interaction rules / interaction_adjuster / calibration_adjuster / step7_pipeline calibration branch. Learning layer is READ-ONLY observer. Не подключается к Meta / combined_analysis / shadow_*. НЕ содержит ML-тренировки — это data engine для future training (Step 11+).

### Что построено (всё внутри `modules/ta_prediction_intelligence/learning/`)

| Файл | Роль |
|---|---|
| `feature_schema.py` | Canonical **82 features** с типами, ranges, defaults (8 блоков: Structure×12 / Momentum×13 / Level×12 / Pattern×10 / Volatility×10 / Price-Action×10 / Transitions×7 / Meta×8). Enum codebook'ы (append-only). `FEATURE_SCHEMA_HASH` вычисляется один раз, **64-hex deterministic**. `coerce_to_schema` клипует + кастует. |
| `feature_hash.py` | Canonical JSON (sorted keys, round(6), no whitespace, ASCII-only) → sha256. Order-independent, float-stable hashing. |
| `state_machine.py` | 3 явных FSM: Trend (range/weak_trend/strong_trend/exhaustion), Momentum (flat/building/strong/exhaust), Volatility (compression/normal/expansion/chaos). Classifiers + `detect_*_transition` — разрешённые переходы имеют unique codes, неразрешённые и шум → 0. |
| `price_action.py` | Pure candle geometry — 10 features (range_pct_10, body_ratio_mean_5, wicks, close_pos, consecutive up/down, volatility clustering, gap_flag, inside_bar_streak). |
| `temporal_buffer.py` | `HybridTemporalBuffer`: RAM ring per `(symbol, tf)` (window=50) + Mongo checkpoint каждые 10 pushes в `ta_prediction_temporal_buffer` (индекс `by_sym_tf_ts`). Lazy cold-load при первом access. Thread-safe (RLock). Flush всей очереди на shutdown. |
| `feature_builder.py` | `FeatureBuilder.build(result)` → FeatureSnapshot с 82 features + hash + states + missing_engines + latency_ms. `build_preview` — без push в buffer. Process-wide singleton. |
| `../learning_routes.py` | Read-only endpoints: `GET /features/schema`, `GET /features/preview`, `GET /buffer/status`. |

### Integration (additive)
- `step7_pipeline.apply_step7_postprocess`: после calibration **опционально** вызывает `feature_builder.build(result)`, кладёт `_features_debug` (lightweight meta) в response и передаёт `features_bundle` в `repository.record_prediction`. Ошибки feature builder изолированы — они никогда не ломают Step 6/7.
- `repository.record_prediction(..., features_bundle=None)` теперь сохраняет `features_v1`, `feature_version`, `feature_schema_hash`, `feature_hash`, `feature_builder_version`, `feature_states`, `feature_ts`, `feature_missing_engines`, `feature_latency_ms` в doc.
- `server.py`: registers learning routes + `flush_all()` temporal buffer в shutdown.

### Новый response shape у `/live` (только добавлено)
```
_features_debug: {
  feature_version: "v1",
  feature_schema_hash: "<64 hex>",
  feature_hash: "<64 hex>",
  builder_version: "1.0.0",
  feature_count: 82,
  states: { trend, momentum, volatility },
  missing_engines: [...],
  latency_ms: <float>
}
```
Сам feature vector (82 значения) **не попадает в response** — он живёт в истории Mongo. Это защищает contract Step 6/7.

### Новые endpoints
```
GET /api/ta-prediction-intelligence/features/schema   — schema + schema_hash
GET /api/ta-prediction-intelligence/features/preview  — build snapshot без push
GET /api/ta-prediction-intelligence/buffer/status     — RAM ring + checkpoint stats
```

### Тесты
- `scripts/poc_step8_features.py` — **13/13 PASS** (schema shape + hash stability + coerce clipping + classifiers + transitions + price_action math + buffer RAM/checkpoint + 6 HTTP endpoints).
- `scripts/poc_step7_calibration.py` — **12/12 PASS** (regression).
- Backend testing agent (`iteration_4.json`) — **63/63 PASS** (Step 6+7 non-regression + Step 8 feature system + Step 9 buffer + determinism + Meta isolation).

### Invariants
- 82 features, schema_hash и feature_hash = SHA-256 64 hex, deterministic
- Никакого `random`, никаких ML-моделей, никаких мутаций существующих слоёв
- Read-only observer — errors в learning НЕ ломают Step 6/7
- Mongo-коллекция `ta_prediction_temporal_buffer` append-only, cold-load recovery при рестарте
- `features_v1` + hashes сохраняются per-prediction — готовый датасет для Step 11

### GATED → Step 10 / 11+
- **Step 10 (Dataset Builder)** ✅ COMPLETED (см. ниже).
- **Step 11 (Model Trainer LightGBM)** — БЛОКИРОВАН: nужно `n ≥ 500` evaluated predictions per (symbol, tf) для первого baseline.
- **Step 12-13** (Inference Engine + Blend Layer) — блокированы Step 11.

---

## 0.3) Step 10 — Dataset Builder ✅ COMPLETED (2026-04-27)

**Architectural lockdown:** zero changes to engines / aggregator / conflict_resolver / ScenarioBuilder / interaction_adjuster / calibration_adjuster / feature_builder / temporal_buffer / live_adapter. Dataset Builder — чистый read-only transformer поверх evaluated predictions с `features_v1`. НЕ содержит модели, inference, blend, UI, влияния на `/live` response.

### Что построено (всё внутри `modules/ta_prediction_intelligence/learning/`)

| Файл | Роль |
|---|---|
| `dataset_builder.py` | `build_sample(record)`, `build_dataset(records)`, `build_sample_id` (deterministic sha256), `compute_sample_weight`, `compute_stats`, `persist_samples`, `read_samples_from_mongo`, `count_samples_in_mongo`. |
| `../evaluation/ta_prediction_outcome_worker.py` | **Additive:** outcome теперь также содержит `volatility_future_h6` = stdev of log returns h1..h6 (real forward measurement). |
| `../learning_routes.py` | **+3 endpoints:** `/dataset/preview`, `/dataset/stats`, `POST /dataset/rebuild`. |

### Sample contract (v1)
```json
{
  "sample_id": "<sha256('ta_dataset_sample|v1|<prediction_id>')>",
  "prediction_id": "...",
  "symbol": "ETHUSDT", "tf": "1H",
  "feature_version": "v1",
  "feature_hash": "<64 hex>",
  "feature_schema_hash": "<64 hex>",
  "X": { 82 canonical features },
  "y": {
    "direction_h1": 0|1, "direction_h3": 0|1, "direction_h6": 0|1,
    "return_h1": float, "return_h3": float, "return_h6": float,
    "max_favourable_h6": float, "max_adverse_h6": float,
    "volatility_future_h6": float,
    "winning_scenario": "bull"|"base"|"bear"
  },
  "sample_weight": float in [0.40, 1.20],
  "dataset_version": "v1", "dataset_builder_version": "1.0.0",
  "meta": { feature_states, feature_missing_engines, volatility_proxied, created_at, evaluated_at }
}
```

### Жёсткие правила (реализованы)
1. Только `evaluation_state=="evaluated"` → остальные → `skip="not_evaluated"`.
2. `features_v1` отсутствует → `skip="no_features_v1"`.
3. outcome без return_h1/h3/h6 или winning_scenario → `skip="incomplete_outcome"`.
4. `record.feature_schema_hash` ≠ current `FEATURE_SCHEMA_HASH` → `skip="schema_mismatch"`.
5. `sample_id` детерминирован, дубликаты → `skip="duplicate_sample_id"`.
6. `volatility_future_h6` реальный (новый outcome_worker) либо proxy = `mfe - mae` с флагом `meta.volatility_proxied=True` для legacy записей.
7. `sample_weight = volatility_factor(vol_state) × completeness_factor(missing_engines)` deterministic, floor 0.40, ceil 1.20.
8. Никакого synthetic y. Никакого random. Никаких model calls.

### Persistence
- Collection `ta_prediction_dataset`
- Unique index `uniq_sample_id` (sample_id)
- Secondary index `by_pair_version` (symbol, tf, dataset_version)
- Upsert-only; перезапись безопасна (idempotent).

### Тесты
- POC `scripts/poc_step10_dataset.py`: **11/11 PASS** (determinism, 4 skip reasons, y shape + directions, volatility proxy flag, sample_weight math, dedup/stats, Mongo persist/read/count, 3 HTTP endpoints, regression).
- Regression: `poc_step7_calibration.py` 12/12, `poc_step8_features.py` 13/13 — **36/36 total POC**.
- Testing agent (`iteration_5.json`): **23/23 PASS** (Step 6+7+8+9 non-regression, Step 10 endpoints, contract validation, empty-state handling, skip counts).

### Invariants
- Read-only: dataset_builder НИЧЕГО не мутирует в source records
- Deterministic: same inputs → same samples → same sample_ids → same hashes
- Idempotent persistence через upsert
- `min_samples_for_training=500` зашит в `/dataset/stats` как явный GATE для Step 11

### GATED → Step 11
- Model Trainer остаётся закрыт до накопления `n ≥ 500` evaluated samples per (symbol, tf).
- Мониторинг прогресса: `GET /api/ta-prediction-intelligence/dataset/stats` — как только `stats.by_pair["ETHUSDT_1H"] >= 500`, архитектор даёт команду строить Step 11.
- `POST /dataset/rebuild` можно вызывать периодически — сохраняет актуальный dataset в Mongo для обучения.


---

## 0.4) Step 12 — Decision Intelligence Layer ✅ COMPLETED (2026-04-27)

**Architectural lockdown:** ZERO mutations to engines / aggregator / conflict_resolver / ScenarioBuilder / interaction_adjuster / calibration_adjuster / feature_builder / temporal_buffer / temporal_intelligence. Decision Intelligence — чистый read-only аналитический слой поверх `scenarios + interaction + temporal_intelligence + conflict_ratio + bias`. Не ML, не trading, не MetaBrain, не execution.

### Pipeline (зафиксирован)

```
engines → conflict → interaction → scenario adjustment →
calibration → features → temporal → DECISION INTELLIGENCE → UI
```

Decision не меняет `scenarios`, `bias`, `confidence` upstream. Он производит НОВОЕ поле `decision_intelligence` в response и в history record.

### Что построено (всё внутри `modules/ta_prediction_intelligence/decision_intelligence/`)

| Файл | Роль |
|---|---|
| `types.py` | `DecisionIntelligenceContext` dataclass + `to_dict()` (JSON-safe, rounded). Enum-literals: `PRIMARY_SCENARIOS`, `BIAS_VALUES`, `STRENGTHS`, `RISK_LEVELS`, `DOMINANCE_LABELS`, `ACTION_FRAMES`. Версии: `DECISION_VERSION="v1"`, `DECISION_BUILDER_VERSION="1.0.0"`. |
| `scenario_selector.py` | `select_primary_scenario(scenarios)` — принимает list-of-dicts или dict, нормализует, сортирует по `(-probability, name)` (детерминированный tiebreak). `SCENARIO_BIAS` map (`bull→bullish`, `base→neutral`, `bear→bearish`). |
| `dominance_engine.py` | `compute_dominance(primary_prob, secondary_prob)` → `(dominance_float, label)`. Лестница: `>=0.30 dominant`, `>=0.15 clear`, `>=0.07 thin`, иначе `ambiguous`. |
| `risk_engine.py` | `compute_risk(context)` — агрегирует 6 сигналов: engine conflict (>0.40), temporal instability (>0.60), reversal pressure (>0.60), regime flip frequency (>0.30), risky interaction types (fake_breakout/expansion_chaos/whipsaw), chaotic sequence. Возвращает `(score∈[0,1], level, reasons[])`. |
| `alignment_engine.py` | Infer interaction direction через `INTERACTION_DIRECTION_MAP` (aligned/opposed/neutral) относительно aggregated bias. `compute_alignment(primary_bias, context)` — base=0.5, ±0.20 interaction, ±0.15 temporal continuation/reversal, +0.10 для neutral primary при instability. Clamp [0,1]. |
| `decision_classifier.py` | `classify_decision(confidence, dominance, risk_level)` — hard-kills: `dominance<0.07 → no_edge`, `risk=extreme → no_edge`. Иначе ladder: strong (≥70% · dom≥0.20 · low risk), moderate (≥50% · dom≥0.12 · low/elevated), weak (≥35% · dom≥0.07), else no_edge. |
| `decision_builder.py` | `build_decision_intelligence(result)` — орекстратор. Confidence formula: `primary_prob × (0.50+0.50×alignment) × (0.60+0.40×temporal) × (1.00−0.50×risk)`. Temporal not-ready → `temporal_score=0.5` (neutral). Empty scenarios → safe `{primary="none", strength="no_edge"}`. Все exceptions поглощаются. |

### Integration (additive, read-only)

- `step7_pipeline.apply_step7_postprocess`: после temporal layer вызывает `build_decision_intelligence(result)`, кладёт dict в `result["decision_intelligence"]`. Исключения → safe stub с `decision_internal_error` тегом.
- `repository.record_prediction(..., decision_context=None)` — новый опциональный kwarg; сохраняет `decision_intelligence` в doc рядом с `temporal_intelligence`.
- `live_adapter` и `TAPredictionService` ничего не меняют — pipeline переиспользует общий step7_pipeline.

### Новый блок в `/live` response

```json
"decision_intelligence": {
  "primary_scenario": "bull|base|bear|none",
  "secondary_scenario": "base|null",
  "scenario_probability": 0.6673,
  "secondary_probability": 0.2464,
  "scenario_dominance": 0.4209,
  "scenario_dominance_label": "dominant|clear|thin|ambiguous",
  "decision_confidence": 0.4817,
  "signal_strength": "strong|moderate|weak|no_edge",
  "risk_level": "low|elevated|high|extreme",
  "risk_score": 0.0,
  "alignment_score": 0.65,
  "temporal_score": 0.6875,
  "action_frame": "continuation|reversal|range|uncertainty",
  "decision_bias": "bullish|bearish|neutral",
  "drivers": ["temporal_continuation_support", ...],
  "risks": ["high_engine_conflict", ...],
  "summary": "...",
  "version": "v1",
  "builder_version": "1.0.0"
}
```

### Frontend (`pages/PredictionPage.jsx`)

- Новая карта `IntelDecisionCard` (testid=`ta-intel-decision`) — вставлена после `IntelTemporalCard`, до `IntelEnginesCard`.
- Header: 3 pill'а — `BEAR · BEARISH` (decision_bias color), `MODERATE/STRONG/WEAK/NO_EDGE` (strength), `RISK: LOW/ELEVATED/HIGH/EXTREME`.
- Summary stripe — поле `decision.summary`.
- 3-column grid:
  - **Decision Confidence** — крупный % + прогресс-бар + action_frame badge.
  - **Scenario Selection** — primary/secondary prob-rows + Dominance pill (`DOMINANT · 85pp`).
  - **Component Scores** — Alignment / Temporal / Risk bars.
- Footer: drivers (зелёные pills) + risks (красные pills) — testids `decision-driver-pill` / `decision-risk-pill-item`.

### Тесты

- POC `scripts/poc_step12_decision.py`: **12/12 PASS**
  - scenario_selector (primary/secondary + tiebreak + empty safe)
  - dominance_engine (5 ladder cases)
  - risk_engine (high + low contexts)
  - alignment_engine (direction inference + score nudges)
  - decision_classifier (6 ladder cases + hard kills)
  - decision_builder full happy-path
  - decision_builder deterministic (identical output bytewise)
  - decision_builder missing scenarios → `no_edge`
  - decision_builder temporal-not-ready → `temporal_score=0.5`
  - HTTP `/live` exposes `decision_intelligence` block
  - HTTP `/health` green (regression)
  - HTTP `/from-typed` clean 4xx (no crash)
- Regression: `poc_step7_calibration.py` 12/12, `poc_step8_features.py` 13/13, `poc_step10_dataset.py` 11/11, `poc_temporal_intelligence.py` 11/11 → **59/59 total POC**.
- Визуальный smoke через `/tech-analysis → Prediction` tab: карта рендерится, реальные данные (primary=bear · 91%, confidence=67%, dominance=DOMINANT · 85pp, strength=moderate, risk=low, action_frame=REVERSAL, driver=`interaction_aligned_with_primary_scenario`).

### Invariants (все соблюдены)

- ❌ Не меняет `scenarios`, `bias`, `confidence`, `contributions`, `interaction`, `temporal_intelligence`.
- ❌ Не вызывает ML / random / external APIs.
- ❌ Не связан с MetaBrain / trading / execution.
- ✅ Deterministic: same input → same output (подтверждено bytewise сравнением).
- ✅ Безопасен против отсутствия scenarios → `primary="none"`, `strength="no_edge"`, `confidence=0`.
- ✅ Безопасен против неготового temporal слоя → `temporal_score=0.5` (нейтральный).
- ✅ Все exceptions изолированы — decision_internal_error тег без поломки live response.

### Философия слоя

```
До Step 12 система умела:
  ✔ анализировать (engines)
  ✔ интерпретировать (interaction + scenarios)
  ✔ калибровать (calibration)
  ✔ видеть во времени (temporal)

Шаг 12 добавил:
  ✔ решать, что из этого — edge (no_edge / weak / moderate / strong)
  ✔ сжимать 4 измерения (probability, dominance, alignment, temporal) минус risk
     в одно consolidated confidence
  ✔ вырабатывать action_frame (continuation / reversal / range / uncertainty)
```

Это финальный слой BEFORE ML. Теперь когда Step 11 (LightGBM) будет построен, его задача станет компактной: предсказывать direction/return, а не "что с этим делать" — второе уже решает Decision Intelligence.

### GATED → Step 11 (Model Trainer, LightGBM)

- Блокирован до `n ≥ 500` evaluated samples per (symbol, tf).
- Текущий прогресс отслеживается через `GET /api/ta-prediction-intelligence/dataset/stats`.
- Как только накопим данные — команда `BUILD STEP 11` разблокирует обучение.


---

## 2) Implementation Steps

### Phase 1 — Core POC (isolation): persist → evaluate → calibrate → adjust
**Core workflow:** корректно записываем предикт, затем через N свечей считаем outcome, затем калибруем и применяем bounded adjustment.

**User stories (POC):**
1. As a developer, I can record a prediction with fully-auditable scenarios (orig + interaction-adjusted) and get back `prediction_id`.
2. As a developer, I can evaluate a stored prediction after h1/h3/h6 candles and persist outcomes deterministically.
3. As a developer, I can rebuild calibration stats for buckets and get stable metrics (hit-rate, brier, Wilson CI).
4. As a developer, I can apply calibration adjustment on top of Step-6 scenarios with strict caps/floors and renormalization.
5. As a developer, if `n < 30` in a bucket, calibration is skipped with `applied=false` and an explicit reason.

**Work items:**
- Add `prediction_repository` extensions in `modules/ta_prediction_intelligence/repository.py`:
  - `TAPredictionRecord` schema (fields from context + `evaluation_state`).
  - `record_prediction(...)`, `get_pending_predictions(...)`, `update_prediction_outcome(...)`, `get_recent_predictions(...)`.
  - Indexes: `(symbol, tf, candle_close_ts)`, `evaluation_state`, optional unique `prediction_id`.
- Implement `ta_prediction_outcome_worker.py` (async tick ~60s):
  - Select pending predictions; if enough closed candles exist (>= h6), compute `return_h1/h3/h6`, `mfe/mae`.
  - Resolve `winning_scenario` by deterministic rules (target/invalidation if present; else directional outcome threshold).
  - Persist outcome + mark `evaluation_state=evaluated`; isolate errors per record.
- Implement `calibration/calibration_engine.py` (pure):
  - `aggregate_calibration(records, group_by=interaction_type|dominant_engine|scenario_name)`.
  - Metrics per bucket: `n`, hit-rates, avg_predicted, brier, Wilson CI.
- Implement `scenarios/scenario_calibration_adjuster.py` (pure):
  - `apply_calibration_adjustment(scenarios, context, stats)`.
  - Guardrails: per-scenario |Δ|<=0.08; total cap Σ|Δ|<=0.20; clip 0.02..0.92; renorm; `n<30` → no-op.
- Create a minimal POC script `scripts/poc_step7_calibration.py`:
  - Call `/api/ta-prediction-intelligence/from-typed` or service directly.
  - Force-create a small synthetic dataset (for unit) + verify skip behavior.

**POC verification checklist:**
- At least 1 prediction persisted and then evaluated (local candles) without crashes.
- Calibration rebuild produces deterministic bucket stats.
- Calibration adjuster never breaks invariants (sum=1, bounds, caps).

---

### Phase 2 — V1 module integration (backend): wire Step 7 into live flow
**User stories:**
1. As an API user, I receive `prediction_id`, `scenarios_pre_calibration`, and `scenarios_calibration` in responses.
2. As an API user, I can query recent prediction history with outcomes and filtering by symbol/tf/state.
3. As an operator, I can see outcome worker status (ticks/evaluated/errors) to trust background evaluation.
4. As an operator, I can rebuild calibration stats on demand and read diagnostics.
5. As a user, calibration never changes Step-6 semantics; it only post-processes probabilities and explains why.

**Work items:**
- Integration order in `live_adapter.fetch_live_context()` and `TAPredictionService.build_from_*`:
  1) scenario_builder → 2) interaction layer → 3) interaction_adjuster (Step 6) →
  4) calibration_adjuster (Step 7) → 5) repository.record_prediction.
- Add lifespan wiring in `backend/server.py`:
  - start/stop `ta_prediction_outcome_worker` (graceful shutdown).
- Add routes in `ta_prediction_routes.py`:
  - `GET /history` (filters: symbol/tf/limit/state)
  - `GET /outcome_worker/status`
  - `POST /calibration/rebuild`
  - `GET /calibration` + `GET /calibration/diagnostics`
- Add storage for calibration stats: `ta_prediction_calibration_stats` (rebuild-only; no auto mutation).

---

### Phase 3 — Frontend UX (PredictionPage): show calibrated vs adjusted vs original
**User stories:**
1. As a user, I can see whether scenarios are calibrated (and why/why not) directly in the Scenarios card.
2. As a user, I can see a 3-stage probability view: original → interaction-adjusted → calibrated.
3. As a user, I can inspect last N predictions with outcomes to build trust.
4. As a user, I can see calibration bucket stats (n, predicted vs actual, brier) in a compact card.
5. As a user, UI remains stable even when history is empty or calibration is unavailable.

**Work items:**
- Update `pages/PredictionPage.jsx` (TA path only):
  - Render calibration pill/state in `IntelScenariosCard`.
  - Add mini deltas per scenario for both adjustments.
  - Add section: “Prediction History & Calibration” (table + small diagnostics card).

---

### Phase 4 — Testing & non-regression
**User stories:**
1. As a maintainer, unit tests validate outcome math for bullish/bearish and MFE/MAE.
2. As a maintainer, unit tests validate calibration metrics (brier, hit-rate, Wilson bounds) on synthetic data.
3. As a maintainer, unit tests enforce adjuster invariants (caps/floor/ceil/renorm).
4. As a maintainer, integration tests confirm `/live` returns new fields and persists predictions.
5. As a maintainer, background worker updates predictions to `evaluated` and endpoints reflect it.

**Work items:**
- Add backend tests under `backend/tests` covering repository, worker (with controlled candles), calibration engine, adjuster.
- Run existing suite to ensure no regression in Step 6 endpoints.

---

## 3) Next Actions
1. Implement Phase 1 POC end-to-end (repo + worker + calibration engine + calibration adjuster + script).
2. Fix until POC is deterministic and stable (no calibration when n<30; bounded adjustments always valid).
3. Wire into live adapter/service + server lifespan; add APIs.
4. Implement frontend display for calibration + history.
5. Run full test pass + smoke: `/api/ta-prediction-intelligence/live` shows both adjustments + persistence; history/outcome/calibration endpoints work.

---

## 4) Success Criteria
- ✅ `/api/ta-prediction-intelligence/live` returns: `prediction_id`, `scenarios_original`, Step-6 adjustment meta, and Step-7 `scenarios_calibration` meta.
- ✅ Predictions persist in Mongo and transition pending → evaluated via background worker.
- ✅ Calibration stats can be rebuilt and queried; bucket metrics are deterministic and JSON-safe.
- ✅ Calibration adjustment obeys invariants: floor/ceil, caps, renormalization; never applies when `n<30`.
- ✅ No changes to engines/aggregator/conflict_resolver/scenario_builder/interaction rules; module remains autonomous (no Meta/Trading coupling).
