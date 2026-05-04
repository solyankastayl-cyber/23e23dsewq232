"""Strategy Allocator V2 — Capital Allocation Engine

Week 4: Fund-level allocator

Flow:
1. Score signals (alpha + performance + execution + regime)
2. Filter execution-poor signals
3. Apply portfolio constraints
4. Calculate risk-based sizing
5. Return allocation decisions
"""

import logging
from typing import List, Dict, Any
from .types import Signal, StrategyStats
from .scoring import score_signal

logger = logging.getLogger(__name__)


class StrategyAllocatorV2:
    """Capital allocator (fund-level)."""
    
    # Portfolio constraints
    MAX_POSITIONS = 5
    RISK_PER_TRADE = 0.01  # 1% per trade
    MAX_HEAT = 0.7  # Max 70% capital at risk
    MIN_SCORE = 0.4  # Filter low-quality signals
    MAX_SLIPPAGE_BPS = 15  # Filter bad execution
    
    def allocate(
        self,
        signals: List[Signal],
        stats_map: Dict[str, StrategyStats],
        portfolio: Dict[str, Any],
        execution_map: Dict[str, Dict[str, Any]],
        regime: str
    ) -> List[Dict[str, Any]]:
        """
        Allocate capital to signals.
        
        Args:
            signals: List of trading signals
            stats_map: {strategy_name: StrategyStats}
            portfolio: {equity, balance, risk_heat, positions_count}
            execution_map: {symbol: {slippage_bps, latency_ms}}
            regime: Market regime ("trend" | "chop" | "high_vol")
        
        Returns:
            List of allocation decisions:
            [
                {
                    "symbol": "BTCUSDT",
                    "side": "LONG",
                    "size_usd": 100.0,
                    "score": 0.85,
                    "strategy": "trend_v1",
                    "entry": 50000,
                    "stop": 49000,
                    "target": 51000
                }
            ]
        """
        equity = portfolio.get("equity", 10000)
        risk_heat = portfolio.get("risk_heat", 0.0)
        positions_count = portfolio.get("positions_count", 0)
        
        logger.info(
            f"[AllocatorV2] Processing {len(signals)} signals | "
            f"Equity: ${equity:,.2f} | Risk Heat: {risk_heat:.1%} | "
            f"Positions: {positions_count} | Regime: {regime}"
        )
        
        # Step 1: Score all signals
        scored_signals = []
        
        for signal in signals:
            # Get strategy stats
            stats = stats_map.get(signal.source)
            if not stats:
                logger.warning(f"[AllocatorV2] No stats for strategy: {signal.source}")
                continue
            
            # Get execution data
            execution = execution_map.get(signal.symbol, {"slippage_bps": 5, "latency_ms": 100})
            
            # Calculate score
            score = score_signal(signal, stats, execution, regime)
            
            scored_signals.append((signal, score, execution))
        
        logger.info(f"[AllocatorV2] Scored {len(scored_signals)} signals")
        
        # Step 2: Filter by execution quality
        filtered = [
            (sig, score, exec_data)
            for sig, score, exec_data in scored_signals
            if exec_data.get("slippage_bps", 999) <= self.MAX_SLIPPAGE_BPS
        ]
        
        if len(filtered) < len(scored_signals):
            logger.info(
                f"[AllocatorV2] Filtered {len(scored_signals) - len(filtered)} signals "
                f"due to poor execution (slippage > {self.MAX_SLIPPAGE_BPS} bps)"
            )
        
        # Step 3: Filter by minimum score
        filtered = [
            (sig, score, exec_data)
            for sig, score, exec_data in filtered
            if score >= self.MIN_SCORE
        ]
        
        # Step 4: Sort by score (descending)
        filtered.sort(key=lambda x: x[1], reverse=True)
        
        # Step 5: Apply portfolio constraints
        decisions = []
        risk_budget = equity * self.RISK_PER_TRADE
        
        available_slots = self.MAX_POSITIONS - positions_count
        
        if available_slots <= 0:
            logger.warning(f"[AllocatorV2] No available slots (max {self.MAX_POSITIONS} reached)")
            return []
        
        for signal, score, exec_data in filtered[:available_slots]:
            # Check risk heat
            if risk_heat > self.MAX_HEAT:
                logger.warning(
                    f"[AllocatorV2] Risk heat exceeded: {risk_heat:.1%} > {self.MAX_HEAT:.1%}"
                )
                break
            
            # Risk-based sizing
            if signal.stop_distance <= 0:
                logger.warning(
                    f"[AllocatorV2] Invalid stop distance for {signal.symbol}: {signal.stop_distance}"
                )
                continue
            
            # size = risk / stop_distance
            position_size_usd = risk_budget / signal.stop_distance
            
            # Cap at reasonable max (e.g., 5% of equity per trade)
            max_size = equity * 0.05
            position_size_usd = min(position_size_usd, max_size)
            
            decisions.append({
                "symbol": signal.symbol,
                "side": signal.side,
                "size_usd": position_size_usd,
                "score": score,
                "strategy": signal.source,
                "entry": signal.entry_price,
                "stop": signal.stop_price,
                "target": signal.target_price,
                "execution_quality": {
                    "slippage_bps": exec_data.get("slippage_bps"),
                    "latency_ms": exec_data.get("latency_ms"),
                },
            })
        
        logger.info(
            f"[AllocatorV2] Generated {len(decisions)} allocation decisions "
            f"(from {len(filtered)} filtered signals)"
        )
        
        return decisions
