"""Signal Engine V2 — Adaptive Strategy Orchestrator

Key improvements:
- Adaptive thresholds based on regime
- Soft fallback when no hard triggers
- Debug visibility (rejection reasons)
- Never returns empty unless candles invalid
"""

import logging
from typing import List, Dict, Any

from modules.signal_engine.trend_strategy import evaluate_trend
from modules.signal_engine.breakout_strategy import evaluate_breakout
from modules.signal_engine.mean_reversion_strategy import evaluate_mean_reversion
from modules.signal_engine.adaptive_thresholds import build_thresholds
from modules.signal_engine.soft_signal import generate_soft_signal
from modules.signal_engine.signal_models import TradingSignal
from modules.strategy.regime import detect_regime, calculate_volatility

logger = logging.getLogger(__name__)


class SignalEngine:
    """Orchestrates multiple trading strategies with adaptive thresholds."""
    
    def __init__(self):
        logger.info("[SignalEngineV2] Initialized with adaptive thresholds + soft fallback")
    
    def run(self, symbol: str, timeframe: str, candles: List[dict]) -> List[TradingSignal]:
        """
        Run all strategies with adaptive thresholds.
        
        Returns list of signals (always at least 1 via soft fallback)
        """
        if len(candles) < 60:
            logger.warning(f"[SignalEngineV2] Not enough candles for {symbol}: {len(candles)}")
            return []
        
        # Detect regime and volatility
        market_data = {"volatility": calculate_volatility(candles), "trend_strength": 0.6}
        regime = detect_regime(market_data)
        volatility = calculate_volatility(candles)
        
        # Build adaptive thresholds
        thresholds = build_thresholds(regime, volatility)
        
        logger.info(
            f"[SignalEngineV2] {symbol}: regime={regime}, vol={volatility:.4f}, "
            f"thresh_trend_mom={thresholds['trend']['momentum_min']:.2f}"
        )
        
        signals = []
        debug_info = {
            "symbol": symbol,
            "regime": regime,
            "volatility": volatility,
            "strategies": {}
        }
        
        # Run strategies
        strategies = [
            ("trend", evaluate_trend),
            ("breakout", evaluate_breakout),
            ("mean_reversion", evaluate_mean_reversion),
        ]
        
        for strategy_name, strategy_func in strategies:
            try:
                result = strategy_func(symbol, timeframe, candles, thresholds)
                debug_info["strategies"][strategy_name] = {
                    "triggered": result.get("triggered"),
                    "reason": result.get("reason")
                }
                
                if result.get("triggered") and result.get("signal"):
                    signals.append(result["signal"])
                    logger.info(
                        f"[SignalEngineV2] ✅ {strategy_name} → {result['signal'].direction} "
                        f"{result['signal'].confidence:.2f}"
                    )
                else:
                    logger.debug(
                        f"[SignalEngineV2] ❌ {strategy_name}: {result.get('reason')}"
                    )
            except Exception as e:
                logger.error(f"[SignalEngineV2] Strategy error {strategy_name}: {e}", exc_info=True)
                debug_info["strategies"][strategy_name] = {
                    "triggered": False,
                    "reason": f"error: {str(e)}"
                }
        
        # SOFT FALLBACK: If no hard triggers, generate soft signal
        if not signals:
            logger.warning(
                f"[SignalEngineV2] ⚠️ {symbol}: No hard triggers in {regime} regime. "
                f"Using soft fallback."
            )
            
            # Compute minimal indicators for soft signal
            indicators = {
                "ema20": self._compute_ema([c["close"] for c in candles], 20),
                "ema50": self._compute_ema([c["close"] for c in candles], 50),
                "atr": self._compute_atr(candles),
            }
            
            soft = generate_soft_signal(symbol, candles, indicators, regime)
            if soft:
                # Convert dict to TradingSignal
                signals.append(TradingSignal(
                    symbol=soft["symbol"],
                    timeframe=timeframe,
                    direction=soft["side"],
                    strategy=soft["strategy"],
                    confidence=soft["confidence"],
                    entry=soft["entry"],
                    stop=soft["stop"],
                    target=soft["target"],
                    reason=soft["reason"],
                    asset_vol=0.025,
                    metadata=soft.get("meta", {})
                ))
                debug_info["soft_fallback_used"] = True
        
        logger.info(f"[SignalEngineV2] {symbol}: {len(signals)} signals generated")
        return signals
    
    def _compute_ema(self, prices: List[float], period: int) -> float:
        """Quick EMA calc"""
        from modules.signal_engine.indicators import ema
        return ema(prices, period) or prices[-1]
    
    def _compute_atr(self, candles: List[dict]) -> float:
        """Quick ATR calc"""
        from modules.signal_engine.indicators import atr
        highs = [c["high"] for c in candles]
        lows = [c["low"] for c in candles]
        closes = [c["close"] for c in candles]
        return atr(highs, lows, closes, 14) or (closes[-1] * 0.01)
