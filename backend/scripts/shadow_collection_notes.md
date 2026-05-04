# Shadow Collection Data Quality Notes

## Known Limitations (Phase A.3 - Batch 1)

### 1. Alignment Feature - PROVISIONAL
- **Current**: `alignment = "aligned" if confidence >= 0.65 else "divergent"`
- **Issue**: This is a confidence threshold, NOT true multi-timeframe alignment
- **Risk**: May show false alignment vs divergent differences
- **Action**: Do NOT make hard decisions based on alignment from this batch
- **Fix**: Implement proper multi-timeframe alignment detection in future

### 2. Horizon = 1h (Accelerated)
- **Purpose**: Fast feedback for initial truth extraction
- **Limitation**: 
  - 1h = more noise
  - 4h edge may not materialize
  - Trends don't fully develop
- **Action**: After batch 1, run batch 2 with 4h horizon (20-30 trades) for validation

### 3. Sample Size & Independence
- **Target**: 60 trades
- **Real independence**: ~10-15 unique market conditions (due to correlation)
- **Mitigation**: Deduplication (1 trade per symbol per cycle)

## Data Integrity Protections

### Applied Corrections:
1. ✅ Random sampling (no top-N bias)
2. ✅ 1 trade per symbol per cycle (reduced correlation)
3. ✅ ALL signals saved (no filter contamination)
4. ✅ Pure discovery pipeline (no execution layer)

### Still Required:
- 🔜 Batch 2 with 4h horizon for edge validation
- 🔜 Proper alignment feature implementation

## Decision Framework

### After Batch 1 (60 trades, 1h horizon):
- Use for: cluster quality, basic timeframe comparison
- Don't use for: final alignment decisions, long-term edge validation

### After Batch 2 (20-30 trades, 4h horizon):
- Validate: 4h edge strength, trend capture ability
- Compare: 1h vs 4h horizon impact

## Notes for Analysis
When reviewing `/api/debug/features-from-shadow`:
- Cluster breakdown: RELIABLE
- Timeframe breakdown: MODERATELY RELIABLE (validate with 4h batch)
- Alignment breakdown: PROVISIONAL (don't trust fully)
