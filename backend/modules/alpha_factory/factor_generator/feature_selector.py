"""
PHASE 13.3 - Feature Selector
==============================
Selects valid feature combinations for factor generation.

Prevents:
- Redundant combinations (price + price + price)
- Incompatible categories
- Unstable features
- Duplicate factors
"""

from typing import Dict, List, Set, Tuple, Optional
from itertools import combinations, permutations
import random


# Category compatibility matrix
# Each category lists compatible categories for combining
CATEGORY_COMPATIBILITY: Dict[str, List[str]] = {
    "price": ["volatility", "volume", "structure", "microstructure", "correlation"],
    "volatility": ["price", "volume", "liquidity", "structure", "context"],
    "volume": ["price", "volatility", "liquidity", "microstructure"],
    "liquidity": ["volume", "volatility", "microstructure", "structure"],
    "structure": ["price", "volatility", "liquidity", "microstructure"],
    "microstructure": ["volume", "liquidity", "structure", "price"],
    "correlation": ["price", "context", "volatility"],
    "context": ["volatility", "correlation", "liquidity"],
}


# Features that should not be combined (same base indicator)
REDUNDANT_GROUPS = [
    # Price returns at different timeframes
    ["returns_1m", "returns_5m", "returns_15m", "returns_30m", "returns_1h"],
    ["log_returns_1m", "log_returns_5m", "log_returns_15m"],
    # RSI variations
    ["rsi_7", "rsi_14", "rsi_21", "rsi_28"],
    # ATR variations
    ["atr_7", "atr_14", "atr_21", "atr_50"],
    # Volume SMAs
    ["volume_sma_5", "volume_sma_10", "volume_sma_20", "volume_sma_50"],
    # Realized volatility
    ["realized_volatility_5", "realized_volatility_10", "realized_volatility_20"],
]


class FeatureSelector:
    """
    Selects valid feature combinations for factor generation.
    """
    
    def __init__(self):
        # Build redundancy lookup
        self.redundancy_map: Dict[str, Set[str]] = {}
        for group in REDUNDANT_GROUPS:
            for feature in group:
                self.redundancy_map[feature] = set(group) - {feature}
        
        # Track used combinations
        self.used_combinations: Set[str] = set()
    
    def reset(self):
        """Reset used combinations."""
        self.used_combinations = set()
    
    def is_compatible(self, categories: List[str]) -> bool:
        """
        Check if categories are compatible for combination.
        """
        if len(categories) < 2:
            return True
        
        # Check each pair
        for i, cat1 in enumerate(categories):
            for cat2 in categories[i+1:]:
                if cat1 == cat2:
                    continue  # Same category is ok
                
                # Check compatibility
                compat1 = CATEGORY_COMPATIBILITY.get(cat1, [])
                compat2 = CATEGORY_COMPATIBILITY.get(cat2, [])
                
                if cat2 not in compat1 and cat1 not in compat2:
                    return False
        
        return True
    
    def has_redundancy(self, feature_ids: List[str]) -> bool:
        """
        Check if feature combination has redundant features.
        """
        for f1 in feature_ids:
            redundant = self.redundancy_map.get(f1, set())
            for f2 in feature_ids:
                if f1 != f2 and f2 in redundant:
                    return True
        return False
    
    def is_duplicate(self, feature_ids: List[str], template: str) -> bool:
        """
        Check if this combination was already used.
        """
        key = f"{template}:{'_'.join(sorted(feature_ids))}"
        if key in self.used_combinations:
            return True
        return False
    
    def mark_used(self, feature_ids: List[str], template: str):
        """
        Mark combination as used.
        """
        key = f"{template}:{'_'.join(sorted(feature_ids))}"
        self.used_combinations.add(key)
    
    def validate_combination(
        self,
        feature_ids: List[str],
        categories: List[str],
        template: str,
        min_categories: int = 1
    ) -> Tuple[bool, str]:
        """
        Validate a feature combination.
        
        Returns:
            (is_valid, reason)
        """
        # Check category count
        unique_categories = set(categories)
        if len(unique_categories) < min_categories:
            return False, f"Need {min_categories} categories, got {len(unique_categories)}"
        
        # Check compatibility
        if not self.is_compatible(categories):
            return False, "Incompatible categories"
        
        # Check redundancy
        if self.has_redundancy(feature_ids):
            return False, "Redundant features"
        
        # Check duplicate
        if self.is_duplicate(feature_ids, template):
            return False, "Duplicate combination"
        
        return True, "Valid"
    
    def select_pairs(
        self,
        features: List[Dict],
        max_pairs: int = 500,
        min_categories: int = 1
    ) -> List[Tuple[Dict, Dict]]:
        """
        Select valid feature pairs.
        """
        valid_pairs = []
        
        # Group by category
        by_category: Dict[str, List[Dict]] = {}
        for f in features:
            cat = f.get("category", "price")
            if cat not in by_category:
                by_category[cat] = []
            by_category[cat].append(f)
        
        categories = list(by_category.keys())
        
        # Generate cross-category pairs
        for i, cat1 in enumerate(categories):
            for cat2 in categories[i:]:
                # Check compatibility
                if cat1 != cat2 and not self.is_compatible([cat1, cat2]):
                    continue
                
                features1 = by_category[cat1]
                features2 = by_category[cat2] if cat1 != cat2 else features1
                
                # Sample pairs
                for f1 in features1:
                    for f2 in features2:
                        if f1["feature_id"] >= f2["feature_id"]:
                            continue  # Avoid duplicates
                        
                        ids = [f1["feature_id"], f2["feature_id"]]
                        cats = [f1["category"], f2["category"]]
                        
                        if len(set(cats)) < min_categories:
                            continue
                        
                        if self.has_redundancy(ids):
                            continue
                        
                        valid_pairs.append((f1, f2))
                        
                        if len(valid_pairs) >= max_pairs * 3:
                            break
                    if len(valid_pairs) >= max_pairs * 3:
                        break
                if len(valid_pairs) >= max_pairs * 3:
                    break
            if len(valid_pairs) >= max_pairs * 3:
                break
        
        # Shuffle and limit
        random.shuffle(valid_pairs)
        return valid_pairs[:max_pairs]
    
    def select_triples(
        self,
        features: List[Dict],
        max_triples: int = 300,
        min_categories: int = 2
    ) -> List[Tuple[Dict, Dict, Dict]]:
        """
        Select valid feature triples.
        """
        valid_triples = []
        
        # Group by category
        by_category: Dict[str, List[Dict]] = {}
        for f in features:
            cat = f.get("category", "price")
            if cat not in by_category:
                by_category[cat] = []
            by_category[cat].append(f)
        
        categories = list(by_category.keys())
        
        # Generate cross-category triples
        for cat1 in categories:
            for cat2 in categories:
                for cat3 in categories:
                    cats = [cat1, cat2, cat3]
                    if len(set(cats)) < min_categories:
                        continue
                    
                    if not self.is_compatible(cats):
                        continue
                    
                    # Sample limited triples
                    f1_list = random.sample(by_category[cat1], min(5, len(by_category[cat1])))
                    f2_list = random.sample(by_category[cat2], min(5, len(by_category[cat2])))
                    f3_list = random.sample(by_category[cat3], min(5, len(by_category[cat3])))
                    
                    for f1 in f1_list:
                        for f2 in f2_list:
                            for f3 in f3_list:
                                ids = sorted([f1["feature_id"], f2["feature_id"], f3["feature_id"]])
                                if len(set(ids)) < 3:
                                    continue  # Need distinct features
                                
                                if self.has_redundancy(ids):
                                    continue
                                
                                valid_triples.append((f1, f2, f3))
                                
                                if len(valid_triples) >= max_triples * 2:
                                    break
                            if len(valid_triples) >= max_triples * 2:
                                break
                        if len(valid_triples) >= max_triples * 2:
                            break
                    if len(valid_triples) >= max_triples * 2:
                        break
                if len(valid_triples) >= max_triples * 2:
                    break
            if len(valid_triples) >= max_triples * 2:
                break
        
        # Shuffle and limit
        random.shuffle(valid_triples)
        return valid_triples[:max_triples]
