"""
Regime Memory Engine

PHASE 34 — Market Regime Memory Layer

Core engine for finding similar historical market states using cosine similarity.

Key formulas:
- cosine_similarity(query_vector, memory_vector)
- Filter: similarity >= 0.75
- memory_score = 0.50 * similarity + 0.30 * success_rate + 0.20 * recency_weight
- recency_weight = 1 / log(days_since_event + 2)
"""

import math
import hashlib
from typing import Optional, List, Dict, Tuple
from datetime import datetime, timezone, timedelta
from collections import Counter

from .memory_types import (
    StructureVector,
    RegimeMemoryRecord,
    MemoryMatch,
    MemoryQuery,
    MemoryResponse,
    MemoryPattern,
    MemorySummary,
    MemoryModifier,
    PendingOutcomeRecord,
    VECTOR_SIZE,
    SIMILARITY_THRESHOLD,
    WEIGHT_SIMILARITY,
    WEIGHT_SUCCESS_RATE,
    WEIGHT_RECENCY,
    REGIME_MEMORY_WEIGHT,
)


# ══════════════════════════════════════════════════════════════
# Regime Memory Engine
# ══════════════════════════════════════════════════════════════

class RegimeMemoryEngine:
    """
    Regime Memory Engine — PHASE 34
    
    Compares current market structure against historical snapshots
    to find similar situations and their outcomes.
    
    Pipeline:
    1. Build current structure vector from intelligence layers
    2. Query historical memory records
    3. Calculate cosine similarity for each record
    4. Filter by threshold (>= 0.75)
    5. Calculate memory_score with recency weighting
    6. Aggregate expected direction and success rate
    """
    
    def __init__(self):
        # In-memory cache
        self._responses: Dict[str, List[MemoryResponse]] = {}
        self._current: Dict[str, MemoryResponse] = {}
        self._pending: Dict[str, List[PendingOutcomeRecord]] = {}
    
    # ═══════════════════════════════════════════════════════════
    # 1. Structure Vector Building
    # ═══════════════════════════════════════════════════════════
    
    def build_structure_vector(self, symbol: str) -> StructureVector:
        """
        Build current market structure vector from intelligence layers.
        
        Vector components:
        1. trend_slope — from Regime Intelligence
        2. volatility — from market data
        3. volume_delta — from market data
        4. microstructure_bias — from Microstructure Intelligence
        5. liquidity_state — from Microstructure Intelligence
        6. regime_numeric — encoded regime type
        7. fractal_alignment — from Fractal Intelligence
        """
        symbol = symbol.upper()
        
        trend_slope = self._get_trend_slope(symbol)
        volatility = self._get_volatility(symbol)
        volume_delta = self._get_volume_delta(symbol)
        microstructure_bias = self._get_microstructure_bias(symbol)
        liquidity_state = self._get_liquidity_state(symbol)
        regime_numeric = self._get_regime_numeric(symbol)
        fractal_alignment = self._get_fractal_alignment(symbol)
        
        return StructureVector(
            trend_slope=trend_slope,
            volatility=volatility,
            volume_delta=volume_delta,
            microstructure_bias=microstructure_bias,
            liquidity_state=liquidity_state,
            regime_numeric=regime_numeric,
            fractal_alignment=fractal_alignment,
        )
    
    def _get_trend_slope(self, symbol: str) -> float:
        """Get trend slope from Regime Intelligence."""
        try:
            from modules.regime_intelligence_v2 import get_regime_engine
            engine = get_regime_engine()
            regime = engine.get_current_regime(symbol)
            if regime:
                if regime.regime_type == "TREND_UP":
                    return min(0.5 + regime.confidence * 0.5, 1.0)
                elif regime.regime_type == "TREND_DOWN":
                    return max(-0.5 - regime.confidence * 0.5, -1.0)
                elif regime.regime_type == "TRENDING":
                    return regime.confidence * 0.6
                return 0.0
        except Exception:
            pass
        
        # Deterministic fallback
        seed = int(hashlib.md5(f"{symbol}_trend_{datetime.now(timezone.utc).hour}".encode()).hexdigest()[:6], 16)
        return round(((seed % 200) - 100) / 100, 4)
    
    def _get_volatility(self, symbol: str) -> float:
        """Get volatility measure."""
        try:
            from core.database import get_database
            db = get_database()
            if db:
                candles = list(db.candles.find(
                    {"symbol": symbol},
                    {"_id": 0, "high": 1, "low": 1, "close": 1}
                ).sort("timestamp", -1).limit(20))
                
                if candles:
                    ranges = [(c["high"] - c["low"]) / max(c["close"], 1) for c in candles]
                    avg_range = sum(ranges) / len(ranges)
                    return round(min(avg_range * 10, 1.0), 4)
        except Exception:
            pass
        
        # Deterministic fallback based on asset
        vol_map = {"BTC": 0.45, "ETH": 0.55, "SOL": 0.65}
        base = vol_map.get(symbol, 0.50)
        seed = int(hashlib.md5(f"{symbol}_vol".encode()).hexdigest()[:4], 16)
        return round(min(max(base + (seed % 20 - 10) / 100, 0.0), 1.0), 4)
    
    def _get_volume_delta(self, symbol: str) -> float:
        """Get volume delta (change ratio)."""
        try:
            from core.database import get_database
            db = get_database()
            if db:
                candles = list(db.candles.find(
                    {"symbol": symbol},
                    {"_id": 0, "volume": 1}
                ).sort("timestamp", -1).limit(20))
                
                if len(candles) >= 10:
                    recent_vol = sum(c.get("volume", 0) for c in candles[:5])
                    older_vol = sum(c.get("volume", 0) for c in candles[5:10])
                    if older_vol > 0:
                        delta = (recent_vol - older_vol) / older_vol
                        return round(min(max(delta, -1.0), 1.0), 4)
        except Exception:
            pass
        
        seed = int(hashlib.md5(f"{symbol}_voldelta".encode()).hexdigest()[:6], 16)
        return round(((seed % 160) - 80) / 100, 4)
    
    def _get_microstructure_bias(self, symbol: str) -> float:
        """Get microstructure directional bias."""
        try:
            from modules.microstructure_intelligence_v2 import get_microstructure_context_engine
            engine = get_microstructure_context_engine()
            ctx = engine.get_context(symbol)
            if ctx:
                bias_map = {
                    "BID_DOMINANT": 0.5,
                    "ASK_DOMINANT": -0.5,
                    "BALANCED": 0.0,
                }
                base_bias = bias_map.get(ctx.pressure_bias, 0.0)
                vacuum_adj = 0.2 if ctx.vacuum_direction == "UP" else (-0.2 if ctx.vacuum_direction == "DOWN" else 0.0)
                return round(min(max(base_bias + vacuum_adj, -1.0), 1.0), 4)
        except Exception:
            pass
        
        seed = int(hashlib.md5(f"{symbol}_bias".encode()).hexdigest()[:6], 16)
        return round(((seed % 140) - 70) / 100, 4)
    
    def _get_liquidity_state(self, symbol: str) -> float:
        """Get liquidity state from Microstructure Intelligence."""
        try:
            from modules.microstructure_intelligence_v2 import get_microstructure_context_engine
            engine = get_microstructure_context_engine()
            ctx = engine.get_context(symbol)
            if ctx:
                state_map = {
                    "SUPPORTIVE": 0.85,
                    "NEUTRAL": 0.55,
                    "FRAGILE": 0.35,
                    "STRESSED": 0.15,
                }
                return state_map.get(ctx.microstructure_state, 0.50)
        except Exception:
            pass
        
        seed = int(hashlib.md5(f"{symbol}_liq".encode()).hexdigest()[:6], 16)
        return round((seed % 70 + 30) / 100, 4)
    
    def _get_regime_numeric(self, symbol: str) -> float:
        """
        Encode regime type as numeric value.
        
        TRENDING = 1.0
        RANGING = 0.66
        VOLATILE = 0.33
        UNCERTAIN = 0.0
        """
        try:
            from modules.regime_intelligence_v2 import get_regime_context_engine
            engine = get_regime_context_engine()
            ctx = engine.get_context(symbol)
            if ctx:
                regime_map = {
                    "TRENDING": 1.0,
                    "TREND_UP": 1.0,
                    "TREND_DOWN": 1.0,
                    "RANGING": 0.66,
                    "VOLATILE": 0.33,
                    "UNCERTAIN": 0.0,
                }
                return regime_map.get(ctx.regime_type, 0.5)
        except Exception:
            pass
        
        # Fallback
        return 0.5
    
    def _get_fractal_alignment(self, symbol: str) -> float:
        """Get multi-timeframe fractal alignment."""
        try:
            from modules.fractal_market_intelligence import get_fractal_engine
            engine = get_fractal_engine()
            analysis = engine.get_current_analysis(symbol)
            if analysis:
                if analysis.fractal_alignment == "ALIGNED":
                    return 0.8 if analysis.dominant_direction == "LONG" else -0.8
                elif analysis.fractal_alignment == "DIVERGENT":
                    return 0.0
                return analysis.alignment_strength * (1 if analysis.dominant_direction == "LONG" else -1)
        except Exception:
            pass
        
        seed = int(hashlib.md5(f"{symbol}_fractal".encode()).hexdigest()[:6], 16)
        return round(((seed % 160) - 80) / 100, 4)
    
    # ═══════════════════════════════════════════════════════════
    # 2. Cosine Similarity Calculation
    # ═══════════════════════════════════════════════════════════
    
    def calculate_cosine_similarity(
        self,
        vector_a: List[float],
        vector_b: List[float],
    ) -> float:
        """
        Calculate cosine similarity between two vectors.
        
        cosine_similarity = (A · B) / (||A|| × ||B||)
        
        Returns value in [0, 1] range (normalized from [-1, 1]).
        """
        if len(vector_a) != len(vector_b):
            return 0.0
        
        if len(vector_a) != VECTOR_SIZE:
            return 0.0
        
        # Dot product
        dot_product = sum(a * b for a, b in zip(vector_a, vector_b))
        
        # Magnitudes
        magnitude_a = math.sqrt(sum(a * a for a in vector_a))
        magnitude_b = math.sqrt(sum(b * b for b in vector_b))
        
        if magnitude_a == 0 or magnitude_b == 0:
            return 0.0
        
        # Raw similarity [-1, 1]
        raw_similarity = dot_product / (magnitude_a * magnitude_b)
        
        # Normalize to [0, 1]
        normalized = (raw_similarity + 1) / 2
        
        return round(normalized, 4)
    
    # ═══════════════════════════════════════════════════════════
    # 3. Recency Weight Calculation
    # ═══════════════════════════════════════════════════════════
    
    def calculate_recency_weight(self, timestamp: datetime) -> float:
        """
        Calculate recency weight for a memory record.
        
        Formula: recency_weight = 1 / log(days_since_event + 2)
        
        Recent events have higher weight.
        """
        now = datetime.now(timezone.utc)
        
        # Ensure timestamp is timezone-aware
        if timestamp.tzinfo is None:
            timestamp = timestamp.replace(tzinfo=timezone.utc)
        
        days_since = (now - timestamp).total_seconds() / 86400
        days_since = max(days_since, 0)
        
        # recency = 1 / log(days + 2)
        recency = 1.0 / math.log(days_since + 2)
        
        # Normalize to [0, 1] approximately
        # log(2) ≈ 0.693, so max recency ≈ 1.44
        # log(32) ≈ 3.47, so 30-day recency ≈ 0.29
        normalized = min(recency / 1.44, 1.0)
        
        return round(normalized, 4)
    
    # ═══════════════════════════════════════════════════════════
    # 4. Memory Score Calculation
    # ═══════════════════════════════════════════════════════════
    
    def calculate_memory_score(
        self,
        similarity: float,
        success_rate: float,
        recency_weight: float,
    ) -> float:
        """
        Calculate memory score for hypothesis engine.
        
        Formula:
        memory_score = 0.50 * similarity
                     + 0.30 * success_rate
                     + 0.20 * recency_weight
        """
        score = (
            WEIGHT_SIMILARITY * similarity
            + WEIGHT_SUCCESS_RATE * success_rate
            + WEIGHT_RECENCY * recency_weight
        )
        
        return round(min(max(score, 0.0), 1.0), 4)
    
    # ═══════════════════════════════════════════════════════════
    # 5. Find Similar Memories
    # ═══════════════════════════════════════════════════════════
    
    def find_similar_memories(
        self,
        query_vector: List[float],
        records: List[RegimeMemoryRecord],
        threshold: float = SIMILARITY_THRESHOLD,
    ) -> List[MemoryMatch]:
        """
        Find historical memory records similar to query vector.
        
        Steps:
        1. Calculate cosine similarity for each record
        2. Filter by threshold (>= 0.75)
        3. Calculate memory_score
        4. Sort by memory_score descending
        """
        matches = []
        
        for record in records:
            similarity = self.calculate_cosine_similarity(
                query_vector,
                record.structure_vector,
            )
            
            if similarity < threshold:
                continue
            
            # Calculate success rate (single record = 1.0 if success else 0.0)
            success_rate = 1.0 if record.success else 0.0
            
            # Calculate recency
            recency_weight = self.calculate_recency_weight(record.timestamp)
            
            # Calculate memory score
            memory_score = self.calculate_memory_score(
                similarity,
                success_rate,
                recency_weight,
            )
            
            match = MemoryMatch(
                record_id=record.record_id,
                similarity=similarity,
                memory_score=memory_score,
                future_move=record.future_move_percent,
                success_rate=success_rate,
                timestamp=record.timestamp,
                regime_state=record.regime_state,
                hypothesis_type=record.hypothesis_type,
                horizon_minutes=record.horizon_minutes,
            )
            matches.append(match)
        
        # Sort by memory_score descending
        matches.sort(key=lambda m: m.memory_score, reverse=True)
        
        return matches
    
    # ═══════════════════════════════════════════════════════════
    # 6. Query Memory
    # ═══════════════════════════════════════════════════════════
    
    def query_memory(
        self,
        symbol: str,
        records: List[RegimeMemoryRecord],
        query_vector: Optional[List[float]] = None,
        threshold: float = SIMILARITY_THRESHOLD,
        limit: int = 10,
    ) -> MemoryResponse:
        """
        Query regime memory for similar historical situations.
        
        Returns aggregated response with matches and signals.
        """
        symbol = symbol.upper()
        
        # Build query vector if not provided
        if query_vector is None:
            structure = self.build_structure_vector(symbol)
            query_vector = structure.to_vector()
        
        # Find matches
        matches = self.find_similar_memories(query_vector, records, threshold)
        
        # Limit results
        all_matches = matches
        matches = matches[:limit]
        top_matches = matches[:5]
        
        # Aggregate signals
        expected_direction, agg_success, avg_move = self._aggregate_signals(all_matches)
        
        # Calculate memory score and confidence
        if matches:
            memory_score = sum(m.memory_score for m in top_matches) / len(top_matches)
            memory_confidence = sum(m.similarity for m in top_matches) / len(top_matches)
            best_similarity = max(m.similarity for m in matches)
        else:
            memory_score = 0.0
            memory_confidence = 0.0
            best_similarity = 0.0
        
        response = MemoryResponse(
            symbol=symbol,
            query_vector=query_vector,
            matches=matches,
            top_matches=top_matches,
            expected_direction=expected_direction,
            aggregated_success_rate=agg_success,
            avg_future_move=avg_move,
            memory_score=round(memory_score, 4),
            memory_confidence=round(memory_confidence, 4),
            total_records_searched=len(records),
            matches_found=len(all_matches),
            best_similarity=best_similarity,
        )
        
        # Cache
        self._store_response(symbol, response)
        
        return response
    
    def _aggregate_signals(
        self,
        matches: List[MemoryMatch],
    ) -> Tuple[str, float, float]:
        """Aggregate direction and success from matches."""
        if not matches:
            return "NEUTRAL", 0.0, 0.0
        
        # Weighted voting based on memory_score
        long_votes = 0.0
        short_votes = 0.0
        neutral_votes = 0.0
        
        total_success = 0.0
        total_move = 0.0
        total_weight = 0.0
        
        for match in matches:
            weight = match.memory_score
            total_weight += weight
            
            # Count success rate
            total_success += match.success_rate * weight
            total_move += match.future_move * weight
            
            # Vote on direction based on future move
            if match.future_move > 1.0:
                long_votes += weight
            elif match.future_move < -1.0:
                short_votes += weight
            else:
                neutral_votes += weight
        
        # Determine direction
        if long_votes > short_votes and long_votes > neutral_votes:
            direction = "LONG"
        elif short_votes > long_votes and short_votes > neutral_votes:
            direction = "SHORT"
        else:
            direction = "NEUTRAL"
        
        # Calculate averages
        if total_weight > 0:
            avg_success = total_success / total_weight
            avg_move = total_move / total_weight
        else:
            avg_success = 0.0
            avg_move = 0.0
        
        return direction, round(avg_success, 4), round(avg_move, 4)
    
    # ═══════════════════════════════════════════════════════════
    # 7. Memory Modifier for Hypothesis Engine
    # ═══════════════════════════════════════════════════════════
    
    def get_memory_modifier(
        self,
        symbol: str,
        hypothesis_direction: str,
        records: List[RegimeMemoryRecord],
    ) -> MemoryModifier:
        """
        Get modifier for hypothesis engine based on memory analysis.
        
        Aligned with historical success: modifier > 1
        Conflict with historical patterns: modifier < 1
        Neutral / no signal: modifier = 1
        """
        symbol = symbol.upper()
        
        # Query memory
        response = self.query_memory(symbol, records)
        
        # Determine alignment
        is_aligned = False
        modifier = 1.0
        reason = "No strong memory signal"
        
        if response.matches_found > 0 and response.memory_confidence >= 0.5:
            if response.expected_direction == hypothesis_direction:
                is_aligned = True
                modifier = 1.0 + (response.memory_score * 0.15)  # Up to 1.15
                reason = f"Memory aligned with {hypothesis_direction} (score: {response.memory_score:.2f})"
            elif response.expected_direction != "NEUTRAL":
                modifier = 1.0 - (response.memory_score * 0.10)  # Down to 0.90
                reason = f"Memory conflicts ({response.expected_direction} vs {hypothesis_direction})"
        
        return MemoryModifier(
            symbol=symbol,
            memory_score=response.memory_score,
            memory_confidence=response.memory_confidence,
            expected_direction=response.expected_direction,
            is_aligned=is_aligned,
            modifier=round(modifier, 4),
            matches_found=response.matches_found,
            best_similarity=response.best_similarity,
            historical_success_rate=response.aggregated_success_rate,
            reason=reason,
        )
    
    # ═══════════════════════════════════════════════════════════
    # 8. Pattern Analysis
    # ═══════════════════════════════════════════════════════════
    
    def analyze_patterns(
        self,
        symbol: str,
        records: List[RegimeMemoryRecord],
    ) -> List[MemoryPattern]:
        """
        Analyze memory records to find recurring patterns.
        """
        symbol = symbol.upper()
        
        # Group by regime + hypothesis combination
        pattern_groups: Dict[str, List[RegimeMemoryRecord]] = {}
        
        for record in records:
            if record.symbol != symbol:
                continue
            
            key = f"{record.hypothesis_type}_{record.regime_state}"
            if key not in pattern_groups:
                pattern_groups[key] = []
            pattern_groups[key].append(record)
        
        patterns = []
        for pattern_type, group_records in pattern_groups.items():
            if len(group_records) < 3:  # Minimum sample size
                continue
            
            successful = sum(1 for r in group_records if r.success)
            success_rate = successful / len(group_records)
            avg_move = sum(r.future_move_percent for r in group_records) / len(group_records)
            
            parts = pattern_type.split("_")
            hypothesis_type = parts[0] if parts else ""
            regime_state = parts[-1] if len(parts) > 1 else ""
            
            pattern = MemoryPattern(
                pattern_type=pattern_type,
                occurrence_count=len(group_records),
                avg_success_rate=round(success_rate, 4),
                avg_future_move=round(avg_move, 4),
                regime_state=regime_state,
                hypothesis_type=hypothesis_type,
                sample_records=[r.record_id for r in group_records[:5]],
            )
            patterns.append(pattern)
        
        # Sort by occurrence count
        patterns.sort(key=lambda p: p.occurrence_count, reverse=True)
        
        return patterns
    
    # ═══════════════════════════════════════════════════════════
    # 9. Summary Generation
    # ═══════════════════════════════════════════════════════════
    
    def generate_summary(
        self,
        symbol: str,
        records: List[RegimeMemoryRecord],
    ) -> MemorySummary:
        """
        Generate summary statistics for regime memory.
        """
        symbol = symbol.upper()
        symbol_records = [r for r in records if r.symbol == symbol]
        
        if not symbol_records:
            return MemorySummary(symbol=symbol)
        
        total = len(symbol_records)
        successful = sum(1 for r in symbol_records if r.success)
        failed = total - successful
        
        # By regime
        regime_stats = {}
        for regime in ["TRENDING", "RANGING", "VOLATILE"]:
            regime_records = [r for r in symbol_records if r.regime_state == regime]
            if regime_records:
                success_count = sum(1 for r in regime_records if r.success)
                regime_stats[regime] = success_count / len(regime_records)
            else:
                regime_stats[regime] = 0.0
        
        # By hypothesis
        hypothesis_stats = {}
        for hyp in ["BULLISH_CONTINUATION", "BEARISH_CONTINUATION", "BREAKOUT_FORMING", "RANGE_MEAN_REVERSION"]:
            hyp_records = [r for r in symbol_records if r.hypothesis_type == hyp]
            if hyp_records:
                success_count = sum(1 for r in hyp_records if r.success)
                hypothesis_stats[hyp] = success_count / len(hyp_records)
            else:
                hypothesis_stats[hyp] = 0.0
        
        # Recent accuracy (last 100)
        recent_records = sorted(symbol_records, key=lambda r: r.timestamp, reverse=True)[:100]
        if recent_records:
            recent_success = sum(1 for r in recent_records if r.success)
            recent_accuracy = recent_success / len(recent_records)
        else:
            recent_accuracy = 0.0
        
        avg_move = sum(r.future_move_percent for r in symbol_records) / total
        
        return MemorySummary(
            symbol=symbol,
            total_records=total,
            successful_records=successful,
            failed_records=failed,
            trending_success_rate=round(regime_stats.get("TRENDING", 0.0), 4),
            ranging_success_rate=round(regime_stats.get("RANGING", 0.0), 4),
            volatile_success_rate=round(regime_stats.get("VOLATILE", 0.0), 4),
            bullish_continuation_success=round(hypothesis_stats.get("BULLISH_CONTINUATION", 0.0), 4),
            bearish_continuation_success=round(hypothesis_stats.get("BEARISH_CONTINUATION", 0.0), 4),
            breakout_success=round(hypothesis_stats.get("BREAKOUT_FORMING", 0.0), 4),
            mean_reversion_success=round(hypothesis_stats.get("RANGE_MEAN_REVERSION", 0.0), 4),
            overall_success_rate=round(successful / total, 4),
            avg_future_move=round(avg_move, 4),
            recent_accuracy=round(recent_accuracy, 4),
            last_updated=datetime.now(timezone.utc),
        )
    
    # ═══════════════════════════════════════════════════════════
    # 10. Storage and Cache
    # ═══════════════════════════════════════════════════════════
    
    def _store_response(self, symbol: str, response: MemoryResponse) -> None:
        """Store response in cache."""
        if symbol not in self._responses:
            self._responses[symbol] = []
        self._responses[symbol].append(response)
        self._current[symbol] = response
    
    def get_current_response(self, symbol: str) -> Optional[MemoryResponse]:
        """Get cached response for symbol."""
        return self._current.get(symbol.upper())
    
    def get_history(self, symbol: str, limit: int = 100) -> List[MemoryResponse]:
        """Get response history."""
        history = self._responses.get(symbol.upper(), [])
        return sorted(history, key=lambda r: r.created_at, reverse=True)[:limit]
    
    # ═══════════════════════════════════════════════════════════
    # 11. Pending Outcome Management
    # ═══════════════════════════════════════════════════════════
    
    def add_pending_outcome(self, record: PendingOutcomeRecord) -> None:
        """Add record waiting for outcome evaluation."""
        symbol = record.symbol.upper()
        if symbol not in self._pending:
            self._pending[symbol] = []
        self._pending[symbol].append(record)
    
    def get_pending_outcomes(self, symbol: str) -> List[PendingOutcomeRecord]:
        """Get pending outcomes for symbol."""
        return self._pending.get(symbol.upper(), [])
    
    def remove_pending_outcome(self, pending_id: str, symbol: str) -> bool:
        """Remove pending outcome after evaluation."""
        symbol = symbol.upper()
        if symbol not in self._pending:
            return False
        
        initial_len = len(self._pending[symbol])
        self._pending[symbol] = [p for p in self._pending[symbol] if p.pending_id != pending_id]
        return len(self._pending[symbol]) < initial_len


# ══════════════════════════════════════════════════════════════
# Singleton
# ══════════════════════════════════════════════════════════════

_memory_engine: Optional[RegimeMemoryEngine] = None


def get_memory_engine() -> RegimeMemoryEngine:
    """Get singleton instance of RegimeMemoryEngine."""
    global _memory_engine
    if _memory_engine is None:
        _memory_engine = RegimeMemoryEngine()
    return _memory_engine
