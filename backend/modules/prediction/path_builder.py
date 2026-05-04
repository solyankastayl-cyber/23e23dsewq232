"""
Path Builder

Builds curved prediction paths with confidence bands.
"""

import math
from typing import List, Dict
from datetime import datetime, timedelta

from .types import (
    PredictionInput,
    Scenario,
    PathPoint,
    TIMEFRAME_HORIZONS,
)


def resolve_horizon(timeframe: str) -> int:
    """
    Resolve timeframe to horizon in days.
    """
    return TIMEFRAME_HORIZONS.get(timeframe, 5)


def build_paths_for_scenarios(
    scenarios: Dict[str, Scenario],
    price: float,
    horizon_days: int,
    volatility: float,
    start_time: datetime = None,
) -> Dict[str, Scenario]:
    """
    Build paths and bands for all scenarios.
    """
    start_time = start_time or datetime.utcnow()
    
    for name, scenario in scenarios.items():
        # Build main path
        scenario.path = build_curved_path(
            price=price,
            target=scenario.target_price,
            horizon_days=horizon_days,
            start_time=start_time,
        )
        
        # Build confidence bands
        bands = build_bands(
            path=scenario.path,
            volatility=volatility,
            scenario_name=name,
        )
        scenario.band_low = bands["low"]
        scenario.band_high = bands["high"]
    
    return scenarios


def build_curved_path(
    price: float,
    target: float,
    horizon_days: int,
    start_time: datetime = None,
) -> List[PathPoint]:
    """
    Build curved (non-linear) prediction path.
    
    Uses ease-out curve for natural price movement:
    - Fast initial move
    - Slowing as it approaches target
    
    Formula: progress = 1 - (1 - t)^2
    """
    start_time = start_time or datetime.utcnow()
    path = []
    
    steps = horizon_days
    
    for i in range(steps + 1):
        # Linear progress 0 to 1
        t = i / steps if steps > 0 else 1
        
        # Apply ease-out curve
        curve = _ease_out_quad(t)
        
        # Calculate price at this point
        value = price + (target - price) * curve
        
        # Calculate timestamp
        timestamp = start_time + timedelta(days=i)
        
        path.append(PathPoint(
            t=i,
            price=value,
            timestamp=timestamp,
        ))
    
    return path


def build_bands(
    path: List[PathPoint],
    volatility: float,
    scenario_name: str = "base",
) -> Dict[str, List[PathPoint]]:
    """
    Build confidence bands around the path.
    
    Band width increases with:
    - Time (farther = more uncertainty)
    - Volatility
    
    Bull scenario: wider upside band
    Bear scenario: wider downside band
    """
    low = []
    high = []
    
    # Base spread multiplier
    base_spread = volatility * 0.5
    
    # Scenario-specific asymmetry
    if scenario_name == "bull":
        low_mult = 0.7
        high_mult = 1.3
    elif scenario_name == "bear":
        low_mult = 1.3
        high_mult = 0.7
    else:
        low_mult = 1.0
        high_mult = 1.0
    
    for i, point in enumerate(path):
        # Time factor: uncertainty grows with time
        time_factor = 1 + (i / len(path)) * 0.5
        
        # Calculate spread at this point
        spread = point.price * base_spread * time_factor
        
        low.append(PathPoint(
            t=point.t,
            price=point.price - spread * low_mult,
            timestamp=point.timestamp,
        ))
        
        high.append(PathPoint(
            t=point.t,
            price=point.price + spread * high_mult,
            timestamp=point.timestamp,
        ))
    
    return {"low": low, "high": high}


def _ease_out_quad(t: float) -> float:
    """
    Ease-out quadratic curve.
    
    Fast start, slow finish.
    f(t) = 1 - (1 - t)^2
    """
    return 1 - (1 - t) ** 2


def _ease_in_out_quad(t: float) -> float:
    """
    Ease-in-out quadratic curve.
    
    Slow start, fast middle, slow end.
    """
    if t < 0.5:
        return 2 * t * t
    return 1 - (-2 * t + 2) ** 2 / 2


def _ease_out_cubic(t: float) -> float:
    """
    Ease-out cubic curve.
    
    Even faster start than quadratic.
    f(t) = 1 - (1 - t)^3
    """
    return 1 - (1 - t) ** 3
