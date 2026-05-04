"""
PHASE 6.4 - Edge Ranker
========================
Ranks discovered edges by composite score.
"""

from typing import Dict, List, Optional
from dataclasses import dataclass
import math

from .edge_types import DiscoveredEdge, EdgeStatus


@dataclass
class RankingWeights:
    """Weights for ranking score calculation"""
    profit_factor: float = 0.25
    win_rate: float = 0.20
    sharpe_ratio: float = 0.15
    confidence: float = 0.15
    sample_size: float = 0.10
    risk_score: float = 0.10
    expectancy: float = 0.05


class EdgeRanker:
    """
    Ranks discovered edges by composite score.
    """
    
    def __init__(self, weights: RankingWeights = None):
        self.weights = weights or RankingWeights()
    
    def rank_edges(
        self,
        edges: List[DiscoveredEdge]
    ) -> List[DiscoveredEdge]:
        """
        Rank edges by composite score.
        """
        if not edges:
            return []
        
        # Calculate composite score for each edge
        for edge in edges:
            edge.composite_score = self._calculate_composite_score(edge)
        
        # Sort by composite score (descending)
        sorted_edges = sorted(edges, key=lambda x: x.composite_score, reverse=True)
        
        # Assign ranks
        for i, edge in enumerate(sorted_edges):
            edge.rank = i + 1
        
        return sorted_edges
    
    def _calculate_composite_score(self, edge: DiscoveredEdge) -> float:
        """
        Calculate composite ranking score.
        """
        w = self.weights
        
        # Normalize metrics to 0-1 scale
        
        # Profit factor: 1.0 = 0, 2.0 = 0.5, 3.0+ = 1.0
        pf_score = min(1.0, max(0, (edge.profit_factor - 1) / 2))
        
        # Win rate: 0.5 = 0, 0.7 = 1.0
        wr_score = min(1.0, max(0, (edge.win_rate - 0.5) / 0.2))
        
        # Sharpe ratio: 0 = 0, 2.0 = 1.0
        sharpe_score = min(1.0, max(0, edge.sharpe_ratio / 2))
        
        # Confidence: already 0-1
        conf_score = edge.confidence_score
        
        # Sample size: log scale, 50 = 0.5, 200 = 1.0
        sample_score = min(1.0, math.log(edge.sample_size + 1) / math.log(200))
        
        # Risk score: inverted, 0.5 = 0.5, 0.2 = 1.0
        risk_inv_score = max(0, 1 - edge.risk_score)
        
        # Expectancy: 0 = 0.5, 0.02 = 1.0
        exp_score = min(1.0, max(0, edge.expectancy / 0.02 + 0.5))
        
        # Calculate weighted sum
        composite = (
            w.profit_factor * pf_score +
            w.win_rate * wr_score +
            w.sharpe_ratio * sharpe_score +
            w.confidence * conf_score +
            w.sample_size * sample_score +
            w.risk_score * risk_inv_score +
            w.expectancy * exp_score
        )
        
        return composite
    
    def get_top_edges(
        self,
        edges: List[DiscoveredEdge],
        n: int = 10
    ) -> List[DiscoveredEdge]:
        """Get top N edges by rank"""
        ranked = self.rank_edges(edges)
        return ranked[:n]
    
    def filter_by_category(
        self,
        edges: List[DiscoveredEdge],
        category: str
    ) -> List[DiscoveredEdge]:
        """Filter edges by category"""
        filtered = [
            e for e in edges
            if (e.category.value if hasattr(e.category, 'value') else e.category) == category
        ]
        return self.rank_edges(filtered)
    
    def get_production_ready(
        self,
        edges: List[DiscoveredEdge],
        min_score: float = 0.6,
        min_confidence: float = 0.7
    ) -> List[DiscoveredEdge]:
        """Get edges ready for production"""
        ranked = self.rank_edges(edges)
        
        ready = [
            e for e in ranked
            if e.composite_score >= min_score
            and e.confidence_score >= min_confidence
            and e.status in [EdgeStatus.VALIDATED, EdgeStatus.PRODUCTION]
        ]
        
        return ready
    
    def get_ranking_summary(
        self,
        edges: List[DiscoveredEdge]
    ) -> Dict:
        """Get summary of rankings"""
        if not edges:
            return {"total": 0}
        
        ranked = self.rank_edges(edges)
        
        # Categories breakdown
        by_category = {}
        for edge in ranked:
            cat = edge.category.value if hasattr(edge.category, 'value') else str(edge.category)
            if cat not in by_category:
                by_category[cat] = 0
            by_category[cat] += 1
        
        # Score distribution
        scores = [e.composite_score for e in ranked]
        
        return {
            "total": len(ranked),
            "avg_score": sum(scores) / len(scores),
            "max_score": max(scores),
            "min_score": min(scores),
            "by_category": by_category,
            "production_ready": len([e for e in ranked if e.composite_score >= 0.6]),
            "top_edge": {
                "edge_id": ranked[0].edge_id,
                "name": ranked[0].name,
                "score": ranked[0].composite_score
            } if ranked else None
        }
