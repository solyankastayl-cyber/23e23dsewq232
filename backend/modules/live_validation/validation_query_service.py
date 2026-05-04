"""
Validation Query Service - Read-only queries for validation data
"""
from typing import List, Dict, Optional

from .shadow_trade_repository import ShadowTradeRepository


class ValidationQueryService:
    """Service for querying validation data"""
    
    def __init__(self, repo: ShadowTradeRepository):
        self.repo = repo
    
    def get_recent_shadow_trades(
        self, 
        symbol: Optional[str] = None, 
        limit: int = 20
    ) -> List[dict]:
        """Get recent shadow trades"""
        return self.repo.list_shadow_trades(symbol=symbol, limit=limit)
    
    def get_recent_results(
        self, 
        symbol: Optional[str] = None, 
        limit: int = 20
    ) -> List[dict]:
        """Get recent validation results"""
        return self.repo.list_validation_results(symbol=symbol, limit=limit)
    
    def get_shadow_trade_with_result(self, shadow_id: str) -> Optional[dict]:
        """Get shadow trade combined with its validation result"""
        shadow = self.repo.get_shadow_trade(shadow_id)
        if not shadow:
            return None
        
        result = self.repo.get_validation_result(shadow_id)
        
        return {
            "shadow_trade": shadow,
            "validation_result": result,
        }
    
    def get_combined_recent(
        self, 
        symbol: Optional[str] = None, 
        limit: int = 20
    ) -> List[dict]:
        """Get recent shadow trades with their validation results"""
        shadows = self.repo.list_shadow_trades(symbol=symbol, limit=limit)
        
        combined = []
        for shadow in shadows:
            result = self.repo.get_validation_result(shadow["shadow_id"])
            combined.append({
                "shadow_trade": shadow,
                "validation_result": result,
            })
        
        return combined
    
    def get_summary(self) -> dict:
        """Get validation summary"""
        stats = self.repo.get_stats()
        
        # Get recent results for quick stats
        results = self.repo.list_validation_results(limit=100)
        
        wins = sum(1 for r in results if r.get("result") == "WIN")
        losses = sum(1 for r in results if r.get("result") == "LOSS")
        
        return {
            **stats,
            "recent_wins": wins,
            "recent_losses": losses,
            "recent_win_rate": wins / (wins + losses) if (wins + losses) > 0 else 0,
        }
