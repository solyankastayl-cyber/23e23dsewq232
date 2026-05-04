"""
PHASE 11.6.5 - Change Audit
============================
Tracks all changes made by adaptive system.

Records:
- What was changed
- Why (evidence/metrics)
- Who approved (which gate)
- Result after change
"""

from typing import Dict, Optional, List
from datetime import datetime, timezone
from dataclasses import dataclass
from enum import Enum


class ChangeOutcome(str, Enum):
    """Outcome of a change after implementation."""
    PENDING = "PENDING"
    POSITIVE = "POSITIVE"
    NEGATIVE = "NEGATIVE"
    NEUTRAL = "NEUTRAL"
    ROLLED_BACK = "ROLLED_BACK"


@dataclass
class ChangeRecord:
    """Record of an adaptive change."""
    record_id: str
    timestamp: datetime
    
    # What changed
    change_type: str              # PARAMETER, WEIGHT, STRATEGY, ALLOCATION
    target: str                   # What was changed
    old_value: any
    new_value: any
    
    # Why
    trigger_reason: str
    evidence: Dict
    confidence: float
    
    # Approval
    approved_by: str              # Which gate/mechanism approved
    safety_checks_passed: List[str]
    
    # Outcome (updated later)
    outcome: ChangeOutcome = ChangeOutcome.PENDING
    outcome_metrics: Dict = None
    outcome_timestamp: Optional[datetime] = None
    
    def to_dict(self) -> Dict:
        return {
            "record_id": self.record_id,
            "timestamp": self.timestamp.isoformat(),
            "change_type": self.change_type,
            "target": self.target,
            "old_value": self.old_value,
            "new_value": self.new_value,
            "trigger_reason": self.trigger_reason,
            "evidence": self.evidence,
            "confidence": self.confidence,
            "approved_by": self.approved_by,
            "safety_checks_passed": self.safety_checks_passed,
            "outcome": self.outcome.value,
            "outcome_metrics": self.outcome_metrics,
            "outcome_timestamp": self.outcome_timestamp.isoformat() if self.outcome_timestamp else None
        }


class ChangeAudit:
    """
    Change Audit System
    
    Maintains complete audit trail of all adaptive changes
    for analysis, rollback capability, and learning.
    """
    
    def __init__(self):
        self.records: List[ChangeRecord] = []
        self.max_records = 1000
        self._record_counter = 0
    
    def record_change(
        self,
        change_type: str,
        target: str,
        old_value: any,
        new_value: any,
        trigger_reason: str,
        evidence: Dict,
        confidence: float,
        approved_by: str,
        safety_checks: List[str]
    ) -> ChangeRecord:
        """
        Record a new change.
        
        Args:
            change_type: Type of change
            target: What was changed
            old_value: Previous value
            new_value: New value
            trigger_reason: Why change was made
            evidence: Supporting evidence
            confidence: Confidence in change
            approved_by: Approving mechanism
            safety_checks: List of passed safety checks
            
        Returns:
            ChangeRecord
        """
        now = datetime.now(timezone.utc)
        self._record_counter += 1
        
        record = ChangeRecord(
            record_id=f"change_{self._record_counter}_{int(now.timestamp())}",
            timestamp=now,
            change_type=change_type,
            target=target,
            old_value=old_value,
            new_value=new_value,
            trigger_reason=trigger_reason,
            evidence=evidence,
            confidence=confidence,
            approved_by=approved_by,
            safety_checks_passed=safety_checks,
            outcome=ChangeOutcome.PENDING,
            outcome_metrics={}
        )
        
        self.records.append(record)
        
        if len(self.records) > self.max_records:
            self.records = self.records[-self.max_records:]
        
        return record
    
    def update_outcome(
        self,
        record_id: str,
        outcome: ChangeOutcome,
        outcome_metrics: Dict
    ) -> bool:
        """Update the outcome of a change."""
        for record in self.records:
            if record.record_id == record_id:
                record.outcome = outcome
                record.outcome_metrics = outcome_metrics
                record.outcome_timestamp = datetime.now(timezone.utc)
                return True
        return False
    
    def get_record(self, record_id: str) -> Optional[ChangeRecord]:
        """Get a specific record."""
        for record in self.records:
            if record.record_id == record_id:
                return record
        return None
    
    def get_records_for_target(self, target: str) -> List[ChangeRecord]:
        """Get all records for a target."""
        return [r for r in self.records if r.target == target]
    
    def get_recent_changes(
        self,
        hours: int = 24,
        change_type: Optional[str] = None
    ) -> List[ChangeRecord]:
        """Get recent changes."""
        from datetime import timedelta
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
        
        recent = [r for r in self.records if r.timestamp >= cutoff]
        
        if change_type:
            recent = [r for r in recent if r.change_type == change_type]
        
        return recent
    
    def get_changes_to_rollback(self) -> List[ChangeRecord]:
        """Get changes that resulted in negative outcome."""
        return [
            r for r in self.records
            if r.outcome == ChangeOutcome.NEGATIVE
            and r.outcome_timestamp is not None
        ]
    
    def get_audit_summary(self) -> Dict:
        """Get summary of audit records."""
        if not self.records:
            return {"summary": "NO_RECORDS"}
        
        # Count by type
        by_type = {}
        for r in self.records:
            by_type[r.change_type] = by_type.get(r.change_type, 0) + 1
        
        # Count by outcome
        by_outcome = {}
        for r in self.records:
            by_outcome[r.outcome.value] = by_outcome.get(r.outcome.value, 0) + 1
        
        # Calculate success rate
        evaluated = [r for r in self.records if r.outcome != ChangeOutcome.PENDING]
        if evaluated:
            positive = sum(1 for r in evaluated if r.outcome == ChangeOutcome.POSITIVE)
            success_rate = positive / len(evaluated)
        else:
            success_rate = 0.0
        
        return {
            "total_records": len(self.records),
            "by_type": by_type,
            "by_outcome": by_outcome,
            "pending_evaluation": by_outcome.get("PENDING", 0),
            "success_rate": round(success_rate, 3),
            "avg_confidence": round(
                sum(r.confidence for r in self.records) / len(self.records), 3
            )
        }
    
    def export_for_analysis(self) -> List[Dict]:
        """Export all records for analysis."""
        return [r.to_dict() for r in self.records]
