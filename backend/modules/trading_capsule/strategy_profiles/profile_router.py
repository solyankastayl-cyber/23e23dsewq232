"""
Strategy Profile Router (STR1)
==============================

Routes signals and execution decisions through active profile.

Integrates with:
- Execution Engine
- Risk Engine
- Strategy Runtime
"""

import threading
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

from .profile_types import StrategyProfile, ProfileMode
from .profile_service import strategy_profile_service


class ProfileRouter:
    """
    Routes trading decisions through active profile constraints.
    
    Pipeline:
    Signal → Profile Router → Execution
    
    The router validates and modifies orders based on
    the active profile's rules.
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
        self._initialized = True
        print("[ProfileRouter] Initialized")
    
    # ===========================================
    # Signal Validation
    # ===========================================
    
    def validate_signal(
        self,
        symbol: str,
        signal_confidence: float,
        signal_direction: str
    ) -> Dict[str, Any]:
        """
        Validate if signal meets profile requirements.
        
        Args:
            symbol: Trading symbol
            signal_confidence: Signal confidence (0-1)
            signal_direction: "LONG" or "SHORT"
        
        Returns:
            Validation result with pass/fail and reasons
        """
        profile = strategy_profile_service.get_active_profile()
        
        result = {
            "valid": True,
            "symbol": symbol,
            "signal_confidence": signal_confidence,
            "direction": signal_direction,
            "profile_mode": profile.mode.value,
            "reasons": []
        }
        
        # Check symbol allowed
        if not strategy_profile_service.is_symbol_allowed(symbol):
            result["valid"] = False
            result["reasons"].append(f"Symbol {symbol} not in allowed list for {profile.mode.value}")
        
        # Check confidence threshold
        if signal_confidence < profile.signal_threshold:
            result["valid"] = False
            result["reasons"].append(
                f"Confidence {signal_confidence:.2f} below threshold {profile.signal_threshold:.2f}"
            )
        
        # Check market mode for shorts
        if signal_direction == "SHORT":
            if profile.market_mode.value == "SPOT_ONLY":
                result["valid"] = False
                result["reasons"].append("SHORT not allowed in SPOT_ONLY mode")
        
        return result
    
    # ===========================================
    # Position Sizing
    # ===========================================
    
    def calculate_position_size(
        self,
        portfolio_value: float,
        signal_confidence: float,
        current_exposure_pct: float = 0.0
    ) -> Dict[str, Any]:
        """
        Calculate position size based on profile rules.
        
        Args:
            portfolio_value: Total portfolio value in USD
            signal_confidence: Signal confidence (0-1)
            current_exposure_pct: Current exposure percentage
        
        Returns:
            Position sizing details
        """
        profile = strategy_profile_service.get_active_profile()
        
        # Max position value
        max_position_value = portfolio_value * profile.max_position_pct
        
        # Remaining exposure budget
        remaining_exposure = profile.max_portfolio_exposure_pct - current_exposure_pct
        max_from_exposure = portfolio_value * remaining_exposure
        
        # Scale by confidence
        confidence_factor = min(1.0, signal_confidence / profile.signal_threshold)
        
        # Calculate position
        base_position = min(max_position_value, max_from_exposure)
        scaled_position = base_position * confidence_factor
        
        # Apply min/max limits
        position_usd = max(profile.min_position_usd, min(profile.max_position_usd, scaled_position))
        
        # Check if position is valid
        is_valid = position_usd >= profile.min_position_usd and remaining_exposure > 0
        
        return {
            "valid": is_valid,
            "position_usd": round(position_usd, 2),
            "position_pct": round(position_usd / portfolio_value, 4) if portfolio_value > 0 else 0,
            "max_position_usd": profile.max_position_usd,
            "remaining_exposure_pct": round(remaining_exposure, 4),
            "confidence_scaling": round(confidence_factor, 4),
            "profile_limits": {
                "max_position_pct": profile.max_position_pct,
                "max_exposure_pct": profile.max_portfolio_exposure_pct
            }
        }
    
    # ===========================================
    # Risk Parameters
    # ===========================================
    
    def get_stop_levels(
        self,
        entry_price: float,
        direction: str
    ) -> Dict[str, float]:
        """
        Get stop loss and take profit levels.
        
        Args:
            entry_price: Entry price
            direction: "LONG" or "SHORT"
        
        Returns:
            Stop loss and take profit prices
        """
        profile = strategy_profile_service.get_active_profile()
        
        sl_pct = profile.default_stop_loss_pct
        tp_pct = profile.default_take_profit_pct
        
        if direction == "LONG":
            stop_loss = entry_price * (1 - sl_pct)
            take_profit = entry_price * (1 + tp_pct)
        else:  # SHORT
            stop_loss = entry_price * (1 + sl_pct)
            take_profit = entry_price * (1 - tp_pct)
        
        return {
            "stop_loss": round(stop_loss, 8),
            "take_profit": round(take_profit, 8),
            "stop_loss_pct": sl_pct,
            "take_profit_pct": tp_pct,
            "use_trailing": profile.use_trailing_stop,
            "trailing_pct": profile.trailing_stop_pct if profile.use_trailing_stop else None
        }
    
    # ===========================================
    # Leverage
    # ===========================================
    
    def get_leverage(
        self,
        signal_confidence: float,
        volatility: float = 0.02
    ) -> Dict[str, Any]:
        """
        Get leverage based on profile and market conditions.
        
        Args:
            signal_confidence: Signal confidence
            volatility: Current market volatility
        
        Returns:
            Leverage recommendation
        """
        profile = strategy_profile_service.get_active_profile()
        
        # Base leverage from profile
        base_leverage = profile.default_leverage
        max_leverage = profile.max_leverage
        
        # Reduce leverage for lower confidence
        confidence_factor = min(1.0, signal_confidence / 0.8)
        
        # Reduce leverage for high volatility
        vol_factor = min(1.0, 0.03 / volatility) if volatility > 0 else 1.0
        
        # Calculate final leverage
        adjusted_leverage = base_leverage * confidence_factor * vol_factor
        final_leverage = max(1.0, min(max_leverage, adjusted_leverage))
        
        return {
            "leverage": round(final_leverage, 1),
            "max_leverage": max_leverage,
            "base_leverage": base_leverage,
            "adjustments": {
                "confidence_factor": round(confidence_factor, 2),
                "volatility_factor": round(vol_factor, 2)
            }
        }
    
    # ===========================================
    # Trade Frequency Checks
    # ===========================================
    
    def check_trade_allowed(
        self,
        trades_today: int,
        last_trade_timestamp: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Check if new trade is allowed based on frequency limits.
        
        Args:
            trades_today: Number of trades executed today
            last_trade_timestamp: Timestamp of last trade
        
        Returns:
            Whether trade is allowed
        """
        profile = strategy_profile_service.get_active_profile()
        
        result = {
            "allowed": True,
            "reasons": [],
            "limits": {
                "max_trades_per_day": profile.max_trades_per_day,
                "min_interval_minutes": profile.min_time_between_trades_minutes
            }
        }
        
        # Check daily limit
        if trades_today >= profile.max_trades_per_day:
            result["allowed"] = False
            result["reasons"].append(f"Daily trade limit reached: {trades_today}/{profile.max_trades_per_day}")
        
        # Check time between trades
        if last_trade_timestamp:
            elapsed = (datetime.now(timezone.utc) - last_trade_timestamp).total_seconds() / 60
            if elapsed < profile.min_time_between_trades_minutes:
                result["allowed"] = False
                wait_time = profile.min_time_between_trades_minutes - elapsed
                result["reasons"].append(f"Must wait {wait_time:.1f} minutes between trades")
                result["wait_minutes"] = round(wait_time, 1)
        
        return result
    
    # ===========================================
    # Exit Validation
    # ===========================================
    
    def should_exit(
        self,
        current_confidence: float,
        bars_held: int,
        current_pnl_pct: float
    ) -> Dict[str, Any]:
        """
        Check if position should be exited.
        
        Args:
            current_confidence: Current signal confidence
            bars_held: Number of bars position has been held
            current_pnl_pct: Current PnL percentage
        
        Returns:
            Exit recommendation
        """
        profile = strategy_profile_service.get_active_profile()
        
        result = {
            "should_exit": False,
            "exit_reasons": [],
            "priority": "normal"
        }
        
        # Check confidence drop
        if current_confidence < profile.exit_threshold:
            result["should_exit"] = True
            result["exit_reasons"].append(
                f"Confidence {current_confidence:.2f} below exit threshold {profile.exit_threshold:.2f}"
            )
        
        # Check max holding period
        if bars_held >= profile.max_holding_bars:
            result["should_exit"] = True
            result["exit_reasons"].append(
                f"Max holding period reached: {bars_held}/{profile.max_holding_bars} bars"
            )
        
        # Check stop loss
        if current_pnl_pct <= -profile.default_stop_loss_pct:
            result["should_exit"] = True
            result["exit_reasons"].append(f"Stop loss triggered: {current_pnl_pct*100:.2f}%")
            result["priority"] = "high"
        
        # Check take profit
        if current_pnl_pct >= profile.default_take_profit_pct:
            result["should_exit"] = True
            result["exit_reasons"].append(f"Take profit reached: {current_pnl_pct*100:.2f}%")
        
        return result
    
    # ===========================================
    # Full Order Processing
    # ===========================================
    
    def process_order_request(
        self,
        symbol: str,
        direction: str,
        signal_confidence: float,
        portfolio_value: float,
        current_exposure_pct: float,
        entry_price: float,
        trades_today: int = 0,
        last_trade_timestamp: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Process a full order request through profile rules.
        
        Returns complete order specification or rejection.
        """
        profile = strategy_profile_service.get_active_profile()
        
        # Validate signal
        signal_validation = self.validate_signal(symbol, signal_confidence, direction)
        if not signal_validation["valid"]:
            return {
                "approved": False,
                "stage": "signal_validation",
                "reasons": signal_validation["reasons"]
            }
        
        # Check trade frequency
        frequency_check = self.check_trade_allowed(trades_today, last_trade_timestamp)
        if not frequency_check["allowed"]:
            return {
                "approved": False,
                "stage": "frequency_check",
                "reasons": frequency_check["reasons"]
            }
        
        # Calculate position size
        position = self.calculate_position_size(portfolio_value, signal_confidence, current_exposure_pct)
        if not position["valid"]:
            return {
                "approved": False,
                "stage": "position_sizing",
                "reasons": ["Position size invalid or no remaining exposure budget"]
            }
        
        # Get stop levels
        stops = self.get_stop_levels(entry_price, direction)
        
        # Get leverage
        leverage = self.get_leverage(signal_confidence)
        
        return {
            "approved": True,
            "order": {
                "symbol": symbol,
                "direction": direction,
                "quantity_usd": position["position_usd"],
                "leverage": leverage["leverage"],
                "entry_price": entry_price,
                "stop_loss": stops["stop_loss"],
                "take_profit": stops["take_profit"],
                "use_trailing_stop": stops["use_trailing"],
                "trailing_stop_pct": stops["trailing_pct"]
            },
            "profile": {
                "mode": profile.mode.value,
                "signal_threshold": profile.signal_threshold,
                "market_mode": profile.market_mode.value
            },
            "validation": {
                "signal": signal_validation,
                "frequency": frequency_check,
                "position": position
            }
        }
    
    def get_health(self) -> Dict[str, Any]:
        """Get router health"""
        return {
            "service": "ProfileRouter",
            "status": "healthy",
            "version": "str1",
            "active_profile": strategy_profile_service.get_active_mode().value
        }


# Global singleton
profile_router = ProfileRouter()
