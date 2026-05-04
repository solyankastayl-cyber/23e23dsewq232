"""
PHASE 13.6 - Alpha DAG Repository
===================================
MongoDB persistence for Alpha DAG.

Collections:
- alpha_dag_nodes
- alpha_dag_edges
- alpha_dag_snapshots
"""

from typing import Dict, List, Optional
from datetime import datetime, timezone

from core.database import MongoRepository, get_database

from .dag_types import DagNode, DagEdge, DagSnapshot, NodeType


class DagRepository(MongoRepository):
    """
    Repository for Alpha DAG data.
    """
    
    def __init__(self):
        super().__init__()
        self.collection_name = "alpha_dag_nodes"
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
            db.alpha_dag_nodes.create_index([("node_id", 1)], unique=True)
            db.alpha_dag_nodes.create_index([("node_type", 1)])
            db.alpha_dag_nodes.create_index([("level", 1)])
            db.alpha_dag_nodes.create_index([("source_factor_id", 1)])
            
            # Edges collection
            db.alpha_dag_edges.create_index([("edge_id", 1)], unique=True)
            db.alpha_dag_edges.create_index([("source_node", 1)])
            db.alpha_dag_edges.create_index([("target_node", 1)])
            
            # Snapshots collection
            db.alpha_dag_snapshots.create_index([("snapshot_id", 1)], unique=True)
            db.alpha_dag_snapshots.create_index([("created_at", -1)])
            
            print("[DagRepository] Indexes created")
            
        except Exception as e:
            print(f"[DagRepository] Index error: {e}")
    
    # ===== Nodes =====
    
    def save_node(self, node: DagNode) -> bool:
        """Save a DAG node."""
        if not self.connected:
            return False
        
        try:
            db = self.db
            if db is None:
                return False
            
            doc = node.to_dict()
            db.alpha_dag_nodes.update_one(
                {"node_id": node.node_id},
                {"$set": doc},
                upsert=True
            )
            return True
            
        except Exception as e:
            print(f"[DagRepository] Save node error: {e}")
            return False
    
    def save_nodes_bulk(self, nodes: List[DagNode]) -> int:
        """Save multiple nodes in bulk."""
        if not self.connected or not nodes:
            return 0
        
        try:
            db = self.db
            if db is None:
                return 0
            
            from pymongo import UpdateOne
            
            operations = [
                UpdateOne(
                    {"node_id": node.node_id},
                    {"$set": node.to_dict()},
                    upsert=True
                )
                for node in nodes
            ]
            
            result = db.alpha_dag_nodes.bulk_write(operations)
            return result.upserted_count + result.modified_count
            
        except Exception as e:
            print(f"[DagRepository] Bulk save error: {e}")
            return 0
    
    def get_node(self, node_id: str) -> Optional[DagNode]:
        """Get a node by ID."""
        if not self.connected:
            return None
        
        try:
            db = self.db
            if db is None:
                return None
            
            doc = db.alpha_dag_nodes.find_one(
                {"node_id": node_id},
                {"_id": 0}
            )
            
            if doc:
                return DagNode.from_dict(doc)
            return None
            
        except Exception as e:
            print(f"[DagRepository] Get node error: {e}")
            return None
    
    def get_nodes(
        self,
        node_type: Optional[NodeType] = None,
        level: Optional[int] = None,
        limit: int = 500
    ) -> List[DagNode]:
        """Get nodes with optional filters."""
        if not self.connected:
            return []
        
        try:
            db = self.db
            if db is None:
                return []
            
            query = {}
            if node_type:
                query["node_type"] = node_type.value
            if level is not None:
                query["level"] = level
            
            cursor = db.alpha_dag_nodes.find(
                query,
                {"_id": 0}
            ).sort("execution_order", 1).limit(limit)
            
            return [DagNode.from_dict(doc) for doc in cursor]
            
        except Exception as e:
            print(f"[DagRepository] Get nodes error: {e}")
            return []
    
    def count_nodes(self) -> int:
        """Count total nodes."""
        if not self.connected:
            return 0
        
        try:
            db = self.db
            if db is None:
                return 0
            return db.alpha_dag_nodes.count_documents({})
        except Exception:
            return 0
    
    def count_nodes_by_type(self) -> Dict[str, int]:
        """Count nodes by type."""
        if not self.connected:
            return {}
        
        try:
            db = self.db
            if db is None:
                return {}
            
            pipeline = [
                {"$group": {"_id": "$node_type", "count": {"$sum": 1}}}
            ]
            
            result = {}
            for doc in db.alpha_dag_nodes.aggregate(pipeline):
                result[doc["_id"]] = doc["count"]
            
            return result
            
        except Exception as e:
            print(f"[DagRepository] Count by type error: {e}")
            return {}
    
    # ===== Edges =====
    
    def save_edge(self, edge: DagEdge) -> bool:
        """Save a DAG edge."""
        if not self.connected:
            return False
        
        try:
            db = self.db
            if db is None:
                return False
            
            doc = edge.to_dict()
            db.alpha_dag_edges.update_one(
                {"edge_id": edge.edge_id},
                {"$set": doc},
                upsert=True
            )
            return True
            
        except Exception as e:
            print(f"[DagRepository] Save edge error: {e}")
            return False
    
    def save_edges_bulk(self, edges: List[DagEdge]) -> int:
        """Save multiple edges in bulk."""
        if not self.connected or not edges:
            return 0
        
        try:
            db = self.db
            if db is None:
                return 0
            
            from pymongo import UpdateOne
            
            operations = [
                UpdateOne(
                    {"edge_id": edge.edge_id},
                    {"$set": edge.to_dict()},
                    upsert=True
                )
                for edge in edges
            ]
            
            result = db.alpha_dag_edges.bulk_write(operations)
            return result.upserted_count + result.modified_count
            
        except Exception as e:
            print(f"[DagRepository] Bulk save edges error: {e}")
            return 0
    
    def get_edge(self, edge_id: str) -> Optional[DagEdge]:
        """Get an edge by ID."""
        if not self.connected:
            return None
        
        try:
            db = self.db
            if db is None:
                return None
            
            doc = db.alpha_dag_edges.find_one(
                {"edge_id": edge_id},
                {"_id": 0}
            )
            
            if doc:
                return DagEdge.from_dict(doc)
            return None
            
        except Exception as e:
            print(f"[DagRepository] Get edge error: {e}")
            return None
    
    def get_edges(
        self,
        source_node: Optional[str] = None,
        target_node: Optional[str] = None,
        limit: int = 1000
    ) -> List[DagEdge]:
        """Get edges with optional filters."""
        if not self.connected:
            return []
        
        try:
            db = self.db
            if db is None:
                return []
            
            query = {}
            if source_node:
                query["source_node"] = source_node
            if target_node:
                query["target_node"] = target_node
            
            cursor = db.alpha_dag_edges.find(
                query,
                {"_id": 0}
            ).limit(limit)
            
            return [DagEdge.from_dict(doc) for doc in cursor]
            
        except Exception as e:
            print(f"[DagRepository] Get edges error: {e}")
            return []
    
    def count_edges(self) -> int:
        """Count total edges."""
        if not self.connected:
            return 0
        
        try:
            db = self.db
            if db is None:
                return 0
            return db.alpha_dag_edges.count_documents({})
        except Exception:
            return 0
    
    # ===== Snapshots =====
    
    def save_snapshot(self, snapshot: DagSnapshot) -> bool:
        """Save a DAG snapshot."""
        if not self.connected:
            return False
        
        try:
            db = self.db
            if db is None:
                return False
            
            doc = snapshot.to_dict()
            db.alpha_dag_snapshots.update_one(
                {"snapshot_id": snapshot.snapshot_id},
                {"$set": doc},
                upsert=True
            )
            return True
            
        except Exception as e:
            print(f"[DagRepository] Save snapshot error: {e}")
            return False
    
    def get_snapshots(self, limit: int = 10) -> List[Dict]:
        """Get recent snapshots."""
        if not self.connected:
            return []
        
        try:
            db = self.db
            if db is None:
                return []
            
            cursor = db.alpha_dag_snapshots.find(
                {},
                {"_id": 0}
            ).sort("created_at", -1).limit(limit)
            
            return list(cursor)
            
        except Exception as e:
            print(f"[DagRepository] Get snapshots error: {e}")
            return []
    
    # ===== Clear =====
    
    def clear_dag(self) -> Dict[str, int]:
        """Clear all DAG data."""
        if not self.connected:
            return {}
        
        try:
            db = self.db
            if db is None:
                return {}
            
            nodes_deleted = db.alpha_dag_nodes.delete_many({}).deleted_count
            edges_deleted = db.alpha_dag_edges.delete_many({}).deleted_count
            
            return {
                "nodes_deleted": nodes_deleted,
                "edges_deleted": edges_deleted
            }
            
        except Exception as e:
            print(f"[DagRepository] Clear error: {e}")
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
            nodes_by_type = self.count_nodes_by_type()
            snapshots_count = db.alpha_dag_snapshots.count_documents({})
            
            # Get depth
            max_level = 0
            max_doc = db.alpha_dag_nodes.find_one(
                {},
                {"level": 1, "_id": 0},
                sort=[("level", -1)]
            )
            if max_doc:
                max_level = max_doc.get("level", 0) + 1
            
            return {
                "connected": True,
                "total_nodes": nodes_count,
                "total_edges": edges_count,
                "depth": max_level,
                "nodes_by_type": nodes_by_type,
                "total_snapshots": snapshots_count
            }
            
        except Exception as e:
            return {"connected": True, "error": str(e)}
