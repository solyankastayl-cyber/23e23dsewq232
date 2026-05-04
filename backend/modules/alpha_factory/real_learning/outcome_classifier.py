"""
Outcome Classifier - AF6

Classifies trade outcomes into GOOD/BAD/NEUTRAL.
Identifies mistake types and quality dimensions.
"""

from typing import Dict, Any, List
import logging

logger = logging.getLogger(__name__)


class OutcomeClassifier:
    """
    Trade outcome classifier.
    
    Adds intelligence layer on top of raw outcome:
    - Overall quality (GOOD/BAD/NEUTRAL)
    - Mistake types (early_entry, wrong_direction, bad_execution)
    - Quality dimensions (entry/execution/exit quality)
    """
    
    def classify(self, outcome: Dict[str, Any]) -> Dict[str, Any]:
        """
        Classify outcome and add quality metadata.
        
        Args:
            outcome: Raw outcome from TradeOutcomeEngine
            
        Returns:
            Classified outcome with added fields:
            - outcome_type: GOOD/BAD/NEUTRAL
            - quality: {entry_quality, execution_quality, exit_quality}
            - mistake_type: List of identified mistakes
        """
        pnl = float(outcome.get("pnl", 0.0) or 0.0)
        wrong_early = bool(outcome.get("wrong_early", False))
        exit_reason = outcome.get("exit_reason", "UNKNOWN")
        duration_sec = int(outcome.get("duration_sec", 0) or 0)
        mae = float(outcome.get("mae", 0.0) or 0.0)
        
        mistake_types: List[str] = []
        
        # Identify mistake types
        if wrong_early:
            mistake_types.append("early_entry")
        
        if pnl < 0 and exit_reason == "STOP_HIT":
            mistake_types.append("wrong_direction")
        
        if pnl < 0 and duration_sec < 300:  # Lost money in < 5min
            mistake_types.append("bad_execution")
        
        if pnl < 0 and abs(mae) > 2.0:  # Big drawdown before loss
            mistake_types.append("overstay")
        
        # Overall quality classification
        if pnl > 0 and exit_reason in ["TARGET_HIT", "MANUAL_PROFIT"]:
            quality = "GOOD"
        elif pnl < 0:
            quality = "BAD"
        else:
            quality = "NEUTRAL"
        
        # Quality dimensions
        entry_quality = "BAD" if wrong_early else "GOOD"
        
        execution_quality = "BAD" if "bad_execution" in mistake_types else "GOOD"
        
        if exit_reason in ["TARGET_HIT", "MANUAL_PROFIT"]:
            exit_quality = "GOOD"
        elif pnl < 0:
            exit_quality = "BAD"
        else:
            exit_quality = "NEUTRAL"
        
        classified = {
            **outcome,
            "outcome_type": quality,
            "quality": {
                "entry_quality": entry_quality,
                "execution_quality": execution_quality,
                "exit_quality": exit_quality,
            },
            "mistake_type": mistake_types,
        }
        
        logger.debug(
            f"[OutcomeClassifier] Classified {outcome.get('trade_id')}: "
            f"{quality} | mistakes={mistake_types}"
        )
        
        return classified
