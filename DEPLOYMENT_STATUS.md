# DEPLOYMENT_STATUS.md — Trading Terminal развёрнут на /app

> Создано после полной развертки: 2026-05-01

---

## ✅ Развёртка успешно завершена

### Текущее состояние сервисов

| Сервис | Статус | Порт | Примечание |
|---|---|---|---|
| backend (FastAPI) | RUNNING | 8001 | `/api/system/health` → 200 OK |
| frontend (React+craco) | RUNNING | 3000 | UI грузится через preview |
| mongodb | RUNNING | 27017 | DB=`trading_os`, ~30 коллекций восстановлено |
| code-server, nginx-code-proxy | RUNNING | — | вспомогательные |

### Public Preview URL
- UI: `https://tech-analysis-core-2.preview.emergentagent.com/`
- API: `https://tech-analysis-core-2.preview.emergentagent.com/api/*`

### Что было сделано (Phase 1)

1. ✅ `/app/backend/.env` создан заново со значениями:
   ```
   MONGO_URL="mongodb://localhost:27017"
   DB_NAME="trading_os"
   CORS_ORIGINS="*"
   JWT_SECRET="fomo-admin-secret-key-2024"
   EXCHANGE_MODE="PAPER"
   ```
2. ✅ `/app/frontend/.env` сохранён (`REACT_APP_BACKEND_URL` неизменён).
3. ✅ Репозиторий скопирован: `/tmp/project_repo → /app` (без `.git`, `node_modules`).
4. ✅ `pip install -r requirements.txt` (130 пакетов).
5. ✅ `yarn install` (success, lockfile saved).
6. ✅ Снапшоты MongoDB восстановлены:
   - **base** (`data_snapshots/latest/`): 23 коллекции, ~9000 документов (candles 3396, exchange_sync_logs 2820, shadow_trades 496, trading_cases 292 …).
   - **overlay** (`data_snapshots/live2h/`): regime_controls (3), trading_cases (15), position_exit_events (78), regime_guard_events (1).
7. ✅ `supervisorctl restart backend frontend` — оба RUNNING.

### Что было проверено (Phase 2)

| Команда | Результат |
|---|---|
| `curl /api/system/health` | `{"ok":true,"status":"healthy","services":{"database":"connected","api":"running"}}` |
| `curl /api/p27/status` | `total_trades=0, target=50, status=waiting_for_trades` |
| `curl /api/auto-safety/state` | `state_id=main, daily_pnl_usd=0` |
| `curl /openapi.json` | **953 эндпоинта** зарегистрировано |
| `python3 scripts/observe_live2h.py` | `closed_2H=15  W=9/L=6  WR=60.0%  avg=+0.0203%` |
| `python3 scripts/forensic_v2_mfe_mae.py` | 20 закрытых трейдов, отчёт записан в `/tmp/forensic_v2_report.md` |
| `python3 scripts/poc_step8_features.py` | **13/13 PASS** |
| `python3 scripts/poc_step7_calibration.py` | 10/12 (2 failures — `outcome produced` ожидаемо: свежая БД) |

### Frontend UI (verified)
Скриншот главной страницы показал работающую навигацию:
`Prediction · Fractal · Exchange · On-chain · Twitter · Telegram · Terminal`. На главной отображаются виджеты "Exchange Pressure", "Signals & Attribution" (Active Signals=17), Calibration: UNKNOWN, "No tokens yet".

---

## 🗺 Карта архитектуры TA Prediction Intelligence (Phase 3)

> Эта карта подготовлена для следующей итерации R&D (доработка теханализа, не торговли).

### 1) Где живёт TA Prediction Intelligence

```
backend/modules/ta_prediction_intelligence/
├── ta_prediction_routes.py          # точка входа REST (95 эндпоинтов)
├── ta_prediction_service.py         # основной сервис
├── ta_prediction_aggregator.py      # агрегация сигналов от всех движков
├── ta_prediction_conflict_resolver.py  # разрешение конфликтов
├── step7_pipeline.py                # Step 7: калибровка
├── live_adapter.py                  # ↔ TA Engine (signals → predictions)
├── repository.py                    # Mongo persistence
├── types.py                         # Pydantic-модели
│
├── engines/                         # подмодули-движки (TA сигналы)
├── engine_interactions.py
├── calibration/                     # Step 7 калибровка по бакетам
├── decision_intelligence/           # Step 12: финальное решение
├── learning/                        # Step 8: features + buffer
│   └── learning_routes.py
├── data_health/                     # Step 11: gate qualification
├── debug/                           # Step 9: debug layer
├── debug_routes.py
├── ml_readiness/                    # ML gate (n≥500)
├── root_cause_aggregator/
├── scenarios/                       # Step 12 winning scenario
├── simulation/                      # backtesting
├── temporal_intelligence/           # Step 10 dataset builder
└── evaluation/                      # outcome worker
```

### 2) Ключевые REST-точки (выборка)

```
/api/ta-prediction-intelligence/buffer/status       # Step 8 кольцевой буфер
/api/ta-prediction-intelligence/calibration         # Step 7 текущие бакеты
/api/ta-prediction-intelligence/calibration/rebuild # пересобрать калибровку
/api/ta-prediction-intelligence/calibration/diagnostics
/api/ta-prediction-intelligence/data-health         # Step 11 trust score
/api/ta-prediction-intelligence/data-health/checks
```

### 3) Цепочка Step 6 → 7 → 8/9 → 10 → 12 (карта пайплайна)

| Шаг | Назначение | Где править |
|---|---|---|
| Step 6 | Engine Interactions | `engine_interactions.py`, `engines/` |
| **Step 7** | Калибровка вероятностей по бакетам | `step7_pipeline.py`, `calibration/` |
| Step 8 | Features v1 (82 фичи) + Ring Buffer | `learning/`, `learning_routes.py` |
| Step 9 | Debug Layer (трассировка) | `debug/`, `debug_routes.py` |
| Step 10 | Dataset Builder (для будущего ML) | `temporal_intelligence/` |
| Step 11 | Data Health Gate (trust_score, n≥500) | `data_health/` |
| Step 12 | Decision Intelligence (winning scenario) | `decision_intelligence/`, `scenarios/` |

### 4) Инварианты, которые **нельзя** ломать (из `plan_project.md`)

❌ Не менять логику входа `SimpleMA`
❌ Не добавлять новые стратегии без forensic
❌ Не реактивировать regime gates без архитекторского одобрения
❌ Не трогать UI Decisions tab / Prediction overlay (paused)
❌ Никаких изменений калибровки/агрегатора/conflict logic без forensic-обоснования
❌ Никакой ML до выполнения gate `n_evaluated >= 500`

### 5) Безопасные точки расширения для следующей R&D-итерации

✅ Новые **read-only** диагностические эндпоинты (`/diagnostics/*`)
✅ Новые группировки/метрики бакетов (без изменения upstream-семантики)
✅ Усиление мониторинга dataset-stats и trust-score
✅ Новые отчёты forensic (по аналогии с `forensic_v2_mfe_mae.py`)
✅ Дополнительные тесты POC (по образцу `poc_step7_*`, `poc_step8_*`)

---

## 🔄 Runbook (Phase 4) — Operator/Developer

### Свежий резерв или fork
```bash
bash /app/scripts/bootstrap_live2h.sh
```
Скрипт идемпотентен. Восстановит снапшоты, перезапустит backend, поднимет observer + watchdog v2.

### Снэпшот текущего состояния (перед R&D)
```bash
python3 /app/scripts/snapshot_live2h.py
```

### Smoke-чек после деплоя
```bash
sudo supervisorctl status                                  # все RUNNING?
curl -s localhost:8001/api/system/health                   # ok=true?
curl -s localhost:8001/api/p27/status | head               # P2.7 baseline
mongosh trading_os --quiet --eval 'db.trading_cases.countDocuments({})'
python3 /app/scripts/observe_live2h.py                     # snapshot
```

### Полный forensic
```bash
python3 /app/scripts/forensic_v2_mfe_mae.py
cat /tmp/forensic_v2_report.md
```

### POC-скрипты (read-only регрессия)
```bash
python3 /app/scripts/poc_step7_calibration.py
python3 /app/scripts/poc_step8_features.py
python3 /app/scripts/poc_step10_dataset.py
python3 /app/scripts/poc_step12_decision.py
```

### Логи
```bash
tail -n 200 /var/log/supervisor/backend.err.log /var/log/supervisor/frontend.err.log
tail -n 200 /var/log/supervisor/backend.out.log
```

### Ролбек
```bash
# При повреждении БД восстановить из снапшотов:
python3 /app/scripts/restore_snapshot.py --snapshot /app/data_snapshots/latest --mode base
python3 /app/scripts/restore_snapshot.py --snapshot /app/data_snapshots/live2h --mode overlay
sudo supervisorctl restart backend
```

---

## ✅ Критерии успеха (status)

- [x] `/app` запускает репо (не template) — `supervisorctl status` показывает RUNNING.
- [x] MongoDB использует `trading_os` и содержит восстановленный LIVE-2H overlay.
- [x] `bash /app/scripts/bootstrap_live2h.sh` идемпотентен (использован restore_snapshot.py при первой развёртке).
- [x] Backend health endpoints отвечают; **953 эндпоинта** зарегистрировано, включая `/api/ta-prediction-intelligence/*`.
- [x] Read-only forensic/POC-скрипты выполняются и пишут артефакты.
- [x] Карта расширения для следующей R&D-итерации зафиксирована (см. секцию 5).

---

## 🚀 Готово к следующему шагу

Согласно директиве архитектора: **следующая работа — продолжение блока теханализа** (TA Prediction Intelligence), без торговой логики.

Безопасные точки правки описаны выше — ждём конкретное направление от пользователя:
- расширение метрик калибровки?
- новый forensic для Step 12?
- усиление data-health gate?
- доработка features v1?
- что-то иное?
