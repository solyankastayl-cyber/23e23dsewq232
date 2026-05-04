"""
Regime-specific prediction models.

Each model is specialized for a particular market regime:
- trend_model: Strong directional movements
- range_model: Mean reversion within bounds
- compression_model: Breakout anticipation
- high_vol_model: Momentum-driven volatility
"""

from .trend_model import predict_trend
from .range_model import predict_range
from .compression_model import predict_compression
from .high_vol_model import predict_high_vol

__all__ = [
    "predict_trend",
    "predict_range", 
    "predict_compression",
    "predict_high_vol",
]
