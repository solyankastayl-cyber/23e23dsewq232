# TA Module — Backend API Contract (Phase A.1)

> **Status:** Phase A.1 Complete · Backend Namespace via alias layer
> **Owner:** TA / Trading vertical
> **Source of truth:** `/app/backend/modules/ta_module/ta_namespace.py`

---

## 1. Goal

Establish a clean module boundary for the TA / Trading vertical (analysis ·
prediction · decision · execution · analytics · admin) by exposing every
TA-related endpoint under a single canonical prefix:

```
/api/ta/*
```

while keeping every legacy URL working **bit-for-bit identical**. One handler,
two valid URLs, identical response.

This is **Phase A.1** of the integration plan in `plan_project.md`. It is
intentionally minimal — no handler is duplicated, no response shape is
changed, no router file is moved.

---

## 2. Implementation

A tiny ASGI middleware (`TANamespaceAliasMiddleware`) rewrites the inbound
request path **before** FastAPI dispatches routing. The downstream handler
receives the legacy path and answers exactly as it always has. The middleware
is order-sensitive: most-specific rule first.

```
modules/ta_module/
├── __init__.py
└── ta_namespace.py    ← TA_ALIAS_RULES + middleware + install()
```

Mounted in `server.py` immediately after CORS:

```python
from modules.ta_module.ta_namespace import install_ta_namespace_alias
install_ta_namespace_alias(app)
```

---

## 3. Canonical → Legacy mapping (Phase A.1)

| Canonical                              | Legacy                          | Notes                                     |
| -------------------------------------- | ------------------------------- | ----------------------------------------- |
| `/api/ta/runtime/trace/{...}`          | `/api/trace/{...}`              | special-case — trace lives at top-level   |
| `/api/ta/runtime/decisions/{...}`      | `/api/runtime/decisions/{...}`  | falls naturally out of `/api/ta/runtime/` |
| `/api/ta/runtime/{...}`                | `/api/runtime/{...}`            | catch-all for runtime                     |
| `/api/ta/analytics/{...}`              | `/api/analytics/{...}`          |                                           |
| `/api/ta/learning/{...}`               | `/api/learning/{...}`           |                                           |

**Verified equivalence (curl smoke test, executed 2026-05-01):**

| Canonical                             | Legacy                          | Status        |
| ------------------------------------- | ------------------------------- | ------------- |
| `/api/ta/runtime/state`               | `/api/runtime/state`            | ✅ identical  |
| `/api/ta/runtime/trace/latest`        | `/api/trace/latest`             | ✅ identical  |
| `/api/ta/runtime/decisions/pending`   | `/api/runtime/decisions/pending`| ✅ identical  |
| `/api/ta/analytics/decision-quality`  | `/api/analytics/decision-quality`| ✅ identical |
| `/api/ta/learning/health`             | `/api/learning/health`          | ✅ identical  |

---

## 4. Already-canonical TA routes (NOT touched by alias)

These were already exposed under `/api/ta/...` or `/api/ta-...` and remain
canonical:

* `GET  /api/ta/research`
* `GET  /api/ta/setup` · `GET /api/ta/setup/v2`
* `GET  /api/ta/ideas/*`
* `GET  /api/ta/debug` · `GET /api/ta/indicators/*` · `GET /api/ta/confluence`
* `*    /api/ta-engine/*`           — TA engine internals
* `*    /api/ta-prediction-intelligence/*` — Prediction Intelligence

A future Phase A.x may consolidate the dashed `ta-engine` /
`ta-prediction-intelligence` namespaces under `/api/ta/engine/*` and
`/api/ta/prediction/*`, again with alias-only migration.

---

## 5. Hard rules for Phase A.1

* ❌ Do not delete legacy endpoints.
* ❌ Do not change a single response field (no rename, no removal, no
  reorder).
* ❌ Do not modify the frontend in this phase.
* ❌ Do not add new business logic in `ta_namespace.py` — it is a pure
  path-rewriter.

* ✅ Adding new alias rules is allowed (append to `TA_ALIAS_RULES`).
* ✅ Adding new canonical-only TA routers under `/api/ta/...` is allowed and
  encouraged — they will simply not be matched by the alias.

---

## 6. Verification (smoke test you can re-run)

```bash
URL=http://localhost:8001
for pair in \
    "/api/runtime/state                            /api/ta/runtime/state" \
    "/api/trace/latest                             /api/ta/runtime/trace/latest" \
    "/api/runtime/decisions/pending                /api/ta/runtime/decisions/pending" \

## 9. Phase A.3 Step 1 — Analytics migration (2026-05-01)

**Migrated hooks (6):**

| Hook file                                   | Before (legacy)                                   | After (canonical)                       |
| ------------------------------------------- | ------------------------------------------------- | --------------------------------------- |
| `hooks/analytics/useDecisionAnalytics.js`   | `fetch('/api/analytics/decisions/summary')`       | `taAnalytics.decisions.getSummary()`    |
| `hooks/analytics/useDecisionQuality.js`     | `fetch('/api/analytics/decision-quality')`        | `taAnalytics.getDecisionQuality()`      |
| `hooks/analytics/useExecutionAnalytics.js`  | `fetch('/api/analytics/execution/summary')`       | `taAnalytics.getExecutionSummary()`     |
| `hooks/analytics/useSafetyAnalytics.js`     | `fetch('/api/analytics/safety/summary')`          | `taAnalytics.getSafetySummary()`        |
| `hooks/analytics/useDynamicRiskAnalytics.js`| `fetch('/api/analytics/dynamic-risk/summary')`    | `taAnalytics.getDynamicRiskSummary()`   |
| `hooks/analytics/useAdaptiveRiskAnalytics.js`| `fetch('/api/analytics/adaptive-risk/summary')`  | `taAnalytics.getAdaptiveRiskSummary()`  |

**Small upgrades shipped alongside:**

* `credentials: 'include'` added to `_request` — forwards cookies for any
  auth/session-based handler (cheap insurance).
* `taAnalytics.*` methods now accept an optional `opts` argument so callers
  can pass `{ signal }` for AbortController (used by `useAdaptiveRiskAnalytics`
  to preserve its 5-second timeout semantics).

**Verification:**

Live Playwright network-tab capture on `/terminal`:

```
CANONICAL (/api/ta/analytics/*) hits: 4
  /api/ta/analytics/decisions/summary   ×2
  /api/ta/analytics/decision-quality    ×2
LEGACY    (/api/analytics/*)   hits: 0
```

Static grep across `frontend/src/`:

* Active `/api/analytics/` fetches outside `taService.js`: **0**
* Remaining references: **5 in code-comments only** (documentation, not
  behaviour).

External interface of each hook is unchanged (same return shape, same loading
semantics, same polling intervals).

**Boundaries of this step:**

* ❌ `/api/runtime/*` not touched.
* ❌ `/api/trace/*`  not touched.
* ❌ `/api/learning/*` not touched.
* ❌ Zero AnalyticsWorkspace or UI component files modified — only the hook
  implementations.

    "/api/analytics/decision-quality               /api/ta/analytics/decision-quality" \
    "/api/learning/health                          /api/ta/learning/health"
do
    LEG=$(echo $pair | awk '{print $1}')
    NEW=$(echo $pair | awk '{print $2}')
    A=$(curl -s -m 5 $URL$LEG)
    B=$(curl -s -m 5 $URL$NEW)
    [ "$A" = "$B" ] && echo "OK   $NEW" || echo "DIFF $NEW"
done
```

Expected: `OK` on every line.

---

## 7. Phase roadmap

| Phase | Status | Scope                                                                              |
| ----- | ------ | ---------------------------------------------------------------------------------- |
| A.1   | ✅ Done | Backend namespace `/api/ta/*` via ASGI alias middleware (one handler, two URLs). |
| A.2   | ✅ Done | Canonical HTTP client `frontend/src/modules/ta/services/taService.js` — UI points here. |
| A.3.1 | ✅ Done | Step 1 · Analytics migration — 6 hooks moved to `taAnalytics.*`. Zero legacy /api/analytics/* fetches remain. |
| A.3.2 | ✅ Done | Step 2 · Learning migration — `useLearningInsights` + `ShadowMLDashboard` routed through `taLearning.*`. Zero legacy /api/learning/* fetches remain (client side). |
| A.3.3 | ✅ Done | Step 3 · Trace migration — `DecisionsWorkspace` + `DecisionTraceView` routed through `taTrace.*`. Zero legacy /api/trace/* fetches remain. |
| A.3.4.1 | ✅ Done | Step 4.1 · Read-only runtime — `runtime/state` + `daemon/status` migrated. Zero legacy read-only runtime fetches remain. |
| A.3.4.2 |        | Step 4.2 · Safe operator actions — `daemon/start`, `daemon/stop`, `runtime/run-once`. |
| A.3.4.3 |        | Step 4.3 · Decision lifecycle — `decisions/{id}/approve`, `decisions/{id}/reject`, `/decisions/{id}/note`. |
| A.4   |        | React-Query / SWR adapter for cached subscriptions.                               |
| B.1   |        | Module input/output contract (`signal`, `decision`, `execution intent`).          |
| B.2   |        | Unify signal/decision schema across producers.                                    |
| C     |        | Terminal as canonical entry point (single header · 8 tabs — already live).        |
| D     |        | Wire TA into platform module registry.                                            |
| E     |        | Cross-module events (`SIGNAL_CREATED`, `DECISION_APPROVED`, `TRADE_EXECUTED`).    |

---

## 8. Phase A.2 — Service layer (2026-05-01)

**Added files**

```
frontend/src/modules/ta/services/
├── taService.js    ← canonical HTTP client (runtime · trace · analytics · learning · raw escape hatch)
├── index.js        ← public re-exports
└── README.md       ← usage + rules + migration guidance
```

**Idempotency guard on backend middleware**

`TANamespaceAliasMiddleware.dispatch()` now:

* skips if `request.scope["_ta_namespace_rewritten"]` is truthy (defends
  against future middleware chain changes);
* refuses double-prefixed paths (`/api/ta/ta/...`) rather than silently
  rewriting them — returns a clean 404 that surfaces the bug to the caller.

Verified: `GET /api/ta/ta/runtime/state → 404`.

**taService surface**

* `taRuntime`  — state, start, stop, setMode, setSymbols, setInterval,
  runOnce, `decisions.{listPending, approve, reject}`,
  `daemon.{start, stop, getStatus}`, `risk.{getStatus, reset}`.
* `taTrace`    — `getLatest`, `getStats`, `getById`, `getBySymbol`.
* `taAnalytics` — `getDecisionQuality`, `getDynamicRiskSummary`,
  `getDynamicRiskReasons`, `getExecutionSummary`, `getSafetySummary`,
  `getAdaptiveRiskSummary`, `decisions.{getSummary, getOutcome}`.
* `taLearning` — `getHealth`, `getInsights`, `submitOutcome`, `getMetrics`,
  `getOutcomes`, `getSummary`.
* `taRaw`      — low-level GET/POST/PUT/DELETE escape hatch for endpoints
  not yet promoted into typed namespaces.

**Call-site migration**

*Not started in A.2.* Rule of thumb going forward:

* New code — import from `modules/ta/services`; never `fetch('/api/...')`
  directly.
* Bug-fix touching a call site — migrate it opportunistically.
* No global rewrite pass yet — that's Phase A.3.

---

_Last updated: 2026-05-01 · Phase A.1 alias layer · 5 prefix groups,
0 handler duplication, 0 response-shape change._

## 10. Phase A.3 Step 2 — Learning migration (2026-05-01)

**Migrated call-sites (2 files, 5 fetches):**

| File                                          | Fetches  | Canonical routes                                         |
| --------------------------------------------- | -------- | -------------------------------------------------------- |
| `hooks/analytics/useLearningInsights.js`      | 1        | `taLearning.getInsights()`                               |
| `pages/ShadowMLDashboard.jsx`                 | 4        | `taLearning.shadow.{getStatus, getStats, getPredictions, getEvaluation}` |

**Small upgrades shipped alongside:**

* Dev-only console tracing added to `_request`:
  `console.debug('[TA API]', method, url)` fires in `NODE_ENV === 'development'`
  only — zero cost in production builds.
* `taLearning` namespace extended:
  * `shadow.getStatus()` · `shadow.getStats(horizon)` ·
    `shadow.getPredictions(limit)` · `shadow.getEvaluation(horizon)` ·
    `shadow.getCalibration(snapshotId, horizon)` ·
    `shadow.train(payload)` / `shadow.infer(payload)` (admin-only).
  * All methods accept optional `opts` (e.g. `{ signal }`).

**Error-semantic preservation (important):**

`ShadowMLDashboard` uses `Promise.all([...])`; if any call threw the whole
dashboard would flip to an error state, whereas the legacy implementation
silently tolerated 404s by passing the 404 body through and gating on
`if (xxxRes.ok)`. A tiny `_safeShadowCall()` helper was added inside the
component so the new typed wrappers still deliver the legacy `{ok: false, ...}`
envelope on non-2xx — dashboard behaviour is bit-for-bit identical.

**Verification:**

Live Playwright network-tab capture on `/shadow-ml`:

```
CANONICAL (/api/ta/learning/*) hits: 8
  /api/ta/learning/shadow/status             ×2
  /api/ta/learning/shadow/stats?horizon=7d   ×2
  /api/ta/learning/shadow/eval/7d            ×2
  /api/ta/learning/shadow/predictions?limit=10 ×2
LEGACY    (/api/learning/*)   hits: 0
```

(×2 each because of React StrictMode double-render in dev.)

Static grep across `frontend/src/`:

* Active `/api/learning/` client-side fetches outside `taService.js`: **0**.
* Remaining references in `src/core/learning/routes/*.ts`, `src/api/routes.ts`,
  `src/core/learning_control/*.ts` are **server-side Fastify route
  definitions** of a sidecar service embedded in the frontend repo — they
  are OUT OF SCOPE for client-side migration (they define routes, they don't
  fetch them).

**Boundaries of this step:**

* ❌ `/api/runtime/*` not touched.
* ❌ `/api/trace/*` not touched.
* ❌ Fastify sidecar route definitions not touched.
* ❌ Decisions approve/reject not touched.
* ✅ External hook interfaces unchanged — callers see identical API.


## 11. Phase A.3 Step 3 — Trace migration (2026-05-01)

**Migrated call-sites (2 files, 4 fetches):**

| File                                                      | Fetches | Canonical routes                          |
| --------------------------------------------------------- | ------- | ----------------------------------------- |
| `components/terminal/workspaces/DecisionsWorkspace.jsx`   | 2       | `taTrace.getLatest({limit:30})`, `taTrace.getStats()` |
| `components/terminal/trace/DecisionTraceView.jsx`         | 2       | `taTrace.getLatest({limit:20})`, `taTrace.getStats()` |

**Small upgrade shipped alongside:**

* `taTrace.getLatest()` now accepts an `opts` object including an optional
  `limit` query parameter: `taTrace.getLatest({ limit: 30, signal })`. Other
  trace methods (`getStats`, `getById`, `getBySymbol`) also accept `opts` for
  consistency.

**Explicitly NOT touched in this step (Step 4 territory):**

Both workspaces contain adjacent runtime fetches that were left as-is:

* `fetch('/api/runtime/daemon/status')` — polled every 5s
* `fetch('/api/runtime/daemon/start'|'stop')` — toggle button
* `fetch('/api/runtime/decisions/:id/approve'|'reject')` — approve/reject
* `fetch('/api/decisions/:id/note')` — operator note

These surface the most side-effectful API calls in the codebase
(start/stop/approve/reject) and get their own dedicated migration in Step 4.

**Verification:**

Live Playwright network capture on `/terminal` → Decisions tab (3 polling
ticks at 5s):

```
CANONICAL (/api/ta/runtime/trace/*) hits: 6
  /api/ta/runtime/trace/latest?limit=30  ×3
  /api/ta/runtime/trace/stats            ×3
LEGACY    (/api/trace/*)            hits: 0

(info) runtime.* untouched hits:
  /api/runtime/daemon/status  ×3
```

Static grep across `frontend/src/`:

* Active `/api/trace/` fetches outside `taService.js`: **0**
* Remaining references: none in JSX, only internal module consts/comments.

**Functional spot-check:**

Decisions workspace render confirmed on `/terminal`:

* 4-metric summary (Decisions / Executed / Pending / Rejected) loads
* "System is paused · No decisions yet" empty-state renders correctly
* Polling at 5s cadence (3 tick observed in trace → matches expected)

**Boundaries of this step:**

* ❌ `/api/runtime/*` not touched.
* ❌ Approve/Reject/Note/Start/Stop — not touched.
* ❌ `/api/decisions/*` (operator note) — not touched (different prefix).
* ✅ External component interface unchanged; consumers see identical API.
* ✅ Legacy `/api/trace/*` still works end-to-end via alias (backend contract
  is unchanged, only client call pattern moved).


## 12. Phase A.3 Step 4.1 — Read-only runtime migration (2026-05-01)

**Scope:** the *read-only* slice of `/api/runtime/*`. Write-side endpoints
(`daemon/start|stop`, `run-once`, `decisions/{id}/{approve, reject}`, note)
are explicitly out of scope and migrate in Step 4.2 / 4.3.

**Migrated call-sites (5 files, 5 fetches):**

| File                                                      | Fetch                              | Canonical                         |
| --------------------------------------------------------- | ---------------------------------- | --------------------------------- |
| `hooks/runtime/useRuntimeState.js`                        | `fetch('/api/runtime/state')`      | `taRuntime.getState()`            |
| `components/terminal/ContextStrip.jsx`                    | `fetch('/api/runtime/state', {signal})` | `taRuntime.getState({signal})` (5s abort preserved) |
| `components/ta-overview/TAOverviewPanel.jsx`              | `safeGet('/api/runtime/state')` (axios) | `safeTaGet(taRuntime.getState())` |
| `components/terminal/workspaces/DecisionsWorkspace.jsx`   | `fetch('/api/runtime/daemon/status')` | `taRuntime.daemon.getStatus()` |
| `components/terminal/trace/DecisionTraceView.jsx`         | `fetch('/api/runtime/daemon/status')` | `taRuntime.daemon.getStatus()` |

**Small upgrade shipped alongside:**

* All `taRuntime.*` methods (read + write) now accept an optional `opts`
  argument (`{ signal, headers, ... }`) so callers can wire in their own
  AbortControllers — used by `ContextStrip` to keep its 5-second abort
  semantics intact.

**Explicitly NOT touched (Step 4.2 / 4.3 territory):**

```
POST /api/runtime/daemon/start   ← Step 4.2 (write — daemon control)
POST /api/runtime/daemon/stop    ← Step 4.2
POST /api/runtime/run-once       ← Step 4.2
POST /api/runtime/decisions/{id}/approve  ← Step 4.3
POST /api/runtime/decisions/{id}/reject   ← Step 4.3
POST /api/decisions/{id}/note             ← Step 4.3 (different prefix; out-of-scope for /api/ta)
```

Verified still on legacy via grep (5 untouched fetches in
`useRuntimeActions.js`, `cockpit/services/api.js`, `DecisionsWorkspace.jsx`,
`DecisionTraceView.jsx`).

**Verification:**

Live Playwright network capture on `/terminal` → Decisions tab (3 polling
ticks):

```
CANONICAL /api/ta/runtime/state         : 0 hits (component not on this page; covered by static grep instead)
CANONICAL /api/ta/runtime/daemon/status : 3 hits  ✓
LEGACY    /api/runtime/state            : 0 hits  ✓
LEGACY    /api/runtime/daemon/status    : 0 hits  ✓
LEGACY write-side runtime               : 0 hits  ✓ (no operator action triggered)
```

Static grep across `frontend/src/`:

* Active `/api/runtime/state` fetches outside `taService.js`: **0**
* Active `/api/runtime/daemon/status` fetches outside `taService.js`: **0**

**Functional spot-check:**

* `/terminal` → Decisions tab renders correctly:
  - "System is paused" status string sourced from `daemon.getStatus()` ✓
  - 4-metric strip (Decisions / Executed / Pending / Rejected) populated from
    trace stats ✓
  - 5s polling cadence preserved (3 ticks observed) ✓

**Boundaries of this step:**

* ❌ daemon/start, daemon/stop — not touched
* ❌ run-once — not touched
* ❌ approve, reject, note — not touched
* ❌ payload, polling cadence, error handling, UX — unchanged
* ✅ External hook/component interfaces — bit-for-bit identical
* ✅ Legacy URLs still served via alias — backend contract unchanged

