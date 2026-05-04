"""
Rotation Detection Engine

PHASE 42.2 — Capital Rotation Detection

Determines capital rotation between buckets from a flow snapshot.

Formula:
rotation_strength =
  0.40 * relative_flow_diff
  + 0.20 * dominance_shift
  + 0.20 * oi_shift
  + 0.20 * volume_shift

Rotation types:
  BTC_TO_ETH, ETH_TO_ALTS, ALTS_TO_BTC,
  BTC_TO_CASH, ETH_TO_CASH, RISK_TO_CASH,
  CASH_TO_BTC, CASH_TO_ETH, NO_ROTATION
"""

from typing import Optional, List, Tuple
from datetime import datetime, timezone

from .flow_types import (
    CapitalFlowSnapshot,
    RotationState,
    RotationType,
    FlowBucket,
    CapitalFlowConfig,
)


# Rotation detection rules: (from_bucket, to_bucket, rotation_type)
_ROTATION_RULES: List[Tuple[str, str, RotationType]] = [
    ("btc", "eth", RotationType.BTC_TO_ETH),
    ("eth", "alt", RotationType.ETH_TO_ALTS),
    ("alt", "btc", RotationType.ALTS_TO_BTC),
    ("btc", "cash", RotationType.BTC_TO_CASH),
    ("eth", "cash", RotationType.ETH_TO_CASH),
    ("cash", "btc", RotationType.CASH_TO_BTC),
    ("cash", "eth", RotationType.CASH_TO_ETH),
]

_BUCKET_MAP = {
    "btc": FlowBucket.BTC,
    "eth": FlowBucket.ETH,
    "alt": FlowBucket.ALTS,
    "cash": FlowBucket.CASH,
}


class RotationDetectionEngine:
    """
    Detects capital rotation from flow snapshots.
    """

    def __init__(self, config: Optional[CapitalFlowConfig] = None):
        self._config = config or CapitalFlowConfig()

    def detect_rotation(self, snapshot: CapitalFlowSnapshot) -> RotationState:
        """
        Detect dominant rotation from a flow snapshot.
        """
        flows = {
            "btc": snapshot.btc_flow_score,
            "eth": snapshot.eth_flow_score,
            "alt": snapshot.alt_flow_score,
            "cash": snapshot.cash_flow_score,
        }

        best_rotation = RotationType.NO_ROTATION
        best_strength = 0.0
        best_from = FlowBucket.BTC
        best_to = FlowBucket.ETH

        # Check RISK_TO_CASH: all risk buckets outflow, cash inflow
        risk_to_cash_strength = self._check_risk_to_cash(snapshot, flows)
        if risk_to_cash_strength > best_strength:
            best_strength = risk_to_cash_strength
            best_rotation = RotationType.RISK_TO_CASH
            best_from = FlowBucket.ALTS  # representative
            best_to = FlowBucket.CASH

        # Check each pairwise rotation
        for from_key, to_key, rot_type in _ROTATION_RULES:
            strength = self._compute_rotation_strength(
                snapshot, flows, from_key, to_key
            )
            if strength > best_strength:
                best_strength = strength
                best_rotation = rot_type
                best_from = _BUCKET_MAP[from_key]
                best_to = _BUCKET_MAP[to_key]

        # Below threshold → NO_ROTATION
        if best_strength < self._config.min_rotation_strength:
            best_rotation = RotationType.NO_ROTATION
            best_strength = 0.0

        # Confidence
        confidence = self._compute_confidence(best_strength, snapshot)

        return RotationState(
            rotation_type=best_rotation,
            from_bucket=best_from,
            to_bucket=best_to,
            rotation_strength=min(1.0, max(0.0, best_strength)),
            confidence=min(1.0, max(0.0, confidence)),
        )

    def _compute_rotation_strength(
        self,
        snapshot: CapitalFlowSnapshot,
        flows: dict,
        from_key: str,
        to_key: str,
    ) -> float:
        """
        Compute rotation strength between two buckets.

        Formula:
        0.40 * relative_flow_diff
        + 0.20 * dominance_shift_component
        + 0.20 * oi_shift
        + 0.20 * volume_shift
        """
        c = self._config

        # Flow difference: to_bucket gaining, from_bucket losing
        from_flow = flows.get(from_key, 0.0)
        to_flow = flows.get(to_key, 0.0)
        flow_diff = to_flow - from_flow  # positive = rotation happening

        if flow_diff <= 0:
            return 0.0  # No rotation in this direction

        # Dominance component
        dom_component = self._get_dominance_component(snapshot, from_key, to_key)

        # OI and volume as supporting signals
        oi_component = abs(snapshot.oi_shift) if snapshot.oi_shift != 0 else 0.0
        vol_component = abs(snapshot.volume_shift) if snapshot.volume_shift != 0 else 0.0

        strength = (
            c.rotation_weight_flow_diff * flow_diff
            + c.rotation_weight_dominance * dom_component
            + c.rotation_weight_oi * oi_component
            + c.rotation_weight_volume * vol_component
        )

        return max(0.0, strength)

    def _check_risk_to_cash(self, snapshot: CapitalFlowSnapshot, flows: dict) -> float:
        """Check for broad risk-to-cash rotation."""
        btc = flows["btc"]
        eth = flows["eth"]
        alt = flows["alt"]
        cash = flows["cash"]

        # All risk assets losing, cash gaining
        if btc < 0 and eth < 0 and alt < 0 and cash > 0:
            risk_outflow = abs(btc) + abs(eth) + abs(alt)
            c = self._config
            strength = (
                c.rotation_weight_flow_diff * (cash + risk_outflow / 3.0)
                + c.rotation_weight_dominance * abs(snapshot.btc_dominance_shift + snapshot.eth_dominance_shift)
                + c.rotation_weight_oi * abs(snapshot.oi_shift)
                + c.rotation_weight_volume * abs(snapshot.volume_shift)
            )
            return max(0.0, strength)

        return 0.0

    def _get_dominance_component(
        self,
        snapshot: CapitalFlowSnapshot,
        from_key: str,
        to_key: str,
    ) -> float:
        """Get dominance shift component for rotation."""
        # BTC dominance dropping + ETH/ALT gaining
        if from_key == "btc":
            return max(0, -snapshot.btc_dominance_shift)
        if to_key == "btc":
            return max(0, snapshot.btc_dominance_shift)
        if from_key == "eth":
            return max(0, -snapshot.eth_dominance_shift)
        if to_key == "eth":
            return max(0, snapshot.eth_dominance_shift)
        return 0.0

    def _compute_confidence(self, strength: float, snapshot: CapitalFlowSnapshot) -> float:
        """Compute rotation confidence."""
        if strength <= 0:
            return 0.0

        # Multiple signals aligning increases confidence
        signal_count = 0
        if abs(snapshot.oi_shift) > 0.01:
            signal_count += 1
        if abs(snapshot.funding_shift) > 0.001:
            signal_count += 1
        if abs(snapshot.volume_shift) > 0.01:
            signal_count += 1
        if abs(snapshot.btc_dominance_shift) > 0.005:
            signal_count += 1
        if abs(snapshot.eth_dominance_shift) > 0.003:
            signal_count += 1

        alignment_bonus = min(0.3, signal_count * 0.06)
        confidence = min(1.0, strength * 0.8 + alignment_bonus)

        return confidence
