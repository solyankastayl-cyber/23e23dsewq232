"""
Generator State Manager — F-TRADE v2
====================================

Single authority for generator lifecycle, state persistence, and checkpointing.

Philosophy:
  - One generator instance per (strategy, symbol, timeframe)
  - State survives process restart (MongoDB checkpoints)
  - Clear separation: warmup / update / generate

Critical Rules:
  1. One generator instance per key
  2. One candle timestamp processed once
  3. Warmup never creates signals
  4. Generate never updates history

Persistence contract:
  - If generator exposes `to_state()` / `from_state(state)` — use those.
  - Otherwise, fall back to attribute-based restore (legacy).

Phase B.2 additions:
  - `extra` field pass-through: generators can embed strategy-specific payloads
    (e.g. TrendPullbackLongGenerator stores full OHLC under extra.ohlc_candles).
    The state manager round-trips this opaque dict unchanged.

Uses **synchronous** pymongo for the `generator_state` collection because
generator operations happen in tight inner loops where async overhead
hurts — async callers can pass a sync pymongo `Database` here.
"""

from __future__ import annotations
from typing import Dict, Any, Optional, Callable, List
from datetime import datetime, timezone
import logging

logger = logging.getLogger(__name__)


class GeneratorStateManager:
    """
    In-memory cache + persistent MongoDB checkpoint for generator state.

    State Key Format: "{strategy}:{symbol}:{timeframe}"
    Example: "SHORT_TREND:BTCUSDT:4H"
    """

    def __init__(self, db, lane: Optional[str] = None):
        """
        Args:
            db: pymongo (sync) Database instance. Must expose
                `generator_state` and `validator_observations` collections.
            lane: Optional lane qualifier (e.g. "phase_c", "discovery"). Keeps
                state isolated between concurrent Phase-C truth loop and
                discovery_matrix_live exploration loop so they don't race on
                the same (strategy, symbol, tf) checkpoint docs.
                None = legacy behavior (bare "{strategy}:{symbol}:{tf}" key).
        """
        self.db = db
        self.lane = lane
        self.cache: Dict[str, Any] = {}

        try:
            self.db.generator_state.create_index("key", unique=True)
            logger.info(f"[StateManager] Initialized lane={lane!r} with persistent checkpoint")
        except Exception as e:
            logger.warning(f"[StateManager] Index creation warning: {e}")

    # --------------------------------------------------------------- #
    #  Key helpers
    # --------------------------------------------------------------- #
    def _make_key(self, strategy: str, symbol: str, timeframe: str) -> str:
        if self.lane:
            return f"{self.lane}:{strategy}:{symbol}:{timeframe}"
        return f"{strategy}:{symbol}:{timeframe}"

    # --------------------------------------------------------------- #
    #  Lifecycle
    # --------------------------------------------------------------- #
    def get_or_create(
        self,
        strategy: str,
        symbol: str,
        timeframe: str,
        factory: Callable[[str, str], Any],
        warmup_candles: Optional[List[Dict[str, Any]]] = None,
    ) -> Any:
        """
        Get-or-create generator for (strategy, symbol, timeframe).

        Lifecycle:
          1. Cache HIT → return cached instance.
          2. Cache MISS + Mongo checkpoint EXISTS → factory + from_state(doc).
          3. Cache MISS + no checkpoint → factory + warmup(candles) if provided.

        Args:
            strategy: strategy identifier (e.g. "SHORT_TREND", "LONG_PULLBACK").
            symbol:   trading pair.
            timeframe: TF string.
            factory:   callable (symbol, timeframe) -> generator instance.
            warmup_candles: candles list for fresh warmup (only used on MISS w/o checkpoint).

        Returns:
            Generator instance (ready for update() / maybe_generate()).
        """
        key = self._make_key(strategy, symbol, timeframe)

        # 1) In-memory cache
        cached = self.cache.get(key)
        if cached is not None:
            logger.debug(f"[StateManager] Cache HIT: {key}")
            return cached

        logger.debug(f"[StateManager] Cache MISS: {key}")

        # Build fresh instance from factory
        generator = factory(symbol, timeframe)

        # 2) Try restore from Mongo checkpoint
        doc = self.db.generator_state.find_one({"key": key})

        if doc:
            logger.info(
                f"[StateManager] Restoring from checkpoint: {key} "
                f"(last_ts={doc.get('last_candle_ts')}, prices={len(doc.get('prices', []))}, "
                f"extra_keys={list((doc.get('extra') or {}).keys())})"
            )
            state_payload = {
                "prices": doc.get("prices", []),
                "last_candle_ts": doc.get("last_candle_ts"),
                "is_warm": doc.get("meta", {}).get("warm", False),
                "symbol": doc.get("symbol"),
                "timeframe": doc.get("timeframe"),
                # B.2: opaque strategy-specific payload (OHLC for long, etc.)
                "extra": doc.get("extra") or {},
            }
            if hasattr(generator, "from_state"):
                generator.from_state(state_payload)
            else:
                # Legacy attribute-based restore
                if hasattr(generator, "prices"):
                    generator.prices = state_payload["prices"]
                if hasattr(generator, "last_candle_ts"):
                    generator.last_candle_ts = state_payload["last_candle_ts"]
                if hasattr(generator, "is_warm"):
                    generator.is_warm = state_payload["is_warm"]
        else:
            # 3) Fresh warmup (only if caller provided candles)
            logger.info(f"[StateManager] Creating new generator: {key}")
            if warmup_candles and hasattr(generator, "warmup"):
                try:
                    generator.warmup(warmup_candles)
                    logger.info(
                        f"[StateManager] Warmed up {key} with {len(warmup_candles)} candles"
                    )
                except Exception as e:
                    logger.error(f"[StateManager] Warmup failed for {key}: {e}")

        self.cache[key] = generator
        return generator

    def save_checkpoint(
        self,
        strategy: str,
        symbol: str,
        timeframe: str,
        generator: Any,
        regime: Optional[str] = None,
    ) -> bool:
        """
        Persist generator state to MongoDB.

        Uses `generator.to_state()` if available, else reads attributes directly.

        B.2: preserves `extra` dict from `to_state()` output so strategies with
        non-float state (e.g. OHLC for long_pullback) can round-trip cleanly.
        """
        key = self._make_key(strategy, symbol, timeframe)

        try:
            extra: Dict[str, Any] = {}
            if hasattr(generator, "to_state"):
                state = generator.to_state()
                prices = state.get("prices", [])
                last_candle_ts = state.get("last_candle_ts")
                is_warm = state.get("is_warm", False)
                extra = state.get("extra") or {}
            else:
                prices = getattr(generator, "prices", [])
                last_candle_ts = getattr(generator, "last_candle_ts", None)
                is_warm = getattr(generator, "is_warm", False)

            # Normalize prices to a plain list of floats (deque → list)
            prices = [float(p) for p in list(prices)][-250:]

            checkpoint = {
                "key": key,
                "strategy": strategy,
                "symbol": symbol,
                "timeframe": timeframe,
                "last_candle_ts": last_candle_ts,
                "prices": prices,
                "meta": {
                    "warm": bool(is_warm),
                    "updated_at": datetime.now(timezone.utc),
                    "regime_at_last_update": regime,
                    "price_count": len(prices),
                },
                "extra": extra,  # B.2: opaque pass-through (e.g. ohlc_candles)
            }

            self.db.generator_state.update_one(
                {"key": key},
                {"$set": checkpoint},
                upsert=True,
            )
            logger.debug(
                f"[StateManager] Checkpoint saved: {key} "
                f"(last_ts={last_candle_ts}, prices={len(prices)}, "
                f"extra_keys={list(extra.keys())}, regime={regime})"
            )
            return True
        except Exception as e:
            logger.error(f"[StateManager] Checkpoint save failed for {key}: {e}")
            return False

    # --------------------------------------------------------------- #
    #  Introspection / admin
    # --------------------------------------------------------------- #
    def get_stats(self) -> Dict[str, Any]:
        return {
            "cache_size": len(self.cache),
            "cached_keys": list(self.cache.keys()),
            "checkpoint_count": self.db.generator_state.count_documents({}),
        }

    def clear_cache(self) -> None:
        logger.info(f"[StateManager] Clearing cache ({len(self.cache)} generators)")
        self.cache.clear()

    def delete_checkpoint(self, strategy: str, symbol: str, timeframe: str) -> bool:
        key = self._make_key(strategy, symbol, timeframe)
        result = self.db.generator_state.delete_one({"key": key})
        logger.info(
            f"[StateManager] Deleted checkpoint: {key} (deleted={result.deleted_count})"
        )
        return result.deleted_count > 0


# --------------------------------------------------------------- #
#  Singleton accessor
# --------------------------------------------------------------- #
_state_manager: Optional[GeneratorStateManager] = None


def get_state_manager(db, lane: Optional[str] = None) -> GeneratorStateManager:
    """
    Return process-wide singleton GeneratorStateManager.

    NOTE: First caller wins the db/lane binding. Pass a sync pymongo DB.
    `lane` isolates state between concurrent phase_c / discovery runs.
    """
    global _state_manager
    if _state_manager is None:
        _state_manager = GeneratorStateManager(db, lane=lane)
    return _state_manager


def reset_state_manager() -> None:
    """Reset singleton (useful for tests)."""
    global _state_manager
    _state_manager = None
