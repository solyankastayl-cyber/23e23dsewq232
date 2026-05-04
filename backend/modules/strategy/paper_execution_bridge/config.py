"""
Paper Execution Config
======================

Phase 3.0A configuration constants.
"""

# Paper execution configuration
PAPER_CONFIG = {
    # Position sizing
    "position_size_usd": 100,  # Fixed $100 per position
    
    # Time horizons
    "close_after_hours": 24,  # Fixed 24h close
    
    # Price source
    "use_live_price": True,  # Use live market price (not snapshot)
    
    # Balance tracking
    "track_balance": False,  # Per-position PnL only (no portfolio equity)
    
    # Execution protection
    "cooldown_hours_per_symbol": 4,  # Don't open new if OPEN exists within 4h
    "max_open_positions_global": 5,  # Max 5 open positions globally
    
    # Sanity checks
    "min_price": 0.0001,  # Skip if price <= this
}

# Paper decision statuses
class PaperDecisionStatus:
    """Paper decision lifecycle."""
    CREATED = "CREATED"  # Decision created, not yet executed
    EXECUTED = "EXECUTED"  # Position opened
    REJECTED = "REJECTED"  # Rejected by policy/checks
    FAILED = "FAILED"  # Execution failed (technical error)

# Paper position statuses
class PaperPositionStatus:
    """Paper position lifecycle."""
    OPEN = "OPEN"  # Position currently open
    CLOSED = "CLOSED"  # Position closed with PnL
