"""
PHASE 26.5 — Alpha Factory Engine

Unified pipeline orchestrator.

Pipeline:
Discovery → Scoring → Survival → Registry

Features:
- Single run_alpha_pipeline() method
- Scheduler support
- Max active factors protection (30)
"""

from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field

from .factor_discovery_engine import FactorDiscoveryEngine, get_factor_discovery_engine
from .alpha_scoring_engine import AlphaScoringEngine, get_alpha_scoring_engine
from .factor_survival_engine import FactorSurvivalEngine, get_factor_survival_engine
from .alpha_registry import AlphaRegistry, get_alpha_registry
from .factor_types import AlphaFactor


# ══════════════════════════════════════════════════════════════
# Result Contract
# ══════════════════════════════════════════════════════════════

class AlphaFactoryResult(BaseModel):
    """Result of alpha factory pipeline run."""
    candidates_generated: int
    scored_factors: int
    active_factors: int
    deprecated_factors: int
    strongest_factor: Optional[str]
    weakest_factor: Optional[str]
    average_alpha_score: float
    
    # Metadata
    pipeline_duration_ms: int = 0
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class AlphaFactoryStatus(BaseModel):
    """Status of alpha factory."""
    pipeline_state: str  # READY | RUNNING | ERROR
    last_run: Optional[datetime]
    active_factors: int
    deprecated_factors: int
    total_factors: int


# ══════════════════════════════════════════════════════════════
# Constants
# ══════════════════════════════════════════════════════════════

# Maximum active factors (runaway protection)
MAX_ACTIVE_FACTORS = 30

# Recommended schedule interval (hours)
SCHEDULE_INTERVAL_HOURS = 6


class AlphaFactoryEngine:
    """
    Alpha Factory Engine.
    
    Orchestrates the full alpha pipeline:
    Discovery → Scoring → Survival → Registry
    
    Features:
    - Single run method for full pipeline
    - Max active factors protection
    - Scheduler support
    """
    
    def __init__(
        self,
        discovery: Optional[FactorDiscoveryEngine] = None,
        scoring: Optional[AlphaScoringEngine] = None,
        survival: Optional[FactorSurvivalEngine] = None,
        registry: Optional[AlphaRegistry] = None,
    ):
        self._discovery = discovery or FactorDiscoveryEngine()
        self._scoring = scoring or AlphaScoringEngine()
        self._survival = survival or FactorSurvivalEngine()
        self._registry = registry or AlphaRegistry()
        
        self._last_run: Optional[datetime] = None
        self._last_result: Optional[AlphaFactoryResult] = None
        self._pipeline_state = "READY"
    
    # ═══════════════════════════════════════════════════════════
    # Main Pipeline
    # ═══════════════════════════════════════════════════════════
    
    async def run_alpha_pipeline(self) -> AlphaFactoryResult:
        """
        Run full alpha pipeline.
        
        Sequence:
        1. Discovery → Generate candidates
        2. Scoring → Score all candidates
        3. Survival → Filter weak factors
        4. Registry → Store survivors
        
        Returns:
            AlphaFactoryResult with pipeline statistics
        """
        start_time = datetime.utcnow()
        self._pipeline_state = "RUNNING"
        
        try:
            # Step 1: Discovery
            candidates = self._discovery.discover_all()
            candidates_count = len(candidates)
            
            # Step 2: Scoring
            scored = self._scoring.score_candidates(candidates)
            scored_count = len(scored)
            
            # Step 3: Survival
            survived = self._survival.apply_survival(scored)
            
            # Step 4: Apply max active factors protection
            active_factors = [f for f in survived if f.status == "ACTIVE"]
            deprecated_factors = [f for f in survived if f.status == "DEPRECATED"]
            
            if len(active_factors) > MAX_ACTIVE_FACTORS:
                # Keep only top N by alpha_score
                active_factors, extra_deprecated = self._apply_max_active_limit(
                    active_factors
                )
                deprecated_factors.extend(extra_deprecated)
                
                # Update survived list
                survived = active_factors + deprecated_factors
            
            # Step 5: Registry update
            await self._registry.register_factors_bulk(survived)
            
            # Build result
            active_count = len(active_factors)
            deprecated_count = len(deprecated_factors)
            
            strongest = self._get_strongest_factor(survived)
            weakest = self._get_weakest_factor(survived)
            avg_alpha = self._compute_average_alpha(survived)
            
            end_time = datetime.utcnow()
            duration_ms = int((end_time - start_time).total_seconds() * 1000)
            
            result = AlphaFactoryResult(
                candidates_generated=candidates_count,
                scored_factors=scored_count,
                active_factors=active_count,
                deprecated_factors=deprecated_count,
                strongest_factor=strongest,
                weakest_factor=weakest,
                average_alpha_score=round(avg_alpha, 4),
                pipeline_duration_ms=duration_ms,
                timestamp=end_time,
            )
            
            self._last_run = end_time
            self._last_result = result
            self._pipeline_state = "READY"
            
            return result
            
        except Exception as e:
            self._pipeline_state = "ERROR"
            raise e
    
    def _apply_max_active_limit(
        self,
        active_factors: List[AlphaFactor],
    ) -> tuple:
        """
        Apply max active factors limit.
        
        Keeps top N by alpha_score, deprecates the rest.
        """
        sorted_factors = sorted(
            active_factors,
            key=lambda f: f.alpha_score,
            reverse=True,
        )
        
        keep = sorted_factors[:MAX_ACTIVE_FACTORS]
        deprecate = sorted_factors[MAX_ACTIVE_FACTORS:]
        
        # Update status to DEPRECATED for extras
        deprecated = []
        for f in deprecate:
            deprecated.append(AlphaFactor(
                factor_id=f.factor_id,
                name=f.name,
                category=f.category,
                lookback=f.lookback,
                signal_strength=f.signal_strength,
                sharpe_score=f.sharpe_score,
                stability_score=f.stability_score,
                drawdown_score=f.drawdown_score,
                alpha_score=f.alpha_score,
                status="DEPRECATED",
                parameters=f.parameters,
                source=f.source,
            ))
        
        return keep, deprecated
    
    # ═══════════════════════════════════════════════════════════
    # Scheduler
    # ═══════════════════════════════════════════════════════════
    
    async def run_scheduled(self) -> Optional[AlphaFactoryResult]:
        """
        Run pipeline if enough time has passed since last run.
        
        Interval: 6 hours
        
        Returns:
            AlphaFactoryResult if run, None if skipped
        """
        if self._last_run is not None:
            hours_since = (datetime.utcnow() - self._last_run).total_seconds() / 3600
            
            if hours_since < SCHEDULE_INTERVAL_HOURS:
                return None  # Skip, too soon
        
        return await self.run_alpha_pipeline()
    
    def should_run_scheduled(self) -> bool:
        """Check if scheduled run is needed."""
        if self._last_run is None:
            return True
        
        hours_since = (datetime.utcnow() - self._last_run).total_seconds() / 3600
        return hours_since >= SCHEDULE_INTERVAL_HOURS
    
    # ═══════════════════════════════════════════════════════════
    # Helpers
    # ═══════════════════════════════════════════════════════════
    
    def _get_strongest_factor(
        self,
        factors: List[AlphaFactor],
    ) -> Optional[str]:
        """Get name of strongest factor."""
        if not factors:
            return None
        strongest = max(factors, key=lambda f: f.alpha_score)
        return strongest.name
    
    def _get_weakest_factor(
        self,
        factors: List[AlphaFactor],
    ) -> Optional[str]:
        """Get name of weakest factor."""
        if not factors:
            return None
        weakest = min(factors, key=lambda f: f.alpha_score)
        return weakest.name
    
    def _compute_average_alpha(
        self,
        factors: List[AlphaFactor],
    ) -> float:
        """Compute average alpha score."""
        if not factors:
            return 0.0
        return sum(f.alpha_score for f in factors) / len(factors)
    
    # ═══════════════════════════════════════════════════════════
    # Status & Accessors
    # ═══════════════════════════════════════════════════════════
    
    async def get_status(self) -> AlphaFactoryStatus:
        """Get current factory status."""
        all_factors = await self._registry.get_all_factors()
        active = [f for f in all_factors if f.status == "ACTIVE"]
        deprecated = [f for f in all_factors if f.status == "DEPRECATED"]
        
        return AlphaFactoryStatus(
            pipeline_state=self._pipeline_state,
            last_run=self._last_run,
            active_factors=len(active),
            deprecated_factors=len(deprecated),
            total_factors=len(all_factors),
        )
    
    async def get_active_factors(self) -> List[AlphaFactor]:
        """Get active factors from registry."""
        factors = await self._registry.get_active_factors()
        # Convert RegistryAlphaFactor to AlphaFactor
        return [
            AlphaFactor(
                factor_id=f.factor_id,
                name=f.name,
                category=f.category,
                lookback=f.lookback,
                signal_strength=f.signal_strength,
                sharpe_score=f.sharpe_score,
                stability_score=f.stability_score,
                drawdown_score=f.drawdown_score,
                alpha_score=f.alpha_score,
                status=f.status,
                parameters=f.parameters,
                source=f.source,
            )
            for f in factors
        ]
    
    async def get_summary(self) -> dict:
        """Get factory summary."""
        summary = await self._registry.get_summary()
        return {
            "total_factors": summary.total_factors,
            "active_factors": summary.active_factors,
            "deprecated_factors": summary.deprecated_factors,
            "top_factor": summary.top_factor,
            "average_alpha_score": summary.average_alpha_score,
            "last_run": self._last_run.isoformat() if self._last_run else None,
            "pipeline_state": self._pipeline_state,
        }
    
    @property
    def last_run(self) -> Optional[datetime]:
        """Get timestamp of last pipeline run."""
        return self._last_run
    
    @property
    def last_result(self) -> Optional[AlphaFactoryResult]:
        """Get result of last pipeline run."""
        return self._last_result
    
    @property
    def pipeline_state(self) -> str:
        """Get current pipeline state."""
        return self._pipeline_state


# Singleton
_engine: Optional[AlphaFactoryEngine] = None


def get_alpha_factory_engine() -> AlphaFactoryEngine:
    """Get singleton instance of AlphaFactoryEngine."""
    global _engine
    if _engine is None:
        # Use shared registry singleton
        _engine = AlphaFactoryEngine(
            registry=get_alpha_registry()
        )
    return _engine
