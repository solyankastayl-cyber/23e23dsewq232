"""
Trend Pullback Long Generator — Phase A.9 → B.2
=================================================

NEW BUY ENGINE (не модификация старого crossover).

Architecture:
  Regime  → Setup       → Trigger
  uptrend → pullback    → bullish reclaim candle

Philosophy:
  НЕ "угадывание роста"
  А "покупка отката внутри тренда"

Version: V1 (FROZEN strategy logic — B.2 adds stateful contract only)

──────────────────────────────────────────────────────────────────────
Phase B.2 (2026-04-20) — Stateful Contract Integration
──────────────────────────────────────────────────────────────────────
Added F-TRADE v2 quant-engine interface (same as MultiAssetGenerator):
  - warmup(candles)       — load history, NO SIGNALS
  - update(candle)        — append one candle w/ dedup by time
  - maybe_generate()      — pure signal calc, NO MUTATION
  - to_state()/from_state() — persistence contract

Strategy parameters UNCHANGED:
  - pullback_threshold = 0.4% from MA20
  - min_body_pct       = 0.1%
  - regime rule        = uptrend (price > ma50 AND ma20 > ma50)
  - trigger            = bullish candle (close > open)
  - body filter        = >= min_body_pct

Legacy interface preserved (preload_history / append_candle / generate_signal)
for batch7_long_collection.py and existing pool consumers.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone
import logging

logger = logging.getLogger(__name__)


# Keep tail of OHLC candles in state (covers MA50 + pullback detection with margin)
_STATE_CANDLE_TAIL = 250


@dataclass
class LongSignalDebug:
    """Debug info for signal generation."""
    symbol: str
    timeframe: str
    price: float
    ma20: Optional[float]
    ma50: Optional[float]
    trend_up: bool
    in_pullback_zone: bool
    bullish_candle: bool
    body_ok: bool
    reject_reason: Optional[str] = None


class TrendPullbackLongGenerator:
    """
    BUY-only generator based on trend pullback logic.

    Architecture (UNCHANGED from Phase A.9):
      1. Regime: uptrend confirmed (price > ma50 AND ma20 > ma50)
      2. Setup: pullback to value zone (near ma20)
      3. Trigger: bullish candle + adequate body

    F-TRADE v2 stateful contract (B.2):
      - warmup(candles): load history WITHOUT producing signals
      - update(candle):  append one candle, dedup by candle['time'], bool
      - maybe_generate(): pure calc, no mutation
      - to_state() / from_state(state): serialize/restore across restart
    """

    # --------------------------------------------------------------- #
    #  Construction — strategy params FROZEN
    # --------------------------------------------------------------- #
    def __init__(
        self,
        symbol: str,
        timeframe: str,
        pullback_threshold: float = 0.004,   # 0.4% from ma20 — FROZEN
        min_body_pct: float = 0.001,         # 0.1% minimum body — FROZEN
        warmup_limit: int = 60,              # legacy ring for backwards compat
    ) -> None:
        """
        Args:
            symbol: Trading pair
            timeframe: Timeframe (1H, 4H, 1D)
            pullback_threshold: Max distance from ma20 for pullback (default 0.4%) — FROZEN
            min_body_pct: Minimum candle body % (default 0.1%) — FROZEN
            warmup_limit: Legacy ring size (append_candle path). B.2 state ring is
                          controlled by _STATE_CANDLE_TAIL (250).
        """
        self.symbol = symbol
        self.timeframe = timeframe
        self.pullback_threshold = pullback_threshold
        self.min_body_pct = min_body_pct
        self.warmup_limit = warmup_limit

        # ── State (serializable) ────────────────────────────────────
        self._candles: List[Dict[str, Any]] = []
        self.last_candle_ts: Optional[int] = None  # seconds since epoch
        self.is_warm: bool = False

        # Warmth threshold: MA50 is the deepest indicator used by this strategy.
        self._trend_period = 50

        logger.info(
            f"[TrendPullbackLong] Init {symbol} tf={timeframe} "
            f"(pullback={pullback_threshold*100:.1f}%, min_body={min_body_pct*100:.2f}%)"
        )

    # --------------------------------------------------------------- #
    #  Public stateful interface (F-TRADE v2 contract)
    # --------------------------------------------------------------- #
    def warmup(self, candles: List[Dict[str, Any]]) -> None:
        """
        Load historical candles without producing any signals.

        - Replaces existing OHLC history (idempotent warmup).
        - Sets last_candle_ts from last candle.
        - Flags is_warm=True once we have >= 50 candles (MA50 warmth).

        Args:
            candles: list of dicts with {'time','open','high','low','close'}.
                     `time` in seconds-since-epoch (BinanceProvider format).
        """
        if not candles:
            logger.warning(f"[TrendPullbackLong] warmup({self.symbol}) called with empty candles")
            return

        # Normalize + cap tail
        tail = candles[-_STATE_CANDLE_TAIL:]
        normalized: List[Dict[str, Any]] = []
        for c in tail:
            try:
                normalized.append({
                    "time": c.get("time") if c.get("time") is not None else c.get("timestamp"),
                    "open": float(c["open"]),
                    "high": float(c["high"]),
                    "low": float(c["low"]),
                    "close": float(c["close"]),
                })
            except (KeyError, TypeError, ValueError) as e:
                logger.warning(f"[TrendPullbackLong] warmup skip malformed candle: {e}")
                continue

        self._candles = normalized
        last = normalized[-1] if normalized else None
        self.last_candle_ts = last.get("time") if last else None
        self.is_warm = len(self._candles) >= self._trend_period

        logger.info(
            f"[TrendPullbackLong] warmup {self.symbol} tf={self.timeframe}: "
            f"{len(self._candles)} candles, last_ts={self.last_candle_ts}, warm={self.is_warm}"
        )

    def update(self, candle: Dict[str, Any]) -> bool:
        """
        Append one candle to state. Deduplicate by candle['time'].

        Returns:
            True  — new candle accepted (state changed).
            False — duplicate/older candle (state unchanged).
        """
        ts = candle.get("time") if candle.get("time") is not None else candle.get("timestamp")

        if ts is None:
            logger.warning(
                f"[TrendPullbackLong] update({self.symbol}) candle without time/timestamp — accepted w/o dedup"
            )
        elif self.last_candle_ts is not None and ts <= self.last_candle_ts:
            logger.debug(
                f"[TrendPullbackLong] update {self.symbol} {self.timeframe} dup skip "
                f"(ts={ts}, last={self.last_candle_ts})"
            )
            return False

        try:
            self._candles.append({
                "time": ts,
                "open": float(candle["open"]),
                "high": float(candle["high"]),
                "low": float(candle["low"]),
                "close": float(candle["close"]),
            })
        except (KeyError, TypeError, ValueError) as e:
            logger.warning(f"[TrendPullbackLong] update malformed candle: {e}")
            return False

        if len(self._candles) > _STATE_CANDLE_TAIL:
            self._candles = self._candles[-_STATE_CANDLE_TAIL:]

        if ts is not None:
            self.last_candle_ts = ts

        # is_warm can only flip True → never False in update()
        if not self.is_warm and len(self._candles) >= self._trend_period:
            self.is_warm = True

        return True

    def maybe_generate(self) -> Optional[Dict[str, Any]]:
        """
        Compute signal from current state. NO mutation.

        Logic UNCHANGED from Phase A.9:
          1. Regime: uptrend (price > ma50 AND ma20 > ma50)
          2. Setup:  pullback (|price - ma20| / ma20 <= pullback_threshold)
          3. Trigger: bullish candle (close > open)
          4. Strength: body_pct >= min_body_pct
        """
        if not self.is_warm:
            logger.debug(
                f"[TrendPullbackLong] maybe_generate {self.symbol}: cold "
                f"({len(self._candles)}/{self._trend_period})"
            )
            return None

        candle = self._last_candle()
        if candle is None:
            return None

        price = candle["close"]
        ma20 = self._ma(20)
        ma50 = self._ma(50)

        if ma20 is None or ma50 is None:
            logger.debug(
                f"[TrendPullbackLong] {self.symbol}: insufficient data "
                f"(candles={len(self._candles)}, need=50)"
            )
            return None

        # Layer 1: REGIME (uptrend) — FROZEN
        trend_up = price > ma50 and ma20 > ma50
        if not trend_up:
            logger.debug(
                f"[TrendPullbackLong] REJECT {self.symbol} {self.timeframe} "
                f"(no_uptrend: price={price:.2f} ma20={ma20:.2f} ma50={ma50:.2f})"
            )
            return None

        # Layer 2: SETUP (pullback zone) — FROZEN
        dist_to_ma20 = abs(price - ma20) / ma20
        in_pullback_zone = dist_to_ma20 <= self.pullback_threshold
        if not in_pullback_zone:
            logger.debug(
                f"[TrendPullbackLong] REJECT {self.symbol} {self.timeframe} "
                f"(not_in_pullback_zone: dist={dist_to_ma20*100:.2f}% vs threshold={self.pullback_threshold*100:.1f}%)"
            )
            return None

        # Layer 3: TRIGGER (bullish candle) — FROZEN
        bullish_candle = candle["close"] > candle["open"]
        if not bullish_candle:
            logger.debug(
                f"[TrendPullbackLong] REJECT {self.symbol} {self.timeframe} "
                f"(bearish_candle: open={candle['open']:.2f} close={candle['close']:.2f})"
            )
            return None

        # Layer 4: STRENGTH (adequate body) — FROZEN
        body_pct = abs(candle["close"] - candle["open"]) / candle["open"] if candle["open"] else 0.0
        body_ok = body_pct >= self.min_body_pct
        if not body_ok:
            logger.debug(
                f"[TrendPullbackLong] REJECT {self.symbol} {self.timeframe} "
                f"(weak_body: body={body_pct*100:.3f}% vs min={self.min_body_pct*100:.2f}%)"
            )
            return None

        # Confidence model (UNCHANGED from V1)
        pullback_score = max(0.0, 1.0 - (dist_to_ma20 / self.pullback_threshold))
        body_score = min(1.0, body_pct / (self.min_body_pct * 3))
        confidence = round(0.5 + 0.25 * pullback_score + 0.25 * body_score, 4)

        signal = {
            "symbol": self.symbol,
            "timeframe": self.timeframe,
            "side": "BUY",
            "price": price,
            "confidence": confidence,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "last_candle_ts": self.last_candle_ts,
            "source": "trend_pullback_long_v1",
            "features": {
                "generator": "trend_pullback_long_v1",
                "cluster": self._classify_cluster(self.symbol),
                "alignment": "aligned" if confidence >= 0.65 else "divergent",
                "regime": "uptrend",
                "dist_to_ma20": round(dist_to_ma20, 6),
                "body_pct": round(body_pct, 6),
                "ma20": round(ma20, 8),
                "ma50": round(ma50, 8),
            },
        }

        logger.info(
            f"[TrendPullbackLong] SIGNAL {self.symbol} {self.timeframe} BUY "
            f"@ ${price:.2f} conf={confidence:.2f} "
            f"(ma20=${ma20:.2f} ma50=${ma50:.2f} body={body_pct*100:.2f}%)"
        )
        return signal

    # --------------------------------------------------------------- #
    #  Serialization contract (GeneratorStateManager round-trip)
    # --------------------------------------------------------------- #
    def to_state(self) -> Dict[str, Any]:
        """
        Export state for persistence.

        - `prices` kept as list-of-closes for backward compatibility with
          GeneratorStateManager's legacy float-only schema.
        - Full OHLC stream lives under `extra.ohlc_candles` (StateManager
          passes this through unchanged — see B.2 StateManager patch).
        """
        tail = self._candles[-_STATE_CANDLE_TAIL:]
        closes = [c["close"] for c in tail]
        return {
            "prices": closes,
            "last_candle_ts": self.last_candle_ts,
            "is_warm": self.is_warm,
            "symbol": self.symbol,
            "timeframe": self.timeframe,
            "params": {
                "pullback_threshold": self.pullback_threshold,
                "min_body_pct": self.min_body_pct,
            },
            "extra": {
                "ohlc_candles": tail,  # list of {time,open,high,low,close}
            },
        }

    def from_state(self, state: Dict[str, Any]) -> None:
        """
        Restore state from persisted doc.

        Preference order for candle data:
          1. state["extra"]["ohlc_candles"] — full OHLC, preferred
          2. state["prices"] — degraded restore (close-only; open/high/low
             synthesized from close so Trigger/body checks gracefully fail
             on these synthesized bars; the moving averages survive).
        """
        if not state:
            return

        extra = state.get("extra") or {}
        ohlc = extra.get("ohlc_candles")

        if ohlc:
            restored: List[Dict[str, Any]] = []
            for c in ohlc[-_STATE_CANDLE_TAIL:]:
                try:
                    restored.append({
                        "time": c.get("time"),
                        "open": float(c["open"]),
                        "high": float(c["high"]),
                        "low": float(c["low"]),
                        "close": float(c["close"]),
                    })
                except (KeyError, TypeError, ValueError):
                    continue
            self._candles = restored
        else:
            # Degraded restore from closes only. MAs work, but candle-body
            # check will always reject (open==close → body_pct=0), which is
            # the safe behavior — next real update() will supply a true OHLC.
            closes = state.get("prices") or []
            self._candles = [
                {"time": None, "open": float(p), "high": float(p), "low": float(p), "close": float(p)}
                for p in closes[-_STATE_CANDLE_TAIL:]
            ]
            if self._candles:
                logger.warning(
                    f"[TrendPullbackLong] from_state {self.symbol}: degraded restore "
                    f"(close-only, no OHLC) — next candle will rehydrate"
                )

        self.last_candle_ts = state.get("last_candle_ts")
        self.is_warm = bool(state.get("is_warm")) and len(self._candles) >= self._trend_period
        if not self.is_warm and len(self._candles) >= self._trend_period:
            self.is_warm = True

        logger.info(
            f"[TrendPullbackLong] from_state {self.symbol} tf={self.timeframe}: "
            f"restored {len(self._candles)} candles, last_ts={self.last_candle_ts}, warm={self.is_warm}"
        )

    # --------------------------------------------------------------- #
    #  Internals
    # --------------------------------------------------------------- #
    def _ma(self, period: int) -> Optional[float]:
        if len(self._candles) < period:
            return None
        window = self._candles[-period:]
        return sum(c["close"] for c in window) / period

    def _last_candle(self) -> Optional[Dict[str, Any]]:
        if not self._candles:
            return None
        return self._candles[-1]

    @staticmethod
    def _classify_cluster(symbol: str) -> str:
        """Classify symbol into cluster for analysis."""
        majors = {"BTCUSDT", "ETHUSDT"}
        stable = {"USDCUSDT", "BUSDUSDT", "USDTUSDT"}

        if symbol in majors:
            return "majors"
        if symbol in stable:
            return "stable"
        return "alts"

    # --------------------------------------------------------------- #
    #  Legacy interface (backward compatibility for pre-B.2 callers)
    # --------------------------------------------------------------- #
    def preload_history(self, candles: List[Dict[str, Any]]) -> None:
        """
        LEGACY: Replace internal history with fresh candles (capped to warmup_limit).

        B.2 callers should use `warmup()` instead (which uses _STATE_CANDLE_TAIL).
        Kept for batch7_long_collection.py.
        """
        normalized: List[Dict[str, Any]] = []
        for c in candles[-self.warmup_limit:]:
            try:
                normalized.append({
                    "time": c.get("time") if c.get("time") is not None else c.get("timestamp"),
                    "open": float(c["open"]),
                    "high": float(c["high"]),
                    "low": float(c["low"]),
                    "close": float(c["close"]),
                })
            except (KeyError, TypeError, ValueError):
                continue
        self._candles = normalized
        if normalized:
            last = normalized[-1]
            self.last_candle_ts = last.get("time")
        if not self.is_warm and len(self._candles) >= self._trend_period:
            self.is_warm = True
        logger.debug(f"[TrendPullbackLong] {self.symbol} preloaded {len(normalized)} candles")

    def append_candle(self, candle: Dict[str, Any]) -> None:
        """
        LEGACY: Add new candle to history (no dedup — caller is responsible).
        B.2 callers should use `update(candle)` instead.
        """
        try:
            self._candles.append({
                "time": candle.get("time") if candle.get("time") is not None else candle.get("timestamp"),
                "open": float(candle["open"]),
                "high": float(candle["high"]),
                "low": float(candle["low"]),
                "close": float(candle["close"]),
            })
        except (KeyError, TypeError, ValueError):
            return
        self._candles = self._candles[-max(self.warmup_limit, _STATE_CANDLE_TAIL):]
        ts = candle.get("time") if candle.get("time") is not None else candle.get("timestamp")
        if ts is not None:
            self.last_candle_ts = ts
        if not self.is_warm and len(self._candles) >= self._trend_period:
            self.is_warm = True

    def generate_signal(self) -> Optional[Dict[str, Any]]:
        """
        LEGACY parameterless interface — thin wrapper over `maybe_generate()`.
        Kept for batch7_long_collection.py and earlier runners.
        """
        return self.maybe_generate()


# --------------------------------------------------------------- #
#  Legacy generator pool (kept for batch7_long_collection.py)
# --------------------------------------------------------------- #
_long_pool: Dict[str, TrendPullbackLongGenerator] = {}


def get_long_generator(symbol_key: str) -> TrendPullbackLongGenerator:
    """
    LEGACY: Get or create long generator for symbol+timeframe via global pool.

    New v2 code should use `GeneratorStateManager.get_or_create(...)` with
    factory — which handles persistence + warmup + restart restore.
    """
    global _long_pool

    if symbol_key not in _long_pool:
        if "_" in symbol_key:
            symbol, timeframe = symbol_key.rsplit("_", 1)
        else:
            symbol = symbol_key
            timeframe = "4H"  # default

        _long_pool[symbol_key] = TrendPullbackLongGenerator(
            symbol=symbol,
            timeframe=timeframe,
        )
        logger.info(f"[LongPool] Created generator for {symbol_key}")

    return _long_pool[symbol_key]


def get_pool_size() -> int:
    """Get current pool size."""
    return len(_long_pool)
