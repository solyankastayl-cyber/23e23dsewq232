"""
Forward Engine
==============

Main forward simulation engine (PHASE 2.3)
"""

import time
import uuid
import random
from typing import Dict, List, Optional, Any

from .forward_types import (
    SimulationConfig,
    SimulationRun,
    SimulatedTrade,
    SimulationStatus,
    TradeDirection,
    TradeStatus,
    Candle,
    MarketScenario
)
from .market_replay_engine import market_replay_engine
from .forward_broker_simulator import broker_simulator, OrderRequest
from .forward_position_manager import ForwardPositionManager
from .forward_metrics_engine import forward_metrics_engine


class ForwardEngine:
    """
    Main forward simulation engine.
    
    Orchestrates:
    1. Market replay
    2. Strategy signal generation
    3. Order execution
    4. Position management
    5. Metrics calculation
    """
    
    def __init__(self):
        # Strategy baselines (from Trading Doctrine)
        self._strategy_configs = {
            "TREND_CONFIRMATION": {
                "ideal_regimes": ["TRENDING"],
                "stop_atr_mult": 2.0,
                "target_atr_mult": 4.0,
                "signal_rate": 0.08,  # 8% chance per bar
                "base_win_rate": 0.52
            },
            "MOMENTUM_BREAKOUT": {
                "ideal_regimes": ["TRENDING", "HIGH_VOLATILITY"],
                "stop_atr_mult": 1.5,
                "target_atr_mult": 3.0,
                "signal_rate": 0.12,
                "base_win_rate": 0.45
            },
            "MEAN_REVERSION": {
                "ideal_regimes": ["RANGE", "LOW_VOLATILITY"],
                "stop_atr_mult": 1.0,
                "target_atr_mult": 2.0,
                "signal_rate": 0.15,
                "base_win_rate": 0.58
            }
        }
        
        print("[ForwardEngine] Initialized (PHASE 2.3)")
    
    def run_simulation(
        self,
        config: SimulationConfig,
        progress_callback: Optional[callable] = None
    ) -> SimulationRun:
        """
        Run complete forward simulation.
        """
        
        run = SimulationRun(
            run_id=f"fwd_{uuid.uuid4().hex[:12]}",
            status=SimulationStatus.RUNNING,
            config=config,
            started_at=int(time.time() * 1000)
        )
        
        try:
            # Initialize position manager
            position_manager = ForwardPositionManager()
            position_manager.reset()
            
            # Generate candles
            candles = market_replay_engine.generate_candles(
                scenario=config.scenario,
                count=config.candle_count,
                timeframe=config.timeframe
            )
            
            run.total_bars = len(candles)
            
            # Track capital
            current_capital = config.initial_capital
            
            # Process each candle
            history = []
            
            for bar_index, candle in enumerate(candles):
                history.append(candle)
                run.current_bar = bar_index
                
                # Update progress
                run.progress_pct = (bar_index / run.total_bars) * 100
                if progress_callback:
                    progress_callback(run.progress_pct)
                
                # Need enough history for indicators
                if len(history) < 30:
                    continue
                
                # Get current regime
                regime = market_replay_engine.get_current_regime(history)
                
                # Get indicators
                indicators = market_replay_engine.calculate_indicators(history)
                atr = indicators.get("atr", candle.close * 0.02)
                
                # Update open positions (check stops/targets)
                closed_trades = position_manager.update_positions(
                    candle=candle,
                    bar_index=bar_index,
                    config=config
                )
                
                # Update capital from closed trades
                for trade in closed_trades:
                    current_capital += trade.pnl
                
                # Update trailing stops
                for pos in position_manager.get_open_positions():
                    position_manager.update_trailing_stop(pos.trade_id, candle, atr)
                
                # Check if can open new position
                if not position_manager.can_open_new_position(current_capital):
                    continue
                
                # Generate signals and potentially open position
                signal = self._generate_signal(
                    candle=candle,
                    regime=regime,
                    indicators=indicators,
                    config=config
                )
                
                if signal:
                    # Calculate position size
                    stop_distance = atr * signal["stop_mult"]
                    
                    if signal["direction"] == TradeDirection.LONG:
                        entry_price = candle.close
                        stop_price = entry_price - stop_distance
                        target_price = entry_price + (atr * signal["target_mult"])
                    else:
                        entry_price = candle.close
                        stop_price = entry_price + stop_distance
                        target_price = entry_price - (atr * signal["target_mult"])
                    
                    position_size = broker_simulator.calculate_position_size(
                        capital=current_capital,
                        entry_price=entry_price,
                        stop_price=stop_price,
                        risk_pct=config.risk_per_trade_pct,
                        max_size_pct=config.max_position_size_pct
                    )
                    
                    if position_size > 0:
                        # Create order
                        order = OrderRequest(
                            symbol=config.symbol,
                            direction=signal["direction"],
                            size=position_size,
                            entry_price=entry_price,
                            stop_price=stop_price,
                            target_price=target_price,
                            strategy=signal["strategy"],
                            regime=regime,
                            execution_style=signal.get("execution_style", "AGGRESSIVE")
                        )
                        
                        # Execute order
                        success, trade = broker_simulator.execute_order(
                            order=order,
                            current_candle=candle,
                            config=config
                        )
                        
                        if success:
                            trade.timeframe = config.timeframe
                            trade.entry_bar = bar_index
                            position_manager.open_position(trade)
            
            # Close any remaining open positions at last candle
            final_candle = candles[-1]
            for pos in position_manager.get_open_positions():
                position_manager.close_position(
                    trade_id=pos.trade_id,
                    exit_price=final_candle.close,
                    status=TradeStatus.CLOSED,
                    exit_bar=len(candles) - 1,
                    config=config
                )
            
            # Get all trades
            all_trades = position_manager.get_all_trades()
            run.trades = all_trades
            
            # Build equity curve
            run.equity_curve = forward_metrics_engine.build_equity_curve(
                trades=all_trades,
                config=config,
                total_bars=len(candles)
            )
            
            # Calculate metrics
            run.metrics = forward_metrics_engine.calculate_metrics(
                trades=all_trades,
                equity_curve=run.equity_curve,
                config=config
            )
            
            run.status = SimulationStatus.COMPLETED
            run.progress_pct = 100.0
            
        except Exception as e:
            run.status = SimulationStatus.FAILED
            run.error = str(e)
        
        run.completed_at = int(time.time() * 1000)
        run.duration_ms = run.completed_at - run.started_at
        
        return run
    
    def _generate_signal(
        self,
        candle: Candle,
        regime: str,
        indicators: Dict[str, float],
        config: SimulationConfig
    ) -> Optional[Dict[str, Any]]:
        """
        Generate trading signal based on strategy selection.
        """
        
        # Select best strategy for regime
        if config.use_strategy_selection:
            strategy = self._select_strategy(regime, config.strategies)
        else:
            strategy = random.choice(config.strategies)
        
        strategy_config = self._strategy_configs.get(strategy)
        if not strategy_config:
            return None
        
        # Check if strategy should generate signal
        # Adjust signal rate based on regime compatibility
        signal_rate = strategy_config["signal_rate"]
        
        if regime in strategy_config["ideal_regimes"]:
            signal_rate *= 1.3  # More signals in ideal regime
        elif regime in ["TRANSITION"]:
            signal_rate *= 0.7  # Fewer signals in transition
        else:
            signal_rate *= 0.5  # Much fewer in wrong regime
        
        if random.random() > signal_rate:
            return None
        
        # Determine direction based on indicators
        rsi = indicators.get("rsi", 50)
        macd_hist = indicators.get("macdHist", 0)
        close = indicators.get("close", candle.close)
        sma20 = indicators.get("sma20", close)
        
        # Strategy-specific direction logic
        if strategy == "TREND_CONFIRMATION":
            # Trend following - go with the trend
            if close > sma20 and macd_hist > 0:
                direction = TradeDirection.LONG
            elif close < sma20 and macd_hist < 0:
                direction = TradeDirection.SHORT
            else:
                return None
                
        elif strategy == "MOMENTUM_BREAKOUT":
            # Momentum - strong moves
            if rsi > 60 and macd_hist > 0:
                direction = TradeDirection.LONG
            elif rsi < 40 and macd_hist < 0:
                direction = TradeDirection.SHORT
            else:
                return None
                
        elif strategy == "MEAN_REVERSION":
            # Mean reversion - fade extremes
            if rsi < 35:
                direction = TradeDirection.LONG
            elif rsi > 65:
                direction = TradeDirection.SHORT
            else:
                return None
        else:
            return None
        
        # Simulate win/loss outcome
        base_wr = strategy_config["base_win_rate"]
        
        # Adjust win rate by regime
        if regime in strategy_config["ideal_regimes"]:
            wr_modifier = 0.1
        else:
            wr_modifier = -0.15
        
        effective_wr = min(0.75, max(0.30, base_wr + wr_modifier))
        
        return {
            "strategy": strategy,
            "direction": direction,
            "stop_mult": strategy_config["stop_atr_mult"],
            "target_mult": strategy_config["target_atr_mult"],
            "win_rate": effective_wr,
            "execution_style": "AGGRESSIVE" if strategy == "MOMENTUM_BREAKOUT" else "SCALED"
        }
    
    def _select_strategy(
        self,
        regime: str,
        available_strategies: List[str]
    ) -> str:
        """
        Select best strategy for current regime.
        """
        
        # Regime rankings (from Trading Doctrine)
        regime_rankings = {
            "TRENDING": ["TREND_CONFIRMATION", "MOMENTUM_BREAKOUT", "MEAN_REVERSION"],
            "RANGE": ["MEAN_REVERSION", "TREND_CONFIRMATION", "MOMENTUM_BREAKOUT"],
            "HIGH_VOLATILITY": ["MOMENTUM_BREAKOUT", "TREND_CONFIRMATION", "MEAN_REVERSION"],
            "LOW_VOLATILITY": ["MEAN_REVERSION", "TREND_CONFIRMATION", "MOMENTUM_BREAKOUT"],
            "TRANSITION": ["TREND_CONFIRMATION", "MOMENTUM_BREAKOUT", "MEAN_REVERSION"]
        }
        
        rankings = regime_rankings.get(regime, ["TREND_CONFIRMATION"])
        
        # Return first available strategy from rankings
        for strategy in rankings:
            if strategy in available_strategies:
                return strategy
        
        return available_strategies[0] if available_strategies else "TREND_CONFIRMATION"
    
    def get_health(self) -> Dict[str, Any]:
        """Get engine health"""
        return {
            "module": "PHASE 2.3 Forward Simulation",
            "status": "healthy",
            "version": "1.0.0",
            "engines": {
                "marketReplay": "active",
                "broker": "active",
                "positionManager": "active",
                "metrics": "active"
            },
            "scenarios": [s.value for s in MarketScenario],
            "strategies": list(self._strategy_configs.keys()),
            "timestamp": int(time.time() * 1000)
        }


# Global singleton
forward_engine = ForwardEngine()
