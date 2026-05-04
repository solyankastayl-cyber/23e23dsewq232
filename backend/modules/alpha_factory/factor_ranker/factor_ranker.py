"""
PHASE 13.4 - Factor Ranker
===========================
Main ranking engine for factors.

Workflow:
1. Load candidate factors
2. Evaluate each factor (metrics)
3. Rank by composite score
4. Apply family balance constraints
5. Generate approved list
"""

from typing import Dict, List, Optional, Tuple
from datetime import datetime, timezone
import uuid

from .factor_metrics import MetricsResult
from .factor_evaluator import FactorEvaluator
from .ranker_repository import RankerRepository

# Import Factor Repository
try:
    from modules.alpha_factory.factor_generator import FactorRepository as GeneratorRepository
    GENERATOR_OK = True
except ImportError:
    GENERATOR_OK = False
    GeneratorRepository = None


class RankingRun:
    """Ranking run result."""
    
    def __init__(self):
        self.run_id = str(uuid.uuid4())[:8]
        self.started_at: Optional[datetime] = None
        self.finished_at: Optional[datetime] = None
        self.duration_seconds: float = 0.0
        
        # Counts
        self.total_evaluated: int = 0
        self.elite_count: int = 0
        self.strong_count: int = 0
        self.promising_count: int = 0
        self.weak_count: int = 0
        self.rejected_count: int = 0
        self.approved_count: int = 0
        
        # By family
        self.family_approved: Dict[str, int] = {}
        
        # Status
        self.status: str = "pending"
        self.error_message: Optional[str] = None
    
    def to_dict(self) -> Dict:
        return {
            "run_id": self.run_id,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "finished_at": self.finished_at.isoformat() if self.finished_at else None,
            "duration_seconds": self.duration_seconds,
            "total_evaluated": self.total_evaluated,
            "verdicts": {
                "elite": self.elite_count,
                "strong": self.strong_count,
                "promising": self.promising_count,
                "weak": self.weak_count,
                "rejected": self.rejected_count
            },
            "approved_count": self.approved_count,
            "family_approved": self.family_approved,
            "status": self.status,
            "error_message": self.error_message
        }


class FactorRanker:
    """
    Factor Ranker - filters and ranks candidate factors.
    
    1140 candidates → ~150 approved factors
    """
    
    # Family balance constraints
    MAX_FAMILY_SHARE = 0.35  # Max 35% from one family
    MAX_APPROVED_PER_FAMILY = 50
    
    def __init__(self, seed: int = 42):
        """
        Initialize ranker.
        
        Args:
            seed: Random seed for reproducibility
        """
        self.evaluator = FactorEvaluator(seed=seed)
        self.repository = RankerRepository()
        self.generator_repository = GeneratorRepository() if GENERATOR_OK else None
        
        self.last_run: Optional[RankingRun] = None
    
    def run_ranking(
        self,
        factors: List[Dict] = None,
        max_approved: int = 200,
        clear_existing: bool = True,
        seed: int = None
    ) -> RankingRun:
        """
        Run full ranking pipeline.
        
        Args:
            factors: List of factor dicts (if None, loads from generator)
            max_approved: Maximum approved factors
            clear_existing: Clear existing rankings
            seed: Random seed
        
        Returns:
            RankingRun with results
        """
        run = RankingRun()
        run.started_at = datetime.now(timezone.utc)
        run.status = "running"
        
        if seed is not None:
            self.evaluator = FactorEvaluator(seed=seed)
        
        try:
            # Load factors if not provided
            if factors is None:
                if self.generator_repository and self.generator_repository.connected:
                    db_factors = self.generator_repository.list_factors(limit=2000)
                    factors = [f.to_dict() for f in db_factors]
                else:
                    raise ValueError("No factors provided and generator repository not available")
            
            if not factors:
                raise ValueError("No factors to rank")
            
            # Clear existing if requested
            if clear_existing:
                self.repository.clear_rankings()
            
            # Evaluate all factors
            results: List[MetricsResult] = []
            for factor in factors:
                result = self.evaluator.evaluate_factor(factor, n_samples=500)
                results.append(result)
            
            run.total_evaluated = len(results)
            
            # Sort by composite score
            results.sort(key=lambda r: r.composite_score, reverse=True)
            
            # Apply family balance and select approved
            approved_results = self._apply_family_balance(
                results, max_approved
            )
            
            # Count verdicts and save
            for result in results:
                # Update verdict counts
                if result.verdict == "ELITE":
                    run.elite_count += 1
                elif result.verdict == "STRONG":
                    run.strong_count += 1
                elif result.verdict == "PROMISING":
                    run.promising_count += 1
                elif result.verdict == "WEAK":
                    run.weak_count += 1
                else:
                    run.rejected_count += 1
                
                # Check if approved
                if result in approved_results:
                    result.approved = True
                    run.approved_count += 1
                    
                    # Get family from factor
                    factor = next((f for f in factors if f.get("factor_id") == result.factor_id), None)
                    if factor:
                        family = factor.get("family", "unknown")
                        run.family_approved[family] = run.family_approved.get(family, 0) + 1
                
                # Save to repository
                self.repository.save_ranking(result, factors)
            
            # Save run
            run.status = "completed"
            
        except Exception as e:
            run.status = "failed"
            run.error_message = str(e)
        
        run.finished_at = datetime.now(timezone.utc)
        run.duration_seconds = (run.finished_at - run.started_at).total_seconds()
        
        # Save run record
        self.repository.save_run(run)
        self.last_run = run
        
        return run
    
    def _apply_family_balance(
        self,
        results: List[MetricsResult],
        max_approved: int
    ) -> List[MetricsResult]:
        """
        Apply family balance constraints.
        
        Ensures no single family dominates the approved list.
        """
        approved = []
        family_counts: Dict[str, int] = {}
        
        # Get factor info for family lookup
        factor_families = {}
        if self.generator_repository and self.generator_repository.connected:
            db_factors = self.generator_repository.list_factors(limit=2000)
            for f in db_factors:
                factor_families[f.factor_id] = f.family.value if hasattr(f.family, 'value') else f.family
        
        for result in results:
            if len(approved) >= max_approved:
                break
            
            # Must be at least PROMISING
            if result.verdict in ["WEAK", "REJECTED"]:
                continue
            
            # Get family
            family = factor_families.get(result.factor_id, "unknown")
            
            # Check family balance
            current_count = family_counts.get(family, 0)
            max_for_family = min(
                self.MAX_APPROVED_PER_FAMILY,
                int(max_approved * self.MAX_FAMILY_SHARE)
            )
            
            if current_count >= max_for_family:
                continue  # Skip, family quota reached
            
            # Approve
            approved.append(result)
            family_counts[family] = current_count + 1
        
        return approved
    
    def evaluate_single(
        self,
        factor_id: str
    ) -> Optional[MetricsResult]:
        """
        Evaluate a single factor by ID.
        """
        if not self.generator_repository:
            return None
        
        factor = self.generator_repository.get_factor(factor_id)
        if not factor:
            return None
        
        result = self.evaluator.evaluate_factor(factor.to_dict())
        self.repository.save_ranking(result, [factor.to_dict()])
        
        return result
    
    def get_rankings(
        self,
        verdict: Optional[str] = None,
        approved_only: bool = False,
        limit: int = 100
    ) -> List[Dict]:
        """
        Get rankings.
        """
        return self.repository.get_rankings(
            verdict=verdict,
            approved_only=approved_only,
            limit=limit
        )
    
    def get_top_factors(
        self,
        n: int = 20
    ) -> List[Dict]:
        """
        Get top N factors by composite score.
        """
        return self.repository.get_top_rankings(n)
    
    def get_approved_factors(self) -> List[Dict]:
        """
        Get all approved factors.
        """
        return self.repository.get_rankings(approved_only=True, limit=500)
    
    def get_stats(self) -> Dict:
        """
        Get ranker statistics.
        """
        repo_stats = self.repository.get_stats()
        
        return {
            "repository": repo_stats,
            "last_run": self.last_run.to_dict() if self.last_run else None,
            "config": {
                "max_family_share": self.MAX_FAMILY_SHARE,
                "max_approved_per_family": self.MAX_APPROVED_PER_FAMILY
            }
        }


# Global singleton
_ranker_instance: Optional[FactorRanker] = None


def get_factor_ranker() -> FactorRanker:
    """Get singleton ranker instance."""
    global _ranker_instance
    if _ranker_instance is None:
        _ranker_instance = FactorRanker()
    return _ranker_instance
