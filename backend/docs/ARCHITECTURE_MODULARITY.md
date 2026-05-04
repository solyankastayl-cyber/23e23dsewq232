# Market Analysis Domain Architecture
## TA Engine + Exchange Intelligence

Version: Phase 13.8.B  
Status: **MODULAR** ✅

---

## Архитектурная схема

```
Core Modules
│
├── Market Analysis Domain ◄─────────────────────────────┐
│     │                                                   │
│     ├── TA Engine (Price Analysis)                      │
│     │     ├── alpha_factory/                            │
│     │     │     ├── alpha_node_registry                 │
│     │     │     ├── feature_library                     │
│     │     │     ├── factor_generator                    │
│     │     │     ├── factor_ranker                       │
│     │     │     ├── alpha_graph                         │
│     │     │     ├── alpha_dag                           │
│     │     │     └── alpha_deployment                    │
│     │     └── patterns/, detectors/, hypothesis/        │
│     │                                                   │
│     └── Exchange Intelligence (Market Structure)        │
│           ├── funding_oi_engine                         │
│           ├── derivatives_pressure_engine               │
│           ├── exchange_liquidation_engine               │
│           ├── exchange_flow_engine                      │
│           ├── exchange_volume_engine                    │
│           └── exchange_context_aggregator               │
│                                                         │
├── Fractals (reserved)                                   │
├── Sentiment (reserved)                                  │
├── On-chain (reserved)                                   │
│                                                         │
└── Exchange Core (TS Data Layer) ────────────────────────┘
          │
          ▼
      MongoDB Collections
          │
          ▼
      Exchange Intelligence (Python Analysis)
```

---

## Доказательство модульности

### Тест 1: Удаляем Exchange Intelligence → TA работает?
```python
sys.modules['modules.exchange_intelligence'] = None
from modules.alpha_factory.alpha_node_registry import get_alpha_registry
# ✅ TA работает: 88 nodes
```

### Тест 2: Удаляем TA → Exchange Intelligence работает?
```python
sys.modules['modules.alpha_factory'] = None
from modules.exchange_intelligence.exchange_context_aggregator import ExchangeContextAggregator
# ✅ Exchange работает: BULLISH, confidence=0.808
```

---

## Правила модульности

### ✅ Разрешено:
- Анализировать одни и те же candles
- Работать с одними и теми же symbols
- Использовать общую MongoDB
- Регистрироваться в одном API сервере

### ❌ Запрещено:
- TA импортирует Exchange Intelligence
- Exchange Intelligence импортирует TA
- Прямые вызовы функций между модулями
- Общие internal types/contracts

---

## Потоки данных

```
                    ┌─────────────────┐
                    │   Market Data   │
                    │    (Candles)    │
                    └────────┬────────┘
                             │
              ┌──────────────┼──────────────┐
              │              │              │
              ▼              ▼              ▼
    ┌─────────────────┐    ...    ┌─────────────────────┐
    │   TA Engine     │           │ Exchange Intelligence│
    │  (Patterns)     │           │  (Market Structure)  │
    └────────┬────────┘           └──────────┬──────────┘
             │                               │
             │    НЕТ СВЯЗИ МЕЖДУ НИМИ       │
             │                               │
             ▼                               ▼
    ┌─────────────────┐           ┌─────────────────────┐
    │  TA Signals     │           │  Exchange Context    │
    │  /api/ta/*      │           │  /api/exchange-*     │
    └────────┬────────┘           └──────────┬──────────┘
             │                               │
             └───────────────┬───────────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │ Decision Layer  │
                    │   (Future)      │
                    └─────────────────┘
```

---

## Data Layer Architecture

```
Exchange Core (TypeScript)
│
├── funding/services/* ─────► MongoDB: exchange_funding_context
├── indicators/positioning/* ► MongoDB: exchange_symbol_snapshots
├── liquidations/* ─────────► MongoDB: exchange_liquidation_events
├── order-flow/* ───────────► MongoDB: exchange_trade_flows
└── volume/* ───────────────► MongoDB: candles (volume data)
         │
         ▼
    MongoDB Collections
         │
         ▼
Exchange Intelligence (Python)
│
├── funding_oi_engine ◄────── exchange_funding_context
├── derivatives_engine ◄───── exchange_symbol_snapshots
├── liquidation_engine ◄───── exchange_liquidation_events
├── flow_engine ◄──────────── exchange_trade_flows
└── volume_engine ◄────────── candles + trade_flows
```

---

## API Endpoints (Independent)

### TA Engine `/api/ta/*`
```
GET  /api/ta/registry     # Alpha nodes registry
GET  /api/ta/patterns     # Pattern definitions
POST /api/ta/analyze      # Run analysis
```

### Alpha Factory `/api/alpha-factory/*`
```
GET  /api/alpha-factory/nodes
GET  /api/alpha-factory/stats
POST /api/alpha-factory/nodes
```

### Exchange Intelligence `/api/exchange-intelligence/*`
```
GET  /api/exchange-intelligence/context/{symbol}
GET  /api/exchange-intelligence/funding/{symbol}
GET  /api/exchange-intelligence/derivatives/{symbol}
GET  /api/exchange-intelligence/liquidation/{symbol}
GET  /api/exchange-intelligence/flow/{symbol}
GET  /api/exchange-intelligence/volume/{symbol}
```

---

## Graceful Degradation

Server регистрирует каждый модуль в `try/except`:

```python
try:
    from modules.alpha_factory.alpha_routes import router
    app.include_router(router)
except ImportError:
    print("Alpha Factory not available")

try:
    from modules.exchange_intelligence.exchange_intel_routes import router
    app.include_router(router)
except ImportError:
    print("Exchange Intelligence not available")
```

**Результат:** Если один модуль падает — остальные продолжают работать.

---

## Версионирование

| Module | Version | Phase |
|--------|---------|-------|
| TA Engine (Alpha Factory) | 13.7.0 | Complete |
| Exchange Intelligence | 13.8.B | Native Binding |
| Combined Domain | 13.8.B | Active |

---

## Когда объединять в Decision Layer

Только когда оба модуля будут:
- TA: Hypothesis Engine ready
- Exchange: Conflict Resolver ready

```
Future Architecture:
│
├── TA Signal ─────────┐
│                      ├──► Decision Layer ──► Trading Signal
├── Exchange Context ──┘
│
```
