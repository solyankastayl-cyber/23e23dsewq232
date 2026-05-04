# Capital Flow Engine Architecture

**PHASE 42 — Capital Flow Engine**  
**PHASE 42.4 — Capital Flow Integration**  
**PHASE 42.5 — Architecture Freeze**

---

## Overview

Capital Flow Engine is the 12th intelligence layer in the Market Intelligence OS.  
It tracks inter-asset capital rotation across 4 fixed buckets:

- **BTC** — Bitcoin
- **ETH** — Ethereum  
- **ALTS** — Altcoins basket
- **CASH** — Stablecoins / risk-off

---

## Core Contracts

### 1. CapitalFlowSnapshot (42.1)

```python
class CapitalFlowSnapshot:
    snapshot_id: str
    timestamp: datetime
    
    # Flow scores per bucket: -1..+1
    btc_flow_score: float
    eth_flow_score: float
    alt_flow_score: float
    cash_flow_score: float
    
    # Dominance shifts
    btc_dominance_shift: float
    eth_dominance_shift: float
    
    # Market structure shifts
    oi_shift: float
    funding_shift: float
    volume_shift: float
    
    # Flow state — snapshot description
    flow_state: FlowState  # BTC_INFLOW, ETH_INFLOW, ALT_INFLOW, CASH_INFLOW, MIXED_FLOW
```

### 2. RotationState (42.2)

```python
class RotationState:
    rotation_id: str
    rotation_type: RotationType
    from_bucket: FlowBucket
    to_bucket: FlowBucket
    rotation_strength: float  # 0..1
    confidence: float         # 0..1
    timestamp: datetime
```

**Rotation Types:**
- `BTC_TO_ETH`
- `ETH_TO_ALTS`
- `ALTS_TO_BTC`
- `BTC_TO_CASH`
- `ETH_TO_CASH`
- `RISK_TO_CASH`
- `CASH_TO_BTC`
- `CASH_TO_ETH`
- `NO_ROTATION`

### 3. FlowScore (42.3)

```python
class FlowScore:
    score_id: str
    flow_bias: FlowBias      # BTC, ETH, ALTS, CASH, NEUTRAL
    flow_strength: float     # 0..1
    flow_confidence: float   # 0..1
    dominant_rotation: RotationType
    timestamp: datetime
```

---

## Integration Points (PHASE 42.4)

### 1. Hypothesis Engine Integration

**Weight in formula:** `capital_flow_weight = 0.05`

**Updated Hypothesis Score Formula:**

| Factor | Weight |
|--------|--------|
| Alpha | 0.25 |
| Regime | 0.18 |
| Microstructure | 0.13 |
| Macro | 0.08 |
| Fractal Market | 0.05 |
| Fractal Similarity | 0.05 |
| Cross-Asset | 0.05 |
| Regime Memory | 0.07 |
| Reflexivity | 0.05 |
| Regime Graph | 0.04 |
| **Capital Flow** | **0.05** |
| **Total** | **1.00** |

**Flow Modifier:**

```
If flow_bias aligns with hypothesis:
    modifier = 1.08
If flow_bias conflicts:
    modifier = 0.92
If neutral:
    modifier = 1.0
```

**Alignment Examples:**

| flow_bias | hypothesis | result |
|-----------|------------|--------|
| BTC | BTC_BREAKOUT (LONG) | aligned → 1.08 |
| CASH | ALT_BREAKOUT (LONG) | conflict → 0.92 |
| ETH | ETHUSDT SHORT | conflict → 0.92 |
| ALTS | SOL LONG | aligned → 1.08 |

### 2. Portfolio Manager Integration

**Capital Flow → Portfolio Rotation**

| Flow Bias | Portfolio Action |
|-----------|------------------|
| BTC | Increase BTC exposure |
| ETH | Increase ETH exposure |
| ALTS | Increase alt basket |
| CASH | Reduce risk exposure |

**Weight Modifiers:**

```
aligned asset weight × 1.05
conflicting asset weight × 0.95
```

### 3. Simulation Engine Integration

**Flow Bias → Scenario Ranking**

| Rotation | Boosted Scenarios |
|----------|-------------------|
| ALTS_TO_BTC | BTC leadership, risk-off |
| RISK_TO_CASH | Crash, delever scenarios |
| CASH_TO_BTC | Recovery scenarios |
| ETH_TO_ALTS | Alt season scenarios |

**Ranking Modifiers:**

```
aligned scenario × 1.06
conflict scenario × 0.94
```

---

## Critical Rules

Capital Flow Engine:

- ❌ Does **NOT** generate orders
- ❌ Does **NOT** manage execution
- ❌ Does **NOT** influence stop/TP directly

It **ONLY** influences:
- ✅ Hypothesis confidence
- ✅ Portfolio rotation weights
- ✅ Scenario ranking

---

## Rotation Detection Formula (42.2)

```
rotation_strength =
    0.40 * relative_flow_diff
  + 0.20 * dominance_shift
  + 0.20 * oi_shift
  + 0.20 * volume_shift
```

**Threshold:** `min_rotation_strength = 0.15`  
Below threshold → `NO_ROTATION`

---

## Flow Score Formula (42.3)

```
flow_strength =
    0.50 * abs(rotation_strength)
  + 0.30 * abs(dominance_shift)
  + 0.20 * abs(volume_shift)

flow_confidence =
    0.60 * flow_strength
  + 0.40 * rotation_confidence
```

**Threshold:** `min_flow_strength = 0.10`  
Below threshold → `NEUTRAL` bias

---

## MongoDB Collections

### capital_flow_snapshots

```javascript
{
  snapshot_id: "cfs_20260314...",
  btc_flow_score: 0.35,
  eth_flow_score: 0.12,
  alt_flow_score: -0.15,
  cash_flow_score: -0.32,
  flow_state: "BTC_INFLOW",
  timestamp: ISODate("...")
}
```

**Indexes:**
- `{ timestamp: -1 }`
- `{ flow_state: 1, timestamp: -1 }`

### capital_flow_rotations

```javascript
{
  rotation_id: "rot_20260314...",
  rotation_type: "ALTS_TO_BTC",
  from_bucket: "ALTS",
  to_bucket: "BTC",
  rotation_strength: 0.45,
  confidence: 0.72,
  timestamp: ISODate("...")
}
```

**Indexes:**
- `{ timestamp: -1 }`
- `{ rotation_type: 1, timestamp: -1 }`

### capital_flow_scores

```javascript
{
  score_id: "fs_20260314...",
  flow_bias: "BTC",
  flow_strength: 0.48,
  flow_confidence: 0.65,
  dominant_rotation: "ALTS_TO_BTC",
  timestamp: ISODate("...")
}
```

**Indexes:**
- `{ timestamp: -1 }`
- `{ flow_bias: 1, timestamp: -1 }`

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/capital-flow/snapshot` | Current flow snapshot |
| GET | `/api/v1/capital-flow/rotation` | Current rotation state |
| GET | `/api/v1/capital-flow/score` | Current flow score |
| POST | `/api/v1/capital-flow/recompute` | Recompute with custom data |
| GET | `/api/v1/capital-flow/history` | Historical data |
| GET | `/api/v1/capital-flow/config` | Configuration |
| GET | `/api/v1/capital-flow/health` | Health check |
| GET | `/api/v1/capital-flow/summary` | Full integration summary |
| GET | `/api/v1/capital-flow/hypothesis-modifier` | Hypothesis modifier |
| GET | `/api/v1/capital-flow/portfolio-adjustment` | Portfolio adjustment |
| GET | `/api/v1/capital-flow/portfolio-rotation-signals` | Rotation signals |
| GET | `/api/v1/capital-flow/scenario-modifier` | Scenario ranking modifier |

---

## Intelligence Layers (After PHASE 42)

The system now has **12 intelligence layers**:

1. Alpha
2. Regime
3. Microstructure
4. Fractal Market
5. Fractal Similarity
6. Cross-Asset
7. Simulation
8. Regime Memory
9. Reflexivity
10. Regime Graph
11. **Capital Flow** ← NEW
12. Hypothesis (aggregator)

---

## Configuration

```python
class CapitalFlowConfig:
    # Rotation formula weights
    rotation_weight_flow_diff: float = 0.40
    rotation_weight_dominance: float = 0.20
    rotation_weight_oi: float = 0.20
    rotation_weight_volume: float = 0.20

    # Flow score formula weights
    score_weight_rotation: float = 0.50
    score_weight_dominance: float = 0.30
    score_weight_volume: float = 0.20

    # Confidence formula weights
    confidence_weight_strength: float = 0.60
    confidence_weight_rotation: float = 0.40

    # Thresholds
    min_rotation_strength: float = 0.15
    min_flow_strength: float = 0.10
    strong_flow_threshold: float = 0.50
```

---

## File Structure

```
modules/
├── capital_flow/
│   ├── __init__.py
│   ├── flow_types.py           # Contracts
│   ├── flow_snapshot_engine.py # 42.1
│   ├── flow_rotation_engine.py # 42.2
│   ├── flow_scoring_engine.py  # 42.3
│   ├── flow_integration.py     # 42.4
│   ├── flow_registry.py        # Storage
│   └── flow_routes.py          # API
```

---

## Version History

| Phase | Description |
|-------|-------------|
| 42.1 | Flow Snapshot Engine |
| 42.2 | Rotation Detection Engine |
| 42.3 | Flow Scoring Engine |
| 42.4 | Integration (Hypothesis/Portfolio/Simulation) |
| 42.5 | Architecture Freeze |

---

**Document Version:** 1.0  
**Last Updated:** 2026-03-14  
**Status:** FROZEN
