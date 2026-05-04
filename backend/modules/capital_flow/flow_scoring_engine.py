"""
Flow Scoring Engine

PHASE 42.3 — Capital Flow Scoring

Final scoring: converts snapshot + rotation into a flow_bias decision.

flow_strength =
  0.50 * abs(rotation_strength)
  + 0.30 * abs(dominance_shift)
  + 0.20 * abs(volume_shift)

flow_confidence =
  0.60 * flow_strength
  + 0.40 * rotation_confidence

flow_bias: BTC / ETH / ALTS / CASH / NEUTRAL
"""

from typing import Optional
from datetime import datetime, timezone

from .flow_types import (
    CapitalFlowSnapshot,
    RotationState,
    FlowScore,
    FlowBias,
    RotationType,
    CapitalFlowConfig,
)


class FlowScoringEngine:
    """
    Computes final flow score from snapshot + rotation.
    """

    def __init__(self, config: Optional[CapitalFlowConfig] = None):
        self._config = config or CapitalFlowConfig()

    def compute_score(
        self,
        snapshot: CapitalFlowSnapshot,
        rotation: RotationState,
    ) -> FlowScore:
        """
        Compute flow score from snapshot and rotation.
        """
        c = self._config

        # Flow strength
        dominance_magnitude = (
            abs(snapshot.btc_dominance_shift) + abs(snapshot.eth_dominance_shift)
        ) / 2.0

        flow_strength = (
            c.score_weight_rotation * abs(rotation.rotation_strength)
            + c.score_weight_dominance * dominance_magnitude
            + c.score_weight_volume * abs(snapshot.volume_shift)
        )
        flow_strength = min(1.0, max(0.0, flow_strength))

        # Flow confidence
        flow_confidence = (
            c.confidence_weight_strength * flow_strength
            + c.confidence_weight_rotation * rotation.confidence
        )
        flow_confidence = min(1.0, max(0.0, flow_confidence))

        # Determine flow bias
        flow_bias = self._determine_bias(snapshot, rotation, flow_strength)

        return FlowScore(
            flow_bias=flow_bias,
            flow_strength=round(flow_strength, 4),
            flow_confidence=round(flow_confidence, 4),
            dominant_rotation=rotation.rotation_type,
        )

    def _determine_bias(
        self,
        snapshot: CapitalFlowSnapshot,
        rotation: RotationState,
        strength: float,
    ) -> FlowBias:
        """
        Determine flow bias from snapshot and rotation.

        Uses the rotation's "to_bucket" as primary signal,
        validated by flow scores.
        """
        if strength < self._config.min_flow_strength:
            return FlowBias.NEUTRAL

        if rotation.rotation_type == RotationType.NO_ROTATION:
            # Use raw flow scores
            return self._bias_from_flows(snapshot)

        # Rotation-driven bias: capital is flowing TO this bucket
        rotation_to_bias = {
            RotationType.BTC_TO_ETH: FlowBias.ETH,
            RotationType.ETH_TO_ALTS: FlowBias.ALTS,
            RotationType.ALTS_TO_BTC: FlowBias.BTC,
            RotationType.BTC_TO_CASH: FlowBias.CASH,
            RotationType.ETH_TO_CASH: FlowBias.CASH,
            RotationType.RISK_TO_CASH: FlowBias.CASH,
            RotationType.CASH_TO_BTC: FlowBias.BTC,
            RotationType.CASH_TO_ETH: FlowBias.ETH,
        }

        return rotation_to_bias.get(rotation.rotation_type, FlowBias.NEUTRAL)

    def _bias_from_flows(self, snapshot: CapitalFlowSnapshot) -> FlowBias:
        """Determine bias from raw flow scores when no rotation detected."""
        scores = {
            FlowBias.BTC: snapshot.btc_flow_score,
            FlowBias.ETH: snapshot.eth_flow_score,
            FlowBias.ALTS: snapshot.alt_flow_score,
            FlowBias.CASH: snapshot.cash_flow_score,
        }

        max_bias = max(scores, key=scores.get)
        max_val = scores[max_bias]

        if max_val < self._config.min_flow_strength:
            return FlowBias.NEUTRAL

        return max_bias
