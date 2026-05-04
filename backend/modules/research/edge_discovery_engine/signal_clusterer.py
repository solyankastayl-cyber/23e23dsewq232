"""
PHASE 6.4 - Signal Clusterer
=============================
Clusters similar patterns using machine learning techniques.
"""

import random
import math
from typing import Dict, List, Optional, Tuple
from collections import defaultdict

from .edge_types import PatternMatch, MarketFeatures


class SignalClusterer:
    """
    Clusters similar market patterns.
    Uses simplified K-Means and density-based clustering.
    """
    
    def __init__(self, n_clusters: int = 5):
        self.n_clusters = n_clusters
        self.features_to_use = [
            'trend_strength', 'volatility_percentile', 'price_momentum',
            'volume_spike', 'volume_trend', 'liquidity_score',
            'funding_rate_zscore', 'orderbook_imbalance'
        ]
    
    def cluster_patterns(
        self,
        patterns: List[PatternMatch],
        method: str = "kmeans"
    ) -> Dict[int, List[PatternMatch]]:
        """
        Cluster patterns into groups.
        
        Args:
            patterns: List of pattern matches
            method: 'kmeans' or 'density'
        
        Returns:
            Dict mapping cluster_id to list of patterns
        """
        if len(patterns) < self.n_clusters:
            return {0: patterns}
        
        # Extract feature vectors
        vectors = [self._pattern_to_vector(p) for p in patterns]
        
        if method == "kmeans":
            labels = self._kmeans(vectors, self.n_clusters)
        else:
            labels = self._density_cluster(vectors)
        
        # Group patterns by cluster
        clusters = defaultdict(list)
        for pattern, label in zip(patterns, labels):
            clusters[label].append(pattern)
        
        return dict(clusters)
    
    def _pattern_to_vector(self, pattern: PatternMatch) -> List[float]:
        """Convert pattern features to numeric vector"""
        features = pattern.features
        vector = []
        
        for fname in self.features_to_use:
            value = getattr(features, fname, 0)
            if isinstance(value, bool):
                value = 1.0 if value else 0.0
            elif isinstance(value, str):
                value = hash(value) % 100 / 100  # Simple hash encoding
            vector.append(float(value))
        
        return vector
    
    def _kmeans(
        self,
        vectors: List[List[float]],
        k: int,
        max_iters: int = 50
    ) -> List[int]:
        """Simple K-Means clustering"""
        if not vectors:
            return []
        
        n = len(vectors)
        dim = len(vectors[0])
        
        # Initialize centroids randomly
        random.seed(42)
        centroid_indices = random.sample(range(n), min(k, n))
        centroids = [vectors[i].copy() for i in centroid_indices]
        
        labels = [0] * n
        
        for _ in range(max_iters):
            # Assign labels
            new_labels = []
            for vec in vectors:
                distances = [self._euclidean_distance(vec, c) for c in centroids]
                new_labels.append(distances.index(min(distances)))
            
            # Check convergence
            if new_labels == labels:
                break
            
            labels = new_labels
            
            # Update centroids
            for j in range(k):
                cluster_vecs = [vectors[i] for i in range(n) if labels[i] == j]
                if cluster_vecs:
                    centroids[j] = self._mean_vector(cluster_vecs)
        
        return labels
    
    def _density_cluster(
        self,
        vectors: List[List[float]],
        eps: float = 0.5,
        min_samples: int = 3
    ) -> List[int]:
        """Simplified density-based clustering (DBSCAN-like)"""
        n = len(vectors)
        labels = [-1] * n  # -1 = noise
        cluster_id = 0
        
        visited = set()
        
        for i in range(n):
            if i in visited:
                continue
            
            visited.add(i)
            
            # Find neighbors
            neighbors = self._get_neighbors(vectors, i, eps)
            
            if len(neighbors) < min_samples:
                continue  # Noise point
            
            # Start new cluster
            labels[i] = cluster_id
            
            # Expand cluster
            seed_set = list(neighbors)
            j = 0
            while j < len(seed_set):
                q = seed_set[j]
                
                if q not in visited:
                    visited.add(q)
                    q_neighbors = self._get_neighbors(vectors, q, eps)
                    
                    if len(q_neighbors) >= min_samples:
                        seed_set.extend([n for n in q_neighbors if n not in seed_set])
                
                if labels[q] == -1:
                    labels[q] = cluster_id
                
                j += 1
            
            cluster_id += 1
        
        return labels
    
    def _get_neighbors(
        self,
        vectors: List[List[float]],
        idx: int,
        eps: float
    ) -> List[int]:
        """Get all points within eps distance"""
        neighbors = []
        for i, vec in enumerate(vectors):
            if self._euclidean_distance(vectors[idx], vec) <= eps:
                neighbors.append(i)
        return neighbors
    
    def _euclidean_distance(self, v1: List[float], v2: List[float]) -> float:
        """Calculate Euclidean distance"""
        return math.sqrt(sum((a - b) ** 2 for a, b in zip(v1, v2)))
    
    def _mean_vector(self, vectors: List[List[float]]) -> List[float]:
        """Calculate mean of vectors"""
        if not vectors:
            return []
        
        n = len(vectors)
        dim = len(vectors[0])
        
        return [sum(v[i] for v in vectors) / n for i in range(dim)]
    
    def analyze_clusters(
        self,
        clusters: Dict[int, List[PatternMatch]]
    ) -> Dict:
        """Analyze cluster characteristics"""
        analysis = {}
        
        for cluster_id, patterns in clusters.items():
            if not patterns:
                continue
            
            # Calculate cluster statistics
            returns = [p.outcome_return for p in patterns if p.outcome_return is not None]
            
            win_count = sum(1 for r in returns if r > 0)
            total = len(returns)
            
            analysis[cluster_id] = {
                "size": len(patterns),
                "win_rate": win_count / total if total > 0 else 0,
                "avg_return": sum(returns) / len(returns) if returns else 0,
                "avg_confidence": sum(p.confidence for p in patterns) / len(patterns),
                "pattern_types": list(set(
                    p.pattern_type.value if hasattr(p.pattern_type, 'value') else str(p.pattern_type)
                    for p in patterns
                ))
            }
        
        return analysis
    
    def find_best_cluster(
        self,
        clusters: Dict[int, List[PatternMatch]]
    ) -> Tuple[int, Dict]:
        """Find the cluster with best trading performance"""
        analysis = self.analyze_clusters(clusters)
        
        if not analysis:
            return -1, {}
        
        # Score clusters
        best_id = -1
        best_score = -float('inf')
        
        for cluster_id, stats in analysis.items():
            # Score = win_rate * log(sample_size) * avg_confidence
            score = (
                stats["win_rate"] *
                math.log(stats["size"] + 1) *
                stats["avg_confidence"]
            )
            
            if score > best_score:
                best_score = score
                best_id = cluster_id
        
        return best_id, analysis.get(best_id, {})
