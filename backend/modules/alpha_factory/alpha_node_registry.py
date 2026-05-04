"""
PHASE 13.1 - Alpha Node Registry
=================================
Central registry for all alpha nodes in the system.

Manages:
- Node registration and lookup
- Node relationships (for Alpha Graph)
- Node inputs/outputs (for Alpha DAG)
- Node performance tracking
"""

from typing import List, Dict, Optional, Any
from datetime import datetime, timezone

from core.database import MongoRepository, get_database

from .alpha_types import (
    AlphaNode, NodeType, NodeStatus, NodeUsageRecord, 
    NodePerformanceRecord, DEFAULT_ALPHA_NODES
)

try:
    from pymongo import DESCENDING, ASCENDING
    MONGO_OK = True
except ImportError:
    MONGO_OK = False


class AlphaNodeRegistry(MongoRepository):
    """
    Alpha Node Registry - Central catalog of all system signals.
    
    Features:
    - CRUD operations for nodes
    - Node relationship management (for Alpha Graph)
    - Input/output tracking (for Alpha DAG)
    - Performance metrics storage
    """
    
    def __init__(self, auto_seed: bool = True):
        super().__init__()
        self.collection_name = "alpha_nodes"
        self._in_memory_cache: Dict[str, AlphaNode] = {}
        self._init_collections()
        
        if auto_seed:
            self._seed_default_nodes()
    
    def _init_collections(self):
        """Initialize MongoDB collections and indexes."""
        if not self.connected:
            print("[AlphaNodeRegistry] Running in memory-only mode")
            return
        
        try:
            db = self.db
            if db is None:
                return
            
            # Main nodes collection
            db.alpha_nodes.create_index([("node_id", 1)], unique=True)
            db.alpha_nodes.create_index([("node_type", 1)])
            db.alpha_nodes.create_index([("tags", 1)])
            db.alpha_nodes.create_index([("status", 1)])
            
            # Usage tracking
            db.alpha_node_usage.create_index([("node_id", 1), ("used_at", -1)])
            
            # Performance tracking
            db.alpha_node_performance.create_index([("node_id", 1), ("timestamp", -1)])
            
            # Relations (for Alpha Graph)
            db.alpha_node_relations.create_index([("source_node", 1)])
            db.alpha_node_relations.create_index([("target_node", 1)])
            
            print("[AlphaNodeRegistry] Indexes created")
            
        except Exception as e:
            print(f"[AlphaNodeRegistry] Index error: {e}")
    
    def _seed_default_nodes(self):
        """Seed default alpha nodes if not present."""
        try:
            existing_count = self.count_nodes()
            
            if existing_count < len(DEFAULT_ALPHA_NODES):
                seeded = 0
                for node in DEFAULT_ALPHA_NODES:
                    if not self.get_node(node.node_id):
                        node.created_at = datetime.now(timezone.utc)
                        self.register_node(node)
                        seeded += 1
                
                if seeded > 0:
                    print(f"[AlphaNodeRegistry] Seeded {seeded} default nodes")
            
        except Exception as e:
            print(f"[AlphaNodeRegistry] Seed error: {e}")
    
    # ===== CRUD Operations =====
    
    def register_node(self, node: AlphaNode) -> bool:
        """Register a new alpha node."""
        if not node.created_at:
            node.created_at = datetime.now(timezone.utc)
        
        # Update cache
        self._in_memory_cache[node.node_id] = node
        
        if not self.connected:
            return True
        
        try:
            doc = node.to_dict()
            doc["_created_at"] = datetime.now(timezone.utc)
            
            # Upsert to handle duplicates
            db = self.db
            if db is not None:
                db.alpha_nodes.update_one(
                    {"node_id": node.node_id},
                    {"$set": doc},
                    upsert=True
                )
            return True
            
        except Exception as e:
            print(f"[AlphaNodeRegistry] Register error: {e}")
            return False
    
    def get_node(self, node_id: str) -> Optional[AlphaNode]:
        """Get a node by ID."""
        # Check cache first
        if node_id in self._in_memory_cache:
            return self._in_memory_cache[node_id]
        
        if not self.connected:
            return None
        
        try:
            db = self.db
            if db is None:
                return None
            
            doc = db.alpha_nodes.find_one(
                {"node_id": node_id},
                {"_id": 0, "_created_at": 0}
            )
            
            if doc:
                node = AlphaNode.from_dict(doc)
                self._in_memory_cache[node_id] = node
                return node
            
            return None
            
        except Exception as e:
            print(f"[AlphaNodeRegistry] Get error: {e}")
            return None
    
    def update_node(self, node_id: str, updates: Dict) -> bool:
        """Update a node."""
        updates["updated_at"] = datetime.now(timezone.utc).isoformat()
        
        # Update cache
        if node_id in self._in_memory_cache:
            for key, value in updates.items():
                if hasattr(self._in_memory_cache[node_id], key):
                    setattr(self._in_memory_cache[node_id], key, value)
        
        if not self.connected:
            return True
        
        try:
            db = self.db
            if db is None:
                return False
            
            result = db.alpha_nodes.update_one(
                {"node_id": node_id},
                {"$set": updates}
            )
            return result.modified_count > 0
            
        except Exception as e:
            print(f"[AlphaNodeRegistry] Update error: {e}")
            return False
    
    def delete_node(self, node_id: str) -> bool:
        """Delete a node (marks as deprecated)."""
        # Remove from cache
        if node_id in self._in_memory_cache:
            del self._in_memory_cache[node_id]
        
        return self.update_node(node_id, {"status": NodeStatus.DEPRECATED.value})
    
    # ===== Query Operations =====
    
    def list_nodes(
        self,
        node_type: Optional[NodeType] = None,
        tags: Optional[List[str]] = None,
        status: NodeStatus = NodeStatus.ACTIVE,
        limit: int = 500
    ) -> List[AlphaNode]:
        """List nodes with optional filters."""
        
        # Build query
        query = {}
        if node_type:
            query["node_type"] = node_type.value
        if tags:
            query["tags"] = {"$in": tags}
        if status:
            query["status"] = status.value
        
        # Try database first
        if self.connected:
            try:
                db = self.db
                if db is not None:
                    cursor = db.alpha_nodes.find(
                        query,
                        {"_id": 0, "_created_at": 0}
                    ).limit(limit)
                    
                    return [AlphaNode.from_dict(doc) for doc in cursor]
                    
            except Exception as e:
                print(f"[AlphaNodeRegistry] List error: {e}")
        
        # Fallback to cache
        nodes = []
        for node in self._in_memory_cache.values():
            if node_type and node.node_type != node_type:
                continue
            if tags and not any(t in node.tags for t in tags):
                continue
            if status and node.status != status:
                continue
            nodes.append(node)
            if len(nodes) >= limit:
                break
        
        return nodes
    
    def get_nodes_by_type(self, node_type: NodeType) -> List[AlphaNode]:
        """Get all nodes of a specific type."""
        return self.list_nodes(node_type=node_type)
    
    def search_nodes(self, query: str, limit: int = 50) -> List[AlphaNode]:
        """Search nodes by text query."""
        query_lower = query.lower()
        
        if self.connected:
            try:
                db = self.db
                if db is not None:
                    cursor = db.alpha_nodes.find(
                        {
                            "$or": [
                                {"node_id": {"$regex": query, "$options": "i"}},
                                {"description": {"$regex": query, "$options": "i"}},
                                {"tags": {"$in": [query_lower]}}
                            ]
                        },
                        {"_id": 0}
                    ).limit(limit)
                    
                    return [AlphaNode.from_dict(doc) for doc in cursor]
                    
            except Exception as e:
                print(f"[AlphaNodeRegistry] Search error: {e}")
        
        # Fallback to cache
        results = []
        for node in self._in_memory_cache.values():
            if (query_lower in node.node_id.lower() or
                query_lower in node.description.lower() or
                any(query_lower in t for t in node.tags)):
                results.append(node)
                if len(results) >= limit:
                    break
        
        return results
    
    # ===== DAG Support =====
    
    def get_node_inputs(self, node_id: str) -> List[str]:
        """Get input dependencies for a node (for DAG)."""
        node = self.get_node(node_id)
        return node.inputs if node else []
    
    def get_node_outputs(self, node_id: str) -> List[str]:
        """Get outputs produced by a node (for DAG)."""
        node = self.get_node(node_id)
        return node.outputs if node else []
    
    def get_dependent_nodes(self, node_id: str) -> List[str]:
        """Get nodes that depend on this node's outputs."""
        node = self.get_node(node_id)
        if not node:
            return []
        
        outputs = set(node.outputs)
        dependents = []
        
        for other_node in self.list_nodes():
            if other_node.node_id == node_id:
                continue
            if outputs.intersection(set(other_node.inputs)):
                dependents.append(other_node.node_id)
        
        return dependents
    
    # ===== Graph Support =====
    
    def get_supporting_nodes(self, node_id: str) -> List[str]:
        """Get nodes that support this node."""
        node = self.get_node(node_id)
        return node.supports if node else []
    
    def get_contradicting_nodes(self, node_id: str) -> List[str]:
        """Get nodes that contradict this node."""
        node = self.get_node(node_id)
        return node.contradicts if node else []
    
    def get_node_relationships(self, node_id: str) -> Dict[str, List[str]]:
        """Get all relationships for a node."""
        node = self.get_node(node_id)
        if not node:
            return {}
        
        return {
            "supports": node.supports,
            "contradicts": node.contradicts,
            "amplifies": node.amplifies,
            "conditional_on": node.conditional_on
        }
    
    # ===== Usage & Performance =====
    
    def record_usage(self, node_id: str, used_in: str, context: Dict = None):
        """Record node usage."""
        record = NodeUsageRecord(
            node_id=node_id,
            used_in=used_in,
            used_at=datetime.now(timezone.utc),
            context=context or {}
        )
        
        if self.connected:
            try:
                db = self.db
                if db is not None:
                    db.alpha_node_usage.insert_one(record.to_dict())
            except Exception:
                pass
    
    def record_performance(
        self,
        node_id: str,
        hit_rate: float = 0.0,
        ic: float = 0.0,
        sharpe: float = 0.0,
        decay: float = 0.0
    ):
        """Record node performance metrics."""
        record = NodePerformanceRecord(
            node_id=node_id,
            timestamp=datetime.now(timezone.utc),
            hit_rate=hit_rate,
            information_coefficient=ic,
            sharpe_contribution=sharpe,
            decay_rate=decay
        )
        
        if self.connected:
            try:
                db = self.db
                if db is not None:
                    db.alpha_node_performance.insert_one(record.to_dict())
            except Exception:
                pass
    
    def get_node_performance(self, node_id: str, limit: int = 10) -> List[Dict]:
        """Get node performance history."""
        if not self.connected:
            return []
        
        try:
            db = self.db
            if db is None:
                return []
            
            cursor = db.alpha_node_performance.find(
                {"node_id": node_id},
                {"_id": 0}
            ).sort("timestamp", DESCENDING).limit(limit)
            
            return list(cursor)
            
        except Exception:
            return []
    
    # ===== Statistics =====
    
    def count_nodes(self, node_type: Optional[NodeType] = None) -> int:
        """Count nodes, optionally by type."""
        query = {}
        if node_type:
            query["node_type"] = node_type.value
        
        if self.connected:
            try:
                db = self.db
                if db is not None:
                    return db.alpha_nodes.count_documents(query)
            except Exception:
                pass
        
        # Fallback to cache
        if node_type:
            return sum(1 for n in self._in_memory_cache.values() if n.node_type == node_type)
        return len(self._in_memory_cache)
    
    def get_stats(self) -> Dict:
        """Get registry statistics."""
        stats = {
            "connected": self.connected,
            "total_nodes": 0,
            "nodes_by_type": {},
            "nodes_by_category": {},
            "active_nodes": 0
        }
        
        # Count by type
        for nt in NodeType:
            count = self.count_nodes(nt)
            stats["nodes_by_type"][nt.value] = count
            stats["total_nodes"] += count
        
        # Count active
        active_nodes = self.list_nodes(status=NodeStatus.ACTIVE)
        stats["active_nodes"] = len(active_nodes)
        
        # Count by category
        categories = {}
        for node in active_nodes:
            cat = node.category or "uncategorized"
            categories[cat] = categories.get(cat, 0) + 1
        stats["nodes_by_category"] = categories
        
        return stats
    
    def get_type_breakdown(self) -> Dict[str, int]:
        """Get count of nodes by type."""
        return {nt.value: self.count_nodes(nt) for nt in NodeType}


# Global singleton instance
_registry_instance: Optional[AlphaNodeRegistry] = None


def get_alpha_registry() -> AlphaNodeRegistry:
    """Get singleton registry instance."""
    global _registry_instance
    if _registry_instance is None:
        _registry_instance = AlphaNodeRegistry()
    return _registry_instance
