"""
Learning Policy Bridge - AF6

Bridges learning actions into ORCH-3 override registry.
Closes the loop: learning → policy → enforcement.
"""

from typing import Dict, List, Any
import logging

logger = logging.getLogger(__name__)


class LearningPolicyBridge:
    """
    Learning-to-policy bridge.
    
    Converts adaptive actions from AlphaFeedbackEngine
    into policy changes via IntegrationEngine's override registry.
    
    This closes the intelligence loop:
    outcome → learning → action → override → FinalGate → future decision
    """
    
    def __init__(self, integration_engine):
        """
        Args:
            integration_engine: ORCH-3 IntegrationEngine instance
        """
        self.integration_engine = integration_engine
    
    def apply(self, actions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Apply adaptive actions to override registry.
        
        Args:
            actions: List of actions from AlphaFeedbackEngine
            
        Returns:
            Applied actions summary
        """
        alpha_actions = []
        regime_actions = []
        
        for a in actions:
            action_type = a.get("type")
            
            # Entry mode and symbol actions → alpha path
            if action_type in [
                "DISABLE_ENTRY_MODE",
                "UPGRADE_ENTRY_MODE",
                "REDUCE_ENTRY_MODE",
                "DISABLE_SYMBOL"
            ]:
                alpha_actions.append(a)
            
            # Regime actions → regime path
            elif action_type == "REDUCE_ACTIVITY_IN_REGIME":
                # Convert to regime-specific action
                regime_actions.append({
                    "type": "DISABLE_MODE_IN_REGIME",
                    "regime": a["regime"],
                    "entry_mode": "GO_FULL",  # Conservative: disable aggressive mode
                    "reason": a["reason"],
                })
        
        # Ingest into override registry
        if alpha_actions:
            try:
                self.integration_engine.ingest_alpha_actions(alpha_actions)
                logger.info(f"[LearningPolicyBridge] Applied {len(alpha_actions)} alpha actions")
            except Exception as e:
                logger.error(f"[LearningPolicyBridge] Failed to apply alpha actions: {e}")
        
        if regime_actions:
            try:
                self.integration_engine.ingest_regime_actions(regime_actions)
                logger.info(f"[LearningPolicyBridge] Applied {len(regime_actions)} regime actions")
            except Exception as e:
                logger.error(f"[LearningPolicyBridge] Failed to apply regime actions: {e}")
        
        return {
            "alpha_actions_applied": alpha_actions,
            "regime_actions_applied": regime_actions,
            "total_applied": len(alpha_actions) + len(regime_actions),
        }
