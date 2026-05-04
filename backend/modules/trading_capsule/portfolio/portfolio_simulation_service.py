"""
Portfolio Simulation Service (S4.1)
===================================

Main service for Portfolio Simulation.

Pipeline:
1. Load allocation plan
2. Create simulation
3. Generate strategy slots
4. Distribute capital
5. Create initial state
6. Start simulation

Depends on:
- Allocation Engine (S3)
- Strategy Registry
"""

import threading
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
import uuid

from .portfolio_types import (
    PortfolioSimulation,
    PortfolioStrategySlot,
    PortfolioState,
    PortfolioSimulationStatus,
    SlotStatus,
    SlotsSummary
)
from .portfolio_repository import portfolio_repository
from .portfolio_state_service import portfolio_state_service


class PortfolioSimulationService:
    """
    Main service for portfolio simulation.
    
    Thread-safe singleton.
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
        self._initialized = True
        print("[PortfolioSimulationService] Initialized")
    
    # ===========================================
    # Create Simulation
    # ===========================================
    
    def create_simulation(
        self,
        allocation_plan_id: str,
        total_capital_usd: float,
        name: str = "",
        description: str = "",
        start_date: str = "",
        end_date: str = "",
        tags: List[str] = None,
        config: Dict[str, Any] = None
    ) -> PortfolioSimulation:
        """
        Create a new portfolio simulation.
        
        Steps:
        1. Load allocation plan
        2. Create simulation entity
        3. Create strategy slots
        4. Create initial state
        
        Args:
            allocation_plan_id: ID of allocation plan to use
            total_capital_usd: Total capital for simulation
            name: Optional simulation name
            description: Optional description
            start_date: Optional start date (ISO format)
            end_date: Optional end date (ISO format)
            tags: Optional tags
            config: Optional configuration overrides
        
        Returns:
            PortfolioSimulation
        """
        # Load allocation plan
        allocation_plan = self._get_allocation_plan(allocation_plan_id)
        
        # Generate name if not provided
        if not name:
            timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M")
            name = f"Portfolio_Sim_{timestamp}"
        
        # Create simulation
        simulation = PortfolioSimulation(
            allocation_plan_id=allocation_plan_id,
            name=name,
            description=description,
            total_capital_usd=total_capital_usd,
            start_date=start_date,
            end_date=end_date,
            status=PortfolioSimulationStatus.CREATED,
            tags=tags or [],
            config=config or {}
        )
        
        # Save simulation
        portfolio_repository.create_simulation(simulation)
        
        # Create strategy slots from allocation plan
        self._create_strategy_slots(simulation, allocation_plan)
        
        # Create initial portfolio state
        portfolio_state_service.create_initial_state(simulation)
        
        print(f"[PortfolioSimulationService] Created simulation: {simulation.simulation_id}")
        return simulation
    
    def _get_allocation_plan(self, plan_id: str) -> Dict[str, Any]:
        """
        Get allocation plan from Allocation Engine.
        
        Tries to load from S3 Allocation Engine, falls back to mock.
        """
        try:
            from ..allocation.allocation_engine import allocation_engine
            plan = allocation_engine.get_plan(plan_id)
            if plan:
                return plan.to_dict()
        except ImportError:
            pass
        except Exception as e:
            print(f"[PortfolioSimulationService] Error loading plan: {e}")
        
        # Return mock plan for testing
        print(f"[PortfolioSimulationService] Using mock allocation plan for {plan_id}")
        return self._create_mock_allocation_plan(plan_id)
    
    def _create_mock_allocation_plan(self, plan_id: str) -> Dict[str, Any]:
        """Create mock allocation plan for testing"""
        return {
            "plan_id": plan_id,
            "strategies": [
                {
                    "strategy_id": "strat_trend_001",
                    "allocation": {
                        "target_weight": 0.35,
                        "target_capital_usd": 35000
                    }
                },
                {
                    "strategy_id": "strat_breakout_002",
                    "allocation": {
                        "target_weight": 0.30,
                        "target_capital_usd": 30000
                    }
                },
                {
                    "strategy_id": "strat_momentum_003",
                    "allocation": {
                        "target_weight": 0.20,
                        "target_capital_usd": 20000
                    }
                },
                {
                    "strategy_id": "strat_reversal_004",
                    "allocation": {
                        "target_weight": 0.15,
                        "target_capital_usd": 15000
                    }
                }
            ],
            "capital": {
                "total_usd": 100000,
                "allocated_usd": 100000
            }
        }
    
    def _create_strategy_slots(
        self,
        simulation: PortfolioSimulation,
        allocation_plan: Dict[str, Any]
    ):
        """
        Create strategy slots from allocation plan.
        
        Each strategy gets a slot with:
        - Target weight
        - Allocated capital
        - Initial state
        """
        strategies = allocation_plan.get("strategies", [])
        
        for strategy_data in strategies:
            strategy_id = strategy_data.get("strategy_id", "")
            allocation = strategy_data.get("allocation", {})
            
            target_weight = allocation.get("target_weight", 0.0)
            
            # Calculate allocated capital based on simulation total
            allocated_capital = simulation.total_capital_usd * target_weight
            
            slot = PortfolioStrategySlot(
                simulation_id=simulation.simulation_id,
                strategy_id=strategy_id,
                target_weight=target_weight,
                allocated_capital_usd=allocated_capital,
                current_capital_usd=allocated_capital,
                current_weight=target_weight,
                status=SlotStatus.PENDING,
                enabled=True
            )
            
            portfolio_repository.create_slot(slot)
        
        print(f"[PortfolioSimulationService] Created {len(strategies)} slots for {simulation.simulation_id}")
    
    # ===========================================
    # Get Simulation
    # ===========================================
    
    def get_simulation(self, simulation_id: str) -> Optional[PortfolioSimulation]:
        """Get simulation by ID"""
        return portfolio_repository.get_simulation(simulation_id)
    
    def list_simulations(
        self,
        status: Optional[PortfolioSimulationStatus] = None,
        limit: int = 50
    ) -> List[PortfolioSimulation]:
        """List simulations with optional status filter"""
        return portfolio_repository.list_simulations(status, limit)
    
    # ===========================================
    # Simulation Lifecycle
    # ===========================================
    
    def start_simulation(
        self,
        simulation_id: str
    ) -> Optional[PortfolioSimulation]:
        """
        Start a simulation.
        
        Changes status to RUNNING and activates slots.
        """
        simulation = portfolio_repository.get_simulation(simulation_id)
        if not simulation:
            return None
        
        if simulation.status not in [
            PortfolioSimulationStatus.CREATED,
            PortfolioSimulationStatus.PAUSED
        ]:
            print(f"[PortfolioSimulationService] Cannot start simulation in {simulation.status.value} state")
            return simulation
        
        # Update simulation status
        simulation.status = PortfolioSimulationStatus.RUNNING
        simulation.started_at = datetime.now(timezone.utc)
        portfolio_repository.update_simulation(simulation)
        
        # Activate all pending slots
        slots = portfolio_repository.get_slots_by_simulation(simulation_id)
        for slot in slots:
            if slot.status == SlotStatus.PENDING:
                slot.status = SlotStatus.ACTIVE
                portfolio_repository.update_slot(slot)
        
        print(f"[PortfolioSimulationService] Started simulation: {simulation_id}")
        return simulation
    
    def pause_simulation(
        self,
        simulation_id: str
    ) -> Optional[PortfolioSimulation]:
        """Pause a running simulation"""
        simulation = portfolio_repository.get_simulation(simulation_id)
        if not simulation:
            return None
        
        if simulation.status != PortfolioSimulationStatus.RUNNING:
            return simulation
        
        simulation.status = PortfolioSimulationStatus.PAUSED
        portfolio_repository.update_simulation(simulation)
        
        print(f"[PortfolioSimulationService] Paused simulation: {simulation_id}")
        return simulation
    
    def complete_simulation(
        self,
        simulation_id: str
    ) -> Optional[PortfolioSimulation]:
        """Mark simulation as completed"""
        simulation = portfolio_repository.get_simulation(simulation_id)
        if not simulation:
            return None
        
        simulation.status = PortfolioSimulationStatus.COMPLETED
        simulation.completed_at = datetime.now(timezone.utc)
        portfolio_repository.update_simulation(simulation)
        
        # Mark all slots as inactive
        slots = portfolio_repository.get_slots_by_simulation(simulation_id)
        for slot in slots:
            slot.status = SlotStatus.INACTIVE
            portfolio_repository.update_slot(slot)
        
        print(f"[PortfolioSimulationService] Completed simulation: {simulation_id}")
        return simulation
    
    # ===========================================
    # Strategy Slots
    # ===========================================
    
    def get_slots(
        self,
        simulation_id: str
    ) -> List[PortfolioStrategySlot]:
        """Get all slots for a simulation"""
        return portfolio_repository.get_slots_by_simulation(simulation_id)
    
    def get_slots_summary(
        self,
        simulation_id: str
    ) -> SlotsSummary:
        """Get summary of all slots"""
        slots = portfolio_repository.get_slots_by_simulation(simulation_id)
        
        summary = SlotsSummary(
            total_slots=len(slots),
            active_slots=len([s for s in slots if s.status == SlotStatus.ACTIVE]),
            inactive_slots=len([s for s in slots if s.status == SlotStatus.INACTIVE]),
            pending_slots=len([s for s in slots if s.status == SlotStatus.PENDING]),
            total_allocated_usd=sum(s.allocated_capital_usd for s in slots),
            total_current_usd=sum(s.current_capital_usd for s in slots)
        )
        
        # Calculate weight deviation
        if slots:
            deviations = [
                abs(s.current_weight - s.target_weight) 
                for s in slots
            ]
            summary.weight_deviation = sum(deviations) / len(deviations)
        
        return summary
    
    def enable_slot(
        self,
        slot_id: str
    ) -> Optional[PortfolioStrategySlot]:
        """Enable a slot"""
        slot = portfolio_repository.get_slot(slot_id)
        if not slot:
            return None
        
        slot.enabled = True
        slot.status = SlotStatus.ACTIVE
        return portfolio_repository.update_slot(slot)
    
    def disable_slot(
        self,
        slot_id: str
    ) -> Optional[PortfolioStrategySlot]:
        """Disable a slot"""
        slot = portfolio_repository.get_slot(slot_id)
        if not slot:
            return None
        
        slot.enabled = False
        slot.status = SlotStatus.INACTIVE
        return portfolio_repository.update_slot(slot)
    
    # ===========================================
    # Portfolio State
    # ===========================================
    
    def get_portfolio_state(
        self,
        simulation_id: str
    ) -> Optional[PortfolioState]:
        """Get current portfolio state"""
        return portfolio_state_service.get_portfolio_state(simulation_id)
    
    # ===========================================
    # Delete Simulation
    # ===========================================
    
    def delete_simulation(
        self,
        simulation_id: str
    ) -> bool:
        """Delete a simulation and all related data"""
        return portfolio_repository.delete_simulation(simulation_id)
    
    # ===========================================
    # Health
    # ===========================================
    
    def get_health(self) -> Dict[str, Any]:
        """Get service health status"""
        stats = portfolio_repository.get_stats()
        return {
            "service": "PortfolioSimulationService",
            "status": "healthy",
            "version": "s4.1",
            "stats": stats
        }


# Global singleton
portfolio_simulation_service = PortfolioSimulationService()
