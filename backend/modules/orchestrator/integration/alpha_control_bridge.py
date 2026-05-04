"""
Alpha → Control Bridge
=====================

Bridge that converts Alpha Factory actions into Control overrides.

This is where alpha actions STOP being "pending" and START being "applied".
"""

from typing import Dict, Any, List
from .override_registry import OverrideRegistry
import logging

logger = logging.getLogger(__name__)


class AlphaControlBridge:
    """
    Bridge Alpha Factory actions to Control overrides.
    
    Takes actions from AF3/AF4 and applies them to override registry.
    """
    
    def __init__(self, override_registry: OverrideRegistry):
        """Initialize with override registry."""
        self.override_registry = override_registry
    
    def ingest(self, alpha_actions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Ingest alpha actions and apply to override registry.
        
        Args:
            alpha_actions: List of actions from Alpha Factory
        
        Returns:
            Snapshot of current overrides after ingestion
        """
        if not alpha_actions:
            return self.override_registry.snapshot()
        
        logger.info(f"[AlphaControlBridge] Ingesting {len(alpha_actions)} actions")
        
        for action in alpha_actions:
            try:
                self.override_registry.apply_alpha_action(action)
            except Exception as e:
                logger.warning(f"[AlphaControlBridge] Error applying action: {e}")
                continue
        
        return self.override_registry.snapshot()
