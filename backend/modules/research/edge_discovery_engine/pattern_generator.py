"""
PHASE 6.4 - Pattern Generator
==============================
Generates candidate edge hypotheses from patterns.
"""

import random
import uuid
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timezone
from itertools import combinations

from .edge_types import (
    PatternType, PatternMatch, EdgeCandidate, EdgeCategory,
    EdgeStatus, MarketFeatures
)


class PatternGenerator:
    """
    Generates candidate trading edges from detected patterns.
    """
    
    def __init__(self):
        self.min_sample_size = 20
        self.min_win_rate = 0.5
    
    def generate_candidates(
        self,
        pattern_matches: List[PatternMatch],
        max_candidates: int = 20
    ) -> List[EdgeCandidate]:
        """
        Generate edge candidates from pattern matches.
        
        Approaches:
        1. Single pattern edges
        2. Pattern combinations
        3. Feature-based edges
        """
        candidates = []
        
        # Group patterns by type
        patterns_by_type = self._group_by_type(pattern_matches)
        
        # Generate single pattern edges
        single_edges = self._generate_single_pattern_edges(patterns_by_type)
        candidates.extend(single_edges)
        
        # Generate combination edges
        combo_edges = self._generate_combination_edges(patterns_by_type)
        candidates.extend(combo_edges)
        
        # Generate feature-based edges
        feature_edges = self._generate_feature_edges(pattern_matches)
        candidates.extend(feature_edges)
        
        # Filter and sort
        valid_candidates = [
            c for c in candidates
            if c.sample_size >= self.min_sample_size
            and c.win_rate_estimate >= self.min_win_rate
        ]
        
        # Sort by estimated win rate
        valid_candidates.sort(key=lambda x: x.win_rate_estimate, reverse=True)
        
        return valid_candidates[:max_candidates]
    
    def _group_by_type(
        self,
        matches: List[PatternMatch]
    ) -> Dict[PatternType, List[PatternMatch]]:
        """Group pattern matches by type"""
        grouped = {}
        for match in matches:
            ptype = match.pattern_type
            if ptype not in grouped:
                grouped[ptype] = []
            grouped[ptype].append(match)
        return grouped
    
    def _generate_single_pattern_edges(
        self,
        patterns_by_type: Dict[PatternType, List[PatternMatch]]
    ) -> List[EdgeCandidate]:
        """Generate edges from single pattern types"""
        edges = []
        
        for pattern_type, matches in patterns_by_type.items():
            if len(matches) < self.min_sample_size:
                continue
            
            # Calculate win rate for LONG and SHORT
            long_wins = sum(1 for m in matches if m.outcome_return and m.outcome_return > 0)
            short_wins = sum(1 for m in matches if m.outcome_return and m.outcome_return < 0)
            total_with_outcome = sum(1 for m in matches if m.outcome_return is not None)
            
            if total_with_outcome < self.min_sample_size:
                continue
            
            long_wr = long_wins / total_with_outcome
            short_wr = short_wins / total_with_outcome
            
            # Pick better direction
            if long_wr > short_wr and long_wr >= self.min_win_rate:
                direction = "LONG"
                win_rate = long_wr
            elif short_wr >= self.min_win_rate:
                direction = "SHORT"
                win_rate = short_wr
            else:
                continue
            
            # Calculate average return
            returns = [m.outcome_return for m in matches if m.outcome_return is not None]
            avg_return = sum(returns) / len(returns) if returns else 0
            
            # Create candidate
            category = self._pattern_to_category(pattern_type)
            
            edge = EdgeCandidate(
                edge_id=f"edge_{uuid.uuid4().hex[:8]}",
                name=f"{pattern_type.value} Edge",
                description=f"Trade {direction} on {pattern_type.value} pattern",
                category=category,
                pattern_types=[pattern_type],
                feature_conditions=self._get_default_conditions(pattern_type),
                expected_direction=direction,
                sample_matches=matches[:10],  # Keep sample
                sample_size=total_with_outcome,
                win_rate_estimate=win_rate,
                avg_return_estimate=abs(avg_return) if direction == "LONG" else -avg_return,
                status=EdgeStatus.CANDIDATE,
                discovered_at=datetime.now(timezone.utc)
            )
            edges.append(edge)
        
        return edges
    
    def _generate_combination_edges(
        self,
        patterns_by_type: Dict[PatternType, List[PatternMatch]]
    ) -> List[EdgeCandidate]:
        """Generate edges from pattern combinations"""
        edges = []
        
        # Get pattern types with enough samples
        valid_types = [
            pt for pt, matches in patterns_by_type.items()
            if len(matches) >= 10
        ]
        
        if len(valid_types) < 2:
            return edges
        
        # Generate pairs
        for pt1, pt2 in combinations(valid_types, 2):
            matches1 = patterns_by_type[pt1]
            matches2 = patterns_by_type[pt2]
            
            # Find overlapping timestamps (within window)
            combined_matches = self._find_overlapping_patterns(matches1, matches2)
            
            if len(combined_matches) < self.min_sample_size:
                continue
            
            # Calculate metrics
            wins = sum(1 for m in combined_matches if m.outcome_return and m.outcome_return > 0)
            total = len([m for m in combined_matches if m.outcome_return is not None])
            
            if total < self.min_sample_size:
                continue
            
            win_rate = wins / total
            
            if win_rate < self.min_win_rate:
                continue
            
            returns = [m.outcome_return for m in combined_matches if m.outcome_return is not None]
            avg_return = sum(returns) / len(returns) if returns else 0
            
            direction = "LONG" if avg_return > 0 else "SHORT"
            
            edge = EdgeCandidate(
                edge_id=f"edge_{uuid.uuid4().hex[:8]}",
                name=f"{pt1.value} + {pt2.value} Combo",
                description=f"Combined {pt1.value} and {pt2.value} patterns",
                category=EdgeCategory.STRUCTURE,
                pattern_types=[pt1, pt2],
                feature_conditions={
                    pt1.value: self._get_default_conditions(pt1),
                    pt2.value: self._get_default_conditions(pt2)
                },
                expected_direction=direction,
                sample_matches=combined_matches[:10],
                sample_size=total,
                win_rate_estimate=win_rate,
                avg_return_estimate=abs(avg_return),
                status=EdgeStatus.CANDIDATE,
                discovered_at=datetime.now(timezone.utc)
            )
            edges.append(edge)
        
        return edges
    
    def _find_overlapping_patterns(
        self,
        matches1: List[PatternMatch],
        matches2: List[PatternMatch],
        window: int = 3600000  # 1 hour in ms
    ) -> List[PatternMatch]:
        """Find patterns that occur close together"""
        overlapping = []
        
        ts2_set = {m.timestamp for m in matches2}
        
        for m1 in matches1:
            # Check if any match2 is within window
            for ts2 in ts2_set:
                if abs(m1.timestamp - ts2) <= window:
                    overlapping.append(m1)
                    break
        
        return overlapping
    
    def _generate_feature_edges(
        self,
        matches: List[PatternMatch]
    ) -> List[EdgeCandidate]:
        """Generate edges based on feature combinations"""
        edges = []
        
        if len(matches) < self.min_sample_size:
            return edges
        
        # Group by feature thresholds
        feature_groups = [
            ("high_volatility_compression", lambda f: f.volatility_percentile < 0.2),
            ("high_volume_spike", lambda f: f.volume_spike > 2.0),
            ("strong_trend", lambda f: f.trend_strength > 0.6),
            ("near_support", lambda f: f.near_support),
            ("near_resistance", lambda f: f.near_resistance),
            ("extreme_funding", lambda f: abs(f.funding_rate_zscore) > 1.5),
        ]
        
        for group_name, condition in feature_groups:
            filtered = [m for m in matches if condition(m.features)]
            
            if len(filtered) < self.min_sample_size:
                continue
            
            wins = sum(1 for m in filtered if m.outcome_return and m.outcome_return > 0)
            total = len([m for m in filtered if m.outcome_return is not None])
            
            if total < self.min_sample_size:
                continue
            
            win_rate = wins / total
            
            if win_rate < self.min_win_rate:
                continue
            
            returns = [m.outcome_return for m in filtered if m.outcome_return is not None]
            avg_return = sum(returns) / len(returns) if returns else 0
            
            direction = "LONG" if avg_return > 0 else "SHORT"
            
            edge = EdgeCandidate(
                edge_id=f"edge_{uuid.uuid4().hex[:8]}",
                name=f"{group_name.replace('_', ' ').title()} Edge",
                description=f"Feature-based edge: {group_name}",
                category=EdgeCategory.STRUCTURE,
                pattern_types=[],
                feature_conditions={group_name: True},
                expected_direction=direction,
                sample_matches=filtered[:10],
                sample_size=total,
                win_rate_estimate=win_rate,
                avg_return_estimate=abs(avg_return),
                status=EdgeStatus.CANDIDATE,
                discovered_at=datetime.now(timezone.utc)
            )
            edges.append(edge)
        
        return edges
    
    def _pattern_to_category(self, pattern_type: PatternType) -> EdgeCategory:
        """Map pattern type to edge category"""
        mapping = {
            PatternType.VOLATILITY_COMPRESSION: EdgeCategory.VOLATILITY,
            PatternType.VOLUME_ANOMALY: EdgeCategory.VOLUME,
            PatternType.LIQUIDITY_EVENT: EdgeCategory.LIQUIDITY,
            PatternType.STRUCTURE_SHIFT: EdgeCategory.STRUCTURE,
            PatternType.FUNDING_EXTREME: EdgeCategory.FUNDING,
            PatternType.ORDERBOOK_IMBALANCE: EdgeCategory.MICROSTRUCTURE,
            PatternType.PRICE_PATTERN: EdgeCategory.MOMENTUM,
        }
        return mapping.get(pattern_type, EdgeCategory.STRUCTURE)
    
    def _get_default_conditions(self, pattern_type: PatternType) -> Dict:
        """Get default feature conditions for pattern"""
        conditions = {
            PatternType.VOLATILITY_COMPRESSION: {"volatility_percentile": {"lt": 0.2}},
            PatternType.VOLUME_ANOMALY: {"volume_spike": {"gt": 2.0}},
            PatternType.LIQUIDITY_EVENT: {"liquidity_score": {"lt": 0.3}},
            PatternType.STRUCTURE_SHIFT: {"structure_type": "CHANGED"},
            PatternType.FUNDING_EXTREME: {"funding_rate_zscore": {"abs_gt": 1.5}},
            PatternType.ORDERBOOK_IMBALANCE: {"orderbook_imbalance": {"abs_gt": 0.3}},
            PatternType.PRICE_PATTERN: {"price_momentum": {"abs_gt": 0.03}},
        }
        return conditions.get(pattern_type, {})
