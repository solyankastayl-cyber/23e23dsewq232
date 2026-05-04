"""
PHASE 13.3 - Factor Combinator
===============================
Combines features into factors using templates.

Supports:
- Pair combinations (A + B)
- Triple combinations (A + B + C)
- Ratio combinations (A / B)
- Difference combinations (A - B)
- Conditional combinations (A if B)
- Interaction combinations (A * B)
"""

from typing import Dict, List, Optional, Tuple
from datetime import datetime, timezone
import hashlib

from .factor_types import Factor, FactorTemplate, FactorFamily, FactorStatus
from .factor_templates import (
    get_template_config, infer_family_from_categories, 
    infer_direction, REGIME_TYPES
)


class FactorCombinator:
    """
    Combines features into factors.
    """
    
    def __init__(self):
        self.generated_ids: set = set()
    
    def reset(self):
        """Reset generated IDs."""
        self.generated_ids = set()
    
    def _flatten_tags(self, *features) -> List[str]:
        """Flatten and deduplicate tags from features."""
        all_tags = []
        for f in features:
            tags = f.get("tags", [])
            if isinstance(tags, list):
                for t in tags:
                    if isinstance(t, str):
                        all_tags.append(t)
            elif isinstance(tags, str):
                all_tags.append(tags)
        return list(set(all_tags))
    
    def _generate_id(self, inputs: List[str], template: str) -> str:
        """Generate unique factor ID."""
        key = f"{template}:{'_'.join(sorted(inputs))}"
        factor_id = hashlib.md5(key.encode()).hexdigest()[:12]
        
        # Handle collisions
        base_id = factor_id
        counter = 1
        while factor_id in self.generated_ids:
            factor_id = f"{base_id}_{counter}"
            counter += 1
        
        self.generated_ids.add(factor_id)
        return factor_id
    
    def _generate_name(self, inputs: List[str], template: FactorTemplate) -> str:
        """Generate human-readable factor name."""
        template_prefix = {
            FactorTemplate.SINGLE_FEATURE: "single",
            FactorTemplate.PAIR_FEATURE: "pair",
            FactorTemplate.TRIPLE_FEATURE: "triple",
            FactorTemplate.RATIO_FEATURE: "ratio",
            FactorTemplate.DIFFERENCE_FEATURE: "diff",
            FactorTemplate.CONDITIONAL_FEATURE: "cond",
            FactorTemplate.REGIME_CONDITIONED: "regime",
            FactorTemplate.INTERACTION_FEATURE: "interact",
        }
        
        prefix = template_prefix.get(template, "factor")
        # Take first letters of inputs
        input_abbrev = "_".join(inp[:8] for inp in inputs[:3])
        return f"{prefix}_{input_abbrev}"
    
    def create_single_factor(
        self,
        feature: Dict,
        transforms: List[str] = None
    ) -> Factor:
        """
        Create single feature factor.
        """
        config = get_template_config(FactorTemplate.SINGLE_FEATURE)
        inputs = [feature["feature_id"]]
        categories = [feature.get("category", "price")]
        
        return Factor(
            factor_id=self._generate_id(inputs, "single"),
            name=self._generate_name(inputs, FactorTemplate.SINGLE_FEATURE),
            family=infer_family_from_categories(categories),
            template=FactorTemplate.SINGLE_FEATURE,
            inputs=inputs,
            input_categories=categories,
            transforms=transforms or config.default_transforms,
            expected_direction=infer_direction(inputs, categories),
            complexity=1,
            description=f"Single feature factor: {inputs[0]}",
            tags=self._flatten_tags(feature) + ["single"],
            created_at=datetime.now(timezone.utc),
            status=FactorStatus.CANDIDATE
        )
    
    def create_pair_factor(
        self,
        feature1: Dict,
        feature2: Dict,
        transforms: List[str] = None
    ) -> Factor:
        """
        Create pair feature factor (weighted sum).
        """
        config = get_template_config(FactorTemplate.PAIR_FEATURE)
        inputs = [feature1["feature_id"], feature2["feature_id"]]
        categories = [feature1.get("category"), feature2.get("category")]
        
        return Factor(
            factor_id=self._generate_id(inputs, "pair"),
            name=self._generate_name(inputs, FactorTemplate.PAIR_FEATURE),
            family=infer_family_from_categories(categories),
            template=FactorTemplate.PAIR_FEATURE,
            inputs=inputs,
            input_categories=categories,
            transforms=transforms or config.default_transforms,
            expected_direction=infer_direction(inputs, categories),
            complexity=2,
            description=f"Pair factor: {inputs[0]} + {inputs[1]}",
            tags=self._flatten_tags(feature1, feature2) + ["pair"],
            created_at=datetime.now(timezone.utc),
            status=FactorStatus.CANDIDATE
        )
    
    def create_triple_factor(
        self,
        feature1: Dict,
        feature2: Dict,
        feature3: Dict,
        transforms: List[str] = None
    ) -> Factor:
        """
        Create triple feature factor.
        """
        config = get_template_config(FactorTemplate.TRIPLE_FEATURE)
        inputs = [feature1["feature_id"], feature2["feature_id"], feature3["feature_id"]]
        categories = [feature1.get("category"), feature2.get("category"), feature3.get("category")]
        
        return Factor(
            factor_id=self._generate_id(inputs, "triple"),
            name=self._generate_name(inputs, FactorTemplate.TRIPLE_FEATURE),
            family=infer_family_from_categories(categories),
            template=FactorTemplate.TRIPLE_FEATURE,
            inputs=inputs,
            input_categories=categories,
            transforms=transforms or config.default_transforms,
            expected_direction=infer_direction(inputs, categories),
            complexity=3,
            description=f"Triple factor: {inputs[0]} + {inputs[1]} + {inputs[2]}",
            tags=self._flatten_tags(feature1, feature2, feature3) + ["triple"],
            created_at=datetime.now(timezone.utc),
            status=FactorStatus.CANDIDATE
        )
    
    def create_ratio_factor(
        self,
        numerator: Dict,
        denominator: Dict,
        transforms: List[str] = None
    ) -> Factor:
        """
        Create ratio factor (A / B).
        """
        config = get_template_config(FactorTemplate.RATIO_FEATURE)
        inputs = [numerator["feature_id"], denominator["feature_id"]]
        categories = [numerator.get("category"), denominator.get("category")]
        
        return Factor(
            factor_id=self._generate_id(inputs, "ratio"),
            name=self._generate_name(inputs, FactorTemplate.RATIO_FEATURE),
            family=infer_family_from_categories(categories),
            template=FactorTemplate.RATIO_FEATURE,
            inputs=inputs,
            input_categories=categories,
            transforms=transforms or config.default_transforms,
            expected_direction=infer_direction(inputs, categories),
            complexity=2,
            description=f"Ratio factor: {inputs[0]} / {inputs[1]}",
            tags=self._flatten_tags(numerator, denominator) + ["ratio"],
            created_at=datetime.now(timezone.utc),
            status=FactorStatus.CANDIDATE
        )
    
    def create_difference_factor(
        self,
        feature1: Dict,
        feature2: Dict,
        transforms: List[str] = None
    ) -> Factor:
        """
        Create difference factor (A - B).
        """
        config = get_template_config(FactorTemplate.DIFFERENCE_FEATURE)
        inputs = [feature1["feature_id"], feature2["feature_id"]]
        categories = [feature1.get("category"), feature2.get("category")]
        
        return Factor(
            factor_id=self._generate_id(inputs, "diff"),
            name=self._generate_name(inputs, FactorTemplate.DIFFERENCE_FEATURE),
            family=infer_family_from_categories(categories),
            template=FactorTemplate.DIFFERENCE_FEATURE,
            inputs=inputs,
            input_categories=categories,
            transforms=transforms or config.default_transforms,
            expected_direction=infer_direction(inputs, categories),
            complexity=2,
            description=f"Difference factor: {inputs[0]} - {inputs[1]}",
            tags=self._flatten_tags(feature1, feature2) + ["difference"],
            created_at=datetime.now(timezone.utc),
            status=FactorStatus.CANDIDATE
        )
    
    def create_conditional_factor(
        self,
        signal_feature: Dict,
        condition_feature: Dict,
        transforms: List[str] = None
    ) -> Factor:
        """
        Create conditional factor (A if B).
        """
        config = get_template_config(FactorTemplate.CONDITIONAL_FEATURE)
        inputs = [signal_feature["feature_id"], condition_feature["feature_id"]]
        categories = [signal_feature.get("category"), condition_feature.get("category")]
        
        return Factor(
            factor_id=self._generate_id(inputs, "cond"),
            name=self._generate_name(inputs, FactorTemplate.CONDITIONAL_FEATURE),
            family=infer_family_from_categories(categories),
            template=FactorTemplate.CONDITIONAL_FEATURE,
            inputs=inputs,
            input_categories=categories,
            transforms=transforms or config.default_transforms,
            expected_direction=infer_direction(inputs, categories),
            complexity=2,
            description=f"Conditional factor: {inputs[0]} if {inputs[1]}",
            tags=self._flatten_tags(signal_feature, condition_feature) + ["conditional"],
            created_at=datetime.now(timezone.utc),
            status=FactorStatus.CANDIDATE
        )
    
    def create_regime_factor(
        self,
        feature: Dict,
        regime: str,
        transforms: List[str] = None
    ) -> Factor:
        """
        Create regime-conditioned factor.
        """
        config = get_template_config(FactorTemplate.REGIME_CONDITIONED)
        inputs = [feature["feature_id"]]
        categories = [feature.get("category")]
        
        return Factor(
            factor_id=self._generate_id(inputs + [regime], "regime"),
            name=f"regime_{feature['feature_id'][:8]}_{regime.lower()[:4]}",
            family=FactorFamily.REGIME,
            template=FactorTemplate.REGIME_CONDITIONED,
            inputs=inputs,
            input_categories=categories,
            transforms=transforms or config.default_transforms,
            regime_dependency=[regime],
            expected_direction=infer_direction(inputs, categories),
            complexity=1,
            description=f"Regime factor: {inputs[0]} in {regime}",
            tags=self._flatten_tags(feature) + ["regime", regime.lower()],
            created_at=datetime.now(timezone.utc),
            status=FactorStatus.CANDIDATE
        )
    
    def create_interaction_factor(
        self,
        feature1: Dict,
        feature2: Dict,
        transforms: List[str] = None
    ) -> Factor:
        """
        Create interaction factor (A * B).
        """
        config = get_template_config(FactorTemplate.INTERACTION_FEATURE)
        inputs = [feature1["feature_id"], feature2["feature_id"]]
        categories = [feature1.get("category"), feature2.get("category")]
        
        return Factor(
            factor_id=self._generate_id(inputs, "interact"),
            name=self._generate_name(inputs, FactorTemplate.INTERACTION_FEATURE),
            family=infer_family_from_categories(categories),
            template=FactorTemplate.INTERACTION_FEATURE,
            inputs=inputs,
            input_categories=categories,
            transforms=transforms or config.default_transforms,
            expected_direction=infer_direction(inputs, categories),
            complexity=2,
            description=f"Interaction factor: {inputs[0]} * {inputs[1]}",
            tags=self._flatten_tags(feature1, feature2) + ["interaction"],
            created_at=datetime.now(timezone.utc),
            status=FactorStatus.CANDIDATE
        )
