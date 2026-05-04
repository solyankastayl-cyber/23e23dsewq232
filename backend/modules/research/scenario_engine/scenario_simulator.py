"""
PHASE 6.2 - Scenario Simulator
===============================
Modifies market data to simulate stress scenarios.
"""

import random
import math
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

from .scenario_types import ScenarioDefinition, ShockParameters, ScenarioType


@dataclass
class SimulatedCandle:
    """Candle after scenario modification"""
    timestamp: int
    open: float
    high: float
    low: float
    close: float
    volume: float
    
    # Original values for comparison
    original_close: float
    
    # Simulation metadata
    shock_applied: bool = False
    shock_phase: str = "NORMAL"  # NORMAL, SHOCK, RECOVERY
    
    def to_dict(self) -> Dict:
        return {
            "timestamp": self.timestamp,
            "open": round(self.open, 2),
            "high": round(self.high, 2),
            "low": round(self.low, 2),
            "close": round(self.close, 2),
            "volume": round(self.volume, 2),
            "original_close": round(self.original_close, 2),
            "shock_applied": self.shock_applied,
            "shock_phase": self.shock_phase
        }


@dataclass
class SimulatedOrderbook:
    """Orderbook under scenario conditions"""
    bid_price: float
    ask_price: float
    spread_pct: float
    bid_depth: float
    ask_depth: float
    liquidity_score: float  # 0-1
    
    def to_dict(self) -> Dict:
        return {
            "bid_price": round(self.bid_price, 2),
            "ask_price": round(self.ask_price, 2),
            "spread_pct": round(self.spread_pct, 4),
            "bid_depth": round(self.bid_depth, 2),
            "ask_depth": round(self.ask_depth, 2),
            "liquidity_score": round(self.liquidity_score, 3)
        }


class ScenarioSimulator:
    """
    Simulates market conditions under stress scenarios.
    Modifies price, volume, liquidity, and other market data.
    """
    
    def __init__(self, scenario: ScenarioDefinition):
        self.scenario = scenario
        self.shock = scenario.shock_parameters
        self.current_candle_idx = 0
        self.shock_start_idx: Optional[int] = None
        self.price_offset = 0.0  # Cumulative price change
        self._random_seed = random.randint(0, 100000)
    
    def simulate_candles(
        self,
        original_candles: List[Dict],
        shock_start_candle: int = 10
    ) -> List[SimulatedCandle]:
        """
        Apply scenario modifications to candle data
        
        Args:
            original_candles: Original OHLCV data
            shock_start_candle: Index where shock begins
        """
        self.shock_start_idx = shock_start_candle
        simulated = []
        
        shock_end_idx = shock_start_candle + self.shock.shock_duration_candles
        recovery_end_idx = shock_end_idx + self.shock.recovery_candles
        
        for i, candle in enumerate(original_candles):
            self.current_candle_idx = i
            
            # Determine phase
            if i < shock_start_candle:
                phase = "NORMAL"
            elif i < shock_end_idx:
                phase = "SHOCK"
            elif i < recovery_end_idx:
                phase = "RECOVERY"
            else:
                phase = "NORMAL"
            
            simulated_candle = self._simulate_candle(candle, phase, i - shock_start_candle)
            simulated.append(simulated_candle)
        
        return simulated
    
    def _simulate_candle(
        self,
        candle: Dict,
        phase: str,
        phase_candle_idx: int
    ) -> SimulatedCandle:
        """Simulate a single candle based on phase"""
        
        original_close = candle['close']
        original_open = candle['open']
        original_high = candle['high']
        original_low = candle['low']
        original_volume = candle.get('volume', 1000)
        
        if phase == "NORMAL":
            return SimulatedCandle(
                timestamp=candle['timestamp'],
                open=original_open,
                high=original_high,
                low=original_low,
                close=original_close,
                volume=original_volume,
                original_close=original_close,
                shock_applied=False,
                shock_phase=phase
            )
        
        elif phase == "SHOCK":
            return self._apply_shock(candle, phase_candle_idx)
        
        elif phase == "RECOVERY":
            return self._apply_recovery(candle, phase_candle_idx)
        
        return SimulatedCandle(
            timestamp=candle['timestamp'],
            open=original_open,
            high=original_high,
            low=original_low,
            close=original_close,
            volume=original_volume,
            original_close=original_close,
            shock_applied=False,
            shock_phase=phase
        )
    
    def _apply_shock(self, candle: Dict, shock_candle_idx: int) -> SimulatedCandle:
        """Apply shock modifications to candle"""
        
        shock_duration = self.shock.shock_duration_candles
        progress = shock_candle_idx / max(1, shock_duration)  # 0 to 1
        
        # Price change - gradual application
        target_price_change = self.shock.price_change_pct / 100
        current_price_change = target_price_change * progress
        
        # Volatility increase
        vol_mult = self.shock.price_volatility_multiplier
        random.seed(self._random_seed + shock_candle_idx)
        vol_noise = random.gauss(0, 0.01) * (vol_mult - 1)
        
        # Apply to OHLC
        base_price = candle['close']
        price_factor = 1 + current_price_change + vol_noise
        
        new_close = base_price * price_factor
        new_open = candle['open'] * (1 + current_price_change * 0.8 + vol_noise)
        
        # Exaggerate high/low based on volatility
        range_expansion = vol_mult
        original_range = candle['high'] - candle['low']
        expanded_range = original_range * range_expansion
        
        if self.shock.price_change_pct < 0:
            # Crash - extend lows
            new_low = min(new_close, new_open) - expanded_range * 0.7
            new_high = max(new_close, new_open) + expanded_range * 0.3
        else:
            # Rally - extend highs
            new_high = max(new_close, new_open) + expanded_range * 0.7
            new_low = min(new_close, new_open) - expanded_range * 0.3
        
        # Volume spike
        new_volume = candle.get('volume', 1000) * self.shock.volume_spike_multiplier
        
        return SimulatedCandle(
            timestamp=candle['timestamp'],
            open=new_open,
            high=new_high,
            low=new_low,
            close=new_close,
            volume=new_volume,
            original_close=candle['close'],
            shock_applied=True,
            shock_phase="SHOCK"
        )
    
    def _apply_recovery(self, candle: Dict, recovery_candle_idx: int) -> SimulatedCandle:
        """Apply recovery modifications"""
        
        recovery_duration = self.shock.recovery_candles
        progress = recovery_candle_idx / max(1, recovery_duration)  # 0 to 1
        
        # Gradual return toward original levels
        remaining_shock = 1 - progress
        shock_effect = self.shock.price_change_pct / 100 * remaining_shock
        
        # Reduced volatility during recovery
        vol_mult = 1 + (self.shock.price_volatility_multiplier - 1) * remaining_shock * 0.5
        
        random.seed(self._random_seed + 1000 + recovery_candle_idx)
        vol_noise = random.gauss(0, 0.005) * vol_mult
        
        base_price = candle['close']
        price_factor = 1 + shock_effect + vol_noise
        
        new_close = base_price * price_factor
        new_open = candle['open'] * (1 + shock_effect * 0.9 + vol_noise)
        
        # Normal range with slight expansion
        original_range = candle['high'] - candle['low']
        expanded_range = original_range * vol_mult
        
        new_high = max(new_close, new_open) + expanded_range * 0.5
        new_low = min(new_close, new_open) - expanded_range * 0.5
        
        # Volume normalizing
        volume_mult = 1 + (self.shock.volume_spike_multiplier - 1) * remaining_shock
        new_volume = candle.get('volume', 1000) * volume_mult
        
        return SimulatedCandle(
            timestamp=candle['timestamp'],
            open=new_open,
            high=new_high,
            low=new_low,
            close=new_close,
            volume=new_volume,
            original_close=candle['close'],
            shock_applied=True,
            shock_phase="RECOVERY"
        )
    
    def simulate_orderbook(
        self,
        base_price: float,
        phase: str = "NORMAL"
    ) -> SimulatedOrderbook:
        """Simulate orderbook conditions under scenario"""
        
        # Base spread
        base_spread_pct = 0.001  # 0.1%
        
        if phase == "NORMAL":
            spread_mult = 1.0
            liquidity_mult = 1.0
        elif phase == "SHOCK":
            spread_mult = self.shock.spread_multiplier
            liquidity_mult = 1 - (self.shock.liquidity_reduction_pct / 100)
        elif phase == "RECOVERY":
            spread_mult = 1 + (self.shock.spread_multiplier - 1) * 0.5
            liquidity_mult = 1 - (self.shock.liquidity_reduction_pct / 200)
        else:
            spread_mult = 1.0
            liquidity_mult = 1.0
        
        actual_spread_pct = base_spread_pct * spread_mult
        half_spread = base_price * actual_spread_pct / 2
        
        bid_price = base_price - half_spread
        ask_price = base_price + half_spread
        
        # Depth
        base_depth = 100000  # Base USD depth
        bid_depth = base_depth * liquidity_mult * random.uniform(0.8, 1.2)
        ask_depth = base_depth * liquidity_mult * random.uniform(0.8, 1.2)
        
        # Liquidity score
        liquidity_score = liquidity_mult * (1 / spread_mult) * 0.8
        liquidity_score = max(0, min(1, liquidity_score))
        
        return SimulatedOrderbook(
            bid_price=bid_price,
            ask_price=ask_price,
            spread_pct=actual_spread_pct,
            bid_depth=bid_depth,
            ask_depth=ask_depth,
            liquidity_score=liquidity_score
        )
    
    def calculate_slippage(
        self,
        order_size_usd: float,
        side: str,  # "BUY" or "SELL"
        phase: str = "NORMAL"
    ) -> float:
        """Calculate expected slippage for an order"""
        
        base_slippage = 0.001  # 0.1% base
        
        if phase == "SHOCK":
            slippage_mult = self.shock.slippage_multiplier
        elif phase == "RECOVERY":
            slippage_mult = 1 + (self.shock.slippage_multiplier - 1) * 0.5
        else:
            slippage_mult = 1.0
        
        # Size impact
        size_factor = math.log10(max(1, order_size_usd / 10000)) * 0.1
        
        total_slippage = base_slippage * slippage_mult + size_factor
        
        return total_slippage
    
    def get_execution_latency(self, phase: str = "NORMAL") -> int:
        """Get expected execution latency in ms"""
        
        base_latency = 50  # 50ms base
        
        if phase == "SHOCK":
            return base_latency + self.shock.latency_ms
        elif phase == "RECOVERY":
            return base_latency + self.shock.latency_ms // 2
        
        return base_latency
