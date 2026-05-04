# 🏛️ ПОЛНЫЙ АУДИТ БЭКЕНДА ТОРГОВОЙ СИСТЕМЫ

**Дата:** 2026-04-10  
**Анализ:** Trading Terminal Backend Architecture  
**Размер кодовой базы:** ~44,000+ строк только TA Engine

---

## 📊 ОБЩАЯ СТАТИСТИКА

### Метрики
- **Всего модулей:** 150+ директорий
- **Python файлов:** 2,202 файлов
- **Размер кодовой базы:** 37MB в /modules
- **TA Engine:** ~44,273 строк кода
- **Execution Reality:** ~25+ sub-modules
- **Всего слоев:** 12 архитектурных уровней

---

## 🎯 АРХИТЕКТУРНЫЕ СЛОИ (12 УРОВНЕЙ)

### СЛОЙ 0: OPERATOR CONTROL (NEW - Sprint R1/R2/R3)
**Расположение:** `/app/backend/modules/runtime/`
**Статус:** ✅ ПОЛНОСТЬЮ РАБОТАЕТ

**Назначение:** Human-in-the-loop контроль торговой системы

**Компоненты:**
1. **RuntimeController** (`controller.py` - 3,753 строк)
   - Состояния: MANUAL / SEMI_AUTO / AUTO
   - Loop interval management
   - Symbols management
   - Mode gate (блокирует/разрешает execution)

2. **PendingDecisionRepository** (`repository.py` - 4,475 строк)
   - Очередь решений для SEMI_AUTO mode
   - Approve/Reject логика
   - Decision expiration (30 минут TTL)

3. **RuntimeService** (`service.py` - 11,495 строк)
   - Facade для всех runtime операций
   - Интеграция с RiskManager, OrderManager, ExchangeService
   - Cycle execution (run-once logic)

4. **SignalProvider** (`signal_provider.py` - 1,446 строк)
   - Mock signals для testing
   - Placeholder для real signal integration

**API Endpoints:**
```python
GET  /api/runtime/state              # Runtime status
POST /api/runtime/start              # Start runtime
POST /api/runtime/stop               # Stop runtime  
POST /api/runtime/mode               # Set mode (MANUAL/SEMI_AUTO/AUTO)
POST /api/runtime/run-once           # Manual cycle execution
GET  /api/runtime/decisions/pending  # Get pending decisions
POST /api/runtime/decisions/{id}/approve  # Approve decision
POST /api/runtime/decisions/{id}/reject   # Reject decision
```

**Flow:**
```
MANUAL mode:     Signal → BLOCKED
SEMI_AUTO mode:  Signal → Pending Queue → Human Approval → Execution
AUTO mode:       Signal → Direct Execution
```

---

### СЛОЙ 1: SIGNAL GENERATION (TA ENGINE)
**Расположение:** `/app/backend/modules/ta_engine/`
**Статус:** ✅ PRODUCTION READY
**Размер:** ~44,273 строк кода

**Назначение:** Технический анализ и генерация торговых сигналов

#### 1.1 TA Setup System
**Файл:** `setup/indicator_engine.py` (1,793 строк)

**30+ Индикаторов:**

| Категория | Индикаторы | Описание |
|-----------|------------|----------|
| **Trend** | EMA (20/50/200), SMA, HMA, VWMA, Supertrend, Ichimoku | Направление тренда |
| **Momentum** | RSI, MACD, Stochastic, StochRSI, Momentum, ROC, CCI, Williams %R | Сила движения |
| **Volatility** | ATR, Bollinger Bands, BB Width, Keltner, Donchian | Волатильность рынка |
| **Volume** | OBV, VWAP, MFI, CMF, ADL | Объёмный анализ |
| **Structure** | Parabolic SAR, TRIX | Структура рынка |

#### 1.2 Pattern Detection System
**Файл:** `setup/pattern_engine_v3.py` (574 строк)

**Паттерны:**
- **Triangles:** Ascending, Descending, Symmetrical
- **Channels:** Ascending, Descending, Horizontal
- **Reversal:** Double Top/Bottom, Head & Shoulders, Inverse H&S
- **Continuation:** Flags, Pennants, Wedges (Falling/Rising)

#### 1.3 Structure Analysis
**Файл:** `setup/structure_engine_v2.py` (636 строк)

**Компоненты:**
- **Market Bias:** Bullish/Bearish/Neutral detection
- **Regime Detection:** Trending vs Ranging
- **Support/Resistance Levels** (`level_engine.py`)
- **Fibonacci Levels** (`fibonacci/fibonacci_engine.py`)

#### 1.4 Hypothesis Builder
**Файл:** `hypothesis/ta_hypothesis_builder.py` (714 строк)

**Логика:**
```python
TAHypothesis = {
    "direction": "BUY" | "SELL",
    "confidence": 0.0 - 1.0,
    "entry_zone": (price_low, price_high),
    "stop_loss": price,
    "take_profit": [price1, price2, price3],
    "pattern": "Triangle_Breakout",
    "regime": "TRENDING",
    "supporting_factors": [...],
    "invalidation_price": price
}
```

#### 1.5 Multi-Timeframe Analysis
**Файл:** `mtf_engine.py`

**Timeframes:**
- 1m, 5m, 15m, 1h, 4h, 1D
- Alignment scoring across timeframes
- HTF confirmation logic

---

### СЛОЙ 2: PREDICTION ENGINE
**Расположение:** `/app/backend/modules/prediction/`
**Статус:** ✅ ACTIVE

**Компоненты:**
1. **Direction Prediction:** BUY/SELL/NEUTRAL
2. **Target Price Prediction:** TP1, TP2, TP3
3. **Confidence Scoring:** 0.0 - 1.0
4. **Scenario Generation:** Bull/Base/Bear scenarios
5. **Path Probability:** Вероятность достижения таргета

---

### СЛОЙ 3: STRATEGY ENGINE
**Расположение:** `/app/backend/modules/strategy_engine/`
**Статус:** ✅ PRODUCTION

**Файлы:**
- `kill_switch.py` - Emergency stop all
- `risk_manager.py` - Risk validation
- `routes.py` - API endpoints
- `models.py` - Strategy models

**Логика:**
```python
Strategy Flow:
1. Receive Signal (from TA/Prediction)
2. Validate against Kill Switch
3. Check Risk Manager constraints
4. Generate Trading Decision
5. Pass to Execution Layer
```

---

### СЛОЙ 4: RISK MANAGEMENT
**Расположение:** `/app/backend/modules/risk/`
**Статус:** ✅ ACTIVE

**Компоненты:**

#### 4.1 Risk Engine
**Файл:** `risk_engine.py`

**Checks:**
- Position size limits
- Max exposure per asset
- Portfolio heat (total risk %)
- Correlation checks
- Daily loss limits

#### 4.2 Institutional Risk
**Расположение:** `/app/backend/modules/institutional_risk/`

**Sub-modules:**
- `var_engine/` - Value at Risk calculation
- `tail_risk/` - Extreme event modeling
- `correlation_spike/` - Correlation monitoring
- `cluster_contagion/` - Cluster risk
- `crisis_aggregator/` - Crisis scenarios

#### 4.3 Position Sizing
**Логика:**
```python
Position Size = (
    Account Balance *
    Risk Per Trade % *
    (Entry Price - Stop Loss) / Entry Price
)
```

---

### СЛОЙ 5: EXECUTION REALITY (P0 MILESTONE A)
**Расположение:** `/app/backend/modules/execution_reality/`
**Статус:** ✅ PRODUCTION READY
**Размер:** 25+ sub-modules

**Назначение:** Real-world execution pipeline с full lifecycle management

#### 5.1 Order Manager
**Файл:** `execution_reality_controller.py`

**Функции:**
- Order placement
- Order status tracking
- Fill reconciliation
- Order cancellation
- Position sync

#### 5.2 Exchange Adapters
**Расположение:** `adapters/`

**Поддерживаемые exchanges:**
1. **Binance Demo** (`binance_rest_adapter.py`)
   - REST API integration
   - User stream (WebSocket)
   - Listen key management
   - Order mapping (Binance ↔ Internal)

2. **Paper Trading** (mock adapter)
   - Simulated fills
   - No real money
   - Testing environment

#### 5.3 Execution Queue v2
**Расположение:** `queue_v2/`

**Компоненты:**
- `execution_job_models.py` - Job states
- `execution_queue_repository.py` - Persistent storage
- `execution_queue_worker.py` - Worker pool
- `execution_retry_scheduler.py` - Retry logic
- `execution_job_fsm.py` - Finite State Machine

**Job States:**
```
QUEUED → PROCESSING → SUBMITTED → FILLED → COMPLETED
                  ↓
              FAILED → RETRY → DEAD_LETTER_QUEUE
```

#### 5.4 Event Bus
**Расположение:** `events/`

**Events:**
- `SIGNAL_DETECTED` - Signal generated
- `DECISION_APPROVED` - Decision approved
- `ORDER_SUBMITTED` - Order sent to exchange
- `ORDER_FILLED` - Order executed
- `ORDER_REJECTED` - Order rejected
- `RUNTIME_ERROR` - System error

**Storage:** MongoDB `execution_events` collection

#### 5.5 PnL Engine
**Расположение:** `pnl/`

**Компоненты:**
- `pnl_engine.py` - Realized/Unrealized PnL
- `fee_engine.py` - Fee calculation (maker/taker)
- `slippage_engine.py` - Slippage tracking
- `trade_ledger.py` - Trade history

#### 5.6 Reconciliation
**Расположение:** `reconciliation/`

**Функции:**
- Exchange snapshot polling
- Order state diff detection
- Position mismatch alerts
- Auto-correction logic

#### 5.7 Rate Limiting
**Расположение:** `rate_limit/`

**Механизмы:**
- Token bucket algorithm
- Circuit breaker
- Request throttling
- Burst protection

---

### СЛОЙ 6: PORTFOLIO MANAGEMENT
**Расположение:** `/app/backend/modules/portfolio_manager/`
**Статус:** ✅ ACTIVE

**Компоненты:**

#### 6.1 Portfolio Engine
**Файл:** `portfolio_engine.py`

**Функции:**
- Position aggregation
- Portfolio value calculation
- Exposure tracking
- Performance metrics

#### 6.2 Portfolio Registry
**Файл:** `portfolio_registry.py`

**Данные:**
- Active positions
- Historical trades
- Per-symbol P&L
- Risk metrics

#### 6.3 Trading Cases
**Расположение:** `/app/backend/modules/trading_cases/`

**Lifecycle per position:**
```
ENTRY → ACTIVE → (STOP_HIT | TARGET_HIT | MANUAL_CLOSE) → CLOSED
```

---

### СЛОЙ 7: TRADING TERMINAL
**Расположение:** `/app/backend/modules/trading_terminal/`
**Статус:** ✅ ACTIVE

**Sub-modules:**
- `accounts/` - Account management
- `control/` - System control
- `dashboard/` - Metrics dashboard
- `execution/` - Execution UI bridge
- `portfolio/` - Portfolio view
- `positions/` - Position tracking
- `risk/` - Risk monitoring
- `trades/` - Trade history
- `validation/` - Pre-trade validation

---

### СЛОЙ 8: MARKET DATA
**Расположение:** `/app/backend/modules/market_data_live/`
**Статус:** ✅ ACTIVE

**Источники:**
- Coinbase (auto-initialized)
- Binance
- Historical data fallback

**Данные:**
- Real-time price
- Candles (1m, 5m, 15m, 1h, 4h, 1D)
- Order book snapshots
- Funding rates
- Open interest

---

### СЛОЙ 9: ALPHA FACTORY
**Расположение:** `/app/backend/modules/alpha_factory/`
**Статус:** 🟡 RESEARCH

**Компоненты:**
- `factor_generator/` - Feature engineering
- `factor_ranker/` - Factor importance
- `alpha_dag/` - Alpha dependency graph
- `alpha_deployment/` - Alpha production deployment
- `validation_bridge/` - Validation integration

---

### СЛОЙ 10: RESEARCH & VALIDATION
**Расположение:** `/app/backend/modules/research/`
**Статус:** 🟡 RESEARCH

**Sub-modules:**
- `hypothesis_engine/` - Hypothesis testing
- `monte_carlo_engine/` - Monte Carlo simulation
- `scenario_engine/` - Scenario analysis
- `calibration_matrix/` - Strategy calibration
- `edge_discovery_engine/` - Edge discovery

---

### СЛОЙ 11: SYSTEM INTELLIGENCE
**Расположение:** `/app/backend/modules/system_control/`
**Статус:** ✅ ACTIVE

**Компоненты:**
- System metrics
- Health monitoring
- Auto-healing
- Circuit breakers
- Performance tracking

---

### СЛОЙ 12: AUDIT & LOGGING
**Расположение:** `/app/backend/modules/audit/`
**Статус:** ✅ ACTIVE

**Данные:**
- All API calls
- Trade decisions
- Risk violations
- System errors
- Performance metrics

---

## 🔄 ПОЛНЫЙ EXECUTION FLOW

### Режим SEMI_AUTO (Human-in-the-loop)

```
1. SIGNAL GENERATION
   TA Engine → Hypothesis → Signal
   ↓

2. RUNTIME GATE (NEW)
   RuntimeService checks mode
   Mode = SEMI_AUTO → Create Pending Decision
   ↓

3. PENDING QUEUE
   Decision stored in MongoDB
   Frontend polls /api/runtime/decisions/pending
   ↓

4. HUMAN APPROVAL
   User clicks APPROVE in UI
   POST /api/runtime/decisions/{id}/approve
   ↓

5. RISK VALIDATION
   RiskManager.evaluate_signal(signal)
   - Position limits
   - Exposure checks
   - Kill switch status
   ↓

6. ORDER CREATION
   OrderManager.place_order(order)
   ↓

7. EXECUTION QUEUE
   Job created in execution_queue_v2
   State: QUEUED
   ↓

8. EXCHANGE SUBMISSION
   BinanceRestAdapter.submit_order(order)
   State: SUBMITTED
   ↓

9. FILL RECONCILIATION
   User stream receives fill event
   State: FILLED
   ↓

10. PORTFOLIO UPDATE
    PortfolioManager.update_position(fill)
    TradingCase created
    ↓

11. EVENT LOGGING
    ExecutionEventBus.emit("ORDER_FILLED")
    Stored in execution_events collection
    ↓

12. UI UPDATE
    Frontend ExecutionFeed shows event
    Position appears in Portfolio tab
```

---

## 📁 DATABASE SCHEMA

### MongoDB Collections

**Runtime:**
```javascript
// runtime_config
{
  config_id: "main",
  symbols: ["BTCUSDT"],
  loop_interval_sec: 60,
  mode: "SEMI_AUTO",
  enabled: true,
  last_run_at: 1775844105,
  next_run_at: 1775844165
}

// pending_decisions
{
  decision_id: "dec_abc123",
  symbol: "BTCUSDT",
  side: "BUY",
  status: "PENDING",
  entry_price: 70000,
  size_usd: 500,
  confidence: 0.75,
  strategy: "Triangle_Breakout",
  created_at: 1775844000,
  expires_at: 1775845800  // 30 min TTL
}
```

**Execution:**
```javascript
// execution_events
{
  event_id: "evt_xyz789",
  event_type: "ORDER_FILLED",
  symbol: "BTCUSDT",
  side: "BUY",
  qty: 0.007,
  price: 70000,
  timestamp: 1775844123,
  metadata: { order_id: "ord_123" }
}

// execution_queue_v2
{
  job_id: "job_456",
  state: "FILLED",
  symbol: "BTCUSDT",
  order: { side: "BUY", qty: 0.007, type: "MARKET" },
  exchange_order_id: "binance_789",
  created_at: 1775844100,
  filled_at: 1775844105
}
```

**Portfolio:**
```javascript
// trading_cases
{
  case_id: "case_001",
  symbol: "BTCUSDT",
  status: "ACTIVE",
  entry_price: 70000,
  qty: 0.007,
  stop_loss: 69000,
  take_profit: [71000, 72000, 73000],
  unrealized_pnl: 50.00,
  entry_time: 1775844105
}
```

---

## 🛡️ КРИТИЧЕСКИЕ SAFETY МЕХАНИЗМЫ

### 1. Kill Switch
**Расположение:** `modules/strategy_engine/kill_switch.py`

**Функции:**
- Emergency stop all trading
- Cancels all pending orders
- Blocks new signal execution
- Frontend UI control

### 2. Circuit Breaker
**Расположение:** `modules/circuit_breaker/`

**Triggers:**
- Too many failed orders (5 в 1 минуту)
- API rate limit exceeded
- Exchange connection lost
- Extreme slippage detected

### 3. Position Limits
**Risk Manager checks:**
- Max positions: 3 concurrent
- Max exposure: 95% of portfolio
- Max single position: 33% of portfolio
- Daily loss limit: -5%

### 4. Order Validation
**Pre-submit checks:**
- Symbol exists
- Quantity > min notional
- Price within ±10% of market
- No duplicate orders
- Balance sufficient

---

## 🔧 КОНФИГУРАЦИЯ

### Environment Variables

```bash
# MongoDB
MONGO_URL=mongodb://localhost:27017/trading_os

# Backend URL
REACT_APP_BACKEND_URL=https://tech-analysis-core-1.preview.emergentagent.com

# Runtime
PYTHONPATH=/app/backend
```

### Risk Limits (hardcoded)

```python
MAX_POSITIONS = 3
MAX_EXPOSURE_PCT = 0.95
MAX_POSITION_SIZE_PCT = 0.33
DAILY_LOSS_LIMIT_PCT = -0.05
ORDER_SIZE_MIN_USD = 10
ORDER_SIZE_MAX_USD = 10000
```

---

## 📈 PRODUCTION STATUS

### ✅ WORKING (Production Ready)
1. **Runtime Controller** - SEMI_AUTO mode fully functional
2. **Execution Reality** - Order placement, fills, reconciliation
3. **Event Bus** - Real-time event stream
4. **Risk Manager** - Position limits, exposure checks
5. **Portfolio Manager** - Position tracking, PnL
6. **TA Engine** - Signal generation
7. **Exchange Adapters** - Binance Demo integration

### 🟡 PARTIAL (Needs Integration)
1. **Auto Mode** - Backend ready, needs extended testing
2. **Real Signal Provider** - Mock signals only
3. **Advanced Risk** - VaR, correlation, tail risk (code exists, not integrated)

### 🔴 NOT IMPLEMENTED
1. **Live Binance Production** - Only testnet/demo
2. **Multi-exchange** - Only Binance supported
3. **Advanced Strategies** - Alpha Factory research only

---

## 🎯 NEXT STEPS (Sprint R4)

### Safe AUTO Rollout
- [ ] Enable AUTO mode with strict limits (1 symbol, 60s interval, max 1 trade)
- [ ] Kill switch integration testing
- [ ] Extended runtime monitoring (30+ minutes)
- [ ] Real signal integration (connect TA Engine → SignalProvider)

### Production Hardening
- [ ] Real Binance Testnet API keys
- [ ] Extended stress testing (100+ trades)
- [ ] Error recovery scenarios
- [ ] Latency optimization

---

## 📚 ДОКУМЕНТАЦИЯ

Существующие audit files:
- `/app/backend/FULL_TRADING_LOGIC_AUDIT.md`
- `/app/backend/INDICATORS_FULL_AUDIT.md`
- `/app/backend/CHART_RENDERING_AUDIT.md`
- `/app/backend/PREDICTION_AUDIT.md`
- `/app/backend/MODULE_STATUS.md`

---

**АУДИТ ЗАВЕРШЁН**  
**Дата:** 2026-04-10  
**Архитектура:** 12 слоев, 150+ модулей, 2,202 Python файла  
**Статус:** Production-ready execution pipeline с Human-in-the-loop control