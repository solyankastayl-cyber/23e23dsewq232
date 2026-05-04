"""
Regime → Policy Bridge
=====================

Bridge that converts regime analysis into system-wide policy.

This is where regime STOPS being "just UI data" and STARTS being "system rules".
"""

from typing import Dict, Any, List
from .override_registry import OverrideRegistry
import logging

logger = logging.getLogger(__name__)


class RegimePolicyBridge:
    """
    Bridge Regime analysis to system policy.
    
    Takes regime state and converts it to:
    - Active restrictions (modes to avoid)
    - Active boosts (modes to prefer)
    - Regime-specific overrides
    """
    
    def __init__(self, override_registry: OverrideRegistry):
        """Initialize with override registry."""
        self.override_registry = override_registry
    
    def ingest(self, regime_actions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Ingest regime actions and apply to override registry.
        
        Args:
            regime_actions: List of regime-based actions (from AF5)
        
        Returns:
            Snapshot of current overrides after ingestion
        """
        if not regime_actions:
            return self.override_registry.snapshot()
        
        logger.info(f"[RegimePolicyBridge] Ingesting {len(regime_actions)} regime actions")
        
        for action in regime_actions:
            try:
                self.override_registry.apply_regime_action(action)
            except Exception as e:
                logger.warning(f"[RegimePolicyBridge] Error applying action: {e}")
                continue
        
        return self.override_registry.snapshot()
    
    def build_regime_state(self, raw_regime: Dict[str, Any]) -> Dict[str, Any]:
        """
        Build enriched regime state with active restrictions/boosts.
        
        Args:
            raw_regime: Raw regime analysis
        
        Returns:
            Enriched regime state with applied policy
        """
        current = raw_regime.get("current", "NEUTRAL")
        
        # Get regime-specific overrides from registry
        snapshot = self.override_registry.snapshot()
        regime_overrides = snapshot["regime_mode_overrides"].get(current, {})
        
        # Extract restrictions and boosts
        restrictions = [
            mode for mode, state in regime_overrides.items() 
            if state == "DISABLED"
        ]
        boosted = [
            mode for mode, state in regime_overrides.items() 
            if state == "BOOSTED"
        ]
        
        return {
            **raw_regime,
            "restrictions": restrictions,
            "boosted_modes": boosted,
            "regime_overrides": regime_overrides,
        }
