# PHASE 1: COVERAGE AUDIT V2

## Дата: 2026-04-02

---

# ТАБЛИЦЯ 1: PATTERN COVERAGE

## Зареєстровані паттерни в PatternFigureRegistry: 65

| pattern_name | family | detector | geometry | confidence | lifecycle | levels | hypothesis | adapter | prediction |
|--------------|--------|----------|----------|------------|-----------|--------|------------|---------|------------|
| **REVERSAL (13)** |
| double_top | reversal | ✅ detect_double_patterns | ✅ | ✅ | ❌ | ✅ | ❌ | ✅ | ✅ |
| double_bottom | reversal | ✅ | ✅ | ✅ | ❌ | ✅ | ❌ | ✅ | ✅ |
| triple_top | reversal | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| triple_bottom | reversal | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| head_shoulders | reversal | ✅ detect_head_shoulders | ✅ | ✅ | ❌ | ✅ | ❌ | ✅ | ✅ |
| inverse_head_shoulders | reversal | ✅ | ✅ | ✅ | ❌ | ✅ | ❌ | ✅ | ✅ |
| rounding_top | reversal | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| rounding_bottom | reversal | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| cup_handle | reversal | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| bump_run | reversal | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| island_reversal | reversal | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| v_top | reversal | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| v_bottom | reversal | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| **CONTINUATION (13)** |
| bull_flag | continuation | ✅ detect_flags | ✅ | ✅ | ❌ | ❌ | ❌ | ✅ | ✅ |
| bear_flag | continuation | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ | ✅ | ✅ |
| pennant | continuation | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| ascending_triangle | triangle | ✅ detect_triangles | ✅ | ✅ | ❌ | ✅ | ❌ | ✅ | ✅ |
| descending_triangle | triangle | ✅ | ✅ | ✅ | ❌ | ✅ | ❌ | ✅ | ✅ |
| symmetrical_triangle | triangle | ✅ | ✅ | ✅ | ❌ | ✅ | ❌ | ✅ | ✅ |
| expanding_triangle | triangle | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| rising_wedge | wedge | ✅ detect_wedge | ✅ | ✅ | ❌ | ❌ | ❌ | ✅ | ✅ |
| falling_wedge | wedge | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ | ✅ | ✅ |
| rectangle_bull | range | ✅ detect_range | ✅ | ✅ | ❌ | ❌ | ❌ | ✅ | ✅ |
| rectangle_bear | range | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ | ✅ | ✅ |
| broadening_formation | continuation | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| measured_move | continuation | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| high_tight_flag | continuation | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| **HARMONIC (13)** |
| gartley | harmonic | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| bat | harmonic | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| butterfly | harmonic | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| crab | harmonic | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| deep_crab | harmonic | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| shark | harmonic | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| cypher | harmonic | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| three_drives | harmonic | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| abcd | harmonic | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| wolfe_wave | harmonic | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| dragon | harmonic | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| inverse_dragon | harmonic | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| diamond_top | harmonic | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| **COMPLEX (8)** |
| diamond_bottom | complex | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| broadening_wedge | complex | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| diagonal | complex | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| ending_diagonal | complex | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| elliott_impulse | complex | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| elliott_correction | complex | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| flat_correction | complex | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| **CANDLESTICK (18)** |
| bullish_engulfing | candlestick | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| bearish_engulfing | candlestick | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| hammer | candlestick | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| inverted_hammer | candlestick | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| shooting_star | candlestick | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| hanging_man | candlestick | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| doji | candlestick | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| dragonfly_doji | candlestick | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| gravestone_doji | candlestick | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| morning_star | candlestick | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| evening_star | candlestick | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| three_white_soldiers | candlestick | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| three_black_crows | candlestick | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| inside_bar | candlestick | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| outside_bar | candlestick | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| pin_bar | candlestick | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| tweezer_top | candlestick | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| tweezer_bottom | candlestick | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |

### РЕЗЮМЕ ПАТТЕРНІВ:

| Категорія | Всього | Детектуються | % покриття |
|-----------|--------|--------------|------------|
| Reversal | 13 | 4 | 31% |
| Continuation | 13 | 10 | 77% |
| Harmonic | 13 | 0 | 0% |
| Complex | 8 | 0 | 0% |
| Candlestick | 18 | 0 | 0% |
| **TOTAL** | **65** | **14** | **22%** |

### Активні детектори (зареєстровані в @register_pattern):
1. detect_head_shoulders_unified
2. detect_triangles_unified
3. detect_channels_unified
4. detect_double_patterns_unified
5. detect_compression_unified
6. detect_flags_unified
7. detect_range_unified
8. detect_wedge_unified
9. detect_breakout_unified

### 🔴 КРИТИЧНІ ЗНАХІДКИ:
1. **78% паттернів НЕ детектуються** (51 з 65)
2. **Lifecycle НЕ передається** для жодного паттерна в prediction
3. **Harmonic паттерни повністю відсутні** (0 з 13)
4. **Candlestick паттерни повністю відсутні** (0 з 18)
5. **TAHypothesis НЕ отримує паттерни** — працює тільки на MA/RSI/MACD

---

# ТАБЛИЦЯ 2: INDICATOR COVERAGE

## Індикатори в IndicatorEngine: 37+

| indicator | computed | confluence | hypothesis | adapter | prediction | affects_direction | affects_confidence | aggregated |
|-----------|----------|------------|------------|---------|------------|-------------------|-------------------|------------|
| **TREND (10)** |
| EMA_20 | ✅ | ✅ | ✅ (MA alignment) | ❌ | ❌ | ❌ | ❌ | ❌ |
| EMA_50 | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| EMA_200 | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| SMA_20 | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| SMA_50 | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| SMA_200 | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| HMA | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| VWMA | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| Supertrend | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| Ichimoku | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| **MOMENTUM (12)** |
| RSI | ✅ | ✅ | ✅ | ✅ | ✅ partial | ✅ | ❌ | ❌ |
| MACD | ✅ | ✅ | ✅ | ✅ | ✅ partial | ✅ | ❌ | ❌ |
| Stochastic | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| StochRSI | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| Momentum | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| ROC | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| CCI | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| Williams_R | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| ADX | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| DMI | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| Aroon | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| TRIX | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| **VOLATILITY (6)** |
| ATR | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| Bollinger_Bands | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| BB_Width | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| Keltner | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| Donchian | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| Hist_Volatility | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| **VOLUME (7)** |
| OBV | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| MFI | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| VWAP | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| CMF | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| ADL | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| Volume_MA | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| **OTHER (2)** |
| Parabolic_SAR | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| Pivot_Points | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |

### РЕЗЮМЕ ІНДИКАТОРІВ:

| Стадія | Кількість | % від 37 |
|--------|-----------|----------|
| Computed | 37 | 100% |
| Confluence | 15 | 41% |
| Hypothesis | 6 | 16% |
| Adapter | 2 | 5% |
| Prediction | 2 | 5% |
| Affects direction | 2 | 5% |

### 🔴 КРИТИЧНІ ЗНАХІДКИ:
1. **95% індикаторів НЕ впливають на prediction**
2. **Тільки RSI та MACD** частково передаються в prediction
3. **ADX, ATR, OBV, MFI** — обчислюються, але НЕ використовуються
4. **Немає агрегації** — жоден індикатор не в aggregated layer
5. **Hypothesis використовує тільки MA** для trend detection

---

# ТАБЛИЦЯ 3: STRUCTURE / SEMANTIC OUTPUT

| field | computed | source | hypothesis | adapter | prediction | critical |
|-------|----------|--------|------------|---------|------------|----------|
| **REGIME** |
| regime | ✅ | structure_engine_v2 | ❌ | ✅ (state) | ✅ | ✅ |
| market_state | ✅ | market_state_engine | ❌ | ✅ | ❌ | ✅ |
| market_phase | ✅ | structure_engine_v2 | ❌ | ❌ | ❌ | ✅ |
| **TREND** |
| trend_direction | ✅ | structure_engine_v2 | ✅ | ✅ (trend) | ✅ | ✅ |
| trend_strength | ✅ | structure_engine_v2 | ✅ | ✅ | ✅ | ✅ |
| bias | ✅ | structure_engine_v2 | ❌ | ✅ | ❌ | ✅ |
| **SCORES** |
| range_score | ✅ | structure_engine_v2 | ❌ | ❌ | ❌ | ✅ |
| compression_score | ✅ | structure_engine_v2 | ❌ | ❌ | ❌ | ✅ |
| volatility_score | ✅ | market_state_engine | ❌ | ✅ (volatility) | ❌ | ✅ |
| structure_score | ✅ | structure_engine_v2 | ❌ | ❌ | ❌ | ✅ |
| **EVENTS** |
| bos_up/down | ✅ | structure_engine_v2 | ❌ | ❌ | ❌ | ✅ |
| choch_up/down | ✅ | structure_engine_v2 | ❌ | ❌ | ❌ | ✅ |
| last_event | ✅ | structure_engine_v2 | ❌ | ❌ | ❌ | ✅ |
| **COUNTS** |
| hh_count | ✅ | structure_engine_v2 | ❌ | ❌ | ❌ | ✅ |
| hl_count | ✅ | structure_engine_v2 | ❌ | ❌ | ❌ | ✅ |
| lh_count | ✅ | structure_engine_v2 | ❌ | ❌ | ❌ | ✅ |
| ll_count | ✅ | structure_engine_v2 | ❌ | ❌ | ❌ | ✅ |
| **QUALITY** |
| setup_quality | ✅ | hypothesis_builder | ✅ | ❌ | ❌ | ✅ |
| breakout_quality | ❌ | - | ❌ | ❌ | ❌ | ✅ |
| entry_quality | ✅ | hypothesis_builder | ✅ | ❌ | ❌ | ✅ |
| **CONFLUENCE** |
| bullish_confluence | ❌ | - | ❌ | ❌ | ❌ | ✅ |
| bearish_confluence | ❌ | - | ❌ | ❌ | ❌ | ✅ |
| conflict_score | ❌ | - | ❌ | ❌ | ❌ | ✅ |
| agreement_score | ❌ | - | ❌ | ❌ | ❌ | ✅ |
| **LEVELS** |
| active_supports | ✅ | structure_engine_v2 | ❌ | ❌ | ❌ | ❌ |
| active_resistances | ✅ | structure_engine_v2 | ❌ | ❌ | ❌ | ❌ |

### РЕЗЮМЕ СТРУКТУРИ:

| Тип даних | Computed | → Prediction | % покриття |
|-----------|----------|--------------|------------|
| Regime fields | 3 | 1 | 33% |
| Trend fields | 3 | 2 | 67% |
| Score fields | 4 | 0 | 0% |
| Event fields | 4 | 0 | 0% |
| Count fields | 4 | 0 | 0% |
| Quality fields | 3 | 0 | 0% |
| Confluence | 4 | 0 | 0% |
| **TOTAL** | **25** | **3** | **12%** |

### 🔴 КРИТИЧНІ ЗНАХІДКИ:
1. **88% structure outputs НЕ доходять до prediction**
2. **range_score, compression_score** — обчислюються, але НЕ передаються
3. **BOS/CHOCH events** — обчислюються, але НЕ передаються
4. **HH/HL/LH/LL counts** — обчислюються, але НЕ передаються
5. **Confluence/Conflict** — взагалі НЕ обчислюються
6. **Setup quality** — є в hypothesis, але НЕ в prediction

---

# ЗАГАЛЬНІ ВИСНОВКИ

## ГОЛОВНИЙ РОЗРИВ:

```
TA Engine виробляє ~150+ сигналів
        ↓
Adapter передає ~10 сигналів
        ↓
Prediction використовує ~5 сигналів
```

## ВТРАТИ ПО ШЛЯХУ:

| Layer | Signals IN | Signals OUT | Loss |
|-------|------------|-------------|------|
| TA Engine | 150+ | 150+ | 0% |
| TA Summary | 150+ | ~30 | 80% |
| Adapter | ~30 | ~10 | 67% |
| Prediction Input | ~10 | ~5 | 50% |
| **TOTAL LOSS** | **150+** | **~5** | **~97%** |

## ЩО PREDICTION РЕАЛЬНО ОТРИМУЄ:

```python
# З patterns:
- pattern.type       ✅
- pattern.direction  ✅  
- pattern.confidence ✅
- pattern.breakout_level ✅ (частково)

# З structure:
- state (regime)     ✅
- trend              ✅
- trend_strength     ✅

# З indicators:
- momentum           ✅ (derived, не raw)
- RSI                ✅ (partial)
- MACD               ✅ (partial)
```

## ЩО PREDICTION НЕ ОТРИМУЄ (але повинен):

```python
# Patterns:
- lifecycle (forming/confirmed/invalid)
- bounds (upper/lower lines)
- maturity
- setup_quality
- touch_count

# Structure:
- range_score
- compression_score
- market_phase
- bos/choch events
- hh_hl_lh_ll counts
- volatility_score

# Indicators:
- 35 індикаторів (крім RSI/MACD)
- trend_aggregate
- momentum_aggregate
- volatility_aggregate
- volume_aggregate

# Quality:
- setup_quality
- entry_quality
- conflict_score
- confluence_score
```

---

# ROADMAP ФІКСІВ

## Phase 2.1: Expand Adapter (HIGH PRIORITY)

Передавати в prediction:
1. range_score
2. compression_score
3. market_phase
4. hh_hl_lh_ll counts
5. last_event (bos/choch)
6. pattern.lifecycle
7. pattern.bounds

## Phase 2.2: Add Indicator Aggregates

Створити:
1. trend_aggregate (MA, Supertrend, Ichimoku)
2. momentum_aggregate (RSI, MACD, Stoch, CCI)
3. volatility_aggregate (ATR, BB, Keltner)
4. volume_aggregate (OBV, MFI, CMF, ADL)

## Phase 2.3: Add Quality Signals

Передавати:
1. setup_quality
2. entry_quality
3. conflict_score
4. confluence_score

## Phase 3: Activate Missing Detectors

Реалізувати:
1. Candlestick patterns (18)
2. Harmonic patterns (13, optional)
3. Triple top/bottom

---

*Аудит покриття завершено: 2026-04-02*
