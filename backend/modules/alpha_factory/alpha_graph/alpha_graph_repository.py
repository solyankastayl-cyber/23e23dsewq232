"""
PHASE 13.5 - Alpha Graph Repository
====================================
MongoDB persistence for Alpha Graph.

Collections:
- alpha_graph_nodes
- alpha_graph_edges
- alpha_graph_snapshots
"""

from typing import Dict, List, Optional
from datetime import datetime, timezone

from core.database import MongoRepository, get_database

from .alpha_graph_types import GraphNode, GraphEdge, GraphSnapshot, RelationType


class GraphRepository(MongoRepository):
    """
    Repository for Alpha Graph data.
    """
    
    def __init__(self):
        super().__init__()
        self.collection_name = "alpha_graph_nodes"
        self._init_indexes()
    
    def _init_indexes(self):
        """Initialize MongoDB indexes."""
        if not self.connected:
            return
        
        try:
            db = self.db
            if db is None:
                return
            
            # Nodes collection
            db.alpha_graph_nodes.create_index([("node_id", 1)], unique=True)
            db.alpha_graph_nodes.create_index([("family", 1)])
            db.alpha_graph_nodes.create_index([("factor_id", 1)])
            
            # Edges collection
            db.alpha_graph_edges.create_index([("edge_id", 1)], unique=True)
            db.alpha_graph_edges.create_index([("source_node", 1)])
            db.alpha_graph_edges.create_index([("target_node", 1)])
            db.alpha_graph_edges.create_index([("relation_type", 1)])
            
            # Snapshots collection
            db.alpha_graph_snapshots.create_index([("snapshot_id", 1)], unique=True)
            db.alpha_graph_snapshots.create_index([("created_at", -1)])
            
            print("[GraphRepository] Indexes created")
            
        except Exception as e:
            print(f"[GraphRepository] Index error: {e}")
    
    # ===== Nodes =====
    
    def save_node(self, node: GraphNode) -> bool:
        """Save a graph node."""
        if not self.connected:
            return False
        
        try:
            db = self.db
            if db is None:
                return False
            
            doc = node.to_dict()
            db.alpha_graph_nodes.update_one(
                {"node_id": node.node_id},
                {"$set": doc},
                upsert=True
            )
            return True
            
        except Exception as e:
            print(f"[GraphRepository] Save node error: {e}")
            return False
    
    def get_node(self, node_id: str) -> Optional[GraphNode]:
        """Get a node by ID."""
        if not self.connected:
            return None
        
        try:
            db = self.db
            if db is None:
                return None
            
            doc = db.alpha_graph_nodes.find_one(
                {"node_id": node_id},
                {"_id": 0}
            )
            
            if doc:
                return GraphNode.from_dict(doc)
            return None
            
        except Exception as e:
            print(f"[GraphRepository] Get node error: {e}")
            return None
    
    def get_nodes(
        self,
        family: Optional[str] = None,
        limit: int = 100
    ) -> List[GraphNode]:
        """Get nodes with optional filter."""
        if not self.connected:
            return []
        
        try:
            db = self.db
            if db is None:
                return []
            
            query = {}
            if family:
                query["family"] = family
            
            cursor = db.alpha_graph_nodes.find(
                query,
                {"_id": 0}
            ).limit(limit)
            
            return [GraphNode.from_dict(doc) for doc in cursor]
            
        except Exception as e:
            print(f"[GraphRepository] Get nodes error: {e}")
            return []
    
    def count_nodes(self) -> int:
        """Count total nodes."""
        if not self.connected:
            return 0
        
        try:
            db = self.db
            if db is None:
                return 0
            return db.alpha_graph_nodes.count_documents({})
        except Exception:
            return 0
    
    # ===== Edges =====
    
    def save_edge(self, edge: GraphEdge) -> bool:
        """Save a graph edge."""
        if not self.connected:
            return False
        
        try:
            db = self.db
            if db is None:
                return False
            
            doc = edge.to_dict()
            db.alpha_graph_edges.update_one(
                {"edge_id": edge.edge_id},
                {"$set": doc},
                upsert=True
            )
            return True
            
        except Exception as e:
            print(f"[GraphRepository] Save edge error: {e}")
            return False
    
    def get_edge(self, edge_id: str) -> Optional[GraphEdge]:
        """Get an edge by ID."""
        if not self.connected:
            return None
        
        try:
            db = self.db
            if db is None:
                return None
            
            doc = db.alpha_graph_edges.find_one(
                {"edge_id": edge_id},
                {"_id": 0}
            )
            
            if doc:
                return GraphEdge.from_dict(doc)
            return None
            
        except Exception as e:
            print(f"[GraphRepository] Get edge error: {e}")
            return None
    
    def get_edges(
        self,
        relation_type: Optional[RelationType] = None,
        source_node: Optional[str] = None,
        target_node: Optional[str] = None,
        limit: int = 500
    ) -> List[GraphEdge]:
        """Get edges with filters."""
        if not self.connected:
            return []
        
        try:
            db = self.db
            if db is None:
                return []
            
            query = {}
            if relation_type:
                query["relation_type"] = relation_type.value
            if source_node:
                query["source_node"] = source_node
            if target_node:
                query["target_node"] = target_node
            
            cursor = db.alpha_graph_edges.find(
                query,
                {"_id": 0}
            ).limit(limit)
            
            return [GraphEdge.from_dict(doc) for doc in cursor]
            
        except Exception as e:
            print(f"[GraphRepository] Get edges error: {e}")
            return []
    
    def count_edges(self) -> int:
        """Count total edges."""
        if not self.connected:
            return 0
        
        try:
            db = self.db
            if db is None:
                return 0
            return db.alpha_graph_edges.count_documents({})
        except Exception:
            return 0
    
    def count_edges_by_type(self) -> Dict[str, int]:
        """Count edges by relation type."""
        if not self.connected:
            return {}
        
        try:
            db = self.db
            if db is None:
                return {}
            
            pipeline = [
                {"$group": {"_id": "$relation_type", "count": {"$sum": 1}}}
            ]
            
            result = {}
            for doc in db.alpha_graph_edges.aggregate(pipeline):
                result[doc["_id"]] = doc["count"]
            
            return result
            
        except Exception as e:
            print(f"[GraphRepository] Count edges error: {e}")
            return {}
    
    # ===== Snapshots =====
    
    def save_snapshot(self, snapshot: GraphSnapshot) -> bool:
        """Save a graph snapshot."""
        if not self.connected:
            return False
        
        try:
            db = self.db
            if db is None:
                return False
            
            doc = snapshot.to_dict()
            db.alpha_graph_snapshots.update_one(
                {"snapshot_id": snapshot.snapshot_id},
                {"$set": doc},
                upsert=True
            )
            return True
            
        except Exception as e:
            print(f"[GraphRepository] Save snapshot error: {e}")
            return False
    
    def get_snapshots(self, limit: int = 10) -> List[Dict]:
        """Get recent snapshots."""
        if not self.connected:
            return []
        
        try:
            db = self.db
            if db is None:
                return []
            
            cursor = db.alpha_graph_snapshots.find(
                {},
                {"_id": 0}
            ).sort("created_at", -1).limit(limit)
            
            return list(cursor)
            
        except Exception as e:
            print(f"[GraphRepository] Get snapshots error: {e}")
            return []
    
    # ===== Clear =====
    
    def clear_graph(self) -> Dict[str, int]:
        """Clear all graph data."""
        if not self.connected:
            return {}
        
        try:
            db = self.db
            if db is None:
                return {}
            
            nodes_deleted = db.alpha_graph_nodes.delete_many({}).deleted_count
            edges_deleted = db.alpha_graph_edges.delete_many({}).deleted_count
            
            return {
                "nodes_deleted": nodes_deleted,
                "edges_deleted": edges_deleted
            }
            
        except Exception as e:
            print(f"[GraphRepository] Clear error: {e}")
            return {}
    
    # ===== Stats =====
    
    def get_stats(self) -> Dict:
        """Get repository statistics."""
        if not self.connected:
            return {"connected": False}
        
        try:
            db = self.db
            if db is None:
                return {"connected": False}
            
            nodes_count = self.count_nodes()
            edges_count = self.count_edges()
            edges_by_type = self.count_edges_by_type()
            snapshots_count = db.alpha_graph_snapshots.count_documents({})
            
            # Nodes by family
            pipeline = [
                {"$group": {"_id": "$family", "count": {"$sum": 1}}}
            ]
            nodes_by_family = {}
            for doc in db.alpha_graph_nodes.aggregate(pipeline):
                nodes_by_family[doc["_id"]] = doc["count"]
            
            return {
                "connected": True,
                "total_nodes": nodes_count,
                "total_edges": edges_count,
                "edges_by_type": edges_by_type,
                "nodes_by_family": nodes_by_family,
                "total_snapshots": snapshots_count
            }
            
        except Exception as e:
            return {"connected": True, "error": str(e)}
