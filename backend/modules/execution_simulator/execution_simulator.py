"""
Execution Simulator — PHASE 2.4 (Orchestrator)

Pipeline:
1. Order creation (from trade setup)
2. Latency impact (delayed price)
3. Slippage (volatility-based)
4. Fill logic (deterministic, no magic)

CRITICAL:
- Deterministic
- Simple math
- No ML
- Correctness first, realism later
"""

from .order_simulator import OrderSimulator
from .fill_engine import FillEngine
from .slippage_engine import SlippageEngine
from .latency_engine import LatencyEngine


class ExecutionSimulator:

    def simulate(self, trade_setup: dict, candle: dict, market_state: dict) -> dict:
        """
        Simulate execution of a trade setup against a candle.

        Args:
            trade_setup: {entry, stop, target, order_type, direction, position_size}
            candle: {open, high, low, close}
            market_state: {volatility, ...}

        Returns:
            {filled, entry_price, slippage, latency_price}
        """

        # 1. Order creation
        order = OrderSimulator().create_order(trade_setup)

        # 2. Latency impact
        delayed_price = LatencyEngine().apply(order, candle)

        # 3. Slippage
        slipped_price = SlippageEngine().apply(order, delayed_price, market_state)

        # 4. Fill logic
        fill = FillEngine().execute(order, slipped_price, candle)

        return {
            "filled": fill["filled"],
            "entry_price": fill.get("price"),
            "slippage": slipped_price - trade_setup["entry"],
            "latency_price": delayed_price,
        }
