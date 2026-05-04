"""
Breakout Long Generator — Phase A.9.2 → B.3
=============================================

BUY engine for ANY REGIME (not only uptrend).

Architecture:
  Breakout → Volume Confirmation → Strength Validation → Distance Filter

Philosophy:
  Ловим momentum: разворот, выход из range, early uptrend.

Version: V1 (FROZEN strategy logic — B.3 adds stateful contract only)

──────────────────────────────────────────────────────────────────────
Phase B.3 (2026-04-20) — Stateful Contract Integration
──────────────────────────────────────────────────────────────────────
Added F-TRADE v2 quant-engine interface (mirror of MultiAssetGenerator &
TrendPullbackLongGenerator):
  - warmup(candles)          — load history, NO SIGNALS
  - update(candle)           — append one candle w/ dedup by time
  - maybe_generate()         — pure signal calc, NO MUTATION
  - to_state()/from_state()  — persistence contract (OHLC+volume under extra)

Strategy parameters UNCHANGED (FROZEN):
  - lookback_period      = 20
  - volume_multiplier    = 1.5x
  - min_close_strength   = 0.7
  - max_breakout_distance = 0.3%

Legacy interface preserved (preload_history / append_candle / generate_signal)
for batch7_1_breakout_collection.py and existing pool consumers.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone
import logging

logger = logging.getLogger(__name__)


# Keep tail of OHLC+volume candles in state (covers lookback_period with margin)
_STATE_CANDLE_TAIL = 250


@dataclass
class BreakoutSignalDebug:
    """Debug info for breakout signal."""
    symbol: str
    timeframe: str
    price: float
    recent_high: Optional[float]
    is_breakout: bool
    volume_confirmed: bool
    close_strength: float
    reject_reason: Optional[str] = None


class BreakoutLongGenerator:
    """
    BUY-only generator based on breakout logic.

    Architecture (UNCHANGED from Phase A.9.2):
      1. Breakout: price > recent_high over lookback_period (exclusive of current candle)
      2. Volume confirmation: current_volume >= avg_volume * volume_multiplier
      3. Close strength: (close-low)/(high-low) >= min_close_strength
      4. Distance: (price-recent_high)/recent_high <= max_breakout_distance

    Works in: Uptrend, Range, Recovery (regime-agnostic).

    F-TRADE v2 stateful contract (B.3):
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
        lookback_period: int = 20,          # FROZEN
        volume_multiplier: float = 1.5,     # FROZEN
        min_close_strength: float = 0.7,    # FROZEN — top 30% of candle
        max_breakout_distance: float = 0.003,  # FROZEN — 0.3%
        warmup_limit: int = 60,             # legacy ring for backwards compat
    ) -> None:
        """
        Args:
            symbol: Trading pair
            timeframe: Timeframe (1H, 4H, 1D)
            lookback_period: Period for recent_high (default 20) — FROZEN
            volume_multiplier: Volume confirmation threshold (default 1.5x) — FROZEN
            min_close_strength: Min (close-low)/(high-low) (default 0.7) — FROZEN
            max_breakout_distance: Max distance from breakout point (default 0.3%) — FROZEN
            warmup_limit: Legacy ring size (append_candle path). B.3 state ring is
                          controlled by _STATE_CANDLE_TAIL (250).
        """
        self.symbol = symbol
        self.timeframe = timeframe
        self.lookback_period = lookback_period
        self.volume_multiplier = volume_multiplier
        self.min_close_strength = min_close_strength
        self.max_breakout_distance = max_breakout_distance
        self.warmup_limit = warmup_limit

        # ── State (serializable) ────────────────────────────────────
        self._candles: List[Dict[str, Any]] = []  # OHLC + volume
        self.last_candle_ts: Optional[int] = None  # seconds since epoch
        self.is_warm: bool = False

        # Warmth threshold: need lookback+1 candles so recent_high excludes current.
        self._warm_period = lookback_period + 1

        logger.info(
            f"[BreakoutLong] Init {symbol} tf={timeframe} "
            f"(lookback={lookback_period}, vol_mult={volume_multiplier}x, "
            f"close_strength>={min_close_strength}, max_dist={max_breakout_distance*100:.1f}%)"
        )

    # --------------------------------------------------------------- #
    #  Public stateful interface (F-TRADE v2 contract)
    # --------------------------------------------------------------- #
    def warmup(self, candles: List[Dict[str, Any]]) -> None:
        """
        Load historical candles without producing any signals.

        - Replaces existing OHLC+volume history (idempotent warmup).
        - Sets last_candle_ts from last candle.
        - Flips is_warm once we have >= lookback_period+1 candles.

        Args:
            candles: list of dicts with {'time','open','high','low','close','volume'}.
                     `time` in seconds-since-epoch (BinanceProvider format).
        """
        if not candles:
            logger.warning(f"[BreakoutLong] warmup({self.symbol}) called with empty candles")
            return

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
                    "volume": float(c.get("volume", 0.0)),
                })
            except (KeyError, TypeError, ValueError) as e:
                logger.warning(f"[BreakoutLong] warmup skip malformed candle: {e}")
                continue

        self._candles = normalized
        last = normalized[-1] if normalized else None
        self.last_candle_ts = last.get("time") if last else None
        self.is_warm = len(self._candles) >= self._warm_period

        logger.info(
            f"[BreakoutLong] warmup {self.symbol} tf={self.timeframe}: "
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
                f"[BreakoutLong] update({self.symbol}) candle without time/timestamp — accepted w/o dedup"
            )
        elif self.last_candle_ts is not None and ts <= self.last_candle_ts:
            logger.debug(
                f"[BreakoutLong] update {self.symbol} {self.timeframe} dup skip "
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
                "volume": float(candle.get("volume", 0.0)),
            })
        except (KeyError, TypeError, ValueError) as e:
            logger.warning(f"[BreakoutLong] update malformed candle: {e}")
            return False

        if len(self._candles) > _STATE_CANDLE_TAIL:
            self._candles = self._candles[-_STATE_CANDLE_TAIL:]

        if ts is not None:
            self.last_candle_ts = ts

        # is_warm can only flip True → never False in update()
        if not self.is_warm and len(self._candles) >= self._warm_period:
            self.is_warm = True

        return True

    def maybe_generate(self) -> Optional[Dict[str, Any]]:
        """
        Compute signal from current state. NO mutation.

        Logic UNCHANGED from Phase A.9.2:
          1. Breakout:    price > recent_high(lookback_period)
          2. Volume:      current_vol / avg_vol >= volume_multiplier
          3. Strength:    (close-low)/(high-low) >= min_close_strength
          4. Distance:    (price-recent_high)/recent_high <= max_breakout_distance
        """
        if not self.is_warm:
            logger.debug(
                f"[BreakoutLong] maybe_generate {self.symbol}: cold "
                f"({len(self._candles)}/{self._warm_period})"
            )
            return None

        candle = self._last_candle()
        if candle is None:
            return None

        price = candle["close"]
        current_volume = candle["volume"]

        if len(self._candles) < self.lookback_period + 1:
            logger.debug(
                f"[BreakoutLong] {self.symbol}: insufficient data "
                f"(candles={len(self._candles)}, need={self.lookback_period + 1})"
            )
            return None

        # Layer 1: BREAKOUT — FROZEN
        recent_high = self._recent_high(self.lookback_period)
        if recent_high is None:
            return None
        is_breakout = price > recent_high
        if not is_breakout:
            logger.debug(
                f"[BreakoutLong] REJECT {self.symbol} {self.timeframe} "
                f"(no_breakout: price=${price:.2f} vs recent_high=${recent_high:.2f})"
            )
            return None

        # Layer 2: VOLUME CONFIRMATION — FROZEN
        avg_volume = self._avg_volume(self.lookback_period)
        if avg_volume is None or avg_volume == 0:
            logger.debug(
                f"[BreakoutLong] REJECT {self.symbol} {self.timeframe} (no_volume_data)"
            )
            return None
        volume_ratio = current_volume / avg_volume if avg_volume else 0.0
        volume_confirmed = volume_ratio >= self.volume_multiplier
        if not volume_confirmed:
            logger.debug(
                f"[BreakoutLong] REJECT {self.symbol} {self.timeframe} "
                f"(weak_volume: {volume_ratio:.2f}x vs {self.volume_multiplier}x threshold)"
            )
            return None

        # Layer 3: CLOSE STRENGTH — FROZEN
        candle_range = candle["high"] - candle["low"]
        if candle_range == 0:
            logger.debug(
                f"[BreakoutLong] REJECT {self.symbol} {self.timeframe} (zero_range: doji candle)"
            )
            return None
        close_strength = (candle["close"] - candle["low"]) / candle_range
        if close_strength < self.min_close_strength:
            logger.debug(
                f"[BreakoutLong] REJECT {self.symbol} {self.timeframe} "
                f"(weak_close: strength={close_strength:.2f} vs {self.min_close_strength} min)"
            )
            return None

        # Layer 4: DISTANCE — FROZEN
        distance_from_breakout = (price - recent_high) / recent_high if recent_high else 0.0
        if distance_from_breakout > self.max_breakout_distance:
            logger.debug(
                f"[BreakoutLong] REJECT {self.symbol} {self.timeframe} "
                f"(too_late: distance={distance_from_breakout*100:.2f}% vs {self.max_breakout_distance*100:.1f}% max)"
            )
            return None

        # Confidence (UNCHANGED from V1)
        volume_score = min(1.0, (volume_ratio - self.volume_multiplier) / self.volume_multiplier)
        strength_score = (close_strength - self.min_close_strength) / (1.0 - self.min_close_strength)
        distance_score = 1.0 - (distance_from_breakout / self.max_breakout_distance)
        confidence = round(0.5 + 0.2 * volume_score + 0.2 * strength_score + 0.1 * distance_score, 4)

        signal = {
            "symbol": self.symbol,
            "timeframe": self.timeframe,
            "side": "BUY",
            "price": price,
            "confidence": confidence,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "last_candle_ts": self.last_candle_ts,
            "source": "breakout_long_v1",
            "features": {
                "generator": "breakout_long_v1",
                "cluster": self._classify_cluster(self.symbol),
                "alignment": "aligned" if confidence >= 0.65 else "divergent",
                "regime": "breakout",
                "recent_high": round(recent_high, 8),
                "breakout_distance": round(distance_from_breakout, 6),
                "volume_ratio": round(volume_ratio, 2),
                "close_strength": round(close_strength, 4),
            },
        }

        logger.info(
            f"[BreakoutLong] SIGNAL {self.symbol} {self.timeframe} BUY "
            f"@ ${price:.2f} conf={confidence:.2f} "
            f"(breakout=${recent_high:.2f}, vol={volume_ratio:.1f}x, strength={close_strength:.2f})"
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
        - Full OHLC+volume stream lives under `extra.ohlc_candles`. The
          StateManager round-trips the opaque `extra` dict unchanged
          (see B.2 StateManager patch).
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
                "lookback_period": self.lookback_period,
                "volume_multiplier": self.volume_multiplier,
                "min_close_strength": self.min_close_strength,
                "max_breakout_distance": self.max_breakout_distance,
            },
            "extra": {
                "ohlc_candles": tail,  # list of {time,open,high,low,close,volume}
            },
        }

    def from_state(self, state: Dict[str, Any]) -> None:
        """
        Restore state from persisted doc.

        Preference order for candle data:
          1. state["extra"]["ohlc_candles"] — full OHLC+volume, preferred
          2. state["prices"] — degraded restore (close-only; open=high=low=close,
             volume=0 — recent_high/avg_volume will safely reject on these
             synthesized bars until real update() supplies fresh OHLC+volume).
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
                        "volume": float(c.get("volume", 0.0)),
                    })
                except (KeyError, TypeError, ValueError):
                    continue
            self._candles = restored
        else:
            closes = state.get("prices") or []
            self._candles = [
                {"time": None, "open": float(p), "high": float(p),
                 "low": float(p), "close": float(p), "volume": 0.0}
                for p in closes[-_STATE_CANDLE_TAIL:]
            ]
            if self._candles:
                logger.warning(
                    f"[BreakoutLong] from_state {self.symbol}: degraded restore "
                    f"(close-only, no OHLC/volume) — next candle will rehydrate"
                )

        self.last_candle_ts = state.get("last_candle_ts")
        self.is_warm = bool(state.get("is_warm")) and len(self._candles) >= self._warm_period
        if not self.is_warm and len(self._candles) >= self._warm_period:
            self.is_warm = True

        logger.info(
            f"[BreakoutLong] from_state {self.symbol} tf={self.timeframe}: "
            f"restored {len(self._candles)} candles, last_ts={self.last_candle_ts}, warm={self.is_warm}"
        )

    # --------------------------------------------------------------- #
    #  Internals (UNCHANGED from V1)
    # --------------------------------------------------------------- #
    def _last_candle(self) -> Optional[Dict[str, Any]]:
        if not self._candles:
            return None
        return self._candles[-1]

    def _recent_high(self, period: int) -> Optional[float]:
        """Highest high in recent period (EXCLUDING current candle)."""
        if len(self._candles) < period + 1:
            return None
        highs = [c["high"] for c in self._candles[-(period + 1):-1]]
        return max(highs) if highs else None

    def _avg_volume(self, period: int) -> Optional[float]:
        """Average volume over period (EXCLUDING current candle)."""
        if len(self._candles) < period + 1:
            return None
        volumes = [c["volume"] for c in self._candles[-(period + 1):-1]]
        return sum(volumes) / len(volumes) if volumes else None

    def _atr(self, period: int = 14) -> Optional[float]:
        """Calculate ATR (kept for external use / debug). Not used in maybe_generate."""
        if len(self._candles) < period:
            return None
        trs = []
        for i in range(len(self._candles) - period, len(self._candles)):
            candle = self._candles[i]
            prev_close = self._candles[i - 1]["close"] if i > 0 else candle["open"]
            tr = max(
                candle["high"] - candle["low"],
                abs(candle["high"] - prev_close),
                abs(candle["low"] - prev_close),
            )
            trs.append(tr)
        return sum(trs) / len(trs) if trs else None

    @staticmethod
    def _classify_cluster(symbol: str) -> str:
        """Classify symbol into cluster."""
        majors = {"BTCUSDT", "ETHUSDT"}
        stable = {"USDCUSDT", "BUSDUSDT", "USDTUSDT"}
        if symbol in majors:
            return "majors"
        if symbol in stable:
            return "stable"
        return "alts"

    # --------------------------------------------------------------- #
    #  Legacy interface (backward compatibility for pre-B.3 callers)
    # --------------------------------------------------------------- #
    def preload_history(self, candles: List[Dict[str, Any]]) -> None:
        """
        LEGACY: Replace internal history with fresh candles (capped to warmup_limit).

        B.3 callers should use `warmup()` instead (which uses _STATE_CANDLE_TAIL).
        Kept for batch7_1_breakout_collection.py.
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
                    "volume": float(c.get("volume", 0.0)),
                })
            except (KeyError, TypeError, ValueError):
                continue
        self._candles = normalized
        if normalized:
            self.last_candle_ts = normalized[-1].get("time")
        if not self.is_warm and len(self._candles) >= self._warm_period:
            self.is_warm = True
        logger.debug(f"[BreakoutLong] {self.symbol} preloaded {len(normalized)} candles")

    def append_candle(self, candle: Dict[str, Any]) -> None:
        """
        LEGACY: Add new candle to history (no dedup — caller is responsible).
        B.3 callers should use `update(candle)` instead.
        """
        try:
            self._candles.append({
                "time": candle.get("time") if candle.get("time") is not None else candle.get("timestamp"),
                "open": float(candle["open"]),
                "high": float(candle["high"]),
                "low": float(candle["low"]),
                "close": float(candle["close"]),
                "volume": float(candle.get("volume", 0.0)),
            })
        except (KeyError, TypeError, ValueError):
            return
        self._candles = self._candles[-max(self.warmup_limit, _STATE_CANDLE_TAIL):]
        ts = candle.get("time") if candle.get("time") is not None else candle.get("timestamp")
        if ts is not None:
            self.last_candle_ts = ts
        if not self.is_warm and len(self._candles) >= self._warm_period:
            self.is_warm = True

    def generate_signal(self) -> Optional[Dict[str, Any]]:
        """
        LEGACY parameterless interface — thin wrapper over `maybe_generate()`.
        Kept for batch7_1_breakout_collection.py and earlier runners.
        """
        return self.maybe_generate()


# --------------------------------------------------------------- #
#  Legacy generator pool (kept for batch7_1_breakout_collection.py)
# --------------------------------------------------------------- #
_breakout_pool: Dict[str, BreakoutLongGenerator] = {}


def get_breakout_generator(symbol_key: str) -> BreakoutLongGenerator:
    """
    LEGACY: Get or create breakout generator by "SYMBOL_TF" key from a global pool.

    New v2 code should use `GeneratorStateManager.get_or_create(...)` — which handles
    persistence + warmup + duplicate symbol/TF reuse.
    """
    global _breakout_pool

    if symbol_key not in _breakout_pool:
        if "_" in symbol_key:
            symbol, timeframe = symbol_key.rsplit("_", 1)
        else:
            symbol = symbol_key
            timeframe = "4H"  # default

        _breakout_pool[symbol_key] = BreakoutLongGenerator(
            symbol=symbol,
            timeframe=timeframe,
        )
        logger.info(f"[BreakoutPool] Created generator for {symbol_key}")

    return _breakout_pool[symbol_key]


def get_pool_size() -> int:
    """Get current pool size."""
    return len(_breakout_pool)
