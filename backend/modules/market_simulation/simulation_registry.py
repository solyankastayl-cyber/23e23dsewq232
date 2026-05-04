"""
Market Simulation Registry

PHASE 32.3 — MongoDB persistence for simulation results.
"""

from typing import Optional, List, Dict
from datetime import datetime, timezone

from core.database import get_database

from .simulation_types import (
    MarketScenario,
    SimulationResult,
    SimulationSummary,
    SCENARIO_TYPES,
)


# ══════════════════════════════════════════════════════════════
# Collection Names
# ══════════════════════════════════════════════════════════════

SCENARIOS_COLLECTION = "market_simulation_scenarios"
RESULTS_COLLECTION = "market_simulation_results"


# ══════════════════════════════════════════════════════════════
# Simulation Registry
# ══════════════════════════════════════════════════════════════

class SimulationRegistry:
    """
    MongoDB registry for market simulation data.
    """
    
    def __init__(self):
        self._db = None
    
    @property
    def db(self):
        """Get database connection."""
        if self._db is None:
            self._db = get_database()
        return self._db
    
    @property
    def scenarios_collection(self):
        """Get scenarios collection."""
        return self.db[SCENARIOS_COLLECTION]
    
    @property
    def results_collection(self):
        """Get results collection."""
        return self.db[RESULTS_COLLECTION]
    
    # ═══════════════════════════════════════════════════════════
    # Scenario Operations
    # ═══════════════════════════════════════════════════════════
    
    def save_scenario(self, scenario: MarketScenario) -> str:
        """Save market scenario to database."""
        doc = scenario.model_dump()
        doc["created_at"] = datetime.now(timezone.utc)
        doc.pop("_id", None)
        
        result = self.scenarios_collection.insert_one(doc)
        return scenario.scenario_id
    
    def save_scenarios(self, scenarios: List[MarketScenario]) -> int:
        """Save multiple scenarios."""
        if not scenarios:
            return 0
        
        docs = []
        for s in scenarios:
            doc = s.model_dump()
            doc["created_at"] = datetime.now(timezone.utc)
            doc.pop("_id", None)
            docs.append(doc)
        
        result = self.scenarios_collection.insert_many(docs)
        return len(result.inserted_ids)
    
    def get_latest_scenarios(
        self,
        symbol: str,
        limit: int = 5,
    ) -> List[MarketScenario]:
        """Get latest scenarios for symbol."""
        docs = self.scenarios_collection.find(
            {"symbol": symbol.upper()},
            {"_id": 0}
        ).sort("created_at", -1).limit(limit)
        
        return [MarketScenario(**doc) for doc in docs]
    
    def get_scenario_by_type(
        self,
        symbol: str,
        scenario_type: str,
        limit: int = 10,
    ) -> List[MarketScenario]:
        """Get scenarios by type."""
        docs = self.scenarios_collection.find(
            {"symbol": symbol.upper(), "scenario_type": scenario_type},
            {"_id": 0}
        ).sort("created_at", -1).limit(limit)
        
        return [MarketScenario(**doc) for doc in docs]
    
    # ═══════════════════════════════════════════════════════════
    # Result Operations
    # ═══════════════════════════════════════════════════════════
    
    def save_result(self, result: SimulationResult) -> str:
        """Save simulation result to database."""
        doc = result.model_dump()
        doc["created_at"] = datetime.now(timezone.utc)
        
        # Convert nested models
        doc["scenarios"] = [s.model_dump() for s in result.scenarios]
        if result.top_scenario:
            doc["top_scenario"] = result.top_scenario.model_dump()
        if result.input_data:
            doc["input_data"] = result.input_data.model_dump()
        
        doc.pop("_id", None)
        
        insert_result = self.results_collection.insert_one(doc)
        return str(insert_result.inserted_id)
    
    def get_latest_result(
        self,
        symbol: str,
    ) -> Optional[SimulationResult]:
        """Get latest simulation result."""
        doc = self.results_collection.find_one(
            {"symbol": symbol.upper()},
            {"_id": 0},
            sort=[("created_at", -1)]
        )
        
        if doc:
            return SimulationResult(**doc)
        return None
    
    def get_result_history(
        self,
        symbol: str,
        limit: int = 100,
    ) -> List[SimulationResult]:
        """Get simulation result history."""
        docs = self.results_collection.find(
            {"symbol": symbol.upper()},
            {"_id": 0}
        ).sort("created_at", -1).limit(limit)
        
        return [SimulationResult(**doc) for doc in docs]
    
    def get_result_stats(self, symbol: str) -> Dict:
        """Get result statistics."""
        pipeline = [
            {"$match": {"symbol": symbol.upper()}},
            {"$group": {
                "_id": "$symbol",
                "total_simulations": {"$sum": 1},
                "avg_scenarios": {"$avg": "$scenarios_generated"},
                "avg_volatility": {"$avg": "$expected_volatility"},
            }},
        ]
        
        results = list(self.results_collection.aggregate(pipeline))
        
        if results:
            r = results[0]
            return {
                "symbol": symbol.upper(),
                "total_simulations": r.get("total_simulations", 0),
                "avg_scenarios": round(r.get("avg_scenarios", 0), 2),
                "avg_volatility": round(r.get("avg_volatility", 0), 2),
            }
        
        return {
            "symbol": symbol.upper(),
            "total_simulations": 0,
            "avg_scenarios": 0,
            "avg_volatility": 0,
        }
    
    def get_scenario_distribution(self, symbol: str) -> Dict[str, int]:
        """Get scenario type distribution."""
        pipeline = [
            {"$match": {"symbol": symbol.upper()}},
            {"$unwind": "$scenarios"},
            {"$group": {
                "_id": "$scenarios.scenario_type",
                "count": {"$sum": 1}
            }},
        ]
        
        results = list(self.results_collection.aggregate(pipeline))
        return {r["_id"]: r["count"] for r in results}
    
    # ═══════════════════════════════════════════════════════════
    # Index Management
    # ═══════════════════════════════════════════════════════════
    
    def ensure_indexes(self) -> None:
        """Create indexes for collections."""
        # Scenarios indexes
        self.scenarios_collection.create_index([("symbol", 1), ("scenario_type", 1)])
        self.scenarios_collection.create_index([("created_at", -1)])
        self.scenarios_collection.create_index([("scenario_id", 1)], unique=True)
        
        # Results indexes
        self.results_collection.create_index([("symbol", 1)])
        self.results_collection.create_index([("created_at", -1)])


# ══════════════════════════════════════════════════════════════
# Singleton
# ══════════════════════════════════════════════════════════════

_simulation_registry: Optional[SimulationRegistry] = None


def get_simulation_registry() -> SimulationRegistry:
    """Get singleton instance of SimulationRegistry."""
    global _simulation_registry
    if _simulation_registry is None:
        _simulation_registry = SimulationRegistry()
    return _simulation_registry
