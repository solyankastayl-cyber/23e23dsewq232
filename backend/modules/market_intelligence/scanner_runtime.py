"""Scanner Runtime — Orchestrator

Объединяет Universe Scanner + Indicator Engine + Signal Engine.
Возвращает market opportunities (сигналы готовые к исполнению).
"""

import asyncio
from typing import List, Dict, Any
from datetime import datetime, timezone

from modules.scanner.market_data.binance_provider import get_market_data_provider
from .universe_scanner import scan_market_universe
from .indicator_engine import compute_indicators
from .signal_engine import generate_signal


# In-memory cache для последнего скана
_last_scan_result: List[Dict[str, Any]] = []
_last_scan_timestamp: str = ""


async def run_scanner() -> List[Dict[str, Any]]:
    """Run full scanner pipeline.
    
    Steps:
    1. Scan universe (filter eligible assets)
    2. Fetch candles for eligible
    3. Compute indicators
    4. Generate signals
    
    Returns:
        List of market opportunities (signals).
    """
    global _last_scan_result, _last_scan_timestamp
    
    print("[ScannerRuntime] Starting market scan...")
    
    # Step 1: Scan universe
    universe_snapshots = await scan_market_universe()
    eligible = [s for s in universe_snapshots if s["eligible"]]
    
    print(f"[ScannerRuntime] Universe: {len(universe_snapshots)} pairs, {len(eligible)} eligible")
    
    if not eligible:
        print("[ScannerRuntime] No eligible pairs found")
        _last_scan_result = []
        _last_scan_timestamp = datetime.now(timezone.utc).isoformat()
        return []
    
    # Step 2-4: Process eligible pairs
    provider = get_market_data_provider()
    signals = []
    
    for snapshot in eligible:
        symbol = snapshot["symbol"]
        tf = snapshot["timeframe"]
        
        try:
            # Fetch candles
            candles = await asyncio.to_thread(
                provider.get_candles,
                symbol,
                tf,
                limit=200,
            )
            
            if not candles:
                continue
            
            # Compute indicators
            indicators = compute_indicators(candles)
            
            # Generate signal
            signal = generate_signal(indicators, candles)
            
            if signal:
                signals.append({
                    "symbol": symbol,
                    "timeframe": tf,
                    "direction": signal["direction"],
                    "confidence": signal["confidence"],
                    "strategy": signal["strategy"],
                    "entry_zone": signal["entry_zone"],
                    "stop": signal["stop"],
                    "target": signal["target"],
                    "reasoning": signal["reasoning"],
                    "current_price": indicators["current_price"],
                    "rsi": indicators["rsi"],
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                })
                print(f"[ScannerRuntime] ✅ Signal: {symbol} {tf} {signal['direction']} {signal['strategy']} conf={signal['confidence']}")
        
        except Exception as e:
            print(f"[ScannerRuntime] Error processing {symbol} {tf}: {e}")
            continue
    
    # Sort by confidence descending
    signals.sort(key=lambda s: s["confidence"], reverse=True)
    
    print(f"[ScannerRuntime] Generated {len(signals)} signals")
    
    # Cache result
    _last_scan_result = signals
    _last_scan_timestamp = datetime.now(timezone.utc).isoformat()
    
    return signals


async def get_market_opportunities() -> Dict[str, Any]:
    """Get market opportunities (cached or fresh scan).
    
    Returns:
        {
            "opportunities": [...],
            "total": int,
            "last_scan": iso timestamp,
        }
    """
    global _last_scan_result, _last_scan_timestamp
    
    # If cache is empty or stale (>5 min), run fresh scan
    if not _last_scan_result:
        await run_scanner()
    
    return {
        "opportunities": _last_scan_result,
        "total": len(_last_scan_result),
        "last_scan": _last_scan_timestamp,
    }
