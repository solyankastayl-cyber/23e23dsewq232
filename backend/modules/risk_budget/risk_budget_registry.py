"""
Risk Budget Registry

PHASE 38.5 — Risk Budget Engine

MongoDB persistence for risk budget state.

Collections:
- portfolio_risk_budget: Current state snapshots
- risk_budget_history: Historical tracking
- strategy_risk_allocations: Strategy-level budgets
"""

from typing import Optional, List, Dict
from datetime import datetime, timezone, timedelta

from .risk_budget_types import (
    RiskBudget,
    PortfolioRiskBudget,
    RiskBudgetHistoryEntry,
    PositionRisk,
)


# ══════════════════════════════════════════════════════════════
# Risk Budget Registry
# ══════════════════════════════════════════════════════════════

class RiskBudgetRegistry:
    """
    MongoDB registry for risk budget persistence.
    """
    
    def __init__(self):
        self._db = None
    
    def _get_db(self):
        """Get database connection."""
        if self._db is None:
            try:
                from core.database import get_database
                self._db = get_database()
            except Exception:
                pass
        return self._db
    
    def _db_available(self) -> bool:
        """Check if database is available."""
        db = self._get_db()
        return db is not None
    
    # ═══════════════════════════════════════════════════════════
    # Portfolio Risk Budget
    # ═══════════════════════════════════════════════════════════
    
    def save_portfolio_risk_budget(self, state: PortfolioRiskBudget) -> bool:
        """Save current portfolio risk budget state."""
        db = self._get_db()
        if db is None:
            return False
        
        try:
            doc = {
                "total_risk": state.total_risk,
                "total_risk_limit": state.total_risk_limit,
                "risk_utilization": state.risk_utilization,
                "strategy_count": state.strategy_count,
                "position_count": state.position_count,
                "systematic_risk": state.systematic_risk,
                "idiosyncratic_risk": state.idiosyncratic_risk,
                "target_volatility": state.target_volatility,
                "current_volatility": state.current_volatility,
                "volatility_ratio": state.volatility_ratio,
                "vol_scale_factor": state.vol_scale_factor,
                "total_capital": state.total_capital,
                "risk_capital": state.risk_capital,
                "risk_state": state.risk_state,
                "needs_rebalance": state.needs_rebalance,
                "warnings": state.warnings,
                "timestamp": state.timestamp,
                "strategy_budgets": [
                    {
                        "strategy": b.strategy,
                        "strategy_type": b.strategy_type,
                        "risk_target": b.risk_target,
                        "risk_allocated": b.risk_allocated,
                        "risk_used": b.risk_used,
                        "allocated_capital": b.allocated_capital,
                        "max_capital": b.max_capital,
                        "risk_contribution": b.risk_contribution,
                        "volatility": b.volatility,
                        "position_count": b.position_count,
                        "is_active": b.is_active,
                        "is_over_budget": b.is_over_budget,
                    }
                    for b in state.strategy_budgets
                ],
                "position_risks": [
                    {
                        "symbol": p.symbol,
                        "strategy": p.strategy,
                        "position_size_usd": p.position_size_usd,
                        "weight": p.weight,
                        "asset_volatility": p.asset_volatility,
                        "volatility_annualized": p.volatility_annualized,
                        "risk_contribution": p.risk_contribution,
                        "marginal_risk": p.marginal_risk,
                        "avg_correlation": p.avg_correlation,
                        "is_within_budget": p.is_within_budget,
                    }
                    for p in state.position_risks
                ],
            }
            
            db.portfolio_risk_budget.update_one(
                {"_id": "current"},
                {"$set": {"_id": "current", **doc}},
                upsert=True
            )
            
            return True
        except Exception as e:
            print(f"[RiskBudgetRegistry] Error saving state: {e}")
            return False
    
    def get_portfolio_risk_budget(self) -> Optional[Dict]:
        """Get current portfolio risk budget state."""
        db = self._get_db()
        if db is None:
            return None
        
        try:
            doc = db.portfolio_risk_budget.find_one({"_id": "current"}, {"_id": 0})
            return doc
        except Exception:
            return None
    
    # ═══════════════════════════════════════════════════════════
    # Strategy Risk Allocations
    # ═══════════════════════════════════════════════════════════
    
    def save_strategy_allocation(self, budget: RiskBudget) -> bool:
        """Save strategy risk allocation."""
        db = self._get_db()
        if db is None:
            return False
        
        try:
            doc = {
                "strategy": budget.strategy,
                "strategy_type": budget.strategy_type,
                "risk_target": budget.risk_target,
                "risk_allocated": budget.risk_allocated,
                "risk_used": budget.risk_used,
                "allocated_capital": budget.allocated_capital,
                "max_capital": budget.max_capital,
                "risk_contribution": budget.risk_contribution,
                "volatility": budget.volatility,
                "volatility_scaled": budget.volatility_scaled,
                "position_count": budget.position_count,
                "avg_position_risk": budget.avg_position_risk,
                "is_active": budget.is_active,
                "is_over_budget": budget.is_over_budget,
                "sharpe_ratio": budget.sharpe_ratio,
                "recent_pnl": budget.recent_pnl,
                "last_updated": budget.last_updated,
            }
            
            db.strategy_risk_allocations.update_one(
                {"strategy": budget.strategy},
                {"$set": doc},
                upsert=True
            )
            
            return True
        except Exception as e:
            print(f"[RiskBudgetRegistry] Error saving strategy: {e}")
            return False
    
    def get_strategy_allocation(self, strategy: str) -> Optional[Dict]:
        """Get strategy risk allocation."""
        db = self._get_db()
        if db is None:
            return None
        
        try:
            doc = db.strategy_risk_allocations.find_one(
                {"strategy": strategy},
                {"_id": 0}
            )
            return doc
        except Exception:
            return None
    
    def get_all_strategy_allocations(self) -> List[Dict]:
        """Get all strategy risk allocations."""
        db = self._get_db()
        if db is None:
            return []
        
        try:
            docs = list(db.strategy_risk_allocations.find({}, {"_id": 0}))
            return docs
        except Exception:
            return []
    
    # ═══════════════════════════════════════════════════════════
    # History
    # ═══════════════════════════════════════════════════════════
    
    def save_history_entry(self, entry: RiskBudgetHistoryEntry) -> bool:
        """Save history entry."""
        db = self._get_db()
        if db is None:
            return False
        
        try:
            doc = {
                "total_risk": entry.total_risk,
                "risk_limit": entry.risk_limit,
                "risk_utilization": entry.risk_utilization,
                "strategy_count": entry.strategy_count,
                "position_count": entry.position_count,
                "current_volatility": entry.current_volatility,
                "target_volatility": entry.target_volatility,
                "vol_scale_factor": entry.vol_scale_factor,
                "risk_state": entry.risk_state,
                "timestamp": entry.timestamp,
            }
            
            db.risk_budget_history.insert_one(doc)
            return True
        except Exception as e:
            print(f"[RiskBudgetRegistry] Error saving history: {e}")
            return False
    
    def get_history(
        self,
        limit: int = 100,
        hours_back: Optional[int] = None,
    ) -> List[Dict]:
        """Get risk budget history."""
        db = self._get_db()
        if db is None:
            return []
        
        try:
            query = {}
            if hours_back:
                since = datetime.now(timezone.utc) - timedelta(hours=hours_back)
                query["timestamp"] = {"$gte": since}
            
            docs = list(
                db.risk_budget_history.find(query, {"_id": 0})
                .sort("timestamp", -1)
                .limit(limit)
            )
            return list(reversed(docs))
        except Exception:
            return []
    
    # ═══════════════════════════════════════════════════════════
    # Position Risks
    # ═══════════════════════════════════════════════════════════
    
    def save_position_risk(self, position: PositionRisk) -> bool:
        """Save position risk."""
        db = self._get_db()
        if db is None:
            return False
        
        try:
            doc = {
                "symbol": position.symbol,
                "strategy": position.strategy,
                "position_size_usd": position.position_size_usd,
                "weight": position.weight,
                "asset_volatility": position.asset_volatility,
                "volatility_annualized": position.volatility_annualized,
                "risk_contribution": position.risk_contribution,
                "marginal_risk": position.marginal_risk,
                "avg_correlation": position.avg_correlation,
                "correlation_adjustment": position.correlation_adjustment,
                "risk_budget_used": position.risk_budget_used,
                "max_size_from_risk_budget": position.max_size_from_risk_budget,
                "is_within_budget": position.is_within_budget,
                "updated_at": datetime.now(timezone.utc),
            }
            
            db.position_risks.update_one(
                {"symbol": position.symbol},
                {"$set": doc},
                upsert=True
            )
            
            return True
        except Exception as e:
            print(f"[RiskBudgetRegistry] Error saving position: {e}")
            return False
    
    def get_position_risk(self, symbol: str) -> Optional[Dict]:
        """Get position risk."""
        db = self._get_db()
        if db is None:
            return None
        
        try:
            doc = db.position_risks.find_one({"symbol": symbol}, {"_id": 0})
            return doc
        except Exception:
            return None
    
    def get_all_position_risks(self) -> List[Dict]:
        """Get all position risks."""
        db = self._get_db()
        if db is None:
            return []
        
        try:
            docs = list(db.position_risks.find({}, {"_id": 0}))
            return docs
        except Exception:
            return []
    
    def remove_position_risk(self, symbol: str) -> bool:
        """Remove position risk."""
        db = self._get_db()
        if db is None:
            return False
        
        try:
            db.position_risks.delete_one({"symbol": symbol})
            return True
        except Exception:
            return False
    
    # ═══════════════════════════════════════════════════════════
    # Statistics
    # ═══════════════════════════════════════════════════════════
    
    def get_statistics(self) -> Dict:
        """Get risk budget statistics."""
        db = self._get_db()
        if db is None:
            return {"status": "no_database"}
        
        try:
            # Current state
            current = self.get_portfolio_risk_budget()
            
            # Strategy counts
            strategy_count = db.strategy_risk_allocations.count_documents({})
            
            # Position counts
            position_count = db.position_risks.count_documents({})
            
            # History count
            history_count = db.risk_budget_history.count_documents({})
            
            # Recent risk states
            recent_history = self.get_history(limit=24)
            risk_states = {}
            for h in recent_history:
                state = h.get("risk_state", "UNKNOWN")
                risk_states[state] = risk_states.get(state, 0) + 1
            
            # Over budget strategies
            over_budget = db.strategy_risk_allocations.count_documents({"is_over_budget": True})
            
            return {
                "status": "ok",
                "current_state": {
                    "total_risk": current.get("total_risk", 0) if current else 0,
                    "risk_state": current.get("risk_state", "UNKNOWN") if current else "UNKNOWN",
                    "needs_rebalance": current.get("needs_rebalance", False) if current else False,
                },
                "counts": {
                    "strategies": strategy_count,
                    "positions": position_count,
                    "history_entries": history_count,
                },
                "alerts": {
                    "over_budget_strategies": over_budget,
                },
                "recent_risk_states": risk_states,
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}
    
    # ═══════════════════════════════════════════════════════════
    # Collections Setup
    # ═══════════════════════════════════════════════════════════
    
    def ensure_collections(self) -> bool:
        """Ensure MongoDB collections and indexes exist."""
        db = self._get_db()
        if db is None:
            return False
        
        try:
            # Create collections if not exist
            collections = [
                "portfolio_risk_budget",
                "strategy_risk_allocations",
                "risk_budget_history",
                "position_risks",
            ]
            
            existing = db.list_collection_names()
            
            for col in collections:
                if col not in existing:
                    db.create_collection(col)
            
            # Create indexes
            db.strategy_risk_allocations.create_index([("strategy", 1)], unique=True)
            db.risk_budget_history.create_index([("timestamp", -1)])
            db.position_risks.create_index([("symbol", 1)], unique=True)
            db.position_risks.create_index([("strategy", 1)])
            
            return True
        except Exception as e:
            print(f"[RiskBudgetRegistry] Error ensuring collections: {e}")
            return False


# ══════════════════════════════════════════════════════════════
# Singleton
# ══════════════════════════════════════════════════════════════

_registry: Optional[RiskBudgetRegistry] = None


def get_risk_budget_registry() -> RiskBudgetRegistry:
    """Get singleton instance of RiskBudgetRegistry."""
    global _registry
    if _registry is None:
        _registry = RiskBudgetRegistry()
        _registry.ensure_collections()
    return _registry
