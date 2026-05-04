"""
Position Policy Service
=======================

Main service for Position Management (PHASE 1.3)
"""

import time
import threading
from typing import Dict, List, Optional, Any

from .position_policy_types import PositionPolicy
from .position_policy_registry import position_policy_registry
from .stop_policy_engine import stop_policy_engine, StopCalculation
from .take_profit_engine import take_profit_engine, TPCalculation
from .trailing_stop_engine import trailing_stop_engine, TrailingUpdate
from .partial_close_engine import partial_close_engine, PartialCloseDecision
from .time_stop_engine import time_stop_engine, TimeStopDecision
from .forced_exit_engine import forced_exit_engine, ForcedExitDecision


class PositionPolicyService:
    """
    Main service for Position Management.
    
    Coordinates:
    - Stop loss policies
    - Take profit policies
    - Trailing stop policies
    - Partial close policies
    - Time stop policies
    - Forced exit policies
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
        print("[PositionPolicyService] Initialized (PHASE 1.3)")
    
    # ===========================================
    # Complete Policies
    # ===========================================
    
    def get_policy(self, strategy: str) -> Optional[Dict[str, Any]]:
        """Get complete policy for strategy"""
        policy = position_policy_registry.get_policy(strategy)
        if policy:
            return policy.to_dict()
        return None
    
    def get_all_policies(self) -> List[Dict[str, Any]]:
        """Get all policies"""
        return [p.to_dict() for p in position_policy_registry.get_all_policies()]
    
    def get_policy_summary(self, strategy: str) -> Optional[Dict[str, Any]]:
        """Get policy summary for strategy"""
        return position_policy_registry.get_policy_summary(strategy)
    
    def get_all_strategies(self) -> List[str]:
        """Get all strategies with policies"""
        return [p.primary_strategy for p in position_policy_registry.get_all_policies()]
    
    # ===========================================
    # Stop Loss
    # ===========================================
    
    def calculate_stop(
        self,
        strategy: str,
        entry_price: float,
        direction: str,
        atr: Optional[float] = None,
        swing_low: Optional[float] = None,
        swing_high: Optional[float] = None,
        support: Optional[float] = None,
        resistance: Optional[float] = None
    ) -> Dict[str, Any]:
        """Calculate stop loss"""
        result = stop_policy_engine.calculate_stop(
            strategy=strategy,
            entry_price=entry_price,
            direction=direction,
            atr=atr,
            swing_low=swing_low,
            swing_high=swing_high,
            support=support,
            resistance=resistance
        )
        return result.to_dict()
    
    def get_stop_types(self) -> List[Dict[str, Any]]:
        """Get all stop types"""
        return stop_policy_engine.get_all_stop_types()
    
    def get_stop_matrix(self) -> Dict[str, Dict[str, Any]]:
        """Get strategy-stop matrix"""
        return stop_policy_engine.get_strategy_matrix()
    
    # ===========================================
    # Take Profit
    # ===========================================
    
    def calculate_tp(
        self,
        strategy: str,
        entry_price: float,
        stop_price: float,
        direction: str,
        resistance: Optional[float] = None,
        support: Optional[float] = None,
        vwap: Optional[float] = None
    ) -> Dict[str, Any]:
        """Calculate take profit levels"""
        result = take_profit_engine.calculate_tp(
            strategy=strategy,
            entry_price=entry_price,
            stop_price=stop_price,
            direction=direction,
            resistance=resistance,
            support=support,
            vwap=vwap
        )
        return result.to_dict()
    
    def get_tp_types(self) -> List[Dict[str, Any]]:
        """Get all TP types"""
        return take_profit_engine.get_all_tp_types()
    
    def get_tp_matrix(self) -> Dict[str, Dict[str, Any]]:
        """Get strategy-TP matrix"""
        return take_profit_engine.get_strategy_matrix()
    
    # ===========================================
    # Trailing Stop
    # ===========================================
    
    def calculate_trailing(
        self,
        strategy: str,
        entry_price: float,
        current_stop: float,
        current_price: float,
        direction: str,
        atr: Optional[float] = None,
        swing_low: Optional[float] = None,
        swing_high: Optional[float] = None,
        bars_in_trade: int = 0
    ) -> Dict[str, Any]:
        """Calculate trailing stop update"""
        result = trailing_stop_engine.calculate_trailing_stop(
            strategy=strategy,
            entry_price=entry_price,
            current_stop=current_stop,
            current_price=current_price,
            direction=direction,
            atr=atr,
            swing_low=swing_low,
            swing_high=swing_high,
            bars_in_trade=bars_in_trade
        )
        return result.to_dict()
    
    def get_trailing_types(self) -> List[Dict[str, Any]]:
        """Get all trailing types"""
        return trailing_stop_engine.get_all_trailing_types()
    
    def get_trailing_matrix(self) -> Dict[str, Dict[str, Any]]:
        """Get strategy-trailing matrix"""
        return trailing_stop_engine.get_strategy_matrix()
    
    # ===========================================
    # Partial Close
    # ===========================================
    
    def evaluate_partial_close(
        self,
        strategy: str,
        entry_price: float,
        current_price: float,
        stop_price: float,
        target_price: float,
        direction: str,
        current_position_size: float = 1.0,
        already_closed_pct: float = 0.0
    ) -> Dict[str, Any]:
        """Evaluate partial close"""
        result = partial_close_engine.evaluate_partial_close(
            strategy=strategy,
            entry_price=entry_price,
            current_price=current_price,
            stop_price=stop_price,
            target_price=target_price,
            direction=direction,
            current_position_size=current_position_size,
            already_closed_pct=already_closed_pct
        )
        return result.to_dict()
    
    def get_partial_types(self) -> List[Dict[str, Any]]:
        """Get all partial close types"""
        return partial_close_engine.get_all_partial_types()
    
    def get_partial_matrix(self) -> Dict[str, Dict[str, Any]]:
        """Get strategy-partial matrix"""
        return partial_close_engine.get_strategy_matrix()
    
    # ===========================================
    # Time Stop
    # ===========================================
    
    def evaluate_time_stop(
        self,
        strategy: str,
        bars_held: int,
        entry_price: float,
        current_price: float,
        direction: str,
        current_position_size: float = 1.0
    ) -> Dict[str, Any]:
        """Evaluate time stop"""
        result = time_stop_engine.evaluate_time_stop(
            strategy=strategy,
            bars_held=bars_held,
            entry_price=entry_price,
            current_price=current_price,
            direction=direction,
            current_position_size=current_position_size
        )
        return result.to_dict()
    
    def get_time_stop_types(self) -> List[Dict[str, Any]]:
        """Get all time stop types"""
        return time_stop_engine.get_all_time_stop_types()
    
    def get_time_stop_matrix(self) -> Dict[str, Dict[str, Any]]:
        """Get strategy-time stop matrix"""
        return time_stop_engine.get_strategy_matrix()
    
    # ===========================================
    # Forced Exit
    # ===========================================
    
    def evaluate_forced_exit(
        self,
        strategy: str,
        current_regime: str,
        previous_regime: Optional[str] = None,
        current_volatility: float = 1.0,
        normal_volatility: float = 1.0,
        structure_broken: bool = False,
        position_pnl_pct: float = 0.0,
        daily_pnl_pct: float = 0.0,
        correlation_spike: bool = False
    ) -> Dict[str, Any]:
        """Evaluate forced exit"""
        result = forced_exit_engine.evaluate_forced_exit(
            strategy=strategy,
            current_regime=current_regime,
            previous_regime=previous_regime,
            current_volatility=current_volatility,
            normal_volatility=normal_volatility,
            structure_broken=structure_broken,
            position_pnl_pct=position_pnl_pct,
            daily_pnl_pct=daily_pnl_pct,
            correlation_spike=correlation_spike
        )
        return result.to_dict()
    
    def get_forced_exit_triggers(self) -> List[Dict[str, Any]]:
        """Get all forced exit triggers"""
        return forced_exit_engine.get_all_exit_triggers()
    
    def get_forced_exit_matrix(self) -> Dict[str, Dict[str, Any]]:
        """Get strategy-forced exit matrix"""
        return forced_exit_engine.get_strategy_matrix()
    
    # ===========================================
    # Combined Matrices
    # ===========================================
    
    def get_strategy_policy_matrix(self) -> Dict[str, Any]:
        """Get complete strategy-policy matrix"""
        return {
            "matrix": position_policy_registry.get_strategy_policy_matrix(),
            "description": "Complete strategy to position policy mapping"
        }
    
    def get_full_evaluation(
        self,
        strategy: str,
        entry_price: float,
        current_price: float,
        stop_price: float,
        target_price: float,
        direction: str,
        bars_held: int = 0,
        current_regime: str = "TRENDING",
        previous_regime: Optional[str] = None,
        atr: Optional[float] = None,
        current_volatility: float = 1.0,
        structure_broken: bool = False,
        position_pnl_pct: float = 0.0
    ) -> Dict[str, Any]:
        """
        Get full position evaluation.
        
        Returns all policy evaluations at once.
        """
        
        # Calculate profit %
        is_long = direction.upper() == "LONG"
        if is_long:
            pnl_pct = ((current_price - entry_price) / entry_price) * 100
        else:
            pnl_pct = ((entry_price - current_price) / entry_price) * 100
        
        return {
            "strategy": strategy.upper(),
            "position": {
                "entryPrice": entry_price,
                "currentPrice": current_price,
                "stopPrice": stop_price,
                "targetPrice": target_price,
                "direction": direction.upper(),
                "barsHeld": bars_held,
                "pnlPct": round(pnl_pct, 4)
            },
            "trailing": self.calculate_trailing(
                strategy=strategy,
                entry_price=entry_price,
                current_stop=stop_price,
                current_price=current_price,
                direction=direction,
                atr=atr,
                bars_in_trade=bars_held
            ),
            "partialClose": self.evaluate_partial_close(
                strategy=strategy,
                entry_price=entry_price,
                current_price=current_price,
                stop_price=stop_price,
                target_price=target_price,
                direction=direction
            ),
            "timeStop": self.evaluate_time_stop(
                strategy=strategy,
                bars_held=bars_held,
                entry_price=entry_price,
                current_price=current_price,
                direction=direction
            ),
            "forcedExit": self.evaluate_forced_exit(
                strategy=strategy,
                current_regime=current_regime,
                previous_regime=previous_regime,
                current_volatility=current_volatility,
                structure_broken=structure_broken,
                position_pnl_pct=position_pnl_pct or pnl_pct
            ),
            "timestamp": int(time.time() * 1000)
        }
    
    # ===========================================
    # Health
    # ===========================================
    
    def get_health(self) -> Dict[str, Any]:
        """Get service health"""
        return {
            "module": "PHASE 1.3 Position Management Policy",
            "status": "healthy",
            "version": "1.0.0",
            "strategiesConfigured": len(position_policy_registry.get_all_policies()),
            "engines": {
                "stopPolicy": "active",
                "takeProfit": "active",
                "trailingStop": "active",
                "partialClose": "active",
                "timeStop": "active",
                "forcedExit": "active"
            },
            "timestamp": int(time.time() * 1000)
        }


# Global singleton
position_policy_service = PositionPolicyService()
