"""
Pilot Trading Mode

PHASE 43.3 — Pilot Trading Mode

Safe launch mode for live trading.

Pilot constraints:
- max_capital_usage = 5% portfolio
- max_position_size = 2% portfolio
- max_trades_per_hour = 10

Rules:
- If exceeded → execution blocked
- APPROVAL mode default
- All safety layers ON
"""

from typing import Optional, Dict, List
from datetime import datetime, timezone, timedelta
from pydantic import BaseModel, Field
from enum import Enum


class TradingMode(str, Enum):
    """Trading operation mode."""
    PAPER = "PAPER"           # Simulated only
    PILOT = "PILOT"           # Live with strict limits
    LIVE = "LIVE"             # Full live trading
    MAINTENANCE = "MAINTENANCE"  # No trading


class PilotConstraints(BaseModel):
    """Pilot mode constraints."""
    # Capital limits
    max_capital_usage_pct: float = 5.0        # Max 5% of portfolio
    max_position_size_pct: float = 2.0        # Max 2% per position
    max_single_order_usd: float = 5000.0      # Max $5000 per order
    
    # Rate limits
    max_trades_per_hour: int = 10
    max_trades_per_day: int = 30
    
    # Safety requirements
    require_approval_mode: bool = True
    require_kill_switch: bool = True
    require_circuit_breaker: bool = True
    require_trade_throttle: bool = True


class PilotState(BaseModel):
    """Current pilot mode state."""
    state_id: str = Field(default_factory=lambda: f"pilot_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S%f')}")
    
    # Mode
    trading_mode: TradingMode = TradingMode.PILOT
    
    # Usage tracking
    capital_used_pct: float = 0.0
    capital_used_usd: float = 0.0
    largest_position_pct: float = 0.0
    
    # Trade counts
    trades_this_hour: int = 0
    trades_today: int = 0
    
    # Constraint violations
    violations_today: int = 0
    last_violation: Optional[str] = None
    
    # Safety status
    approval_mode_active: bool = True
    kill_switch_ready: bool = True
    circuit_breaker_ready: bool = True
    trade_throttle_active: bool = True
    
    # Timestamps
    pilot_started_at: Optional[datetime] = None
    last_trade_at: Optional[datetime] = None
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class PilotCheckResult(BaseModel):
    """Result of pilot constraint check."""
    allowed: bool
    violated_constraints: List[str] = Field(default_factory=list)
    adjusted_size_usd: Optional[float] = None
    message: str = ""


class PilotModeEngine:
    """
    Pilot Mode Engine — PHASE 43.3
    
    Enforces safe trading constraints during pilot rollout.
    
    Stages:
    A. paper + approval
    B. live + approval + small capital (PILOT)
    C. live + partial automation
    D. full automation (after stats confirm stability)
    """
    
    def __init__(
        self,
        constraints: Optional[PilotConstraints] = None,
        portfolio_value_usd: float = 100000.0,
    ):
        self._constraints = constraints or PilotConstraints()
        self._portfolio_value_usd = portfolio_value_usd
        self._state = PilotState()
        
        # Position tracking
        self._positions_usd: Dict[str, float] = {}
        
        # Trade history (for rate limits)
        self._trades_hourly: List[datetime] = []
        self._trades_daily: List[datetime] = []
    
    # ═══════════════════════════════════════════════════════════
    # 1. Constraint Checking
    # ═══════════════════════════════════════════════════════════
    
    def check_constraints(
        self,
        symbol: str,
        size_usd: float,
        side: str,
    ) -> PilotCheckResult:
        """
        Check if trade meets pilot constraints.
        
        Called before execution.
        """
        if self._state.trading_mode == TradingMode.PAPER:
            return PilotCheckResult(allowed=True, message="Paper mode - all trades allowed")
        
        if self._state.trading_mode == TradingMode.MAINTENANCE:
            return PilotCheckResult(
                allowed=False,
                violated_constraints=["MAINTENANCE_MODE"],
                message="System in maintenance mode",
            )
        
        violations = []
        adjusted_size = size_usd
        
        # Check 1: Single order size
        max_order = self._constraints.max_single_order_usd
        if size_usd > max_order:
            violations.append(f"ORDER_SIZE: ${size_usd:.0f} > ${max_order:.0f}")
            adjusted_size = max_order
        
        # Check 2: Position size limit
        max_position_pct = self._constraints.max_position_size_pct
        max_position_usd = self._portfolio_value_usd * (max_position_pct / 100)
        
        current_position = self._positions_usd.get(symbol, 0.0)
        new_position = current_position + size_usd if side == "BUY" else current_position - size_usd
        
        if abs(new_position) > max_position_usd:
            violations.append(f"POSITION_SIZE: {symbol} would be ${abs(new_position):.0f} > ${max_position_usd:.0f}")
            # Adjust size to stay within limit
            if side == "BUY":
                adjusted_size = max(0, max_position_usd - current_position)
            else:
                adjusted_size = max(0, current_position + max_position_usd)
        
        # Check 3: Total capital usage
        max_capital_pct = self._constraints.max_capital_usage_pct
        max_capital_usd = self._portfolio_value_usd * (max_capital_pct / 100)
        
        total_exposure = sum(abs(v) for v in self._positions_usd.values())
        if total_exposure + size_usd > max_capital_usd:
            violations.append(f"CAPITAL_USAGE: ${total_exposure + size_usd:.0f} > ${max_capital_usd:.0f}")
        
        # Check 4: Hourly trade limit
        self._cleanup_old_trades()
        if len(self._trades_hourly) >= self._constraints.max_trades_per_hour:
            violations.append(f"HOURLY_LIMIT: {len(self._trades_hourly)}/{self._constraints.max_trades_per_hour}")
        
        # Check 5: Daily trade limit
        if len(self._trades_daily) >= self._constraints.max_trades_per_day:
            violations.append(f"DAILY_LIMIT: {len(self._trades_daily)}/{self._constraints.max_trades_per_day}")
        
        # Check 6: Safety layers
        if self._constraints.require_approval_mode and not self._state.approval_mode_active:
            violations.append("APPROVAL_MODE: Required but not active")
        
        if self._constraints.require_kill_switch and not self._state.kill_switch_ready:
            violations.append("KILL_SWITCH: Required but not ready")
        
        if self._constraints.require_circuit_breaker and not self._state.circuit_breaker_ready:
            violations.append("CIRCUIT_BREAKER: Required but not ready")
        
        # Determine result
        if violations:
            self._state.violations_today += 1
            self._state.last_violation = violations[0]
            
            # Some violations are hard blocks, some allow adjusted size
            hard_blocks = ["MAINTENANCE_MODE", "HOURLY_LIMIT", "DAILY_LIMIT", "APPROVAL_MODE", "KILL_SWITCH", "CIRCUIT_BREAKER"]
            has_hard_block = any(v.split(":")[0] in hard_blocks for v in violations)
            
            if has_hard_block:
                return PilotCheckResult(
                    allowed=False,
                    violated_constraints=violations,
                    message=f"Blocked: {violations[0]}",
                )
            else:
                # Allow with adjusted size
                return PilotCheckResult(
                    allowed=adjusted_size > 0,
                    violated_constraints=violations,
                    adjusted_size_usd=adjusted_size if adjusted_size != size_usd else None,
                    message=f"Adjusted: {violations[0]}" if adjusted_size != size_usd else "OK",
                )
        
        return PilotCheckResult(
            allowed=True,
            message="All pilot constraints passed",
        )
    
    # ═══════════════════════════════════════════════════════════
    # 2. Trade Recording
    # ═══════════════════════════════════════════════════════════
    
    def record_trade(self, symbol: str, size_usd: float, side: str):
        """Record a completed trade."""
        now = datetime.now(timezone.utc)
        
        # Update position
        current = self._positions_usd.get(symbol, 0.0)
        if side == "BUY":
            self._positions_usd[symbol] = current + size_usd
        else:
            self._positions_usd[symbol] = current - size_usd
        
        # Record trade time
        self._trades_hourly.append(now)
        self._trades_daily.append(now)
        
        # Update state
        self._state.trades_this_hour = len(self._trades_hourly)
        self._state.trades_today = len(self._trades_daily)
        self._state.last_trade_at = now
        
        # Update capital usage
        total_exposure = sum(abs(v) for v in self._positions_usd.values())
        self._state.capital_used_usd = total_exposure
        self._state.capital_used_pct = (total_exposure / self._portfolio_value_usd) * 100
        
        # Update largest position
        if self._positions_usd:
            largest = max(abs(v) for v in self._positions_usd.values())
            self._state.largest_position_pct = (largest / self._portfolio_value_usd) * 100
        
        self._state.updated_at = now
    
    def _cleanup_old_trades(self):
        """Remove old trades from tracking."""
        now = datetime.now(timezone.utc)
        
        # Hourly: keep last hour
        cutoff_hour = now - timedelta(hours=1)
        self._trades_hourly = [t for t in self._trades_hourly if t > cutoff_hour]
        
        # Daily: keep last 24 hours
        cutoff_day = now - timedelta(hours=24)
        self._trades_daily = [t for t in self._trades_daily if t > cutoff_day]
    
    # ═══════════════════════════════════════════════════════════
    # 3. Mode Management
    # ═══════════════════════════════════════════════════════════
    
    def set_mode(self, mode: TradingMode):
        """Set trading mode."""
        self._state.trading_mode = mode
        
        if mode == TradingMode.PILOT and not self._state.pilot_started_at:
            self._state.pilot_started_at = datetime.now(timezone.utc)
    
    def get_mode(self) -> TradingMode:
        """Get current trading mode."""
        return self._state.trading_mode
    
    def set_safety_status(
        self,
        approval_mode: Optional[bool] = None,
        kill_switch: Optional[bool] = None,
        circuit_breaker: Optional[bool] = None,
        trade_throttle: Optional[bool] = None,
    ):
        """Update safety layer status."""
        if approval_mode is not None:
            self._state.approval_mode_active = approval_mode
        if kill_switch is not None:
            self._state.kill_switch_ready = kill_switch
        if circuit_breaker is not None:
            self._state.circuit_breaker_ready = circuit_breaker
        if trade_throttle is not None:
            self._state.trade_throttle_active = trade_throttle
    
    def set_portfolio_value(self, value_usd: float):
        """Update portfolio value."""
        self._portfolio_value_usd = value_usd
    
    # ═══════════════════════════════════════════════════════════
    # 4. State Access
    # ═══════════════════════════════════════════════════════════
    
    def get_state(self) -> PilotState:
        """Get current pilot state."""
        self._cleanup_old_trades()
        self._state.trades_this_hour = len(self._trades_hourly)
        self._state.trades_today = len(self._trades_daily)
        self._state.updated_at = datetime.now(timezone.utc)
        return self._state
    
    def get_constraints(self) -> PilotConstraints:
        """Get pilot constraints."""
        return self._constraints
    
    def update_constraints(self, constraints: PilotConstraints):
        """Update pilot constraints."""
        self._constraints = constraints
    
    def get_summary(self) -> Dict:
        """Get pilot mode summary."""
        state = self.get_state()
        
        return {
            "phase": "43.3",
            "trading_mode": state.trading_mode.value,
            "capital_usage": {
                "used_pct": round(state.capital_used_pct, 2),
                "used_usd": round(state.capital_used_usd, 2),
                "limit_pct": self._constraints.max_capital_usage_pct,
                "limit_usd": round(self._portfolio_value_usd * self._constraints.max_capital_usage_pct / 100, 2),
            },
            "position_limits": {
                "largest_pct": round(state.largest_position_pct, 2),
                "max_pct": self._constraints.max_position_size_pct,
                "max_order_usd": self._constraints.max_single_order_usd,
            },
            "trade_counts": {
                "this_hour": f"{state.trades_this_hour}/{self._constraints.max_trades_per_hour}",
                "today": f"{state.trades_today}/{self._constraints.max_trades_per_day}",
            },
            "safety_status": {
                "approval_mode": state.approval_mode_active,
                "kill_switch": state.kill_switch_ready,
                "circuit_breaker": state.circuit_breaker_ready,
                "trade_throttle": state.trade_throttle_active,
            },
            "violations_today": state.violations_today,
            "last_violation": state.last_violation,
            "pilot_started_at": state.pilot_started_at.isoformat() if state.pilot_started_at else None,
        }


# ══════════════════════════════════════════════════════════════
# Singleton
# ══════════════════════════════════════════════════════════════

_pilot_engine: Optional[PilotModeEngine] = None


def get_pilot_mode_engine() -> PilotModeEngine:
    """Get singleton instance."""
    global _pilot_engine
    if _pilot_engine is None:
        _pilot_engine = PilotModeEngine()
    return _pilot_engine
