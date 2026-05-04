"""
PHASE 6.3 - Monte Carlo Simulator
==================================
Core simulation engine with bootstrapping, shuffling, and noise injection.
"""

import random
import math
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import statistics

from .monte_types import TradeRecord, MonteCarloMethod


class MonteCarloSimulator:
    """
    Monte Carlo simulation engine.
    Generates thousands of alternative trade sequences.
    """
    
    def __init__(
        self,
        trades: List[TradeRecord],
        method: MonteCarloMethod = MonteCarloMethod.COMBINED,
        noise_level: float = 0.1
    ):
        self.original_trades = trades
        self.method = method
        self.noise_level = noise_level
        self._random_seed = random.randint(0, 100000)
    
    def simulate(self, iterations: int = 1000) -> List[List[TradeRecord]]:
        """
        Generate N alternative trade sequences.
        
        Returns list of trade sequences, each representing one simulation.
        """
        simulations = []
        
        for i in range(iterations):
            if self.method == MonteCarloMethod.BOOTSTRAP:
                sim = self._bootstrap(i)
            elif self.method == MonteCarloMethod.SHUFFLE:
                sim = self._shuffle(i)
            elif self.method == MonteCarloMethod.NOISE_INJECTION:
                sim = self._inject_noise(i)
            else:  # COMBINED
                sim = self._combined(i)
            
            simulations.append(sim)
        
        return simulations
    
    def _bootstrap(self, seed_offset: int) -> List[TradeRecord]:
        """
        Bootstrap resampling - sample with replacement.
        Creates a new sequence of same length by randomly picking trades.
        """
        random.seed(self._random_seed + seed_offset)
        n = len(self.original_trades)
        
        resampled = []
        for j in range(n):
            trade = random.choice(self.original_trades)
            new_trade = TradeRecord(
                trade_id=f"{trade.trade_id}_bs_{j}",
                return_pct=trade.return_pct,
                duration_candles=trade.duration_candles,
                win=trade.win,
                risk_taken=trade.risk_taken
            )
            resampled.append(new_trade)
        
        return resampled
    
    def _shuffle(self, seed_offset: int) -> List[TradeRecord]:
        """
        Shuffle trade order - random permutation.
        Same trades, different sequence.
        """
        random.seed(self._random_seed + seed_offset + 10000)
        
        shuffled = []
        for j, trade in enumerate(self.original_trades):
            new_trade = TradeRecord(
                trade_id=f"{trade.trade_id}_sh_{j}",
                return_pct=trade.return_pct,
                duration_candles=trade.duration_candles,
                win=trade.win,
                risk_taken=trade.risk_taken
            )
            shuffled.append(new_trade)
        
        random.shuffle(shuffled)
        return shuffled
    
    def _inject_noise(self, seed_offset: int) -> List[TradeRecord]:
        """
        Add random noise to returns.
        Simulates execution variance and slippage.
        """
        random.seed(self._random_seed + seed_offset + 20000)
        
        noisy = []
        for j, trade in enumerate(self.original_trades):
            # Add gaussian noise
            noise = random.gauss(0, self.noise_level * abs(trade.return_pct) + 0.001)
            new_return = trade.return_pct + noise
            
            new_trade = TradeRecord(
                trade_id=f"{trade.trade_id}_ni_{j}",
                return_pct=new_return,
                duration_candles=trade.duration_candles,
                win=new_return > 0,
                risk_taken=trade.risk_taken
            )
            noisy.append(new_trade)
        
        return noisy
    
    def _combined(self, seed_offset: int) -> List[TradeRecord]:
        """
        Combine all methods for maximum variance exploration.
        """
        random.seed(self._random_seed + seed_offset + 30000)
        
        # Step 1: Bootstrap
        n = len(self.original_trades)
        resampled = []
        for j in range(n):
            trade = random.choice(self.original_trades)
            resampled.append(trade)
        
        # Step 2: Shuffle
        random.shuffle(resampled)
        
        # Step 3: Add noise
        combined = []
        for j, trade in enumerate(resampled):
            noise = random.gauss(0, self.noise_level * abs(trade.return_pct) + 0.001)
            new_return = trade.return_pct + noise
            
            new_trade = TradeRecord(
                trade_id=f"{trade.trade_id}_cb_{j}",
                return_pct=new_return,
                duration_candles=trade.duration_candles,
                win=new_return > 0,
                risk_taken=trade.risk_taken
            )
            combined.append(new_trade)
        
        return combined
    
    def get_return_series(self, trades: List[TradeRecord]) -> List[float]:
        """Extract return series from trades"""
        return [t.return_pct for t in trades]
    
    def calculate_cumulative_returns(self, returns: List[float]) -> List[float]:
        """Calculate cumulative equity curve from returns"""
        equity = [1.0]  # Start with 1.0 (100%)
        
        for ret in returns:
            new_equity = equity[-1] * (1 + ret)
            equity.append(new_equity)
        
        return equity
    
    @staticmethod
    def generate_mock_trades(
        n_trades: int = 100,
        win_rate: float = 0.55,
        avg_win: float = 0.02,
        avg_loss: float = 0.015,
        strategy_id: str = "MOCK"
    ) -> List[TradeRecord]:
        """Generate mock trade history for testing"""
        trades = []
        
        for i in range(n_trades):
            is_win = random.random() < win_rate
            
            if is_win:
                # Wins vary around avg_win
                return_pct = random.gauss(avg_win, avg_win * 0.3)
                return_pct = max(0.001, return_pct)  # Min positive
            else:
                # Losses vary around -avg_loss
                return_pct = -random.gauss(avg_loss, avg_loss * 0.3)
                return_pct = min(-0.001, return_pct)  # Min negative
            
            trade = TradeRecord(
                trade_id=f"{strategy_id}_{i}",
                return_pct=return_pct,
                duration_candles=random.randint(1, 20),
                win=is_win,
                risk_taken=random.uniform(0.01, 0.03)
            )
            trades.append(trade)
        
        return trades
