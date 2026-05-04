"""
Portfolio Models

Normalized portfolio state representation.
"""

from pydantic import BaseModel
from typing import List


class PortfolioSummary(BaseModel):
    """Aggregated portfolio state"""
    total_equity: float
    cash_balance: float
    positions_value: float
    
    unrealized_pnl: float
    realized_pnl: float
    total_pnl: float
    
    total_return_pct: float
    
    deployment_pct: float
    active_positions: int
    
    ath: float
    drawdown_pct: float
    
    class Config:
        json_encoders = {
            float: lambda v: round(v, 2)
        }


class EquityPoint(BaseModel):
    """Single equity snapshot"""
    timestamp: int
    equity: float
    
    class Config:
        json_encoders = {
            float: lambda v: round(v, 2)
        }


class AssetAllocation(BaseModel):
    """Asset allocation breakdown"""
    asset: str
    value: float
    pct: float
    
    class Config:
        json_encoders = {
            float: lambda v: round(v, 2)
        }
