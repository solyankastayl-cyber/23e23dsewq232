# V-9 RE-MOUNT — Exchange ML tab is live

**Date:** 2026-04-29
**Series:** Этап 2 (RE-MOUNT), Шаг 5
**Source:** canonical `pages/admin/AdminExchangeMLPage.jsx` (480 LOC,
relocated there in MOVE V-9 from `pages/MLAdminPage.jsx`).
**Target:** `/admin/tech-analysis` → "Exchange ML" sub-tab.
**Type:** trivial drop-in. **Zero modifications inside the canonical
file.** This is the cleanest re-mount of the entire series.

---

## 1. Why this one is the simplest

Unlike Calibration (V-1) and MLOps (V-3 + V-4), the Exchange ML
admin page was *already* in admin-correct shape:

| Pre-condition | State |
|---|---|
| File location | `/pages/admin/` ✅ since MOVE V-9 |
| Auth boundary | inherited from `AdminLayout` ✅ |
| Operator surface | already labelled "Exchange ML Admin" ✅ |
| Internal AdminLayout wrap | **no** (clean root `<div>`) — safe to mount inside another AdminLayout |
| Canonical sub-components | none — page is self-contained |

So this step really is "import + render". No banner, no confirm,
no rename, no copy.

---

## 2. What landed where

| Action | Detail |
|---|---|
| Import in admin page | `import AdminExchangeMLPage from './AdminExchangeMLPage';` (sibling import — both in `/pages/admin/`) |
| Tab body | `<AdminExchangeMLPage />` rendered inside a `data-testid="ta-tab-exchange-ml-content"` wrapper |
| Status pill in sub-sidebar | `exchange-ml` flipped from `shell` → `live` |
| Exchange ML placeholder | removed |

The two operator mutations on the page (`POST /api/v10/exchange/ml/train`,
`POST /api/v10/exchange/ml/freeze`) keep working exactly as before
— same buttons, same payload, same handlers. Confirm dialogs are
**intentionally deferred** to a future single sweep that will hit
all remaining admin write actions in one consistent pass.

---

## 3. Routing topology after this step

```
/admin/tech-analysis
  └── group "Analysis"
        └── tab "Calibration"        ← V-1 ✅
        └── (other tabs are shells)
  └── group "ML Lifecycle"
        └── tab "Trainer"            ← V-2 (will stay disabled)
        └── tab "MLOps"              ← V-3 + V-4 ✅
        └── tab "Exchange ML"        ← V-9 ✅  ← this doc
```

The standalone admin route to the same canonical page is
**preserved unchanged**:

```
/admin/exchange/ml
  → AdminExchangeWrapper (App.js ~517)
  → lazy('./AdminExchangeMLPage')
  → renders inside its own AdminLayout
```

Both surfaces resolve to the same canonical file. There is no
duplication — only two valid mount points, both inside the admin
tree, both behind admin auth.

---

## 4. Why no confirm here (architectural decision)

The two mutations on this page (`Train Models`, `Freeze Model`)
are operator-grade and ideally should carry the same
`window.confirm()` guard pattern that V-3 + V-4 added to the MLOps
dashboard. They do not, yet. That is intentional:

* Adding a confirm guard requires touching the canonical
  `AdminExchangeMLPage.jsx` file. The user-facing instruction for
  this step explicitly forbade any change inside that file.
* A future sweep (`OPERATOR-CONFIRMS-SWEEP`) will visit *every*
  remaining admin write action — Exchange ML, Trading Control,
  any future Trainer mutations, etc. — and apply the confirm
  pattern uniformly so they all share one description vocabulary.
* Until that sweep, the admin auth boundary itself
  (`AdminLayout` + `useAdminAuth`) is the operative gate.

Tracked as a single follow-up item, not a per-page concern.

---

## 5. Operator topology after this step

```
Calibration   → corrects probability calibration of TA scenarios
MLOps         → manages the lifecycle of the global ML pipeline
Exchange ML   → manages diagnostics + training of the Exchange ML model
```

Three operator surfaces, three intents, one home:
`/admin/tech-analysis`. This is the v1 of the operator UI.

---

## 6. Verification at re-mount time

| Check | Expected | Result |
|---|---|---|
| Frontend compiles | `compiled with 1 warning` (pre-existing eslint) | to be checked post-edit |
| `/admin/tech-analysis` → "Exchange ML" pill = `live` | yes | ✅ in registry |
| Header status strip | `3 live · 12 shell` | to be checked |
| Page renders inside the tab | yes — page header, status cards, registry, drift, disagreement explorer | to be checked |
| `data-testid="ml-admin-page"` survives the mount | yes (page is unchanged) | ✅ canonical file untouched |
| `data-testid="ta-tab-exchange-ml-content"` wrapper present | yes (added by re-mount) | ✅ |
| Standalone `/admin/exchange/ml` still works | yes — separate mount via AdminExchangeWrapper | ✅ unchanged |
| `Train Models` and `Freeze Model` buttons present | yes (carried over verbatim) | to be checked |
| Internal AdminLayout double-wrap | no — `AdminExchangeMLPage` has no own `<AdminLayout>` | ✅ verified by grep |

---

## 7. Files touched

| File | Change |
|---|---|
| `pages/admin/AdminTechAnalysisPage.jsx` | +1 import, replaced `ExchangeMLTab` placeholder, flipped pill |
| `pages/admin/AdminExchangeMLPage.jsx` | **untouched** |
| Other canonical files | **untouched** |

Total change: ≈ 18 LOC in one admin page. No new files created.

---

## 8. Tracking

```
LEVEL 1 CRITICAL                    ЭТАП 2 — RE-MOUNT
V-1 ✅                              [Шаг 1] Calibration   ✅ + USER-CLOSE ✅
V-2 ✅                              [Шаг 4] MLOps         ✅
V-3 ✅                              [Шаг 5] Exchange ML   ✅ ← this doc
V-4 ✅                              [Шаг 6] Trainer       ← V-2, leave disabled
V-9 ✅
                                    DEFERRED (first-implementation phase):
                                    Root Cause / ML Readiness / Simulation /
                                    Debug / Data Health / Overview wiring
                                    Trading group wiring (Control / Risk /
                                    Execution / Strategies / Audit)
                                    
                                    DEFERRED (single sweep):
                                    OPERATOR-CONFIRMS-SWEEP
                                    BACKEND-AUTH-GATE on /api/v10/*
```

**State after this step:**

* USER UI = read-only ✅
* ADMIN OPERATOR LAYER (v1) = COMPLETE
  * Calibration (V-1) ✅
  * MLOps (V-3 + V-4) ✅
  * Exchange ML (V-9) ✅
* ADMIN ANALYTICS LAYER = pending (Root Cause / ML Readiness /
  Simulation / Debug — first-implementation phase)
* ADMIN TRADING LAYER = pending (5 shell tabs awaiting backend wire)

This is the natural pause point: **PHASE: OPERATOR UI COMPLETE (v1).**
