"""
Constraint Engine — PHASE 2.7 (Orchestrator)

Runs all portfolio constraints against a new trade.
Returns allow/reject + modified position size if needed.
"""

from .asset_cap import AssetCap
from .direction_cap import DirectionCap
from .correlation_cap import CorrelationCap
from .portfolio_heat import PortfolioHeat


class ConstraintEngine:

    def __init__(
        self,
        asset_cap_pct: float = 0.20,
        max_long_pct: float = 0.60,
        max_short_pct: float = 0.40,
        max_correlated: int = 2,
        max_heat: float = 0.06,
    ):
        self.asset_cap = AssetCap(max_pct=asset_cap_pct)
        self.direction_cap = DirectionCap(max_long_pct=max_long_pct, max_short_pct=max_short_pct)
        self.correlation_cap = CorrelationCap(max_per_group=max_correlated)
        self.portfolio_heat = PortfolioHeat(max_heat=max_heat)

    def evaluate(self, positions: list, new_trade: dict, capital: float) -> dict:
        """
        Run all constraints.

        Args:
            positions: current open positions
            new_trade: proposed trade
            capital: total capital

        Returns:
            {allowed, rejected_by, checks, adjusted_risk}
        """
        checks = {}
        rejected_by = []

        # 1. Asset cap
        asset_check = self.asset_cap.check(positions, new_trade, capital)
        checks["asset_cap"] = asset_check
        if not asset_check["allowed"]:
            rejected_by.append("asset_cap")

        # 2. Direction cap
        dir_check = self.direction_cap.check(positions, new_trade, capital)
        checks["direction_cap"] = dir_check
        if not dir_check["allowed"]:
            rejected_by.append("direction_cap")

        # 3. Correlation cap
        corr_check = self.correlation_cap.check(positions, new_trade)
        checks["correlation_cap"] = corr_check
        if not corr_check["allowed"]:
            rejected_by.append("correlation_cap")

        # 4. Portfolio heat
        heat_check = self.portfolio_heat.check(positions, new_trade, capital)
        checks["portfolio_heat"] = heat_check
        if not heat_check["allowed"]:
            rejected_by.append("portfolio_heat")

        # Adjusted risk (if heat is the only constraint)
        adjusted_risk = None
        if "portfolio_heat" in rejected_by and len(rejected_by) == 1:
            adjusted_risk = self.portfolio_heat.compute_adjusted_size(positions, new_trade, capital)

        return {
            "allowed": len(rejected_by) == 0,
            "rejected_by": rejected_by,
            "checks": checks,
            "adjusted_risk": adjusted_risk,
        }
