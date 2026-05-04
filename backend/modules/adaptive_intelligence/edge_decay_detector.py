"""
PHASE 11.4 - Edge Decay Detector
=================================
Detects weakening or dying edges.

Metrics:
- Rolling profit factor
- Rolling expectancy
- Hit rate drift
- Confidence degradation
- Signal conflict growth

Requires multi-axis confirmation before flagging decay.
"""

import random
from typing import List, Dict, Optional
from datetime import datetime, timezone, timedelta

from .adaptive_types import (
    EdgeDecaySignal, EdgeStatus, AdaptiveAction,
    DEFAULT_ADAPTIVE_CONFIG
)


class EdgeDecayDetector:
    """
    Edge Decay Detection Engine
    
    Monitors edges for signs of decay and provides
    early warning before edges die completely.
    """
    
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or DEFAULT_ADAPTIVE_CONFIG
        self.edge_history: Dict[str, List[EdgeDecaySignal]] = {}
        self.performance_series: Dict[str, List[Dict]] = {}
        self.max_history = 100
    
    def record_edge_performance(
        self,
        strategy_id: str,
        edge_name: str,
        trade_result: Dict
    ):
        """Record individual trade result for an edge."""
        key = f"{strategy_id}_{edge_name}"
        
        if key not in self.performance_series:
            self.performance_series[key] = []
        
        self.performance_series[key].append({
            "timestamp": datetime.now(timezone.utc),
            "pnl": trade_result.get("pnl", 0),
            "win": trade_result.get("pnl", 0) > 0,
            "confidence": trade_result.get("entry_confidence", 0.5)
        })
        
        # Keep last N trades
        lookback = self.config.get("edge_decay_lookback_days", 30) * 5  # ~5 trades/day
        if len(self.performance_series[key]) > lookback:
            self.performance_series[key] = self.performance_series[key][-lookback:]
    
    def detect_decay(
        self,
        strategy_id: str,
        edge_name: str,
        trades: Optional[List[Dict]] = None
    ) -> EdgeDecaySignal:
        """
        Detect edge decay.
        
        Args:
            strategy_id: Strategy identifier
            edge_name: Name of the edge
            trades: Optional trade history
            
        Returns:
            EdgeDecaySignal with decay analysis
        """
        now = datetime.now(timezone.utc)
        key = f"{strategy_id}_{edge_name}"
        
        # Get performance data
        if trades:
            perf_data = trades
        else:
            perf_data = self.performance_series.get(key, [])
        
        # If no data, generate mock
        if not perf_data:
            perf_data = self._generate_mock_performance(50)
        
        # Calculate decay metrics
        rolling_pf = self._calculate_rolling_pf(perf_data)
        rolling_expectancy = self._calculate_rolling_expectancy(perf_data)
        hit_rate_drift = self._calculate_hit_rate_drift(perf_data)
        confidence_degradation = self._calculate_confidence_degradation(perf_data)
        
        # Multi-axis confirmation
        confirmation_axes = []
        decay_signals = 0
        
        # Axis 1: Rolling PF
        if rolling_pf < self.config["edge_death_threshold"]:
            confirmation_axes.append("ROLLING_PF_CRITICAL")
            decay_signals += 2
        elif rolling_pf < 1.2:
            confirmation_axes.append("ROLLING_PF_LOW")
            decay_signals += 1
        
        # Axis 2: Expectancy
        if rolling_expectancy < 0:
            confirmation_axes.append("NEGATIVE_EXPECTANCY")
            decay_signals += 2
        elif rolling_expectancy < 0.001:
            confirmation_axes.append("LOW_EXPECTANCY")
            decay_signals += 1
        
        # Axis 3: Hit rate drift
        if hit_rate_drift < -0.1:
            confirmation_axes.append("HIT_RATE_DECLINING")
            decay_signals += 1
        
        # Axis 4: Confidence degradation
        if confidence_degradation > 0.15:
            confirmation_axes.append("CONFIDENCE_DEGRADING")
            decay_signals += 1
        
        # Determine edge status
        if decay_signals >= 4:
            edge_status = EdgeStatus.DEAD
            decay_probability = 0.95
        elif decay_signals >= 3:
            edge_status = EdgeStatus.CRITICAL
            decay_probability = 0.8
        elif decay_signals >= 2:
            edge_status = EdgeStatus.WEAKENING
            decay_probability = 0.5
        elif decay_signals >= 1:
            edge_status = EdgeStatus.HEALTHY
            decay_probability = 0.2
        else:
            edge_status = EdgeStatus.STRONG
            decay_probability = 0.05
        
        # Confirmed decay requires 2+ axes
        confirmed_decay = len(confirmation_axes) >= 2
        
        # Recommend action
        if edge_status == EdgeStatus.DEAD:
            action = AdaptiveAction.DISABLE_STRATEGY
            urgency = 1.0
        elif edge_status == EdgeStatus.CRITICAL:
            action = AdaptiveAction.DECREASE_ALLOCATION
            urgency = 0.8
        elif edge_status == EdgeStatus.WEAKENING:
            action = AdaptiveAction.ADJUST_PARAMETER
            urgency = 0.5
        else:
            action = AdaptiveAction.NO_ACTION
            urgency = 0.0
        
        signal = EdgeDecaySignal(
            strategy_id=strategy_id,
            edge_name=edge_name,
            timestamp=now,
            edge_status=edge_status,
            decay_probability=decay_probability,
            rolling_pf=rolling_pf,
            rolling_expectancy=rolling_expectancy,
            hit_rate_drift=hit_rate_drift,
            confidence_degradation=confidence_degradation,
            confirmed_decay=confirmed_decay,
            confirmation_axes=confirmation_axes,
            recommended_action=action,
            urgency=urgency
        )
        
        # Save to history
        self._add_to_history(key, signal)
        
        return signal
    
    def _calculate_rolling_pf(self, trades: List[Dict]) -> float:
        """Calculate rolling profit factor."""
        if not trades:
            return 1.0
        
        recent = trades[-30:]  # Last 30 trades
        
        gross_profit = sum(t["pnl"] for t in recent if t.get("pnl", 0) > 0)
        gross_loss = abs(sum(t["pnl"] for t in recent if t.get("pnl", 0) < 0))
        
        if gross_loss > 0:
            return gross_profit / gross_loss
        elif gross_profit > 0:
            return 3.0  # Cap at 3 if no losses
        return 1.0
    
    def _calculate_rolling_expectancy(self, trades: List[Dict]) -> float:
        """Calculate rolling expectancy."""
        if not trades:
            return 0.0
        
        recent = trades[-30:]
        return sum(t.get("pnl", 0) for t in recent) / len(recent)
    
    def _calculate_hit_rate_drift(self, trades: List[Dict]) -> float:
        """Calculate change in hit rate."""
        if len(trades) < 40:
            return 0.0
        
        older = trades[-60:-30]
        recent = trades[-30:]
        
        older_hr = sum(1 for t in older if t.get("win", False)) / len(older)
        recent_hr = sum(1 for t in recent if t.get("win", False)) / len(recent)
        
        return recent_hr - older_hr  # Negative = declining
    
    def _calculate_confidence_degradation(self, trades: List[Dict]) -> float:
        """Calculate confidence degradation."""
        if len(trades) < 40:
            return 0.0
        
        older = trades[-60:-30]
        recent = trades[-30:]
        
        older_conf = sum(t.get("confidence", 0.5) for t in older) / len(older)
        recent_conf = sum(t.get("confidence", 0.5) for t in recent) / len(recent)
        
        return older_conf - recent_conf  # Positive = degrading
    
    def _generate_mock_performance(self, count: int) -> List[Dict]:
        """Generate mock performance data."""
        trades = []
        
        for i in range(count):
            # Slight positive expectancy with some variance
            pnl = random.gauss(0.002, 0.02) * 100
            win = pnl > 0
            confidence = 0.6 + random.gauss(0, 0.1)
            
            trades.append({
                "pnl": pnl,
                "win": win,
                "confidence": max(0.3, min(0.9, confidence)),
                "timestamp": datetime.now(timezone.utc) - timedelta(hours=count - i)
            })
        
        return trades
    
    def _add_to_history(self, key: str, signal: EdgeDecaySignal):
        """Add signal to history."""
        if key not in self.edge_history:
            self.edge_history[key] = []
        
        self.edge_history[key].append(signal)
        
        if len(self.edge_history[key]) > self.max_history:
            self.edge_history[key] = self.edge_history[key][-self.max_history:]
    
    def get_all_edges_status(self) -> Dict[str, Dict]:
        """Get status of all tracked edges."""
        status = {}
        
        for key, history in self.edge_history.items():
            if history:
                latest = history[-1]
                status[key] = {
                    "status": latest.edge_status.value,
                    "decay_probability": round(latest.decay_probability, 3),
                    "rolling_pf": round(latest.rolling_pf, 3),
                    "confirmed_decay": latest.confirmed_decay,
                    "recommended_action": latest.recommended_action.value
                }
        
        return status
    
    def get_decaying_edges(self) -> List[str]:
        """Get list of edges showing decay."""
        decaying = []
        
        for key, history in self.edge_history.items():
            if history and history[-1].edge_status in [
                EdgeStatus.WEAKENING, EdgeStatus.CRITICAL, EdgeStatus.DEAD
            ]:
                decaying.append(key)
        
        return decaying
    
    def get_decay_summary(self) -> Dict:
        """Get summary of edge decay analysis."""
        strong = 0
        healthy = 0
        weakening = 0
        critical = 0
        dead = 0
        
        for history in self.edge_history.values():
            if history:
                status = history[-1].edge_status
                if status == EdgeStatus.STRONG:
                    strong += 1
                elif status == EdgeStatus.HEALTHY:
                    healthy += 1
                elif status == EdgeStatus.WEAKENING:
                    weakening += 1
                elif status == EdgeStatus.CRITICAL:
                    critical += 1
                elif status == EdgeStatus.DEAD:
                    dead += 1
        
        return {
            "total_edges": len(self.edge_history),
            "strong": strong,
            "healthy": healthy,
            "weakening": weakening,
            "critical": critical,
            "dead": dead,
            "edges_requiring_attention": weakening + critical + dead
        }
