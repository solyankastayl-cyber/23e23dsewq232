"""
Risk Budget Engine
==================

PHASE 3.3 - Manages portfolio risk budget allocation and tracking.
"""

import time
from typing import Dict, List, Optional, Any

from .risk_types import (
    RiskBudget,
    BudgetStatus
)


class RiskBudgetEngine:
    """
    Manages portfolio risk budget:
    - Total risk budget allocation
    - Per-strategy budget limits
    - Per-asset budget limits
    - Per-regime budget limits
    - Direction (long/short) budget limits
    """
    
    def __init__(self):
        # Default budget configuration
        self._config = {
            "total_budget_pct": 10.0,        # 10% max portfolio risk
            "max_single_trade_pct": 2.0,     # 2% max per trade
            "max_strategy_pct": 4.0,         # 4% max per strategy
            "max_asset_pct": 3.0,            # 3% max per asset
            "max_regime_pct": 5.0,           # 5% max per regime
            "max_direction_pct": 6.0,        # 6% max per direction
            "reserve_pct": 1.0               # 1% always reserved
        }
        
        # Current state
        self._budget = RiskBudget(
            total_budget_pct=self._config["total_budget_pct"],
            max_single_trade_pct=self._config["max_single_trade_pct"],
            max_strategy_pct=self._config["max_strategy_pct"],
            max_asset_pct=self._config["max_asset_pct"],
            max_regime_pct=self._config["max_regime_pct"],
            max_direction_pct=self._config["max_direction_pct"]
        )
        
        # Position tracking
        self._positions: Dict[str, Dict[str, Any]] = {}
        
        print("[RiskBudgetEngine] Initialized (PHASE 3.3)")
    
    def get_budget(self) -> RiskBudget:
        """Get current budget state"""
        self._recalculate_budget()
        return self._budget
    
    def allocate_risk(
        self,
        position_id: str,
        risk_pct: float,
        symbol: str,
        strategy: str,
        direction: str,
        regime: str
    ) -> Dict[str, Any]:
        """
        Allocate risk from budget for a new position.
        Returns allocation result with any constraints applied.
        """
        
        self._recalculate_budget()
        
        constraints = []
        original_risk = risk_pct
        
        # Check single trade limit
        if risk_pct > self._config["max_single_trade_pct"]:
            risk_pct = self._config["max_single_trade_pct"]
            constraints.append(f"Single trade limit: {original_risk:.2f}% -> {risk_pct:.2f}%")
        
        # Check strategy limit
        strategy_used = self._budget.by_strategy.get(strategy, 0)
        strategy_available = self._config["max_strategy_pct"] - strategy_used
        if risk_pct > strategy_available:
            risk_pct = max(0, strategy_available)
            constraints.append(f"Strategy limit ({strategy}): reduced to {risk_pct:.2f}%")
        
        # Check asset limit
        asset_used = self._budget.by_asset.get(symbol, 0)
        asset_available = self._config["max_asset_pct"] - asset_used
        if risk_pct > asset_available:
            risk_pct = max(0, asset_available)
            constraints.append(f"Asset limit ({symbol}): reduced to {risk_pct:.2f}%")
        
        # Check regime limit
        regime_used = self._budget.by_regime.get(regime, 0)
        regime_available = self._config["max_regime_pct"] - regime_used
        if risk_pct > regime_available:
            risk_pct = max(0, regime_available)
            constraints.append(f"Regime limit ({regime}): reduced to {risk_pct:.2f}%")
        
        # Check direction limit
        direction_used = self._budget.by_direction.get(direction, 0)
        direction_available = self._config["max_direction_pct"] - direction_used
        if risk_pct > direction_available:
            risk_pct = max(0, direction_available)
            constraints.append(f"Direction limit ({direction}): reduced to {risk_pct:.2f}%")
        
        # Check total budget (with reserve)
        available = self._budget.available_budget_pct - self._config["reserve_pct"]
        if risk_pct > available:
            risk_pct = max(0, available)
            constraints.append(f"Total budget: reduced to {risk_pct:.2f}%")
        
        # Store position if risk > 0
        if risk_pct > 0:
            self._positions[position_id] = {
                "risk_pct": risk_pct,
                "symbol": symbol,
                "strategy": strategy,
                "direction": direction,
                "regime": regime,
                "allocated_at": int(time.time() * 1000)
            }
            self._recalculate_budget()
        
        # Determine status
        budget_status = self._get_budget_status()
        
        return {
            "positionId": position_id,
            "requested": round(original_risk, 2),
            "allocated": round(risk_pct, 2),
            "constraints": constraints,
            "budgetBefore": round(self._budget.used_budget_pct - risk_pct, 2),
            "budgetAfter": round(self._budget.used_budget_pct, 2),
            "budgetStatus": budget_status.value,
            "success": risk_pct > 0
        }
    
    def release_risk(self, position_id: str) -> Dict[str, Any]:
        """Release risk when position is closed"""
        
        if position_id not in self._positions:
            return {
                "positionId": position_id,
                "success": False,
                "reason": "Position not found"
            }
        
        position = self._positions[position_id]
        released = position["risk_pct"]
        
        del self._positions[position_id]
        self._recalculate_budget()
        
        return {
            "positionId": position_id,
            "released": round(released, 2),
            "budgetAfter": round(self._budget.used_budget_pct, 2),
            "budgetStatus": self._get_budget_status().value,
            "success": True
        }
    
    def check_allocation(
        self,
        risk_pct: float,
        symbol: str,
        strategy: str,
        direction: str,
        regime: str
    ) -> Dict[str, Any]:
        """
        Check if allocation is possible without actually allocating.
        Returns available amount and any limits that would be hit.
        """
        
        self._recalculate_budget()
        
        limits = []
        available = risk_pct
        
        # Check each limit
        if risk_pct > self._config["max_single_trade_pct"]:
            available = min(available, self._config["max_single_trade_pct"])
            limits.append({"type": "single_trade", "max": self._config["max_single_trade_pct"]})
        
        strategy_available = self._config["max_strategy_pct"] - self._budget.by_strategy.get(strategy, 0)
        if risk_pct > strategy_available:
            available = min(available, strategy_available)
            limits.append({"type": "strategy", "category": strategy, "available": strategy_available})
        
        asset_available = self._config["max_asset_pct"] - self._budget.by_asset.get(symbol, 0)
        if risk_pct > asset_available:
            available = min(available, asset_available)
            limits.append({"type": "asset", "category": symbol, "available": asset_available})
        
        regime_available = self._config["max_regime_pct"] - self._budget.by_regime.get(regime, 0)
        if risk_pct > regime_available:
            available = min(available, regime_available)
            limits.append({"type": "regime", "category": regime, "available": regime_available})
        
        direction_available = self._config["max_direction_pct"] - self._budget.by_direction.get(direction, 0)
        if risk_pct > direction_available:
            available = min(available, direction_available)
            limits.append({"type": "direction", "category": direction, "available": direction_available})
        
        total_available = self._budget.available_budget_pct - self._config["reserve_pct"]
        if risk_pct > total_available:
            available = min(available, total_available)
            limits.append({"type": "total_budget", "available": total_available})
        
        return {
            "requested": round(risk_pct, 2),
            "available": round(max(0, available), 2),
            "canAllocate": available > 0,
            "limits": limits,
            "budgetStatus": self._get_budget_status().value
        }
    
    def _recalculate_budget(self):
        """Recalculate budget from positions"""
        
        self._budget.by_strategy.clear()
        self._budget.by_asset.clear()
        self._budget.by_regime.clear()
        self._budget.by_direction.clear()
        self._budget.position_risks.clear()
        
        total_used = 0.0
        
        for pos_id, pos in self._positions.items():
            risk = pos["risk_pct"]
            total_used += risk
            
            # Strategy
            strategy = pos["strategy"]
            self._budget.by_strategy[strategy] = self._budget.by_strategy.get(strategy, 0) + risk
            
            # Asset
            symbol = pos["symbol"]
            self._budget.by_asset[symbol] = self._budget.by_asset.get(symbol, 0) + risk
            
            # Regime
            regime = pos["regime"]
            self._budget.by_regime[regime] = self._budget.by_regime.get(regime, 0) + risk
            
            # Direction
            direction = pos["direction"]
            self._budget.by_direction[direction] = self._budget.by_direction.get(direction, 0) + risk
            
            # Position risks
            self._budget.position_risks[pos_id] = risk
        
        self._budget.used_budget_pct = total_used
        self._budget.available_budget_pct = self._budget.total_budget_pct - total_used
        self._budget.utilization_pct = (total_used / self._budget.total_budget_pct * 100) if self._budget.total_budget_pct > 0 else 0
        self._budget.active_positions = len(self._positions)
        self._budget.status = self._get_budget_status()
        self._budget.updated_at = int(time.time() * 1000)
    
    def _get_budget_status(self) -> BudgetStatus:
        """Get current budget status"""
        utilization = self._budget.utilization_pct
        
        if utilization >= 100:
            return BudgetStatus.EXCEEDED
        elif utilization >= 95:
            return BudgetStatus.EXHAUSTED
        elif utilization >= 80:
            return BudgetStatus.RESTRICTED
        elif utilization >= 50:
            return BudgetStatus.LIMITED
        else:
            return BudgetStatus.AVAILABLE
    
    def update_config(self, config: Dict[str, float]) -> Dict[str, Any]:
        """Update budget configuration"""
        for key, value in config.items():
            if key in self._config:
                self._config[key] = value
        
        self._budget.total_budget_pct = self._config["total_budget_pct"]
        self._budget.max_single_trade_pct = self._config["max_single_trade_pct"]
        self._budget.max_strategy_pct = self._config["max_strategy_pct"]
        self._budget.max_asset_pct = self._config["max_asset_pct"]
        self._budget.max_regime_pct = self._config["max_regime_pct"]
        self._budget.max_direction_pct = self._config["max_direction_pct"]
        
        self._recalculate_budget()
        
        return {
            "config": self._config,
            "budget": self._budget.to_dict()
        }
    
    def get_config(self) -> Dict[str, float]:
        """Get current configuration"""
        return self._config.copy()
    
    def clear(self):
        """Clear all positions and reset budget"""
        self._positions.clear()
        self._recalculate_budget()
    
    def get_health(self) -> Dict[str, Any]:
        """Get engine health"""
        return {
            "engine": "RiskBudgetEngine",
            "version": "1.0.0",
            "phase": "3.3",
            "status": "active",
            "activePositions": len(self._positions),
            "budgetUtilization": round(self._budget.utilization_pct, 1),
            "budgetStatus": self._budget.status.value,
            "timestamp": int(time.time() * 1000)
        }


# Global singleton
risk_budget_engine = RiskBudgetEngine()
