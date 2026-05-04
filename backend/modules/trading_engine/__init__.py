"""
Trading Engine Module

Transforms indicator intelligence into trading decisions and signals.

Components:
- EntryFilterEngine: Allow/block trades based on feature vector
- PositionSizeEngine: Scale position by indicator confidence  
- StopLossEngine: ATR/Donchian/Keltner based stops
- TakeProfitEngine: R:R based targets
- MarketStateEngine: Regime detection (trending/ranging/breakout)
- SignalEngine: Generate formalized trading signals
- SignalStorageService: MongoDB persistence for signals
- TradingEngineService: Main orchestration service
"""

from .entry_filter_engine import (
    # Types
    TradeDirection,
    EntryDecision,
    PositionSizeDecision,
    StopLossDecision,
    TakeProfitDecision,
    TradingDecision,
    TradingConfig,
    
    # Engines
    EntryFilterEngine,
    PositionSizeEngine,
    StopLossEngine,
    TakeProfitEngine,
    ScenarioValidationEngine,
    TradingEngineService,
    
    # Factory
    get_trading_engine,
)

from .market_state_engine import (
    MarketState,
    MarketStateResult,
    MarketStateEngine,
    get_market_state_engine,
    STATE_INDICATOR_MAP,
)

from .signal_engine import (
    SignalDirection,
    SignalStrength,
    SignalStatus,
    TradingSignal,
    SignalAlert,
    SignalEngine,
    get_signal_engine,
)

from .signal_storage import (
    SignalStorageService,
    get_signal_storage,
)

__all__ = [
    # Types
    "TradeDirection",
    "EntryDecision",
    "PositionSizeDecision",
    "StopLossDecision",
    "TakeProfitDecision",
    "TradingDecision",
    "TradingConfig",
    "MarketState",
    "MarketStateResult",
    "SignalDirection",
    "SignalStrength",
    "SignalStatus",
    "TradingSignal",
    "SignalAlert",
    
    # Engines
    "EntryFilterEngine",
    "PositionSizeEngine",
    "StopLossEngine",
    "TakeProfitEngine",
    "ScenarioValidationEngine",
    "TradingEngineService",
    "MarketStateEngine",
    "SignalEngine",
    "SignalStorageService",
    
    # Factories
    "get_trading_engine",
    "get_market_state_engine",
    "get_signal_engine",
    "get_signal_storage",
    
    # Config
    "STATE_INDICATOR_MAP",
]
