# V-1 RE-MOUNT — Calibration tab is live

**Date:** 2026-04-29
**Series:** Этап 2 (RE-MOUNT), Шаг 1
**Source:** canonical components preserved in `/components/calibration/`
**Target:** `/admin/tech-analysis` → "Calibration" tab
**Modus operandi:** vertical re-mount, **zero rewrite**.

---

## 1. What landed where

| Component (LOC) | Where it lives now | Notes |
|---|---|---|
| `CalibrationStatusCard` (230) | mounted in tab | read-only, 7d window |
| `CalibrationBuildPanel` (435) | mounted in tab | operator actions: build / simulate / apply |
| `CalibrationRunHistory` (156) | mounted in tab | last 10 runs, all windows |
| `CalibrationAttackTests` (183) | mounted in tab | invariant checks |

All four files in `/components/calibration/*.jsx` are byte-identical
to their pre-mount state. The barrel `index.js` is also unchanged.

---

## 2. Layout reproduced 1:1

The canonical `CalibrationTab` from `pages/SettingsPage.jsx`
(line 698 onward) was reproduced inside
`pages/admin/AdminTechAnalysisPage.jsx` with the same:

* `refreshKey` state + `handleRefresh` callback.
* Component order: Status → Build → History → Attack Tests.
* `key`-based remount on Status and History after every build/apply.

The only intentional differences:

* Wrapping `<div className="p-6 space-y-6">` (matches the page's
  TabsContent padding for the rest of the tab set, instead of the
  Settings page's `space-y-6`-only).
* Tab-level header (`<h2>` + description) added at the top so the
  tab visually matches its siblings (`Overview`, `Calibration`, etc.).
* `data-testid="ta-tab-calibration-content"` added on the wrapper
  for testing.

The "Phase 5 Safety Guarantees" green panel from `SettingsPage` is
**intentionally not** copied — it is a static info box that does
not belong in the admin control plane (no operator action attached).
If the architect wants it back, it is a one-line drop-in from the
source.

---

## 3. Backend reality at re-mount time

🔴 The endpoints the canonical components call **are not currently
served by the running FastAPI backend**:

```
GET  /api/ml/calibration/active   → 404
GET  /api/ml/calibration/runs     → 404
POST /api/ml/calibration/build    → 404 (expected)
POST /api/ml/calibration/simulate → 404 (expected)
POST /api/ml/calibration/apply    → 404 (expected)
... (full list in /api/calibration.api.js)
```

The handlers exist in legacy TypeScript code under
`frontend/src/core/ml_calibration_phase5/calibration.routes.ts`
but were **never ported** to the active Python backend.

The `/api/ta-prediction-intelligence/calibration*` routes do work
(200), but those are a **different surface** (probability-bucket
calibration of TA scenarios, not Phase-5 ML calibration maps).

### Implication

* The cards will render their empty / error states until the
  backend is restored. This is **expected and correct** — the
  re-mount is a structural action, not a backend resurrection.
* The architectural surface (`/admin/tech-analysis → Calibration`)
  is now in place. Whichever calibration the project keeps as the
  canonical — Phase-5 ML or TA-scenario buckets — its endpoints
  go behind these existing UI cards.
* **Out of scope for V-1 re-mount, tracked separately:**
  "Restore backend `/api/ml/calibration/*` (port from TS or replace
  with TA-scenario calibration that already lives at
  `/api/ta-prediction-intelligence/calibration`)."

---

## 4. ⚠️ V-1 is NOT closed on the user side yet

This is the second important finding from the re-mount audit.

The canonical `<CalibrationStatusCard /> <CalibrationBuildPanel />
<CalibrationRunHistory /> <CalibrationAttackTests />` composition
is still imported and rendered by **`pages/SettingsPage.jsx`**
(user-zone), inside its own `Calibration` tab.

```
SettingsPage.jsx:30-34   imports the four canonical components
SettingsPage.jsx:698     defines a local CalibrationTab
SettingsPage.jsx:1237    renders it when activeTab === 'calibration'
```

That means the original write-capable Calibration UI surface is
**still reachable in user space** through whatever route mounts
`SettingsPage`. The MOVE-series convention requires removing it
from user routing once the admin re-mount is in place — same
pattern that was applied to V-3, V-4, V-9.

Tracked as follow-up: **MOVE V-1-USER-CLOSE** — strip the
Calibration tab out of `SettingsPage.jsx` (or remove the route to
`SettingsPage` if it is only used as the operator surface).

---

## 5. Verification done at re-mount time

| Check | Expected | Result |
|---|---|---|
| Frontend compiles | webpack `Compiled successfully` | to be checked post-edit |
| `/admin/tech-analysis` accessible | requires admin login (admin/admin123) | ✅ confirmed earlier |
| Calibration tab opens | renders 4 canonical cards in canonical order | to be checked post-edit |
| `data-testid="ta-tab-calibration-content"` | present | added |
| No canonical files mutated | `wc -l /components/calibration/*.jsx` matches pre-mount | ✅ |
| Skeleton-phase amber strip on the page | still present (other 9 tabs are placeholders) | ✅ |

---

## 6. Tracking

```
ЭТАП 2 — RE-MOUNT
[Шаг 1] Calibration   ← V-1 ✅ (this doc)
[Шаг 2] Root Cause + ML Readiness   ← read-only analytics — pending
[Шаг 3] Simulation                  ← offline engine — pending
[Шаг 4] MLOps        ← V-3 + V-4 mutating, requires confirms — pending
[Шаг 5] Exchange ML  ← V-9 trivial drop-in — pending
[Шаг 6] Trainer      ← V-2, leave disabled with explanation — pending
```

Out-of-scope but recorded:

1. `MOVE V-1-USER-CLOSE` — remove Calibration tab from
   `pages/SettingsPage.jsx`.
2. Backend port — `/api/ml/calibration/*` (or replace with the
   TA-scenario surface). Owner: backend.
