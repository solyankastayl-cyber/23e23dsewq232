"""
PHASE 13.8 — Exchange Context Aggregator
==========================================
Combines all 5 engine outputs into a unified ExchangeContext.

Architecture:
  TA ─────────────┐
                   ├── Trading Decision Layer
  Exchange Intel ──┘

This module produces the "Exchange Intel" leg.
It knows NOTHING about TA. It only knows about the market.
"""

from datetime import datetime, timezone
from typing import Optional, Dict, List

from .exchange_intel_types import (
    ExchangeContext, ExchangeBias,
    FundingOISignal, DerivativesPressureSignal, LiquidationSignal,
    ExchangeFlowSignal, VolumeContextSignal,
    FundingState, OIPressureState, VolumeState,
)
from .exchange_intel_repository import ExchangeIntelRepository
from .funding_oi_engine import FundingOIEngine
from .derivatives_pressure_engine import DerivativesPressureEngine
from .exchange_liquidation_engine import ExchangeLiquidationEngine
from .exchange_flow_engine import ExchangeFlowEngine
from .exchange_volume_engine import ExchangeVolumeEngine


# ── Weights for bias computation ────────────────

W_FUNDING = 0.20
W_DERIVATIVES = 0.20
W_LIQUIDATION = 0.15
W_FLOW = 0.30
W_VOLUME = 0.15


class ExchangeContextAggregator:
    """
    Aggregates all exchange engine signals into a unified context.
    This is the main entry point for the Exchange Intelligence Module.
    """

    def __init__(self, repo: Optional[ExchangeIntelRepository] = None):
        self.repo = repo or ExchangeIntelRepository()
        self.funding_engine = FundingOIEngine(self.repo)
        self.derivatives_engine = DerivativesPressureEngine(self.repo)
        self.liquidation_engine = ExchangeLiquidationEngine(self.repo)
        self.flow_engine = ExchangeFlowEngine(self.repo)
        self.volume_engine = ExchangeVolumeEngine(self.repo)

    def compute(
        self,
        symbol: str,
        exchange_data: Optional[Dict] = None
    ) -> ExchangeContext:
        """
        Compute full exchange context for a symbol.

        Args:
            symbol: Trading pair (e.g., "BTC")
            exchange_data: Optional dict with pre-fetched exchange data.
                          If None, engines read from MongoDB/candles.
        """
        now = datetime.now(timezone.utc)

        # Run all engines
        funding_sig = self.funding_engine.compute(
            symbol,
            exchange_data.get("funding") if exchange_data else None
        )
        derivatives_sig = self.derivatives_engine.compute(
            symbol,
            exchange_data.get("derivatives") if exchange_data else None
        )
        liquidation_sig = self.liquidation_engine.compute(
            symbol,
            exchange_data.get("liquidation") if exchange_data else None
        )
        flow_sig = self.flow_engine.compute(
            symbol,
            exchange_data.get("flow") if exchange_data else None
        )
        volume_sig = self.volume_engine.compute(
            symbol,
            exchange_data.get("volume") if exchange_data else None
        )

        # Compute composite bias
        bias_score = self._compute_bias_score(
            funding_sig, derivatives_sig, liquidation_sig, flow_sig, volume_sig
        )

        # Classify bias
        if bias_score > 0.15:
            exchange_bias = ExchangeBias.BULLISH
        elif bias_score < -0.15:
            exchange_bias = ExchangeBias.BEARISH
        else:
            exchange_bias = ExchangeBias.NEUTRAL

        # Composite confidence (weighted avg of sub-confidences)
        confidence = (
            W_FUNDING * funding_sig.confidence
            + W_DERIVATIVES * derivatives_sig.confidence
            + W_LIQUIDATION * liquidation_sig.confidence
            + W_FLOW * flow_sig.confidence
            + W_VOLUME * volume_sig.confidence
        )

        # Aggregate drivers
        drivers = self._aggregate_drivers(
            funding_sig, derivatives_sig, liquidation_sig, flow_sig, volume_sig
        )

        # Derivatives pressure as scalar (-1 to 1)
        deriv_pressure = self._derivatives_to_scalar(derivatives_sig)

        # Flow pressure as scalar (-1 to 1)
        flow_pressure = flow_sig.aggressive_flow

        context = ExchangeContext(
            symbol=symbol,
            timestamp=now,
            exchange_bias=exchange_bias,
            confidence=confidence,
            funding_state=funding_sig.funding_state,
            oi_pressure=funding_sig.oi_pressure,
            derivatives_pressure=deriv_pressure,
            liquidation_risk=liquidation_sig.cascade_probability,
            flow_pressure=flow_pressure,
            volume_state=volume_sig.volume_state,
            crowding_risk=funding_sig.crowding_risk,
            squeeze_probability=derivatives_sig.squeeze_probability,
            cascade_probability=liquidation_sig.cascade_probability,
            drivers=drivers,
            funding_signal=funding_sig,
            derivatives_signal=derivatives_sig,
            liquidation_signal=liquidation_sig,
            flow_signal=flow_sig,
            volume_signal=volume_sig,
        )

        # Persist
        self.repo.save_exchange_context(context.to_dict())

        return context

    def compute_batch(
        self, symbols: List[str], exchange_data: Optional[Dict] = None
    ) -> List[ExchangeContext]:
        """Compute exchange context for multiple symbols."""
        results = []
        for sym in symbols:
            sym_data = exchange_data.get(sym) if exchange_data else None
            ctx = self.compute(sym, sym_data)
            results.append(ctx)
        return results

    def _compute_bias_score(
        self,
        funding: FundingOISignal,
        derivatives: DerivativesPressureSignal,
        liquidation: LiquidationSignal,
        flow: ExchangeFlowSignal,
        volume: VolumeContextSignal,
    ) -> float:
        """
        Compute composite bias from -1 (bearish) to 1 (bullish).
        Each engine contributes a directional score.
        """
        # Funding bias: negative funding = shorts paying longs = bullish
        funding_bias = 0.0
        if funding.funding_state in (FundingState.SHORT_CROWDED, FundingState.EXTREME_SHORT):
            funding_bias = 0.5  # Contrarian bullish
        elif funding.funding_state in (FundingState.LONG_CROWDED, FundingState.EXTREME_LONG):
            funding_bias = -0.5  # Contrarian bearish

        # OI pressure
        oi_bias = 0.0
        if funding.oi_pressure == OIPressureState.EXPANDING:
            oi_bias = 0.3  # Conviction in current trend
        elif funding.oi_pressure == OIPressureState.CONTRACTING:
            oi_bias = -0.2  # Reducing conviction

        # Derivatives: long/short ratio as signal
        deriv_bias = 0.0
        ls = derivatives.long_short_ratio
        if ls > 1.2:
            deriv_bias = -0.3  # Contrarian: too many longs
        elif ls < 0.8:
            deriv_bias = 0.3  # Contrarian: too many shorts

        # Liquidation risk direction
        liq_bias = 0.0
        if liquidation.net_liq_flow > 0.2:
            liq_bias = -0.3  # Long liquidations = bearish pressure
        elif liquidation.net_liq_flow < -0.2:
            liq_bias = 0.3  # Short liquidations = bullish pressure

        # Flow direction (strongest signal)
        flow_bias = flow.aggressive_flow

        # Volume confirmation
        vol_bias = 0.0
        if volume.volume_state == VolumeState.BREAKOUT_CONFIRMED:
            vol_bias = 0.3 if flow_bias > 0 else -0.3
        elif volume.volume_state == VolumeState.EXHAUSTION:
            vol_bias = -0.2 if flow_bias > 0 else 0.2  # Contrarian

        # Weighted sum
        raw = (
            W_FUNDING * (funding_bias + oi_bias)
            + W_DERIVATIVES * deriv_bias
            + W_LIQUIDATION * liq_bias
            + W_FLOW * flow_bias
            + W_VOLUME * vol_bias
        )

        return max(-1.0, min(1.0, raw))

    def _derivatives_to_scalar(self, sig: DerivativesPressureSignal) -> float:
        """Convert derivatives state to -1 to 1 scalar."""
        from .exchange_intel_types import DerivativesPressure as DP
        base = 0.0
        if sig.pressure_state == DP.SHORT_SQUEEZE:
            base = 0.6
        elif sig.pressure_state == DP.LONG_SQUEEZE:
            base = -0.6
        elif sig.pressure_state == DP.LEVERAGE_EXCESS:
            base = -0.3 if sig.long_short_ratio > 1.0 else 0.3

        # Scale by squeeze probability
        return base * max(sig.squeeze_probability, 0.3)

    def _aggregate_drivers(self, *signals) -> List[str]:
        """Collect top drivers from all engines."""
        all_drivers = []
        for sig in signals:
            all_drivers.extend(sig.drivers[:3])  # Top 3 from each
        return all_drivers[:10]  # Global top 10
