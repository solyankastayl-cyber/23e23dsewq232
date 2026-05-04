"""
PHASE 13.7 - Deployment Registry
==================================
Manages deployed factors and their status.

Responsibilities:
- Track which factors are deployed
- Track deployment status (shadow, active, paused)
- Manage family balance
- Enforce deployment constraints
"""

from typing import Dict, List, Optional, Set
from datetime import datetime, timezone
from collections import defaultdict

from .deployment_types import (
    DeployedAlpha,
    DeploymentStatus,
    DeploymentMode,
    DeploymentDecision,
    DeploymentSnapshot,
    RiskProfile
)
from .deployment_repository import DeploymentRepository


class DeploymentRegistry:
    """
    Registry for deployed factors.
    
    Manages:
    - Deployment status tracking
    - Family balance constraints
    - Regime coverage
    """
    
    # Constraints
    MAX_ACTIVE_DEPLOYMENTS = 50
    MAX_SHADOW_DEPLOYMENTS = 100
    MAX_PER_FAMILY = 10
    MIN_COMPOSITE_SCORE = 0.45
    
    def __init__(self):
        self.repository = DeploymentRepository()
        
        # In-memory cache
        self._cache: Dict[str, DeployedAlpha] = {}
        self._active_ids: Set[str] = set()
        self._shadow_ids: Set[str] = set()
        self._family_counts: Dict[str, int] = defaultdict(int)
        
        # Load from DB
        self._load_from_db()
    
    def _load_from_db(self):
        """Load deployments from database."""
        try:
            # Load active
            active = self.repository.get_active_deployments()
            for dep in active:
                self._cache[dep.factor_id] = dep
                self._active_ids.add(dep.factor_id)
                self._family_counts[dep.factor_family] += 1
            
            # Load shadow
            shadow = self.repository.get_shadow_deployments()
            for dep in shadow:
                self._cache[dep.factor_id] = dep
                self._shadow_ids.add(dep.factor_id)
                self._family_counts[dep.factor_family] += 1
            
            print(f"[DeploymentRegistry] Loaded {len(active)} active, {len(shadow)} shadow")
            
        except Exception as e:
            print(f"[DeploymentRegistry] Load error: {e}")
    
    def register_deployment(
        self,
        factor_id: str,
        factor_family: str,
        factor_template: str,
        inputs: List[str],
        composite_score: float,
        ic: float = 0.0,
        sharpe: float = 0.0,
        stability: float = 0.0,
        decay_score: float = 0.0,
        regime_dependency: List[str] = None,
        shadow_mode: bool = True
    ) -> Optional[DeployedAlpha]:
        """
        Register a factor for deployment.
        
        Args:
            factor_id: Factor ID
            factor_family: Factor family
            factor_template: Template used
            inputs: Input features
            composite_score: Ranking score
            ic: Information coefficient
            sharpe: Sharpe ratio
            stability: Factor stability
            decay_score: Current decay
            regime_dependency: Required regimes
            shadow_mode: Start in shadow mode
        
        Returns:
            DeployedAlpha or None if rejected
        """
        # Check if already deployed
        if factor_id in self._cache:
            return self._cache[factor_id]
        
        # Validate score
        if composite_score < self.MIN_COMPOSITE_SCORE:
            return None
        
        # Check family limit
        if self._family_counts[factor_family] >= self.MAX_PER_FAMILY:
            return None
        
        # Check total limits
        if shadow_mode and len(self._shadow_ids) >= self.MAX_SHADOW_DEPLOYMENTS:
            return None
        if not shadow_mode and len(self._active_ids) >= self.MAX_ACTIVE_DEPLOYMENTS:
            return None
        
        # Create deployment
        deployment = DeployedAlpha(
            deployment_id="",  # Auto-generated
            factor_id=factor_id,
            factor_family=factor_family,
            factor_template=factor_template,
            inputs=inputs,
            deployment_mode=DeploymentMode.SHADOW if shadow_mode else DeploymentMode.LIMITED,
            status=DeploymentStatus.SHADOW if shadow_mode else DeploymentStatus.ACTIVE,
            weight=self._calculate_initial_weight(composite_score),
            regime_dependency=regime_dependency or [],
            composite_score=composite_score,
            ic=ic,
            sharpe=sharpe,
            stability=stability,
            decay_score=decay_score,
            shadow_mode=shadow_mode,
            created_at=datetime.now(timezone.utc)
        )
        
        # Save
        if self.repository.save_deployment(deployment):
            self._cache[factor_id] = deployment
            if shadow_mode:
                self._shadow_ids.add(factor_id)
            else:
                self._active_ids.add(factor_id)
            self._family_counts[factor_family] += 1
            
            # Record decision
            decision = DeploymentDecision(
                decision_id="",
                factor_id=factor_id,
                action="deploy",
                reason=f"Registered with score {composite_score:.3f}",
                shadow_mode=shadow_mode,
                target_status=deployment.status,
                approved=True,
                composite_score=composite_score,
                ic=ic,
                sharpe=sharpe,
                decay_score=decay_score
            )
            self.repository.save_decision(decision)
            
            return deployment
        
        return None
    
    def _calculate_initial_weight(self, composite_score: float) -> float:
        """Calculate initial weight based on score."""
        if composite_score >= 0.75:
            return 1.0
        elif composite_score >= 0.65:
            return 0.8
        elif composite_score >= 0.55:
            return 0.6
        else:
            return 0.4
    
    def activate(self, factor_id: str, reason: str = "") -> bool:
        """
        Move deployment from shadow to active.
        """
        if factor_id not in self._cache:
            return False
        
        deployment = self._cache[factor_id]
        
        if deployment.status != DeploymentStatus.SHADOW:
            return False
        
        # Check active limit
        if len(self._active_ids) >= self.MAX_ACTIVE_DEPLOYMENTS:
            return False
        
        # Update status
        deployment.status = DeploymentStatus.ACTIVE
        deployment.deployment_mode = DeploymentMode.GRADUATED
        deployment.shadow_mode = False
        deployment.deployed_at = datetime.now(timezone.utc)
        deployment.updated_at = datetime.now(timezone.utc)
        
        if self.repository.save_deployment(deployment):
            self._shadow_ids.discard(factor_id)
            self._active_ids.add(factor_id)
            
            # Record decision
            decision = DeploymentDecision(
                decision_id="",
                factor_id=factor_id,
                action="activate",
                reason=reason or "Graduated from shadow",
                shadow_mode=False,
                target_status=DeploymentStatus.ACTIVE,
                approved=True,
                composite_score=deployment.composite_score,
                ic=deployment.ic,
                sharpe=deployment.sharpe
            )
            self.repository.save_decision(decision)
            
            return True
        
        return False
    
    def pause(self, factor_id: str, reason: str = "") -> bool:
        """
        Pause a deployment.
        """
        if factor_id not in self._cache:
            return False
        
        deployment = self._cache[factor_id]
        
        if deployment.status == DeploymentStatus.PAUSED:
            return True
        
        old_status = deployment.status
        deployment.status = DeploymentStatus.PAUSED
        deployment.pause_reason = reason
        deployment.updated_at = datetime.now(timezone.utc)
        
        if self.repository.save_deployment(deployment):
            self._active_ids.discard(factor_id)
            self._shadow_ids.discard(factor_id)
            
            # Record decision
            decision = DeploymentDecision(
                decision_id="",
                factor_id=factor_id,
                action="pause",
                reason=reason or "Manual pause",
                target_status=DeploymentStatus.PAUSED,
                approved=True,
                composite_score=deployment.composite_score
            )
            self.repository.save_decision(decision)
            
            return True
        
        return False
    
    def resume(self, factor_id: str, to_shadow: bool = True) -> bool:
        """
        Resume a paused deployment.
        """
        if factor_id not in self._cache:
            return False
        
        deployment = self._cache[factor_id]
        
        if deployment.status != DeploymentStatus.PAUSED:
            return False
        
        new_status = DeploymentStatus.SHADOW if to_shadow else DeploymentStatus.ACTIVE
        deployment.status = new_status
        deployment.shadow_mode = to_shadow
        deployment.pause_reason = None
        deployment.auto_paused = False
        deployment.updated_at = datetime.now(timezone.utc)
        
        if self.repository.save_deployment(deployment):
            if to_shadow:
                self._shadow_ids.add(factor_id)
            else:
                self._active_ids.add(factor_id)
            
            return True
        
        return False
    
    def set_shadow(self, factor_id: str, reason: str = "") -> bool:
        """
        Move deployment to shadow mode.
        """
        if factor_id not in self._cache:
            return False
        
        deployment = self._cache[factor_id]
        
        if deployment.status == DeploymentStatus.SHADOW:
            return True
        
        deployment.status = DeploymentStatus.SHADOW
        deployment.deployment_mode = DeploymentMode.SHADOW
        deployment.shadow_mode = True
        deployment.updated_at = datetime.now(timezone.utc)
        
        if self.repository.save_deployment(deployment):
            self._active_ids.discard(factor_id)
            self._shadow_ids.add(factor_id)
            
            decision = DeploymentDecision(
                decision_id="",
                factor_id=factor_id,
                action="shadow",
                reason=reason or "Moved to shadow",
                shadow_mode=True,
                target_status=DeploymentStatus.SHADOW,
                approved=True,
                composite_score=deployment.composite_score
            )
            self.repository.save_decision(decision)
            
            return True
        
        return False
    
    def get_deployment(self, factor_id: str) -> Optional[DeployedAlpha]:
        """Get deployment by factor ID."""
        return self._cache.get(factor_id)
    
    def get_active(self) -> List[DeployedAlpha]:
        """Get all active deployments."""
        return [self._cache[fid] for fid in self._active_ids if fid in self._cache]
    
    def get_shadow(self) -> List[DeployedAlpha]:
        """Get all shadow deployments."""
        return [self._cache[fid] for fid in self._shadow_ids if fid in self._cache]
    
    def get_all(self) -> List[DeployedAlpha]:
        """Get all deployments."""
        return list(self._cache.values())
    
    def is_deployed(self, factor_id: str) -> bool:
        """Check if factor is deployed."""
        return factor_id in self._cache
    
    def is_active(self, factor_id: str) -> bool:
        """Check if factor is active."""
        return factor_id in self._active_ids
    
    def is_shadow(self, factor_id: str) -> bool:
        """Check if factor is in shadow."""
        return factor_id in self._shadow_ids
    
    def update_live_metrics(
        self,
        factor_id: str,
        live_ic: float = None,
        live_sharpe: float = None,
        live_hit_rate: float = None,
        signal_count_delta: int = 0,
        profitable_signals_delta: int = 0
    ) -> bool:
        """
        Update live performance metrics.
        """
        if factor_id not in self._cache:
            return False
        
        deployment = self._cache[factor_id]
        
        if live_ic is not None:
            deployment.live_ic = live_ic
        if live_sharpe is not None:
            deployment.live_sharpe = live_sharpe
        if live_hit_rate is not None:
            deployment.live_hit_rate = live_hit_rate
        
        deployment.signal_count += signal_count_delta
        deployment.profitable_signals += profitable_signals_delta
        deployment.last_signal_at = datetime.now(timezone.utc)
        deployment.updated_at = datetime.now(timezone.utc)
        
        return self.repository.save_deployment(deployment)
    
    def create_snapshot(self) -> DeploymentSnapshot:
        """Create a snapshot of current state."""
        active = self.get_active()
        shadow = self.get_shadow()
        
        # Family breakdown
        family_breakdown = {}
        for dep in list(active) + list(shadow):
            family = dep.factor_family
            family_breakdown[family] = family_breakdown.get(family, 0) + 1
        
        # Regime coverage
        regime_coverage = {}
        for dep in list(active) + list(shadow):
            for regime in dep.regime_dependency:
                regime_coverage[regime] = regime_coverage.get(regime, 0) + 1
        
        # Averages
        all_deps = list(active) + list(shadow)
        avg_score = sum(d.composite_score for d in all_deps) / len(all_deps) if all_deps else 0
        avg_hit = sum(d.live_hit_rate for d in all_deps) / len(all_deps) if all_deps else 0
        
        snapshot = DeploymentSnapshot(
            snapshot_id="",
            total_deployed=len(all_deps),
            active_count=len(active),
            shadow_count=len(shadow),
            paused_count=len([d for d in self._cache.values() if d.status == DeploymentStatus.PAUSED]),
            family_breakdown=family_breakdown,
            regime_coverage=regime_coverage,
            avg_composite_score=avg_score,
            avg_live_hit_rate=avg_hit
        )
        
        self.repository.save_snapshot(snapshot)
        return snapshot
    
    def get_stats(self) -> Dict:
        """Get registry statistics."""
        return {
            "total_cached": len(self._cache),
            "active_count": len(self._active_ids),
            "shadow_count": len(self._shadow_ids),
            "family_counts": dict(self._family_counts),
            "repository": self.repository.get_stats(),
            "constraints": {
                "max_active": self.MAX_ACTIVE_DEPLOYMENTS,
                "max_shadow": self.MAX_SHADOW_DEPLOYMENTS,
                "max_per_family": self.MAX_PER_FAMILY,
                "min_score": self.MIN_COMPOSITE_SCORE
            }
        }


# Global singleton
_registry_instance: Optional[DeploymentRegistry] = None


def get_deployment_registry() -> DeploymentRegistry:
    """Get singleton registry instance."""
    global _registry_instance
    if _registry_instance is None:
        _registry_instance = DeploymentRegistry()
    return _registry_instance
