"""
OPS3 Forensics Repository
=========================

Data access for forensics reports.
"""

import os
import time
from typing import Dict, List, Optional, Any

from .forensics_types import (
    TradeForensicsReport,
    BlockAnalysis,
    StrategyBehaviorAnalysis
)

# MongoDB connection
try:
    from pymongo import MongoClient, DESCENDING
    MONGO_URI = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
    DB_NAME = os.environ.get("DB_NAME", "ta_engine")
    client = MongoClient(MONGO_URI)
    db = client[DB_NAME]
    MONGO_AVAILABLE = True
except Exception as e:
    print(f"[ForensicsRepository] MongoDB not available: {e}")
    MONGO_AVAILABLE = False
    db = None


class ForensicsRepository:
    """
    Repository for forensics data storage and retrieval.
    """
    
    def __init__(self):
        self._ensure_collections()
    
    def _ensure_collections(self):
        """Ensure required collections exist"""
        if not MONGO_AVAILABLE:
            return
        
        try:
            # Create indexes
            db.forensics_reports.create_index([("trade_id", 1)], unique=True, sparse=True)
            db.forensics_reports.create_index([("position_id", 1)])
            db.forensics_reports.create_index([("strategy_id", 1)])
            db.forensics_reports.create_index([("generated_at", DESCENDING)])
            
            db.block_analysis.create_index([("block_id", 1)], unique=True)
            db.block_analysis.create_index([("strategy_id", 1)])
            db.block_analysis.create_index([("timestamp", DESCENDING)])
        except Exception as e:
            print(f"[ForensicsRepository] Index creation: {e}")
    
    # ===========================================
    # Forensics Reports
    # ===========================================
    
    def save_report(self, report: TradeForensicsReport) -> bool:
        """Save forensics report"""
        if not MONGO_AVAILABLE:
            return False
        
        try:
            report_dict = report.to_dict()
            report_dict["_id"] = report.report_id
            
            db.forensics_reports.update_one(
                {"_id": report.report_id},
                {"$set": report_dict},
                upsert=True
            )
            return True
        except Exception as e:
            print(f"[ForensicsRepository] Save report error: {e}")
            return False
    
    def get_report_by_trade(self, trade_id: str) -> Optional[Dict]:
        """Get report by trade ID"""
        if not MONGO_AVAILABLE:
            return None
        
        try:
            doc = db.forensics_reports.find_one(
                {"tradeId": trade_id},
                {"_id": 0}
            )
            return doc
        except Exception as e:
            print(f"[ForensicsRepository] Get report error: {e}")
            return None
    
    def get_report_by_position(self, position_id: str) -> Optional[Dict]:
        """Get report by position ID"""
        if not MONGO_AVAILABLE:
            return None
        
        try:
            doc = db.forensics_reports.find_one(
                {"positionId": position_id},
                {"_id": 0}
            )
            return doc
        except Exception as e:
            print(f"[ForensicsRepository] Get report error: {e}")
            return None
    
    def get_reports_by_strategy(
        self,
        strategy_id: str,
        limit: int = 50
    ) -> List[Dict]:
        """Get reports for a strategy"""
        if not MONGO_AVAILABLE:
            return []
        
        try:
            cursor = db.forensics_reports.find(
                {"ownership.strategyId": strategy_id},
                {"_id": 0}
            ).sort("generatedAt", DESCENDING).limit(limit)
            
            return list(cursor)
        except Exception as e:
            print(f"[ForensicsRepository] Get reports error: {e}")
            return []
    
    def get_recent_reports(self, limit: int = 20) -> List[Dict]:
        """Get most recent reports"""
        if not MONGO_AVAILABLE:
            return []
        
        try:
            cursor = db.forensics_reports.find(
                {},
                {"_id": 0}
            ).sort("generatedAt", DESCENDING).limit(limit)
            
            return list(cursor)
        except Exception as e:
            print(f"[ForensicsRepository] Get recent error: {e}")
            return []
    
    # ===========================================
    # Block Analysis
    # ===========================================
    
    def save_block(self, block: BlockAnalysis) -> bool:
        """Save block analysis"""
        if not MONGO_AVAILABLE:
            return False
        
        try:
            block_dict = block.to_dict()
            block_dict["_id"] = block.block_id
            
            db.block_analysis.update_one(
                {"_id": block.block_id},
                {"$set": block_dict},
                upsert=True
            )
            return True
        except Exception as e:
            print(f"[ForensicsRepository] Save block error: {e}")
            return False
    
    def get_blocks_by_strategy(
        self,
        strategy_id: str,
        limit: int = 100
    ) -> List[Dict]:
        """Get blocks for a strategy"""
        if not MONGO_AVAILABLE:
            return []
        
        try:
            cursor = db.block_analysis.find(
                {"strategyId": strategy_id},
                {"_id": 0}
            ).sort("timestamp", DESCENDING).limit(limit)
            
            return list(cursor)
        except Exception as e:
            print(f"[ForensicsRepository] Get blocks error: {e}")
            return []
    
    def get_block_summary(self) -> Dict[str, Any]:
        """Get summary of all blocks"""
        if not MONGO_AVAILABLE:
            return {}
        
        try:
            pipeline = [
                {
                    "$group": {
                        "_id": "$blockReason.type",
                        "count": {"$sum": 1}
                    }
                },
                {"$sort": {"count": -1}}
            ]
            
            result = list(db.block_analysis.aggregate(pipeline))
            
            return {
                "byReason": {r["_id"]: r["count"] for r in result},
                "totalBlocks": sum(r["count"] for r in result)
            }
        except Exception as e:
            print(f"[ForensicsRepository] Get block summary error: {e}")
            return {}
    
    # ===========================================
    # Event Ledger Access
    # ===========================================
    
    def get_events_for_trade(self, trade_id: str) -> List[Dict]:
        """Get events from Event Ledger for a trade"""
        if not MONGO_AVAILABLE:
            return []
        
        try:
            cursor = db.event_ledger.find({
                "$or": [
                    {"aggregate_id": trade_id},
                    {"payload.trade_id": trade_id},
                    {"payload.tradeId": trade_id}
                ]
            }).sort("created_at", 1)
            
            return list(cursor)
        except Exception as e:
            print(f"[ForensicsRepository] Get events error: {e}")
            return []
    
    def get_events_for_position(self, position_id: str) -> List[Dict]:
        """Get events from Event Ledger for a position"""
        if not MONGO_AVAILABLE:
            return []
        
        try:
            cursor = db.event_ledger.find({
                "$or": [
                    {"aggregate_id": position_id},
                    {"payload.position_id": position_id},
                    {"payload.positionId": position_id}
                ]
            }).sort("created_at", 1)
            
            return list(cursor)
        except Exception as e:
            print(f"[ForensicsRepository] Get events error: {e}")
            return []
    
    def get_decision_events(self, decision_id: str) -> List[Dict]:
        """Get events for a decision"""
        if not MONGO_AVAILABLE:
            return []
        
        try:
            cursor = db.event_ledger.find({
                "$or": [
                    {"payload.decision_id": decision_id},
                    {"payload.decisionId": decision_id},
                    {"metadata.correlation_id": decision_id}
                ]
            }).sort("created_at", 1)
            
            return list(cursor)
        except Exception as e:
            print(f"[ForensicsRepository] Get decision events error: {e}")
            return []
    
    # ===========================================
    # Strategy Behavior
    # ===========================================
    
    def get_strategy_signals(
        self,
        strategy_id: str,
        limit: int = 500
    ) -> List[Dict]:
        """Get signal events for a strategy"""
        if not MONGO_AVAILABLE:
            return []
        
        try:
            cursor = db.event_ledger.find({
                "event_type": {"$in": ["SIGNAL_RECEIVED", "STRATEGY_DECISION_MADE", "STRATEGY_BLOCKED"]},
                "$or": [
                    {"payload.strategy_id": strategy_id},
                    {"payload.strategyId": strategy_id}
                ]
            }).sort("created_at", DESCENDING).limit(limit)
            
            return list(cursor)
        except Exception as e:
            print(f"[ForensicsRepository] Get signals error: {e}")
            return []
    
    def get_trades_by_strategy(
        self,
        strategy_id: str,
        limit: int = 200
    ) -> List[Dict]:
        """Get trades for a strategy"""
        if not MONGO_AVAILABLE:
            return []
        
        try:
            cursor = db.trades.find({
                "$or": [
                    {"strategy_id": strategy_id},
                    {"strategyId": strategy_id}
                ]
            }).sort("created_at", DESCENDING).limit(limit)
            
            return list(cursor)
        except Exception as e:
            print(f"[ForensicsRepository] Get trades error: {e}")
            return []


# Global singleton
forensics_repository = ForensicsRepository()
