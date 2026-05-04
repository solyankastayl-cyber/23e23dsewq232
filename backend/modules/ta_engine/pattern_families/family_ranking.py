"""
Family Ranking — Selects Dominant Pattern
==========================================

After family detectors run, this engine:
1. Collects all candidates from all families
2. VALIDATES each pattern window (NEW!)
3. Ranks them by confidence
4. Resolves conflicts
5. Returns dominant + alternatives

KEY PRINCIPLE: Better to return "no pattern" than garbage fallback
"""

from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field

from .pattern_family_matrix import PatternFamily, PatternBias
from .pattern_window_validator import validate_pattern_window


@dataclass
class RankedPattern:
    """A pattern with ranking metadata."""
    type: str
    family: PatternFamily
    bias: PatternBias
    confidence: float
    rank: int
    pattern_data: Dict = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        return {
            "type": self.type,
            "family": self.family.value,
            "bias": self.bias.value,
            "confidence": round(self.confidence, 2),
            "rank": self.rank,
            **self.pattern_data,
        }


@dataclass
class RankingResult:
    """Result of pattern ranking."""
    dominant: Optional[RankedPattern]
    alternatives: List[RankedPattern]
    rejected: List[Dict]  # Patterns below threshold with reasons
    conflict: Optional[str]  # If there's bullish/bearish conflict
    tradeable: bool
    
    def to_dict(self) -> Dict:
        return {
            "dominant": self.dominant.to_dict() if self.dominant else None,
            "alternatives": [a.to_dict() for a in self.alternatives],
            "rejected_count": len(self.rejected),
            "rejected": self.rejected[:3],  # Only first 3 for brevity
            "conflict": self.conflict,
            "tradeable": self.tradeable,
        }


class FamilyRanking:
    """
    Ranks and selects patterns from all families.
    
    CRITICAL FIX:
    - confidence = DOMINANCE over others, NOT pattern quality
    - NEVER show 100% (max 0.92)
    - Triangle = compression state, not directional signal
    
    Config:
    - min_confidence: minimum confidence to be considered
    - conflict_threshold: score difference to declare conflict
    - max_alternatives: how many alternatives to return
    """
    
    def __init__(self, config: Dict = None):
        config = config or {}
        
        self.min_confidence = config.get("min_confidence", 0.4)
        self.conflict_score_diff = config.get("conflict_score_diff", 0.10)  # 10% difference
        self.clear_score_diff = config.get("clear_score_diff", 0.25)        # 25% for CLEAR
        self.max_alternatives = config.get("max_alternatives", 2)
        self.max_confidence = 0.92  # NEVER show 100%
    
    def rank(
        self,
        candidates: List[Dict],  # Pattern dicts from family detectors
        candles: List[Dict] = None,  # Candles for window validation
        swings: List[Dict] = None,   # Swings for noise filter
        active_range: Dict = None,   # Active range for conflict
        timeframe: str = "4H",       # Timeframe for window limits
    ) -> RankingResult:
        """
        Rank all pattern candidates.
        
        CRITICAL FLOW:
        1. Validate each pattern window (NEW!)
        2. Filter by minimum confidence
        3. Compute dominance confidence
        4. Detect conflicts
        5. Return ranked result
        
        Args:
            candidates: List of pattern dicts, each must have:
                - type: pattern name
                - family: family name
                - bias: bullish/bearish/neutral
                - confidence: 0-1 (pattern quality)
            candles: OHLCV candles for window validation
            swings: Pre-computed swings
            active_range: Active range if exists
            timeframe: Current timeframe
        
        Returns:
            RankingResult with dominant, alternatives, rejected
        """
        if not candidates:
            return RankingResult(
                dominant=None,
                alternatives=[],
                rejected=[],
                conflict=None,
                tradeable=False,
            )
        
        # ═══════════════════════════════════════════════════════════════
        # STEP 1: WINDOW VALIDATION (CRITICAL NEW STEP)
        # ═══════════════════════════════════════════════════════════════
        validated = []
        rejected = []
        
        for c in candidates:
            # Skip window validation if no candles provided
            if candles is None:
                validated.append(c)
                continue
            
            # Validate pattern window
            is_valid, reason, penalty = validate_pattern_window(
                pattern=c,
                candles=candles,
                swings=swings,
                active_range=active_range,
                timeframe=timeframe
            )
            
            if not is_valid:
                rejected.append({
                    "type": c.get("type"),
                    "confidence": c.get("confidence", 0),
                    "reason": f"window_validation_failed: {reason}"
                })
                continue
            
            # Apply score penalty if any
            if penalty > 0:
                c["confidence"] = max(0.1, c.get("confidence", 0) - penalty)
                c["window_penalty"] = penalty
            
            validated.append(c)
        
        # ═══════════════════════════════════════════════════════════════
        # STEP 2: LIFECYCLE SCORE ADJUSTMENT (CRITICAL)
        # confirmed → boost, invalidated → heavy penalty
        # ═══════════════════════════════════════════════════════════════
        for c in validated:
            lc_state = c.get("lifecycle", "forming")
            conf = c.get("confidence", 0)
            
            if lc_state in ("confirmed_up", "confirmed_down"):
                # Confirmed patterns get a significant boost
                c["confidence"] = min(conf + 0.20, 0.95)
                c["lifecycle_boost"] = 0.20
            elif lc_state == "invalidated":
                # Invalidated patterns get crushed
                c["confidence"] = max(conf - 0.50, 0.05)
                c["lifecycle_penalty"] = -0.50
                c["tradeable"] = False
                c["visibility"] = "ghost"
        
        # ═══════════════════════════════════════════════════════════════
        # STEP 3: CONFIDENCE FILTER
        # ═══════════════════════════════════════════════════════════════
        valid = []
        
        for c in validated:
            conf = c.get("confidence", 0)
            if conf >= self.min_confidence:
                valid.append(c)
            else:
                rejected.append({
                    "type": c.get("type"),
                    "confidence": conf,
                    "reason": f"below_threshold ({conf:.2f} < {self.min_confidence})"
                })
        
        if not valid:
            return RankingResult(
                dominant=None,
                alternatives=[],
                rejected=rejected,
                conflict=None,
                tradeable=False,
            )
        
        # Sort by confidence (pattern quality)
        valid.sort(key=lambda x: x.get("confidence", 0), reverse=True)
        
        # CRITICAL: Calculate REAL confidence (dominance over others)
        real_confidences = self._compute_dominance_confidence(valid)
        
        # Check for conflicts
        conflict = self._detect_conflict_v2(valid, real_confidences)
        
        # Determine confidence state
        confidence_state = self._compute_confidence_state(valid, real_confidences, conflict)
        
        # Build ranked patterns with REAL confidence
        ranked = []
        for i, c in enumerate(valid):
            # Clamp confidence - NEVER 100%
            real_conf = min(real_confidences[i], self.max_confidence)
            
            ranked.append(RankedPattern(
                type=c.get("type"),
                family=PatternFamily(c.get("family", "horizontal")),
                bias=PatternBias(c.get("bias", "neutral")),
                confidence=real_conf,  # Use REAL confidence, not pattern quality
                rank=i + 1,
                pattern_data={
                    **c,
                    "pattern_quality": c.get("confidence", 0),  # Original
                    "dominance_confidence": real_conf,          # Real
                },
            ))
        
        # Dominant is first (highest confidence)
        dominant = ranked[0] if ranked else None
        
        # Alternatives are next N
        alternatives = ranked[1:self.max_alternatives + 1] if len(ranked) > 1 else []
        
        # Tradeable only if CLEAR and directional
        tradeable = self._is_tradeable_v2(dominant, alternatives, conflict, confidence_state)
        
        return RankingResult(
            dominant=dominant,
            alternatives=alternatives,
            rejected=rejected,
            conflict=conflict,
            tradeable=tradeable,
        )
    
    def _compute_dominance_confidence(self, patterns: List[Dict]) -> List[float]:
        """
        Compute REAL confidence = dominance over other patterns.
        
        NOT pattern quality, but how much stronger than competition.
        """
        if len(patterns) == 0:
            return []
        
        if len(patterns) == 1:
            # Single pattern - moderate confidence
            return [0.7]
        
        confidences = []
        scores = [p.get("confidence", 0) for p in patterns]
        top_score = scores[0]
        
        for i, score in enumerate(scores):
            if i == 0:
                # Dominant: confidence based on gap to second
                second_score = scores[1] if len(scores) > 1 else 0
                gap = top_score - second_score
                
                # Normalize gap: 0.3 gap = 0.9 confidence, 0 gap = 0.3 confidence
                dominance = 0.3 + (gap * 2.0)  # Scale gap
                dominance = min(max(dominance, 0.2), self.max_confidence)
                confidences.append(dominance)
            else:
                # Alternatives: proportional to how close to dominant
                ratio = score / top_score if top_score > 0 else 0
                alt_confidence = ratio * 0.7  # Max 70% for alternatives
                confidences.append(min(alt_confidence, 0.7))
        
        return confidences
    
    def _detect_conflict_v2(
        self, 
        patterns: List[Dict],
        real_confidences: List[float]
    ) -> Optional[str]:
        """
        Detect if there's a bullish/bearish conflict.
        
        CRITICAL: Small gap between top patterns = CONFLICTED
        """
        if len(patterns) < 2:
            return None
        
        top = patterns[0]
        second = patterns[1]
        
        bias1 = top.get("bias", "neutral")
        bias2 = second.get("bias", "neutral")
        
        score1 = top.get("confidence", 0)
        score2 = second.get("confidence", 0)
        gap = score1 - score2
        
        # Case 1: Both high confidence, different biases
        if bias1 != "neutral" and bias2 != "neutral" and bias1 != bias2:
            if gap < self.clear_score_diff:
                return f"directional_conflict: {top.get('type')} ({bias1}) vs {second.get('type')} ({bias2}), gap={gap:.2f}"
        
        # Case 2: Dominant is neutral (compression) but has directional rivals
        if bias1 == "neutral" and bias2 != "neutral":
            # Triangle vs Double Bottom/Top = conflicted
            if gap < self.clear_score_diff:
                return f"neutral_vs_directional: {top.get('type')} (wait) vs {second.get('type')} ({bias2})"
        
        # Case 3: Very close scores regardless of bias
        if gap < self.conflict_score_diff:
            return f"close_competition: {top.get('type')} vs {second.get('type')}, gap={gap:.2f}"
        
        return None
    
    def _compute_confidence_state(
        self,
        patterns: List[Dict],
        real_confidences: List[float],
        conflict: Optional[str]
    ) -> str:
        """
        Compute overall confidence state.
        
        CLEAR: Strong dominance, no conflict, directional
        WEAK: Pattern found but low dominance
        CONFLICTED: Multiple competing signals
        COMPRESSION: Dominant is neutral (triangle/range)
        NONE: No valid pattern
        """
        if not patterns:
            return "NONE"
        
        if conflict:
            return "CONFLICTED"
        
        top = patterns[0]
        top_conf = real_confidences[0] if real_confidences else 0
        bias = top.get("bias", "neutral")
        
        # Neutral patterns (triangle, range) = COMPRESSION state
        if bias == "neutral":
            return "COMPRESSION"
        
        # Check dominance
        if len(patterns) >= 2:
            gap = patterns[0].get("confidence", 0) - patterns[1].get("confidence", 0)
            if gap >= self.clear_score_diff and top_conf >= 0.6:
                return "CLEAR"
            elif gap >= self.conflict_score_diff:
                return "WEAK"
            else:
                return "CONFLICTED"
        
        # Single pattern
        if top_conf >= 0.6:
            return "CLEAR"
        
        return "WEAK"
    
    def _detect_conflict(self, patterns: List[Dict]) -> Optional[str]:
        """DEPRECATED - use _detect_conflict_v2"""
        return self._detect_conflict_v2(patterns, [p.get("confidence", 0) for p in patterns])
    
    def _is_tradeable(
        self,
        dominant: Optional[RankedPattern],
        alternatives: List[RankedPattern],
        conflict: Optional[str]
    ) -> bool:
        """DEPRECATED - use _is_tradeable_v2"""
        return self._is_tradeable_v2(dominant, alternatives, conflict, "WEAK")
    
    def _is_tradeable_v2(
        self,
        dominant: Optional[RankedPattern],
        alternatives: List[RankedPattern],
        conflict: Optional[str],
        confidence_state: str
    ) -> bool:
        """
        Determine if the pattern setup is tradeable.
        
        CRITICAL RULES:
        - CONFLICTED = NOT tradeable
        - COMPRESSION (triangle/range) = NOT immediately tradeable (wait for breakout)
        - WEAK = tradeable with reduced size
        - CLEAR = fully tradeable
        """
        if not dominant:
            return False
        
        # Conflict = not tradeable
        if conflict:
            return False
        
        # COMPRESSION state (neutral patterns) = not immediately tradeable
        if confidence_state == "COMPRESSION":
            return False  # Wait for breakout
        
        # CONFLICTED = not tradeable
        if confidence_state == "CONFLICTED":
            return False
        
        # CLEAR with good confidence = tradeable
        if confidence_state == "CLEAR" and dominant.confidence >= 0.5:
            return True
        
        # WEAK can be tradeable with good confidence
        if confidence_state == "WEAK" and dominant.confidence >= 0.6:
            return True
        
        return False


# Singleton
_family_ranking = None

def get_family_ranking(config: Dict = None) -> FamilyRanking:
    global _family_ranking
    if _family_ranking is None or config:
        _family_ranking = FamilyRanking(config)
    return _family_ranking
