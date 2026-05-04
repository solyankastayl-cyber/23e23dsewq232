"""
Market Dynamic Signal Ranking
==============================

Phase 2.4: Simple, clean ranking for multi-asset discovery.

NOT complex AI scoring - just clear factor-based ranking.

Formula:
  score = confidence * 0.45 +
          liquidity * 0.20 +
          volatility * 0.15 +
          regime * 0.10 +
          spread * 0.10
"""

import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)


def compute_market_bias(signals: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Compute market bias AND structure from signal distribution.
    
    Structure = hierarchical bias (majors vs alts).
    
    Returns:
        - bias: "bullish" | "bearish" | "mixed" | "neutral"
        - structure: majors_bias, alts_bias, alignment
        - long_ratio, short_ratio, total_signals
    """
    if not signals:
        return {
            "bias": "neutral",
            "structure": {
                "majors_bias": "neutral",
                "alts_bias": "neutral",
                "alignment": "neutral",
            },
            "long_ratio": 0.0,
            "short_ratio": 0.0,
            "total_signals": 0,
        }
    
    # Overall bias
    long_count = sum(1 for s in signals if s.get("side") == "BUY")
    short_count = sum(1 for s in signals if s.get("side") == "SELL")
    total = len(signals)
    
    long_ratio = long_count / total if total > 0 else 0.0
    short_ratio = short_count / total if total > 0 else 0.0
    
    # Classify overall
    if long_ratio >= 0.7:
        bias = "bullish"
    elif short_ratio >= 0.7:
        bias = "bearish"
    elif total == 0:
        bias = "neutral"
    else:
        bias = "mixed"
    
    # Market Structure: majors vs alts
    majors = ["BTCUSDT", "ETHUSDT"]
    
    majors_signals = [s for s in signals if s.get("symbol") in majors]
    alts_signals = [s for s in signals if s.get("symbol") not in majors]
    
    # Majors bias
    if majors_signals:
        majors_long = sum(1 for s in majors_signals if s.get("side") == "BUY")
        majors_total = len(majors_signals)
        
        majors_long_ratio = majors_long / majors_total
        
        if majors_long_ratio >= 0.7:
            majors_bias = "bullish"
        elif majors_long_ratio <= 0.3:
            majors_bias = "bearish"
        else:
            majors_bias = "mixed"
    else:
        majors_bias = "neutral"
    
    # Alts bias
    if alts_signals:
        alts_long = sum(1 for s in alts_signals if s.get("side") == "BUY")
        alts_total = len(alts_signals)
        
        alts_long_ratio = alts_long / alts_total
        
        if alts_long_ratio >= 0.7:
            alts_bias = "bullish"
        elif alts_long_ratio <= 0.3:
            alts_bias = "bearish"
        else:
            alts_bias = "mixed"
    else:
        alts_bias = "neutral"
    
    # Alignment
    if majors_bias == alts_bias and majors_bias != "mixed":
        alignment = "aligned"
    elif majors_bias == "neutral" or alts_bias == "neutral":
        alignment = "incomplete"
    else:
        alignment = "divergent"
    
    return {
        "bias": bias,
        "structure": {
            "majors_bias": majors_bias,
            "alts_bias": alts_bias,
            "alignment": alignment,
        },
        "long_ratio": round(long_ratio, 2),
        "short_ratio": round(short_ratio, 2),
        "total_signals": total,
        "long_count": long_count,
        "short_count": short_count,
    }


def score_signal(
    signal: Dict[str, Any],
    market_bias: str,
    asset_metadata: Optional[Dict[str, Any]] = None,
    calibrator=None  # PHASE 2.7B
) -> tuple[float, Optional[Dict[str, Any]]]:
    """
    Score a single signal.
    
    PHASE 2.7B: Applies calibration adjustment.
    
    Returns:
        (final_score, calibration_metadata)
    """
    # 1. Confidence (45%)
    confidence_score = min(max(signal.get("confidence", 0.5), 0.0), 1.0)
    
    # 2. Liquidity (20%)
    if asset_metadata and "volume_24h" in asset_metadata:
        volume = asset_metadata["volume_24h"]
        if volume >= 5_000_000:
            liquidity_score = 1.0
        elif volume >= 1_000_000:
            liquidity_score = 0.8
        elif volume >= 300_000:
            liquidity_score = 0.6
        else:
            liquidity_score = 0.4
    else:
        liquidity_score = 0.6
    
    # 3. Volatility (15%)
    if asset_metadata and "atr_pct" in asset_metadata:
        atr_pct = asset_metadata["atr_pct"]
        if 0.8 <= atr_pct <= 3.0:
            volatility_score = 1.0
        elif 0.5 <= atr_pct < 0.8:
            volatility_score = 0.7
        elif 3.0 < atr_pct <= 5.0:
            volatility_score = 0.7
        else:
            volatility_score = 0.4
    else:
        volatility_score = 0.6
    
    # 4. Regime (10%)
    signal_side = signal.get("side", "BUY")
    if market_bias == "bullish" and signal_side == "BUY":
        regime_score = 1.0
    elif market_bias == "bullish" and signal_side == "SELL":
        regime_score = 0.3
    elif market_bias == "bearish" and signal_side == "SELL":
        regime_score = 1.0
    elif market_bias == "bearish" and signal_side == "BUY":
        regime_score = 0.3
    else:
        regime_score = 0.6
    
    # 5. Spread (10%)
    if asset_metadata and "spread_bps" in asset_metadata:
        spread_bps = asset_metadata["spread_bps"]
        if spread_bps <= 30:
            spread_score = 1.0
        elif spread_bps <= 75:
            spread_score = 0.8
        elif spread_bps <= 150:
            spread_score = 0.6
        else:
            spread_score = 0.3
    else:
        spread_score = 0.6
    
    # Base score (composite)
    base_score = (
        confidence_score * 0.45 +
        liquidity_score * 0.20 +
        volatility_score * 0.15 +
        regime_score * 0.10 +
        spread_score * 0.10
    )
    
    # PHASE 2.7B: Apply calibration adjustment
    calibration_meta = None
    final_score = base_score
    
    if calibrator:
        try:
            # Get adjustment synchronously (calibrator handles async internally if needed)
            # For now, we'll need to make this work with sync code
            # We'll pass calibration data separately in rank_market_dynamic_signals
            pass
        except Exception as e:
            logger.warning(f"[Ranking] Calibration failed: {e}")
    
    return round(final_score, 4), calibration_meta


async def rank_market_dynamic_signals(
    signals: List[Dict[str, Any]],
    eligible_assets: List[Dict[str, Any]],
    db=None  # PHASE 2.7B: For calibration
) -> tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    Rank signals for market_dynamic experiment.
    
    PHASE 2.7B: Applies score calibration.
    
    Returns:
        (ranked_signals, market_bias_data)
    """
    # Build asset metadata lookup
    asset_lookup = {}
    for asset in eligible_assets:
        key = f"{asset['symbol']}_{asset['timeframe']}"
        asset_lookup[key] = {
            "volume_24h": asset.get("volume_24h_usd", 0),
            "atr_pct": asset.get("atr_pct", 0),
            "spread_bps": asset.get("spread_bps", 0),
        }
    
    # Compute market bias
    market_bias_data = compute_market_bias(signals)
    market_bias = market_bias_data["bias"]
    
    logger.info(
        f"[Ranking] Market bias: {market_bias} "
        f"(long={market_bias_data['long_ratio']}, short={market_bias_data['short_ratio']})"
    )
    
    # PHASE 2.7B: Get calibrator
    calibrator = None
    if db:
        try:
            from modules.strategy.score_calibrator import get_score_calibrator
            calibrator = get_score_calibrator(db)
        except Exception as e:
            logger.warning(f"[Ranking] Calibrator not available: {e}")
    
    # Score each signal
    ranked = []
    for signal in signals:
        key = f"{signal['symbol']}_{signal['timeframe']}"
        asset_metadata = asset_lookup.get(key)
        
        # Calculate base score
        base_score, _ = score_signal(signal, market_bias, asset_metadata)
        
        # PHASE 2.7B: Apply calibration
        adjustment = 0.0
        calibration_meta = None
        
        if calibrator:
            try:
                calib_data = await calibrator.get_adjustment(base_score)
                adjustment = calib_data.get("adjustment", 0.0)
                calibration_meta = calib_data
            except Exception as e:
                logger.warning(f"[Ranking] Calibration failed for {signal['symbol']}: {e}")
        
        final_score = base_score + adjustment
        final_score = round(final_score, 4)
        
        # Add score and metadata to signal
        ranked_signal = {
            **signal,
            "base_score": base_score,
            "score": final_score,
            "calibration": calibration_meta,
            "market_bias": market_bias,
        }
        
        # Add asset metadata
        if asset_metadata:
            ranked_signal["volume_24h"] = asset_metadata["volume_24h"]
            ranked_signal["atr_pct"] = asset_metadata["atr_pct"]
            ranked_signal["spread_bps"] = asset_metadata["spread_bps"]
        
        ranked.append(ranked_signal)
    
    # Sort by final score descending
    ranked.sort(key=lambda s: s["score"], reverse=True)
    
    logger.info(
        f"[Ranking] Ranked {len(ranked)} signals, "
        f"top score: {ranked[0]['score'] if ranked else 0:.4f}"
    )
    
    return ranked, market_bias_data
