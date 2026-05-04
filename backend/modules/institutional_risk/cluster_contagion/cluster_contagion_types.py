"""
PHASE 22.3 — Cluster Contagion Types
====================================
Type definitions for Cluster Contagion Engine.

Core contracts:
- ClusterContagionState: Contagion metrics and state
- ContagionLevel: Contagion level enum
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone


# ══════════════════════════════════════════════════════════════
# CONTAGION LEVEL ENUM
# ══════════════════════════════════════════════════════════════

class ContagionLevel(str, Enum):
    LOW = "LOW"             # score < 0.25
    ELEVATED = "ELEVATED"   # score 0.25-0.45
    HIGH = "HIGH"           # score 0.45-0.65
    SYSTEMIC = "SYSTEMIC"   # score > 0.65


# ══════════════════════════════════════════════════════════════
# CONTAGION RECOMMENDED ACTION ENUM
# ══════════════════════════════════════════════════════════════

class ContagionAction(str, Enum):
    HOLD = "HOLD"                       # LOW
    REDUCE_CLUSTER = "REDUCE_CLUSTER"   # ELEVATED
    HEDGE_CLUSTER = "HEDGE_CLUSTER"     # HIGH
    DELEVER_SYSTEM = "DELEVER_SYSTEM"   # SYSTEMIC


# ══════════════════════════════════════════════════════════════
# CONTAGION STATE THRESHOLDS
# ══════════════════════════════════════════════════════════════

CONTAGION_THRESHOLDS = {
    ContagionLevel.LOW: 0.25,
    ContagionLevel.ELEVATED: 0.45,
    ContagionLevel.HIGH: 0.65,
}


# ══════════════════════════════════════════════════════════════
# CLUSTER DEFINITIONS
# ══════════════════════════════════════════════════════════════

CLUSTER_IDS = [
    "btc_cluster",
    "majors_cluster",
    "alts_cluster",
    "trend_cluster",
    "reversal_cluster",
]

DEFAULT_CLUSTER_EXPOSURES = {
    "btc_cluster": 0.30,
    "majors_cluster": 0.25,
    "alts_cluster": 0.20,
    "trend_cluster": 0.15,
    "reversal_cluster": 0.10,
}


# ══════════════════════════════════════════════════════════════
# CONTAGION MAP
# ══════════════════════════════════════════════════════════════

CONTAGION_MAP = {
    "btc_cluster": ["majors_cluster", "alts_cluster"],
    "majors_cluster": ["alts_cluster"],
    "trend_cluster": ["majors_cluster"],
    "alts_cluster": ["reversal_cluster"],
    "reversal_cluster": [],
}


# ══════════════════════════════════════════════════════════════
# CLUSTER VOLATILITY MULTIPLIERS
# ══════════════════════════════════════════════════════════════

CLUSTER_VOLATILITY_MULTIPLIERS = {
    "LOW": 0.7,
    "NORMAL": 1.0,
    "HIGH": 1.4,
    "EXPANDING": 1.8,
    "EXTREME": 2.2,
    "COMPRESSED": 0.8,
}


# ══════════════════════════════════════════════════════════════
# MARKET RISK MULTIPLIERS
# ══════════════════════════════════════════════════════════════

MARKET_RISK_MULTIPLIERS = {
    "NORMAL": 1.0,
    "ELEVATED": 1.2,
    "HIGH": 1.5,
    "CRITICAL": 1.8,
}


# ══════════════════════════════════════════════════════════════
# SYSTEMIC RISK WEIGHTS
# ══════════════════════════════════════════════════════════════

SYSTEMIC_RISK_WEIGHTS = {
    "max_cluster_stress": 0.40,
    "avg_contagion_prob": 0.35,
    "concentration_score": 0.25,
}


# ══════════════════════════════════════════════════════════════
# CONTAGION MODIFIERS
# ══════════════════════════════════════════════════════════════

CONTAGION_MODIFIERS = {
    ContagionLevel.LOW: {
        "confidence_modifier": 1.00,
        "capital_modifier": 1.00,
    },
    ContagionLevel.ELEVATED: {
        "confidence_modifier": 0.95,
        "capital_modifier": 0.90,
    },
    ContagionLevel.HIGH: {
        "confidence_modifier": 0.85,
        "capital_modifier": 0.75,
    },
    ContagionLevel.SYSTEMIC: {
        "confidence_modifier": 0.70,
        "capital_modifier": 0.55,
    },
}


# ══════════════════════════════════════════════════════════════
# CLUSTER CONTAGION STATE
# ══════════════════════════════════════════════════════════════

@dataclass
class ClusterContagionState:
    """
    Cluster Contagion State.
    """
    cluster_stress: Dict[str, float]
    contagion_probabilities: Dict[str, float]
    contagion_paths: List[str]

    systemic_risk_score: float
    contagion_state: ContagionLevel
    recommended_action: ContagionAction

    confidence_modifier: float
    capital_modifier: float

    dominant_cluster: str
    weakest_cluster: str

    reason: str

    volatility_state: str = "NORMAL"
    market_risk_state: str = "NORMAL"
    concentration_score: float = 0.3

    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "cluster_stress": {k: round(v, 4) for k, v in self.cluster_stress.items()},
            "contagion_probabilities": {k: round(v, 4) for k, v in self.contagion_probabilities.items()},
            "contagion_paths": self.contagion_paths,
            "systemic_risk_score": round(self.systemic_risk_score, 4),
            "contagion_state": self.contagion_state.value,
            "recommended_action": self.recommended_action.value,
            "confidence_modifier": round(self.confidence_modifier, 4),
            "capital_modifier": round(self.capital_modifier, 4),
            "dominant_cluster": self.dominant_cluster,
            "weakest_cluster": self.weakest_cluster,
            "reason": self.reason,
            "timestamp": self.timestamp.isoformat(),
        }

    def to_full_dict(self) -> Dict[str, Any]:
        result = self.to_dict()
        result["inputs"] = {
            "volatility_state": self.volatility_state,
            "market_risk_state": self.market_risk_state,
            "concentration_score": round(self.concentration_score, 4),
        }
        return result

    def to_summary(self) -> Dict[str, Any]:
        return {
            "systemic_risk_score": round(self.systemic_risk_score, 4),
            "contagion_state": self.contagion_state.value,
            "recommended_action": self.recommended_action.value,
            "dominant_cluster": self.dominant_cluster,
            "weakest_cluster": self.weakest_cluster,
            "confidence_modifier": round(self.confidence_modifier, 4),
            "capital_modifier": round(self.capital_modifier, 4),
        }


# ══════════════════════════════════════════════════════════════
# CONTAGION HISTORY ENTRY
# ══════════════════════════════════════════════════════════════

@dataclass
class ContagionHistoryEntry:
    contagion_state: ContagionLevel
    systemic_risk_score: float
    dominant_cluster: str
    recommended_action: ContagionAction
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "contagion_state": self.contagion_state.value,
            "systemic_risk_score": round(self.systemic_risk_score, 4),
            "dominant_cluster": self.dominant_cluster,
            "recommended_action": self.recommended_action.value,
            "timestamp": self.timestamp.isoformat(),
        }
