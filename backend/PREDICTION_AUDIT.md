# PREDICTION ENGINE AUDIT
## TA Engine — Prediction & Forecasting Logic Analysis

**Date:** April 1, 2026  
**Auditor:** E1 Agent  
**Scope:** Backend modules for price prediction based on TA patterns and indicators

---

## EXECUTIVE SUMMARY

### What EXISTS:
1. **Probability Engine** — Aggregates factors (structure, impulse, regime, pattern, position) into bullish/bearish probabilities
2. **Expectation Engine** — Computes expected move % and resolution time based on historical stats
3. **Scenario Engine V3** — Builds primary/alternative scenarios with triggers and invalidations
4. **Decision Engine V2** — Final decision layer combining MTF, structure, indicators, patterns
5. **Live Probability Engine** — Real-time probability updates based on price position
6. **Setup Builder** — Generates target_price from patterns (breakout level + measured move)
7. **Fractal Intelligence** — Horizon-based analysis (7, 14, 30, 60 days) with expected_return

### What is MISSING:
1. **Horizon-Based Price Forecasting** — No actual price prediction for 1D, 7D, 30D horizons
2. **ML-Based Prediction Model** — ML overlay exists but only for binary classification
3. **Price Target Calculation Engine** — Pattern targets exist, but no unified forecast chart data
4. **Forecast Path Generation** — Currently using random.uniform() — NOT real predictions
5. **Indicator-Based Prediction** — Indicators give signals, not price targets
6. **Confidence Intervals** — No upper/lower bound predictions
7. **Backtested Accuracy Metrics** — No validation of prediction accuracy

---

## DETAILED MODULE ANALYSIS

### 1. PROBABILITY ENGINE (`/modules/ta_engine/probability_engine.py`)

**Purpose:** Aggregates factors into direction probability

**What it does:**
```python
{
    "bullish": 38,      # 0-100%
    "bearish": 62,      # 0-100%
    "neutral": 0,
    "confidence": "medium",  # low/medium/high
    "dominant_bias": "bearish",
    "factors": [...]    # structure, impulse, regime, pattern, position
}
```

**Weights:**
- Structure: 25%
- Impulse: 20%
- Regime: 15%
- Pattern: 15%
- Position: 15%
- Momentum: 10%

**LIMITATION:** Gives direction probability, NOT price prediction

---

### 2. EXPECTATION ENGINE (`/modules/ta_engine/expectation_engine.py`)

**Purpose:** Expected outcomes from historical performance

**What it does:**
```python
{
    "move_pct": 4.8,           # Expected % move
    "resolution_h": 26.0,      # Expected time to target
    "confidence": "MEDIUM",    # Based on sample size
    "risk_adjusted_move": 3.2, # Accounting for winrate
    "best_case": 8.5,
    "worst_case": -2.1,
    "label": "Expected move ~4.8% in ~26h (improving recently)"
}
```

**LIMITATION:** Based on historical stats, NOT current market prediction

---

### 3. SCENARIO ENGINE V3 (`/modules/ta_engine/scenario/scenario_engine_v3.py`)

**Purpose:** Builds trading scenarios from decision + context

**What it does:**
```python
{
    "scenarios": [
        {
            "type": "primary",
            "direction": "bearish",
            "title": "Bearish continuation after relief bounce",
            "probability": 0.64,
            "trigger": "rejection below 89200",
            "invalidation": "acceptance above 90300",
            "action": "wait rejection from resistance"
        },
        ...
    ]
}
```

**LIMITATION:** Qualitative scenarios, NOT price targets

---

### 4. DECISION ENGINE V2 (`/modules/ta_engine/decision/decision_engine_v2.py`)

**Purpose:** Final trading decision

**Weights (with ta_context):**
- MTF Context: 35%
- Structure Context: 25%
- Indicators: 25%
- Pattern Evidence: 15%

**Output:**
```python
{
    "bias": "bearish",
    "confidence": 0.71,
    "context": "relief_bounce",
    "alignment": "mixed",
    "tradeability": "conditional",
    "summary": "..."
}
```

**LIMITATION:** Direction decision, NOT price forecast

---

### 5. LIVE PROBABILITY ENGINE (`/modules/ta_engine/live_probability_engine.py`)

**Purpose:** Real-time probability from price action

**Factors:**
- Position in range (support/resistance)
- Recent momentum
- Distance to breakout
- Volume spikes
- Compression detection

**Output:**
```python
{
    "breakout_up": 0.71,
    "breakdown": 0.19,
    "neutral": 0.10,
    "edge": "bullish",
    "confidence": 0.71,
    "position_in_range": 0.72
}
```

**LIMITATION:** Event probability, NOT price prediction

---

### 6. SETUP BUILDER (`/modules/ta_engine/setup/setup_builder.py`)

**Purpose:** Generates trading setups with targets

**Target calculation:**
```python
if pattern.target_price:
    targets = [pattern.target_price]
    if pattern.direction == Direction.BULLISH:
        move = pattern.target_price - pattern.breakout_level
        targets.append(pattern.breakout_level + move * 1.5)  # 150% extension
```

**Patterns with target_price:**
- Double Top/Bottom → measured move
- Head & Shoulders → neckline ± pattern_height
- Channels → channel_width projection
- Flags → pole projection

**STRENGTH:** Has real pattern-based targets
**LIMITATION:** Only works when pattern detected

---

### 7. FRACTAL INTELLIGENCE (`/modules/fractal_intelligence/`)

**Purpose:** Multi-horizon fractal analysis

**Horizons:** 7, 14, 30, 60 days

**Output:**
```python
{
    "direction": "LONG",
    "confidence": 0.72,
    "reliability": 0.68,
    "dominant_horizon": 30,
    "expected_return": 0.12,    # 12% expected return
    "phase": "ACCUMULATION",
    "strength": 0.75
}
```

**STRENGTH:** Has expected_return for horizons
**LIMITATION:** Needs integration with chart forecast

---

### 8. CURRENT FORECAST ENDPOINTS (server.py)

**Problem: Using random.uniform() — NOT REAL PREDICTIONS**

```python
# Lines 960-977 — Forecast is RANDOM
forecast_base = candles[-1]["c"] if candles else base_price
synthetic.append({
    "t": ts.strftime("%Y-%m-%d"),
    "v": round(forecast_base * (1 + random.uniform(-0.1, 0.15) * i / 30), 2)
})
```

**Endpoints affected:**
- `/api/meta-brain-v2/forecast-curve` — random curve
- `/api/forecast/{asset}` — random predictions
- `/api/fractal/v2.1/chart` — synthetic/replay/hybrid paths are random

---

## WHAT NEEDS TO BE BUILT

### 1. **Unified Prediction Engine** (`prediction_engine.py`)

Should combine:
```python
class PredictionEngine:
    def predict(self, symbol: str, horizon: str) -> Dict:
        """
        horizon: "1D" | "7D" | "30D"
        
        Returns:
            {
                "symbol": "BTC",
                "horizon": "7D",
                "current_price": 68000,
                "predicted_price": 72500,
                "direction": "BULLISH",
                "confidence": 0.71,
                "range": {
                    "low": 65000,
                    "high": 78000
                },
                "path": [...],  # Day-by-day forecast
                "factors": {
                    "pattern_contribution": 0.35,
                    "indicator_contribution": 0.25,
                    "fractal_contribution": 0.20,
                    "structure_contribution": 0.20
                }
            }
        """
```

### 2. **Path Generation Engine** (`path_generator.py`)

Should generate realistic forecast paths:
```python
def generate_forecast_path(
    current_price: float,
    target_price: float,
    horizon_days: int,
    volatility: float,
    trend_strength: float
) -> List[Dict]:
    """
    Generate day-by-day price path from current to target.
    Uses random walk with drift, respecting:
    - Historical volatility
    - Trend strength
    - Support/resistance levels
    """
```

### 3. **Target Aggregator** (`target_aggregator.py`)

Should combine all target sources:
```python
def aggregate_targets(
    pattern_targets: List[float],
    fib_levels: List[float],
    fractal_expected_return: float,
    indicator_signals: Dict
) -> Dict:
    """
    Weighted combination of all target sources.
    """
```

### 4. **Backtest Validator** (`prediction_validator.py`)

Should track prediction accuracy:
```python
def validate_predictions(
    historical_predictions: List[Dict],
    actual_outcomes: List[Dict]
) -> Dict:
    """
    Calculate:
    - Direction accuracy (% correct)
    - Price accuracy (avg error %)
    - Horizon-specific accuracy
    """
```

---

## INTEGRATION POINTS

### Frontend needs:

```typescript
// From /api/prediction/forecast
{
    symbol: "BTC",
    currentPrice: 68000,
    forecasts: {
        "1D": { price: 68500, confidence: 0.72, range: [67000, 70000] },
        "7D": { price: 72500, confidence: 0.68, range: [65000, 78000] },
        "30D": { price: 85000, confidence: 0.55, range: [60000, 95000] }
    },
    path: [
        { date: "2026-04-01", price: 68000, type: "actual" },
        { date: "2026-04-02", price: 68500, type: "forecast" },
        ...
    ],
    factors: [...],
    accuracy: {
        "1D": 0.72,
        "7D": 0.65,
        "30D": 0.58
    }
}
```

---

## RECOMMENDATION

### Priority 1: Replace Random Forecasts
- Create `PredictionEngine` that combines all existing signals
- Use pattern targets + fractal expected_return + indicator signals

### Priority 2: Path Generation
- Generate realistic paths using Monte Carlo or random walk with drift
- Respect volatility and support/resistance levels

### Priority 3: Validation System
- Track predictions vs outcomes
- Show historical accuracy on UI

### Priority 4: Chart Integration
- Connect to Fractal chart component
- Show forecast overlay with confidence bands

---

## FILES TO CREATE

1. `/app/backend/modules/ta_engine/prediction/prediction_engine.py`
2. `/app/backend/modules/ta_engine/prediction/path_generator.py`
3. `/app/backend/modules/ta_engine/prediction/target_aggregator.py`
4. `/app/backend/modules/ta_engine/prediction/prediction_validator.py`
5. `/app/backend/modules/ta_engine/prediction/__init__.py`

## ENDPOINTS TO ADD

1. `GET /api/ta/prediction/{symbol}?horizon=7D` — Full prediction
2. `GET /api/ta/prediction/{symbol}/path?horizon=30D` — Forecast path
3. `GET /api/ta/prediction/{symbol}/accuracy` — Historical accuracy
4. `POST /api/ta/prediction/validate` — Record outcome for validation

---

## SUMMARY

| Component | Status | Action Required |
|-----------|--------|-----------------|
| Probability Engine | EXISTS | Use as input |
| Expectation Engine | EXISTS | Use for historical stats |
| Scenario Engine | EXISTS | Use for scenario context |
| Decision Engine | EXISTS | Use for final bias |
| Live Probability | EXISTS | Use for real-time updates |
| Setup Builder | EXISTS | Use for pattern targets |
| Fractal Intelligence | EXISTS | Use for horizon returns |
| **Prediction Engine** | MISSING | CREATE |
| **Path Generator** | MISSING | CREATE |
| **Target Aggregator** | MISSING | CREATE |
| **Prediction Validator** | MISSING | CREATE |
| **Chart Integration** | PARTIAL | ENHANCE |
