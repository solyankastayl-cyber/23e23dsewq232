"""
Decision Trace — Sprint 2: Full Decision Narrative

Records every step of a decision through the canonical pipeline:
  Signal → R1 → R2 → Safety → Execution → Position

Each trace is a single document in MongoDB with timestamped steps.
This gives the operator full explainability of every decision.
"""

import time
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
from uuid import uuid4

logger = logging.getLogger(__name__)


class DecisionTrace:
    """
    One trace = one decision's full journey through the pipeline.
    
    Usage:
        trace = DecisionTrace(symbol="ETHUSDT", side="BUY")
        trace.add_step("SIGNAL", {...})
        trace.add_step("R1_SIZING", {...})
        trace.add_step("R2_ADAPTIVE", {...})
        trace.add_step("SAFETY", {...})
        trace.add_step("EXECUTION", {...})
        trace.add_step("POSITION", {...})
        await trace_service.save(trace)
    """
    
    def __init__(self, symbol: str, side: str, source: str = "TA_ENGINE"):
        self.trace_id = f"trace_{uuid4().hex[:12]}"
        self.symbol = symbol
        self.side = side
        self.source = source
        self.started_at = datetime.now(timezone.utc)
        self.steps: List[Dict[str, Any]] = []
        self.final_status = "IN_PROGRESS"  # IN_PROGRESS | EXECUTED | REJECTED | BLOCKED | PENDING
        self.final_reason = None
    
    def add_step(self, step_type: str, data: Dict[str, Any]):
        """Add a step to the trace."""
        self.steps.append({
            "step": step_type,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "ts_ms": int(time.time() * 1000),
            "data": data,
        })
    
    def finalize(self, status: str, reason: str = None):
        """Mark trace as complete."""
        self.final_status = status
        self.final_reason = reason
    
    def to_dict(self) -> dict:
        """Convert to MongoDB document (no _id)."""
        return {
            "trace_id": self.trace_id,
            "symbol": self.symbol,
            "side": self.side,
            "source": self.source,
            "started_at": self.started_at.isoformat(),
            "completed_at": datetime.now(timezone.utc).isoformat(),
            "duration_ms": int((datetime.now(timezone.utc) - self.started_at).total_seconds() * 1000),
            "steps": self.steps,
            "steps_count": len(self.steps),
            "final_status": self.final_status,
            "final_reason": self.final_reason,
        }


class DecisionTraceService:
    """
    Service for saving and retrieving decision traces.
    """
    
    def __init__(self, db):
        self.col = db.decision_traces
        logger.info("[DecisionTraceService] Initialized")
    
    async def save(self, trace: DecisionTrace):
        """Save a completed trace."""
        doc = trace.to_dict()
        await self.col.insert_one(doc)
        logger.info(f"[Trace] Saved {trace.trace_id}: {trace.symbol} {trace.side} → {trace.final_status}")
        return doc
    
    async def get_latest(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get latest traces."""
        traces = await self.col.find(
            {}, {"_id": 0}
        ).sort("started_at", -1).limit(limit).to_list(length=limit)
        return traces
    
    async def get_by_id(self, trace_id: str) -> Optional[Dict[str, Any]]:
        """Get trace by ID."""
        return await self.col.find_one({"trace_id": trace_id}, {"_id": 0})
    
    async def get_by_symbol(self, symbol: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get traces for a specific symbol."""
        traces = await self.col.find(
            {"symbol": symbol}, {"_id": 0}
        ).sort("started_at", -1).limit(limit).to_list(length=limit)
        return traces
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get trace statistics."""
        total = await self.col.count_documents({})
        executed = await self.col.count_documents({"final_status": "EXECUTED"})
        rejected = await self.col.count_documents({"final_status": "REJECTED"})
        blocked = await self.col.count_documents({"final_status": "BLOCKED"})
        pending = await self.col.count_documents({"final_status": "PENDING"})
        
        return {
            "total_traces": total,
            "executed": executed,
            "rejected": rejected,
            "blocked": blocked,
            "pending": pending,
            "pass_rate": round(executed / total * 100, 1) if total > 0 else 0,
        }


# ─── Singleton ─────────────────────────────────────────
_trace_service = None


def init_decision_trace_service(db) -> DecisionTraceService:
    global _trace_service
    _trace_service = DecisionTraceService(db)
    return _trace_service


def get_decision_trace_service() -> DecisionTraceService:
    if _trace_service is None:
        raise RuntimeError("DecisionTraceService not initialized")
    return _trace_service
