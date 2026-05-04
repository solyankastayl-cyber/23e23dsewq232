"""
Portfolio Backtester — PHASE 2.5

Simulates portfolio-level trading:
- Sequential trade execution
- Equity curve tracking
- Capital management
- Drawdown computation
"""

from .portfolio_backtester import PortfolioBacktester
from .portfolio_state import PortfolioState
from .trade_ledger import TradeLedger
from .equity_engine import EquityEngine
from .drawdown_engine import DrawdownEngine
from .portfolio_metrics import PortfolioMetrics
from .capital_allocator import CapitalAllocator
