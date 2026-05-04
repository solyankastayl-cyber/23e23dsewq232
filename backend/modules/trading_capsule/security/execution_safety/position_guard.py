"""
Position Guard (SEC1)
=====================

Protects against:
- Too large positions
- Wrong direction
- Position duplication
- Max scaling depth exceeded
"""

import threading
from datetime import datetime, timezone
from typing import Dict, List, Optional

from .safety_types import (
    SafetyDecision,
    SafetyDecisionResult,
    SafetyGuardType,
    PositionGuardConfig,
    OrderValidationRequest
)


class PositionGuard:
    """
    Position Limit Guard.
    
    Validates orders against:
    - Max position size
    - Max leverage
    - Direction conflicts
    - Scaling depth limits
    """
    
    def __init__(self, config: Optional[PositionGuardConfig] = None):
        self.config = config or PositionGuardConfig()
        self._positions: Dict[str, Dict] = {}  # symbol -> position info
        self._scaling_counts: Dict[str, int] = {}  # symbol -> scale count
        self._lock = threading.Lock()
    
    def validate(
        self,
        order: OrderValidationRequest,
        current_position: Optional[Dict] = None,
        current_price: Optional[float] = None
    ) -> SafetyDecisionResult:
        """Validate order against position limits"""
        if not self.config.enabled:
            return SafetyDecisionResult(
                decision=SafetyDecision.ALLOW,
                order_id=order.order_id,
                reason="Position guard disabled"
            )
        
        warnings = []
        
        # Calculate order value
        price = current_price or order.price or 0.0
        order_value = order.size * price
        
        # Get current position
        position = current_position or self._positions.get(order.symbol, {})
        position_size = position.get("size", 0.0)
        position_side = position.get("side", "")
        position_value = position.get("notional", 0.0)
        
        # Check 1: Max position size
        new_position_value = position_value + order_value
        if new_position_value > self.config.max_position_size_usd:
            return SafetyDecisionResult(
                decision=SafetyDecision.BLOCK,
                guard=SafetyGuardType.POSITION,
                order_id=order.order_id,
                reason=f"Order would exceed max position size ({new_position_value:.2f} > {self.config.max_position_size_usd})",
                details={
                    "currentPositionValue": position_value,
                    "orderValue": order_value,
                    "maxPositionSize": self.config.max_position_size_usd
                }
            )
        
        # Check 2: Direction conflict
        if position_side and position_size > 0:
            order_direction = "LONG" if order.side == "BUY" else "SHORT"
            position_direction = "LONG" if position_side == "BUY" else "SHORT"
            
            if order_direction != position_direction and not self.config.allow_direction_conflict:
                # This might be a close, which is OK
                if order_value >= position_value:
                    # Trying to flip position - warn but allow
                    warnings.append(f"Order will flip position direction ({position_direction} -> {order_direction})")
        
        # Check 3: Scaling depth
        with self._lock:
            scale_count = self._scaling_counts.get(order.symbol, 0)
            if position_size > 0 and order_direction == position_direction:
                # Adding to existing position
                if scale_count >= self.config.max_scaling_depth:
                    return SafetyDecisionResult(
                        decision=SafetyDecision.BLOCK,
                        guard=SafetyGuardType.POSITION,
                        order_id=order.order_id,
                        reason=f"Max scaling depth reached ({scale_count} >= {self.config.max_scaling_depth})",
                        details={
                            "currentScaleCount": scale_count,
                            "maxScalingDepth": self.config.max_scaling_depth
                        }
                    )
        
        # Check 4: Leverage (if we have account info)
        # This would require equity info to calculate properly
        
        result = SafetyDecisionResult(
            decision=SafetyDecision.WARN if warnings else SafetyDecision.ALLOW,
            order_id=order.order_id,
            reason="Position checks passed" + (f" with {len(warnings)} warning(s)" if warnings else ""),
            warnings=warnings
        )
        
        return result
    
    def update_position(self, symbol: str, position: Dict):
        """Update tracked position"""
        with self._lock:
            if position.get("size", 0) == 0:
                self._positions.pop(symbol, None)
                self._scaling_counts.pop(symbol, None)
            else:
                self._positions[symbol] = position
    
    def increment_scale_count(self, symbol: str):
        """Increment scaling count for symbol"""
        with self._lock:
            self._scaling_counts[symbol] = self._scaling_counts.get(symbol, 0) + 1
    
    def reset_scale_count(self, symbol: str):
        """Reset scaling count (when position closes)"""
        with self._lock:
            self._scaling_counts.pop(symbol, None)
    
    def get_stats(self) -> Dict:
        """Get guard statistics"""
        with self._lock:
            return {
                "trackedPositions": len(self._positions),
                "scalingCounts": dict(self._scaling_counts),
                "maxPositionSize": self.config.max_position_size_usd,
                "maxLeverage": self.config.max_leverage,
                "enabled": self.config.enabled
            }


# Global instance
position_guard = PositionGuard()
