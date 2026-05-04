"""
Fractal Similarity Engine

PHASE 32.2 — Fractal Similarity Engine

Finds historical market structures similar to the current one
and uses that information to influence trading decisions.

Key features:
- Structure encoding (vectorization of market data)
- Cosine Similarity algorithm for pattern matching
- Expected direction inference from historical outcomes
- Confidence calculation based on similarity and success rate
- Integration with Hypothesis Engine via modifier

Scoring formula (updated):
0.35 alpha + 0.25 regime + 0.20 microstructure + 0.10 macro + 0.05 fractal_market + 0.05 fractal_similarity
"""

import math
import hashlib
from typing import Optional, List, Dict, Tuple
from datetime import datetime, timezone
from collections import Counter

from .similarity_types import (
    StructureVector,
    HistoricalPattern,
    SimilarityMatch,
    SimilarityAnalysis,
    SimilarityModifier,
    SimilaritySummary,
    DirectionType,
    WINDOW_SIZES,
    SIMILARITY_THRESHOLD,
    SIMILARITY_WEIGHT,
    HISTORICAL_SUCCESS_WEIGHT,
    SIMILARITY_ALIGNED_MODIFIER,
    SIMILARITY_CONFLICT_MODIFIER,
)


# ══════════════════════════════════════════════════════════════
# Fractal Similarity Engine
# ══════════════════════════════════════════════════════════════

class FractalSimilarityEngine:
    """
    Fractal Similarity Engine — PHASE 32.2
    
    Finds historical market structures similar to the current one
    and provides modifiers for hypothesis scoring.
    
    Pipeline:
    1. Encode current market data into structure vector
    2. Compare with historical patterns using cosine similarity
    3. Find matches with similarity >= 0.75
    4. Infer expected direction from historical outcomes
    5. Calculate confidence based on similarity and success rate
    6. Provide modifier for hypothesis scoring
    """
    
    def __init__(self):
        # In-memory storage (would be MongoDB in production)
        self._patterns: Dict[str, List[HistoricalPattern]] = {}
        self._analyses: Dict[str, List[SimilarityAnalysis]] = {}
        self._current: Dict[str, SimilarityAnalysis] = {}
    
    # ═══════════════════════════════════════════════════════════
    # 1. Structure Encoding
    # ═══════════════════════════════════════════════════════════
    
    def encode_structure(
        self,
        symbol: str,
        window_size: int,
        candle_data: Optional[Dict] = None,
    ) -> StructureVector:
        """
        Encode market data into structure vector.
        
        Converts candle window into numeric features:
        - trend_slope: EMA slope normalized
        - volatility_ratio: ATR / avg ATR
        - volume_delta: Volume change ratio
        - momentum: RSI normalized to [-1, 1]
        - range_position: Price position in range [0, 1]
        - body_ratio: Avg candle body / range
        - upper_wick_ratio: Avg upper wick / range
        - lower_wick_ratio: Avg lower wick / range
        - trend_strength: ADX normalized [0, 1]
        """
        symbol = symbol.upper()
        
        if candle_data is None:
            candle_data = self._generate_mock_candle_data(symbol, window_size)
        
        vector = StructureVector(
            symbol=symbol,
            window_size=window_size,
            trend_slope=candle_data.get("trend_slope", 0.0),
            volatility_ratio=candle_data.get("volatility_ratio", 1.0),
            volume_delta=candle_data.get("volume_delta", 0.0),
            momentum=candle_data.get("momentum", 0.0),
            range_position=candle_data.get("range_position", 0.5),
            body_ratio=candle_data.get("body_ratio", 0.5),
            upper_wick_ratio=candle_data.get("upper_wick_ratio", 0.25),
            lower_wick_ratio=candle_data.get("lower_wick_ratio", 0.25),
            trend_strength=candle_data.get("trend_strength", 0.5),
        )
        
        vector.vector = vector.to_vector()
        
        return vector
    
    def _generate_mock_candle_data(
        self,
        symbol: str,
        window_size: int,
    ) -> Dict:
        """Generate mock candle data for testing."""
        # Generate deterministic but varied data
        seed = int(hashlib.md5(f"{symbol}{window_size}".encode()).hexdigest()[:8], 16)
        
        # Create realistic-looking features
        base_trend = ((seed % 100) - 50) / 100  # [-0.5, 0.5]
        
        return {
            "trend_slope": base_trend * (1 + (seed % 20) / 50),
            "volatility_ratio": 0.7 + (seed % 60) / 100,
            "volume_delta": ((seed % 80) - 40) / 100,
            "momentum": ((seed % 100) - 50) / 50,  # RSI-like
            "range_position": (seed % 100) / 100,
            "body_ratio": 0.3 + (seed % 40) / 100,
            "upper_wick_ratio": 0.1 + (seed % 30) / 100,
            "lower_wick_ratio": 0.1 + (seed % 30) / 100,
            "trend_strength": 0.2 + (seed % 60) / 100,
        }
    
    # ═══════════════════════════════════════════════════════════
    # 2. Cosine Similarity
    # ═══════════════════════════════════════════════════════════
    
    def cosine_similarity(
        self,
        vec_a: List[float],
        vec_b: List[float],
    ) -> float:
        """
        Calculate cosine similarity between two vectors.
        
        Formula: cos(θ) = (A · B) / (||A|| × ||B||)
        
        Returns: similarity score [0, 1]
        """
        if len(vec_a) != len(vec_b):
            return 0.0
        
        if not vec_a or not vec_b:
            return 0.0
        
        # Dot product
        dot_product = sum(a * b for a, b in zip(vec_a, vec_b))
        
        # Magnitudes
        mag_a = math.sqrt(sum(a * a for a in vec_a))
        mag_b = math.sqrt(sum(b * b for b in vec_b))
        
        if mag_a == 0 or mag_b == 0:
            return 0.0
        
        similarity = dot_product / (mag_a * mag_b)
        
        # Normalize to [0, 1] (cosine can be [-1, 1])
        normalized = (similarity + 1) / 2
        
        return round(min(max(normalized, 0.0), 1.0), 4)
    
    # ═══════════════════════════════════════════════════════════
    # 3. Pattern Matching
    # ═══════════════════════════════════════════════════════════
    
    def find_similar_patterns(
        self,
        current_vector: StructureVector,
        threshold: float = SIMILARITY_THRESHOLD,
        max_results: int = 20,
    ) -> List[SimilarityMatch]:
        """
        Find historical patterns similar to current structure.
        
        Returns matches with similarity >= threshold.
        """
        symbol = current_vector.symbol
        window_size = current_vector.window_size
        
        # Get patterns for this symbol and window
        key = f"{symbol}_{window_size}"
        patterns = self._patterns.get(key, [])
        
        # If no patterns, generate some mock historical data
        if not patterns:
            patterns = self._generate_mock_patterns(symbol, window_size)
            self._patterns[key] = patterns
        
        current_vec = current_vector.to_vector()
        matches = []
        
        for pattern in patterns:
            similarity = self.cosine_similarity(current_vec, pattern.vector)
            
            if similarity >= threshold:
                match = SimilarityMatch(
                    pattern_id=pattern.pattern_id,
                    similarity_score=similarity,
                    historical_direction=pattern.outcome_direction,
                    historical_return=pattern.outcome_return,
                    was_successful=pattern.was_successful,
                    pattern_timestamp=pattern.end_timestamp,
                    window_size=pattern.window_size,
                )
                matches.append(match)
        
        # Sort by similarity (descending)
        matches.sort(key=lambda m: m.similarity_score, reverse=True)
        
        return matches[:max_results]
    
    def _generate_mock_patterns(
        self,
        symbol: str,
        window_size: int,
        count: int = 50,
    ) -> List[HistoricalPattern]:
        """Generate mock historical patterns for testing."""
        patterns = []
        
        for i in range(count):
            seed = int(hashlib.md5(f"{symbol}{window_size}{i}".encode()).hexdigest()[:8], 16)
            
            # Generate varied vectors
            vector = [
                ((seed + j) % 100 - 50) / 100
                for j in range(9)
            ]
            
            # Determine outcome based on pattern
            trend_direction = sum(vector[:3]) / 3
            if trend_direction > 0.1:
                direction = "LONG"
                outcome_return = abs(trend_direction) * 10 + (seed % 5)
                was_successful = (seed % 3) != 0  # 67% success
            elif trend_direction < -0.1:
                direction = "SHORT"
                outcome_return = -abs(trend_direction) * 10 - (seed % 5)
                was_successful = (seed % 3) != 0
            else:
                direction = "NEUTRAL"
                outcome_return = ((seed % 10) - 5) / 2
                was_successful = (seed % 2) == 0  # 50% success
            
            pattern = HistoricalPattern(
                pattern_id=f"{symbol}_{window_size}_{i}",
                symbol=symbol,
                window_size=window_size,
                vector=vector,
                outcome_direction=direction,
                outcome_return=round(outcome_return, 2),
                outcome_bars=20,
                was_successful=was_successful,
                start_timestamp=datetime.now(timezone.utc),
                end_timestamp=datetime.now(timezone.utc),
            )
            patterns.append(pattern)
        
        return patterns
    
    # ═══════════════════════════════════════════════════════════
    # 4. Direction Inference
    # ═══════════════════════════════════════════════════════════
    
    def infer_direction(
        self,
        matches: List[SimilarityMatch],
    ) -> Tuple[DirectionType, float]:
        """
        Infer expected direction from historical matches.
        
        Weights by similarity score and success.
        
        Returns: (direction, confidence)
        """
        if not matches:
            return "NEUTRAL", 0.0
        
        # Weight votes by similarity
        long_score = 0.0
        short_score = 0.0
        neutral_score = 0.0
        
        for match in matches:
            weight = match.similarity_score
            
            # Boost weight if pattern was successful
            if match.was_successful:
                weight *= 1.2
            
            if match.historical_direction == "LONG":
                long_score += weight
            elif match.historical_direction == "SHORT":
                short_score += weight
            else:
                neutral_score += weight
        
        total = long_score + short_score + neutral_score
        
        if total == 0:
            return "NEUTRAL", 0.0
        
        # Determine winner
        if long_score >= short_score and long_score >= neutral_score:
            direction = "LONG"
            confidence = long_score / total
        elif short_score >= long_score and short_score >= neutral_score:
            direction = "SHORT"
            confidence = short_score / total
        else:
            direction = "NEUTRAL"
            confidence = neutral_score / total
        
        return direction, round(confidence, 4)
    
    # ═══════════════════════════════════════════════════════════
    # 5. Success Rate Calculation
    # ═══════════════════════════════════════════════════════════
    
    def calculate_success_rate(
        self,
        matches: List[SimilarityMatch],
    ) -> Tuple[float, float]:
        """
        Calculate success rate and average return of matches.
        
        Returns: (success_rate, avg_return)
        """
        if not matches:
            return 0.0, 0.0
        
        successful = sum(1 for m in matches if m.was_successful)
        success_rate = successful / len(matches)
        
        avg_return = sum(m.historical_return for m in matches) / len(matches)
        
        return round(success_rate, 4), round(avg_return, 4)
    
    # ═══════════════════════════════════════════════════════════
    # 6. Confidence Calculation
    # ═══════════════════════════════════════════════════════════
    
    def calculate_confidence(
        self,
        best_similarity: float,
        success_rate: float,
    ) -> float:
        """
        Calculate overall similarity confidence.
        
        Formula:
        confidence = 0.60 × best_similarity + 0.40 × success_rate
        """
        confidence = (
            SIMILARITY_WEIGHT * best_similarity
            + HISTORICAL_SUCCESS_WEIGHT * success_rate
        )
        
        return round(min(max(confidence, 0.0), 1.0), 4)
    
    # ═══════════════════════════════════════════════════════════
    # 7. Full Analysis
    # ═══════════════════════════════════════════════════════════
    
    def analyze_similarity(
        self,
        symbol: str,
        candle_data: Optional[Dict[int, Dict]] = None,
    ) -> SimilarityAnalysis:
        """
        Perform full similarity analysis.
        
        Analyzes all window sizes (50, 100, 200) and aggregates results.
        """
        symbol = symbol.upper()
        
        all_matches = []
        all_vectors = []
        
        for window_size in WINDOW_SIZES:
            # Get candle data for this window
            window_data = None
            if candle_data and window_size in candle_data:
                window_data = candle_data[window_size]
            
            # Encode current structure
            vector = self.encode_structure(symbol, window_size, window_data)
            all_vectors.append(vector)
            
            # Find similar patterns
            matches = self.find_similar_patterns(vector)
            all_matches.extend(matches)
        
        # Sort all matches by similarity
        all_matches.sort(key=lambda m: m.similarity_score, reverse=True)
        
        # Get top matches
        top_matches = all_matches[:5]
        
        # Infer direction
        expected_direction, direction_confidence = self.infer_direction(all_matches)
        
        # Calculate success rate
        success_rate, avg_return = self.calculate_success_rate(all_matches)
        
        # Calculate confidence
        best_similarity = all_matches[0].similarity_score if all_matches else 0.0
        similarity_confidence = self.calculate_confidence(best_similarity, success_rate)
        
        # Use first vector as primary (100 window)
        primary_vector = all_vectors[1] if len(all_vectors) > 1 else (all_vectors[0] if all_vectors else None)
        
        analysis = SimilarityAnalysis(
            symbol=symbol,
            current_vector=primary_vector,
            matches=all_matches[:20],
            top_matches=top_matches,
            expected_direction=expected_direction,
            direction_confidence=direction_confidence,
            historical_success_rate=success_rate,
            avg_historical_return=avg_return,
            similarity_confidence=similarity_confidence,
            patterns_searched=len(self._patterns.get(f"{symbol}_100", [])) * len(WINDOW_SIZES),
            matches_found=len(all_matches),
            best_similarity=best_similarity,
        )
        
        # Store analysis
        self._store_analysis(symbol, analysis)
        
        return analysis
    
    # ═══════════════════════════════════════════════════════════
    # 8. Similarity Modifier
    # ═══════════════════════════════════════════════════════════
    
    def get_similarity_modifier(
        self,
        symbol: str,
        hypothesis_direction: str,
    ) -> SimilarityModifier:
        """
        Get similarity modifier for hypothesis scoring.
        
        If expected_direction matches hypothesis: modifier = 1.12
        If conflict: modifier = 0.90
        """
        symbol = symbol.upper()
        
        # Get current analysis
        analysis = self._current.get(symbol)
        if analysis is None:
            analysis = self.analyze_similarity(symbol)
        
        # Normalize hypothesis direction
        h_dir = hypothesis_direction.upper()
        if h_dir in ["LONG", "BULLISH", "TREND_UP", "UP"]:
            h_dir = "LONG"
        elif h_dir in ["SHORT", "BEARISH", "TREND_DOWN", "DOWN"]:
            h_dir = "SHORT"
        else:
            h_dir = "NEUTRAL"
        
        # Check alignment
        is_aligned = (
            (analysis.expected_direction == "LONG" and h_dir == "LONG")
            or (analysis.expected_direction == "SHORT" and h_dir == "SHORT")
            or analysis.expected_direction == "NEUTRAL"
        )
        
        # Apply modifier
        if is_aligned:
            if analysis.expected_direction != "NEUTRAL":
                modifier = SIMILARITY_ALIGNED_MODIFIER
                reason = f"Similarity aligned: expected={analysis.expected_direction}, hypothesis={h_dir}"
            else:
                modifier = 1.0
                reason = "Similarity neutral - no clear historical pattern"
        else:
            modifier = SIMILARITY_CONFLICT_MODIFIER
            reason = f"Similarity conflict: expected={analysis.expected_direction}, hypothesis={h_dir}"
        
        return SimilarityModifier(
            hypothesis_direction=hypothesis_direction,
            expected_direction=analysis.expected_direction,
            similarity_confidence=analysis.similarity_confidence,
            is_aligned=is_aligned,
            modifier=modifier,
            matches_found=analysis.matches_found,
            best_similarity=analysis.best_similarity,
            historical_success_rate=analysis.historical_success_rate,
            reason=reason,
        )
    
    # ═══════════════════════════════════════════════════════════
    # 9. Storage
    # ═══════════════════════════════════════════════════════════
    
    def _store_analysis(
        self,
        symbol: str,
        analysis: SimilarityAnalysis,
    ) -> None:
        """Store analysis in memory."""
        if symbol not in self._analyses:
            self._analyses[symbol] = []
        self._analyses[symbol].append(analysis)
        self._current[symbol] = analysis
    
    def store_pattern(
        self,
        pattern: HistoricalPattern,
    ) -> str:
        """Store a new historical pattern."""
        key = f"{pattern.symbol}_{pattern.window_size}"
        if key not in self._patterns:
            self._patterns[key] = []
        self._patterns[key].append(pattern)
        return pattern.pattern_id
    
    def get_current_analysis(
        self,
        symbol: str,
    ) -> Optional[SimilarityAnalysis]:
        """Get current similarity analysis."""
        return self._current.get(symbol.upper())
    
    def get_top_matches(
        self,
        symbol: str,
        limit: int = 5,
    ) -> List[SimilarityMatch]:
        """Get top similarity matches."""
        analysis = self._current.get(symbol.upper())
        if analysis:
            return analysis.top_matches[:limit]
        return []
    
    def get_history(
        self,
        symbol: str,
        limit: int = 100,
    ) -> List[SimilarityAnalysis]:
        """Get analysis history."""
        history = self._analyses.get(symbol.upper(), [])
        return sorted(history, key=lambda a: a.created_at, reverse=True)[:limit]
    
    # ═══════════════════════════════════════════════════════════
    # 10. Summary
    # ═══════════════════════════════════════════════════════════
    
    def get_summary(self, symbol: str) -> SimilaritySummary:
        """Get similarity summary for symbol."""
        symbol = symbol.upper()
        history = self._analyses.get(symbol, [])
        current = self._current.get(symbol)
        
        if not history or not current:
            return SimilaritySummary(symbol=symbol)
        
        # Calculate averages
        avg_match_rate = sum(
            a.matches_found / max(a.patterns_searched, 1)
            for a in history
        ) / len(history)
        
        avg_success_rate = sum(
            a.historical_success_rate
            for a in history
        ) / len(history)
        
        # Find best window
        window_success = {ws: [] for ws in WINDOW_SIZES}
        for a in history:
            for match in a.matches:
                if match.was_successful:
                    window_success[match.window_size].append(1)
                else:
                    window_success[match.window_size].append(0)
        
        best_window = max(
            WINDOW_SIZES,
            key=lambda ws: (
                sum(window_success[ws]) / max(len(window_success[ws]), 1)
                if window_success[ws] else 0
            )
        )
        best_rate = (
            sum(window_success[best_window]) / len(window_success[best_window])
            if window_success[best_window] else 0
        )
        
        # Count patterns
        total_patterns = sum(
            len(patterns)
            for key, patterns in self._patterns.items()
            if key.startswith(symbol)
        )
        
        return SimilaritySummary(
            symbol=symbol,
            current_direction=current.expected_direction,
            current_confidence=current.similarity_confidence,
            total_patterns_stored=total_patterns,
            total_analyses=len(history),
            avg_match_rate=round(avg_match_rate, 4),
            avg_success_rate=round(avg_success_rate, 4),
            best_window_size=best_window,
            best_window_success_rate=round(best_rate, 4),
            last_updated=current.created_at,
        )


# ══════════════════════════════════════════════════════════════
# Singleton
# ══════════════════════════════════════════════════════════════

_similarity_engine: Optional[FractalSimilarityEngine] = None


def get_similarity_engine() -> FractalSimilarityEngine:
    """Get singleton instance of FractalSimilarityEngine."""
    global _similarity_engine
    if _similarity_engine is None:
        _similarity_engine = FractalSimilarityEngine()
    return _similarity_engine
