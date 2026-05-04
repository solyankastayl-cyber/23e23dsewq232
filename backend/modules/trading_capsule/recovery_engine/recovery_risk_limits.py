"""
Recovery Risk Limits
====================

Risk limits for Recovery Engine (PHASE 1.4)
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass

from .recovery_types import (
    RiskLimitsResult,
    PositionHealthResult,
    RecoveryConfig
)


class RecoveryRiskLimits:
    """
    Enforces risk limits for recovery operations.
    
    This is the most critical component - recovery must
    never increase total risk beyond defined limits.
    """
    
    def __init__(self):
        self._default_config = RecoveryConfig()
    
    def check_position_health(
        self,
        current_loss_r: float,
        structure_valid: bool = True,
        max_loss_r: float = 1.5
    ) -> PositionHealthResult:
        """
        Check if position is healthy enough for recovery.
        
        Args:
            current_loss_r: Current loss in R multiples
            structure_valid: Is position structure still valid
            max_loss_r: Maximum allowed loss for recovery
        """
        
        notes = []
        
        # Check loss level
        loss_ok = current_loss_r <= max_loss_r
        
        if not loss_ok:
            notes.append(f"Position loss {current_loss_r:.2f}R exceeds max {max_loss_r}R")
        else:
            notes.append(f"Position loss {current_loss_r:.2f}R within limits")
        
        # Check structure
        if not structure_valid:
            notes.append("Position structure invalidated")
        
        healthy = loss_ok and structure_valid
        
        if healthy:
            reason = "Position healthy for recovery"
        else:
            reasons = []
            if not loss_ok:
                reasons.append(f"loss > {max_loss_r}R")
            if not structure_valid:
                reasons.append("structure invalid")
            reason = f"Position too unhealthy: {', '.join(reasons)}"
        
        return PositionHealthResult(
            healthy=healthy,
            current_loss_r=current_loss_r,
            max_allowed_loss_r=max_loss_r,
            structure_valid=structure_valid,
            reason=reason,
            notes=notes
        )
    
    def check_risk_limits(
        self,
        current_adds: int,
        current_exposure: float,
        portfolio_exposure_pct: float,
        daily_loss_pct: float = 0.0,
        config: Optional[RecoveryConfig] = None
    ) -> RiskLimitsResult:
        """
        Check if recovery is within risk limits.
        
        Args:
            current_adds: Number of adds already made
            current_exposure: Current position exposure (1.0 = base)
            portfolio_exposure_pct: Position % of portfolio
            daily_loss_pct: Daily PnL %
            config: Recovery config (uses default if None)
        """
        
        cfg = config or self._default_config
        notes = []
        violations = []
        
        # Check max adds
        adds_ok = current_adds < cfg.max_adds
        if not adds_ok:
            violations.append(f"max adds reached ({current_adds}/{cfg.max_adds})")
        else:
            notes.append(f"Adds: {current_adds}/{cfg.max_adds}")
        
        # Check exposure limit
        exposure_ok = current_exposure < cfg.max_total_exposure
        if not exposure_ok:
            violations.append(f"exposure limit ({current_exposure:.2f}x/{cfg.max_total_exposure}x)")
        else:
            notes.append(f"Exposure: {current_exposure:.2f}x/{cfg.max_total_exposure}x")
        
        # Check portfolio exposure
        portfolio_ok = portfolio_exposure_pct < cfg.max_portfolio_exposure_pct
        if not portfolio_ok:
            violations.append(f"portfolio limit ({portfolio_exposure_pct:.1f}%/{cfg.max_portfolio_exposure_pct}%)")
        else:
            notes.append(f"Portfolio: {portfolio_exposure_pct:.1f}%/{cfg.max_portfolio_exposure_pct}%")
        
        # Check daily loss limit (5% max)
        max_daily_loss = 5.0
        daily_ok = daily_loss_pct > -max_daily_loss
        if not daily_ok:
            violations.append(f"daily loss limit ({daily_loss_pct:.1f}%)")
        
        within_limits = adds_ok and exposure_ok and portfolio_ok and daily_ok
        
        if within_limits:
            reason = "Within all risk limits"
        else:
            reason = f"Risk limits violated: {'; '.join(violations)}"
        
        return RiskLimitsResult(
            within_limits=within_limits,
            current_adds=current_adds,
            max_adds=cfg.max_adds,
            current_exposure=current_exposure,
            max_exposure=cfg.max_total_exposure,
            portfolio_exposure_pct=portfolio_exposure_pct,
            max_portfolio_pct=cfg.max_portfolio_exposure_pct,
            reason=reason,
            notes=notes
        )
    
    def calculate_add_size(
        self,
        base_size: float,
        current_adds: int,
        regime_multiplier: float = 1.0,
        config: Optional[RecoveryConfig] = None
    ) -> Dict[str, Any]:
        """
        Calculate recommended add size.
        
        Each add is smaller than the previous.
        """
        
        cfg = config or self._default_config
        
        # Base multiplier decreases with each add
        # Add 0: 0.5x base
        # Add 1: 0.25x base
        add_multiplier = cfg.add_size_multiplier * (cfg.add_size_multiplier ** current_adds)
        
        # Apply regime multiplier
        add_multiplier *= regime_multiplier
        
        # Ensure minimum size
        add_multiplier = max(add_multiplier, cfg.min_add_size_pct)
        
        add_size = base_size * add_multiplier
        
        return {
            "addSize": round(add_size, 4),
            "addMultiplier": round(add_multiplier, 4),
            "baseSize": round(base_size, 4),
            "addNumber": current_adds + 1,
            "regimeMultiplier": round(regime_multiplier, 4)
        }
    
    def calculate_new_average(
        self,
        current_avg_price: float,
        current_size: float,
        add_price: float,
        add_size: float
    ) -> Dict[str, Any]:
        """
        Calculate new average price after add.
        """
        
        total_cost = (current_avg_price * current_size) + (add_price * add_size)
        new_size = current_size + add_size
        new_avg = total_cost / new_size if new_size > 0 else current_avg_price
        
        improvement_pct = ((current_avg_price - new_avg) / current_avg_price) * 100
        
        return {
            "newAveragePrice": round(new_avg, 8),
            "previousAverage": round(current_avg_price, 8),
            "newTotalSize": round(new_size, 4),
            "improvementPct": round(improvement_pct, 4)
        }
    
    def get_risk_limits_summary(self, config: Optional[RecoveryConfig] = None) -> Dict[str, Any]:
        """Get summary of risk limits"""
        cfg = config or self._default_config
        
        return {
            "maxAdds": cfg.max_adds,
            "maxTotalExposure": cfg.max_total_exposure,
            "maxPortfolioExposurePct": cfg.max_portfolio_exposure_pct,
            "addSizeMultiplier": cfg.add_size_multiplier,
            "minAddSizePct": cfg.min_add_size_pct,
            "maxPositionLossR": cfg.max_position_loss_r,
            "requireStructureIntact": cfg.require_structure_intact,
            "description": "Recovery is strictly bounded - never exceeds these limits"
        }


# Global singleton
recovery_risk_limits = RecoveryRiskLimits()
