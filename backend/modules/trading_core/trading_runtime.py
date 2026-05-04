"""Trading Runtime — Week 4

Полный торговый цикл с Allocator V3:
Signals → Scoring → Regime → Allocation → Orders → Fills → Positions

Week 4 Update: Integrated AllocatorV3 with fund-level math
"""

import asyncio
import logging
from typing import List, Dict, Any
from datetime import datetime, timezone

from modules.market_intelligence.scanner_runtime import run_scanner
from .decision_engine import make_decision
from .portfolio_service import get_portfolio_service
from .execution_events import get_events_service
from modules.exchange.service import exchange_service
from modules.exchange.models import OrderRequest

# Week 4: Allocator V3 integration
from modules.strategy.allocator_v3 import StrategyAllocatorV3
from modules.strategy.strategy_stats_service import StrategyStatsService
from modules.strategy.regime import detect_regime, calculate_trend_strength, calculate_volatility
from modules.strategy.types import StrategyStats

# Week 5: Brain Integration (Risk + Portfolio + Ranking)
from modules.risk.risk_engine import get_risk_engine
from modules.risk.portfolio_engine import get_portfolio_engine
from modules.strategy.signal_ranking import rank_signals

logger = logging.getLogger(__name__)

# Global state for preview and explainability
_last_allocation_preview = None
_last_cycle_results = None
_last_explainability_snapshot = {
    "ok": True,
    "mode": "bootstrap",
    "regime": "unknown",
    "timestamp": None,
    "signals": {
        "generated": 0,
        "hard_triggers": 0,
        "soft_fallback_used": False,
        "by_strategy": {},
    },
    "ranking": {
        "ranked": 0,
        "accepted": 0,
        "rejected": 0,
        "min_score": 0.45,
        "top_scores": [],
    },
    "risk": {
        "can_trade": True,
        "risk_multiplier": 1.0,
        "reason": "normal",
    },
    "allocator": {
        "signals_in": 0,
        "decisions_out": 0,
        "reason": "init",
        "forced_fallback_used": False,
        "mode": "bootstrap",
    },
}


def normalize_stats_map(stats_map: dict) -> dict:
    """Convert dict stats to StrategyStats objects.
    
    Args:
        stats_map: Dict of strategy -> stats (dict or StrategyStats)
    
    Returns:
        Dict of strategy -> StrategyStats objects
    """
    result = {}

    for strategy, stats in stats_map.items():
        if isinstance(stats, StrategyStats):
            result[strategy] = stats
            continue

        if isinstance(stats, dict):
            result[strategy] = StrategyStats(
                win_rate=float(stats.get("win_rate", 0.5)),
                sharpe=float(stats.get("sharpe", 0.0)),
                drawdown=float(stats.get("drawdown", 0.0)),
                recent_pnl=float(stats.get("recent_pnl", 0.0)),
            )

    return result

# Scheduler state
_scheduler_task: asyncio.Task = None
_scheduler_running = False

# Trading state
_last_cycle_results = {
    "timestamp": None,
    "signals_count": 0,
    "decisions_count": 0,
    "orders_submitted": 0,
    "orders_filled": 0,
    "positions_total": 0,
}

# Week 4: Allocator V3 state
_allocator_v3 = None
_strategy_stats_service = None
_last_allocation_preview = None


def init_allocator_v3(db):
    """Initialize Allocator V3 and dependencies."""
    global _allocator_v3, _strategy_stats_service
    
    if _allocator_v3 is None:
        _allocator_v3 = StrategyAllocatorV3()
        logger.info("[Runtime] AllocatorV3 initialized")
    
    if _strategy_stats_service is None:
        _strategy_stats_service = StrategyStatsService(db)
        logger.info("[Runtime] StrategyStatsService initialized")


def get_last_allocation_preview():
    """Get cached allocation preview for UI."""
    return _last_allocation_preview or {
        "decisions": [],
        "allocator_meta": {"reason": "No allocations yet"}
    }


async def run_trading_cycle_v3() -> Dict[str, Any]:
    """Run trading cycle with full Brain integration.
    
    Week 5 Flow (Brain Integration):
    1. Get signals from Signal Engine
    2. Rank signals (AI Ranking V2 with fallback)
    3. Risk Engine gate (can_trade check)
    4. Portfolio Engine sizing (with risk_multiplier)
    5. AllocatorV3.allocate() → decisions
    6. Submit orders to exchange
    7. Cache allocation preview for UI
    
    Returns:
        Cycle results with full metadata (risk_state, ranking, portfolio)
    """
    global _last_allocation_preview
    
    logger.info("[TradingRuntimeV3] 🚀 Starting Brain-integrated cycle...")
    
    # Initialize services
    from modules.trading_core.portfolio_service import get_portfolio_service
    portfolio_service = get_portfolio_service()
    db = portfolio_service.db
    
    init_allocator_v3(db)
    risk_engine = get_risk_engine()
    portfolio_engine = get_portfolio_engine()
    
    # ═══════════════════════════════════════════════════════════════
    # STEP 1: SIGNAL GENERATION
    # ═══════════════════════════════════════════════════════════════
    from modules.signal_engine.signal_engine import SignalEngine
    from modules.market_data_live import get_market_data_service
    
    signal_engine = SignalEngine()
    market_data_service = get_market_data_service()
    
    symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT", "ADAUSDT"]
    raw_signals = []
    
    logger.info(f"[Runtime] 🔍 PIPELINE DEBUG START | Universe: {len(symbols)} symbols")
    
    for symbol in symbols:
        try:
            candles = await market_data_service.get_candles(symbol, timeframe="4h", limit=120)
            
            candles_count = len(candles) if candles else 0
            logger.info(f"[Runtime] [1/7] {symbol}: candles={candles_count}")
            
            if not candles or len(candles) < 60:
                logger.warning(f"[Runtime] Insufficient candles for {symbol}: {candles_count}")
                continue
            
            symbol_signals = signal_engine.run(symbol, "4h", candles)
            logger.info(f"[Runtime] [2/7] {symbol}: signals_generated={len(symbol_signals)}")
            
            raw_signals.extend(symbol_signals)
            
        except Exception as e:
            logger.error(f"[Runtime] Signal generation failed for {symbol}: {e}", exc_info=True)
    
    logger.info(f"[Runtime] [2/7] 📊 TOTAL RAW SIGNALS: {len(raw_signals)}")
    
    # Update explainability snapshot - Signals
    _last_explainability_snapshot["timestamp"] = datetime.now(timezone.utc).isoformat()
    _last_explainability_snapshot["signals"] = {
        "generated": len(raw_signals),
        "hard_triggers": len([s for s in raw_signals if s.strategy != "soft_fallback_v1"]),
        "soft_fallback_used": any(s.strategy == "soft_fallback_v1" for s in raw_signals),
        "by_strategy": {
            "trend": len([s for s in raw_signals if "trend" in s.strategy]),
            "breakout": len([s for s in raw_signals if "breakout" in s.strategy]),
            "meanrev": len([s for s in raw_signals if "meanrev" in s.strategy]),
            "soft": len([s for s in raw_signals if s.strategy == "soft_fallback_v1"]),
        }
    }
    
    # ═══════════════════════════════════════════════════════════════
    # STEP 2: GET PORTFOLIO STATE + STATS
    # ═══════════════════════════════════════════════════════════════
    portfolio_state = await portfolio_service.get_portfolio_state()
    open_positions = portfolio_state.get("positions", [])
    equity = portfolio_state.get("equity", 10000)
    drawdown = portfolio_state.get("drawdown", 0.0)
    daily_pnl = portfolio_state.get("daily_pnl", 0.0)
    risk_heat = portfolio_state.get("risk_heat", 0.0)
    
    logger.info(
        f"[Runtime] 💼 Portfolio: equity=${equity:,.2f}, dd={drawdown:.2%}, "
        f"daily_pnl=${daily_pnl:,.2f}, heat={risk_heat:.2%}, positions={len(open_positions)}"
    )
    
    stats_map_raw = await _strategy_stats_service.get_stats_map()
    stats_map_dict = {k: v.__dict__ if hasattr(v, '__dict__') else v for k, v in stats_map_raw.items()}
    logger.info(f"[Runtime] 📈 Loaded stats for {len(stats_map_dict)} strategies")
    
    # ═══════════════════════════════════════════════════════════════
    # STEP 3: SIGNAL RANKING + FALLBACK
    # ═══════════════════════════════════════════════════════════════
    # Convert TradingSignal → dict for ranking
    signals_for_ranking = []
    signal_vol_map = {}
    
    for s in raw_signals:
        signals_for_ranking.append({
            "symbol": s.symbol,
            "strategy": s.strategy,
            "side": s.direction,
            "entry": s.entry,
            "stop": s.stop,
            "target": s.target,
            "confidence": s.confidence,
        })
        signal_vol_map[s.symbol] = s.asset_vol
    
    logger.info(f"[Runtime] [3/7] Converted {len(signals_for_ranking)} signals for ranking")
    
    # Build execution map
    execution_map = {}
    for sig_dict in signals_for_ranking:
        execution_map[sig_dict["symbol"]] = {
            "expected_slippage_bps": 5.0,
            "expected_latency_ms": 120.0,
            "volatility": signal_vol_map.get(sig_dict["symbol"], 0.025),
        }
    
    # Detect regime
    market_data = {"volatility": 0.025, "trend_strength": 0.6}
    regime = detect_regime(market_data)
    logger.info(f"[Runtime] [3/7] 🌍 Market regime: {regime}")
    
    # RANK SIGNALS (with fallback)
    ranked_signals = rank_signals(
        signals=signals_for_ranking,
        stats_map=stats_map_dict,
        execution_map=execution_map,
        regime=regime,
        portfolio=portfolio_state,
        open_positions=open_positions,
        min_score=0.45,
    )
    
    accepted_signals = [r for r in ranked_signals if r.accepted]
    
    logger.info(
        f"[Runtime] [4/7] 🎯 Ranking: {len(ranked_signals)} total, "
        f"{len(accepted_signals)} accepted (min_score=0.45)"
    )
    
    # Update explainability snapshot - Ranking
    _last_explainability_snapshot["ranking"] = {
        "ranked": len(ranked_signals),
        "accepted": len(accepted_signals),
        "rejected": len(ranked_signals) - len(accepted_signals),
        "min_score": 0.45,
        "top_scores": [
            {
                "symbol": r.symbol,
                "strategy": r.strategy,
                "score": round(r.final_score, 4),
                "accepted": r.accepted,
                "bucket": r.confidence_bucket,
            }
            for r in ranked_signals[:5]
        ],
    }
    _last_explainability_snapshot["regime"] = regime
    
    # EARLY EXIT: No valid signals after ranking + fallback
    if len(accepted_signals) == 0:
        logger.warning("[Runtime] ⚠️ No valid signals after ranking + fallback")
        
        _last_allocation_preview = {
            "decisions": [],
            "allocator_meta": {
                "reason": "no_valid_signals_after_fallback",
                "ranking": {
                    "min_score": 0.45,
                    "ranked_count": len(ranked_signals),
                    "accepted_count": 0,
                    "fallback_used": True,
                },
                "portfolio": {
                    "equity": equity,
                    "drawdown": drawdown,
                    "risk_heat": risk_heat,
                    "positions_count": len(open_positions),
                }
            }
        }
        
        global _last_cycle_results
        _last_cycle_results = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "signals_count": len(raw_signals),
            "decisions_count": 0,
            "orders_submitted": 0,
            "orders_filled": 0,
            "positions_total": len(open_positions),
            "reason": "no_valid_signals_after_fallback",
        }
        
        return _last_cycle_results
    
    # ═══════════════════════════════════════════════════════════════
    # STEP 4: RISK ENGINE GATE
    # ═══════════════════════════════════════════════════════════════
    # Get metrics for risk evaluation
    events_service = get_events_service()
    
    # TODO: Get real metrics from events/portfolio
    # For now, use safe defaults
    metrics = {
        "trades_last_hour": 0,
        "trades_today": 0,
    }
    
    market_volatility = signal_vol_map.get("BTCUSDT", 0.025)  # Use BTC vol as proxy
    
    risk_state = risk_engine.evaluate(
        portfolio=portfolio_state,
        metrics=metrics,
        market_volatility=market_volatility,
    )
    
    logger.info(
        f"[Runtime] 🛡️ Risk Engine: can_trade={risk_state.can_trade}, "
        f"risk_multiplier={risk_state.risk_multiplier:.2f}, reason={risk_state.reason}"
    )
    
    # Update explainability snapshot - Risk
    _last_explainability_snapshot["risk"] = {
        "can_trade": risk_state.can_trade,
        "risk_multiplier": risk_state.risk_multiplier,
        "reason": risk_state.reason,
    }
    
    # RISK GATE: Stop trading if can_trade=False
    if not risk_state.can_trade:
        logger.warning(
            f"[Runtime] 🛑 RISK STOP: {risk_state.reason} | "
            f"restrictions={risk_state.restrictions}"
        )
        
        # Map risk_state.reason to canonical UI reason
        stop_reason_map = {
            "daily_loss_limit": "daily_loss_limit",
            "drawdown_circuit_breaker": "drawdown_limit",
            "high_portfolio_heat": "overheat",
            "high_volatility": "volatility_shutdown",
        }
        
        canonical_reason = stop_reason_map.get(
            risk_state.reason.split("_")[0] + "_" + risk_state.reason.split("_")[1] 
            if "_" in risk_state.reason else risk_state.reason,
            risk_state.reason  # fallback to raw reason
        )
        
        _last_allocation_preview = {
            "decisions": [],
            "allocator_meta": {
                "reason": canonical_reason,
                "risk_state": {
                    "can_trade": False,
                    "risk_multiplier": risk_state.risk_multiplier,
                    "reason": risk_state.reason,
                    "restrictions": risk_state.restrictions,
                    "max_positions": risk_state.max_positions,
                    "max_size_per_trade": risk_state.max_size_per_trade,
                },
                "ranking": {
                    "min_score": 0.45,
                    "ranked_count": len(ranked_signals),
                    "accepted_count": len(accepted_signals),
                },
                "portfolio": {
                    "equity": equity,
                    "drawdown": drawdown,
                    "daily_pnl": daily_pnl,
                    "risk_heat": risk_heat,
                    "positions_count": len(open_positions),
                }
            }
        }
        
        _last_cycle_results = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "signals_count": len(raw_signals),
            "decisions_count": 0,
            "orders_submitted": 0,
            "orders_filled": 0,
            "positions_total": len(open_positions),
            "reason": canonical_reason,
            "risk_stop": True,
        }
        
        return _last_cycle_results
    
    # ═══════════════════════════════════════════════════════════════
    # STEP 5: CONVERT RANKED SIGNALS → Signal objects for Allocator
    # ═══════════════════════════════════════════════════════════════
    from modules.strategy.types import Signal
    
    allocator_signals = []
    for r in accepted_signals:
        stop_distance = abs((r.entry - r.stop) / r.entry) if r.entry and r.stop and r.entry != 0 else 0.01
        
        allocator_signals.append(Signal(
            symbol=r.symbol,
            side=r.side,
            confidence=r.confidence,
            stop_distance=stop_distance,
            source=r.strategy,
            entry_price=r.entry,
            stop_price=r.stop,
            target_price=r.target,
        ))
    
    logger.info(f"[Runtime] [5/7] Converted {len(allocator_signals)} accepted signals → Signal objects")
    
    # ═══════════════════════════════════════════════════════════════
    # STEP 6: ALLOCATOR V3 (with risk_multiplier applied)
    # ═══════════════════════════════════════════════════════════════
    stats_map = normalize_stats_map(stats_map_raw)
    
    logger.info(f"[Runtime] [6/7] Passing {len(allocator_signals)} signals to Allocator V3")
    
    allocation = _allocator_v3.allocate(
        signals=allocator_signals,
        stats_map=stats_map,
        portfolio=portfolio_state,
        execution_map=execution_map,
        regime=regime,
        open_positions=open_positions,
    )
    
    decisions = allocation["decisions"]
    allocator_meta = allocation["allocator_meta"]
    
    logger.info(f"[Runtime] [6/7] ✅ Allocator V3 returned {len(decisions)} decisions")
    
    # Update explainability snapshot - Allocator
    allocator_debug = allocator_meta.get("allocator_debug", {})
    _last_explainability_snapshot["allocator"] = {
        "signals_in": len(allocator_signals),
        "decisions_out": len(decisions),
        "reason": allocator_meta.get("reason", "unknown"),
        "forced_fallback_used": allocator_debug.get("forced_fallback_used", False),
        "mode": allocator_meta.get("mode", "PRODUCTION"),
    }
    _last_explainability_snapshot["mode"] = allocator_meta.get("mode", "PRODUCTION").lower()
    
    # CRITICAL DEBUG: If 0 decisions but signals passed
    if len(allocator_signals) > 0 and len(decisions) == 0:
        logger.error(
            f"[Runtime] ❌ CRITICAL: Allocator killed all signals! "
            f"signals_in={len(allocator_signals)}, decisions_out=0, "
            f"reason={allocator_meta.get('reason', 'unknown')}"
        )
    
    # APPLY RISK_MULTIPLIER TO SIZING
    for d in decisions:
        original_size = d["size_usd"]
        d["size_usd"] = original_size * risk_state.risk_multiplier
        d["risk_adjusted"] = True
        d["risk_multiplier_applied"] = risk_state.risk_multiplier
        d["original_size_usd"] = original_size
    
    logger.info(
        f"[Runtime] [7/7] 💰 Final: {len(decisions)} decisions | "
        f"Risk multiplier: {risk_state.risk_multiplier:.2f}x"
    )
    
    # Cache preview with FULL metadata
    _last_allocation_preview = {
        "decisions": decisions,
        "allocator_meta": {
            **allocator_meta,
            "risk_state": {
                "can_trade": risk_state.can_trade,
                "risk_multiplier": risk_state.risk_multiplier,
                "reason": risk_state.reason,
                "max_positions": risk_state.max_positions,
                "max_size_per_trade": risk_state.max_size_per_trade,
            },
            "ranking": {
                "min_score": 0.45,
                "ranked_count": len(ranked_signals),
                "accepted_count": len(accepted_signals),
                "fallback_used": any("FALLBACK" in r.rank_reason for r in ranked_signals),
            },
            "portfolio": {
                "equity": equity,
                "drawdown": drawdown,
                "daily_pnl": daily_pnl,
                "risk_heat": risk_heat,
                "positions_count": len(open_positions),
            }
        }
    }
    
    # ═══════════════════════════════════════════════════════════════
    # STEP 7: SUBMIT ORDERS
    # ═══════════════════════════════════════════════════════════════
    submitted = 0
    filled = 0
    
    for d in decisions:
        try:
            order_request = OrderRequest(
                symbol=d["symbol"],
                side="BUY" if d["side"] == "LONG" else "SELL",
                order_type="MARKET",
                quantity=round(d["size_usd"] / 60000.0, 6),
                client_order_id=f'{d["strategy"]}-{d["symbol"]}-{submitted}',
            )
            
            adapter = exchange_service.get_adapter()
            order_response = await adapter.place_order(order_request)
            submitted += 1
            
            current_mode = exchange_service.get_mode()
            
            if current_mode == "PAPER":
                if order_response.success and order_response.status == "FILLED":
                    await portfolio_service.apply_fill(order_response)
                    filled += 1
                    
                    logger.info(
                        f"[Runtime] ✅ PAPER filled: {d['symbol']} {d['side']} "
                        f"${d['size_usd']:.2f} @ ${order_response.avg_fill_price:.2f}"
                    )
            else:
                logger.info(
                    f"[Runtime] ✅ TESTNET submitted: {d['symbol']} "
                    f"order_id={order_response.order_id}"
                )
            
            await events_service.log_event("BRAIN_ORDER", d["symbol"], {
                "strategy": d["strategy"],
                "score": d["score"],
                "risk_multiplier": risk_state.risk_multiplier,
                "original_size_usd": d.get("original_size_usd"),
                "final_size_usd": d["size_usd"],
                "order_id": order_response.order_id if order_response.success else None,
            })
            
        except Exception as e:
            logger.error(f"[Runtime] Order failed for {d['symbol']}: {e}")
    
    # ═══════════════════════════════════════════════════════════════
    # STEP 8: UPDATE RESULTS
    # ═══════════════════════════════════════════════════════════════
    _last_cycle_results = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "signals_count": len(raw_signals),
        "decisions_count": len(decisions),
        "orders_submitted": submitted,
        "orders_filled": filled,
        "positions_total": len(open_positions),
        "allocator_version": "V3_BRAIN",
        "regime": allocator_meta.get("regime"),
        "risk_multiplier": risk_state.risk_multiplier,
        "drawdown": drawdown,
    }
    
    logger.info(
        f"[Runtime] ✅ Cycle complete: {submitted} orders, {filled} filled | "
        f"Risk: {risk_state.risk_multiplier:.2f}x"
    )
    
    return _last_cycle_results


async def run_trading_cycle() -> Dict[str, Any]:
    """Run complete trading cycle.
    
    Week 3 Flow:
    1. Run market scanner (get signals)
    2. Make decisions for each signal
    3. Submit orders to exchange (NOT in-memory positions)
    4. Apply fills to portfolio
    5. Update portfolio metrics
    
    Returns:
        Cycle results summary
    """
    logger.info("[TradingRuntime] Starting trading cycle...")
    
    # Step 1: Get signals
    try:
        signals_data = await run_scanner()
    except Exception as e:
        logger.error(f"[TradingRuntime] Scanner failed: {e}")
        signals_data = []
    
    signals_count = len(signals_data)
    logger.info(f"[TradingRuntime] Signals: {signals_count}")
    
    # Step 2: Get current portfolio state
    portfolio_service = get_portfolio_service()
    portfolio_state = await portfolio_service.get_portfolio_state()
    
    # Check max positions limit
    max_positions = 5  # TODO: make configurable
    current_positions = len(portfolio_state.get("positions", []))
    
    if current_positions >= max_positions:
        logger.warning(
            f"[TradingRuntime] Max positions limit reached: {current_positions}/{max_positions}"
        )
        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "signals_count": signals_count,
            "decisions_count": 0,
            "orders_submitted": 0,
            "orders_filled": 0,
            "positions_total": current_positions,
            "reason": "max_positions_limit",
        }
    
    # Step 3: Make decisions
    decisions = []
    events_service = get_events_service()
    
    for signal in signals_data:
        # Log signal detected
        await events_service.log_event("SIGNAL_DETECTED", signal["symbol"], {
            "strategy": signal.get("strategy"),
            "direction": signal.get("direction"),
            "confidence": signal.get("confidence"),
        })
        
        decision = await make_decision(signal, portfolio_state)  # NOW ASYNC
        
        if decision.get("action") == "OPEN":
            decisions.append(decision)
            
            # Log decision made WITH mark_price_at_decision
            await events_service.log_event("DECISION_MADE", decision["symbol"], {
                "action": "OPEN",
                "side": decision["side"],
                "size": decision["size"],
                "entry": decision.get("entry"),
                "stop": decision.get("stop"),
                "target": decision.get("target"),
                "confidence": decision.get("confidence"),
                "mark_price_at_decision": decision.get("mark_price_at_decision"),  # ADDED
            })
    
    logger.info(f"[TradingRuntime] Decisions (OPEN): {len(decisions)}")
    
    # Step 4: Submit orders to exchange (NEW: Week 3)
    if not exchange_service.is_connected():
        logger.error("[TradingRuntime] Exchange not connected! Cannot submit orders.")
        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "signals_count": signals_count,
            "decisions_count": len(decisions),
            "orders_submitted": 0,
            "orders_filled": 0,
            "positions_total": current_positions,
            "error": "exchange_not_connected",
        }
    
    adapter = exchange_service.get_adapter()
    
    orders_submitted = 0
    orders_filled = 0
    available_slots = max_positions - current_positions
    
    for decision in decisions[:available_slots]:
        try:
            # Convert decision → OrderRequest
            order_request = OrderRequest(
                symbol=decision["symbol"],
                side="BUY" if decision["side"] == "LONG" else "SELL",
                order_type="MARKET",
                quantity=decision["size"],
                client_order_id=f"decision-{decision['symbol']}-{int(datetime.now().timestamp())}",
                stop_loss=decision.get("stop"),
                take_profit=decision.get("target"),
            )
            
            # Log order submitted
            await events_service.log_event("ORDER_SUBMITTED", decision["symbol"], {
                "order_type": "MARKET",
                "side": order_request.side,
                "quantity": order_request.quantity,
            })
            
            # Submit to exchange
            order_response = await adapter.place_order(order_request)
            orders_submitted += 1
            
            # CRITICAL: Differentiate PAPER vs TESTNET execution flow
            # PAPER: Instant fill (simulated), apply immediately
            # TESTNET: Real exchange, FillSyncService will handle fills later
            current_mode = exchange_service.get_mode()
            
            if current_mode == "PAPER":
                # PAPER MODE: Apply fill immediately (synchronous simulation)
                if order_response.success and order_response.status == "FILLED":
                    # Log order filled
                    await events_service.log_event("ORDER_FILLED", decision["symbol"], {
                        "order_id": order_response.order_id,
                        "filled_quantity": order_response.filled_quantity,
                        "avg_fill_price": order_response.avg_fill_price,
                    })
                    
                    # Apply fill to portfolio
                    await portfolio_service.apply_fill(order_response)
                    orders_filled += 1
                    
                    # Log position opened
                    await events_service.log_event("POSITION_OPENED", decision["symbol"], {
                        "side": decision["side"],
                        "size": decision["size"],
                        "entry_price": order_response.avg_fill_price,
                    })
                    
                    logger.info(
                        f"[TradingRuntime] ✅ PAPER Order filled: {decision['symbol']} "
                        f"{decision['side']} {decision['size']:.4f} @ ${order_response.avg_fill_price:.2f}"
                    )
                else:
                    logger.warning(
                        f"[TradingRuntime] ⚠️ PAPER Order not filled: {decision['symbol']} "
                        f"status={order_response.status}"
                    )
            
            else:
                # TESTNET MODE: Order submitted to real exchange
                # DO NOT create position here! FillSyncService will poll fills and apply them
                if order_response.success:
                    logger.info(
                        f"[TradingRuntime] ✅ TESTNET Order submitted: {decision['symbol']} "
                        f"{decision['side']} {decision['size']:.4f} "
                        f"order_id={order_response.order_id} status={order_response.status}"
                    )
                    logger.info(
                        f"[TradingRuntime] ⏳ Waiting for FillSyncService to process fill from exchange..."
                    )
                else:
                    logger.error(
                        f"[TradingRuntime] ❌ TESTNET Order submission failed: {decision['symbol']}"
                    )
        
        except Exception as e:
            logger.error(f"[TradingRuntime] Failed to submit order: {e}", exc_info=True)
    
    # Step 5: Get updated portfolio state
    updated_portfolio = await portfolio_service.get_portfolio_state()
    
    # Results
    result = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "signals_count": signals_count,
        "decisions_count": len(decisions),
        "orders_submitted": orders_submitted,
        "orders_filled": orders_filled,
        "positions_total": len(updated_portfolio.get("positions", [])),
    }
    
    global _last_cycle_results
    _last_cycle_results = result
    
    logger.info(
        f"[TradingRuntime] Cycle complete: "
        f"signals={signals_count}, decisions={len(decisions)}, "
        f"orders_submitted={orders_submitted}, filled={orders_filled}, "
        f"positions={result['positions_total']}"
    )
    
    return result


async def _scheduler_loop():
    """Background scheduler loop (runs every 60 seconds)."""
    global _scheduler_running
    
    while _scheduler_running:
        try:
            await run_trading_cycle()
        except Exception as e:
            logger.error(f"[TradingScheduler] Cycle error: {e}", exc_info=True)
        
        # Wait 60 seconds before next cycle
        await asyncio.sleep(60)


def start_trading_scheduler():
    """Start background trading scheduler."""
    global _scheduler_task, _scheduler_running
    
    if _scheduler_running:
        logger.warning("[TradingScheduler] Already running")
        return
    
    _scheduler_running = True
    _scheduler_task = asyncio.create_task(_scheduler_loop())
    logger.info("[TradingScheduler] ✅ Started (60s interval)")


def stop_trading_scheduler():
    """Stop background trading scheduler."""
    global _scheduler_task, _scheduler_running
    
    if not _scheduler_running:
        logger.warning("[TradingScheduler] Not running")
        return
    
    _scheduler_running = False
    if _scheduler_task:
        _scheduler_task.cancel()
    
    logger.info("[TradingScheduler] Stopped")


def get_last_cycle_results() -> Dict[str, Any]:
    """Get results from last trading cycle."""
    return _last_cycle_results.copy()



def get_last_explainability_snapshot() -> Dict[str, Any]:
    """Get last explainability snapshot for System UI."""
    global _last_explainability_snapshot
    return _last_explainability_snapshot.copy()
