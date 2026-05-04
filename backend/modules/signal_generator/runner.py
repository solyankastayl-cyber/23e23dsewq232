"""
Signal Generator Runner
========================

Lightweight loop для автогенерации сигналов.

Запускается один раз при старте сервера.
Работает параллельно с RuntimeDaemon.
"""

import asyncio
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional

logger = logging.getLogger(__name__)


class SignalGeneratorRunner:
    """
    Автогенератор сигналов в фоне.
    
    - Запрашивает текущую цену каждые 30-60 сек
    - Генерит сигнал через SimpleMAGenerator
    - Создает decision через RuntimeService
    - Cooldown 5 минут на symbol (анти-спам)
    """
    
    def __init__(self, runtime_service, market_data_service, interval_seconds: int = 30, experiment_id: str = "baseline_btc"):
        """
        Args:
            runtime_service: RuntimeService instance
            market_data_service: MarketDataService instance
            interval_seconds: Частота проверки (default 30s)
            experiment_id: Experiment ID for isolation (default: baseline_btc)
        """
        self.runtime_service = runtime_service
        self.market_data = market_data_service
        self.interval = interval_seconds
        self.experiment_id = experiment_id  # ← ADD: Experiment isolation
        
        # Cooldown tracking (symbol → last_decision_time)
        self.cooldowns = {}
        self.cooldown_minutes = 5
        
        # Control
        self._task: Optional[asyncio.Task] = None
        self._running = False
        
        logger.info(
            f"✅ SignalGeneratorRunner initialized: interval={interval_seconds}s, "
            f"cooldown={self.cooldown_minutes}m"
        )
    
    async def start(self):
        """Start background loop."""
        if self._running:
            logger.warning("[SignalRunner] Already running")
            return
        
        self._running = True
        self._task = asyncio.create_task(self._loop())
        logger.info("[SignalRunner] Started")
    
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
        
        logger.info("[SignalRunner] Stopped")
    
    def _check_cooldown(self, symbol: str) -> bool:
        """
        Проверить cooldown для symbol.
        
        Returns:
            True если можно создать decision, False если cooldown активен
        """
        if symbol not in self.cooldowns:
            return True
        
        last_time = self.cooldowns[symbol]
        elapsed = datetime.now(timezone.utc) - last_time
        
        if elapsed.total_seconds() < (self.cooldown_minutes * 60):
            return False
        
        return True
    
    def _update_cooldown(self, symbol: str):
        """Обновить cooldown timestamp для symbol."""
        self.cooldowns[symbol] = datetime.now(timezone.utc)

    # ----------------------------------------------------------------
    # Phase LIVE-3d-fix-multi: read active universe from MongoDB so we
    # can flip ETH/SOL on/off without redeploy. Defaults to BTCUSDT
    # only — if mongo is unavailable or doc is missing, behaviour is
    # 100% identical to the legacy single-asset path.
    # ----------------------------------------------------------------
    _UNIVERSE_DEFAULT = ["BTCUSDT"]
    _UNIVERSE_TTL_SEC = 30.0

    def _get_active_symbols(self) -> list:
        """Return ordered list of active trading symbols.

        Source priority:
          1. regime_controls.scanner_universe.symbols  (list[str])
          2. fallback → ["BTCUSDT"]

        Cached for _UNIVERSE_TTL_SEC seconds inside the runner instance
        to avoid hitting Mongo every iteration.
        """
        now = datetime.now(timezone.utc).timestamp()
        cached = getattr(self, "_universe_cache", None)
        if cached and (now - cached["ts"] < self._UNIVERSE_TTL_SEC):
            return list(cached["symbols"])

        symbols = list(self._UNIVERSE_DEFAULT)
        try:
            import os
            from pymongo import MongoClient
            url = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
            db_name = os.environ.get("DB_NAME", "trading_os")
            with MongoClient(url, serverSelectionTimeoutMS=2000) as cli:
                doc = cli[db_name].regime_controls.find_one(
                    {"control": "scanner_universe"}
                )
            if doc:
                raw = doc.get("symbols")
                if isinstance(raw, list) and raw:
                    cleaned = [
                        str(s).upper().strip() for s in raw
                        if isinstance(s, str) and s.strip()
                    ]
                    if cleaned:
                        symbols = cleaned
        except Exception as exc:
            logger.warning(
                "[SignalRunner] universe read failed, falling back to "
                "defaults: %s", exc,
            )

        self._universe_cache = {"ts": now, "symbols": symbols}
        return list(symbols)
    
    async def _loop(self):
        """Main generator loop."""
        import sys
        print("[SignalRunner] _loop() STARTING...", file=sys.stderr, flush=True)
        
        from modules.signal_generator.simple_ma_generator import (
            get_generator_for_symbol,
        )

        # Phase LIVE-3d-fix-multi: log initial universe so ops can see
        # how many assets we're scanning right after restart.
        startup_universe = self._get_active_symbols()
        print(
            f"[SignalRunner] universe = {startup_universe}",
            file=sys.stderr, flush=True,
        )
        logger.info("[SignalRunner] universe=%s", startup_universe)

        logger.info("[SignalRunner] Loop started")
        
        iteration = 0
        
        while self._running:
            iteration += 1
            print(f"[SignalRunner] Iteration {iteration} starting...", file=sys.stderr, flush=True)
            
            try:
                if not self.market_data:
                    logger.debug("[SignalRunner] No market data service")
                    await asyncio.sleep(self.interval)
                    continue

                # Refresh universe each iteration (cache TTL=30s).
                symbols = self._get_active_symbols()

                for symbol in symbols:
                    # Per-symbol generator with independent price history.
                    generator = get_generator_for_symbol(symbol)

                    # Fetch current price (async).
                    current_price = await self.market_data.get_last_price(
                        symbol, timeframe="4h"
                    )
                    if current_price is None:
                        logger.debug(
                            f"[SignalRunner] No price data for {symbol}"
                        )
                        continue

                    # Generate signal
                    signal = generator.generate_signal(current_price)
                    if signal is None:
                        # Not enough data yet OR same side as last (dedup).
                        continue

                    # Check cooldown (per-symbol).
                    if not self._check_cooldown(symbol):
                        logger.debug(
                            f"[SignalRunner] Cooldown active for "
                            f"{symbol}, skipping"
                        )
                        continue

                    # Create decision through RuntimeService
                    logger.info(
                        f"[SignalRunner] Creating decision from signal: "
                        f"{symbol} {signal['side']} @ "
                        f"${signal['entry_price']:.2f}"
                    )

                    decision = await self._create_decision_from_signal(
                        signal
                    )

                    if decision:
                        self._update_cooldown(symbol)
                        logger.info(
                            f"✅ [SignalRunner] Decision created: "
                            f"{decision.get('decision_id')}"
                        )
                        # Phase closing-loop.1: auto-approve after create.
                        # Architect directive: "Auto-approve = ON" — signals must
                        # flow signal → decision → APPROVED → execution →
                        # trading_case without human-in-the-loop.
                        # Note: only auto-approve SignalRunner's own
                        # decisions (strategy=SIMPLE_MA baseline).
                        dec_id = decision.get("decision_id")
                        if dec_id and hasattr(
                            self.runtime_service, "approve_decision"
                        ):
                            try:
                                approve_result = (
                                    await self.runtime_service.approve_decision(
                                        dec_id
                                    )
                                )
                                if approve_result and approve_result.get("ok"):
                                    logger.info(
                                        f"✅ [SignalRunner] Auto-approved "
                                        f"{dec_id}: executed via "
                                        f"runtime_service"
                                    )
                                else:
                                    logger.warning(
                                        f"[SignalRunner] Auto-approve "
                                        f"returned non-ok for {dec_id}: "
                                        f"{approve_result}"
                                    )
                            except Exception as ae:
                                # Never kill the signal loop for an
                                # approval error — the decision still sits
                                # as PENDING and can be approved manually.
                                logger.error(
                                    f"[SignalRunner] Auto-approve failed "
                                    f"for {dec_id}: {ae}"
                                )
                
            except asyncio.CancelledError:
                logger.info("[SignalRunner] Loop cancelled")
                break
            except Exception as e:
                logger.error(f"[SignalRunner] Loop error: {e}", exc_info=True)
            
            # Sleep
            await asyncio.sleep(self.interval)
    
    async def _create_decision_from_signal(self, signal: dict) -> Optional[dict]:
        """
        Создать decision из сигнала через RuntimeService.
        
        Использует СУЩЕСТВУЮЩИЙ pipeline (не обходит архитектуру).
        """
        try:
            # Проверяем есть ли метод create_decision в RuntimeService
            if not hasattr(self.runtime_service, 'create_decision'):
                # Fallback: создать decision напрямую в БД (минимальный вариант)
                return await self._create_decision_direct(signal)
            
            # Используем RuntimeService method если есть
            decision = await self.runtime_service.create_decision(signal)
            return decision
            
        except Exception as e:
            logger.error(f"[SignalRunner] Failed to create decision: {e}")
            return None
    
    async def _create_decision_direct(self, signal: dict) -> Optional[dict]:
        """
        Fallback: создать decision напрямую в БД.
        
        Используется если RuntimeService не имеет create_decision метода.
        """
        try:
            from motor.motor_asyncio import AsyncIOMotorClient
            import os
            import uuid
            
            mongo_url = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
            client = AsyncIOMotorClient(mongo_url)
            db = client["trading_os"]
            
            decision_id = f"auto-{uuid.uuid4().hex[:12]}"
            
            decision = {
                "decision_id": decision_id,
                "experiment_id": "baseline_btc",  # ← Hardcoded for baseline runner
                "symbol": signal["symbol"],
                "side": signal["side"],
                "strategy": signal["strategy"],
                "confidence": signal["confidence"],
                "entry_price": signal.get("entry_price", 0.0),
                "stop_price": None,
                "target_price": None,
                # Phase LIVE-2b (2026-04-24): align producer contract with
                # RiskGuard MAX_POSITION_SIZE_USD=100. Historically this was
                # hard-coded to 500, which RiskGuard rejected 100% of the
                # time, blocking all new entries. Architect directive:
                # "producer must not generate a signal that is guaranteed
                # to be rejected by RiskGuard."
                "size_usd": 100,
                "thesis": f"Auto-generated {signal['strategy']} signal",
                "timeframe": signal.get("timeframe", "1m"),
                "status": "PENDING",
                "created_at": datetime.now(timezone.utc).isoformat(),
                "auto_generated": True
            }
            
            # STEP 1.5.1: Safe fallback for experiment_id
            # If experiment_id not present, default to baseline_btc
            if "experiment_id" not in decision:
                decision["experiment_id"] = "baseline_btc"
            
            await db["pending_decisions"].insert_one(decision)
            
            return decision
            
        except Exception as e:
            logger.error(f"[SignalRunner] Direct decision creation failed: {e}")
            return None


# Singleton
_runner: Optional[SignalGeneratorRunner] = None


def get_runner(runtime_service, market_data_service) -> SignalGeneratorRunner:
    """Get or create singleton runner."""
    global _runner
    if _runner is None:
        _runner = SignalGeneratorRunner(
            runtime_service=runtime_service,
            market_data_service=market_data_service,
            interval_seconds=10  # 10 секунд для быстрого накопления данных
        )
    return _runner
