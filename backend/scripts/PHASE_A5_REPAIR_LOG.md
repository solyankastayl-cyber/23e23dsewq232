# PHASE A.5 - GENERATOR REPAIR LOG

## Date: 2026-04-18

---

## ✅ P0 FIX IMPLEMENTED: TREND FILTER (MA20)

### Problem Identified:
- **Root cause:** Blind MA crossover without trend context
- **Symptom:** BUY winrate = 0% (0/29) in Batch 2
- **Diagnosis:** Generator creates BUY on every small bounce, even in strong downtrends

### Fix Applied:
```python
# BEFORE (Batch 2):
if short_ma > long_ma:
    side = "BUY"
else:
    side = "SELL"

# AFTER (Phase A.5):
if short_ma > long_ma and price > trend_ma:
    side = "BUY"
elif short_ma < long_ma and price < trend_ma:
    side = "SELL"
else:
    return None  # Reject signal
```

### Implementation Details:
- **File:** `/app/backend/modules/signal_generator/multi_asset_generator.py`
- **Change:** Added `trend_period=20` parameter (MA20)
- **Logic:** 
  - BUY only if price > MA20 (above trend baseline)
  - SELL only if price < MA20 (below trend baseline)
  - Signals against trend → rejected

### Sanity Test Results:
```
✅ PASS: Falling knife block (bearish bounce → no BUY)
✅ PASS: Bullish pullback (valid BUY allowed)
✅ PASS: Bearish continuation (valid SELL allowed)
✅ PASS: Bullish rally (no SELL against trend)

Result: 4/4 tests passed
```

---

## 🚫 WHAT WAS NOT CHANGED

**Deliberately NOT implemented (to isolate P0 fix):**
- ❌ Asymmetric confidence thresholds (P1)
- ❌ Longer MA periods (P2)
- ❌ Regime detection (P3)
- ❌ Ranking filters
- ❌ Any other modifications

**Rationale:** Single controlled repair to measure isolated effect.

---

## 📊 EXPECTED OUTCOMES IN BATCH 3

### Primary Goal:
**Verify that LONG side is no longer structurally broken**

### Success Criteria:
```
Minimum acceptable:
  BUY winrate > 25-35% (NOT 0%)
  
Ideal:
  BUY winrate > 40%
  SELL remains functional
  Overall avg PnL > 0
```

### Expected Changes:
```
Signal generation:
  - Fewer total signals (trend filter rejects ~30-40%)
  - More "None" returns (counter-trend rejected)
  - BUY/SELL ratio closer to 1:1 (not 1:2)

Performance:
  - Overall winrate may drop from 66% → 52-58% (NORMAL)
  - BUY should no longer be deterministic loser
  - System becomes directional, not blind
```

---

## 🔬 BATCH 3 CONFIGURATION

```yaml
Experiment ID:    batch3_with_trend_filter
Horizon:          4h
Interval:         15 min
Target:           40-60 resolved
Max per cycle:    5-7
Mode:             PURE DISCOVERY (no filters)
Generator:        multi_asset_ma WITH trend_filter=MA20
```

### What We're Testing:
```
NOT: "Is there an edge?"
YES: "Did trend filter fix LONG side?"
```

### Key Metrics:
1. **BUY winrate** (must be > 25%)
2. **SELL stability** (should remain functional)
3. **Signal rejection rate** (expect ~30-40% rejected)
4. **BUY/SELL distribution** (should be more balanced)

---

## 🎯 POST-BATCH 3 DECISION TREE

### Scenario A: BUY Recovered
```
BUY wr > 30%, SELL stable, avg pnl > 0
→ SUCCESS
→ Next: Consider P1 (asymmetric thresholds) if needed
```

### Scenario B: BUY Still Broken
```
BUY wr < 15%, still failing
→ P0 insufficient
→ Next: Implement P1 (asymmetric confidence) immediately
```

### Scenario C: High Noise
```
BUY alive but too many false signals
→ P0 working, need refinement
→ Next: P2 (lengthen MA periods to 5/10 or 10/20)
```

### Scenario D: SELL Degraded
```
SELL wr drops significantly
→ Trend filter too restrictive
→ Review: Maybe MA20 → MA10, or adjust logic
```

---

## 📝 NOTES

- **Batch 2 data preserved:** experiment_id=`batch2_4h` (89 resolved, untouched)
- **Batch 3 will use:** experiment_id=`batch3_with_trend_filter`
- **No mixing:** Clean separation for before/after comparison
- **Generator change:** This is the ONLY modification between Batch 2 and Batch 3

---

## ✅ STATUS: READY FOR BATCH 3

**Checklist:**
- ✅ P0 fix implemented (trend filter)
- ✅ Sanity test passed (4/4)
- ✅ No contamination (only one change)
- ✅ Clear success criteria defined
- ✅ Decision tree prepared

**Next action:** Launch Batch 3 collection with updated generator.
