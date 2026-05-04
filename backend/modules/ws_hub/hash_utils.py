"""
Hash utilities for WebSocket snapshot debouncing
Sprint WS-3: Stable hash generation for broadcast deduplication
"""

import hashlib
import json
import logging
from typing import Any

logger = logging.getLogger(__name__)


def stable_hash(obj: Any) -> str:
    """
    Generate stable MD5 hash for any object.
    
    Uses stable JSON serialization:
    - sort_keys=True: deterministic key ordering
    - default=str: handle non-serializable types (datetime, Decimal, etc.)
    - separators=(',', ':'): no whitespace (compact + deterministic)
    
    Args:
        obj: Any JSON-serializable object (dict, list, primitives)
    
    Returns:
        str: MD5 hash hex digest (32 chars)
    
    Example:
        >>> stable_hash({"b": 2, "a": 1})
        'abc123...'
        >>> stable_hash({"a": 1, "b": 2})
        'abc123...'  # Same hash despite different key order
    """
    try:
        # Stable JSON serialization
        json_str = json.dumps(
            obj,
            sort_keys=True,
            default=str,
            separators=(',', ':')
        )
        
        # MD5 hash
        hash_obj = hashlib.md5(json_str.encode('utf-8'))
        return hash_obj.hexdigest()
    
    except Exception as e:
        logger.error(f"[stable_hash] Failed to hash object: {e}")
        # Fallback: return empty hash (will always trigger broadcast)
        return ""


class SnapshotDebouncer:
    """
    Debouncer for WebSocket snapshot broadcasts.
    
    Tracks last hash per channel and prevents duplicate broadcasts.
    """
    
    def __init__(self):
        self._last_hashes = {}
    
    def should_broadcast(self, channel: str, data: Any) -> bool:
        """
        Check if snapshot should be broadcast.
        
        Args:
            channel: Channel name (e.g., "portfolio.summary")
            data: Snapshot data
        
        Returns:
            bool: True if hash changed (should broadcast), False otherwise
        """
        current_hash = stable_hash(data)
        last_hash = self._last_hashes.get(channel)
        
        if current_hash != last_hash:
            self._last_hashes[channel] = current_hash
            last_hash_short = last_hash[:8] if last_hash else "None"
            logger.debug(f"[Debouncer] {channel}: hash changed ({last_hash_short}→{current_hash[:8]}), will broadcast")
            return True
        
        logger.debug(f"[Debouncer] {channel}: hash unchanged ({current_hash[:8]}), skip broadcast")
        return False
    
    def reset(self, channel: str = None):
        """
        Reset debounce state.
        
        Args:
            channel: Specific channel to reset, or None to reset all
        """
        if channel:
            self._last_hashes.pop(channel, None)
            logger.debug(f"[Debouncer] Reset: {channel}")
        else:
            self._last_hashes.clear()
            logger.debug("[Debouncer] Reset: all channels")
