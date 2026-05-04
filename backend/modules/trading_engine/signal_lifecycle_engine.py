"""
Signal Lifecycle Engine — Signal Tracking & Performance Analytics

Manages the complete lifecycle of trading signals:
- Signal monitoring (active signals tracking)
- TP hit detection (TP1, TP2, TP3)
- SL hit detection
- Signal expiration
- Performance statistics & analytics
- Indicator quality analysis

This enables the system to:
1. Track signal outcomes
2. Measure strategy performance
3. Improve indicator weights based on results
"""

from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timezone, timedelta
from pydantic import BaseModel, Field
from collections import defaultdict
import statistics

from .signal_engine import (
    TradingSignal,
    SignalAlert,
    SignalStatus,
    SignalDirection,
    SignalStrength,
    get_signal_engine,
)
from .signal_storage import get_signal_storage


# ═══════════════════════════════════════════════════════════════
# Performance Models
# ═══════════════════════════════════════════════════════════════

class SignalPerformance(BaseModel):
    """Aggregated signal performance metrics."""
    
    # Overview
    signals_total: int = 0
    signals_closed: int = 0
    signals_active: int = 0
    
    # Win/Loss
    wins: int = 0
    losses: int = 0
    win_rate: float = 0.0
    
    # Profit metrics
    total_pnl_pct: float = 0.0
    avg_pnl_pct: float = 0.0
    profit_factor: float = 0.0  # gross_profit / gross_loss
    
    # Risk/Reward
    avg_rr_achieved: float = 0.0
    best_rr: float = 0.0
    worst_rr: float = 0.0
    
    # Duration
    avg_duration_hours: float = 0.0
    avg_duration_display: str = ""
    
    # TP Hit Rates
    tp1_hit_rate: float = 0.0
    tp2_hit_rate: float = 0.0
    tp3_hit_rate: float = 0.0
    
    # By direction
    long_win_rate: float = 0.0
    short_win_rate: float = 0.0
    
    # By strength
    strong_signal_win_rate: float = 0.0
    medium_signal_win_rate: float = 0.0
    weak_signal_win_rate: float = 0.0
    
    # Time period
    period_days: int = 30
    
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class IndicatorQualityReport(BaseModel):
    """Analysis of indicator contribution to winning trades."""
    
    # Best performing indicators
    best_indicator_drivers: List[Dict[str, Any]] = Field(default_factory=list)
    
    # Worst performing indicators
    worst_indicator_drivers: List[Dict[str, Any]] = Field(default_factory=list)
    
    # Indicator win rates
    indicator_win_rates: Dict[str, float] = Field(default_factory=dict)
    
    # Correlation with outcomes
    direction_correlation: Dict[str, float] = Field(default_factory=dict)
    
    # Suggested weight adjustments
    weight_adjustments: Dict[str, float] = Field(default_factory=dict)
    
    # Sample size
    signals_analyzed: int = 0
    
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class SignalOutcome(BaseModel):
    """Detailed outcome for a single signal."""
    signal_id: str
    direction: str
    
    # Prices
    entry_price: float
    exit_price: float
    stop_loss: float
    
    # Outcome
    outcome: str  # "win", "loss", "breakeven"
    exit_reason: str  # "tp1_hit", "tp2_hit", "tp3_hit", "sl_hit", "expired", "manual"
    
    # Metrics
    pnl_pct: float
    rr_achieved: float
    duration_hours: float
    
    # Contributing factors
    indicator_drivers: List[Dict[str, Any]] = Field(default_factory=list)
    market_state_at_entry: str = ""
    
    timestamp: str = ""


# ═══════════════════════════════════════════════════════════════
# Signal Lifecycle Engine
# ═══════════════════════════════════════════════════════════════

class SignalLifecycleEngine:
    """
    Manages signal lifecycle: monitoring, outcome detection, analytics.
    
    Lifecycle stages:
    1. generated - Signal created but not yet active
    2. active - Entry conditions met
    3. tp1_hit - First take profit reached
    4. tp2_hit - Second take profit reached  
    5. tp3_hit - Full profit (closed)
    6. sl_hit - Stop loss triggered (closed)
    7. expired - Time expiry without entry/exit
    8. invalidated - Market conditions changed, signal no longer valid
    """
    
    def __init__(self):
        self.storage = get_signal_storage()
        self.signal_engine = get_signal_engine()
    
    # ═══════════════════════════════════════════════════════════════
    # Signal Monitoring
    # ═══════════════════════════════════════════════════════════════
    
    def update_signal_with_price(
        self,
        signal: TradingSignal,
        current_price: float
    ) -> Tuple[TradingSignal, List[SignalAlert]]:
        """
        Update signal status based on current price.
        
        Checks:
        - Entry activation (pending → active)
        - TP levels hit
        - SL hit
        - Expiration
        
        Returns updated signal and any generated alerts.
        """
        alerts = []
        now = datetime.now(timezone.utc)
        
        # Check expiration first
        if signal.expires_at and signal.status == SignalStatus.PENDING:
            try:
                expiry = datetime.fromisoformat(signal.expires_at.replace('Z', '+00:00'))
                if now > expiry:
                    signal.status = SignalStatus.EXPIRED
                    signal.closed_at = now.isoformat()
                    signal.exit_reason = "Time expiry without activation"
                    return signal, alerts
            except:
                pass
        
        # Update current price
        signal.current_price = current_price
        
        # Check stop loss
        sl_hit = False
        if signal.direction == SignalDirection.LONG:
            if current_price <= signal.stop_loss:
                sl_hit = True
        else:  # SHORT
            if current_price >= signal.stop_loss:
                sl_hit = True
        
        if sl_hit:
            signal.status = SignalStatus.SL_HIT
            signal.exit_price = current_price
            signal.exit_reason = "Stop loss triggered"
            signal.closed_at = now.isoformat()
            
            # Calculate PnL
            if signal.direction == SignalDirection.LONG:
                signal.pnl_pct = (current_price - signal.entry_price) / signal.entry_price
            else:
                signal.pnl_pct = (signal.entry_price - current_price) / signal.entry_price
            
            alerts.append(SignalAlert(
                alert_type="sl_hit",
                symbol=signal.symbol,
                timeframe=signal.timeframe,
                message=f"🛑 SL hit on {signal.symbol} {signal.direction.value.upper()} | PnL: {signal.pnl_pct:.2%}",
                priority="high",
                signal_id=signal.signal_id,
                data={
                    "exit_price": current_price,
                    "pnl_pct": signal.pnl_pct,
                    "entry_price": signal.entry_price,
                }
            ))
            return signal, alerts
        
        # Check take profit levels
        for tp in signal.take_profit:
            if tp.hit:
                continue
            
            tp_hit = False
            if signal.direction == SignalDirection.LONG:
                if current_price >= tp.price:
                    tp_hit = True
            else:  # SHORT
                if current_price <= tp.price:
                    tp_hit = True
            
            if tp_hit:
                tp.hit = True
                tp.hit_at = now.isoformat()
                
                # Update status based on TP level
                if tp.level == 1:
                    signal.status = SignalStatus.TP1_HIT
                elif tp.level == 2:
                    signal.status = SignalStatus.TP2_HIT
                elif tp.level >= 3:
                    signal.status = SignalStatus.TP3_HIT
                    signal.closed_at = now.isoformat()
                    signal.exit_price = current_price
                    signal.exit_reason = f"TP{tp.level} hit"
                    
                    # Calculate full PnL
                    if signal.direction == SignalDirection.LONG:
                        signal.pnl_pct = (current_price - signal.entry_price) / signal.entry_price
                    else:
                        signal.pnl_pct = (signal.entry_price - current_price) / signal.entry_price
                
                alerts.append(SignalAlert(
                    alert_type="tp_hit",
                    symbol=signal.symbol,
                    timeframe=signal.timeframe,
                    message=f"✅ TP{tp.level} hit on {signal.symbol} ({tp.rr_ratio}:1 R:R)",
                    priority="normal" if tp.level < 3 else "high",
                    signal_id=signal.signal_id,
                    data={
                        "tp_level": tp.level,
                        "price": current_price,
                        "rr_ratio": tp.rr_ratio,
                    }
                ))
        
        # Activate pending signal
        if signal.status == SignalStatus.PENDING:
            signal.status = SignalStatus.ACTIVE
            signal.activated_at = now.isoformat()
        
        return signal, alerts
    
    def process_all_active_signals(
        self,
        price_updates: Dict[str, float]
    ) -> Tuple[List[TradingSignal], List[SignalAlert]]:
        """
        Process all active signals with current prices.
        
        Args:
            price_updates: Dict of symbol -> current_price
            
        Returns:
            Updated signals and generated alerts
        """
        updated_signals = []
        all_alerts = []
        
        active_signals = self.storage.get_active_signals()
        
        for signal in active_signals:
            symbol = signal.symbol.upper()
            if symbol not in price_updates:
                continue
            
            current_price = price_updates[symbol]
            updated_signal, alerts = self.update_signal_with_price(signal, current_price)
            
            # Save updated signal
            self.storage.save_signal(updated_signal)
            
            # Save alerts
            for alert in alerts:
                self.storage.save_alert(alert)
            
            updated_signals.append(updated_signal)
            all_alerts.extend(alerts)
        
        return updated_signals, all_alerts
    
    # ═══════════════════════════════════════════════════════════════
    # Performance Analytics
    # ═══════════════════════════════════════════════════════════════
    
    def calculate_performance(
        self,
        symbol: Optional[str] = None,
        days: int = 30
    ) -> SignalPerformance:
        """
        Calculate comprehensive performance metrics.
        """
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        
        # Get all signals in period
        all_signals = self.storage.get_signals(
            symbol=symbol,
            limit=1000,
        )
        
        # Filter by date
        signals = [
            s for s in all_signals 
            if s.created_at and s.created_at >= cutoff.isoformat()
        ]
        
        if not signals:
            return SignalPerformance(period_days=days)
        
        # Categorize signals
        closed_signals = [s for s in signals if s.status in [
            SignalStatus.TP1_HIT, SignalStatus.TP2_HIT, SignalStatus.TP3_HIT,
            SignalStatus.SL_HIT, SignalStatus.EXPIRED, SignalStatus.CANCELLED
        ]]
        
        active_signals = [s for s in signals if s.status in [
            SignalStatus.PENDING, SignalStatus.ACTIVE
        ]]
        
        # Win/Loss calculation
        wins = []
        losses = []
        long_wins = 0
        long_total = 0
        short_wins = 0
        short_total = 0
        
        strong_wins = 0
        strong_total = 0
        medium_wins = 0
        medium_total = 0
        weak_wins = 0
        weak_total = 0
        
        tp1_hits = 0
        tp2_hits = 0
        tp3_hits = 0
        total_closed_with_tp = 0
        
        durations = []
        rrs = []
        
        gross_profit = 0.0
        gross_loss = 0.0
        
        for signal in closed_signals:
            pnl = signal.pnl_pct or 0
            
            # Win/Loss
            if pnl > 0:
                wins.append(signal)
                gross_profit += pnl
            elif pnl < 0:
                losses.append(signal)
                gross_loss += abs(pnl)
            
            # By direction
            if signal.direction == SignalDirection.LONG:
                long_total += 1
                if pnl > 0:
                    long_wins += 1
            else:
                short_total += 1
                if pnl > 0:
                    short_wins += 1
            
            # By strength
            if signal.strength == SignalStrength.STRONG:
                strong_total += 1
                if pnl > 0:
                    strong_wins += 1
            elif signal.strength == SignalStrength.MEDIUM:
                medium_total += 1
                if pnl > 0:
                    medium_wins += 1
            else:
                weak_total += 1
                if pnl > 0:
                    weak_wins += 1
            
            # TP hit tracking
            if signal.status in [SignalStatus.TP1_HIT, SignalStatus.TP2_HIT, SignalStatus.TP3_HIT]:
                total_closed_with_tp += 1
                if signal.status == SignalStatus.TP1_HIT:
                    tp1_hits += 1
                elif signal.status == SignalStatus.TP2_HIT:
                    tp2_hits += 1
                    tp1_hits += 1
                elif signal.status == SignalStatus.TP3_HIT:
                    tp3_hits += 1
                    tp2_hits += 1
                    tp1_hits += 1
            
            # Duration
            if signal.created_at and signal.closed_at:
                try:
                    created = datetime.fromisoformat(signal.created_at.replace('Z', '+00:00'))
                    closed = datetime.fromisoformat(signal.closed_at.replace('Z', '+00:00'))
                    duration_hours = (closed - created).total_seconds() / 3600
                    durations.append(duration_hours)
                except:
                    pass
            
            # R:R achieved
            if signal.entry_price and signal.exit_price and signal.stop_loss:
                risk = abs(signal.entry_price - signal.stop_loss)
                reward = abs(signal.exit_price - signal.entry_price)
                if risk > 0:
                    rr = reward / risk if pnl > 0 else -reward / risk
                    rrs.append(rr)
        
        # Calculate metrics
        total_closed = len(closed_signals)
        win_rate = len(wins) / total_closed if total_closed > 0 else 0
        
        total_pnl = gross_profit - gross_loss
        avg_pnl = total_pnl / total_closed if total_closed > 0 else 0
        
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else (
            float('inf') if gross_profit > 0 else 0
        )
        
        avg_rr = statistics.mean(rrs) if rrs else 0
        best_rr = max(rrs) if rrs else 0
        worst_rr = min(rrs) if rrs else 0
        
        avg_duration = statistics.mean(durations) if durations else 0
        
        # Format duration
        if avg_duration < 1:
            duration_display = f"{int(avg_duration * 60)}m"
        elif avg_duration < 24:
            duration_display = f"{avg_duration:.1f}h"
        else:
            duration_display = f"{avg_duration / 24:.1f}d"
        
        return SignalPerformance(
            signals_total=len(signals),
            signals_closed=total_closed,
            signals_active=len(active_signals),
            
            wins=len(wins),
            losses=len(losses),
            win_rate=round(win_rate, 3),
            
            total_pnl_pct=round(total_pnl, 4),
            avg_pnl_pct=round(avg_pnl, 4),
            profit_factor=round(profit_factor, 2) if profit_factor != float('inf') else 999.99,
            
            avg_rr_achieved=round(avg_rr, 2),
            best_rr=round(best_rr, 2),
            worst_rr=round(worst_rr, 2),
            
            avg_duration_hours=round(avg_duration, 1),
            avg_duration_display=duration_display,
            
            tp1_hit_rate=round(tp1_hits / total_closed_with_tp, 3) if total_closed_with_tp > 0 else 0,
            tp2_hit_rate=round(tp2_hits / total_closed_with_tp, 3) if total_closed_with_tp > 0 else 0,
            tp3_hit_rate=round(tp3_hits / total_closed_with_tp, 3) if total_closed_with_tp > 0 else 0,
            
            long_win_rate=round(long_wins / long_total, 3) if long_total > 0 else 0,
            short_win_rate=round(short_wins / short_total, 3) if short_total > 0 else 0,
            
            strong_signal_win_rate=round(strong_wins / strong_total, 3) if strong_total > 0 else 0,
            medium_signal_win_rate=round(medium_wins / medium_total, 3) if medium_total > 0 else 0,
            weak_signal_win_rate=round(weak_wins / weak_total, 3) if weak_total > 0 else 0,
            
            period_days=days,
        )
    
    # ═══════════════════════════════════════════════════════════════
    # Indicator Quality Analysis
    # ═══════════════════════════════════════════════════════════════
    
    def analyze_indicator_quality(
        self,
        symbol: Optional[str] = None,
        days: int = 30
    ) -> IndicatorQualityReport:
        """
        Analyze which indicators contributed to winning vs losing trades.
        
        This enables:
        - Identifying best performing indicator combinations
        - Suggesting weight adjustments
        - Understanding market regime effectiveness
        """
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        
        # Get closed signals with outcomes
        all_signals = self.storage.get_signals(symbol=symbol, limit=1000)
        
        signals = [
            s for s in all_signals 
            if s.created_at and s.created_at >= cutoff.isoformat()
            and s.pnl_pct is not None
        ]
        
        if not signals:
            return IndicatorQualityReport(signals_analyzed=0)
        
        # Track indicator performance
        indicator_wins = defaultdict(int)
        indicator_losses = defaultdict(int)
        indicator_scores = defaultdict(list)
        
        # Track by market state
        state_wins = defaultdict(int)
        state_losses = defaultdict(int)
        
        for signal in signals:
            is_win = signal.pnl_pct > 0
            
            # Track indicator drivers
            for driver in signal.indicator_drivers:
                indicator_name = driver.get("indicator", "unknown")
                score = driver.get("score", 0)
                
                if is_win:
                    indicator_wins[indicator_name] += 1
                else:
                    indicator_losses[indicator_name] += 1
                
                indicator_scores[indicator_name].append((score, is_win))
            
            # Track market state
            state = signal.market_state
            if is_win:
                state_wins[state] += 1
            else:
                state_losses[state] += 1
        
        # Calculate win rates per indicator
        indicator_win_rates = {}
        for indicator in set(indicator_wins.keys()) | set(indicator_losses.keys()):
            wins = indicator_wins[indicator]
            losses = indicator_losses[indicator]
            total = wins + losses
            if total > 0:
                indicator_win_rates[indicator] = round(wins / total, 3)
        
        # Sort by win rate
        sorted_indicators = sorted(
            indicator_win_rates.items(),
            key=lambda x: x[1],
            reverse=True
        )
        
        # Best indicators
        best_drivers = []
        for indicator, win_rate in sorted_indicators[:5]:
            scores = indicator_scores[indicator]
            avg_score = statistics.mean([s[0] for s in scores]) if scores else 0
            
            best_drivers.append({
                "indicator": indicator,
                "win_rate": win_rate,
                "avg_score": round(avg_score, 2),
                "sample_size": len(scores),
            })
        
        # Worst indicators
        worst_drivers = []
        for indicator, win_rate in sorted_indicators[-5:]:
            scores = indicator_scores[indicator]
            avg_score = statistics.mean([s[0] for s in scores]) if scores else 0
            
            worst_drivers.append({
                "indicator": indicator,
                "win_rate": win_rate,
                "avg_score": round(avg_score, 2),
                "sample_size": len(scores),
            })
        
        # Calculate weight adjustments
        # Increase weight for high win rate indicators, decrease for low
        weight_adjustments = {}
        baseline_win_rate = 0.5  # Expected random win rate
        
        for indicator, win_rate in indicator_win_rates.items():
            if indicator_wins[indicator] + indicator_losses[indicator] >= 5:  # Minimum sample
                # Adjust weight based on deviation from baseline
                adjustment = (win_rate - baseline_win_rate) * 0.5  # Scale factor
                weight_adjustments[indicator] = round(adjustment, 2)
        
        # Direction correlation
        direction_correlation = {}
        for state in set(state_wins.keys()) | set(state_losses.keys()):
            wins = state_wins[state]
            losses = state_losses[state]
            total = wins + losses
            if total > 0:
                direction_correlation[state] = round(wins / total, 3)
        
        return IndicatorQualityReport(
            best_indicator_drivers=best_drivers,
            worst_indicator_drivers=worst_drivers,
            indicator_win_rates=indicator_win_rates,
            direction_correlation=direction_correlation,
            weight_adjustments=weight_adjustments,
            signals_analyzed=len(signals),
        )
    
    # ═══════════════════════════════════════════════════════════════
    # Signal Outcomes
    # ═══════════════════════════════════════════════════════════════
    
    def get_signal_outcomes(
        self,
        symbol: Optional[str] = None,
        limit: int = 50
    ) -> List[SignalOutcome]:
        """
        Get detailed outcomes for closed signals.
        """
        signals = self.storage.get_signals(symbol=symbol, limit=limit)
        
        outcomes = []
        for signal in signals:
            if signal.pnl_pct is None:
                continue
            
            # Determine outcome
            if signal.pnl_pct > 0.001:
                outcome = "win"
            elif signal.pnl_pct < -0.001:
                outcome = "loss"
            else:
                outcome = "breakeven"
            
            # Calculate duration
            duration_hours = 0
            if signal.created_at and signal.closed_at:
                try:
                    created = datetime.fromisoformat(signal.created_at.replace('Z', '+00:00'))
                    closed = datetime.fromisoformat(signal.closed_at.replace('Z', '+00:00'))
                    duration_hours = (closed - created).total_seconds() / 3600
                except:
                    pass
            
            # Calculate R:R achieved
            rr_achieved = 0
            if signal.entry_price and signal.exit_price and signal.stop_loss:
                risk = abs(signal.entry_price - signal.stop_loss)
                reward = abs(signal.exit_price - signal.entry_price)
                if risk > 0:
                    rr_achieved = reward / risk if signal.pnl_pct > 0 else -reward / risk
            
            outcomes.append(SignalOutcome(
                signal_id=signal.signal_id,
                direction=signal.direction.value,
                entry_price=signal.entry_price,
                exit_price=signal.exit_price or signal.entry_price,
                stop_loss=signal.stop_loss,
                outcome=outcome,
                exit_reason=signal.exit_reason or signal.status.value,
                pnl_pct=round(signal.pnl_pct, 4),
                rr_achieved=round(rr_achieved, 2),
                duration_hours=round(duration_hours, 1),
                indicator_drivers=signal.indicator_drivers,
                market_state_at_entry=signal.market_state,
                timestamp=signal.closed_at or signal.created_at,
            ))
        
        return outcomes
    
    # ═══════════════════════════════════════════════════════════════
    # Signal Invalidation
    # ═══════════════════════════════════════════════════════════════
    
    def invalidate_signal(
        self,
        signal_id: str,
        reason: str = "Market conditions changed"
    ) -> bool:
        """
        Invalidate a signal when market conditions no longer support it.
        """
        signal = self.storage.get_signal(signal_id)
        if not signal:
            return False
        
        if signal.status not in [SignalStatus.PENDING, SignalStatus.ACTIVE]:
            return False  # Can't invalidate closed signals
        
        signal.status = SignalStatus.CANCELLED
        signal.exit_reason = f"Invalidated: {reason}"
        signal.closed_at = datetime.now(timezone.utc).isoformat()
        
        self.storage.save_signal(signal)
        return True
    
    def check_signal_validity(
        self,
        signal: TradingSignal,
        current_feature_vector: Dict[str, float]
    ) -> Tuple[bool, str]:
        """
        Check if signal is still valid based on current market conditions.
        
        Returns (is_valid, reason)
        """
        # Get original signal conditions
        original_trend = signal.feature_vector.get("trend_score", 0)
        original_net = signal.feature_vector.get("net_score", 0)
        
        current_trend = current_feature_vector.get("trend_score", 0)
        current_net = current_feature_vector.get("net_score", 0)
        
        # Check for direction reversal
        if signal.direction == SignalDirection.LONG:
            # Long signal invalid if trend turns bearish
            if current_trend < -0.3 and original_trend > 0:
                return False, "Trend reversed to bearish"
            if current_net < -0.2 and original_net > 0:
                return False, "Net score turned negative"
        else:
            # Short signal invalid if trend turns bullish
            if current_trend > 0.3 and original_trend < 0:
                return False, "Trend reversed to bullish"
            if current_net > 0.2 and original_net < 0:
                return False, "Net score turned positive"
        
        # Check for confidence drop
        original_conf = signal.feature_vector.get("confidence", 0)
        current_conf = current_feature_vector.get("confidence", 0)
        
        if current_conf < original_conf * 0.5:
            return False, "Confidence dropped significantly"
        
        return True, "Signal still valid"


# ═══════════════════════════════════════════════════════════════
# Singleton
# ═══════════════════════════════════════════════════════════════

_lifecycle_engine: Optional[SignalLifecycleEngine] = None

def get_lifecycle_engine() -> SignalLifecycleEngine:
    """Get singleton instance."""
    global _lifecycle_engine
    if _lifecycle_engine is None:
        _lifecycle_engine = SignalLifecycleEngine()
    return _lifecycle_engine
