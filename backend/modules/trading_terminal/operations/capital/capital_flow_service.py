"""
OPS4 Capital Flow Service
=========================

Main service for capital flow management.

Provides:
- Capital state monitoring
- Strategy allocation tracking
- Exposure analysis
- Capital efficiency metrics
- Risk concentration analysis
"""

import os
import time
import threading
import random
from typing import Dict, List, Optional, Any

from .capital_types import (
    CapitalState,
    StrategyAllocation,
    ExposureView,
    ExposureBreakdown,
    CapitalFlowEvent,
    CapitalTimeline,
    FlowEventType,
    RiskConcentration,
    CapitalEfficiency,
    PortfolioMetrics
)

# MongoDB connection
try:
    from pymongo import MongoClient, DESCENDING
    MONGO_URI = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
    DB_NAME = os.environ.get("DB_NAME", "ta_engine")
    client = MongoClient(MONGO_URI)
    db = client[DB_NAME]
    MONGO_AVAILABLE = True
except Exception as e:
    print(f"[CapitalFlowService] MongoDB not available: {e}")
    MONGO_AVAILABLE = False
    db = None


class CapitalFlowService:
    """
    Main service for OPS4 Capital Flow.
    
    Answers: WHERE is capital and how is it being used?
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        # Base capital for mock data
        self._base_equity = 50000.0
        
        # Cache
        self._state_cache: Optional[CapitalState] = None
        self._cache_timestamp: int = 0
        self._cache_ttl_ms: int = 5000  # 5 seconds
        
        self._initialized = True
        print("[CapitalFlowService] Initialized (OPS4)")
    
    # ===========================================
    # Capital State
    # ===========================================
    
    def get_capital_state(self) -> CapitalState:
        """
        Get current capital state.
        """
        
        # Check cache
        now = int(time.time() * 1000)
        if self._state_cache and (now - self._cache_timestamp) < self._cache_ttl_ms:
            return self._state_cache
        
        # Try to get from database
        state = self._fetch_capital_state()
        
        if not state:
            state = self._generate_mock_state()
        
        # Update cache
        self._state_cache = state
        self._cache_timestamp = now
        
        return state
    
    def _fetch_capital_state(self) -> Optional[CapitalState]:
        """Fetch capital state from database"""
        if not MONGO_AVAILABLE:
            return None
        
        try:
            # Query accounts/positions for real data
            accounts = list(db.accounts.find({})) if "accounts" in db.list_collection_names() else []
            positions = list(db.positions.find({"status": "OPEN"})) if "positions" in db.list_collection_names() else []
            
            if not accounts:
                return None
            
            total_equity = sum(a.get("equity", 0) for a in accounts)
            used_margin = sum(p.get("margin_used", 0) for p in positions)
            unrealized = sum(p.get("unrealized_pnl", 0) for p in positions)
            
            return CapitalState(
                total_equity=total_equity,
                used_margin=used_margin,
                free_margin=total_equity - used_margin,
                unrealized_pnl=unrealized,
                open_positions=len(positions)
            )
        except Exception as e:
            print(f"[CapitalFlowService] Fetch state error: {e}")
            return None
    
    # ===========================================
    # Strategy Allocations
    # ===========================================
    
    def get_strategy_allocations(self) -> List[StrategyAllocation]:
        """
        Get capital allocation by strategy.
        """
        
        # Try database first
        allocations = self._fetch_strategy_allocations()
        
        if not allocations:
            allocations = self._generate_mock_allocations()
        
        return allocations
    
    def get_strategy_allocation(self, strategy_id: str) -> Optional[StrategyAllocation]:
        """
        Get allocation for specific strategy.
        """
        
        allocations = self.get_strategy_allocations()
        
        for alloc in allocations:
            if alloc.strategy_id == strategy_id:
                return alloc
        
        # Generate mock if not found
        return self._generate_mock_allocation(strategy_id)
    
    def _fetch_strategy_allocations(self) -> List[StrategyAllocation]:
        """Fetch allocations from database"""
        if not MONGO_AVAILABLE:
            return []
        
        try:
            # Query strategy allocations
            if "strategy_allocations" in db.list_collection_names():
                docs = list(db.strategy_allocations.find({}))
                return [self._doc_to_allocation(d) for d in docs]
            return []
        except Exception as e:
            print(f"[CapitalFlowService] Fetch allocations error: {e}")
            return []
    
    def _doc_to_allocation(self, doc: Dict) -> StrategyAllocation:
        """Convert document to StrategyAllocation"""
        return StrategyAllocation(
            strategy_id=doc.get("strategy_id", ""),
            strategy_name=doc.get("strategy_name", ""),
            capital_allocated=doc.get("capital_allocated", 0),
            capital_used=doc.get("capital_used", 0),
            unrealized_pnl=doc.get("unrealized_pnl", 0),
            realized_pnl=doc.get("realized_pnl", 0)
        )
    
    # ===========================================
    # Exposure Analysis
    # ===========================================
    
    def get_exposure_by_symbol(self) -> List[ExposureView]:
        """
        Get exposure breakdown by symbol.
        """
        
        exposures = self._fetch_symbol_exposures()
        
        if not exposures:
            exposures = self._generate_mock_symbol_exposures()
        
        return exposures
    
    def get_exposure_by_exchange(self) -> Dict[str, float]:
        """
        Get exposure breakdown by exchange.
        """
        
        return self._generate_mock_exchange_exposures()
    
    def get_exposure_breakdown(self) -> ExposureBreakdown:
        """
        Get complete exposure breakdown.
        """
        
        symbol_exposures = self.get_exposure_by_symbol()
        exchange_exposures = self.get_exposure_by_exchange()
        strategy_allocations = self.get_strategy_allocations()
        
        strategy_exposures = {
            a.strategy_id: a.capital_used for a in strategy_allocations
        }
        
        total_exposure = sum(e.exposure_usd for e in symbol_exposures)
        long_exposure = sum(e.exposure_usd for e in symbol_exposures if e.side in ["LONG", "MIXED"])
        short_exposure = sum(e.exposure_usd for e in symbol_exposures if e.side == "SHORT")
        
        return ExposureBreakdown(
            by_symbol=symbol_exposures,
            by_strategy=strategy_exposures,
            by_exchange=exchange_exposures,
            by_side={"LONG": long_exposure, "SHORT": short_exposure},
            total_exposure_usd=total_exposure,
            long_exposure_usd=long_exposure,
            short_exposure_usd=short_exposure,
            net_exposure_usd=long_exposure - short_exposure
        )
    
    def _fetch_symbol_exposures(self) -> List[ExposureView]:
        """Fetch symbol exposures from positions"""
        if not MONGO_AVAILABLE:
            return []
        
        try:
            if "positions" not in db.list_collection_names():
                return []
            
            pipeline = [
                {"$match": {"status": "OPEN"}},
                {"$group": {
                    "_id": "$symbol",
                    "total_exposure": {"$sum": "$exposure_usd"},
                    "count": {"$sum": 1}
                }}
            ]
            
            results = list(db.positions.aggregate(pipeline))
            
            return [
                ExposureView(
                    symbol=r["_id"],
                    exposure_usd=r["total_exposure"],
                    position_count=r["count"]
                )
                for r in results
            ]
        except Exception as e:
            print(f"[CapitalFlowService] Fetch exposures error: {e}")
            return []
    
    # ===========================================
    # Capital Timeline
    # ===========================================
    
    def get_capital_timeline(
        self,
        period_hours: int = 24
    ) -> CapitalTimeline:
        """
        Get capital flow timeline.
        """
        
        events = self._fetch_capital_events(period_hours)
        
        if not events:
            events = self._generate_mock_timeline_events(period_hours)
        
        # Calculate summary
        start_balance = events[0].balance_after - events[0].amount if events else self._base_equity
        end_balance = events[-1].balance_after if events else self._base_equity
        
        period_end = int(time.time() * 1000)
        period_start = period_end - (period_hours * 3600 * 1000)
        
        return CapitalTimeline(
            events=events,
            start_balance=start_balance,
            end_balance=end_balance,
            net_flow=end_balance - start_balance,
            period_start=period_start,
            period_end=period_end
        )
    
    def _fetch_capital_events(self, period_hours: int) -> List[CapitalFlowEvent]:
        """Fetch capital events from database"""
        if not MONGO_AVAILABLE:
            return []
        
        try:
            if "capital_events" not in db.list_collection_names():
                return []
            
            cutoff = int(time.time() * 1000) - (period_hours * 3600 * 1000)
            
            docs = list(db.capital_events.find(
                {"timestamp": {"$gte": cutoff}}
            ).sort("timestamp", 1))
            
            return [self._doc_to_event(d) for d in docs]
        except Exception as e:
            print(f"[CapitalFlowService] Fetch events error: {e}")
            return []
    
    def _doc_to_event(self, doc: Dict) -> CapitalFlowEvent:
        """Convert document to CapitalFlowEvent"""
        return CapitalFlowEvent(
            event_id=doc.get("event_id", ""),
            event_type=FlowEventType(doc.get("event_type", "CAPITAL_ALLOCATED")),
            timestamp=doc.get("timestamp", 0),
            amount=doc.get("amount", 0),
            strategy_id=doc.get("strategy_id"),
            position_id=doc.get("position_id"),
            symbol=doc.get("symbol"),
            balance_after=doc.get("balance_after", 0)
        )
    
    # ===========================================
    # Risk Concentration
    # ===========================================
    
    def get_risk_concentration(self) -> RiskConcentration:
        """
        Analyze risk concentration.
        """
        
        state = self.get_capital_state()
        exposures = self.get_exposure_by_symbol()
        allocations = self.get_strategy_allocations()
        exchange_exp = self.get_exposure_by_exchange()
        
        # Find largest position
        largest_symbol = None
        largest_exposure = 0.0
        
        for exp in exposures:
            if exp.exposure_usd > largest_exposure:
                largest_exposure = exp.exposure_usd
                largest_symbol = exp.symbol
        
        # Find largest strategy
        largest_strategy = None
        largest_strat_exp = 0.0
        
        for alloc in allocations:
            if alloc.capital_used > largest_strat_exp:
                largest_strat_exp = alloc.capital_used
                largest_strategy = alloc.strategy_id
        
        # Find largest exchange
        largest_exchange = None
        largest_exch_exp = 0.0
        
        for exch, exp in exchange_exp.items():
            if exp > largest_exch_exp:
                largest_exch_exp = exp
                largest_exchange = exch
        
        # Calculate Herfindahl index (concentration)
        total_exp = state.exposure_usd or 1
        hhi = sum((e.exposure_usd / total_exp) ** 2 for e in exposures)
        
        # Top 3 concentration
        sorted_exp = sorted(exposures, key=lambda x: x.exposure_usd, reverse=True)
        top3_exp = sum(e.exposure_usd for e in sorted_exp[:3])
        top3_pct = top3_exp / total_exp if total_exp > 0 else 0
        
        # Risk flags
        flags = []
        if largest_exposure > total_exp * 0.5:
            flags.append("HIGH_SINGLE_POSITION_CONCENTRATION")
        if largest_strat_exp > total_exp * 0.6:
            flags.append("HIGH_STRATEGY_CONCENTRATION")
        if top3_pct > 0.8:
            flags.append("TOP_3_DOMINATE_PORTFOLIO")
        
        return RiskConcentration(
            largest_position_symbol=largest_symbol,
            largest_position_exposure=largest_exposure,
            largest_position_pct=largest_exposure / total_exp if total_exp > 0 else 0,
            largest_strategy_id=largest_strategy,
            largest_strategy_exposure=largest_strat_exp,
            largest_strategy_pct=largest_strat_exp / total_exp if total_exp > 0 else 0,
            largest_exchange=largest_exchange,
            largest_exchange_exposure=largest_exch_exp,
            largest_exchange_pct=largest_exch_exp / total_exp if total_exp > 0 else 0,
            herfindahl_index=hhi,
            top_3_concentration=top3_pct,
            risk_flags=flags
        )
    
    # ===========================================
    # Capital Efficiency
    # ===========================================
    
    def get_capital_efficiency(self) -> CapitalEfficiency:
        """
        Calculate capital efficiency metrics.
        """
        
        state = self.get_capital_state()
        
        capital_used_pct = state.used_margin / state.total_equity if state.total_equity > 0 else 0
        
        return CapitalEfficiency(
            capital_used_pct=capital_used_pct,
            capital_idle_pct=1 - capital_used_pct,
            return_on_capital=state.total_pnl / state.total_equity if state.total_equity > 0 else 0,
            pnl_per_trade=random.uniform(15, 45),  # Mock
            pnl_per_dollar_risked=random.uniform(0.02, 0.08),  # Mock
            capital_turnover=random.uniform(2, 8),  # Mock
            avg_holding_period_hours=random.uniform(4, 48),  # Mock
            efficiency_score=random.uniform(0.6, 0.85)  # Mock
        )
    
    # ===========================================
    # Portfolio Metrics
    # ===========================================
    
    def get_portfolio_metrics(self) -> PortfolioMetrics:
        """
        Get portfolio-level metrics.
        """
        
        return PortfolioMetrics(
            total_return=random.uniform(0.05, 0.25),
            daily_return=random.uniform(-0.02, 0.03),
            weekly_return=random.uniform(-0.05, 0.08),
            monthly_return=random.uniform(0.02, 0.12),
            volatility=random.uniform(0.15, 0.35),
            max_drawdown=random.uniform(0.08, 0.20),
            current_drawdown=random.uniform(0, 0.08),
            sharpe_ratio=random.uniform(1.2, 2.5),
            sortino_ratio=random.uniform(1.5, 3.0),
            calmar_ratio=random.uniform(0.8, 2.0),
            win_rate=random.uniform(0.52, 0.68),
            profit_factor=random.uniform(1.3, 2.5),
            avg_win=random.uniform(50, 200),
            avg_loss=random.uniform(30, 100)
        )
    
    # ===========================================
    # Health
    # ===========================================
    
    def get_health(self) -> Dict[str, Any]:
        """Get service health"""
        return {
            "module": "OPS4 Capital Flow",
            "status": "healthy",
            "version": "1.0.0",
            "mongoAvailable": MONGO_AVAILABLE,
            "timestamp": int(time.time() * 1000)
        }
    
    # ===========================================
    # Mock Data Generators
    # ===========================================
    
    def _generate_mock_state(self) -> CapitalState:
        """Generate mock capital state"""
        
        total_equity = self._base_equity + random.uniform(-2000, 5000)
        used_margin = total_equity * random.uniform(0.2, 0.45)
        unrealized = random.uniform(-500, 1500)
        realized = random.uniform(100, 2500)
        
        return CapitalState(
            total_equity=round(total_equity, 2),
            used_margin=round(used_margin, 2),
            free_margin=round(total_equity - used_margin, 2),
            unrealized_pnl=round(unrealized, 2),
            realized_pnl=round(realized, 2),
            total_pnl=round(unrealized + realized, 2),
            exposure_usd=round(used_margin * random.uniform(2, 5), 2),
            exposure_pct=round(used_margin / total_equity, 4),
            open_positions=random.randint(3, 8),
            active_strategies=random.randint(2, 5)
        )
    
    def _generate_mock_allocations(self) -> List[StrategyAllocation]:
        """Generate mock strategy allocations"""
        
        strategies = [
            ("momentum_breakout", "Momentum Breakout"),
            ("trend_following", "Trend Following"),
            ("mean_reversion", "Mean Reversion"),
            ("channel_breakout", "Channel Breakout")
        ]
        
        total_capital = self._base_equity
        allocations = []
        
        remaining = total_capital
        for i, (sid, sname) in enumerate(strategies):
            if i == len(strategies) - 1:
                allocated = remaining
            else:
                allocated = total_capital * random.uniform(0.15, 0.35)
                remaining -= allocated
            
            used = allocated * random.uniform(0.3, 0.7)
            unrealized = random.uniform(-100, 300)
            realized = random.uniform(50, 500)
            
            allocations.append(StrategyAllocation(
                strategy_id=sid,
                strategy_name=sname,
                capital_allocated=round(allocated, 2),
                capital_used=round(used, 2),
                capital_available=round(allocated - used, 2),
                utilization_pct=round(used / allocated, 4),
                unrealized_pnl=round(unrealized, 2),
                realized_pnl=round(realized, 2),
                total_pnl=round(unrealized + realized, 2),
                pnl_pct=round((unrealized + realized) / allocated, 4),
                open_positions=random.randint(1, 4),
                total_trades=random.randint(20, 100),
                win_rate=round(random.uniform(0.52, 0.68), 4),
                allocation_pct=round(allocated / total_capital, 4)
            ))
        
        return allocations
    
    def _generate_mock_allocation(self, strategy_id: str) -> StrategyAllocation:
        """Generate mock allocation for single strategy"""
        
        allocated = self._base_equity * random.uniform(0.15, 0.35)
        used = allocated * random.uniform(0.3, 0.7)
        
        return StrategyAllocation(
            strategy_id=strategy_id,
            strategy_name=strategy_id.replace("_", " ").title(),
            capital_allocated=round(allocated, 2),
            capital_used=round(used, 2),
            capital_available=round(allocated - used, 2),
            utilization_pct=round(used / allocated, 4),
            unrealized_pnl=round(random.uniform(-100, 300), 2),
            realized_pnl=round(random.uniform(50, 500), 2),
            open_positions=random.randint(1, 4),
            total_trades=random.randint(20, 100),
            win_rate=round(random.uniform(0.52, 0.68), 4),
            allocation_pct=round(allocated / self._base_equity, 4)
        )
    
    def _generate_mock_symbol_exposures(self) -> List[ExposureView]:
        """Generate mock symbol exposures"""
        
        symbols = [
            ("BTCUSDT", 0.38),
            ("ETHUSDT", 0.24),
            ("SOLUSDT", 0.11),
            ("BNBUSDT", 0.08),
            ("XRPUSDT", 0.07),
            ("OTHERS", 0.12)
        ]
        
        total_exp = self._base_equity * random.uniform(0.5, 1.2)
        
        return [
            ExposureView(
                symbol=sym,
                exposure_usd=round(total_exp * pct, 2),
                exposure_pct=round(pct, 4),
                position_count=random.randint(1, 3),
                side=random.choice(["LONG", "SHORT", "MIXED"])
            )
            for sym, pct in symbols
        ]
    
    def _generate_mock_exchange_exposures(self) -> Dict[str, float]:
        """Generate mock exchange exposures"""
        
        total = self._base_equity * random.uniform(0.5, 1.0)
        
        return {
            "binance": round(total * 0.52, 2),
            "bybit": round(total * 0.31, 2),
            "hyperliquid": round(total * 0.17, 2)
        }
    
    def _generate_mock_timeline_events(
        self,
        period_hours: int
    ) -> List[CapitalFlowEvent]:
        """Generate mock timeline events"""
        
        events = []
        now = int(time.time() * 1000)
        period_ms = period_hours * 3600 * 1000
        
        num_events = min(period_hours // 4, 20)
        balance = self._base_equity
        
        event_types = [
            FlowEventType.POSITION_OPENED,
            FlowEventType.POSITION_CLOSED,
            FlowEventType.PNL_REALIZED,
            FlowEventType.POSITION_SCALED
        ]
        
        for i in range(num_events):
            ts = now - period_ms + (i * period_ms // num_events)
            evt_type = random.choice(event_types)
            
            if evt_type == FlowEventType.POSITION_OPENED:
                amount = -random.uniform(500, 2000)
            elif evt_type == FlowEventType.PNL_REALIZED:
                amount = random.uniform(-200, 500)
            elif evt_type == FlowEventType.POSITION_CLOSED:
                amount = random.uniform(500, 2000)
            else:
                amount = random.uniform(-300, 300)
            
            balance += amount
            
            events.append(CapitalFlowEvent(
                event_type=evt_type,
                timestamp=ts,
                amount=round(amount, 2),
                strategy_id=random.choice(["momentum_breakout", "trend_following", "mean_reversion"]),
                symbol=random.choice(["BTCUSDT", "ETHUSDT", "SOLUSDT"]),
                balance_after=round(balance, 2)
            ))
        
        return events


# Global singleton
capital_flow_service = CapitalFlowService()
