"""
PHASE 13.6 - Alpha DAG Cache
==============================
Caching layer for DAG node values.

Features:
1. Input hash validation
2. Automatic invalidation
3. Hit rate tracking
4. Memory management
"""

from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
from collections import OrderedDict
import hashlib
import json

from .dag_types import CacheEntry


class DagCache:
    """
    Cache layer for DAG computations.
    
    Uses input hashing to determine if cached values are still valid.
    When inputs haven't changed, returns cached value instead of recomputing.
    """
    
    def __init__(self, max_size: int = 10000):
        """
        Initialize cache.
        
        Args:
            max_size: Maximum number of entries to cache
        """
        self.max_size = max_size
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        
        # Statistics
        self.total_hits = 0
        self.total_misses = 0
        self.total_invalidations = 0
    
    def _compute_input_hash(self, inputs: Dict[str, Any]) -> str:
        """
        Compute hash of input values.
        
        Args:
            inputs: Dictionary of input node_id -> value
        
        Returns:
            Hash string
        """
        # Sort keys for consistent hashing
        sorted_items = sorted(inputs.items())
        
        # Handle different value types
        normalized = []
        for key, value in sorted_items:
            if isinstance(value, float):
                # Round floats to avoid precision issues
                normalized.append((key, round(value, 10)))
            else:
                normalized.append((key, value))
        
        hash_input = json.dumps(normalized, sort_keys=True)
        return hashlib.md5(hash_input.encode()).hexdigest()
    
    def get(self, node_id: str, input_values: Dict[str, Any]) -> Optional[Any]:
        """
        Get cached value if valid.
        
        Args:
            node_id: Node ID to look up
            input_values: Current input values for hash comparison
        
        Returns:
            Cached value if valid, None otherwise
        """
        if node_id not in self._cache:
            self.total_misses += 1
            return None
        
        entry = self._cache[node_id]
        current_hash = self._compute_input_hash(input_values)
        
        if entry.is_valid(current_hash):
            # Cache hit - update stats and move to end (LRU)
            self.total_hits += 1
            entry.hits += 1
            self._cache.move_to_end(node_id)
            return entry.value
        else:
            # Cache miss - hash changed
            self.total_misses += 1
            self.total_invalidations += 1
            return None
    
    def set(self, node_id: str, input_values: Dict[str, Any], value: Any):
        """
        Set cached value.
        
        Args:
            node_id: Node ID to cache
            input_values: Input values for hash
            value: Computed value to cache
        """
        input_hash = self._compute_input_hash(input_values)
        
        entry = CacheEntry(
            node_id=node_id,
            input_hash=input_hash,
            value=value,
            timestamp=datetime.now(timezone.utc),
            hits=0
        )
        
        self._cache[node_id] = entry
        self._cache.move_to_end(node_id)
        
        # Evict oldest entries if over capacity
        while len(self._cache) > self.max_size:
            self._cache.popitem(last=False)
    
    def invalidate(self, node_id: str):
        """
        Invalidate cache entry for a node.
        
        Args:
            node_id: Node ID to invalidate
        """
        if node_id in self._cache:
            del self._cache[node_id]
            self.total_invalidations += 1
    
    def invalidate_all(self):
        """Invalidate all cache entries."""
        count = len(self._cache)
        self._cache.clear()
        self.total_invalidations += count
    
    def invalidate_dependent(self, node_id: str, dependencies: Dict[str, List[str]]):
        """
        Invalidate a node and all nodes that depend on it.
        
        Args:
            node_id: Node ID to invalidate
            dependencies: Map of node_id -> list of dependent node_ids
        """
        to_invalidate = {node_id}
        queue = [node_id]
        
        while queue:
            current = queue.pop(0)
            for dependent in dependencies.get(current, []):
                if dependent not in to_invalidate:
                    to_invalidate.add(dependent)
                    queue.append(dependent)
        
        for nid in to_invalidate:
            self.invalidate(nid)
    
    def get_hit_rate(self) -> float:
        """Get cache hit rate."""
        total = self.total_hits + self.total_misses
        return self.total_hits / total if total > 0 else 0.0
    
    def get_stats(self) -> Dict:
        """Get cache statistics."""
        return {
            "size": len(self._cache),
            "max_size": self.max_size,
            "total_hits": self.total_hits,
            "total_misses": self.total_misses,
            "total_invalidations": self.total_invalidations,
            "hit_rate": self.get_hit_rate(),
            "utilization": len(self._cache) / self.max_size if self.max_size > 0 else 0.0
        }
    
    def get_top_hits(self, n: int = 10) -> List[Dict]:
        """Get top N most frequently hit cache entries."""
        sorted_entries = sorted(
            self._cache.values(),
            key=lambda e: e.hits,
            reverse=True
        )[:n]
        
        return [
            {
                "node_id": e.node_id,
                "hits": e.hits,
                "timestamp": e.timestamp.isoformat()
            }
            for e in sorted_entries
        ]
    
    def reset_stats(self):
        """Reset statistics counters."""
        self.total_hits = 0
        self.total_misses = 0
        self.total_invalidations = 0
        
        for entry in self._cache.values():
            entry.hits = 0


class StreamingCache(DagCache):
    """
    Extended cache for streaming/tick-by-tick execution.
    
    Optimized for high-frequency updates with:
    - Time-based expiration
    - Differential updates
    - Warm-up tracking
    """
    
    def __init__(self, max_size: int = 10000, ttl_seconds: float = 60.0):
        """
        Initialize streaming cache.
        
        Args:
            max_size: Maximum entries
            ttl_seconds: Time-to-live for entries
        """
        super().__init__(max_size)
        self.ttl_seconds = ttl_seconds
        
        # Track warm-up state
        self._warm_nodes: set = set()
        self._last_tick_time: Optional[datetime] = None
    
    def get(self, node_id: str, input_values: Dict[str, Any]) -> Optional[Any]:
        """Get with TTL check."""
        if node_id not in self._cache:
            self.total_misses += 1
            return None
        
        entry = self._cache[node_id]
        
        # Check TTL
        age = (datetime.now(timezone.utc) - entry.timestamp).total_seconds()
        if age > self.ttl_seconds:
            self.invalidate(node_id)
            self.total_misses += 1
            return None
        
        # Check hash
        current_hash = self._compute_input_hash(input_values)
        
        if entry.is_valid(current_hash):
            self.total_hits += 1
            entry.hits += 1
            self._cache.move_to_end(node_id)
            return entry.value
        else:
            self.total_misses += 1
            return None
    
    def record_tick(self):
        """Record a new market tick."""
        self._last_tick_time = datetime.now(timezone.utc)
    
    def mark_warm(self, node_id: str):
        """Mark a node as warmed up (has been computed at least once)."""
        self._warm_nodes.add(node_id)
    
    def is_warm(self, node_id: str) -> bool:
        """Check if a node is warmed up."""
        return node_id in self._warm_nodes
    
    def get_warm_ratio(self, total_nodes: int) -> float:
        """Get ratio of warmed up nodes."""
        return len(self._warm_nodes) / total_nodes if total_nodes > 0 else 0.0
    
    def get_stats(self) -> Dict:
        """Get extended statistics."""
        stats = super().get_stats()
        stats.update({
            "ttl_seconds": self.ttl_seconds,
            "warm_nodes": len(self._warm_nodes),
            "last_tick_time": self._last_tick_time.isoformat() if self._last_tick_time else None
        })
        return stats
