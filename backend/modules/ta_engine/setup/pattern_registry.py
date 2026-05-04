"""
Pattern Registry
=================

CORE PRINCIPLE: All available pattern detectors must participate in analysis.

Not: "user asked for double top → we add double top"
But: "entire available pattern set enters candidate pool automatically"

Pipeline:
    all_detectors → all_candidates → validation → expiration → ranking → best selection → output

This registry ensures:
1. Every detector returns unified PatternCandidate format
2. All detectors are called in unified pipeline
3. No pattern type gets unfair advantage
"""

from typing import List, Callable, Dict, Any, Optional
from dataclasses import dataclass
from .pattern_candidate import PatternCandidate


# =============================================================================
# REGISTRY
# =============================================================================

PATTERN_REGISTRY: List[Callable] = []


def register_pattern(detector_fn: Callable):
    """Register a pattern detector function."""
    if detector_fn not in PATTERN_REGISTRY:
        PATTERN_REGISTRY.append(detector_fn)
    return detector_fn


def get_all_detectors() -> List[Callable]:
    """Get all registered pattern detectors."""
    return PATTERN_REGISTRY.copy()


# =============================================================================
# UNIFIED ADAPTER - converts any pattern format to PatternCandidate
# =============================================================================

def adapt_to_candidate(raw_pattern: Dict, pattern_type: str = None) -> Optional[PatternCandidate]:
    """
    Convert any raw pattern dict to unified PatternCandidate.
    
    This adapter ensures all detectors can participate regardless
    of their original return format.
    """
    if not raw_pattern:
        return None
    
    # Determine type
    p_type = pattern_type or raw_pattern.get("type", "unknown")
    
    # Handle different possible field names
    direction = raw_pattern.get("direction", "neutral")
    if isinstance(direction, str):
        direction = direction.lower()
    else:
        direction = direction.value if hasattr(direction, 'value') else "neutral"
    
    # Confidence/score
    confidence = raw_pattern.get("confidence", 0.5)
    if isinstance(confidence, (int, float)):
        confidence = float(confidence)
    else:
        confidence = 0.5
    
    # Points extraction
    points = raw_pattern.get("points", {})
    anchor_points = raw_pattern.get("anchor_points", {})
    
    # Index info
    start_index = raw_pattern.get("start_index", 0)
    end_index = raw_pattern.get("end_index", 0)
    last_touch_index = raw_pattern.get("last_touch_index", end_index)
    
    # Calculate geometry score from available data
    geometry_score = confidence
    if raw_pattern.get("line_scores"):
        line_vals = list(raw_pattern["line_scores"].values())
        if line_vals:
            avg_line = sum(line_vals) / len(line_vals)
            geometry_score = (confidence + min(1.0, avg_line / 20)) / 2
    
    return PatternCandidate(
        type=p_type,
        direction=direction,
        confidence=confidence,
        geometry_score=geometry_score,
        touch_count=raw_pattern.get("touches", raw_pattern.get("touch_count", 0)),
        containment=raw_pattern.get("containment", 0.0),
        line_scores=raw_pattern.get("line_scores", {}),
        points=points,
        anchor_points=anchor_points,
        start_index=start_index,
        end_index=end_index,
        last_touch_index=last_touch_index,
        breakout_level=raw_pattern.get("breakout_level"),
        invalidation=raw_pattern.get("invalidation"),
    )


def adapt_detected_pattern(detected_pattern) -> Optional[PatternCandidate]:
    """
    Adapt DetectedPattern (from pattern_detector.py) to PatternCandidate.
    """
    if not detected_pattern:
        return None
    
    # Get type as string
    p_type = detected_pattern.pattern_type.value if hasattr(detected_pattern.pattern_type, 'value') else str(detected_pattern.pattern_type)
    direction = detected_pattern.direction.value if hasattr(detected_pattern.direction, 'value') else str(detected_pattern.direction)
    
    # Convert points
    points = {}
    if detected_pattern.points:
        points = detected_pattern.points if isinstance(detected_pattern.points, dict) else {"points": detected_pattern.points}
    
    return PatternCandidate(
        type=p_type,
        direction=direction,
        confidence=detected_pattern.confidence,
        geometry_score=detected_pattern.confidence,
        touch_count=len(detected_pattern.points) if detected_pattern.points else 0,
        containment=0.8,  # Default for validated patterns
        line_scores={},
        points=points,
        anchor_points={},
        start_index=0,
        end_index=0,
        last_touch_index=0,
        breakout_level=detected_pattern.breakout_level,
        invalidation=detected_pattern.invalidation,
    )


# =============================================================================
# VALIDATION FILTER
# =============================================================================

def validate_candidate(candidate: PatternCandidate) -> bool:
    """
    Hard validation: reject garbage patterns.
    
    HARDENED RULES:
    - Minimum 4 touches (was 2)
    - Containment >= 0.6 (was 0.5)
    - Geometry >= 0.4 (was 0.35)
    - Confidence >= 0.55 (was 0.4)
    
    EXCEPTION: Active Range from Range Regime Engine V2
    - Active ranges have different validation (is_active=True)
    """
    # Special case: Active Range from Range Regime Engine V2
    # These have their own validation in the engine
    if candidate.type.lower() == "range" and getattr(candidate, 'is_active', None) == True:
        # Range Regime Engine V2 has its own validation
        # Just check confidence
        return candidate.confidence >= 0.5
    
    if candidate.touch_count < 4:
        return False
    
    if candidate.containment < 0.6:
        return False
    
    if candidate.geometry_score < 0.4:
        return False
    
    if candidate.confidence < 0.55:
        return False
    
    return True


# =============================================================================
# STRUCTURE GATING V2 — HARD REJECTION by market regime
# =============================================================================

def structure_gate_single(candidate: PatternCandidate, regime: str, phase: str) -> bool:
    """
    Hard gate: return True if pattern is ALLOWED in current regime.
    
    Rules from TA spec:
    - triangle → compression, reversal_candidate, range
    - wedge → trend_down, trend_up, reversal_candidate
    - head_shoulders → distribution, range, reversal_candidate
    - inverse_head_shoulders → accumulation, range, reversal_candidate
    - range → range
    - channel → trend_up, trend_down
    """
    c_type = candidate.type.lower()
    
    if "triangle" in c_type:
        return regime in ["compression", "reversal_candidate", "range"]
    
    if "wedge" in c_type:
        if "falling" in c_type:
            return regime in ["trend_down", "reversal_candidate", "compression"]
        if "rising" in c_type:
            return regime in ["trend_up", "reversal_candidate", "compression"]
        return regime in ["trend_down", "trend_up", "reversal_candidate", "compression"]
    
    if c_type == "head_shoulders":
        return phase in ["distribution", "range"] or regime == "reversal_candidate"
    
    if c_type == "inverse_head_shoulders":
        return phase in ["accumulation", "range"] or regime == "reversal_candidate"
    
    if c_type == "range":
        # Active Range (from Range Regime Engine V2) allowed in many regimes
        # because range IS the regime - it defines the market state
        if getattr(candidate, 'is_active', None) == True:
            # Active range allowed almost everywhere (it's a market regime)
            return regime not in ["expansion", "strong_trend"]
        return regime in ["range", "accumulation", "distribution", "compression", "sideways"]
    
    if "channel" in c_type:
        return regime in ["trend_up", "trend_down", "expansion", "range"]
    
    # Expansion regime — channels and continuation patterns allowed
    if regime == "expansion":
        if "channel" in c_type or "flag" in c_type or "pennant" in c_type:
            return True
        return False
    
    # Unknown pattern type — allow but penalize
    return True


def filter_by_structure(candidates: List[PatternCandidate], structure_ctx) -> List[PatternCandidate]:
    """
    STRUCTURE GATING V2: Hard rejection + penalties.
    
    If structure does not support pattern → REJECT (not just penalize).
    """
    if not structure_ctx:
        return candidates
    
    regime = structure_ctx.regime
    phase = getattr(structure_ctx, 'market_phase', regime)  # v2 has market_phase
    bias = structure_ctx.bias
    filtered = []
    
    for c in candidates:
        # Hard gate — reject if structure doesn't support pattern
        allowed = structure_gate_single(c, regime, phase)
        if not allowed:
            print(f"[Pattern] REJECTED: {c.type} (regime={regime}, phase={phase})")
            continue
        
        print(f"[Pattern] ALLOWED: {c.type} (regime={regime})")
        
        # Soft penalties for counter-trend patterns
        if regime == "trend_up" and c.direction == "bearish":
            c.geometry_score *= 0.6  # Heavy penalty
            c.confidence *= 0.7
        
        if regime == "trend_down" and c.direction == "bullish":
            c.geometry_score *= 0.6
            c.confidence *= 0.7
        
        # Bonus for regime-aligned patterns
        if regime == "compression" and "triangle" in c.type.lower():
            c.geometry_score *= 1.1
        
        if regime == "range" and c.type.lower() == "range":
            c.geometry_score *= 1.15
        
        filtered.append(c)
    
    return filtered


# =============================================================================
# ANTI-OVERFIT: Penalize dominant pattern types
# =============================================================================

def penalize_overused_patterns(candidates: List[PatternCandidate]) -> List[PatternCandidate]:
    """
    Prevent one pattern type from dominating.
    
    If system finds too many triangles, penalize them so other
    patterns have fair chance.
    """
    if not candidates:
        return candidates
    
    # Count by base type
    type_count = {}
    for c in candidates:
        base_type = c.type.split("_")[0].lower()  # "symmetrical_triangle" → "symmetrical"
        type_count[base_type] = type_count.get(base_type, 0) + 1
    
    # Penalize if one type has > 40% share
    total = len(candidates)
    for c in candidates:
        base_type = c.type.split("_")[0].lower()
        share = type_count[base_type] / total
        
        if share > 0.4:
            penalty = 0.9 - (share - 0.4) * 0.5  # Max penalty ~0.7
            c.total_score *= max(0.7, penalty)
    
    return candidates


# =============================================================================
# UNIFIED DETECTION PIPELINE
# =============================================================================

def run_all_detectors(
    candles: List[Dict],
    pivots_high: List = None,
    pivots_low: List = None,
    levels: List[Dict] = None,
    structure_ctx = None,
    timeframe: str = "1D",
    config: Dict = None
) -> List[PatternCandidate]:
    """
    Run ALL registered detectors and collect candidates.
    
    This is the core function that ensures full pattern coverage.
    """
    all_candidates = []
    
    for detector in PATTERN_REGISTRY:
        try:
            # Try calling detector with all possible args
            results = detector(
                candles=candles,
                pivots_high=pivots_high,
                pivots_low=pivots_low,
                levels=levels,
                structure_ctx=structure_ctx,
                timeframe=timeframe,
                config=config or {}
            )
            
            if results:
                if isinstance(results, list):
                    all_candidates.extend(results)
                else:
                    all_candidates.append(results)
                    
        except TypeError:
            # Detector might have different signature - try simpler call
            try:
                results = detector(candles, config or {})
                if results:
                    if isinstance(results, list):
                        all_candidates.extend(results)
                    else:
                        all_candidates.append(results)
            except Exception:
                continue  # Fail-safe: detector error doesn't break pipeline
        except Exception:
            continue
    
    return all_candidates


# Singleton registry instance reference
pattern_registry = PATTERN_REGISTRY
