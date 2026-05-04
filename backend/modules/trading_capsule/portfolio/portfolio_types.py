"""
Portfolio Types (S4.1)
======================

Type definitions for Portfolio Simulation module.

Includes:
- PortfolioSimulation: Main simulation entity
- PortfolioStrategySlot: Individual strategy allocation slot
- PortfolioState: Real-time portfolio state snapshot
"""

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from enum import Enum
import uuid


# ===========================================
# Enums
# ===========================================

class PortfolioSimulationStatus(Enum):
    """Portfolio simulation lifecycle status"""
    CREATED = "CREATED"           # Initial state
    RUNNING = "RUNNING"           # Active simulation
    PAUSED = "PAUSED"             # Temporarily paused
    COMPLETED = "COMPLETED"       # Finished simulation
    FAILED = "FAILED"             # Error state


class SlotStatus(Enum):
    """Strategy slot status"""
    ACTIVE = "ACTIVE"             # Slot is trading
    INACTIVE = "INACTIVE"         # Slot is disabled
    PENDING = "PENDING"           # Awaiting activation
    EXHAUSTED = "EXHAUSTED"       # Capital depleted


# ===========================================
# PortfolioSimulation (S4.1.1)
# ===========================================

@dataclass
class PortfolioSimulation:
    """
    Main portfolio simulation entity.
    
    Represents a multi-strategy portfolio simulation run.
    Links to allocation plan and manages strategy slots.
    """
    simulation_id: str = field(default_factory=lambda: f"psim_{uuid.uuid4().hex[:12]}")
    
    # Source
    allocation_plan_id: str = ""
    name: str = ""
    description: str = ""
    
    # Capital
    total_capital_usd: float = 0.0
    
    # Time bounds
    start_date: str = ""          # ISO date string
    end_date: str = ""            # ISO date string
    
    # Status
    status: PortfolioSimulationStatus = PortfolioSimulationStatus.CREATED
    
    # Timestamps
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    # Metadata
    version: int = 1
    tags: List[str] = field(default_factory=list)
    
    # Configuration
    config: Dict[str, Any] = field(default_factory=lambda: {
        "rebalance_enabled": False,
        "rebalance_frequency": "none",
        "stop_on_drawdown": False,
        "max_drawdown_pct": 0.25
    })
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "simulation_id": self.simulation_id,
            "allocation_plan_id": self.allocation_plan_id,
            "name": self.name,
            "description": self.description,
            "capital": {
                "total_capital_usd": round(self.total_capital_usd, 2)
            },
            "time_bounds": {
                "start_date": self.start_date,
                "end_date": self.end_date
            },
            "status": self.status.value,
            "timestamps": {
                "created_at": self.created_at.isoformat() if self.created_at else None,
                "started_at": self.started_at.isoformat() if self.started_at else None,
                "completed_at": self.completed_at.isoformat() if self.completed_at else None
            },
            "version": self.version,
            "tags": self.tags,
            "config": self.config
        }


# ===========================================
# PortfolioStrategySlot (S4.1.2)
# ===========================================

@dataclass
class PortfolioStrategySlot:
    """
    Individual strategy slot within portfolio.
    
    Each strategy in the portfolio gets a slot with:
    - Target weight from allocation plan
    - Allocated capital
    - Current position state
    """
    slot_id: str = field(default_factory=lambda: f"slot_{uuid.uuid4().hex[:8]}")
    
    # Parent references
    simulation_id: str = ""
    strategy_id: str = ""
    
    # Allocation
    target_weight: float = 0.0           # 0-1 scale from allocation plan
    allocated_capital_usd: float = 0.0   # Target capital for this slot
    
    # Current state (to be updated in S4.2)
    current_capital_usd: float = 0.0
    current_weight: float = 0.0
    
    # Status
    status: SlotStatus = SlotStatus.PENDING
    enabled: bool = True
    
    # Position tracking (S4.2+ will populate)
    position_count: int = 0
    has_open_position: bool = False
    
    # Performance (S4.2+ will calculate)
    realized_pnl_usd: float = 0.0
    unrealized_pnl_usd: float = 0.0
    total_trades: int = 0
    
    # Timestamps
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_updated_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "slot_id": self.slot_id,
            "simulation_id": self.simulation_id,
            "strategy_id": self.strategy_id,
            "allocation": {
                "target_weight": round(self.target_weight, 4),
                "target_weight_pct": f"{self.target_weight * 100:.2f}%",
                "allocated_capital_usd": round(self.allocated_capital_usd, 2)
            },
            "current": {
                "current_capital_usd": round(self.current_capital_usd, 2),
                "current_weight": round(self.current_weight, 4),
                "current_weight_pct": f"{self.current_weight * 100:.2f}%"
            },
            "status": {
                "slot_status": self.status.value,
                "enabled": self.enabled
            },
            "position": {
                "position_count": self.position_count,
                "has_open_position": self.has_open_position
            },
            "performance": {
                "realized_pnl_usd": round(self.realized_pnl_usd, 2),
                "unrealized_pnl_usd": round(self.unrealized_pnl_usd, 2),
                "total_pnl_usd": round(self.realized_pnl_usd + self.unrealized_pnl_usd, 2),
                "total_trades": self.total_trades
            },
            "timestamps": {
                "created_at": self.created_at.isoformat() if self.created_at else None,
                "last_updated_at": self.last_updated_at.isoformat() if self.last_updated_at else None
            }
        }


# ===========================================
# PortfolioState (S4.1.3)
# ===========================================

@dataclass
class PortfolioState:
    """
    Real-time portfolio state snapshot.
    
    Captures the current financial state of the portfolio.
    Updated on every trade/event.
    """
    state_id: str = field(default_factory=lambda: f"pstate_{uuid.uuid4().hex[:8]}")
    
    # Parent
    simulation_id: str = ""
    
    # Capital breakdown
    equity_usd: float = 0.0              # Total portfolio value
    cash_usd: float = 0.0                # Available cash
    used_capital_usd: float = 0.0        # Capital in positions
    free_capital_usd: float = 0.0        # Cash available for new positions
    
    # Margin (for future use)
    margin_used_usd: float = 0.0
    margin_available_usd: float = 0.0
    
    # Performance
    total_pnl_usd: float = 0.0
    total_pnl_pct: float = 0.0
    
    # High water marks
    peak_equity_usd: float = 0.0
    drawdown_usd: float = 0.0
    drawdown_pct: float = 0.0
    
    # Position summary
    total_positions: int = 0
    open_positions: int = 0
    
    # Timestamp
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    # State version for optimistic locking
    version: int = 1
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "state_id": self.state_id,
            "simulation_id": self.simulation_id,
            "capital": {
                "equity_usd": round(self.equity_usd, 2),
                "cash_usd": round(self.cash_usd, 2),
                "used_capital_usd": round(self.used_capital_usd, 2),
                "free_capital_usd": round(self.free_capital_usd, 2)
            },
            "margin": {
                "used_usd": round(self.margin_used_usd, 2),
                "available_usd": round(self.margin_available_usd, 2)
            },
            "performance": {
                "total_pnl_usd": round(self.total_pnl_usd, 2),
                "total_pnl_pct": round(self.total_pnl_pct, 4)
            },
            "risk": {
                "peak_equity_usd": round(self.peak_equity_usd, 2),
                "drawdown_usd": round(self.drawdown_usd, 2),
                "drawdown_pct": round(self.drawdown_pct, 4)
            },
            "positions": {
                "total": self.total_positions,
                "open": self.open_positions
            },
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "version": self.version
        }


# ===========================================
# Slot Summary
# ===========================================

@dataclass
class SlotsSummary:
    """Summary of all slots in a simulation"""
    total_slots: int = 0
    active_slots: int = 0
    inactive_slots: int = 0
    pending_slots: int = 0
    total_allocated_usd: float = 0.0
    total_current_usd: float = 0.0
    weight_deviation: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "counts": {
                "total": self.total_slots,
                "active": self.active_slots,
                "inactive": self.inactive_slots,
                "pending": self.pending_slots
            },
            "capital": {
                "total_allocated_usd": round(self.total_allocated_usd, 2),
                "total_current_usd": round(self.total_current_usd, 2)
            },
            "weight_deviation": round(self.weight_deviation, 4)
        }
