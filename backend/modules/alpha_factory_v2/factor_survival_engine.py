"""
PHASE 26.3 — Factor Survival Engine

Natural selection for alpha factors.

Rules:
1. Base threshold: alpha_score >= 0.55
2. Additional filters:
   - sharpe_score >= 0.40
   - stability_score >= 0.35
   - drawdown_score >= 0.30
3. Overfitting cap: alpha_score <= 0.85

Pipeline:
CANDIDATE → ACTIVE (if passes all checks)
CANDIDATE → DEPRECATED (if fails any check)
"""

from typing import List, Optional, Tuple
from datetime import datetime

from .factor_types import (
    AlphaFactor,
    FactorStatus,
    SURVIVAL_THRESHOLD,
)


# ══════════════════════════════════════════════════════════════
# Survival Summary
# ══════════════════════════════════════════════════════════════

from pydantic import BaseModel


class SurvivalSummary(BaseModel):
    """Summary of survival filtering results."""
    total_factors: int
    active_factors: int
    deprecated_factors: int
    strongest_factor: Optional[str]
    weakest_factor: Optional[str]
    average_alpha_score: float
    
    # Filter statistics
    failed_alpha_threshold: int = 0
    failed_sharpe_filter: int = 0
    failed_stability_filter: int = 0
    failed_drawdown_filter: int = 0


# ══════════════════════════════════════════════════════════════
# Constants
# ══════════════════════════════════════════════════════════════

# Base survival threshold
ALPHA_THRESHOLD = 0.55

# Additional filter thresholds
SHARPE_THRESHOLD = 0.40
STABILITY_THRESHOLD = 0.35
DRAWDOWN_THRESHOLD = 0.30

# Overfitting cap
OVERFIT_CAP = 0.85


class FactorSurvivalEngine:
    """
    Factor Survival Engine.
    
    Determines which factors survive to become ACTIVE.
    
    Survival Rules:
    - alpha_score >= 0.55
    - sharpe_score >= 0.40
    - stability_score >= 0.35
    - drawdown_score >= 0.30
    
    Overfitting Protection:
    - alpha_score capped at 0.85
    """
    
    def __init__(self):
        self._survived_factors: List[AlphaFactor] = []
        self._last_survival: Optional[datetime] = None
        self._summary: Optional[SurvivalSummary] = None
    
    # ═══════════════════════════════════════════════════════════
    # Main Survival
    # ═══════════════════════════════════════════════════════════
    
    def apply_survival(
        self,
        factors: List[AlphaFactor],
    ) -> List[AlphaFactor]:
        """
        Apply survival filter to list of factors.
        
        Args:
            factors: List of scored AlphaFactor
        
        Returns:
            List of AlphaFactor with updated status (ACTIVE/DEPRECATED)
        """
        survived = []
        
        # Statistics for summary
        failed_alpha = 0
        failed_sharpe = 0
        failed_stability = 0
        failed_drawdown = 0
        
        for factor in factors:
            # Apply overfitting cap first
            capped_factor = self._apply_overfit_cap(factor)
            
            # Check survival
            survives, fail_reason = self._check_survival(capped_factor)
            
            # Update status
            if survives:
                capped_factor = self._update_status(capped_factor, "ACTIVE")
            else:
                capped_factor = self._update_status(capped_factor, "DEPRECATED")
                
                # Track failure reasons
                if fail_reason == "alpha":
                    failed_alpha += 1
                elif fail_reason == "sharpe":
                    failed_sharpe += 1
                elif fail_reason == "stability":
                    failed_stability += 1
                elif fail_reason == "drawdown":
                    failed_drawdown += 1
            
            survived.append(capped_factor)
        
        self._survived_factors = survived
        self._last_survival = datetime.utcnow()
        
        # Build summary
        self._summary = self._build_summary(
            survived,
            failed_alpha,
            failed_sharpe,
            failed_stability,
            failed_drawdown,
        )
        
        return survived
    
    def _check_survival(
        self,
        factor: AlphaFactor,
    ) -> Tuple[bool, Optional[str]]:
        """
        Check if factor survives.
        
        Returns:
            (survives: bool, fail_reason: Optional[str])
        """
        # Check alpha threshold
        if factor.alpha_score < ALPHA_THRESHOLD:
            return False, "alpha"
        
        # Check sharpe filter
        if factor.sharpe_score < SHARPE_THRESHOLD:
            return False, "sharpe"
        
        # Check stability filter
        if factor.stability_score < STABILITY_THRESHOLD:
            return False, "stability"
        
        # Check drawdown filter
        if factor.drawdown_score < DRAWDOWN_THRESHOLD:
            return False, "drawdown"
        
        return True, None
    
    def _apply_overfit_cap(
        self,
        factor: AlphaFactor,
    ) -> AlphaFactor:
        """
        Apply overfitting protection cap.
        
        If alpha_score > 0.85, cap it to 0.85.
        """
        if factor.alpha_score <= OVERFIT_CAP:
            return factor
        
        # Create new factor with capped score
        return AlphaFactor(
            factor_id=factor.factor_id,
            name=factor.name,
            category=factor.category,
            lookback=factor.lookback,
            signal_strength=factor.signal_strength,
            sharpe_score=factor.sharpe_score,
            stability_score=factor.stability_score,
            drawdown_score=factor.drawdown_score,
            alpha_score=OVERFIT_CAP,  # Capped
            status=factor.status,
            parameters=factor.parameters,
            source=factor.source,
            created_at=factor.created_at,
            last_evaluated=factor.last_evaluated,
        )
    
    def _update_status(
        self,
        factor: AlphaFactor,
        new_status: FactorStatus,
    ) -> AlphaFactor:
        """Update factor status."""
        return AlphaFactor(
            factor_id=factor.factor_id,
            name=factor.name,
            category=factor.category,
            lookback=factor.lookback,
            signal_strength=factor.signal_strength,
            sharpe_score=factor.sharpe_score,
            stability_score=factor.stability_score,
            drawdown_score=factor.drawdown_score,
            alpha_score=factor.alpha_score,
            status=new_status,
            parameters=factor.parameters,
            source=factor.source,
            created_at=factor.created_at,
            last_evaluated=datetime.utcnow(),
        )
    
    # ═══════════════════════════════════════════════════════════
    # Summary
    # ═══════════════════════════════════════════════════════════
    
    def _build_summary(
        self,
        factors: List[AlphaFactor],
        failed_alpha: int,
        failed_sharpe: int,
        failed_stability: int,
        failed_drawdown: int,
    ) -> SurvivalSummary:
        """Build survival summary."""
        if not factors:
            return SurvivalSummary(
                total_factors=0,
                active_factors=0,
                deprecated_factors=0,
                strongest_factor=None,
                weakest_factor=None,
                average_alpha_score=0.0,
            )
        
        active = [f for f in factors if f.status == "ACTIVE"]
        deprecated = [f for f in factors if f.status == "DEPRECATED"]
        
        # Find strongest and weakest
        sorted_factors = sorted(factors, key=lambda f: f.alpha_score, reverse=True)
        strongest = sorted_factors[0].name if sorted_factors else None
        weakest = sorted_factors[-1].name if sorted_factors else None
        
        # Average alpha score
        avg_alpha = sum(f.alpha_score for f in factors) / len(factors)
        
        return SurvivalSummary(
            total_factors=len(factors),
            active_factors=len(active),
            deprecated_factors=len(deprecated),
            strongest_factor=strongest,
            weakest_factor=weakest,
            average_alpha_score=round(avg_alpha, 4),
            failed_alpha_threshold=failed_alpha,
            failed_sharpe_filter=failed_sharpe,
            failed_stability_filter=failed_stability,
            failed_drawdown_filter=failed_drawdown,
        )
    
    # ═══════════════════════════════════════════════════════════
    # Accessors
    # ═══════════════════════════════════════════════════════════
    
    def get_survived_factors(self) -> List[AlphaFactor]:
        """Get all factors after survival filtering."""
        return self._survived_factors
    
    def get_active_factors(self) -> List[AlphaFactor]:
        """Get only ACTIVE factors."""
        return [f for f in self._survived_factors if f.status == "ACTIVE"]
    
    def get_deprecated_factors(self) -> List[AlphaFactor]:
        """Get only DEPRECATED factors."""
        return [f for f in self._survived_factors if f.status == "DEPRECATED"]
    
    def get_summary(self) -> Optional[SurvivalSummary]:
        """Get survival summary."""
        return self._summary
    
    def get_strongest_factor(self) -> Optional[AlphaFactor]:
        """Get the strongest factor by alpha_score."""
        if not self._survived_factors:
            return None
        return max(self._survived_factors, key=lambda f: f.alpha_score)
    
    def get_weakest_factor(self) -> Optional[AlphaFactor]:
        """Get the weakest factor by alpha_score."""
        if not self._survived_factors:
            return None
        return min(self._survived_factors, key=lambda f: f.alpha_score)
    
    @property
    def last_survival(self) -> Optional[datetime]:
        """Get timestamp of last survival run."""
        return self._last_survival


# Singleton
_engine: Optional[FactorSurvivalEngine] = None


def get_factor_survival_engine() -> FactorSurvivalEngine:
    """Get singleton instance of FactorSurvivalEngine."""
    global _engine
    if _engine is None:
        _engine = FactorSurvivalEngine()
    return _engine
