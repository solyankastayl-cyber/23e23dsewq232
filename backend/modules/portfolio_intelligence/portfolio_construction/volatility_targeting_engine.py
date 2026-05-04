"""
PHASE 10 - Volatility Targeting Engine
=======================================
Maintains target portfolio volatility.

If market becomes more volatile:
  position_size ↓

If market is calm:
  position_size ↑
"""

import math
from typing import List, Dict, Optional
from datetime import datetime, timezone

from .portfolio_types import (
    VolatilityTarget, VolatilityRegime, DEFAULT_PORTFOLIO_CONFIG
)


class VolatilityTargetingEngine:
    """
    Volatility Targeting Engine
    
    Scales positions to maintain target portfolio volatility,
    regardless of current market conditions.
    """
    
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or DEFAULT_PORTFOLIO_CONFIG
        self.history: List[VolatilityTarget] = []
        self.max_history = 100
        self.realized_vol_window: List[float] = []
    
    def calculate_volatility_scaling(
        self,
        current_volatility: float,
        target_volatility: Optional[float] = None,
        recent_returns: Optional[List[float]] = None
    ) -> VolatilityTarget:
        """
        Calculate volatility scaling factor.
        
        Args:
            current_volatility: Current portfolio volatility
            target_volatility: Target volatility (default from config)
            recent_returns: Recent daily returns for realized vol
            
        Returns:
            VolatilityTarget with scaling recommendations
        """
        now = datetime.now(timezone.utc)
        
        if target_volatility is None:
            target_volatility = self.config["target_volatility"]
        
        # Calculate realized volatility if returns provided
        realized_volatility = self._calculate_realized_vol(recent_returns)
        if realized_volatility == 0:
            realized_volatility = current_volatility
        
        # Update realized vol window
        self.realized_vol_window.append(realized_volatility)
        if len(self.realized_vol_window) > 20:
            self.realized_vol_window = self.realized_vol_window[-20:]
        
        # Calculate volatility scalar
        if current_volatility > 0:
            raw_scalar = target_volatility / current_volatility
        else:
            raw_scalar = 1.0
        
        # Apply bounds
        max_scalar = self.config["vol_scaling_max"]
        min_scalar = self.config["vol_scaling_min"]
        volatility_scalar = max(min_scalar, min(max_scalar, raw_scalar))
        
        # Calculate position size adjustment
        position_size_adjustment = (volatility_scalar - 1.0) * 100  # As percentage
        
        # Determine volatility regime
        volatility_regime = self._determine_regime(current_volatility)
        
        # Forecast future volatility (simple EWMA)
        vol_forecast_1d = self._forecast_volatility(1)
        vol_forecast_5d = self._forecast_volatility(5)
        
        result = VolatilityTarget(
            timestamp=now,
            target_volatility=target_volatility,
            current_volatility=current_volatility,
            realized_volatility=realized_volatility,
            volatility_scalar=volatility_scalar,
            position_size_adjustment=position_size_adjustment,
            volatility_regime=volatility_regime,
            vol_forecast_1d=vol_forecast_1d,
            vol_forecast_5d=vol_forecast_5d
        )
        
        self._add_to_history(result)
        
        return result
    
    def _calculate_realized_vol(
        self,
        returns: Optional[List[float]],
        annualize: bool = True
    ) -> float:
        """Calculate realized volatility from returns."""
        if not returns or len(returns) < 2:
            return 0.0
        
        # Calculate standard deviation
        mean = sum(returns) / len(returns)
        variance = sum((r - mean) ** 2 for r in returns) / (len(returns) - 1)
        std = math.sqrt(variance)
        
        # Annualize (assuming daily returns)
        if annualize:
            std *= math.sqrt(252)
        
        return std
    
    def _determine_regime(self, volatility: float) -> VolatilityRegime:
        """Determine volatility regime."""
        if volatility < 0.10:
            return VolatilityRegime.LOW
        elif volatility < 0.20:
            return VolatilityRegime.NORMAL
        elif volatility < 0.35:
            return VolatilityRegime.HIGH
        else:
            return VolatilityRegime.EXTREME
    
    def _forecast_volatility(self, days: int) -> float:
        """Simple volatility forecast using EWMA."""
        if len(self.realized_vol_window) < 3:
            return 0.0
        
        # EWMA with decay factor
        decay = 0.94
        weights = [decay ** i for i in range(len(self.realized_vol_window))]
        weights.reverse()
        total_weight = sum(weights)
        
        ewma_vol = sum(
            w * v for w, v in zip(weights, self.realized_vol_window)
        ) / total_weight
        
        # Simple scaling for forecast horizon
        # Vol scales with sqrt(time) for short horizons
        return ewma_vol * math.sqrt(days)
    
    def _add_to_history(self, result: VolatilityTarget):
        """Add result to history."""
        self.history.append(result)
        if len(self.history) > self.max_history:
            self.history = self.history[-self.max_history:]
    
    def get_scaling_recommendation(self) -> Dict:
        """Get current scaling recommendation."""
        if not self.history:
            return {"recommendation": "NO_HISTORY"}
        
        recent = self.history[-1]
        
        # Determine action
        if recent.volatility_scalar > 1.1:
            action = "INCREASE_EXPOSURE"
            reason = "Volatility below target"
        elif recent.volatility_scalar < 0.9:
            action = "DECREASE_EXPOSURE"
            reason = "Volatility above target"
        else:
            action = "MAINTAIN"
            reason = "Volatility near target"
        
        return {
            "action": action,
            "reason": reason,
            "scalar": round(recent.volatility_scalar, 4),
            "current_vol": round(recent.current_volatility, 4),
            "target_vol": round(recent.target_volatility, 4),
            "regime": recent.volatility_regime.value,
            "position_adjustment": f"{recent.position_size_adjustment:+.1f}%"
        }
    
    def get_volatility_summary(self) -> Dict:
        """Get summary of volatility targeting."""
        if not self.history:
            return {"summary": "NO_HISTORY"}
        
        recent = self.history[-5:] if len(self.history) >= 5 else self.history
        
        avg_scalar = sum(h.volatility_scalar for h in recent) / len(recent)
        avg_realized = sum(h.realized_volatility for h in recent) / len(recent)
        
        # Count regime distribution
        regimes = {}
        for h in recent:
            r = h.volatility_regime.value
            regimes[r] = regimes.get(r, 0) + 1
        
        return {
            "avg_volatility_scalar": round(avg_scalar, 4),
            "avg_realized_vol": round(avg_realized, 4),
            "current_regime": recent[-1].volatility_regime.value,
            "regime_distribution": regimes,
            "periods": len(recent)
        }
