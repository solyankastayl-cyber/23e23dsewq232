# INDICATOR AUDIT REPORT

## Обзор модулей

### 1. TA Engine (modules/ta_engine/indicators/)
Отвечает за **классические технические индикаторы**:
- Registry (38 индикаторов зарегистрировано)
- Calculations (в research_analytics/indicators.py — 19 реализованы)

### 2. Exchange Intelligence (modules/exchange_intelligence/)
Отвечает за **биржевые/деривативные индикаторы**:
- Funding Rate + Open Interest
- Long/Short Ratio
- Derivatives Pressure (Squeeze detection)
- Order Flow (Taker buy/sell)
- Volume Context
- Liquidation Zones

---

## Статус индикаторов TA Engine

### РАБОТАЮТ (Registry + Calculation):
| ID | Название | Тип |
|----|----------|-----|
| sma | Simple MA | overlay |
| ema | Exponential MA | overlay |
| vwap | VWAP | overlay |
| bollinger | Bollinger Bands | overlay |
| supertrend | Supertrend | overlay |
| ichimoku | Ichimoku Cloud | overlay |
| parabolic_sar | Parabolic SAR | overlay |
| donchian | Donchian Channels | overlay |
| keltner | Keltner Channels | overlay |
| rsi | RSI | oscillator |
| stochastic | Stochastic | oscillator |
| cci | CCI | oscillator |
| williams_r | Williams %R | oscillator |
| macd | MACD | momentum |
| momentum | Momentum | momentum |
| atr | ATR | volatility |
| adx | ADX | trend |
| obv | OBV | volume |
| volume_profile | Volume Profile | volume |

### НЕ РАБОТАЮТ (Registry есть, Calculation НЕТ):
| ID | Название | Тип | Статус |
|----|----------|-----|--------|
| vwma | Volume Weighted MA | overlay | Нужна реализация |
| hma | Hull MA | overlay | Нужна реализация |
| pivot_points | Pivot Points | overlay | Нужна реализация |
| fib_retracement | Fibonacci | overlay | Нужна реализация |
| stoch_rsi | Stochastic RSI | oscillator | Нужна реализация |
| mfi | Money Flow Index | oscillator | Нужна реализация |
| roc | Rate of Change | momentum | Нужна реализация |
| trix | TRIX | momentum | Нужна реализация |
| adl | A/D Line | volume | Нужна реализация |
| cmf | Chaikin Money Flow | volume | Нужна реализация |
| volume | Volume bars | volume | Нужна реализация |
| bb_width | BB Width | volatility | Нужна реализация |
| historical_volatility | HV | volatility | Нужна реализация |
| dmi | DMI (+DI/-DI) | trend | Нужна реализация |
| aroon | Aroon | trend | Нужна реализация |

---

## Статус Exchange Intelligence

### РАБОТАЮТ:
| Индикатор | Файл | Статус |
|-----------|------|--------|
| Funding Rate | funding_oi_engine.py | ✅ Работает (с fallback на candles) |
| Open Interest | funding_oi_engine.py | ✅ Работает (с fallback) |
| Funding State | funding_oi_engine.py | ✅ Классификация |
| OI Pressure | funding_oi_engine.py | ✅ Классификация |
| Long/Short Ratio | derivatives_pressure_engine.py | ✅ Работает |
| Leverage Index | derivatives_pressure_engine.py | ✅ Работает |
| Squeeze Probability | derivatives_pressure_engine.py | ✅ Рассчитывается |
| Perp Premium | derivatives_pressure_engine.py | ✅ Работает |
| Taker Buy Ratio | exchange_flow_engine.py | ✅ Работает |
| Aggressive Flow | exchange_flow_engine.py | ✅ Работает |
| Absorption Detection | exchange_flow_engine.py | ✅ Работает |
| Volume State | exchange_volume_engine.py | ✅ Работает |
| Liquidation Zones | exchange_liquidation_engine.py | ✅ Работает |

### ПРОБЛЕМЫ:
1. **Данные Coinbase** — реальные данные требуют подключения API
2. **Fallback логика** — все engines имеют fallback на candle-derived данные

---

## План действий

### Фаза 1: Доделать недостающие индикаторы TA Engine
1. VWMA (Volume Weighted MA)
2. HMA (Hull MA)
3. Pivot Points
4. Fibonacci Retracement
5. Stochastic RSI
6. MFI (Money Flow Index)
7. ROC (Rate of Change)
8. TRIX
9. A/D Line
10. CMF (Chaikin Money Flow)
11. Volume bars
12. BB Width
13. Historical Volatility
14. DMI (+DI/-DI)
15. Aroon

### Фаза 2: Интеграция Exchange Intelligence
1. Проверить Coinbase adapter
2. Добавить realtime данные funding/OI
3. Интегрировать в UI

### Фаза 3: Визуализация на графике
1. Pattern rendering (фигуры)
2. Structure analysis визуализация
3. Level/Zone отображение

---

## Приоритеты

**HIGH (нужно для базового анализа):**
- [ ] MFI
- [ ] Stochastic RSI
- [ ] DMI
- [ ] VWMA
- [ ] Volume bars

**MEDIUM (расширенный анализ):**
- [ ] Pivot Points
- [ ] Fibonacci
- [ ] Aroon
- [ ] ROC
- [ ] TRIX

**LOW (специализированные):**
- [ ] HMA
- [ ] A/D Line
- [ ] CMF
- [ ] BB Width
- [ ] Historical Volatility
