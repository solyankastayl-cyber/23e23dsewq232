"""
Reconciliation Engine
=====================

PHASE 4.2 - Core orchestrator for execution reconciliation.

Flow:
  Fetch Exchange State -> Compare Internal -> Detect Discrepancies -> Resolve -> Log
"""

import time
import uuid
import random
from typing import Dict, List, Optional

from .reconciliation_types import (
    ExchangeState,
    ExchangePosition,
    ExchangeOrder,
    ExchangeBalance,
    ReconciliationRun,
    ReconciliationStatus,
    ReconciliationEvent
)
from .position_reconciler import position_reconciler, PositionReconciler
from .order_reconciler import order_reconciler, OrderReconciler
from .balance_reconciler import balance_reconciler, BalanceReconciler
from .discrepancy_resolver import discrepancy_resolver, DiscrepancyResolver
from .reconciliation_repository import reconciliation_repository


class ReconciliationEngine:
    """
    Main reconciliation orchestrator.
    Fetches exchange state (mock), compares with internal, detects discrepancies,
    resolves them, and logs everything.
    """

    def __init__(self):
        self._position_reconciler = position_reconciler
        self._order_reconciler = order_reconciler
        self._balance_reconciler = balance_reconciler
        self._discrepancy_resolver = discrepancy_resolver
        self._repository = reconciliation_repository

        self._auto_reconcile_interval = 60  # seconds
        self._last_run_at = 0
        self._total_runs = 0

        print("[ReconciliationEngine] Initialized (PHASE 4.2)")

    def run_reconciliation(
        self,
        exchange: str = "BINANCE",
        check_positions: bool = True,
        check_orders: bool = True,
        check_balances: bool = True
    ) -> ReconciliationRun:
        """
        Run a full reconciliation cycle.
        """
        run_id = f"recon_{uuid.uuid4().hex[:8]}"
        started_at = int(time.time() * 1000)

        run = ReconciliationRun(
            run_id=run_id,
            exchange=exchange,
            status=ReconciliationStatus.RUNNING,
            check_positions=check_positions,
            check_orders=check_orders,
            check_balances=check_balances,
            started_at=started_at
        )

        events = []
        events.append(ReconciliationEvent(
            event_id=f"evt_{uuid.uuid4().hex[:8]}",
            event_type="RECONCILIATION_STARTED",
            run_id=run_id,
            details={"exchange": exchange, "scope": {
                "positions": check_positions,
                "orders": check_orders,
                "balances": check_balances
            }},
            timestamp=started_at
        ))

        all_discrepancies = []

        # 1. Fetch exchange state (mock)
        exchange_state = self._fetch_exchange_state(exchange)
        run.exchange_state = exchange_state

        # 2. Detect discrepancies
        if check_positions:
            pos_discs = self._position_reconciler.reconcile(
                exchange_state.positions, exchange
            )
            all_discrepancies.extend(pos_discs)

        if check_orders:
            ord_discs = self._order_reconciler.reconcile(
                exchange_state.orders, exchange
            )
            all_discrepancies.extend(ord_discs)

        if check_balances:
            bal_discs = self._balance_reconciler.reconcile(
                exchange_state.balances, exchange
            )
            all_discrepancies.extend(bal_discs)

        for disc in all_discrepancies:
            events.append(ReconciliationEvent(
                event_id=f"evt_{uuid.uuid4().hex[:8]}",
                event_type="DISCREPANCY_DETECTED",
                run_id=run_id,
                discrepancy_id=disc.discrepancy_id,
                details={
                    "type": disc.discrepancy_type.value,
                    "severity": disc.severity.value,
                    "symbol": disc.symbol,
                    "description": disc.description
                },
                timestamp=int(time.time() * 1000)
            ))

        run.discrepancies = all_discrepancies
        run.discrepancies_detected = len(all_discrepancies)

        # 3. Resolve discrepancies
        if all_discrepancies:
            resolved, failed, resolution_events = self._discrepancy_resolver.resolve_all(
                all_discrepancies,
                self._position_reconciler,
                self._order_reconciler,
                self._balance_reconciler,
                run_id
            )
            run.discrepancies_resolved = resolved
            run.discrepancies_failed = failed
            events.extend(resolution_events)

        # 4. Finalize
        completed_at = int(time.time() * 1000)
        run.completed_at = completed_at
        run.duration_ms = completed_at - started_at

        if run.discrepancies_failed > 0:
            run.status = ReconciliationStatus.PARTIAL
        else:
            run.status = ReconciliationStatus.COMPLETED

        events.append(ReconciliationEvent(
            event_id=f"evt_{uuid.uuid4().hex[:8]}",
            event_type="RECONCILIATION_COMPLETED",
            run_id=run_id,
            details={
                "status": run.status.value,
                "detected": run.discrepancies_detected,
                "resolved": run.discrepancies_resolved,
                "failed": run.discrepancies_failed,
                "durationMs": run.duration_ms
            },
            timestamp=completed_at
        ))

        # 5. Persist
        self._repository.save_run(run)
        self._repository.save_events(events)
        self._repository.save_discrepancies(all_discrepancies)

        self._last_run_at = completed_at
        self._total_runs += 1

        return run

    def _fetch_exchange_state(self, exchange: str) -> ExchangeState:
        """
        Mock exchange state. In production, this calls the exchange API adapter.
        Generates realistic positions, orders, and balances with some discrepancies.
        """
        now = int(time.time() * 1000)

        # Generate positions
        symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
        positions = []
        for sym in symbols:
            if random.random() > 0.3:  # 70% chance position exists
                positions.append(ExchangePosition(
                    symbol=sym,
                    side=random.choice(["LONG", "SHORT"]),
                    size=round(random.uniform(0.01, 2.0), 4),
                    entry_price=round(random.uniform(30000, 100000) if "BTC" in sym
                                      else random.uniform(1500, 4000) if "ETH" in sym
                                      else random.uniform(50, 200), 2),
                    unrealized_pnl=round(random.uniform(-500, 500), 2),
                    margin=round(random.uniform(100, 5000), 2),
                    leverage=random.choice([1, 3, 5, 10]),
                    liquidation_price=round(random.uniform(10000, 80000), 2),
                    updated_at=now
                ))

        # Generate orders
        orders = []
        for i in range(random.randint(1, 4)):
            sym = random.choice(symbols)
            qty = round(random.uniform(0.01, 1.0), 4)
            filled = round(random.uniform(0, qty), 4)
            status = "FILLED" if filled >= qty else "PARTIALLY_FILLED" if filled > 0 else random.choice(["NEW", "OPEN"])
            orders.append(ExchangeOrder(
                order_id=f"exch_ord_{uuid.uuid4().hex[:6]}",
                symbol=sym,
                side=random.choice(["BUY", "SELL"]),
                order_type=random.choice(["MARKET", "LIMIT"]),
                status=status,
                quantity=qty,
                filled_quantity=filled,
                price=round(random.uniform(30000, 100000) if "BTC" in sym
                             else random.uniform(1500, 4000) if "ETH" in sym
                             else random.uniform(50, 200), 2),
                avg_fill_price=round(random.uniform(30000, 100000) if "BTC" in sym
                                      else random.uniform(1500, 4000) if "ETH" in sym
                                      else random.uniform(50, 200), 2) if filled > 0 else 0,
                created_at=now - random.randint(60000, 3600000),
                updated_at=now
            ))

        # Generate balances
        balances = [
            ExchangeBalance(
                asset="USDT",
                total=round(random.uniform(5000, 50000), 2),
                available=round(random.uniform(3000, 40000), 2),
                locked=round(random.uniform(500, 5000), 2),
                unrealized_pnl=round(random.uniform(-200, 200), 2),
                updated_at=now
            ),
            ExchangeBalance(
                asset="BTC",
                total=round(random.uniform(0.1, 3.0), 6),
                available=round(random.uniform(0.05, 2.0), 6),
                locked=round(random.uniform(0, 0.5), 6),
                unrealized_pnl=0,
                updated_at=now
            )
        ]

        return ExchangeState(
            exchange=exchange,
            positions=positions,
            orders=orders,
            balances=balances,
            fetched_at=now
        )

    def get_status(self) -> Dict:
        summary = self._repository.get_summary()
        return {
            "engine": "ReconciliationEngine",
            "version": "1.0.0",
            "phase": "4.2",
            "status": "active",
            "totalRuns": self._total_runs,
            "lastRunAt": self._last_run_at,
            "autoInterval": self._auto_reconcile_interval,
            "summary": summary.to_dict(),
            "subEngines": {
                "positions": self._position_reconciler.get_health(),
                "orders": self._order_reconciler.get_health(),
                "balances": self._balance_reconciler.get_health(),
                "resolver": self._discrepancy_resolver.get_health()
            },
            "timestamp": int(time.time() * 1000)
        }

    def get_health(self) -> Dict:
        return {
            "engine": "ReconciliationEngine",
            "version": "1.0.0",
            "phase": "4.2",
            "status": "active",
            "totalRuns": self._total_runs,
            "timestamp": int(time.time() * 1000)
        }

    def clear(self):
        self._position_reconciler.clear()
        self._order_reconciler.clear()
        self._balance_reconciler.clear()
        self._discrepancy_resolver.clear()
        self._repository.clear()
        self._total_runs = 0
        self._last_run_at = 0


reconciliation_engine = ReconciliationEngine()
