"""Market Universe Scanner

Сканирует universe активов (BTC, ETH, SOL и т.д.) на всех таймфреймах.
Отбирает eligible активы по критериям volume/ATR/spread.
"""

import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone

from modules.scanner.market_data.binance_provider import get_market_data_provider


# Universe definition
UNIVERSE_SYMBOLS = [
    "BTCUSDT",
    "ETHUSDT",
    "SOLUSDT",
    "BNBUSDT",
    "XRPUSDT",
    "DOGEUSDT",
    "ADAUSDT",
    "AVAXUSDT",
    "LINKUSDT",
]

TIMEFRAMES = ["1H", "4H", "1D"]

# Eligibility criteria (RELAXED для реального рынка)
MIN_VOLUME_24H_USD = 100_000  # $100K (relaxed)
MIN_ATR_PCT = 0.005  # 0.5% (relaxed)
MAX_SPREAD_BPS = 500  # 5% (relaxed, это оценка из свечей, не реальный spread)


def calculate_volume_24h(candles: List[Dict]) -> float:
    """Calculate approximate 24h volume in USD.
    
    NOTE: This is an APPROXIMATION based on recent candles.
    For 1H: last 24 candles ≈ 24h
    For 4H: last 6 candles ≈ 24h
    For 1D: last candle ≈ 1 day
    """
    if not candles:
        return 0.0
    
    # Get approximate 24h window
    if len(candles) >= 24:
        recent = candles[-24:]  # 1H timeframe
    elif len(candles) >= 6:
        recent = candles[-6:]  # 4H timeframe
    else:
        recent = candles[-1:]  # 1D timeframe
    
    return sum(c["volume"] * c["close"] for c in recent)


def calculate_atr_pct(candles: List[Dict], period: int = 14) -> float:
    """Calculate ATR as % of close price."""
    if len(candles) < period + 1:
        return 0.0
    
    true_ranges = []
    for i in range(1, len(candles)):
        high = candles[i]["high"]
        low = candles[i]["low"]
        prev_close = candles[i - 1]["close"]
        
        tr = max(
            high - low,
            abs(high - prev_close),
            abs(low - prev_close),
        )
        true_ranges.append(tr)
    
    if len(true_ranges) < period:
        return 0.0
    
    atr = sum(true_ranges[-period:]) / period
    current_close = candles[-1]["close"]
    
    return (atr / current_close) if current_close > 0 else 0.0


def calculate_spread_bps(candles: List[Dict]) -> float:
    """Estimate spread in basis points from recent candles."""
    if not candles:
        return 0.0
    
    # Approximation: среднее (high - low) / close
    recent = candles[-10:]
    spreads = [(c["high"] - c["low"]) / c["close"] * 10000 for c in recent if c["close"] > 0]
    
    return sum(spreads) / len(spreads) if spreads else 0.0


async def scan_market_universe(
    symbols: Optional[List[str]] = None,
    timeframes: Optional[List[str]] = None,
) -> List[Dict[str, Any]]:
    """Scan universe symbols on all timeframes.

    Args:
        symbols:    Optional override for UNIVERSE_SYMBOLS (e.g. expanded
                    list for discovery_matrix_live). Defaults to the
                    module-level UNIVERSE_SYMBOLS used by Phase C.
        timeframes: Optional override for TIMEFRAMES. Defaults to module-level.

    Returns:
        List of universe snapshots with eligibility flags.
    """
    provider = get_market_data_provider()
    results = []

    scan_symbols = list(symbols) if symbols else UNIVERSE_SYMBOLS
    scan_tfs = list(timeframes) if timeframes else TIMEFRAMES

    print(f"[UniverseScanner] Starting scan: {len(scan_symbols)} symbols x {len(scan_tfs)} timeframes = {len(scan_symbols) * len(scan_tfs)} total")

    for symbol in scan_symbols:
        for tf in scan_tfs:
            try:
                # Fetch candles (sync call, wrapped in executor)
                candles = await asyncio.to_thread(
                    provider.get_candles,
                    symbol,
                    tf,
                    limit=200,
                )
                
                if not candles:
                    print(f"[UniverseScanner] {symbol} {tf}: No candles received")
                    continue
                
                # Metrics
                volume_24h = calculate_volume_24h(candles)
                atr_pct = calculate_atr_pct(candles)
                spread_bps = calculate_spread_bps(candles)
                
                # PHASE 3.2: TEMPORARILY RELAXED FILTERS FOR TESTING
                # Accept ALL assets with any data to test filtering logic
                eligible = True  # Force eligible for testing
                
                # Original eligibility (commented for now)
                # eligible = (
                #     volume_24h >= MIN_VOLUME_24H_USD
                #     and atr_pct >= MIN_ATR_PCT
                #     and spread_bps <= MAX_SPREAD_BPS
                # )
                
                reason = None
                if not eligible:
                    if volume_24h < MIN_VOLUME_24H_USD:
                        reason = f"volume_low_{int(volume_24h)}"
                    elif atr_pct < MIN_ATR_PCT:
                        reason = f"atr_low_{atr_pct:.3f}"
                    elif spread_bps > MAX_SPREAD_BPS:
                        reason = f"spread_high_{spread_bps:.1f}bps"
                
                results.append({
                    "symbol": symbol,
                    "timeframe": tf,
                    "volume_24h_usd": round(volume_24h, 2),
                    "atr_pct": round(atr_pct, 4),
                    "spread_bps": round(spread_bps, 2),
                    "eligible": eligible,
                    "reason": reason,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                })
            
            except Exception as e:
                print(f"[UniverseScanner] Error scanning {symbol} {tf}: {e}")
                import traceback
                traceback.print_exc()
                continue
    
    eligible_count = sum(1 for r in results if r["eligible"])
    print(f"[UniverseScanner] Scan complete: {len(results)} total, {eligible_count} eligible")
    
    # Debug: Show first few results
    if results:
        print(f"[UniverseScanner] Sample: {results[0]}")
    
    return results
