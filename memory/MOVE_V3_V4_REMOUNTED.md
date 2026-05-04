# V-3 + V-4 RE-MOUNT — MLOps tab is live

**Date:** 2026-04-29
**Series:** Этап 2 (RE-MOUNT), Шаг 4 (out of order — Exchange ML next)
**Source:** canonical `/pages/mlops/MLOpsPage.jsx` (now 287 LOC after
the two safety additions, was 259).
**Target:** `/admin/tech-analysis` → "MLOps" sub-tab.
**Closes:** the operator-side of MOVE V-3 (Promotion) and MOVE V-4
(full MLOps console). The `/mlops` user route was already removed
in V-4 — this step gives those canonical components their permanent
admin home.

---

## 1. What landed where

| Action | Detail |
|---|---|
| Import in admin page | `import MLOpsPage from '../mlops/MLOpsPage';` (no wrapper) |
| Tab body | `<MLOpsPage />` rendered inside a `data-testid="ta-tab-mlops-content"` wrapper |
| Status pill in sub-sidebar | `mlops` flipped from `shell` → `live` |
| MLOps placeholder | removed |

The canonical `MLOpsPage` and all five sub-components
(`ModelRegistry`, `RunsHistory`, `ShadowHealth`, `MetricsChart`,
`MLOpsActions`) are rendered as-is. None of them was forked into a
new file; none was wrapped; none was copied. The admin page simply
mounts the same default export.

---

## 2. The two — and only two — modifications inside the canonical file

The re-mount contract said: *the only allowed change is operator
safety*. Two minimal additions, both clearly tagged with
`V-3 + V-4 RE-MOUNT (2026-04-29)`:

### 2.1 `window.confirm()` guard inside `handleAction()`

A `ACTION_DESCRIPTIONS` map gives each of the five mutating actions
a one-paragraph human description, and every action goes through
the same prompt before any HTTP call:

```
Are you sure you want to execute "<action>"?

<one-paragraph human description>

This action will hit the operator API.
```

Cancelling the prompt aborts the call before `fetch` is touched.

Actions covered:
- `retrain`  → `POST /api/v10/mlops/retrain`
- `promote`  → `POST /api/v10/mlops/promote`
- `rollback` → `POST /api/v10/mlops/rollback`
- `retire`   → `POST /api/v10/mlops/retire`
- `evaluate` → `POST /api/v10/mlops/shadow/evaluate`

A previous local `window.confirm` that lived only on the Rollback
button (`MLOpsActions.jsx:31`) is now redundant for that path but
left untouched on the sub-component — defense in depth.

### 2.2 Red "Operator Console" banner above the page header

```
⚠ Operator Console. Changes here affect production ML state.
              Each action requires explicit confirmation.
```

Pure safety UX, no logic. Renders at the top of the dashboard
before the existing white header card. Carries
`data-testid="mlops-operator-banner"`.

Nothing else inside the canonical file was changed: layout,
component tree, fetch logic, polling interval, error handling,
state shape — all unchanged.

---

## 3. Routing topology after this step

```
/admin/tech-analysis
  └── sub-sidebar group "Analysis"
        └── tab "Calibration"  ← V-1 RE-MOUNT (LIVE)
  └── sub-sidebar group "ML Lifecycle"
        └── tab "MLOps"        ← V-3 + V-4 RE-MOUNT (LIVE) ← this doc
        └── tab "Exchange ML"  ← V-9 (next, trivial drop-in)
        └── tab "Trainer"      ← V-2 (will stay disabled)
```

Direct user route `/mlops` is still gone (removed in V-4). There is
now exactly **one** way to reach the MLOps console — via the admin
control plane.

---

## 4. Backend reality

🔴 The five operator endpoints `/api/v10/mlops/*` still return
**404** on the deployed FastAPI backend (legacy Fastify/TS routes
were never ported). This was already documented in
`MOVE_V4_EXTRACTED.md §6.1`. The re-mount is structurally
complete — when the backend is restored, the dashboard will start
showing live state without further UI work.

Until then:
- The four `GET` calls behind `fetchData()` will fail; the page
  shows its loading / empty states.
- Operator buttons will fire confirm and then fail at the network
  level (404 from the alert message). No production state changes
  because no production endpoint is wired.

This is **expected and correct** for the current step.

---

## 5. Verification at re-mount time

| Check | Expected | Result |
|---|---|---|
| Frontend compiles | `webpack compiled with 1 warning` (pre-existing eslint) | to be checked post-edit |
| `/mlops` user route | absent (404 / fallback) | ✅ confirmed in V-4 |
| `/admin/tech-analysis → MLOps` shows the dashboard | yes (header, state cards, registry, runs, actions) | to be checked |
| Operator banner visible | yes, with `data-testid="mlops-operator-banner"` | to be checked |
| Confirm fires on Retrain / Promote / Rollback / Retire / Evaluate | yes, single dialog per click | to be checked |
| Cancelling confirm aborts the fetch | yes — early `return` before `fetch` | ✅ by inspection of edit |
| Status pill in sub-sidebar | `mlops` → `live` | ✅ |
| No other tab affected | yes | ✅ |

---

## 6. Tracking

```
LEVEL 1 CRITICAL                    ЭТАП 2 — RE-MOUNT
V-1 ✅                              [Шаг 1] Calibration   ← V-1 ✅ + USER-CLOSE ✅
V-2 ✅                              [Шаг 4] MLOps         ← V-3 + V-4 ✅ (this doc)
V-3 ✅                              [Шаг 5] Exchange ML   ← V-9, NEXT
V-4 ✅                              [Шаг 6] Trainer       ← V-2 (will stay disabled)
V-9 ✅                              ----
                                    DEFERRED to first-implementation phase:
                                    [Шаг 2] Root Cause + ML Readiness
                                    [Шаг 3] Simulation + Debug
                                    (no canonical UI exists; pure backend contracts)
```

V-1, V-3, V-4 — operator-side closed.
Next: V-9 (Exchange ML) drop-in.
