"""
Analytics Service
Phase 4: Operational Analytics Layer

Read-only analytics over existing truth layers.
NO business logic. NO decisions. ONLY aggregations.
"""

from typing import Dict, List, Any


class AnalyticsService:
    """
    Operational analytics service.
    
    Provides read-only aggregations over execution events, strategy decisions,
    and safety blocks for operator visibility.
    
    Sources:
    - execution_events (DYNAMIC_RISK_*, EXECUTION_*, ORDER_*, AUTO_BLOCKED)
    - strategy_decisions_recent (via StrategyVisibilityService)
    - auto_safety state
    
    Sprint: Analytics Layer P0
    """
    
    def __init__(self, execution_repo):
        """
        Initialize analytics service.
        
        Args:
            execution_repo: ExecutionEventRepository for event queries
        """
        self.execution_repo = execution_repo
    
    async def get_dynamic_risk_summary(self) -> Dict[str, Any]:
        """
        Dynamic Risk Analytics Summary.
        
        Aggregates R1 decisions to answer:
        - R1 пропускает или блокирует?
        - Как часто режет размер (clamp)?
        - Средний multiplier и notional?
        
        Returns:
            {
                "approved_count": int,
                "blocked_count": int,
                "approval_rate_pct": float,
                "avg_multiplier": float,
                "avg_notional_usd": float,
                "clamped_count": int,
                "clamp_rate_pct": float
            }
        """
        # Get all dynamic risk events
        approved_events = await self.execution_repo.find_by_type("DYNAMIC_RISK_APPROVED")
        blocked_events = await self.execution_repo.find_by_type("DYNAMIC_RISK_BLOCKED")
        
        approved_count = len(approved_events)
        blocked_count = len(blocked_events)
        total = approved_count + blocked_count
        
        approval_rate_pct = (approved_count / total * 100) if total > 0 else 0.0
        
        # Calculate averages from approved events
        multipliers = []
        notionals = []
        clamped_count = 0
        
        for event in approved_events:
            debug = event.get("debug", {})
            
            # Multiplier
            mult = debug.get("size_multiplier")
            if mult is not None:
                multipliers.append(mult)
            
            # Notional
            notional = debug.get("clamped_notional") or debug.get("raw_notional")
            if notional is not None:
                notionals.append(notional)
            
            # Clamp detection
            raw = debug.get("raw_notional")
            clamped = debug.get("clamped_notional")
            if raw is not None and clamped is not None and raw != clamped:
                clamped_count += 1
        
        avg_multiplier = sum(multipliers) / len(multipliers) if multipliers else 0.0
        avg_notional_usd = sum(notionals) / len(notionals) if notionals else 0.0
        clamp_rate_pct = (clamped_count / approved_count * 100) if approved_count > 0 else 0.0
        
        return {
            "approved_count": approved_count,
            "blocked_count": blocked_count,
            "approval_rate_pct": round(approval_rate_pct, 2),
            "avg_multiplier": round(avg_multiplier, 2),
            "avg_notional_usd": round(avg_notional_usd, 2),
            "clamped_count": clamped_count,
            "clamp_rate_pct": round(clamp_rate_pct, 2)
        }
    
    async def get_dynamic_risk_reasons(self) -> List[Dict[str, Any]]:
        """
        Top Dynamic Risk block reasons.
        
        Aggregates R1 rejection reasons to answer:
        - Почему R1 чаще всего блокирует?
        
        Returns:
            [
                {"reason": "MAX_PORTFOLIO_EXPOSURE", "count": 5},
                {"reason": "NO_CONFIDENCE", "count": 4},
                ...
            ]
        """
        blocked_events = await self.execution_repo.find_by_type("DYNAMIC_RISK_BLOCKED")
        
        reason_counts = {}
        for event in blocked_events:
            reason = event.get("reason") or "UNKNOWN"
            reason_counts[reason] = reason_counts.get(reason, 0) + 1
        
        # Sort by count descending
        reasons = [
            {"reason": reason, "count": count}
            for reason, count in reason_counts.items()
        ]
        reasons.sort(key=lambda x: x["count"], reverse=True)
        
        return reasons
    
    async def get_execution_summary(self) -> Dict[str, Any]:
        """
        Execution Analytics Summary.
        
        Aggregates execution pipeline to answer:
        - Доходят ли решения до fill?
        - Где ломается execution?
        
        Returns:
            {
                "queued": int,
                "started": int,
                "submitted": int,
                "filled": int,
                "failed": int,
                "fill_rate_pct": float
            }
        """
        # Get execution events by type
        queued = await self.execution_repo.find_by_type("EXECUTION_QUEUED")
        started = await self.execution_repo.find_by_type("EXECUTION_STARTED")
        submitted = await self.execution_repo.find_by_type("ORDER_SUBMITTED")
        filled = await self.execution_repo.find_by_type("ORDER_FILLED")
        failed = await self.execution_repo.find_by_type("ORDER_FAILED")
        
        queued_count = len(queued)
        started_count = len(started)
        submitted_count = len(submitted)
        filled_count = len(filled)
        failed_count = len(failed)
        
        fill_rate_pct = (filled_count / submitted_count * 100) if submitted_count > 0 else 0.0
        
        return {
            "queued": queued_count,
            "started": started_count,
            "submitted": submitted_count,
            "filled": filled_count,
            "failed": failed_count,
            "fill_rate_pct": round(fill_rate_pct, 2)
        }
    
    async def get_safety_summary(self) -> Dict[str, Any]:
        """
        Safety Analytics Summary.
        
        Aggregates safety blocks to answer:
        - Кто блокирует чаще: R1 или AutoSafety?
        - Какое правило самое частое?
        
        Returns:
            {
                "total_blocks": int,
                "dynamic_risk_block_count": int,
                "auto_block_count": int,
                "top_rule": str
            }
        """
        # Get block events
        dynamic_risk_blocks = await self.execution_repo.find_by_type("DYNAMIC_RISK_BLOCKED")
        auto_blocks = await self.execution_repo.find_by_type("AUTO_BLOCKED")
        
        dynamic_risk_count = len(dynamic_risk_blocks)
        auto_count = len(auto_blocks)
        total = dynamic_risk_count + auto_count
        
        # Find top rule (combine both block types)
        rule_counts = {}
        
        for event in dynamic_risk_blocks:
            reason = event.get("reason") or "UNKNOWN"
            rule_counts[reason] = rule_counts.get(reason, 0) + 1
        
        for event in auto_blocks:
            reason = event.get("reason") or event.get("rule") or "UNKNOWN"
            rule_counts[reason] = rule_counts.get(reason, 0) + 1
        
        # Get top rule
        top_rule = "NONE"
        if rule_counts:
            top_rule = max(rule_counts.items(), key=lambda x: x[1])[0]
        
        return {
            "total_blocks": total,
            "dynamic_risk_block_count": dynamic_risk_count,
            "auto_block_count": auto_count,
            "top_rule": top_rule
        }
    
    async def get_adaptive_risk_summary(self) -> Dict[str, Any]:
        """
        Adaptive Risk (R2) Analytics Summary.
        
        Aggregates R2 decisions to answer:
        - R2 работает вообще? (activation rate)
        - Насколько агрессивно режет? (avg multiplier)
        - Из-за чего включается? (drawdown vs loss streak)
        
        Returns:
            {
                "activation_rate_pct": float,
                "avg_r2_multiplier": float,
                "avg_drawdown_component": float,
                "avg_loss_streak_component": float,
            }
        """
        # Fetch recent R2 events
        all_events = await self.execution_repo.find_recent(limit=1000)
        r2_events = [
            e for e in all_events
            if e.get("event_type") == "ADAPTIVE_RISK_APPLIED"
        ]
        
        if not r2_events:
            return {
                "activation_rate_pct": 0,
                "avg_r2_multiplier": None,
                "avg_drawdown_component": None,
                "avg_loss_streak_component": None,
            }
        
        total = len(r2_events)
        
        # Active R2 (multiplier < 1)
        active = [e for e in r2_events if e.get("r2_multiplier", 1) < 1]
        activation_rate = (len(active) / total) * 100 if total else 0
        
        # Average multiplier
        avg_multiplier = sum(
            e.get("r2_multiplier", 1) for e in r2_events
        ) / total
        
        # Average components
        avg_drawdown = sum(
            e.get("r2_components", {}).get("drawdown", 1) for e in r2_events
        ) / total
        
        avg_loss = sum(
            e.get("r2_components", {}).get("loss_streak", 1) for e in r2_events
        ) / total
        
        return {
            "activation_rate_pct": round(activation_rate, 2),
            "avg_r2_multiplier": round(avg_multiplier, 3),
            "avg_drawdown_component": round(avg_drawdown, 3),
            "avg_loss_streak_component": round(avg_loss, 3),
        }


# Singleton instance
_analytics_service = None


def get_analytics_service():
    """Get singleton analytics service instance."""
    if _analytics_service is None:
        raise RuntimeError("AnalyticsService not initialized")
    return _analytics_service


def init_analytics_service(service):
    """Initialize singleton analytics service."""
    global _analytics_service
    _analytics_service = service
