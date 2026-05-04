"""
System Dashboard & Config Module

Final backend micro-tasks:
1. System Status Aggregator - aggregated dashboard endpoint
2. System Snapshot - save system state for debug/replay
3. Global Config Registry - runtime configuration
"""

from typing import Optional, Dict, List, Any
from datetime import datetime, timezone
from pydantic import BaseModel, Field
import os


# ══════════════════════════════════════════════════════════════
# 1. System Status Dashboard
# ══════════════════════════════════════════════════════════════

class DashboardStatus(BaseModel):
    """Aggregated system status for dashboard."""
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    # Overall health
    system_health: str = "HEALTHY"  # HEALTHY, DEGRADED, UNHEALTHY
    
    # Portfolio
    portfolio_exposure: float = 0.0
    open_positions: int = 0
    unrealized_pnl: float = 0.0
    total_equity_usd: float = 0.0
    
    # Orders
    pending_orders: int = 0
    orders_today: int = 0
    
    # Safety
    kill_switch_status: str = "ACTIVE"  # ACTIVE, TRIGGERED
    circuit_breakers_tripped: int = 0
    trade_throttle_level: str = "NONE"
    
    # Trading mode
    trading_mode: str = "PILOT"
    execution_mode: str = "APPROVAL"
    
    # Latency
    latency_avg_ms: float = 0.0
    latency_p95_ms: float = 0.0
    latency_p99_ms: float = 0.0
    
    # Queues
    execution_queue_depth: int = 0
    signal_queue_depth: int = 0
    
    # Errors
    error_rate: float = 0.0
    errors_last_hour: int = 0
    
    # Exchange connectivity
    exchanges_connected: List[str] = Field(default_factory=list)
    exchanges_disconnected: List[str] = Field(default_factory=list)
    
    # Reconciliation
    positions_synced: bool = True
    last_reconciliation: Optional[datetime] = None
    
    # Alpha / Intelligence
    active_hypotheses: int = 0
    dominant_alpha_family: Optional[str] = None
    avg_signal_decay: float = 1.0


def get_dashboard_status() -> DashboardStatus:
    """Aggregate all system status into single dashboard object."""
    status = DashboardStatus()
    
    # Get system metrics
    try:
        from modules.system_metrics import get_metrics_engine
        metrics_engine = get_metrics_engine()
        metrics = metrics_engine.get_metrics()
        health = metrics_engine.get_health()
        
        status.system_health = health.status
        status.latency_avg_ms = metrics.avg_latency_ms
        status.latency_p95_ms = metrics.p95_latency_ms
        status.latency_p99_ms = metrics.p99_latency_ms
        status.error_rate = metrics.api_error_rate
        status.errors_last_hour = metrics.total_errors_1h
        status.execution_queue_depth = metrics.execution_queue_depth
        status.signal_queue_depth = metrics.signal_queue_depth
    except Exception:
        pass
    
    # Get pilot mode
    try:
        from modules.pilot_mode import get_pilot_mode_engine
        pilot = get_pilot_mode_engine()
        state = pilot.get_state()
        status.trading_mode = state.trading_mode.value
        status.orders_today = state.trades_today
    except Exception:
        pass
    
    # Get trade throttle
    try:
        from modules.trade_throttle import get_trade_throttle_engine
        throttle = get_trade_throttle_engine()
        state = throttle.get_state()
        status.trade_throttle_level = state.throttle_level.value
    except Exception:
        pass
    
    # Get reconciliation
    try:
        from modules.execution_reconciliation import get_reconciliation_engine
        recon = get_reconciliation_engine()
        state = recon.get_state()
        status.positions_synced = state.is_synced
        status.last_reconciliation = state.last_check
    except Exception:
        pass
    
    # Get exchange sync
    try:
        from modules.exchange_sync import get_exchange_sync_engine
        sync = get_exchange_sync_engine()
        summary = sync.get_summary()
        status.exchanges_connected = list(summary.get("exchanges", {}).keys())
        status.open_positions = summary.get("total_positions", 0)
    except Exception:
        pass
    
    # Get meta-alpha
    try:
        from modules.meta_alpha_portfolio import get_meta_alpha_engine
        meta = get_meta_alpha_engine()
        state = meta.get_state()
        status.dominant_alpha_family = state.dominant_alpha_family
    except Exception:
        pass
    
    # Get alpha decay
    try:
        from modules.alpha_decay import get_alpha_decay_engine
        decay = get_alpha_decay_engine()
        summary = decay.get_summary()
        status.active_hypotheses = summary.total_signals
        status.avg_signal_decay = summary.avg_decay_factor
    except Exception:
        pass
    
    return status


# ══════════════════════════════════════════════════════════════
# 2. System Snapshot
# ══════════════════════════════════════════════════════════════

class SystemSnapshot(BaseModel):
    """Complete system state snapshot for debug/replay."""
    snapshot_id: str = Field(default_factory=lambda: f"snap_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S%f')}")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    # Dashboard status
    dashboard: Optional[Dict] = None
    
    # Portfolio state
    portfolio: Optional[Dict] = None
    positions: List[Dict] = Field(default_factory=list)
    
    # Signals state
    active_signals: List[Dict] = Field(default_factory=list)
    decay_states: List[Dict] = Field(default_factory=list)
    
    # Alpha weights
    alpha_weights: Optional[Dict] = None
    
    # Risk state
    risk_state: Optional[Dict] = None
    
    # Market context
    market_context: Optional[Dict] = None
    
    # Config
    system_config: Optional[Dict] = None
    
    # Reason for snapshot
    reason: str = "manual"
    notes: str = ""


async def create_system_snapshot(reason: str = "manual", notes: str = "") -> SystemSnapshot:
    """Create a complete system snapshot."""
    snapshot = SystemSnapshot(reason=reason, notes=notes)
    
    # Dashboard
    snapshot.dashboard = get_dashboard_status().model_dump()
    
    # Positions
    try:
        from modules.exchange_sync import get_exchange_sync_engine
        sync = get_exchange_sync_engine()
        positions = sync.get_positions()
        snapshot.positions = [p.model_dump() for p in positions]
    except Exception:
        pass
    
    # Alpha decay states
    try:
        from modules.alpha_decay import get_alpha_decay_engine
        decay = get_alpha_decay_engine()
        states = list(decay._decay_states.values())
        snapshot.decay_states = [s.model_dump() for s in states[:100]]
    except Exception:
        pass
    
    # Alpha weights
    try:
        from modules.meta_alpha_portfolio import get_meta_alpha_engine
        meta = get_meta_alpha_engine()
        snapshot.alpha_weights = meta.get_portfolio_allocation_weights()
    except Exception:
        pass
    
    # Config
    snapshot.system_config = get_system_config().model_dump()
    
    # Save to MongoDB
    await save_snapshot(snapshot)
    
    return snapshot


async def save_snapshot(snapshot: SystemSnapshot):
    """Save snapshot to MongoDB."""
    try:
        from motor.motor_asyncio import AsyncIOMotorClient
        
        mongo_url = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
        db_name = os.environ.get("DB_NAME", "fomo_trading")
        
        client = AsyncIOMotorClient(mongo_url)
        db = client[db_name]
        
        await db.system_snapshots.insert_one(snapshot.model_dump())
        client.close()
    except Exception:
        pass


async def get_snapshots(limit: int = 10) -> List[SystemSnapshot]:
    """Get recent snapshots."""
    try:
        from motor.motor_asyncio import AsyncIOMotorClient
        
        mongo_url = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
        db_name = os.environ.get("DB_NAME", "fomo_trading")
        
        client = AsyncIOMotorClient(mongo_url)
        db = client[db_name]
        
        cursor = db.system_snapshots.find().sort("timestamp", -1).limit(limit)
        
        snapshots = []
        async for doc in cursor:
            doc.pop("_id", None)
            snapshots.append(SystemSnapshot(**doc))
        
        client.close()
        return snapshots
    except Exception:
        return []


# ══════════════════════════════════════════════════════════════
# 3. Global Config Registry
# ══════════════════════════════════════════════════════════════

class SystemConfig(BaseModel):
    """Global system configuration."""
    config_id: str = "main"
    
    # Trading mode
    trading_mode: str = "PILOT"  # PAPER, PILOT, LIVE
    execution_mode: str = "APPROVAL"  # APPROVAL, LIVE
    
    # Risk limits
    max_portfolio_exposure_pct: float = 30.0
    max_position_size_pct: float = 5.0
    max_daily_drawdown_pct: float = 5.0
    max_single_trade_usd: float = 10000.0
    
    # Throttle rules
    max_trades_per_5min: int = 3
    max_trades_per_hour: int = 10
    max_turnover_per_hour_pct: float = 15.0
    loss_streak_cooldown_minutes: int = 10
    
    # Pilot config
    pilot_max_capital_pct: float = 5.0
    pilot_max_position_pct: float = 2.0
    pilot_max_order_usd: float = 5000.0
    
    # Alpha decay half-lives (minutes)
    half_life_trend: int = 120
    half_life_breakout: int = 90
    half_life_mean_reversion: int = 30
    half_life_fractal: int = 180
    half_life_default: int = 60
    
    # Meta-alpha thresholds
    meta_alpha_strong_threshold: float = 0.70
    meta_alpha_moderate_threshold: float = 0.55
    
    # Safety
    kill_switch_enabled: bool = True
    circuit_breaker_enabled: bool = True
    auto_reconciliation_enabled: bool = True
    
    # Reconciliation
    reconciliation_interval_seconds: int = 15
    position_tolerance_pct: float = 0.01
    
    # Exchange adapters
    enabled_exchanges: List[str] = Field(default_factory=lambda: ["BINANCE", "BYBIT"])
    
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# In-memory config (loaded from DB on startup)
_system_config: Optional[SystemConfig] = None


def get_system_config() -> SystemConfig:
    """Get current system configuration."""
    global _system_config
    if _system_config is None:
        _system_config = SystemConfig()
    return _system_config


def update_system_config(updates: Dict[str, Any]) -> SystemConfig:
    """Update system configuration."""
    global _system_config
    
    config = get_system_config()
    
    # Apply updates
    for key, value in updates.items():
        if hasattr(config, key):
            setattr(config, key, value)
    
    config.updated_at = datetime.now(timezone.utc)
    _system_config = config
    
    return config


async def save_config_to_db():
    """Save config to MongoDB."""
    try:
        from motor.motor_asyncio import AsyncIOMotorClient
        
        mongo_url = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
        db_name = os.environ.get("DB_NAME", "fomo_trading")
        
        client = AsyncIOMotorClient(mongo_url)
        db = client[db_name]
        
        config = get_system_config()
        await db.system_config.update_one(
            {"config_id": "main"},
            {"$set": config.model_dump()},
            upsert=True,
        )
        
        client.close()
    except Exception:
        pass


async def load_config_from_db():
    """Load config from MongoDB."""
    global _system_config
    
    try:
        from motor.motor_asyncio import AsyncIOMotorClient
        
        mongo_url = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
        db_name = os.environ.get("DB_NAME", "fomo_trading")
        
        client = AsyncIOMotorClient(mongo_url)
        db = client[db_name]
        
        doc = await db.system_config.find_one({"config_id": "main"})
        if doc:
            doc.pop("_id", None)
            _system_config = SystemConfig(**doc)
        
        client.close()
    except Exception:
        pass
