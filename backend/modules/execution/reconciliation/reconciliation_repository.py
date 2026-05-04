"""
Reconciliation Repository
=========================

PHASE 4.2 - In-memory persistence for reconciliation runs and events.
"""

import time
from typing import Dict, List, Optional

from .reconciliation_types import (
    ReconciliationRun,
    ReconciliationEvent,
    Discrepancy,
    ReconciliationSummary,
    DiscrepancySeverity,
    ResolutionStatus
)


class ReconciliationRepository:
    """Stores reconciliation runs, events, and discrepancy history."""

    def __init__(self):
        self._runs: List[ReconciliationRun] = []
        self._events: List[ReconciliationEvent] = []
        self._discrepancies: List[Discrepancy] = []
        self._max_runs = 100
        self._max_events = 1000
        self._max_discrepancies = 500
        print("[ReconciliationRepository] Initialized (PHASE 4.2)")

    def save_run(self, run: ReconciliationRun):
        self._runs.append(run)
        if len(self._runs) > self._max_runs:
            self._runs = self._runs[-self._max_runs:]

    def save_events(self, events: List[ReconciliationEvent]):
        self._events.extend(events)
        if len(self._events) > self._max_events:
            self._events = self._events[-self._max_events:]

    def save_discrepancies(self, discrepancies: List[Discrepancy]):
        self._discrepancies.extend(discrepancies)
        if len(self._discrepancies) > self._max_discrepancies:
            self._discrepancies = self._discrepancies[-self._max_discrepancies:]

    def get_runs(self, limit: int = 20) -> List[ReconciliationRun]:
        return self._runs[-limit:][::-1]

    def get_run(self, run_id: str) -> Optional[ReconciliationRun]:
        for r in reversed(self._runs):
            if r.run_id == run_id:
                return r
        return None

    def get_events(self, limit: int = 50) -> List[ReconciliationEvent]:
        return self._events[-limit:][::-1]

    def get_events_for_run(self, run_id: str) -> List[ReconciliationEvent]:
        return [e for e in self._events if e.run_id == run_id]

    def get_discrepancies(self, limit: int = 50, status: str = None) -> List[Discrepancy]:
        items = self._discrepancies
        if status:
            try:
                target = ResolutionStatus(status.upper())
                items = [d for d in items if d.resolution_status == target]
            except ValueError:
                pass
        return items[-limit:][::-1]

    def get_pending_discrepancies(self) -> List[Discrepancy]:
        return [d for d in self._discrepancies if d.resolution_status == ResolutionStatus.PENDING]

    def get_summary(self) -> ReconciliationSummary:
        last_run = self._runs[-1] if self._runs else None

        by_type: Dict[str, int] = {}
        by_severity: Dict[str, int] = {}
        pending = 0
        resolved = 0

        for d in self._discrepancies:
            t = d.discrepancy_type.value
            s = d.severity.value
            by_type[t] = by_type.get(t, 0) + 1
            by_severity[s] = by_severity.get(s, 0) + 1
            if d.resolution_status == ResolutionStatus.PENDING:
                pending += 1
            elif d.resolution_status == ResolutionStatus.RESOLVED:
                resolved += 1

        return ReconciliationSummary(
            total_runs=len(self._runs),
            last_run_at=last_run.completed_at if last_run else 0,
            last_run_status=last_run.status.value if last_run else "",
            total_discrepancies=len(self._discrepancies),
            pending_discrepancies=pending,
            resolved_discrepancies=resolved,
            by_type=by_type,
            by_severity=by_severity
        )

    def get_stats(self) -> Dict:
        return {
            "runs": len(self._runs),
            "events": len(self._events),
            "discrepancies": len(self._discrepancies),
            "pendingDiscrepancies": len(self.get_pending_discrepancies())
        }

    def clear(self):
        self._runs.clear()
        self._events.clear()
        self._discrepancies.clear()


reconciliation_repository = ReconciliationRepository()
