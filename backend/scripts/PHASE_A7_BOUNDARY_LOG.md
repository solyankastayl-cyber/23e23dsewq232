# PHASE A.7 - BOUNDARY CALIBRATION

## Date: 2026-04-19

---

## 🔬 BATCH 4 FORENSIC FINDINGS

### Data:
```
Total: 18 resolved
  BUY:  3 (all XRPUSDT, all 1H, all $1.43-1.44)
  SELL: 11 (0% winrate)
```

### Forensic Analysis:
```
3 BUY ≠ 3 independent signals
3 BUY = 1 pattern × 3 repetitions

Pattern:
  - XRPUSDT micro bounce
  - Confidence 0.50 (weakest)
  - +0.3-0.6% (noise, not trend)
  
→ 100% winrate = ZERO information
→ System caught one noise moment, not "fixed"
```

---

## 🎯 REAL DIAGNOSIS

### ❌ NOT:
```
"BUY fixed" (it didn't fix)
"SELL broken" (it didn't break)
```

### ✅ ACTUALLY:
```
System became TOO CONSERVATIVE

P0 + P0.5:
  ✅ Removed counter-trend
  ✅ Removed 1D BUY
  ❌ Now almost DOESN'T TRADE
  
Effect: Killed entries, not just noise
```

---

## 🧠 KEY INSIGHT: SELL 0% IS THE KEY

```
Batch 2-3: Market ↓, SELL = 98-100%
Batch 4:   Market reversed/sideways, SELL = 0%

MA20 filter now BLOCKS SELL entries
→ System on wrong side of parameter boundary
```

---

## 🎯 BOUNDARY STATE

```
Batch 2: Too aggressive (noise + garbage)
Batch 3: Better, but BUY breaks
Batch 4: Too conservative (almost nothing)

→ Found SYSTEM BOUNDARY
   between: noisy ←→ too few signals
```

---

## 🔧 FIXES IMPLEMENTED (NOT P1!)

### FIX 1: Soften MA20 Filter (0.5% buffer)

**Problem:** Hard line at MA20 kills entries in transition zones

```python
# BEFORE (too strict):
if price > trend_ma: BUY ok
if price < trend_ma: SELL ok

# AFTER (with buffer):
buffer = 0.005  # 0.5%

if price > trend_ma * (1 - buffer): BUY ok
if price < trend_ma * (1 + buffer): SELL ok
```

**Effect:**
- Allows entries NEAR trend (gray zone)
- Still blocks hard counter-trend
- SELL can enter in transitional market

### FIX 2: Signal Strength Filter (0.1% min)

**Problem:** Weak MA crossovers = micro bounces (XRPUSDT 0.50 conf)

```python
# NEW check:
ma_strength = abs(short_ma - long_ma) / long_ma

if ma_strength < 0.001:  # 0.1%
    return None  # Too weak
```

**Effect:**
- Blocks micro bounces
- Requires meaningful MA separation
- Raises quality threshold

---

## 🎯 WHY THESE FIXES ARE CORRECT

### FIX 1 (buffer) solves:
```
SELL death in Batch 4:
  - Market sideways/transitional
  - Price slightly above MA20 → SELL blocked
  - Buffer allows "gray zone" entries
```

### FIX 2 (strength) solves:
```
Micro bounce noise:
  - MA3/MA5 barely cross
  - Confidence 0.50 (minimum)
  - Strength filter removes this
```

**This is NOT P1 (asymmetry).** This is **signal quality enforcement.**

---

## 📊 EXPECTED OUTCOME (NEXT BATCH)

```
Signal count: More than 18, less than 95
  - Not over-filtered (Batch 4)
  - Not too noisy (Batch 2)
  
BUY:
  - Should appear on multiple symbols
  - Strength > 0.1%
  - Not just one micro moment
  
SELL:
  - Should recover (buffer helps)
  - Quality > weak crossovers
```

---

## 🚀 NEXT STEPS

1. ✅ FIX 1: MA20 buffer (0.5%)
2. ✅ FIX 2: Signal strength (0.1%)
3. ⏳ Batch 5: 20-30 trades validation
4. ⏳ Then: Assess if P1 (asymmetry) needed

---

## 🧠 KEY LEARNING

```
Forensic > Statistics:
  - 3 trades looked like data
  - Forensic revealed: 1 pattern × 3
  
Boundary found:
  - Too aggressive → Too conservative
  - Need to calibrate, not amplify
  
Fix type:
  - NOT suppression (P1)
  - Signal quality + boundary tuning
```

---

## ✅ STATUS

- ✅ P0: MA20 trend filter
- ✅ P0.5: 1D BUY block
- ✅ A.7: Boundary calibration (buffer + strength)
- ⏳ Batch 5: Validate calibration

**Mode:** Boundary tuning, not feature addition
