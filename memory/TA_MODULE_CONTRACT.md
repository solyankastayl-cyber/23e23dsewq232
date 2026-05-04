# TA Module — Contract

> **Status:** Phase A — 100% DONE · Phase B — this document · code freeze for isolation layer.
> **Created:** 2026-05-01 · after Step 4.2B + duplicate cleanup.
> **Sources of truth:** `frontend/src/modules/ta/services/taService.js`, `backend/modules/ta_module/ta_namespace.py`, `plan_project.md`.
>
> **This is a contract, not a description.** Use imperative voice. If something here disagrees with code, the code is wrong — open an issue.

---

## 1. Overview

TA Module = the autonomous analytics + decision-execution core of the trading platform.

It owns:

* signal generation (engines, aggregator, conflict resolver, scenarios)
* prediction intelligence (calibration, learning observer, decision intelligence)
* decision lifecycle (pending → approve / reject / note → execution)
* runtime control (engine start/stop/mode + daemon scheduler)
* trace + analytics + learning read-paths

It does NOT own:

* operator tooling (cockpit) — separate module
* exchange adapters / order routing internals — used, not owned
* auth / billing / system control — host-app concerns

For full boundaries see `TA_MODULE_BOUNDARIES.md`.

---

## 2. Boundaries

See **`TA_MODULE_BOUNDARIES.md`**. That file is the gating doc for any PR touching TA.

---

## 3. Canonical Backend API — `/api/ta/*`

**Rule:** every TA HTTP route MUST be reachable under `/api/ta/*`. Aliasing to legacy paths is implementation detail (see `ta_namespace.py`).

### 3.1 Runtime control (engine)

```
GET  /api/ta/runtime/state                     → current engine state
POST /api/ta/runtime/start                     → engine ON
POST /api/ta/runtime/stop                      → engine OFF
POST /api/ta/runtime/mode      body {mode}     → set MANUAL | SEMI_AUTO | AUTO
POST /api/ta/runtime/symbols   body {symbols}  → universe replace
POST /api/ta/runtime/interval  body {interval_sec}
POST /api/ta/runtime/run-once                  → one cycle (manual)
```

Response shape (all): `{ ok: bool, message: str, ...state }` where `state` carries `enabled, mode, status (IDLE|RUNNING|STOPPED), loop_interval_sec, symbols, last_run_at, next_run_at, last_error, updated_at`.

### 3.2 Daemon (background scheduler)

```
GET  /api/ta/runtime/daemon/status   → { ok, is_running, cycles_count, started_at, uptime_sec, last_error }
POST /api/ta/runtime/daemon/start    → background loop ON
POST /api/ta/runtime/daemon/stop     → background loop OFF
```

### 3.3 Decisions lifecycle

```
GET  /api/ta/runtime/decisions/pending                     → { ok, decisions[] }
POST /api/ta/runtime/decisions/{id}/approve                → { ok, result: { ok, job_id } }
POST /api/ta/runtime/decisions/{id}/reject  body {reason}  → { ok }
POST /api/ta/decisions/{id}/note            body {note}    → { ok, decision_id }
```

**Payload keys are non-negotiable:** `reason`, `note`. Not `text`, not `content`, not `message`.

### 3.4 Trace

```
GET /api/ta/runtime/trace/latest             ?limit=N
GET /api/ta/runtime/trace/stats
GET /api/ta/runtime/trace/{trace_id}
GET /api/ta/runtime/trace/symbol/{symbol}
```

### 3.5 Analytics

```
GET /api/ta/analytics/decision-quality
GET /api/ta/analytics/dynamic-risk/summary
GET /api/ta/analytics/dynamic-risk/reasons
GET /api/ta/analytics/execution/summary
GET /api/ta/analytics/safety/summary
GET /api/ta/analytics/adaptive-risk/summary
GET /api/ta/analytics/decisions/summary
GET /api/ta/analytics/decisions/outcome/{decision_id}
```

### 3.6 Learning

```
GET  /api/ta/learning/health
GET  /api/ta/learning/insights
GET  /api/ta/learning/metrics
GET  /api/ta/learning/summary
GET  /api/ta/learning/outcomes               ?params
POST /api/ta/learning/outcome
GET  /api/ta/learning/shadow/status
GET  /api/ta/learning/shadow/stats           ?horizon=7d
GET  /api/ta/learning/shadow/predictions     ?limit=10
GET  /api/ta/learning/shadow/eval/{horizon}
GET  /api/ta/learning/shadow/calibration/{snapshotId}/{horizon}
POST /api/ta/learning/shadow/train           ⚠ admin-only surface
POST /api/ta/learning/shadow/infer           ⚠ admin-only surface
```

### 3.7 Risk

```
GET  /api/ta/runtime/risk-status
POST /api/ta/runtime/risk-reset
```

### 3.8 Namespace mapping (implementation, MAY change)

The alias rules (in `ta_namespace.py`, ASGI middleware) are:

| Canonical prefix | Aliased to |
|---|---|
| `/api/ta/runtime/trace/*` | `/api/trace/*` |
| `/api/ta/runtime/*` | `/api/runtime/*` |
| `/api/ta/analytics/*` | `/api/analytics/*` |
| `/api/ta/learning/*` | `/api/learning/*` |
| `/api/ta/decisions/*` | `/api/decisions/*` |

Clients MUST NOT depend on the alias being a transparent proxy beyond byte-identical responses; the legacy paths can be retired in Phase C.

---

## 4. Frontend public API — `taService`

**Import path:** `frontend/src/modules/ta/services/taService.js` (barrel: `frontend/src/modules/ta/services/index.js`).

**Rule:** all TA HTTP traffic MUST go through this module. Direct `fetch('/api/...')` for any TA-owned route is forbidden (see Boundaries).

### 4.1 Surface

```js
import { taRuntime, taTrace, taAnalytics, taLearning, taRaw, TA_API_ROOT }
  from 'modules/ta/services';
```

### 4.2 `taRuntime`

```js
taRuntime.getState()
taRuntime.start()
taRuntime.stop()
taRuntime.setMode(mode)         // "MANUAL" | "SEMI_AUTO" | "AUTO"
taRuntime.setSymbols(symbols)   // string[]
taRuntime.setInterval(seconds)
taRuntime.runOnce()

taRuntime.daemon.start()
taRuntime.daemon.stop()
taRuntime.daemon.getStatus()

taRuntime.decisions.listPending()
taRuntime.decisions.approve(decisionId)
taRuntime.decisions.reject(decisionId, reason)   // reason = '' default
taRuntime.decisions.note(decisionId, noteText)

taRuntime.risk.getStatus()
taRuntime.risk.reset()
```

### 4.3 `taTrace`

```js
taTrace.getLatest({ limit })
taTrace.getStats()
taTrace.getById(traceId)
taTrace.getBySymbol(symbol)
```

### 4.4 `taAnalytics`

```js
taAnalytics.getDecisionQuality()
taAnalytics.getDynamicRiskSummary()
taAnalytics.getDynamicRiskReasons()
taAnalytics.getExecutionSummary()
taAnalytics.getSafetySummary()
taAnalytics.getAdaptiveRiskSummary()
taAnalytics.decisions.getSummary()
taAnalytics.decisions.getOutcome(decisionId)
```

### 4.5 `taLearning`

```js
taLearning.getHealth()
taLearning.getInsights()
taLearning.getMetrics()
taLearning.getSummary()
taLearning.getOutcomes(params)
taLearning.submitOutcome(payload)

taLearning.shadow.getStatus()
taLearning.shadow.getStats(horizon = '7d')
taLearning.shadow.getPredictions(limit = 10)
taLearning.shadow.getEvaluation(horizon = '7d')
taLearning.shadow.getCalibration(snapshotId, horizon)
// admin-only:
taLearning.shadow.train(payload)
taLearning.shadow.infer(payload)
```

### 4.6 `taRaw` — escape hatch

Use only when adding a new endpoint **before** it's promoted into a typed namespace. PRs adding `taRaw.*` calls outside `modules/ta/*` are rejected.

```js
taRaw.get(path, opts)
taRaw.post(path, body, opts)
taRaw.put(path, body, opts)
taRaw.delete(path, opts)
```

### 4.7 Error contract

All helpers return parsed JSON on `2xx`. On non-2xx they throw `Error` with attached `.status`, `.statusText`, `.data`. Callers MUST `try/catch` around any write operation; never silently swallow.

### 4.8 No business logic in transport

`taService` is **pure transport**. It MUST NOT:

* trim / coerce / default user input (callers do that)
* validate enums or schemas
* retry / cache / memoize
* log anything beyond the dev-only debug trace
* hold state

---

## 5. Runtime Model — engine vs daemon (DO NOT CONFUSE)

These are TWO orthogonal control planes. Mixing them = bug.

| Concept | What it controls | Endpoints | Frontend surface |
|---|---|---|---|
| **Engine (runtime)** | Trading orchestrator: signals → decisions → execution. The thing that produces money/loss. | `/api/ta/runtime/{start,stop,mode,state,symbols,interval}` | `taRuntime.{start,stop,setMode,getState,setSymbols,setInterval}` |
| **Daemon** | Background scheduler loop that calls `run-once` on a tick. Restartable, idempotent. | `/api/ta/runtime/daemon/{start,stop,status}` | `taRuntime.daemon.{start,stop,getStatus}` |

**Rules:**

* Stopping the engine ≠ stopping the daemon, and vice versa. They are independent.
* `run-once` is a manual cycle trigger; it does NOT depend on daemon being running.
* UI buttons MUST label them differently. Never mix them under a single "Start" control.
* Service-level helpers MUST live in their respective namespaces (`taRuntime.*` vs `taRuntime.daemon.*`). No shortcuts.

---

## 6. Decision Lifecycle

```
     ┌──────────────────┐
     │  signal pipeline │
     └────────┬─────────┘
              │ creates
              ▼
     ┌──────────────────┐
     │     pending      │  ◀── GET  /api/ta/runtime/decisions/pending
     └─┬─────────┬──────┘
       │         │
  approve     reject
       │         │
       ▼         ▼
  ┌─────────┐ ┌──────────┐
  │ EXECUTING │ REJECTED │
  └─────────┘ └──────────┘
       │
       ▼
   final outcome → analytics + learning
```

* `approve` payload: empty body. Returns `{ok, result: {ok, job_id}}`.
* `reject`  payload: `{reason: string}`. `null` allowed (legacy semantics) but discouraged. UI MUST send a non-empty constant (`OPERATOR_REJECTED`) for operator-initiated rejects.
* `note`    payload: `{note: string}`. Caller `trim()`s. Empty notes are blocked at caller, not service. Applies to any decision regardless of status.
* Lifecycle is irreversible: once approved or rejected, a decision MUST NOT re-enter `pending`.
* `decision_id` is opaque. Never parse, never transform, only `encodeURIComponent`.

---

## 7. Invariants — DO NOT (frozen surfaces)

These are **inherited from `plan_project.md`** and apply to anyone touching TA, including this contract's authors.

### 7.1 Frozen logic — zero mutations

* engines / aggregator / conflict_resolver / ScenarioBuilder
* interaction_adjuster / calibration_adjuster / feature_builder / temporal_buffer / temporal_intelligence / live_adapter
* SimpleMA entry logic
* regime gates

### 7.2 No new strategies without forensic evidence

Every new strategy proposal requires a `scripts/forensic_v2_*.py`-style report attached to the PR. No exceptions.

### 7.3 ML gate

No model training, no inference influencing `/live` responses, no predictor wiring until **`n_evaluated ≥ 500`** per `(symbol, timeframe)` bucket. Monitor via `GET /api/ta-prediction-intelligence/dataset/stats`.

### 7.4 TA Prediction Intelligence stays autonomous

`wired_to_meta = false`. No coupling to MetaBrain, combined_analysis, shadow_*, trading layer, or execution.

### 7.5 Calibration invariants

* `n < 30` → calibration **skip** + honest meta. No fallback values.
* Adjuster MUST preserve: `sum=1`, bounds, caps, floor/ceil, renormalization.
* Calibration history is append-only.

### 7.6 No UI changes that affect contract

* No silent payload renames.
* No new required fields without bumping a version field.
* No removing `legacy fallback` behavior in Phase B (deprecation belongs to Phase C).

---

## 8. Legacy Policy

**Legacy routes are supported for backward compatibility only. They are not a second public API.**

* Legacy routes (`/api/runtime/*`, `/api/trace/*`, `/api/analytics/*`, `/api/learning/*`, `/api/decisions/*`) are **deprecated, but supported**.
* They remain alive as a fallback safety net (e.g. for clients not yet aware of the canonical namespace, including the cockpit module today) — **not** as an equivalent alternative to `/api/ta/*`.
* **New code MUST use `/api/ta/*`.** Direct legacy calls in new code = PR reject. Using a legacy route anywhere requires an explicit justification in the PR description and a `TODO(migration-owner: @name)` comment at the callsite.
* Deprecation, removal, or behavior change of legacy routes is a separate phase (Phase C) and requires its own contract revision.
* Backend handlers stay at their legacy paths; the canonical namespace is alias-only. This is implementation detail, not contract.

---

## 9. Integration

### 9.1 Environment

* Backend reads `MONGO_URL`, `DB_NAME` (default `trading_os`), `JWT_SECRET`, `EXCHANGE_MODE`.
* Frontend reads `REACT_APP_BACKEND_URL` at build time (`taService` derives the API root from it).
* `EXCHANGE_MODE=PAPER` is the only safe default. `LIVE` requires architect approval per PR.

### 9.2 MongoDB collections owned by TA

Reads + writes (TA owns the schema):

* `pending_decisions` · `decision_outcomes` · `runtime_audit`
* `trade_traces` (or equivalent — current name in `decision_outcome` module)
* `trading_cases` · `position_exit_events` · `regime_*`
* `ta_prediction_*` family (calibration, learning, dataset, decision_intel)

Reads only (other modules own):

* `auth_*` · `experiments` · `worker_heartbeats` · `auto_safety_*`

### 9.3 Supervisor processes

* `backend` (FastAPI on `:8001`) — must bind `0.0.0.0`, `/api/*` is required prefix.
* `frontend` (CRA dev or build) — must respect `REACT_APP_BACKEND_URL`.
* MongoDB on `:27017`.
* No TA-specific worker processes outside this list.

### 9.4 Plug-and-play checklist

To lift TA into another host project, the integrator MUST provide:

1. A FastAPI app instance with `install_ta_namespace_alias(app)` invoked at startup.
2. The legacy routers mounted (`runtime`, `trace`, `analytics`, `learning`, `decision_outcome`).
3. `MONGO_URL` reachable to the named collections in §9.2.
4. The `modules/ta/services/taService.js` module imported into the host frontend, with `REACT_APP_BACKEND_URL` pointing at the FastAPI ingress.
5. No edits to TA invariants (§7).

If any of (1)-(5) is violated, behavior is undefined.

---

## 10. Phase Status

| Phase | Scope | Status |
|---|---|---|
| A.1 | Backend canonical namespace `/api/ta/*` (alias middleware) | ✅ DONE |
| A.1.1 | Namespace extension to `/api/ta/decisions/*` | ✅ DONE |
| A.2 | Frontend `taService` (taRuntime/taTrace/taAnalytics/taLearning/taRaw) | ✅ DONE |
| A.3 Step 3 | Trace reads on canonical | ✅ DONE |
| A.3 Step 4.1 | Daemon-status read on canonical | ✅ DONE |
| A.3 Step 4.2A | Daemon start/stop + run-once on canonical | ✅ DONE |
| A.3 Step 4.2B | Engine start/stop/mode on canonical | ✅ DONE |
| A.3 Step 4.3 | Decisions approve/reject/note on canonical | ✅ DONE |
| **A — overall** | **TA isolation 100%** | ✅ **DONE** |
| **B** | **This contract — boundaries + invariants frozen** | ✅ **DONE** (this file) |
| C | Legacy retirement (out of scope today) | ⏳ deferred |
| Cockpit | Operator tooling alignment | ⏳ separate track (A.5) |

---

## 11. Cockpit (out of scope)

The cockpit module (`frontend/src/modules/cockpit/`) is operator tooling, **not part of the TA module**. It currently retains direct legacy calls (`/api/runtime/decisions/{pending,approve,reject}`) and is intentionally untouched by Phase A and Phase B. Aligning cockpit with the canonical namespace is a separate deliverable ("Phase A.5 — Cockpit alignment") and MUST NOT be bundled into TA module work.

---

## 12. Ownership

TA module has a single architectural owner.

Any changes to:

* runtime behavior
* decision lifecycle
* API contract
* invariants

require explicit approval from the owner.
Unowned changes are considered invalid.

---

*End of contract. If you need to change anything above, you are changing the module contract — bump the version, write a migration note, and get architect sign-off.*
