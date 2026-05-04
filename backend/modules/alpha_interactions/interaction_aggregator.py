"""
PHASE 16.6 — Interaction Aggregator
====================================
Final aggregation layer for Alpha Interaction signals.

Purpose:
    Combine outputs from Reinforcement, Conflict, Synergy, and Cancellation engines
    into a unified interaction assessment with modifiers for downstream use.

Key Principles:
    1. Aggregator NEVER changes direction (only TAHypothesis/TradingDecision set direction)
    2. Aggregator modifies only: confidence, size, execution aggressiveness
    3. Cancellation has priority: cancellation_strength > 0.7 → CRITICAL state
    4. Execution modifier is a RECOMMENDATION, not a direct mode change

Formula:
    interaction_score = 
        + 0.30 * reinforcement_strength
        + 0.25 * synergy_strength
        - 0.25 * conflict_strength
        - 0.20 * cancellation_strength

    Hard Override:
        if cancellation_strength > 0.7:
            interaction_state = "CRITICAL"

State Thresholds:
    > 0.50      → STRONG_POSITIVE
    0.20–0.50   → POSITIVE
    -0.20–0.20  → NEUTRAL
    -0.50–-0.20 → NEGATIVE
    < -0.50     → CRITICAL

Modifiers by State:
    State            Confidence  Size    Execution
    STRONG_POSITIVE  1.12        1.10    BOOST
    POSITIVE         1.05        1.03    NORMAL
    NEUTRAL          1.00        1.00    NORMAL
    NEGATIVE         0.88        0.85    CAUTION
    CRITICAL         0.70        0.65    RESTRICT
"""

import os
import sys
from pathlib import Path
from typing import Dict, Optional, Any, List
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# MongoDB
from pymongo import MongoClient

MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.environ.get("DB_NAME", "ta_engine")


# ══════════════════════════════════════════════════════════════
# INTERACTION STATE ENUM (Extended for Aggregator)
# ══════════════════════════════════════════════════════════════

class AggregateInteractionState(str, Enum):
    """Aggregate interaction state classification."""
    STRONG_POSITIVE = "STRONG_POSITIVE"  # Strong reinforcement/synergy
    POSITIVE = "POSITIVE"                 # Moderate positive interaction
    NEUTRAL = "NEUTRAL"                   # Balanced or no interaction
    NEGATIVE = "NEGATIVE"                 # Moderate conflict
    CRITICAL = "CRITICAL"                 # Strong conflict or cancellation


class ExecutionModifier(str, Enum):
    """Execution aggressiveness modifier (recommendation only)."""
    BOOST = "BOOST"       # Can increase aggressiveness
    NORMAL = "NORMAL"     # No change
    CAUTION = "CAUTION"   # Decrease aggressiveness
    RESTRICT = "RESTRICT" # Forbid aggressive execution


# ══════════════════════════════════════════════════════════════
# AGGREGATION WEIGHTS
# ══════════════════════════════════════════════════════════════

AGGREGATION_WEIGHTS = {
    "reinforcement": 0.30,
    "synergy": 0.25,
    "conflict": -0.25,
    "cancellation": -0.20,
}

# ══════════════════════════════════════════════════════════════
# STATE THRESHOLDS
# ══════════════════════════════════════════════════════════════

STATE_THRESHOLDS = {
    "strong_positive_min": 0.50,
    "positive_min": 0.20,
    "neutral_min": -0.20,
    "negative_min": -0.50,
    # Below negative_min = CRITICAL
}

# ══════════════════════════════════════════════════════════════
# CANCELLATION OVERRIDE THRESHOLD
# ══════════════════════════════════════════════════════════════

CANCELLATION_OVERRIDE_THRESHOLD = 0.7  # If cancellation > 0.7 → CRITICAL

# ══════════════════════════════════════════════════════════════
# MODIFIERS BY STATE
# ══════════════════════════════════════════════════════════════

STATE_MODIFIERS = {
    AggregateInteractionState.STRONG_POSITIVE: {
        "confidence_modifier": 1.12,
        "size_modifier": 1.10,
        "execution_modifier": ExecutionModifier.BOOST,
    },
    AggregateInteractionState.POSITIVE: {
        "confidence_modifier": 1.05,
        "size_modifier": 1.03,
        "execution_modifier": ExecutionModifier.NORMAL,
    },
    AggregateInteractionState.NEUTRAL: {
        "confidence_modifier": 1.00,
        "size_modifier": 1.00,
        "execution_modifier": ExecutionModifier.NORMAL,
    },
    AggregateInteractionState.NEGATIVE: {
        "confidence_modifier": 0.88,
        "size_modifier": 0.85,
        "execution_modifier": ExecutionModifier.CAUTION,
    },
    AggregateInteractionState.CRITICAL: {
        "confidence_modifier": 0.70,
        "size_modifier": 0.65,
        "execution_modifier": ExecutionModifier.RESTRICT,
    },
}


# ══════════════════════════════════════════════════════════════
# AGGREGATE CONTRACT
# ══════════════════════════════════════════════════════════════

@dataclass
class AlphaInteractionAggregate:
    """
    Final aggregation output from Interaction Layer.
    
    This is the single source of truth for all interaction effects
    on trading decisions.
    
    Key Principle:
        - Does NOT change direction (direction is from TA/Decision)
        - Only modifies confidence, size, and execution aggressiveness
    """
    symbol: str
    timestamp: datetime
    
    # Input strengths (0..1)
    reinforcement_strength: float
    conflict_strength: float
    synergy_strength: float
    cancellation_strength: float
    
    # Calculated outputs
    interaction_score: float  # -1 to +1
    interaction_state: AggregateInteractionState
    
    # Modifiers for downstream use
    confidence_modifier: float  # 0.70 to 1.12
    size_modifier: float        # 0.65 to 1.10
    execution_modifier: ExecutionModifier  # BOOST / NORMAL / CAUTION / RESTRICT
    
    # Explainability
    strongest_force: str        # reinforcement / synergy / conflict / cancellation
    weakest_force: str          # reinforcement / synergy / conflict / cancellation
    drivers: Dict[str, Any] = field(default_factory=dict)
    
    # Override flags
    cancellation_override: bool = False  # True if cancellation forced CRITICAL
    
    def to_dict(self) -> Dict:
        return {
            "symbol": self.symbol,
            "timestamp": self.timestamp.isoformat(),
            "reinforcement_strength": round(self.reinforcement_strength, 4),
            "conflict_strength": round(self.conflict_strength, 4),
            "synergy_strength": round(self.synergy_strength, 4),
            "cancellation_strength": round(self.cancellation_strength, 4),
            "interaction_score": round(self.interaction_score, 4),
            "interaction_state": self.interaction_state.value,
            "confidence_modifier": round(self.confidence_modifier, 4),
            "size_modifier": round(self.size_modifier, 4),
            "execution_modifier": self.execution_modifier.value,
            "strongest_force": self.strongest_force,
            "weakest_force": self.weakest_force,
            "cancellation_override": self.cancellation_override,
            "drivers": self.drivers,
        }
    
    def to_snapshot(self) -> Dict:
        """
        Compact snapshot for Trading Product integration.
        """
        return {
            "state": self.interaction_state.value,
            "score": round(self.interaction_score, 4),
            "strongest_force": self.strongest_force,
            "confidence_modifier": round(self.confidence_modifier, 4),
            "size_modifier": round(self.size_modifier, 4),
            "execution_modifier": self.execution_modifier.value,
        }


# ══════════════════════════════════════════════════════════════
# INTERACTION AGGREGATOR ENGINE
# ══════════════════════════════════════════════════════════════

class InteractionAggregator:
    """
    Interaction Aggregator — PHASE 16.6
    
    Combines outputs from all interaction sub-engines into
    a single unified assessment with modifiers.
    
    Input Sources:
        - Reinforcement Patterns Engine (reinforcement_strength)
        - Conflict Patterns Engine (conflict_strength)
        - Synergy Engine (synergy_strength)
        - Cancellation Engine (cancellation_strength)
    
    Output:
        AlphaInteractionAggregate with unified modifiers.
    
    Key Principles:
        1. Never changes direction
        2. Cancellation > 0.7 forces CRITICAL state
        3. Execution modifier is a recommendation only
    """
    
    def __init__(self):
        self.client = MongoClient(MONGO_URL)
        self.db = self.client[DB_NAME]
        
        # Lazy load sub-engines
        self._reinforcement_engine = None
        self._conflict_engine = None
        self._synergy_engine = None
        self._cancellation_engine = None
    
    # ═══════════════════════════════════════════════════════════
    # LAZY LOADERS
    # ═══════════════════════════════════════════════════════════
    
    @property
    def reinforcement_engine(self):
        if self._reinforcement_engine is None:
            try:
                from modules.alpha_interactions.reinforcement_patterns_engine import get_reinforcement_patterns_engine
                self._reinforcement_engine = get_reinforcement_patterns_engine()
            except ImportError:
                pass
        return self._reinforcement_engine
    
    @property
    def conflict_engine(self):
        if self._conflict_engine is None:
            try:
                from modules.alpha_interactions.conflict_patterns_engine import get_conflict_patterns_engine
                self._conflict_engine = get_conflict_patterns_engine()
            except ImportError:
                pass
        return self._conflict_engine
    
    @property
    def synergy_engine(self):
        if self._synergy_engine is None:
            try:
                from modules.alpha_interactions.synergy_engine import get_synergy_engine
                self._synergy_engine = get_synergy_engine()
            except ImportError:
                pass
        return self._synergy_engine
    
    @property
    def cancellation_engine(self):
        if self._cancellation_engine is None:
            try:
                from modules.alpha_interactions.cancellation_engine import get_cancellation_engine
                self._cancellation_engine = get_cancellation_engine()
            except ImportError:
                pass
        return self._cancellation_engine
    
    # ═══════════════════════════════════════════════════════════
    # MAIN AGGREGATION
    # ═══════════════════════════════════════════════════════════
    
    def aggregate(self, symbol: str) -> AlphaInteractionAggregate:
        """
        Aggregate all interaction signals for a symbol.
        
        Args:
            symbol: Trading pair (BTC, ETH, SOL)
        
        Returns:
            AlphaInteractionAggregate with unified modifiers
        """
        now = datetime.now(timezone.utc)
        
        # Gather strengths from sub-engines
        reinforcement_data = self._get_reinforcement_strength(symbol)
        conflict_data = self._get_conflict_strength(symbol)
        synergy_data = self._get_synergy_strength(symbol)
        cancellation_data = self._get_cancellation_strength(symbol)
        
        reinforcement_strength = reinforcement_data.get("pattern_reinforcement_strength", 0.0)
        conflict_strength = conflict_data.get("pattern_conflict_strength", 0.0)
        synergy_strength = synergy_data.get("synergy_strength", 0.0)
        cancellation_strength = cancellation_data.get("cancellation_strength", 0.0)
        
        # Calculate interaction score using weighted formula
        interaction_score = self._calculate_interaction_score(
            reinforcement_strength,
            conflict_strength,
            synergy_strength,
            cancellation_strength,
        )
        
        # Determine interaction state (with cancellation override)
        interaction_state, cancellation_override = self._determine_state(
            interaction_score, cancellation_strength
        )
        
        # Get modifiers based on state
        modifiers = STATE_MODIFIERS[interaction_state]
        confidence_modifier = modifiers["confidence_modifier"]
        size_modifier = modifiers["size_modifier"]
        execution_modifier = modifiers["execution_modifier"]
        
        # Determine strongest and weakest forces
        strongest_force, weakest_force = self._determine_force_ranking(
            reinforcement_strength,
            conflict_strength,
            synergy_strength,
            cancellation_strength,
        )
        
        # Build drivers
        drivers = self._build_drivers(
            reinforcement_data, conflict_data, synergy_data, cancellation_data,
            interaction_score, interaction_state,
        )
        
        return AlphaInteractionAggregate(
            symbol=symbol,
            timestamp=now,
            reinforcement_strength=reinforcement_strength,
            conflict_strength=conflict_strength,
            synergy_strength=synergy_strength,
            cancellation_strength=cancellation_strength,
            interaction_score=interaction_score,
            interaction_state=interaction_state,
            confidence_modifier=confidence_modifier,
            size_modifier=size_modifier,
            execution_modifier=execution_modifier,
            strongest_force=strongest_force,
            weakest_force=weakest_force,
            cancellation_override=cancellation_override,
            drivers=drivers,
        )
    
    def aggregate_from_inputs(
        self,
        symbol: str,
        reinforcement_strength: float,
        conflict_strength: float,
        synergy_strength: float,
        cancellation_strength: float,
    ) -> AlphaInteractionAggregate:
        """
        Aggregate with provided inputs (for testing).
        """
        now = datetime.now(timezone.utc)
        
        # Calculate interaction score
        interaction_score = self._calculate_interaction_score(
            reinforcement_strength,
            conflict_strength,
            synergy_strength,
            cancellation_strength,
        )
        
        # Determine state
        interaction_state, cancellation_override = self._determine_state(
            interaction_score, cancellation_strength
        )
        
        # Get modifiers
        modifiers = STATE_MODIFIERS[interaction_state]
        confidence_modifier = modifiers["confidence_modifier"]
        size_modifier = modifiers["size_modifier"]
        execution_modifier = modifiers["execution_modifier"]
        
        # Force ranking
        strongest_force, weakest_force = self._determine_force_ranking(
            reinforcement_strength,
            conflict_strength,
            synergy_strength,
            cancellation_strength,
        )
        
        # Basic drivers
        drivers = {
            "reinforcement_contribution": round(reinforcement_strength * AGGREGATION_WEIGHTS["reinforcement"], 4),
            "synergy_contribution": round(synergy_strength * AGGREGATION_WEIGHTS["synergy"], 4),
            "conflict_contribution": round(conflict_strength * abs(AGGREGATION_WEIGHTS["conflict"]), 4),
            "cancellation_contribution": round(cancellation_strength * abs(AGGREGATION_WEIGHTS["cancellation"]), 4),
        }
        
        return AlphaInteractionAggregate(
            symbol=symbol,
            timestamp=now,
            reinforcement_strength=reinforcement_strength,
            conflict_strength=conflict_strength,
            synergy_strength=synergy_strength,
            cancellation_strength=cancellation_strength,
            interaction_score=interaction_score,
            interaction_state=interaction_state,
            confidence_modifier=confidence_modifier,
            size_modifier=size_modifier,
            execution_modifier=execution_modifier,
            strongest_force=strongest_force,
            weakest_force=weakest_force,
            cancellation_override=cancellation_override,
            drivers=drivers,
        )
    
    # ═══════════════════════════════════════════════════════════
    # STRENGTH GETTERS
    # ═══════════════════════════════════════════════════════════
    
    def _get_reinforcement_strength(self, symbol: str) -> Dict[str, Any]:
        """Get reinforcement strength from engine."""
        if self.reinforcement_engine is None:
            return {"pattern_reinforcement_strength": 0.0, "patterns_detected": []}
        
        try:
            return self.reinforcement_engine.get_pattern_strength_for_interaction(symbol)
        except Exception:
            return {"pattern_reinforcement_strength": 0.0, "patterns_detected": []}
    
    def _get_conflict_strength(self, symbol: str) -> Dict[str, Any]:
        """Get conflict strength from engine."""
        if self.conflict_engine is None:
            return {"pattern_conflict_strength": 0.0, "conflict_patterns": []}
        
        try:
            return self.conflict_engine.get_conflict_strength_for_interaction(symbol)
        except Exception:
            return {"pattern_conflict_strength": 0.0, "conflict_patterns": []}
    
    def _get_synergy_strength(self, symbol: str) -> Dict[str, Any]:
        """Get synergy strength from engine."""
        if self.synergy_engine is None:
            return {"synergy_strength": 0.0, "synergy_patterns": []}
        
        try:
            return self.synergy_engine.get_synergy_strength_for_interaction(symbol)
        except Exception:
            return {"synergy_strength": 0.0, "synergy_patterns": []}
    
    def _get_cancellation_strength(self, symbol: str) -> Dict[str, Any]:
        """Get cancellation strength from engine."""
        if self.cancellation_engine is None:
            return {"cancellation_strength": 0.0, "cancellation_patterns": [], "trade_cancelled": False}
        
        try:
            return self.cancellation_engine.get_cancellation_for_interaction(symbol)
        except Exception:
            return {"cancellation_strength": 0.0, "cancellation_patterns": [], "trade_cancelled": False}
    
    # ═══════════════════════════════════════════════════════════
    # CALCULATION METHODS
    # ═══════════════════════════════════════════════════════════
    
    def _calculate_interaction_score(
        self,
        reinforcement: float,
        conflict: float,
        synergy: float,
        cancellation: float,
    ) -> float:
        """
        Calculate weighted interaction score.
        
        Formula:
            score = + 0.30 * reinforcement
                    + 0.25 * synergy
                    - 0.25 * conflict
                    - 0.20 * cancellation
        
        Returns:
            Score in range [-1, +1]
        """
        score = (
            AGGREGATION_WEIGHTS["reinforcement"] * reinforcement
            + AGGREGATION_WEIGHTS["synergy"] * synergy
            + AGGREGATION_WEIGHTS["conflict"] * conflict  # Already negative weight
            + AGGREGATION_WEIGHTS["cancellation"] * cancellation  # Already negative weight
        )
        
        # Clamp to [-1, +1]
        return max(-1.0, min(1.0, score))
    
    def _determine_state(
        self,
        score: float,
        cancellation_strength: float,
    ) -> tuple[AggregateInteractionState, bool]:
        """
        Determine interaction state from score.
        
        CRITICAL RULE: If cancellation_strength > 0.7, state is CRITICAL
        regardless of other factors.
        
        Returns:
            (state, cancellation_override_flag)
        """
        # HARD OVERRIDE: Cancellation protection
        if cancellation_strength > CANCELLATION_OVERRIDE_THRESHOLD:
            return (AggregateInteractionState.CRITICAL, True)
        
        # Normal threshold-based classification
        if score > STATE_THRESHOLDS["strong_positive_min"]:
            return (AggregateInteractionState.STRONG_POSITIVE, False)
        elif score > STATE_THRESHOLDS["positive_min"]:
            return (AggregateInteractionState.POSITIVE, False)
        elif score > STATE_THRESHOLDS["neutral_min"]:
            return (AggregateInteractionState.NEUTRAL, False)
        elif score > STATE_THRESHOLDS["negative_min"]:
            return (AggregateInteractionState.NEGATIVE, False)
        else:
            return (AggregateInteractionState.CRITICAL, False)
    
    def _determine_force_ranking(
        self,
        reinforcement: float,
        conflict: float,
        synergy: float,
        cancellation: float,
    ) -> tuple[str, str]:
        """
        Determine strongest and weakest interaction forces.
        
        Returns:
            (strongest_force_name, weakest_force_name)
        """
        forces = {
            "reinforcement": reinforcement,
            "synergy": synergy,
            "conflict": conflict,
            "cancellation": cancellation,
        }
        
        sorted_forces = sorted(forces.items(), key=lambda x: x[1], reverse=True)
        strongest = sorted_forces[0][0]
        weakest = sorted_forces[-1][0]
        
        return (strongest, weakest)
    
    def _build_drivers(
        self,
        reinforcement_data: Dict,
        conflict_data: Dict,
        synergy_data: Dict,
        cancellation_data: Dict,
        interaction_score: float,
        interaction_state: AggregateInteractionState,
    ) -> Dict[str, Any]:
        """Build explainability drivers."""
        return {
            # Contributions
            "reinforcement_contribution": round(
                reinforcement_data.get("pattern_reinforcement_strength", 0.0) * AGGREGATION_WEIGHTS["reinforcement"], 4
            ),
            "synergy_contribution": round(
                synergy_data.get("synergy_strength", 0.0) * AGGREGATION_WEIGHTS["synergy"], 4
            ),
            "conflict_contribution": round(
                conflict_data.get("pattern_conflict_strength", 0.0) * abs(AGGREGATION_WEIGHTS["conflict"]), 4
            ),
            "cancellation_contribution": round(
                cancellation_data.get("cancellation_strength", 0.0) * abs(AGGREGATION_WEIGHTS["cancellation"]), 4
            ),
            
            # Pattern counts
            "reinforcement_pattern_count": len(reinforcement_data.get("patterns_detected", [])),
            "conflict_pattern_count": len(conflict_data.get("conflict_patterns", [])),
            "synergy_pattern_count": len(synergy_data.get("synergy_patterns", [])),
            "cancellation_pattern_count": len(cancellation_data.get("cancellation_patterns", [])),
            
            # Dominant patterns
            "dominant_reinforcement": reinforcement_data.get("dominant_pattern"),
            "dominant_conflict": conflict_data.get("dominant_conflict"),
            "dominant_synergy": synergy_data.get("dominant_synergy"),
            "dominant_cancellation": cancellation_data.get("dominant_cancellation"),
            
            # State info
            "trade_cancelled": cancellation_data.get("trade_cancelled", False),
            "synergy_potential": synergy_data.get("synergy_potential", "LOW"),
            "conflict_severity": conflict_data.get("conflict_severity", "LOW_CONFLICT"),
        }
    
    # ═══════════════════════════════════════════════════════════
    # PUBLIC API FOR INTEGRATION
    # ═══════════════════════════════════════════════════════════
    
    def get_aggregate_for_symbol(self, symbol: str) -> Dict[str, Any]:
        """
        Get aggregate modifiers for Position Sizing / Execution Mode integration.
        
        This is the primary integration point for downstream modules.
        
        Returns:
            Dict with all modifiers and state info
        """
        result = self.aggregate(symbol)
        
        return {
            # Core modifiers
            "interaction_confidence_modifier": result.confidence_modifier,
            "interaction_size_modifier": result.size_modifier,
            "interaction_execution_modifier": result.execution_modifier.value,
            
            # State info
            "interaction_state": result.interaction_state.value,
            "interaction_score": result.interaction_score,
            
            # Force analysis
            "strongest_force": result.strongest_force,
            "weakest_force": result.weakest_force,
            
            # Override flags
            "cancellation_override": result.cancellation_override,
            
            # Raw strengths for debugging
            "reinforcement_strength": result.reinforcement_strength,
            "conflict_strength": result.conflict_strength,
            "synergy_strength": result.synergy_strength,
            "cancellation_strength": result.cancellation_strength,
        }
    
    def get_snapshot_for_trading_product(self, symbol: str) -> Dict[str, Any]:
        """
        Get compact snapshot for Trading Product Snapshot integration.
        
        Returns minimal data needed for trading product output.
        """
        result = self.aggregate(symbol)
        return result.to_snapshot()


# ═══════════════════════════════════════════════════════════════
# SINGLETON
# ═══════════════════════════════════════════════════════════════

_aggregator: Optional[InteractionAggregator] = None


def get_interaction_aggregator() -> InteractionAggregator:
    """Get singleton aggregator instance."""
    global _aggregator
    if _aggregator is None:
        _aggregator = InteractionAggregator()
    return _aggregator
