"""
Market Regime Detector — F-TRADE v2 Core
========================================

Brain of the system: Determines WHEN strategies should operate.

Philosophy:
  Strategies don't work "always" — they work in specific regimes.
  
Architecture:
  Market Data → Regime Detection → Strategy Routing → Signal Generation
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class RegimeType(Enum):
    """Market regime types."""
    DOWNTREND = "DOWNTREND"
    UPTREND = "UPTREND"
    RANGE = "RANGE"
    UNKNOWN = "UNKNOWN"


@dataclass
class MarketRegime:
    """Market regime state."""
    regime: RegimeType
    confidence: float  # 0.0 - 1.0
    price: float
    ma50: Optional[float]
    ma200: Optional[float]
    context: Dict[str, Any]


class RegimeDetector:
    """
    Detects current market regime.
    
    V1: Simple MA-based detection
    Future: Add volatility, structure, volume
    """
    
    def __init__(self):
        """Initialize regime detector."""
        logger.info("[RegimeDetector] Initialized (v1: MA-based)")
    
    def detect(
        self,
        price: float,
        ma20: Optional[float] = None,
        ma50: Optional[float] = None,
        ma200: Optional[float] = None,
    ) -> MarketRegime:
        """
        Detect market regime.
        
        Logic (V1):
          - DOWNTREND: price < ma50 < ma200
          - UPTREND: price > ma50 > ma200
          - RANGE: everything else
        
        Args:
            price: Current price
            ma20: MA20 (optional, for context)
            ma50: MA50 (required)
            ma200: MA200 (optional, fallback to ma50)
        
        Returns:
            MarketRegime with detected regime
        """
        # Fallback if ma200 not provided
        if ma200 is None:
            ma200 = ma50
        
        # Check sufficient data
        if ma50 is None:
            logger.warning("[RegimeDetector] Insufficient data (no MA50)")
            return MarketRegime(
                regime=RegimeType.UNKNOWN,
                confidence=0.0,
                price=price,
                ma50=ma50,
                ma200=ma200,
                context={"reason": "insufficient_data"}
            )
        
        # Detect regime
        context = {
            "price": price,
            "ma20": ma20,
            "ma50": ma50,
            "ma200": ma200,
        }
        
        # DOWNTREND: price < ma50 AND ma50 < ma200
        if price < ma50 and ma50 < ma200:
            # Calculate confidence based on how far below
            distance_pct = (ma50 - price) / ma50
            confidence = min(1.0, 0.5 + distance_pct * 100)  # More distance = more confident
            
            logger.debug(
                f"[RegimeDetector] DOWNTREND detected "
                f"(price=${price:.2f} < ma50=${ma50:.2f} < ma200=${ma200:.2f}, "
                f"conf={confidence:.2f})"
            )
            
            return MarketRegime(
                regime=RegimeType.DOWNTREND,
                confidence=confidence,
                price=price,
                ma50=ma50,
                ma200=ma200,
                context=context
            )
        
        # UPTREND: price > ma50 AND ma50 > ma200
        if price > ma50 and ma50 > ma200:
            # Calculate confidence
            distance_pct = (price - ma50) / ma50
            confidence = min(1.0, 0.5 + distance_pct * 100)
            
            logger.debug(
                f"[RegimeDetector] UPTREND detected "
                f"(price=${price:.2f} > ma50=${ma50:.2f} > ma200=${ma200:.2f}, "
                f"conf={confidence:.2f})"
            )
            
            return MarketRegime(
                regime=RegimeType.UPTREND,
                confidence=confidence,
                price=price,
                ma50=ma50,
                ma200=ma200,
                context=context
            )
        
        # RANGE: everything else
        logger.debug(
            f"[RegimeDetector] RANGE detected "
            f"(price=${price:.2f}, ma50=${ma50:.2f}, ma200=${ma200:.2f})"
        )
        
        return MarketRegime(
            regime=RegimeType.RANGE,
            confidence=0.7,  # Default confidence for range
            price=price,
            ma50=ma50,
            ma200=ma200,
            context=context
        )


class StrategyRouter:
    """
    Routes to appropriate strategies based on market regime.
    
    This is the KEY: strategies are regime-specific, not universal.
    """
    
    def __init__(self):
        """Initialize strategy router."""
        logger.info("[StrategyRouter] Initialized")
    
    def route(self, regime: MarketRegime) -> List[str]:
        """
        Determine which strategies are allowed in current regime.
        
        Args:
            regime: Current market regime
        
        Returns:
            List of allowed strategy names
        """
        allowed_strategies = []
        
        if regime.regime == RegimeType.DOWNTREND:
            # Only SHORT in downtrend
            allowed_strategies = ["SHORT_TREND"]
            logger.debug(
                f"[StrategyRouter] DOWNTREND → Allowed: {allowed_strategies}"
            )
        
        elif regime.regime == RegimeType.UPTREND:
            # Only LONG strategies in uptrend
            allowed_strategies = ["LONG_PULLBACK", "LONG_BREAKOUT"]
            logger.debug(
                f"[StrategyRouter] UPTREND → Allowed: {allowed_strategies}"
            )
        
        elif regime.regime == RegimeType.RANGE:
            # Range strategies (none for now)
            allowed_strategies = []
            logger.debug(
                f"[StrategyRouter] RANGE → Allowed: {allowed_strategies} (do nothing)"
            )
        
        else:
            # Unknown regime - do nothing
            allowed_strategies = []
            logger.warning(
                "[StrategyRouter] UNKNOWN regime → Allowed: [] (do nothing)"
            )
        
        return allowed_strategies


class SignalValidator:
    """
    Non-blocking observer layer: logs warnings + emits metrics.

    DESIGN (F-TRADE v2 B.1.3):
      The StrategyRouter is the PRIMARY gate — only allowed strategies run.
      The Validator is a SECONDARY observer that records architectural drift
      (e.g. unexpected side in a regime) for later analysis.

      CRITICAL: Validator NEVER drops signals. It always returns True / a
      report dict with `passed=True`. This prevents double-filtering that
      could silently destroy the proven SHORT edge.

    Metrics (persisted to MongoDB `validator_observations` collection if
    a sync pymongo Database is supplied):
      - ts, strategy, regime, symbol, timeframe, side, warn_reason
    """

    def __init__(self, db=None):
        """
        Args:
            db: optional sync pymongo Database for `validator_observations` metrics.
                If None, validator only logs (no persistence).
        """
        self.db = db
        # In-memory counters (survive-of-process observability)
        self.counters: Dict[str, int] = {
            "observed_total": 0,
            "warn_total": 0,
        }
        self.warn_by_reason: Dict[str, int] = {}

        if db is not None:
            try:
                db.validator_observations.create_index([("ts", 1)])
                db.validator_observations.create_index([("warn_reason", 1)])
            except Exception as e:
                logger.warning(f"[SignalValidator] Index create warning: {e}")
        logger.info(f"[SignalValidator] Initialized (observer-only, db={'yes' if db is not None else 'no'})")

    # --------------------------------------------------------------- #
    #  Observer entry point (preferred)
    # --------------------------------------------------------------- #
    def observe(
        self,
        signal: Dict[str, Any],
        regime: "MarketRegime",
        strategy: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Observe a signal AFTER it passed the Router. NEVER blocks.

        Returns:
            {
              "passed": True,              # always True — observer-only
              "warn": bool,                # True if architectural drift detected
              "warn_reason": Optional[str],
              "strategy": str,
              "regime": str,
              "symbol": str,
              "side": str,
            }
        """
        side = signal.get("side")
        symbol = signal.get("symbol", "UNKNOWN")
        timeframe = signal.get("timeframe") or signal.get("tf")
        regime_value = regime.regime.value if regime else "UNKNOWN"

        self.counters["observed_total"] += 1

        warn_reason: Optional[str] = None

        # Architectural drift checks — these SHOULD never trigger if Router
        # is wired correctly. If they do, we log + persist metric, but do
        # NOT drop the signal (trust the Router).
        if regime and regime.regime == RegimeType.DOWNTREND and side == "BUY":
            warn_reason = "BUY_in_DOWNTREND"
        elif regime and regime.regime == RegimeType.UPTREND and side == "SELL":
            warn_reason = "SELL_in_UPTREND"
        elif regime and regime.regime == RegimeType.RANGE:
            warn_reason = f"{side}_in_RANGE"
        elif regime and regime.regime == RegimeType.UNKNOWN:
            warn_reason = f"{side}_in_UNKNOWN_regime"

        if warn_reason:
            self.counters["warn_total"] += 1
            self.warn_by_reason[warn_reason] = self.warn_by_reason.get(warn_reason, 0) + 1
            logger.warning(
                f"[SignalValidator] DRIFT {symbol} {side} regime={regime_value} "
                f"strategy={strategy} reason={warn_reason} "
                f"(observer-only: NOT dropping signal)"
            )
            # Persist metric (best-effort)
            if self.db is not None:
                try:
                    self.db.validator_observations.insert_one({
                        "ts": datetime.now(timezone.utc),
                        "strategy": strategy,
                        "regime": regime_value,
                        "symbol": symbol,
                        "timeframe": timeframe,
                        "side": side,
                        "warn_reason": warn_reason,
                        "regime_confidence": regime.confidence if regime else None,
                    })
                except Exception as e:
                    logger.error(f"[SignalValidator] Metric persist failed: {e}")

        return {
            "passed": True,  # ALWAYS True — observer-only
            "warn": bool(warn_reason),
            "warn_reason": warn_reason,
            "strategy": strategy,
            "regime": regime_value,
            "symbol": symbol,
            "side": side,
        }

    def get_counters(self) -> Dict[str, Any]:
        return {
            **self.counters,
            "by_reason": dict(self.warn_by_reason),
        }

    # --------------------------------------------------------------- #
    #  Legacy interface (kept for backward compatibility)
    # --------------------------------------------------------------- #
    def validate(self, signal: Dict[str, Any], regime: "MarketRegime") -> bool:
        """
        LEGACY: returns True always (observer-only).

        Pre-B.1.3 callers used bool return as a gate; that behavior is
        deprecated. Kept as an alias so old imports don't break.
        """
        report = self.observe(signal, regime)
        return report["passed"]  # always True


# Singleton instances
_regime_detector = None
_strategy_router = None
_signal_validator = None


def get_regime_detector() -> RegimeDetector:
    """Get singleton regime detector."""
    global _regime_detector
    if _regime_detector is None:
        _regime_detector = RegimeDetector()
    return _regime_detector


def get_strategy_router() -> StrategyRouter:
    """Get singleton strategy router."""
    global _strategy_router
    if _strategy_router is None:
        _strategy_router = StrategyRouter()
    return _strategy_router


def get_signal_validator(db=None) -> SignalValidator:
    """Get singleton signal validator.

    First caller can bind a sync pymongo Database for metrics persistence.
    Subsequent calls ignore the db argument.
    """
    global _signal_validator
    if _signal_validator is None:
        _signal_validator = SignalValidator(db=db)
    return _signal_validator
