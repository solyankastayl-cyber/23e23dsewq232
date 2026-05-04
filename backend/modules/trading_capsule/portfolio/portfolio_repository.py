"""
Portfolio Repository (S4.1)
===========================

Data persistence layer for Portfolio Simulation.

Collections:
- portfolio_simulations: Main simulation entities
- portfolio_slots: Strategy slots
- portfolio_states: State snapshots

Supports both in-memory and MongoDB storage.
"""

import os
import threading
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

from .portfolio_types import (
    PortfolioSimulation,
    PortfolioStrategySlot,
    PortfolioState,
    PortfolioSimulationStatus,
    SlotStatus
)


class PortfolioRepository:
    """
    Repository for Portfolio Simulation data persistence.
    
    Thread-safe singleton with MongoDB support.
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        # In-memory storage
        self._simulations: Dict[str, PortfolioSimulation] = {}
        self._slots: Dict[str, PortfolioStrategySlot] = {}
        self._states: Dict[str, PortfolioState] = {}
        
        # Simulation -> Slots mapping
        self._sim_slots: Dict[str, List[str]] = {}
        
        # Simulation -> Latest state mapping
        self._sim_latest_state: Dict[str, str] = {}
        
        # MongoDB (lazy init)
        self._db = None
        self._simulations_col = None
        self._slots_col = None
        self._states_col = None
        
        self._initialized = True
        print("[PortfolioRepository] Initialized")
    
    def _get_collections(self):
        """Get MongoDB collections"""
        if self._simulations_col is None:
            try:
                from pymongo import MongoClient
                
                mongo_url = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
                db_name = os.environ.get("DB_NAME", "trading_capsule")
                
                client = MongoClient(mongo_url)
                self._db = client[db_name]
                self._simulations_col = self._db["portfolio_simulations"]
                self._slots_col = self._db["portfolio_slots"]
                self._states_col = self._db["portfolio_states"]
                
                # Create indexes
                self._simulations_col.create_index("simulation_id", unique=True)
                self._slots_col.create_index("slot_id", unique=True)
                self._slots_col.create_index("simulation_id")
                self._states_col.create_index("state_id", unique=True)
                self._states_col.create_index([("simulation_id", 1), ("timestamp", -1)])
                
                print("[PortfolioRepository] MongoDB connected")
            except Exception as e:
                print(f"[PortfolioRepository] MongoDB connection failed: {e}")
        
        return self._simulations_col, self._slots_col, self._states_col
    
    # ===========================================
    # Simulation CRUD
    # ===========================================
    
    def create_simulation(self, simulation: PortfolioSimulation) -> PortfolioSimulation:
        """Create a new simulation"""
        self._simulations[simulation.simulation_id] = simulation
        self._sim_slots[simulation.simulation_id] = []
        
        # Persist to MongoDB
        sim_col, _, _ = self._get_collections()
        if sim_col is not None:
            try:
                sim_col.insert_one(simulation.to_dict())
            except Exception as e:
                print(f"[PortfolioRepository] Create simulation failed: {e}")
        
        return simulation
    
    def get_simulation(self, simulation_id: str) -> Optional[PortfolioSimulation]:
        """Get simulation by ID"""
        return self._simulations.get(simulation_id)
    
    def update_simulation(self, simulation: PortfolioSimulation) -> PortfolioSimulation:
        """Update an existing simulation"""
        self._simulations[simulation.simulation_id] = simulation
        
        sim_col, _, _ = self._get_collections()
        if sim_col is not None:
            try:
                sim_col.replace_one(
                    {"simulation_id": simulation.simulation_id},
                    simulation.to_dict(),
                    upsert=True
                )
            except Exception as e:
                print(f"[PortfolioRepository] Update simulation failed: {e}")
        
        return simulation
    
    def list_simulations(
        self,
        status: Optional[PortfolioSimulationStatus] = None,
        limit: int = 50
    ) -> List[PortfolioSimulation]:
        """List simulations with optional status filter"""
        simulations = list(self._simulations.values())
        
        if status:
            simulations = [s for s in simulations if s.status == status]
        
        # Sort by created_at descending
        simulations.sort(key=lambda s: s.created_at, reverse=True)
        return simulations[:limit]
    
    def delete_simulation(self, simulation_id: str) -> bool:
        """Delete simulation and all related data"""
        # Remove slots
        slot_ids = self._sim_slots.get(simulation_id, [])
        for slot_id in slot_ids:
            self._slots.pop(slot_id, None)
        
        # Remove states
        states_to_remove = [
            sid for sid, s in self._states.items() 
            if s.simulation_id == simulation_id
        ]
        for state_id in states_to_remove:
            self._states.pop(state_id, None)
        
        # Remove simulation
        self._simulations.pop(simulation_id, None)
        self._sim_slots.pop(simulation_id, None)
        self._sim_latest_state.pop(simulation_id, None)
        
        # Remove from MongoDB
        sim_col, slots_col, states_col = self._get_collections()
        if sim_col is not None:
            try:
                sim_col.delete_one({"simulation_id": simulation_id})
                if slots_col is not None:
                    slots_col.delete_many({"simulation_id": simulation_id})
                if states_col is not None:
                    states_col.delete_many({"simulation_id": simulation_id})
            except Exception as e:
                print(f"[PortfolioRepository] Delete simulation failed: {e}")
        
        return True
    
    # ===========================================
    # Slot CRUD
    # ===========================================
    
    def create_slot(self, slot: PortfolioStrategySlot) -> PortfolioStrategySlot:
        """Create a new strategy slot"""
        self._slots[slot.slot_id] = slot
        
        # Add to simulation mapping
        if slot.simulation_id not in self._sim_slots:
            self._sim_slots[slot.simulation_id] = []
        self._sim_slots[slot.simulation_id].append(slot.slot_id)
        
        # Persist to MongoDB
        _, slots_col, _ = self._get_collections()
        if slots_col is not None:
            try:
                slots_col.insert_one(slot.to_dict())
            except Exception as e:
                print(f"[PortfolioRepository] Create slot failed: {e}")
        
        return slot
    
    def get_slot(self, slot_id: str) -> Optional[PortfolioStrategySlot]:
        """Get slot by ID"""
        return self._slots.get(slot_id)
    
    def get_slots_by_simulation(self, simulation_id: str) -> List[PortfolioStrategySlot]:
        """Get all slots for a simulation"""
        slot_ids = self._sim_slots.get(simulation_id, [])
        return [self._slots[sid] for sid in slot_ids if sid in self._slots]
    
    def update_slot(self, slot: PortfolioStrategySlot) -> PortfolioStrategySlot:
        """Update an existing slot"""
        slot.last_updated_at = datetime.now(timezone.utc)
        self._slots[slot.slot_id] = slot
        
        _, slots_col, _ = self._get_collections()
        if slots_col is not None:
            try:
                slots_col.replace_one(
                    {"slot_id": slot.slot_id},
                    slot.to_dict(),
                    upsert=True
                )
            except Exception as e:
                print(f"[PortfolioRepository] Update slot failed: {e}")
        
        return slot
    
    def delete_slot(self, slot_id: str) -> bool:
        """Delete a slot"""
        slot = self._slots.pop(slot_id, None)
        if slot and slot.simulation_id in self._sim_slots:
            self._sim_slots[slot.simulation_id] = [
                s for s in self._sim_slots[slot.simulation_id] if s != slot_id
            ]
        
        _, slots_col, _ = self._get_collections()
        if slots_col is not None:
            try:
                slots_col.delete_one({"slot_id": slot_id})
            except Exception as e:
                print(f"[PortfolioRepository] Delete slot failed: {e}")
        
        return True
    
    # ===========================================
    # State CRUD
    # ===========================================
    
    def save_state(self, state: PortfolioState) -> PortfolioState:
        """Save a portfolio state snapshot"""
        self._states[state.state_id] = state
        self._sim_latest_state[state.simulation_id] = state.state_id
        
        _, _, states_col = self._get_collections()
        if states_col is not None:
            try:
                states_col.insert_one(state.to_dict())
            except Exception as e:
                print(f"[PortfolioRepository] Save state failed: {e}")
        
        return state
    
    def get_latest_state(self, simulation_id: str) -> Optional[PortfolioState]:
        """Get latest state for a simulation"""
        state_id = self._sim_latest_state.get(simulation_id)
        if state_id:
            return self._states.get(state_id)
        return None
    
    def get_state_history(
        self,
        simulation_id: str,
        limit: int = 100
    ) -> List[PortfolioState]:
        """Get state history for a simulation"""
        states = [
            s for s in self._states.values()
            if s.simulation_id == simulation_id
        ]
        states.sort(key=lambda s: s.timestamp, reverse=True)
        return states[:limit]
    
    # ===========================================
    # Stats
    # ===========================================
    
    def get_stats(self) -> Dict[str, Any]:
        """Get repository statistics"""
        return {
            "simulations_count": len(self._simulations),
            "slots_count": len(self._slots),
            "states_count": len(self._states),
            "status_breakdown": {
                status.value: len([
                    s for s in self._simulations.values() 
                    if s.status == status
                ])
                for status in PortfolioSimulationStatus
            }
        }


# Global singleton
portfolio_repository = PortfolioRepository()
