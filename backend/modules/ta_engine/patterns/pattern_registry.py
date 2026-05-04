"""
Pattern Registry
================
Registry of supported pattern types and their validators.
"""

from __future__ import annotations
from typing import List, Protocol, Any, Dict, Optional

from .pattern_candidate import PatternCandidate, PatternWindow


class PatternValidator(Protocol):
    """Protocol for pattern validators."""
    pattern_type: str
    
    def validate(
        self,
        candles: List[Dict[str, Any]],
        pivot_highs: List[Dict[str, Any]],
        pivot_lows: List[Dict[str, Any]],
        window: PatternWindow,
        structure_context: Dict[str, Any],
        liquidity: Dict[str, Any],
        displacement: Dict[str, Any],
        poi: Dict[str, Any],
    ) -> Optional[PatternCandidate]:
        ...


class PatternRegistry:
    """Registry of all supported pattern validators."""
    
    def __init__(self, validators: List[PatternValidator]):
        self._validators = validators
        self._type_map = {v.pattern_type: v for v in validators}
    
    def validators(self) -> List[PatternValidator]:
        """Get all registered validators."""
        return self._validators
    
    def get_validator(self, pattern_type: str) -> Optional[PatternValidator]:
        """Get validator by pattern type."""
        return self._type_map.get(pattern_type)
    
    def supported_types(self) -> List[str]:
        """Get list of supported pattern types."""
        return list(self._type_map.keys())
