# MOVE V-1-USER-CLOSE — Calibration UI removed from user space

**Date:** 2026-04-29
**Closes:** the open follow-up flagged in `MOVE_V1_REMOUNTED.md` §4.
**Result:** V-1 is now **fully closed** — Calibration control surface
exists in exactly one place: `/admin/tech-analysis → Calibration`.

---

## 1. What was removed from `pages/SettingsPage.jsx`

Four touch-points, all in the same user-zone file. The canonical
component files (`/components/calibration/*`) were **not** modified.

### 1.1 Imports

```jsx
// REMOVED
import {
  CalibrationStatusCard,
  CalibrationBuildPanel,
  CalibrationRunHistory,
  CalibrationAttackTests
} from '../components/calibration';
```

Replaced with an audit-comment block of the same shape so the
removal point is grep-friendly. (`grep "MOVE V-1-USER-CLOSE"`).

### 1.2 Tab entry in `TabNav`

```jsx
// REMOVED
{ id: 'calibration', label: 'Calibration', icon: Activity, badge: 'Phase 5' },
```

Replaced with a commented-out stub at the original position, plus
a one-line audit header. The `Activity` lucide icon import was
**kept** — it is still used by other sections of the page (lines
266 and 366), so no dead imports remain.

### 1.3 `function CalibrationTab()` definition (~62 lines)

The whole local function — the four canonical cards plus the
green "Phase 5 Safety Guarantees" tooltip box — was removed and
replaced with a multi-line audit comment that:
- explains the removal,
- lists the canonical component file paths that still own the UI,
- references this blueprint for the full audit trail.

### 1.4 Render guard in `<main>`

```jsx
// REMOVED
{activeTab === 'calibration' && <CalibrationTab />}
```

Even if a stale URL or saved state still sets `activeTab` to
`'calibration'` after this change, no panel renders — the page
falls through to a no-op. That is the safe behaviour.

---

## 2. What was NOT touched (by design)

| Surface | State | Why |
|---|---|---|
| `components/calibration/CalibrationStatusCard.jsx` (230 LOC) | unchanged | canonical |
| `components/calibration/CalibrationBuildPanel.jsx` (435 LOC) | unchanged | canonical |
| `components/calibration/CalibrationRunHistory.jsx` (156 LOC) | unchanged | canonical |
| `components/calibration/CalibrationAttackTests.jsx` (183 LOC) | unchanged | canonical |
| `components/calibration/index.js` (barrel) | unchanged | re-exported by admin re-mount |
| `pages/admin/AdminTechAnalysisPage.jsx` (`CalibrationTab`) | unchanged | V-1 RE-MOUNT lives here |
| `api/calibration.api.js` | unchanged | shared API client, used by canonical components |
| Backend routes | not touched | out of scope of this UI move |

---

## 3. What is still left in the user UI under "calibration" name
   (and why it is OK)

`grep -rn 'Calibration' /app/frontend/src/pages /app/frontend/src/components`
in user space still returns hits in:

* `pages/OnchainV3/tabs/MarketStateSnapshot.tsx`
* `pages/SignalsAttribution.jsx`
* `pages/PredictionPage.jsx` (`IntelCalibrationHistoryCard`)

**These are NOT the Phase-5 ML calibration surface.** They are
read-only display cells named "Confidence Calibration" that show
the status (`OK / OVERCONFIDENT / INSUFFICIENT_DATA / …`) of the
TA-scenarios calibration coming back from Prediction / Signals
endpoints. They:

* render text, not buttons.
* never call build / simulate / apply / disable.
* do not produce side effects.

They are display surfaces, not control surfaces. Leaving them in
user space is correct — removing them would hide useful diagnostic
data that the regular user is allowed to see.

If a future step decides to gate even these display cells, that is
a separate, easier MOVE because the components are already pure
read-only.

---

## 4. Final Calibration topology

```
USER  (no calibration control surface)
  └── pages/SettingsPage.jsx              ← Calibration tab REMOVED
  └── (read-only "Calibration status" cells stay — display only)

ADMIN (single canonical home)
  └── /admin/tech-analysis
        └── sub-sidebar group "Analysis"
              └── tab "Calibration"        ← V-1 RE-MOUNT (LIVE)
                    ├── CalibrationStatusCard
                    ├── CalibrationBuildPanel
                    ├── CalibrationRunHistory
                    └── CalibrationAttackTests
```

Build / Simulate / Apply / Disable can no longer be reached from
user space, period.

---

## 5. Verification

| Check | Expected | Result |
|---|---|---|
| Frontend compiles | `webpack compiled with 1 warning` (pre-existing eslint) | ✅ |
| `grep CalibrationStatusCard pages/SettingsPage.jsx` | 0 active hits, only audit comments | ✅ |
| `grep "function CalibrationTab" pages/SettingsPage.jsx` | 0 hits | ✅ |
| `grep "activeTab === 'calibration'" pages/SettingsPage.jsx` | 0 active hits | ✅ |
| `wc -l pages/SettingsPage.jsx` | shrunk from 1263 → 1239 | ✅ (-24 net) |
| Canonical files byte-identical | `wc -l components/calibration/*.jsx` matches pre-state | ✅ |
| Admin re-mount still renders | `/admin/tech-analysis → Calibration` works | to re-screenshot |
| Activity lucide icon import still needed | yes — used at lines 266 + 366 of SettingsPage | ✅ kept |
| Default activeTab | not `'calibration'` (nothing forces it) | ✅ |

---

## 6. Tracking

```
LEVEL 1 CRITICAL
V-1 ✅
V-2 ✅
V-3 ✅
V-4 ✅
V-9 ✅

ЭТАП 2 — RE-MOUNT
[Шаг 1] Calibration         ← V-1 RE-MOUNT ✅
        + USER-CLOSE         ← V-1 USER-CLOSE ✅ (this doc)
[Шаг 2] Root Cause + ML Readiness   ← next
[Шаг 3] Simulation
[Шаг 4] MLOps   ← V-3 + V-4 (mutating, requires confirms)
[Шаг 5] Exchange ML   ← V-9 trivial drop-in
[Шаг 6] Trainer   ← V-2 (leave disabled)
```

V-1 boundary is now closed both ways:
* removed from user (this move),
* re-mounted in admin (previous move).

The unrelated backend reality — `/api/ml/calibration/*` → 404 on
the deployed FastAPI — remains an open backend hardening item and
is **not** affected by this UI close.
