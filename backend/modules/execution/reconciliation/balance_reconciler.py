"""
Balance Reconciler
==================

PHASE 4.2 - Reconciles balances between system and exchange.
Detects balance drift and margin mismatches.
"""

import time
import uuid
from typing import Dict, List

from .reconciliation_types import (
    ExchangeBalance,
    InternalBalance,
    Discrepancy,
    DiscrepancyType,
    DiscrepancySeverity,
    ResolutionStrategy
)


class BalanceReconciler:
    """
    Reconciles balances:
    - Balance drift (total differs)
    - Margin mismatch (locked vs expected)
    """

    def __init__(self):
        self._drift_tolerance_pct = 0.5  # 0.5% drift allowed
        self._margin_tolerance_pct = 1.0  # 1% margin mismatch allowed
        self._internal_balances: Dict[str, InternalBalance] = {}
        print("[BalanceReconciler] Initialized (PHASE 4.2)")

    def reconcile(
        self,
        exchange_balances: List[ExchangeBalance],
        exchange: str = "BINANCE"
    ) -> List[Discrepancy]:
        discrepancies = []
        now = int(time.time() * 1000)

        exchange_by_asset = {b.asset: b for b in exchange_balances if b.total > 0}
        internal_by_asset = {b.asset: b for b in self._internal_balances.values() if b.total > 0}

        # Check all exchange assets
        for asset, ex_bal in exchange_by_asset.items():
            if asset not in internal_by_asset:
                # Asset on exchange but not tracked — minor if small
                severity = DiscrepancySeverity.WARNING if ex_bal.total < 100 else DiscrepancySeverity.HIGH
                discrepancies.append(Discrepancy(
                    discrepancy_id=f"disc_{uuid.uuid4().hex[:8]}",
                    discrepancy_type=DiscrepancyType.BALANCE_DRIFT,
                    severity=severity,
                    exchange=exchange,
                    symbol=asset,
                    internal_value=0,
                    exchange_value=ex_bal.total,
                    difference=ex_bal.total,
                    difference_pct=100.0,
                    description=f"Untracked balance: {asset} = {ex_bal.total} on exchange",
                    details={"asset": asset, "exchangeTotal": ex_bal.total},
                    resolution_strategy=ResolutionStrategy.BALANCE_REFRESH,
                    detected_at=now
                ))
                continue

            int_bal = internal_by_asset[asset]

            # Total balance drift
            if int_bal.total > 0:
                drift = abs(ex_bal.total - int_bal.total)
                drift_pct = (drift / int_bal.total) * 100

                if drift_pct > self._drift_tolerance_pct:
                    severity = DiscrepancySeverity.CRITICAL if drift_pct > 5 else DiscrepancySeverity.HIGH
                    discrepancies.append(Discrepancy(
                        discrepancy_id=f"disc_{uuid.uuid4().hex[:8]}",
                        discrepancy_type=DiscrepancyType.BALANCE_DRIFT,
                        severity=severity,
                        exchange=exchange,
                        symbol=asset,
                        internal_value=int_bal.total,
                        exchange_value=ex_bal.total,
                        difference=drift,
                        difference_pct=drift_pct,
                        description=f"Balance drift: {asset} internal={int_bal.total:.4f} exchange={ex_bal.total:.4f} ({drift_pct:.2f}%)",
                        details={
                            "asset": asset,
                            "internalTotal": int_bal.total,
                            "exchangeTotal": ex_bal.total,
                            "internalAvailable": int_bal.available,
                            "exchangeAvailable": ex_bal.available
                        },
                        resolution_strategy=ResolutionStrategy.BALANCE_REFRESH,
                        detected_at=now
                    ))

            # Margin mismatch (locked funds)
            int_locked = int_bal.reserved
            ex_locked = ex_bal.locked
            if int_locked > 0 or ex_locked > 0:
                margin_diff = abs(ex_locked - int_locked)
                margin_base = max(int_locked, ex_locked, 0.0001)
                margin_diff_pct = (margin_diff / margin_base) * 100

                if margin_diff_pct > self._margin_tolerance_pct:
                    discrepancies.append(Discrepancy(
                        discrepancy_id=f"disc_{uuid.uuid4().hex[:8]}",
                        discrepancy_type=DiscrepancyType.MARGIN_MISMATCH,
                        severity=DiscrepancySeverity.HIGH,
                        exchange=exchange,
                        symbol=asset,
                        internal_value=int_locked,
                        exchange_value=ex_locked,
                        difference=margin_diff,
                        difference_pct=margin_diff_pct,
                        description=f"Margin mismatch: {asset} internal_reserved={int_locked:.4f} exchange_locked={ex_locked:.4f}",
                        details={
                            "asset": asset,
                            "internalReserved": int_locked,
                            "exchangeLocked": ex_locked
                        },
                        resolution_strategy=ResolutionStrategy.BALANCE_REFRESH,
                        detected_at=now
                    ))

        return discrepancies

    def set_balance(self, balance: InternalBalance):
        self._internal_balances[balance.asset] = balance

    def get_balance(self, asset: str) -> InternalBalance:
        return self._internal_balances.get(asset)

    def get_balances(self) -> List[InternalBalance]:
        return list(self._internal_balances.values())

    def sync_balance(self, exchange_balance: ExchangeBalance) -> InternalBalance:
        internal = InternalBalance(
            asset=exchange_balance.asset,
            total=exchange_balance.total,
            available=exchange_balance.available,
            reserved=exchange_balance.locked,
            updated_at=int(time.time() * 1000)
        )
        self._internal_balances[exchange_balance.asset] = internal
        return internal

    def clear(self):
        self._internal_balances.clear()

    def get_health(self) -> Dict:
        return {
            "engine": "BalanceReconciler",
            "version": "1.0.0",
            "phase": "4.2",
            "status": "active",
            "trackedAssets": len(self._internal_balances),
            "driftTolerance": self._drift_tolerance_pct,
            "marginTolerance": self._margin_tolerance_pct,
            "timestamp": int(time.time() * 1000)
        }


balance_reconciler = BalanceReconciler()
