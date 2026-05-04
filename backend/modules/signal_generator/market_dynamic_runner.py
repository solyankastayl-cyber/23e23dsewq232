"""
Market Dynamic Experiment Runner
=================================

Phase 2.2 - Universe Scanner Plumbing

Connects universe scanner to market_dynamic experiment.
DOES NOT execute trades - only scans and logs eligible assets.

Architecture:
- Isolated from baseline_btc runner
- ONLY scanner invocation
- NO signal generation (comes in Phase 2.3)
- NO execution (dry-run only)
"""

import asyncio
import logging
import sys
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List

logger = logging.getLogger(__name__)


class MarketDynamicRunner:
    """
    Market Dynamic experiment runner.
    
    Phase 2.2: Scanner plumbing ✅
    Phase 2.3: Multi-signal build (IN PROGRESS)
    - Scans market universe
    - Generates signals for each eligible asset
    - Logs signal metadata
    - NO execution
    """
    
    def __init__(self, market_data_service=None, interval_seconds: int = 60, db=None):
        """
        Args:
            market_data_service: MarketDataService for fetching prices
            interval_seconds: Scan frequency (default 60s)
            db: MongoDB database (for snapshot storage)
        """
        self.interval = interval_seconds
        self.experiment_id = "market_dynamic"
        self.market_data = market_data_service
        self.db = db  # PHASE 2.5: Database for snapshots
        
        # Phase 2.2: Scan history
        self.scan_history: List[Dict[str, Any]] = []
        
        # Phase 2.3: Signal history (SEPARATE from scan!)
        self.signal_history: List[Dict[str, Any]] = []
        
        self.max_history = 100  # Keep last 100 scans
        
        # Control
        self._task: Optional[asyncio.Task] = None
        self._running = False
        
        logger.info(
            f"✅ [MarketDynamic] Runner initialized: interval={interval_seconds}s, "
            f"market_data={'available' if market_data_service else 'not available'}, "
            f"db={'available' if db is not None else 'not available'}"
        )
    
    def _classify_cluster(self, symbol: str) -> str:
        """
        Classify trading pair into cluster for feature analysis.
        
        PHASE A.2: Simple rule-based classification
        - majors: BTC, ETH
        - alts: everything else
        - stable: USDC, DAI (not in universe yet)
        """
        symbol_upper = symbol.upper()
        
        if symbol_upper in ["BTCUSDT", "ETHUSDT"]:
            return "majors"
        elif symbol_upper in ["USDCUSDT", "DAIUSDT", "USDTUSDT"]:
            return "stable"
        else:
            return "alts"
    
    def _classify_alignment(self, confidence: float) -> str:
        """
        Classify signal alignment based on confidence.
        
        PHASE A.2: Simple threshold-based classification
        - aligned: confidence >= 0.65 (multi-timeframe agreement)
        - divergent: confidence < 0.65 (weak signal)
        """
        return "aligned" if confidence >= 0.65 else "divergent"
    
    async def start(self):
        """Start background loop."""
        if self._running:
            logger.warning("[MarketDynamic] Already running")
            return
        
        self._running = True
        self._task = asyncio.create_task(self._loop())
        logger.info("[MarketDynamic] Started")
    
    async def stop(self):
        """Stop background loop."""
        if not self._running:
            return
        
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        
        logger.info("[MarketDynamic] Stopped")
    
    async def _loop(self):
        """Main scanner loop."""
        print("[MarketDynamic] _loop() STARTING...", file=sys.stderr, flush=True)
        
        from modules.market_intelligence.universe_scanner import scan_market_universe
        
        logger.info("[MarketDynamic] Loop started (scanner + signals)")
        
        iteration = 0
        
        while self._running:
            iteration += 1
            print(
                f"[MarketDynamic] Iteration {iteration} starting...",
                file=sys.stderr, flush=True
            )
            
            try:
                # ═══════════════════════════════════════
                # PHASE 2.2: SCANNER INVOCATION
                # ═══════════════════════════════════════
                
                scan_start = datetime.now(timezone.utc)
                
                # Call scanner
                universe_snapshots = await scan_market_universe()
                
                # Filter eligible assets
                eligible_assets = [
                    snap for snap in universe_snapshots if snap.get("eligible", False)
                ]
                
                scan_duration_ms = (datetime.now(timezone.utc) - scan_start).total_seconds() * 1000
                
                # ═══════════════════════════════════════
                # PHASE 2.2: SCAN METADATA (SEPARATE)
                # ═══════════════════════════════════════
                
                scan_metadata = {
                    "timestamp": scan_start.isoformat(),
                    "experiment_id": self.experiment_id,
                    "eligible_count": len(eligible_assets),
                    "total_scanned": len(universe_snapshots),
                    "filtered_out_reasons": self._get_filter_reasons(universe_snapshots),
                    "scan_duration_ms": round(scan_duration_ms, 2),
                }
                
                # Store scan history (SEPARATE from signals)
                self.scan_history.append(scan_metadata)
                if len(self.scan_history) > self.max_history:
                    self.scan_history.pop(0)
                
                # Log scan results
                logger.info(
                    f"[MarketDynamic] Scan complete: "
                    f"{len(eligible_assets)}/{len(universe_snapshots)} eligible "
                    f"(duration: {scan_duration_ms:.2f}ms)"
                )
                
                # ═══════════════════════════════════════
                # PHASE 2.3: MULTI-SIGNAL GENERATION
                # ═══════════════════════════════════════
                
                if eligible_assets and self.market_data:
                    signal_result = await self._generate_signals(eligible_assets)
                    
                    # Store signal history (SEPARATE from scan)
                    self.signal_history.append(signal_result)
                    if len(self.signal_history) > self.max_history:
                        self.signal_history.pop(0)
                    
                    # Log signal results
                    logger.info(
                        f"[MarketDynamic] Signals generated: "
                        f"{signal_result['signals_generated']}/{len(eligible_assets)} "
                        f"(unique_symbols: {signal_result['unique_symbols']}, "
                        f"pool_size: {signal_result['pool_size']})"
                    )
                    
                    # ═══════════════════════════════════════
                    # PHASE 2.4: RANKING + ALLOCATION
                    # ═══════════════════════════════════════
                    
                    if signal_result['signals_generated'] > 0:
                        preview_result = await self._rank_and_allocate(
                            signal_result['raw_signals'],
                            eligible_assets
                        )
                        
                        # Store preview (FINAL result for this cycle)
                        self.preview_history = getattr(self, 'preview_history', [])
                        self.preview_history.append(preview_result)
                        if len(self.preview_history) > self.max_history:
                            self.preview_history.pop(0)
                        
                        # Log preview results
                        logger.info(
                            f"[MarketDynamic] Preview: "
                            f"{preview_result['selected_count']}/{preview_result['signals_total']} selected, "
                            f"market_bias={preview_result['market_bias']}, "
                            f"structure={preview_result['market_structure']['alignment']}"
                        )
                        
                        # ═══════════════════════════════════════
                        # PHASE 2.5: SNAPSHOT STORAGE
                        # ═══════════════════════════════════════
                        
                        if self.db:
                            try:
                                from modules.strategy.snapshot_storage import save_snapshot
                                from modules.strategy.shadow_trade_service import ShadowTradeService
                                
                                # Save snapshot (returns snapshot with _id)
                                snapshot = await save_snapshot(
                                    self.db,
                                    preview_result,
                                    scan_metadata=scan_metadata,
                                    signal_metadata=signal_result
                                )
                                
                                # PHASE 2.6: Create shadow trades
                                shadow_service = ShadowTradeService(self.db)
                                trade_ids = await shadow_service.create_from_snapshot(snapshot)
                                
                                logger.debug(
                                    f"[MarketDynamic] Snapshot saved: {snapshot['_id']}, "
                                    f"shadow trades: {len(trade_ids)}"
                                )
                            except Exception as e:
                                logger.error(f"[MarketDynamic] Snapshot/Shadow save failed: {e}")
                        else:
                            logger.debug("[MarketDynamic] No DB, skipping snapshot")
                    else:
                        logger.debug("[MarketDynamic] No signals to rank/allocate")
                    
                    # Print detailed signal metadata
                    print(
                        f"\n[MarketDynamic] SIGNAL METADATA:\n"
                        f"  Signals generated: {signal_result['signals_generated']}\n"
                        f"  Unique symbols: {signal_result['unique_symbols']}\n"
                        f"  Pool size: {signal_result['pool_size']}\n"
                        f"  Top signals: {signal_result['top_signals'][:3]}\n"
                        f"  Skipped: {signal_result['skipped']}\n",
                        file=sys.stderr,
                        flush=True
                    )
                else:
                    if not eligible_assets:
                        logger.debug("[MarketDynamic] No eligible assets, skipping signal generation")
                    if not self.market_data:
                        logger.warning("[MarketDynamic] No market_data service, skipping signal generation")
                
                # ═══════════════════════════════════════
                # PHASE 2.2: NO FALLBACK
                # ═══════════════════════════════════════
                
                # If no eligible assets, just log and continue
                # DO NOT fallback to BTC
                if not eligible_assets:
                    logger.debug("[MarketDynamic] Empty scan, no fallback")
                
                # ═══════════════════════════════════════
                # PHASE 2.2: NO SIGNAL GENERATION
                # ═══════════════════════════════════════
                
                # Signal generation comes in Phase 2.3
                # For now, we only scan
                
                # ═══════════════════════════════════════
                # PHASE 2.2: NO EXECUTION
                # ═══════════════════════════════════════
                
                # Execution stays disabled until baseline completes
                
            except asyncio.CancelledError:
                logger.info("[MarketDynamic] Loop cancelled")
                break
            except Exception as e:
                logger.error(f"[MarketDynamic] Loop error: {e}", exc_info=True)
            
            # Sleep
            await asyncio.sleep(self.interval)
    
    def _get_filter_reasons(self, snapshots: List[Dict]) -> Dict[str, int]:
        """Count filter-out reasons."""
        reasons = {}
        for snap in snapshots:
            if not snap.get("eligible", False):
                reason = snap.get("reason", "unknown")
                reasons[reason] = reasons.get(reason, 0) + 1
        return reasons
    
    async def _generate_signals(self, eligible_assets: List[Dict]) -> Dict[str, Any]:
        """
        PHASE 2.3: Generate signals for all eligible assets.
        
        Uses MultiAssetGenerator (NO same_side filtering).
        Pure signal generation - filtering happens in ranking layer.
        
        КОРРЕКЦИЯ №2: symbol+timeframe key
        КОРРЕКЦИЯ №3: Explicit deduplication
        КОРРЕКЦИЯ №4: Normalized signal structure
        КОРРЕКЦИЯ №5: Skipped reasons (no_signal, duplicate, error)
        КОРРЕКЦИЯ №6: Pool size control
        
        Args:
            eligible_assets: List of eligible asset snapshots from scanner
            
        Returns:
            Signal generation metadata
        """
        from modules.signal_generator.multi_asset_generator import (
            get_multi_generator, get_pool_size
        )
        
        signals = []
        seen = set()  # КОРРЕКЦИЯ №3: Explicit deduplication
        skipped = {
            "no_signal": 0,
            "duplicate": 0,
            "error": 0,
        }
        
        generation_start = datetime.now(timezone.utc)
        
        for asset in eligible_assets:
            symbol = asset["symbol"]
            timeframe = asset["timeframe"]
            
            # КОРРЕКЦИЯ №3: Deduplication check
            key = (symbol, timeframe)
            if key in seen:
                skipped["duplicate"] += 1
                continue
            seen.add(key)
            
            try:
                # КОРРЕКЦИЯ №2: symbol+timeframe key for generator
                generator_key = f"{symbol}_{timeframe}"
                generator = get_multi_generator(generator_key)
                
                # PHASE 2.3: Pre-load history if generator is new (empty)
                if len(generator.prices) == 0:
                    # Load recent candles to bootstrap history
                    try:
                        from modules.scanner.market_data.binance_provider import get_market_data_provider
                        provider = get_market_data_provider()
                        
                        # PHASE A.5 FIX: Load enough candles for MA20 trend filter (need 20+)
                        limit = max(25, generator.trend_period + 5)
                        candles = await asyncio.to_thread(
                            provider.get_candles,
                            symbol,
                            timeframe,
                            limit=limit
                        )
                        
                        if candles and len(candles) >= generator.trend_period:
                            # Add last N prices to generator
                            for candle in candles[-(limit):]:
                                generator.add_price(candle["close"])
                            
                            logger.debug(
                                f"[MarketDynamic] Pre-loaded {len(generator.prices)} prices "
                                f"for {generator_key} (MA{generator.trend_period} filter)"
                            )
                        else:
                            logger.warning(
                                f"[MarketDynamic] Insufficient candles for {generator_key}: "
                                f"got {len(candles) if candles else 0}, need {generator.trend_period}"
                            )
                    except Exception as e:
                        logger.warning(
                            f"[MarketDynamic] Failed to pre-load for {generator_key}: {e}"
                        )
                
                # Get current price from market_data
                # Note: BinanceProvider.get_last_price is sync, call without await
                current_price = self.market_data.get_last_price(
                    symbol, timeframe=timeframe.lower()
                )
                
                if current_price is None:
                    skipped["no_signal"] += 1
                    continue
                
                # Generate signal (MultiAssetGenerator ALWAYS generates, no same_side)
                raw_signal = generator.generate_signal(current_price)
                
                if not raw_signal:
                    skipped["no_signal"] += 1
                    continue
                
                # КОРРЕКЦИЯ №4: Normalize signal structure
                normalized_signal = {
                    "symbol": symbol,
                    "timeframe": timeframe,
                    "side": raw_signal.get("side", "BUY"),
                    "confidence": raw_signal.get("confidence", 0.6),
                    "price": raw_signal.get("price", current_price),
                    "source": raw_signal.get("source", "multi_asset"),
                    "timestamp": raw_signal.get("timestamp", datetime.now(timezone.utc).isoformat()),
                    # PHASE A.2: Feature Integrity - add metadata for filtering
                    "cluster": self._classify_cluster(symbol),
                    "alignment": self._classify_alignment(raw_signal.get("confidence", 0.6)),
                }
                
                signals.append(normalized_signal)
                
            except Exception as e:
                skipped["error"] += 1
                logger.error(
                    f"[MarketDynamic] Signal generation error for {symbol}:{timeframe}: {e}"
                )
        
        generation_duration_ms = (
            datetime.now(timezone.utc) - generation_start
        ).total_seconds() * 1000
        
        # КОРРЕКЦИЯ №6: Pool size control
        pool_size = get_pool_size()
        unique_keys_this_cycle = len(seen)
        
        # Count unique symbols in generated signals
        unique_symbols = len(set(s["symbol"] for s in signals))
        
        # Top signals (first 5)
        top_signals = signals[:5]
        
        # Check for symbol dominance (for Phase 2.4 planning)
        symbol_counts = {}
        for sig in signals:
            sym = sig["symbol"]
            symbol_counts[sym] = symbol_counts.get(sym, 0) + 1
        
        dominant_symbol = None
        dominant_percentage = 0.0
        if signals:
            max_count_symbol = max(symbol_counts.items(), key=lambda x: x[1])[0]
            dominant_count = symbol_counts[max_count_symbol]
            dominant_percentage = (dominant_count / len(signals)) * 100
            if dominant_percentage > 50:
                dominant_symbol = max_count_symbol
        
        return {
            "timestamp": generation_start.isoformat(),
            "experiment_id": self.experiment_id,
            "signals_generated": len(signals),
            "unique_symbols": unique_symbols,
            "pool_size": pool_size,
            "unique_keys_this_cycle": unique_keys_this_cycle,
            "top_signals": top_signals,
            "skipped": skipped,
            "generation_duration_ms": round(generation_duration_ms, 2),
            "dominant_symbol": dominant_symbol,
            "dominant_percentage": round(dominant_percentage, 2) if dominant_symbol else 0.0,
            "symbol_distribution": symbol_counts,
            "raw_signals": signals,  # PHASE 2.4: Add raw signals for ranking
            "signals": signals,  # PHASE 3.2: Also expose as 'signals' for compatibility
        }
    
    async def _rank_and_allocate(
        self,
        signals: List[Dict],
        eligible_assets: List[Dict]
    ) -> Dict[str, Any]:
        """
        PHASE 2.4: Rank and allocate signals.
        PHASE 2.7A: Use dynamic constraints.
        
        Pipeline:
          signals → rank → filter → DYNAMIC CONSTRAINTS → allocate → preview
        
        Returns:
            Preview snapshot with selected positions
        """
        from modules.strategy.market_dynamic_ranking import rank_market_dynamic_signals
        from modules.strategy.portfolio_allocator import (
            filter_signals,
            allocate_signals,
            get_cluster_distribution
        )
        from modules.strategy.dynamic_constraints import get_dynamic_constraints
        
        ranking_start = datetime.now(timezone.utc)
        
        # Step 1: Rank signals (PHASE 2.7B: pass db for calibration)
        ranked_signals, market_bias_data = await rank_market_dynamic_signals(
            signals, eligible_assets, db=self.db
        )
        
        # Step 2: Filter low-quality signals
        filtered_signals, filter_rejected = filter_signals(
            ranked_signals,
            min_signal_score=0.55,
            max_spread_bps=500.0,
            min_volume=100_000.0
        )
        
        # Step 3: Get dynamic constraints (PHASE 2.7A)
        if self.db:
            try:
                dynamic_constraints_svc = get_dynamic_constraints(self.db)
                constraints = await dynamic_constraints_svc.get_constraints(horizon="24h")
                
                logger.info(
                    f"[MarketDynamic] Dynamic constraints: mode={constraints['mode']}, "
                    f"max_positions={constraints['max_open_positions']}, "
                    f"reason={constraints['reason']}"
                )
            except Exception as e:
                logger.warning(f"[MarketDynamic] Dynamic constraints failed: {e}, using defaults")
                # Fallback to static constraints
                constraints = {
                    "max_open_positions": 3,
                    "max_per_cluster": 2,
                    "max_per_symbol": 1,
                    "max_total_risk": 0.25,
                    "mode": "neutral",
                    "reason": "error (using defaults)"
                }
        else:
            # No DB, use static constraints
            constraints = {
                "max_open_positions": 3,
                "max_per_cluster": 2,
                "max_per_symbol": 1,
                "max_total_risk": 0.25,
                "mode": "neutral",
                "reason": "no db (static)"
            }
        
        # Step 4: Allocate within dynamic constraints
        selected_signals, alloc_rejected = allocate_signals(
            filtered_signals,
            max_open_positions=constraints["max_open_positions"],
            max_per_cluster=constraints["max_per_cluster"],
            max_per_symbol=constraints["max_per_symbol"],
            max_total_risk=constraints["max_total_risk"],
            default_risk_cost=0.05
        )
        
        ranking_duration_ms = (
            datetime.now(timezone.utc) - ranking_start
        ).total_seconds() * 1000
        
        # Compute distributions
        cluster_dist = get_cluster_distribution(selected_signals)
        
        # Calculate avg confidence
        avg_confidence = (
            sum(s["confidence"] for s in selected_signals) / len(selected_signals)
            if selected_signals else 0.0
        )
        
        # Combine rejected reasons
        rejected_total = {
            **filter_rejected,
            **alloc_rejected,
        }
        
        return {
            "timestamp": ranking_start.isoformat(),
            "experiment_id": self.experiment_id,
            "market_bias": market_bias_data["bias"],
            "market_structure": market_bias_data["structure"],  # PHASE 2.5
            "long_ratio": market_bias_data["long_ratio"],
            "short_ratio": market_bias_data["short_ratio"],
            "signals_total": len(signals),
            "signals_filtered": len(filtered_signals),
            "selected_count": len(selected_signals),
            "avg_confidence": round(avg_confidence, 4),
            "cluster_distribution": cluster_dist,
            "selected_signals": selected_signals,
            "rejected": rejected_total,
            "ranking_duration_ms": round(ranking_duration_ms, 2),
            "constraints": constraints,  # PHASE 2.7A: Include constraints used
        }
    
    def get_latest_preview(self) -> Optional[Dict[str, Any]]:
        """Get latest preview (Phase 2.4)."""
        preview_history = getattr(self, 'preview_history', [])
        if not preview_history:
            return None
        return preview_history[-1]
    
    def get_latest_signal_result(self) -> Optional[Dict[str, Any]]:
        """Get latest signal generation result."""
        if not self.signal_history:
            return None
        return self.signal_history[-1]
    
    def get_stats(self) -> Dict[str, Any]:
        """Get combined stats for monitoring."""
        latest_scan = self.get_latest_scan()
        latest_signals = self.get_latest_signal_result()
        latest_preview = self.get_latest_preview()  # PHASE 2.4
        
        return {
            "experiment_id": self.experiment_id,
            "runner_active": self._running,
            "latest_scan": latest_scan,
            "latest_signals": latest_signals,
            "latest_preview": latest_preview,  # PHASE 2.4
            "scan_history_size": len(self.scan_history),
            "signal_history_size": len(self.signal_history),
            "preview_history_size": len(getattr(self, 'preview_history', [])),  # PHASE 2.4
        }
    
    def get_latest_scan(self) -> Optional[Dict[str, Any]]:
        """Get latest scan metadata."""
        if not self.scan_history:
            return None
        return self.scan_history[-1]
    
    def get_scan_history(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get recent scan history."""
        return self.scan_history[-limit:]


# Singleton
_market_dynamic_runner: Optional[MarketDynamicRunner] = None


def get_market_dynamic_runner(market_data_service=None, db=None) -> MarketDynamicRunner:
    """Get or create singleton runner."""
    global _market_dynamic_runner
    if _market_dynamic_runner is None:
        _market_dynamic_runner = MarketDynamicRunner(
            market_data_service=market_data_service,
            db=db,  # PHASE 2.5
            interval_seconds=60  # Scan every 60 seconds
        )
    return _market_dynamic_runner
