"""
Hybrid Temporal Buffer — Step 9.

RAM: per (symbol, tf) ring of last N FeatureSnapshot dicts (O(1) push/last).
Mongo: append-only checkpoint collection for durability and cold-start recovery.

Contract:
  * push() is fire-and-forget from the callers POV — always non-blocking
    for the hot path; Mongo flushes happen on checkpoint boundaries only.
  * On first access for a (symbol, tf) pair, cold-loads last `window` snapshots
    from Mongo in sorted-ascending order (so .last() returns the most recent).
  * Thread-safety: a single reentrant lock protects both the deque and the
    pending-flush list. Mongo I/O is done OUTSIDE the lock to avoid blocking.
  * No background timer. No random. Deterministic.

Mongo collection: ta_prediction_temporal_buffer
  index: (symbol, tf, ts desc)

Snapshot shape (what push expects):
  {
    'ts': int|None,
    'symbol': str,
    'tf': str,
    'features': dict[str, Any],
    'feature_hash': str,
    'feature_version': str,
    'feature_schema_hash': str,
    'builder_version': str,
    'states': {'trend': 'range|weak_trend|...', 'momentum': ..., 'volatility': ...},
  }
"""
from __future__ import annotations

import threading
import time
from collections import deque
from typing import Any, Deque, Dict, List, Optional, Tuple

from .feature_schema import DEFAULT_WINDOW

CHECKPOINT_EVERY_N = 10
COL_TEMPORAL = "ta_prediction_temporal_buffer"


class HybridTemporalBuffer:
    def __init__(self, window: int = DEFAULT_WINDOW, db_provider=None):
        self.window = int(window)
        self.buffers: Dict[Tuple[str, str], Deque[Dict[str, Any]]] = {}
        self.push_count: Dict[Tuple[str, str], int] = {}
        self._pending: Dict[Tuple[str, str], List[Dict[str, Any]]] = {}
        self._loaded_from_mongo: set = set()
        self._lock = threading.RLock()
        self._checkpoints = 0
        self._checkpoint_errors = 0
        self._last_checkpoint_ts: Optional[float] = None
        self._db_provider = db_provider  # for DI in tests

    # ------------------------------------------------------------------
    # DB helpers
    # ------------------------------------------------------------------
    def _db(self):
        if self._db_provider is not None:
            try:
                return self._db_provider()
            except Exception:
                return None
        try:
            from core.database import get_database
            return get_database()
        except Exception:
            return None

    def _col(self):
        db = self._db()
        if db is None:
            return None
        try:
            col = db[COL_TEMPORAL]
            # idempotent index creation
            try:
                col.create_index(
                    [("symbol", 1), ("tf", 1), ("ts", -1)], name="by_sym_tf_ts"
                )
            except Exception:
                pass
            return col
        except Exception:
            return None

    # ------------------------------------------------------------------
    # Lazy cold-load
    # ------------------------------------------------------------------
    def _ensure_loaded(self, symbol: str, tf: str) -> None:
        key = (symbol, tf)
        if key in self._loaded_from_mongo:
            return
        # Try load last `window` docs in ascending order.
        col = self._col()
        if col is None:
            self._loaded_from_mongo.add(key)
            return
        try:
            cur = (
                col.find({"symbol": symbol, "tf": tf})
                .sort("ts", -1)
                .limit(self.window)
            )
            docs = list(cur)
        except Exception:
            docs = []
        docs.reverse()  # now ascending by ts
        buf = self.buffers.setdefault(key, deque(maxlen=self.window))
        for d in docs:
            # strip mongo _id from re-populated cache
            d.pop("_id", None)
            buf.append(d)
        self._loaded_from_mongo.add(key)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def push(self, symbol: str, tf: str, snapshot: Dict[str, Any]) -> None:
        """Append a snapshot; maybe flush to Mongo. Never raises on Mongo error.

        Idempotent w.r.t. (symbol, tf, ts): if a snapshot with the same ts is
        already at the tail, REPLACE it in-place instead of appending. This
        keeps the buffer anchored on bars (not on calls), which is required for
        deterministic feature_hash (FIX PIPELINE bug #2).
        """
        key = (symbol.upper(), tf.upper())
        snap = dict(snapshot)
        snap.setdefault("symbol", key[0])
        snap.setdefault("tf", key[1])
        flushables: Optional[List[Dict[str, Any]]] = None
        with self._lock:
            self._ensure_loaded(*key)
            buf = self.buffers.setdefault(key, deque(maxlen=self.window))
            snap_ts = snap.get("ts")
            # Idempotent replace if last entry shares the same ts.
            if (
                snap_ts is not None
                and buf
                and buf[-1].get("ts") == snap_ts
            ):
                buf[-1] = snap
                # Replace the latest pending too (don't double-write to Mongo).
                pending = self._pending.setdefault(key, [])
                if pending and pending[-1].get("ts") == snap_ts:
                    pending[-1] = snap
                # No push_count increment, no checkpoint trigger.
                return
            buf.append(snap)
            self.push_count[key] = self.push_count.get(key, 0) + 1
            pending = self._pending.setdefault(key, [])
            pending.append(snap)
            if self.push_count[key] % CHECKPOINT_EVERY_N == 0:
                flushables = pending[:]
                self._pending[key] = []
        if flushables is not None:
            self._flush(flushables)

    def prev_bar(self, symbol: str, tf: str, current_ts: Optional[int]) -> Optional[Dict[str, Any]]:
        """Return the most recent buffered snapshot whose ts < current_ts.

        Used by feature_builder so transitions are computed against the prior
        BAR, not the prior CALL. None if no eligible prior snapshot exists.
        """
        key = (symbol.upper(), tf.upper())
        with self._lock:
            self._ensure_loaded(*key)
            buf = self.buffers.get(key)
            if not buf:
                return None
            # Walk from most recent backwards.
            for snap in reversed(buf):
                snap_ts = snap.get("ts")
                if current_ts is None:
                    if snap_ts is None:
                        continue
                    return snap
                if snap_ts is None:
                    continue
                if snap_ts < current_ts:
                    return snap
            return None

    def get(self, symbol: str, tf: str) -> List[Dict[str, Any]]:
        key = (symbol.upper(), tf.upper())
        with self._lock:
            self._ensure_loaded(*key)
            return list(self.buffers.get(key, ()))

    def last(self, symbol: str, tf: str) -> Optional[Dict[str, Any]]:
        key = (symbol.upper(), tf.upper())
        with self._lock:
            self._ensure_loaded(*key)
            buf = self.buffers.get(key)
            if not buf:
                return None
            return buf[-1]

    def size(self, symbol: str, tf: str) -> int:
        key = (symbol.upper(), tf.upper())
        with self._lock:
            self._ensure_loaded(*key)
            return len(self.buffers.get(key, ()))

    def status(self) -> Dict[str, Any]:
        with self._lock:
            out: Dict[str, Any] = {
                "window": self.window,
                "checkpoint_every_n": CHECKPOINT_EVERY_N,
                "checkpoints": self._checkpoints,
                "checkpoint_errors": self._checkpoint_errors,
                "last_checkpoint_ts": self._last_checkpoint_ts,
                "pairs": [],
            }
            for key, buf in self.buffers.items():
                last = buf[-1] if buf else None
                out["pairs"].append({
                    "symbol": key[0],
                    "tf": key[1],
                    "size": len(buf),
                    "push_count": self.push_count.get(key, 0),
                    "pending": len(self._pending.get(key, [])),
                    "last_ts": (last or {}).get("ts"),
                    "last_feature_hash": (last or {}).get("feature_hash"),
                })
            return out

    def flush_all(self) -> int:
        """Force flush any pending items. Returns number of snapshots written."""
        with self._lock:
            all_pending: List[Dict[str, Any]] = []
            for key in list(self._pending.keys()):
                all_pending.extend(self._pending[key])
                self._pending[key] = []
        if not all_pending:
            return 0
        self._flush(all_pending)
        return len(all_pending)

    # ------------------------------------------------------------------
    # Internal flush
    # ------------------------------------------------------------------
    def _flush(self, snapshots: List[Dict[str, Any]]) -> None:
        if not snapshots:
            return
        col = self._col()
        if col is None:
            # No Mongo — record counters anyway for visibility.
            self._checkpoint_errors += 1
            return
        try:
            to_write = [dict(s) for s in snapshots]
            col.insert_many(to_write, ordered=False)
            self._checkpoints += 1
            self._last_checkpoint_ts = time.time()
        except Exception:
            self._checkpoint_errors += 1


# Process-wide singleton -----------------------------------------------------
_buffer_singleton: Optional[HybridTemporalBuffer] = None


def get_temporal_buffer() -> HybridTemporalBuffer:
    global _buffer_singleton
    if _buffer_singleton is None:
        _buffer_singleton = HybridTemporalBuffer()
    return _buffer_singleton
