"""
Flow Snapshot Engine

PHASE 42.1 — Capital Flow Snapshot

Builds a unified snapshot of capital flows between BTC/ETH/ALTS/CASH.

Sources (from existing system data):
- Relative performance
- OI delta
- Funding delta
- Volume delta
- BTC/ETH dominance proxy
"""

from typing import Optional, Dict
from datetime import datetime, timezone

from .flow_types import (
    CapitalFlowSnapshot,
    FlowState,
    CapitalFlowConfig,
)


class FlowSnapshotEngine:
    """
    Builds capital flow snapshots from market data sources.
    """

    def __init__(self, config: Optional[CapitalFlowConfig] = None):
        self._config = config or CapitalFlowConfig()

    def build_snapshot(self, market_data: Optional[Dict] = None) -> CapitalFlowSnapshot:
        """
        Build a capital flow snapshot.

        market_data can contain:
        - btc_return, eth_return, alt_return (relative performance)
        - btc_oi_delta, eth_oi_delta, alt_oi_delta (OI shifts)
        - btc_funding, eth_funding, alt_funding (funding rates)
        - btc_volume_delta, eth_volume_delta, alt_volume_delta (volume shifts)
        - btc_dominance, eth_dominance (dominance %)
        - prev_btc_dominance, prev_eth_dominance (previous dominance %)
        """
        data = market_data or self._get_live_market_data()

        # Compute flow scores per bucket
        btc_flow = self._compute_bucket_flow("btc", data)
        eth_flow = self._compute_bucket_flow("eth", data)
        alt_flow = self._compute_bucket_flow("alt", data)

        # Cash flow is inverse of risk flows
        risk_avg = (btc_flow + eth_flow + alt_flow) / 3.0
        cash_flow = -risk_avg

        # Dominance shifts
        btc_dom_shift = data.get("btc_dominance", 0.0) - data.get("prev_btc_dominance", 0.0)
        eth_dom_shift = data.get("eth_dominance", 0.0) - data.get("prev_eth_dominance", 0.0)

        # Market structure shifts
        oi_shift = self._compute_aggregate_shift(data, "oi_delta")
        funding_shift = self._compute_aggregate_shift(data, "funding")
        volume_shift = self._compute_aggregate_shift(data, "volume_delta")

        # Determine flow state
        flow_state = self._determine_flow_state(btc_flow, eth_flow, alt_flow, cash_flow)

        return CapitalFlowSnapshot(
            btc_flow_score=self._clamp(btc_flow),
            eth_flow_score=self._clamp(eth_flow),
            alt_flow_score=self._clamp(alt_flow),
            cash_flow_score=self._clamp(cash_flow),
            btc_dominance_shift=btc_dom_shift,
            eth_dominance_shift=eth_dom_shift,
            oi_shift=oi_shift,
            funding_shift=funding_shift,
            volume_shift=volume_shift,
            flow_state=flow_state,
        )

    def _compute_bucket_flow(self, prefix: str, data: Dict) -> float:
        """
        Compute flow score for a single bucket.
        Combines performance, OI, funding, volume signals.
        """
        c = self._config

        perf = data.get(f"{prefix}_return", 0.0)
        oi = data.get(f"{prefix}_oi_delta", 0.0)
        funding = data.get(f"{prefix}_funding", 0.0)
        volume = data.get(f"{prefix}_volume_delta", 0.0)

        # Dominance contribution (only for BTC/ETH)
        dom = 0.0
        if prefix == "btc":
            dom = data.get("btc_dominance", 0.0) - data.get("prev_btc_dominance", 0.0)
        elif prefix == "eth":
            dom = data.get("eth_dominance", 0.0) - data.get("prev_eth_dominance", 0.0)

        flow = (
            c.performance_weight * perf
            + c.oi_weight * oi
            + c.funding_weight * funding
            + c.volume_weight * volume
            + c.dominance_weight * dom
        )

        return flow

    def _compute_aggregate_shift(self, data: Dict, suffix: str) -> float:
        """Compute aggregate shift across BTC/ETH/ALT."""
        btc = data.get(f"btc_{suffix}", 0.0)
        eth = data.get(f"eth_{suffix}", 0.0)
        alt = data.get(f"alt_{suffix}", 0.0)
        return (btc + eth + alt) / 3.0

    def _determine_flow_state(
        self,
        btc: float,
        eth: float,
        alt: float,
        cash: float,
    ) -> FlowState:
        """Determine the dominant flow state from scores."""
        scores = {
            FlowState.BTC_INFLOW: btc,
            FlowState.ETH_INFLOW: eth,
            FlowState.ALT_INFLOW: alt,
            FlowState.CASH_INFLOW: cash,
        }

        max_state = max(scores, key=scores.get)
        max_val = scores[max_state]

        # If dominant flow is weak or multiple are close → MIXED
        second_val = sorted(scores.values(), reverse=True)[1]
        if max_val < 0.05 or (max_val - second_val) < 0.03:
            return FlowState.MIXED_FLOW

        return max_state

    def _clamp(self, value: float, lo: float = -1.0, hi: float = 1.0) -> float:
        return max(lo, min(hi, value))

    def _get_live_market_data(self) -> Dict:
        """
        Get market data from existing system modules.
        Returns default structure if modules unavailable.
        """
        data = {
            "btc_return": 0.0, "eth_return": 0.0, "alt_return": 0.0,
            "btc_oi_delta": 0.0, "eth_oi_delta": 0.0, "alt_oi_delta": 0.0,
            "btc_funding": 0.0, "eth_funding": 0.0, "alt_funding": 0.0,
            "btc_volume_delta": 0.0, "eth_volume_delta": 0.0, "alt_volume_delta": 0.0,
            "btc_dominance": 0.50, "eth_dominance": 0.18,
            "prev_btc_dominance": 0.50, "prev_eth_dominance": 0.18,
        }

        # Try to get real data from existing modules
        try:
            from modules.portfolio_manager import get_portfolio_engine
            engine = get_portfolio_engine()
            state = engine.get_portfolio_state()
            # Use portfolio data as proxy for relative performance
            if hasattr(state, 'positions'):
                for pos in state.positions:
                    sym = pos.symbol.upper() if hasattr(pos, 'symbol') else ""
                    pnl_pct = pos.unrealized_pnl_pct if hasattr(pos, 'unrealized_pnl_pct') else 0.0
                    if "BTC" in sym:
                        data["btc_return"] = pnl_pct
                    elif "ETH" in sym:
                        data["eth_return"] = pnl_pct
        except Exception:
            pass

        return data
