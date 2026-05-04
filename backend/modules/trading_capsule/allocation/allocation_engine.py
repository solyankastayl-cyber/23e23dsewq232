"""
Allocation Engine (S3.3)
========================

Main engine for capital allocation.

Pipeline:
1. Select eligible strategies (S3.1)
2. Calculate weights (S3.2)
3. Build allocation plan
4. Save snapshot

Also handles:
- Rebalance preview
- Plan activation
- Historical snapshots
"""

from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
import threading
import os

from .allocation_types import (
    CapitalAllocationPlan,
    StrategyAllocation,
    AllocationSnapshot,
    AllocationPolicy,
    AllocationStatus,
    RebalancePreview
)

from .strategy_selector import strategy_selector
from .weight_allocator import weight_allocator


# Default policies
DEFAULT_POLICIES = {
    "default": AllocationPolicy(),
    "conservative": AllocationPolicy(
        policy_id="conservative",
        name="Conservative Policy",
        require_robust=True,
        max_weight_per_strategy=0.25,
        max_drawdown_threshold=0.20
    ),
    "aggressive": AllocationPolicy(
        policy_id="aggressive",
        name="Aggressive Policy",
        allow_weak=True,
        max_strategies=8,
        max_weight_per_strategy=0.40,
        max_drawdown_threshold=0.50
    )
}


class AllocationEngine:
    """
    Main engine for capital allocation.
    
    Thread-safe singleton.
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        # In-memory storage
        self._plans: Dict[str, CapitalAllocationPlan] = {}
        self._snapshots: Dict[str, AllocationSnapshot] = {}
        self._policies: Dict[str, AllocationPolicy] = DEFAULT_POLICIES.copy()
        
        # Plan -> latest snapshot mapping
        self._plan_latest_snapshot: Dict[str, str] = {}
        
        # MongoDB (lazy init)
        self._db = None
        self._plans_col = None
        self._snapshots_col = None
        
        self._initialized = True
        print("[AllocationEngine] Initialized")
    
    def _get_collections(self):
        """Get MongoDB collections"""
        if self._plans_col is None:
            try:
                from pymongo import MongoClient
                
                mongo_url = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
                db_name = os.environ.get("DB_NAME", "trading_capsule")
                
                client = MongoClient(mongo_url)
                self._db = client[db_name]
                self._plans_col = self._db["allocation_plans"]
                self._snapshots_col = self._db["allocation_snapshots"]
                
                self._plans_col.create_index("plan_id", unique=True)
                self._snapshots_col.create_index("snapshot_id", unique=True)
                self._snapshots_col.create_index("plan_id")
                
                print("[AllocationEngine] MongoDB connected")
            except Exception as e:
                print(f"[AllocationEngine] MongoDB connection failed: {e}")
        
        return self._plans_col, self._snapshots_col
    
    # ===========================================
    # Create Allocation Plan
    # ===========================================
    
    def create_allocation_plan(
        self,
        experiment_id: str,
        total_capital_usd: float,
        policy_id: str = "default",
        walkforward_experiment_id: Optional[str] = None,
        notes: str = ""
    ) -> CapitalAllocationPlan:
        """
        Create a new capital allocation plan.
        
        Args:
            experiment_id: Research experiment ID
            total_capital_usd: Total capital to allocate
            policy_id: Policy to use (default, conservative, aggressive)
            walkforward_experiment_id: Optional Walk Forward experiment
            notes: Optional notes
            
        Returns:
            CapitalAllocationPlan
        """
        # Get policy
        policy = self._policies.get(policy_id, DEFAULT_POLICIES["default"])
        
        # Step 1: Select eligible strategies
        all_strategies = strategy_selector.select_strategies(
            experiment_id,
            walkforward_experiment_id,
            policy
        )
        
        eligible = [s for s in all_strategies if s.is_eligible]
        
        # Step 2: Calculate weights
        allocations = weight_allocator.calculate_weights(
            eligible,
            total_capital_usd,
            policy
        )
        
        # Step 3: Build plan
        allocated_capital = sum(a.target_capital_usd for a in allocations if a.enabled)
        
        plan = CapitalAllocationPlan(
            experiment_id=experiment_id,
            walkforward_experiment_id=walkforward_experiment_id or "",
            total_capital_usd=total_capital_usd,
            allocated_capital_usd=allocated_capital,
            cash_reserve_usd=total_capital_usd - allocated_capital,
            policy_id=policy_id,
            strategies=allocations,
            total_strategies_evaluated=len(all_strategies),
            strategies_selected=len(eligible),
            strategies_rejected=len(all_strategies) - len(eligible),
            status=AllocationStatus.DRAFT,
            notes=notes
        )
        
        # Store
        self._plans[plan.plan_id] = plan
        self._save_plan(plan)
        
        # Create initial snapshot
        snapshot = self._create_snapshot(plan, "CREATION")
        
        print(f"[AllocationEngine] Created plan: {plan.plan_id} " +
              f"({len(allocations)} strategies, ${allocated_capital:.2f} allocated)")
        
        return plan
    
    # ===========================================
    # Get / List Plans
    # ===========================================
    
    def get_plan(self, plan_id: str) -> Optional[CapitalAllocationPlan]:
        """Get allocation plan by ID"""
        return self._plans.get(plan_id)
    
    def list_plans(
        self,
        status: Optional[AllocationStatus] = None,
        limit: int = 50
    ) -> List[CapitalAllocationPlan]:
        """List allocation plans"""
        plans = list(self._plans.values())
        
        if status:
            plans = [p for p in plans if p.status == status]
        
        plans.sort(key=lambda p: p.created_at, reverse=True)
        return plans[:limit]
    
    # ===========================================
    # Activate / Pause
    # ===========================================
    
    def activate_plan(self, plan_id: str) -> Optional[CapitalAllocationPlan]:
        """Activate an allocation plan"""
        plan = self.get_plan(plan_id)
        if not plan:
            return None
        
        plan.status = AllocationStatus.ACTIVE
        plan.activated_at = datetime.now(timezone.utc)
        self._save_plan(plan)
        
        print(f"[AllocationEngine] Activated plan: {plan_id}")
        return plan
    
    def pause_plan(self, plan_id: str) -> Optional[CapitalAllocationPlan]:
        """Pause an allocation plan"""
        plan = self.get_plan(plan_id)
        if not plan:
            return None
        
        plan.status = AllocationStatus.PAUSED
        self._save_plan(plan)
        
        print(f"[AllocationEngine] Paused plan: {plan_id}")
        return plan
    
    def close_plan(self, plan_id: str) -> Optional[CapitalAllocationPlan]:
        """Close an allocation plan"""
        plan = self.get_plan(plan_id)
        if not plan:
            return None
        
        plan.status = AllocationStatus.CLOSED
        self._save_plan(plan)
        
        print(f"[AllocationEngine] Closed plan: {plan_id}")
        return plan
    
    # ===========================================
    # Rebalance
    # ===========================================
    
    def preview_rebalance(
        self,
        plan_id: str
    ) -> RebalancePreview:
        """
        Preview rebalance changes without applying them.
        """
        plan = self.get_plan(plan_id)
        if not plan:
            return RebalancePreview(plan_id=plan_id, reason="Plan not found")
        
        # Get policy
        policy = self._policies.get(plan.policy_id, DEFAULT_POLICIES["default"])
        
        # Calculate new allocations
        all_strategies = strategy_selector.select_strategies(
            plan.experiment_id,
            plan.walkforward_experiment_id or None,
            policy
        )
        eligible = [s for s in all_strategies if s.is_eligible]
        new_allocations = weight_allocator.calculate_weights(
            eligible,
            plan.total_capital_usd,
            policy
        )
        
        # Compare with current
        current_map = {s.strategy_id: s for s in plan.strategies}
        new_map = {s.strategy_id: s for s in new_allocations}
        
        changes = []
        strategies_added = 0
        strategies_removed = 0
        weights_adjusted = 0
        max_drift = 0.0
        
        # Check for new strategies
        for sid, new_alloc in new_map.items():
            if sid not in current_map:
                changes.append({
                    "strategy_id": sid,
                    "type": "ADDED",
                    "old_weight": 0,
                    "new_weight": new_alloc.target_weight
                })
                strategies_added += 1
            else:
                old_weight = current_map[sid].target_weight
                new_weight = new_alloc.target_weight
                drift = abs(new_weight - old_weight)
                
                if drift > 0.001:
                    changes.append({
                        "strategy_id": sid,
                        "type": "ADJUSTED",
                        "old_weight": old_weight,
                        "new_weight": new_weight,
                        "drift": drift
                    })
                    weights_adjusted += 1
                    max_drift = max(max_drift, drift)
        
        # Check for removed strategies
        for sid in current_map:
            if sid not in new_map:
                changes.append({
                    "strategy_id": sid,
                    "type": "REMOVED",
                    "old_weight": current_map[sid].target_weight,
                    "new_weight": 0
                })
                strategies_removed += 1
        
        # Determine if rebalance needed
        should_rebalance = (
            strategies_added > 0 or
            strategies_removed > 0 or
            max_drift > policy.rebalance_threshold
        )
        
        reason = ""
        if should_rebalance:
            reasons = []
            if strategies_added:
                reasons.append(f"{strategies_added} new strategies")
            if strategies_removed:
                reasons.append(f"{strategies_removed} removed strategies")
            if max_drift > policy.rebalance_threshold:
                reasons.append(f"Weight drift {max_drift*100:.1f}% > threshold {policy.rebalance_threshold*100:.0f}%")
            reason = "; ".join(reasons)
        else:
            reason = "No significant changes detected"
        
        return RebalancePreview(
            plan_id=plan_id,
            current_snapshot_id=self._plan_latest_snapshot.get(plan_id, ""),
            changes=changes,
            strategies_added=strategies_added,
            strategies_removed=strategies_removed,
            weights_adjusted=weights_adjusted,
            should_rebalance=should_rebalance,
            reason=reason
        )
    
    def execute_rebalance(
        self,
        plan_id: str
    ) -> Optional[CapitalAllocationPlan]:
        """
        Execute rebalance and create new snapshot.
        """
        plan = self.get_plan(plan_id)
        if not plan:
            return None
        
        # Get policy
        policy = self._policies.get(plan.policy_id, DEFAULT_POLICIES["default"])
        
        # Calculate new allocations
        all_strategies = strategy_selector.select_strategies(
            plan.experiment_id,
            plan.walkforward_experiment_id or None,
            policy
        )
        eligible = [s for s in all_strategies if s.is_eligible]
        new_allocations = weight_allocator.calculate_weights(
            eligible,
            plan.total_capital_usd,
            policy
        )
        
        # Update plan
        plan.strategies = new_allocations
        plan.allocated_capital_usd = sum(a.target_capital_usd for a in new_allocations if a.enabled)
        plan.cash_reserve_usd = plan.total_capital_usd - plan.allocated_capital_usd
        plan.strategies_selected = len(eligible)
        plan.total_strategies_evaluated = len(all_strategies)
        plan.strategies_rejected = len(all_strategies) - len(eligible)
        plan.last_rebalance_at = datetime.now(timezone.utc)
        plan.version += 1
        
        self._save_plan(plan)
        
        # Create snapshot
        self._create_snapshot(plan, "REBALANCE")
        
        print(f"[AllocationEngine] Rebalanced plan: {plan_id} (v{plan.version})")
        return plan
    
    # ===========================================
    # Snapshots
    # ===========================================
    
    def _create_snapshot(
        self,
        plan: CapitalAllocationPlan,
        reason: str
    ) -> AllocationSnapshot:
        """Create and store a snapshot"""
        snapshot = AllocationSnapshot(
            plan_id=plan.plan_id,
            total_capital_usd=plan.total_capital_usd,
            strategies=[StrategyAllocation(**s.__dict__) for s in plan.strategies],
            reason=reason
        )
        
        self._snapshots[snapshot.snapshot_id] = snapshot
        self._plan_latest_snapshot[plan.plan_id] = snapshot.snapshot_id
        self._save_snapshot(snapshot)
        
        return snapshot
    
    def get_latest_snapshot(
        self,
        plan_id: str
    ) -> Optional[AllocationSnapshot]:
        """Get latest snapshot for a plan"""
        snapshot_id = self._plan_latest_snapshot.get(plan_id)
        if snapshot_id:
            return self._snapshots.get(snapshot_id)
        return None
    
    def get_snapshot_history(
        self,
        plan_id: str,
        limit: int = 20
    ) -> List[AllocationSnapshot]:
        """Get snapshot history for a plan"""
        snapshots = [
            s for s in self._snapshots.values()
            if s.plan_id == plan_id
        ]
        snapshots.sort(key=lambda s: s.timestamp, reverse=True)
        return snapshots[:limit]
    
    # ===========================================
    # Policies
    # ===========================================
    
    def get_policy(self, policy_id: str) -> Optional[AllocationPolicy]:
        """Get policy by ID"""
        return self._policies.get(policy_id)
    
    def list_policies(self) -> List[AllocationPolicy]:
        """List all policies"""
        return list(self._policies.values())
    
    def add_custom_policy(
        self,
        policy: AllocationPolicy
    ) -> AllocationPolicy:
        """Add a custom policy"""
        self._policies[policy.policy_id] = policy
        return policy
    
    # ===========================================
    # Persistence
    # ===========================================
    
    def _save_plan(self, plan: CapitalAllocationPlan):
        plans_col, _ = self._get_collections()
        if plans_col is not None:
            try:
                plans_col.replace_one(
                    {"plan_id": plan.plan_id},
                    plan.to_dict(),
                    upsert=True
                )
            except Exception as e:
                print(f"[AllocationEngine] Save plan failed: {e}")
    
    def _save_snapshot(self, snapshot: AllocationSnapshot):
        _, snapshots_col = self._get_collections()
        if snapshots_col is not None:
            try:
                snapshots_col.replace_one(
                    {"snapshot_id": snapshot.snapshot_id},
                    snapshot.to_dict(),
                    upsert=True
                )
            except Exception as e:
                print(f"[AllocationEngine] Save snapshot failed: {e}")
    
    # ===========================================
    # Cleanup
    # ===========================================
    
    def delete_plan(self, plan_id: str) -> bool:
        """Delete plan and its snapshots"""
        self._plans.pop(plan_id, None)
        self._plan_latest_snapshot.pop(plan_id, None)
        
        # Remove snapshots
        self._snapshots = {
            k: v for k, v in self._snapshots.items()
            if v.plan_id != plan_id
        }
        
        # Remove from MongoDB
        plans_col, snapshots_col = self._get_collections()
        if plans_col is not None:
            try:
                plans_col.delete_one({"plan_id": plan_id})
                if snapshots_col is not None:
                    snapshots_col.delete_many({"plan_id": plan_id})
            except Exception:
                pass
        
        return True


# Global singleton
allocation_engine = AllocationEngine()
