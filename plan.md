# plan.md — Deploy FARM-stack Trading Terminal to /app + prepare TA Prediction Intelligence continuation

## 1) Objectives
- Deploy the existing repo into the `/app` runtime (supervisor-managed FastAPI + React + MongoDB).
- Restore **LIVE-2H** baseline state (snapshots + gates OFF + TP/SL ±0.30%) and verify services.
- Establish a repeatable ops routine: bootstrap, restart, verify health, run read-only forensics.
- Study and map **TA Prediction Intelligence** architecture (Steps 6/7/8/9/10/12 already completed) to prepare the next R&D work without breaking invariants.

---

## 2) Implementation Steps

### Phase 1 — Core deployment POC (isolation): “can we boot the stack reliably?”
**Core workflow to prove (must pass before any further work):**
`copy repo → install deps → set env → restore snapshots → supervisor restart → /api health + UI loads`

**User stories (POC):**
1. As an operator, I can redeploy code to `/app` without losing the required `.env` settings.
2. As an operator, I can boot backend + frontend via supervisor and see both as RUNNING.
3. As an operator, I can restore MongoDB to the LIVE-2H baseline snapshot idempotently.
4. As an operator, I can call backend health endpoints and get an OK response.
5. As a developer, I can run the read-only observation/forensic scripts and get reports.

**Work items:**
- Backup current env/config:
  - `/app/backend/.env` and `/app/frontend/.env` (preserve `MONGO_URL`, `REACT_APP_BACKEND_URL`).
- Replace `/app` code with repo contents:
  - Copy `/tmp/project_repo/* → /app/` (exclude `node_modules`, keep `.env` from backups).
  - Ensure executable flags for scripts (`scripts/*.sh`).
- Env correctness:
  - Set `/app/backend/.env`: `DB_NAME=trading_os` (keep `MONGO_URL` intact).
  - Keep `/app/frontend/.env` as-is; confirm proxy settings (frontend `package.json` uses `proxy: http://localhost:8001`).
- Install deps:
  - Backend: install `/app/backend/requirements.txt` into runtime venv.
  - Frontend: `yarn install` in `/app/frontend`.
- Data restore:
  - Run `bash /app/scripts/bootstrap_live2h.sh` (or manual `restore_snapshot.py` base+overlay).
- Restart services:
  - `sudo supervisorctl restart backend frontend mongodb`.
- POC verification:
  - Confirm supervisor status, tail logs, confirm `/api/health` (and any relevant TA endpoints), confirm frontend renders.

**Exit criteria:**
- Backend + frontend both RUNNING after restart.
- Mongo contains LIVE-2H collections (regime_controls + trading_cases overlay applied).
- `bootstrap_live2h.sh` completes without fatal errors.

---

### Phase 2 — V1 Ops hardening (repeatability + smoke suite)
**User stories:**
1. As an operator, I can do a one-command restore+restart (bootstrap) and trust the state.
2. As an operator, I can quickly diagnose failures via a small set of log/health commands.
3. As a developer, I can run POC scripts for Step 7/8/10/12 without modifying production code.
4. As a developer, I can snapshot current DB state for safe experimentation.
5. As a maintainer, I can verify “no regression” on key API responses after redeploy.

**Work items:**
- Create a minimal “smoke checklist” (commands only) for:
  - supervisor status + log tails
  - backend health
  - frontend reachability
  - Mongo ping + collection presence
- Run existing read-only scripts (no code changes):
  - `scripts/observe_live2h.py` (one-shot and watch)
  - `scripts/forensic_v2_mfe_mae.py`
  - TA intelligence POCs: `poc_step7_calibration.py`, `poc_step8_features.py`, `poc_step10_dataset.py`, `poc_step12_decision.py` (as regression checks)
- Snapshot routine:
  - `scripts/snapshot_live2h.py` before any future R&D changes.

**Exit criteria:**
- All smoke checks pass; POC scripts run cleanly (or documented known constraints).

---

### Phase 3 — Architecture study & “where to edit next” map (no mutations)
**User stories:**
1. As a developer, I can identify the exact `/api/ta-prediction-intelligence/*` entry points used by the UI.
2. As a developer, I can trace the Step-6→7→8/9→10→12 pipeline end-to-end.
3. As a developer, I can find where persistence happens (history, calibration stats, dataset, buffer).
4. As a developer, I can locate invariants/guardrails that must not be violated (caps, n<30 skip, determinism).
5. As a developer, I can propose the next R&D change points without touching engines/aggregator/conflict logic.

**Work items:**
- Read canonical state + architecture docs:
  - `/app/PHASE_STATE.md`
  - `backend/COMPLETE_BACKEND_ARCHITECTURE_AUDIT.md`
  - `backend/PREDICTION_AUDIT.md`
- Produce an internal map (notes) of TA module structure:
  - `backend/modules/ta_prediction_intelligence/`:
    - step7 pipeline, calibration, learning/features+buffer, dataset builder, decision intelligence, routes, repository
- Identify safe extension points for the next phase (examples):
  - new read-only diagnostics endpoints
  - new bucket groupings/metrics (without altering upstream semantics)
  - dataset stats gates / monitoring improvements

**Exit criteria:**
- Clear list of “allowed edit surfaces” + “forbidden surfaces” consistent with plan_project.md/phase discipline.

---

### Phase 4 — Handoff package (operator + developer)
**User stories:**
1. As an operator, I can redeploy and restore LIVE-2H with a documented runbook.
2. As a developer, I can run the key TA POC scripts to validate non-regression.
3. As a developer, I can query history/calibration/dataset/worker status endpoints confidently.
4. As a developer, I can start the next TA R&D step with a pre-approved change surface.
5. As a maintainer, I can verify production invariants remain intact after changes.

**Work items:**
- Write a short runbook section in-repo (or update existing docs) with:
  - deploy steps, bootstrap steps, verification commands, and rollback approach.
- Summarize current TA Prediction Intelligence state (Steps completed + what data is needed next, e.g., `n≥500` evaluated for Step 11 gating).

---

## 3) Next Actions
1. Deploy repo into `/app` while preserving `.env` files; set `DB_NAME=trading_os`.
2. Install backend + frontend deps; restart supervisor services.
3. Run `bootstrap_live2h.sh` and confirm snapshot restore.
4. Execute smoke checks + run read-only POC scripts as regression.
5. Produce TA prediction module entry-point map and list of safe next-step modifications.

---

## 4) Success Criteria
- ✅ `/app` runs the repo (not the template): supervisor shows backend+frontend+mongodb running, UI loads.
- ✅ MongoDB uses `trading_os` and contains restored LIVE-2H overlay (regime_controls + trading_cases).
- ✅ `bash /app/scripts/bootstrap_live2h.sh` is idempotent and restarts backend cleanly.
- ✅ Backend health endpoints respond; TA Prediction Intelligence endpoints available.
- ✅ Read-only forensic/POC scripts run and produce expected artifacts without code changes.
- ✅ A clear, documented "where to work next" map exists for TA prediction logic continuation.

---

## 5) Deployment completed (2026-05-04)

| Item | Status | Evidence |
|---|---|---|
| Services | ✅ RUNNING | `supervisorctl status` → backend, frontend, mongodb all RUNNING |
| Backend health | ✅ `/api/system/health` = 200 OK | `{"ok":true,"services":{"database":"connected"}}` |
| API endpoints | ✅ 953 registered | `GET /openapi.json` |
| MongoDB | ✅ `trading_os` DB restored | base + live2h overlay applied |
| LIVE-2H observer | ✅ running | N=41 closed, WR=56.1%, avg=+0.0183% |
| POC step7 | ✅ 10/12 (2 expected fail on fresh DB) | `poc_step7_calibration.py` |
| POC step8 | ✅ 13/13 | `poc_step8_features.py` |
| POC step10 | ✅ 11/11 | `poc_step10_dataset.py` |
| POC step12 | ✅ 12/12 | `poc_step12_decision.py` |
| Forensic v2 | ✅ 63 trades analysed | `/tmp/forensic_v2_report.md` |
| Frontend UI | ✅ loads at preview URL | Prediction · Fractal · Exchange · On-chain · Twitter · Telegram · Terminal |
| TA architecture map | ✅ written | `/app/TA_PREDICTION_INTELLIGENCE_MAP.md` |

### Public preview
- UI / API: `https://market-analyzer-core.preview.emergentagent.com/`
- Example: `GET /api/system/health`, `GET /api/ta-prediction-intelligence/health`

### Known (pre-existing, non-blocking) issues
- `server.py:1323` — `UnboundLocalError: db` inside the MarketDynamic runner
  startup try/except. It is caught by the outer `except Exception`; the
  MarketDynamic experiment is not enabled in LIVE-2H, so this is dormant.
  **Do not fix without forensic justification** (project invariant: no code
  change to production logic without architect approval).

### Ready for next iteration
Per architect directive: next R&D work is on the **TA Prediction Intelligence
block** (calibration / data health / debug / decision layer), NOT on trading
execution. Safe extension surface is enumerated in
`TA_PREDICTION_INTELLIGENCE_MAP.md` §6.

---

## 6) Stage A — read-only restoration of orphaned TA branches (2026-05-04, ✅ DONE)

Architect directive (verbatim, RU): «делать Stage A: read-only restore of Fractal +
Exchange + TA Engine endpoints. ❌ не подключать это в execution. ❌ не давать этим
модулям голос в aggregator. ❌ не менять weights. ❌ не включать auto-trading
decisions. ❌ не объединять три prediction-системы сразу.»

### Что сделано (точно по объёму этапа A)
| Sub-task | Что | Где | Статус |
|---|---|---|---|
| A0 | Инспекция 5 orphaned route-файлов (Exchange Intel, Asset-Fractal, Fractal-Context, Macro-Fractal, Cross-Asset) — все 33 endpoints **исключительно GET** | `/app/backend/modules/{exchange_intelligence, fractal_intelligence, macro_fractal_brain, cross_asset_intelligence}` | ✅ |
| A1 | Read-only регистрация в `server.py` под защитой try/except, явный комментарий «STAGE A — READ-ONLY visibility» | `/app/backend/server.py` после блока fractal_market | ✅ |
| A2 | Smoke-тест: health + payload + BTCUSDT/ETHUSDT + проверка отсутствия non-GET методов + регрессия живых endpoints | `/app/scripts/smoke_stage_a.py` | ✅ |
| A3 | Aggregator endpoints `/api/admin/branches/health` + `/summary` (cache 60s, безопасный probe, никаких записей) | `/app/backend/modules/stage_a_visibility/routes.py` | ✅ |
| A3-UI | React-страница `/admin/stage-a` — Branches Health Panel | `/app/frontend/src/pages/admin/StageABranchesPage.jsx` | ✅ |

### Подключённые ветки (только GET, +35 endpoints)

| Branch | Prefix | GET endpoints | Status |
|---|---|---|---|
| Exchange Intelligence | `/api/exchange-intelligence/*` | 12 | ✅ ALIVE |
| Fractal — Asset (BTC/SPX/DXY) | `/api/v1/fractal-assets/*` | 6 | ✅ ALIVE |
| Fractal — Context | `/api/v1/fractal-intelligence/*` | 4 | ✅ ALIVE |
| Macro-Fractal Brain | `/api/v1/macro-fractal/*` | 4 | ✅ ALIVE |
| Cross-Asset Intelligence | `/api/v1/cross-asset/*` | 7 | ✅ ALIVE |
| **Stage A admin** | `/api/admin/branches/*` | 2 | ✅ |

`openapi.json` total: 953 → **988** endpoints.

### Гарантии read-only (проверены автоматически в smoke-тесте)
- ✅ 0 не-GET методов на 6 префиксах Stage A
- ✅ 0 модификаций `aggregator` / `engines` / `conflict_resolver` / `weights`
- ✅ 0 модификаций `signal_generator` / `execution/bridge.py` / `position_exit_manager`
- ✅ 0 коллекций MongoDB записаны Stage A кодом
- ✅ Регрессия: 6/6 prior endpoints (`/api/system/health`, `/api/p27/status`, `/api/auto-safety/state`, `/api/ta-prediction-intelligence/health`, `/api/ta/registry`, `/api/fractal/v2.1/signal`) — все 200 OK

### Состояние агрегатора (snapshot после A)
```
Alive 8/8 · Dead 0
  ✅ exchange_intelligence            (Stage A · restored)
  ✅ fractal_assets                   (Stage A · restored)
  ✅ fractal_intelligence             (Stage A · restored)
  ✅ macro_fractal                    (Stage A · restored)
  ✅ cross_asset                      (Stage A · restored)
  ✅ fractal_market                   (live)
  ✅ ta_engine                        (live)
  ✅ ta_prediction_intelligence       (live)
```

### Артефакты Stage A
- `/app/backend/modules/stage_a_visibility/routes.py` — aggregator (read-only)
- `/app/backend/modules/stage_a_visibility/__init__.py`
- `/app/scripts/smoke_stage_a.py` — повторно прогоняемый regression smoke
- `/app/frontend/src/pages/admin/StageABranchesPage.jsx` — UI-панель
- Routes block в `server.py` — 60 строк read-only с явной маркировкой

### Что НЕ делалось (по директиве, явно)
- ❌ не давали этим модулям голос в `ta_prediction_aggregator`
- ❌ не подключали к `ExecutionBridge`
- ❌ не меняли `_compute_current_regime`
- ❌ не меняли `position_exit_manager` пороги
- ❌ не объединяли три prediction-системы (legacy + middle + new)
- ❌ не меняли weights в `MacroFractalEngine` или `ExchangeContextAggregator`

### Готово к Stage B
Все 5 restored ветвей дают непустой payload по BTCUSDT/ETHUSDT. Это значит,
что форензик Stage B можно гонять напрямую через `/api/admin/branches/health`
+ через каждую ветку отдельно. Никаких новых HTTP «дыр» сюрпризом не появится —
поверхность стабильна.

Команда на следующий шаг: дайте указание «B» — и для каждой ветки запустим
форензик-цикл: история payload → корреляция с `trading_cases.realized_pnl_pct` →
вердикт alpha / no-alpha / reserve.
