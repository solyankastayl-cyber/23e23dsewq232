"""
Strategy Regime Engine Service
==============================

Main service for market regime classification.

Provides:
- Regime classification (TRENDING, RANGE, HIGH_VOL, LOW_VOL, TRANSITION)
- Confidence metrics
- Stability scoring
- Transition risk detection
- Integration with STG2 and STG5
"""

import os
import time
import uuid
import threading
from typing import Dict, List, Optional, Any
from collections import deque

from .regime_types import (
    MarketRegimeType,
    RegimeState,
    RegimeFeatureSet,
    RegimeTransitionEvent,
    RegimeConfig
)
from .regime_features import feature_calculator, Candle
from .regime_classifier import regime_classifier
from .regime_confidence import confidence_calculator
from .regime_repository import regime_repository

# MongoDB for candle data
try:
    from pymongo import MongoClient
    MONGO_URI = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
    DB_NAME = os.environ.get("DB_NAME", "ta_engine")
    client = MongoClient(MONGO_URI)
    db = client[DB_NAME]
    MONGO_AVAILABLE = True
except Exception:
    MONGO_AVAILABLE = False
    db = None


class RegimeService:
    """
    Main regime classification service.
    
    Usage:
    1. Call classify_regime(symbol, timeframe) to get current regime
    2. Use get_current_state(symbol) to check regime state
    3. Use get_transitions(symbol) to see regime changes
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
        
        self._config = RegimeConfig()
        
        # In-memory state cache
        self._current_states: Dict[str, RegimeState] = {}  # symbol:tf -> state
        self._recent_transitions: deque = deque(maxlen=100)
        
        self._initialized = True
        print("[RegimeService] Initialized (Strategy Regime Engine)")
    
    # ===========================================
    # Main Classification
    # ===========================================
    
    def classify_regime(
        self,
        symbol: str,
        timeframe: str = "4H",
        candles: Optional[List[Dict]] = None
    ) -> RegimeState:
        """
        Classify current market regime for symbol.
        
        Args:
            symbol: Trading pair (e.g., "BTCUSDT", "BTC")
            timeframe: Timeframe (e.g., "1H", "4H", "1D")
            candles: Optional candle data. If None, fetches from DB.
        
        Returns:
            RegimeState with classification result
        """
        
        symbol = symbol.upper()
        timeframe = timeframe.upper()
        key = f"{symbol}:{timeframe}"
        
        # Get candle data
        if candles is None:
            candles = self._fetch_candles(symbol, timeframe)
        
        if not candles or len(candles) < 20:
            # Return uncertain state if not enough data
            return self._create_uncertain_state(symbol, timeframe, "Insufficient data")
        
        # Convert to Candle objects
        candle_objs = [
            Candle(
                timestamp=c.get("timestamp", 0),
                open=c.get("open", 0),
                high=c.get("high", 0),
                low=c.get("low", 0),
                close=c.get("close", 0),
                volume=c.get("volume", 0)
            )
            for c in candles
        ]
        
        # 1. Compute features
        features = feature_calculator.compute_features(candle_objs, symbol, timeframe)
        
        # 2. Classify regime
        regime, probabilities, reasons = regime_classifier.classify(features)
        
        # 3. Calculate confidence metrics
        confidence_metrics = confidence_calculator.calculate_confidence(
            regime, features, probabilities
        )
        
        # 4. Determine trend direction (for TRENDING regime)
        trend_direction = self._determine_trend_direction(features, regime)
        
        # 5. Track regime duration
        bars_in_regime, regime_start = self._track_regime_duration(key, regime)
        
        # 6. Create state
        state = RegimeState(
            regime_id=f"regime_{int(time.time() * 1000)}_{symbol}",
            symbol=symbol,
            timeframe=timeframe,
            regime=regime,
            confidence=confidence_metrics.confidence,
            stability_score=confidence_metrics.stability_score,
            transition_risk=confidence_metrics.transition_risk,
            regime_probabilities=probabilities,
            trend_direction=trend_direction,
            features=features,
            classification_reasons=reasons,
            bars_in_regime=bars_in_regime,
            regime_start_at=regime_start
        )
        
        # 7. Check for transition
        prev_state = self._current_states.get(key)
        if prev_state and prev_state.regime != regime:
            self._record_transition(prev_state, state)
        
        # 8. Update cache
        self._current_states[key] = state
        
        # 9. Persist to DB
        regime_repository.save_state(state)
        
        return state
    
    def _fetch_candles(self, symbol: str, timeframe: str, limit: int = 100) -> List[Dict]:
        """Fetch candles from MongoDB"""
        if not MONGO_AVAILABLE:
            return []
        
        try:
            # Map symbol to DB format
            db_symbol = symbol.replace("USDT", "").replace("USD", "")
            
            cursor = db.candles.find(
                {"symbol": db_symbol, "timeframe": timeframe.lower()}
            ).sort("timestamp", -1).limit(limit)
            
            candles = list(cursor)
            candles.reverse()  # Oldest first
            
            return candles
        except Exception as e:
            print(f"[RegimeService] Fetch candles error: {e}")
            return []
    
    def _create_uncertain_state(
        self,
        symbol: str,
        timeframe: str,
        reason: str
    ) -> RegimeState:
        """Create uncertain/transition state"""
        return RegimeState(
            regime_id=f"regime_{int(time.time() * 1000)}_{symbol}",
            symbol=symbol,
            timeframe=timeframe,
            regime=MarketRegimeType.TRANSITION,
            confidence=0.3,
            stability_score=0.0,
            transition_risk=0.8,
            classification_reasons=[reason, "Using TRANSITION as fallback"]
        )
    
    def _determine_trend_direction(
        self,
        features: RegimeFeatureSet,
        regime: MarketRegimeType
    ) -> str:
        """Determine trend direction if applicable"""
        
        if regime != MarketRegimeType.TRENDING:
            return "NEUTRAL"
        
        # Use slope and MA to determine direction
        if features.ma_separation > 0.3 and features.trend_strength > 0.5:
            # Check raw slope for direction
            if features.raw_slope > 0:
                return "UP"
            else:
                return "DOWN"
        
        # Fallback: use directional consistency
        if features.directional_consistency > 0.6:
            return "UP"  # Assume up if consistent
        elif features.directional_consistency < 0.4:
            return "DOWN"
        
        return "NEUTRAL"
    
    def _track_regime_duration(
        self,
        key: str,
        current_regime: MarketRegimeType
    ) -> tuple:
        """Track how long we've been in this regime"""
        
        prev_state = self._current_states.get(key)
        
        if prev_state and prev_state.regime == current_regime:
            # Same regime - increment bars
            return prev_state.bars_in_regime + 1, prev_state.regime_start_at
        else:
            # New regime
            return 1, int(time.time() * 1000)
    
    def _record_transition(self, prev_state: RegimeState, new_state: RegimeState):
        """Record regime transition event"""
        
        # Determine triggers
        triggers = []
        if prev_state.features and new_state.features:
            pf = prev_state.features
            nf = new_state.features
            
            if abs(nf.volatility_level - pf.volatility_level) > 0.3:
                triggers.append("volatility_change")
            if abs(nf.trend_strength - pf.trend_strength) > 0.3:
                triggers.append("trend_change")
            if abs(nf.range_compression - pf.range_compression) > 0.3:
                triggers.append("compression_change")
        
        event = RegimeTransitionEvent(
            event_id=f"trans_{int(time.time() * 1000)}_{new_state.symbol}",
            symbol=new_state.symbol,
            timeframe=new_state.timeframe,
            from_regime=prev_state.regime,
            to_regime=new_state.regime,
            confidence_before=prev_state.confidence,
            confidence_after=new_state.confidence,
            confidence_drop=prev_state.confidence - new_state.confidence,
            trigger_indicators=triggers
        )
        
        # Store
        self._recent_transitions.append(event)
        regime_repository.save_transition(event)
    
    # ===========================================
    # State Access
    # ===========================================
    
    def get_current_state(
        self,
        symbol: str,
        timeframe: str = "4H"
    ) -> Optional[RegimeState]:
        """Get current regime state for symbol"""
        
        key = f"{symbol.upper()}:{timeframe.upper()}"
        
        # Check cache first
        if key in self._current_states:
            return self._current_states[key]
        
        # Check DB
        state = regime_repository.get_current_state(symbol, timeframe)
        if state:
            self._current_states[key] = state
        
        return state
    
    def get_features(
        self,
        symbol: str,
        timeframe: str = "4H"
    ) -> Optional[RegimeFeatureSet]:
        """Get current features for symbol"""
        state = self.get_current_state(symbol, timeframe)
        return state.features if state else None
    
    def get_transitions(
        self,
        symbol: str,
        timeframe: str = "4H",
        limit: int = 20
    ) -> List[Dict]:
        """Get regime transitions for symbol"""
        return regime_repository.get_transitions(symbol, timeframe, limit)
    
    def get_snapshot(self) -> Dict[str, Any]:
        """Get snapshot of all current regime states"""
        
        # Update states from memory cache
        states = []
        for key, state in self._current_states.items():
            states.append(state.to_dict())
        
        # Group by regime
        by_regime = {}
        for state in states:
            regime = state.get("regime", "UNKNOWN")
            if regime not in by_regime:
                by_regime[regime] = []
            by_regime[regime].append({
                "symbol": state["symbol"],
                "timeframe": state["timeframe"],
                "confidence": state["confidence"],
                "stabilityScore": state["stabilityScore"],
                "transitionRisk": state["transitionRisk"]
            })
        
        return {
            "totalSymbols": len(states),
            "byRegime": {k: len(v) for k, v in by_regime.items()},
            "details": by_regime,
            "timestamp": int(time.time() * 1000)
        }
    
    def get_regime_history(
        self,
        symbol: str,
        timeframe: str = "4H",
        limit: int = 50
    ) -> List[Dict]:
        """Get regime state history"""
        return regime_repository.get_state_history(symbol, timeframe, limit)
    
    # ===========================================
    # Configuration
    # ===========================================
    
    def get_config(self) -> Dict[str, Any]:
        """Get current configuration"""
        return self._config.to_dict()
    
    def update_config(self, updates: Dict[str, Any]):
        """Update configuration"""
        
        if "trendingThreshold" in updates:
            self._config.trending_threshold = updates["trendingThreshold"]
        if "rangeThreshold" in updates:
            self._config.range_threshold = updates["rangeThreshold"]
        if "highVolThreshold" in updates:
            self._config.high_vol_threshold = updates["highVolThreshold"]
        if "lowVolThreshold" in updates:
            self._config.low_vol_threshold = updates["lowVolThreshold"]
        if "compressionThreshold" in updates:
            self._config.compression_threshold = updates["compressionThreshold"]
        
        # Update child components
        from .regime_classifier import regime_classifier
        from .regime_confidence import confidence_calculator
        regime_classifier.config = self._config
        confidence_calculator.config = self._config
    
    # ===========================================
    # Analysis for STG2/STG5 Integration
    # ===========================================
    
    def is_regime_compatible(
        self,
        symbol: str,
        strategy_compatible_regimes: List[str],
        strategy_hostile_regimes: List[str],
        timeframe: str = "4H"
    ) -> Dict[str, Any]:
        """
        Check if current regime is compatible with strategy.
        
        Used by STG2 Logic Engine.
        """
        
        state = self.get_current_state(symbol, timeframe)
        
        if not state:
            return {
                "compatible": True,  # Allow by default if no regime data
                "regime": None,
                "reason": "No regime data available"
            }
        
        current_regime = state.regime.value
        
        # Check hostile
        if current_regime in [r.upper() for r in strategy_hostile_regimes]:
            return {
                "compatible": False,
                "regime": current_regime,
                "confidence": state.confidence,
                "reason": f"Current regime {current_regime} is hostile for this strategy"
            }
        
        # Check compatible
        if current_regime in [r.upper() for r in strategy_compatible_regimes]:
            return {
                "compatible": True,
                "regime": current_regime,
                "confidence": state.confidence,
                "boost": True,
                "reason": f"Current regime {current_regime} is optimal for this strategy"
            }
        
        # Neutral
        return {
            "compatible": True,
            "regime": current_regime,
            "confidence": state.confidence,
            "boost": False,
            "reason": f"Current regime {current_regime} is neutral for this strategy"
        }
    
    def get_regime_modifier(
        self,
        symbol: str,
        timeframe: str = "4H"
    ) -> Dict[str, float]:
        """
        Get regime-based modifiers for sizing/risk.
        
        Used by STG5 Selection.
        """
        
        state = self.get_current_state(symbol, timeframe)
        
        if not state:
            return {
                "size_modifier": 1.0,
                "confidence_modifier": 1.0,
                "stop_modifier": 1.0
            }
        
        modifiers = {
            "size_modifier": 1.0,
            "confidence_modifier": 1.0,
            "stop_modifier": 1.0
        }
        
        # Adjust based on regime
        if state.regime == MarketRegimeType.TRANSITION:
            modifiers["size_modifier"] = 0.7  # Reduce size
            modifiers["confidence_modifier"] = 0.8
            modifiers["stop_modifier"] = 0.85  # Tighter stops
        
        elif state.regime == MarketRegimeType.HIGH_VOLATILITY:
            modifiers["size_modifier"] = 0.6  # Reduce size more
            modifiers["stop_modifier"] = 1.3  # Wider stops
        
        elif state.regime == MarketRegimeType.LOW_VOLATILITY:
            modifiers["size_modifier"] = 1.1  # Slightly larger
            modifiers["stop_modifier"] = 0.75  # Tighter stops (less noise)
        
        # Adjust by confidence
        if state.confidence < 0.5:
            modifiers["size_modifier"] *= 0.85
            modifiers["confidence_modifier"] *= 0.9
        
        # Adjust by transition risk
        if state.transition_risk > 0.6:
            modifiers["size_modifier"] *= 0.9
        
        return modifiers
    
    # ===========================================
    # Health
    # ===========================================
    
    def get_health(self) -> Dict[str, Any]:
        """Get service health"""
        return {
            "module": "Strategy Regime Engine",
            "phase": "REG",
            "status": "healthy",
            "regimeTypes": [r.value for r in MarketRegimeType],
            "trackedSymbols": len(self._current_states),
            "recentTransitions": len(self._recent_transitions),
            "mongoAvailable": MONGO_AVAILABLE,
            "timestamp": int(time.time() * 1000)
        }


# Global singleton
regime_service = RegimeService()
