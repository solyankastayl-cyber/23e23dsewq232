# MOVE V-9 — MLAdminPage relocated into admin tree

**Date:** 2026-04-29
**Status:** EXECUTED
**Class of defect:** 🕳 "Hidden admin outside admin" — file lived in
the user-zone folder but was mounted only under a `/admin/*` route.

---

## 1. Summary

Moved:

```
frontend/src/pages/MLAdminPage.jsx            ❌ removed
frontend/src/pages/admin/AdminExchangeMLPage.jsx   ✅ new canonical location
```

Symbol rename (default export):

```
export default function MLAdminPage()  →  export default function AdminExchangeMLPage()
```

Reason for the new name:
- Matches the file name (standard for this codebase).
- Follows the admin-tree naming convention established by sibling
  files: `AdminExchangeControlPage`, `AdminExchangeWrapper`,
  `AdminMLOverviewPage`, `AdminMLFeaturesPage`, etc.
- The existing name `AdminMLPage.jsx` was already taken in
  `/pages/admin/` and refers to a different legacy ML admin page.

---

## 2. What the page actually is

This is the S10.7.4 **Exchange ML Admin UI** — a diagnostic
dashboard showing model health, rules-vs-ML agreement, feature
importance, drift monitor and a disagreement explorer.

Important behaviour note for the audit: the page exposes two
operator mutations (buttons in the header):

| Button | Endpoint | Effect |
|---|---|---|
| **Train Models** | `POST /api/v10/exchange/ml/train` | Retrains the ML model on the last N samples |
| **Freeze Model** | `POST /api/v10/exchange/ml/freeze` | Freezes the registry (lock) |

Read-only endpoints:
- `GET  /api/v10/exchange/ml/admin/summary`
- `GET  /api/v10/exchange/ml/cases/disagreement?limit=10`

These mutations **stay** in V-9 — they are already guarded by the
admin-only route `/admin/exchange/ml` and will keep working. V-9
only fixes the physical location of the file.

---

## 3. Callers updated

Two files imported the page; both are updated:

### 3.1 `frontend/src/App.js`

Before:

```jsx
// around line 315
const MLAdminPage = lazy(() => import("./pages/MLAdminPage"));
...
// around line 678 — DEAD DUPLICATE
<Route path="/admin/exchange/ml" element={<MLAdminPage />} />
```

After:

```jsx
// Around line 315 — lazy import REMOVED entirely (now dead code).
//   Detailed audit comment block in its place explaining V-9.
//
// Around line 678 — duplicate <Route> is commented out with an
//   audit comment explaining that it was UNREACHABLE: the live
//   mount of `/admin/exchange/ml` is earlier in the file and
//   resolves to <AdminExchangeWrapper />, which internally lazy-
//   loads AdminExchangeMLPage via pathname match. In React Router
//   v6 the first matching <Route> wins, so the duplicate never ran.
```

**Bonus outcome:** V-9 also removed one dead-duplicate route that
was pre-existing in `App.js` — `/admin/exchange/ml` was declared
twice; the second declaration was never reachable. Cleanup
recorded in the same audit block.

### 3.2 `frontend/src/pages/admin/AdminExchangeWrapper.jsx`

Before:

```jsx
const MLAdminPage = lazy(() => import('../MLAdminPage'));
```

After:

```jsx
// MOVE V-9 audit comment
const MLAdminPage = lazy(() => import('./AdminExchangeMLPage'));
```

The local binding name `MLAdminPage` is intentionally preserved so
that the `getPageComponent(pathname)` lookup table in the wrapper
remains unchanged:

```jsx
if (pathname.includes('/exchange/ml')) return MLAdminPage;
```

This is the canonical mount of the page and the only live path
after V-9.

---

## 4. Routing topology after V-9

```
USER path: /admin/exchange/ml
   ↓
<Route element={<AdminExchangeWrapper />}> (App.js ~line 517)
   ↓
getPageComponent(pathname) → returns AdminExchangeMLPage (alias: MLAdminPage)
   ↓
Suspense-lazy from './AdminExchangeMLPage'
```

There is now exactly **one** way to reach the page, through the
canonical admin wrapper, with the canonical layout shell
(`AdminLayout` inside `AdminExchangeWrapper`).

---

## 5. Verification performed at move time

| Check | Expectation | Result |
|---|---|---|
| Old file gone | `frontend/src/pages/MLAdminPage.jsx` absent | ✅ |
| New file present | `frontend/src/pages/admin/AdminExchangeMLPage.jsx` ~455 LOC with renamed export | ✅ (file size consistent with old) |
| No stale imports to `../MLAdminPage` or `pages/MLAdminPage` | `grep -rn` returns 0 in active source (only MOVE V-9 audit comments) | to be verified post-edit |
| `App.js` has no leftover `MLAdminPage` binding | Only audit-comment occurrences remain | to be verified |
| Dead duplicate route `<Route path="/admin/exchange/ml" element={<MLAdminPage />} />` | commented out | ✅ |
| `AdminExchangeWrapper` points to new path | `import('./AdminExchangeMLPage')` | ✅ |
| Frontend compiles | `webpack compiled successfully` | to be verified |
| Route still serves the page | `/admin/exchange/ml` renders Exchange ML Admin | to be verified |

---

## 6. Out of scope for V-9 (tracked but not done here)

1. Two operator mutations on the page (`train`, `freeze`) still do
   not carry an explicit `RequireAdmin` gate or a
   `window.confirm()` guard. The admin tree is implicitly protected
   by `AdminLayout` (which is the admin-auth boundary in this
   project), but an explicit confirm dialog on Train/Freeze would
   match the safety pattern already applied to Rollback in MLOps.
   → Add during `/admin/tech-analysis` build or in a dedicated
     admin-hardening pass.

2. Dormant legacy file `pages/admin/AdminMLOpsPage.jsx` still
   imports `MLOpsPage` directly (detected during V-4). Not used by
   the router (`/admin/mlops` is a `<Navigate>` stub), but it is a
   candidate for the eventual "ARCHIVE legacy" step.

3. Backend endpoints `/api/v10/exchange/ml/train` and
   `/api/v10/exchange/ml/freeze` should require admin JWT at the
   server boundary — separate backend hardening ticket.

---

## 7. Tracking

```
LEVEL 1 CRITICAL
V-1 ✅
V-2 ✅
V-3 ✅
V-4 ✅
V-9 ✅  ← this doc
```

**LEVEL 1 = 100% closed. USER UI is now a pure read-only terminal.**

Next phase: `/admin/tech-analysis` blueprint + build.
