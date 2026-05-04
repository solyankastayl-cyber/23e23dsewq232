"""
False Signal Engine
===================

Detects false signals in trades (PHASE 2.2)
"""

import time
import random
import uuid
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

from .failure_types import FalseSignal, FailureSeverity


@dataclass
class TradeData:
    """Trade data for analysis"""
    trade_id: str
    strategy: str
    symbol: str
    timeframe: str
    regime: str
    direction: str
    entry_price: float
    exit_price: float
    stop_price: float
    r_multiple: float
    duration_bars: int
    structure_intact: bool


class FalseSignalEngine:
    """
    Detects false signals in trades.
    
    False signal indicators:
    - loss < -1R (exceeded stop)
    - duration extremely short (< 3 bars)
    - structure break immediately after entry
    - immediate reversal
    """
    
    def __init__(self):
        # Thresholds
        self._min_duration_bars = 3
        self._severe_loss_threshold = -1.5  # R
        
        print("[FalseSignalEngine] Initialized (PHASE 2.2)")
    
    def detect(self, trade: TradeData) -> Optional[FalseSignal]:
        """
        Detect if trade was a false signal.
        """
        
        is_false = False
        indicators = {
            "loss_exceeded_1r": False,
            "duration_too_short": False,
            "structure_break_after_entry": False,
            "immediate_reversal": False
        }
        notes = []
        
        # Check 1: Loss exceeded 1R
        if trade.r_multiple < -1.0:
            indicators["loss_exceeded_1r"] = True
            is_false = True
            notes.append(f"Loss exceeded 1R: {trade.r_multiple:.2f}R")
        
        # Check 2: Duration too short
        if trade.duration_bars < self._min_duration_bars:
            indicators["duration_too_short"] = True
            is_false = True
            notes.append(f"Duration too short: {trade.duration_bars} bars")
        
        # Check 3: Structure break after entry
        if not trade.structure_intact and trade.r_multiple < 0:
            indicators["structure_break_after_entry"] = True
            is_false = True
            notes.append("Structure broke immediately after entry")
        
        # Check 4: Immediate reversal (price moved against > 50% of stop distance)
        if trade.direction == "LONG":
            stop_distance = trade.entry_price - trade.stop_price
            adverse_move = trade.entry_price - min(trade.exit_price, trade.entry_price)
        else:
            stop_distance = trade.stop_price - trade.entry_price
            adverse_move = max(trade.exit_price, trade.entry_price) - trade.entry_price
        
        if stop_distance > 0 and adverse_move / stop_distance > 0.5 and trade.duration_bars < 5:
            indicators["immediate_reversal"] = True
            is_false = True
            notes.append("Immediate adverse price movement")
        
        if not is_false:
            return None
        
        # Determine severity
        severity = FailureSeverity.LOW
        indicator_count = sum(1 for v in indicators.values() if v)
        
        if indicator_count >= 3 or trade.r_multiple < self._severe_loss_threshold:
            severity = FailureSeverity.CRITICAL
        elif indicator_count >= 2:
            severity = FailureSeverity.HIGH
        elif trade.r_multiple < -1.0:
            severity = FailureSeverity.MEDIUM
        
        return FalseSignal(
            trade_id=trade.trade_id,
            strategy=trade.strategy,
            symbol=trade.symbol,
            timeframe=trade.timeframe,
            regime=trade.regime,
            entry_price=trade.entry_price,
            exit_price=trade.exit_price,
            direction=trade.direction,
            r_multiple=trade.r_multiple,
            loss_exceeded_1r=indicators["loss_exceeded_1r"],
            duration_too_short=indicators["duration_too_short"],
            structure_break_after_entry=indicators["structure_break_after_entry"],
            immediate_reversal=indicators["immediate_reversal"],
            severity=severity,
            notes=notes,
            detected_at=int(time.time() * 1000)
        )
    
    def scan_trades(
        self,
        trades: List[TradeData]
    ) -> List[FalseSignal]:
        """Scan multiple trades for false signals"""
        
        false_signals = []
        for trade in trades:
            signal = self.detect(trade)
            if signal:
                false_signals.append(signal)
        
        return false_signals
    
    def generate_simulated_trades(
        self,
        strategy: str,
        symbol: str,
        timeframe: str,
        regime: str,
        count: int = 50
    ) -> List[TradeData]:
        """Generate simulated trades for testing"""
        
        trades = []
        
        # False signal rate based on strategy-regime compatibility
        false_signal_rates = {
            ("TREND_CONFIRMATION", "RANGE"): 0.25,
            ("TREND_CONFIRMATION", "TRENDING"): 0.08,
            ("MOMENTUM_BREAKOUT", "RANGE"): 0.30,
            ("MOMENTUM_BREAKOUT", "LOW_VOLATILITY"): 0.28,
            ("MEAN_REVERSION", "TRENDING"): 0.35,
            ("MEAN_REVERSION", "HIGH_VOLATILITY"): 0.30,
            ("MEAN_REVERSION", "RANGE"): 0.10
        }
        
        base_false_rate = false_signal_rates.get(
            (strategy, regime),
            0.12  # Default rate
        )
        
        for i in range(count):
            is_false = random.random() < base_false_rate
            
            if is_false:
                # Generate a false signal trade
                r_multiple = random.uniform(-2.0, -0.5)
                duration = random.randint(1, 4)
                structure_intact = random.random() > 0.6
            else:
                # Generate normal trade
                r_multiple = random.uniform(-1.0, 3.0)
                duration = random.randint(5, 50)
                structure_intact = random.random() > 0.15
            
            entry_price = 100.0
            stop_distance = 2.0
            direction = random.choice(["LONG", "SHORT"])
            
            if direction == "LONG":
                stop_price = entry_price - stop_distance
                exit_price = entry_price + (r_multiple * stop_distance)
            else:
                stop_price = entry_price + stop_distance
                exit_price = entry_price - (r_multiple * stop_distance)
            
            trades.append(TradeData(
                trade_id=f"trade_{uuid.uuid4().hex[:8]}",
                strategy=strategy,
                symbol=symbol,
                timeframe=timeframe,
                regime=regime,
                direction=direction,
                entry_price=entry_price,
                exit_price=exit_price,
                stop_price=stop_price,
                r_multiple=r_multiple,
                duration_bars=duration,
                structure_intact=structure_intact
            ))
        
        return trades
    
    def calculate_false_signal_rate(
        self,
        false_signals: List[FalseSignal],
        total_trades: int
    ) -> float:
        """Calculate false signal rate"""
        if total_trades == 0:
            return 0.0
        return len(false_signals) / total_trades
    
    def find_clusters(
        self,
        false_signals: List[FalseSignal]
    ) -> List[Dict[str, Any]]:
        """Find clusters of false signals"""
        
        # Group by strategy + regime
        clusters = {}
        for sig in false_signals:
            key = f"{sig.strategy}:{sig.regime}"
            if key not in clusters:
                clusters[key] = {
                    "strategy": sig.strategy,
                    "regime": sig.regime,
                    "count": 0,
                    "avgLoss": 0.0,
                    "signals": []
                }
            clusters[key]["count"] += 1
            clusters[key]["avgLoss"] += sig.r_multiple
            clusters[key]["signals"].append(sig.trade_id)
        
        # Calculate averages
        result = []
        for key, data in clusters.items():
            if data["count"] > 0:
                data["avgLoss"] = round(data["avgLoss"] / data["count"], 2)
            result.append(data)
        
        # Sort by count
        result.sort(key=lambda x: x["count"], reverse=True)
        
        return result


# Global singleton
false_signal_engine = FalseSignalEngine()
