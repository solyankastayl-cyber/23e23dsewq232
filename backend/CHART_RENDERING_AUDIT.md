# ГЛУБОКИЙ АУДИТ: ГРАФИК И TA RENDERING

## ОБЩАЯ АРХИТЕКТУРА

```
┌─────────────────────────────────────────────────────────────────────────┐
│                              BACKEND                                      │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                           │
│  ┌─────────────┐    ┌──────────────────┐    ┌───────────────────────┐   │
│  │ Coinbase    │───▶│ per_tf_builder   │───▶│ render_plan_engine_v2 │   │
│  │ Data        │    │ (MAIN BRAIN)     │    │ (VISUAL BRAIN)        │   │
│  └─────────────┘    └──────────────────┘    └───────────────────────┘   │
│                              │                         │                  │
│                              ▼                         ▼                  │
│  ┌─────────────────────────────────────────────────────────────────────┐ │
│  │                    API RESPONSE (JSON)                               │ │
│  │  - candles[]                                                         │ │
│  │  - structure_context, liquidity, displacement, poi, fib             │ │
│  │  - primary_pattern, indicator_insights, decision                     │ │
│  │  - render_plan { structure, patterns, levels, liquidity, execution } │ │
│  └─────────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    │ HTTP /api/ta-engine/mtf/{symbol}
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                              FRONTEND                                     │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                           │
│  ┌─────────────────┐    ┌────────────────────────────────────────────┐  │
│  │ ResearchViewNew │───▶│ ResearchChart.jsx (1443 lines)             │  │
│  │ (orchestrator)  │    │ lightweight-charts library                  │  │
│  └─────────────────┘    └────────────────────────────────────────────┘  │
│                                       │                                   │
│                                       ▼                                   │
│  ┌─────────────────────────────────────────────────────────────────────┐ │
│  │                      RENDERING LAYERS                                │ │
│  │  1. Candlestick series (OHLC)                                        │ │
│  │  2. Structure legs (HH/HL/LH/LL lines)                               │ │
│  │  3. BOS/CHOCH lines                                                  │ │
│  │  4. Support/Resistance levels                                        │ │
│  │  5. Pattern geometry (lines, points)                                 │ │
│  │  6. Fibonacci levels                                                 │ │
│  │  7. Liquidity zones (BSL/SSL)                                        │ │
│  │  8. POI zones                                                        │ │
│  │  9. Indicator overlays (EMA, BB, VWAP)                               │ │
│  │  10. Indicator panes (RSI, MACD)                                     │ │
│  └─────────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 1. BACKEND — КЛЮЧЕВЫЕ ФАЙЛЫ

### 1.1 per_tf_builder.py — ГЛАВНЫЙ МОЗГ
**Путь:** `/app/backend/modules/ta_engine/per_tf_builder.py`
**Строк:** 667

**Что делает:**
- Строит ПОЛНЫЙ TA payload для ОДНОГО таймфрейма
- Вызывает 11 шагов анализа последовательно
- Результат идёт на фронтенд как JSON

**11 шагов:**
```
1. Structure Analysis (find_pivots, structure_engine_v2, structure_context_engine)
2. Liquidity & Displacement
3. CHOCH Validation
4. POI & Fibonacci
5. Pattern Detection (run_all_detectors, filter_by_structure, pattern_selector)
6. Indicators (indicator_engine, indicator_visualization, indicator_insights)
7. Decision Engine
8. Unified Setup & Trade Setup
9. Execution Layer
10. Chain Map (for highlighting)
11. Render Plan V2
```

**OUTPUT STRUCTURE:**
```python
{
    "timeframe": "4H",
    "symbol": "BTCUSDT",
    "candles": [...],                    # OHLCV data for chart
    "current_price": 84500,
    
    # Structure
    "structure_context": {
        "trend": "downtrend",
        "regime": "range",
        "bias": "bearish",
        "swings": [...],
        "last_choch": {...},
        "last_bos": {...}
    },
    
    # Smart Money
    "liquidity": {
        "pools": [...],
        "sweeps": [...],
        "bsl": 85000,
        "ssl": 83000
    },
    "displacement": { "events": [...], "detected": bool },
    "choch_validation": { "is_valid": bool, "direction": "...", ... },
    "poi": { "zones": [...] },
    "fib": { "fib_levels_for_chart": [...], "fib_set": {...} },
    
    # Patterns
    "primary_pattern": {
        "type": "double_bottom",
        "direction_bias": "bullish",
        "breakout_level": 85000,
        "invalidation_level": 82000,
        "points": [...],
        "lines": [...]              # Geometry for chart
    },
    
    # Indicators (for chart rendering)
    "indicators": {
        "overlays": [               # EMA, BB, VWAP
            { "id": "ema_20", "data": [...] }
        ],
        "panes": [                  # RSI, MACD
            { "id": "rsi", "data": [...], "value": 37 }
        ]
    },
    "indicator_insights": {
        "rsi": { "value": 37, "state": "near_oversold", ... },
        "macd": { "zone": "below_zero", "momentum": "fading", ... }
    },
    
    # Decision
    "decision": {
        "technical_bias": "bearish",
        "confidence": 0.68,
        "regime": "range",
        "tradeability": "low",
        "summary": "..."
    },
    
    # RENDER PLAN V2 — key for chart
    "render_plan": {
        "structure": { "swings": [...], "choch": {...}, "bos": {...} },
        "levels": [...],
        "patterns": { "primary": {...}, "has_figure": bool },
        "liquidity": { "bsl": [...], "ssl": [...], "sweeps": [...] },
        "execution": { "status": "no_trade", ... },
        "visual_priority": {...}
    }
}
```

---

### 1.2 render_plan_engine_v2.py — ВИЗУАЛЬНЫЙ МОЗГ
**Путь:** `/app/backend/modules/ta_engine/render_plan/render_plan_engine_v2.py`
**Строк:** 964

**Что делает:**
- Фильтрует и приоритизирует данные для ЧИСТОЙ визуализации
- 6 изолированных слоёв
- Определяет render_mode: figure_mode, range_mode, structure_mode

**6 СЛОЁВ:**
```
A. Market State    — trend, channel, volatility (CONTEXT, не pattern)
B. Structure       — swings (MAX 4!), CHOCH (MAX 1), BOS (MAX 1)
C. Indicators      — smart selection: trend→EMA+RSI, range→BB+RSI
D. Pattern Figures — ТОЛЬКО реальные patterns (НЕ channels!)
E. Liquidity       — MAX 2 BSL, MAX 2 SSL, 1 sweep
F. Execution       — ВСЕГДА видим: valid/waiting/no_trade
```

**LIMITS:**
```python
MAX_CHART_SWINGS = 4        # Не 6!
MAX_CHART_LEVELS = 5        # Для читаемости
MAX_POI_ZONES = 1
MAX_LIQUIDITY_ELEMENTS = 2
MAX_INDICATOR_OVERLAYS = 2
MAX_INDICATOR_PANES = 1
```

---

### 1.3 ta_routes.py — API ENDPOINTS
**Путь:** `/app/backend/modules/ta_engine/ta_routes.py`

**Ключевые endpoints:**
```
GET /api/ta-engine/mtf/{symbol}           — MTF analysis (main endpoint!)
GET /api/ta-engine/mtf/{symbol}/{tf}      — Single TF
GET /api/ta-engine/render-plan-v2/{symbol} — Render plan only
GET /api/ta-engine/registry/patterns       — Pattern registry
GET /api/ta-engine/registry/indicators     — Indicator registry
```

**MTF Response содержит:**
- `tf_map` — данные для каждого TF
- `mtf_context` — alignment, tradeability
- `default_tf` — рекомендуемый TF

---

## 2. FRONTEND — КЛЮЧЕВЫЕ ФАЙЛЫ

### 2.1 ResearchChart.jsx — MAIN CHART COMPONENT
**Путь:** `/app/frontend/src/modules/cockpit/components/ResearchChart.jsx`
**Строк:** 1443

**Props:**
```javascript
{
  candles,          // OHLCV data
  levels,           // Support/Resistance
  chartStructure,   // { legs: [...], pivots: [...] }
  pattern,          // Active pattern geometry
  patternV2,        // Pattern from render_plan
  baseLayer,        // Channels, trendlines
  liquidity,        // BSL/SSL/sweeps
  poi,              // POI zones
  fibonacci,        // Fib levels
  indicators,       // { overlays: [...], panes: [...] }
  renderPlan,       // render_plan from backend
  showBaseLayer,    // Toggle
  showPatternLayer, // Toggle
  showTALayer,      // Toggle
  showSetupLayer,   // Toggle
}
```

**RENDERING ORDER (в useEffect):**
```
1. Chart creation (lightweight-charts)
2. Candlestick series (main)
3. Volume histogram (bottom)
4. STRUCTURE from render_plan:
   - structure.swings → markers
   - structure legs → line series (NOW 1.5px, 50% opacity)
   - structure.bos / structure.choch → dashed lines
5. LEVELS → horizontal lines
6. PATTERN geometry:
   - pattern.lines → line series
   - pattern.points → markers
   - pattern.breakout_level → dashed line
7. FIBONACCI levels → horizontal lines
8. BASE LAYER (channels, trendlines)
9. LIQUIDITY (BSL/SSL zones, sweeps)
10. POI zones → area series
11. INDICATOR overlays (EMA, BB, VWAP) → line series
12. INDICATOR panes (RSI, MACD) — IF ACTIVE
```

**COLORS (текущие после P2):**
```javascript
const STRUCT_COLORS = {
  bullishLeg: 'rgba(34, 197, 94, 0.5)',   // 50% opacity
  bearishLeg: 'rgba(239, 68, 68, 0.5)',
  HH: 'rgba(22, 163, 74, 0.7)',
  HL: 'rgba(74, 222, 128, 0.7)',
  LH: 'rgba(249, 115, 22, 0.7)',
  LL: 'rgba(220, 38, 38, 0.7)',
  BOS_bull: 'rgba(34, 197, 94, 0.6)',
  BOS_bear: 'rgba(239, 68, 68, 0.6)',
  CHOCH_bull: 'rgba(59, 130, 246, 0.6)',
  CHOCH_bear: 'rgba(249, 115, 22, 0.6)',
};
```

---

### 2.2 ResearchViewNew.jsx — ORCHESTRATOR
**Путь:** `/app/frontend/src/modules/cockpit/views/ResearchViewNew.jsx`
**Строк:** 2072

**Data Flow:**
```
1. useEffect → fetch /api/ta-engine/mtf/{symbol}
2. Parse response → setupData = tf_map[selectedTF]
3. Extract from setupData:
   - candles
   - levels
   - chartStructure (from structure_context.legs + pivots)
   - pattern (primary_pattern)
   - liquidity
   - poi
   - fibonacci (fib)
   - indicators
   - renderPlan (render_plan)
4. Pass all to <ResearchChart />
5. Render surrounding UI:
   - IndicatorControlBar (RSI/MACD toggles)
   - StoryLine
   - Market Context / Technical Setup
   - Analysis blocks
```

**STATE:**
```javascript
const [activeIndicators, setActiveIndicators] = useState({ rsi: false, macd: false });
const [viewMode, setViewMode] = useState('auto');
const [showBaseLayer, setShowBaseLayer] = useState(true);
const [showPatternLayer, setShowPatternLayer] = useState(true);
const [showTALayer, setShowTALayer] = useState(true);
const [showSetupLayer, setShowSetupLayer] = useState(true);
```

---

## 3. СВЯЗКА BACKEND ↔ FRONTEND

### 3.1 API Call
```javascript
// ResearchViewNew.jsx
const response = await researchService.getMTFAnalysis(symbol, timeframes);
// → GET /api/ta-engine/mtf/BTC?timeframes=1D,4H,1H
```

### 3.2 Response Mapping
```javascript
// Backend sends:
{
  "tf_map": {
    "4H": { candles, structure_context, primary_pattern, render_plan, ... }
  }
}

// Frontend receives and extracts:
const setupData = response.tf_map[selectedTF];
const candles = setupData.candles;
const chartStructure = buildChartStructure(setupData.structure_context);
const pattern = setupData.primary_pattern;
const renderPlan = setupData.render_plan;
```

### 3.3 Chart Structure Building
```javascript
// Frontend transforms structure_context to chart-renderable format
function buildChartStructure(structureContext) {
  const swings = structureContext?.swings || [];
  const legs = [];
  
  // Build legs from consecutive swings
  for (let i = 1; i < swings.length; i++) {
    const prev = swings[i-1];
    const curr = swings[i];
    legs.push({
      from: { time: prev.time, price: prev.price },
      to: { time: curr.time, price: curr.price },
      type: curr.type === 'HH' || curr.type === 'HL' ? 'bullish_leg' : 'bearish_leg'
    });
  }
  
  return { swings, legs };
}
```

---

## 4. ПРОБЛЕМЫ И GAPS

### 4.1 Backend Issues

**❌ Pattern lines не всегда правильно форматируются:**
```python
# per_tf_builder.py вызывает pattern.to_dict()
# Но pattern.lines может быть пустым если детектор не заполнил
```

**❌ Render plan v2 не всегда используется:**
```python
# ResearchChart.jsx проверяет renderPlan?.structure
# Но если render_plan = None (ошибка), fallback на chartStructure
```

**❌ FVG, Order Block, Liquidity Zones — логика есть, визуализация incomplete:**
```python
# liquidity_engine возвращает pools[], sweeps[]
# Но для FVG/OB нет dedicated rendering
```

### 4.2 Frontend Issues

**❌ Тяжёлый useEffect (1443 строк):**
```javascript
// ResearchChart.jsx — весь rendering в одном useEffect
// Очень сложно поддерживать
```

**❌ Дублирование логики:**
```javascript
// chartStructure vs renderPlan.structure
// Оба содержат swings, но разный формат
// Frontend должен выбирать один источник
```

**❌ Markers для swings не всегда рендерятся:**
```javascript
// Код есть, но markers часто не видны на графике
// Нужна проверка: правильный ли формат time?
```

### 4.3 Data Inconsistency

**❌ time format:**
```
Backend: время в секундах (Unix timestamp)
Frontend: lightweight-charts ожидает секунды
Проблема: иногда приходит в миллисекундах (> 1e12)
Решение: parseTime = (t) => t > 1e12 ? Math.floor(t / 1000) : t
```

**❌ Pattern points:**
```
Backend: pattern.points = [{ index, value, time }, ...]
Frontend: ожидает { time, value }
Нужна нормализация
```

---

## 5. РЕКОМЕНДАЦИИ

### 5.1 Backend

1. **Унифицировать формат времени:**
   - Всегда отправлять в СЕКУНДАХ
   - Добавить валидацию перед отправкой

2. **Гарантировать render_plan:**
   - Обрабатывать все ошибки
   - Всегда возвращать валидный объект (хотя бы пустой)

3. **FVG/OB rendering data:**
   - Добавить `fvg_zones` и `order_blocks` в render_plan
   - Формат: `{ time_start, time_end, price_top, price_bottom, type }`

### 5.2 Frontend

1. **Один источник истины:**
   - Использовать ТОЛЬКО `renderPlan` для всего
   - Убрать fallback на `chartStructure`

2. **Refactor ResearchChart:**
   - Разбить на подкомпоненты:
     - CandlestickLayer
     - StructureLayer
     - PatternLayer
     - LiquidityLayer
     - IndicatorLayer

3. **Нормализация данных:**
   - Создать `normalizeRenderPlan(raw)` функцию
   - Гарантировать формат перед рендерингом

### 5.3 Тестирование

1. **Backend unit tests:**
   - `test_render_plan_v2.py` — проверить все слои
   - `test_pattern_geometry.py` — проверить lines/points

2. **Frontend E2E:**
   - Проверить что все элементы рендерятся на графике
   - Проверить markers, lines, zones видимы

---

## 6. FILE MAP

```
BACKEND:
/app/backend/
├── modules/ta_engine/
│   ├── per_tf_builder.py         ★ MAIN BRAIN
│   ├── ta_routes.py              ★ API ENDPOINTS
│   ├── render_plan/
│   │   ├── render_plan_engine.py    (v1)
│   │   └── render_plan_engine_v2.py ★ VISUAL BRAIN
│   ├── structure/
│   │   ├── structure_visualization_builder.py
│   │   └── choch_validation_engine.py
│   ├── patterns/
│   │   ├── pattern_engine.py
│   │   ├── pattern_registry.py
│   │   └── validators/
│   ├── liquidity/
│   │   └── liquidity_engine.py
│   ├── indicators/
│   │   ├── indicator_registry.py
│   │   ├── indicator_visualization.py
│   │   └── indicator_insights.py
│   └── setup/
│       ├── pattern_validator_v2.py
│       ├── structure_engine_v2.py
│       └── unified_setup_engine.py

FRONTEND:
/app/frontend/src/
├── modules/cockpit/
│   ├── views/
│   │   └── ResearchViewNew.jsx    ★ ORCHESTRATOR
│   └── components/
│       ├── ResearchChart.jsx      ★ CHART RENDERING
│       ├── IndicatorControlBar.jsx (P2 new)
│       └── StoryLine.jsx          (P2 new)
├── services/
│   └── researchService.js         ★ API CALLS
└── store/
    └── marketStore.js             ★ STATE MANAGEMENT
```

---

## 7. ИТОГ

**РАБОТАЕТ:**
- ✅ Candles rendering
- ✅ Structure legs (HH/HL/LH/LL)
- ✅ BOS/CHOCH lines
- ✅ Support/Resistance levels
- ✅ Pattern basic geometry
- ✅ Fibonacci levels
- ✅ Indicator overlays (EMA, BB)
- ✅ Indicator panes (RSI, MACD)

**ЧАСТИЧНО РАБОТАЕТ:**
- ⚠️ Pattern complex geometry (lines array)
- ⚠️ Liquidity zones (BSL/SSL)
- ⚠️ POI zones

**НЕ РАБОТАЕТ / НЕ ВИЗУАЛИЗИРУЕТСЯ:**
- ❌ FVG (Fair Value Gap)
- ❌ Order Blocks
- ❌ Detailed Liquidity Zones
- ❌ Sweep animations/highlights
