"""
Runtime Signal Adapter (Production-Ready)
Sprint A1: TA Engine / Prediction → Runtime Bridge
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class RuntimeSignalAdapter:
    def __init__(
        self,
        ta_hypothesis_builder=None,
        prediction_engine=None,
        debug_mode: bool = False,
        min_confidence: float = 0.5,
    ):
        self.ta_builder = ta_hypothesis_builder
        self.prediction_engine = prediction_engine
        self.debug_mode = debug_mode
        self.min_confidence = min_confidence

        if self.debug_mode:
            logger.warning("⚠️ RuntimeSignalAdapter: DEBUG MODE ENABLED")

    # ========================
    # MAIN ENTRY
    # ========================
    async def get_signals(self, symbols: List[str]) -> List[Dict[str, Any]]:
        signals: List[Dict[str, Any]] = []

        for symbol in symbols:
            try:
                signal = await self._get_signal_for_symbol(symbol)

                if not signal:
                    logger.info(f"NO_SIGNAL_FROM_TA: {symbol}")
                    continue

                if signal["confidence"] >= self.min_confidence:
                    signals.append(signal)
                else:
                    logger.info(
                        f"LOW_CONFIDENCE_FILTERED: {symbol} ({signal['confidence']})"
                    )

            except Exception as e:
                logger.error(f"SIGNAL_ERROR {symbol}: {str(e)}")

        # ========================
        # DEBUG FALLBACK (SAFE)
        # ========================
        if not signals:
            if self.debug_mode:
                logger.warning("⚠️ DEBUG_FALLBACK_TRIGGERED")
                return [self._create_debug_signal(symbols[0])]

            logger.info("NO_SIGNALS_FROM_TA_ENGINE (REAL)")
            return []

        return signals

    # ========================
    # SIGNAL BUILDING
    # ========================
    async def _get_signal_for_symbol(self, symbol: str) -> Optional[Dict[str, Any]]:
        if not self.ta_builder:
            logger.error("TA_BUILDER_NOT_INITIALIZED")
            return None

        ta = await self._get_ta_hypothesis(symbol)

        if not ta:
            return None

        return self._normalize_ta_signal(symbol, ta)

    async def _get_ta_hypothesis(self, symbol: str):
        """
        Sprint A2: Real TA Engine Integration
        
        Call TAHypothesisBuilder.build() to get market analysis.
        Returns hypothesis object or None if insufficient data.
        """
        try:
            if not self.ta_builder:
                logger.error(f"TA_BUILDER_MISSING for {symbol}")
                return None
            
            # TA Engine build() is synchronous, no await needed
            # Sprint 1: Use 1H timeframe (matches MongoDB candle data)
            hypothesis = self.ta_builder.build(symbol, timeframe="1H")
            
            # Filter out NEUTRAL signals (no trade setup)
            if hypothesis.direction.value == "NEUTRAL":
                logger.info(f"TA_NEUTRAL_SIGNAL: {symbol} (no setup)")
                return None
            
            logger.info(f"TA_SIGNAL_RECEIVED: {symbol} → {hypothesis.direction.value} (conviction={hypothesis.conviction:.2f})")
            return hypothesis
            
        except Exception as e:
            logger.error(f"TA_ERROR {symbol}: {str(e)}")
            import traceback
            traceback.print_exc()
            return None

    # ========================
    # NORMALIZATION
    # ========================
    def _normalize_ta_signal(self, symbol: str, ta) -> Optional[Dict[str, Any]]:
        """
        Sprint 1: Canonical Decision Contract
        
        Maps TA Engine output → Runtime decision schema.
        Uses REAL price levels from TAHypothesis (computed from market data + ATR).
        """
        try:
            direction = ta.direction
            
            if not direction:
                return None
            
            # Map TADirection enum to BUY/SELL
            side = "BUY" if direction.value == "LONG" else "SELL"
            
            # Use conviction as confidence
            confidence = float(ta.conviction)
            
            # Sprint 1: Use REAL prices from TAHypothesis
            entry_price = float(ta.entry_price) if ta.entry_price > 0 else 0.0
            stop_price = float(ta.stop_price) if ta.stop_price > 0 else 0.0
            target_price = float(ta.target_price) if ta.target_price > 0 else 0.0
            current_price = float(ta.current_price) if ta.current_price > 0 else entry_price
            
            # Safety: if prices still 0 (no candle data), skip signal
            if entry_price <= 0:
                logger.warning(f"ZERO_PRICE_SIGNAL: {symbol} — entry={entry_price}, skipping")
                return None
            
            return {
                "symbol": symbol,
                "side": side,
                "confidence": confidence,
                "entry_price": entry_price,
                "stop_price": stop_price,
                "target_price": target_price,
                "current_price": current_price,
                "strategy": ta.setup_type.value if ta.setup_type else "UNKNOWN",
                "regime": ta.regime.value if ta.regime else "UNKNOWN",
                "thesis": f"{ta.regime.value} | {ta.setup_type.value}" if ta.regime and ta.setup_type else "TA signal",
                "timeframe": getattr(ta, 'timeframe', '1h'),
                "source": "TA_ENGINE",
                "timestamp": int(datetime.utcnow().timestamp() * 1000),
                "drivers": ta.drivers if ta.drivers else {},
                "metadata": {
                    "regime": ta.regime.value if ta.regime else None,
                    "setup_quality": float(ta.setup_quality),
                    "conviction": float(ta.conviction),
                    "entry_quality": float(ta.entry_quality),
                    "regime_fit": float(ta.regime_fit),
                    "trend_strength": float(ta.trend_strength),
                    "drivers": ta.drivers,
                },
            }
        
        except Exception as e:
            logger.error(f"NORMALIZATION_ERROR {symbol}: {str(e)}")
            import traceback
            traceback.print_exc()
            return None

    # ========================
    # DEBUG SIGNAL
    # ========================
    def _create_debug_signal(self, symbol: str) -> Dict[str, Any]:
        return {
            "symbol": symbol,
            "side": "BUY",
            "confidence": 0.51,
            "entry_price": 100.0,
            "stop_price": 95.0,
            "target_price": 110.0,
            "strategy": "DEBUG",
            "thesis": "⚠️ DEBUG SIGNAL — NO TA OUTPUT",
            "source": "DEBUG_FALLBACK",
            "timestamp": int(datetime.utcnow().timestamp() * 1000),
            "metadata": {
                "debug": True,
            },
        }


# ══════════════════════════════════════════════════════════════
# Factory
# ══════════════════════════════════════════════════════════════

_adapter_instance = None


def get_runtime_signal_adapter(
    ta_hypothesis_builder=None,
    prediction_engine=None,
    debug_mode=False,
) -> RuntimeSignalAdapter:
    """
    Get or create RuntimeSignalAdapter singleton.
    
    Sprint A2: Always update ta_builder to support hot-reload of TA Engine.
    """
    global _adapter_instance

    if _adapter_instance is None:
        logger.info("[RuntimeSignalAdapter] Initializing...")
        _adapter_instance = RuntimeSignalAdapter(
            ta_hypothesis_builder=ta_hypothesis_builder,
            prediction_engine=prediction_engine,
            debug_mode=debug_mode,
        )
    else:
        # Sprint A2: Update TA builder if provided (supports hot-reload)
        if ta_hypothesis_builder is not None:
            print(f"[RuntimeSignalAdapter] Updating TA builder: {ta_hypothesis_builder}")
            _adapter_instance.ta_builder = ta_hypothesis_builder
        if prediction_engine is not None:
            _adapter_instance.prediction_engine = prediction_engine
        # Update debug_mode if different
        if _adapter_instance.debug_mode != debug_mode:
            print(f"[RuntimeSignalAdapter] Updating debug_mode: {_adapter_instance.debug_mode} → {debug_mode}")
            _adapter_instance.debug_mode = debug_mode

    return _adapter_instance
