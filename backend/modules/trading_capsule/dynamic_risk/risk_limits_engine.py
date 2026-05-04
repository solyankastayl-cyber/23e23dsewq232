"""
Risk Limits Engine
==================

PHASE 3.3 - Manages exposure limits across multiple dimensions.
"""

import time
from typing import Dict, List, Optional, Any

from .risk_types import (
    ExposureType,
    ExposureLimit,
    ExposureSummary
)


class RiskLimitsEngine:
    """
    Manages exposure limits:
    - Single trade exposure
    - Strategy exposure
    - Asset exposure
    - Regime exposure
    - Direction exposure
    - Portfolio exposure
    """
    
    def __init__(self):
        # Default limits
        self._limits = {
            ExposureType.SINGLE_TRADE: 2.0,
            ExposureType.STRATEGY: 4.0,
            ExposureType.ASSET: 3.0,
            ExposureType.REGIME: 5.0,
            ExposureType.DIRECTION: 6.0,
            ExposureType.PORTFOLIO: 15.0
        }
        
        # Current exposures
        self._exposures: Dict[str, Dict[str, float]] = {
            ExposureType.STRATEGY.value: {},
            ExposureType.ASSET.value: {},
            ExposureType.REGIME.value: {},
            ExposureType.DIRECTION.value: {}
        }
        
        # Position tracking
        self._positions: Dict[str, Dict[str, Any]] = {}
        
        # Warning thresholds (% of limit)
        self._warning_threshold = 0.75
        
        print("[RiskLimitsEngine] Initialized (PHASE 3.3)")
    
    def check_limits(
        self,
        risk_pct: float,
        symbol: str,
        strategy: str,
        direction: str,
        regime: str
    ) -> Dict[str, Any]:
        """
        Check all limits for a potential position.
        """
        
        violations = []
        warnings = []
        
        # Single trade limit
        if risk_pct > self._limits[ExposureType.SINGLE_TRADE]:
            violations.append({
                "type": ExposureType.SINGLE_TRADE.value,
                "limit": self._limits[ExposureType.SINGLE_TRADE],
                "requested": risk_pct
            })
        
        # Strategy limit
        strategy_current = self._exposures[ExposureType.STRATEGY.value].get(strategy, 0)
        strategy_after = strategy_current + risk_pct
        if strategy_after > self._limits[ExposureType.STRATEGY]:
            violations.append({
                "type": ExposureType.STRATEGY.value,
                "category": strategy,
                "current": strategy_current,
                "limit": self._limits[ExposureType.STRATEGY],
                "after": strategy_after
            })
        elif strategy_after > self._limits[ExposureType.STRATEGY] * self._warning_threshold:
            warnings.append(f"Strategy {strategy} approaching limit ({strategy_after:.1f}%/{self._limits[ExposureType.STRATEGY]}%)")
        
        # Asset limit
        asset_current = self._exposures[ExposureType.ASSET.value].get(symbol, 0)
        asset_after = asset_current + risk_pct
        if asset_after > self._limits[ExposureType.ASSET]:
            violations.append({
                "type": ExposureType.ASSET.value,
                "category": symbol,
                "current": asset_current,
                "limit": self._limits[ExposureType.ASSET],
                "after": asset_after
            })
        elif asset_after > self._limits[ExposureType.ASSET] * self._warning_threshold:
            warnings.append(f"Asset {symbol} approaching limit ({asset_after:.1f}%/{self._limits[ExposureType.ASSET]}%)")
        
        # Regime limit
        regime_current = self._exposures[ExposureType.REGIME.value].get(regime, 0)
        regime_after = regime_current + risk_pct
        if regime_after > self._limits[ExposureType.REGIME]:
            violations.append({
                "type": ExposureType.REGIME.value,
                "category": regime,
                "current": regime_current,
                "limit": self._limits[ExposureType.REGIME],
                "after": regime_after
            })
        elif regime_after > self._limits[ExposureType.REGIME] * self._warning_threshold:
            warnings.append(f"Regime {regime} approaching limit ({regime_after:.1f}%/{self._limits[ExposureType.REGIME]}%)")
        
        # Direction limit
        direction_current = self._exposures[ExposureType.DIRECTION.value].get(direction, 0)
        direction_after = direction_current + risk_pct
        if direction_after > self._limits[ExposureType.DIRECTION]:
            violations.append({
                "type": ExposureType.DIRECTION.value,
                "category": direction,
                "current": direction_current,
                "limit": self._limits[ExposureType.DIRECTION],
                "after": direction_after
            })
        elif direction_after > self._limits[ExposureType.DIRECTION] * self._warning_threshold:
            warnings.append(f"Direction {direction} approaching limit ({direction_after:.1f}%/{self._limits[ExposureType.DIRECTION]}%)")
        
        # Portfolio limit
        portfolio_current = self._get_total_exposure()
        portfolio_after = portfolio_current + risk_pct
        if portfolio_after > self._limits[ExposureType.PORTFOLIO]:
            violations.append({
                "type": ExposureType.PORTFOLIO.value,
                "current": portfolio_current,
                "limit": self._limits[ExposureType.PORTFOLIO],
                "after": portfolio_after
            })
        elif portfolio_after > self._limits[ExposureType.PORTFOLIO] * self._warning_threshold:
            warnings.append(f"Portfolio approaching limit ({portfolio_after:.1f}%/{self._limits[ExposureType.PORTFOLIO]}%)")
        
        return {
            "canProceed": len(violations) == 0,
            "violations": violations,
            "warnings": warnings,
            "requestedRisk": round(risk_pct, 2),
            "portfolioExposure": {
                "current": round(portfolio_current, 2),
                "after": round(portfolio_after, 2),
                "limit": self._limits[ExposureType.PORTFOLIO]
            }
        }
    
    def add_exposure(
        self,
        position_id: str,
        risk_pct: float,
        symbol: str,
        strategy: str,
        direction: str,
        regime: str
    ) -> bool:
        """Add exposure for a position"""
        
        self._positions[position_id] = {
            "risk_pct": risk_pct,
            "symbol": symbol,
            "strategy": strategy,
            "direction": direction,
            "regime": regime
        }
        
        self._recalculate_exposures()
        return True
    
    def remove_exposure(self, position_id: str) -> bool:
        """Remove exposure for a position"""
        
        if position_id in self._positions:
            del self._positions[position_id]
            self._recalculate_exposures()
            return True
        return False
    
    def get_exposure_summary(self) -> ExposureSummary:
        """Get summary of all exposures"""
        
        limits = []
        breached = []
        warnings = []
        
        # Strategy exposures
        for strategy, exposure in self._exposures[ExposureType.STRATEGY.value].items():
            limit = ExposureLimit(
                exposure_type=ExposureType.STRATEGY,
                category=strategy,
                max_exposure_pct=self._limits[ExposureType.STRATEGY],
                current_exposure_pct=exposure,
                available_pct=max(0, self._limits[ExposureType.STRATEGY] - exposure),
                utilization_pct=(exposure / self._limits[ExposureType.STRATEGY] * 100) if self._limits[ExposureType.STRATEGY] > 0 else 0,
                is_breached=exposure > self._limits[ExposureType.STRATEGY],
                positions_count=sum(1 for p in self._positions.values() if p["strategy"] == strategy)
            )
            limits.append(limit)
            
            if limit.is_breached:
                breached.append(f"Strategy {strategy}")
            elif limit.utilization_pct >= 75:
                warnings.append(f"Strategy {strategy} at {limit.utilization_pct:.0f}%")
        
        # Asset exposures
        for asset, exposure in self._exposures[ExposureType.ASSET.value].items():
            limit = ExposureLimit(
                exposure_type=ExposureType.ASSET,
                category=asset,
                max_exposure_pct=self._limits[ExposureType.ASSET],
                current_exposure_pct=exposure,
                available_pct=max(0, self._limits[ExposureType.ASSET] - exposure),
                utilization_pct=(exposure / self._limits[ExposureType.ASSET] * 100) if self._limits[ExposureType.ASSET] > 0 else 0,
                is_breached=exposure > self._limits[ExposureType.ASSET],
                positions_count=sum(1 for p in self._positions.values() if p["symbol"] == asset)
            )
            limits.append(limit)
            
            if limit.is_breached:
                breached.append(f"Asset {asset}")
            elif limit.utilization_pct >= 75:
                warnings.append(f"Asset {asset} at {limit.utilization_pct:.0f}%")
        
        # Regime exposures
        for regime, exposure in self._exposures[ExposureType.REGIME.value].items():
            limit = ExposureLimit(
                exposure_type=ExposureType.REGIME,
                category=regime,
                max_exposure_pct=self._limits[ExposureType.REGIME],
                current_exposure_pct=exposure,
                available_pct=max(0, self._limits[ExposureType.REGIME] - exposure),
                utilization_pct=(exposure / self._limits[ExposureType.REGIME] * 100) if self._limits[ExposureType.REGIME] > 0 else 0,
                is_breached=exposure > self._limits[ExposureType.REGIME],
                positions_count=sum(1 for p in self._positions.values() if p["regime"] == regime)
            )
            limits.append(limit)
            
            if limit.is_breached:
                breached.append(f"Regime {regime}")
            elif limit.utilization_pct >= 75:
                warnings.append(f"Regime {regime} at {limit.utilization_pct:.0f}%")
        
        # Direction exposures
        for direction, exposure in self._exposures[ExposureType.DIRECTION.value].items():
            limit = ExposureLimit(
                exposure_type=ExposureType.DIRECTION,
                category=direction,
                max_exposure_pct=self._limits[ExposureType.DIRECTION],
                current_exposure_pct=exposure,
                available_pct=max(0, self._limits[ExposureType.DIRECTION] - exposure),
                utilization_pct=(exposure / self._limits[ExposureType.DIRECTION] * 100) if self._limits[ExposureType.DIRECTION] > 0 else 0,
                is_breached=exposure > self._limits[ExposureType.DIRECTION],
                positions_count=sum(1 for p in self._positions.values() if p["direction"] == direction)
            )
            limits.append(limit)
            
            if limit.is_breached:
                breached.append(f"Direction {direction}")
            elif limit.utilization_pct >= 75:
                warnings.append(f"Direction {direction} at {limit.utilization_pct:.0f}%")
        
        total_exposure = self._get_total_exposure()
        
        return ExposureSummary(
            limits=limits,
            breached_limits=breached,
            warnings=warnings,
            total_portfolio_exposure=total_exposure,
            max_portfolio_exposure=self._limits[ExposureType.PORTFOLIO]
        )
    
    def _recalculate_exposures(self):
        """Recalculate all exposures from positions"""
        
        # Clear
        for key in self._exposures:
            self._exposures[key] = {}
        
        # Recalculate
        for pos in self._positions.values():
            risk = pos["risk_pct"]
            
            # Strategy
            strategy = pos["strategy"]
            self._exposures[ExposureType.STRATEGY.value][strategy] = \
                self._exposures[ExposureType.STRATEGY.value].get(strategy, 0) + risk
            
            # Asset
            symbol = pos["symbol"]
            self._exposures[ExposureType.ASSET.value][symbol] = \
                self._exposures[ExposureType.ASSET.value].get(symbol, 0) + risk
            
            # Regime
            regime = pos["regime"]
            self._exposures[ExposureType.REGIME.value][regime] = \
                self._exposures[ExposureType.REGIME.value].get(regime, 0) + risk
            
            # Direction
            direction = pos["direction"]
            self._exposures[ExposureType.DIRECTION.value][direction] = \
                self._exposures[ExposureType.DIRECTION.value].get(direction, 0) + risk
    
    def _get_total_exposure(self) -> float:
        """Get total portfolio exposure"""
        return sum(p["risk_pct"] for p in self._positions.values())
    
    def update_limits(self, limits: Dict[str, float]) -> Dict[str, Any]:
        """Update exposure limits"""
        for key, value in limits.items():
            try:
                exp_type = ExposureType(key)
                self._limits[exp_type] = value
            except ValueError:
                pass
        
        return {
            "limits": {k.value: v for k, v in self._limits.items()},
            "summary": self.get_exposure_summary().to_dict()
        }
    
    def get_limits(self) -> Dict[str, float]:
        """Get current limits"""
        return {k.value: v for k, v in self._limits.items()}
    
    def clear(self):
        """Clear all positions and exposures"""
        self._positions.clear()
        self._recalculate_exposures()
    
    def get_health(self) -> Dict[str, Any]:
        """Get engine health"""
        return {
            "engine": "RiskLimitsEngine",
            "version": "1.0.0",
            "phase": "3.3",
            "status": "active",
            "activePositions": len(self._positions),
            "totalExposure": round(self._get_total_exposure(), 2),
            "maxExposure": self._limits[ExposureType.PORTFOLIO],
            "timestamp": int(time.time() * 1000)
        }


# Global singleton
risk_limits_engine = RiskLimitsEngine()
