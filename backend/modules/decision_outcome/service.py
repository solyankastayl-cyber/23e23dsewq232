"""
Decision Outcome — Sprint 5

Tracks the RESULT of each decision: WIN/LOSS/BREAKEVEN/CANCELLED.
This is the READ-ONLY analytics layer — it never influences the pipeline.

Source: pending_decisions (decision) + decision_traces (journey)
1 decision = 1 outcome
"""

import logging
import time
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class DecisionOutcomeService:
    """
    Computes and stores decision outcomes.
    
    READ ONLY — never changes pipeline, risk, or decisions.
    """
    
    def __init__(self, db):
        self.db = db
        self.outcomes_col = db.decision_outcomes
        self.decisions_col = db.pending_decisions
        self.traces_col = db.decision_traces
        logger.info("[DecisionOutcomeService] Initialized")
    
    async def compute_outcome(self, decision_id: str, pnl_usd: float = 0, pnl_pct: float = 0, duration_sec: int = 0) -> Dict[str, Any]:
        """
        Record outcome for a decision.
        Called when a position is closed.
        """
        # Determine status
        if pnl_pct > 0.1:
            status = "WIN"
        elif pnl_pct < -0.1:
            status = "LOSS"
        else:
            status = "BREAKEVEN"
        
        outcome = {
            "decision_id": decision_id,
            "status": status,
            "pnl_usd": round(pnl_usd, 2),
            "pnl_pct": round(pnl_pct, 4),
            "duration_sec": duration_sec,
            "closed_at": datetime.now(timezone.utc).isoformat(),
            "created_at": int(time.time()),
        }
        
        # Upsert (1 decision = 1 outcome)
        await self.outcomes_col.update_one(
            {"decision_id": decision_id},
            {"$set": outcome},
            upsert=True,
        )
        
        logger.info(f"[Outcome] {decision_id}: {status} pnl={pnl_pct:.2f}%")
        return outcome
    
    async def get_by_decision(self, decision_id: str) -> Optional[Dict[str, Any]]:
        """Get outcome for a specific decision."""
        doc = await self.outcomes_col.find_one({"decision_id": decision_id}, {"_id": 0})
        return doc
    
    async def get_analytics_summary(self) -> Dict[str, Any]:
        """
        Decision-centric analytics.
        
        Returns aggregated metrics from decisions + outcomes + traces.
        """
        # 1. Decision counts from pending_decisions
        total_decisions = await self.decisions_col.count_documents({})
        approved = await self.decisions_col.count_documents({"status": "APPROVED"})
        rejected = await self.decisions_col.count_documents({"status": "REJECTED"})
        executed = await self.decisions_col.count_documents({"status": "EXECUTED"})
        pending = await self.decisions_col.count_documents({"status": "PENDING"})
        expired = await self.decisions_col.count_documents({"status": "EXPIRED"})
        
        # 2. Outcome stats from decision_outcomes
        outcomes = await self.outcomes_col.find({}, {"_id": 0}).to_list(length=10000)
        
        wins = sum(1 for o in outcomes if o.get("status") == "WIN")
        losses = sum(1 for o in outcomes if o.get("status") == "LOSS")
        breakeven = sum(1 for o in outcomes if o.get("status") == "BREAKEVEN")
        
        total_with_outcome = wins + losses + breakeven
        win_rate = round(wins / total_with_outcome * 100, 1) if total_with_outcome > 0 else 0
        
        pnl_values = [o.get("pnl_pct", 0) for o in outcomes]
        avg_pnl = round(sum(pnl_values) / len(pnl_values), 2) if pnl_values else 0
        total_pnl_usd = round(sum(o.get("pnl_usd", 0) for o in outcomes), 2)
        
        durations = [o.get("duration_sec", 0) for o in outcomes if o.get("duration_sec")]
        avg_duration = round(sum(durations) / len(durations)) if durations else 0
        
        # 3. Trace-based analytics
        traces = await self.traces_col.find({}, {"_id": 0, "steps": 1, "source": 1, "final_status": 1}).to_list(length=10000)
        
        total_traces = len(traces)
        
        # Operator override: decisions where source is TRADE_THIS_BRIDGE (manual)
        operator_created = sum(1 for t in traces if t.get("source") == "TRADE_THIS_BRIDGE")
        operator_override_pct = round(operator_created / total_traces * 100, 1) if total_traces > 0 else 0
        
        # R2 active: traces that have R2_ADAPTIVE step with multiplier < 1
        r2_active = 0
        for t in traces:
            for s in t.get("steps", []):
                if s.get("step") == "R2_ADAPTIVE":
                    if s.get("data", {}).get("r2_multiplier", 1.0) < 0.99:
                        r2_active += 1
        r2_active_pct = round(r2_active / total_traces * 100, 1) if total_traces > 0 else 0
        
        # Source breakdown
        source_ta = sum(1 for t in traces if t.get("source") == "TA_ENGINE")
        source_manual = sum(1 for t in traces if t.get("source") == "TRADE_THIS_BRIDGE")
        
        # Status breakdown from traces
        trace_executed = sum(1 for t in traces if t.get("final_status") == "EXECUTED")
        trace_pending = sum(1 for t in traces if t.get("final_status") == "PENDING")
        trace_rejected = sum(1 for t in traces if t.get("final_status") == "REJECTED")
        trace_blocked = sum(1 for t in traces if t.get("final_status") == "BLOCKED")
        
        return {
            "total_decisions": total_decisions,
            "total_traces": total_traces,
            
            # Decision status
            "approved": approved,
            "rejected": rejected,
            "executed": executed,
            "pending": pending,
            "expired": expired,
            
            # Outcomes
            "wins": wins,
            "losses": losses,
            "breakeven": breakeven,
            "win_rate_pct": win_rate,
            "avg_pnl_pct": avg_pnl,
            "total_pnl_usd": total_pnl_usd,
            "avg_duration_sec": avg_duration,
            
            # Operator
            "operator_override_pct": operator_override_pct,
            "operator_created": operator_created,
            
            # R2
            "r2_active_pct": r2_active_pct,
            "r2_active_count": r2_active,
            
            # Source breakdown
            "source_ta": source_ta,
            "source_manual": source_manual,
            
            # Trace status
            "trace_executed": trace_executed,
            "trace_pending": trace_pending,
            "trace_rejected": trace_rejected,
            "trace_blocked": trace_blocked,
            
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    
    async def add_operator_note(self, decision_id: str, note: str) -> Dict[str, Any]:
        """
        Sprint 5.8: Operator Notes.
        Operator explains WHY they approved/rejected.
        This builds a training dataset.
        """
        await self.decisions_col.update_one(
            {"decision_id": decision_id},
            {"$set": {
                "operator_note": note,
                "note_at": int(time.time()),
            }}
        )
        logger.info(f"[Outcome] Note added to {decision_id}")
        return {"ok": True, "decision_id": decision_id}


# ─── Singleton ─────────────────────────────────────────
_service = None

def init_decision_outcome_service(db) -> DecisionOutcomeService:
    global _service
    _service = DecisionOutcomeService(db)
    return _service

def get_decision_outcome_service() -> DecisionOutcomeService:
    if _service is None:
        raise RuntimeError("DecisionOutcomeService not initialized")
    return _service
