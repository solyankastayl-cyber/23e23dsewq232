"""
Sprint 7.2-7.4: Adaptation Service
===================================

Generates recommendations and applies changes (with operator approval).

CRITICAL: Service CANNOT auto-apply. Only generates recommendations.
"""

from typing import Dict, List, Optional
from motor.motor_asyncio import AsyncIOMotorDatabase
from modules.adaptation.repository import AdaptationRepository
from modules.adaptation.config import (
    ADAPTATION_DEFAULTS,
    CONFIDENCE_EXPECTED_FLOORS,
    CHANGE_TYPE_CONFIDENCE_BUCKET,
    STATUS_PROPOSED,
    STATUS_APPLIED,
    STATUS_REJECTED
)
from modules.learning.service import get_learning_service
from datetime import datetime, timezone


class AdaptationService:
    """
    Controlled Adaptation Service
    
    Responsibilities:
    1. Generate recommendations based on learning insights
    2. Apply operator-approved changes to config
    3. Provide active config for R1/R2 consumption
    
    DOES NOT:
    - Auto-apply changes
    - Modify config without operator approval
    """
    
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.repo = AdaptationRepository(db)
    
    async def generate_recommendations(self) -> Dict:
        """
        Generate adaptation recommendations based on learning data.
        
        Phase 7.2-7.3: Confidence bucket adjustments only (minimal scope)
        
        Returns:
            {
                "recommendations": [
                    {
                        "change_id": "...",
                        "type": "CONFIDENCE_BUCKET_ADJUSTMENT",
                        "bucket": "0.7-0.8",
                        "current_weight": 1.0,
                        "suggested_weight": 0.9,
                        "reason": "...",
                        "sample_size": 25
                    }
                ],
                "total": 1
            }
        """
        try:
            # Get learning insights
            learning_service = get_learning_service()
            insights = await learning_service.analyze_patterns()
            
            if insights.get("total_decisions", 0) < ADAPTATION_DEFAULTS["min_sample_size"]:
                return {
                    "recommendations": [],
                    "total": 0,
                    "reason": f"Insufficient data (need {ADAPTATION_DEFAULTS['min_sample_size']} decisions)"
                }
            
            # Get current active config
            active_config = await self.get_active_config()
            current_weights = active_config.get("confidence_bucket_adjustments", {})
            
            # Analyze confidence calibration
            calibration = insights.get("confidence_calibration", {})
            recommendations = []
            
            for bucket, actual_win_rate in calibration.items():
                # Get expected floor
                expected_floor = CONFIDENCE_EXPECTED_FLOORS.get(bucket, 0.40)
                current_weight = current_weights.get(bucket, 1.0)
                
                # Check for overestimation
                if actual_win_rate < (expected_floor * 100) - 10:  # More than 10% below expected
                    # Suggest reducing weight
                    suggested_weight = max(
                        ADAPTATION_DEFAULTS["min_confidence_weight"],
                        current_weight - 0.1
                    )
                    
                    # Only create if different from current
                    if abs(suggested_weight - current_weight) >= 0.05:
                        # Check if recommendation already exists
                        existing = await self._find_existing_recommendation(bucket)
                        if not existing:
                            change = await self.repo.create_change(
                                CHANGE_TYPE_CONFIDENCE_BUCKET,
                                {
                                    "bucket": bucket,
                                    "current_weight": current_weight,
                                    "suggested_weight": round(suggested_weight, 2),
                                    "reason": f"Overestimated confidence: actual {actual_win_rate}% vs expected ≥{expected_floor*100:.0f}%",
                                    "actual_win_rate": actual_win_rate,
                                    "expected_floor": expected_floor * 100,
                                    "sample_size": insights.get("total_decisions", 0)
                                }
                            )
                            recommendations.append(self._format_recommendation(change))
                
                # Check for underestimation (low confidence performing well)
                elif bucket in ["0.0-0.5", "0.5-0.6"]:  # Only for low confidence buckets
                    expected_ceiling = expected_floor + 0.15  # Small window
                    if actual_win_rate > (expected_ceiling * 100) + 10:  # More than 10% above
                        # Suggest slight increase
                        suggested_weight = min(
                            ADAPTATION_DEFAULTS["max_confidence_weight"],
                            current_weight + 0.05
                        )
                        
                        if abs(suggested_weight - current_weight) >= 0.05:
                            existing = await self._find_existing_recommendation(bucket)
                            if not existing:
                                change = await self.repo.create_change(
                                    CHANGE_TYPE_CONFIDENCE_BUCKET,
                                    {
                                        "bucket": bucket,
                                        "current_weight": current_weight,
                                        "suggested_weight": round(suggested_weight, 2),
                                        "reason": f"Underestimated confidence: actual {actual_win_rate}% (surprisingly strong)",
                                        "actual_win_rate": actual_win_rate,
                                        "sample_size": insights.get("total_decisions", 0)
                                    }
                                )
                                recommendations.append(self._format_recommendation(change))
            
            return {
                "ok": True,
                "recommendations": recommendations,
                "total": len(recommendations),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        
        except Exception as e:
            print(f"[AdaptationService] Failed to generate recommendations: {e}")
            return {
                "ok": False,
                "error": str(e),
                "recommendations": [],
                "total": 0
            }
    
    async def _find_existing_recommendation(self, bucket: str) -> Optional[Dict]:
        """Check if recommendation for bucket already exists (PROPOSED status)"""
        pending = await self.repo.get_pending_changes()
        for change in pending:
            if change.get("payload", {}).get("bucket") == bucket:
                return change
        return None
    
    def _format_recommendation(self, change: Dict) -> Dict:
        """Format change document into recommendation"""
        payload = change.get("payload", {})
        return {
            "change_id": change["change_id"],
            "type": change["type"],
            "status": change["status"],
            "bucket": payload.get("bucket"),
            "current_weight": payload.get("current_weight"),
            "suggested_weight": payload.get("suggested_weight"),
            "reason": payload.get("reason"),
            "actual_win_rate": payload.get("actual_win_rate"),
            "sample_size": payload.get("sample_size"),
            "created_at": change["created_at"].isoformat() if change.get("created_at") else None
        }
    
    async def apply_change(self, change_id: str, applied_by: str) -> Dict:
        """
        Apply operator-approved change.
        
        Phase 7.4: Versioned config application
        
        Args:
            change_id: Change ID to apply
            applied_by: Operator username
        
        Returns:
            Result with new config version
        """
        # Get change
        change = await self.repo.get_change_by_id(change_id)
        if not change:
            return {"ok": False, "error": "Change not found"}
        
        if change["status"] != STATUS_PROPOSED:
            return {"ok": False, "error": f"Change already {change['status']}"}
        
        # Get current active config
        current_config_doc = await self.repo.get_active_config()
        current_config = current_config_doc["config"] if current_config_doc else await self.repo.get_default_config()
        
        # Apply change to config
        new_config = dict(current_config)  # Copy
        
        if change["type"] == CHANGE_TYPE_CONFIDENCE_BUCKET:
            payload = change["payload"]
            bucket = payload["bucket"]
            new_weight = payload["suggested_weight"]
            
            if "confidence_bucket_adjustments" not in new_config:
                new_config["confidence_bucket_adjustments"] = {}
            
            new_config["confidence_bucket_adjustments"][bucket] = new_weight
        
        # Create new config version
        new_config_doc = await self.repo.create_config_version(new_config, applied_by)
        
        # Mark change as applied
        await self.repo.mark_change_applied(change_id, applied_by)
        
        return {
            "ok": True,
            "change_id": change_id,
            "config_version": new_config_doc["version"],
            "applied_by": applied_by,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    
    async def reject_change(self, change_id: str, rejected_by: str) -> Dict:
        """
        Reject change proposal.
        
        Args:
            change_id: Change ID to reject
            rejected_by: Operator username
        
        Returns:
            Result
        """
        change = await self.repo.get_change_by_id(change_id)
        if not change:
            return {"ok": False, "error": "Change not found"}
        
        if change["status"] != STATUS_PROPOSED:
            return {"ok": False, "error": f"Change already {change['status']}"}
        
        success = await self.repo.mark_change_rejected(change_id, rejected_by)
        
        return {
            "ok": success,
            "change_id": change_id,
            "rejected_by": rejected_by,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    
    async def get_active_config(self) -> Dict:
        """
        Get active configuration for R1/R2 consumption.
        
        Returns:
            Config dict with adjustments
        """
        config_doc = await self.repo.get_active_config()
        if config_doc:
            return config_doc["config"]
        else:
            return await self.repo.get_default_config()
    
    async def get_history(self, limit: int = 50) -> Dict:
        """Get change history"""
        changes = await self.repo.get_change_history(limit)
        
        return {
            "ok": True,
            "changes": [self._format_recommendation(c) for c in changes],
            "total": len(changes)
        }


# Global service instance
_service: Optional[AdaptationService] = None


def init_adaptation_service(db: AsyncIOMotorDatabase) -> AdaptationService:
    """Initialize adaptation service"""
    global _service
    _service = AdaptationService(db)
    return _service


def get_adaptation_service() -> AdaptationService:
    """Get adaptation service instance"""
    if _service is None:
        raise RuntimeError("AdaptationService not initialized")
    return _service
