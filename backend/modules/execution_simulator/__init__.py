"""
Execution Simulator — PHASE 2.4

Simulates real-world order execution:
- Order creation (limit / market / breakout)
- Latency impact
- Slippage modeling
- Fill logic (no magic fills)
"""

from .execution_simulator import ExecutionSimulator
from .order_simulator import OrderSimulator
from .fill_engine import FillEngine
from .slippage_engine import SlippageEngine
from .latency_engine import LatencyEngine
