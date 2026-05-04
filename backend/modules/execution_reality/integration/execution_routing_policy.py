"""
Execution Routing Policy (P1.3.3)
==================================

Routing Control Plane для canary deployment.

Routing Modes:
- LEGACY_ONLY: всё через legacy path
- SHADOW: dual-write (queue + legacy)
- CANARY: deterministic split (1-10% queue, остальное legacy)
- QUEUE_ONLY: только queue (для future 100% routing)
"""

import os
import hashlib
from typing import Literal, Optional
from pydantic import BaseModel, Field


# Routing Modes (строгий enum)
ExecutionRoutingMode = Literal["LEGACY_ONLY", "SHADOW", "CANARY", "QUEUE_ONLY"]


class ExecutionRoutingPolicy(BaseModel):
    """
    Execution Routing Policy Configuration.
    
    P1.3.3: Canary routing control.
    """
    # Routing Mode
    mode: ExecutionRoutingMode = Field(
        default="SHADOW",
        description="Routing mode: LEGACY_ONLY | SHADOW | CANARY | QUEUE_ONLY"
    )
    
    # Canary Percentage (только для CANARY mode)
    canary_percent: int = Field(
        default=1,
        ge=0,
        le=100,
        description="Canary percentage (0-100, deterministic routing)"
    )
    
    # Kill Switch (КРИТИЧНО)
    kill_switch_enabled: bool = Field(
        default=False,
        description="Emergency kill switch (true → force LEGACY_ONLY)"
    )
    
    # Health Gate
    require_queue_healthy: bool = Field(
        default=True,
        description="Require queue health check before routing"
    )
    
    # Safe Symbol Whitelist (для canary)
    safe_symbols: list[str] = Field(
        default=["BTCUSDT", "ETHUSDT"],
        description="Symbols allowed for canary routing"
    )
    
    # Safe Order Types (для canary)
    safe_order_types: list[str] = Field(
        default=["MARKET"],
        description="Order types allowed for canary routing"
    )
    
    class Config:
        use_enum_values = True


class RoutingDecision(BaseModel):
    """Routing decision output."""
    route_to_queue: bool
    execute_legacy: bool
    reason: str
    canary_selected: bool = False


def make_routing_decision(
    policy: ExecutionRoutingPolicy,
    trace_id: str,
    symbol: str,
    order_type: str = "MARKET",
    account_id: str = "default",
    queue_healthy: bool = True
) -> RoutingDecision:
    """
    Make routing decision based on policy.
    
    P1.3.3: Deterministic canary routing with safety guards.
    
    Args:
        policy: Routing policy configuration
        trace_id: Causal trace ID (for deterministic hashing)
        symbol: Trading symbol
        order_type: Order type (MARKET/LIMIT)
        account_id: Account identifier
        queue_healthy: Queue health status
    
    Returns:
        RoutingDecision
    """
    # CRITICAL: Kill Switch (emergency fallback)
    if policy.kill_switch_enabled:
        return RoutingDecision(
            route_to_queue=False,
            execute_legacy=True,
            reason="KILL_SWITCH_ENABLED (emergency fallback to legacy)"
        )
    
    # Health Gate: Queue unhealthy → fallback to legacy
    if policy.require_queue_healthy and not queue_healthy:
        return RoutingDecision(
            route_to_queue=False,
            execute_legacy=True,
            reason="QUEUE_UNHEALTHY (fallback to legacy)"
        )
    
    # Routing Matrix по mode
    mode = policy.mode
    
    if mode == "LEGACY_ONLY":
        return RoutingDecision(
            route_to_queue=False,
            execute_legacy=True,
            reason="MODE=LEGACY_ONLY"
        )
    
    elif mode == "SHADOW":
        return RoutingDecision(
            route_to_queue=True,
            execute_legacy=True,
            reason="MODE=SHADOW (dual-write)"
        )
    
    elif mode == "QUEUE_ONLY":
        return RoutingDecision(
            route_to_queue=True,
            execute_legacy=False,
            reason="MODE=QUEUE_ONLY (100% queue)"
        )
    
    elif mode == "CANARY":
        # Canary Safety Guards
        # 1. Symbol whitelist
        if symbol not in policy.safe_symbols:
            return RoutingDecision(
                route_to_queue=False,
                execute_legacy=True,
                reason=f"CANARY_BLOCKED: symbol {symbol} not in safe_symbols"
            )
        
        # 2. Order type whitelist
        if order_type not in policy.safe_order_types:
            return RoutingDecision(
                route_to_queue=False,
                execute_legacy=True,
                reason=f"CANARY_BLOCKED: orderType {order_type} not in safe_order_types"
            )
        
        # 3. Deterministic canary split (hash-based)
        # CRITICAL: Используем trace_id для determinism (тот же trace → тот же routing)
        canary_hash = int(hashlib.sha256(trace_id.encode()).hexdigest(), 16)
        canary_bucket = canary_hash % 100
        
        is_canary = (canary_bucket < policy.canary_percent)
        
        if is_canary:
            # Canary traffic → queue only
            return RoutingDecision(
                route_to_queue=True,
                execute_legacy=False,
                reason=f"CANARY_SELECTED (bucket={canary_bucket} < {policy.canary_percent}%)",
                canary_selected=True
            )
        else:
            # Non-canary → legacy only
            return RoutingDecision(
                route_to_queue=False,
                execute_legacy=True,
                reason=f"CANARY_NOT_SELECTED (bucket={canary_bucket} >= {policy.canary_percent}%)"
            )
    
    # Fallback (should never reach)
    return RoutingDecision(
        route_to_queue=False,
        execute_legacy=True,
        reason="UNKNOWN_MODE (fallback to legacy)"
    )


# Global policy instance
_routing_policy: ExecutionRoutingPolicy = ExecutionRoutingPolicy()


def get_routing_policy() -> ExecutionRoutingPolicy:
    """Get global routing policy."""
    return _routing_policy


def set_routing_policy(policy: ExecutionRoutingPolicy):
    """Set global routing policy."""
    global _routing_policy
    _routing_policy = policy


def load_routing_policy_from_env() -> ExecutionRoutingPolicy:
    """
    Load routing policy from environment variables.
    
    Environment Variables:
    - EXECUTION_ROUTING_MODE: LEGACY_ONLY | SHADOW | CANARY | QUEUE_ONLY
    - EXECUTION_QUEUE_CANARY_PERCENT: 0-100
    - EXECUTION_QUEUE_KILL_SWITCH: true | false
    """
    mode = os.getenv("EXECUTION_ROUTING_MODE", "SHADOW")
    canary_percent = int(os.getenv("EXECUTION_QUEUE_CANARY_PERCENT", "1"))
    kill_switch = os.getenv("EXECUTION_QUEUE_KILL_SWITCH", "false").lower() == "true"
    
    return ExecutionRoutingPolicy(
        mode=mode,
        canary_percent=canary_percent,
        kill_switch_enabled=kill_switch
    )
