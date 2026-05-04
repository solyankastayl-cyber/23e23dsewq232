"""
Integration Engine
==================

Main orchestration engine for ORCH-3.

Combines:
- Override Registry (policy memory)
- Alpha → Control bridge
- Regime → Policy bridge
- State Normalizer

This is the single entry point for normalized orchestrator state.
"""

from typing import Dict, Any, List
from .override_registry import OverrideRegistry, get_override_registry
from .alpha_control_bridge import AlphaControlBridge
from .regime_policy_bridge import RegimePolicyBridge
from .state_normalizer import StateNormalizer
import logging

logger = logging.getLogger(__name__)


class OrchestratorIntegrationEngine:
    """
    Main integration engine for ORCH-3.
    
    Provides:
    - Centralized override registry
    - Action ingestion (alpha, regime)
    - State normalization
    """
    
    def __init__(self):
        """Initialize integration engine."""
        self.override_registry = get_override_registry()
        self.alpha_bridge = AlphaControlBridge(self.override_registry)
        self.regime_bridge = RegimePolicyBridge(self.override_registry)
        self.normalizer = StateNormalizer(self.override_registry, self.regime_bridge)
    
    def ingest_alpha_actions(self, actions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Ingest alpha actions into override registry.
        
        Args:
            actions: List of alpha actions
        
        Returns:
            Current override snapshot
        """
        return self.alpha_bridge.ingest(actions)
    
    def ingest_regime_actions(self, actions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Ingest regime actions into override registry.
        
        Args:
            actions: List of regime actions
        
        Returns:
            Current override snapshot
        """
        return self.regime_bridge.ingest(actions)
    
    def build_state(
        self,
        raw_control: Dict[str, Any],
        raw_risk: Dict[str, Any],
        raw_validation: Dict[str, Any],
        raw_alpha: Dict[str, Any],
        raw_regime: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Build normalized orchestrator state.
        
        Args:
            raw_control: From control backend
            raw_risk: From risk engine
            raw_validation: From validation layer
            raw_alpha: From alpha factory
            raw_regime: From regime analysis
        
        Returns:
            Normalized orchestrator state ready for Final Gate
        """
        return self.normalizer.normalize(
            raw_control=raw_control,
            raw_risk=raw_risk,
            raw_validation=raw_validation,
            raw_alpha=raw_alpha,
            raw_regime=raw_regime,
        )
    
    def get_override_snapshot(self) -> Dict[str, Any]:
        """Get current override registry snapshot."""
        return self.override_registry.snapshot()


# Singleton instance
_integration_engine: Any = None


def get_integration_engine() -> OrchestratorIntegrationEngine:
    """Get or create singleton integration engine."""
    global _integration_engine
    if _integration_engine is None:
        _integration_engine = OrchestratorIntegrationEngine()
    return _integration_engine
