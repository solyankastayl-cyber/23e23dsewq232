"""
Shadow Trade Repository - In-memory storage for shadow trades
"""
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class ShadowTradeRepository:
    """Repository for shadow trades and validation results"""
    
    def __init__(self):
        self.shadow_trades: Dict[str, dict] = {}
        self.validation_results: Dict[str, dict] = {}
    
    def save_shadow_trade(self, item: dict) -> dict:
        """Save a shadow trade"""
        self.shadow_trades[item["shadow_id"]] = item
        return item
    
    def get_shadow_trade(self, shadow_id: str) -> Optional[dict]:
        """Get shadow trade by ID"""
        return self.shadow_trades.get(shadow_id)
    
    def list_shadow_trades(
        self, 
        symbol: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 100
    ) -> List[dict]:
        """List shadow trades with optional filters"""
        items = list(self.shadow_trades.values())
        
        if symbol:
            items = [x for x in items if x.get("symbol") == symbol]
        if status:
            items = [x for x in items if x.get("status") == status]
            
        # Sort by created_at descending
        items = sorted(items, key=lambda x: x.get("created_at", ""), reverse=True)
        return items[:limit]
    
    def update_shadow_trade_status(self, shadow_id: str, status: str) -> Optional[dict]:
        """Update shadow trade status"""
        if shadow_id in self.shadow_trades:
            self.shadow_trades[shadow_id]["status"] = status
            return self.shadow_trades[shadow_id]
        return None
    
    def save_validation_result(self, item: dict) -> dict:
        """Save validation result"""
        self.validation_results[item["shadow_id"]] = item
        return item
    
    def get_validation_result(self, shadow_id: str) -> Optional[dict]:
        """Get validation result by shadow ID"""
        return self.validation_results.get(shadow_id)
    
    def list_validation_results(
        self, 
        symbol: Optional[str] = None,
        result_type: Optional[str] = None,
        limit: int = 100
    ) -> List[dict]:
        """List validation results with optional filters"""
        items = list(self.validation_results.values())
        
        if symbol:
            items = [x for x in items if x.get("symbol") == symbol]
        if result_type:
            items = [x for x in items if x.get("result") == result_type]
            
        return items[:limit]
    
    def get_pending_shadow_trades(self) -> List[dict]:
        """Get all pending shadow trades"""
        return [x for x in self.shadow_trades.values() if x.get("status") == "PENDING"]
    
    def get_entered_shadow_trades(self) -> List[dict]:
        """Get all entered (active) shadow trades"""
        return [x for x in self.shadow_trades.values() if x.get("status") == "ENTERED"]
    
    def clear_all(self):
        """Clear all data (for testing)"""
        self.shadow_trades.clear()
        self.validation_results.clear()
    
    def get_stats(self) -> dict:
        """Get repository statistics"""
        return {
            "total_shadow_trades": len(self.shadow_trades),
            "total_validation_results": len(self.validation_results),
            "pending_trades": len(self.get_pending_shadow_trades()),
            "entered_trades": len(self.get_entered_shadow_trades()),
        }
