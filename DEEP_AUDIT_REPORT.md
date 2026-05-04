# 🔬 ПОЛНЫЙ АРХИТЕКТУРНЫЙ АУДИТ: TA / Predictions / Trading

> **Дата:** 2026-05-04
> **Цель:** выявить, какая логика используется в реальном потоке, какая оторвана,
> где обрывы и деградации в трёх блоках — TA Core, Predictions, Trading System.
> **Метод:** построчная трассировка `server.py` (3697 строк), `signal_generator/runner.py`,
> `execution/bridge.py`, `ta_prediction_intelligence/live_adapter.py` + grep-карта
> импортов по 179 модулям backend.

---

## 🧨 TL;DR — главные открытия

| # | Проблема | Масштаб |
|---|---|---|
| 1 | **Ветка Exchange Intelligence полностью оторвана от HTTP и от пайплайна** — 0 endpoints, не используется ни одним активным модулем | ~2 700 LOC мертвы |
| 2 | **Ветка Fractal Intelligence (AssetFractal + MacroFractal) оторвана** — только `fractal_market_intelligence` жив (10 endpoints), остальные фракталы — нет | ~6 600 LOC мертвы |
| 3 | **Sentiment/Reflexivity ветка оторвана** — 0 endpoints | ~2 160 LOC мертвы |
| 4 | **Живой торговый loop использует ТОЛЬКО `SimpleMA` (EMA crossover)** — вся остальная TA/Prediction инфраструктура просто не консумится | catastrophic degradation |
| 5 | **`ta_prediction_intelligence` — гермитично изолирован**: его 5 движков читают только свои типы, live_adapter тянет данные только из `research_analytics` + ОДИН вызов `ta_engine.context_engine` | разорван upstream с 3 ветками TA |
| 6 | **Три параллельные prediction-системы** сосуществуют: `/api/prediction/*` (старая, 24 ep), `/api/ta-prediction/*` (средняя), `/api/ta-prediction-intelligence/*` (новая, 30 ep) — конкурируют за UI и данные | deprecation debt |
| 7 | **~54 000 LOC** кода в модулях, которые импортируют orphaned ветки (trading_product, alpha_interactions, trading_decision, execution_context, strategy_brain, hypothesis_engine, regime_memory, system_validation), — **тоже оторваны**, т.к. их routes не зарегистрированы в `server.py` | gigantic dead constellation |
| 8 | Активных `include_router(...)` в `server.py` = **120**; реально используемых веток анализа рынка — **3** (ta_engine, fractal_market_intelligence, ta_prediction_intelligence). Остальные 176 модулей либо служат вспомогательно, либо мертвы | — |

---

## 🧭 Общая схема того, что ЕСТЬ vs что РАБОТАЕТ

```
╔═══════════════════════════════════════════════════════════════════════════╗
║                       ЗАДУМАННАЯ АРХИТЕКТУРА                              ║
║                       (по аудит-докам апреля)                              ║
╠═══════════════════════════════════════════════════════════════════════════╣
║                                                                           ║
║  ┌──────────────────┐   ┌─────────────────┐   ┌───────────────────────┐   ║
║  │  FRACTAL branch  │   │  TA ENGINE      │   │  EXCHANGE INTEL       │   ║
║  │                  │   │  ( "TT Engine") │   │  ( "IndicExchange")   │   ║
║  │ fractal_intel    │   │ ta_engine       │   │ exchange_intel        │   ║
║  │ macro_fractal    │   │ ├ indicators    │   │ ├ funding_oi          │   ║
║  │ fractal_similar  │   │ ├ patterns      │   │ ├ derivatives_press   │   ║
║  │ cross_asset      │   │ ├ structure     │   │ ├ liquidation         │   ║
║  │ fractal_market   │   │ ├ fibonacci     │   │ ├ flow                │   ║
║  │                  │   │ ├ hypothesis    │   │ ├ volume              │   ║
║  │ ──┐              │   │ ├ probability   │   │ └ aggregator          │   ║
║  │   │              │   │ ├ expectation   │   │                       │   ║
║  │   │              │   │ ├ decision_v2   │   │ reflexivity_engine    │   ║
║  │   │              │   │ └ scenario_v3   │   │ (sentiment)           │   ║
║  └───┼──────────────┘   └────────┬────────┘   └──────────┬────────────┘   ║
║      │                           │                        │                ║
║      └───────────────┬───────────┴────────────────────────┘                ║
║                      ▼                                                    ║
║              ┌───────────────┐                                            ║
║              │  Predictions  │  (ta_prediction_intelligence)              ║
║              │  Steps 6–12   │  engines: structure, pattern, momentum,    ║
║              │               │  level_zone, volatility + aggregator +     ║
║              │               │  conflict_resolver + calibration +         ║
║              │               │  decision_intelligence + scenarios         ║
║              └───────┬───────┘                                            ║
║                      ▼                                                    ║
║              ┌───────────────┐                                            ║
║              │ Trading loop  │  SimpleMA + RegimeDetector → ExecutionBridge │
║              │               │  → ExecutionQueue → Binance/Paper          ║
║              │               │  → TP/SL/Time exits → trading_cases        ║
║              └───────────────┘                                            ║
╚═══════════════════════════════════════════════════════════════════════════╝

╔═══════════════════════════════════════════════════════════════════════════╗
║                         ФАКТИЧЕСКОЕ СОСТОЯНИЕ                              ║
║                      (runtime + server.py wiring)                          ║
╠═══════════════════════════════════════════════════════════════════════════╣
║                                                                           ║
║  FRACTAL branch           TA ENGINE              EXCHANGE INTEL           ║
║  ┌──────────────┐         ┌──────────────┐      ┌─────────────────┐      ║
║  │ fractal_mkt  │   ✅    │  ta_engine   │   ✅  │ 🕳️  ОТОРВАНА    │      ║
║  │  /api/fractal│         │  /api/ta/*   │      │  0 endpoints    │      ║
║  │  10 endpoints│         │  44 endpoints│      │  ~2700 LOC мерт │      ║
║  │              │         │              │      └─────────────────┘      ║
║  │ ❌ fractal_int         │              │      ┌─────────────────┐      ║
║  │ ❌ macro_fract         │              │      │ ❌ reflexivity  │      ║
║  │ ❌ fractal_sim         │              │      │  0 endpoints    │      ║
║  │ ❌ cross_asset         │              │      └─────────────────┘      ║
║  └──────┬───────┘         └──────┬───────┘              ✖                ║
║         │                        │                      │                ║
║         │   (UI rendering only)  │  (UI rendering only) │                ║
║         │                        │                      │                ║
║         ▼                        ▼                      ✖                ║
║    UI renders                UI renders              никто не            ║
║    fractal tab               TA tab                  потребляет           ║
║         .                        .                      .                 ║
║         .                        │                                        ║
║         .                        │ ONE call (context_engine only)         ║
║         .                        ▼                                        ║
║   ┌─────────────────────────────────────┐                                ║
║   │   ta_prediction_intelligence         │    (гермитичная коробка)     ║
║   │   live_adapter только из:            │    POC 44/46 проходят        ║
║   │   • research_analytics.indicators    │    30 endpoints работают     ║
║   │   • research_analytics.patterns      │    ...НО НЕ ВЛИЯЕТ НА         ║
║   │   • research_analytics.chart_data    │       ТОРГОВЛЮ                ║
║   │   • ta_engine.context_engine (1×)    │                               ║
║   └─────────────────────────────────────┘                                ║
║                                                                           ║
║                         ⛔  РАЗРЫВ  ⛔                                    ║
║                                                                           ║
║   ┌─────────────────────────────────────┐                                ║
║   │   Trading loop (SignalRunner)       │                                ║
║   │   • ТОЛЬКО SimpleMA (EMA crossover) │                                ║
║   │   • _compute_current_regime (EMA20/50)                               ║
║   │   • regime_controls DB flag         │                                ║
║   │   • ExecutionBridge — 4 софт-гейта  │                                ║
║   │   • → Queue → Paper/Binance         │                                ║
║   │   • → TP/SL ±0.30%  TIME_EXIT 30m   │                                ║
║   └─────────────────────────────────────┘                                ║
║                                                                           ║
╚═══════════════════════════════════════════════════════════════════════════╝
```

---

# БЛОК 1. TA CORE — три ветки анализа рынка

## 1.1. Ветка «Fractal» — частично жива

### Состав (5 подсистем)

| Модуль | LOC | Routes? | Wired в server.py? | Статус |
|---|---|---|---|---|
| `fractal_market_intelligence` | ~2600 | `fractal_routes.py` | ✅ **ДА** | 🟢 ACTIVE — 10 endpoints `/api/fractal/*` и `/api/v1/fractal/*` |
| `fractal_intelligence` (AssetFractalService, BTC/SPX/DXY adapters) | 2 985 | `asset_fractal_routes.py`, `fractal_context_routes.py` | ❌ **НЕТ** | 🔴 ORPHANED |
| `macro_fractal_brain` (Level 3, кросс-ассет фракталы) | 1 584 | `macro_fractal_routes.py` | ❌ **НЕТ** | 🔴 ORPHANED |
| `fractal_similarity` (поиск похожих фракталов) | 2 013 | нет routes | n/a | 🔴 UNUSED |
| `cross_asset_intelligence` (BTC×SPX×DXY bridges) | 1 801 | `cross_asset_routes.py` | ❌ **НЕТ** | 🔴 ORPHANED |

### Что реально делает живая часть (`fractal_market_intelligence`)
Работающие endpoints:
```
GET  /api/fractal/summary/{asset}
GET  /api/fractal/v2.1/chart
GET  /api/fractal/v2.1/focus-pack
GET  /api/fractal/v2.1/signal
GET  /api/v1/fractal/state/{symbol}
GET  /api/v1/fractal/summary/{symbol}
GET  /api/v1/fractal/history/{symbol}
GET  /api/v1/fractal/modifier/{symbol}
POST /api/v1/fractal/recompute/{symbol}
GET  /api/v1/research-analytics/fractal-matches/{symbol}/{timeframe}
```
— UI Fractal вкладка рендерится из них.

### Обрывы ветки Fractal
1. **AssetFractalService оторван.** По авторскому плану он должен был давать `direction`, `expected_return`, `dominant_horizon` (7/14/30/60 дн.), `phase` (ACCUMULATION/MARKUP/…). **Никто не вызывает.**
2. **MacroFractalEngine оторван.** Должен был выдавать `final_bias` из 5 компонентов (macro, btc, spx, dxy, cross_asset) с весами. **Никто не вызывает.**
3. **Cross-asset analysis (SPX↔BTC, DXY↔BTC) оторван.**
4. **В prediction-пайплайн ни одна фрактальная метрика не поступает** (см. Блок 2).

---

## 1.2. Ветка «TA Engine» (TT Engine) — живая, но изолированная

### Состав
- `ta_engine/` — главный модуль, ~44 000 строк.
- Подключено: `ta_routes`, `ta_setup_api`, `ta_hypothesis_builder`, `idea_worker`, `research_api`.
- **44 endpoints** на `/api/ta/*`.

### Реально доступные эндпоинты
```
/api/ta/analyze (POST)                  ← основной анализ
/api/ta/candles/{symbol} (GET)
/api/ta/confluence[/{symbol}/{tf}] (GET)
/api/ta/debug (GET)
/api/ta/ideas (POST,GET) + CRUD         ← идеи трейдера
/api/ta/indicators/compute (GET)
/api/ta/indicators/registry (GET)
/api/ta/indicators/{symbol}/{tf} (GET)
/api/ta/levels/{symbol}/{tf} (GET)
/api/ta/patterns[/{symbol}/{tf}] (GET)
/api/ta/registry (GET)
/api/ta/research (GET)
/api/ta/setup[/v2][/{symbol}/{tf}] (GET)
/api/ta/status (GET)
/api/ta/structure/{symbol}/{tf} (GET)
```

### Внутренние компоненты (из `COMPLETE_BACKEND_ARCHITECTURE_AUDIT.md`)
- `setup/indicator_engine.py` — 30+ индикаторов (RSI, MACD, BB, ATR, OBV, Supertrend, Ichimoku…)
- `setup/pattern_engine_v3.py` — 574 LOC, паттерны (треугольники, каналы, H&S, флаги)
- `setup/structure_engine_v2.py` — 636 LOC, market bias + regime
- `hypothesis/ta_hypothesis_builder.py` — 714 LOC, генерация `TAHypothesis`
- `probability_engine.py`, `expectation_engine.py`, `scenario_engine_v3.py`, `decision_engine_v2.py`, `live_probability_engine.py`
- `mtf_engine.py` — multi-timeframe alignment

### Где деградация
- ✅ TA Engine endpoints работают (UI их использует для TA tab).
- ❌ **TA Engine не питает prediction-пайплайн напрямую.** `ta_prediction_intelligence/live_adapter.py` использует ТОЛЬКО `ta_engine.context_engine.build_market_context` (1 функция) — вся остальная логика TA Engine (probability_engine, expectation_engine, decision_engine_v2, scenario_engine_v3, hypothesis_builder) **обходится стороной**.
- ❌ TA Engine не имеет продакшн канала в live trading: `SignalRunner` не вызывает `/api/ta/analyze`.

---

## 1.3. Ветка «Exchange Intelligence» (IndicExchange) — 🔴 полностью оторвана

### Состав

| Компонент | LOC | Назначение |
|---|---|---|
| `funding_oi_engine.py` | ~400 | funding rate + OI crowding detection |
| `derivatives_pressure_engine.py` | ~450 | long/short ratio + leverage + squeeze |
| `exchange_liquidation_engine.py` | ~380 | cascade probability + trapped positions |
| `exchange_flow_engine.py` | ~420 | taker buy/sell, absorption detection |
| `exchange_volume_engine.py` | ~380 | volume ratio + CLIMAX/EXHAUSTION |
| `exchange_context_aggregator.py` | ~280 | итог: `exchange_bias` + `confidence` |
| `conflict_resolver/` | ~350 | разрешение конфликтов движков |
| **ИТОГО** | **~2 662** | (плюс `exchange_intel_routes.py`) |

### Состояние

| Проверка | Результат |
|---|---|
| `exchange_intel_routes` подключен в server.py? | ❌ **Нет** (только в `server_original.py`, `server_full.py`) |
| `/api/exchange-intelligence/*` endpoints в OpenAPI? | ❌ **0 endpoints** |
| Кто-то из **активных** модулей импортирует `exchange_intelligence`? | ❌ **Нет**. Импортируют только 4 других orphaned модуля (`trading_product`, `alpha_interactions`, `trading_decision`, `execution_mode_engine` — они тоже не wired) |
| Данные из `exchange_funding_context`, `exchange_oi_snapshots`, `exchange_symbol_snapshots`, `exchange_liquidation_events`, `exchange_trade_flows` собираются? | ❌ Коллекции существуют в `trading_os`, но нет активного worker'а, который бы эти данные читал в `prediction` или `trading` пайплайн |
| Прогноз (`crowding_risk`, `squeeze_probability`, `cascade_probability`, `flow_pressure`) где-то считается в runtime? | ❌ Нигде |

### Почему это критично
По `DEEP_AUDIT_EXCHANGE_SENTIMENT_FRACTAL.md` (апрель) exchange_bias должен быть самым сильным сигналом в объединённом predicting engine:
```python
W_FUNDING    = 0.20
W_DERIVATIVES= 0.20
W_LIQUIDATION= 0.15
W_FLOW       = 0.30   # ← сильнейший сигнал
W_VOLUME     = 0.15
```
…но этот объединённый engine **никогда не был собран**. Вся 3я ветка существует как код-артефакт, не подключённый к реальности.

---

## 1.4. Sentiment / Reflexivity — 🔴 оторвана

| Модуль | LOC | Routes? | Wired? |
|---|---|---|---|
| `reflexivity_engine` (Soros reflexivity: sentiment+positioning+volatility feedback) | 2 160 | `reflexivity_routes.py` | ❌ **Нет** |

- 0 endpoints в OpenAPI.
- Используется только `hypothesis_engine` (тоже not wired), `control_dashboard` (не wired), `system_validation` (не wired).
- Формула `reflexivity_score = 0.35*sentiment + 0.25*positioning + 0.20*trend_accel + 0.20*vol_expansion` — код есть, но никто не вызывает.

---

# БЛОК 2. PREDICTIONS — три параллельные системы, нестыковки

## 2.1. Сосуществующие prediction-системы

| Система | Endpoints | Где код | Статус | Кто вызывает |
|---|---|---|---|---|
| **Legacy `prediction/*`** | 24 (`/api/prediction/*`, `/api/prediction/ta/*`, `/api/prediction/v3/*`) | `modules/prediction/` | 🟡 live, но частично использует `random.uniform()` (см. `PREDICTION_AUDIT.md`) | старый UI + scanner |
| **Middle `ta_prediction/*`** | ? (через `ta_prediction_router`) | `modules/ta_prediction/` | 🟡 wired в server.py, назначение неясно, дублирует другие | ? |
| **New `ta-prediction-intelligence/*`** | 30 (`/api/ta-prediction-intelligence/*`) | `modules/ta_prediction_intelligence/` | 🟢 Working (POC 10/12 + 13/13 + 11/11 + 12/12) | POC-скрипты; HTTP-потребители (UI — частично) |

### Нестыковка между ними
1. Legacy **использует `random.uniform()`** для прогноза пути (см. `PREDICTION_AUDIT.md` строки 212–228 — `/api/forecast/{asset}`, `/api/meta-brain-v2/forecast-curve`).
2. Middle (`ta_prediction`) — остаток от промежуточной итерации, частично дублирует новую.
3. New (`ta-prediction-intelligence`) — чистый Step 6–12 пайплайн, но **герметично изолирован**.

## 2.2. Питание нового prediction-пайплайна (что и откуда читает)

```
ta_prediction_intelligence/live_adapter.fetch_live_context()

  ┌─ research_analytics.indicators → RSI(14), MACD            ✅
  ├─ research_analytics.patterns   → patterns + levels        ✅
  ├─ research_analytics.chart_data → candles + fallback       ✅
  └─ ta_engine.context_engine.build_market_context()  ← ОДИН вызов ✅

    ─ НЕТ ─── exchange_intelligence / funding / OI / flow     ❌
    ─ НЕТ ─── fractal_intelligence / AssetFractal             ❌
    ─ НЕТ ─── macro_fractal_brain / cross_asset               ❌
    ─ НЕТ ─── reflexivity_engine / sentiment                  ❌
    ─ НЕТ ─── ta_engine.hypothesis / probability / decision_v2 ❌
```

### Что поступает в `TAPredictionSetup`:
```python
TAPredictionSetup(
    symbol, timeframe, price,
    direction, confidence, strength,
    trend_strength, structure_state,   # из context_engine
    rsi, macd_hist,                    # из research_analytics
    support, resistance,               # из pattern_service
    atr_pct, volatility_state,         # из context_engine
    patterns=[...]                     # из pattern_service
)
```
— и это ВСЁ. 5 движков (`structure`, `pattern`, `momentum`, `level_zone`, `volatility`) получают только этот узкий slice.

### Что не доходит до движков
- `funding_rate`, `oi_change`, `crowding_risk`, `cascade_probability`, `flow_pressure` (exchange_int)
- `fractal_alignment`, `expected_return`, `dominant_horizon`, `phase` (fractal_int/macro_fractal)
- `reflexivity_score`, `feedback_direction`, `positioning_score` (reflexivity)
- `final_bias` кросс-ассет уровня (cross_asset_intelligence)

**Следствие:** Step 7 калибровка и Step 12 decision-engine работают по обеднённому feature-set. Brier scores: 0.21–0.66 на бакетах (см. observ выше) — калибровка плохая отчасти потому, что критические фичи не попадают в корзину.

## 2.3. Что работает внутри `ta_prediction_intelligence` (это хорошая часть)

✅ Конвейер Step 6 → 7 → 8 → 9 → 10 → 11 → 12 реализован.
✅ Калибровка (buckets: `interaction_type`, `dominant_engine`, `symbol_tf`, `symbol_tf_interaction`) — 4 типа группировок, пересобираются по команде.
✅ Features v1 — 82 фичи, детерминированные хэши, ring buffer.
✅ Debug layer — taxonomy + root cause.
✅ Data Health Gate — trust score (сейчас 0.9, status=broken из-за debug_coverage=0).
✅ ML Readiness — hard gate `n_evaluated ≥ 500` (сейчас 43 — ещё далеко).
✅ Decision Intelligence (Step 12) — dominance + alignment + risk + scenario_selector.

**Persistence (MongoDB `trading_os`):**
- `ta_prediction_history` — 43 записей
- `ta_prediction_temporal_buffer` — 18
- калибровочные коллекции создаются on-demand

---

# БЛОК 3. TRADING SYSTEM — работает на SimpleMA, игнорирует всё остальное

## 3.1. Полный живой поток

```
[DAEMON] SignalRunner._loop()              (interval=30s)
    │
    ├─ symbols = ["BTCUSDT","ETHUSDT"]     (из startup universe)
    │
    ├─ for symbol in symbols:
    │     price = market_data.get_last_price(symbol, tf="4h")
    │     signal = SimpleMAGenerator.generate_signal(price)     ← ЕДИНСТВЕННЫЙ источник
    │     if signal and not cooldown:
    │         decision = runtime_service._create_decision_from_signal(signal)
    │         await runtime_service.approve_decision(decision.id)  ← AUTO-APPROVE
    │
    ▼
[FLOW] runtime_service.approve_decision
    │
    ├─ ExecutionBridge.submit(signal)
    │     │
    │     ├─ gate 1: short_trading_enabled (DB flag)
    │     ├─ gate 2: short_downtrend_only ⟺ regime == DOWNTREND
    │     ├─ gate 3: long_uptrend_only   ⟺ regime == UPTREND
    │     │       ← regime вычисляется _compute_current_regime(): EMA20/50 на 1h
    │     ├─ gate 4: confidence adjustment (LIVE-3a soft gate, forensic-based multipliers)
    │     └─ gate 5: low-volatility gate (LIVE-3d, ATR threshold)
    │
    ▼
[QUEUE] ExecutionQueue v2 → Paper/Binance adapter
    │
    ▼
[DAEMONS]
    ├─ mark_price_updater          (обновляет PnL каждые 8s)
    └─ position_exit_manager       (TP=+0.30% / SL=-0.30% / TIME=30м)
    │
    ▼
[REPOSITORY] trading_cases collection → trading_cases tab
```

## 3.2. Что НЕ используется в этом потоке

| Компонент | Назначение | Используется в live loop? |
|---|---|---|
| `ta_engine` (44 ep, 44k LOC) | паттерны, индикаторы, структура | ❌ нет |
| `ta_prediction_intelligence` (30 ep, Steps 6–12) | калиброванные predictions | ❌ нет |
| `prediction/*` (24 ep) | legacy predictions | ❌ нет |
| `exchange_intelligence` | funding/OI/liquidation/flow/volume | ❌ нет |
| `fractal_intelligence` | AssetFractalService | ❌ нет |
| `macro_fractal_brain` | cross-asset bias | ❌ нет |
| `reflexivity_engine` | sentiment + feedback | ❌ нет |
| `hypothesis_engine` (standalone) | hypothesis testing | ❌ нет |
| `alpha_factory`, `alpha_interactions` | factor generation | ❌ нет |
| `trading_decision` (decision_layer, execution_mode, position_sizing) | ❌ routes не wired, engines не вызываются | ❌ нет |

## 3.3. Что используется

| Компонент | Как вызывается |
|---|---|
| `SimpleMAGenerator` | `signal_generator/simple_ma_generator.py` — EMA(short)/EMA(long) cross |
| `runtime_service` | принимает decisions, auto-approve, forwards to bridge |
| `ExecutionBridge` | 4 gate'а; отправляет в queue |
| `_compute_current_regime` | EMA20/50 на 1h (inline в `execution/bridge.py`) — **НЕ связан с `regime/market_regime.py`** — это дубликат |
| `regime_controls` (DB) | кнопки ON/OFF для short/long gates |
| `market_context` (ATR 20-период) | используется low-vol gate |
| `mark_price_updater` + `position_exit_manager` | TP/SL/Time exit |
| `trading_cases` repo | persistence |

## 3.4. Деградации

1. **Нет enrichment сигнала.** SimpleMA даёт `{side, entry_price, confidence=0.60}` — всё. Никакой confluence, MTF, indicator alignment, pattern confirmation.
2. **Regime detector дублируется.** `modules/regime/market_regime.py` — официальный; `_compute_current_regime()` в `execution/bridge.py` — локальный дубликат. Они могут расходиться.
3. **Confidence всегда ~0.60** → gate LIVE-3a применяет forensic multipliers, но база плоская, т.е. нет реального сигнала для дискриминации.
4. **Auto-approve = ON** — human-in-the-loop отсутствует (по архитекторской директиве "closing-loop.1").
5. **TP/SL и TIME_EXIT хардкод** в `position_exit_manager.py` — любая переконфигурация требует рестарта backend.

---

# БЛОК 4. МЁРТВЫЙ КОД — «созвездие orphaned»

Ниже — модули, которые:
- НЕ подключены как router в `server.py`,
- НЕ вызываются из wired модулей,
- но содержат значительный код (их импортируют друг друга).

| Модуль | LOC | Импортирует orphaned ветки |
|---|---|---|
| `trading_product` | 2 308 | exchange_intelligence, fractal_intelligence |
| `alpha_interactions` | 10 402 | exchange_intelligence |
| `trading_decision` (execution_mode, position_sizing, market_state, decision_layer) | 6 163 | exchange_intelligence |
| `execution_context` | 1 351 | fractal_intelligence, macro_fractal_brain |
| `strategy_brain` (включая `fractal_hint`) | 6 928 | fractal_intelligence |
| `hypothesis_engine` | 5 711 | reflexivity_engine |
| `control_dashboard` | — | fractal_intelligence, reflexivity_engine |
| `regime_memory` | 3 573 | fractal_market_intelligence |
| `system_validation` (ab_test_routes, integration_audit) | 4 076 | fractal_intelligence, macro_fractal_brain, reflexivity_engine |
| `cross_asset_intelligence` | 1 801 | fractal_intelligence |
| `exchange_intelligence` | 2 662 | — (сам orphan) |
| `fractal_intelligence` | 2 985 | — (сам orphan) |
| `macro_fractal_brain` | 1 584 | — (сам orphan) |
| `reflexivity_engine` | 2 160 | — (сам orphan) |
| `fractal_similarity` | 2 013 | — (сам orphan) |
| **ИТОГО** | **~54 000 LOC** | |

Это ~54k строк кода, который автор репозитория разрабатывал последний месяц-полтора — и который **сейчас не участвует ни в HTTP-поверхности, ни в trading loop**.

---

# БЛОК 5. КАРТА РАЗРЫВОВ (actionable)

## Разрыв R1 — Exchange Intelligence <-> Prediction Pipeline
- **Что должно было быть:** `exchange_context_aggregator` → feature в `live_adapter` → 5 движков.
- **Где разорвано:** `live_adapter.py:540–580` собирает `TAPredictionSetup` без единого exchange-поля.
- **Как починить (minimum viable bridge):** в `live_adapter._build_setup()` добавить `exchange_ctx = ExchangeContextAggregator().compute(symbol)` и пробросить в `_raw_data` → engines расширить чтением этих полей.

## Разрыв R2 — Fractal Intelligence <-> Prediction
- **Что должно было быть:** `MacroFractalEngine` → `final_bias` + `expected_return` → prediction.
- **Где разорвано:** live_adapter не вызывает ни `AssetFractalService`, ни `MacroFractalEngine`.
- **Как починить:** добавить fractal routes в `server.py` + вызвать engine из live_adapter.

## Разрыв R3 — Reflexivity <-> Prediction
- **Что должно было быть:** `ReflexivityEngine.compute_state()` → `reflexivity_score` + `feedback_direction` → модификатор hypothesis.
- **Где разорвано:** ReflexivityEngine не вызывается ни в одном wired модуле.
- **Как починить:** подключить `reflexivity_routes` + добавить поле в `TAPredictionSetup`.

## Разрыв R4 — Predictions <-> Trading
- **Что должно было быть:** `decision_intelligence.primary` + `strength` + `conf` из `ta_prediction_intelligence` → сигнал в `ExecutionBridge`.
- **Где разорвано:** `SignalRunner` вызывает только `SimpleMA`; `ExecutionBridge.submit()` не читает `ta_prediction_intelligence/live`.
- **Как починить:** переделать `signal_generator/runner.py` чтобы параллельно с `SimpleMA` консультироваться с `/ta-prediction-intelligence/live` и использовать его `decision_intelligence` для affirmative/veto.

## Разрыв R5 — TA Engine hypothesis/probability/decision_v2 <-> Prediction
- **Что должно было быть:** `ta_hypothesis_builder` → `TAHypothesis` → вход prediction engines.
- **Где разорвано:** wired в routes, но предсказательный пайплайн не консумится.
- **Как починить:** в `live_adapter.py` после сбора фич дополнительно вызывать `TAHypothesisBuilder.build()` и передавать `TAHypothesis` в engines.

## Разрыв R6 — Three parallel prediction systems
- **Что должно было быть:** одна система.
- **Где разорвано:** `prediction/routes`, `ta_prediction/routes`, `ta_prediction_intelligence/*` — три параллели.
- **Как починить:** выбрать `ta_prediction_intelligence` как канонический; legacy и middle пометить как deprecated; переключить UI.

## Разрыв R7 — Regime detector duplication
- **Что должно было быть:** единый `RegimeDetector` (`modules/regime/market_regime.py`).
- **Где разорвано:** `execution/bridge.py._compute_current_regime()` — локальный дубликат.
- **Как починить:** удалить локальную копию, вызывать canonical.

## Разрыв R8 — Hardcoded TP/SL/Time в position_exit_manager
- **Что должно было быть:** конфиг через `regime_controls` или отдельную коллекцию.
- **Где разорвано:** `modules/positions/position_exit_manager.py` — `TP_PCT=0.0030, SL_PCT=0.0030, TIME_EXIT_MIN=30` хардкод.
- **Как починить:** вытащить в `runtime_config` collection + hot-reload.

---

# БЛОК 6. ТАБЛИЦА ЗДОРОВЬЯ всех 3 веток

| Ветка | Код | Routes в server.py | Endpoints live | Используется в Prediction? | Используется в Trading? | Статус |
|---|---|---|---|---|---|---|
| **Fractal (fractal_market_intelligence)** | 2 600 LOC | ✅ | 10 | ❌ | ❌ | 🟢 жив для UI |
| Fractal (fractal_intelligence) | 2 985 LOC | ❌ | 0 | ❌ | ❌ | 🔴 ORPHAN |
| Fractal (macro_fractal_brain) | 1 584 LOC | ❌ | 0 | ❌ | ❌ | 🔴 ORPHAN |
| Fractal (cross_asset_intelligence) | 1 801 LOC | ❌ | 0 | ❌ | ❌ | 🔴 ORPHAN |
| Fractal (fractal_similarity) | 2 013 LOC | n/a | — | ❌ | ❌ | 🔴 UNUSED |
| **TA Engine** | ~44 000 LOC | ✅ | 44 | только `context_engine` (1 fn) | ❌ | 🟡 частично |
| **Exchange Intelligence** | 2 662 LOC | ❌ | 0 | ❌ | ❌ | 🔴 ORPHAN |
| **Reflexivity (sentiment)** | 2 160 LOC | ❌ | 0 | ❌ | ❌ | 🔴 ORPHAN |
| ta_prediction (legacy) | — | ✅ | ? | — | ❌ | 🟡 deprecated |
| prediction (legacy) | — | ✅ | 24 | — | ❌ | 🟡 deprecated (использует random.uniform) |
| **ta_prediction_intelligence** | — | ✅ | 30 | self | ❌ | 🟢 жив, изолирован |
| signal_generator (SimpleMA) | ~400 LOC | — | 18 | — | ✅ | 🟢 единственный источник |
| execution_bridge | 1 027 LOC | — | 60 | — | ✅ (4 гейта) | 🟢 |
| positions (mark/exit) | — | — | — | — | ✅ | 🟢 |

---

# БЛОК 7. ЧТО ДЕЛАТЬ ДАЛЬШЕ (предложенные этапы)

> Все шаги соответствуют инвариантам в `PHASE_STATE.md` и `plan_project.md`
> (нельзя менять SimpleMA, аггрегатор, conflict logic без forensic-обоснования).

### Этап A — Безопасное восстановление HTTP-поверхности (чистый read-only)
Цель: вернуть видимость оторванных веток, не трогая production logic.
1. Зарегистрировать в `server.py`:
   - `modules.exchange_intelligence.exchange_intel_routes`
   - `modules.fractal_intelligence.asset_fractal_routes`
   - `modules.fractal_intelligence.fractal_context_routes`
   - `modules.macro_fractal_brain.macro_fractal_routes`
   - `modules.reflexivity_engine.reflexivity_routes`
   - `modules.cross_asset_intelligence.cross_asset_routes`
2. Прокатать smoke-тесты каждого endpoint.
3. Написать `poc_branches_connectivity.py` с валидацией: каждая ветка возвращает живой JSON для BTCUSDT/ETHUSDT.
4. **Нулевой риск для trading** — это чистое read-only добавление HTTP-маршрутов.

### Этап B — Форензик на каждой ветке (без кода)
Для каждой оторванной ветки:
1. Запустить её engine на 30 дней исторических свечей.
2. Померить корреляцию с `trading_cases.realized_pnl_pct`.
3. Решить: включать в prediction (если alpha > 0) или reserve.

### Этап C — Интеграция в prediction pipeline (после архитекторского утверждения)
В порядке приоритета по ожидаемой alpha:
1. **Exchange Intelligence** (авторский W_FLOW=0.30 — самый весомый сигнал).
2. **MacroFractalEngine + AssetFractalService** (dominant_horizon + expected_return — source of targets).
3. **Reflexivity** (continuation vs reversal modifier).
4. **Cross-asset** (DXY/SPX/BTC bridges).

Каждый шаг:
- extension-only модификация `live_adapter.py` (добавить поле в `TAPredictionSetup`);
- extension-only модификация движков (читать новое поле, но старый scorer без изменений);
- отдельный `phase tag` в `trading_cases`, чтобы разделять результаты.

### Этап D — Consolidation prediction-систем
1. Пометить `/api/prediction/*` как deprecated (alias → ta_prediction_intelligence).
2. Пометить `/api/ta-prediction/*` (middle) как deprecated.
3. UI переключить на `/api/ta-prediction-intelligence/live`.

### Этап E — Соединение predictions ↔ trading
Только после этапов A–D.
1. `SignalRunner._loop` параллельно с SimpleMA вызывает `/api/ta-prediction-intelligence/live/{symbol}`.
2. Используется `decision_intelligence.strength` как дополнительный SOFT-gate (не blocking, только logging) в shadow-режиме 2 недели.
3. Forensic сравнивает performance с/без gate.
4. Если alpha положительная — переключить на HARD-gate.

### Этап F — Cleanup
Удалить `server_original.py`, `server_full.py`, `server.py:1323 UnboundLocalError`, дубликат `_compute_current_regime`.

---

# БЛОК 8. ПРИЛОЖЕНИЕ — полный список «что подключено» в server.py

120 `include_router(...)` вызовов. Группировка:

| Группа | Routers |
|---|---|
| TA | `ta_engine_router`, `ta_setup_api_router`, `ta_setup_router`, `ta_ideas_router`, `ta_prediction_router`, `ta_prediction_intelligence_router`, `ta_learning_router`, `ta_debug_router`, `ta_data_health_router`, `ta_ml_readiness_router`, `ta_root_cause_router`, `ta_simulation_router` |
| Fractal/Analysis | `fractal_router` (fractal_market_intelligence), `combined_analysis_router`, `meta_router`, `hypothesis_router` (research.hypothesis_engine) |
| Trading | `strategy_engine_router`, `strategy_router`, `trading_engine_router`, `trading_core_router`, `trading_terminal_*` (10+ sub-routers), `signal_engine_router` |
| Execution | `execution_router`, `execution_*` (queue, routes, jobs, shadow_test, trace_diagnostic, quality, logger) — ~15 |
| Runtime | `runtime_router`, `p27_router`, `paper_performance_router`, `auto_run_router`, `auto_safety_router` |
| Risk/Portfolio | `risk_router`, `dynamic_risk_router`, `portfolio_router`, `portfolio_v3_router`, `portfolio_session_router`, `portfolio_risk_router` |
| Other | `broker_router`, `terminal_live_router`, `trading_cases_router`, `alpha_factory_router`, `alpha_policy_router` |

**НЕ подключены (основные):**
`exchange_intelligence`, `fractal_intelligence`, `macro_fractal_brain`, `cross_asset_intelligence`, `reflexivity_engine`, `trading_product`, `alpha_interactions`, `trading_decision`, `execution_context`, `strategy_brain`, `hypothesis_engine`, `regime_memory`, `system_validation`, `control_dashboard`, `adaptive_intelligence`, `evolution_engine`, `autopsy_engine`, `reflexivity_engine`, `microstructure_intelligence_v2`, `microstructure_lab`, `alpha_ecology`, `alpha_tournament`, `portfolio_intelligence`, `portfolio_backtester`, `regime_intelligence_v2`, `regime_graph`, `reflexivity_engine`, `shadow_portfolio`, `shadow_stress_lab`, и многие другие.

---

**Аудит выполнен 2026-05-04.**
**Следующий ход — за архитектором:** выбрать этап (A → F) и порядок восстановления связей.
