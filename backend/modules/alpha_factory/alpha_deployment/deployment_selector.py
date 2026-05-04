"""
PHASE 13.7 - Deployment Selector
==================================
Selects factors for deployment from approved list.

Selection criteria:
- Composite score
- Family balance
- Regime coverage
- Decay score
- Factor stability
"""

from typing import Dict, List, Optional, Set, Tuple
from datetime import datetime, timezone
from collections import defaultdict

from .deployment_types import (
    DeployedAlpha,
    DeploymentDecision,
    DeploymentStatus,
    DeploymentMode
)
from .deployment_registry import DeploymentRegistry, get_deployment_registry

# Import Factor Ranker
try:
    from modules.alpha_factory.factor_ranker import get_factor_ranker
    RANKER_OK = True
except ImportError:
    RANKER_OK = False
    get_factor_ranker = None


class SelectionCriteria:
    """Selection criteria configuration."""
    
    # Score thresholds (relaxed for first wave)
    MIN_COMPOSITE_SCORE = 0.38
    MIN_IC = 0.005
    MIN_SHARPE = 0.15
    MAX_DECAY_SCORE = 0.55
    MIN_STABILITY = 0.30
    
    # Balance constraints
    MAX_FAMILY_SHARE = 0.50
    MIN_FAMILIES = 2
    
    # Target counts
    TARGET_FIRST_WAVE = 25     # 20-30 deployed
    TARGET_TOTAL = 50
    
    # Regime coverage
    TARGET_REGIME_COVERAGE = 0.8  # 80% of regimes


class DeploymentSelector:
    """
    Selects factors for deployment.
    
    Takes approved factors and selects the optimal set for deployment.
    """
    
    REGIMES = ["TRENDING", "RANGING", "HIGH_VOL", "LOW_VOL", "BREAKOUT"]
    
    def __init__(self, registry: DeploymentRegistry = None):
        self.registry = registry or get_deployment_registry()
        self.criteria = SelectionCriteria()
        
        self.last_selection: Optional[Dict] = None
    
    def select_for_deployment(
        self,
        factors: List[Dict] = None,
        target_count: int = None,
        shadow_mode: bool = True
    ) -> Dict:
        """
        Select factors for deployment.
        
        Args:
            factors: List of approved factors (or loads from ranker)
            target_count: Target number of deployments
            shadow_mode: Deploy in shadow mode
        
        Returns:
            Selection result with deployed factors
        """
        target = target_count or self.criteria.TARGET_FIRST_WAVE
        
        # Load factors if not provided
        if factors is None:
            if RANKER_OK:
                ranker = get_factor_ranker()
                factors = ranker.get_approved_factors()
            else:
                factors = []
        
        if not factors:
            return {
                "status": "no_factors",
                "message": "No approved factors available",
                "selected": 0
            }
        
        result = {
            "started_at": datetime.now(timezone.utc).isoformat(),
            "input_factors": len(factors),
            "target_count": target,
            "shadow_mode": shadow_mode,
            "selected": [],
            "rejected": [],
            "decisions": []
        }
        
        # Step 1: Filter by basic criteria
        candidates = self._filter_by_criteria(factors)
        result["after_filter"] = len(candidates)
        
        # Step 2: Sort by composite score
        candidates.sort(key=lambda f: f.get("composite_score", 0), reverse=True)
        
        # Step 3: Apply family balance
        selected = self._apply_family_balance(candidates, target)
        
        # Step 4: Deploy selected
        deployed = []
        for factor in selected:
            deployment = self._deploy_factor(factor, shadow_mode)
            if deployment:
                deployed.append(deployment)
                result["selected"].append({
                    "factor_id": factor.get("factor_id"),
                    "family": factor.get("family"),
                    "score": factor.get("composite_score"),
                    "deployment_id": deployment.deployment_id
                })
            else:
                result["rejected"].append({
                    "factor_id": factor.get("factor_id"),
                    "reason": "deployment_failed"
                })
        
        # Record decisions
        for factor in candidates:
            fid = factor.get("factor_id")
            is_selected = fid in [d.factor_id for d in deployed]
            
            decision = DeploymentDecision(
                decision_id="",
                factor_id=fid,
                action="deploy" if is_selected else "skip",
                reason="Selected for deployment" if is_selected else "Not selected in this wave",
                shadow_mode=shadow_mode,
                target_status=DeploymentStatus.SHADOW if shadow_mode else DeploymentStatus.ACTIVE,
                approved=is_selected,
                composite_score=factor.get("composite_score", 0),
                ic=factor.get("ic", 0),
                sharpe=factor.get("sharpe", 0),
                decay_score=factor.get("decay_score", 0)
            )
            result["decisions"].append(decision.to_dict())
        
        # Summary
        result["finished_at"] = datetime.now(timezone.utc).isoformat()
        result["total_deployed"] = len(deployed)
        result["status"] = "completed"
        
        # Coverage stats
        result["family_coverage"] = self._calculate_family_coverage(deployed)
        result["regime_coverage"] = self._calculate_regime_coverage(deployed)
        
        self.last_selection = result
        return result
    
    def _filter_by_criteria(self, factors: List[Dict]) -> List[Dict]:
        """
        Filter factors by selection criteria.
        """
        filtered = []
        
        for factor in factors:
            # Skip already deployed
            factor_id = factor.get("factor_id", "")
            if self.registry.is_deployed(factor_id):
                continue
            
            # Score check
            score = factor.get("composite_score", 0)
            if score < self.criteria.MIN_COMPOSITE_SCORE:
                continue
            
            # IC check
            ic = factor.get("ic", 0)
            if ic < self.criteria.MIN_IC:
                continue
            
            # Sharpe check
            sharpe = factor.get("sharpe", 0)
            if sharpe < self.criteria.MIN_SHARPE:
                continue
            
            # Decay check
            decay = factor.get("decay_score", 0)
            if decay > self.criteria.MAX_DECAY_SCORE:
                continue
            
            # Stability check
            stability = factor.get("stability", 0.5)
            if stability < self.criteria.MIN_STABILITY:
                continue
            
            filtered.append(factor)
        
        return filtered
    
    def _apply_family_balance(
        self,
        candidates: List[Dict],
        target_count: int
    ) -> List[Dict]:
        """
        Apply family balance constraints.
        
        Ensures no single family dominates.
        """
        selected = []
        family_counts: Dict[str, int] = defaultdict(int)
        
        # Get existing family counts
        for dep in self.registry.get_all():
            family_counts[dep.factor_family] += 1
        
        max_per_family = max(3, int(target_count * self.criteria.MAX_FAMILY_SHARE))
        
        for factor in candidates:
            if len(selected) >= target_count:
                break
            
            family = factor.get("family", "unknown")
            
            # Check family limit
            if family_counts[family] >= max_per_family:
                continue
            
            selected.append(factor)
            family_counts[family] += 1
        
        # Ensure minimum family diversity
        families_covered = len([f for f, c in family_counts.items() if c > 0])
        
        if families_covered < self.criteria.MIN_FAMILIES and len(candidates) > len(selected):
            # Try to add factors from underrepresented families
            covered_families = {factor.get("family") for factor in selected}
            for factor in candidates:
                if factor in selected:
                    continue
                
                family = factor.get("family", "unknown")
                if family not in covered_families:
                    selected.append(factor)
                    covered_families.add(family)
                    
                    if len(covered_families) >= self.criteria.MIN_FAMILIES:
                        break
        
        return selected
    
    def _deploy_factor(
        self,
        factor: Dict,
        shadow_mode: bool
    ) -> Optional[DeployedAlpha]:
        """
        Deploy a single factor.
        """
        return self.registry.register_deployment(
            factor_id=factor.get("factor_id", ""),
            factor_family=factor.get("family", "unknown"),
            factor_template=factor.get("template", ""),
            inputs=factor.get("inputs", []),
            composite_score=factor.get("composite_score", 0),
            ic=factor.get("ic", 0),
            sharpe=factor.get("sharpe", 0),
            stability=factor.get("stability", 0.5),
            decay_score=factor.get("decay_score", 0),
            regime_dependency=factor.get("regime_dependency", []),
            shadow_mode=shadow_mode
        )
    
    def _calculate_family_coverage(self, deployed: List[DeployedAlpha]) -> Dict:
        """Calculate family distribution."""
        family_counts = defaultdict(int)
        for dep in deployed:
            family_counts[dep.factor_family] += 1
        
        total = len(deployed) or 1
        return {
            family: {"count": count, "share": round(count / total, 2)}
            for family, count in family_counts.items()
        }
    
    def _calculate_regime_coverage(self, deployed: List[DeployedAlpha]) -> Dict:
        """Calculate regime coverage."""
        regime_counts = defaultdict(int)
        
        for dep in deployed:
            for regime in dep.regime_dependency or self.REGIMES:
                regime_counts[regime] += 1
        
        total_regimes = len(self.REGIMES)
        covered_regimes = len([r for r in self.REGIMES if regime_counts.get(r, 0) > 0])
        
        return {
            "by_regime": dict(regime_counts),
            "coverage_ratio": round(covered_regimes / total_regimes, 2),
            "covered_regimes": covered_regimes,
            "total_regimes": total_regimes
        }
    
    def get_selection_stats(self) -> Dict:
        """Get selection statistics."""
        return {
            "last_selection": self.last_selection,
            "criteria": {
                "min_composite_score": self.criteria.MIN_COMPOSITE_SCORE,
                "min_ic": self.criteria.MIN_IC,
                "min_sharpe": self.criteria.MIN_SHARPE,
                "max_decay": self.criteria.MAX_DECAY_SCORE,
                "min_stability": self.criteria.MIN_STABILITY,
                "max_family_share": self.criteria.MAX_FAMILY_SHARE,
                "target_first_wave": self.criteria.TARGET_FIRST_WAVE
            }
        }
