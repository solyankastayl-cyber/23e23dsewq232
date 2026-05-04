# DEEP AUDIT: Exchange Intelligence, Reflexivity (Sentiment), Fractal Intelligence

## Date: April 1, 2026

---

# 1. EXCHANGE INTELLIGENCE MODULE

**Path:** `/app/backend/modules/exchange_intelligence/`

## Architecture

```
ExchangeContextAggregator
├── FundingOIEngine         (funding rate, OI change)
├── DerivativesPressureEngine   (long/short ratio, leverage, squeeze)
├── ExchangeLiquidationEngine   (cascade probability, trapped positions)
├── ExchangeFlowEngine      (taker buy/sell, aggressive flow, absorption)
└── ExchangeVolumeEngine    (volume ratio, anomaly, exhaustion)
```

## Available for Prediction

### FundingOIEngine (`funding_oi_engine.py`)
```python
Output: FundingOISignal
- funding_rate: float           # Current 8h funding
- funding_annualized: float     # Annualized funding
- funding_state: FundingState   # EXTREME_LONG/LONG_CROWDED/NEUTRAL/SHORT_CROWDED/EXTREME_SHORT
- oi_value: float              # Open interest in USD
- oi_change_pct: float         # OI change %
- oi_pressure: OIPressureState # EXPANDING/CONTRACTING/STABLE
- crowding_risk: float         # 0-1 (high funding + expanding OI)
- funding_oi_divergence: bool  # Unsustainable crowding

# USEFUL FOR PREDICTION:
# - crowding_risk > 0.7 → contrarian signal
# - funding_oi_divergence → reversal warning
# - EXTREME_LONG/SHORT → squeeze potential
```

### DerivativesPressureEngine (`derivatives_pressure_engine.py`)
```python
Output: DerivativesPressureSignal
- long_short_ratio: float      # L/S ratio (>2 or <0.5 = extreme)
- leverage_index: float        # 0-1 leverage level
- squeeze_probability: float   # 0-1 squeeze risk
- pressure_state: DerivativesPressure  # SHORT_SQUEEZE/LONG_SQUEEZE/LEVERAGE_EXCESS/BALANCED
- perp_premium: float          # Perp vs spot spread

# USEFUL FOR PREDICTION:
# - squeeze_probability > 0.6 + long_short_ratio → direction of squeeze
# - leverage_index > 0.7 → volatility spike warning
# - Formula: squeeze = 0.45*imbalance + 0.35*leverage + 0.20*premium
```

### ExchangeLiquidationEngine (`exchange_liquidation_engine.py`)
```python
Output: LiquidationSignal
- long_liq_zone: float         # Price level for long liquidations
- short_liq_zone: float        # Price level for short liquidations
- cascade_probability: float   # 0-1 cascade risk
- trapped_longs_pct: float     # % of OI in danger zone
- trapped_shorts_pct: float    # % of OI in danger zone
- net_liq_flow: float          # Recent liquidation direction

# USEFUL FOR PREDICTION:
# - cascade_probability > 0.6 → expect volatility
# - Price near long_liq_zone → expect dump + bounce
# - Price near short_liq_zone → expect pump + pullback
# - Formula: cascade = 0.35*trapped + 0.40*proximity + 0.25*flow
```

### ExchangeFlowEngine (`exchange_flow_engine.py`)
```python
Output: ExchangeFlowSignal
- taker_buy_ratio: float       # 0-1 (>0.6 = buy dominant)
- aggressive_flow: float       # -1 to 1 (buy/sell pressure)
- absorption_detected: bool    # High volume + small move
- flow_direction: FlowDirection # AGGRESSIVE_BUY/SELL/ABSORPTION_BUY/SELL/BALANCED
- flow_intensity: float        # 0-1 strength

# USEFUL FOR PREDICTION:
# - aggressive_flow > 0.3 → bullish momentum
# - absorption_detected → potential reversal
# - flow_intensity * direction → momentum factor
```

### ExchangeVolumeEngine (`exchange_volume_engine.py`)
```python
Output: VolumeContextSignal
- volume_ratio: float          # Current/avg (>2 = breakout, >3 = climax)
- volume_state: VolumeState    # CLIMAX/BREAKOUT_CONFIRMED/EXHAUSTION/ABNORMAL_HIGH/LOW/NORMAL
- buy_volume_pct: float        # 0-1 buy pressure
- volume_trend: str            # INCREASING/DECREASING/FLAT
- anomaly_score: float         # 0-1 z-score based

# USEFUL FOR PREDICTION:
# - CLIMAX/EXHAUSTION → reversal imminent
# - BREAKOUT_CONFIRMED + trend direction → continuation
# - anomaly_score > 0.7 → expect volatility
```

### ExchangeContextAggregator (`exchange_context_aggregator.py`)
```python
Output: ExchangeContext
- exchange_bias: ExchangeBias  # BULLISH/BEARISH/NEUTRAL
- confidence: float            # 0-1 weighted avg
- squeeze_probability: float
- cascade_probability: float
- crowding_risk: float
- flow_pressure: float         # -1 to 1

# BIAS COMPUTATION WEIGHTS:
W_FUNDING = 0.20
W_DERIVATIVES = 0.20
W_LIQUIDATION = 0.15
W_FLOW = 0.30      # ← STRONGEST SIGNAL
W_VOLUME = 0.15
```

---

# 2. REFLEXIVITY (SENTIMENT) ENGINE

**Path:** `/app/backend/modules/reflexivity_engine/`

## Architecture

Based on Soros Reflexivity Theory:
- Participants' expectations → influence prices
- Price changes → influence expectations
- Creates self-reinforcing/self-correcting feedback loops

## Reflexivity Engine (`reflexivity_engine.py`)

### Core Formula
```python
reflexivity_score = (
    0.35 * sentiment_score      # funding + liquidation imbalance
  + 0.25 * positioning_score    # OI expansion + crowding
  + 0.20 * trend_acceleration   # momentum acceleration
  + 0.20 * volatility_expansion # volume spike + OI expansion
)
```

### Source Data
```python
ReflexivitySource:
- funding_rate: float           # -0.003 to 0.003 typical
- funding_sentiment: float      # -1 to 1 (derived from funding)
- oi_change_24h: float         # % change
- oi_expansion: bool           # >3% = True
- long_liquidations: float     # USD volume
- short_liquidations: float    # USD volume
- liquidation_imbalance: float # -1 to 1 (short-long)/total
- volume_spike_ratio: float    # current/avg
- price_momentum: float        # -1 to 1
- trend_acceleration: float    # -1 to 1
```

### Sentiment Score Calculation
```python
sentiment = 0.6 * funding_sentiment + 0.4 * liquidation_imbalance
score = abs(sentiment)  # Magnitude matters, not direction
```

### Positioning Score Calculation
```python
oi_score = min(|oi_change_24h| * 5, 1.0) if expansion else 0
crowding = abs(funding_sentiment)
score = 0.5 * oi_score + 0.5 * crowding
```

### Feedback Direction
```python
# POSITIVE feedback (self-reinforcing):
# Rising prices + bullish sentiment = more bullish
# Falling prices + bearish sentiment = more bearish
if sentiment_direction * momentum_direction > 0:
    direction = "POSITIVE"  # Trend continues

# NEGATIVE feedback (self-correcting):
# Rising prices + bearish sentiment = reversal
if sentiment_direction * momentum_direction < 0:
    direction = "NEGATIVE"  # Reversal imminent
```

### Strength Classification
```python
WEAK_REFLEXIVITY_THRESHOLD = 0.3
STRONG_REFLEXIVITY_THRESHOLD = 0.6

if reflexivity_score >= 0.6:
    strength = "STRONG"    # High confidence prediction
elif reflexivity_score >= 0.3:
    strength = "MODERATE"
else:
    strength = "WEAK"
```

### Useful for Prediction
```python
# Strong positive feedback → trend continuation
# Strong negative feedback → expect reversal
# Reflexivity modifier for hypothesis:
REFLEXIVITY_WEIGHT = 0.08  # 8% adjustment to hypothesis score

if aligned:
    modifier = 1 + 0.08  # = 1.08x
else:
    modifier = 1 - 0.08  # = 0.92x
```

---

# 3. FRACTAL INTELLIGENCE MODULE

**Path:** `/app/backend/modules/fractal_intelligence/` + `/modules/fractal_market_intelligence/` + `/modules/macro_fractal_brain/`

## Architecture

### Three Levels:

#### Level 1: Fractal Market Intelligence
```
FractalEngine (fractal_engine.py)
├── classify_timeframe_state()  # 5m, 15m, 1h, 4h, 1d
├── calculate_alignment()        # Multi-timeframe agreement
├── determine_bias()             # LONG/SHORT/NEUTRAL
└── get_fractal_modifier()       # Hypothesis adjustment
```

#### Level 2: Asset Fractal Intelligence
```
AssetFractalService (asset_fractal_service.py)
├── BTCFractalAdapter
├── SPXFractalAdapter
└── DXYFractalAdapter
```

#### Level 3: Macro-Fractal Brain
```
MacroFractalEngine (macro_fractal_engine.py)
├── MacroContext
├── BTC/SPX/DXY AssetFractalContext
└── CrossAssetAlignment
```

## Fractal Market Intelligence (`fractal_engine.py`)

### Timeframe State Classification
```python
def classify_timeframe_state(ema_slope, atr_expansion, structure_break):
    # VOLATILE: High ATR expansion (>1.5)
    # TREND_UP: Positive EMA slope (>0.02)
    # TREND_DOWN: Negative EMA slope (<-0.02)
    # RANGE: Low ATR, flat EMA
    
    if atr_expansion > 1.5:
        return "VOLATILE", 0.5 + atr_expansion * 0.2
    
    if abs(ema_slope) > 0.02:
        confidence = 0.5 + abs(ema_slope) * 10
        return "TREND_UP" if ema_slope > 0 else "TREND_DOWN", confidence
    
    return "RANGE", 0.6 + (1 - atr_expansion) * 0.3
```

### Alignment Calculation
```python
def calculate_alignment(tf_states):
    up_count = count("TREND_UP")
    down_count = count("TREND_DOWN")
    
    alignment = dominant_count / total_timeframes
    # alignment >= 0.6 → strong directional bias
    # alignment < 0.4 → neutral
```

### Fractal Confidence
```python
ALIGNMENT_WEIGHT = 0.60
VOLATILITY_CONSISTENCY_WEIGHT = 0.40

confidence = 0.60 * alignment + 0.40 * volatility_consistency
```

### Hypothesis Modifier
```python
FRACTAL_ALIGNED_MODIFIER = 1.08    # +8% if aligned
FRACTAL_CONFLICT_MODIFIER = 0.92   # -8% if conflict
```

## Asset Fractal Types (`asset_fractal_types.py`)

```python
class AssetFractalContext:
    direction: str           # LONG/SHORT/HOLD
    confidence: float        # 0-1
    reliability: float       # 0-1
    dominant_horizon: int    # 7, 14, 30, or 60 days
    expected_return: float   # Expected % return for horizon
    phase: str              # ACCUMULATION/DISTRIBUTION/MARKUP/MARKDOWN
    strength: float         # 0-1
    context_state: str      # SUPPORTIVE/CONFLICTED/BLOCKED/NEUTRAL

# USEFUL FOR PREDICTION:
# - direction + expected_return → price target
# - dominant_horizon → timeframe for prediction
# - phase → market cycle position
```

## Macro-Fractal Brain (`macro_fractal_engine.py`)

### Final Bias Computation
```python
# BULLISH: cross_asset BULLISH + BTC not bearish + macro not RISK_OFF
# BEARISH: cross_asset BEARISH + BTC not bullish + macro not RISK_ON
# MIXED: conflicting signals
# NEUTRAL: weak signals
```

### Confidence Weights
```python
CONFIDENCE_WEIGHTS = {
    "macro": 0.25,
    "btc": 0.20,
    "spx": 0.15,
    "dxy": 0.10,
    "cross_asset": 0.30
}
```

### Reliability Weights
```python
RELIABILITY_WEIGHTS = {
    "macro": 0.30,
    "btc": 0.20,
    "spx": 0.15,
    "dxy": 0.10,
    "cross_asset": 0.25
}
```

### Context State
```python
# BLOCKED: macro blocked + all assets neutral + low alignment
# SUPPORTIVE: directional bias + high confidence + high reliability
# CONFLICTED: mixed bias or low reliability
# MIXED: everything else
```

---

# 4. MONTE CARLO & SIMULATION

**Path:** `/app/backend/modules/validation/`

## Monte Carlo Engine (`montecarlo.py`)

### Purpose
Tests strategy robustness through simulated variations.

### Variations Applied
```python
variations = {
    "volatility_range": [0.8, 1.2],      # ±20% volatility
    "slippage_range": [5, 30],           # bps
    "wick_multiplier_range": [0.5, 2.0]  # Wick size variation
}
```

### Simulation Process
```python
for i in range(1000 iterations):
    # Apply random variations
    volatility_mult = random.uniform(0.8, 1.2)
    slippage_mult = random.uniform(0.5, 3.0)
    wick_mult = random.uniform(0.5, 2.0)
    
    # Adjust win rate based on variations
    adjusted_win_rate = base_win_rate
    adjusted_win_rate *= (1 - (volatility_mult - 1) * 0.1)  # Higher vol = lower WR
    adjusted_win_rate *= (1 - (slippage_mult - 1) * 0.02)   # Higher slip = lower WR
    adjusted_win_rate *= (1 - (wick_mult - 1) * 0.03)       # Bigger wicks = lower WR
    
    # Simulate trades
    for trade in trades_per_run:
        if win:
            r = random.uniform(0.5, 3.0) * volatility_mult
        else:
            r = -random.uniform(0.5, 1.5) * wick_mult
```

### Output
```python
MonteCarloResult:
- median_pnl: float
- mean_pnl: float
- std_pnl: float
- worst_case_pnl: float       # 0th percentile
- best_case_pnl: float        # 100th percentile
- percentile_5: float         # 5th percentile (VaR)
- percentile_95: float        # 95th percentile
- survival_rate: float        # % survived without ruin
- ruin_probability: float     # % hit 50% drawdown
- robustness_score: float     # 0-1 overall score
```

### Robustness Score Formula
```python
robustness = (
    0.30 * survival_rate
  + 0.25 * median_positive_score
  + 0.20 * low_volatility_score
  + 0.25 * positive_5th_percentile_score
)
```

---

# 5. WHAT CAN BE USED FOR PREDICTION ENGINE

## From Exchange Intelligence:
1. **squeeze_probability** → Directional volatility forecast
2. **cascade_probability** → Volatility magnitude forecast
3. **crowding_risk** → Contrarian signal (reversal probability)
4. **exchange_bias** → Direction with confidence
5. **flow_pressure** → Momentum continuation/exhaustion
6. **liquidation zones** → Price targets (support/resistance)

## From Reflexivity (Sentiment):
1. **reflexivity_score** → Trend strength/sustainability
2. **feedback_direction** → POSITIVE = continuation, NEGATIVE = reversal
3. **sentiment_state** → EUPHORIC/GREEDY/NEUTRAL/FEARFUL/PANIC
4. **positioning_score** → Crowding indicator

## From Fractal Intelligence:
1. **fractal_alignment** → Multi-timeframe agreement
2. **expected_return** → Price target % for horizon
3. **dominant_horizon** → Best prediction timeframe
4. **phase** → Market cycle (accumulation → markup → distribution → markdown)
5. **context_state** → SUPPORTIVE/CONFLICTED/BLOCKED

## From Monte Carlo:
1. **robustness_score** → Confidence in prediction
2. **percentile_5** → Worst-case scenario
3. **percentile_95** → Best-case scenario
4. **survival_rate** → Probability of success

---

# 6. PROPOSED UNIFIED PREDICTION ENGINE

```python
class UnifiedPredictionEngine:
    def predict(self, symbol: str, horizon: str) -> Prediction:
        # 1. Gather signals
        exchange = ExchangeContextAggregator().compute(symbol)
        reflexivity = ReflexivityEngine().compute_state(symbol)
        fractal = MacroFractalEngine().compute(...)
        
        # 2. Determine direction
        direction_signals = [
            (exchange.exchange_bias, exchange.confidence * 0.30),
            (reflexivity.feedback_direction, reflexivity.reflexivity_score * 0.25),
            (fractal.final_bias, fractal.final_confidence * 0.25),
            (pattern_signal, pattern_confidence * 0.20)
        ]
        direction = weighted_vote(direction_signals)
        
        # 3. Calculate price target
        base_move = fractal.btc.expected_return  # e.g., 0.12 = 12%
        
        # Adjust by exchange signals
        if exchange.squeeze_probability > 0.6:
            base_move *= 1.3  # Squeeze adds momentum
        if exchange.crowding_risk > 0.7:
            base_move *= 0.8  # Contrarian = less certain
        
        # Adjust by reflexivity
        if reflexivity.feedback_direction == "POSITIVE":
            base_move *= (1 + reflexivity.reflexivity_score * 0.2)
        else:
            base_move *= (1 - reflexivity.reflexivity_score * 0.3)
        
        # 4. Generate path
        path = PathGenerator().generate(
            current_price=current_price,
            target_price=current_price * (1 + base_move),
            horizon_days=horizon_to_days(horizon),
            volatility=exchange.volume_signal.anomaly_score,
            trend_strength=fractal.fractal_alignment
        )
        
        # 5. Calculate confidence bands
        mc_result = MonteCarloEngine().run(...)
        
        return Prediction(
            direction=direction,
            price_target=current_price * (1 + base_move),
            confidence=combined_confidence,
            range_low=current_price * (1 + mc_result.percentile_5),
            range_high=current_price * (1 + mc_result.percentile_95),
            path=path,
            robustness=mc_result.robustness_score
        )
```

---

# 7. SUMMARY TABLE

| Module | Component | Used For | Weight |
|--------|-----------|----------|--------|
| Exchange | squeeze_probability | Volatility direction | 0.15 |
| Exchange | cascade_probability | Volatility magnitude | 0.10 |
| Exchange | exchange_bias | Direction | 0.20 |
| Exchange | flow_pressure | Momentum | 0.15 |
| Reflexivity | reflexivity_score | Trend sustainability | 0.15 |
| Reflexivity | feedback_direction | Continuation vs reversal | 0.10 |
| Fractal | expected_return | Price target | 0.25 |
| Fractal | fractal_alignment | Confidence modifier | 0.10 |
| Fractal | phase | Cycle position | 0.05 |
| Monte Carlo | robustness_score | Final confidence | 0.10 |
| Monte Carlo | percentiles | Confidence bands | - |

---

# 8. FILES TO USE

```
/app/backend/modules/exchange_intelligence/
├── exchange_context_aggregator.py   # Main entry point
├── funding_oi_engine.py
├── derivatives_pressure_engine.py
├── exchange_liquidation_engine.py
├── exchange_flow_engine.py
└── exchange_volume_engine.py

/app/backend/modules/reflexivity_engine/
├── reflexivity_engine.py            # Main entry point
└── reflexivity_types.py

/app/backend/modules/fractal_intelligence/
├── asset_fractal_service.py         # Main entry point
└── asset_fractal_types.py

/app/backend/modules/macro_fractal_brain/
├── macro_fractal_engine.py          # Main entry point
└── macro_fractal_types.py

/app/backend/modules/validation/
├── montecarlo.py                    # Monte Carlo simulation
└── simulation.py                    # Historical simulation
```
