"""
PHASE 6.4 - Edge Repository
============================
Persistence layer for discovered edges.
"""

from datetime import datetime, timezone
from typing import Dict, List, Optional
from pymongo import MongoClient
from pymongo.database import Database
import os

from .edge_types import (
    EdgeCandidate, EdgeValidation, DiscoveredEdge,
    EdgeStatus, EdgeCategory
)


class EdgeRepository:
    """
    Repository for persisting edge discovery data.
    """
    
    def __init__(self, db: Database = None):
        if db is None:
            mongo_url = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
            db_name = os.environ.get("DB_NAME", "ta_engine")
            client = MongoClient(mongo_url)
            db = client[db_name]
        
        self.db = db
        self._ensure_collections()
    
    def _ensure_collections(self):
        """Ensure collections and indexes exist"""
        # Candidates collection
        if "edge_candidates" not in self.db.list_collection_names():
            self.db.create_collection("edge_candidates")
        
        self.db.edge_candidates.create_index("edge_id", unique=True)
        self.db.edge_candidates.create_index("status")
        self.db.edge_candidates.create_index("category")
        
        # Validated edges collection
        if "discovered_edges" not in self.db.list_collection_names():
            self.db.create_collection("discovered_edges")
        
        self.db.discovered_edges.create_index("edge_id", unique=True)
        self.db.discovered_edges.create_index("status")
        self.db.discovered_edges.create_index([("composite_score", -1)])
        self.db.discovered_edges.create_index([("rank", 1)])
    
    # ==================== Candidates ====================
    
    def save_candidate(self, candidate: EdgeCandidate) -> bool:
        """Save edge candidate"""
        try:
            data = candidate.to_dict()
            data["_id"] = candidate.edge_id
            
            # Don't save full pattern matches to DB
            if "sample_matches" in data:
                data["sample_matches"] = data["sample_matches"][:3]  # Keep only 3
            
            self.db.edge_candidates.update_one(
                {"edge_id": candidate.edge_id},
                {"$set": data},
                upsert=True
            )
            return True
        except Exception as e:
            print(f"Error saving candidate: {e}")
            return False
    
    def get_candidate(self, edge_id: str) -> Optional[Dict]:
        """Get candidate by ID"""
        doc = self.db.edge_candidates.find_one({"edge_id": edge_id}, {"_id": 0})
        return doc
    
    def get_all_candidates(self, status: str = None) -> List[Dict]:
        """Get all candidates, optionally filtered by status"""
        query = {}
        if status:
            query["status"] = status
        
        docs = self.db.edge_candidates.find(query, {"_id": 0})
        return list(docs)
    
    def update_candidate_status(self, edge_id: str, status: str) -> bool:
        """Update candidate status"""
        result = self.db.edge_candidates.update_one(
            {"edge_id": edge_id},
            {"$set": {"status": status}}
        )
        return result.modified_count > 0
    
    def delete_candidate(self, edge_id: str) -> bool:
        """Delete candidate"""
        result = self.db.edge_candidates.delete_one({"edge_id": edge_id})
        return result.deleted_count > 0
    
    # ==================== Discovered Edges ====================
    
    def save_edge(self, edge: DiscoveredEdge) -> bool:
        """Save discovered edge"""
        try:
            data = edge.to_dict()
            data["_id"] = edge.edge_id
            
            self.db.discovered_edges.update_one(
                {"edge_id": edge.edge_id},
                {"$set": data},
                upsert=True
            )
            return True
        except Exception as e:
            print(f"Error saving edge: {e}")
            return False
    
    def get_edge(self, edge_id: str) -> Optional[Dict]:
        """Get edge by ID"""
        doc = self.db.discovered_edges.find_one({"edge_id": edge_id}, {"_id": 0})
        return doc
    
    def get_all_edges(self, status: str = None) -> List[Dict]:
        """Get all edges"""
        query = {}
        if status:
            query["status"] = status
        
        docs = self.db.discovered_edges.find(
            query, {"_id": 0}
        ).sort("composite_score", -1)
        return list(docs)
    
    def get_validated_edges(self, limit: int = 50) -> List[Dict]:
        """Get validated edges sorted by score"""
        docs = self.db.discovered_edges.find(
            {"status": {"$in": ["VALIDATED", "PRODUCTION"]}},
            {"_id": 0}
        ).sort("composite_score", -1).limit(limit)
        return list(docs)
    
    def get_top_edges(self, limit: int = 10) -> List[Dict]:
        """Get top edges by composite score"""
        docs = self.db.discovered_edges.find(
            {},
            {"_id": 0}
        ).sort("composite_score", -1).limit(limit)
        return list(docs)
    
    def get_edges_by_category(self, category: str, limit: int = 20) -> List[Dict]:
        """Get edges by category"""
        docs = self.db.discovered_edges.find(
            {"category": category},
            {"_id": 0}
        ).sort("composite_score", -1).limit(limit)
        return list(docs)
    
    def update_edge_status(self, edge_id: str, status: str) -> bool:
        """Update edge status"""
        result = self.db.discovered_edges.update_one(
            {"edge_id": edge_id},
            {"$set": {"status": status}}
        )
        return result.modified_count > 0
    
    def promote_to_production(self, edge_id: str) -> bool:
        """Promote edge to production status"""
        return self.update_edge_status(edge_id, "PRODUCTION")
    
    def deprecate_edge(self, edge_id: str) -> bool:
        """Deprecate an edge"""
        return self.update_edge_status(edge_id, "DEPRECATED")
    
    # ==================== Statistics ====================
    
    def get_statistics(self) -> Dict:
        """Get discovery statistics"""
        total_candidates = self.db.edge_candidates.count_documents({})
        total_edges = self.db.discovered_edges.count_documents({})
        
        # Status breakdown for candidates
        candidate_status = {}
        for status in ["CANDIDATE", "VALIDATING", "VALIDATED", "REJECTED"]:
            candidate_status[status] = self.db.edge_candidates.count_documents({"status": status})
        
        # Status breakdown for edges
        edge_status = {}
        for status in ["VALIDATED", "PRODUCTION", "DEPRECATED"]:
            edge_status[status] = self.db.discovered_edges.count_documents({"status": status})
        
        # Category breakdown
        category_pipeline = [
            {"$group": {"_id": "$category", "count": {"$sum": 1}}}
        ]
        category_counts = {
            doc["_id"]: doc["count"]
            for doc in self.db.discovered_edges.aggregate(category_pipeline)
        }
        
        # Average metrics
        avg_pipeline = [
            {
                "$group": {
                    "_id": None,
                    "avg_score": {"$avg": "$composite_score"},
                    "avg_win_rate": {"$avg": "$win_rate"},
                    "avg_confidence": {"$avg": "$confidence_score"}
                }
            }
        ]
        avg_results = list(self.db.discovered_edges.aggregate(avg_pipeline))
        avg_metrics = avg_results[0] if avg_results else {}
        
        return {
            "total_candidates": total_candidates,
            "total_edges": total_edges,
            "candidates_by_status": candidate_status,
            "edges_by_status": edge_status,
            "edges_by_category": category_counts,
            "average_metrics": {
                "composite_score": round(avg_metrics.get("avg_score", 0), 3),
                "win_rate": round(avg_metrics.get("avg_win_rate", 0), 4),
                "confidence": round(avg_metrics.get("avg_confidence", 0), 3)
            }
        }
