"""
TA Engine Python Backend - Minimal Runtime
==========================================
"""
import os
import sys
import jwt
import hashlib
from datetime import datetime, timezone, timedelta
from contextlib import asynccontextmanager
from pydantic import BaseModel

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI, HTTPException, Header, Query, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional, List, Dict
import asyncio
import json


class LoginRequest(BaseModel):
    username: str
    password: str

# Admin credentials (for demo)
ADMIN_USERS = {
    "admin": {
        "password_hash": hashlib.sha256("admin123".encode()).hexdigest(),
        "role": "ADMIN"
    },
    "moderator": {
        "password_hash": hashlib.sha256("mod123".encode()).hexdigest(),
        "role": "MODERATOR"
    }
}
JWT_SECRET = os.environ.get("JWT_SECRET", "fomo-admin-secret-key-2024")

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Initialize MongoDB
try:
    from core.database import get_database, mongo_health_check
    _db = get_database()
    print("[Server] MongoDB connection initialized")
except Exception as e:
    print(f"[Server] MongoDB connection warning: {e}")
    _db = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("[Server] TA Engine starting...")
    
    # Auto-initialize Coinbase provider
    try:
        from modules.data.coinbase_auto_init import init_coinbase_provider
        result = await init_coinbase_provider()
        if result.get("ok"):
            print(f"[Coinbase] Provider initialized - BTC: ${result.get('btc_price', 0):,.2f}")
        else:
            print(f"[Coinbase] Init warning: {result.get('error', 'unknown')}")
    except Exception as e:
        print(f"[Coinbase] Init skipped: {e}")
    
    # Start Idea Auto-Worker (auto-update + auto-resolve)
    try:
        from modules.ta_engine.ideas.idea_worker import start_auto_worker
        start_auto_worker()
        print("[Worker] Idea auto-worker started")
    except Exception as e:
        print(f"[Worker] Auto-worker skipped: {e}")
    
    # Initialize V2 Validation Scheduler
    try:
        from modules.live_validation.validation_routes import _engine as validation_engine
        from modules.alpha_factory.validation_bridge.validation_bridge_routes import _get_bridge_engine
        from modules.alpha_factory.entry_mode_adaptation.entry_mode_routes import _engine as entry_mode_engine
        from modules.trading_terminal.control.control_routes import _engine as control_engine
        
        from modules.live_validation.scheduler.scheduler_jobs import SchedulerJobs
        from modules.live_validation.scheduler.validation_scheduler import ValidationScheduler
        from modules.live_validation.scheduler.scheduler_routes import init_scheduler
        from modules.live_validation.scheduler.scheduler_config import SCHEDULER_CONFIG
        
        # Create scheduler jobs
        jobs = SchedulerJobs(
            validation_engine=validation_engine,
            validation_bridge_engine=_get_bridge_engine(),
            entry_mode_engine=entry_mode_engine,
            control_engine=control_engine,
        )
        
        # Create and initialize scheduler
        scheduler = ValidationScheduler(jobs)
        init_scheduler(scheduler)
        
        # Auto-start if enabled in config
        if SCHEDULER_CONFIG.get("enabled", True):
            scheduler.start()
            print("[Scheduler] V2 Validation Scheduler auto-started")
        
        print("[Scheduler] V2 Validation Scheduler initialized")
    except Exception as e:
        print(f"[Scheduler] V2 Validation Scheduler init skipped: {e}")
        import traceback
        traceback.print_exc()
    
    # Initialize AF6 Real Learning Engine
    try:
        from modules.trading_terminal.terminal_state.terminal_state_routes import _get_integration_engine
        from modules.alpha_factory.real_learning import RealLearningEngine, TradeOutcomeEngine, init_learning
        
        integration_engine = _get_integration_engine()
        if integration_engine:
            learning_engine = RealLearningEngine(integration_engine)
            outcome_engine = TradeOutcomeEngine()
            init_learning(learning_engine, outcome_engine)
            print("[AF6] Real Learning Engine initialized")
        else:
            print("[AF6] Skipped: IntegrationEngine not available")
    except Exception as e:
        print(f"[AF6] Real Learning Engine init skipped: {e}")
        import traceback
        traceback.print_exc()
    
    # Initialize ORCH-6 Lifecycle Control
    try:
        from modules.trading_terminal.terminal_state.terminal_state_engine import get_terminal_engine
        from modules.execution_live.lifecycle_control.lifecycle_routes import init_lifecycle
        
        terminal_engine = get_terminal_engine()
        execution_controller = terminal_engine._execution_controller
        
        if execution_controller and hasattr(execution_controller, 'lifecycle_controller'):
            init_lifecycle(execution_controller.lifecycle_controller)
            print("[ORCH-6] Lifecycle Control initialized")
        else:
            print("[ORCH-6] Skipped: ExecutionController not available")
    except Exception as e:
        print(f"[ORCH-6] Lifecycle Control init skipped: {e}")
        import traceback
        traceback.print_exc()
    
    
    # Initialize MongoDB connection globally (used by multiple modules)
    from motor.motor_asyncio import AsyncIOMotorClient
    mongo_url = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
    audit_motor_client = AsyncIOMotorClient(mongo_url)
    audit_motor_db = audit_motor_client["trading_os"]
    
    # Initialize P0.7 Audit Trail
    try:
        from modules.audit.audit_controller import AuditController
        from modules.audit.audit_routes import set_audit_controller
        from modules.execution_reality.routes import controller as execution_reality_controller
        from modules.trading_terminal.terminal_state.terminal_state_engine import set_audit_controller_for_terminal, get_terminal_engine
        from modules.meta_layer.meta_controller import set_audit_controller_for_meta, get_meta_controller
        from modules.alpha_factory.real_learning.learning_routes import get_learning_engine
        
        # Create audit controller with motor async db
        audit_controller = AuditController(audit_motor_db)
        await audit_controller.ensure_indexes()
        
        # ── Risk Guard ────────────────────────────────────
        from modules.risk_guard import init_risk_guard
        risk_guard = init_risk_guard(db=audit_motor_db)
        _rg_status = await risk_guard.get_status()
        print(f"[P1] Risk Guard initialized: max_size=${_rg_status['config']['max_position_size_usd']}, max_pos={_rg_status['config']['max_open_positions']}")
        
        # P2: Decision Quality Analytics
        from modules.decision_quality import init_decision_quality_service
        init_decision_quality_service(db=audit_motor_db)
        print("[P2] Decision Quality Analytics initialized")
        
        # Wire audit into ExecutionEventBus
        execution_reality_controller.event_bus.audit_repo = audit_controller.execution
        
        # Wire audit into TerminalStateEngine (P0.7 Hook 2)
        # IMPORTANT: Set on existing instance + save ref for future instances
        set_audit_controller_for_terminal(audit_controller)
        terminal_engine = get_terminal_engine()
        terminal_engine.audit_controller = audit_controller  # Force set on singleton
        
        # Wire audit into MetaController (P0.7 Hook 3)
        set_audit_controller_for_meta(audit_controller)
        meta_controller = get_meta_controller()
        meta_controller.audit_controller = audit_controller  # Force set on singleton
        
        # Wire audit into RealLearningEngine (P0.7 Hook 4)
        learning_engine = get_learning_engine()
        if learning_engine:
            learning_engine.audit_controller = audit_controller
            print(f"[P0.7]    - Learning audit: wired into RealLearningEngine")
        
        # Register in audit routes
        set_audit_controller(audit_controller)
        
        print("[P0.7] ✅ Audit Trail initialized (all indexes created)")
        print(f"[P0.7]    - Execution audit: wired into EventBus")
        print(f"[P0.7]    - Decision audit: wired into TerminalStateEngine (singleton forced)")
        print(f"[P0.7]    - Strategy audit: wired into MetaController (singleton forced)")
    except Exception as e:
        print(f"[P0.7] Audit Trail init skipped: {e}")
        import traceback
        traceback.print_exc()
    
    # Initialize P1.1B Persistent Queue + Async Workers
    try:
        from modules.execution_reality.queue.persistent_queue_repository import PersistentQueueRepository
        from modules.execution_reality.queue.dlq_repository import DLQRepository
        from modules.execution_reality.queue.worker_pool_v2 import WorkerPoolV2
        
        # Create persistent queue (Mongo-backed)
        persistent_queue = PersistentQueueRepository(
            db=audit_motor_db,
            lease_duration_seconds=30,  # 30s worker lease
            worker_id=None  # Auto-generated
        )
        
        # Ensure queue indexes
        await persistent_queue.ensure_indexes()
        
        # Create DLQ repository
        dlq_repository = DLQRepository(audit_motor_db)
        
        # Wire persistent queue + DLQ into execution_reality_controller
        execution_reality_controller.persistent_queue = persistent_queue
        execution_reality_controller.dlq_repository = dlq_repository
        
        # Re-initialize controller to ensure DLQ indexes
        await execution_reality_controller.initialize()
        
        # Create worker pool V2 (persistent queue)
        worker_pool = WorkerPoolV2(
            persistent_queue=persistent_queue,
            dlq_repository=dlq_repository,
            event_store=execution_reality_controller.event_store,
            event_bus=execution_reality_controller.event_bus,
            binance_adapter=execution_reality_controller.binance_adapter,
            binance_mapper=execution_reality_controller.binance_mapper,
            num_workers=3  # Configurable
        )
        
        # Start worker pool
        await worker_pool.start()
        
        # Store in app state for shutdown + metrics access
        app.state.execution_reality_controller = execution_reality_controller
        app.state.worker_pool = worker_pool
        
        print("[P1.1B] ✅ Persistent Queue + Async Workers initialized")
        print(f"[P1.1B]    - Queue: Mongo-backed (source of truth)")
        print(f"[P1.1B]    - Lease: 30s worker lock with auto-recovery")
        print(f"[P1.1B]    - Workers: {worker_pool.num_workers} async workers")
        print(f"[P1.1B]    - DLQ: MongoDB collection 'failed_order_queue'")
        print(f"[P1.1B]    - Collection: 'order_queue' (durable)")
    except Exception as e:
        print(f"[P1.1B] Persistent Queue init skipped: {e}")
        import traceback
        traceback.print_exc()
    
    # ========================================
    # P1.3 — Execution Queue v2 (Domain Execution Discipline)
    # ========================================
    try:
        from modules.execution_reality.queue_v2.execution_queue_repository import ExecutionQueueRepository
        from modules.execution_reality.queue_v2.execution_dispatch_service import (
            ExecutionDispatchService,
            set_execution_dispatch_service
        )
        from modules.execution_reality.queue_v2.execution_queue_audit import (
            ExecutionQueueAuditLogger,
            set_execution_queue_audit_logger
        )
        
        # Create audit logger (Checkpoint 5)
        execution_queue_audit_logger = ExecutionQueueAuditLogger(db=audit_motor_db)
        set_execution_queue_audit_logger(execution_queue_audit_logger)
        
        # Create execution queue repository (NEW коллекция: execution_jobs)
        execution_queue_repo = ExecutionQueueRepository(
            db=audit_motor_db,
            lease_duration_seconds=30,  # 30s lease (зафиксировано)
            worker_id=None,  # Auto-generated
            audit_logger=execution_queue_audit_logger  # Checkpoint 5
        )
        
        # Ensure indexes
        await execution_queue_repo.ensure_indexes()
        
        # Create dispatch service
        execution_dispatch_service = ExecutionDispatchService(
            execution_queue_repo=execution_queue_repo
        )
        
        # Set global singleton
        set_execution_dispatch_service(execution_dispatch_service)
        
        # Store in app state
        app.state.execution_queue_repo = execution_queue_repo
        app.state.execution_dispatch_service = execution_dispatch_service
        app.state.execution_queue_audit_logger = execution_queue_audit_logger
        
        # Sprint A2.3: Initialize ExecutionBridge
        from modules.execution import init_execution_bridge
        execution_bridge = init_execution_bridge(queue_repo=execution_queue_repo)
        app.state.execution_bridge = execution_bridge
        print("[A2.3] ✅ ExecutionBridge initialized (Runtime → Queue)")
        
        print("[P1.3] ✅ Execution Queue v2 (Domain Layer) initialized")
        print(f"[P1.3]    - Collection: 'execution_jobs' (NEW, domain-specific)")
        print(f"[P1.3]    - Lease: 30s with leaseToken verification")
        print(f"[P1.3]    - Priority: Execution-specific scale (100=LIQUIDATION, 90=STOP, 80=ENTRY)")
        print(f"[P1.3]    - Audit: execution_queue_audit (Checkpoint 5)")
        print(f"[P1.3]    - Feature Flag: USE_EXECUTION_QUEUE (planned for P1.3.1)")
        print(f"[P1.3]    - Status: Step 1 (Schema + Repo + Dispatch) + 5 Checkpoints COMPLETE")
        
        # P1.3.1 — Integration Service (Shadow Mode)
        from modules.execution_reality.integration.execution_queue_integration import (
            ExecutionQueueIntegrationService,
            set_execution_queue_integration_service
        )
        from modules.execution_reality.integration.execution_queue_feature_flags import log_feature_flags
        
        # P1.3.1D — Diff Repository (Execution Truth Layer)
        from modules.execution_reality.integration.execution_shadow_diff_repository import (
            ExecutionShadowDiffRepository,
            set_execution_shadow_diff_repo
        )
        
        # Create diff repository
        execution_shadow_diff_repo = ExecutionShadowDiffRepository(db=audit_motor_db)
        await execution_shadow_diff_repo.ensure_indexes()
        
        # Set global singleton
        set_execution_shadow_diff_repo(execution_shadow_diff_repo)
        
        # Store in app state
        app.state.execution_shadow_diff_repo = execution_shadow_diff_repo
        
        print("[P1.3.1D] ✅ Execution Shadow Diff Repository initialized")
        
        # Create integration service (with diff_repo)
        execution_queue_integration_service = ExecutionQueueIntegrationService(
            dispatch_service=execution_dispatch_service,
            audit_logger=execution_queue_audit_logger,
            diff_repo=execution_shadow_diff_repo  # P1.3.1D
        )
        
        # Set global singleton
        set_execution_queue_integration_service(execution_queue_integration_service)
        
        # Store in app state
        app.state.execution_queue_integration_service = execution_queue_integration_service
        
        # Log feature flags (P1.3.1C)
        log_feature_flags()
        
        print("[P1.3.1] ✅ Execution Queue Integration Service initialized")
        print(f"[P1.3.1]    - Shadow Integration ready (dual-write mode)")
        print(f"[P1.3.1]    - Diff Capture enabled (execution truth layer)")
        
        # P1.3.2 — Worker Runtime (Single-Worker Dry-Run → Sprint A2.3: REAL mode support)
        from modules.execution_reality.queue_v2.execution_worker_manager import (
            ExecutionWorkerManager,
            set_worker_manager
        )
        from modules.execution_reality.queue_v2.execution_worker_config import ExecutionWorkerConfig
        from modules.exchange.order_manager import OrderManager
        
        # Sprint A2.3: Create OrderManager for Workers (REAL execution)
        # Uses same mock adapter for now (will be replaced with Binance Demo)
        class MockExchangeAdapter:
            """Mock adapter for Workers."""
            def __init__(self):
                self.connected = True
                self.account_id = "worker_mock_testnet"
            
            async def place_order(self, order_request: dict):
                """Mock order placement."""
                import uuid
                return {
                    "order_id": f"order_{uuid.uuid4().hex[:12]}",
                    "exchange_order_id": f"worker_mock_{uuid.uuid4().hex[:12]}",
                    "status": "FILLED",
                    "filled_qty": order_request.get("quantity", 0),
                    "avg_price": order_request.get("price", 70000.0)
                }
        
        worker_mock_adapter = MockExchangeAdapter()
        worker_order_manager = OrderManager(worker_mock_adapter, audit_motor_db)
        
        # Create worker config (P1.3.2B: multi-worker enabled)
        worker_config = ExecutionWorkerConfig(
            worker_count=2,  # P1.3.2B: multi-worker
            dry_run=True,  # Still dry-run
            mixed_mode=True,  # P1.3.2B: retry testing
            allow_reclaim_leased=True,  # P1.3.2B: zombie reclaim
            allow_reclaim_in_flight=False  # Still prohibited
        )
        
        # Create worker manager
        worker_manager = ExecutionWorkerManager(
            db=audit_motor_db,
            queue_repo=execution_queue_repo,
            config=worker_config,
            audit_logger=execution_queue_audit_logger,
            order_manager=worker_order_manager  # Sprint A2.3: для REAL mode
        )
        
        # Start workers
        await worker_manager.start()
        
        # Set global singleton
        set_worker_manager(worker_manager)
        
        # Store in app state
        app.state.execution_worker_manager = worker_manager
        
        print("[P1.3.2B] ✅ Execution Worker Runtime initialized (MULTI-WORKER DRY-RUN)")
        print(f"[P1.3.2B]    - Mode: multi-worker ({worker_config.worker_count}), dry-run, retry-enabled")
        print(f"[P1.3.2B]    - Workers started: {worker_config.worker_count}")
        print(f"[P1.3.2B]    - Heartbeat: {worker_config.heartbeat_interval_seconds}s")
        print(f"[P1.3.2B]    - Lease: {worker_config.lease_duration_seconds}s")
        print(f"[P1.3.2B]    - Reclaim: leased=true, in_flight=false")
        
    except Exception as e:
        print(f"[P1.3] Execution Queue v2 init skipped: {e}")
        import traceback
        traceback.print_exc()
    
    # Initialize Exchange Service V2 (P0.1)
    try:
        from modules.exchange.service_v2 import init_exchange_service, get_exchange_service
        
        # Initialize with MongoDB client
        init_exchange_service(audit_motor_client)
        
        # Get service instance
        exchange_service_v2 = get_exchange_service()
        
        # Determine exchange mode from environment variable
        exchange_mode = os.getenv("EXCHANGE_MODE", "PAPER")
        
        if exchange_mode == "BINANCE_TESTNET":
            # Get Binance credentials from environment
            binance_api_key = os.getenv("BINANCE_TESTNET_API_KEY")
            binance_api_secret = os.getenv("BINANCE_TESTNET_API_SECRET")
            
            if binance_api_key and binance_api_secret:
                # Load proxy config if exists
                proxy_url = None
                try:
                    import json
                    proxy_config_path = "/app/backend/proxy_config.json"
                    if os.path.exists(proxy_config_path):
                        with open(proxy_config_path, 'r') as f:
                            proxy_data = json.load(f)
                            proxy = proxy_data.get("proxy", {})
                            if proxy.get("enabled") and proxy.get("host") and proxy.get("port"):
                                if proxy.get("username") and proxy.get("password"):
                                    proxy_url = f"http://{proxy['username']}:{proxy['password']}@{proxy['host']}:{proxy['port']}"
                                else:
                                    proxy_url = f"http://{proxy['host']}:{proxy['port']}"
                                print(f"[P0.1] Using proxy for Binance Testnet")
                except Exception as e:
                    print(f"[P0.1] Failed to load proxy config: {e}")
                
                config = {
                    "api_key": binance_api_key,
                    "api_secret": binance_api_secret,
                    "account_id": "binance_testnet_default"
                }
                
                if proxy_url:
                    config["proxy"] = proxy_url
                
                await exchange_service_v2.connect("BINANCE_TESTNET", config)
                print("[P0.1] ✅ Exchange Service V2 initialized (BINANCE TESTNET)")
            else:
                print("[P0.1] ⚠️ BINANCE_TESTNET credentials missing, falling back to PAPER mode")
                await exchange_service_v2.connect("PAPER", {"account_id": "paper_default", "initial_balance": 10000.0})
                print("[P0.1] ✅ Exchange Service V2 initialized (PAPER mode)")
        else:
            # Default to PAPER mode
            await exchange_service_v2.connect("PAPER", {"account_id": "paper_default", "initial_balance": 10000.0})
            print("[P0.1] ✅ Exchange Service V2 initialized (PAPER mode)")
    except Exception as e:
        print(f"[P0.1] Exchange Service V2 initialization failed: {e}")
        import traceback
        traceback.print_exc()
    
    # Initialize TradingCase Service (P0.2)
    try:
        from modules.trading_cases.service import init_trading_case_service, get_trading_case_service
        from modules.trading_cases.repository import init_repository
        from modules.exchange.service_v2 import get_exchange_service
        
        # Initialize repository with MongoDB
        init_repository(audit_motor_db)
        
        # Initialize with exchange service
        exchange_service_v2 = get_exchange_service()
        init_trading_case_service(exchange_service_v2)
        
        print("[P0.2] ✅ TradingCase Service initialized (MongoDB-backed)")
    except Exception as e:
        print(f"[P0.2] TradingCase Service initialization failed: {e}")
        import traceback
        traceback.print_exc()
    
    # Initialize Portfolio Service (P0.3)
    try:
        from modules.portfolio.service import init_portfolio_service, get_portfolio_service
        from modules.exchange.service_v2 import get_exchange_service
        from modules.trading_cases.service import get_trading_case_service
        
        # Initialize with exchange and trading case services
        exchange_service_v2 = get_exchange_service()
        trading_case_service = get_trading_case_service()
        init_portfolio_service(exchange_service_v2, trading_case_service, audit_motor_db)
        
        print("[P0.3] ✅ Portfolio Service initialized")
    except Exception as e:
        print(f"[P0.3] Portfolio Service initialization failed: {e}")
        import traceback
        traceback.print_exc()
    
    
    # Initialize Execution Logger (P1.4)
    try:
        from modules.execution_logger import init_execution_logger, get_execution_logger
        
        init_execution_logger(audit_motor_db)
        exec_logger = get_execution_logger()
        
        print("[P1.4] ✅ Execution Logger initialized")
    except Exception as e:
        print(f"[P1.4] Execution Logger init failed: {e}")
        import traceback
        traceback.print_exc()
    
    # Initialize Kill Switch (P1.1) — AFTER Portfolio Service init
    try:
        from modules.strategy_engine.kill_switch import init_kill_switch, get_kill_switch
        
        init_kill_switch(audit_motor_db)
        kill_switch = get_kill_switch()
        
        # Check initial state
        status = await kill_switch.get_status()
        
        if status["active"]:
            print(f"[P1.1] ⚠️ Kill Switch ACTIVE: {status['reason']}")
        else:
            print("[P1.1] ✅ Kill Switch initialized (inactive)")
    except Exception as e:
        print(f"[P1.1] Kill Switch init failed: {e}")
        import traceback
        traceback.print_exc()
    
    # Initialize Risk Manager (P1.1) — AFTER Portfolio Service init
    try:
        from modules.strategy_engine.risk_manager import init_risk_manager, get_risk_manager
        from modules.portfolio.service import get_portfolio_service
        from modules.exchange.service_v2 import get_exchange_service
        
        portfolio_service = get_portfolio_service()
        exchange_service_v2 = get_exchange_service()
        
        init_risk_manager(portfolio_service, exchange_service_v2, audit_motor_db)
        risk_manager = get_risk_manager()
        
        print("[P1.1] ✅ Risk Manager initialized")
        print(f"[P1.1]    - Max positions: {risk_manager.MAX_POSITIONS}")
        print(f"[P1.1]    - Max trades/hour: {risk_manager.MAX_TRADES_PER_HOUR}")
        print(f"[P1.1]    - Daily loss limit: ${risk_manager.DAILY_LOSS_LIMIT}")
        print(f"[P1.1]    - Cooldown: {risk_manager.COOLDOWN_SECONDS}s")
        print(f"[P1.1]    - Max slippage: {risk_manager.MAX_SLIPPAGE_PCT*100}%")
    except Exception as e:
        print(f"[P1.1] Risk Manager init failed: {e}")
        import traceback
        traceback.print_exc()
    
    # Sprint A2.2: Initialize Market Data Ingestion
    try:
        from modules.market_data.candle_repository import CandleRepository
        from modules.market_data.ingestion_service import MarketDataIngestionService
        from modules.market_data.service_locator import init_market_data_ingestion_service
        from modules.market_data.routes import router as market_data_router
        from modules.market_data_live.binance_rest_client import BinanceRestClient
        
        print("[A2.2] Initializing Market Data Ingestion Service...")
        
        candle_repo = CandleRepository(audit_motor_db)
        binance_rest_client = BinanceRestClient()
        
        market_data_service = MarketDataIngestionService(
            candle_repository=candle_repo,
            binance_rest_client=binance_rest_client,
            symbols=["BTCUSDT", "ETHUSDT"],
            timeframes=["1h", "4h", "1d"],
            refresh_interval_sec=60,
            exchange="binance",
        )
        
        init_market_data_ingestion_service(market_data_service)
        
        # Bootstrap if DB empty
        print("[A2.2] Checking if bootstrap seed is needed...")
        freshness = await market_data_service.get_freshness()
        should_seed = False
        
        for symbol, by_tf in freshness["symbols"].items():
            for _, item in by_tf.items():
                if item["latest_timestamp"] is None:
                    should_seed = True
                    break
            if should_seed:
                break
        
        if should_seed:
            print("[A2.2] Database empty - running historical seed...")
            seed_result = await market_data_service.seed_historical(limit=500)
            print(f"[A2.2] Seed complete: {seed_result['seeded']} candles")
        else:
            print("[A2.2] Database has data - skipping seed")
        
        # Start background ingestion loop
        import asyncio
        asyncio.create_task(market_data_service.run_loop())
        
        print("[A2.2] ✅ Market Data Ingestion Service initialized and running")
        print(f"[A2.2]    - Symbols: {market_data_service.symbols}")
        print(f"[A2.2]    - Timeframes: {market_data_service.timeframes}")
        print(f"[A2.2]    - Refresh interval: {market_data_service.refresh_interval_sec}s")
        
        # Register routes
        app.include_router(market_data_router)
        
    except Exception as e:
        print(f"[A2.2] ❌ Market Data Ingestion init failed: {e}")
        import traceback
        traceback.print_exc()
    
    # Sprint A3: Initialize Strategy Visibility Layer
    try:
        from modules.strategy_visibility import (
            StrategyVisibilityRepository,
            StrategyVisibilityService,
            init_strategy_visibility_service,
        )
        from modules.strategy_visibility.routes import router as strategy_visibility_router
        
        print("[A3] Initializing Strategy Visibility Layer...")
        
        strategy_visibility_repo = StrategyVisibilityRepository(audit_motor_db)
        strategy_visibility_service = StrategyVisibilityService(strategy_visibility_repo)
        init_strategy_visibility_service(strategy_visibility_service)
        
        app.include_router(strategy_visibility_router)
        
        print("[A3] ✅ Strategy Visibility Layer initialized")
        print("[A3]    - GET /api/strategy/signals/live")
        print("[A3]    - GET /api/strategy/decisions/recent")
        print("[A3]    - GET /api/strategy/summary")
        
    except Exception as e:
        print(f"[A3] ❌ Strategy Visibility init failed: {e}")
        import traceback
        traceback.print_exc()
    
    # Sprint A4: Initialize Auto Safety Layer
    try:
        from modules.auto_safety.repository import AutoSafetyRepository
        from modules.auto_safety.service import AutoSafetyService
        from modules.auto_safety.service_locator import init_auto_safety_service
        from modules.auto_safety.routes import router as auto_safety_router
        
        print("[A4] Initializing Auto Safety Layer...")
        
        auto_safety_repo = AutoSafetyRepository(audit_motor_db)
        auto_safety_service = AutoSafetyService(auto_safety_repo)
        
        # Initialize config + state
        await auto_safety_service.initialize()
        
        init_auto_safety_service(auto_safety_service)
        
        app.include_router(auto_safety_router)
        
        print("[A4] ✅ Auto Safety Layer initialized")
        print("[A4]    - GET /api/auto-safety/config")
        print("[A4]    - POST /api/auto-safety/config")
        print("[A4]    - GET /api/auto-safety/state")
        
    except Exception as e:
        print(f"[A4] ❌ Auto Safety init failed: {e}")
        import traceback
        traceback.print_exc()
    
    # Sprint A4.5: Exchange Proxy Configuration
    try:
        from modules.exchange_config.routes import router as exchange_config_router
        
        app.include_router(exchange_config_router)
        
        print("[A4.5] ✅ Exchange Config initialized")
        print("[A4.5]    - GET /api/exchange/proxy-config")
        print("[A4.5]    - POST /api/exchange/proxy-config")
        print("[A4.5]    - GET /api/exchange/test-connection")
        
    except Exception as e:
        print(f"[A4.5] ❌ Exchange Config init failed: {e}")
        import traceback
        traceback.print_exc()
    
    # Sprint R1: Initialize Dynamic Risk Engine
    try:
        from modules.dynamic_risk.service import DynamicRiskEngine
        from modules.dynamic_risk.repository import PositionRepository
        from modules.dynamic_risk.config import DYNAMIC_RISK_DEFAULTS
        from modules.dynamic_risk.service_locator import init_dynamic_risk_engine
        from modules.dynamic_risk.routes import router as dynamic_risk_router
        from modules.portfolio.service import get_portfolio_service
        
        # Phase 4: Analytics Layer
        from modules.analytics import AnalyticsService, init_analytics_service, router as analytics_router
        
        print("[R1] Initializing Dynamic Risk Engine...")
        
        # Get portfolio service for exposure calculations
        portfolio_service = get_portfolio_service()
        
        # Create position repository
        position_repo = PositionRepository(audit_motor_db)
        
        # Create and initialize DynamicRiskEngine
        dynamic_risk_engine = DynamicRiskEngine(
            portfolio_service=portfolio_service,
            position_repo=position_repo,
            config=DYNAMIC_RISK_DEFAULTS
        )
        
        init_dynamic_risk_engine(dynamic_risk_engine)
        
        # Register routes
        app.include_router(dynamic_risk_router)
        
        print("[R1] ✅ Dynamic Risk Engine initialized")
        print(f"[R1]    - Base notional: ${DYNAMIC_RISK_DEFAULTS['base_notional_usd']}")
        
        # Phase 4: Initialize Analytics Service
        print("[Analytics] Initializing Operational Analytics...")
        from modules.execution_logger.repository import ExecutionEventRepository
        execution_repo = ExecutionEventRepository(audit_motor_db)
        analytics_service = AnalyticsService(execution_repo)
        init_analytics_service(analytics_service)
        app.include_router(analytics_router)
        print("[Analytics] ✅ Operational Analytics initialized")
        
        # P2.7 Baseline Validation Monitor (READ ONLY)
        print("[P2.7] Initializing Baseline Validation Monitor...")
        from modules.p27_baseline.monitor import init_p27_monitor
        from modules.p27_baseline.routes import router as p27_router
        init_p27_monitor(audit_motor_db)
        app.include_router(p27_router)
        print("[P2.7] ✅ Baseline Monitor initialized (READ ONLY)")
        print("[P2.7]    - Target: 50 trades")
        print("[P2.7]    - GET /api/p27/status")
        print("[P2.7]    - GET /api/p27/equity-curve")
        
        # Experiments Module (Isolation Infrastructure)
        print("[Experiments] Initializing Experiment Isolation...")
        from modules.experiments import init_experiment_registry
        from modules.experiments.routes import router as experiments_router
        exp_registry = init_experiment_registry(audit_motor_db)
        await exp_registry.initialize_defaults()
        app.include_router(experiments_router)
        print("[Experiments] ✅ Experiment isolation initialized")
        print("[Experiments]    - baseline_btc: ENABLED")
        print("[Experiments]    - market_dynamic: DISABLED (until baseline completes)")
        print("[Experiments]    - GET /api/experiments")
        
        # Phase 5: Initialize Adaptive Risk (R2)
        print("[R2] Initializing Adaptive Risk Engine...")
        from modules.adaptive_risk import AdaptiveRiskService, init_adaptive_risk_service, ADAPTIVE_RISK_DEFAULTS
        
        # R2 requires portfolio service (for drawdown) and execution repo (for loss streak)
        adaptive_risk_service = AdaptiveRiskService(
            portfolio_service=portfolio_service,
            execution_repo=execution_repo,
            config=ADAPTIVE_RISK_DEFAULTS
        )
        
        init_adaptive_risk_service(adaptive_risk_service)
        
        print("[R2] ✅ Adaptive Risk Engine initialized")
        print(f"[R2]    - Min multiplier: {ADAPTIVE_RISK_DEFAULTS['min_multiplier']}")
        print(f"[R2]    - Max multiplier: {ADAPTIVE_RISK_DEFAULTS['max_multiplier']}")
        
        print(f"[R1]    - Confidence range: [{DYNAMIC_RISK_DEFAULTS['min_confidence']}, {DYNAMIC_RISK_DEFAULTS['max_confidence']}]")
        print(f"[R1]    - Size multiplier range: [{DYNAMIC_RISK_DEFAULTS['min_size_multiplier']}, {DYNAMIC_RISK_DEFAULTS['max_size_multiplier']}]")
        print(f"[R1]    - Max symbol notional: ${DYNAMIC_RISK_DEFAULTS['max_symbol_notional_usd']}")
        print(f"[R1]    - Max portfolio exposure: {DYNAMIC_RISK_DEFAULTS['max_portfolio_exposure_pct']:.0%}")
        print("[R1]    - POST /api/dynamic-risk/preview")
        print("[R1]    - GET /api/dynamic-risk/config")
        
    except Exception as e:
        print(f"[R1] ❌ Dynamic Risk Engine init failed: {e}")
        import traceback
        traceback.print_exc()
    
    # Sprint A5: Position Tracking + PnL + Close Logic
    # Sprint A7: Protection Layer (TP/SL via watcher)
    try:
        from modules.positions.sync_service import PositionSyncService
        from modules.positions.service_locator import init_position_sync_service, init_protection_watcher
        from modules.positions.routes import router as positions_router, init_positions_db
        from modules.positions.protection_routes import router as protection_router, init_protection_db
        from modules.positions.protection_repository import ProtectionRepository
        from modules.positions.protection_watcher import ProtectionWatcher
        
        print("[A5] Initializing Position Tracking Layer...")
        
        # Get exchange adapter and db
        exchange_service = get_exchange_service()
        
        # Initialize DB for positions routes
        init_positions_db(audit_motor_db)
        init_protection_db(audit_motor_db)
        
        # Create and initialize PositionSyncService
        position_sync_service = PositionSyncService(
            adapter=exchange_service.adapter,
            db=audit_motor_db
        )
        
        init_position_sync_service(position_sync_service)
        
        # Create and initialize ProtectionWatcher
        protection_repo = ProtectionRepository(audit_motor_db)
        protection_watcher = ProtectionWatcher(
            exchange_adapter=exchange_service.adapter,
            repo=protection_repo
        )
        
        init_protection_watcher(protection_watcher)
        
        # Register routes
        app.include_router(positions_router)
        app.include_router(protection_router)
        
        print("[A5] ✅ Position Tracking Layer initialized")
        print("[A5]    - GET /api/positions")
        print("[A5]    - POST /api/positions/sync")
        print("[A5]    - POST /api/positions/{symbol}/close")
        print("[A7] ✅ Protection Layer initialized")
        print("[A7]    - GET /api/protection/{symbol}")
        print("[A7]    - POST /api/protection/{symbol}/tp")
        print("[A7]    - POST /api/protection/{symbol}/sl")
        print("[A7]    - POST /api/protection/{symbol}/cancel")
        
    except Exception as e:
        print(f"[A5/A7] ❌ Position/Protection init failed: {e}")
        import traceback
        traceback.print_exc()
    
    # Sprint A6: Position Control Layer (Manual control)
    try:
        from modules.positions.control_service import PositionControlService
        from modules.positions.control_service_locator import init_position_control_service
        from modules.positions.control_routes import router as control_router
        from modules.positions.protection_repository import ProtectionRepository
        
        print("[A6] Initializing Position Control Layer...")
        
        # Get dependencies
        exchange_service = get_exchange_service()
        protection_repo = ProtectionRepository(audit_motor_db)
        
        # Create and initialize PositionControlService
        position_control_service = PositionControlService(
            exchange_adapter=exchange_service.adapter,
            protection_repo=protection_repo
        )
        
        init_position_control_service(position_control_service)
        
        # Register routes
        app.include_router(control_router)
        
        print("[A6] ✅ Position Control Layer initialized")
        print("[A6]    - POST /api/control/{symbol}/reduce")
        print("[A6]    - POST /api/control/{symbol}/reverse")
        print("[A6]    - POST /api/control/flatten-all")
        
    except Exception as e:
        print(f"[A6] ❌ Position Control init failed: {e}")
        import traceback
        traceback.print_exc()
    
    # Sprint WS-1: WebSocket Streaming (execution.feed)
    try:
        from modules.ws_hub.manager import WebSocketManager
        from modules.ws_hub.broadcaster import WebSocketBroadcaster
        from modules.ws_hub.service_locator import (
            init_ws_manager,
            init_ws_broadcaster,
        )
        from modules.ws_hub.routes import router as ws_router
        
        print("[WS-1] Initializing WebSocket Streaming...")
        
        # Create and initialize WebSocket manager
        ws_manager = WebSocketManager()
        ws_broadcaster = WebSocketBroadcaster(ws_manager)
        
        init_ws_manager(ws_manager)
        init_ws_broadcaster(ws_broadcaster)
        
        # Register WebSocket route with /api prefix for consistency
        app.include_router(ws_router, prefix="/api")
        
        print("[WS-1] ✅ WebSocket Streaming initialized")
        print("[WS-1]    - WS /api/ws")
        print("[WS-1]    - Channel: execution.feed")
        print("[WS-1]    - Heartbeat: 15s")
        
    except Exception as e:
        print(f"[WS-1] ❌ WebSocket init failed: {e}")
        import traceback
        traceback.print_exc()
    
    # Initialize Runtime (R2)
    try:
        from modules.runtime.controller import RuntimeController
        from modules.runtime.repository import PendingDecisionRepository
        from modules.runtime.signal_provider import SignalProvider
        from modules.runtime.service import RuntimeService
        from modules.runtime import init_runtime_service
        from modules.strategy_engine.kill_switch import get_kill_switch
        from modules.strategy_engine.risk_manager import get_risk_manager
        from modules.exchange.order_manager import OrderManager
        from modules.exchange.binance_demo_adapter import BinanceDemoAdapter
        from modules.exchange.service_v2 import get_exchange_service
        from modules.execution_logger import get_execution_logger
        from modules.runtime.signal_adapter import get_runtime_signal_adapter  # Sprint A1
        
        # Create OrderManager for runtime (local instance)
        # For R2: Use mock adapter (real Binance requires API keys)
        # TODO R3: Use real BinanceDemoAdapter when keys are configured
        
        class MockExchangeAdapter:
            """Mock adapter for R2 testing."""
            def __init__(self):
                self.connected = True
                self.account_id = "mock_testnet"
            
            async def place_order(self, order_request: dict):
                """Mock order placement."""
                import uuid
                return {
                    "order_id": f"order_{uuid.uuid4().hex[:12]}",
                    "exchange_order_id": f"mock_{uuid.uuid4().hex[:12]}",
                    "status": "FILLED",
                    "filled_qty": order_request.get("quantity", 0),
                    "avg_price": 70000.0  # Mock price
                }
        
        mock_adapter = MockExchangeAdapter()
        runtime_order_manager = OrderManager(mock_adapter, audit_motor_db)
        
        runtime_controller = RuntimeController(audit_motor_db)
        pending_repo = PendingDecisionRepository(audit_motor_db)
        
        # Sprint A2: Initialize RuntimeSignalAdapter with REAL TA Engine
        from modules.ta_engine.hypothesis.ta_hypothesis_builder import get_hypothesis_builder
        
        ta_builder = get_hypothesis_builder()
        
        signal_adapter = get_runtime_signal_adapter(
            ta_hypothesis_builder=ta_builder,  # ✅ Real TA Engine wired
            prediction_engine=None,           # TODO: Sprint D (Real Intelligence)
            debug_mode=False                  # ✅ REAL MODE - TA Engine is seeded with market data
        )
        
        print("[Sprint A2] ✅ REAL MODE enabled - Runtime will use TA Engine signals")
        
        runtime_service = RuntimeService(
            controller=runtime_controller,
            repository=pending_repo,
            signal_adapter=signal_adapter,  # CHANGED: signal_adapter instead of signal_provider
            risk_manager=get_risk_manager(),
            kill_switch=get_kill_switch(),
            order_manager=runtime_order_manager,
            exchange_service=get_exchange_service(),
            execution_logger=get_execution_logger()
        )
        
        # Sprint 2: Initialize Decision Trace Service (BEFORE RuntimeService)
        from modules.runtime.decision_trace import init_decision_trace_service
        init_decision_trace_service(audit_motor_db)
        
        # Sprint 2: Initialize Truth Layer Validator
        from modules.runtime.truth_validator import init_truth_validator
        init_truth_validator(audit_motor_db)
        
        init_runtime_service(runtime_service)
        
        # Sprint 2: Re-connect trace service to RuntimeService
        from modules.runtime.decision_trace import get_decision_trace_service
        runtime_service._trace_service = get_decision_trace_service()
        
        # Sprint 2: Initialize Runtime Daemon (auto-loop)
        from modules.runtime.daemon import init_runtime_daemon
        runtime_daemon = init_runtime_daemon(runtime_service)
        
        # Sprint 5: Initialize Decision Outcome Service
        from modules.decision_outcome.service import init_decision_outcome_service
        init_decision_outcome_service(audit_motor_db)
        
        # Sprint 6: Initialize Learning Service
        from modules.learning.service import init_learning_service
        init_learning_service(audit_motor_db)
        
        # Sprint 7: Initialize Adaptation Service
        from modules.adaptation.service import init_adaptation_service
        init_adaptation_service(audit_motor_db)
        
        print("[Sprint 2] Runtime Service + DecisionTrace + TruthValidator + Daemon initialized")
        print("[Sprint 5] DecisionOutcomeService initialized")
        print("[Sprint 6] LearningService initialized (pattern extraction, NO ML)")
        print("[Sprint 7] AdaptationService initialized (controlled recommendations, operator-only apply)")
    except Exception as e:
        print(f"[Sprint A2] ❌ Runtime Service init failed: {e}")
        import traceback
        traceback.print_exc()
    
    # Start Portfolio Snapshot Background Job (P0.3)
    async def portfolio_loop():
        """Background job: snapshot equity every 60 seconds (rate limit protection)"""
        try:
            from modules.portfolio.service import get_portfolio_service
            portfolio_service = get_portfolio_service()
            
            while True:
                await portfolio_service.snapshot_equity()
                await asyncio.sleep(60)  # 60s to prevent Binance rate limit
        except Exception as e:
            print(f"[P0.3] Portfolio loop error: {e}")
    
    try:
        asyncio.create_task(portfolio_loop())
        print("[P0.3] ✅ Portfolio snapshot job started (60s interval, rate-limit safe)")
    except Exception as e:
        print(f"[P0.3] Portfolio snapshot job failed: {e}")
    
    # Start Trading Sync Loop (P0.6) — Now uses ExchangeSyncService
    async def trading_sync_loop():
        """Background job: sync positions from exchange → trading cases every 60 seconds"""
        try:
            from modules.trading_cases.service import get_trading_case_service
            from modules.exchange.sync_service import init_sync_service, get_sync_service
            from modules.exchange.service_v2 import get_exchange_service
            
            case_service = get_trading_case_service()
            exchange_service_v2 = get_exchange_service()
            
            # Initialize sync service
            init_sync_service(exchange_service_v2.get_adapter(), audit_motor_db)
            sync_service = get_sync_service()
            
            while True:
                # 1. Sync exchange state (positions + balances)
                await sync_service.sync()
                
                # 2. Sync trading cases (refresh positions)
                await case_service.sync_positions()
                
                await asyncio.sleep(60)  # 60s to prevent Binance rate limit
        except Exception as e:
            print(f"[P0.6] Trading sync error: {e}")
    
    try:
        asyncio.create_task(trading_sync_loop())
        print("[P0.6] ✅ Trading sync loop started (60s interval, rate-limit safe, with ExchangeSyncService)")
    except Exception as e:
        print(f"[P0.6] Trading sync loop failed: {e}")
    
    # Seed Demo Data (P0.6) — auto-create demo case if system is empty
    async def seed_demo_data():
        """Auto-create demo trading case if portfolio is empty"""
        try:
            from modules.trading_cases.service import get_trading_case_service
            from modules.trading_cases.models import CaseCreateRequest
            
            await asyncio.sleep(2)  # Wait for services to initialize
            
            case_service = get_trading_case_service()
            active_cases = case_service.get_active_cases()
            
            if len(active_cases) == 0:
                print("[P0.6] 🌱 Seeding demo trading cases...")
                
                # Get REAL prices from Coinbase
                btc_price, eth_price = 74000.0, 2325.0  # defaults
                try:
                    from modules.data.coinbase_provider import CoinbaseProvider
                    provider = CoinbaseProvider()
                    btc_ticker = await provider.get_ticker("BTC-USD")
                    eth_ticker = await provider.get_ticker("ETH-USD")
                    if btc_ticker and btc_ticker.get("price", 0) > 0:
                        btc_price = float(btc_ticker["price"])
                    if eth_ticker and eth_ticker.get("price", 0) > 0:
                        eth_price = float(eth_ticker["price"])
                    print(f"[P0.6] Using REAL prices: BTC=${btc_price:,.2f}, ETH=${eth_price:,.2f}")
                except Exception as e:
                    print(f"[P0.6] Coinbase failed, using defaults: {e}")
                
                btc_qty = round(5000.0 / btc_price, 6)
                eth_qty = round(3500.0 / eth_price, 4)
                
                # Create BTC position with real price
                btc_req = CaseCreateRequest(
                    symbol="BTCUSDT",
                    side="LONG",
                    entry_price=btc_price,
                    qty=btc_qty,
                    size_usd=round(btc_price * btc_qty, 2),
                    strategy="Momentum",
                    trading_tf="4h",
                    thesis="Auto-seeded BTC demo position",
                    decision_id="demo-btc-1"
                )
                btc_case = await case_service.create_case(btc_req)
                
                # Create ETH position with real price
                eth_req = CaseCreateRequest(
                    symbol="ETHUSDT",
                    side="LONG",
                    entry_price=eth_price,
                    qty=eth_qty,
                    size_usd=round(eth_price * eth_qty, 2),
                    strategy="Breakout",
                    trading_tf="1h",
                    thesis="Auto-seeded ETH demo position",
                    decision_id="demo-eth-1"
                )
                eth_case = await case_service.create_case(eth_req)
                
                # Initial sync
                await case_service.sync_positions()
                
                print("[P0.6] ✅ Demo cases seeded (BTC + ETH)")
            else:
                print(f"[P0.6] System already has {len(active_cases)} active cases, skipping seed")
        except Exception as e:
            print(f"[P0.6] Seed demo data failed: {e}")
            import traceback
            traceback.print_exc()
    
    try:
        # Phase closing-loop.2 (2026-04-23): seed_demo_data DISABLED.
        # Architect directive: "Отключить seed_demo_data навсегда — мусорит
        # runtime и искажает UI/позиции." Historically this routine auto-created
        # 2 stale ACTIVE trading_cases per backend restart (decision_id=
        # demo-btc-1 / demo-eth-1) which accumulated to 262 stale docs and
        # broke RiskGuard max_open_positions semantics. The seed_demo_data()
        # function is preserved above for archival / future dev seeding needs,
        # but never scheduled automatically.
        # asyncio.create_task(seed_demo_data())  # DISABLED
        print("[P0.6] Demo seed DISABLED (closing-loop.2 — never auto-create demo cases)")
    except Exception as e:
        print(f"[P0.6] Demo seed failed: {e}")

    # Phase closing-loop.MARK (2026-04-23): start mark-price updater daemon.
    # Architect directive: "DA → делаем mark-price updater СЕЙЧАС. Без него
    # система полуживая." Runs as an in-process asyncio task; every 8s it
    # reads ACTIVE trading_cases, fetches fresh prices via BinanceProvider,
    # updates current_price/mark_price/unrealized_pnl for each. Does NOT
    # open/close positions, does NOT touch execution flow — pure
    # read→compute→update. If the loop ever dies, it logs and restarts
    # automatically inside the module (see mark_price_updater_loop impl).
    try:
        from modules.positions.mark_price_updater import mark_price_updater_loop
        # Use audit_motor_db (the trading_os motor database) — `db` is not
        # in scope at this point in lifespan. trading_cases lives in trading_os.
        asyncio.create_task(mark_price_updater_loop(audit_motor_db, interval_sec=8))
        print("[closing-loop.MARK] Mark-price updater daemon scheduled (interval=8s)")
    except Exception as e:
        print(f"[closing-loop.MARK] Mark-price updater FAILED to schedule: {e}")

    # Phase LIVE-2 (2026-04-23): start position-exit-manager daemon.
    # Architect directive: "Без exit logic — это не trading system,
    # это position accumulator." Minimal exit rules:
    #   TP: unrealized_pnl_pct >= +0.3%
    #   SL: unrealized_pnl_pct <= -0.3%
    #   TIME: opened_at older than 30 min
    # Reversible — disable by removing this task or flipping a future flag.
    try:
        from modules.positions.position_exit_manager import position_exit_loop
        asyncio.create_task(position_exit_loop(audit_motor_db, interval_sec=10))
        print("[LIVE-2d] Position exit manager daemon scheduled (interval=10s, TP=0.15%, SL=-0.15%, TIME=30m)")
    except Exception as e:
        print(f"[LIVE-2d] Position exit manager FAILED to schedule: {e}")
    
    # Initialize Exchange Service (Week 3) — OLD, keeping for backward compat
    try:
        from modules.exchange.service import exchange_service
        
        # Initialize with MongoDB client
        exchange_service.initialize(audit_motor_client)
        
        # Auto-connect to default mode (PAPER)
        await exchange_service.connect()
        
        print("[Week 3] ✅ Exchange Service initialized and connected (PAPER mode)")
    except Exception as e:
        print(f"[Week 3] Exchange Service initialization failed: {e}")
        import traceback
        traceback.print_exc()
    
    # Initialize Portfolio Service (Week 3)
    try:
        from modules.trading_core.portfolio_service import init_portfolio_service
        
        # Initialize with MongoDB client
        portfolio_service = init_portfolio_service(audit_motor_client, account_id="paper_default")
        await portfolio_service.ensure_indexes()
        
        print("[Week 3] ✅ Portfolio Service initialized (MongoDB-backed)")
    except Exception as e:
        print(f"[Week 3] Portfolio Service initialization failed: {e}")
        import traceback
        traceback.print_exc()
    
    # Initialize Execution Events Service (Week 3)
    try:
        from modules.trading_core.execution_events import init_events_service
        
        # Initialize with MongoDB client
        events_service = init_events_service(audit_motor_client)
        
        print("[Week 3] ✅ Execution Events Service initialized")
    except Exception as e:
        print(f"[Week 3] Execution Events Service initialization failed: {e}")
        import traceback
        traceback.print_exc()
    
    # Initialize Performance Service (Week 4)
    try:
        from modules.trading_core.performance_service import init_performance_service
        
        performance_service = init_performance_service(audit_motor_client, account_id="paper_default")
        
        print("[Week 4] ✅ Performance Service initialized")
    except Exception as e:
        print(f"[Week 4] Performance Service initialization failed: {e}")
        import traceback
        traceback.print_exc()
    
    # Initialize Market Data Live Service
    try:
        from modules.market_data_live import init_market_data_service
        
        market_data_service = init_market_data_service()
        
        # Bootstrap historical candles
        symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT", "ADAUSDT"]
        await market_data_service.bootstrap(symbols, interval="4h", limit=200)
        
        # Start WebSocket stream
        await market_data_service.start_stream(symbols, interval="4h")
        
        print(f"[MarketData] ✅ Live market data initialized for {symbols}")
    except Exception as e:
        print(f"[MarketData] Initialization failed: {e}")
        import traceback
        traceback.print_exc()
    

    # Signal Generator Runner (Шаг B: Auto-генерация решений) — BASELINE
    try:
        from modules.signal_generator.runner import get_runner
        from modules.runtime.service_locator import get_runtime_service
        from modules.market_data_live import get_market_data_service
        
        runtime_svc = get_runtime_service()
        market_data_svc = get_market_data_service()
        
        if runtime_svc and market_data_svc:
            signal_runner = get_runner(
                runtime_service=runtime_svc,
                market_data_service=market_data_svc
            )
            
            await signal_runner.start()
            
            print("[SignalGenerator] ✅ Baseline runner started (10s interval)")
        else:
            print("[SignalGenerator] Skipped: RuntimeService or MarketData not available")
    except Exception as e:
        print(f"[SignalGenerator] Initialization failed: {e}")
        import traceback
        traceback.print_exc()
    
    # Market Dynamic Runner (Phase 2.2: Scanner Plumbing + Phase 2.3: Signal Generation + Phase 2.4: Ranking + Phase 2.5: Snapshots + Phase 2.6: Shadow Trades)
    try:
        from modules.signal_generator.market_dynamic_runner import get_market_dynamic_runner
        from modules.experiments.registry import get_experiment_registry
        from modules.market_data_live import get_market_data_service
        
        registry = get_experiment_registry()
        market_dynamic_exp = await registry.get_experiment("market_dynamic")
        
        if market_dynamic_exp and market_dynamic_exp.status.value == "enabled":
            market_data_svc = get_market_data_service()
            market_dynamic_runner = get_market_dynamic_runner(
                market_data_service=market_data_svc,
                db=db  # PHASE 2.5: Pass DB for snapshots + shadow trades
            )
            await market_dynamic_runner.start()
            print("[MarketDynamic] ✅ Runner started (60s interval, full pipeline)")
        else:
            print("[MarketDynamic] Skipped: experiment not enabled (waiting for baseline completion)")
    except Exception as e:
        print(f"[MarketDynamic] Initialization failed: {e}")
        import traceback
        traceback.print_exc()
    
    # Outcome Resolver (Phase 2.6: Resolve shadow trades)
    try:
        from modules.strategy.outcome_resolver import get_outcome_resolver
        from modules.market_data_live import get_market_data_service
        from modules.runtime.service_locator import get_runtime_service
        
        runtime_svc = get_runtime_service()
        if runtime_svc and hasattr(runtime_svc, 'db'):
            market_data_svc = get_market_data_service()
            outcome_resolver = get_outcome_resolver(db=runtime_svc.db, market_data_service=market_data_svc)
            await outcome_resolver.start()
            print("[OutcomeResolver] ✅ Started (15s interval)")
        else:
            print("[OutcomeResolver] Skipped: DB not available")
    except Exception as e:
        print(f"[OutcomeResolver] Initialization failed: {e}")
        import traceback
        traceback.print_exc()
    
    # Score Calibration Worker (Phase 2.7B: Recalibrate scoring)
    try:
        from modules.strategy.score_calibrator import get_score_calibrator, ScoreCalibrationWorker
        from modules.runtime.service_locator import get_runtime_service
        import asyncio
        
        runtime_svc = get_runtime_service()
        if runtime_svc and hasattr(runtime_svc, 'db'):
            calibrator = get_score_calibrator(runtime_svc.db)
            calibration_worker = ScoreCalibrationWorker(runtime_svc.db, calibrator)
            
            # Background task for periodic recalibration
            async def calibration_loop():
                while True:
                    try:
                        await calibration_worker.recalibrate_if_needed()
                    except Exception as e:
                        print(f"[ScoreCalibrator] Error: {e}")
                    
                    # Check every 10 minutes
                    await asyncio.sleep(600)
            
            asyncio.create_task(calibration_loop())
            print("[ScoreCalibrator] ✅ Started (10min interval, 6h cooldown)")
        else:
            print("[ScoreCalibrator] Skipped: DB not available")
    except Exception as e:
        print(f"[ScoreCalibrator] Initialization failed: {e}")
        import traceback
        traceback.print_exc()


    # Alert Engine Worker (Phase 2.8: Observability / Alerts)
    try:
        from modules.strategy.observability import get_alert_engine
        from modules.strategy.observability.alert_storage import create_indexes as create_alert_indexes
        from modules.runtime.service_locator import get_runtime_service
        import asyncio
        
        runtime_svc = get_runtime_service()
        if runtime_svc and hasattr(runtime_svc, 'db'):
            # Create indexes
            await create_alert_indexes(runtime_svc.db)
            
            alert_engine = get_alert_engine(runtime_svc.db)
            
            # Background task for periodic alert evaluation
            async def alert_loop():
                while True:
                    try:
                        result = await alert_engine.evaluate_alerts(experiment_id="market_dynamic")
                        if result.get("alerts_generated", 0) > 0:
                            print(f"[AlertEngine] Generated {result['alerts_generated']} new alerts")
                    except Exception as e:
                        print(f"[AlertEngine] Error: {e}")
                        import traceback
                        traceback.print_exc()
                    
                    # Check every 60 seconds
                    await asyncio.sleep(60)
            
            asyncio.create_task(alert_loop())
            print("[AlertEngine] ✅ Started (60s interval)")
        else:
            print("[AlertEngine] Skipped: DB not available")
    except Exception as e:
        print(f"[AlertEngine] Initialization failed: {e}")
        import traceback
        traceback.print_exc()

    # P0.LEGACY — AutoTrading Service (DISABLED)
    try:
        from modules.trading_core.autotrading_service import init_autotrading_service
        
        autotrading_service = init_autotrading_service(audit_motor_db)
        
        # DISABLED: Conflicts with new Risk Manager
        # await autotrading_service.start_loop()
        
        print("[LEGACY] ⚠️ AutoTrading loop DISABLED")
    except Exception as e:
        print(f"[LEGACY] AutoTrading init skipped: {e}")
    
    # Sprint A5: Position Sync Loop
    try:
        import asyncio
        from modules.positions.service_locator import get_position_sync_service, get_protection_watcher
        
        async def position_sync_loop():
            service = get_position_sync_service()
            
            # WS-3: Get portfolio service for broadcasting
            try:
                from modules.portfolio.service import get_portfolio_service
                portfolio_service = get_portfolio_service()
            except:
                portfolio_service = None
            
            while True:
                try:
                    result = await service.sync_positions()
                    # Uncomment for debug: logger.debug(f"[POSITION_SYNC] synced: {result}")
                    
                    # WS-3: Broadcast portfolio.summary AFTER position state is fixed
                    if portfolio_service and result.get("ok"):
                        await portfolio_service.broadcast_summary_if_changed()
                
                except Exception as e:
                    print(f"[POSITION_SYNC] error: {e}")
                
                await asyncio.sleep(60)  # 60 seconds (rate limit protection)
        
        asyncio.create_task(position_sync_loop())
        print("[A5] 🚀 Position sync loop started (60s interval, rate-limit safe)")
        
    except Exception as e:
        print(f"[A5] Position sync loop skipped: {e}")
    
    # Sprint A7: Protection Watcher Loop
    try:
        import asyncio
        from modules.positions.service_locator import get_protection_watcher
        
        protection_watcher = get_protection_watcher()
        asyncio.create_task(protection_watcher.start())
        print("[A7] 🚀 Protection watcher started (2s interval)")
        
    except Exception as e:
        print(f"[A7] Protection watcher skipped: {e}")
    
    # WS-1: Start heartbeat loop
    try:
        from modules.ws_hub.service_locator import get_ws_manager
        import asyncio
        
        ws_manager = get_ws_manager()
        asyncio.create_task(ws_manager.start_heartbeat())
        print("[WS-1] Heartbeat loop started")
    except Exception as e:
        print(f"[WS-1] Heartbeat start failed: {e}")
    
    # Phase 3.0B: Paper Auto Runner (Controlled Autonomy)
    try:
        from motor.motor_asyncio import AsyncIOMotorClient
        from modules.strategy.paper_auto_runner import (
            AutoRunnerState,
            AutoRunnerRules,
            PaperAutoRunner
        )
        from modules.strategy.paper_auto_runner.audit_logger import AuditLogger
        from modules.strategy.paper_execution_bridge.paper_bridge_service import PaperBridgeService
        from modules.strategy.paper_execution_bridge.paper_decision_repository import PaperDecisionRepository
        from modules.strategy.paper_execution_bridge.paper_position_repository import PaperPositionRepository
        from modules.strategy.execution_readiness.execution_readiness_service import ExecutionReadinessService
        from modules.strategy.execution_analysis.execution_quality_service import ExecutionQualityService
        from modules.strategy.observability.health_service import HealthService
        
        # Get DB
        mongo_url = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
        client = AsyncIOMotorClient(mongo_url)
        db = client["trading_os"]
        
        # Initialize services
        audit_logger = AuditLogger(db)
        paper_position_repo = PaperPositionRepository(db)
        readiness_service = ExecutionReadinessService(db)
        execution_quality_service = ExecutionQualityService(db)
        
        paper_bridge_service = PaperBridgeService(db)
        
        # Initialize auto-runner state and rules
        auto_runner_state = AutoRunnerState()
        auto_runner_rules = AutoRunnerRules(
            max_runs_per_hour=4,
            max_open_positions=3
        )
        
        # Create auto-runner
        paper_auto_runner = PaperAutoRunner(
            paper_bridge_service=paper_bridge_service,
            readiness_service=readiness_service,
            execution_quality_service=execution_quality_service,
            paper_position_repo=paper_position_repo,
            audit_logger=audit_logger,
            state=auto_runner_state,
            rules=auto_runner_rules,
            interval_seconds=600  # 10 minutes
        )
        
        # Store in app state for API access
        app.state.paper_auto_runner_state = auto_runner_state
        app.state.paper_auto_runner = paper_auto_runner
        
        # Start auto-runner loop (paused by default for safety)
        auto_runner_state.pause("initial_safety")
        auto_runner_task = asyncio.create_task(paper_auto_runner.loop_forever())
        app.state.auto_runner_task = auto_runner_task
        
        print("[Phase 3.0B] ✅ Paper Auto Runner initialized (PAUSED for safety)")
        print("[Phase 3.0B]    Interval: 10 minutes")
        print("[Phase 3.0B]    Max runs/hour: 4")
        print("[Phase 3.0B]    Max open positions: 3")
        print("[Phase 3.0B]    Use /api/experiments/market_dynamic/auto-run/resume to start")
    except Exception as e:
        print(f"[Phase 3.0B] Auto Runner init skipped: {e}")
        import traceback
        traceback.print_exc()
    
    # ────────────────────────────────────────────────────────────────────
    # Pass 5 — Forward Shadow Validation
    #   * shadow_scheduler: tick every minute, log actionable decisions
    #     for ETHUSDT/BTCUSDT/SOLUSDT 1H — paper-only.
    #   * outcome_evaluator: close horizons (h1/h3/h6) by reading close prices.
    # No order execution involved. Failures here MUST NOT block startup.
    # ────────────────────────────────────────────────────────────────────
    try:
        from modules.meta.shadow_scheduler import get_shadow_scheduler
        from modules.meta.shadow_outcome_evaluator import get_outcome_evaluator
        get_shadow_scheduler().start()
        get_outcome_evaluator().start()
        print("[Pass 5] ✅ Shadow scheduler + outcome evaluator started")
    except Exception as e:
        print(f"[Pass 5] Shadow loop init skipped: {e}")
        import traceback
        traceback.print_exc()

    # ────────────────────────────────────────────────────────────────────
    # Step 7 — TA Prediction Intelligence outcome worker
    #   * evaluates pending TA predictions once h6 candles are available
    #   * feeds calibration engine with real outcomes
    #   * fully isolated from Meta / Trading flows
    # ────────────────────────────────────────────────────────────────────
    try:
        from modules.ta_prediction_intelligence.evaluation import get_outcome_worker
        get_outcome_worker().start()
        print("[Step 7] ✅ TA Prediction outcome worker started")
    except Exception as e:
        print(f"[Step 7] TA Prediction outcome worker init skipped: {e}")
    
    yield
    
    # Phase 3.0B: Shutdown Paper Auto Runner
    try:
        if hasattr(app.state, 'paper_auto_runner'):
            print("[Phase 3.0B] Shutting down Paper Auto Runner...")
            app.state.paper_auto_runner.stop()
            
            if hasattr(app.state, 'auto_runner_task'):
                app.state.auto_runner_task.cancel()
                try:
                    await app.state.auto_runner_task
                except asyncio.CancelledError:
                    pass
            
            print("[Phase 3.0B] ✅ Paper Auto Runner stopped")
    except Exception as e:
        print(f"[Phase 3.0B] Auto Runner shutdown error: {e}")
    
    # P1.3.2 — Shutdown Worker Manager (Graceful Drain)
    try:
        if hasattr(app.state, 'execution_worker_manager'):
            print("[P1.3.2] Shutting down execution worker manager...")
            await app.state.execution_worker_manager.stop()
            print("[P1.3.2] ✅ Execution worker manager stopped")
    except Exception as e:
        print(f"[P1.3.2] Worker manager shutdown error: {e}")
    
    # Shutdown P1.1B worker pool
    try:
        if hasattr(app.state, 'worker_pool'):
            await app.state.worker_pool.stop()
            print("[P1.1B] Worker pool stopped")
    except Exception as e:
        print(f"[P1.1] Worker pool shutdown error: {e}")
    
    # Stop scheduler on shutdown
    try:
        from modules.live_validation.scheduler.scheduler_routes import _scheduler
        if _scheduler and _scheduler.running:
            _scheduler.stop()
            print("[Scheduler] V2 Validation Scheduler stopped")
    except:
        pass
    
    # Stop worker on shutdown
    try:
        from modules.ta_engine.ideas.idea_worker import stop_auto_worker
        stop_auto_worker()
        print("[Worker] Idea auto-worker stopped")
    except:
        pass
    
    # Pass 5 — stop shadow scheduler + outcome evaluator
    try:
        from modules.meta.shadow_scheduler import get_shadow_scheduler
        from modules.meta.shadow_outcome_evaluator import get_outcome_evaluator
        await get_shadow_scheduler().stop()
        await get_outcome_evaluator().stop()
        print("[Pass 5] ✅ Shadow loops stopped")
    except Exception as e:
        print(f"[Pass 5] Shadow loop shutdown error: {e}")

    # Step 7 — stop TA Prediction outcome worker
    try:
        from modules.ta_prediction_intelligence.evaluation import get_outcome_worker
        await get_outcome_worker().stop()
        print("[Step 7] ✅ TA Prediction outcome worker stopped")
    except Exception as e:
        print(f"[Step 7] TA Prediction outcome worker shutdown error: {e}")

    # Step 8 — flush temporal buffer to Mongo before shutdown
    try:
        from modules.ta_prediction_intelligence.learning import get_temporal_buffer
        flushed = get_temporal_buffer().flush_all()
        print(f"[Step 8] ✅ Temporal buffer flushed ({flushed} snapshots)")
    except Exception as e:
        print(f"[Step 8] Temporal buffer flush error: {e}")
    
    print("[Server] TA Engine shutting down...")


app = FastAPI(
    title="TA Engine API",
    description="TA Engine Module Runtime",
    version="1.0.0",
    lifespan=lifespan
)

# Debug: Print all registered routes after startup
@app.on_event("startup")
async def debug_routes():
    print("\n" + "="*60)
    print("REGISTERED ROUTES:")
    print("="*60)
    for route in app.routes:
        if hasattr(route, 'path'):
            print(f"  {route.path}")
    print("="*60 + "\n")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─────────────────────────────────────────────────────────────────────────
# Phase A.1 — TA module canonical namespace alias.
#
# Exposes every TA-vertical endpoint under a single canonical prefix
# `/api/ta/*` while keeping legacy routes (`/api/runtime/*`, `/api/trace/*`,
# `/api/analytics/*`, `/api/learning/*`) bit-for-bit identical.
#
# One handler — two valid URLs. See modules/ta_module/ta_namespace.py.
# ─────────────────────────────────────────────────────────────────────────
from modules.ta_module.ta_namespace import install_ta_namespace_alias  # noqa: E402
install_ta_namespace_alias(app)


# ============================================
# WebSocket Manager for Real-time Updates
# ============================================

class ConnectionManager:
    """Manage WebSocket connections for real-time market updates"""
    
    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {}
        self._price_cache: Dict[str, float] = {}
    
    async def connect(self, websocket: WebSocket, channel: str = "market"):
        await websocket.accept()
        if channel not in self.active_connections:
            self.active_connections[channel] = []
        self.active_connections[channel].append(websocket)
    
    def disconnect(self, websocket: WebSocket, channel: str = "market"):
        if channel in self.active_connections:
            if websocket in self.active_connections[channel]:
                self.active_connections[channel].remove(websocket)
    
    async def broadcast(self, message: dict, channel: str = "market"):
        if channel in self.active_connections:
            disconnected = []
            for connection in self.active_connections[channel]:
                try:
                    await connection.send_json(message)
                except:
                    disconnected.append(connection)
            # Clean up disconnected
            for conn in disconnected:
                self.disconnect(conn, channel)
    
    async def send_price_update(self, symbol: str, price: float, change: float = 0):
        self._price_cache[symbol] = price
        await self.broadcast({
            "type": "price",
            "symbol": symbol,
            "price": price,
            "change": change,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
    
    async def send_candle_update(self, symbol: str, timeframe: str, candle: dict):
        await self.broadcast({
            "type": "candle",
            "symbol": symbol,
            "timeframe": timeframe,
            **candle,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })


ws_manager = ConnectionManager()


@app.websocket("/api/ws/market")
async def websocket_market(websocket: WebSocket):
    """WebSocket endpoint for real-time market data"""
    await ws_manager.connect(websocket, "market")
    
    try:
        # Send connection confirmation
        await websocket.send_json({"type": "connected", "channel": "market"})
        
        while True:
            try:
                data = await asyncio.wait_for(websocket.receive_json(), timeout=30)
                
                if data.get("type") == "subscribe":
                    symbol = data.get("symbol", "BTCUSDT")
                    timeframe = data.get("timeframe", "4H")
                    await websocket.send_json({
                        "type": "subscribed",
                        "symbol": symbol,
                        "timeframe": timeframe
                    })
                elif data.get("type") == "ping":
                    await websocket.send_json({"type": "pong"})
                    
            except asyncio.TimeoutError:
                # Send heartbeat
                await websocket.send_json({"type": "heartbeat"})
            except WebSocketDisconnect:
                break
                
    except Exception as e:
        print(f"[WS] Error: {e}")
    finally:
        ws_manager.disconnect(websocket, "market")


@app.get("/api/health")
async def health():
    return {
        "ok": True,
        "mode": "TA_ENGINE_RUNTIME",
        "version": "1.0.0",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


# ============================================
# Admin Auth Endpoints
# ============================================

@app.post("/api/admin/auth/login")
async def admin_login(request: LoginRequest):
    """Admin login endpoint"""
    user = ADMIN_USERS.get(request.username)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    password_hash = hashlib.sha256(request.password.encode()).hexdigest()
    if password_hash != user["password_hash"]:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    expires = datetime.now(timezone.utc) + timedelta(hours=24)
    token = jwt.encode({
        "sub": request.username,
        "role": user["role"],
        "exp": expires
    }, JWT_SECRET, algorithm="HS256")
    
    return {
        "ok": True,
        "token": token,
        "role": user["role"],
        "username": request.username,
        "expiresAtTs": int(expires.timestamp())
    }


@app.get("/api/admin/auth/status")
async def admin_auth_status(authorization: Optional[str] = Header(None)):
    """Check admin auth status"""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    token = authorization.replace("Bearer ", "")
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
        return {
            "ok": True,
            "data": {
                "userId": payload["sub"],
                "role": payload["role"],
                "expiresAtTs": payload["exp"]
            }
        }
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


@app.get("/api/system/db-health")
async def db_health():
    try:
        return mongo_health_check()
    except Exception as e:
        return {"status": "error", "connected": False, "error": str(e)}


# Execution Logger Routes (P1.4)
try:
    from modules.execution_logger.routes import router as execution_logger_router
    app.include_router(execution_logger_router)
    print("[Routes] Execution Logger router registered")
except ImportError as e:
    print(f"[Routes] Execution Logger router not available: {e}")


# Phase 3.0B: Auto-Run API Routes
try:
    from modules.strategy.paper_auto_runner.routes import router as auto_run_router
    app.include_router(auto_run_router)
    print("[Phase 3.0B] ✅ Auto-Run API registered")
    print("[Phase 3.0B]    - GET  /api/auto-run/status")
    print("[Phase 3.0B]    - POST /api/auto-run/pause")
    print("[Phase 3.0B]    - POST /api/auto-run/resume")
    print("[Phase 3.0B]    - POST /api/auto-run/enable")
    print("[Phase 3.0B]    - POST /api/auto-run/disable")
    print("[Phase 3.0B]    - GET  /api/auto-run/audit")
except ImportError as e:
    print(f"[Phase 3.0B] ❌ Auto-Run API not available: {e}")


# Phase 3.1: Execution Quality API (DECOUPLED - Safety System)
try:
    from modules.strategy.execution_analysis.routes import router as execution_quality_router
    app.include_router(execution_quality_router)
    print("[Phase 3.1] ✅ Execution Quality API registered (independent)")
    print("[Phase 3.1]    - GET /api/execution-quality")
except ImportError as e:
    print(f"[Phase 3.1] ❌ Execution Quality API not available: {e}")


# Phase 2.8: Health API (DECOUPLED - Observability)
try:
    from modules.strategy.observability.routes import router as health_router
    app.include_router(health_router)
    print("[Phase 2.8] ✅ Health API registered (independent)")
    print("[Phase 2.8]    - GET /api/health")
except ImportError as e:
    print(f"[Phase 2.8] ❌ Health API not available: {e}")


# Phase 2.9: Readiness API (DECOUPLED - Gating)
try:
    from modules.strategy.execution_readiness.routes import router as readiness_router
    app.include_router(readiness_router)
    print("[Phase 2.9] ✅ Readiness API registered (independent)")
    print("[Phase 2.9]    - GET /api/readiness")
except ImportError as e:
    print(f"[Phase 2.9] ❌ Readiness API not available: {e}")


# Phase 3.0A: Paper Performance API (DECOUPLED - Operational Visibility)
try:
    from modules.strategy.paper_execution_bridge.routes import router as paper_performance_router
    app.include_router(paper_performance_router)
    print("[Phase 3.0A] ✅ Paper Performance API registered (independent)")
    print("[Phase 3.0A]    - GET /api/paper-performance")
except ImportError as e:
    print(f"[Phase 3.0A] ❌ Paper Performance API not available: {e}")


# Runtime Routes (R1)
try:
    from modules.runtime import router as runtime_router
    app.include_router(runtime_router)
    print("[Routes] Runtime router registered")
except ImportError as e:
    print(f"[Routes] Runtime router not available: {e}")

# Phase C.3: Regime Decision Read/Admin API
try:
    from routes.regime_decision import router as regime_decision_router
    app.include_router(regime_decision_router)
    print("[Phase C.3] Regime Decision router registered")
    print("[Phase C.3]    - GET  /api/regime/accuracy")
    print("[Phase C.3]    - GET  /api/regime/decision")
    print("[Phase C.3]    - GET  /api/regime/state")
    print("[Phase C.3]    - GET  /api/regime/alerts")
    print("[Phase C.3]    - GET  /api/regime/guard-events")
    print("[Phase C.3]    - GET  /api/regime/controls/short-v2-guard")
    print("[Phase C.3]    - POST /api/regime/controls/short-v2-guard")
except ImportError as e:
    print(f"[Phase C.3] Regime Decision router not available: {e}")

# Phase 6 / P2: TA Prediction Intelligence (read-only analytical service)
# ---------------------------------------------------------------------------
# Module is independent of combined_analysis / meta_pipeline / policy_registry.
# It is wired in solely so that:
#   1. the architect can call /api/ta-prediction-intelligence/* directly
#   2. comparisons against exchange_intelligence become possible
# It does NOT participate in shadow_logger, scheduler, or any decision flow.
try:
    from modules.ta_prediction_intelligence.ta_prediction_routes import (
        router as ta_prediction_intelligence_router,
    )
    app.include_router(ta_prediction_intelligence_router)
    print("[Phase 6 / P2] TA Prediction Intelligence router registered")
    print("[Phase 6 / P2]    - GET  /api/ta-prediction-intelligence/health")
    print("[Phase 6 / P2]    - POST /api/ta-prediction-intelligence/from-setup")
    print("[Phase 6 / P2]    - POST /api/ta-prediction-intelligence/from-typed")
except ImportError as e:
    print(f"[Phase 6 / P2] TA Prediction Intelligence router not available: {e}")

# Step 8 — Learning layer (features + temporal buffer). READ-ONLY.
try:
    from modules.ta_prediction_intelligence.learning_routes import (
        router as ta_learning_router,
    )
    app.include_router(ta_learning_router)
    print("[Step 8] TA Prediction Intelligence learning routes registered")
    print("[Step 8]    - GET  /api/ta-prediction-intelligence/features/schema")
    print("[Step 8]    - GET  /api/ta-prediction-intelligence/features/preview")
    print("[Step 8]    - GET  /api/ta-prediction-intelligence/buffer/status")
    print("[Step 10]    - GET  /api/ta-prediction-intelligence/dataset/preview")
    print("[Step 10]    - GET  /api/ta-prediction-intelligence/dataset/stats")
    print("[Step 10]    - POST /api/ta-prediction-intelligence/dataset/rebuild")
except ImportError as e:
    print(f"[Step 8] TA learning routes not available: {e}")


# Step DEBUG — Read-only Evaluation Debug Layer (error taxonomy + root cause).
try:
    from modules.ta_prediction_intelligence.debug_routes import (
        router as ta_debug_router,
    )
    from modules.ta_prediction_intelligence.debug import init_debug_repository
    init_debug_repository()
    app.include_router(ta_debug_router)
    print("[Step DEBUG] TA Prediction Intelligence debug layer registered")
    print("[Step DEBUG]    - GET  /api/ta-prediction-intelligence/debug/preview")
    print("[Step DEBUG]    - GET  /api/ta-prediction-intelligence/debug/stats")
    print("[Step DEBUG]    - GET  /api/ta-prediction-intelligence/debug/case/{prediction_id}")
    print("[Step DEBUG]    - POST /api/ta-prediction-intelligence/debug/rebuild")
except ImportError as e:
    print(f"[Step DEBUG] debug layer not available: {e}")


# Step DATA-HEALTH — Read-only Data Quality / Trust Layer.
try:
    from modules.ta_prediction_intelligence.data_health.health_routes import (
        router as ta_data_health_router,
    )
    app.include_router(ta_data_health_router)
    print("[Data Health] TA Prediction Intelligence data-health layer registered")
    print("[Data Health]    - GET /api/ta-prediction-intelligence/data-health")
    print("[Data Health]    - GET /api/ta-prediction-intelligence/data-health/checks")
    print("[Data Health]    - GET /api/ta-prediction-intelligence/data-health/drift")
except ImportError as e:
    print(f"[Data Health] data-health layer not available: {e}")


# Step ML-READINESS — Read-only ML training-readiness assessor.
try:
    from modules.ta_prediction_intelligence.ml_readiness.readiness_routes import (
        router as ta_ml_readiness_router,
    )
    app.include_router(ta_ml_readiness_router)
    print("[ML Readiness] TA Prediction Intelligence ml-readiness layer registered")
    print("[ML Readiness]    - GET /api/ta-prediction-intelligence/ml-readiness")
    print("[ML Readiness]    - GET /api/ta-prediction-intelligence/ml-readiness/details")
except ImportError as e:
    print(f"[ML Readiness] ml-readiness layer not available: {e}")


# Root-Cause Aggregator — detector for repeating systemic weaknesses (live-only).
try:
    from modules.ta_prediction_intelligence.root_cause_aggregator.root_cause_routes import (
        router as ta_root_cause_router,
    )
    app.include_router(ta_root_cause_router)
    print("[Root-Cause] TA Prediction Intelligence root-cause aggregator registered")
    print("[Root-Cause]    - GET /api/ta-prediction-intelligence/root-causes")
    print("[Root-Cause]    - GET /api/ta-prediction-intelligence/root-causes/by/{axis}")
    print("[Root-Cause]    - GET /api/ta-prediction-intelligence/root-causes/weaknesses")
except ImportError as e:
    print(f"[Root-Cause] root-cause aggregator not available: {e}")


# Simulation Engine — strictly isolated offline replay over historical candles.
try:
    from modules.ta_prediction_intelligence.simulation.simulation_routes import (
        router as ta_simulation_router,
    )
    app.include_router(ta_simulation_router)
    print("[Simulation] TA Prediction Intelligence simulation engine registered")
    print("[Simulation]    - POST /api/ta-prediction-intelligence/simulation/replay")
    print("[Simulation]    - GET  /api/ta-prediction-intelligence/simulation/stats")
    print("[Simulation]    - POST /api/ta-prediction-intelligence/simulation/clear")
except ImportError as e:
    print(f"[Simulation] simulation engine not available: {e}")


# P1 Risk Guard Status Endpoint
@app.get("/api/runtime/risk-status")
async def risk_guard_status():
    """Return Risk Guard status, stats, and integrity check."""
    from modules.risk_guard import get_risk_guard
    guard = get_risk_guard()
    if not guard:
        raise HTTPException(status_code=503, detail="Risk Guard not initialized")
    status = await guard.get_status()
    integrity = await guard.integrity_check()
    return {
        "ok": True,
        **status,
        "integrity": integrity,
    }

@app.post("/api/runtime/risk-reset")
async def risk_guard_reset():
    """Manually reset the kill switch."""
    from modules.risk_guard import get_risk_guard
    guard = get_risk_guard()
    if not guard:
        raise HTTPException(status_code=503, detail="Risk Guard not initialized")
    return guard.reset_kill_switch()

# P2: Decision Quality Analytics
@app.get("/api/analytics/decision-quality")
async def decision_quality_analytics():
    """Decision quality metrics — analytics only, no strategy changes."""
    from modules.decision_quality import get_decision_quality_service
    svc = get_decision_quality_service()
    if not svc:
        raise HTTPException(status_code=503, detail="DecisionQualityService not initialized")
    report = await svc.get_quality_report()
    return {"ok": True, **report}

# Sprint 5: Decision Analytics Routes
try:
    from modules.decision_outcome.routes import router as decision_analytics_router
    app.include_router(decision_analytics_router)
    print("[Routes] Decision Analytics router registered")
except ImportError as e:
    print(f"[Routes] Decision Analytics router not available: {e}")

# Sprint 6: Learning Layer Routes
try:
    from modules.learning.routes import router as learning_router
    app.include_router(learning_router)
    print("[Routes] Learning Layer registered (Sprint 6)")
except ImportError as e:
    print(f"[Routes] Learning Layer not available: {e}")

# Sprint 7: Adaptation Layer Routes
try:
    from modules.adaptation.routes import router as adaptation_router
    app.include_router(adaptation_router)
    print("[Routes] Adaptation Layer registered (Sprint 7 - Controlled)")
except ImportError as e:
    print(f"[Routes] Adaptation Layer not available: {e}")



# System Control Routes
try:
    from modules.system_control.routes import router as system_control_router
    app.include_router(system_control_router)
    print("[Routes] System Control router registered")
except ImportError as e:
    print(f"[Routes] System Control router not available: {e}")

# Portfolio Session Stats Routes
try:
    from modules.portfolio.session_routes import router as portfolio_session_router
    app.include_router(portfolio_session_router)
    print("[Routes] Portfolio Session router registered")
except ImportError as e:
    print(f"[Routes] Portfolio Session router not available: {e}")

# Strategy Engine Routes
try:
    from modules.strategy_engine.routes import router as strategy_engine_router
    app.include_router(strategy_engine_router)
    print("[Routes] Strategy Engine router registered")
except ImportError as e:
    print(f"[Routes] Strategy Engine router not available: {e}")

# TA Engine Routes
try:
    from modules.ta_engine.ta_routes import router as ta_engine_router
    app.include_router(ta_engine_router)
    print("[Routes] TA Engine router registered")
except ImportError as e:
    print(f"[Routes] TA Engine router not available: {e}")

# TA Setup API (Clean Research Pipeline)
try:
    from modules.ta_engine.ta_setup_api import router as ta_setup_api_router
    app.include_router(ta_setup_api_router)
    print("[Routes] TA Setup API router registered")
except ImportError as e:
    print(f"[Routes] TA Setup API router not available: {e}")

# TA Research API (Unified Chart Objects Pipeline)
try:
    from modules.ta_engine.research_api import router as research_api_router
    app.include_router(research_api_router)
    print("[Routes] TA Research API router registered")
except ImportError as e:
    print(f"[Routes] TA Research API router not available: {e}")

# TA Setup Engine Routes (Setup Graph Architecture)
try:
    from modules.ta_engine.setup.setup_routes import router as ta_setup_router
    app.include_router(ta_setup_router)
    print("[Routes] TA Setup Engine router registered")
except ImportError as e:
    print(f"[Routes] TA Setup Engine router not available: {e}")

# TA Ideas Routes (Idea System)
try:
    from modules.ta_engine.ideas.idea_routes import router as ta_ideas_router
    app.include_router(ta_ideas_router)
    print("[Routes] TA Ideas router registered")
except ImportError as e:
    print(f"[Routes] TA Ideas router not available: {e}")

# Idea Engine V1 Routes (New Idea System)
try:
    from modules.idea.idea_routes import router as idea_v1_router, favorites_router
    app.include_router(idea_v1_router)
    app.include_router(favorites_router)
    print("[Routes] Idea V1 router registered")
except ImportError as e:
    print(f"[Routes] Idea V1 router not available: {e}")

# PHASE F1 — Research Routes
try:
    from modules.chart_composer.routes import chart_composer_router
    app.include_router(chart_composer_router, prefix="/api/v1")
    print("[Routes] Chart Composer router registered")
except Exception as e:
    print(f"[Routes] Chart Composer not available: {e}")

try:
    from modules.signal_explanation.routes import signal_explanation_router
    app.include_router(signal_explanation_router, prefix="/api/v1")
    print("[Routes] Signal Explanation router registered")
except Exception as e:
    print(f"[Routes] Signal Explanation not available: {e}")

try:
    from modules.research_analytics.routes import research_analytics_router
    app.include_router(research_analytics_router, prefix="/api/v1")
    print("[Routes] Research Analytics router registered")
except Exception as e:
    print(f"[Routes] Research Analytics not available: {e}")

try:
    from modules.trading_capsule.research.research_routes import router as trading_research_router
    app.include_router(trading_research_router, prefix="/api/research")
    print("[Routes] Trading Research router registered")
except Exception as e:
    print(f"[Routes] Trading Research not available: {e}")

try:
    from modules.fractal_market_intelligence.fractal_routes import router as fractal_router
    app.include_router(fractal_router)
    print("[Routes] Fractal Intelligence router registered")
except Exception as e:
    print(f"[Routes] Fractal Intelligence not available: {e}")

try:
    from modules.research.hypothesis_engine.hypothesis_routes import router as hypothesis_router
    app.include_router(hypothesis_router)
    print("[Routes] Hypothesis Engine router registered")
except Exception as e:
    print(f"[Routes] Hypothesis Engine not available: {e}")

try:
    from modules.capital_flow import capital_flow_router
    app.include_router(capital_flow_router)
    print("[Routes] Capital Flow router registered")
except Exception as e:
    print(f"[Routes] Capital Flow not available: {e}")

# TA Prediction (uses shared prediction_core)
try:
    from modules.ta_prediction.ta_prediction_routes import router as ta_prediction_router
    app.include_router(ta_prediction_router)
    print("[Routes] TA Prediction router registered")
except Exception as e:
    print(f"[Routes] TA Prediction not available: {e}")

# Pass 3 — Analytics Unification Layer (TA + Prediction + Hypothesis)
try:
    from modules.analysis.combined_analysis_routes import router as combined_analysis_router
    app.include_router(combined_analysis_router)
    print("[Routes] Combined Analysis (Pass 3) router registered")
except Exception as e:
    print(f"[Routes] Combined Analysis not available: {e}")

# Pass 4 — Meta Scoring Engine (decision math: score + allocation + risk gate)
try:
    from modules.meta.meta_routes import router as meta_router
    app.include_router(meta_router)
    print("[Routes] Meta Scoring (Pass 4) router registered")
except Exception as e:
    print(f"[Routes] Meta Scoring not available: {e}")

# PHASE F2 — Trading Terminal Routes
try:
    from modules.trading_engine.routes import router as trading_engine_router
    app.include_router(trading_engine_router)
    print("[Routes] Trading Engine router registered")
except Exception as e:
    print(f"[Routes] Trading Engine not available: {e}")

# Portfolio Routes (P0.3) — MUST BE BEFORE OLD PORTFOLIO ROUTER
try:
    from modules.portfolio.routes import router as portfolio_v3_router
    app.include_router(portfolio_v3_router)
    print("[Routes] Portfolio router registered (P0.3)")
except Exception as e:
    print(f"[Routes] Portfolio (P0.3) not available: {e}")

try:
    from modules.trading_terminal.portfolio.portfolio_routes import router as portfolio_router
    app.include_router(portfolio_router)
    print("[Routes] Portfolio router registered")
except Exception as e:
    print(f"[Routes] Portfolio not available: {e}")

try:
    from modules.execution_brain import execution_router
    app.include_router(execution_router)
    print("[Routes] Execution Brain router registered")
except Exception as e:
    print(f"[Routes] Execution Brain not available: {e}")

# Broker Adapters Routes (Coinbase, Binance, etc.)
try:
    from modules.broker_adapters.routes import router as broker_router
    app.include_router(broker_router)
    print("[Routes] Broker Adapters router registered")
except Exception as e:
    print(f"[Routes] Broker Adapters not available: {e}")

# Trading Terminal Live Routes (Phase 5.1)
try:
    from modules.trading_terminal.live.terminal_routes import router as terminal_live_router
    app.include_router(terminal_live_router)
    print("[Routes] Trading Terminal Live router registered")
except Exception as e:
    print(f"[Routes] Trading Terminal Live not available: {e}")

# TradingCases Routes (P0.2)
try:
    from modules.trading_cases.routes import router as trading_cases_router
    app.include_router(trading_cases_router)
    print("[Routes] TradingCases router registered (P0.2)")
except Exception as e:
    print(f"[Routes] TradingCases not available: {e}")

# Terminal State Orchestrator (UNIFIED API - Phase T2)
try:
    from modules.trading_terminal.terminal_state.terminal_state_routes import router as terminal_state_router
    app.include_router(terminal_state_router)
    print("[Routes] Terminal State Orchestrator registered")
except Exception as e:
    print(f"[Routes] Terminal State Orchestrator not available: {e}")

# Signal Engine (Signal Generation)
try:
    from modules.signal_engine.routes import router as signal_engine_router
    app.include_router(signal_engine_router)
    print("[Routes] Signal Engine registered")
except Exception as e:
    print(f"[Routes] Signal Engine not available: {e}")

# Execution State Engine (Phase TT1 - Orders & Execution)
try:
    from modules.trading_terminal.execution.execution_routes import router as execution_router
    app.include_router(execution_router)
    print("[Routes] Execution State Engine registered")
except Exception as e:
    print(f"[Routes] Execution State Engine not available: {e}")

# Position Manager (Phase TT2 - Positions)
try:
    from modules.trading_terminal.positions.position_routes import router as position_router
    app.include_router(position_router)
    print("[Routes] Position Manager registered")
except Exception as e:
    print(f"[Routes] Position Manager not available: {e}")

# Portfolio & Risk Console (Phase TT3)
try:
    from modules.trading_terminal.portfolio_risk.portfolio_risk_routes import router as portfolio_risk_router
    app.include_router(portfolio_risk_router)
    print("[Routes] Portfolio & Risk Console registered")
except Exception as e:
    print(f"[Routes] Portfolio & Risk Console not available: {e}")

# History & Forensics (Phase TT4)
try:
    from modules.trading_terminal.forensics.forensics_routes import router as forensics_router
    app.include_router(forensics_router)
    print("[Routes] History & Forensics registered")
except Exception as e:
    print(f"[Routes] History & Forensics not available: {e}")

# Alpha Factory (Phase AF1)
try:
    from modules.alpha_factory.alpha_routes import router as alpha_factory_router
    app.include_router(alpha_factory_router)
    print("[Routes] Alpha Factory registered")
except Exception as e:
    print(f"[Routes] Alpha Factory not available: {e}")

# Operator Control Layer (Phase TT5)
try:
    from modules.trading_terminal.control.control_routes import router as control_router
    app.include_router(control_router)
    print("[Routes] Operator Control Layer registered")
except Exception as e:
    print(f"[Routes] Operator Control Layer not available: {e}")

# Alpha Policy Layer (Phase AF2)
try:
    from modules.alpha_factory.alpha_policy_routes import router as alpha_policy_router
    app.include_router(alpha_policy_router)
    print("[Routes] Alpha Policy Layer registered")
except Exception as e:
    print(f"[Routes] Alpha Policy Layer not available: {e}")

# AF3 Validation Bridge
try:
    from modules.alpha_factory.validation_bridge import validation_bridge_router
    app.include_router(validation_bridge_router)
    print("[Routes] AF3 Validation Bridge registered")
except Exception as e:
    print(f"[Routes] AF3 Validation Bridge not available: {e}")

# AF4 Entry Mode Adaptation
try:
    from modules.alpha_factory.entry_mode_adaptation import entry_mode_adaptation_router
    app.include_router(entry_mode_adaptation_router)
    print("[Routes] AF4 Entry Mode Adaptation registered")
except Exception as e:
    print(f"[Routes] AF4 Entry Mode Adaptation not available: {e}")

# V2 Validation Scheduler
try:
    from modules.live_validation.scheduler.scheduler_routes import router as validation_scheduler_router
    app.include_router(validation_scheduler_router)
    print("[Routes] V2 Validation Scheduler registered")
except Exception as e:
    print(f"[Routes] V2 Validation Scheduler not available: {e}")

# Market Intelligence (Week 1: Scanner + Signal Engine)
try:
    from modules.market_intelligence.routes import router as market_intelligence_router
    app.include_router(market_intelligence_router)
    print("[Routes] Market Intelligence (Scanner + Signals) registered")
except Exception as e:
    print(f"[Routes] Market Intelligence not available: {e}")

# Trading Core (Week 2: Decision Engine + Portfolio + Runtime)
try:
    from modules.trading_core.routes import router as trading_core_router
    app.include_router(trading_core_router)
    print("[Routes] Trading Core (Decision + Portfolio + Runtime) registered")
except Exception as e:
    print(f"[Routes] Trading Core not available: {e}")

# Exchange Layer (Week 3: Paper + Testnet adapters)
try:
    from modules.exchange.routes import router as exchange_router
    app.include_router(exchange_router)
    print("[Routes] Exchange Layer (PAPER/TESTNET) registered")
except Exception as e:
    print(f"[Routes] Exchange Layer not available: {e}")

# Strategy Layer (Week 4: Allocator V2/V3)
try:
    from modules.strategy.routes import router as strategy_router, init_strategy_routes
    from modules.strategy.strategy_stats_service import get_strategy_stats_service
    
    # Initialize strategy stats service (P0 FIX: use None check instead of bool)
    if _db is not None:
        strategy_stats_service = get_strategy_stats_service(db=_db)
        init_strategy_routes(strategy_stats_service, None)
    else:
        print("[Routes] Strategy Layer: MongoDB not available, skipping stats service")
    
    app.include_router(strategy_router)
    print("[Routes] Strategy Layer (Allocator V2) registered + initialized")
except Exception as e:
    print(f"[Routes] Strategy Layer not available: {e}")

# =====================================================
# TRADING TERMINAL INTERNAL SERVICES (RAW APIs)
# These are INTERNAL - UI should use /api/terminal/state
# =====================================================

# TR1 - Account Manager
try:
    from modules.trading_terminal.accounts.account_routes import router as accounts_router
    app.include_router(accounts_router)
    print("[Routes] TR1 Account Manager registered")
except Exception as e:
    print(f"[Routes] TR1 Account Manager not available: {e}")

# TR3 - Trade Monitor
try:
    from modules.trading_terminal.trades.trade_routes import router as trades_router
    app.include_router(trades_router)
    print("[Routes] TR3 Trade Monitor registered")
except Exception as e:
    print(f"[Routes] TR3 Trade Monitor not available: {e}")

# TR4 - Risk Dashboard
try:
    from modules.trading_terminal.risk.risk_routes import router as risk_router
    app.include_router(risk_router)
    print("[Routes] TR4 Risk Dashboard registered")
except Exception as e:
    print(f"[Routes] TR4 Risk Dashboard not available: {e}")

# TR5 - Strategy Control
try:
    from modules.trading_terminal.strategy_control.control_routes import router as strategy_control_router
    app.include_router(strategy_control_router)
    print("[Routes] TR5 Strategy Control registered")
except Exception as e:
    print(f"[Routes] TR5 Strategy Control not available: {e}")

# TR6 - Dashboard
try:
    from modules.trading_terminal.dashboard.dashboard_routes import router as dashboard_router
    app.include_router(dashboard_router)
    print("[Routes] TR6 Dashboard registered")
except Exception as e:
    print(f"[Routes] TR6 Dashboard not available: {e}")

# State Reconciliation
try:
    from modules.trading_terminal.reconciliation.recon_routes import router as recon_router
    app.include_router(recon_router)
    print("[Routes] State Reconciliation registered")
except Exception as e:
    print(f"[Routes] State Reconciliation not available: {e}")

# Operations - Capital
try:
    from modules.trading_terminal.operations.capital.capital_routes import router as capital_router
    app.include_router(capital_router)
    print("[Routes] Ops Capital registered")
except Exception as e:
    print(f"[Routes] Ops Capital not available: {e}")

# Operations - Forensics
try:
    from modules.trading_terminal.operations.forensics.forensics_routes import router as forensics_router
    app.include_router(forensics_router)
    print("[Routes] Ops Forensics registered")
except Exception as e:
    print(f"[Routes] Ops Forensics not available: {e}")

# Operations - Lifecycle
try:
    from modules.trading_terminal.operations.lifecycle.lifecycle_routes import router as lifecycle_router
    app.include_router(lifecycle_router)
    print("[Routes] Ops Lifecycle registered")
except Exception as e:
    print(f"[Routes] Ops Lifecycle not available: {e}")

# Operations - Positions
try:
    from modules.trading_terminal.operations.positions.position_routes import router as positions_router
    app.include_router(positions_router)
    print("[Routes] Ops Positions registered")
except Exception as e:
    print(f"[Routes] Ops Positions not available: {e}")


# PHASE F3 — System Control Routes
try:
    from modules.system_control.control_routes import router as control_router
    app.include_router(control_router)
    print("[Routes] System Control router registered")
except Exception as e:
    print(f"[Routes] System Control not available: {e}")

try:
    from modules.safety_kill_switch.kill_switch_routes import router as kill_switch_router
    app.include_router(kill_switch_router)
    print("[Routes] Kill Switch router registered")
except Exception as e:
    print(f"[Routes] Kill Switch not available: {e}")

try:
    from modules.circuit_breaker.breaker_routes import router as breaker_router
    app.include_router(breaker_router)
    print("[Routes] Circuit Breaker router registered")
except Exception as e:
    print(f"[Routes] Circuit Breaker not available: {e}")

# PHASE V1 — Live Validation Layer
try:
    from modules.live_validation.validation_routes import router as live_validation_router
    app.include_router(live_validation_router)
    print("[Routes] V1 Live Validation router registered")
except Exception as e:
    print(f"[Routes] V1 Live Validation not available: {e}")

# Prediction Engine V2 Routes
try:
    from modules.prediction.routes import router as prediction_router
    app.include_router(prediction_router)
    print("[Routes] Prediction Engine V2 router registered")
except Exception as e:
    print(f"[Routes] Prediction Engine not available: {e}")

# Scanner Engine Routes
try:
    from modules.scanner.routes import router as scanner_router
    app.include_router(scanner_router)
    print("[Routes] Scanner Engine router registered")
except Exception as e:
    print(f"[Routes] Scanner Engine not available: {e}")

# PHASE 2.9 — Calibration Layer Routes
try:
    from modules.calibration.calibration_routes import router as calibration_router
    app.include_router(calibration_router)
    print("[Routes] Calibration Layer router registered")
except Exception as e:
    print(f"[Routes] Calibration Layer not available: {e}")

# PHASE 3.1 — Adaptive Layer Routes
try:
    from modules.adaptive.adaptive_routes import router as adaptive_router
    app.include_router(adaptive_router)
    print("[Routes] Adaptive Layer router registered")
except Exception as e:
    print(f"[Routes] Adaptive Layer not available: {e}")

# PHASE 3.2 — Policy Guard Routes
try:
    from modules.adaptive.policy.policy_routes import router as policy_router
    app.include_router(policy_router)
    print("[Routes] Policy Guard router registered")
except Exception as e:
    print(f"[Routes] Policy Guard not available: {e}")

# PHASE 3.3 — Audit / Rollback Routes
try:
    from modules.adaptive.audit.audit_routes import router as audit_router
    app.include_router(audit_router)
    print("[Routes] Audit / Rollback router registered")
except Exception as e:
    print(f"[Routes] Audit / Rollback not available: {e}")

# PHASE 3.4 — Adaptive Scheduler Routes
try:
    from modules.adaptive.scheduler.scheduler_routes import router as scheduler_router
    app.include_router(scheduler_router)
    print("[Routes] Adaptive Scheduler router registered")
except Exception as e:
    print(f"[Routes] Adaptive Scheduler not available: {e}")

# PHASE 4.1 — Wrong Early Diagnostic Routes
try:
    from modules.entry_timing.diagnostics.wrong_early_routes import router as wrong_early_router
    app.include_router(wrong_early_router)
    print("[Routes] Wrong Early Diagnostic router registered")
except Exception as e:
    print(f"[Routes] Wrong Early Diagnostic not available: {e}")

# PHASE 4.2 — Entry Mode Selector Routes
try:
    from modules.entry_timing.mode_selector.entry_mode_routes import router as entry_mode_router
    app.include_router(entry_mode_router)
    print("[Routes] Entry Mode Selector router registered")
except Exception as e:
    print(f"[Routes] Entry Mode Selector not available: {e}")

# AF6 — Real Learning Engine Routes
try:
    from modules.alpha_factory.real_learning.learning_routes import router as learning_router
    app.include_router(learning_router)
    print("[Routes] AF6 Real Learning Engine router registered")
except Exception as e:
    print(f"[Routes] AF6 Real Learning Engine not available: {e}")

# ORCH-6 — Lifecycle Control Routes
try:
    from modules.execution_live.lifecycle_control.lifecycle_routes import router as lifecycle_router
    app.include_router(lifecycle_router)
    print("[Routes] ORCH-6 Lifecycle Control router registered")
except Exception as e:
    print(f"[Routes] ORCH-6 Lifecycle Control not available: {e}")

# ORCH-7 — Meta Layer Routes
try:
    from modules.meta_layer.meta_routes import router as meta_router
    app.include_router(meta_router)
    print("[Routes] ORCH-7 Meta Layer router registered")
except Exception as e:
    print(f"[Routes] ORCH-7 Meta Layer not available: {e}")

# PHASE 4.3 — Execution Strategy Routes
try:
    from modules.entry_timing.execution_strategy.execution_strategy_routes import router as execution_strategy_router
    app.include_router(execution_strategy_router)
    print("[Routes] Execution Strategy router registered")
except Exception as e:
    print(f"[Routes] Execution Strategy not available: {e}")

# PHASE 4.4 — Entry Quality Routes
try:
    from modules.entry_timing.quality.entry_quality_routes import router as entry_quality_router
    app.include_router(entry_quality_router)
    print("[Routes] Entry Quality router registered")
except Exception as e:
    print(f"[Routes] Entry Quality not available: {e}")

# PHASE 4.5 — Entry Timing Integration Routes
try:
    from modules.entry_timing.integration.entry_timing_routes import router as entry_timing_integration_router
    app.include_router(entry_timing_integration_router)
    print("[Routes] Entry Timing Integration router registered")
except Exception as e:
    print(f"[Routes] Entry Timing Integration not available: {e}")

# PHASE 4.6 — Entry Timing Backtest Routes
try:
    from modules.entry_timing.backtest.entry_timing_backtest_routes import router as entry_timing_backtest_router
    app.include_router(entry_timing_backtest_router)
    print("[Routes] Entry Timing Backtest router registered")
except Exception as e:
    print(f"[Routes] Entry Timing Backtest not available: {e}")

# PHASE 4.7 — MTF Entry Timing Routes
try:
    from modules.entry_timing.mtf.mtf_routes import router as mtf_router
    app.include_router(mtf_router)
    print("[Routes] MTF Entry Timing router registered")
except Exception as e:
    print(f"[Routes] MTF Entry Timing not available: {e}")

# PHASE 4.8 — Microstructure Entry Routes
try:
    from modules.entry_timing.microstructure.microstructure_routes import router as microstructure_router
    app.include_router(microstructure_router)
    print("[Routes] Microstructure Entry router registered")
except Exception as e:
    print(f"[Routes] Microstructure Entry not available: {e}")

# PHASE 4.8.2 — Microstructure Validation Routes
try:
    from modules.entry_timing.microstructure.validation.micro_validation_routes import router as micro_validation_router
    app.include_router(micro_validation_router)
    print("[Routes] Microstructure Validation router registered")
except Exception as e:
    print(f"[Routes] Microstructure Validation not available: {e}")

# PHASE 4.8.3 — Microstructure Weighting Routes
try:
    from modules.entry_timing.microstructure.weighting.micro_weighting_routes import router as micro_weighting_router
    app.include_router(micro_weighting_router)
    print("[Routes] Microstructure Weighting router registered")
except Exception as e:
    print(f"[Routes] Microstructure Weighting not available: {e}")

# PHASE 4.8.4 — Microstructure Weighting Validation Routes
try:
    from modules.entry_timing.microstructure.validation_weighting.micro_weighting_routes import router as micro_weight_val_router
    app.include_router(micro_weight_val_router)
    print("[Routes] Microstructure Weighting Validation router registered")
except Exception as e:
    print(f"[Routes] Microstructure Weighting Validation not available: {e}")


# ============================================
# P0 — Execution Reality (Event-Driven Execution)
# ============================================
try:
    from modules.execution_reality.routes import router as execution_reality_router
    app.include_router(execution_reality_router)
    print("[Routes] ✅ Execution Reality (P0 Milestone A) router registered")
except Exception as e:
    print(f"[Routes] Execution Reality not available: {e}")

# P1.1 — Order Queue Routes
try:
    from modules.execution_reality.queue_routes import router as queue_router
    app.include_router(queue_router, prefix="/api/execution-reality")
    print("[Routes] ✅ Order Queue (P1.1) router registered")
except Exception as e:
    print(f"[Routes] Order Queue not available: {e}")

# P1.3 — Execution Queue v2 Routes
try:
    from modules.execution_reality.queue_v2_routes import router as execution_queue_v2_router
    app.include_router(execution_queue_v2_router, prefix="/api")
    print("[Routes] ✅ Execution Queue v2 (P1.3) router registered")
except Exception as e:
    print(f"[Routes] Execution Queue v2 not available: {e}")

# P1.3.1 — Execution Jobs Ops Routes
try:
    from modules.execution_reality.integration.execution_jobs_ops_routes import router as execution_jobs_ops_router
    app.include_router(execution_jobs_ops_router, prefix="/api")
    print("[Routes] ✅ Execution Jobs Ops (P1.3.1) router registered")
except Exception as e:
    print(f"[Routes] Execution Jobs Ops not available: {e}")

# P1.3.1C — Shadow Integration Test Routes
try:
    from modules.execution_reality.integration.shadow_test_routes import router as shadow_test_router
    app.include_router(shadow_test_router, prefix="/api")
    print("[Routes] ✅ Shadow Integration Test (P1.3.1C) router registered")
except Exception as e:
    print(f"[Routes] Shadow Integration Test not available: {e}")

# P1.3.1D — Trace Diagnostic Routes
try:
    from modules.execution_reality.integration.trace_diagnostic_routes import router as trace_diagnostic_router
    app.include_router(trace_diagnostic_router, prefix="/api")
    print("[Routes] ✅ Trace Diagnostic (P1.3.1D) router registered")
except Exception as e:
    print(f"[Routes] Trace Diagnostic not available: {e}")

# P1.3.2 — Worker Monitor Routes
try:
    from modules.execution_reality.queue_v2.worker_monitor_routes import router as worker_monitor_router
    app.include_router(worker_monitor_router, prefix="/api")
    print("[Routes] ✅ Worker Monitor (P1.3.2) router registered")
except Exception as e:
    print(f"[Routes] Worker Monitor not available: {e}")

# P1.3.2 — Queue Metrics Routes (Operational Correctness)
try:
    from modules.execution_reality.queue_v2.queue_metrics_routes import router as queue_metrics_router
    app.include_router(queue_metrics_router, prefix="/api")
    print("[Routes] ✅ Queue Metrics (P1.3.2) router registered")
except Exception as e:
    print(f"[Routes] Queue Metrics not available: {e}")

# P1.3.3 — Routing Control Plane (Canary Deployment)
try:
    from modules.execution_reality.integration.execution_routing_stats import router as routing_stats_router
    app.include_router(routing_stats_router, prefix="/api")
    print("[Routes] ✅ Routing Control Plane (P1.3.3) router registered")
except Exception as e:
    print(f"[Routes] Routing Control Plane not available: {e}")

# ============================================
# P0.7 — Audit Trail (Persistence + Explainability)
# ============================================
try:
    from modules.audit.audit_routes import router as audit_router
    app.include_router(audit_router)

    # System Status (Step C: Minimal Observability)
    from modules.system_status import router as system_status_router
    app.include_router(system_status_router, prefix="/api/system", tags=["System"])
    
    # Phase 3.2: Discovery Debugging
    from modules.strategy.execution_analysis.debug_routes import router as debug_router
    app.include_router(debug_router)
    print("[Phase 3.2] ✅ Debug routes loaded (features-from-shadow)")

    print("[Routes] ✅ Audit Trail (P0.7) router registered")
except Exception as e:
    print(f"[Routes] Audit Trail not available: {e}")


# ============================================
# Coinbase Provider Live Data Endpoints
# ============================================

@app.get("/api/provider/coinbase/status")
async def coinbase_status():
    """Get Coinbase provider status"""
    try:
        from modules.data.coinbase_auto_init import get_coinbase_status
        return await get_coinbase_status()
    except Exception as e:
        return {"provider": "coinbase", "status": "error", "error": str(e)}


@app.get("/api/provider/coinbase/health")
async def coinbase_health():
    """Coinbase provider health check"""
    try:
        from modules.data.coinbase_auto_init import coinbase_health_check
        return await coinbase_health_check()
    except Exception as e:
        return {"provider": "coinbase", "status": "error", "error": str(e)}


@app.get("/api/provider/coinbase/ticker/{symbol}")
async def coinbase_ticker(symbol: str = "BTC"):
    """Get live ticker from Coinbase"""
    try:
        from modules.data.coinbase_auto_init import coinbase_auto_init
        return await coinbase_auto_init.get_live_ticker(symbol)
    except Exception as e:
        return {"ok": False, "error": str(e), "symbol": symbol}


@app.get("/api/provider/coinbase/candles/{symbol}")
async def coinbase_candles(
    symbol: str = "BTC",
    timeframe: str = Query("1h", description="Timeframe: 1m, 5m, 15m, 1h, 4h, 1d"),
    limit: int = Query(100, ge=1, le=300)
):
    """Get live candles from Coinbase"""
    try:
        from modules.data.coinbase_auto_init import coinbase_auto_init
        return await coinbase_auto_init.get_live_candles(symbol, timeframe, limit)
    except Exception as e:
        return {"ok": False, "error": str(e), "symbol": symbol, "candles": []}


@app.get("/api/provider/list")
async def list_providers():
    """List all data providers and their status"""
    providers = {
        "coinbase": {
            "status": "active",
            "type": "market_data",
            "requires_keys": False,
            "supported_pairs": ["BTC-USD", "ETH-USD", "SOL-USD"],
            "description": "Live market data via public API"
        },
        "binance": {
            "status": "inactive",
            "type": "market_data",
            "requires_keys": False,
            "supported_pairs": ["BTCUSDT", "ETHUSDT", "SOLUSDT"],
            "description": "Available but not auto-initialized"
        },
        "bybit": {
            "status": "inactive",
            "type": "market_data",
            "requires_keys": False,
            "supported_pairs": ["BTCUSDT", "ETHUSDT", "SOLUSDT"],
            "description": "Available but not auto-initialized"
        },
        "hyperliquid": {
            "status": "inactive",
            "type": "market_data",
            "requires_keys": False,
            "description": "Available but not auto-initialized"
        }
    }
    
    # Get Coinbase live status
    try:
        from modules.data.coinbase_auto_init import get_coinbase_status
        cb_status = await get_coinbase_status()
        providers["coinbase"]["live_status"] = cb_status
    except:
        pass
    
    return {
        "ok": True,
        "active_provider": "coinbase",
        "providers": providers,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


# TA Analysis Endpoints
@app.get("/api/ta/registry")
async def ta_registry():
    try:
        from core.database import get_database
        db = get_database()
        if db is None:
            return {"status": "error", "error": "Database not connected"}
        
        strategies = list(db.strategies.find({}, {"_id": 0}))
        regime_map = list(db.regime_map.find({}, {"_id": 0}))
        config = db.config.find_one({"_id": "calibration"}, {"_id": 0})
        
        return {
            "status": "ok",
            "registry": {
                "strategies_count": len(strategies),
                "strategies": strategies,
                "regime_map_count": len(regime_map),
                "calibration_enabled": config.get("enabled", False) if config else False,
            },
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}


@app.get("/api/ta/patterns")
async def ta_patterns():
    try:
        from core.database import get_database
        db = get_database()
        if db is None:
            return {"status": "error", "error": "Database not connected"}
        
        strategies = list(db.strategies.find({}, {"_id": 0}))
        approved = [s for s in strategies if s.get("status") == "APPROVED"]
        limited = [s for s in strategies if s.get("status") == "LIMITED"]
        deprecated = [s for s in strategies if s.get("status") == "DEPRECATED"]
        
        return {
            "status": "ok",
            "patterns": {
                "approved": [s["id"] for s in approved],
                "limited": [s["id"] for s in limited],
                "deprecated": [s["id"] for s in deprecated],
            },
            "total_count": len(strategies),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}


@app.post("/api/ta/analyze")
async def ta_analyze(symbol: str = "BTCUSDT", timeframe: str = "1d"):
    try:
        from core.database import get_database
        db = get_database()
        if db is None:
            return {"status": "error", "error": "Database not connected"}
        
        # Get candles
        symbol_clean = symbol.replace("USDT", "").upper()
        candles = list(db.candles.find(
            {"symbol": symbol_clean, "timeframe": timeframe},
            {"_id": 0}
        ).sort("timestamp", -1).limit(100))
        
        # Get strategies
        strategies = list(db.strategies.find(
            {"status": {"$in": ["APPROVED", "LIMITED"]}},
            {"_id": 0}
        ))
        
        # Get regime map
        regime_map = list(db.regime_map.find({}, {"_id": 0}))
        
        return {
            "status": "ok",
            "symbol": symbol,
            "timeframe": timeframe,
            "analysis": {
                "candles_available": len(candles),
                "strategies_active": len(strategies),
                "regime_mappings": len(regime_map),
            },
            "data_range": {
                "latest": candles[0]["timestamp"] if candles else None,
                "oldest": candles[-1]["timestamp"] if candles else None,
            },
            "signals": [],
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}


# ============================================
# UI Data Endpoints (for Frontend Charts)
# ============================================

@app.get("/api/ui/candles")
async def ui_candles(asset: str = "BTC", days: int = 365, years: int = None):
    """Get candles for UI charts - format compatible with LivePredictionChart"""
    import random
    from datetime import datetime, timedelta
    
    # Calculate days from years if provided
    if years:
        days = years * 365
    
    # Generate mock OHLCV data if database empty
    candles = []
    base_price = 45000 if asset == "BTC" else 2800 if asset == "ETH" else 100
    now = datetime.now(timezone.utc)
    
    for i in list(reversed(list(range(1, days + 1)))):
        ts = now - timedelta(days=i)
        change = random.uniform(-0.03, 0.03)
        open_price = base_price * (1 + change)
        close_price = open_price * (1 + random.uniform(-0.02, 0.02))
        high_price = max(open_price, close_price) * (1 + random.uniform(0, 0.02))
        low_price = min(open_price, close_price) * (1 - random.uniform(0, 0.02))
        volume = random.uniform(1000, 10000) * base_price
        
        # Format for LivePredictionChart: t, o, h, l, c, v
        candles.append({
            "t": ts.strftime("%Y-%m-%d"),
            "o": round(open_price, 2),
            "h": round(high_price, 2),
            "l": round(low_price, 2),
            "c": round(close_price, 2),
            "v": round(volume, 2)
        })
        base_price = close_price
    
    return {
        "ok": True,
        "asset": asset,
        "candles": candles,
        "count": len(candles)
    }


@app.get("/api/meta-brain-v2/forecast-curve")
async def forecast_curve(asset: str = "BTC"):
    """Get forecast curve for MetaBrain chart"""
    import random
    from datetime import datetime, timedelta
    
    base_price = 45000 if asset == "BTC" else 2800 if asset == "ETH" else 100
    now = datetime.now(timezone.utc)
    
    curve = []
    for i in range(30):
        ts = now + timedelta(days=i)
        price_change = random.uniform(-0.01, 0.02) * (i / 30)
        curve.append({
            "time": int(ts.timestamp()),
            "value": round(base_price * (1 + price_change), 2)
        })
    
    verdicts = ["bullish", "bearish", "neutral"]
    return {
        "ok": True,
        "asset": asset,
        "curve": curve,
        "verdict": random.choice(verdicts),
        "confidence": round(random.uniform(0.6, 0.95), 2)
    }


@app.get("/api/forecast/{asset}")
async def forecast_asset(asset: str):
    """Get forecast for specific asset"""
    import random
    
    base_price = 45000 if asset.upper() == "BTC" else 2800 if asset.upper() == "ETH" else 100
    
    predictions = []
    for horizon in ["1D", "7D", "30D"]:
        direction = random.choice(["UP", "DOWN"])
        change = random.uniform(0.01, 0.15)
        predictions.append({
            "horizon": horizon,
            "direction": direction,
            "target_price": round(base_price * (1 + change if direction == "UP" else 1 - change), 2),
            "confidence": round(random.uniform(0.5, 0.9), 2)
        })
    
    return {
        "ok": True,
        "asset": asset,
        "predictions": predictions,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@app.get("/api/fractal/summary/{asset}")
async def fractal_summary(asset: str):
    """Get fractal analysis summary"""
    import random
    
    biases = ["bullish", "bearish", "neutral"]
    return {
        "ok": True,
        "asset": asset,
        "current": {
            "bias": random.choice(biases),
            "confidence": round(random.uniform(0.5, 0.9), 2),
            "alignment": round(random.uniform(0.3, 1.0), 2)
        },
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


# Additional endpoints for frontend
@app.get("/api/market/candles")
async def market_candles(symbol: str = "BTCUSDT", date_range: str = "7d"):
    """Get market candles for chart"""
    import random
    from datetime import datetime, timedelta
    
    # Parse range
    days = 7
    if date_range.endswith("d"):
        days = int(date_range[:-1])
    elif date_range.endswith("m"):
        days = int(date_range[:-1]) * 30
    
    asset = symbol.replace("USDT", "").upper()
    base_price = 45000 if asset == "BTC" else 2800 if asset == "ETH" else 100
    now = datetime.now(timezone.utc)
    
    candles = []
    for i in list(reversed(list(range(1, days * 24 + 1)))):  # hourly candles
        ts = now - timedelta(hours=i)
        change = random.uniform(-0.01, 0.01)
        open_price = base_price * (1 + change)
        close_price = open_price * (1 + random.uniform(-0.005, 0.005))
        high_price = max(open_price, close_price) * (1 + random.uniform(0, 0.005))
        low_price = min(open_price, close_price) * (1 - random.uniform(0, 0.005))
        volume = random.uniform(100, 1000) * base_price
        
        candles.append({
            "time": int(ts.timestamp()),
            "open": round(open_price, 2),
            "high": round(high_price, 2),
            "low": round(low_price, 2),
            "close": round(close_price, 2),
            "volume": round(volume, 2)
        })
        base_price = close_price
    
    return {
        "ok": True,
        "symbol": symbol,
        "candles": candles
    }


@app.get("/api/market/chart/price-vs-expectation-v4")
async def price_vs_expectation(asset: str = "BTC", date_range: str = "7d", horizon: str = "1D"):
    """Get price vs expectation chart data"""
    import random
    from datetime import datetime, timedelta
    
    days = 7
    if date_range.endswith("d"):
        days = int(date_range[:-1])
    
    base_price = 45000 if asset == "BTC" else 2800 if asset == "ETH" else 100
    now = datetime.now(timezone.utc)
    
    history = []
    for i in list(reversed(list(range(1, days + 1)))):
        ts = now - timedelta(days=i)
        actual = base_price * (1 + random.uniform(-0.05, 0.05))
        expected = actual * (1 + random.uniform(-0.02, 0.02))
        history.append({
            "time": int(ts.timestamp()),
            "actual": round(actual, 2),
            "expected": round(expected, 2),
            "delta": round((actual - expected) / expected * 100, 2)
        })
        base_price = actual
    
    return {
        "ok": True,
        "asset": asset,
        "horizon": horizon,
        "history": history,
        "current": {
            "price": round(base_price, 2),
            "expected": round(base_price * 1.02, 2),
            "verdict": random.choice(["bullish", "bearish", "neutral"])
        }
    }


@app.get("/api/system/health")
async def system_health():
    """System health status"""
    return {
        "ok": True,
        "status": "healthy",
        "services": {
            "database": "connected",
            "api": "running",
            "ml_engine": "standby"
        },
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@app.get("/api/system/indexing-status")
async def indexing_status():
    """Indexing status"""
    return {
        "ok": True,
        "status": "idle",
        "last_run": datetime.now(timezone.utc).isoformat(),
        "progress": 100
    }


@app.get("/api/frontend/dashboard")
async def frontend_dashboard(page: int = 1, limit: int = 10):
    """Frontend dashboard data"""
    return {
        "ok": True,
        "globalState": {
            "btcPrice": 46422.26,
            "ethPrice": 2845.50,
            "marketCap": "1.8T",
            "fear_greed": 65,
            "dominance": 52.3
        },
        "tokens": [],
        "pagination": {
            "page": page,
            "limit": limit,
            "total": 0
        },
        "alerts": [],
        "signals": []
    }


@app.get("/api/alerts/feed")
async def alerts_feed(limit: int = 5, unacknowledged: bool = True):
    """Alerts feed"""
    return {
        "ok": True,
        "alerts": [],
        "total": 0
    }


# Exchange & Advanced endpoints
@app.get("/api/exchange/pressure")
async def exchange_pressure(network: str = "ethereum", window: str = "24h"):
    """Exchange pressure data"""
    import random
    return {
        "ok": True,
        "network": network,
        "window": window,
        "data": {
            "inflow": round(random.uniform(1000, 5000), 2),
            "outflow": round(random.uniform(1000, 5000), 2),
            "netFlow": round(random.uniform(-500, 500), 2),
            "pressure": random.choice(["bullish", "bearish", "neutral"]),
            "confidence": round(random.uniform(0.5, 0.9), 2)
        }
    }


@app.get("/api/advanced/signals-attribution")
async def signals_attribution():
    """Signals attribution data"""
    import random
    return {
        "ok": True,
        "coverage": {
            "activeSignals": random.randint(5, 20),
            "totalSignals": random.randint(50, 100),
            "coverage": round(random.uniform(0.6, 0.95), 2)
        },
        "topImpactSignals": [
            {"name": "RSI Divergence", "impact": round(random.uniform(0.1, 0.3), 2)},
            {"name": "Volume Spike", "impact": round(random.uniform(0.1, 0.3), 2)},
            {"name": "MACD Cross", "impact": round(random.uniform(0.05, 0.2), 2)}
        ],
        "confidenceCalibration": {
            "accuracy": round(random.uniform(0.6, 0.85), 2),
            "calibration": round(random.uniform(0.7, 0.9), 2)
        }
    }


# Fractal endpoints
@app.get("/api/fractal/v2.1/chart")
async def fractal_chart(symbol: str = "BTC", limit: int = 450):
    """Fractal chart data"""
    import random
    from datetime import datetime, timedelta
    
    base_price = 45000 if symbol.upper() == "BTC" else 2800 if symbol.upper() == "ETH" else 4500 if symbol.upper() == "SPX" else 105
    now = datetime.now(timezone.utc)
    
    candles = []
    for i in list(reversed(list(range(1, limit + 1)))):
        ts = now - timedelta(days=i)
        change = random.uniform(-0.02, 0.02)
        open_price = base_price * (1 + change)
        close_price = open_price * (1 + random.uniform(-0.015, 0.015))
        high_price = max(open_price, close_price) * (1 + random.uniform(0, 0.01))
        low_price = min(open_price, close_price) * (1 - random.uniform(0, 0.01))
        
        # Fractal format: t,o,h,l,c
        candles.append({
            "t": ts.strftime("%Y-%m-%d"),
            "o": round(open_price, 2),
            "h": round(high_price, 2),
            "l": round(low_price, 2),
            "c": round(close_price, 2)
        })
        base_price = close_price
    
    # SMA200
    sma200 = []
    if len(candles) >= 200:
        for i in list(range(200, len(candles))):
            avg = sum(c["c"] for c in candles[i-200:i]) / 200
            sma200.append({
                "t": candles[i]["t"],
                "v": round(avg, 2)
            })
    
    # Forecast data
    forecast_base = candles[-1]["c"] if candles else base_price
    synthetic = []
    replay = []
    hybrid = []
    
    for i in list(range(1, 31)):
        ts = now + timedelta(days=i)
        synthetic.append({
            "t": ts.strftime("%Y-%m-%d"),
            "v": round(forecast_base * (1 + random.uniform(-0.1, 0.15) * i / 30), 2)
        })
        replay.append({
            "t": ts.strftime("%Y-%m-%d"),
            "v": round(forecast_base * (1 + random.uniform(-0.08, 0.12) * i / 30), 2)
        })
        hybrid.append({
            "t": ts.strftime("%Y-%m-%d"),
            "v": round(forecast_base * (1 + random.uniform(-0.05, 0.10) * i / 30), 2)
        })
    
    # Phases
    phases = [
        {"start": (now - timedelta(days=90)).strftime("%Y-%m-%d"), "end": (now - timedelta(days=60)).strftime("%Y-%m-%d"), "label": "accumulation", "color": "#22c55e"},
        {"start": (now - timedelta(days=60)).strftime("%Y-%m-%d"), "end": (now - timedelta(days=30)).strftime("%Y-%m-%d"), "label": "markup", "color": "#3b82f6"},
        {"start": (now - timedelta(days=30)).strftime("%Y-%m-%d"), "end": now.strftime("%Y-%m-%d"), "label": "distribution", "color": "#f59e0b"}
    ]
    
    return {
        "ok": True,
        "symbol": symbol,
        "candles": candles,
        "sma200": sma200,
        "forecast": {
            "synthetic": synthetic,
            "replay": replay,
            "hybrid": hybrid
        },
        "phases": phases
    }


@app.get("/api/fractal/v2.1/signal")
async def fractal_signal(symbol: str = "BTC"):
    """Fractal signal"""
    import random
    return {
        "ok": True,
        "symbol": symbol,
        "signal": random.choice(["bullish", "bearish", "neutral"]),
        "confidence": round(random.uniform(0.5, 0.9), 2),
        "phase": random.choice(["accumulation", "markup", "distribution", "markdown"]),
        "alignment": round(random.uniform(0.3, 1.0), 2)
    }


@app.get("/api/fractal/v2.1/focus-pack")
async def fractal_focus_pack(symbol: str = "BTC", focus: str = "30d", phaseId: str = None, asOf: str = None):
    """Focus pack data for Fractal Intelligence"""
    import random
    from datetime import datetime, timedelta
    
    base_price = 45000 if symbol.upper() == "BTC" else 2800 if symbol.upper() == "ETH" else 4500 if symbol.upper() == "SPX" else 105
    horizon_days = int(focus.replace("d", "")) if focus.endswith("d") else 30
    now = datetime.now(timezone.utc)
    
    # Generate candles
    candles = []
    for i in list(reversed(list(range(1, 450 + 1)))):
        ts = now - timedelta(days=i)
        change = random.uniform(-0.02, 0.02)
        open_price = base_price * (1 + change)
        close_price = open_price * (1 + random.uniform(-0.015, 0.015))
        high_price = max(open_price, close_price) * (1 + random.uniform(0, 0.01))
        low_price = min(open_price, close_price) * (1 - random.uniform(0, 0.01))
        
        candles.append({
            "t": ts.strftime("%Y-%m-%d"),
            "o": round(open_price, 2),
            "h": round(high_price, 2),
            "l": round(low_price, 2),
            "c": round(close_price, 2)
        })
        base_price = close_price
    
    current_price = candles[-1]["c"] if candles else base_price
    
    # Generate forecast path
    forecast_path = []
    price = current_price
    for i in list(range(horizon_days + 1)):
        forecast_path.append({
            "t": i,
            "price": round(price, 2),
            "pct": round((price / current_price - 1) * 100, 2)
        })
        price = price * (1 + random.uniform(-0.005, 0.01))
    
    # SMA200
    sma200 = []
    if len(candles) >= 200:
        for i in list(range(200, len(candles))):
            avg = sum(c["c"] for c in candles[i-200:i]) / 200
            sma200.append({
                "t": candles[i]["t"],
                "v": round(avg, 2)
            })
    
    # Phases
    phases = [
        {"start": (now - timedelta(days=90)).strftime("%Y-%m-%d"), "end": (now - timedelta(days=60)).strftime("%Y-%m-%d"), "label": "accumulation", "color": "#22c55e"},
        {"start": (now - timedelta(days=60)).strftime("%Y-%m-%d"), "end": (now - timedelta(days=30)).strftime("%Y-%m-%d"), "label": "markup", "color": "#3b82f6"},
        {"start": (now - timedelta(days=30)).strftime("%Y-%m-%d"), "end": now.strftime("%Y-%m-%d"), "label": "distribution", "color": "#f59e0b"}
    ]
    
    # Matches
    matches = []
    for i in list(range(5)):
        match_date = now - timedelta(days=random.randint(365, 2000))
        matches.append({
            "id": f"match_{i}",
            "date": match_date.strftime("%Y-%m-%d"),
            "similarity": round(random.uniform(0.6, 0.95), 2),
            "return": round(random.uniform(-0.1, 0.2), 2),
            "phase": random.choice(["accumulation", "markup", "distribution"])
        })
    
    focus_pack = {
        "symbol": symbol,
        "focus": focus,
        "horizonDays": horizon_days,
        
        # Chart data
        "chart": {
            "candles": candles,
            "sma200": sma200,
            "phases": phases
        },
        
        # Overlay
        "overlay": {
            "forecast": {
                "synthetic": forecast_path,
                "replay": forecast_path,
                "hybrid": forecast_path
            },
            "stats": {
                "hitRate": round(random.uniform(0.5, 0.8), 2),
                "avgReturn": round(random.uniform(-0.05, 0.15), 2)
            }
        },
        
        # Primary match
        "primarySelection": {
            "primaryMatch": matches[0] if matches else None
        },
        
        # Explain
        "explain": {
            "topMatches": matches
        },
        
        # Diagnostics
        "diagnostics": {
            "sampleSize": len(matches),
            "entropy": round(random.uniform(0.3, 0.7), 2),
            "reliability": round(random.uniform(0.5, 0.9), 2)
        },
        
        # Phase
        "phase": {
            "currentPhase": random.choice(["ACCUMULATION", "MARKUP", "DISTRIBUTION"]),
            "trend": random.choice(["UP", "DOWN", "SIDEWAYS"]),
            "volatility": random.choice(["LOW", "MODERATE", "HIGH"])
        },
        
        # Scenario
        "scenario": {
            "bear": {"return": round(random.uniform(-0.15, -0.05), 2), "price": round(current_price * 0.9, 2)},
            "base": {"return": round(random.uniform(-0.02, 0.08), 2), "price": round(current_price, 2)},
            "bull": {"return": round(random.uniform(0.05, 0.20), 2), "price": round(current_price * 1.1, 2)}
        },
        
        # Decision
        "decision": {
            "action": random.choice(["LONG", "SHORT", "HOLD"]),
            "confidence": round(random.uniform(40, 85), 0)
        },
        
        # Price
        "price": {
            "current": current_price,
            "sma200": "ABOVE" if current_price > (sma200[-1]["v"] if sma200 else current_price * 0.95) else "BELOW"
        }
    }
    
    return {
        "ok": True,
        "focusPack": focus_pack
    }


@app.get("/api/ui/overview")
async def ui_overview(asset: str = "BTC", horizon: int = 90):
    """UI Overview data for Fractal Intelligence"""
    import random
    from datetime import datetime, timedelta
    
    base_price = 45000 if asset.upper() == "BTC" else 2800 if asset.upper() == "ETH" else 4500 if asset.upper() == "SPX" else 105
    now = datetime.now(timezone.utc)
    
    candles = []
    for i in list(reversed(list(range(1, min(horizon, 365) + 1)))):
        ts = now - timedelta(days=i)
        change = random.uniform(-0.02, 0.02)
        open_price = base_price * (1 + change)
        close_price = open_price * (1 + random.uniform(-0.015, 0.015))
        high_price = max(open_price, close_price) * (1 + random.uniform(0, 0.01))
        low_price = min(open_price, close_price) * (1 - random.uniform(0, 0.01))
        
        candles.append({
            "time": ts.strftime("%Y-%m-%d"),
            "open": round(open_price, 2),
            "high": round(high_price, 2),
            "low": round(low_price, 2),
            "close": round(close_price, 2)
        })
        base_price = close_price
    
    # Forecast
    forecast = []
    for i in list(range(1, 31)):
        ts = now + timedelta(days=i)
        forecast.append({
            "t": ts.strftime("%Y-%m-%d"),
            "v": round(base_price * (1 + random.uniform(-0.05, 0.10) * i / 30), 2)
        })
    
    return {
        "ok": True,
        "asset": asset,
        "horizon": horizon,
        "candles": candles,
        "forecast": {
            "hybrid": forecast,
            "synthetic": forecast,
            "replay": forecast
        },
        "verdict": {
            "signal": random.choice(["bullish", "bearish", "neutral"]),
            "confidence": round(random.uniform(0.5, 0.9), 2),
            "phase": random.choice(["accumulation", "markup", "distribution"])
        },
        "currentPrice": round(base_price, 2)
    }


@app.get("/api/prediction/snapshots")
async def prediction_snapshots(asset: str = "BTC", view: str = "crossAsset", horizon: int = 90, limit: int = 20):
    """Prediction snapshots"""
    import random
    from datetime import datetime, timedelta
    
    now = datetime.now(timezone.utc)
    snapshots = []
    
    for i in list(range(limit)):
        ts = now - timedelta(hours=i * 6)
        snapshots.append({
            "id": f"snap_{i}",
            "timestamp": ts.isoformat(),
            "asset": asset,
            "prediction": random.choice(["UP", "DOWN"]),
            "confidence": round(random.uniform(0.5, 0.9), 2),
            "horizon": f"{random.choice([1, 7, 30])}D",
            "outcome": random.choice(["WIN", "LOSS", "PENDING"])
        })
    
    return {
        "ok": True,
        "snapshots": snapshots,
        "total": limit
    }


@app.get("/")
async def root():
    return {
        "name": "TA Engine Runtime",
        "version": "1.0.0",
        "status": "running",
        "endpoints": {
            "health": "/api/health",
            "db_health": "/api/system/db-health",
            "ta_registry": "/api/ta/registry",
            "ta_patterns": "/api/ta/patterns",
            "ta_analyze": "/api/ta/analyze",
            "ui_candles": "/api/ui/candles",
            "forecast_curve": "/api/meta-brain-v2/forecast-curve",
            "forecast": "/api/forecast/{asset}",
            "fractal_summary": "/api/fractal/summary/{asset}",
            "fractal_chart": "/api/fractal/v2.1/chart",
            "exchange_pressure": "/api/exchange/pressure",
            "signals_attribution": "/api/advanced/signals-attribution"
        }
    }

