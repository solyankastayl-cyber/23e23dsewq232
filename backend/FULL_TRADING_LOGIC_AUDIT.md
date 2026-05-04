# ПОВНИЙ АУДИТ ТОРГОВОЇ ЛОГІКИ TA ENGINE

## Дата: 2026-04-02

---

## АРХІТЕКТУРА СИСТЕМИ

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         TRADING INTELLIGENCE                            │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌───────────────────┐  ┌───────────────────┐  ┌───────────────────┐   │
│  │   TA INTELLIGENCE │  │FRACTAL INTELLIGENCE│  │EXCHANGE INTELLIGENCE│ │
│  │                   │  │                   │  │                   │   │
│  │ • Indicators      │  │ • BTC Fractal     │  │ • Funding/OI      │   │
│  │ • Patterns        │  │ • SPX Fractal     │  │ • Derivatives     │   │
│  │ • Structure       │  │ • DXY Fractal     │  │ • Liquidations    │   │
│  │ • Levels          │  │ • Phase Detection │  │ • Exchange Flow   │   │
│  │ • Regime          │  │ • Reliability     │  │ • Volume Context  │   │
│  └─────────┬─────────┘  └─────────┬─────────┘  └─────────┬─────────┘   │
│            │                      │                      │             │
│            └──────────────────────┼──────────────────────┘             │
│                                   │                                    │
│                    ┌──────────────▼──────────────┐                     │
│                    │     TRADING DECISION        │                     │
│                    │        ENGINE               │                     │
│                    │                             │                     │
│                    │  TAHypothesis + Exchange +  │                     │
│                    │  MarketState → Decision     │                     │
│                    └──────────────┬──────────────┘                     │
│                                   │                                    │
│                    ┌──────────────▼──────────────┐                     │
│                    │    PREDICTION ENGINE V3     │                     │
│                    │                             │                     │
│                    │  • Direction                │                     │
│                    │  • Target Price             │                     │
│                    │  • Confidence               │                     │
│                    │  • Path + Scenarios         │                     │
│                    └─────────────────────────────┘                     │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## БЛОК 1: TA INTELLIGENCE

### Розташування: `/app/backend/modules/ta_engine/`

### Кількість коду: ~70,000+ рядків

### Структура:

```
ta_engine/
├── per_tf_builder.py (2390 lines) - CORE: Будує повний TA для timeframe
├── setup/
│   ├── indicator_engine.py (1793 lines) - 30+ індикаторів
│   ├── structure_engine_v2.py (636 lines) - Regime/Bias detection
│   ├── pattern_engine_v3.py (574 lines) - Pattern detection
│   ├── pattern_detectors_unified.py - Уніфіковані детектори
│   ├── level_engine.py - Support/Resistance
│   └── pattern_*.py - Різні pattern engines
├── indicators/
│   ├── confluence_engine.py - Confluence analysis
│   ├── indicator_registry.py - Registry of indicators
│   └── indicator_insights.py - Insights generation
├── hypothesis/
│   ├── ta_hypothesis_builder.py (714 lines) - TA→TAHypothesis
│   ├── ta_hypothesis_types.py - Types
│   └── ta_hypothesis_rules.py - Thresholds
├── pattern/ - Pattern geometry
├── structure/ - Structure visualization
├── fibonacci/ - Fibonacci levels
├── liquidity/ - Liquidity zones
├── displacement/ - Displacement detection
├── poi/ - Points of Interest
└── mtf_engine.py - Multi-timeframe analysis
```

### ІНДИКАТОРИ (30+):

| Категорія | Індикатори |
|-----------|------------|
| **Trend** | EMA (20/50/200), SMA, HMA, VWMA, Supertrend, Ichimoku |
| **Momentum** | RSI, MACD, Stochastic, StochRSI, Momentum, ROC, CCI, Williams %R |
| **Volatility** | ATR, Bollinger Bands, BB Width, Keltner, Donchian, Historical Vol |
| **Volume** | OBV, VWAP, MFI, CMF, ADL |
| **Structure** | Parabolic SAR, TRIX |

### ПАТЕРНИ:

| Тип | Патерни |
|-----|---------|
| **Triangles** | Ascending, Descending, Symmetrical |
| **Channels** | Ascending, Descending, Horizontal |
| **Reversal** | Double Top/Bottom, Head & Shoulders, Inv H&S |
| **Continuation** | Flags, Pennants, Wedges |

### STRUCTURE STATE:

```python
StructureState:
  bias: bullish / bearish / neutral
  regime: trend_up / trend_down / range / compression / expansion
  market_phase: markup / markdown / range / compression
  last_event: bos_up / bos_down / choch_up / choch_down
  
  # Swing counts
  hh_count, hl_count, lh_count, ll_count
  
  # Scores
  trend_strength, compression_score, range_score
```

### TAHypothesis OUTPUT:

```python
TAHypothesis:
  direction: LONG / SHORT / NEUTRAL
  conviction: 0.0 - 1.0
  drivers: [trend_score, momentum_score, structure_score]
  regime: TRENDING / RANGING / VOLATILE
  setup_type: BREAKOUT / PULLBACK / REVERSAL / RANGE_BOUND
  setup_quality: 0.0 - 1.0
```

---

## БЛОК 2: FRACTAL INTELLIGENCE

### Розташування: `/app/backend/modules/fractal_intelligence/`

### Призначення:
Аналізує кореляції з глобальними активами (BTC, SPX, DXY) для контексту.

### Компоненти:

| Файл | Функція |
|------|---------|
| `fractal_context_engine.py` | Core engine - strength, state |
| `btc_fractal_adapter.py` | BTC correlation |
| `spx_fractal_adapter.py` | S&P 500 correlation |
| `dxy_fractal_adapter.py` | Dollar Index correlation |
| `fractal_context_client.py` | Data fetching |
| `fractal_context_adapter.py` | Adaptation layer |

### Формула:

```python
fractal_strength = 0.45 * confidence + 0.35 * reliability + 0.20 * phase_confidence
```

### Context States:

| State | Умова |
|-------|-------|
| **BLOCKED** | governance HALT/FROZEN_ONLY OR reliability < 0.20 |
| **SUPPORTIVE** | direction != HOLD, confidence >= 0.60, reliability >= 0.60 |
| **CONFLICTED** | direction != HOLD, confidence >= 0.55, reliability < 0.45 |
| **NEUTRAL** | all other |

### Output:

```python
FractalContext:
  fractal_strength: float
  context_state: BLOCKED/SUPPORTIVE/CONFLICTED/NEUTRAL
  horizon_bias: HorizonBias
  health_status: FractalHealthStatus
  reason: str
```

---

## БЛОК 3: EXCHANGE INTELLIGENCE

### Розташування: `/app/backend/modules/exchange_intelligence/`

### Компоненти:

| Engine | Функція |
|--------|---------|
| `funding_oi_engine.py` | Funding rate + Open Interest |
| `derivatives_pressure_engine.py` | Derivatives analysis |
| `exchange_liquidation_engine.py` | Liquidation data |
| `exchange_flow_engine.py` | Exchange inflow/outflow |
| `exchange_volume_engine.py` | Volume context |
| `exchange_context_aggregator.py` | **MAIN**: combines all |

### Weights:

```python
W_FUNDING = 0.20
W_DERIVATIVES = 0.20
W_LIQUIDATION = 0.15
W_FLOW = 0.30
W_VOLUME = 0.15
```

### Output:

```python
ExchangeContext:
  exchange_bias: BULLISH / BEARISH / NEUTRAL
  bias_score: -1.0 to 1.0
  funding_signal: FundingOISignal
  derivatives_signal: DerivativesPressureSignal
  liquidation_signal: LiquidationSignal
  flow_signal: ExchangeFlowSignal
  volume_signal: VolumeContextSignal
```

---

## БЛОК 4: TRADING DECISION ENGINE

### Розташування: `/app/backend/modules/trading_decision/`

### Архітектура:

```
TAHypothesis ──────────┐
                        │
ExchangeContext ────────┼── Decision Engine ── TradingDecision
                        │
MarketStateMatrix ─────┘
```

### Підмодулі:

| Модуль | Функція |
|--------|---------|
| `decision_layer/` | Core decision logic |
| `execution_mode/` | NORMAL/CONSERVATIVE/AGGRESSIVE |
| `market_state/` | Market state analysis |
| `position_sizing/` | Position sizing |

### Decision Output:

```python
TradingDecision:
  action: ALLOW / ALLOW_REDUCED / ALLOW_AGGRESSIVE / BLOCK / WAIT / REVERSE_CANDIDATE
  execution_mode: NORMAL / CONSERVATIVE / AGGRESSIVE
  direction: LONG / SHORT / NEUTRAL
  confidence: 0.0 - 1.0
  position_multiplier: 0.0 - 2.0
  rules_triggered: List[DecisionRule]
```

---

## БЛОК 5: PREDICTION ENGINE V3

### Розташування: `/app/backend/modules/prediction/`

### Архітектура:

```
TA Input → Regime Detector → Model Router → Specialized Model → Prediction
                                              │
                                              ├── trend_model.py
                                              ├── range_model.py
                                              ├── compression_model.py
                                              └── high_vol_model.py
```

### Компоненти:

| Файл | Функція |
|------|---------|
| `prediction_engine_v3.py` | Core with drift/correction |
| `regime_detector.py` | trend/range/compression/high_vol |
| `regime_router.py` | Routes to specialized model |
| `direction.py` | Direction detection |
| `confidence.py` | Confidence calculation |
| `stability.py` | Stability scoring |
| `filter.py` | Bad setup filtering |
| `calibration_engine.py` | Real-time calibration |
| `model_health.py` | Model health monitoring |
| `backtest_*.py` | P6 Historical Backtest |

### Prediction Output:

```python
PredictionOutput:
  direction:
    label: bullish/bearish/neutral
    strength: 0.0 - 1.0
  target:
    start_price: float
    target_price: float
    expected_return: float
  confidence:
    value: 0.0 - 1.0
    drivers: List[str]
  stability: float
  scenarios: List[Scenario]
  path: List[PathPoint]
  regime: str
  model: str
```

---

## ПОТОЧНИЙ СТАН BACKTEST (P6)

### Метрики (1063 predictions, BTC+ETH+SOL, 4H, 180 days):

| Метрика | Значення |
|---------|----------|
| Total | 1063 |
| **Accuracy** | **34.5%** |
| Partial | 4.4% |
| Wrong | 61.0% |
| Wrong Early | 57.8% |

### По режимах:

| Regime | Count | Accuracy |
|--------|-------|----------|
| Trend | 998 (94%) | 34.6% |
| Compression | 22 (2%) | 4.5% |
| High Volatility | 43 (4%) | 48.8% |

### Direction Bias:

| Direction | Count | Accuracy |
|-----------|-------|----------|
| Bullish | 334 (31%) | 20.4% |
| Bearish | 729 (69%) | 41.0% |

---

## ПРОБЛЕМИ ТА РЕКОМЕНДАЦІЇ

### 🔴 КРИТИЧНІ

1. **Bearish Bias 69%**
   - Система надто часто предбачає падіння
   - Bullish accuracy лише 20.4% vs Bearish 41.0%
   - Потрібно балансувати direction detection

2. **Wrong Early Rate 57.8%**
   - Ціна йде проти prediction на >3% занадто швидко
   - Invalidation threshold 3% занадто низький
   - Рекомендація: збільшити до 5%

3. **Compression Model 4.5% accuracy**
   - Модель майже не працює
   - Потрібна переробка логіки

### 🟡 СЕРЕДНІ

4. **Range regime не активується**
   - Range model не викликається в backtest
   - Потрібно перевірити range_score threshold

5. **Trend_strength використовується неправильно**
   - Часто значення 0 або дуже низькі
   - Momentum не передається в indicators правильно

6. **Target занадто агресивний**
   - Average error 6.3%
   - Targets часто 8-15% vs реальний рух 3-5%

### 🟢 НИЗЬКІ

7. **High Volatility model працює добре (48.8%)**
   - Можна використати як reference

8. **Fractal Intelligence не інтегрований в prediction**
   - Є код, але не використовується

9. **Exchange Intelligence не інтегрований в prediction**
   - Є код, але не використовується

---

## РЕКОМЕНДОВАНІ ЗМІНИ

### Phase 1: Quick Wins

1. Збільшити invalidation threshold до 5%
2. Зменшити target multiplier до 0.7x
3. Покращити momentum передачу в backtest adapter

### Phase 2: Model Improvement

4. Переробити compression_model
5. Активувати range_model
6. Балансувати direction detection

### Phase 3: Integration

7. Інтегрувати Fractal Intelligence в prediction
8. Інтегрувати Exchange Intelligence в prediction
9. P7: Calibration from Backtest

---

## СТАТИСТИКА КОДУ

| Модуль | Рядків |
|--------|--------|
| ta_engine/ | ~70,000 |
| prediction/ | ~3,500 |
| fractal_intelligence/ | ~1,500 |
| exchange_intelligence/ | ~2,500 |
| trading_decision/ | ~3,000 |
| **TOTAL** | **~80,000+** |

---

*Аудит завершено: 2026-04-02*
