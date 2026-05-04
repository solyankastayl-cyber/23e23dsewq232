"""
PHASE 11.6.2 - Cooldown Manager
================================
Prevents rapid consecutive changes.

Ensures:
- Parameter changed → wait N days before next change
- Weight changed → wait M days
- Strategy disabled → wait P days before re-enabling
"""

from typing import Dict, Optional, Tuple
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass

from ..adaptive_types import DEFAULT_ADAPTIVE_CONFIG


@dataclass
class CooldownRecord:
    """Record of a cooldown period."""
    key: str
    change_type: str
    applied_at: datetime
    cooldown_ends: datetime
    change_details: Dict


class CooldownManager:
    """
    Cooldown Manager
    
    Tracks when changes were applied and enforces
    minimum waiting periods before new changes.
    """
    
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or DEFAULT_ADAPTIVE_CONFIG
        self.active_cooldowns: Dict[str, CooldownRecord] = {}
        self.cooldown_history: list = []
        self.max_history = 500
    
    def start_cooldown(
        self,
        key: str,
        change_type: str,
        change_details: Optional[Dict] = None
    ) -> CooldownRecord:
        """
        Start a cooldown period for a change.
        
        Args:
            key: Unique identifier (e.g., "strat_1_lookback")
            change_type: Type of change (PARAMETER, WEIGHT, STRATEGY, ALLOCATION)
            change_details: Details about the change made
            
        Returns:
            CooldownRecord
        """
        now = datetime.now(timezone.utc)
        
        # Get cooldown duration based on type
        if change_type == "PARAMETER":
            hours = self.config["parameter_cooldown_hours"]
        elif change_type == "WEIGHT":
            hours = self.config["weight_cooldown_hours"]
        elif change_type == "STRATEGY":
            hours = self.config["strategy_cooldown_hours"]
        else:
            hours = 24  # Default 24 hours
        
        cooldown_ends = now + timedelta(hours=hours)
        
        record = CooldownRecord(
            key=key,
            change_type=change_type,
            applied_at=now,
            cooldown_ends=cooldown_ends,
            change_details=change_details or {}
        )
        
        self.active_cooldowns[key] = record
        self.cooldown_history.append(record)
        
        # Trim history
        if len(self.cooldown_history) > self.max_history:
            self.cooldown_history = self.cooldown_history[-self.max_history:]
        
        return record
    
    def check_cooldown(self, key: str) -> Tuple[bool, Optional[datetime]]:
        """
        Check if a key is in cooldown.
        
        Returns:
            Tuple of (is_clear, cooldown_ends_at)
            - is_clear: True if no active cooldown
            - cooldown_ends_at: When cooldown ends (None if clear)
        """
        now = datetime.now(timezone.utc)
        
        record = self.active_cooldowns.get(key)
        
        if not record:
            return True, None
        
        if now >= record.cooldown_ends:
            # Cooldown has expired
            del self.active_cooldowns[key]
            return True, None
        
        return False, record.cooldown_ends
    
    def get_remaining_cooldown(self, key: str) -> Optional[timedelta]:
        """Get remaining cooldown time for a key."""
        is_clear, ends_at = self.check_cooldown(key)
        
        if is_clear:
            return None
        
        return ends_at - datetime.now(timezone.utc)
    
    def force_clear_cooldown(self, key: str) -> bool:
        """Force clear a cooldown (use with caution)."""
        if key in self.active_cooldowns:
            del self.active_cooldowns[key]
            return True
        return False
    
    def extend_cooldown(self, key: str, additional_hours: float) -> bool:
        """Extend an existing cooldown."""
        record = self.active_cooldowns.get(key)
        
        if not record:
            return False
        
        record.cooldown_ends += timedelta(hours=additional_hours)
        return True
    
    def get_active_cooldowns(self) -> Dict[str, Dict]:
        """Get all active cooldowns."""
        now = datetime.now(timezone.utc)
        result = {}
        
        for key, record in list(self.active_cooldowns.items()):
            if now >= record.cooldown_ends:
                del self.active_cooldowns[key]
            else:
                remaining = record.cooldown_ends - now
                result[key] = {
                    "change_type": record.change_type,
                    "applied_at": record.applied_at.isoformat(),
                    "cooldown_ends": record.cooldown_ends.isoformat(),
                    "remaining_hours": remaining.total_seconds() / 3600
                }
        
        return result
    
    def get_cooldown_summary(self) -> Dict:
        """Get summary of cooldown state."""
        now = datetime.now(timezone.utc)
        
        # Clean up expired
        for key in list(self.active_cooldowns.keys()):
            if now >= self.active_cooldowns[key].cooldown_ends:
                del self.active_cooldowns[key]
        
        # Count by type
        by_type = {}
        for record in self.active_cooldowns.values():
            t = record.change_type
            by_type[t] = by_type.get(t, 0) + 1
        
        return {
            "active_cooldowns": len(self.active_cooldowns),
            "by_type": by_type,
            "total_historical": len(self.cooldown_history),
            "cooldown_config": {
                "parameter_hours": self.config["parameter_cooldown_hours"],
                "weight_hours": self.config["weight_cooldown_hours"],
                "strategy_hours": self.config["strategy_cooldown_hours"]
            }
        }
