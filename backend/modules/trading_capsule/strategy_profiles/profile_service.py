"""
Strategy Profile Service (STR1)
===============================

Core service for Strategy Profile Engine.

Features:
- Profile switching
- Active profile management
- Profile validation
- Event logging
- Integration with Execution/Risk layers
"""

import threading
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from copy import deepcopy

from .profile_types import (
    StrategyProfile,
    ProfileMode,
    ProfileSwitchEvent,
    ProfileValidationResult,
    ProfileSummary
)
from .profile_registry import (
    PROFILE_REGISTRY,
    get_profile,
    get_all_profiles,
    get_profile_by_name,
    compare_profiles
)


class StrategyProfileService:
    """
    Strategy Profile Service.
    
    Manages active trading profile and profile switching.
    Thread-safe singleton.
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
        
        # Active profile (default: BALANCED)
        self._active_profile: StrategyProfile = deepcopy(get_profile(ProfileMode.BALANCED))
        self._active_profile.is_active = True
        
        # Custom profiles storage
        self._custom_profiles: Dict[str, StrategyProfile] = {}
        
        # Switch history
        self._switch_history: List[ProfileSwitchEvent] = []
        
        # Listeners for profile changes
        self._listeners: List[callable] = []
        
        self._initialized = True
        print(f"[StrategyProfileService] Initialized with {self._active_profile.mode.value} profile")
    
    # ===========================================
    # Active Profile
    # ===========================================
    
    def get_active_profile(self) -> StrategyProfile:
        """Get currently active profile"""
        return self._active_profile
    
    def get_active_mode(self) -> ProfileMode:
        """Get active profile mode"""
        return self._active_profile.mode
    
    # ===========================================
    # Switch Profile
    # ===========================================
    
    def switch_profile(
        self,
        mode: str,
        reason: str = "",
        switched_by: str = "admin"
    ) -> Dict[str, Any]:
        """
        Switch to a different profile.
        
        Args:
            mode: Profile mode name (CONSERVATIVE, BALANCED, AGGRESSIVE)
            reason: Reason for switching
            switched_by: Who/what initiated the switch
        
        Returns:
            Switch result with old and new profile details
        """
        with self._lock:
            # Get target mode
            try:
                target_mode = ProfileMode[mode.upper()]
            except KeyError:
                return {
                    "success": False,
                    "error": f"Invalid profile mode: {mode}. Valid modes: CONSERVATIVE, BALANCED, AGGRESSIVE"
                }
            
            # Get current profile info
            old_profile = self._active_profile
            old_mode = old_profile.mode
            
            # Check if already on this profile
            if old_mode == target_mode:
                return {
                    "success": True,
                    "message": f"Already on {target_mode.value} profile",
                    "profile": old_profile.to_dict()
                }
            
            # Get new profile
            new_profile = deepcopy(get_profile(target_mode))
            
            # Validate switch
            validation = self._validate_switch(old_profile, new_profile)
            if not validation.is_valid:
                return {
                    "success": False,
                    "error": "Profile switch validation failed",
                    "validation": validation.to_dict()
                }
            
            # Perform switch
            old_profile.is_active = False
            old_profile.last_switched_at = datetime.now(timezone.utc)
            
            new_profile.is_active = True
            new_profile.last_switched_at = datetime.now(timezone.utc)
            
            self._active_profile = new_profile
            
            # Log switch event
            event = ProfileSwitchEvent(
                from_profile_id=old_profile.profile_id,
                to_profile_id=new_profile.profile_id,
                from_mode=old_mode.value,
                to_mode=target_mode.value,
                switched_by=switched_by,
                reason=reason
            )
            self._switch_history.append(event)
            
            # Notify listeners
            self._notify_listeners(event)
            
            print(f"[StrategyProfileService] Switched {old_mode.value} -> {target_mode.value}")
            
            return {
                "success": True,
                "message": f"Switched to {target_mode.value} profile",
                "from_profile": old_profile.to_dict(),
                "to_profile": new_profile.to_dict(),
                "event": event.to_dict(),
                "validation": validation.to_dict()
            }
    
    def _validate_switch(
        self,
        from_profile: StrategyProfile,
        to_profile: StrategyProfile
    ) -> ProfileValidationResult:
        """Validate profile switch"""
        result = ProfileValidationResult(
            profile_id=to_profile.profile_id,
            is_valid=True
        )
        
        # Check if target profile is enabled
        if not to_profile.is_enabled:
            result.is_valid = False
            result.errors.append(f"Profile {to_profile.mode.value} is disabled")
        
        # Check risk escalation
        risk_order = {"LOW": 1, "MEDIUM": 2, "HIGH": 3, "EXTREME": 4}
        from_risk = risk_order.get(from_profile.risk_level.value, 0)
        to_risk = risk_order.get(to_profile.risk_level.value, 0)
        
        if to_risk > from_risk + 1:
            result.warnings.append(
                f"Large risk escalation: {from_profile.risk_level.value} -> {to_profile.risk_level.value}"
            )
            result.recommendations.append("Consider gradual risk increase")
        
        # Check leverage increase
        if to_profile.max_leverage > from_profile.max_leverage * 2:
            result.warnings.append(
                f"Large leverage increase: {from_profile.max_leverage}x -> {to_profile.max_leverage}x"
            )
        
        return result
    
    # ===========================================
    # Profile List
    # ===========================================
    
    def list_profiles(self) -> List[StrategyProfile]:
        """List all available profiles"""
        profiles = get_all_profiles()
        
        # Add custom profiles
        profiles.extend(self._custom_profiles.values())
        
        # Mark active
        for p in profiles:
            p.is_active = (p.profile_id == self._active_profile.profile_id)
        
        return profiles
    
    def get_profile(self, profile_id: str) -> Optional[StrategyProfile]:
        """Get specific profile by ID"""
        # Check standard profiles
        for profile in get_all_profiles():
            if profile.profile_id == profile_id:
                return profile
        
        # Check custom profiles
        return self._custom_profiles.get(profile_id)
    
    def compare_profiles(self) -> Dict[str, Any]:
        """Get comparison of all profiles"""
        return compare_profiles()
    
    # ===========================================
    # Custom Profiles
    # ===========================================
    
    def create_custom_profile(
        self,
        name: str,
        base_mode: str = "BALANCED",
        **overrides
    ) -> StrategyProfile:
        """
        Create a custom profile based on an existing one.
        
        Args:
            name: Custom profile name
            base_mode: Base profile mode to start from
            **overrides: Parameters to override
        """
        base_profile = get_profile_by_name(base_mode)
        
        # Create copy
        custom = deepcopy(base_profile)
        custom.profile_id = f"profile_custom_{name.lower().replace(' ', '_')}"
        custom.name = name
        custom.description = f"Custom profile based on {base_mode}"
        
        # Apply overrides
        for key, value in overrides.items():
            if hasattr(custom, key):
                setattr(custom, key, value)
        
        # Store
        self._custom_profiles[custom.profile_id] = custom
        
        return custom
    
    # ===========================================
    # Switch History
    # ===========================================
    
    def get_switch_history(self, limit: int = 50) -> List[ProfileSwitchEvent]:
        """Get profile switch history"""
        return list(reversed(self._switch_history[-limit:]))
    
    # ===========================================
    # Profile Parameters
    # ===========================================
    
    def get_signal_threshold(self) -> float:
        """Get current signal threshold"""
        return self._active_profile.signal_threshold
    
    def get_max_leverage(self) -> float:
        """Get current max leverage"""
        return self._active_profile.max_leverage
    
    def get_max_position_pct(self) -> float:
        """Get current max position percentage"""
        return self._active_profile.max_position_pct
    
    def get_max_exposure_pct(self) -> float:
        """Get current max exposure percentage"""
        return self._active_profile.max_portfolio_exposure_pct
    
    def get_stop_loss_pct(self) -> float:
        """Get current default stop loss"""
        return self._active_profile.default_stop_loss_pct
    
    def get_take_profit_pct(self) -> float:
        """Get current default take profit"""
        return self._active_profile.default_take_profit_pct
    
    def get_holding_limits(self) -> Dict[str, int]:
        """Get holding period limits"""
        return {
            "min_bars": self._active_profile.min_holding_bars,
            "max_bars": self._active_profile.max_holding_bars
        }
    
    def is_symbol_allowed(self, symbol: str) -> bool:
        """Check if symbol is allowed in current profile"""
        return symbol in self._active_profile.allowed_symbols
    
    def get_trading_parameters(self) -> Dict[str, Any]:
        """Get all trading parameters for execution layer"""
        p = self._active_profile
        return {
            "profile_mode": p.mode.value,
            "market_mode": p.market_mode.value,
            "leverage": p.default_leverage,
            "max_leverage": p.max_leverage,
            "signal_threshold": p.signal_threshold,
            "exit_threshold": p.exit_threshold,
            "max_position_pct": p.max_position_pct,
            "max_exposure_pct": p.max_portfolio_exposure_pct,
            "stop_loss_pct": p.default_stop_loss_pct,
            "take_profit_pct": p.default_take_profit_pct,
            "use_trailing_stop": p.use_trailing_stop,
            "trailing_stop_pct": p.trailing_stop_pct,
            "max_trades_per_day": p.max_trades_per_day,
            "min_trade_interval_minutes": p.min_time_between_trades_minutes,
            "min_holding_bars": p.min_holding_bars,
            "max_holding_bars": p.max_holding_bars,
            "allowed_symbols": p.allowed_symbols,
            "max_drawdown_pct": p.max_drawdown_pct,
            "daily_loss_limit_pct": p.daily_loss_limit_pct
        }
    
    # ===========================================
    # Listeners
    # ===========================================
    
    def add_listener(self, callback: callable) -> None:
        """Add listener for profile changes"""
        self._listeners.append(callback)
    
    def _notify_listeners(self, event: ProfileSwitchEvent) -> None:
        """Notify all listeners of profile change"""
        for listener in self._listeners:
            try:
                listener(event)
            except Exception as e:
                print(f"[StrategyProfileService] Listener error: {e}")
    
    # ===========================================
    # Health
    # ===========================================
    
    def get_health(self) -> Dict[str, Any]:
        """Get service health"""
        return {
            "service": "StrategyProfileService",
            "status": "healthy",
            "version": "str1",
            "active_profile": self._active_profile.mode.value,
            "total_switches": len(self._switch_history),
            "custom_profiles": len(self._custom_profiles)
        }


# Global singleton
strategy_profile_service = StrategyProfileService()
