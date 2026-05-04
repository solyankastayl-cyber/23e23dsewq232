"""
Execution Types — PHASE 2.4

Supported order types and execution constants.
"""

# Order types
ORDER_TYPE_LIMIT = "limit"
ORDER_TYPE_MARKET = "market"
ORDER_TYPE_BREAKOUT = "breakout"

VALID_ORDER_TYPES = {ORDER_TYPE_LIMIT, ORDER_TYPE_MARKET, ORDER_TYPE_BREAKOUT}

# Directions
DIRECTION_LONG = "long"
DIRECTION_SHORT = "short"

VALID_DIRECTIONS = {DIRECTION_LONG, DIRECTION_SHORT}
