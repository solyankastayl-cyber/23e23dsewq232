"""
Multi-Asset Signal Generator — F-TRADE v2 Stateful Interface
============================================================

Phase B.1.2: Refactored to stateful quant engine interface.

Strict separation of concerns:
  1. warmup(candles)  — load history, set last_candle_ts, NO SIGNALS
  2. update(candle)   — add ONE candle with dedup, returns bool
  3. maybe_generate() — pure signal calculation from state, NO MUTATION
  4. to_state() / from_state(state) — persistence contract

Strategy (UNCHANGED — frozen after Batch 6 validation):
  - Fast MA crossover (MA3 vs MA5) with MA20 trend filter
  - SHORT-only: BUY generation frozen (Phase A.8)
  - Edge: 83.7% WR in DOWNTREND regime (Batch 6 manual resolution)

Architecture:
  Generator layer = pure calculator (stateful, deterministic)
  State layer     = GeneratorStateManager owns persistence
  Routing layer   = MarketRegime + StrategyRouter decide WHEN to run
  Validator layer = observer-only (metrics, no blocking)
"""

import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


# Keep tail of prices in state (covers all indicator windows with margin)
_STATE_PRICE_TAIL = 250


class MultiAssetGenerator:
    """
    Stateful SHORT-only MA-crossover signal generator.

    Contract (F-TRADE v2):
      - warmup(candles): load history WITHOUT generating signals
      - update(candle): append one candle, dedup by candle['time']
      - maybe_generate(): compute signal from current state, no mutation
      - to_state()/from_state(state): serialize/restore across process restart

    The underlying MA math and filters are UNCHANGED from Phase A.8:
      - MA3 / MA5 / MA20 trend filter with 0.5% buffer
      - Weak-signal rejection (<0.1% MA spread)
      - 1D BUY rejection
      - HARD BUY freeze (Phase A.8 — SHORT-only validation)
    """

    # --------------------------------------------------------------- #
    #  Construction
    # --------------------------------------------------------------- #
    def __init__(
        self,
        symbol: str,
        short_period: int = 3,
        long_period: int = 5,
        trend_period: int = 20,
        timeframe: Optional[str] = None,
    ):
        """
        Args:
            symbol: Trading pair (e.g., BTCUSDT)
            short_period: Short MA (default 3) — FROZEN
            long_period: Long MA (default 5) — FROZEN
            trend_period: Trend filter MA (default 20) — FROZEN
            timeframe: Timeframe string (1H / 4H / 1D ...) — for TF-specific filters
        """
        self.symbol = symbol
        self.short_period = short_period
        self.long_period = long_period
        self.trend_period = trend_period
        self.timeframe = timeframe

        # ── State (serializable) ────────────────────────────────────
        self.prices: List[float] = []
        self.last_candle_ts: Optional[int] = None  # seconds since epoch
        self.is_warm: bool = False

        logger.info(
            f"[MultiAsset] Init {symbol} tf={timeframe} "
            f"(MA{short_period}/{long_period}, trend=MA{trend_period})"
        )

    # --------------------------------------------------------------- #
    #  Public stateful interface (F-TRADE v2)
    # --------------------------------------------------------------- #
    def warmup(self, candles: List[Dict[str, Any]]) -> None:
        """
        Load historical candles without producing any signals.

        - Replaces existing prices list (idempotent warmup).
        - Sets last_candle_ts to timestamp of last candle.
        - Flags is_warm=True once we have ≥ trend_period prices.

        Args:
            candles: list of dicts with at least {'time', 'close'}.
                     `time` is seconds-since-epoch (BinanceProvider format).
        """
        if not candles:
            logger.warning(f"[MultiAsset] warmup({self.symbol}) called with empty candles")
            return

        # Clean idempotent reload
        self.prices = [float(c["close"]) for c in candles]
        # Keep only tail to bound memory/state size
        if len(self.prices) > _STATE_PRICE_TAIL:
            self.prices = self.prices[-_STATE_PRICE_TAIL:]

        # Use `time` from BinanceProvider (seconds). Fallback to `timestamp` for legacy callers.
        last_candle = candles[-1]
        self.last_candle_ts = last_candle.get("time") or last_candle.get("timestamp")

        self.is_warm = len(self.prices) >= self.trend_period

        logger.info(
            f"[MultiAsset] warmup {self.symbol} tf={self.timeframe}: "
            f"{len(self.prices)} prices, last_ts={self.last_candle_ts}, warm={self.is_warm}"
        )

    def update(self, candle: Dict[str, Any]) -> bool:
        """
        Append one candle to state. Deduplicate by candle['time'].

        Returns:
            True  — new candle was accepted (state changed).
            False — duplicate candle (state unchanged).
        """
        ts = candle.get("time") or candle.get("timestamp")

        if ts is None:
            # Defensive: no timestamp means we can't dedup safely. Accept but warn.
            logger.warning(
                f"[MultiAsset] update({self.symbol}) candle without time/timestamp — accepted w/o dedup"
            )
        elif self.last_candle_ts is not None and ts <= self.last_candle_ts:
            # Same or older candle — skip (dedup)
            logger.debug(
                f"[MultiAsset] update {self.symbol} {self.timeframe} dup skip "
                f"(ts={ts}, last={self.last_candle_ts})"
            )
            return False

        close_price = float(candle["close"])
        self.prices.append(close_price)
        if len(self.prices) > _STATE_PRICE_TAIL:
            self.prices = self.prices[-_STATE_PRICE_TAIL:]
        if ts is not None:
            self.last_candle_ts = ts

        # Warmth check can only flip True → never False in update()
        if not self.is_warm and len(self.prices) >= self.trend_period:
            self.is_warm = True

        return True

    def maybe_generate(self) -> Optional[Dict[str, Any]]:
        """
        Compute signal from current state. NO mutation.

        Returns:
            Signal dict or None.
        """
        if not self.is_warm:
            logger.debug(
                f"[MultiAsset] maybe_generate {self.symbol}: cold "
                f"({len(self.prices)}/{self.trend_period})"
            )
            return None

        if len(self.prices) < self.trend_period:
            # Double-check (state could have been restored with short tail)
            return None

        current_price = self.prices[-1]
        short_ma = self._ma(self.short_period)
        long_ma = self._ma(self.long_period)
        trend_ma = self._ma(self.trend_period)

        if short_ma is None or long_ma is None or trend_ma is None:
            return None

        # ────────────────────────────────────────────────────────────
        # PHASE A.5 + A.7: Trend filter with 0.5% buffer (UNCHANGED)
        # ────────────────────────────────────────────────────────────
        buffer = 0.005  # 0.5% buffer
        side = None
        rejected_reason = None

        if short_ma > long_ma and current_price > trend_ma * (1 - buffer):
            side = "BUY"
        elif short_ma < long_ma and current_price < trend_ma * (1 + buffer):
            side = "SELL"
        else:
            if short_ma > long_ma and current_price < trend_ma * (1 - buffer):
                rejected_reason = "BUY_too_far_below_trend"
            elif short_ma < long_ma and current_price > trend_ma * (1 + buffer):
                rejected_reason = "SELL_too_far_above_trend"
            else:
                rejected_reason = "neutral_zone"

            logger.info(
                f"[TREND_FILTER] REJECT {self.symbol} reason={rejected_reason} "
                f"price=${current_price:.2f} vs MA{self.trend_period}=${trend_ma:.2f} "
                f"cross={'bullish' if short_ma > long_ma else 'bearish'}"
            )
            return None

        # ────────────────────────────────────────────────────────────
        # PHASE A.6: 1D BUY block (UNCHANGED)
        # ────────────────────────────────────────────────────────────
        if self.timeframe == "1D" and side == "BUY":
            logger.info(
                f"[TF_FILTER] REJECT {self.symbol} 1D BUY "
                f"(MA{self.short_period}/{self.long_period} too fast for daily)"
            )
            return None

        # ────────────────────────────────────────────────────────────
        # PHASE A.7: Weak-signal rejection (UNCHANGED)
        # ────────────────────────────────────────────────────────────
        spread = abs(short_ma - long_ma)
        ma_strength = spread / long_ma if long_ma != 0 else 0.0

        if ma_strength < 0.001:  # 0.1% min spread
            logger.info(
                f"[WEAK_SIGNAL] REJECT {self.symbol} {side} "
                f"MA spread too small: {ma_strength*100:.3f}%"
            )
            return None

        confidence = min(0.95, max(0.50, spread / current_price * 100))

        # ────────────────────────────────────────────────────────────
        # PHASE A.8: HARD BUY FREEZE (UNCHANGED — SHORT-only edge)
        # ────────────────────────────────────────────────────────────
        if side == "BUY":
            logger.info(
                f"[BUY_FREEZE] REJECT {self.symbol} {self.timeframe or 'default'} "
                f"conf={confidence:.2f} ma_strength={ma_strength:.4f} "
                f"price=${current_price:.2f} MA3={short_ma:.2f} MA5={long_ma:.2f} MA20={trend_ma:.2f}"
            )
            return None

        # ────────────────────────────────────────────────────────────
        # SHORT signal passes — build output
        # ────────────────────────────────────────────────────────────
        signal = {
            "symbol": self.symbol,
            "timeframe": self.timeframe,
            "side": side,
            "confidence": round(confidence, 4),
            "price": current_price,
            "short_ma": round(short_ma, 2),
            "long_ma": round(long_ma, 2),
            "trend_ma": round(trend_ma, 2),
            "spread_pct": round((spread / current_price) * 100, 4),
            "source": "multi_asset_ma",
            "last_candle_ts": self.last_candle_ts,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        logger.debug(
            f"[MultiAsset] {self.symbol}: {side} @ ${current_price:.2f} "
            f"(MA{self.short_period}={short_ma:.2f}, MA{self.long_period}={long_ma:.2f}, "
            f"trend_MA{self.trend_period}={trend_ma:.2f}, conf={confidence:.2f})"
        )
        return signal

    # --------------------------------------------------------------- #
    #  Serialization contract
    # --------------------------------------------------------------- #
    def to_state(self) -> Dict[str, Any]:
        """Export minimal state for persistence (GeneratorStateManager)."""
        return {
            "prices": list(self.prices)[-_STATE_PRICE_TAIL:],
            "last_candle_ts": self.last_candle_ts,
            "is_warm": self.is_warm,
            "symbol": self.symbol,
            "timeframe": self.timeframe,
            "params": {
                "short_period": self.short_period,
                "long_period": self.long_period,
                "trend_period": self.trend_period,
            },
        }

    def from_state(self, state: Dict[str, Any]) -> None:
        """Restore state from persisted doc (GeneratorStateManager)."""
        if not state:
            return
        prices = state.get("prices") or []
        self.prices = [float(p) for p in prices][-_STATE_PRICE_TAIL:]
        self.last_candle_ts = state.get("last_candle_ts")
        # Recompute is_warm from prices (don't trust persisted flag blindly)
        self.is_warm = bool(state.get("is_warm")) and len(self.prices) >= self.trend_period
        if not self.is_warm and len(self.prices) >= self.trend_period:
            self.is_warm = True

        logger.info(
            f"[MultiAsset] from_state {self.symbol} tf={self.timeframe}: "
            f"restored {len(self.prices)} prices, last_ts={self.last_candle_ts}, warm={self.is_warm}"
        )

    # --------------------------------------------------------------- #
    #  Internals
    # --------------------------------------------------------------- #
    def _ma(self, period: int) -> Optional[float]:
        if len(self.prices) < period:
            return None
        window = self.prices[-period:]
        return sum(window) / period

    # --------------------------------------------------------------- #
    #  Legacy interface (backward compatibility)
    # --------------------------------------------------------------- #
    def add_price(self, price: float) -> None:
        """
        LEGACY: Append raw price to state (no timestamp, no dedup).

        Used by `market_dynamic_runner.py` in pre-v2 path. New code
        must use `update(candle)` instead.
        """
        self.prices.append(float(price))
        if len(self.prices) > _STATE_PRICE_TAIL:
            self.prices = self.prices[-_STATE_PRICE_TAIL:]
        if not self.is_warm and len(self.prices) >= self.trend_period:
            self.is_warm = True

    def calculate_ma(self, period: int) -> Optional[float]:
        """LEGACY accessor used by old tests."""
        return self._ma(period)

    def generate_signal(self, current_price: float) -> Optional[Dict[str, Any]]:
        """
        LEGACY tick-based interface for pre-v2 runners.

        Appends `current_price` to state (no dedup — caller is responsible),
        then delegates to `maybe_generate()`.

        New v2 code MUST use update(candle) + maybe_generate() instead.
        """
        self.add_price(current_price)
        return self.maybe_generate()


# --------------------------------------------------------------- #
#  Legacy global pool (kept for runner.py / market_dynamic_runner)
# --------------------------------------------------------------- #
_multi_pool: Dict[str, MultiAssetGenerator] = {}


def get_multi_generator(symbol_key: str) -> MultiAssetGenerator:
    """
    LEGACY: Get or create generator by "SYMBOL_TF" key from a global pool.

    New v2 code should use `GeneratorStateManager.get_or_create(...)` instead,
    which handles persistence + warmup + duplicate symbol/TF reuse.
    """
    global _multi_pool

    if symbol_key not in _multi_pool:
        if "_" in symbol_key:
            symbol, timeframe = symbol_key.rsplit("_", 1)
        else:
            symbol = symbol_key
            timeframe = None
        _multi_pool[symbol_key] = MultiAssetGenerator(symbol=symbol, timeframe=timeframe)
        logger.info(f"[MultiAsset] Pool created generator for {symbol_key}")

    return _multi_pool[symbol_key]


def get_pool_size() -> int:
    return len(_multi_pool)
