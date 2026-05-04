"""
PHASE 13.3 - Factor Types
==========================
Core data types for Factor Generator.
"""

from enum import Enum
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
import hashlib


class FactorTemplate(str, Enum):
    """Factor generation templates."""
    SINGLE_FEATURE = "single_feature"        # A
    PAIR_FEATURE = "pair_feature"            # A + B
    TRIPLE_FEATURE = "triple_feature"        # A + B + C
    RATIO_FEATURE = "ratio_feature"          # A / B
    DIFFERENCE_FEATURE = "difference_feature"  # A - B
    CONDITIONAL_FEATURE = "conditional_feature"  # A if B
    REGIME_CONDITIONED = "regime_conditioned"    # A only in regime R
    INTERACTION_FEATURE = "interaction_feature"  # A * B


class FactorFamily(str, Enum):
    """Factor family classification."""
    TREND = "trend"
    BREAKOUT = "breakout"
    REVERSAL = "reversal"
    LIQUIDITY = "liquidity"
    CORRELATION = "correlation"
    MICROSTRUCTURE = "microstructure"
    MACRO = "macro"
    REGIME = "regime"
    MOMENTUM = "momentum"
    VOLATILITY = "volatility"
    VOLUME = "volume"
    STRUCTURE = "structure"


class FactorStatus(str, Enum):
    """Factor lifecycle status."""
    CANDIDATE = "candidate"      # Just generated
    TESTING = "testing"          # Under evaluation
    APPROVED = "approved"        # Passed tests
    DEPLOYED = "deployed"        # In production
    DEPRECATED = "deprecated"    # Retired
    REJECTED = "rejected"        # Failed tests


class BatchRunStatus(str, Enum):
    """Batch generation run status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class Factor:
    """
    Factor Definition for Alpha Factory.
    
    Factors are trading constructs built from features.
    """
    
    # Identity
    factor_id: str
    name: str
    family: FactorFamily
    
    # Template
    template: FactorTemplate
    
    # Inputs
    inputs: List[str] = field(default_factory=list)  # feature_ids
    input_categories: List[str] = field(default_factory=list)
    
    # Transformations
    transforms: List[str] = field(default_factory=list)
    transform_params: Dict = field(default_factory=dict)
    
    # Dependencies
    regime_dependency: List[str] = field(default_factory=list)
    
    # Properties
    expected_direction: str = "NEUTRAL"  # LONG, SHORT, NEUTRAL
    complexity: int = 1  # Number of inputs
    
    # Description
    description: str = ""
    tags: List[str] = field(default_factory=list)
    
    # Metadata
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    status: FactorStatus = FactorStatus.CANDIDATE
    version: str = "1.0.0"
    
    # Performance (filled by ranker)
    ic_score: Optional[float] = None
    sharpe_ratio: Optional[float] = None
    stability_score: Optional[float] = None
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for MongoDB."""
        return {
            "factor_id": self.factor_id,
            "name": self.name,
            "family": self.family.value if isinstance(self.family, FactorFamily) else self.family,
            "template": self.template.value if isinstance(self.template, FactorTemplate) else self.template,
            "inputs": self.inputs,
            "input_categories": self.input_categories,
            "transforms": self.transforms,
            "transform_params": self.transform_params,
            "regime_dependency": self.regime_dependency,
            "expected_direction": self.expected_direction,
            "complexity": self.complexity,
            "description": self.description,
            "tags": self.tags,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "status": self.status.value if isinstance(self.status, FactorStatus) else self.status,
            "version": self.version,
            "ic_score": self.ic_score,
            "sharpe_ratio": self.sharpe_ratio,
            "stability_score": self.stability_score
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> "Factor":
        """Create from dictionary."""
        return cls(
            factor_id=data["factor_id"],
            name=data.get("name", ""),
            family=FactorFamily(data["family"]) if data.get("family") else FactorFamily.TREND,
            template=FactorTemplate(data["template"]) if data.get("template") else FactorTemplate.SINGLE_FEATURE,
            inputs=data.get("inputs", []),
            input_categories=data.get("input_categories", []),
            transforms=data.get("transforms", []),
            transform_params=data.get("transform_params", {}),
            regime_dependency=data.get("regime_dependency", []),
            expected_direction=data.get("expected_direction", "NEUTRAL"),
            complexity=data.get("complexity", 1),
            description=data.get("description", ""),
            tags=data.get("tags", []),
            created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else None,
            updated_at=datetime.fromisoformat(data["updated_at"]) if data.get("updated_at") else None,
            status=FactorStatus(data["status"]) if data.get("status") else FactorStatus.CANDIDATE,
            version=data.get("version", "1.0.0"),
            ic_score=data.get("ic_score"),
            sharpe_ratio=data.get("sharpe_ratio"),
            stability_score=data.get("stability_score")
        )
    
    @staticmethod
    def generate_id(inputs: List[str], template: str) -> str:
        """Generate unique factor ID from inputs and template."""
        key = f"{template}:{'_'.join(sorted(inputs))}"
        return hashlib.md5(key.encode()).hexdigest()[:12]


@dataclass
class FactorBatchRun:
    """
    Factor batch generation run.
    """
    run_id: str
    
    # Counts
    generated_count: int = 0
    accepted_count: int = 0
    rejected_count: int = 0
    
    # By family
    family_counts: Dict[str, int] = field(default_factory=dict)
    
    # By template
    template_counts: Dict[str, int] = field(default_factory=dict)
    
    # Timing
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    duration_seconds: float = 0.0
    
    # Status
    status: BatchRunStatus = BatchRunStatus.PENDING
    error_message: Optional[str] = None
    
    # Config
    config: Dict = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "run_id": self.run_id,
            "generated_count": self.generated_count,
            "accepted_count": self.accepted_count,
            "rejected_count": self.rejected_count,
            "family_counts": self.family_counts,
            "template_counts": self.template_counts,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "finished_at": self.finished_at.isoformat() if self.finished_at else None,
            "duration_seconds": self.duration_seconds,
            "status": self.status.value if isinstance(self.status, BatchRunStatus) else self.status,
            "error_message": self.error_message,
            "config": self.config
        }
