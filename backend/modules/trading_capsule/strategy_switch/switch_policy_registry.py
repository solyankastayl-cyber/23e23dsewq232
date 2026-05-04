"""
Switch Policy Registry (STR3)
=============================

Standard policies for strategy switching.

Default policies:
- LOSS_LIMIT_PROTECTION: Switch to conservative on daily loss > 5%
- DRAWDOWN_GUARD: Switch to conservative on drawdown > 10%
- WEEKEND_SAFE_MODE: Conservative on weekends
- HIGH_VOLATILITY_MODE: Conservative on high volatility
"""

from typing import Dict, List, Optional
from .switch_types import (
    SwitchPolicy,
    SwitchTriggerType,
    SwitchPriority,
    PolicyStatus,
    PolicyCondition,
    ConditionOperator,
    ScheduleConfig
)


# ===========================================
# Policy Registry Storage
# ===========================================

POLICY_REGISTRY: Dict[str, SwitchPolicy] = {}


# ===========================================
# Default Policies
# ===========================================

def _create_default_policies() -> None:
    """Create default system policies"""
    
    # ========================================
    # 1. LOSS_LIMIT_PROTECTION
    # ========================================
    POLICY_REGISTRY["LOSS_LIMIT_PROTECTION"] = SwitchPolicy(
        policy_id="policy_loss_limit",
        name="Loss Limit Protection",
        description="Switch to CONSERVATIVE when daily loss exceeds 5%",
        trigger_type=SwitchTriggerType.RULE,
        target_profile="CONSERVATIVE",
        conditions=[
            PolicyCondition(
                condition_id="cond_daily_loss",
                field="daily_loss_pct",
                operator=ConditionOperator.GREATER_EQUAL,
                value=0.05,
                description="Daily loss >= 5%"
            )
        ],
        condition_logic="AND",
        priority=SwitchPriority.HIGH,
        status=PolicyStatus.ENABLED,
        auto_revert=True,
        revert_profile="BALANCED",
        revert_delay_minutes=60,
        cooldown_minutes=30,
        created_by="system",
        tags=["risk", "protection", "daily_loss"]
    )
    
    # ========================================
    # 2. DRAWDOWN_GUARD
    # ========================================
    POLICY_REGISTRY["DRAWDOWN_GUARD"] = SwitchPolicy(
        policy_id="policy_drawdown_guard",
        name="Drawdown Guard",
        description="Switch to CONSERVATIVE when portfolio drawdown exceeds 10%",
        trigger_type=SwitchTriggerType.RULE,
        target_profile="CONSERVATIVE",
        conditions=[
            PolicyCondition(
                condition_id="cond_drawdown",
                field="portfolio_drawdown_pct",
                operator=ConditionOperator.GREATER_EQUAL,
                value=0.10,
                description="Portfolio drawdown >= 10%"
            )
        ],
        condition_logic="AND",
        priority=SwitchPriority.HIGH,
        status=PolicyStatus.ENABLED,
        auto_revert=False,  # Requires manual revert
        cooldown_minutes=60,
        created_by="system",
        tags=["risk", "protection", "drawdown"]
    )
    
    # ========================================
    # 3. WEEKEND_SAFE_MODE
    # ========================================
    POLICY_REGISTRY["WEEKEND_SAFE_MODE"] = SwitchPolicy(
        policy_id="policy_weekend_safe",
        name="Weekend Safe Mode",
        description="Switch to CONSERVATIVE on weekends",
        trigger_type=SwitchTriggerType.SCHEDULE,
        target_profile="CONSERVATIVE",
        schedule=ScheduleConfig(
            days=["SATURDAY", "SUNDAY"],
            start_time="00:00",
            end_time="23:59",
            timezone="UTC"
        ),
        priority=SwitchPriority.MEDIUM,
        status=PolicyStatus.ENABLED,
        auto_revert=True,
        revert_profile="BALANCED",
        revert_delay_minutes=0,  # Immediate revert when schedule ends
        cooldown_minutes=5,
        created_by="system",
        tags=["schedule", "weekend", "safety"]
    )
    
    # ========================================
    # 4. HIGH_VOLATILITY_MODE
    # ========================================
    POLICY_REGISTRY["HIGH_VOLATILITY_MODE"] = SwitchPolicy(
        policy_id="policy_high_volatility",
        name="High Volatility Mode",
        description="Switch to BALANCED when market volatility is high",
        trigger_type=SwitchTriggerType.RULE,
        target_profile="BALANCED",
        conditions=[
            PolicyCondition(
                condition_id="cond_volatility",
                field="volatility_score",
                operator=ConditionOperator.GREATER_EQUAL,
                value=0.7,
                description="Volatility score >= 0.7"
            )
        ],
        condition_logic="AND",
        priority=SwitchPriority.MEDIUM,
        status=PolicyStatus.ENABLED,
        auto_revert=True,
        revert_profile="AGGRESSIVE",
        revert_delay_minutes=120,
        cooldown_minutes=30,
        created_by="system",
        tags=["volatility", "market_condition"]
    )
    
    # ========================================
    # 5. CONSECUTIVE_LOSSES_GUARD
    # ========================================
    POLICY_REGISTRY["CONSECUTIVE_LOSSES_GUARD"] = SwitchPolicy(
        policy_id="policy_consecutive_losses",
        name="Consecutive Losses Guard",
        description="Switch to CONSERVATIVE after 3 consecutive losses",
        trigger_type=SwitchTriggerType.RULE,
        target_profile="CONSERVATIVE",
        conditions=[
            PolicyCondition(
                condition_id="cond_consecutive_losses",
                field="consecutive_losses",
                operator=ConditionOperator.GREATER_EQUAL,
                value=3,
                description="Consecutive losses >= 3"
            )
        ],
        condition_logic="AND",
        priority=SwitchPriority.HIGH,
        status=PolicyStatus.ENABLED,
        auto_revert=True,
        revert_profile="BALANCED",
        revert_delay_minutes=30,
        cooldown_minutes=15,
        created_by="system",
        tags=["risk", "protection", "losses"]
    )
    
    # ========================================
    # 6. NIGHT_MODE
    # ========================================
    POLICY_REGISTRY["NIGHT_MODE"] = SwitchPolicy(
        policy_id="policy_night_mode",
        name="Night Mode",
        description="Switch to CONSERVATIVE during night hours (00:00-06:00 UTC)",
        trigger_type=SwitchTriggerType.SCHEDULE,
        target_profile="CONSERVATIVE",
        schedule=ScheduleConfig(
            days=["MONDAY", "TUESDAY", "WEDNESDAY", "THURSDAY", "FRIDAY", "SATURDAY", "SUNDAY"],
            start_time="00:00",
            end_time="06:00",
            timezone="UTC"
        ),
        priority=SwitchPriority.LOW,
        status=PolicyStatus.DISABLED,  # Disabled by default
        auto_revert=True,
        revert_profile="BALANCED",
        revert_delay_minutes=0,
        cooldown_minutes=5,
        created_by="system",
        tags=["schedule", "night", "safety"]
    )
    
    # ========================================
    # 7. MANUAL_OVERRIDE
    # ========================================
    POLICY_REGISTRY["MANUAL_OVERRIDE"] = SwitchPolicy(
        policy_id="policy_manual_override",
        name="Manual Override",
        description="Manual switch policy for admin control",
        trigger_type=SwitchTriggerType.MANUAL,
        target_profile="",  # Target set at runtime
        priority=SwitchPriority.CRITICAL,
        status=PolicyStatus.ENABLED,
        auto_revert=False,
        cooldown_minutes=0,  # No cooldown for manual
        created_by="system",
        tags=["manual", "admin"]
    )


# Initialize default policies
_create_default_policies()


# ===========================================
# Registry Functions
# ===========================================

def get_policy(policy_id: str) -> Optional[SwitchPolicy]:
    """Get policy by ID or name"""
    # Check by ID
    for policy in POLICY_REGISTRY.values():
        if policy.policy_id == policy_id:
            return policy
    
    # Check by name (case-insensitive)
    return POLICY_REGISTRY.get(policy_id.upper())


def get_all_policies() -> List[SwitchPolicy]:
    """Get all policies"""
    return list(POLICY_REGISTRY.values())


def get_enabled_policies() -> List[SwitchPolicy]:
    """Get all enabled policies"""
    return [p for p in POLICY_REGISTRY.values() if p.status == PolicyStatus.ENABLED]


def get_policies_by_type(trigger_type: SwitchTriggerType) -> List[SwitchPolicy]:
    """Get policies by trigger type"""
    return [p for p in POLICY_REGISTRY.values() if p.trigger_type == trigger_type]


def get_policies_by_tag(tag: str) -> List[SwitchPolicy]:
    """Get policies by tag"""
    return [p for p in POLICY_REGISTRY.values() if tag in p.tags]


def register_policy(policy: SwitchPolicy) -> bool:
    """Register a custom policy"""
    if policy.name.upper() in POLICY_REGISTRY:
        return False
    
    POLICY_REGISTRY[policy.name.upper()] = policy
    return True


def enable_policy(policy_id: str) -> bool:
    """Enable a policy"""
    policy = get_policy(policy_id)
    if policy:
        policy.status = PolicyStatus.ENABLED
        return True
    return False


def disable_policy(policy_id: str) -> bool:
    """Disable a policy"""
    policy = get_policy(policy_id)
    if policy:
        policy.status = PolicyStatus.DISABLED
        return True
    return False


def get_policy_summary() -> Dict[str, any]:
    """Get summary of all policies"""
    policies = get_all_policies()
    
    return {
        "total": len(policies),
        "enabled": len([p for p in policies if p.status == PolicyStatus.ENABLED]),
        "disabled": len([p for p in policies if p.status == PolicyStatus.DISABLED]),
        "by_type": {
            "MANUAL": len([p for p in policies if p.trigger_type == SwitchTriggerType.MANUAL]),
            "SCHEDULE": len([p for p in policies if p.trigger_type == SwitchTriggerType.SCHEDULE]),
            "RULE": len([p for p in policies if p.trigger_type == SwitchTriggerType.RULE]),
            "AUTO": len([p for p in policies if p.trigger_type == SwitchTriggerType.AUTO])
        },
        "by_priority": {
            "CRITICAL": len([p for p in policies if p.priority == SwitchPriority.CRITICAL]),
            "HIGH": len([p for p in policies if p.priority == SwitchPriority.HIGH]),
            "MEDIUM": len([p for p in policies if p.priority == SwitchPriority.MEDIUM]),
            "LOW": len([p for p in policies if p.priority == SwitchPriority.LOW])
        }
    }
