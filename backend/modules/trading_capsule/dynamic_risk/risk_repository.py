"""
Risk Repository
===============

PHASE 3.3 - Data persistence for risk calculations and history.
"""

import time
from typing import Dict, List, Optional, Any

from .risk_types import RiskCalculation, RiskBudget


class RiskRepository:
    """
    Repository for risk data:
    - Risk calculations history
    - Position risk records
    - Budget snapshots
    """
    
    def __init__(self):
        self._calculations: Dict[str, RiskCalculation] = {}
        self._history: Dict[str, List[RiskCalculation]] = {}
        self._budget_snapshots: List[Dict[str, Any]] = []
        
        print("[RiskRepository] Initialized (PHASE 3.3)")
    
    def save_calculation(self, calc: RiskCalculation):
        """Save risk calculation"""
        self._calculations[calc.position_id] = calc
        
        # Add to history
        if calc.position_id not in self._history:
            self._history[calc.position_id] = []
        self._history[calc.position_id].append(calc)
        
        # Keep last 50
        if len(self._history[calc.position_id]) > 50:
            self._history[calc.position_id] = self._history[calc.position_id][-50:]
    
    def get_calculation(self, position_id: str) -> Optional[RiskCalculation]:
        """Get latest calculation for position"""
        return self._calculations.get(position_id)
    
    def get_all_calculations(self) -> List[RiskCalculation]:
        """Get all calculations"""
        return list(self._calculations.values())
    
    def get_history(self, position_id: str, limit: int = 20) -> List[RiskCalculation]:
        """Get calculation history for position"""
        history = self._history.get(position_id, [])
        return history[-limit:]
    
    def save_budget_snapshot(self, budget: RiskBudget):
        """Save budget snapshot"""
        self._budget_snapshots.append(budget.to_dict())
        
        # Keep last 100 snapshots
        if len(self._budget_snapshots) > 100:
            self._budget_snapshots = self._budget_snapshots[-100:]
    
    def get_budget_history(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get budget history"""
        return self._budget_snapshots[-limit:]
    
    def remove_calculation(self, position_id: str):
        """Remove calculation for closed position"""
        self._calculations.pop(position_id, None)
    
    def clear(self):
        """Clear all data"""
        self._calculations.clear()
        self._history.clear()
        self._budget_snapshots.clear()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get repository statistics"""
        calculations = list(self._calculations.values())
        
        # Calculate averages
        avg_multiplier = 0.0
        avg_risk = 0.0
        if calculations:
            avg_multiplier = sum(c.combined_multiplier for c in calculations) / len(calculations)
            avg_risk = sum(c.adjusted_risk_pct for c in calculations) / len(calculations)
        
        return {
            "activeCalculations": len(self._calculations),
            "historyRecords": sum(len(h) for h in self._history.values()),
            "budgetSnapshots": len(self._budget_snapshots),
            "averages": {
                "multiplier": round(avg_multiplier, 3),
                "risk": round(avg_risk, 2)
            },
            "timestamp": int(time.time() * 1000)
        }


# Global singleton
risk_repository = RiskRepository()
