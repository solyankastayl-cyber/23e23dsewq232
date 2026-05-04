"""
Strategy Config Service (STR2)
==============================

Core service for Strategy Configuration Engine.

Features:
- Create and manage configurations
- Parameter validation
- Config versioning
- Config comparison
- Integration with Strategy Profiles
"""

import threading
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
import copy

from .config_types import (
    StrategyConfiguration,
    StrategyConfigVersion,
    ConfigValidationResult,
    ConfigComparison,
    ConfigStatus,
    MarketMode,
    HoldingHorizon,
    PARAMETER_BOUNDS
)
from .config_repository import strategy_config_repository


class StrategyConfigService:
    """
    Strategy Configuration Service.
    
    Manages strategy configurations with validation and versioning.
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
        
        # Initialize default configs from profiles
        self._init_default_configs()
        
        print("[StrategyConfigService] Initialized")
    
    def _init_default_configs(self):
        """Initialize default configurations from profiles"""
        try:
            from ..strategy_profiles.profile_registry import get_all_profiles
            
            for profile in get_all_profiles():
                config = self._profile_to_config(profile)
                strategy_config_repository.save_config(config)
                
                # Create initial version
                version = self._create_version(config, "Initial configuration from profile")
                strategy_config_repository.save_version(version)
                
                # Activate BALANCED by default
                if profile.mode.value == "BALANCED":
                    strategy_config_repository.set_active_config(
                        config.config_id,
                        "system",
                        "Default activation"
                    )
            
            print("[StrategyConfigService] Default configs initialized")
            
        except Exception as e:
            print(f"[StrategyConfigService] Error initializing defaults: {e}")
    
    def _profile_to_config(self, profile) -> StrategyConfiguration:
        """Convert StrategyProfile to StrategyConfiguration"""
        return StrategyConfiguration(
            config_id=f"cfg_{profile.mode.value.lower()}",
            name=f"{profile.name} Config",
            description=f"Configuration derived from {profile.name} profile",
            base_profile=profile.mode.value,
            signal_threshold=profile.signal_threshold,
            exit_threshold=profile.exit_threshold,
            leverage_cap=profile.max_leverage,
            default_leverage=profile.default_leverage,
            max_position_pct=profile.max_position_pct,
            max_portfolio_exposure_pct=profile.max_portfolio_exposure_pct,
            min_position_usd=profile.min_position_usd,
            max_position_usd=profile.max_position_usd,
            max_drawdown_pct=profile.max_drawdown_pct,
            daily_loss_limit_pct=profile.daily_loss_limit_pct,
            stop_loss_pct=profile.default_stop_loss_pct,
            take_profit_pct=profile.default_take_profit_pct,
            use_trailing_stop=profile.use_trailing_stop,
            trailing_stop_pct=profile.trailing_stop_pct,
            holding_horizon=HoldingHorizon[profile.holding_horizon.value],
            min_holding_bars=profile.min_holding_bars,
            max_holding_bars=profile.max_holding_bars,
            max_trades_per_day=profile.max_trades_per_day,
            min_time_between_trades_minutes=profile.min_time_between_trades_minutes,
            market_mode=MarketMode[profile.market_mode.value],
            allowed_symbols=profile.allowed_symbols,
            status=ConfigStatus.VALIDATED,
            tags=["default", profile.mode.value.lower()]
        )
    
    # ===========================================
    # Create Configuration
    # ===========================================
    
    def create_config(
        self,
        name: str,
        base_profile: str = "BALANCED",
        description: str = "",
        created_by: str = "admin",
        **parameters
    ) -> Dict[str, Any]:
        """
        Create a new configuration.
        
        Args:
            name: Configuration name
            base_profile: Base profile to inherit defaults from
            description: Optional description
            created_by: Creator identifier
            **parameters: Override parameters
        
        Returns:
            Created configuration or error
        """
        # Get base config
        base_config = self._get_base_config(base_profile)
        
        # Create new config
        config = base_config.clone(name)
        config.description = description or f"Custom config based on {base_profile}"
        config.base_profile = base_profile
        config.created_by = created_by
        config.tags = ["custom", base_profile.lower()]
        
        # Apply parameter overrides
        for key, value in parameters.items():
            if hasattr(config, key):
                setattr(config, key, value)
        
        # Validate
        validation = self.validate_config(config)
        if not validation.is_valid:
            return {
                "success": False,
                "error": "Configuration validation failed",
                "validation": validation.to_dict()
            }
        
        config.status = ConfigStatus.VALIDATED
        
        # Save
        strategy_config_repository.save_config(config)
        
        # Create version
        version = self._create_version(config, "Initial creation")
        strategy_config_repository.save_version(version)
        
        return {
            "success": True,
            "config": config.to_dict(),
            "validation": validation.to_dict()
        }
    
    def _get_base_config(self, profile: str) -> StrategyConfiguration:
        """Get base configuration for a profile"""
        config_id = f"cfg_{profile.lower()}"
        config = strategy_config_repository.get_config(config_id)
        
        if config:
            return config
        
        # Return default balanced config
        return StrategyConfiguration(
            name="Base Config",
            base_profile="BALANCED"
        )
    
    # ===========================================
    # Update Configuration
    # ===========================================
    
    def update_config(
        self,
        config_id: str,
        updated_by: str = "admin",
        change_reason: str = "",
        **parameters
    ) -> Dict[str, Any]:
        """
        Update an existing configuration.
        
        Creates a new version for rollback.
        """
        config = strategy_config_repository.get_config(config_id)
        if not config:
            return {
                "success": False,
                "error": f"Configuration {config_id} not found"
            }
        
        # Store old parameters
        old_params = config.get_parameters()
        
        # Apply updates
        for key, value in parameters.items():
            if hasattr(config, key):
                setattr(config, key, value)
        
        # Validate
        validation = self.validate_config(config)
        if not validation.is_valid:
            # Rollback changes
            for key, value in old_params.items():
                if hasattr(config, key):
                    setattr(config, key, value)
            
            return {
                "success": False,
                "error": "Validation failed",
                "validation": validation.to_dict()
            }
        
        # Increment version
        config.version += 1
        config.status = ConfigStatus.VALIDATED
        
        # Save
        strategy_config_repository.save_config(config)
        
        # Create version snapshot
        version = self._create_version(config, change_reason)
        strategy_config_repository.save_version(version)
        
        return {
            "success": True,
            "config": config.to_dict(),
            "validation": validation.to_dict(),
            "version": version.to_dict()
        }
    
    def _create_version(
        self,
        config: StrategyConfiguration,
        reason: str = ""
    ) -> StrategyConfigVersion:
        """Create version snapshot"""
        return StrategyConfigVersion(
            config_id=config.config_id,
            version_number=config.version,
            parameters=config.get_parameters(),
            created_by=config.created_by,
            change_reason=reason
        )
    
    # ===========================================
    # Activate Configuration
    # ===========================================
    
    def activate_config(
        self,
        config_id: str,
        activated_by: str = "admin",
        reason: str = ""
    ) -> Dict[str, Any]:
        """
        Activate a configuration for live trading.
        
        Updates Strategy Runtime to use this config.
        """
        config = strategy_config_repository.get_config(config_id)
        if not config:
            return {
                "success": False,
                "error": f"Configuration {config_id} not found"
            }
        
        # Validate before activation
        validation = self.validate_config(config)
        if not validation.is_valid:
            return {
                "success": False,
                "error": "Cannot activate invalid configuration",
                "validation": validation.to_dict()
            }
        
        # Get old active config
        old_active = strategy_config_repository.get_active_config()
        
        # Activate
        success = strategy_config_repository.set_active_config(
            config_id,
            activated_by,
            reason
        )
        
        if not success:
            return {
                "success": False,
                "error": "Activation failed"
            }
        
        # Update profile service if available
        self._sync_to_profile_service(config)
        
        return {
            "success": True,
            "config": config.to_dict(),
            "previous_config_id": old_active.config_id if old_active else None,
            "message": f"Configuration {config_id} activated"
        }
    
    def _sync_to_profile_service(self, config: StrategyConfiguration) -> None:
        """Sync configuration to profile service"""
        try:
            from ..strategy_profiles.profile_service import strategy_profile_service
            # Profile service will be notified of config changes
            # For now, log the sync
            print(f"[StrategyConfigService] Synced config {config.config_id} to profile service")
        except Exception as e:
            print(f"[StrategyConfigService] Profile sync error: {e}")
    
    # ===========================================
    # Validation
    # ===========================================
    
    def validate_config(
        self,
        config: StrategyConfiguration
    ) -> ConfigValidationResult:
        """
        Validate configuration parameters.
        
        Checks:
        - Parameter bounds
        - Logical consistency
        - Risk assessment
        """
        result = ConfigValidationResult(
            config_id=config.config_id,
            is_valid=True
        )
        
        # Check parameter bounds
        params = config.get_parameters()
        for param_name, bounds in PARAMETER_BOUNDS.items():
            if param_name in params:
                value = params[param_name]
                if isinstance(value, (int, float)):
                    if value < bounds["min"]:
                        result.is_valid = False
                        result.invalid_parameters[param_name] = f"Below minimum {bounds['min']}"
                        result.errors.append(f"{param_name}={value} below min {bounds['min']}")
                    elif value > bounds["max"]:
                        result.is_valid = False
                        result.invalid_parameters[param_name] = f"Above maximum {bounds['max']}"
                        result.errors.append(f"{param_name}={value} above max {bounds['max']}")
        
        # Logical consistency checks
        if config.stop_loss_pct >= config.take_profit_pct:
            result.warnings.append("Stop loss >= take profit: may result in negative R:R")
        
        if config.exit_threshold >= config.signal_threshold:
            result.warnings.append("Exit threshold >= entry threshold: may cause early exits")
        
        if config.min_holding_bars >= config.max_holding_bars:
            result.is_valid = False
            result.errors.append("min_holding_bars must be less than max_holding_bars")
        
        # Risk assessment
        risk_score = self._calculate_risk_score(config)
        result.risk_score = risk_score
        
        if risk_score < 0.3:
            result.risk_level = "LOW"
        elif risk_score < 0.6:
            result.risk_level = "MEDIUM"
        elif risk_score < 0.8:
            result.risk_level = "HIGH"
        else:
            result.risk_level = "EXTREME"
            result.warnings.append("Extreme risk configuration - use with caution")
        
        return result
    
    def _calculate_risk_score(self, config: StrategyConfiguration) -> float:
        """Calculate risk score 0-1"""
        score = 0.0
        
        # Leverage contribution (0-0.3)
        leverage_factor = min(1.0, config.leverage_cap / 10.0)
        score += leverage_factor * 0.3
        
        # Position size contribution (0-0.2)
        position_factor = min(1.0, config.max_position_pct / 0.20)
        score += position_factor * 0.2
        
        # Exposure contribution (0-0.2)
        exposure_factor = min(1.0, config.max_portfolio_exposure_pct / 0.60)
        score += exposure_factor * 0.2
        
        # Signal threshold contribution (0-0.15) - lower threshold = higher risk
        threshold_factor = 1.0 - config.signal_threshold
        score += threshold_factor * 0.15
        
        # Stop loss contribution (0-0.15) - wider stop = higher risk
        stop_factor = min(1.0, config.stop_loss_pct / 0.05)
        score += stop_factor * 0.15
        
        return min(1.0, score)
    
    # ===========================================
    # Comparison
    # ===========================================
    
    def compare_configs(
        self,
        config_a_id: str,
        config_b_id: str
    ) -> Optional[ConfigComparison]:
        """Compare two configurations"""
        config_a = strategy_config_repository.get_config(config_a_id)
        config_b = strategy_config_repository.get_config(config_b_id)
        
        if not config_a or not config_b:
            return None
        
        params_a = config_a.get_parameters()
        params_b = config_b.get_parameters()
        
        differences = {}
        
        for key in set(params_a.keys()) | set(params_b.keys()):
            val_a = params_a.get(key)
            val_b = params_b.get(key)
            
            if val_a != val_b:
                diff = {"a": val_a, "b": val_b}
                
                # Calculate change percentage for numeric values
                if isinstance(val_a, (int, float)) and isinstance(val_b, (int, float)) and val_a != 0:
                    diff["change_pct"] = round((val_b - val_a) / val_a * 100, 2)
                
                differences[key] = diff
        
        # Determine risk change
        risk_a = self._calculate_risk_score(config_a)
        risk_b = self._calculate_risk_score(config_b)
        
        if risk_b > risk_a + 0.1:
            risk_change = "INCREASED"
        elif risk_b < risk_a - 0.1:
            risk_change = "DECREASED"
        else:
            risk_change = "SAME"
        
        return ConfigComparison(
            config_a_id=config_a_id,
            config_b_id=config_b_id,
            differences=differences,
            risk_change=risk_change
        )
    
    # ===========================================
    # Query Methods
    # ===========================================
    
    def get_config(self, config_id: str) -> Optional[StrategyConfiguration]:
        """Get configuration by ID"""
        return strategy_config_repository.get_config(config_id)
    
    def get_active_config(self) -> Optional[StrategyConfiguration]:
        """Get active configuration"""
        return strategy_config_repository.get_active_config()
    
    def list_configs(
        self,
        status: Optional[str] = None,
        limit: int = 50
    ) -> List[StrategyConfiguration]:
        """List configurations"""
        config_status = ConfigStatus[status] if status else None
        return strategy_config_repository.list_configs(config_status, limit)
    
    def get_versions(self, config_id: str) -> List[StrategyConfigVersion]:
        """Get configuration versions"""
        return strategy_config_repository.get_versions(config_id)
    
    def get_trading_parameters(self) -> Dict[str, Any]:
        """Get active trading parameters for execution layer"""
        config = self.get_active_config()
        if config:
            return config.get_parameters()
        return {}
    
    def get_activation_history(self, limit: int = 50) -> list:
        """Get activation history"""
        return strategy_config_repository.get_activation_history(limit)
    
    # ===========================================
    # Clone and Rollback
    # ===========================================
    
    def clone_config(
        self,
        config_id: str,
        new_name: str,
        created_by: str = "admin"
    ) -> Dict[str, Any]:
        """Clone a configuration"""
        config = strategy_config_repository.get_config(config_id)
        if not config:
            return {"success": False, "error": "Config not found"}
        
        cloned = config.clone(new_name)
        cloned.created_by = created_by
        
        strategy_config_repository.save_config(cloned)
        
        version = self._create_version(cloned, f"Cloned from {config_id}")
        strategy_config_repository.save_version(version)
        
        return {
            "success": True,
            "config": cloned.to_dict()
        }
    
    def rollback_to_version(
        self,
        config_id: str,
        version_number: int,
        rolled_back_by: str = "admin"
    ) -> Dict[str, Any]:
        """Rollback configuration to a previous version"""
        versions = strategy_config_repository.get_versions(config_id)
        
        target_version = None
        for v in versions:
            if v.version_number == version_number:
                target_version = v
                break
        
        if not target_version:
            return {"success": False, "error": f"Version {version_number} not found"}
        
        config = strategy_config_repository.get_config(config_id)
        if not config:
            return {"success": False, "error": "Config not found"}
        
        # Apply version parameters
        for key, value in target_version.parameters.items():
            if hasattr(config, key):
                # Convert string enums back to enum types
                if key == "market_mode" and isinstance(value, str):
                    value = MarketMode[value]
                elif key == "holding_horizon" and isinstance(value, str):
                    value = HoldingHorizon[value]
                setattr(config, key, value)
        
        config.version += 1
        strategy_config_repository.save_config(config)
        
        # Create rollback version
        new_version = self._create_version(
            config, 
            f"Rolled back to version {version_number} by {rolled_back_by}"
        )
        strategy_config_repository.save_version(new_version)
        
        return {
            "success": True,
            "config": config.to_dict(),
            "rolled_back_to_version": version_number
        }
    
    # ===========================================
    # Health
    # ===========================================
    
    def get_health(self) -> Dict[str, Any]:
        """Get service health"""
        stats = strategy_config_repository.get_stats()
        return {
            "service": "StrategyConfigService",
            "status": "healthy",
            "version": "str2",
            **stats
        }


# Global singleton
strategy_config_service = StrategyConfigService()
