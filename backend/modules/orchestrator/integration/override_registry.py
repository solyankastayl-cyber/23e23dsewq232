"""
Override Registry
=================

Central registry for active policy overrides.

This is the MEMORY of the system - tracks which modes/symbols are:
- DISABLED (blocked)
- BOOSTED (enhanced)
- NEUTRAL (default)

Sources:
- Alpha Factory actions (AF3/AF4)
- Regime-based actions (AF5)
- Manual overrides (future)
"""

from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class OverrideRegistry:
    """
    Central registry for all active policy overrides.
    
    This is the single source of truth for:
    - Which entry modes are disabled/boosted
    - Which symbols are disabled/boosted
    - Which regime+mode combinations are restricted
    """
    
    def __init__(self):
        """Initialize empty registry."""
        # Symbol-level overrides: {"BTCUSDT": "DISABLED"}
        self.symbol_overrides: Dict[str, str] = {}
        
        # Entry mode overrides: {"GO_FULL": "DISABLED"}
        self.entry_mode_overrides: Dict[str, str] = {}
        
        # Regime+mode overrides: {"RANGING": {"GO_FULL": "DISABLED"}}
        self.regime_mode_overrides: Dict[str, Dict[str, str]] = {}
    
    def apply_alpha_action(self, action: Dict[str, Any]) -> None:
        """
        Apply alpha action to registry.
        
        Args:
            action: Alpha action dict with type/scope
        """
        action_type = action.get("type") or action.get("action")
        
        if not action_type:
            return
        
        # Entry mode actions
        if action_type in ["DISABLE_MODE", "DISABLE_ENTRY_MODE"]:
            mode = action.get("entry_mode") or action.get("scope_key")
            if mode:
                self.entry_mode_overrides[mode] = "DISABLED"
                logger.info(f"[OverrideRegistry] Disabled entry mode: {mode}")
        
        elif action_type in ["UPGRADE_MODE", "UPGRADE_ENTRY_MODE", "BOOST_MODE"]:
            mode = action.get("entry_mode") or action.get("scope_key")
            if mode:
                self.entry_mode_overrides[mode] = "BOOSTED"
                logger.info(f"[OverrideRegistry] Boosted entry mode: {mode}")
        
        # Symbol actions
        elif action_type == "DISABLE_SYMBOL":
            symbol = action.get("symbol") or action.get("scope_key")
            if symbol:
                self.symbol_overrides[symbol] = "DISABLED"
                logger.info(f"[OverrideRegistry] Disabled symbol: {symbol}")
        
        elif action_type == "BOOST_SYMBOL":
            symbol = action.get("symbol") or action.get("scope_key")
            if symbol:
                self.symbol_overrides[symbol] = "BOOSTED"
                logger.info(f"[OverrideRegistry] Boosted symbol: {symbol}")
    
    def apply_regime_action(self, action: Dict[str, Any]) -> None:
        """
        Apply regime-based action to registry.
        
        Args:
            action: Regime action dict with regime/mode/type
        """
        action_type = action.get("type")
        regime = action.get("regime")
        entry_mode = action.get("entry_mode")
        
        if not regime or not entry_mode:
            return
        
        # Ensure regime key exists
        if regime not in self.regime_mode_overrides:
            self.regime_mode_overrides[regime] = {}
        
        if action_type == "DISABLE_MODE_IN_REGIME":
            self.regime_mode_overrides[regime][entry_mode] = "DISABLED"
            logger.info(f"[OverrideRegistry] Disabled {entry_mode} in {regime}")
        
        elif action_type == "BOOST_MODE_IN_REGIME":
            self.regime_mode_overrides[regime][entry_mode] = "BOOSTED"
            logger.info(f"[OverrideRegistry] Boosted {entry_mode} in {regime}")
    
    def snapshot(self) -> Dict[str, Any]:
        """
        Get current state of all overrides.
        
        Returns:
            Dict with all active overrides
        """
        return {
            "symbol_overrides": dict(self.symbol_overrides),
            "entry_mode_overrides": dict(self.entry_mode_overrides),
            "regime_mode_overrides": {
                k: dict(v) for k, v in self.regime_mode_overrides.items()
            },
        }
    
    def clear(self) -> None:
        """Clear all overrides (for testing/reset)."""
        self.symbol_overrides.clear()
        self.entry_mode_overrides.clear()
        self.regime_mode_overrides.clear()
        logger.info("[OverrideRegistry] Cleared all overrides")


# Singleton instance
_override_registry: Optional[OverrideRegistry] = None


def get_override_registry() -> OverrideRegistry:
    """Get or create singleton override registry."""
    global _override_registry
    if _override_registry is None:
        _override_registry = OverrideRegistry()
    return _override_registry
