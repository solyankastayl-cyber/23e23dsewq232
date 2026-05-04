"""
Execution Configuration

Centralized configuration for execution routing and safety gates.
"""

EXECUTION_CONFIG = {
    # Default routing
    "default_route": "paper",  # simulation | paper | binance
    
    # Safety gate for live trading
    "allow_live": False,  # Must be explicitly enabled for binance
    
    # Paper trading simulation parameters
    "paper_slippage_bps": 3,  # 3 basis points slippage
    "paper_fee_bps": 5,       # 5 basis points trading fee
    
    # Order size limits (safety)
    "max_order_size_usd": 100000,  # $100k max per order
    "min_order_size_usd": 10,      # $10 minimum
    
    # Routing behavior
    "retry_on_failure": False,
    "max_retries": 0,
}
