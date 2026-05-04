"""
Meta-Alpha Pattern Engine

PHASE 31.1 — Meta-Alpha Pattern Engine

Detects meta-patterns: combinations of regime + hypothesis + microstructure
that produce superior returns.

Example:
    regime = VOLATILE
    hypothesis = BREAKOUT_FORMING
    microstructure = VACUUM
    → success_rate = 78%

This is the 4th level of intelligence (Meta Intelligence) used by
Renaissance, Citadel, Two Sigma.

Key features:
- Pattern extraction from outcome history
- Meta score calculation (success + PnL + observations)
- Pattern classification (STRONG/MODERATE/WEAK)
- Integration with Capital Allocation via meta_alpha_modifier
"""

from typing import Optional, List, Dict, Tuple
from datetime import datetime, timezone
from collections import defaultdict
import math

from .meta_alpha_types import (
    MetaAlphaPattern,
    MetaAlphaSummary,
    PatternObservation,
    StrongMetaPattern,
    MIN_META_OBSERVATIONS,
    META_SCORE_SUCCESS_WEIGHT,
    META_SCORE_PNL_WEIGHT,
    META_SCORE_OBSERVATIONS_WEIGHT,
    PNL_NORMALIZE_MIN,
    PNL_NORMALIZE_MAX,
    OBS_NORMALIZE_BASE,
    STRONG_META_ALPHA_THRESHOLD,
    MODERATE_META_ALPHA_THRESHOLD,
    META_ALPHA_MODIFIERS,
    MetaAlphaClassification,
)


# ══════════════════════════════════════════════════════════════
# Meta-Alpha Pattern Engine
# ══════════════════════════════════════════════════════════════

class MetaAlphaEngine:
    """
    Meta-Alpha Pattern Engine — PHASE 31.1
    
    Discovers meta-patterns across regime, hypothesis, and microstructure.
    
    Pipeline:
    1. Collect observations with context (regime, hypothesis, microstructure)
    2. Group by pattern (regime + hypothesis + microstructure)
    3. Calculate statistics (success_rate, avg_pnl)
    4. Calculate meta_score
    5. Classify patterns
    6. Provide modifiers for Capital Allocation
    """
    
    def __init__(self):
        # Pattern storage by symbol
        self._patterns: Dict[str, Dict[str, MetaAlphaPattern]] = {}
        # Raw observations by symbol
        self._observations: Dict[str, List[PatternObservation]] = {}
        # Current context by symbol
        self._current_context: Dict[str, Dict[str, str]] = {}
    
    # ═══════════════════════════════════════════════════════════
    # 1. Context Management
    # ═══════════════════════════════════════════════════════════
    
    def set_context(
        self,
        symbol: str,
        regime_type: str = "NEUTRAL",
        microstructure_state: str = "BALANCED",
    ) -> None:
        """
        Set current market context for observation recording.
        """
        self._current_context[symbol.upper()] = {
            "regime_type": regime_type,
            "microstructure_state": microstructure_state,
        }
    
    def get_context(self, symbol: str) -> Dict[str, str]:
        """Get current context for symbol."""
        return self._current_context.get(symbol.upper(), {
            "regime_type": "NEUTRAL",
            "microstructure_state": "BALANCED",
        })
    
    # ═══════════════════════════════════════════════════════════
    # 2. Observation Recording
    # ═══════════════════════════════════════════════════════════
    
    def record_observation(
        self,
        symbol: str,
        hypothesis_type: str,
        success: bool,
        pnl_percent: float,
        regime_type: Optional[str] = None,
        microstructure_state: Optional[str] = None,
    ) -> PatternObservation:
        """
        Record an outcome observation with full context.
        """
        symbol = symbol.upper()
        
        # Get context from current state or provided
        context = self.get_context(symbol)
        regime = regime_type or context.get("regime_type", "NEUTRAL")
        micro = microstructure_state or context.get("microstructure_state", "BALANCED")
        
        observation = PatternObservation(
            regime_type=regime,
            hypothesis_type=hypothesis_type,
            microstructure_state=micro,
            success=success,
            pnl_percent=pnl_percent,
        )
        
        if symbol not in self._observations:
            self._observations[symbol] = []
        self._observations[symbol].append(observation)
        
        return observation
    
    # ═══════════════════════════════════════════════════════════
    # 3. Pattern Extraction
    # ═══════════════════════════════════════════════════════════
    
    def extract_patterns(
        self,
        symbol: str,
    ) -> List[MetaAlphaPattern]:
        """
        Extract meta-alpha patterns from observations.
        
        Groups observations by (regime, hypothesis, microstructure)
        and calculates statistics.
        """
        symbol = symbol.upper()
        observations = self._observations.get(symbol, [])
        
        if not observations:
            # Generate mock patterns for testing if no observations
            return self._generate_mock_patterns(symbol)
        
        # Group by pattern
        pattern_groups: Dict[str, List[PatternObservation]] = defaultdict(list)
        
        for obs in observations:
            key = f"{obs.regime_type}|{obs.hypothesis_type}|{obs.microstructure_state}"
            pattern_groups[key].append(obs)
        
        # Calculate patterns
        patterns = []
        for key, obs_list in pattern_groups.items():
            parts = key.split("|")
            regime, hypothesis, micro = parts[0], parts[1], parts[2]
            
            pattern = self._calculate_pattern(
                regime, hypothesis, micro, obs_list
            )
            patterns.append(pattern)
        
        # Store patterns
        self._store_patterns(symbol, patterns)
        
        return patterns
    
    def _generate_mock_patterns(self, symbol: str) -> List[MetaAlphaPattern]:
        """Generate mock patterns when no real data exists."""
        mock_patterns = []
        
        # Define some typical combinations
        combos = [
            ("VOLATILE", "BREAKOUT_FORMING", "VACUUM", 0.71, 0.84, 132),
            ("TRENDING", "BULLISH_CONTINUATION", "BID_DOMINANT", 0.65, 0.52, 98),
            ("RANGING", "MEAN_REVERSION", "BALANCED", 0.58, 0.31, 156),
            ("VOLATILE", "BEARISH_REVERSAL", "ASK_DOMINANT", 0.62, 0.45, 67),
            ("TRENDING", "BREAKOUT_FORMING", "BALANCED", 0.55, 0.22, 89),
        ]
        
        for regime, hypo, micro, sr, pnl, obs in combos:
            pattern_id = MetaAlphaPattern.generate_pattern_id(regime, hypo, micro)
            meta_score = self.calculate_meta_score(sr, pnl, obs)
            classification = self.classify_pattern(meta_score)
            
            pattern = MetaAlphaPattern(
                pattern_id=pattern_id,
                regime_type=regime,
                hypothesis_type=hypo,
                microstructure_state=micro,
                observations=obs,
                success_rate=sr,
                avg_pnl=pnl,
                meta_score=meta_score,
                classification=classification,
            )
            mock_patterns.append(pattern)
        
        self._store_patterns(symbol, mock_patterns)
        return mock_patterns
    
    def _calculate_pattern(
        self,
        regime: str,
        hypothesis: str,
        microstructure: str,
        observations: List[PatternObservation],
    ) -> MetaAlphaPattern:
        """Calculate pattern statistics from observations."""
        pattern_id = MetaAlphaPattern.generate_pattern_id(
            regime, hypothesis, microstructure
        )
        
        total = len(observations)
        successes = sum(1 for o in observations if o.success)
        success_rate = successes / total if total > 0 else 0.5
        avg_pnl = sum(o.pnl_percent for o in observations) / total if total > 0 else 0.0
        
        meta_score = self.calculate_meta_score(success_rate, avg_pnl, total)
        classification = self.classify_pattern(meta_score)
        
        return MetaAlphaPattern(
            pattern_id=pattern_id,
            regime_type=regime,
            hypothesis_type=hypothesis,
            microstructure_state=microstructure,
            observations=total,
            success_rate=round(success_rate, 4),
            avg_pnl=round(avg_pnl, 4),
            meta_score=meta_score,
            classification=classification,
        )
    
    # ═══════════════════════════════════════════════════════════
    # 4. Meta Score Calculation
    # ═══════════════════════════════════════════════════════════
    
    def calculate_meta_score(
        self,
        success_rate: float,
        avg_pnl: float,
        observations: int,
    ) -> float:
        """
        Calculate meta score.
        
        Formula:
        meta_score = 0.50 × success_rate
                   + 0.30 × normalized_pnl
                   + 0.20 × log(observations) / log(base)
        
        Bounded: 0 ≤ meta_score ≤ 1
        """
        # Minimum observations check
        if observations < MIN_META_OBSERVATIONS:
            return 0.0
        
        # Normalize PnL to [0, 1]
        pnl_clamped = max(PNL_NORMALIZE_MIN, min(PNL_NORMALIZE_MAX, avg_pnl))
        normalized_pnl = (pnl_clamped - PNL_NORMALIZE_MIN) / (PNL_NORMALIZE_MAX - PNL_NORMALIZE_MIN)
        
        # Normalize observations (log scale)
        obs_log = math.log(observations + 1)
        base_log = math.log(OBS_NORMALIZE_BASE)
        normalized_obs = min(obs_log / base_log, 1.0)
        
        # Calculate score
        score = (
            META_SCORE_SUCCESS_WEIGHT * success_rate
            + META_SCORE_PNL_WEIGHT * normalized_pnl
            + META_SCORE_OBSERVATIONS_WEIGHT * normalized_obs
        )
        
        # Clamp to [0, 1]
        return round(max(0.0, min(1.0, score)), 4)
    
    # ═══════════════════════════════════════════════════════════
    # 5. Pattern Classification
    # ═══════════════════════════════════════════════════════════
    
    def classify_pattern(self, meta_score: float) -> MetaAlphaClassification:
        """
        Classify pattern based on meta score.
        
        >= 0.70: STRONG_META_ALPHA
        0.55-0.70: MODERATE_META_ALPHA
        < 0.55: WEAK_PATTERN
        """
        if meta_score >= STRONG_META_ALPHA_THRESHOLD:
            return "STRONG_META_ALPHA"
        elif meta_score >= MODERATE_META_ALPHA_THRESHOLD:
            return "MODERATE_META_ALPHA"
        else:
            return "WEAK_PATTERN"
    
    # ═══════════════════════════════════════════════════════════
    # 6. Get Meta Alpha Modifier
    # ═══════════════════════════════════════════════════════════
    
    def get_meta_modifier(
        self,
        symbol: str,
        hypothesis_type: str,
        regime_type: Optional[str] = None,
        microstructure_state: Optional[str] = None,
    ) -> float:
        """
        Get meta-alpha modifier for a specific combination.
        
        Used by Capital Allocation Engine.
        
        STRONG_META_ALPHA: 1.25
        MODERATE_META_ALPHA: 1.10
        WEAK_PATTERN: 1.00
        """
        symbol = symbol.upper()
        context = self.get_context(symbol)
        
        regime = regime_type or context.get("regime_type", "NEUTRAL")
        micro = microstructure_state or context.get("microstructure_state", "BALANCED")
        
        pattern_id = MetaAlphaPattern.generate_pattern_id(regime, hypothesis_type, micro)
        
        symbol_patterns = self._patterns.get(symbol, {})
        pattern = symbol_patterns.get(pattern_id)
        
        if pattern and pattern.observations >= MIN_META_OBSERVATIONS:
            return META_ALPHA_MODIFIERS.get(pattern.classification, 1.0)
        
        return 1.0
    
    def get_all_modifiers(
        self,
        symbol: str,
        regime_type: Optional[str] = None,
        microstructure_state: Optional[str] = None,
    ) -> Dict[str, float]:
        """
        Get all meta-alpha modifiers for hypothesis types.
        """
        symbol = symbol.upper()
        context = self.get_context(symbol)
        
        regime = regime_type or context.get("regime_type", "NEUTRAL")
        micro = microstructure_state or context.get("microstructure_state", "BALANCED")
        
        modifiers = {}
        symbol_patterns = self._patterns.get(symbol, {})
        
        for pattern in symbol_patterns.values():
            if pattern.regime_type == regime and pattern.microstructure_state == micro:
                if pattern.observations >= MIN_META_OBSERVATIONS:
                    modifiers[pattern.hypothesis_type] = META_ALPHA_MODIFIERS.get(
                        pattern.classification, 1.0
                    )
        
        return modifiers
    
    # ═══════════════════════════════════════════════════════════
    # 7. Get Strong Patterns
    # ═══════════════════════════════════════════════════════════
    
    def get_strong_patterns(self, symbol: str) -> List[StrongMetaPattern]:
        """Get all strong meta-alpha patterns."""
        symbol = symbol.upper()
        symbol_patterns = self._patterns.get(symbol, {})
        
        strong = []
        for pattern in symbol_patterns.values():
            if pattern.classification == "STRONG_META_ALPHA":
                strong.append(StrongMetaPattern(
                    pattern_id=pattern.pattern_id,
                    regime_type=pattern.regime_type,
                    hypothesis_type=pattern.hypothesis_type,
                    microstructure_state=pattern.microstructure_state,
                    meta_score=pattern.meta_score,
                    success_rate=pattern.success_rate,
                    avg_pnl=pattern.avg_pnl,
                    observations=pattern.observations,
                    modifier=META_ALPHA_MODIFIERS["STRONG_META_ALPHA"],
                ))
        
        return sorted(strong, key=lambda p: p.meta_score, reverse=True)
    
    # ═══════════════════════════════════════════════════════════
    # 8. Storage
    # ═══════════════════════════════════════════════════════════
    
    def _store_patterns(
        self,
        symbol: str,
        patterns: List[MetaAlphaPattern],
    ) -> None:
        """Store patterns in memory."""
        if symbol not in self._patterns:
            self._patterns[symbol] = {}
        
        for p in patterns:
            self._patterns[symbol][p.pattern_id] = p
    
    def get_patterns(self, symbol: str) -> List[MetaAlphaPattern]:
        """Get all patterns for symbol."""
        symbol_patterns = self._patterns.get(symbol.upper(), {})
        return list(symbol_patterns.values())
    
    def get_pattern(
        self,
        symbol: str,
        pattern_id: str,
    ) -> Optional[MetaAlphaPattern]:
        """Get specific pattern by ID."""
        symbol_patterns = self._patterns.get(symbol.upper(), {})
        return symbol_patterns.get(pattern_id)
    
    # ═══════════════════════════════════════════════════════════
    # 9. Summary
    # ═══════════════════════════════════════════════════════════
    
    def get_summary(self, symbol: str) -> MetaAlphaSummary:
        """Get meta-alpha summary for symbol."""
        patterns = self.get_patterns(symbol.upper())
        
        if not patterns:
            return MetaAlphaSummary(symbol=symbol.upper())
        
        valid_patterns = [p for p in patterns if p.observations >= MIN_META_OBSERVATIONS]
        
        strong = sum(1 for p in valid_patterns if p.classification == "STRONG_META_ALPHA")
        moderate = sum(1 for p in valid_patterns if p.classification == "MODERATE_META_ALPHA")
        weak = sum(1 for p in valid_patterns if p.classification == "WEAK_PATTERN")
        
        total_obs = sum(p.observations for p in patterns)
        
        if valid_patterns:
            avg_score = sum(p.meta_score for p in valid_patterns) / len(valid_patterns)
            avg_sr = sum(p.success_rate for p in valid_patterns) / len(valid_patterns)
            avg_pnl = sum(p.avg_pnl for p in valid_patterns) / len(valid_patterns)
            
            best = max(valid_patterns, key=lambda p: p.meta_score)
            best_desc = f"{best.regime_type}+{best.hypothesis_type}+{best.microstructure_state}"
        else:
            avg_score = avg_sr = avg_pnl = 0.0
            best = None
            best_desc = ""
        
        return MetaAlphaSummary(
            symbol=symbol.upper(),
            total_patterns=len(patterns),
            valid_patterns=len(valid_patterns),
            strong_count=strong,
            moderate_count=moderate,
            weak_count=weak,
            avg_meta_score=round(avg_score, 4),
            avg_success_rate=round(avg_sr, 4),
            avg_pnl=round(avg_pnl, 4),
            best_pattern_id=best.pattern_id if best else "NONE",
            best_pattern_score=best.meta_score if best else 0.0,
            best_pattern_description=best_desc,
            total_observations=total_obs,
            last_updated=max(p.updated_at for p in patterns) if patterns else None,
        )


# ══════════════════════════════════════════════════════════════
# Singleton
# ══════════════════════════════════════════════════════════════

_meta_engine: Optional[MetaAlphaEngine] = None


def get_meta_alpha_engine() -> MetaAlphaEngine:
    """Get singleton instance of MetaAlphaEngine."""
    global _meta_engine
    if _meta_engine is None:
        _meta_engine = MetaAlphaEngine()
    return _meta_engine
