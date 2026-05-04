"""
PHASE 6.2 - Scenario Runner
============================
Runs strategies inside simulated scenarios.
"""

import uuid
import random
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass

from .scenario_types import (
    ScenarioDefinition, ScenarioRun, StrategyScenarioResult,
    ShockParameters
)
from .scenario_simulator import ScenarioSimulator, SimulatedCandle


@dataclass
class SimulatedPosition:
    """Position during simulation"""
    strategy_id: str
    symbol: str
    side: str  # "LONG" or "SHORT"
    entry_price: float
    size: float
    entry_candle_idx: int
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    
    # State
    current_pnl: float = 0.0
    max_adverse_move: float = 0.0
    is_open: bool = True
    exit_price: Optional[float] = None
    exit_candle_idx: Optional[int] = None
    exit_reason: Optional[str] = None


@dataclass
class StrategyState:
    """Strategy state during simulation"""
    strategy_id: str
    
    # Capital
    initial_capital: float = 100000.0
    current_capital: float = 100000.0
    
    # Performance
    total_pnl: float = 0.0
    max_drawdown: float = 0.0
    peak_capital: float = 100000.0
    
    # Positions
    positions: List[SimulatedPosition] = None
    closed_positions: List[SimulatedPosition] = None
    
    # Metrics
    trades_executed: int = 0
    trades_won: int = 0
    trades_lost: int = 0
    risk_breaches: int = 0
    margin_calls: int = 0
    liquidations: int = 0
    orders_failed: int = 0
    total_slippage: float = 0.0
    
    # Status
    is_active: bool = True
    exit_reason: Optional[str] = None
    
    def __post_init__(self):
        if self.positions is None:
            self.positions = []
        if self.closed_positions is None:
            self.closed_positions = []


# Mock strategies for simulation
MOCK_STRATEGIES = [
    {"id": "MTF_BREAKOUT", "type": "trend", "risk_pct": 0.02},
    {"id": "DOUBLE_BOTTOM", "type": "pattern", "risk_pct": 0.015},
    {"id": "MOMENTUM_CONT", "type": "momentum", "risk_pct": 0.02},
    {"id": "MEAN_REVERSION", "type": "mean_reversion", "risk_pct": 0.01},
    {"id": "VOLATILITY_BREAKOUT", "type": "volatility", "risk_pct": 0.025},
]


class ScenarioRunner:
    """
    Runs strategies inside simulated stress scenarios
    """
    
    def __init__(self, db=None):
        self.db = db
    
    async def run_scenario(
        self,
        scenario: ScenarioDefinition,
        symbol: str = "BTC",
        timeframe: str = "1d",
        strategies: List[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Tuple[ScenarioRun, List[StrategyScenarioResult]]:
        """
        Run scenario test
        
        Returns: (run_info, strategy_results)
        """
        
        # Default strategies
        if strategies is None:
            strategies = [s["id"] for s in MOCK_STRATEGIES]
        
        # Default date range
        if not end_date:
            end_date = datetime.now(timezone.utc)
        if not start_date:
            start_date = end_date - timedelta(days=365)
        
        # Create run record
        run = ScenarioRun(
            run_id=f"scnrun_{uuid.uuid4().hex[:12]}",
            scenario_id=scenario.scenario_id,
            symbol=symbol,
            timeframe=timeframe,
            strategies_tested=strategies,
            dataset_start=start_date,
            dataset_end=end_date,
            started_at=datetime.now(timezone.utc),
            status="RUNNING"
        )
        
        try:
            # Get/generate candle data
            candles = await self._get_candles(symbol, timeframe, start_date, end_date)
            
            if len(candles) < scenario.duration_candles + 20:
                run.status = "FAILED"
                run.error = f"Insufficient data: need {scenario.duration_candles + 20}, got {len(candles)}"
                run.finished_at = datetime.now(timezone.utc)
                return run, []
            
            # Create simulator
            simulator = ScenarioSimulator(scenario)
            
            # Determine shock start (random point in first 30% of data)
            shock_start = random.randint(10, len(candles) // 3)
            
            # Simulate candles
            simulated_candles = simulator.simulate_candles(candles, shock_start)
            run.candles_processed = len(simulated_candles)
            
            # Run each strategy
            strategy_results = []
            for strategy_id in strategies:
                result = self._run_strategy(
                    strategy_id=strategy_id,
                    simulated_candles=simulated_candles,
                    simulator=simulator,
                    shock_start=shock_start,
                    scenario=scenario
                )
                strategy_results.append(result)
            
            run.status = "COMPLETED"
            run.finished_at = datetime.now(timezone.utc)
            
            return run, strategy_results
            
        except Exception as e:
            run.status = "FAILED"
            run.error = str(e)
            run.finished_at = datetime.now(timezone.utc)
            return run, []
    
    def _run_strategy(
        self,
        strategy_id: str,
        simulated_candles: List[SimulatedCandle],
        simulator: ScenarioSimulator,
        shock_start: int,
        scenario: ScenarioDefinition
    ) -> StrategyScenarioResult:
        """Run single strategy through scenario"""
        
        # Find strategy config
        strategy_config = next(
            (s for s in MOCK_STRATEGIES if s["id"] == strategy_id),
            {"id": strategy_id, "type": "generic", "risk_pct": 0.02}
        )
        
        # Initialize state
        state = StrategyState(strategy_id=strategy_id)
        
        shock_end = shock_start + scenario.shock_parameters.shock_duration_candles
        recovery_end = shock_end + scenario.shock_parameters.recovery_candles
        
        # Process each candle
        for i, candle in enumerate(simulated_candles):
            if not state.is_active:
                break
            
            phase = candle.shock_phase
            
            # Update positions
            self._update_positions(state, candle, simulator, phase)
            
            # Check for risk breaches
            self._check_risk_limits(state, candle, phase)
            
            # Maybe generate new trades (less likely during shock)
            if state.is_active and random.random() < self._get_trade_probability(phase, strategy_config):
                self._maybe_open_position(state, candle, simulator, phase, strategy_config)
            
            # Update drawdown
            if state.current_capital > state.peak_capital:
                state.peak_capital = state.current_capital
            
            current_dd = (state.peak_capital - state.current_capital) / state.peak_capital
            if current_dd > state.max_drawdown:
                state.max_drawdown = current_dd
            
            # Check for strategy death
            if state.current_capital < state.initial_capital * 0.3:  # 70% loss = dead
                state.is_active = False
                state.exit_reason = "CAPITAL_DEPLETED"
        
        # Calculate recovery time
        recovery_time = self._calculate_recovery_time(
            simulated_candles, shock_start, shock_end
        )
        
        # Build result
        return StrategyScenarioResult(
            strategy_id=strategy_id,
            total_pnl_pct=(state.current_capital - state.initial_capital) / state.initial_capital * 100,
            max_drawdown_pct=state.max_drawdown * 100,
            recovery_time_candles=recovery_time,
            trades_executed=state.trades_executed,
            trades_won=state.trades_won,
            trades_lost=state.trades_lost,
            risk_breaches=state.risk_breaches,
            position_liquidations=state.liquidations,
            margin_calls=state.margin_calls,
            orders_failed=state.orders_failed,
            slippage_total_pct=state.total_slippage * 100,
            survived=state.is_active or state.exit_reason != "CAPITAL_DEPLETED",
            exit_reason=state.exit_reason
        )
    
    def _get_trade_probability(self, phase: str, strategy_config: Dict) -> float:
        """Get probability of trading based on phase"""
        base_prob = 0.1
        
        if phase == "SHOCK":
            # Most strategies reduce activity during shock
            if strategy_config["type"] == "mean_reversion":
                return base_prob * 1.5  # Mean reversion more active
            return base_prob * 0.3  # Others pull back
        elif phase == "RECOVERY":
            return base_prob * 0.7
        
        return base_prob
    
    def _update_positions(
        self,
        state: StrategyState,
        candle: SimulatedCandle,
        simulator: ScenarioSimulator,
        phase: str
    ):
        """Update open positions"""
        for pos in state.positions[:]:  # Copy to allow modification
            if not pos.is_open:
                continue
            
            # Calculate PnL
            if pos.side == "LONG":
                pnl_pct = (candle.close - pos.entry_price) / pos.entry_price
                adverse = (pos.entry_price - candle.low) / pos.entry_price
            else:
                pnl_pct = (pos.entry_price - candle.close) / pos.entry_price
                adverse = (candle.high - pos.entry_price) / pos.entry_price
            
            pos.current_pnl = pnl_pct
            if adverse > pos.max_adverse_move:
                pos.max_adverse_move = adverse
            
            # Check stop loss
            if pos.stop_loss:
                if pos.side == "LONG" and candle.low <= pos.stop_loss:
                    self._close_position(state, pos, pos.stop_loss, "STOP_LOSS")
                elif pos.side == "SHORT" and candle.high >= pos.stop_loss:
                    self._close_position(state, pos, pos.stop_loss, "STOP_LOSS")
            
            # Check take profit
            if pos.is_open and pos.take_profit:
                if pos.side == "LONG" and candle.high >= pos.take_profit:
                    self._close_position(state, pos, pos.take_profit, "TAKE_PROFIT")
                elif pos.side == "SHORT" and candle.low <= pos.take_profit:
                    self._close_position(state, pos, pos.take_profit, "TAKE_PROFIT")
            
            # Liquidation check (during shock, 20% adverse move = liquidation)
            if pos.is_open and phase == "SHOCK" and adverse > 0.2:
                slippage = simulator.calculate_slippage(pos.size * candle.close, pos.side, phase)
                exit_price = candle.close * (1 - slippage if pos.side == "LONG" else 1 + slippage)
                self._close_position(state, pos, exit_price, "LIQUIDATION")
                state.liquidations += 1
    
    def _close_position(
        self,
        state: StrategyState,
        pos: SimulatedPosition,
        exit_price: float,
        reason: str
    ):
        """Close a position"""
        pos.is_open = False
        pos.exit_price = exit_price
        pos.exit_reason = reason
        
        # Calculate final PnL
        if pos.side == "LONG":
            pnl = (exit_price - pos.entry_price) / pos.entry_price * pos.size
        else:
            pnl = (pos.entry_price - exit_price) / pos.entry_price * pos.size
        
        state.current_capital += pnl
        state.total_pnl += pnl
        
        if pnl > 0:
            state.trades_won += 1
        else:
            state.trades_lost += 1
        
        state.positions.remove(pos)
        state.closed_positions.append(pos)
    
    def _maybe_open_position(
        self,
        state: StrategyState,
        candle: SimulatedCandle,
        simulator: ScenarioSimulator,
        phase: str,
        strategy_config: Dict
    ):
        """Maybe open a new position"""
        
        # Don't open if already have position
        if len(state.positions) >= 2:
            return
        
        # Calculate slippage
        risk_pct = strategy_config.get("risk_pct", 0.02)
        position_size = state.current_capital * risk_pct
        slippage = simulator.calculate_slippage(position_size, "BUY", phase)
        state.total_slippage += slippage
        
        # Random direction
        side = random.choice(["LONG", "SHORT"])
        entry_price = candle.close * (1 + slippage if side == "LONG" else 1 - slippage)
        
        # Set SL/TP
        atr_estimate = (candle.high - candle.low) * 2
        if side == "LONG":
            stop_loss = entry_price - atr_estimate
            take_profit = entry_price + atr_estimate * 1.5
        else:
            stop_loss = entry_price + atr_estimate
            take_profit = entry_price - atr_estimate * 1.5
        
        pos = SimulatedPosition(
            strategy_id=state.strategy_id,
            symbol="BTC",
            side=side,
            entry_price=entry_price,
            size=position_size,
            entry_candle_idx=0,
            stop_loss=stop_loss,
            take_profit=take_profit
        )
        
        state.positions.append(pos)
        state.trades_executed += 1
    
    def _check_risk_limits(
        self,
        state: StrategyState,
        candle: SimulatedCandle,
        phase: str
    ):
        """Check for risk limit breaches"""
        
        # Current drawdown check
        if state.peak_capital > 0:
            current_dd = (state.peak_capital - state.current_capital) / state.peak_capital
            
            if current_dd > 0.15 and phase == "SHOCK":
                state.risk_breaches += 1
            
            if current_dd > 0.25:
                state.margin_calls += 1
    
    def _calculate_recovery_time(
        self,
        candles: List[SimulatedCandle],
        shock_start: int,
        shock_end: int
    ) -> int:
        """Calculate how many candles to recover from shock"""
        
        if shock_end >= len(candles):
            return 0
        
        # Find the shock low
        shock_low = min(c.close for c in candles[shock_start:shock_end])
        pre_shock_level = candles[shock_start - 1].close if shock_start > 0 else candles[0].close
        
        # Find recovery point
        for i, candle in enumerate(candles[shock_end:]):
            if candle.close >= pre_shock_level * 0.95:  # 95% recovery
                return i
        
        return len(candles) - shock_end  # Didn't fully recover
    
    async def _get_candles(
        self,
        symbol: str,
        timeframe: str,
        start_date: datetime,
        end_date: datetime
    ) -> List[Dict]:
        """Get candle data"""
        
        # Try MongoDB
        if self.db is not None:
            try:
                start_ts = int(start_date.timestamp() * 1000)
                end_ts = int(end_date.timestamp() * 1000)
                
                cursor = self.db.candles.find({
                    "symbol": symbol,
                    "timeframe": timeframe,
                    "timestamp": {"$gte": start_ts, "$lte": end_ts}
                }).sort("timestamp", 1)
                
                candles = list(cursor)
                if candles:
                    return candles
            except Exception:
                pass
        
        # Generate mock candles
        return self._generate_mock_candles(symbol, timeframe, start_date, end_date)
    
    def _generate_mock_candles(
        self,
        symbol: str,
        timeframe: str,
        start_date: datetime,
        end_date: datetime
    ) -> List[Dict]:
        """Generate mock candle data"""
        
        intervals = {"1m": 60, "5m": 300, "15m": 900, "1h": 3600, "4h": 14400, "1d": 86400}
        interval_seconds = intervals.get(timeframe, 3600)
        
        candles = []
        current_ts = start_date.timestamp()
        end_ts = end_date.timestamp()
        
        base_prices = {"BTC": 50000, "ETH": 3000, "SOL": 100}
        price = base_prices.get(symbol, 1000)
        
        while current_ts < end_ts:
            change = price * random.uniform(-0.02, 0.02)
            open_price = price
            close_price = price + change
            high_price = max(open_price, close_price) * (1 + random.uniform(0, 0.01))
            low_price = min(open_price, close_price) * (1 - random.uniform(0, 0.01))
            
            candles.append({
                "symbol": symbol,
                "timeframe": timeframe,
                "timestamp": int(current_ts * 1000),
                "open": open_price,
                "high": high_price,
                "low": low_price,
                "close": close_price,
                "volume": random.uniform(1000, 50000)
            })
            
            price = close_price
            current_ts += interval_seconds
        
        return candles
