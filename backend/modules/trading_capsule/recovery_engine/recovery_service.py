"""
Recovery Service
================

Main service for Recovery Engine (PHASE 1.4)
"""

import time
import threading
from typing import Dict, List, Optional, Any

from .recovery_types import RecoveryDecisionResult, RecoveryConfig
from .recovery_policy_engine import recovery_policy_engine
from .recovery_regime_filter import recovery_regime_filter
from .recovery_structure_filter import recovery_structure_filter
from .recovery_risk_limits import recovery_risk_limits
from .recovery_decision_engine import recovery_decision_engine
from .recovery_registry import recovery_registry


class RecoveryService:
    """
    Main service for Recovery Engine (PHASE 1.4).
    
    Provides unified API for recovery operations.
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
        
        self._initialized = True
        print("[RecoveryService] Initialized (PHASE 1.4)")
    
    # ===========================================
    # Decision
    # ===========================================
    
    def evaluate_recovery(
        self,
        strategy: str,
        position_id: str = "",
        entry_price: float = 100.0,
        current_price: float = 99.0,
        stop_price: float = 98.0,
        direction: str = "LONG",
        current_size: float = 1.0,
        current_adds: int = 0,
        portfolio_exposure_pct: float = 2.0,
        daily_loss_pct: float = 0.0,
        regime: str = "RANGE",
        support_holding: bool = True,
        range_boundary_valid: bool = True,
        structure_broken: bool = False,
        trend_acceleration: bool = False,
        liquidity_cascade: bool = False,
        vwap_distance_pct: Optional[float] = None
    ) -> Dict[str, Any]:
        """Evaluate recovery decision"""
        
        result = recovery_decision_engine.evaluate_recovery(
            strategy=strategy,
            position_id=position_id,
            entry_price=entry_price,
            current_price=current_price,
            stop_price=stop_price,
            direction=direction,
            current_size=current_size,
            current_adds=current_adds,
            portfolio_exposure_pct=portfolio_exposure_pct,
            daily_loss_pct=daily_loss_pct,
            regime=regime,
            support_holding=support_holding,
            range_boundary_valid=range_boundary_valid,
            structure_broken=structure_broken,
            trend_acceleration=trend_acceleration,
            liquidity_cascade=liquidity_cascade,
            vwap_distance_pct=vwap_distance_pct
        )
        
        return result.to_dict()
    
    # ===========================================
    # Strategies
    # ===========================================
    
    def get_strategy_compatibility(self) -> Dict[str, Any]:
        """Get strategy-recovery compatibility"""
        return recovery_registry.get_strategy_matrix()
    
    def get_strategy_policy(self, strategy: str) -> Optional[Dict[str, Any]]:
        """Get recovery policy for strategy"""
        return recovery_policy_engine.get_policy(strategy)
    
    def is_recovery_allowed(self, strategy: str) -> Dict[str, Any]:
        """Check if recovery is allowed for strategy"""
        allowed = recovery_policy_engine.is_recovery_allowed(strategy)
        recovery_type = recovery_policy_engine.get_recovery_type(strategy)
        
        return {
            "strategy": strategy.upper(),
            "allowed": allowed,
            "recoveryType": recovery_type.value,
            "reason": "Mean reversion allows controlled averaging" if allowed else "Strategy does not allow recovery"
        }
    
    # ===========================================
    # Regimes
    # ===========================================
    
    def get_regime_compatibility(self) -> Dict[str, Any]:
        """Get regime-recovery compatibility"""
        return recovery_registry.get_regime_matrix()
    
    def check_regime(self, regime: str) -> Dict[str, Any]:
        """Check if regime allows recovery"""
        result = recovery_regime_filter.check_regime(regime)
        return result.to_dict()
    
    # ===========================================
    # Structure
    # ===========================================
    
    def get_structure_requirements(self) -> Dict[str, Any]:
        """Get structure requirements for recovery"""
        return recovery_registry.get_structure_requirements()
    
    def check_structure(
        self,
        support_holding: bool = True,
        range_boundary_valid: bool = True,
        structure_broken: bool = False,
        trend_acceleration: bool = False,
        liquidity_cascade: bool = False,
        vwap_distance_pct: Optional[float] = None
    ) -> Dict[str, Any]:
        """Check if structure allows recovery"""
        result = recovery_structure_filter.check_structure(
            support_holding=support_holding,
            range_boundary_valid=range_boundary_valid,
            structure_broken=structure_broken,
            trend_acceleration=trend_acceleration,
            liquidity_cascade=liquidity_cascade,
            vwap_distance_pct=vwap_distance_pct
        )
        return result.to_dict()
    
    # ===========================================
    # Risk Limits
    # ===========================================
    
    def get_risk_limits(self) -> Dict[str, Any]:
        """Get risk limits"""
        return recovery_registry.get_risk_limits()
    
    def check_risk_limits(
        self,
        strategy: str,
        current_adds: int,
        current_exposure: float,
        portfolio_exposure_pct: float,
        daily_loss_pct: float = 0.0
    ) -> Dict[str, Any]:
        """Check if within risk limits"""
        config = recovery_policy_engine.get_config(strategy)
        result = recovery_risk_limits.check_risk_limits(
            current_adds=current_adds,
            current_exposure=current_exposure,
            portfolio_exposure_pct=portfolio_exposure_pct,
            daily_loss_pct=daily_loss_pct,
            config=config
        )
        return result.to_dict()
    
    def calculate_add_size(
        self,
        strategy: str,
        base_size: float,
        current_adds: int,
        regime: str = "RANGE"
    ) -> Dict[str, Any]:
        """Calculate recommended add size"""
        config = recovery_policy_engine.get_config(strategy)
        regime_multiplier = recovery_regime_filter.get_size_multiplier_for_regime(regime)
        
        return recovery_risk_limits.calculate_add_size(
            base_size=base_size,
            current_adds=current_adds,
            regime_multiplier=regime_multiplier,
            config=config
        )
    
    # ===========================================
    # Complete Rules
    # ===========================================
    
    def get_recovery_types(self) -> List[Dict[str, Any]]:
        """Get all recovery types"""
        return recovery_registry.get_recovery_types()
    
    def get_complete_rules(self) -> Dict[str, Any]:
        """Get all recovery rules"""
        return recovery_registry.get_complete_recovery_rules()
    
    def get_blocking_rules(self) -> List[Dict[str, Any]]:
        """Get all blocking rules"""
        return recovery_registry.get_blocking_rules()
    
    # ===========================================
    # Events
    # ===========================================
    
    def get_recent_events(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent recovery events"""
        return recovery_decision_engine.get_recent_events(limit)
    
    def get_event_summary(self) -> Dict[str, Any]:
        """Get recovery event summary"""
        return recovery_decision_engine.get_event_summary()
    
    # ===========================================
    # Health
    # ===========================================
    
    def get_health(self) -> Dict[str, Any]:
        """Get service health"""
        return {
            "module": "PHASE 1.4 Recovery Engine",
            "status": "healthy",
            "version": "1.0.0",
            "components": {
                "policyEngine": "active",
                "regimeFilter": "active",
                "structureFilter": "active",
                "riskLimits": "active",
                "decisionEngine": "active",
                "eventLedger": "active"
            },
            "allowedStrategies": recovery_policy_engine.get_allowed_strategies(),
            "allowedRegimes": recovery_regime_filter.get_allowed_regimes(),
            "blockingRules": len(recovery_registry.get_blocking_rules()),
            "timestamp": int(time.time() * 1000)
        }


# Global singleton
recovery_service = RecoveryService()
