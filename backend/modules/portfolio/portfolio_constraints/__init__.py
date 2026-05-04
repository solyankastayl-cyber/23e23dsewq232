"""
PHASE 18.2 — Portfolio Constraints Module
=========================================
Portfolio Constraint Engine.

Checks portfolio constraints before trade execution.
Determines if a new position CAN be opened even if signal is strong.

Constraint Types:
- HARD CONSTRAINTS: Cannot be violated (exposure, leverage)
- SOFT CONSTRAINTS: Can violate with penalty (cluster, factor)
"""

from modules.portfolio.portfolio_constraints.portfolio_constraint_engine import (
    get_portfolio_constraint_engine,
    PortfolioConstraintEngine,
)
from modules.portfolio.portfolio_constraints.portfolio_constraint_types import (
    PortfolioConstraintState,
    ConstraintState,
    ConstraintType,
    ConstraintViolation,
)

__all__ = [
    "get_portfolio_constraint_engine",
    "PortfolioConstraintEngine",
    "PortfolioConstraintState",
    "ConstraintState",
    "ConstraintType",
    "ConstraintViolation",
]
