"""
PHASE 6.1 - Hypothesis Runner
==============================
Runs hypothesis tests on historical data.
"""

import os
import random
import uuid
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Tuple

from .hypothesis_types import (
    HypothesisDefinition, HypothesisRun, HypothesisResult,
    HypothesisCondition, ConditionOperator
)


class IndicatorSimulator:
    """
    Simulates indicator values for hypothesis testing.
    In production, would pull from real market data and indicator engines.
    """
    
    @staticmethod
    def get_indicator_value(indicator: str, candle: Dict, context: Dict) -> Any:
        """Get simulated indicator value for a candle"""
        
        # Map indicators to simulated values
        simulations = {
            # Volatility indicators
            "volatility_compression": lambda: random.uniform(0.3, 0.9),
            "bollinger_squeeze": lambda: random.random() > 0.7,
            
            # Volume indicators  
            "volume_confirmation": lambda: random.uniform(0.7, 2.0),
            "volume_ratio": lambda: random.uniform(0.5, 1.5),
            "volume_decline": lambda: random.uniform(0.0, 0.5),
            
            # Liquidity indicators
            "liquidity_sweep": lambda: random.random() > 0.8,
            "key_level_proximity": lambda: random.uniform(0.1, 2.0),
            "rejection_wick": lambda: random.uniform(0.2, 0.8),
            
            # Funding/derivatives
            "funding_rate_zscore": lambda: random.uniform(-2.5, 2.5),
            "open_interest_change": lambda: random.uniform(-15, 25),
            "open_interest_trend": lambda: random.uniform(-10, 15),
            "price_divergence": lambda: random.uniform(0.0, 1.0),
            
            # Structure indicators
            "bos_detected": lambda: random.random() > 0.75,
            "breakout_detected": lambda: random.random() > 0.7,
            
            # Trend indicators
            "trend_duration": lambda: random.randint(5, 50),
            "rsi_divergence": lambda: random.random() > 0.6,
            "momentum_weakening": lambda: random.uniform(0.2, 0.8),
            "weak_trend_strength": lambda: random.uniform(0.2, 0.8),
        }
        
        if indicator in simulations:
            return simulations[indicator]()
        
        # Default random value
        return random.uniform(0, 1)


class HypothesisRunner:
    """
    Runs hypothesis tests on historical data
    """
    
    def __init__(self, db=None):
        self.db = db
        self.indicator_sim = IndicatorSimulator()
    
    async def run_hypothesis(
        self,
        hypothesis: HypothesisDefinition,
        symbol: str,
        timeframe: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Tuple[HypothesisRun, List[Dict]]:
        """
        Run hypothesis test on historical data
        Returns: (run_info, trigger_events)
        """
        
        # Default date range: last 365 days
        if not end_date:
            end_date = datetime.now(timezone.utc)
        if not start_date:
            start_date = end_date - timedelta(days=365)
        
        # Create run record
        run = HypothesisRun(
            run_id=f"run_{uuid.uuid4().hex[:12]}",
            hypothesis_id=hypothesis.hypothesis_id,
            symbol=symbol,
            timeframe=timeframe,
            dataset_start=start_date,
            dataset_end=end_date,
            started_at=datetime.now(timezone.utc),
            status="RUNNING"
        )
        
        try:
            # Get candle data
            candles = await self._get_candles(symbol, timeframe, start_date, end_date)
            run.sample_size = len(candles)
            
            if not candles:
                run.status = "FAILED"
                run.error = "No candle data available"
                run.finished_at = datetime.now(timezone.utc)
                return run, []
            
            # Find trigger points
            triggers = []
            context = {"symbol": symbol, "timeframe": timeframe}
            
            for i, candle in enumerate(candles):
                if i < 20:  # Need lookback
                    continue
                
                # Check if all conditions are met
                if self._check_conditions(hypothesis.condition_set, candle, context):
                    trigger = self._create_trigger_event(hypothesis, candle, i, candles)
                    triggers.append(trigger)
            
            run.triggers_found = len(triggers)
            run.status = "COMPLETED"
            run.finished_at = datetime.now(timezone.utc)
            
            return run, triggers
            
        except Exception as e:
            run.status = "FAILED"
            run.error = str(e)
            run.finished_at = datetime.now(timezone.utc)
            return run, []
    
    async def _get_candles(
        self,
        symbol: str,
        timeframe: str,
        start_date: datetime,
        end_date: datetime
    ) -> List[Dict]:
        """Get candle data from MongoDB or generate mock data"""
        
        # Try to get from MongoDB
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
        
        # Generate mock candles if no data
        return self._generate_mock_candles(symbol, timeframe, start_date, end_date)
    
    def _generate_mock_candles(
        self,
        symbol: str,
        timeframe: str,
        start_date: datetime,
        end_date: datetime
    ) -> List[Dict]:
        """Generate mock candle data for testing"""
        
        # Determine candle interval
        intervals = {
            "1m": 60,
            "5m": 300,
            "15m": 900,
            "1h": 3600,
            "4h": 14400,
            "1d": 86400
        }
        interval_seconds = intervals.get(timeframe, 3600)
        
        candles = []
        current_ts = start_date.timestamp()
        end_ts = end_date.timestamp()
        
        # Start price
        base_prices = {"BTC": 50000, "ETH": 3000, "SOL": 100}
        price = base_prices.get(symbol, 1000)
        
        while current_ts < end_ts:
            # Random walk
            change = price * random.uniform(-0.03, 0.03)
            open_price = price
            close_price = price + change
            high_price = max(open_price, close_price) * (1 + random.uniform(0, 0.01))
            low_price = min(open_price, close_price) * (1 - random.uniform(0, 0.01))
            
            candle = {
                "symbol": symbol,
                "timeframe": timeframe,
                "timestamp": int(current_ts * 1000),
                "open": round(open_price, 2),
                "high": round(high_price, 2),
                "low": round(low_price, 2),
                "close": round(close_price, 2),
                "volume": random.uniform(1000, 50000)
            }
            candles.append(candle)
            
            price = close_price
            current_ts += interval_seconds
        
        return candles
    
    def _check_conditions(
        self,
        conditions: List[HypothesisCondition],
        candle: Dict,
        context: Dict
    ) -> bool:
        """Check if all conditions are met for a candle"""
        
        for condition in conditions:
            value = self.indicator_sim.get_indicator_value(
                condition.indicator, candle, context
            )
            
            if not self._evaluate_condition(condition, value):
                return False
        
        return True
    
    def _evaluate_condition(self, condition: HypothesisCondition, value: Any) -> bool:
        """Evaluate single condition"""
        
        op = condition.operator
        threshold = condition.value
        
        if op == ConditionOperator.GT:
            return value > threshold
        elif op == ConditionOperator.GTE:
            return value >= threshold
        elif op == ConditionOperator.LT:
            return value < threshold
        elif op == ConditionOperator.LTE:
            return value <= threshold
        elif op == ConditionOperator.EQ:
            return value == threshold
        elif op == ConditionOperator.NEQ:
            return value != threshold
        elif op == ConditionOperator.IN:
            return value in threshold
        elif op == ConditionOperator.NOT_IN:
            return value not in threshold
        elif op == ConditionOperator.BETWEEN:
            return threshold[0] <= value <= threshold[1]
        
        return False
    
    def _create_trigger_event(
        self,
        hypothesis: HypothesisDefinition,
        candle: Dict,
        index: int,
        all_candles: List[Dict]
    ) -> Dict:
        """Create trigger event with outcome"""
        
        # Look ahead to determine outcome
        horizon = hypothesis.expected_outcome.time_horizon_candles
        target_move = hypothesis.expected_outcome.target_move_pct
        direction = hypothesis.expected_outcome.direction
        
        entry_price = candle['close']
        outcome_price = entry_price
        
        # Check future candles for outcome
        if index + horizon < len(all_candles):
            future_candles = all_candles[index:index + horizon]
            
            if direction == "LONG":
                max_price = max(c['high'] for c in future_candles)
                min_price = min(c['low'] for c in future_candles)
                
                # Check if target hit
                target_price = entry_price * (1 + target_move / 100)
                stop_price = entry_price * (1 - target_move / 200)  # 0.5x target
                
                if max_price >= target_price:
                    outcome = "WIN"
                    exit_price = target_price
                    return_pct = target_move
                elif min_price <= stop_price:
                    outcome = "LOSS"
                    exit_price = stop_price
                    return_pct = -target_move / 2
                else:
                    # Closed at horizon end
                    exit_price = all_candles[index + horizon - 1]['close']
                    return_pct = ((exit_price - entry_price) / entry_price) * 100
                    outcome = "WIN" if return_pct > 0 else "LOSS"
                    
            elif direction == "SHORT":
                max_price = max(c['high'] for c in future_candles)
                min_price = min(c['low'] for c in future_candles)
                
                target_price = entry_price * (1 - target_move / 100)
                stop_price = entry_price * (1 + target_move / 200)
                
                if min_price <= target_price:
                    outcome = "WIN"
                    exit_price = target_price
                    return_pct = target_move
                elif max_price >= stop_price:
                    outcome = "LOSS"
                    exit_price = stop_price
                    return_pct = -target_move / 2
                else:
                    exit_price = all_candles[index + horizon - 1]['close']
                    return_pct = ((entry_price - exit_price) / entry_price) * 100
                    outcome = "WIN" if return_pct > 0 else "LOSS"
            else:
                outcome = "NEUTRAL"
                exit_price = entry_price
                return_pct = 0.0
        else:
            outcome = "INCOMPLETE"
            exit_price = candle['close']
            return_pct = 0.0
        
        return {
            "trigger_id": f"trig_{uuid.uuid4().hex[:8]}",
            "hypothesis_id": hypothesis.hypothesis_id,
            "timestamp": candle['timestamp'],
            "entry_price": round(entry_price, 2),
            "exit_price": round(exit_price, 2),
            "direction": direction,
            "outcome": outcome,
            "return_pct": round(return_pct, 4),
            "target_move_pct": target_move,
            "horizon_candles": horizon
        }
