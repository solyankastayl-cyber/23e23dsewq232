"""
PHASE 13.3 - Factor Constraints
================================
Constraints to prevent generating garbage factors.

Rules:
- max_inputs = 3
- min_categories = 2 (for multi-feature)
- no_duplicate_features
- regime_specificity_required
- max_complexity = 3
"""

from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass

from .factor_types import Factor, FactorTemplate


@dataclass
class ConstraintConfig:
    """Factor generation constraints."""
    max_inputs: int = 3
    min_categories_for_pair: int = 1
    min_categories_for_triple: int = 2
    max_complexity: int = 3
    allow_same_category_triple: bool = False
    require_regime_for_regime_template: bool = True
    max_factors_per_template: int = 500
    max_total_factors: int = 2000


DEFAULT_CONSTRAINTS = ConstraintConfig()


class FactorConstraints:
    """
    Validates factors against constraints.
    """
    
    def __init__(self, config: ConstraintConfig = None):
        self.config = config or DEFAULT_CONSTRAINTS
        self.template_counts: Dict[str, int] = {}
        self.total_count: int = 0
    
    def reset(self):
        """Reset counts."""
        self.template_counts = {}
        self.total_count = 0
    
    def validate(self, factor: Factor) -> Tuple[bool, str]:
        """
        Validate factor against constraints.
        
        Returns:
            (is_valid, reason)
        """
        # Check total count
        if self.total_count >= self.config.max_total_factors:
            return False, "Max total factors reached"
        
        # Check template count
        template_key = factor.template.value if hasattr(factor.template, 'value') else str(factor.template)
        template_count = self.template_counts.get(template_key, 0)
        if template_count >= self.config.max_factors_per_template:
            return False, f"Max factors for template {template_key} reached"
        
        # Check inputs count
        if len(factor.inputs) > self.config.max_inputs:
            return False, f"Too many inputs: {len(factor.inputs)} > {self.config.max_inputs}"
        
        # Check complexity
        if factor.complexity > self.config.max_complexity:
            return False, f"Complexity too high: {factor.complexity} > {self.config.max_complexity}"
        
        # Check categories for triple
        if factor.template == FactorTemplate.TRIPLE_FEATURE:
            unique_cats = set(factor.input_categories)
            if len(unique_cats) < self.config.min_categories_for_triple:
                if not self.config.allow_same_category_triple:
                    return False, f"Triple needs {self.config.min_categories_for_triple} categories"
        
        # Check regime for regime template
        if factor.template == FactorTemplate.REGIME_CONDITIONED:
            if self.config.require_regime_for_regime_template:
                if not factor.regime_dependency:
                    return False, "Regime template requires regime_dependency"
        
        # Check duplicate inputs
        if len(factor.inputs) != len(set(factor.inputs)):
            return False, "Duplicate inputs"
        
        return True, "Valid"
    
    def accept(self, factor: Factor):
        """
        Mark factor as accepted (increment counts).
        """
        template_key = factor.template.value if hasattr(factor.template, 'value') else str(factor.template)
        self.template_counts[template_key] = self.template_counts.get(template_key, 0) + 1
        self.total_count += 1
    
    def get_stats(self) -> Dict:
        """Get constraint statistics."""
        return {
            "total_count": self.total_count,
            "template_counts": self.template_counts.copy(),
            "limits": {
                "max_total": self.config.max_total_factors,
                "max_per_template": self.config.max_factors_per_template
            }
        }
