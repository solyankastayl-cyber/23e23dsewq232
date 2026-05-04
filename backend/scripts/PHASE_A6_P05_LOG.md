# PHASE A.6 (P0.5) - TIMEFRAME-SPECIFIC LOGIC

## Date: 2026-04-19

---

## 🔬 BATCH 3 FINDINGS

### Data:
```
Total: 34 resolved
  BUY:   5 (14.7%) - ALL on 1D timeframe
  SELL: 29 (85.3%) - 1H(15) + 4H(10) + 1D(0)
```

### Performance:
```
1H SELL: 15 trades, 100% wr, +0.78% avg ✅
4H SELL: 10 trades, 100% wr, +0.64% avg ✅
1D BUY:   5 trades,   0% wr, -0.71% avg ❌
```

### Key Insight:
- **ALL 5 BUY = 1D timeframe** (100% concentration)
- **0 SELL on 1D** (trend filter blocked them)
- **Problem localized:** 1D logic, NOT BUY in general

---

## 🎯 ROOT CAUSE: MA PERIODS TOO FAST FOR 1D

### Current MA Config (universal):
```
MA3/MA5/MA20 for ALL timeframes
```

### Problem on 1D:
```
MA3 = 3 days
MA5 = 5 days

→ Too short for daily trend
→ Catches NOISE bounces, not real reversals
→ All 1D BUY signals = false breakouts
```

### Evidence:
```
1D в transition zone:
  - Price briefly crosses MA20 → BUY allowed
  - But overall bearish → BUYs fail
  - MA3/MA5 crossover = meaningless on 1D
```

---

## ✅ P0.5 FIX IMPLEMENTED

### Solution: Block 1D BUY

```python
# PHASE A.6 (P0.5): Timeframe-specific logic
if self.timeframe == "1D" and side == "BUY":
    logger.info(
        f"[TF_FILTER] REJECT {symbol} 1D BUY "
        f"(MA3/MA5 too fast for daily timeframe)"
    )
    return None
```

**File:** `/app/backend/modules/signal_generator/multi_asset_generator.py`

### Changes:
1. Added `timeframe` parameter to `MultiAssetGenerator.__init__`
2. Parse timeframe from `symbol_key` in `get_multi_generator` ("BTCUSDT_1H" → "1H")
3. Block 1D BUY before signal generation

---

## 🎯 WHY THIS IS CORRECT APPROACH

### ❌ Wrong (P1 first):
```python
if side == "BUY" and confidence < 0.65:
    return None
```
- This is **suppression** (blocks symptom)
- Doesn't fix root cause
- 1D still generates garbage

### ✅ Right (P0.5 first):
```python
if timeframe == "1D" and side == "BUY":
    return None
```
- This is **surgical fix** (removes bad source)
- Targets exact problem
- Allows testing if BUY works on 1H/4H

---

## 📊 EXPECTED OUTCOME (BATCH 4 - MINI)

### If P0.5 works:
```
BUY on 1H/4H:  Should appear
BUY on 1D:     Blocked (0 signals)
SELL on all:   Unchanged

BUY winrate:   Should be > 30% (on 1H/4H)
```

### Target:
```
20-30 resolved trades
Focus: Did BUY on 1H/4H recover?
```

---

## 🚀 NEXT STEPS AFTER BATCH 4

### Scenario A: BUY recovers on 1H/4H (e.g., 35-50% wr)
```
→ P0.5 SUCCESS
→ Next: P1 (asymmetric confidence if needed)
→ Long-term: Different MA periods per TF
```

### Scenario B: BUY still fails on 1H/4H
```
→ P0.5 helped but insufficient
→ Need deeper investigation (entry timing? stop distance?)
```

---

## 📋 COMPARISON

```
P0 (MA20 trend filter):
  ✅ Blocks counter-trend entries
  ✅ Reduced noise 64%
  ❌ Didn't solve 1D BUY problem

P0.5 (1D BUY block):
  ✅ Removes specific bad source
  ✅ Surgical, not blanket suppression
  ✅ Allows isolated testing

P1 (asymmetric confidence):
  ⏳ For AFTER P0.5 validation
  ⏳ Applies ONLY if 1H/4H BUY needs tightening
```

---

## ✅ STATUS

- ✅ P0: MA20 trend filter (DONE)
- ✅ P0.5: 1D BUY block (DONE)
- ⏳ Batch 4: Mini validation run (20-30 trades)
- ⏳ P1: Asymmetric confidence (if needed after Batch 4)

**Mode:** Surgical repair, not blanket suppression
