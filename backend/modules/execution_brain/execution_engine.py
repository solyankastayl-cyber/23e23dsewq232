"""
Execution Brain Engine

PHASE 37 — Execution Brain

Core engine for intelligent trade execution planning.

Pipeline:
1. Receive decision from Hypothesis Engine
2. Get capital allocation from Portfolio Engine
3. Calculate position size with risk modifier
4. Calculate stop loss (ATR-based)
5. Calculate take profit (simulation expected_move)
6. Apply liquidity impact adjustment
7. Apply risk gate
8. Generate final execution plan
"""

import hashlib
from typing import Optional, Dict, Tuple, List
from datetime import datetime, timezone

from .execution_types import (
    ExecutionPlan,
    CapitalInput,
    DecisionInput,
    ExecutionSummary,
    ExecutionType,
    RiskLevel,
    RISK_MODIFIERS,
    STOP_MULTIPLIERS,
    MIN_CONFIDENCE_THRESHOLD,
)


# ══════════════════════════════════════════════════════════════
# Execution Brain Engine
# ══════════════════════════════════════════════════════════════

class ExecutionBrainEngine:
    """
    Execution Brain Engine — PHASE 37
    
    Intelligent execution layer that bridges research and execution.
    """
    
    def __init__(self):
        self._plans: Dict[str, List[ExecutionPlan]] = {}
        self._active: Dict[str, ExecutionPlan] = {}
    
    # ═══════════════════════════════════════════════════════════
    # 1. Strategy Mapping
    # ═══════════════════════════════════════════════════════════
    
    def map_strategy(self, hypothesis_type: str) -> str:
        """
        Map hypothesis type to trading strategy.
        """
        mapping = {
            "BULLISH_CONTINUATION": "MOMENTUM_TRADING",
            "BEARISH_CONTINUATION": "MOMENTUM_TRADING",
            "BREAKOUT_FORMING": "BREAKOUT_TRADING",
            "RANGE_MEAN_REVERSION": "RANGE_TRADING",
            "VOLATILITY_EXPANSION": "VOLATILITY_TRADING",
            "NO_EDGE": "MEAN_REVERSION",
        }
        return mapping.get(hypothesis_type, "MOMENTUM_TRADING")
    
    # ═══════════════════════════════════════════════════════════
    # 2. Position Size Calculation
    # ═══════════════════════════════════════════════════════════
    
    def calculate_position_size(
        self,
        portfolio_capital: float,
        allocation_weight: float,
        risk_modifier: float,
    ) -> float:
        """
        Calculate position size.
        
        Formula:
        position_size = portfolio_capital × allocation_weight × risk_modifier
        """
        size = portfolio_capital * allocation_weight * risk_modifier
        return round(max(size, 0), 2)
    
    def get_risk_modifier(self, risk_level: str) -> float:
        """Get risk modifier for position sizing."""
        return RISK_MODIFIERS.get(risk_level, 0.7)
    
    # ═══════════════════════════════════════════════════════════
    # 3. Stop Loss Calculation
    # ═══════════════════════════════════════════════════════════
    
    def calculate_stop_loss(
        self,
        entry_price: float,
        direction: str,
        atr: float,
        stop_type: str = "NORMAL",
    ) -> float:
        """
        Calculate stop loss using ATR.
        
        Formula:
        stop_loss = entry_price ± ATR × stop_multiplier
        """
        multiplier = STOP_MULTIPLIERS.get(stop_type, 2.0)
        atr_distance = atr * multiplier
        
        if direction == "LONG":
            stop = entry_price - atr_distance
        else:
            stop = entry_price + atr_distance
        
        return round(max(stop, 0.01), 2)
    
    def get_atr(self, symbol: str) -> float:
        """Get ATR from market data."""
        try:
            from core.database import get_database
            db = get_database()
            if db:
                # Get recent candles
                candles = list(db.candles.find(
                    {"symbol": symbol},
                    {"_id": 0, "high": 1, "low": 1, "close": 1}
                ).sort("timestamp", -1).limit(14))
                
                if len(candles) >= 14:
                    trs = []
                    for i in range(len(candles) - 1):
                        high = candles[i]["high"]
                        low = candles[i]["low"]
                        prev_close = candles[i + 1]["close"]
                        tr = max(high - low, abs(high - prev_close), abs(low - prev_close))
                        trs.append(tr)
                    return sum(trs) / len(trs)
        except Exception:
            pass
        
        # Fallback: estimate ATR as 2% of price
        price = self._get_current_price(symbol)
        return price * 0.02
    
    def _get_current_price(self, symbol: str) -> float:
        """Get current price."""
        try:
            from core.database import get_database
            db = get_database()
            if db:
                candle = db.candles.find_one(
                    {"symbol": symbol},
                    {"_id": 0, "close": 1},
                    sort=[("timestamp", -1)]
                )
                if candle:
                    return candle["close"]
        except Exception:
            pass
        
        prices = {"BTC": 100000, "ETH": 3500, "SOL": 150}
        return prices.get(symbol.upper(), 100)
    
    # ═══════════════════════════════════════════════════════════
    # 4. Take Profit Calculation
    # ═══════════════════════════════════════════════════════════
    
    def calculate_take_profit(
        self,
        entry_price: float,
        direction: str,
        expected_move_pct: float,
    ) -> float:
        """
        Calculate take profit from simulation expected_move.
        
        Formula:
        take_profit = entry_price ± expected_move
        """
        move = entry_price * (expected_move_pct / 100)
        
        if direction == "LONG":
            target = entry_price + move
        else:
            target = entry_price - move
        
        return round(max(target, 0.01), 2)
    
    def get_expected_move(self, symbol: str, direction: str) -> float:
        """Get expected move from Simulation Engine."""
        try:
            from modules.market_simulation import get_simulation_engine
            engine = get_simulation_engine()
            result = engine.simulate(symbol, horizon_hours=24)
            if result:
                return abs(result.expected_move_percent)
        except Exception:
            pass
        
        # Fallback: 3% expected move
        return 3.0
    
    # ═══════════════════════════════════════════════════════════
    # 5. Risk Level Classification
    # ═══════════════════════════════════════════════════════════
    
    def classify_risk_level(
        self,
        confidence: float,
        reliability: float,
        regime_stability: str = "STABLE",
    ) -> RiskLevel:
        """
        Classify risk level based on hypothesis quality.
        """
        combined = (confidence + reliability) / 2
        
        # Adjust for regime instability
        if regime_stability in ("UNSTABLE", "ACTIVE_TRANSITION"):
            combined *= 0.8
        
        if combined >= 0.70:
            return "LOW"
        elif combined >= 0.55:
            return "MEDIUM"
        elif combined >= 0.40:
            return "HIGH"
        else:
            return "EXTREME"
    
    # ═══════════════════════════════════════════════════════════
    # 6. Risk Reward Calculation
    # ═══════════════════════════════════════════════════════════
    
    def calculate_risk_reward(
        self,
        entry_price: float,
        stop_loss: float,
        take_profit: float,
        direction: str,
    ) -> float:
        """
        Calculate risk/reward ratio.
        """
        if direction == "LONG":
            risk = entry_price - stop_loss
            reward = take_profit - entry_price
        else:
            risk = stop_loss - entry_price
            reward = entry_price - take_profit
        
        if risk <= 0:
            return 0.0
        
        return round(reward / risk, 2)
    
    # ═══════════════════════════════════════════════════════════
    # 7. Risk Gate
    # ═══════════════════════════════════════════════════════════
    
    def apply_risk_gate(
        self,
        risk_level: RiskLevel,
        confidence: float,
    ) -> Tuple[bool, str]:
        """
        Apply final safety gate.
        
        Blocks execution if:
        - risk_level = EXTREME
        - confidence < 0.45
        """
        if risk_level == "EXTREME":
            return False, "Risk level EXTREME - execution blocked"
        
        if confidence < MIN_CONFIDENCE_THRESHOLD:
            return False, f"Confidence {confidence:.2f} below threshold {MIN_CONFIDENCE_THRESHOLD}"
        
        return True, "Passed risk gate"
    
    # ═══════════════════════════════════════════════════════════
    # 8. Main Plan Generation
    # ═══════════════════════════════════════════════════════════
    
    def generate_plan(
        self,
        symbol: str,
        hypothesis_type: str,
        direction: str,
        confidence: float,
        reliability: float,
        portfolio_capital: float = 100000.0,
        allocation_weight: float = 0.10,
        target_price: Optional[float] = None,
        invalidation_price: Optional[float] = None,
    ) -> ExecutionPlan:
        """
        Generate complete execution plan.
        
        Main entry point for Execution Brain.
        """
        symbol = symbol.upper()
        direction = direction.upper()
        
        # 1. Map strategy
        strategy = self.map_strategy(hypothesis_type)
        
        # 2. Get current price
        entry_price = self._get_current_price(symbol)
        
        # 3. Classify risk
        risk_level = self.classify_risk_level(confidence, reliability)
        risk_modifier = self.get_risk_modifier(risk_level)
        
        # 4. Calculate position size
        position_size = self.calculate_position_size(
            portfolio_capital, allocation_weight, risk_modifier
        )
        
        # 5. Calculate stop loss
        atr = self.get_atr(symbol)
        stop_loss = self.calculate_stop_loss(entry_price, direction, atr)
        
        # 6. Calculate take profit
        if target_price:
            take_profit = target_price
        else:
            expected_move = self.get_expected_move(symbol, direction)
            take_profit = self.calculate_take_profit(entry_price, direction, expected_move)
        
        # 7. Invalidation level
        invalidation = invalidation_price or stop_loss
        
        # 8. Risk/reward
        risk_reward = self.calculate_risk_reward(entry_price, stop_loss, take_profit, direction)
        
        # 9. Initial execution type (will be adjusted by Liquidity Impact)
        execution_type = "LIMIT"
        
        # 10. Apply Liquidity Impact adjustment
        adjusted_size = position_size
        type_changed = False
        size_reduction = 0.0
        impact_adjusted = False
        
        try:
            from modules.liquidity_impact import get_liquidity_impact_engine
            impact_engine = get_liquidity_impact_engine()
            
            side = "BUY" if direction == "LONG" else "SELL"
            adjustment = impact_engine.adjust_execution_plan(
                symbol, position_size, side, execution_type
            )
            
            adjusted_size = adjustment["adjusted_size_usd"]
            execution_type = adjustment["adjusted_execution_type"]
            type_changed = adjustment["type_changed"]
            size_reduction = adjustment["size_reduction_pct"]
            impact_adjusted = True
        except Exception:
            pass
        
        # 11. Apply risk gate
        approved, gate_reason = self.apply_risk_gate(risk_level, confidence)
        status = "APPROVED" if approved else "BLOCKED"
        blocked_reason = "" if approved else gate_reason
        
        # 12. Generate reason
        reason = self._generate_reason(
            strategy, direction, risk_level, position_size, adjusted_size, status
        )
        
        plan = ExecutionPlan(
            symbol=symbol,
            strategy=strategy,
            hypothesis_type=hypothesis_type,
            direction=direction,
            position_size_usd=position_size,
            position_size_adjusted=adjusted_size,
            capital_allocation_weight=allocation_weight,
            entry_price=entry_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            invalidation_level=invalidation,
            risk_level=risk_level,
            risk_modifier=risk_modifier,
            risk_reward_ratio=risk_reward,
            execution_type=execution_type,
            execution_type_original="LIMIT",
            confidence=confidence,
            reliability=reliability,
            status=status,
            blocked_reason=blocked_reason,
            impact_adjusted=impact_adjusted,
            size_reduction_pct=size_reduction,
            type_changed=type_changed,
            reason=reason,
        )
        
        # Cache
        self._store_plan(symbol, plan)
        
        return plan
    
    def _generate_reason(
        self,
        strategy: str,
        direction: str,
        risk: str,
        original_size: float,
        adjusted_size: float,
        status: str,
    ) -> str:
        """Generate explanation string."""
        return f"{strategy} {direction}; Risk={risk}; Size ${original_size:,.0f}→${adjusted_size:,.0f}; Status={status}"
    
    # ═══════════════════════════════════════════════════════════
    # 9. Storage and Cache
    # ═══════════════════════════════════════════════════════════
    
    def _store_plan(self, symbol: str, plan: ExecutionPlan) -> None:
        """Store plan in cache."""
        if symbol not in self._plans:
            self._plans[symbol] = []
        self._plans[symbol].append(plan)
        self._active[symbol] = plan
    
    def get_active_plan(self, symbol: str) -> Optional[ExecutionPlan]:
        """Get active plan for symbol."""
        return self._active.get(symbol.upper())
    
    def get_history(self, symbol: str, limit: int = 100) -> List[ExecutionPlan]:
        """Get plan history."""
        history = self._plans.get(symbol.upper(), [])
        return sorted(history, key=lambda p: p.timestamp, reverse=True)[:limit]
    
    # ═══════════════════════════════════════════════════════════
    # 10. Summary
    # ═══════════════════════════════════════════════════════════
    
    def generate_summary(self, symbol: str) -> ExecutionSummary:
        """Generate summary statistics."""
        symbol = symbol.upper()
        history = self._plans.get(symbol, [])
        active = self._active.get(symbol)
        
        if not history:
            return ExecutionSummary(symbol=symbol)
        
        total = len(history)
        approved = sum(1 for p in history if p.status == "APPROVED")
        blocked = sum(1 for p in history if p.status == "BLOCKED")
        executed = sum(1 for p in history if p.status == "EXECUTED")
        
        # Risk distribution
        low_risk = sum(1 for p in history if p.risk_level == "LOW")
        medium_risk = sum(1 for p in history if p.risk_level == "MEDIUM")
        high_risk = sum(1 for p in history if p.risk_level == "HIGH")
        extreme_risk = sum(1 for p in history if p.risk_level == "EXTREME")
        
        # Execution type distribution
        market = sum(1 for p in history if p.execution_type == "MARKET")
        limit = sum(1 for p in history if p.execution_type == "LIMIT")
        twap = sum(1 for p in history if p.execution_type == "TWAP")
        iceberg = sum(1 for p in history if p.execution_type == "ICEBERG")
        
        # Averages
        avg_conf = sum(p.confidence for p in history) / total
        avg_rr = sum(p.risk_reward_ratio for p in history) / total
        
        return ExecutionSummary(
            symbol=symbol,
            has_active_plan=active is not None,
            current_direction=active.direction if active else "",
            current_status=active.status if active else "",
            total_plans=total,
            approved_count=approved,
            blocked_count=blocked,
            executed_count=executed,
            low_risk_count=low_risk,
            medium_risk_count=medium_risk,
            high_risk_count=high_risk,
            extreme_risk_count=extreme_risk,
            market_count=market,
            limit_count=limit,
            twap_count=twap,
            iceberg_count=iceberg,
            avg_confidence=round(avg_conf, 4),
            avg_risk_reward=round(avg_rr, 2),
            last_updated=datetime.now(timezone.utc),
        )


# ══════════════════════════════════════════════════════════════
# Singleton
# ══════════════════════════════════════════════════════════════

_execution_engine: Optional[ExecutionBrainEngine] = None


def get_execution_brain_engine() -> ExecutionBrainEngine:
    """Get singleton instance of ExecutionBrainEngine."""
    global _execution_engine
    if _execution_engine is None:
        _execution_engine = ExecutionBrainEngine()
    return _execution_engine
