"""
Regime Repository
=================

MongoDB storage for regime states and transitions.
"""

import os
import time
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone

from .regime_types import (
    MarketRegimeType,
    RegimeState,
    RegimeTransitionEvent,
    RegimeFeatureSet
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
    print(f"[RegimeRepository] MongoDB not available: {e}")
    MONGO_AVAILABLE = False
    db = None


class RegimeRepository:
    """
    Repository for regime data persistence.
    
    Collections:
    - regime_states: Current and historical regime states
    - regime_transitions: Regime transition events
    """
    
    def __init__(self):
        if MONGO_AVAILABLE:
            self._ensure_indexes()
    
    def _ensure_indexes(self):
        """Create necessary indexes"""
        try:
            # regime_states indexes
            db.regime_states.create_index([("symbol", 1), ("timeframe", 1)])
            db.regime_states.create_index([("generated_at", DESCENDING)])
            
            # regime_transitions indexes
            db.regime_transitions.create_index([("symbol", 1), ("timeframe", 1)])
            db.regime_transitions.create_index([("created_at", DESCENDING)])
        except Exception as e:
            print(f"[RegimeRepository] Index creation error: {e}")
    
    # ===========================================
    # Regime State Operations
    # ===========================================
    
    def save_state(self, state: RegimeState) -> bool:
        """Save regime state to database"""
        if not MONGO_AVAILABLE:
            return False
        
        try:
            doc = {
                "regime_id": state.regime_id,
                "symbol": state.symbol,
                "timeframe": state.timeframe,
                "regime": state.regime.value,
                "confidence": state.confidence,
                "stability_score": state.stability_score,
                "transition_risk": state.transition_risk,
                "regime_probabilities": state.regime_probabilities,
                "trend_direction": state.trend_direction,
                "classification_reasons": state.classification_reasons,
                "generated_at": state.generated_at,
                "bars_in_regime": state.bars_in_regime,
                "regime_start_at": state.regime_start_at,
                "features": state.features.to_dict() if state.features else None
            }
            
            # Upsert by symbol+timeframe for current state
            db.regime_states.update_one(
                {"symbol": state.symbol, "timeframe": state.timeframe},
                {"$set": doc},
                upsert=True
            )
            
            return True
        except Exception as e:
            print(f"[RegimeRepository] Save state error: {e}")
            return False
    
    def get_current_state(self, symbol: str, timeframe: str = "4H") -> Optional[RegimeState]:
        """Get current regime state for symbol"""
        if not MONGO_AVAILABLE:
            return None
        
        try:
            doc = db.regime_states.find_one(
                {"symbol": symbol.upper(), "timeframe": timeframe.upper()}
            )
            
            if not doc:
                return None
            
            return self._doc_to_state(doc)
        except Exception as e:
            print(f"[RegimeRepository] Get state error: {e}")
            return None
    
    def get_state_history(
        self,
        symbol: str,
        timeframe: str = "4H",
        limit: int = 100
    ) -> List[Dict]:
        """Get regime state history"""
        if not MONGO_AVAILABLE:
            return []
        
        try:
            cursor = db.regime_states_history.find(
                {"symbol": symbol.upper(), "timeframe": timeframe.upper()}
            ).sort("generated_at", DESCENDING).limit(limit)
            
            return [self._state_doc_to_dict(doc) for doc in cursor]
        except Exception as e:
            print(f"[RegimeRepository] Get history error: {e}")
            return []
    
    def save_state_to_history(self, state: RegimeState) -> bool:
        """Save state to history collection"""
        if not MONGO_AVAILABLE:
            return False
        
        try:
            doc = {
                "regime_id": state.regime_id,
                "symbol": state.symbol,
                "timeframe": state.timeframe,
                "regime": state.regime.value,
                "confidence": state.confidence,
                "stability_score": state.stability_score,
                "transition_risk": state.transition_risk,
                "generated_at": state.generated_at
            }
            
            db.regime_states_history.insert_one(doc)
            return True
        except Exception as e:
            print(f"[RegimeRepository] Save history error: {e}")
            return False
    
    # ===========================================
    # Transition Operations
    # ===========================================
    
    def save_transition(self, event: RegimeTransitionEvent) -> bool:
        """Save regime transition event"""
        if not MONGO_AVAILABLE:
            return False
        
        try:
            doc = {
                "event_id": event.event_id,
                "symbol": event.symbol,
                "timeframe": event.timeframe,
                "from_regime": event.from_regime.value,
                "to_regime": event.to_regime.value,
                "confidence_before": event.confidence_before,
                "confidence_after": event.confidence_after,
                "confidence_drop": event.confidence_drop,
                "trigger_indicators": event.trigger_indicators,
                "created_at": event.created_at
            }
            
            db.regime_transitions.insert_one(doc)
            return True
        except Exception as e:
            print(f"[RegimeRepository] Save transition error: {e}")
            return False
    
    def get_transitions(
        self,
        symbol: str,
        timeframe: str = "4H",
        limit: int = 50
    ) -> List[Dict]:
        """Get regime transitions for symbol"""
        if not MONGO_AVAILABLE:
            return []
        
        try:
            cursor = db.regime_transitions.find(
                {"symbol": symbol.upper(), "timeframe": timeframe.upper()}
            ).sort("created_at", DESCENDING).limit(limit)
            
            return [self._transition_doc_to_dict(doc) for doc in cursor]
        except Exception as e:
            print(f"[RegimeRepository] Get transitions error: {e}")
            return []
    
    def get_recent_transitions(self, limit: int = 20) -> List[Dict]:
        """Get recent transitions across all symbols"""
        if not MONGO_AVAILABLE:
            return []
        
        try:
            cursor = db.regime_transitions.find().sort("created_at", DESCENDING).limit(limit)
            return [self._transition_doc_to_dict(doc) for doc in cursor]
        except Exception as e:
            print(f"[RegimeRepository] Get recent transitions error: {e}")
            return []
    
    # ===========================================
    # Multi-Symbol Operations
    # ===========================================
    
    def get_all_current_states(self) -> List[Dict]:
        """Get current states for all symbols"""
        if not MONGO_AVAILABLE:
            return []
        
        try:
            cursor = db.regime_states.find()
            return [self._state_doc_to_dict(doc) for doc in cursor]
        except Exception as e:
            print(f"[RegimeRepository] Get all states error: {e}")
            return []
    
    def get_snapshot(self) -> Dict[str, Any]:
        """Get snapshot of all regime states"""
        states = self.get_all_current_states()
        
        # Group by regime
        by_regime = {}
        for state in states:
            regime = state.get("regime", "UNKNOWN")
            if regime not in by_regime:
                by_regime[regime] = []
            by_regime[regime].append(state)
        
        return {
            "totalSymbols": len(states),
            "byRegime": {k: len(v) for k, v in by_regime.items()},
            "states": states,
            "timestamp": int(time.time() * 1000)
        }
    
    # ===========================================
    # Statistics
    # ===========================================
    
    def get_regime_stats(self, symbol: str, timeframe: str = "4H") -> Dict[str, Any]:
        """Get statistics about regime history"""
        if not MONGO_AVAILABLE:
            return {}
        
        try:
            # Count transitions by type
            pipeline = [
                {"$match": {"symbol": symbol.upper(), "timeframe": timeframe.upper()}},
                {"$group": {
                    "_id": {"from": "$from_regime", "to": "$to_regime"},
                    "count": {"$sum": 1}
                }}
            ]
            
            result = list(db.regime_transitions.aggregate(pipeline))
            
            transition_counts = {}
            for r in result:
                key = f"{r['_id']['from']}->{r['_id']['to']}"
                transition_counts[key] = r['count']
            
            return {
                "symbol": symbol,
                "timeframe": timeframe,
                "transitionCounts": transition_counts,
                "totalTransitions": sum(transition_counts.values())
            }
        except Exception as e:
            print(f"[RegimeRepository] Get stats error: {e}")
            return {}
    
    # ===========================================
    # Helpers
    # ===========================================
    
    def _doc_to_state(self, doc: Dict) -> RegimeState:
        """Convert MongoDB doc to RegimeState"""
        features = None
        if doc.get("features"):
            f = doc["features"]
            features = RegimeFeatureSet(
                symbol=f.get("symbol", ""),
                timeframe=f.get("timeframe", ""),
                trend_strength=f.get("trendStrength", 0),
                volatility_level=f.get("volatilityLevel", 0),
                range_compression=f.get("rangeCompression", 0),
                structure_clarity=f.get("structureClarity", 0),
                breakout_pressure=f.get("breakoutPressure", 0)
            )
        
        return RegimeState(
            regime_id=doc.get("regime_id", ""),
            symbol=doc.get("symbol", ""),
            timeframe=doc.get("timeframe", ""),
            regime=MarketRegimeType(doc.get("regime", "TRANSITION")),
            confidence=doc.get("confidence", 0),
            stability_score=doc.get("stability_score", 0),
            transition_risk=doc.get("transition_risk", 0),
            regime_probabilities=doc.get("regime_probabilities", {}),
            trend_direction=doc.get("trend_direction", "NEUTRAL"),
            features=features,
            classification_reasons=doc.get("classification_reasons", []),
            generated_at=doc.get("generated_at", 0),
            bars_in_regime=doc.get("bars_in_regime", 0),
            regime_start_at=doc.get("regime_start_at", 0)
        )
    
    def _state_doc_to_dict(self, doc: Dict) -> Dict:
        """Convert state doc to API dict"""
        return {
            "regimeId": doc.get("regime_id", ""),
            "symbol": doc.get("symbol", ""),
            "timeframe": doc.get("timeframe", ""),
            "regime": doc.get("regime", ""),
            "confidence": doc.get("confidence", 0),
            "stabilityScore": doc.get("stability_score", 0),
            "transitionRisk": doc.get("transition_risk", 0),
            "generatedAt": doc.get("generated_at", 0)
        }
    
    def _transition_doc_to_dict(self, doc: Dict) -> Dict:
        """Convert transition doc to API dict"""
        return {
            "eventId": doc.get("event_id", ""),
            "symbol": doc.get("symbol", ""),
            "timeframe": doc.get("timeframe", ""),
            "fromRegime": doc.get("from_regime", ""),
            "toRegime": doc.get("to_regime", ""),
            "confidenceBefore": doc.get("confidence_before", 0),
            "confidenceAfter": doc.get("confidence_after", 0),
            "confidenceDrop": doc.get("confidence_drop", 0),
            "triggerIndicators": doc.get("trigger_indicators", []),
            "createdAt": doc.get("created_at", 0)
        }


# Global repository instance
regime_repository = RegimeRepository()
