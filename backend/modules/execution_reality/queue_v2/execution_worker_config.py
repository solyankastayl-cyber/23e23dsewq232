"""
Execution Worker Configuration (P1.3.2)
========================================

Конфигурация для execution queue worker runtime.

P1.3.2 Phase 1 Constraints (зафиксировано):
- worker_count = 1 (single-worker only)
- dry_run = true (no real exchange calls)
- mixed_mode = false (deterministic processing)
- allow_reclaim_in_flight = false (safety first)
"""

import os
from typing import Literal
from pydantic import BaseModel, Field


class ExecutionWorkerConfig(BaseModel):
    """
    Execution Worker Configuration.
    
    P1.3.2B: Multi-worker support (2-3 workers).
    """
    # Worker Count (P1.3.2B:允许 multi-worker)
    worker_count: int = Field(
        default=2,
        ge=1,
        le=5,
        description="Number of worker instances (P1.3.2B: 1-5 workers allowed)"
    )
    
    # Dry-Run Mode (P1.3.2B: still dry-run)
    dry_run: bool = Field(
        default=True,
        description="Dry-run mode (no real exchange submit, still true for P1.3.2B)"
    )
    
    # Processing Mode (P1.3.2B: allow mixed mode для retry testing)
    mixed_mode: bool = Field(
        default=True,
        description="Allow mixed processing strategies (P1.3.2B: enabled for retry testing)"
    )
    
    # Reclaim Policy (P1.3.2B: allow reclaim для leased jobs)
    allow_reclaim_leased: bool = Field(
        default=True,
        description="Allow reclaiming leased jobs with expired lease (P1.3.2B: enabled)"
    )
    
    # Reclaim In-Flight (P1.3.2B: still disabled)
    allow_reclaim_in_flight: bool = Field(
        default=False,
        description="Allow reclaiming in_flight jobs (P1.3.2B: still disabled)"
    )
    
    # Heartbeat Settings
    heartbeat_interval_seconds: int = Field(
        default=5,
        description="Heartbeat interval in seconds"
    )
    
    # Lease Settings
    lease_duration_seconds: int = Field(
        default=30,
        description="Lease timeout in seconds"
    )
    
    # Processing Settings
    poll_interval_seconds: float = Field(
        default=1.0,
        description="Queue polling interval in seconds"
    )
    
    max_job_processing_time_seconds: int = Field(
        default=20,
        description="Maximum time to process a single job (watchdog)"
    )
    
    # Shutdown Settings
    graceful_shutdown_timeout_seconds: int = Field(
        default=30,
        description="Graceful shutdown timeout (draining period)"
    )
    
    # Worker Lifecycle States
    worker_status: Literal["starting", "healthy", "busy", "draining", "stopped"] = Field(
        default="starting",
        description="Current worker status"
    )
    
    class Config:
        use_enum_values = True


# Global config instance
_worker_config: ExecutionWorkerConfig = ExecutionWorkerConfig()


def get_worker_config() -> ExecutionWorkerConfig:
    """Get global worker configuration."""
    return _worker_config


def set_worker_config(config: ExecutionWorkerConfig):
    """Set global worker configuration."""
    global _worker_config
    _worker_config = config


def validate_phase1_constraints(config: ExecutionWorkerConfig) -> bool:
    """
    Validate P1.3.2 Phase 1 constraints.
    
    DEPRECATED для P1.3.2B (multi-worker allowed).
    Сохранено для backward compatibility.
    
    Returns:
        True if all constraints satisfied
    
    Raises:
        ValueError if any constraint violated
    """
    violations = []
    
    if config.worker_count != 1:
        violations.append(f"[P1.3.2] worker_count must be 1 (got {config.worker_count})")
    
    if config.dry_run is not True:
        violations.append(f"dry_run must be True (got {config.dry_run})")
    
    if config.mixed_mode is not False:
        violations.append(f"[P1.3.2] mixed_mode must be False (got {config.mixed_mode})")
    
    if config.allow_reclaim_in_flight is not False:
        violations.append(f"allow_reclaim_in_flight must be False (got {config.allow_reclaim_in_flight})")
    
    if violations:
        raise ValueError(
            f"P1.3.2 Phase 1 constraint violations: {', '.join(violations)}"
        )
    
    return True


def validate_phase2b_constraints(config: ExecutionWorkerConfig) -> bool:
    """
    Validate P1.3.2B constraints.
    
    P1.3.2B allows:
    - worker_count: 1-5
    - dry_run: true (still required)
    - mixed_mode: true (for retry testing)
    - allow_reclaim_leased: true (zombie reclaim)
    - allow_reclaim_in_flight: false (still prohibited)
    
    Returns:
        True if all constraints satisfied
    
    Raises:
        ValueError if any constraint violated
    """
    violations = []
    
    if not (1 <= config.worker_count <= 5):
        violations.append(f"worker_count must be 1-5 (got {config.worker_count})")
    
    if config.dry_run is not True:
        violations.append(f"dry_run must be True (got {config.dry_run})")
    
    if config.allow_reclaim_in_flight is not False:
        violations.append(f"allow_reclaim_in_flight must be False (got {config.allow_reclaim_in_flight})")
    
    if violations:
        raise ValueError(
            f"P1.3.2B constraint violations: {', '.join(violations)}"
        )
    
    return True
