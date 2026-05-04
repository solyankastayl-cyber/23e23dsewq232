"""
Trade Setup Generator V1 (PHASE 2.3)

Converts prediction into executable trade setup:
- Entry level
- Stop loss
- Target
- R:R ratio
- Position size
- Execution type

CRITICAL:
- No trade if R:R < 1.2
- Position sizing based on risk budget
- WAIT if levels are missing
"""

from dataclasses import dataclass, asdict
from typing import Dict, Any, Optional


@dataclass
class TradeSetup:
    """Complete trade setup with all execution details."""
    direction: str          # LONG / SHORT / WAIT
    entry: Optional[float]
    stop_loss: Optional[float]
    target: Optional[float]
    rr: Optional[float]
    position_size: Optional[float]  # As fraction of portfolio risk
    execution_type: str     # LIMIT / MARKET / BREAKOUT / WAIT
    valid: bool
    reason: str
    
    # Extra info
    risk_amount: Optional[float] = None
    reward_amount: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "direction": self.direction,
            "entry": self.entry,
            "stop_loss": self.stop_loss,
            "target": self.target,
            "rr": self.rr,
            "position_size": self.position_size,
            "execution_type": self.execution_type,
            "valid": self.valid,
            "reason": self.reason,
            "risk_amount": self.risk_amount,
            "reward_amount": self.reward_amount,
        }


class TradeSetupGenerator:
    """
    Generates executable trade setups from predictions.
    
    Uses pattern levels, regime context, and risk management rules.
    """
    
    def __init__(self):
        # Risk parameters
        self.base_risk_per_trade = 0.01  # 1% of capital per trade
        self.min_rr = 1.2                # Minimum R:R to take trade
        self.max_rr = 10.0               # Cap unrealistic R:R
        
        # Confidence-based position sizing
        self.confidence_multipliers = {
            "HIGH": 1.3,      # confidence >= 0.7
            "MEDIUM": 1.0,    # confidence >= 0.5
            "LOW": 0.7,       # confidence >= 0.35
            "VERY_LOW": 0.5,  # confidence < 0.35
        }
    
    # ═══════════════════════════════════════════════════════════════════
    # MAIN ENTRY
    # ═══════════════════════════════════════════════════════════════════
    
    def build_setup(
        self,
        prediction: Dict[str, Any],
        features: Dict[str, Any]
    ) -> TradeSetup:
        """
        Build trade setup from prediction and features.
        
        Args:
            prediction: From PredictionEngineV2 (with direction, target, confidence)
            features: From expanded adapter (with pattern levels, regime, etc.)
        
        Returns:
            TradeSetup with entry, stop, target, R:R, position size
        """
        # Check tradeability
        if not prediction.get("tradeable", False):
            return TradeSetup(
                direction="WAIT",
                entry=None,
                stop_loss=None,
                target=None,
                rr=None,
                position_size=None,
                execution_type="WAIT",
                valid=False,
                reason=prediction.get("reason", "Prediction not tradeable")
            )
        
        direction = prediction.get("direction", {}).get("label", "neutral").upper()
        if direction not in ["LONG", "SHORT", "BULLISH", "BEARISH"]:
            return TradeSetup(
                direction="WAIT",
                entry=None,
                stop_loss=None,
                target=None,
                rr=None,
                position_size=None,
                execution_type="WAIT",
                valid=False,
                reason="No clear direction"
            )
        
        # Normalize direction
        if direction == "BULLISH":
            direction = "LONG"
        elif direction == "BEARISH":
            direction = "SHORT"
        
        # Flatten features
        f = self._flatten_features(features)
        price = f["price"]
        
        # Compute entry
        entry = self._compute_entry(direction, f, prediction)
        
        # Compute stop loss
        stop = self._compute_stop(direction, f, prediction)
        
        # Get target from prediction
        target = prediction.get("target", {}).get("target_price")
        
        # Validate levels
        if not entry or not stop or not target:
            return TradeSetup(
                direction="WAIT",
                entry=None,
                stop_loss=None,
                target=None,
                rr=None,
                position_size=None,
                execution_type="WAIT",
                valid=False,
                reason="Missing entry/stop/target levels"
            )
        
        # Compute R:R
        rr = self._compute_rr(entry, stop, target, direction)
        
        # Filter low R:R
        if rr is None or rr < self.min_rr:
            return TradeSetup(
                direction="WAIT",
                entry=entry,
                stop_loss=stop,
                target=target,
                rr=rr,
                position_size=None,
                execution_type="WAIT",
                valid=False,
                reason=f"Low R:R ({rr:.2f} < {self.min_rr})" if rr else "Invalid R:R"
            )
        
        # Cap unrealistic R:R
        rr = min(rr, self.max_rr)
        
        # Compute position size
        confidence_label = prediction.get("confidence", {}).get("label", "LOW")
        position_size = self._compute_position_size(entry, stop, confidence_label)
        
        # Determine execution type
        execution_type = self._compute_execution_type(f, price, entry, direction)
        
        # Calculate risk/reward amounts
        risk_amount = abs(entry - stop)
        reward_amount = abs(target - entry)
        
        return TradeSetup(
            direction=direction,
            entry=round(entry, 2),
            stop_loss=round(stop, 2),
            target=round(target, 2),
            rr=round(rr, 2),
            position_size=round(position_size, 6),
            execution_type=execution_type,
            valid=True,
            reason="Valid setup",
            risk_amount=round(risk_amount, 2),
            reward_amount=round(reward_amount, 2),
        )
    
    # ═══════════════════════════════════════════════════════════════════
    # FEATURE FLATTENING
    # ═══════════════════════════════════════════════════════════════════
    
    def _flatten_features(self, features: Dict) -> Dict[str, Any]:
        """Flatten feature blocks."""
        pattern = features.get("pattern", {})
        structure = features.get("structure", {})
        indicators = features.get("indicators", {})
        
        return {
            "price": float(features.get("price", 0)),
            "breakout_level": pattern.get("breakout_level"),
            "invalidation_level": pattern.get("invalidation_level"),
            "range_width": float(pattern.get("range_width", 0)),
            "pattern_type": pattern.get("type", "none"),
            "compression_score": float(structure.get("compression_score", 0)),
            "trend_bias": float(indicators.get("trend_bias", 0)),
            "volatility_state": indicators.get("volatility_state", "normal"),
            "trend_direction": structure.get("trend_direction", "flat"),
            "regime": structure.get("regime", "range"),
        }
    
    # ═══════════════════════════════════════════════════════════════════
    # ENTRY LOGIC
    # ═══════════════════════════════════════════════════════════════════
    
    def _compute_entry(
        self,
        direction: str,
        f: Dict,
        prediction: Dict
    ) -> Optional[float]:
        """
        Compute entry level based on setup type.
        
        Entry types:
        - BREAKOUT: Enter at breakout level
        - PULLBACK: Enter slightly better than current price
        - MARKET: Enter at current price
        """
        price = f["price"]
        breakout = f["breakout_level"]
        compression = f["compression_score"]
        trend_bias = f["trend_bias"]
        regime = f["regime"]
        
        if not price:
            return None
        
        # Breakout entry for compression
        if compression > 0.6 and breakout:
            return breakout
        
        # Breakout entry for triangle/wedge patterns
        if f["pattern_type"] in ["ascending_triangle", "descending_triangle", 
                                  "symmetrical_triangle", "wedge", "pennant"]:
            if breakout:
                return breakout
        
        # Pullback entry in trend
        if regime == "trend":
            if direction == "LONG" and trend_bias > 0.3:
                return price * 0.995  # 0.5% below current
            elif direction == "SHORT" and trend_bias < -0.3:
                return price * 1.005  # 0.5% above current
        
        # Default: market entry
        return price
    
    # ═══════════════════════════════════════════════════════════════════
    # STOP LOSS
    # ═══════════════════════════════════════════════════════════════════
    
    def _compute_stop(
        self,
        direction: str,
        f: Dict,
        prediction: Dict
    ) -> Optional[float]:
        """
        Compute stop loss using invalidation level + buffer.
        """
        invalidation = f["invalidation_level"]
        price = f["price"]
        range_width = f["range_width"]
        volatility = f["volatility_state"]
        
        # Buffer based on volatility
        buffer_pct = {
            "low": 0.002,      # 0.2%
            "normal": 0.005,   # 0.5%
            "high": 0.01,      # 1%
            "compression": 0.003,  # 0.3%
        }.get(volatility, 0.005)
        
        # Use invalidation level if available
        if invalidation:
            buffer = price * buffer_pct
            if direction == "LONG":
                return invalidation - buffer
            else:
                return invalidation + buffer
        
        # Fallback: use % from entry
        default_stop_pct = 0.03  # 3%
        if direction == "LONG":
            return price * (1 - default_stop_pct)
        else:
            return price * (1 + default_stop_pct)
    
    # ═══════════════════════════════════════════════════════════════════
    # R:R CALCULATION
    # ═══════════════════════════════════════════════════════════════════
    
    def _compute_rr(
        self,
        entry: float,
        stop: float,
        target: float,
        direction: str
    ) -> Optional[float]:
        """Calculate risk:reward ratio."""
        if direction == "LONG":
            risk = entry - stop
            reward = target - entry
        else:
            risk = stop - entry
            reward = entry - target
        
        if risk <= 0 or reward <= 0:
            return None
        
        return reward / risk
    
    # ═══════════════════════════════════════════════════════════════════
    # POSITION SIZING
    # ═══════════════════════════════════════════════════════════════════
    
    def _compute_position_size(
        self,
        entry: float,
        stop: float,
        confidence_label: str
    ) -> float:
        """
        Compute position size based on risk budget and confidence.
        
        Formula: position_size = risk_budget / risk_per_unit
        """
        risk_per_trade = self.base_risk_per_trade
        
        # Adjust by confidence
        multiplier = self.confidence_multipliers.get(confidence_label, 1.0)
        risk_per_trade *= multiplier
        
        # Risk per unit
        risk_per_unit = abs(entry - stop)
        
        if risk_per_unit == 0:
            return 0.0
        
        # Position size as fraction of capital at risk
        position_size = risk_per_trade / risk_per_unit
        
        # Normalize to reasonable range
        return min(position_size, 0.1)  # Max 10% position
    
    # ═══════════════════════════════════════════════════════════════════
    # EXECUTION TYPE
    # ═══════════════════════════════════════════════════════════════════
    
    def _compute_execution_type(
        self,
        f: Dict,
        price: float,
        entry: float,
        direction: str
    ) -> str:
        """
        Determine execution type based on context.
        
        Types:
        - BREAKOUT: Wait for level break
        - LIMIT: Place limit order
        - MARKET: Execute immediately
        """
        compression = f["compression_score"]
        volatility = f["volatility_state"]
        pattern_type = f["pattern_type"]
        
        # Compression = breakout
        if compression > 0.6:
            return "BREAKOUT"
        
        # Triangle/wedge = breakout
        if pattern_type in ["ascending_triangle", "descending_triangle",
                            "symmetrical_triangle", "wedge", "pennant"]:
            return "BREAKOUT"
        
        # High volatility = market
        if volatility == "high":
            return "MARKET"
        
        # Entry differs from current price = limit
        if direction == "LONG" and entry < price * 0.999:
            return "LIMIT"
        if direction == "SHORT" and entry > price * 1.001:
            return "LIMIT"
        
        # Default
        return "LIMIT"


# ═══════════════════════════════════════════════════════════════════════════
# SINGLETON
# ═══════════════════════════════════════════════════════════════════════════

_generator = None

def get_trade_setup_generator() -> TradeSetupGenerator:
    """Get singleton instance."""
    global _generator
    if _generator is None:
        _generator = TradeSetupGenerator()
    return _generator


def build_trade_setup(
    prediction: Dict[str, Any],
    features: Dict[str, Any]
) -> Dict[str, Any]:
    """Build trade setup from prediction and features."""
    generator = get_trade_setup_generator()
    setup = generator.build_setup(prediction, features)
    return setup.to_dict()
