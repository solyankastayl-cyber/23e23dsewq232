"""
Execution Shadow Diff Repository (P1.3.1D)
==========================================

Репозиторий для сохранения и извлечения diff-ов между queue и legacy intents.
"""

import logging
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
from motor.motor_asyncio import AsyncIOMotorDatabase

from .execution_shadow_diff_models import ExecutionShadowDiff

logger = logging.getLogger(__name__)


class ExecutionShadowDiffRepository:
    """
    Repository для execution_shadow_diff коллекции.
    
    Хранит результаты сравнения queue vs legacy intents.
    """
    
    def __init__(self, db: AsyncIOMotorDatabase):
        """
        Args:
            db: MongoDB database
        """
        self.collection = db["execution_shadow_diff"]
        logger.info("✅ ExecutionShadowDiffRepository initialized (P1.3.1D)")
    
    async def ensure_indexes(self):
        """Create required indexes."""
        # Trace ID lookup
        await self.collection.create_index("traceId")
        
        # Job ID lookup
        await self.collection.create_index("jobId")
        
        # Severity filtering
        await self.collection.create_index("severity")
        
        # Match status filtering
        await self.collection.create_index("match")
        
        # Timestamp for cleanup/retention
        await self.collection.create_index("createdAt")
        
        logger.info("✅ execution_shadow_diff indexes created")
    
    async def save_diff(
        self,
        trace_id: str,
        job_id: Optional[str],
        queue_intent,
        legacy_intent,
        match: bool,
        diff: Dict[str, Any],
        severity: str
    ) -> str:
        """
        Сохранить diff между queue и legacy intents.
        
        Args:
            trace_id: Causal trace ID
            job_id: Queue job ID (если был создан)
            queue_intent: Normalized queue intent (ExecutionIntent or None)
            legacy_intent: Normalized legacy intent (ExecutionIntent or None)
            match: True если полное совпадение
            diff: Детали различий
            severity: Уровень критичности (CRITICAL/HIGH/MEDIUM/LOW/NONE)
        
        Returns:
            Created diff document ID
        """
        diff_doc = ExecutionShadowDiff(
            traceId=trace_id,
            jobId=job_id,
            queueIntent=queue_intent,
            legacyIntent=legacy_intent,
            match=match,
            diff=diff,
            severity=severity
        )
        
        result = await self.collection.insert_one(diff_doc.dict())
        
        logger.info(
            f"✅ [P1.3.1D Diff] Saved shadow diff: trace_id={trace_id}, "
            f"match={match}, severity={severity}, job_id={job_id}"
        )
        
        return str(result.inserted_id)
    
    async def get_by_trace_id(self, trace_id: str) -> Optional[ExecutionShadowDiff]:
        """Get diff by trace ID."""
        doc = await self.collection.find_one({"traceId": trace_id})
        if doc:
            return ExecutionShadowDiff(**doc)
        return None
    
    async def get_by_job_id(self, job_id: str) -> Optional[ExecutionShadowDiff]:
        """Get diff by job ID."""
        doc = await self.collection.find_one({"jobId": job_id})
        if doc:
            return ExecutionShadowDiff(**doc)
        return None
    
    async def list_recent(
        self,
        limit: int = 100,
        severity_filter: Optional[str] = None,
        match_filter: Optional[bool] = None
    ) -> List[ExecutionShadowDiff]:
        """
        List recent diffs with optional filtering.
        
        Args:
            limit: Maximum number of diffs to return
            severity_filter: Filter by severity (CRITICAL/HIGH/MEDIUM/LOW/NONE)
            match_filter: Filter by match status (True/False)
        
        Returns:
            List of ExecutionShadowDiff
        """
        query = {}
        
        if severity_filter:
            query["severity"] = severity_filter
        
        if match_filter is not None:
            query["match"] = match_filter
        
        cursor = self.collection.find(query).sort("createdAt", -1).limit(limit)
        
        diffs = []
        async for doc in cursor:
            diffs.append(ExecutionShadowDiff(**doc))
        
        return diffs
    
    async def get_consistency_metrics(self, limit: int = 100) -> Dict[str, Any]:
        """
        Вычислить метрики консистентности (match rate, mismatch breakdown).
        
        Args:
            limit: Количество последних diff-ов для анализа
        
        Returns:
            {
                "total": int,
                "match_rate": float,
                "mismatch_rate": float,
                "by_severity": {"CRITICAL": int, "HIGH": int, ...},
                "top_fields": {"quantity": int, "price": int, ...}
            }
        """
        # Get recent diffs
        cursor = self.collection.find().sort("createdAt", -1).limit(limit)
        
        total = 0
        matches = 0
        severity_counts = {
            "CRITICAL": 0,
            "HIGH": 0,
            "MEDIUM": 0,
            "LOW": 0,
            "NONE": 0
        }
        field_mismatch_counts = {}
        
        async for doc in cursor:
            total += 1
            
            if doc.get("match"):
                matches += 1
            
            severity = doc.get("severity", "NONE")
            severity_counts[severity] = severity_counts.get(severity, 0) + 1
            
            # Подсчитать field mismatches
            diff = doc.get("diff", {})
            for field, value in diff.items():
                if field.endswith("_match") and value is False:
                    # Extract field name (e.g., "quantity_match" → "quantity")
                    field_name = field.replace("_match", "")
                    field_mismatch_counts[field_name] = field_mismatch_counts.get(field_name, 0) + 1
        
        if total == 0:
            return {
                "total": 0,
                "match_rate": 0.0,
                "mismatch_rate": 0.0,
                "by_severity": severity_counts,
                "top_fields": {}
            }
        
        match_rate = matches / total
        mismatch_rate = 1.0 - match_rate
        
        # Sort field mismatches by count
        top_fields = dict(sorted(field_mismatch_counts.items(), key=lambda x: x[1], reverse=True))
        
        return {
            "total": total,
            "match_rate": round(match_rate, 4),
            "mismatch_rate": round(mismatch_rate, 4),
            "by_severity": severity_counts,
            "top_fields": top_fields
        }


# Global singleton instance (опционально)
_diff_repo: Optional[ExecutionShadowDiffRepository] = None


def get_execution_shadow_diff_repo() -> Optional[ExecutionShadowDiffRepository]:
    """Get singleton ExecutionShadowDiffRepository instance."""
    global _diff_repo
    return _diff_repo


def set_execution_shadow_diff_repo(repo: ExecutionShadowDiffRepository):
    """Set singleton ExecutionShadowDiffRepository instance."""
    global _diff_repo
    _diff_repo = repo
    logger.info("✅ ExecutionShadowDiffRepository singleton set")
