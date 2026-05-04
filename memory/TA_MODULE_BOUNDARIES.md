# TA Module — Boundaries

> Read this **before** opening any PR that touches `/api/ta/*`, `/api/runtime/*`, `/api/trace/*`, `/api/analytics/*`, `/api/learning/*`, `/api/decisions/*`, `frontend/src/modules/ta/*`, `frontend/src/hooks/runtime/*`, or any `taService` import.
>
> **One page. Imperative. No descriptions. No softening.**
>
> Companion to `TA_MODULE_CONTRACT.md`. The contract is the spec; this file is the firewall.

---

## ✅ What's IN the TA module

Files you may touch as a TA contributor:

* `backend/modules/ta_module/` — namespace alias
* `backend/modules/runtime/` · `backend/modules/runtime/decisions/` — runtime + lifecycle
* `backend/modules/trace/` · `backend/modules/decision_outcome/` — trace, outcomes, notes
* `backend/modules/analytics/` (TA-owned analytics endpoints only)
* `backend/modules/learning/` · `backend/modules/alpha_factory/real_learning/`
* `backend/modules/ta_prediction_intelligence/` — engines, calibration, decision intel, learning observer
* `backend/modules/ta_engine/` · `backend/modules/ta_module/*`
* `frontend/src/modules/ta/` — entire subtree
* `frontend/src/hooks/runtime/` — hooks consuming `taRuntime`
* `frontend/src/components/terminal/{trace,workspaces,zap}/` — TA-driven UI
* `scripts/poc_step*.py`, `scripts/forensic_*.py`, `scripts/observe_*.py` — TA diagnostics

---

## ❌ What's OUT of the TA module

Do NOT modify these as part of any TA-tagged PR:

* `frontend/src/modules/cockpit/` — separate operator tooling
* `backend/modules/auth/` · authentication & sessions
* `backend/modules/exchange*/` · raw exchange adapters (TA consumes, doesn't own)
* `backend/modules/trading_capsule/` (except where it serves `/api/ta/*` aliased routes)
* `backend/modules/system_control/` · host-app system layer
* `backend/modules/billing*`, `backend/modules/users/`, anything user-facing non-trading
* Supervisor configs · ingress · `MONGO_URL` / `REACT_APP_BACKEND_URL` env values

---

## 🚫 Forbidden patterns

### Frontend

* ❌ `fetch('/api/runtime/...')`, `fetch('/api/trace/...')`, `fetch('/api/analytics/...')`, `fetch('/api/learning/...')`, `fetch('/api/decisions/...')` anywhere outside `modules/ta/services/`. Use `taRuntime` / `taTrace` / `taAnalytics` / `taLearning`.
* ❌ Any `axios.create({ baseURL: '/api/...' })` or `axios.post('/api/runtime/...')` for TA-owned routes.
* ❌ **Importing legacy API wrappers for TA functionality when a `taService` equivalent exists.** This includes any `api.js` / `runtimeApi.js` / `legacyClient.*` / cockpit helpers that ultimately hit TA-owned routes. If the helper exists in `taService`, you MUST use it — not going through `fetch` is not enough.
* ❌ Direct `process.env.REACT_APP_BACKEND_URL` concatenation with TA paths in component code. The base URL belongs to `taService` only.
* ❌ Adding business logic to `taService.js`: trimming, defaulting, validating, retrying, caching, throwing on enums.
* ❌ Mixing daemon and engine controls under one button, one helper, one variable name.
* ❌ Renaming a payload key (`note → text`, `reason → message`, `mode → execution_mode`, etc.). Even if it "reads better".
* ❌ Parsing or transforming `decision_id`. It is opaque.

### Backend

* ❌ Adding new TA endpoints **outside** the canonical namespace pattern. Every new TA route MUST be reachable through `/api/ta/*` (either via existing alias rules, or by extending `TA_ALIAS_RULES` in `ta_namespace.py`).
* ❌ Touching frozen-logic files (see Contract §7.1) without architect-approved forensic.
* ❌ Mounting handlers at brand-new top-level prefixes (`/api/foo/*`) for TA functionality — extends contract surface silently.
* ❌ Removing or changing semantics of legacy routes (`/api/runtime/*` etc.) without a Phase C migration plan.
* ❌ Bypassing the alias by hard-coding `/api/ta/*` paths inside backend modules — middleware does the rewrite, handlers stay legacy-named.
* ❌ Wiring TA Prediction Intelligence to MetaBrain / combined_analysis / shadow_* (`wired_to_meta` MUST stay `false`).
* ❌ Enabling ML training / `/live` blending before `n_evaluated ≥ 500` per `(symbol, tf)`.

### Cross-cutting

* ❌ Logging full payloads of `note` or `reason` at INFO level (PII / operator commentary).
* ❌ Catching exceptions from `taRuntime.decisions.{approve,reject,note}` and proceeding silently — operator must see the failure.
* ❌ Hard-coding `mode` as `"PAPER"` / `"LIVE"` in frontend. The valid set is `MANUAL | SEMI_AUTO | AUTO`. Exchange mode is a separate concept (backend env).
* ❌ Bundling cockpit migration into a TA PR.

---

## ✅ Allowed patterns

**Golden path (memorise these three lines):**

* ✅ `UI → taService → /api/ta/*`
* ✅ Backend handler stays legacy-named; middleware owns the canonical rewrite.
* ✅ New TA endpoint = alias rule + smoke test + contract update.

### Frontend

* ✅ `import { taRuntime, taTrace } from 'modules/ta/services';`
* ✅ `const json = await taRuntime.decisions.approve(decisionId);` then `try/catch`.
* ✅ Caller-side `trim()`, validation, defaults BEFORE handing data to `taService`.
* ✅ Adding a new typed helper to `taService.js` when introducing a new endpoint — promote it out of `taRaw` once stable.
* ✅ Polling via `setInterval` + an `abortController` from a hook. The hook owns lifecycle; service is stateless.

### Backend

* ✅ Adding a new endpoint at its **legacy** location and letting the alias middleware expose it under `/api/ta/*`.
* ✅ Extending `TA_ALIAS_RULES` (most-specific-first) when introducing a new top-level prefix that should belong to TA.
* ✅ Read-only diagnostic endpoints (`/diagnostics/*`) for monitoring without touching frozen logic.
* ✅ New forensic scripts in `/scripts/` modeled after `forensic_v2_mfe_mae.py`.

---

## 🔁 Migration rule for new TA work

When adding any new TA endpoint or UI surface:

1. Add backend handler at its legacy location (`/api/<group>/...`).
2. If `<group>` is not yet aliased, add a rule to `TA_ALIAS_RULES` (most-specific-first).
3. Smoke-test both URLs: legacy + canonical → byte-identical response.
4. Add typed helper to `taService.js` (NOT a one-off `taRaw.*` in components).
5. Use the helper at the callsite. **No** direct `fetch`.
6. Update `TA_MODULE_CONTRACT.md` §3 and §4.

Skipping any step = contract violation = PR reject.

---

## 🛑 Hard freeze surfaces (cite §7 of Contract for context)

* SimpleMA entry logic
* engines / aggregator / conflict_resolver / ScenarioBuilder
* interaction_adjuster / calibration_adjuster / feature_builder
* temporal_buffer / temporal_intelligence / live_adapter
* regime gates
* `wired_to_meta = false` for TA Prediction Intelligence
* ML gate `n_evaluated ≥ 500`

Touching any of these without forensic evidence and architect sign-off is an automatic revert, regardless of code quality.

---

## 🧪 PR review checklist

Reviewer runs these mentally before approving any PR with TA-tagged files:

* [ ] Every new HTTP call uses `taRuntime` / `taTrace` / `taAnalytics` / `taLearning` (or extends one of them).
* [ ] No direct `fetch('/api/...')` for TA-owned paths added.
* [ ] No legacy API wrapper is imported when a `taService` equivalent exists.
* [ ] **If a legacy route is used** (backend or frontend): explicit justification in the PR description **and** a `TODO(migration-owner: @name)` comment at the callsite.
* [ ] No payload key renames.
* [ ] No business logic added to `taService.js`.
* [ ] If a new endpoint was added: alias rule + smoke test + contract section updated.
* [ ] No frozen-logic file is in the diff (or, if it is, forensic + architect approval are linked).
* [ ] Cockpit not in diff.
* [ ] No engine ↔ daemon confusion in naming, comments, or UI strings.

If any box is unchecked: request changes.

---

*This file is intentionally short. If you find yourself wanting to expand it, you probably want to expand the Contract instead. Boundaries are a firewall — keep them sharp.*
