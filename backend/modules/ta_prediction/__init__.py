"""TA Prediction Module — adapter for shared prediction core."""

from .ta_prediction_service import (
    map_ta_to_prediction_input,
    build_ta_prediction,
    build_ta_targets,
    get_live_price,
)

__all__ = [
    "map_ta_to_prediction_input",
    "build_ta_prediction",
    "build_ta_targets",
    "get_live_price",
]
