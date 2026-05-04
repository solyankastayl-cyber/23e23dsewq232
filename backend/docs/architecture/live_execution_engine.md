# Live Execution Engine Architecture

**PHASE 43 — Live Exchange Integration**  
**Architecture Freeze Document**

---

## Overview

PHASE 43 establishes the live execution layer enabling real exchange trading through a pilot-safe architecture.

---

## Components

### 43.1 Live Exchange Connectors

Adapters for real exchanges:
- **Binance** (Primary)
- **Bybit** (Secondary)
- **Coinbase** (Disabled by default)
- **Hyperliquid** (Disabled by default)

### 43.2 Exchange Sync Engine

Maintains synchronized state between system and exchanges.
Exchange is the source of truth.

**Sync tasks (every 10-15 seconds):**
- Positions sync
- Balances sync
- Open orders sync
- Recent fills sync

**MongoDB Collections:**
- `exchange_positions`
- `exchange_balances`
- `exchange_orders`
- `exchange_fills`

### 43.3 Pilot Trading Mode

Safe launch mode with strict constraints.

**Default Constraints:**
| Constraint | Limit |
|------------|-------|
| max_capital_usage | 5% portfolio |
| max_position_size | 2% portfolio |
| max_single_order | $5,000 |
| max_trades_per_hour | 10 |
| max_trades_per_day | 30 |

**Pilot Stages:**
1. **Stage A:** Paper + Approval
2. **Stage B:** Live + Approval + Small Capital (PILOT)
3. **Stage C:** Live + Partial Automation
4. **Stage D:** Full Automation (after stats confirm stability)

### 43.4 Trade Throttle Engine

Execution rate limiter + risk throttle.

**Throttle Rules:**
| Rule | Limit |
|------|-------|
| max_trades_per_5min | 3 |
| max_trades_per_hour | 10 |
| max_turnover_per_hour | 15% portfolio |
| max_position_change | 20% per trade |
| loss_streak_cooldown | 10 min after 3 consecutive losses |

**Throttle Levels:**
- NONE: No throttling
- LOW: Minor delays
- MEDIUM: Significant delays
- HIGH: Heavy throttling
- BLOCKED: All execution blocked

---

## Execution Pipeline

```
Hypothesis Engine
       ↓
Portfolio Manager
       ↓
Risk Budget Engine
       ↓
Execution Brain
       ↓
Trade Throttle Engine  ← NEW (43.4)
       ↓
Safety Gate
       ↓
Pilot Mode Check       ← NEW (43.3)
       ↓
Execution Gateway
       ↓
Exchange Adapter
       ↓
Order Fill
       ↓
Exchange Sync          ← NEW (43.2)
       ↓
Portfolio Update
```

---

## Execution Modes

| Mode | Description |
|------|-------------|
| PAPER | Simulated fills |
| APPROVAL | User approves trade, then order goes to exchange |
| LIVE | Auto execution (disabled by default) |

**Default:** `EXECUTION_MODE=APPROVAL`

---

## Safety Requirements

For PILOT mode, all must be TRUE:

- ✅ Approval mode active
- ✅ Kill switch ready
- ✅ Circuit breaker ready
- ✅ Trade throttle active

If any FALSE → execution blocked.

---

## API Endpoints

### Exchange Sync (43.2)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/live-execution/sync/summary` | Sync summary |
| GET | `/api/v1/live-execution/sync/positions` | Synced positions |
| GET | `/api/v1/live-execution/sync/balances` | Synced balances |
| GET | `/api/v1/live-execution/sync/orders` | Open orders |
| POST | `/api/v1/live-execution/sync/start` | Start sync |
| POST | `/api/v1/live-execution/sync/stop` | Stop sync |
| POST | `/api/v1/live-execution/sync/refresh` | Manual refresh |

### Pilot Mode (43.3)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/live-execution/pilot/summary` | Pilot summary |
| GET | `/api/v1/live-execution/pilot/state` | Pilot state |
| GET | `/api/v1/live-execution/pilot/constraints` | Constraints |
| POST | `/api/v1/live-execution/pilot/check` | Check constraints |
| POST | `/api/v1/live-execution/pilot/set-mode` | Set mode |

### Trade Throttle (43.4)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/live-execution/throttle/summary` | Throttle summary |
| GET | `/api/v1/live-execution/throttle/state` | Throttle state |
| GET | `/api/v1/live-execution/throttle/config` | Configuration |
| POST | `/api/v1/live-execution/throttle/check` | Check throttle |
| POST | `/api/v1/live-execution/throttle/emergency-block` | Emergency |
| POST | `/api/v1/live-execution/throttle/reset-daily` | Reset stats |

---

## File Structure

```
modules/
├── exchange_sync/
│   ├── __init__.py
│   ├── sync_types.py
│   └── sync_engine.py
├── pilot_mode/
│   ├── __init__.py
│   └── pilot_engine.py
├── trade_throttle/
│   ├── __init__.py
│   ├── throttle_types.py
│   └── throttle_engine.py
└── live_execution_routes.py
```

---

## Configuration

### Environment Variables

```
EXECUTION_MODE=APPROVAL
LIVE_EXCHANGES=["BINANCE","BYBIT"]
TRADING_MODE=PILOT
```

### Default Safe Config

```python
default_config = {
    "execution_mode": "APPROVAL",
    "capital_mode": "PILOT",
    "kill_switch": "ON",
    "circuit_breaker": "ON",
    "trade_throttle": "REQUIRED",
}
```

---

## Freeze Rules

System:
- ❌ Cannot trade without Safety Gate
- ❌ Cannot trade without Kill Switch
- ❌ Cannot trade without Circuit Breaker
- ❌ Cannot exceed pilot constraints in PILOT mode
- ❌ Cannot bypass trade throttle

---

## After PHASE 43

The system becomes **LIVE TRADING CAPABLE**.

Remaining phases:
- **PHASE 43.8:** Alpha Decay Engine
- **PHASE 44:** Full Frontend Dashboard
- **PHASE 45:** Meta-Alpha Portfolio Engine

---

**Document Version:** 1.0  
**Last Updated:** 2026-03-14  
**Status:** FROZEN
