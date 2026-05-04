"""Allocator V3 — Fund-level portfolio allocator

Features:
- Fractional Kelly sizing
- Volatility targeting
- Correlation penalties
- Concentration limits
- Drawdown-aware throttling
- Portfolio optimization objective
"""

from collections import defaultdict
from typing import List, Dict, Any
import logging

from .types import Signal, StrategyStats
from .scoring import score_signal
from .kelly import fractional_kelly, kelly_multiplier
from .vol_target import vol_target_multiplier, regime_vol_multiplier
from .correlation import correlation_penalty
from .concentration import check_concentration_limits

logger = logging.getLogger(__name__)


class StrategyAllocatorV3:
    """Fund-level capital allocator with advanced risk management."""
    
    # CRITICAL: Bootstrap vs Production mode
    # Bootstrap: Always generate decisions (exploration phase)
    # Production: Apply full risk filters (exploitation phase)
    BOOTSTRAP_MODE = True  # Set to False when ready for production
    
    # Portfolio constraints
    MAX_POSITIONS = 5
    BASE_RISK_PER_TRADE = 0.01  # 1%
    MAX_POSITION_PCT = 0.08  # 8% max per position
    TARGET_VOL = 0.15  # 15% target portfolio vol
    
    # Concentration limits
    MAX_SYMBOL_PCT = 0.20  # 20% max per symbol
    MAX_STRATEGY_PCT = 0.35  # 35% max per strategy
    MAX_TOTAL_HEAT = 0.70  # 70% max total exposure
    
    # Risk filters
    MIN_SCORE = 0.40
    MAX_SLIPPAGE_BPS = 15
    
    # CRITICAL: Position size floors (prevent allocator from rejecting everything)
    MIN_POSITION_USD = 75.0  # Minimum position size
    FORCE_TOP_N_IF_EMPTY = 2  # Force top-N decisions if allocator produces none
    
    def allocate(
        self,
        signals: List[Signal],
        stats_map: Dict[str, StrategyStats],
        portfolio: Dict[str, Any],
        execution_map: Dict[str, Dict[str, Any]],
        regime: str,
        open_positions: List[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Allocate capital using V3 mathematics with SAFETY FLOORS.
        
        Critical fix: Prevents allocator from rejecting all signals due to
        aggressive penalties. Now uses min() floors on all multipliers and
        emergency fallback if decisions=[] but signals passed ranking.
        
        Args:
            signals: Trading signals (already ranked and accepted by ranking layer)
            stats_map: Strategy performance stats
            portfolio: Portfolio state (equity, balance, drawdown, etc.)
            execution_map: Execution quality data per symbol
            regime: Market regime
            open_positions: Currently open positions
        
        Returns:
            {
                "decisions": [...],
                "allocator_meta": {...}
            }
        """
        equity = float(portfolio.get("equity", 0.0))
        drawdown = float(portfolio.get("drawdown", 0.0))
        
        if equity <= 0:
            return self._empty_allocation("NO_EQUITY")
        
        open_positions = open_positions or []
        
        logger.info(
            f"[AllocatorV3] Processing {len(signals)} signals | "
            f"Equity: ${equity:,.2f} | Drawdown: {drawdown:.2%} | "
            f"Regime: {regime} | Open positions: {len(open_positions)} | "
            f"MODE: {'BOOTSTRAP' if self.BOOTSTRAP_MODE else 'PRODUCTION'}"
        )
        
        # ═══════════════════════════════════════════════════════════════
        # BOOTSTRAP MODE: Force decisions for exploration
        # ═══════════════════════════════════════════════════════════════
        if self.BOOTSTRAP_MODE:
            logger.warning(
                f"[AllocatorV3] ⚠️ BOOTSTRAP MODE ACTIVE - "
                f"Forcing top-{min(self.FORCE_TOP_N_IF_EMPTY, len(signals))} signals"
            )
            
            bootstrap_decisions = []
            
            for idx, s in enumerate(signals[:self.FORCE_TOP_N_IF_EMPTY], 1):
                # Validate structure only
                stop_distance = float(s.stop_distance or 0.0)
                if stop_distance <= 0:
                    logger.warning(f"[AllocatorV3] Bootstrap skip {s.symbol}: invalid stop_distance")
                    continue
                
                bootstrap_decisions.append({
                    "symbol": s.symbol,
                    "side": s.side,
                    "strategy": s.source,
                    "entry": getattr(s, "entry_price", 0.0),
                    "stop": getattr(s, "stop_price", 0.0),
                    "target": getattr(s, "target_price", 0.0),
                    "size_usd": self.MIN_POSITION_USD,
                    "score": float(s.confidence),
                    "base_score": float(s.confidence),
                    "kelly_fraction": 0.0,
                    "adaptive_risk": self.BASE_RISK_PER_TRADE,
                    "vol_multiplier": 1.0,
                    "regime_multiplier": 1.0,
                    "execution_multiplier": 1.0,
                    "correlation_penalty": 1.0,
                    "drawdown_multiplier": 1.0,
                    "forced_min_size": True,
                    "allocator_mode": "bootstrap_forced",
                    "allocator_reason": "bootstrap_mode_force_trade",
                    "execution_quality": execution_map.get(s.symbol, {}),
                })
            
            logger.info(
                f"[AllocatorV3] ✅ BOOTSTRAP: Generated {len(bootstrap_decisions)} forced decisions"
            )
            
            return {
                "decisions": bootstrap_decisions,
                "allocator_meta": {
                    "version": "V3",
                    "mode": "BOOTSTRAP",
                    "regime": regime,
                    "drawdown": drawdown,
                    "drawdown_multiplier": 1.0,
                    "signals_in": len(signals),
                    "signals_out": len(bootstrap_decisions),
                    "reason": "bootstrap_mode_force_trade",
                    "allocator_debug": {
                        "candidates_in": len(signals),
                        "decisions_out": len(bootstrap_decisions),
                        "forced_fallback_used": False,
                        "bootstrap_mode": True,
                    }
                },
            }
        
        # ═══════════════════════════════════════════════════════════════
        # PRODUCTION MODE: Full risk management
        # ═══════════════════════════════════════════════════════════════
        
        # Drawdown throttling (CRITICAL) - but with FLOOR
        dd_multiplier = self._drawdown_multiplier(drawdown)
        dd_multiplier = max(0.50, dd_multiplier)  # FLOOR: never go below 50%
        
        if dd_multiplier == 0:
            logger.warning(f"[AllocatorV3] Drawdown too high: {drawdown:.2%}, allocator OFF")
            return self._empty_allocation("DRAWDOWN_LIMIT", regime, drawdown)
        
        # Score and rank all signals
        ranked_candidates = []
        strategy_capital_map = defaultdict(float)
        symbol_capital_map = defaultdict(float)
        
        logger.info(f"[AllocatorV3] 🔍 DEBUG START: Processing {len(signals)} input signals")
        
        for idx, s in enumerate(signals, 1):
            logger.debug(f"[AllocatorV3] Signal {idx}/{len(signals)}: {s.symbol} {s.side} source={s.source}")
            
            # Get strategy stats
            stats = stats_map.get(s.source, self._default_stats(s.source))
            logger.debug(f"[AllocatorV3]   Stats type: {type(stats)}, keys: {stats.keys() if hasattr(stats, 'keys') else 'N/A'}")
            
            # Get execution data
            execution = execution_map.get(s.symbol, {})
            slippage_bps = execution.get("slippage_bps") or execution.get("expected_slippage_bps") or 5.0
            
            # Filter poor execution (softened)
            if slippage_bps > self.MAX_SLIPPAGE_BPS:
                logger.warning(f"[AllocatorV3]   ❌ REJECTED {s.symbol}: slippage too high ({slippage_bps})")
                continue
            
            # Base score
            base_score = score_signal(s, stats, execution, regime)
            logger.debug(f"[AllocatorV3]   Base score: {base_score:.3f} (min: {self.MIN_SCORE})")
            
            if base_score < self.MIN_SCORE:
                logger.warning(f"[AllocatorV3]   ❌ REJECTED {s.symbol}: score too low ({base_score:.3f} < {self.MIN_SCORE})")
                continue
            
            # Kelly fraction (with FLOOR)
            kelly_frac = fractional_kelly(
                win_rate=stats.get("win_rate", 0.5),
                avg_win=max(abs(stats.get("avg_win", 1.0)), 0.01),
                avg_loss=max(abs(stats.get("avg_loss", 1.0)), 0.01),
                fraction=0.25,
                cap=0.03
            )
            kelly_frac = max(0.0, float(kelly_frac))  # FLOOR: never negative
            
            # Volatility targeting (with FLOOR)
            asset_vol = execution.get("volatility", 0.025)  # Default 2.5%
            vol_mult = vol_target_multiplier(asset_vol, target_vol=self.TARGET_VOL)
            vol_mult = max(0.65, float(vol_mult))  # FLOOR: never below 65%
            
            # Regime multiplier (with FLOOR)
            regime_mult = regime_vol_multiplier(regime)
            regime_mult = max(0.75, float(regime_mult))  # FLOOR: never below 75%
            
            # Correlation penalty (with FLOOR)
            corr_penalty = correlation_penalty(s.symbol, open_positions)
            corr_penalty = max(0.70, float(corr_penalty))  # FLOOR: never below 70%
            
            # Execution multiplier (with FLOOR)
            exec_mult = 1.0 - (execution.get("slippage_bps", 0) / 100.0)
            exec_mult = max(0.70, min(exec_mult, 1.0))  # FLOOR: 70%
            
            # Final score (objective function)
            final_score = base_score * corr_penalty
            
            ranked_candidates.append({
                "signal": s,
                "base_score": base_score,
                "final_score": final_score,
                "kelly_fraction": kelly_frac,
                "vol_multiplier": vol_mult,
                "regime_multiplier": regime_mult,
                "execution_multiplier": exec_mult,
                "correlation_penalty": corr_penalty,
                "drawdown_multiplier": dd_multiplier,
                "stats": stats,
                "execution": execution,
            })
        
        # Sort by final score
        ranked_candidates.sort(key=lambda x: x["final_score"], reverse=True)
        
        logger.info(f"[AllocatorV3] ✅ Ranked {len(ranked_candidates)} valid candidates (from {len(signals)} input)")
        
        if not ranked_candidates:
            logger.error(f"[AllocatorV3] ❌ CRITICAL: 0 ranked candidates! All {len(signals)} signals rejected during scoring/filtering")
            return self._empty_allocation("NO_VALID_SIGNALS", regime, drawdown)
        
        logger.info(f"[AllocatorV3] Ranked {len(ranked_candidates)} valid candidates")
        
        # Portfolio construction
        decisions = []
        used_symbols = set()
        
        for item in ranked_candidates:
            if len(decisions) >= self.MAX_POSITIONS:
                break
            
            s = item["signal"]
            
            # Skip duplicate symbols
            if s.symbol in used_symbols:
                continue
            
            # Calculate effective risk (with SAFE FLOORS)
            kelly_component = max(0.75, 1.0 + item["kelly_fraction"])
            
            effective_risk = (
                self.BASE_RISK_PER_TRADE
                * kelly_component
                * item["vol_multiplier"]
                * item["regime_multiplier"]
                * item["execution_multiplier"]
                * item["correlation_penalty"]
                * item["drawdown_multiplier"]
            )
            
            # Cap at reasonable max
            effective_risk = min(effective_risk, 0.05)  # Max 5% per trade
            
            # Calculate position size
            stop_distance = float(s.stop_distance or 0.0)
            if stop_distance <= 0:
                logger.debug(f"[AllocatorV3] Skipped {s.symbol}: invalid stop distance")
                continue
            
            risk_budget = equity * effective_risk
            raw_size_usd = risk_budget / stop_distance
            
            # Cap at max position %
            size_cap = equity * self.MAX_POSITION_PCT
            size_usd = min(raw_size_usd, size_cap)
            
            # CRITICAL: Apply MIN_POSITION_USD floor (don't reject, just set to min)
            forced_min_size = False
            if size_usd < self.MIN_POSITION_USD:
                size_usd = self.MIN_POSITION_USD
                forced_min_size = True
                logger.debug(
                    f"[AllocatorV3] {s.symbol}: size below min (${raw_size_usd:.2f}), "
                    f"forced to ${self.MIN_POSITION_USD}"
                )
            
            # Check concentration limits
            ok, reason = check_concentration_limits(
                symbol=s.symbol,
                strategy=s.source,
                proposed_size_usd=size_usd,
                portfolio=portfolio,
                strategy_capital_map=strategy_capital_map,
                symbol_capital_map=symbol_capital_map,
                equity=equity,
                max_symbol_pct=self.MAX_SYMBOL_PCT,
                max_strategy_pct=self.MAX_STRATEGY_PCT,
                max_total_heat=self.MAX_TOTAL_HEAT
            )
            
            if not ok:
                logger.warning(f"[AllocatorV3] Skipped {s.symbol}: {reason}")
                continue
            
            # Accept decision
            strategy_capital_map[s.source] += size_usd
            symbol_capital_map[s.symbol] += size_usd
            used_symbols.add(s.symbol)
            
            decisions.append({
                "symbol": s.symbol,
                "side": s.side,
                "strategy": s.source,
                "entry": getattr(s, "entry_price", 0.0),
                "stop": getattr(s, "stop_price", 0.0),
                "target": getattr(s, "target_price", 0.0),
                "size_usd": round(size_usd, 2),
                "score": round(item["final_score"], 4),
                "base_score": round(item["base_score"], 4),
                "kelly_fraction": round(item["kelly_fraction"], 4),
                "adaptive_risk": round(effective_risk, 4),
                "vol_multiplier": round(item["vol_multiplier"], 3),
                "regime_multiplier": round(item["regime_multiplier"], 3),
                "execution_multiplier": round(item["execution_multiplier"], 3),
                "correlation_penalty": round(item["correlation_penalty"], 3),
                "drawdown_multiplier": round(item["drawdown_multiplier"], 3),
                "forced_min_size": forced_min_size,
                "execution_quality": item["execution"],
            })
        
        # EMERGENCY FALLBACK: If allocator produced 0 decisions but signals were accepted by ranking
        if not decisions and ranked_candidates:
            logger.warning(
                f"[AllocatorV3] ⚠️ EMERGENCY FALLBACK: {len(ranked_candidates)} candidates "
                f"but 0 decisions. Forcing top-{self.FORCE_TOP_N_IF_EMPTY} with MIN size."
            )
            
            fallback_candidates = ranked_candidates[:self.FORCE_TOP_N_IF_EMPTY]
            
            for item in fallback_candidates:
                s = item["signal"]
                
                # Validate structure
                entry = getattr(s, "entry_price", 0.0)
                stop = getattr(s, "stop_price", 0.0)
                target = getattr(s, "target_price", 0.0)
                
                if entry <= 0 or stop <= 0 or target <= 0:
                    continue
                
                if abs(entry - stop) <= 0:
                    continue
                
                decisions.append({
                    "symbol": s.symbol,
                    "side": s.side,
                    "strategy": s.source,
                    "entry": entry,
                    "stop": stop,
                    "target": target,
                    "size_usd": self.MIN_POSITION_USD,
                    "score": round(item["final_score"], 4),
                    "base_score": round(item["base_score"], 4),
                    "kelly_fraction": 0.0,
                    "adaptive_risk": self.BASE_RISK_PER_TRADE,
                    "vol_multiplier": 1.0,
                    "regime_multiplier": 1.0,
                    "execution_multiplier": 1.0,
                    "correlation_penalty": 1.0,
                    "drawdown_multiplier": 1.0,
                    "forced_min_size": True,
                    "allocator_mode": "forced_fallback",
                    "allocator_reason": "accepted_signals_present_but_allocator_produced_none",
                    "execution_quality": item["execution"],
                })
        
        logger.info(
            f"[AllocatorV3] ✅ Generated {len(decisions)} decisions "
            f"(from {len(ranked_candidates)} candidates)"
        )
        
        # Enhanced metadata for debugging
        allocator_debug = {
            "candidates_in": len(ranked_candidates),
            "decisions_out": len(decisions),
            "forced_fallback_used": any(d.get("allocator_mode") == "forced_fallback" for d in decisions),
            "min_size_forced_count": sum(1 for d in decisions if d.get("forced_min_size")),
        }
        
        return {
            "decisions": decisions,
            "allocator_meta": {
                "version": "V3",
                "regime": regime,
                "drawdown": drawdown,
                "drawdown_multiplier": dd_multiplier,
                "strategy_capital_map": {k: round(v, 2) for k, v in strategy_capital_map.items()},
                "symbol_capital_map": {k: round(v, 2) for k, v in symbol_capital_map.items()},
                "signals_in": len(signals),
                "signals_out": len(decisions),
                "allocator_debug": allocator_debug,
            },
        }
    
    def _drawdown_multiplier(self, drawdown: float) -> float:
        """Calculate drawdown throttling multiplier."""
        if drawdown >= 0.10:  # 10% DD
            return 0.0  # Stop trading
        if drawdown >= 0.07:  # 7% DD
            return 0.35
        if drawdown >= 0.05:  # 5% DD
            return 0.5
        if drawdown >= 0.03:  # 3% DD
            return 0.75
        return 1.0
    
    def _default_stats(self, strategy: str) -> dict:
        """Return default stats for unknown strategy."""
        return {
            "name": strategy,
            "win_rate": 0.5,
            "avg_return": 0.0,
            "avg_win": 1.0,
            "avg_loss": 1.0,
            "sharpe": 0.0,
            "drawdown": 0.0,
            "recent_pnl": 0.0,
        }
    
    def _empty_allocation(self, reason: str, regime: str = "N/A", drawdown: float = 0.0) -> dict:
        """Return empty allocation with reason."""
        return {
            "decisions": [],
            "allocator_meta": {
                "version": "V3",
                "reason": reason,
                "regime": regime,
                "drawdown": drawdown,
                "signals_in": 0,
                "signals_out": 0,
            },
        }
