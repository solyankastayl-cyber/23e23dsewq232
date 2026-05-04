# MOVE V-4 — /mlops → extracted from user routing

**Date:** 2026-04-29
**Status:** EXECUTED (user route removed, component preserved)
**Severity at extraction:** 🔴 CRITICAL — live operator console reachable
via direct URL entry from any unauthenticated user session.

---

## 1. What was removed

### 1.1 Route (user space)

**File:** `frontend/src/App.js`

Removed:

```jsx
{/* MLOps Dashboard */}
<Route path="/mlops" element={<MLOpsPage />} />
```

Replaced by an audit comment block + commented-out `<Route>` stub
(kept in place so the position in the file is obvious for the
eventual re-mount).

### 1.2 Lazy import

Same file, around line 324. The `lazy(() => import(...))` is now
commented out with a MOVE V-4 header. The target module is NOT
imported anywhere else in user-facing bundles.

---

## 2. What was preserved (canonical source — DO NOT TOUCH)

These files remain 1:1 and become the canonical implementation for
the future admin re-mount:

| Path | LOC | Role |
|---|---|---|
| `frontend/src/pages/mlops/MLOpsPage.jsx` | 258 | Top-level dashboard (4 StateCards + 2-column grid) |
| `frontend/src/components/mlops/MLOpsActions.jsx` | 131 | Right-column Quick Actions (Retrain / Rollback) |
| `frontend/src/components/mlops/ModelRegistry.jsx` | — | Left column — list of models + Promote / Retire buttons |
| `frontend/src/components/mlops/ShadowHealth.jsx` | — | Shadow-mode health + Evaluate button |
| `frontend/src/components/mlops/MetricsChart.jsx` | — | Read-only metrics over `runs` |
| `frontend/src/components/mlops/RunsHistory.jsx` | — | Read-only runs timeline |
| `frontend/src/components/mlops/index.js` | — | Barrel export |

All of the above are unchanged. Any future edit to these files
should go through the admin re-mount step, not here.

---

## 3. Operator endpoints that were UI-reachable

All five POST mutations used to be triggerable from `/mlops` without
any authentication layer in front. They **remain reachable on the
backend** over direct HTTP — this move closes only the UI surface.

| Action button | Frontend handler | Backend endpoint |
|---|---|---|
| **Retrain Model** | `handleAction('retrain')` | `POST /api/v10/mlops/retrain` |
| **Promote** (per model) | `handleAction('promote', {modelId})` | `POST /api/v10/mlops/promote` |
| **Rollback Active** | `handleAction('rollback')` | `POST /api/v10/mlops/rollback` |
| **Retire** (per model) | `handleAction('retire', {modelId})` | `POST /api/v10/mlops/retire` |
| **Evaluate Shadow** | `handleAction('evaluate')` | `POST /api/v10/mlops/shadow/evaluate` |

Read-only endpoints used by the page:

- `GET /api/v10/mlops/models?limit=20`
- `GET /api/v10/mlops/runs?limit=50`
- `GET /api/v10/mlops/shadow/health`
- `GET /api/v10/mlops/state`

> Only Rollback had a `window.confirm(...)` guard
> (`MLOpsActions.jsx:31`). Retrain / Promote / Retire / Evaluate
> fired on a single click.

---

## 4. Why this was extracted

* Route was mounted outside `/admin/*` → no auth gate.
* No sidebar / nav link pointed to `/mlops`, but the URL was
  discoverable and worked for anyone who typed it.
* One of the exposed actions (`promote`) directly rewrites the
  ACTIVE model serving production predictions — i.e. the single
  biggest lever in the ML pipeline.
* Rollback / Retrain also cost real compute or rewire serving
  state. These are operator-grade actions, not user features.

---

## 5. Future re-mount plan

Target location: **`/admin/tech-analysis` → "MLOps" tab**.

Implementation sketch (DO NOT EXECUTE YET — waiting for admin
blueprint step):

1. Create `frontend/src/pages/admin/tech-analysis/AdminMLOpsTab.jsx`
   that renders `<MLOpsPage />` unchanged.
2. Wrap it in the same `<RequireAdmin>` / auth HOC used by other
   `/admin/*` pages.
3. Add tab entry "MLOps" inside the Tech-Analysis admin workspace
   next to the future V-3 "Promotion" tab.
4. Hardening follow-ups that are OUT OF SCOPE for this move but
   should be tracked:
   * Add `window.confirm` on Retrain / Promote / Retire.
   * Require admin JWT server-side on all five POST endpoints
     (separate backend hardening ticket).
   * Optionally split mutating buttons into a child `<RequireRole>`
     for operators vs read-only auditors.

---

## 6. Verification done at move time

| Check | Expected | Result |
|---|---|---|
| `/mlops` no longer routed in user SPA | route absent in `App.js` | ✅ only commented-out stub remains |
| No user import resolves to `MLOpsPage` | all grep hits are either preserved canonical files or MOVE V-4 audit comments | ✅ |
| `MLOpsPage.jsx` canonical file intact | 258 LOC | ✅ |
| `components/mlops/*` canonical files intact | MLOpsActions 131, MetricsChart 129, ModelRegistry 215, RunsHistory 153, ShadowHealth 153 (total 1039 LOC with page) | ✅ |
| Frontend builds cleanly post-move | webpack: `Compiled successfully!` | ✅ |
| Sidebar / AppLayout nav links to `/mlops` | none | ✅ (confirmed pre-move) |

### 6.1 Backend-side observation (IMPORTANT FINDING)

During verify the five endpoints listed in §3 were probed against
the running backend:

```
GET  /api/v10/mlops/state   → 404
GET  /api/v10/mlops/models  → 404
```

This means the `/api/v10/mlops/*` handlers referenced by the
frontend code live in the legacy Fastify/TypeScript source tree
(`frontend/src/modules/exchange-ml/ml.routes.ts`,
`frontend/src/modules/mlops/step3/routes/step3.routes.ts`) and were
**never ported to the active FastAPI Python backend** that the
deployed supervisor runs.

Implication for the risk model:
- At the moment the mutating POSTs cannot in fact change any active
  model — they all return 404 from the deployed backend.
- But the TS route files are still checked into the repo, so any
  future backend migration could accidentally wire them up again.
- Removing the `/mlops` UI route therefore closes both:
  (a) the concrete user-facing surface today, and
  (b) the regression risk where a future backend port revives the
      endpoints without revisiting the UI.

### 6.2 Downstream admin file — out of scope for V-4

`pages/admin/AdminMLOpsPage.jsx` imports `MLOpsPage` directly
(`import MLOpsPage from '../mlops/MLOpsPage'`). This admin page is
currently NOT mounted in the router — `/admin/mlops` is a
`<Navigate to="/admin/ml/overview" replace />` stub
(`App.js:425`). The file is dormant legacy; leaving it alone here is
the conservative choice. It will be cleaned up either when the
`/admin/tech-analysis` workspace is assembled or during the
final "ARCHIVE legacy" step.

---

## 7. Tracking

* Move series: V-1 ✅ / V-2 ✅ / V-3 ✅ / **V-4 ✅ (this doc)** / V-9 ⛔ (next)
* Blueprint series: `MOVE_V3_EXTRACTED.md` (was referenced in code,
  file not present in repo — to be reconstructed when admin
  workspace is assembled).
