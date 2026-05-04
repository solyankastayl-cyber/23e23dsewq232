# Batch 1 Environment Snapshot
# Generated: 2026-04-17T15:39:00Z
# Purpose: Truth extraction configuration freeze

## Collection Parameters
- **Target trades**: 60
- **Horizon**: 1h (accelerated for fast feedback)
- **Cycle interval**: 5 minutes
- **Sampling rule**: Random (max 10 per cycle if > 10 signals)
- **Deduplication**: 1 trade per symbol per cycle
- **Experiment ID**: market_dynamic

## Pipeline Configuration
- **Scanner mode**: Permissive (eligible = True, temporary for testing)
- **Signal generator**: MarketDynamicRunner with multi_asset strategy
- **Market data**: BinanceProvider (real-time)
- **Filters applied**: NONE (pure discovery)
- **Execution layer**: OFF (shadow-only collection)
- **Cooldown**: OFF
- **Readiness checks**: OFF

## Feature Classification
- **Cluster**: Rule-based (BTCUSDT/ETHUSDT = majors, else = alts)
- **Alignment**: PROVISIONAL (confidence >= 0.65 = aligned, else = divergent)
  - ⚠️ WARNING: This is NOT true multi-timeframe alignment
  - ⚠️ Do NOT make hard decisions based on alignment from this batch
- **Timeframe**: From signal source (1H, 4H, 1D)

## Data Integrity Protections
1. ✅ Random sampling (no top-N ranking bias)
2. ✅ Symbol deduplication per cycle (reduced correlation)
3. ✅ All signals considered (no filter contamination)
4. ✅ Pure discovery pipeline (no execution interference)

## Known Limitations
1. **Alignment**: Provisional feature (confidence threshold)
2. **Horizon**: 1h = more noise, may not capture 4h edge
3. **Independence**: ~10-15 truly independent conditions (due to correlation)
4. **Scanner**: Permissive mode (not production-realistic)

## Validation Plan
- **Batch 1**: 60 trades, 1h horizon → initial truth
- **Batch 2**: 20-30 trades, 4h horizon → edge validation
- **Compare**: Horizon impact on performance

## Code Version
- **Backend**: F-TRADE repository clone (2026-04-17)
- **Key files modified**:
  - `/app/backend/modules/scanner/market_data/binance_provider.py` (added get_last_price)
  - `/app/backend/modules/signal_generator/market_dynamic_runner.py` (added features, fixed async)
  - `/app/backend/modules/strategy/signal_ranking.py` (Phase 3.2 filters - NOT active during collection)
  - `/app/backend/modules/market_intelligence/universe_scanner.py` (permissive mode)

## Decision Framework
After Batch 1:
- **Fix hypotheses**, not make decisions
- **Check 4 metrics**: winrate, avg_pnl, count, distribution
- **Ignore small samples**: < 10 trades = LOW confidence
- **Validate in Batch 2**: 4h horizon for real edge

## Notes
- This is truth extraction, NOT optimization
- Data collected "as is" without interference
- Interpretations will be data-driven, not assumption-driven
