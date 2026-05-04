"""
State Normalizer
================

Normalizes raw engine outputs into canonical orchestrator state.

This is the adapter layer between "what engines return" and "what Final Gate needs".
"""

from typing import Dict, Any
from .override_registry import OverrideRegistry
from .regime_policy_bridge import RegimePolicyBridge
import logging

logger = logging.getLogger(__name__)


class StateNormalizer:
    """
    Normalizes raw engine outputs into canonical state.
    
    Takes messy, inconsistent engine outputs and produces:
    - Unified format
    - Safe defaults
    - Applied overrides
    - Enriched policy data
    """
    
    def __init__(self, override_registry: OverrideRegistry, regime_policy_bridge: RegimePolicyBridge):
        """Initialize with registry and regime bridge."""
        self.override_registry = override_registry
        self.regime_policy_bridge = regime_policy_bridge
    
    def normalize(
        self,
        raw_control: Dict[str, Any],
        raw_risk: Dict[str, Any],
        raw_validation: Dict[str, Any],
        raw_alpha: Dict[str, Any],
        raw_regime: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Normalize all engine outputs into canonical state.
        
        Args:
            raw_control: From ControlBackendService
            raw_risk: From RiskEngine
            raw_validation: From Validation layer
            raw_alpha: From Alpha Factory
            raw_regime: From Regime analysis
        
        Returns:
            Normalized orchestrator state
        """
        # Get current override snapshot
        registry = self.override_registry.snapshot()
        
        # Build enriched regime state
        regime_state = self.regime_policy_bridge.build_regime_state(raw_regime or {})
        
        # Normalize control
        control_state = {
            "can_trade": bool(raw_control.get("can_trade", True)),
            "can_enter": bool(raw_control.get("can_enter", True)),
            "hard_kill": bool(raw_control.get("hard_kill", False)),
            "soft_kill": bool(raw_control.get("soft_kill", False)),
            "overrides": registry.get("entry_mode_overrides", {}),
            "regime_overrides": regime_state.get("regime_overrides", {}),
            "symbol_overrides": registry.get("symbol_overrides", {}),
        }
        
        # Normalize risk
        risk_state = self._normalize_risk(raw_risk)
        
        # Normalize validation
        validation_state = self._normalize_validation(raw_validation)
        
        # Normalize alpha
        alpha_state = {
            "symbol_verdict": raw_alpha.get("symbol_verdict"),
            "entry_mode_verdict": raw_alpha.get("entry_mode_verdict"),
            "pending_actions": raw_alpha.get("pending_actions", []),
        }
        
        return {
            "control": control_state,
            "risk": risk_state,
            "validation": validation_state,
            "alpha": alpha_state,
            "regime": regime_state,
        }
    
    def _normalize_risk(self, raw_risk: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize risk state."""
        if not raw_risk:
            return {
                "max_allowed_size": None,
                "utilization": 0.0,
                "risk_level": "UNKNOWN",
                "heat": 0.0,
                "drawdown": 0.0,
            }
        
        max_allowed = (
            raw_risk.get("max_allowed_position") 
            or raw_risk.get("max_allowed_size")
        )
        
        return {
            "max_allowed_size": max_allowed,
            "utilization": float(raw_risk.get("utilization", 0.0) or 0.0),
            "risk_level": raw_risk.get("risk_level", "UNKNOWN"),
            "heat": float(raw_risk.get("heat", 0.0) or 0.0),
            "drawdown": float(raw_risk.get("drawdown", 0.0) or 0.0),
        }
    
    def _normalize_validation(self, raw_validation: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize validation state with severity."""
        if not raw_validation:
            return {
                "is_valid": True,
                "critical_count": 0,
                "warning_count": 0,
                "severity": "info",
                "issues": [],
            }
        
        critical = int(raw_validation.get("critical_count", 0) or 0)
        warning = int(raw_validation.get("warning_count", 0) or 0)
        is_valid = bool(raw_validation.get("is_valid", True))
        
        # Determine severity
        if not is_valid or critical > 0:
            severity = "critical"
        elif warning > 0:
            severity = "warning"
        else:
            severity = "info"
        
        return {
            "is_valid": is_valid,
            "critical_count": critical,
            "warning_count": warning,
            "severity": severity,
            "issues": raw_validation.get("issues", []),
        }
