# Market Intelligence OS — Architecture Freeze Documentation

## Version: MARKET_INTELLIGENCE_OS_V1_FROZEN
## Date: 2026-03-14
## Status: PRODUCTION CORE FROZEN

---

## 1. Frozen Architecture Layers

```
┌─────────────────────────────────────────────────────────────┐
│                  MARKET INTELLIGENCE OS V1                  │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  LAYER 7 — Simulation Intelligence                          │
│  └── Market Simulation Engine (forward-looking scenarios)   │
│                                                              │
│  LAYER 6 — Cross-Asset Intelligence                         │
│  └── Cross-Asset Similarity Engine (BTC≈ETH, ETH≈SPX)      │
│                                                              │
│  LAYER 5 — Similarity Intelligence                          │
│  └── Fractal Similarity Engine (current≈historical)        │
│                                                              │
│  LAYER 4 — Fractal Intelligence                             │
│  └── Fractal Market Intelligence (multi-timeframe)         │
│                                                              │
│  LAYER 3 — Microstructure Intelligence                      │
│  └── Microstructure Engine (liquidity, pressure)           │
│                                                              │
│  LAYER 2 — Regime Intelligence                              │
│  └── Regime Engine (market state detection)                │
│                                                              │
│  LAYER 1 — Alpha Intelligence                               │
│  └── Alpha Factory (signal generation)                     │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## 2. Frozen Formulas

### 2.1 Hypothesis Score Formula

```
hypothesis_score =
    0.33 × alpha_support
  + 0.23 × regime_support
  + 0.18 × microstructure_support
  + 0.10 × macro_support
  + 0.05 × fractal_market_confidence
  + 0.05 × fractal_similarity_modifier
  + 0.06 × cross_asset_modifier
────────────────────────────────────
  = 1.00 (total)
```

### 2.2 Scenario Probability Formula

```
scenario_probability =
    0.35 × hypothesis_score
  + 0.20 × regime_support
  + 0.15 × microstructure_support
  + 0.15 × fractal_similarity_score
  + 0.15 × meta_alpha_score
────────────────────────────────────
  = 1.00 (total)
```

### 2.3 Capital Allocation Formula

```
capital_weight =
    ranking_score
  × adaptive_modifier
  × meta_alpha_modifier
  × simulation_modifier
```

### 2.4 Fractal Similarity Modifier

```
aligned_with_historical → 1.12
conflict_with_historical → 0.90
neutral → 1.00
```

### 2.5 Cross-Asset Similarity Modifier

```
aligned_with_cross_asset → 1.10
conflict_with_cross_asset → 0.92
neutral → 1.00
```

### 2.6 Confidence Formula (Similarity)

```
confidence =
    0.50 × similarity_score
  + 0.30 × historical_success_rate
  + 0.20 × cross_asset_weight
```

---

## 3. Frozen API Surface

### 3.1 Hypothesis Engine
- `GET  /api/v1/hypothesis/health`
- `GET  /api/v1/hypothesis/{symbol}`
- `GET  /api/v1/hypothesis/top/{symbol}`
- `POST /api/v1/hypothesis/run/{symbol}`

### 3.2 Hypothesis Portfolio
- `GET  /api/v1/hypothesis/portfolio/{symbol}`
- `GET  /api/v1/hypothesis/portfolio/allocation`

### 3.3 Fractal Intelligence
- `GET  /api/v1/fractal/health`
- `GET  /api/v1/fractal/{symbol}`

### 3.4 Fractal Similarity
- `GET  /api/v1/fractal-similarity/health`
- `GET  /api/v1/fractal-similarity/{symbol}`
- `GET  /api/v1/fractal-similarity/top/{symbol}`
- `GET  /api/v1/fractal-similarity/modifier/{symbol}`
- `POST /api/v1/fractal-similarity/recompute/{symbol}`

### 3.5 Cross-Asset Similarity
- `GET  /api/v1/cross-similarity/health`
- `GET  /api/v1/cross-similarity/matrix`
- `GET  /api/v1/cross-similarity/{symbol}`
- `GET  /api/v1/cross-similarity/top/{symbol}`
- `GET  /api/v1/cross-similarity/assets/{symbol}`
- `GET  /api/v1/cross-similarity/modifier/{symbol}`
- `POST /api/v1/cross-similarity/recompute/{symbol}`

### 3.6 Market Simulation
- `GET  /api/v1/simulation/health`
- `GET  /api/v1/simulation/{symbol}`
- `GET  /api/v1/simulation/top/{symbol}`
- `GET  /api/v1/simulation/history/{symbol}`
- `GET  /api/v1/simulation/modifier/{symbol}`
- `GET  /api/v1/simulation/summary/{symbol}`
- `GET  /api/v1/simulation/multi-horizon/{symbol}`
- `POST /api/v1/simulation/recompute/{symbol}`

---

## 4. Frozen Contracts

### 4.1 HypothesisCandidate
```python
class HypothesisCandidate(BaseModel):
    hypothesis_type: str
    directional_bias: str
    alpha_support: float  # [0, 1]
    regime_support: float  # [0, 1]
    macro_support: float  # [0, 1]
    confidence: float  # [0, 1]
```

### 4.2 MarketScenario
```python
class MarketScenario(BaseModel):
    scenario_id: str
    symbol: str
    scenario_type: ScenarioType
    probability: float  # [0, 1]
    expected_direction: DirectionType
    expected_move_percent: float
    horizon_minutes: int
    confidence: float  # [0, 1]
```

### 4.3 CrossAssetMatch
```python
class CrossAssetMatch(BaseModel):
    match_id: str
    source_symbol: str
    reference_symbol: str
    similarity_score: float  # [0, 1]
    expected_direction: DirectionType
    confidence: float  # [0, 1]
    cross_asset_weight: float  # [0, 1]
```

### 4.4 StructureVector
```python
class StructureVector(BaseModel):
    symbol: str
    window_size: int
    trend_slope: float  # [-1, 1]
    volatility: float  # [0, 1]
    volume_delta: float  # [-1, 1]
    liquidity_state: float  # [0, 1]
    microstructure_bias: float  # [-1, 1]
```

---

## 5. Freeze Rules

### PROHIBITED after freeze:
- ❌ Changing formula weights
- ❌ Modifying contract fields
- ❌ Breaking API compatibility
- ❌ Restructuring layers
- ❌ Removing endpoints

### PERMITTED after freeze:
- ✅ Adding new layers above Layer 7
- ✅ Adding UI/dashboard components
- ✅ Adding control systems
- ✅ Adding new datasets
- ✅ Adding new endpoints (non-breaking)
- ✅ Performance optimizations
- ✅ Bug fixes (logic unchanged)

---

## 6. Module Registry

| Module | Layer | Version | Status |
|--------|-------|---------|--------|
| Alpha Factory | 1 | 1.0.0 | FROZEN |
| Regime Intelligence | 2 | 2.0.0 | FROZEN |
| Microstructure Intelligence | 3 | 2.0.0 | FROZEN |
| Fractal Market Intelligence | 4 | 1.0.0 | FROZEN |
| Fractal Similarity Engine | 5 | 1.0.0 | FROZEN |
| Cross-Asset Similarity | 6 | 1.0.0 | FROZEN |
| Market Simulation Engine | 7 | 1.0.0 | FROZEN |
| Hypothesis Engine | Core | 3.0.0 | FROZEN |
| Capital Allocation | Core | 2.0.0 | FROZEN |
| Meta Alpha Engine | Core | 1.0.0 | FROZEN |

---

## 7. Test Coverage Summary

| Module | Tests | Status |
|--------|-------|--------|
| Fractal Similarity | 36 | ✅ PASS |
| Market Simulation | 41 | ✅ PASS |
| Cross-Asset Similarity | 41 | ✅ PASS |
| **Total Core Tests** | **118+** | ✅ PASS |

---

## 8. Version Tag

```
MARKET_INTELLIGENCE_OS_V1_FROZEN
Released: 2026-03-14
Commit: Architecture freeze - production core locked
```

---

## 9. Signature

This document represents the frozen state of Market Intelligence OS core.
All layers, formulas, and contracts are locked for production use.

```
Status: FROZEN
Date: 2026-03-14
Version: 1.0.0
Integrity: VERIFIED
```
