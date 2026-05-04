"""
Position Intelligence Repository
================================

Storage for position intelligence data (PHASE 3.1)
"""

import time
import threading
from typing import Dict, List, Optional, Any

from .position_quality_types import (
    PositionQualityScore,
    TradeHealthScore,
    RiskAdjustment,
    PositionIntelligence
)


class PositionIntelligenceRepository:
    """
    In-memory repository for position intelligence.
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._quality_scores: Dict[str, PositionQualityScore] = {}
        self._health_scores: Dict[str, TradeHealthScore] = {}
        self._risk_adjustments: Dict[str, RiskAdjustment] = {}
        self._intelligence: Dict[str, PositionIntelligence] = {}
        
        # History
        self._quality_history: List[PositionQualityScore] = []
        self._health_history: List[TradeHealthScore] = []
        
        self._initialized = True
        print("[PositionIntelligenceRepository] Initialized (PHASE 3.1)")
    
    # ==========================================
    # Quality Score Management
    # ==========================================
    
    def save_quality(self, score: PositionQualityScore) -> None:
        """Save quality score"""
        self._quality_scores[score.position_id] = score
        self._quality_history.append(score)
        
        # Keep history limited
        if len(self._quality_history) > 500:
            self._quality_history = self._quality_history[-500:]
    
    def get_quality(self, position_id: str) -> Optional[PositionQualityScore]:
        """Get quality score for position"""
        return self._quality_scores.get(position_id)
    
    def get_quality_history(self, limit: int = 50) -> List[PositionQualityScore]:
        """Get recent quality scores"""
        return self._quality_history[-limit:]
    
    # ==========================================
    # Health Score Management
    # ==========================================
    
    def save_health(self, health: TradeHealthScore) -> None:
        """Save health score"""
        self._health_scores[health.position_id] = health
        self._health_history.append(health)
        
        if len(self._health_history) > 500:
            self._health_history = self._health_history[-500:]
    
    def get_health(self, position_id: str) -> Optional[TradeHealthScore]:
        """Get health score for position"""
        return self._health_scores.get(position_id)
    
    def get_health_history(self, limit: int = 50) -> List[TradeHealthScore]:
        """Get recent health scores"""
        return self._health_history[-limit:]
    
    # ==========================================
    # Risk Adjustment Management
    # ==========================================
    
    def save_risk_adjustment(self, adjustment: RiskAdjustment) -> None:
        """Save risk adjustment"""
        self._risk_adjustments[adjustment.position_id] = adjustment
    
    def get_risk_adjustment(self, position_id: str) -> Optional[RiskAdjustment]:
        """Get risk adjustment for position"""
        return self._risk_adjustments.get(position_id)
    
    # ==========================================
    # Combined Intelligence
    # ==========================================
    
    def save_intelligence(self, intelligence: PositionIntelligence) -> None:
        """Save combined intelligence"""
        self._intelligence[intelligence.position_id] = intelligence
    
    def get_intelligence(self, position_id: str) -> Optional[PositionIntelligence]:
        """Get combined intelligence for position"""
        return self._intelligence.get(position_id)
    
    def get_all_intelligence(self) -> List[PositionIntelligence]:
        """Get all position intelligence"""
        return list(self._intelligence.values())
    
    # ==========================================
    # Stats
    # ==========================================
    
    def get_stats(self) -> Dict[str, Any]:
        """Get repository stats"""
        
        # Calculate averages
        quality_scores = [q.total_score for q in self._quality_scores.values()]
        health_scores = [h.current_health for h in self._health_scores.values()]
        
        return {
            "positions": {
                "tracked": len(self._quality_scores),
                "withHealth": len(self._health_scores),
                "withRiskAdjustment": len(self._risk_adjustments)
            },
            "averages": {
                "quality": round(sum(quality_scores) / len(quality_scores), 1) if quality_scores else 0,
                "health": round(sum(health_scores) / len(health_scores), 1) if health_scores else 0
            },
            "history": {
                "qualityRecords": len(self._quality_history),
                "healthRecords": len(self._health_history)
            }
        }
    
    def clear(self) -> None:
        """Clear all data"""
        self._quality_scores.clear()
        self._health_scores.clear()
        self._risk_adjustments.clear()
        self._intelligence.clear()
        self._quality_history.clear()
        self._health_history.clear()


# Global singleton
position_intelligence_repository = PositionIntelligenceRepository()
