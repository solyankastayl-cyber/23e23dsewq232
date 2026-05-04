"""
Paper Execution Policy
======================

Phase 3.0A: Readiness-based signal filtering.

Responsibilities:
  - Check readiness state
  - Filter signals by readiness policy
  - Enforce max positions limits
  - Apply cooldown rules
"""

import logging
from typing import Dict, Any, List
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class PaperExecutionPolicy:
    """
    Execution policy based on readiness state.
    
    BLOCKED:
      - enabled = False
      - max_positions = 0
    
    LIMITED:
      - enabled = True
      - max_positions = 1
      - only majors cluster
    
    READY:
      - enabled = True
      - max_positions = 5
      - majors + alts
    """
    
    @staticmethod
    def can_execute(readiness_state: str) -> bool:
        """
        Check if execution is allowed.
        
        Args:
            readiness_state: "ready" | "limited" | "blocked"
        
        Returns:
            True if execution allowed, False otherwise
        """
        return readiness_state in ["ready", "limited"]
    
    @staticmethod
    def filter_signals(
        signals: List[Dict[str, Any]],
        readiness_state: str,
        current_open_count: int
    ) -> List[Dict[str, Any]]:
        """
        Filter signals based on readiness policy.
        
        Args:
            signals: List of selected signals
            readiness_state: Current readiness state
            current_open_count: Current number of open positions
        
        Returns:
            Filtered list of signals
        """
        if readiness_state == "blocked":
            logger.info("[Policy] BLOCKED: No signals allowed")
            return []
        
        # Filter by cluster if LIMITED
        if readiness_state == "limited":
            # Only majors
            signals = [
                s for s in signals 
                if s.get("features", {}).get("cluster") == "majors"
            ]
            logger.info(f"[Policy] LIMITED: Filtered to majors only ({len(signals)} signals)")
        
        # Apply max positions limit
        max_positions = PaperExecutionPolicy.get_max_positions(readiness_state)
        available_slots = max_positions - current_open_count
        
        if available_slots <= 0:
            logger.info(
                f"[Policy] Max positions reached: {current_open_count}/{max_positions}"
            )
            return []
        
        # Take only available slots
        filtered = signals[:available_slots]
        
        if len(filtered) < len(signals):
            logger.info(
                f"[Policy] Limited by max_positions: {len(filtered)}/{len(signals)} signals"
            )
        
        return filtered
    
    @staticmethod
    def get_max_positions(readiness_state: str) -> int:
        """
        Get max positions for readiness state.
        
        Args:
            readiness_state: Current readiness state
        
        Returns:
            Max allowed positions
        """
        if readiness_state == "ready":
            return 5
        elif readiness_state == "limited":
            return 1
        else:  # blocked
            return 0
