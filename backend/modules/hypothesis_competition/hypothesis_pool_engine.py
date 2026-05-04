"""
Hypothesis Pool Engine

PHASE 30.1 — Hypothesis Pool Engine

Transforms system from single-hypothesis to multi-hypothesis mode.

Architecture rules:
- Does NOT place orders
- Does NOT do sizing
- Does NOT allocate capital (yet)
- ONLY: collects, filters, ranks, forms HypothesisPool
"""

from typing import Optional, List, Dict
from datetime import datetime, timezone

from .hypothesis_pool_types import (
    HypothesisPoolItem,
    HypothesisPool,
    HypothesisPoolSummary,
    CONFIDENCE_THRESHOLD,
    RELIABILITY_THRESHOLD,
    MAX_POOL_SIZE,
    RANKING_WEIGHT_CONFIDENCE,
    RANKING_WEIGHT_RELIABILITY,
    RANKING_WEIGHT_EXECUTION,
    POOL_CONFIDENCE_TOP_N,
)


# ══════════════════════════════════════════════════════════════
# Hypothesis Pool Engine
# ══════════════════════════════════════════════════════════════

class HypothesisPoolEngine:
    """
    Hypothesis Pool Engine — PHASE 30.1
    
    Generates pool of competing hypotheses instead of single best hypothesis.
    
    Flow:
    1. Get all hypothesis candidates from HypothesisEngine
    2. Filter by confidence/reliability thresholds
    3. Exclude UNFAVORABLE execution
    4. Calculate ranking scores
    5. Sort and limit to top 5
    6. Calculate pool metrics
    """
    
    def __init__(self):
        self._pools: Dict[str, List[HypothesisPool]] = {}
        self._current: Dict[str, HypothesisPool] = {}
    
    # ═══════════════════════════════════════════════════════════
    # 1. Ranking Score Calculation
    # ═══════════════════════════════════════════════════════════
    
    def calculate_ranking_score(
        self,
        confidence: float,
        reliability: float,
        execution_score: float,
    ) -> float:
        """
        Calculate ranking score for hypothesis.
        
        Formula:
        ranking_score = 0.50*confidence + 0.30*reliability + 0.20*execution_score
        """
        score = (
            RANKING_WEIGHT_CONFIDENCE * confidence
            + RANKING_WEIGHT_RELIABILITY * reliability
            + RANKING_WEIGHT_EXECUTION * execution_score
        )
        return round(min(max(score, 0.0), 1.0), 4)
    
    # ═══════════════════════════════════════════════════════════
    # 2. Filter Valid Hypotheses
    # ═══════════════════════════════════════════════════════════
    
    def is_valid_for_pool(
        self,
        hypothesis_type: str,
        confidence: float,
        reliability: float,
        execution_state: str,
    ) -> bool:
        """
        Check if hypothesis is valid for pool inclusion.
        
        Rules:
        - confidence > 0.30
        - reliability > 0.25
        - execution_state != UNFAVORABLE
        - NO_EDGE only if no other candidates
        """
        if hypothesis_type == "NO_EDGE":
            return False  # Will be handled as fallback
        
        if execution_state == "UNFAVORABLE":
            return False
        
        if confidence <= CONFIDENCE_THRESHOLD:
            return False
        
        if reliability <= RELIABILITY_THRESHOLD:
            return False
        
        return True
    
    # ═══════════════════════════════════════════════════════════
    # 3. Generate Pool from Hypothesis Engine
    # ═══════════════════════════════════════════════════════════
    
    def generate_pool(
        self,
        symbol: str,
    ) -> HypothesisPool:
        """
        Generate hypothesis pool from HypothesisEngine.
        
        Steps:
        1. Get all hypothesis candidates
        2. Filter valid candidates
        3. Calculate ranking scores
        4. Sort and limit to max 5
        5. Calculate pool metrics
        """
        # Get hypothesis candidates from engine
        candidates = self._get_hypothesis_candidates(symbol)
        
        # Filter and create pool items
        pool_items: List[HypothesisPoolItem] = []
        
        for candidate in candidates:
            if self.is_valid_for_pool(
                hypothesis_type=candidate.get("hypothesis_type", "NO_EDGE"),
                confidence=candidate.get("confidence", 0.0),
                reliability=candidate.get("reliability", 0.0),
                execution_state=candidate.get("execution_state", "UNFAVORABLE"),
            ):
                ranking_score = self.calculate_ranking_score(
                    confidence=candidate.get("confidence", 0.0),
                    reliability=candidate.get("reliability", 0.0),
                    execution_score=candidate.get("execution_score", 0.0),
                )
                
                item = HypothesisPoolItem(
                    hypothesis_type=candidate.get("hypothesis_type"),
                    directional_bias=candidate.get("directional_bias", "NEUTRAL"),
                    confidence=candidate.get("confidence", 0.0),
                    reliability=candidate.get("reliability", 0.0),
                    structural_score=candidate.get("structural_score", 0.0),
                    execution_score=candidate.get("execution_score", 0.0),
                    conflict_score=candidate.get("conflict_score", 0.0),
                    ranking_score=ranking_score,
                    execution_state=candidate.get("execution_state", "CAUTIOUS"),
                    reason=candidate.get("reason", ""),
                )
                pool_items.append(item)
        
        # Sort by ranking score (descending)
        pool_items.sort(key=lambda x: x.ranking_score, reverse=True)
        
        # Limit to max pool size
        pool_items = pool_items[:MAX_POOL_SIZE]
        
        # Handle empty pool case - add NO_EDGE fallback
        if not pool_items:
            no_edge_candidate = self._get_no_edge_fallback(symbol)
            if no_edge_candidate:
                pool_items.append(no_edge_candidate)
        
        # Calculate pool metrics
        pool_confidence = self._calculate_pool_confidence(pool_items)
        pool_reliability = self._calculate_pool_reliability(pool_items)
        
        # Determine top hypothesis
        top_hypothesis = pool_items[0].hypothesis_type if pool_items else "NO_EDGE"
        
        pool = HypothesisPool(
            symbol=symbol,
            hypotheses=pool_items,
            top_hypothesis=top_hypothesis,
            pool_confidence=pool_confidence,
            pool_reliability=pool_reliability,
            pool_size=len(pool_items),
        )
        
        # Store in history
        self._store_pool(symbol, pool)
        
        return pool
    
    # ═══════════════════════════════════════════════════════════
    # 4. Get Hypothesis Candidates
    # ═══════════════════════════════════════════════════════════
    
    def _get_hypothesis_candidates(self, symbol: str) -> List[dict]:
        """
        Get hypothesis candidates from HypothesisEngine.
        
        Returns list of candidate dictionaries.
        """
        candidates = []
        
        try:
            from modules.hypothesis_engine import get_hypothesis_engine
            from modules.hypothesis_engine.hypothesis_types import HypothesisInputLayers
            
            engine = get_hypothesis_engine()
            
            # Get simulated layers for generating candidates
            layers = self._get_input_layers(symbol)
            
            # Generate all candidates
            raw_candidates = engine.generate_candidates(layers)
            
            # Also generate the full hypothesis for main candidate
            main_hypothesis = engine.generate_hypothesis_simulated(symbol)
            
            # Convert to dict format
            for c in raw_candidates:
                # Get scoring from scoring engine
                from modules.hypothesis_engine import get_hypothesis_scoring_engine
                from modules.hypothesis_engine.hypothesis_conflict_resolver import get_hypothesis_conflict_resolver
                
                scoring_engine = get_hypothesis_scoring_engine()
                conflict_resolver = get_hypothesis_conflict_resolver()
                
                scores = scoring_engine.score_hypothesis(
                    candidate=c,
                    layers=layers,
                    execution_confidence_modifier=1.0,
                    transition_state="STABLE",
                )
                
                resolution = conflict_resolver.resolve(
                    conflict_score=scores["conflict_score"],
                    confidence=scores["confidence"],
                    reliability=scores["reliability"],
                    execution_state=scores["execution_state"],
                    alpha_support=c.alpha_support,
                    regime_support=c.regime_support,
                    microstructure_support=c.microstructure_support,
                    hypothesis_type=c.hypothesis_type,
                )
                
                reason = scoring_engine.generate_enhanced_reason(
                    hypothesis_type=c.hypothesis_type,
                    scores=scores,
                    layers=layers,
                )
                
                candidates.append({
                    "hypothesis_type": c.hypothesis_type,
                    "directional_bias": c.directional_bias,
                    "confidence": resolution.adjusted_confidence,
                    "reliability": resolution.adjusted_reliability,
                    "structural_score": scores["structural_score"],
                    "execution_score": scores["execution_score"],
                    "conflict_score": scores["conflict_score"],
                    "execution_state": resolution.adjusted_execution_state,
                    "reason": reason,
                })
            
        except Exception as e:
            # Fallback: return main hypothesis only
            try:
                from modules.hypothesis_engine import get_hypothesis_engine
                engine = get_hypothesis_engine()
                h = engine.generate_hypothesis_simulated(symbol)
                candidates.append({
                    "hypothesis_type": h.hypothesis_type,
                    "directional_bias": h.directional_bias,
                    "confidence": h.confidence,
                    "reliability": h.reliability,
                    "structural_score": h.structural_score,
                    "execution_score": h.execution_score,
                    "conflict_score": h.conflict_score,
                    "execution_state": h.execution_state,
                    "reason": h.reason,
                })
            except Exception:
                pass
        
        return candidates
    
    def _get_input_layers(self, symbol: str):
        """Get input layers for hypothesis generation."""
        from modules.hypothesis_engine.hypothesis_types import HypothesisInputLayers
        
        # Try to get from live engines
        micro_state = "NEUTRAL"
        micro_confidence = 0.5
        regime_type = "TRENDING"
        regime_confidence = 0.6
        regime_in_transition = False
        vacuum_dir = "NONE"
        pressure_dir = "NONE"
        pressure_directional = False
        
        try:
            from modules.microstructure_intelligence_v2 import get_microstructure_context_engine
            ctx_engine = get_microstructure_context_engine()
            ctx = ctx_engine.get_context(symbol)
            if ctx:
                micro_state = ctx.microstructure_state
                micro_confidence = round(
                    min(max((ctx.confidence_modifier - 0.82) / (1.12 - 0.82), 0.0), 1.0), 4
                )
                vacuum_dir = ctx.vacuum_direction
                pressure_directional = ctx.pressure_bias != "BALANCED"
                if ctx.pressure_bias == "BID_DOMINANT":
                    pressure_dir = "UP"
                elif ctx.pressure_bias == "ASK_DOMINANT":
                    pressure_dir = "DOWN"
        except Exception:
            pass
        
        try:
            from modules.regime_intelligence_v2 import get_regime_context_engine
            regime_engine = get_regime_context_engine()
            regime_ctx = regime_engine.get_context(symbol)
            if regime_ctx:
                regime_type = regime_ctx.regime_type
                regime_confidence = regime_ctx.confidence
                regime_in_transition = regime_ctx.in_transition
        except Exception:
            pass
        
        return HypothesisInputLayers(
            alpha_direction="BULLISH",
            alpha_strength=0.65,
            alpha_breakout_strength=0.45,
            alpha_mean_reversion_strength=0.30,
            regime_type=regime_type,
            regime_confidence=regime_confidence,
            regime_in_transition=regime_in_transition,
            microstructure_state=micro_state,
            microstructure_confidence=micro_confidence,
            vacuum_direction=vacuum_dir,
            pressure_directional=pressure_directional,
            pressure_direction=pressure_dir,
            macro_confidence=0.55,
        )
    
    def _get_no_edge_fallback(self, symbol: str) -> Optional[HypothesisPoolItem]:
        """Create NO_EDGE fallback item when pool is empty."""
        return HypothesisPoolItem(
            hypothesis_type="NO_EDGE",
            directional_bias="NEUTRAL",
            confidence=0.0,
            reliability=0.0,
            structural_score=0.0,
            execution_score=0.0,
            conflict_score=0.0,
            ranking_score=0.0,
            execution_state="UNFAVORABLE",
            reason="no valid hypotheses meet pool criteria",
        )
    
    # ═══════════════════════════════════════════════════════════
    # 5. Pool Metrics
    # ═══════════════════════════════════════════════════════════
    
    def _calculate_pool_confidence(
        self,
        items: List[HypothesisPoolItem],
    ) -> float:
        """
        Calculate pool confidence as mean of top 3 hypotheses.
        """
        if not items:
            return 0.0
        
        # Get top N confidences
        confidences = [item.confidence for item in items[:POOL_CONFIDENCE_TOP_N]]
        return round(sum(confidences) / len(confidences), 4)
    
    def _calculate_pool_reliability(
        self,
        items: List[HypothesisPoolItem],
    ) -> float:
        """
        Calculate pool reliability as mean of all hypotheses in pool.
        """
        if not items:
            return 0.0
        
        reliabilities = [item.reliability for item in items]
        return round(sum(reliabilities) / len(reliabilities), 4)
    
    # ═══════════════════════════════════════════════════════════
    # 6. Storage
    # ═══════════════════════════════════════════════════════════
    
    def _store_pool(self, symbol: str, pool: HypothesisPool) -> None:
        """Store pool in history."""
        if symbol not in self._pools:
            self._pools[symbol] = []
        self._pools[symbol].append(pool)
        self._current[symbol] = pool
    
    def get_pool(self, symbol: str) -> Optional[HypothesisPool]:
        """Get current pool for symbol."""
        return self._current.get(symbol)
    
    def get_history(self, symbol: str, limit: int = 100) -> List[HypothesisPool]:
        """Get pool history for symbol."""
        history = self._pools.get(symbol, [])
        return sorted(history, key=lambda p: p.created_at, reverse=True)[:limit]
    
    # ═══════════════════════════════════════════════════════════
    # 7. Summary
    # ═══════════════════════════════════════════════════════════
    
    def get_summary(self, symbol: str) -> HypothesisPoolSummary:
        """Get summary statistics for symbol."""
        history = self.get_history(symbol, limit=500)
        
        if not history:
            return HypothesisPoolSummary(
                symbol=symbol,
                total_pools=0,
            )
        
        # Top hypothesis distribution
        top_counts: Dict[str, int] = {}
        for pool in history:
            t = pool.top_hypothesis
            top_counts[t] = top_counts.get(t, 0) + 1
        
        # Averages
        avg_size = sum(p.pool_size for p in history) / len(history)
        avg_conf = sum(p.pool_confidence for p in history) / len(history)
        avg_rel = sum(p.pool_reliability for p in history) / len(history)
        
        current = history[0] if history else None
        
        return HypothesisPoolSummary(
            symbol=symbol,
            total_pools=len(history),
            top_hypothesis_counts=top_counts,
            avg_pool_size=round(avg_size, 2),
            avg_pool_confidence=round(avg_conf, 4),
            avg_pool_reliability=round(avg_rel, 4),
            current_top_hypothesis=current.top_hypothesis if current else "NO_EDGE",
            current_pool_size=current.pool_size if current else 0,
        )


# ══════════════════════════════════════════════════════════════
# Singleton
# ══════════════════════════════════════════════════════════════

_pool_engine: Optional[HypothesisPoolEngine] = None


def get_hypothesis_pool_engine() -> HypothesisPoolEngine:
    """Get singleton instance of HypothesisPoolEngine."""
    global _pool_engine
    if _pool_engine is None:
        _pool_engine = HypothesisPoolEngine()
    return _pool_engine
