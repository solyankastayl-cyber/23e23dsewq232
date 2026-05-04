"""
PHASE 26.6 — Alpha Validation Engine

Validates alpha factory stability and health.

Checks:
1. Alpha Stability (drift ≤ 0.20)
2. Factor Turnover (≤ 0.40)
3. Alpha Distribution (mean ∈ [0.40, 0.70])
4. Category Balance (no category > 60%)
5. Active Factor Limit (≤ 30)

Output:
AlphaValidationReport with validation_state: PASSED | WARNING | FAILED
"""

from typing import List, Optional, Dict, Literal
from datetime import datetime
from pydantic import BaseModel, Field

from .alpha_registry import AlphaRegistry, get_alpha_registry, RegistryAlphaFactor
from .factor_types import FactorCategory, FACTOR_CATEGORIES


# ══════════════════════════════════════════════════════════════
# Constants
# ══════════════════════════════════════════════════════════════

# Alpha drift threshold
ALPHA_DRIFT_THRESHOLD = 0.20

# Factor turnover threshold
TURNOVER_THRESHOLD = 0.40

# Alpha distribution bounds
ALPHA_MEAN_MIN = 0.40
ALPHA_MEAN_MAX = 0.70

# Overfit threshold
OVERFIT_THRESHOLD = 0.80

# Category balance threshold
CATEGORY_DOMINANCE_THRESHOLD = 0.60

# Max active factors
MAX_ACTIVE_FACTORS = 30


# ══════════════════════════════════════════════════════════════
# Validation Report Contract
# ══════════════════════════════════════════════════════════════

class AlphaValidationReport(BaseModel):
    """Validation report for alpha factory."""
    
    # Stability checks
    stability_passed: bool
    turnover_rate: float
    alpha_drift_max: float
    
    # Distribution
    average_alpha_score: float
    alpha_score_min: float = 0.0
    alpha_score_max: float = 0.0
    
    # Factor counts
    active_factors: int
    deprecated_factors: int
    total_factors: int
    
    # Category balance
    category_balance: Dict[str, float] = Field(default_factory=dict)
    category_balance_passed: bool = True
    
    # Overall state
    validation_state: Literal["PASSED", "WARNING", "FAILED"]
    
    # Warnings and errors
    warnings: List[str] = Field(default_factory=list)
    errors: List[str] = Field(default_factory=list)
    
    # Metadata
    validated_at: datetime = Field(default_factory=datetime.utcnow)


class FactorDrift(BaseModel):
    """Drift record for a single factor."""
    factor_id: str
    name: str
    previous_score: float
    current_score: float
    drift: float
    is_stable: bool


# ══════════════════════════════════════════════════════════════
# Alpha Validation Engine
# ══════════════════════════════════════════════════════════════

class AlphaValidationEngine:
    """
    Alpha Validation Engine.
    
    Validates:
    - Alpha stability (drift)
    - Factor turnover
    - Alpha distribution
    - Category balance
    - Active factor limit
    """
    
    def __init__(self, registry: Optional[AlphaRegistry] = None):
        self._registry = registry or get_alpha_registry()
        self._previous_factors: Dict[str, float] = {}  # factor_id -> alpha_score
        self._last_validation: Optional[AlphaValidationReport] = None
    
    # ═══════════════════════════════════════════════════════════
    # Main Validation
    # ═══════════════════════════════════════════════════════════
    
    async def validate(self) -> AlphaValidationReport:
        """
        Run full validation on alpha factory.
        
        Returns AlphaValidationReport with validation_state.
        """
        warnings = []
        errors = []
        
        # Get all factors from registry
        all_factors = await self._registry.get_all_factors()
        
        if not all_factors:
            return AlphaValidationReport(
                stability_passed=True,
                turnover_rate=0.0,
                alpha_drift_max=0.0,
                average_alpha_score=0.0,
                active_factors=0,
                deprecated_factors=0,
                total_factors=0,
                validation_state="PASSED",
                warnings=["No factors in registry"],
            )
        
        # Separate active and deprecated
        active = [f for f in all_factors if f.status == "ACTIVE"]
        deprecated = [f for f in all_factors if f.status == "DEPRECATED"]
        
        # 1. Check Alpha Stability (drift)
        drift_result = self._check_alpha_drift(all_factors)
        stability_passed = drift_result["passed"]
        alpha_drift_max = drift_result["max_drift"]
        
        if not stability_passed:
            warnings.append(f"Alpha drift too high: {alpha_drift_max:.4f} > {ALPHA_DRIFT_THRESHOLD}")
        
        # 2. Check Factor Turnover
        turnover_rate = self._calculate_turnover(all_factors)
        
        if turnover_rate > TURNOVER_THRESHOLD:
            warnings.append(f"High turnover rate: {turnover_rate:.2%} > {TURNOVER_THRESHOLD:.0%}")
        
        # 3. Check Alpha Distribution
        distribution = self._check_distribution(all_factors)
        average_alpha = distribution["mean"]
        
        if average_alpha > OVERFIT_THRESHOLD:
            errors.append(f"Possible overfitting: mean alpha {average_alpha:.4f} > {OVERFIT_THRESHOLD}")
        elif average_alpha < ALPHA_MEAN_MIN:
            warnings.append(f"Low alpha scores: mean {average_alpha:.4f} < {ALPHA_MEAN_MIN}")
        
        # 4. Check Category Balance
        balance_result = self._check_category_balance(all_factors)
        category_balance_passed = balance_result["passed"]
        category_balance = balance_result["balance"]
        
        if not category_balance_passed:
            warnings.append(f"Category imbalance detected: {balance_result['dominant_category']}")
        
        # 5. Check Active Factor Limit
        if len(active) > MAX_ACTIVE_FACTORS:
            errors.append(f"Too many active factors: {len(active)} > {MAX_ACTIVE_FACTORS}")
        
        # Determine validation state
        if errors:
            validation_state = "FAILED"
        elif warnings:
            validation_state = "WARNING"
        else:
            validation_state = "PASSED"
        
        # Update previous factors for next validation
        self._update_previous_factors(all_factors)
        
        # Build report
        report = AlphaValidationReport(
            stability_passed=stability_passed,
            turnover_rate=round(turnover_rate, 4),
            alpha_drift_max=round(alpha_drift_max, 4),
            average_alpha_score=round(average_alpha, 4),
            alpha_score_min=round(distribution["min"], 4),
            alpha_score_max=round(distribution["max"], 4),
            active_factors=len(active),
            deprecated_factors=len(deprecated),
            total_factors=len(all_factors),
            category_balance=category_balance,
            category_balance_passed=category_balance_passed,
            validation_state=validation_state,
            warnings=warnings,
            errors=errors,
        )
        
        self._last_validation = report
        return report
    
    # ═══════════════════════════════════════════════════════════
    # Alpha Drift Check
    # ═══════════════════════════════════════════════════════════
    
    def _check_alpha_drift(
        self,
        factors: List[RegistryAlphaFactor],
    ) -> Dict:
        """
        Check alpha score drift.
        
        Drift = |current_score - previous_score|
        Threshold: 0.20
        """
        if not self._previous_factors:
            # First validation, no drift
            return {
                "passed": True,
                "max_drift": 0.0,
                "drifts": [],
            }
        
        drifts = []
        max_drift = 0.0
        
        for factor in factors:
            if factor.factor_id in self._previous_factors:
                prev_score = self._previous_factors[factor.factor_id]
                drift = abs(factor.alpha_score - prev_score)
                
                drifts.append(FactorDrift(
                    factor_id=factor.factor_id,
                    name=factor.name,
                    previous_score=prev_score,
                    current_score=factor.alpha_score,
                    drift=drift,
                    is_stable=drift <= ALPHA_DRIFT_THRESHOLD,
                ))
                
                max_drift = max(max_drift, drift)
        
        passed = max_drift <= ALPHA_DRIFT_THRESHOLD
        
        return {
            "passed": passed,
            "max_drift": max_drift,
            "drifts": drifts,
        }
    
    def calculate_drift(
        self,
        factor_id: str,
        current_score: float,
        previous_score: float,
    ) -> float:
        """Calculate drift for a single factor."""
        return abs(current_score - previous_score)
    
    # ═══════════════════════════════════════════════════════════
    # Turnover Calculation
    # ═══════════════════════════════════════════════════════════
    
    def _calculate_turnover(
        self,
        factors: List[RegistryAlphaFactor],
    ) -> float:
        """
        Calculate factor turnover rate.
        
        Turnover = replaced_factors / total_previous_active
        """
        if not self._previous_factors:
            return 0.0
        
        current_ids = {f.factor_id for f in factors if f.status == "ACTIVE"}
        previous_ids = set(self._previous_factors.keys())
        
        if not previous_ids:
            return 0.0
        
        # Factors that were replaced
        replaced = previous_ids - current_ids
        
        turnover = len(replaced) / len(previous_ids)
        return turnover
    
    def calculate_turnover(
        self,
        previous_active: List[str],
        current_active: List[str],
    ) -> float:
        """Public method to calculate turnover rate."""
        if not previous_active:
            return 0.0
        
        previous_set = set(previous_active)
        current_set = set(current_active)
        
        replaced = previous_set - current_set
        return len(replaced) / len(previous_set)
    
    # ═══════════════════════════════════════════════════════════
    # Distribution Check
    # ═══════════════════════════════════════════════════════════
    
    def _check_distribution(
        self,
        factors: List[RegistryAlphaFactor],
    ) -> Dict:
        """
        Check alpha score distribution.
        
        Expected mean: [0.40, 0.70]
        Overfit if mean > 0.80
        """
        if not factors:
            return {
                "mean": 0.0,
                "min": 0.0,
                "max": 0.0,
                "in_range": True,
            }
        
        scores = [f.alpha_score for f in factors]
        mean_score = sum(scores) / len(scores)
        min_score = min(scores)
        max_score = max(scores)
        
        in_range = ALPHA_MEAN_MIN <= mean_score <= ALPHA_MEAN_MAX
        
        return {
            "mean": mean_score,
            "min": min_score,
            "max": max_score,
            "in_range": in_range,
        }
    
    def check_distribution(
        self,
        alpha_scores: List[float],
    ) -> Dict:
        """Public method to check distribution."""
        if not alpha_scores:
            return {
                "mean": 0.0,
                "min": 0.0,
                "max": 0.0,
                "in_range": True,
            }
        
        mean_score = sum(alpha_scores) / len(alpha_scores)
        return {
            "mean": mean_score,
            "min": min(alpha_scores),
            "max": max(alpha_scores),
            "in_range": ALPHA_MEAN_MIN <= mean_score <= ALPHA_MEAN_MAX,
        }
    
    # ═══════════════════════════════════════════════════════════
    # Category Balance Check
    # ═══════════════════════════════════════════════════════════
    
    def _check_category_balance(
        self,
        factors: List[RegistryAlphaFactor],
    ) -> Dict:
        """
        Check category balance.
        
        No category should dominate > 60%
        """
        if not factors:
            return {
                "passed": True,
                "balance": {},
                "dominant_category": None,
            }
        
        # Count by category
        category_counts: Dict[str, int] = {cat: 0 for cat in FACTOR_CATEGORIES}
        
        for factor in factors:
            if factor.category in category_counts:
                category_counts[factor.category] += 1
        
        total = len(factors)
        balance = {
            cat: round(count / total, 4) if total > 0 else 0.0
            for cat, count in category_counts.items()
        }
        
        # Find dominant category
        dominant_category = None
        passed = True
        
        for cat, ratio in balance.items():
            if ratio > CATEGORY_DOMINANCE_THRESHOLD:
                dominant_category = cat
                passed = False
                break
        
        return {
            "passed": passed,
            "balance": balance,
            "dominant_category": dominant_category,
        }
    
    def check_category_balance(
        self,
        category_counts: Dict[str, int],
    ) -> Dict:
        """Public method to check category balance."""
        total = sum(category_counts.values())
        
        if total == 0:
            return {"passed": True, "balance": {}, "dominant_category": None}
        
        balance = {
            cat: round(count / total, 4)
            for cat, count in category_counts.items()
        }
        
        dominant_category = None
        passed = True
        
        for cat, ratio in balance.items():
            if ratio > CATEGORY_DOMINANCE_THRESHOLD:
                dominant_category = cat
                passed = False
                break
        
        return {
            "passed": passed,
            "balance": balance,
            "dominant_category": dominant_category,
        }
    
    # ═══════════════════════════════════════════════════════════
    # Helpers
    # ═══════════════════════════════════════════════════════════
    
    def _update_previous_factors(
        self,
        factors: List[RegistryAlphaFactor],
    ) -> None:
        """Store current factors for next validation."""
        self._previous_factors = {
            f.factor_id: f.alpha_score
            for f in factors
            if f.status == "ACTIVE"
        }
    
    def set_previous_factors(
        self,
        factors: Dict[str, float],
    ) -> None:
        """Set previous factors manually (for testing)."""
        self._previous_factors = factors.copy()
    
    # ═══════════════════════════════════════════════════════════
    # Accessors
    # ═══════════════════════════════════════════════════════════
    
    @property
    def last_validation(self) -> Optional[AlphaValidationReport]:
        """Get last validation report."""
        return self._last_validation
    
    def get_drift_drifts(self) -> List[FactorDrift]:
        """Get drift details from last validation."""
        # Re-run drift check with current data
        return []


# Singleton
_engine: Optional[AlphaValidationEngine] = None


def get_alpha_validation_engine() -> AlphaValidationEngine:
    """Get singleton instance of AlphaValidationEngine."""
    global _engine
    if _engine is None:
        _engine = AlphaValidationEngine()
    return _engine
