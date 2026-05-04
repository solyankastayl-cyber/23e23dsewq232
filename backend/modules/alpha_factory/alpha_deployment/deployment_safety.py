"""
PHASE 13.7 - Deployment Safety
================================
Safety layer for Alpha Deployment.

Features:
- Shadow mode enforcement
- Minimum sample threshold
- Cooldown after activation
- Max live weight
- Auto-pause on decay
"""

from typing import Dict, List, Optional
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass

from .deployment_types import (
    DeployedAlpha,
    DeploymentStatus,
    DeploymentMode
)
from .deployment_registry import DeploymentRegistry, get_deployment_registry


@dataclass
class SafetyConfig:
    """Safety configuration."""
    
    # Shadow mode requirements
    MIN_SHADOW_SAMPLES: int = 50         # Minimum signals before activation
    MIN_SHADOW_DAYS: int = 3             # Minimum days in shadow
    MIN_SHADOW_HIT_RATE: float = 0.45    # Minimum hit rate to activate
    
    # Cooldown
    COOLDOWN_AFTER_ACTIVATION_HOURS: int = 6
    COOLDOWN_AFTER_PAUSE_HOURS: int = 2
    
    # Weight limits
    MAX_LIVE_WEIGHT: float = 0.15        # Max weight for any single factor
    MAX_TOTAL_WEIGHT: float = 1.0        # Max total weight (normalized)
    
    # Auto-pause thresholds
    AUTO_PAUSE_DECAY_THRESHOLD: float = 0.5
    AUTO_PAUSE_HIT_RATE_THRESHOLD: float = 0.35
    AUTO_PAUSE_CONSECUTIVE_LOSSES: int = 5
    
    # Performance degradation
    IC_DEGRADATION_THRESHOLD: float = 0.5  # Pause if IC drops by 50%
    SHARPE_DEGRADATION_THRESHOLD: float = 0.5


class DeploymentSafety:
    """
    Safety layer for deployment management.
    
    Enforces:
    - Shadow mode graduation criteria
    - Weight limits
    - Auto-pause rules
    - Cooldown periods
    """
    
    def __init__(
        self,
        registry: DeploymentRegistry = None,
        config: SafetyConfig = None
    ):
        self.registry = registry or get_deployment_registry()
        self.config = config or SafetyConfig()
        
        # Track consecutive losses per deployment
        self._consecutive_losses: Dict[str, int] = {}
    
    def check_activation_eligibility(
        self,
        deployment: DeployedAlpha
    ) -> Dict:
        """
        Check if deployment can be activated from shadow.
        
        Returns criteria check results.
        """
        result = {
            "factor_id": deployment.factor_id,
            "eligible": True,
            "criteria": {},
            "blocking_issues": []
        }
        
        # Must be in shadow
        if deployment.status != DeploymentStatus.SHADOW:
            result["eligible"] = False
            result["blocking_issues"].append("Not in shadow mode")
            return result
        
        # Check cooldown
        if deployment.is_in_cooldown:
            result["eligible"] = False
            result["blocking_issues"].append("In cooldown period")
            result["criteria"]["cooldown_clear"] = False
        else:
            result["criteria"]["cooldown_clear"] = True
        
        # Minimum samples
        min_samples = self.config.MIN_SHADOW_SAMPLES
        has_min_samples = deployment.signal_count >= min_samples
        result["criteria"]["min_samples"] = {
            "required": min_samples,
            "actual": deployment.signal_count,
            "passed": has_min_samples
        }
        if not has_min_samples:
            result["eligible"] = False
            result["blocking_issues"].append(f"Need {min_samples} samples, have {deployment.signal_count}")
        
        # Minimum days
        if deployment.created_at:
            days_in_shadow = (datetime.now(timezone.utc) - deployment.created_at).days
        else:
            days_in_shadow = 0
        
        min_days = self.config.MIN_SHADOW_DAYS
        has_min_days = days_in_shadow >= min_days
        result["criteria"]["min_days"] = {
            "required": min_days,
            "actual": days_in_shadow,
            "passed": has_min_days
        }
        if not has_min_days:
            result["eligible"] = False
            result["blocking_issues"].append(f"Need {min_days} days in shadow, have {days_in_shadow}")
        
        # Hit rate
        min_hit_rate = self.config.MIN_SHADOW_HIT_RATE
        actual_hit_rate = deployment.live_hit_rate_pct / 100 if deployment.signal_count > 0 else 0
        has_hit_rate = actual_hit_rate >= min_hit_rate
        result["criteria"]["hit_rate"] = {
            "required": min_hit_rate,
            "actual": actual_hit_rate,
            "passed": has_hit_rate
        }
        if not has_hit_rate:
            result["eligible"] = False
            result["blocking_issues"].append(f"Hit rate {actual_hit_rate:.2%} below {min_hit_rate:.2%}")
        
        return result
    
    def check_auto_pause(self, deployment: DeployedAlpha) -> Dict:
        """
        Check if deployment should be auto-paused.
        
        Returns auto-pause check results.
        """
        result = {
            "factor_id": deployment.factor_id,
            "should_pause": False,
            "checks": {},
            "reasons": []
        }
        
        # Only check active deployments
        if deployment.status != DeploymentStatus.ACTIVE:
            return result
        
        # Check decay
        decay_threshold = self.config.AUTO_PAUSE_DECAY_THRESHOLD
        if deployment.decay_score > decay_threshold:
            result["should_pause"] = True
            result["reasons"].append(f"Decay {deployment.decay_score:.2f} exceeds threshold {decay_threshold}")
            result["checks"]["decay"] = {
                "threshold": decay_threshold,
                "actual": deployment.decay_score,
                "triggered": True
            }
        else:
            result["checks"]["decay"] = {
                "threshold": decay_threshold,
                "actual": deployment.decay_score,
                "triggered": False
            }
        
        # Check hit rate
        hit_rate_threshold = self.config.AUTO_PAUSE_HIT_RATE_THRESHOLD
        if deployment.signal_count > 10:  # Only after sufficient samples
            actual_hit_rate = deployment.live_hit_rate_pct / 100
            if actual_hit_rate < hit_rate_threshold:
                result["should_pause"] = True
                result["reasons"].append(f"Hit rate {actual_hit_rate:.2%} below {hit_rate_threshold:.2%}")
                result["checks"]["hit_rate"] = {
                    "threshold": hit_rate_threshold,
                    "actual": actual_hit_rate,
                    "triggered": True
                }
            else:
                result["checks"]["hit_rate"] = {
                    "threshold": hit_rate_threshold,
                    "actual": actual_hit_rate,
                    "triggered": False
                }
        
        # Check consecutive losses
        cons_losses = self._consecutive_losses.get(deployment.factor_id, 0)
        max_cons_losses = self.config.AUTO_PAUSE_CONSECUTIVE_LOSSES
        if cons_losses >= max_cons_losses:
            result["should_pause"] = True
            result["reasons"].append(f"{cons_losses} consecutive losses")
            result["checks"]["consecutive_losses"] = {
                "threshold": max_cons_losses,
                "actual": cons_losses,
                "triggered": True
            }
        else:
            result["checks"]["consecutive_losses"] = {
                "threshold": max_cons_losses,
                "actual": cons_losses,
                "triggered": False
            }
        
        # Check IC degradation
        if deployment.ic > 0 and deployment.live_ic > 0:
            ic_change = (deployment.live_ic - deployment.ic) / deployment.ic
            if ic_change < -self.config.IC_DEGRADATION_THRESHOLD:
                result["should_pause"] = True
                result["reasons"].append(f"IC degraded by {abs(ic_change):.2%}")
                result["checks"]["ic_degradation"] = {
                    "threshold": self.config.IC_DEGRADATION_THRESHOLD,
                    "actual_change": ic_change,
                    "triggered": True
                }
        
        return result
    
    def enforce_weight_limits(self, deployment: DeployedAlpha) -> float:
        """
        Enforce weight limits on deployment.
        
        Returns adjusted weight.
        """
        max_weight = self.config.MAX_LIVE_WEIGHT
        
        # Cap individual weight
        adjusted = min(deployment.weight, max_weight)
        
        # Reduce if in cooldown
        if deployment.is_in_cooldown:
            adjusted *= 0.5
        
        # Reduce if performance degraded
        if deployment.live_ic > 0 and deployment.ic > 0:
            ic_ratio = deployment.live_ic / deployment.ic
            if ic_ratio < 0.8:
                adjusted *= max(0.3, ic_ratio)
        
        return round(adjusted, 4)
    
    def set_cooldown(
        self,
        factor_id: str,
        hours: int = None,
        reason: str = "manual"
    ) -> bool:
        """
        Set cooldown period for deployment.
        """
        deployment = self.registry.get_deployment(factor_id)
        if not deployment:
            return False
        
        cooldown_hours = hours or self.config.COOLDOWN_AFTER_ACTIVATION_HOURS
        deployment.cooldown_until = datetime.now(timezone.utc) + timedelta(hours=cooldown_hours)
        deployment.updated_at = datetime.now(timezone.utc)
        
        return self.registry.repository.save_deployment(deployment)
    
    def record_signal_outcome(
        self,
        factor_id: str,
        profitable: bool
    ):
        """
        Record signal outcome for consecutive loss tracking.
        """
        if profitable:
            self._consecutive_losses[factor_id] = 0
        else:
            self._consecutive_losses[factor_id] = self._consecutive_losses.get(factor_id, 0) + 1
    
    def run_safety_scan(self) -> Dict:
        """
        Run safety scan on all active deployments.
        
        Returns scan results with any auto-pause actions.
        """
        results = {
            "scanned_at": datetime.now(timezone.utc).isoformat(),
            "active_checked": 0,
            "shadow_checked": 0,
            "auto_paused": [],
            "eligible_for_activation": [],
            "warnings": []
        }
        
        # Check active deployments for auto-pause
        active = self.registry.get_active()
        results["active_checked"] = len(active)
        
        for deployment in active:
            pause_check = self.check_auto_pause(deployment)
            if pause_check["should_pause"]:
                # Auto-pause
                reason = "; ".join(pause_check["reasons"])
                if self.registry.pause(deployment.factor_id, reason=f"Auto: {reason}"):
                    deployment.auto_paused = True
                    results["auto_paused"].append({
                        "factor_id": deployment.factor_id,
                        "reasons": pause_check["reasons"]
                    })
        
        # Check shadow deployments for activation eligibility
        shadow = self.registry.get_shadow()
        results["shadow_checked"] = len(shadow)
        
        for deployment in shadow:
            activation_check = self.check_activation_eligibility(deployment)
            if activation_check["eligible"]:
                results["eligible_for_activation"].append({
                    "factor_id": deployment.factor_id,
                    "criteria": activation_check["criteria"]
                })
        
        return results
    
    def get_safety_stats(self) -> Dict:
        """Get safety statistics."""
        return {
            "config": {
                "min_shadow_samples": self.config.MIN_SHADOW_SAMPLES,
                "min_shadow_days": self.config.MIN_SHADOW_DAYS,
                "min_shadow_hit_rate": self.config.MIN_SHADOW_HIT_RATE,
                "cooldown_hours": self.config.COOLDOWN_AFTER_ACTIVATION_HOURS,
                "max_live_weight": self.config.MAX_LIVE_WEIGHT,
                "auto_pause_decay": self.config.AUTO_PAUSE_DECAY_THRESHOLD,
                "auto_pause_hit_rate": self.config.AUTO_PAUSE_HIT_RATE_THRESHOLD,
                "auto_pause_cons_losses": self.config.AUTO_PAUSE_CONSECUTIVE_LOSSES
            },
            "consecutive_losses_tracked": len(self._consecutive_losses)
        }
