"""
Runtime Models — State & Config
"""

from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime


class RuntimeConfig(BaseModel):
    """Persistent runtime configuration."""
    config_id: str = "main"
    symbols: List[str] = Field(default_factory=lambda: ["BTCUSDT"])
    loop_interval_sec: int = 60
    mode: str = "MANUAL"  # MANUAL | SEMI_AUTO | AUTO
    enabled: bool = False
    updated_at: Optional[datetime] = None


class RuntimeState(BaseModel):
    """Runtime state snapshot."""
    enabled: bool
    mode: str
    status: str  # IDLE | RUNNING | ERROR | STOPPED
    loop_interval_sec: int
    symbols: List[str]
    last_run_at: Optional[int] = None
    next_run_at: Optional[int] = None
    last_error: Optional[str] = None
