"""
Sprint 6.2: Pattern Extraction Service
=======================================

Extracts patterns from decision + outcome data.
NO ML. NO magic. Only deterministic analysis.

Patterns:
1. Confidence vs Outcome (is high confidence actually better?)
2. R2 Impact (does R2 reduce losses?)
3. Operator Impact (does operator improve system?)
"""

from typing import Dict, List, Optional
from motor.motor_asyncio import AsyncIOMotorDatabase
from datetime import datetime, timezone


class LearningService:
    """
    Learning Layer - Pattern Extraction
    
    CRITICAL: READ ONLY
    - Does NOT modify decisions
    - Does NOT change pipeline
    - Only analyzes and reports
    """
    
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.decisions_col = db["pending_decisions"]
        self.traces_col = db["decision_traces"]
        self.outcomes_col = db["decision_outcomes"]
    
    async def analyze_patterns(self) -> Dict:
        """
        Analyze decision patterns without ML.
        
        Returns insights about:
        - Confidence calibration
        - R2 effectiveness
        - Operator impact
        """
        
        # Fetch all decisions with outcomes
        decisions_with_outcomes = await self._get_enriched_decisions()
        
        if len(decisions_with_outcomes) == 0:
            return self._empty_insights()
        
        # Extract patterns
        confidence_insight = self._analyze_confidence(decisions_with_outcomes)
        r2_insight = self._analyze_r2_impact(decisions_with_outcomes)
        operator_insight = self._analyze_operator_impact(decisions_with_outcomes)
        calibration = self._calibrate_confidence(decisions_with_outcomes)
        
        return {
            "ok": True,
            "total_decisions": len(decisions_with_outcomes),
            "confidence_insight": confidence_insight,
            "r2_insight": r2_insight,
            "operator_insight": operator_insight,
            "confidence_calibration": calibration,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    
    async def _get_enriched_decisions(self) -> List[Dict]:
        """
        Fetch decisions enriched with trace + outcome data.
        
        Returns list of:
        {
          "decision_id": "...",
          "confidence": 0.78,
          "r2_multiplier": 0.75,
          "operator_action": "APPROVED",
          "operator_note": "...",
          "outcome_status": "WIN",
          "pnl_pct": 2.3
        }
        """
        enriched = []
        
        # Get all outcomes
        outcomes = await self.outcomes_col.find({}).to_list(length=1000)
        
        for outcome in outcomes:
            decision_id = outcome.get("decision_id")
            if not decision_id:
                continue
            
            # Get decision trace
            trace = await self.traces_col.find_one({"decision_id": decision_id})
            
            # Extract R2 multiplier from trace steps
            r2_multiplier = 1.0
            if trace and "steps" in trace:
                for step in trace.get("steps", []):
                    if step.get("step") == "R2_ADAPTIVE":
                        r2_multiplier = step.get("data", {}).get("r2_multiplier", 1.0)
                        break
            
            # Get decision metadata
            decision = await self.decisions_col.find_one({"decision_id": decision_id})
            
            enriched.append({
                "decision_id": decision_id,
                "confidence": decision.get("confidence", 0.5) if decision else 0.5,
                "r2_multiplier": r2_multiplier,
                "operator_action": decision.get("operator_action", "AUTO") if decision else "AUTO",
                "operator_note": decision.get("operator_note", "") if decision else "",
                "outcome_status": outcome.get("status", "UNKNOWN"),
                "pnl_pct": outcome.get("pnl_pct", 0.0),
            })
        
        return enriched
    
    def _analyze_confidence(self, decisions: List[Dict]) -> str:
        """
        Phase 6.2.1: Confidence vs Outcome
        
        Answer: Do high confidence decisions actually win more?
        """
        if len(decisions) == 0:
            return "Insufficient data"
        
        high_conf = [d for d in decisions if d["confidence"] >= 0.7]
        low_conf = [d for d in decisions if d["confidence"] < 0.5]
        
        high_wins = len([d for d in high_conf if d["outcome_status"] == "WIN"])
        low_wins = len([d for d in low_conf if d["outcome_status"] == "WIN"])
        
        high_wr = (high_wins / len(high_conf) * 100) if len(high_conf) > 0 else 0
        low_wr = (low_wins / len(low_conf) * 100) if len(low_conf) > 0 else 0
        
        if high_wr > low_wr + 10:
            return f"High confidence (≥0.7) yields {high_wr:.0f}% win rate vs {low_wr:.0f}% for low confidence"
        elif low_wr > high_wr + 10:
            return f"⚠️ Low confidence performs better ({low_wr:.0f}% vs {high_wr:.0f}%) — system miscalibrated"
        else:
            return f"Confidence has minimal impact ({high_wr:.0f}% vs {low_wr:.0f}%)"
    
    def _analyze_r2_impact(self, decisions: List[Dict]) -> str:
        """
        Phase 6.2.2: R2 Impact
        
        Answer: Does R2 reduce losses?
        """
        if len(decisions) == 0:
            return "Insufficient data"
        
        r2_active = [d for d in decisions if d["r2_multiplier"] < 1.0]
        r2_inactive = [d for d in decisions if d["r2_multiplier"] >= 1.0]
        
        r2_losses = len([d for d in r2_active if d["outcome_status"] == "LOSS"])
        no_r2_losses = len([d for d in r2_inactive if d["outcome_status"] == "LOSS"])
        
        r2_loss_rate = (r2_losses / len(r2_active) * 100) if len(r2_active) > 0 else 0
        no_r2_loss_rate = (no_r2_losses / len(r2_inactive) * 100) if len(r2_inactive) > 0 else 0
        
        if no_r2_loss_rate > r2_loss_rate + 5:
            reduction = no_r2_loss_rate - r2_loss_rate
            return f"R2 reduces losses significantly (−{reduction:.0f}% loss rate)"
        elif r2_loss_rate > no_r2_loss_rate + 5:
            return f"⚠️ R2 active trades have higher loss rate (+{r2_loss_rate - no_r2_loss_rate:.0f}%)"
        else:
            return f"R2 impact unclear (similar loss rates: {r2_loss_rate:.0f}% vs {no_r2_loss_rate:.0f}%)"
    
    def _analyze_operator_impact(self, decisions: List[Dict]) -> str:
        """
        Phase 6.2.3: Operator Impact
        
        Answer: Does operator improve system performance?
        """
        if len(decisions) == 0:
            return "Insufficient data"
        
        operator_decisions = [d for d in decisions if d["operator_action"] in ["APPROVED", "REJECTED"]]
        auto_decisions = [d for d in decisions if d["operator_action"] == "AUTO"]
        
        # Only count APPROVED decisions for win rate (REJECTED avoided trade)
        operator_approved = [d for d in operator_decisions if d["operator_action"] == "APPROVED"]
        
        op_wins = len([d for d in operator_approved if d["outcome_status"] == "WIN"])
        auto_wins = len([d for d in auto_decisions if d["outcome_status"] == "WIN"])
        
        op_wr = (op_wins / len(operator_approved) * 100) if len(operator_approved) > 0 else 0
        auto_wr = (auto_wins / len(auto_decisions) * 100) if len(auto_decisions) > 0 else 0
        
        if op_wr > auto_wr + 10:
            improvement = op_wr - auto_wr
            return f"Operator improves system performance (+{improvement:.0f}% win rate)"
        elif auto_wr > op_wr + 10:
            return f"⚠️ Auto mode performs better than operator override (+{auto_wr - op_wr:.0f}%)"
        else:
            return f"Operator and auto mode have similar performance ({op_wr:.0f}% vs {auto_wr:.0f}%)"
    
    def _calibrate_confidence(self, decisions: List[Dict]) -> Dict:
        """
        Phase 6.5: Confidence Calibration
        
        Check: Does system's confidence match reality?
        
        Returns calibration map:
        {
          "0.7-0.8": 55,  # confidence 0.7-0.8 → actual 55% win rate
          "0.5-0.6": 60   # confidence 0.5-0.6 → actual 60% win rate
        }
        """
        buckets = {
            "0.8-1.0": [],
            "0.7-0.8": [],
            "0.6-0.7": [],
            "0.5-0.6": [],
            "0.0-0.5": []
        }
        
        for d in decisions:
            conf = d["confidence"]
            is_win = d["outcome_status"] == "WIN"
            
            if conf >= 0.8:
                buckets["0.8-1.0"].append(is_win)
            elif conf >= 0.7:
                buckets["0.7-0.8"].append(is_win)
            elif conf >= 0.6:
                buckets["0.6-0.7"].append(is_win)
            elif conf >= 0.5:
                buckets["0.5-0.6"].append(is_win)
            else:
                buckets["0.0-0.5"].append(is_win)
        
        calibration = {}
        for bucket, wins in buckets.items():
            if len(wins) > 0:
                win_rate = sum(wins) / len(wins) * 100
                calibration[bucket] = round(win_rate, 1)
        
        return calibration
    
    def _empty_insights(self) -> Dict:
        """Return empty insights when no data available"""
        return {
            "ok": True,
            "total_decisions": 0,
            "confidence_insight": "No decisions with outcomes yet",
            "r2_insight": "No R2 data available",
            "operator_insight": "No operator decisions yet",
            "confidence_calibration": {},
            "timestamp": datetime.now(timezone.utc).isoformat()
        }


# Global service instance
_service: Optional[LearningService] = None


def init_learning_service(db: AsyncIOMotorDatabase) -> LearningService:
    """Initialize learning service"""
    global _service
    _service = LearningService(db)
    return _service


def get_learning_service() -> LearningService:
    """Get learning service instance"""
    if _service is None:
        raise RuntimeError("LearningService not initialized")
    return _service
