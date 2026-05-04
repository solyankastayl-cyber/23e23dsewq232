"""
Recovery Regime Filter
======================

Regime filter for Recovery Engine (PHASE 1.4)
"""

from typing import Dict, List, Optional, Any

from .recovery_types import RegimeFilterResult


class RecoveryRegimeFilter:
    """
    Filters recovery based on market regime.
    
    Recovery is only allowed in specific regimes where
    mean reversion has statistical edge.
    """
    
    def __init__(self):
        self._build_regime_matrix()
    
    def _build_regime_matrix(self):
        """Build regime compatibility matrix for recovery"""
        
        # Regime -> (level, reason)
        self._regime_matrix: Dict[str, Dict[str, Any]] = {
            # ALLOWED - Recovery has edge
            "RANGE": {
                "level": "ALLOWED",
                "reason": "Range-bound market supports mean reversion recovery"
            },
            "LOW_VOLATILITY": {
                "level": "ALLOWED", 
                "reason": "Low volatility reduces recovery risk"
            },
            
            # CONDITIONAL - Recovery possible with extra caution
            "TRANSITION": {
                "level": "CONDITIONAL",
                "reason": "Transition regime - recovery allowed with reduced size"
            },
            
            # FORBIDDEN - Recovery too risky
            "TRENDING": {
                "level": "FORBIDDEN",
                "reason": "Trending market - recovery will compound losses"
            },
            "HIGH_VOLATILITY": {
                "level": "FORBIDDEN",
                "reason": "High volatility - recovery too risky"
            }
        }
    
    def check_regime(self, regime: str) -> RegimeFilterResult:
        """
        Check if recovery is allowed in given regime.
        """
        
        regime_upper = regime.upper()
        
        if regime_upper not in self._regime_matrix:
            return RegimeFilterResult(
                allowed=False,
                regime=regime_upper,
                level="UNKNOWN",
                reason=f"Unknown regime: {regime_upper}",
                notes=["Regime not in recovery matrix, defaulting to DENY"]
            )
        
        config = self._regime_matrix[regime_upper]
        level = config["level"]
        reason = config["reason"]
        
        allowed = level in ["ALLOWED", "CONDITIONAL"]
        
        notes = []
        if level == "CONDITIONAL":
            notes.append("Recovery allowed but with reduced size multiplier")
            notes.append("Extra caution required in transition regime")
        elif level == "FORBIDDEN":
            notes.append("Recovery blocked due to regime risk")
        
        return RegimeFilterResult(
            allowed=allowed,
            regime=regime_upper,
            level=level,
            reason=reason,
            notes=notes
        )
    
    def get_allowed_regimes(self) -> List[str]:
        """Get list of regimes where recovery is allowed"""
        return [
            regime for regime, config in self._regime_matrix.items()
            if config["level"] in ["ALLOWED", "CONDITIONAL"]
        ]
    
    def get_forbidden_regimes(self) -> List[str]:
        """Get list of regimes where recovery is forbidden"""
        return [
            regime for regime, config in self._regime_matrix.items()
            if config["level"] == "FORBIDDEN"
        ]
    
    def get_regime_matrix(self) -> Dict[str, Dict[str, Any]]:
        """Get full regime matrix"""
        return {
            regime: {
                "level": config["level"],
                "reason": config["reason"],
                "recoveryAllowed": config["level"] in ["ALLOWED", "CONDITIONAL"]
            }
            for regime, config in self._regime_matrix.items()
        }
    
    def get_size_multiplier_for_regime(self, regime: str) -> float:
        """
        Get size multiplier for recovery in given regime.
        
        Returns multiplier to apply to standard add size.
        """
        regime_upper = regime.upper()
        
        if regime_upper not in self._regime_matrix:
            return 0.0
        
        level = self._regime_matrix[regime_upper]["level"]
        
        if level == "ALLOWED":
            return 1.0  # Full size
        elif level == "CONDITIONAL":
            return 0.5  # Half size in transition
        else:
            return 0.0  # No recovery


# Global singleton
recovery_regime_filter = RecoveryRegimeFilter()
