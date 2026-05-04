"""
PHASE 15.6 — Alpha Ecology Aggregator
======================================
Unified aggregator for all Alpha Ecology engines.

Purpose:
    Combines all 5 ecology dimensions into a single score that
    represents the overall health of alpha signals.

Components:
    - Decay: Signal performance degradation (temporal risk)
    - Crowding: Market crowding level (behavioral risk)
    - Correlation: Signal uniqueness (structural risk)
    - Redundancy: Signal consensus density (consensus risk)
    - Survival: Cross-regime survival (regime risk)

Formula:
    ecology_score = weighted_average(all confidence_modifiers)
    
    Weights:
    - 0.20 decay
    - 0.20 crowding
    - 0.20 correlation
    - 0.20 redundancy
    - 0.20 survival

Ecology States:
    - HEALTHY: > 1.05 (alpha is thriving)
    - STABLE: 0.90-1.05 (alpha is normal)
    - STRESSED: 0.75-0.90 (alpha is under pressure)
    - CRITICAL: < 0.75 (alpha is at risk)

Key Principle:
    Ecology NEVER blocks a signal.
    It provides a unified risk adjustment layer.
"""

import os
import sys
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone
from dataclasses import dataclass, field
from enum import Enum

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from modules.alpha_ecology.alpha_ecology_types import (
    DecayState,
    CrowdingState,
    CorrelationState,
    RedundancyState,
    SurvivalState,
    AlphaEcologyState,
)

# MongoDB
from pymongo import MongoClient

MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.environ.get("DB_NAME", "ta_engine")


# ══════════════════════════════════════════════════════════════
# ECOLOGY STATE ENUM
# ══════════════════════════════════════════════════════════════

class EcologyState(str, Enum):
    HEALTHY = "HEALTHY"
    STABLE = "STABLE"
    STRESSED = "STRESSED"
    CRITICAL = "CRITICAL"


# ══════════════════════════════════════════════════════════════
# ECOLOGY THRESHOLDS
# ══════════════════════════════════════════════════════════════

ECOLOGY_THRESHOLDS = {
    "healthy_min": 1.05,
    "stable_min": 0.90,
    "stressed_min": 0.75,
    # Below stressed_min = CRITICAL
}


ECOLOGY_WEIGHTS = {
    "decay": 0.20,
    "crowding": 0.20,
    "correlation": 0.20,
    "redundancy": 0.20,
    "survival": 0.20,
}


ECOLOGY_MODIFIERS = {
    EcologyState.HEALTHY: {
        "confidence_modifier": 1.05,
        "size_modifier": 1.05,
    },
    EcologyState.STABLE: {
        "confidence_modifier": 1.0,
        "size_modifier": 1.0,
    },
    EcologyState.STRESSED: {
        "confidence_modifier": 0.85,
        "size_modifier": 0.85,
    },
    EcologyState.CRITICAL: {
        "confidence_modifier": 0.65,
        "size_modifier": 0.65,
    },
}


# ══════════════════════════════════════════════════════════════
# ECOLOGY RESULT CONTRACT
# ══════════════════════════════════════════════════════════════

@dataclass
class AlphaEcologyResult:
    """
    Unified output from Alpha Ecology Aggregator.
    
    Combines all ecology dimensions into a single risk assessment.
    """
    symbol: str
    timestamp: datetime
    
    # Individual states
    decay_state: DecayState
    crowding_state: CrowdingState
    correlation_state: CorrelationState
    redundancy_state: RedundancyState
    survival_state: SurvivalState
    
    # Individual modifiers
    decay_modifier: float
    crowding_modifier: float
    correlation_modifier: float
    redundancy_modifier: float
    survival_modifier: float
    
    # Aggregated
    ecology_score: float
    ecology_state: EcologyState
    
    # Final modifiers
    confidence_modifier: float
    size_modifier: float
    
    # Explainability
    drivers: Dict[str, str]
    component_scores: Dict[str, float]
    weakest_component: str
    strongest_component: str
    
    def to_dict(self) -> Dict:
        return {
            "symbol": self.symbol,
            "timestamp": self.timestamp.isoformat(),
            "decay_state": self.decay_state.value,
            "crowding_state": self.crowding_state.value,
            "correlation_state": self.correlation_state.value,
            "redundancy_state": self.redundancy_state.value,
            "survival_state": self.survival_state.value,
            "decay_modifier": round(self.decay_modifier, 4),
            "crowding_modifier": round(self.crowding_modifier, 4),
            "correlation_modifier": round(self.correlation_modifier, 4),
            "redundancy_modifier": round(self.redundancy_modifier, 4),
            "survival_modifier": round(self.survival_modifier, 4),
            "ecology_score": round(self.ecology_score, 4),
            "ecology_state": self.ecology_state.value,
            "confidence_modifier": round(self.confidence_modifier, 4),
            "size_modifier": round(self.size_modifier, 4),
            "drivers": self.drivers,
            "component_scores": {k: round(v, 4) for k, v in self.component_scores.items()},
            "weakest_component": self.weakest_component,
            "strongest_component": self.strongest_component,
        }


# ══════════════════════════════════════════════════════════════
# ALPHA ECOLOGY ENGINE (AGGREGATOR)
# ══════════════════════════════════════════════════════════════

class AlphaEcologyEngine:
    """
    Alpha Ecology Aggregator - PHASE 15.6
    
    Combines all 5 ecology engines into a unified risk assessment.
    
    Key Principle:
        Ecology NEVER blocks a signal.
        It provides unified risk adjustment.
    """
    
    def __init__(self):
        self.client = MongoClient(MONGO_URL)
        self.db = self.client[DB_NAME]
        
        # Lazy load engines
        self._decay_engine = None
        self._crowding_engine = None
        self._correlation_engine = None
        self._redundancy_engine = None
        self._survival_engine = None
    
    @property
    def decay_engine(self):
        if self._decay_engine is None:
            from modules.alpha_ecology.alpha_decay_engine import get_alpha_decay_engine
            self._decay_engine = get_alpha_decay_engine()
        return self._decay_engine
    
    @property
    def crowding_engine(self):
        if self._crowding_engine is None:
            from modules.alpha_ecology.alpha_crowding_engine import get_alpha_crowding_engine
            self._crowding_engine = get_alpha_crowding_engine()
        return self._crowding_engine
    
    @property
    def correlation_engine(self):
        if self._correlation_engine is None:
            from modules.alpha_ecology.alpha_correlation_engine import get_alpha_correlation_engine
            self._correlation_engine = get_alpha_correlation_engine()
        return self._correlation_engine
    
    @property
    def redundancy_engine(self):
        if self._redundancy_engine is None:
            from modules.alpha_ecology.alpha_redundancy_engine import get_alpha_redundancy_engine
            self._redundancy_engine = get_alpha_redundancy_engine()
        return self._redundancy_engine
    
    @property
    def survival_engine(self):
        if self._survival_engine is None:
            from modules.alpha_ecology.alpha_survival_engine import get_alpha_survival_engine
            self._survival_engine = get_alpha_survival_engine()
        return self._survival_engine
    
    def analyze(self, symbol: str) -> AlphaEcologyResult:
        """
        Analyze complete alpha ecology for a symbol.
        
        Args:
            symbol: Trading pair (BTC, ETH, SOL)
        
        Returns:
            AlphaEcologyResult with unified ecology assessment
        """
        now = datetime.now(timezone.utc)
        
        # Get modifiers from each engine
        decay_mod = self.decay_engine.get_modifier_for_symbol(symbol)
        crowding_mod = self.crowding_engine.get_modifier_for_symbol(symbol)
        correlation_mod = self.correlation_engine.get_modifier_for_symbol(symbol)
        redundancy_mod = self.redundancy_engine.get_modifier_for_symbol(symbol)
        survival_mod = self.survival_engine.get_modifier_for_symbol(symbol)
        
        # Extract confidence modifiers
        decay_conf = decay_mod.get("decay_confidence_modifier", 1.0)
        crowding_conf = crowding_mod.get("crowding_confidence_modifier", 1.0)
        correlation_conf = correlation_mod.get("correlation_confidence_modifier", 1.0)
        redundancy_conf = redundancy_mod.get("redundancy_confidence_modifier", 1.0)
        survival_conf = survival_mod.get("survival_confidence_modifier", 1.0)
        
        # Extract states
        decay_state = DecayState(decay_mod.get("decay_state", "STABLE"))
        crowding_state = CrowdingState(crowding_mod.get("crowding_state", "LOW_CROWDING"))
        correlation_state = CorrelationState(correlation_mod.get("correlation_state", "UNIQUE"))
        redundancy_state = RedundancyState(redundancy_mod.get("redundancy_state", "DIVERSIFIED"))
        survival_state = SurvivalState(survival_mod.get("survival_state", "STABLE"))
        
        # Compute weighted ecology score
        ecology_score = (
            ECOLOGY_WEIGHTS["decay"] * decay_conf
            + ECOLOGY_WEIGHTS["crowding"] * crowding_conf
            + ECOLOGY_WEIGHTS["correlation"] * correlation_conf
            + ECOLOGY_WEIGHTS["redundancy"] * redundancy_conf
            + ECOLOGY_WEIGHTS["survival"] * survival_conf
        )
        
        # Determine ecology state
        ecology_state = self._determine_ecology_state(ecology_score)
        
        # Get final modifiers
        modifiers = ECOLOGY_MODIFIERS[ecology_state]
        conf_mod = modifiers["confidence_modifier"]
        size_mod = modifiers["size_modifier"]
        
        # Fine-tune based on severity
        if ecology_state == EcologyState.CRITICAL:
            severity = (0.75 - ecology_score) / 0.25 if ecology_score < 0.75 else 0
            conf_mod *= (1.0 - 0.15 * min(severity, 1.0))
            size_mod *= (1.0 - 0.15 * min(severity, 1.0))
        elif ecology_state == EcologyState.HEALTHY:
            bonus = (ecology_score - 1.05) / 0.15 if ecology_score > 1.05 else 0
            conf_mod = min(1.1, conf_mod + 0.03 * min(bonus, 1.0))
            size_mod = min(1.1, size_mod + 0.02 * min(bonus, 1.0))
        
        # Build drivers
        drivers = {
            "decay": decay_state.value,
            "crowding": crowding_state.value,
            "correlation": correlation_state.value,
            "redundancy": redundancy_state.value,
            "survival": survival_state.value,
        }
        
        # Component scores
        component_scores = {
            "decay": decay_conf,
            "crowding": crowding_conf,
            "correlation": correlation_conf,
            "redundancy": redundancy_conf,
            "survival": survival_conf,
        }
        
        # Find weakest and strongest
        weakest = min(component_scores, key=component_scores.get)
        strongest = max(component_scores, key=component_scores.get)
        
        return AlphaEcologyResult(
            symbol=symbol,
            timestamp=now,
            decay_state=decay_state,
            crowding_state=crowding_state,
            correlation_state=correlation_state,
            redundancy_state=redundancy_state,
            survival_state=survival_state,
            decay_modifier=decay_conf,
            crowding_modifier=crowding_conf,
            correlation_modifier=correlation_conf,
            redundancy_modifier=redundancy_conf,
            survival_modifier=survival_conf,
            ecology_score=ecology_score,
            ecology_state=ecology_state,
            confidence_modifier=max(0.5, conf_mod),  # Never below 0.5
            size_modifier=max(0.5, size_mod),
            drivers=drivers,
            component_scores=component_scores,
            weakest_component=weakest,
            strongest_component=strongest,
        )
    
    def get_modifier_for_symbol(self, symbol: str) -> Dict[str, Any]:
        """
        Get unified ecology modifiers for Trading Product integration.
        """
        result = self.analyze(symbol)
        
        return {
            "ecology_confidence_modifier": result.confidence_modifier,
            "ecology_size_modifier": result.size_modifier,
            "ecology_score": result.ecology_score,
            "ecology_state": result.ecology_state.value,
            "weakest_component": result.weakest_component,
            "strongest_component": result.strongest_component,
            "drivers": result.drivers,
        }
    
    def get_trading_product_ecology(self, symbol: str) -> Dict[str, Any]:
        """
        Get ecology data formatted for Trading Product Snapshot.
        
        This is the integration point for the main trading pipeline.
        """
        result = self.analyze(symbol)
        
        return {
            # Main ecology metrics
            "ecology_score": round(result.ecology_score, 4),
            "ecology_state": result.ecology_state.value,
            "ecology_quality": self._get_quality_label(result.ecology_state),
            
            # Modifiers for pipeline
            "ecology_confidence_modifier": round(result.confidence_modifier, 4),
            "ecology_size_modifier": round(result.size_modifier, 4),
            
            # Component breakdown
            "components": {
                "decay": {
                    "state": result.decay_state.value,
                    "modifier": round(result.decay_modifier, 4),
                },
                "crowding": {
                    "state": result.crowding_state.value,
                    "modifier": round(result.crowding_modifier, 4),
                },
                "correlation": {
                    "state": result.correlation_state.value,
                    "modifier": round(result.correlation_modifier, 4),
                },
                "redundancy": {
                    "state": result.redundancy_state.value,
                    "modifier": round(result.redundancy_modifier, 4),
                },
                "survival": {
                    "state": result.survival_state.value,
                    "modifier": round(result.survival_modifier, 4),
                },
            },
            
            # Analysis
            "weakest_component": result.weakest_component,
            "strongest_component": result.strongest_component,
        }
    
    # ═══════════════════════════════════════════════════════════════
    # STATE DETERMINATION
    # ═══════════════════════════════════════════════════════════════
    
    def _determine_ecology_state(self, score: float) -> EcologyState:
        """Determine ecology state from score."""
        if score >= ECOLOGY_THRESHOLDS["healthy_min"]:
            return EcologyState.HEALTHY
        elif score >= ECOLOGY_THRESHOLDS["stable_min"]:
            return EcologyState.STABLE
        elif score >= ECOLOGY_THRESHOLDS["stressed_min"]:
            return EcologyState.STRESSED
        else:
            return EcologyState.CRITICAL
    
    def _get_quality_label(self, state: EcologyState) -> str:
        """Get human-readable quality label."""
        labels = {
            EcologyState.HEALTHY: "ALPHA_THRIVING",
            EcologyState.STABLE: "ALPHA_NORMAL",
            EcologyState.STRESSED: "ALPHA_PRESSURED",
            EcologyState.CRITICAL: "ALPHA_AT_RISK",
        }
        return labels.get(state, "UNKNOWN")


# ═══════════════════════════════════════════════════════════════
# SINGLETON
# ═══════════════════════════════════════════════════════════════

_engine: Optional[AlphaEcologyEngine] = None


def get_alpha_ecology_engine() -> AlphaEcologyEngine:
    """Get singleton engine instance."""
    global _engine
    if _engine is None:
        _engine = AlphaEcologyEngine()
    return _engine
