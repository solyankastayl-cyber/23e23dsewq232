"""
Outcome Registry - AF6

Central registry for all completed trade outcomes.
Provides storage and query capabilities for learning system.
"""

from typing import Dict, List, Any, Optional
import logging

logger = logging.getLogger(__name__)


class OutcomeRegistry:
    """
    Central registry for trade outcomes.
    
    Stores classified trade results for learning and adaptation.
    """
    
    def __init__(self):
        self.outcomes: Dict[str, Dict[str, Any]] = {}
    
    def register(self, outcome: Dict[str, Any]) -> Dict[str, Any]:
        """
        Register a trade outcome.
        
        Args:
            outcome: Outcome dict (must contain 'trade_id')
            
        Returns:
            Registered outcome
        """
        trade_id = outcome.get("trade_id")
        if not trade_id:
            logger.error("[OutcomeRegistry] Cannot register outcome without trade_id")
            return outcome
        
        self.outcomes[trade_id] = outcome
        logger.info(f"[OutcomeRegistry] Registered outcome: {trade_id} | {outcome.get('outcome')} | pnl={outcome.get('pnl')}")
        
        return outcome
    
    def get(self, trade_id: str) -> Optional[Dict[str, Any]]:
        """
        Get specific outcome.
        
        Args:
            trade_id: Trade ID
            
        Returns:
            Outcome dict or None
        """
        return self.outcomes.get(trade_id)
    
    def list_all(self) -> List[Dict[str, Any]]:
        """
        List all outcomes.
        
        Returns:
            List of all outcomes
        """
        return list(self.outcomes.values())
    
    def list_by_symbol(self, symbol: str) -> List[Dict[str, Any]]:
        """
        List outcomes for specific symbol.
        
        Args:
            symbol: Trading symbol
            
        Returns:
            List of outcomes for symbol
        """
        return [o for o in self.outcomes.values() if o.get("symbol") == symbol]
    
    def list_by_entry_mode(self, entry_mode: str) -> List[Dict[str, Any]]:
        """
        List outcomes for specific entry mode.
        
        Args:
            entry_mode: Entry mode
            
        Returns:
            List of outcomes for entry mode
        """
        return [o for o in self.outcomes.values() if o.get("entry_mode") == entry_mode]
    
    def list_by_regime(self, regime: str) -> List[Dict[str, Any]]:
        """
        List outcomes for specific regime.
        
        Args:
            regime: Regime type
            
        Returns:
            List of outcomes for regime
        """
        return [o for o in self.outcomes.values() if o.get("regime") == regime]
    
    def clear(self):
        """Clear all outcomes."""
        self.outcomes.clear()
        logger.info("[OutcomeRegistry] Cleared all outcomes")
    
    def count(self) -> int:
        """Get total outcome count."""
        return len(self.outcomes)
