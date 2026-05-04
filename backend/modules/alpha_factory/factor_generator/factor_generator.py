"""
PHASE 13.3 - Factor Generator
==============================
Main factor generation engine.

Generates 1000+ factors from 308 features using:
- 8 templates
- Feature selector
- Combinator
- Constraints
"""

from typing import Dict, List, Optional, Tuple
from datetime import datetime, timezone
import uuid
import random

from .factor_types import (
    Factor, FactorFamily, FactorTemplate, FactorStatus,
    FactorBatchRun, BatchRunStatus
)
from .factor_templates import REGIME_TYPES, infer_family_from_categories
from .feature_selector import FeatureSelector
from .factor_combinator import FactorCombinator
from .factor_constraints import FactorConstraints, ConstraintConfig
from .factor_repository import FactorRepository


class FactorGenerator:
    """
    Main factor generation engine.
    """
    
    def __init__(self, repository: FactorRepository = None):
        self.selector = FeatureSelector()
        self.combinator = FactorCombinator()
        self.constraints = FactorConstraints()
        self.repository = repository or FactorRepository()
        
        # Stats
        self.last_run: Optional[FactorBatchRun] = None
    
    def reset(self):
        """Reset generator state."""
        self.selector.reset()
        self.combinator.reset()
        self.constraints.reset()
    
    def generate_batch(
        self,
        features: List[Dict],
        config: Dict = None
    ) -> FactorBatchRun:
        """
        Generate a batch of factors from features.
        
        Args:
            features: List of feature dicts from Feature Library
            config: Generation configuration
        
        Returns:
            FactorBatchRun with results
        """
        config = config or {}
        
        # Create run
        run = FactorBatchRun(
            run_id=str(uuid.uuid4())[:8],
            started_at=datetime.now(timezone.utc),
            status=BatchRunStatus.RUNNING,
            config=config
        )
        
        self.reset()
        
        # Configure constraints
        constraint_config = ConstraintConfig(
            max_inputs=config.get("max_inputs", 3),
            max_factors_per_template=config.get("max_per_template", 200),
            max_total_factors=config.get("max_total", 1500)
        )
        self.constraints = FactorConstraints(constraint_config)
        
        factors: List[Factor] = []
        family_counts: Dict[str, int] = {}
        template_counts: Dict[str, int] = {}
        rejected_count = 0
        
        try:
            # 1. Single feature factors (limited)
            single_factors = self._generate_single_factors(
                features, 
                max_count=config.get("max_single", 50)
            )
            factors.extend(single_factors)
            
            # 2. Pair factors
            pair_factors = self._generate_pair_factors(
                features,
                max_count=config.get("max_pair", 400)
            )
            factors.extend(pair_factors)
            
            # 3. Triple factors
            triple_factors = self._generate_triple_factors(
                features,
                max_count=config.get("max_triple", 300)
            )
            factors.extend(triple_factors)
            
            # 4. Ratio factors
            ratio_factors = self._generate_ratio_factors(
                features,
                max_count=config.get("max_ratio", 200)
            )
            factors.extend(ratio_factors)
            
            # 5. Difference factors
            diff_factors = self._generate_difference_factors(
                features,
                max_count=config.get("max_diff", 150)
            )
            factors.extend(diff_factors)
            
            # 6. Interaction factors
            interaction_factors = self._generate_interaction_factors(
                features,
                max_count=config.get("max_interaction", 200)
            )
            factors.extend(interaction_factors)
            
            # 7. Regime-conditioned factors
            regime_factors = self._generate_regime_factors(
                features,
                max_count=config.get("max_regime", 150)
            )
            factors.extend(regime_factors)
            
            # Validate and count
            valid_factors = []
            for f in factors:
                is_valid, reason = self.constraints.validate(f)
                if is_valid:
                    self.constraints.accept(f)
                    valid_factors.append(f)
                    
                    # Count by family
                    family_key = f.family.value if hasattr(f.family, 'value') else str(f.family)
                    family_counts[family_key] = family_counts.get(family_key, 0) + 1
                    
                    # Count by template
                    template_key = f.template.value if hasattr(f.template, 'value') else str(f.template)
                    template_counts[template_key] = template_counts.get(template_key, 0) + 1
                else:
                    rejected_count += 1
            
            # Save to repository
            if self.repository.connected:
                for f in valid_factors:
                    self.repository.save_factor(f)
            
            # Update run
            run.generated_count = len(factors)
            run.accepted_count = len(valid_factors)
            run.rejected_count = rejected_count
            run.family_counts = family_counts
            run.template_counts = template_counts
            run.status = BatchRunStatus.COMPLETED
            
        except Exception as e:
            run.status = BatchRunStatus.FAILED
            run.error_message = str(e)
        
        run.finished_at = datetime.now(timezone.utc)
        run.duration_seconds = (run.finished_at - run.started_at).total_seconds()
        
        # Save run
        if self.repository.connected:
            self.repository.save_run(run)
        
        self.last_run = run
        return run
    
    def _generate_single_factors(
        self, 
        features: List[Dict], 
        max_count: int = 50
    ) -> List[Factor]:
        """Generate single feature factors."""
        factors = []
        
        # Select important features
        important_tags = ["momentum", "strength", "zscore", "percentile", "regime"]
        important_features = [
            f for f in features 
            if any(tag in f.get("tags", []) for tag in important_tags)
        ]
        
        random.shuffle(important_features)
        
        for feature in important_features[:max_count]:
            factor = self.combinator.create_single_factor(feature)
            factors.append(factor)
        
        return factors
    
    def _generate_pair_factors(
        self,
        features: List[Dict],
        max_count: int = 400
    ) -> List[Factor]:
        """Generate pair factors."""
        factors = []
        
        pairs = self.selector.select_pairs(features, max_pairs=max_count)
        
        for f1, f2 in pairs:
            factor = self.combinator.create_pair_factor(f1, f2)
            factors.append(factor)
        
        return factors
    
    def _generate_triple_factors(
        self,
        features: List[Dict],
        max_count: int = 300
    ) -> List[Factor]:
        """Generate triple factors."""
        factors = []
        
        triples = self.selector.select_triples(features, max_triples=max_count)
        
        for f1, f2, f3 in triples:
            factor = self.combinator.create_triple_factor(f1, f2, f3)
            factors.append(factor)
        
        return factors
    
    def _generate_ratio_factors(
        self,
        features: List[Dict],
        max_count: int = 200
    ) -> List[Factor]:
        """Generate ratio factors."""
        factors = []
        
        pairs = self.selector.select_pairs(features, max_pairs=max_count)
        
        for f1, f2 in pairs[:max_count]:
            # Only ratio features with same output type
            if f1.get("output_type") == f2.get("output_type") == "numeric":
                factor = self.combinator.create_ratio_factor(f1, f2)
                factors.append(factor)
        
        return factors
    
    def _generate_difference_factors(
        self,
        features: List[Dict],
        max_count: int = 150
    ) -> List[Factor]:
        """Generate difference factors."""
        factors = []
        
        # Same category differences are most meaningful
        by_category: Dict[str, List[Dict]] = {}
        for f in features:
            cat = f.get("category", "price")
            if cat not in by_category:
                by_category[cat] = []
            by_category[cat].append(f)
        
        count = 0
        for cat, cat_features in by_category.items():
            if count >= max_count:
                break
            
            # Sample pairs from same category
            for i, f1 in enumerate(cat_features):
                for f2 in cat_features[i+1:]:
                    if count >= max_count:
                        break
                    if f1.get("output_type") == f2.get("output_type") == "numeric":
                        factor = self.combinator.create_difference_factor(f1, f2)
                        factors.append(factor)
                        count += 1
        
        return factors
    
    def _generate_interaction_factors(
        self,
        features: List[Dict],
        max_count: int = 200
    ) -> List[Factor]:
        """Generate interaction (product) factors."""
        factors = []
        
        pairs = self.selector.select_pairs(features, max_pairs=max_count, min_categories=2)
        
        for f1, f2 in pairs[:max_count]:
            # Cross-category interactions only
            if f1.get("category") != f2.get("category"):
                factor = self.combinator.create_interaction_factor(f1, f2)
                factors.append(factor)
        
        return factors
    
    def _generate_regime_factors(
        self,
        features: List[Dict],
        max_count: int = 150
    ) -> List[Factor]:
        """Generate regime-conditioned factors."""
        factors = []
        
        # Select features that make sense in regimes
        regime_relevant = [
            f for f in features
            if any(tag in f.get("tags", []) for tag in ["momentum", "trend", "breakout", "reversal"])
        ]
        
        random.shuffle(regime_relevant)
        
        count = 0
        for feature in regime_relevant:
            if count >= max_count:
                break
            
            # Pick relevant regimes
            feature_tags = feature.get("tags", [])
            
            for regime in ["TRENDING_UP", "TRENDING_DOWN", "HIGH_VOL", "LOW_VOL", "RANGE"]:
                if count >= max_count:
                    break
                
                factor = self.combinator.create_regime_factor(feature, regime)
                factors.append(factor)
                count += 1
        
        return factors
    
    def get_stats(self) -> Dict:
        """Get generator statistics."""
        repo_stats = self.repository.get_stats()
        constraint_stats = self.constraints.get_stats()
        
        return {
            "repository": repo_stats,
            "constraints": constraint_stats,
            "last_run": self.last_run.to_dict() if self.last_run else None
        }


# Global singleton
_generator_instance: Optional[FactorGenerator] = None


def get_factor_generator() -> FactorGenerator:
    """Get singleton generator instance."""
    global _generator_instance
    if _generator_instance is None:
        _generator_instance = FactorGenerator()
    return _generator_instance
