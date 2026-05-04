# Alpha Decay Engine Architecture

**PHASE 43.8 — Alpha Decay Engine**  
**Architecture Freeze Document**

---

## Overview

Alpha Decay Engine tracks signal aging and adjusts confidence/execution eligibility.

**Problem solved:**
- ⚠️ Trading stale signals
- ⚠️ Increased churn
- ⚠️ Catching noise

**Effects:**
- ↓ Reduces unnecessary trades
- ↓ Reduces noise trades
- ↑ Improves timing
- ↑ Increases Sharpe (+10-15% performance improvement)

---

## Core Formula

```
decay_factor = exp(-age_minutes / half_life)
adjusted_confidence = initial_confidence × decay_factor
```

**Example:**
- half_life = 60 min
- age = 30 min
- decay_factor = exp(-30/60) ≈ 0.606
- initial_confidence = 0.80
- adjusted_confidence = 0.80 × 0.606 ≈ 0.48

---

## Decay Stages

| Stage | Decay Factor Range | Description |
|-------|-------------------|-------------|
| FRESH | 0.75 - 1.00 | Signal is fresh and strong |
| ACTIVE | 0.50 - 0.75 | Signal is active |
| WEAKENING | 0.25 - 0.50 | Signal is weakening |
| EXPIRED | < 0.25 | Signal expired, execution blocked |

---

## Dynamic Half-Lives

Different signal types have different decay rates:

| Signal Type | Half-Life | Use Case |
|-------------|-----------|----------|
| TREND | 120 min | Trend-following signals |
| BREAKOUT | 90 min | Breakout signals |
| MEAN_REVERSION | 30 min | Mean reversion (fast decay) |
| FRACTAL | 180 min | Fractal pattern signals |
| CAPITAL_FLOW | 240 min | Capital flow signals |
| REGIME | 360 min | Regime change signals |
| DEFAULT | 60 min | Default for other signals |

---

## Expiration Rule

```
if decay_factor < 0.25:
    signal_status = EXPIRED
    execution_blocked = True
```

When expired:
- Execution Brain blocks trade
- Portfolio Manager doesn't allocate
- Signal flagged for removal

---

## Pipeline Position

```
Market Intelligence
       ↓
Hypothesis Engine
       ↓
Alpha Decay Engine  ← NEW (43.8)
       ↓
Portfolio Manager
       ↓
Execution Brain
       ↓
Exchange Gateway
```

---

## Integration Points

### 1. Hypothesis Engine

Confidence modifier:

```
hypothesis_confidence × decay_factor
```

### 2. Portfolio Manager

Position size modifier:

```
position_size = base_size × decay_factor
```

### 3. Execution Brain

Eligibility check:

```
if decay_stage == EXPIRED:
    execution = BLOCKED
```

---

## Core Contract

```python
class AlphaDecayState(BaseModel):
    hypothesis_id: str
    symbol: str
    signal_type: SignalType
    
    created_at: datetime
    age_minutes: int
    half_life_minutes: int
    
    initial_confidence: float
    decay_factor: float
    adjusted_confidence: float
    
    decay_stage: DecayStage
    
    expires_at: datetime
    is_expired: bool
    execution_blocked: bool
```

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/alpha-decay/health` | Health check |
| GET | `/api/v1/alpha-decay/state/{hypothesis_id}` | Get decay state |
| GET | `/api/v1/alpha-decay/summary/all` | Get summary |
| GET | `/api/v1/alpha-decay/statistics/all` | Get statistics |
| POST | `/api/v1/alpha-decay/create` | Create decay state |
| POST | `/api/v1/alpha-decay/recompute` | Recompute all |
| POST | `/api/v1/alpha-decay/expire` | Expire old signals |
| GET | `/api/v1/alpha-decay/confidence/{hypothesis_id}` | Confidence modifier |
| GET | `/api/v1/alpha-decay/position-size/{hypothesis_id}` | Size modifier |
| GET | `/api/v1/alpha-decay/execution-check/{hypothesis_id}` | Eligibility check |

---

## MongoDB Collection

**Collection:** `alpha_decay_states`

**Indexes:**
- `hypothesis_id` (unique)
- `symbol`
- `created_at`
- `decay_stage`
- `(symbol, created_at)`

---

## Scheduler Tasks

Every 5 minutes:
1. `recompute_decay_states()` — Update all decay factors
2. `expire_old_signals()` — Mark old signals as expired

---

## File Structure

```
modules/
├── alpha_decay/
│   ├── __init__.py
│   ├── decay_types.py      # Contracts
│   ├── decay_engine.py     # Core logic
│   ├── decay_registry.py   # MongoDB
│   └── decay_routes.py     # API
```

---

## Configuration

```python
class AlphaDecayConfig(BaseModel):
    default_half_life_minutes: int = 60
    use_dynamic_half_life: bool = True
    expiration_threshold: float = 0.25
    recompute_interval_minutes: int = 5
    auto_expire_enabled: bool = True
    max_age_hours: int = 24
```

---

## Best Practices

1. **Create decay state when hypothesis is generated**
2. **Check decay before execution**
3. **Use dynamic half-lives for signal types**
4. **Periodically clean up expired states**

---

**Document Version:** 1.0  
**Last Updated:** 2026-03-14  
**Status:** FROZEN
