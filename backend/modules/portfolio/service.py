"""
Portfolio Service

Aggregates system state from:
- balances (exchange)
- positions (exchange)
- trading cases (service)
- fills (execution history)

Sprint WS-3: Broadcasts portfolio.summary via WebSocket when state changes.
"""

import time
import logging
from typing import List, Optional

from .models import PortfolioSummary, EquityPoint, AssetAllocation

logger = logging.getLogger(__name__)


class PortfolioService:
    """
    Portfolio state aggregator
    
    Sprint WS-3: Broadcasts portfolio.summary snapshot when state changes.
    """
    
    def __init__(self, exchange_service, trading_case_service, db=None):
        """
        Initialize portfolio service.
        
        Args:
            exchange_service: ExchangeService instance
            trading_case_service: TradingCaseService instance
            db: MongoDB database instance (optional, for OrderManager compatibility)
        """
        self.exchange = exchange_service
        self.cases = trading_case_service
        self.db = db  # Add db reference for OrderManager
        self.equity_history: List[EquityPoint] = []
        
        # Initial capital (hardcoded for now, later from deposits)
        self.initial_capital = 10000.0
        
        logger.info("[PortfolioService] Initialized")
    
    async def get_summary(self) -> PortfolioSummary:
        """
        Get aggregated portfolio summary.
        
        Returns:
            PortfolioSummary: Current portfolio state
        """
        if not self.exchange.is_connected():
            logger.warning("[PortfolioService] Exchange not connected")
            return self._empty_summary()
        
        adapter = self.exchange.get_adapter()
        
        # Get exchange state
        balances = await adapter.get_balances()
        positions = await adapter.get_positions()
        
        # Get trading cases
        active_cases = self.cases.get_active_cases()
        closed_cases = self.cases.get_closed_cases()
        
        # Calculate cash
        cash = sum(b.free for b in balances if b.asset in ["USDT", "USDC"])
        
        # Calculate positions value
        positions_value = sum(p.qty * p.mark_price for p in positions)
        
        # Calculate unrealized PnL (from positions)
        unrealized_pnl = sum(p.unrealized_pnl for p in positions)
        
        # Calculate realized PnL (from closed cases)
        realized_pnl = sum(c.realized_pnl for c in closed_cases)
        
        # Total equity
        total_equity = cash + positions_value
        
        # Total PnL
        total_pnl = realized_pnl + unrealized_pnl
        
        # Total return %
        total_return_pct = (total_pnl / self.initial_capital) * 100 if self.initial_capital > 0 else 0.0
        
        # Deployment %
        deployment_pct = (positions_value / total_equity) * 100 if total_equity > 0 else 0.0
        
        # ATH (all-time high)
        ath = max([p.equity for p in self.equity_history], default=total_equity)
        if total_equity > ath:
            ath = total_equity
        
        # Drawdown %
        drawdown_pct = ((total_equity - ath) / ath) * 100 if ath > 0 else 0.0
        
        return PortfolioSummary(
            total_equity=total_equity,
            cash_balance=cash,
            positions_value=positions_value,
            unrealized_pnl=unrealized_pnl,
            realized_pnl=realized_pnl,
            total_pnl=total_pnl,
            total_return_pct=total_return_pct,
            deployment_pct=deployment_pct,
            active_positions=len(positions),
            ath=ath,
            drawdown_pct=drawdown_pct,
        )
    
    async def snapshot_equity(self):
        """
        Take equity snapshot and append to history.
        
        This is the ONLY source of truth for equity curve.
        NO fake data, NO random, NO smoothing.
        """
        summary = await self.get_summary()
        
        point = EquityPoint(
            timestamp=int(time.time()),
            equity=summary.total_equity
        )
        
        self.equity_history.append(point)
        
        # Limit to 500 points (prevent unbounded growth)
        if len(self.equity_history) > 500:
            self.equity_history.pop(0)
        
        logger.debug(f"[PortfolioService] Snapshot: equity=${summary.total_equity:.2f}")
    
    def get_equity_curve(self) -> List[EquityPoint]:
        """
        Get equity curve history.
        
        Returns:
            List[EquityPoint]: Historical equity snapshots
        """
        return self.equity_history
    
    async def get_multi_equity_curve(self) -> List[dict]:
        """
        Get multi-asset equity breakdown (Total, BTC, ETH).
        
        Returns:
            List[dict]: Array of { timestamp, total, btc, eth }
        """
        if not self.exchange.is_connected():
            return []
        
        adapter = self.exchange.get_adapter()
        
        result = []
        
        for point in self.equity_history:
            timestamp = point.timestamp
            total_equity = point.equity
            
            # Get balances and positions at this timestamp
            # (approximation: we use current positions, since we don't store historical)
            balances = await adapter.get_balances()
            positions = await adapter.get_positions()
            
            btc_value = 0.0
            eth_value = 0.0
            
            # Calculate BTC equity
            btc_pos = next((p for p in positions if p.symbol == "BTCUSDT"), None)
            if btc_pos:
                btc_value = btc_pos.qty * btc_pos.mark_price
            
            # Calculate ETH equity
            eth_pos = next((p for p in positions if p.symbol == "ETHUSDT"), None)
            if eth_pos:
                eth_value = eth_pos.qty * eth_pos.mark_price
            
            result.append({
                "timestamp": timestamp,
                "total": round(total_equity, 2),
                "btc": round(btc_value, 2),
                "eth": round(eth_value, 2)
            })
        
        return result
    
    async def get_allocations(self) -> List[AssetAllocation]:
        """
        Get asset allocation breakdown.
        
        Returns:
            List[AssetAllocation]: Asset allocations
        """
        if not self.exchange.is_connected():
            return []
        
        adapter = self.exchange.get_adapter()
        positions = await adapter.get_positions()
        
        summary = await self.get_summary()
        total_equity = summary.total_equity
        
        allocations = []
        
        # Cash allocation
        if summary.cash_balance > 0:
            allocations.append(AssetAllocation(
                asset="CASH",
                value=summary.cash_balance,
                pct=(summary.cash_balance / total_equity) * 100 if total_equity > 0 else 0.0
            ))
        
        # Position allocations
        for pos in positions:
            position_value = pos.qty * pos.mark_price
            allocations.append(AssetAllocation(
                asset=pos.symbol.replace("USDT", ""),
                value=position_value,
                pct=(position_value / total_equity) * 100 if total_equity > 0 else 0.0
            ))
        
        return allocations
    
    def _empty_summary(self) -> PortfolioSummary:
        """Return empty portfolio summary when exchange is disconnected."""
        return PortfolioSummary(
            total_equity=0.0,
            cash_balance=0.0,
            positions_value=0.0,
            unrealized_pnl=0.0,
            realized_pnl=0.0,
            total_pnl=0.0,
            total_return_pct=0.0,
            deployment_pct=0.0,
            active_positions=0,
            ath=0.0,
            drawdown_pct=0.0,
        )
    
    async def get_assets(self) -> List[dict]:
        """
        Get asset breakdown (balances + positions).
        
        Returns:
            List[dict]: Asset breakdown with PnL
        """
        if not self.exchange.is_connected():
            return []
        
        adapter = self.exchange.get_adapter()
        balances = await adapter.get_balances()
        positions = await adapter.get_positions()
        
        assets = []
        
        # Add balances (CASH primarily)
        for balance in balances:
            if balance.asset in ["USDT", "USDC"] and balance.total > 0:
                assets.append({
                    "asset": balance.asset,
                    "total": balance.total,
                    "value": balance.total,
                    "avg_entry": None,
                    "current_price": 1.0,
                    "pnl": 0.0,
                    "pnl_pct": 0.0,
                    "allocation_pct": 0.0
                })
        
        # Add positions
        for pos in positions:
            asset = pos.symbol.replace("USDT", "")
            value = pos.qty * pos.mark_price
            
            assets.append({
                "asset": asset,
                "total": pos.qty,
                "value": value,
                "avg_entry": pos.entry_price,
                "current_price": pos.mark_price,
                "pnl": pos.unrealized_pnl,
                "pnl_pct": pos.unrealized_pnl_pct,
                "allocation_pct": 0.0
            })
        
        # Calculate allocation %
        summary = await self.get_summary()
        total_equity = summary.total_equity
        
        for asset in assets:
            if total_equity > 0:
                asset["allocation_pct"] = (asset["value"] / total_equity) * 100
        
        return assets
    
    async def get_active_positions(self) -> List[dict]:
        """
        Get active positions with context from trading cases.
        
        Returns:
            List[dict]: Active positions with strategy/duration
        """
        if not self.exchange.is_connected():
            return []
        
        adapter = self.exchange.get_adapter()
        positions = await adapter.get_positions()
        cases = self.cases.get_active_cases()
        
        result = []
        
        for pos in positions:
            # Find matching case
            case = next((c for c in cases if c.symbol == pos.symbol and c.side == pos.side), None)
            
            # Calculate duration
            duration = None
            if case and case.opened_at:
                from datetime import datetime, timezone
                delta = datetime.now(timezone.utc) - case.opened_at
                days = delta.days
                hours = delta.seconds // 3600
                duration = f"{days}d {hours}h" if days > 0 else f"{hours}h"
            
            result.append({
                "symbol": pos.symbol,
                "side": pos.side,
                "qty": pos.qty,
                "entry_price": pos.entry_price,
                "mark_price": pos.mark_price,
                "pnl": pos.unrealized_pnl,
                "pnl_pct": pos.unrealized_pnl_pct,
                "strategy": case.strategy if case else None,
                "duration": duration
            })
        
        return result
    
    async def get_closed_positions(self) -> List[dict]:
        """
        Get closed positions from trading cases.
        
        Returns:
            List[dict]: Closed positions with PnL
        """
        closed_cases = self.cases.get_closed_cases()
        
        result = []
        
        for case in closed_cases:
            # Calculate duration
            duration = None
            if case.opened_at and case.closed_at:
                delta = case.closed_at - case.opened_at
                days = delta.days
                hours = delta.seconds // 3600
                duration = f"{days}d {hours}h" if days > 0 else f"{hours}h"
            
            # Calculate exit price and PnL %
            exit_price = case.current_price
            pnl_pct = 0.0
            
            if case.size_usd > 0:
                pnl_pct = (case.realized_pnl / case.size_usd) * 100
            
            result.append({
                "symbol": case.symbol,
                "side": case.side,
                "entry": case.entry_price,
                "exit": exit_price,
                "pnl": case.realized_pnl,
                "pnl_pct": pnl_pct,
                "duration": duration,
                "exit_reason": "MANUAL CLOSE"  # TODO: add exit_reason to TradingCase model
            })
        
        return result


    async def get_intelligence(self) -> dict:
        """
        Get system intelligence metrics.
        
        Returns:
            dict: Intelligence metrics (exposure, contributions, best/worst, mode)
        """
        if not self.exchange.is_connected():
            return {
                "deployment_pct": 0.0,
                "total_pnl": 0.0,
                "contributions": [],
                "best": None,
                "worst": None,
                "system_mode": {
                    "regime": "OFFLINE",
                    "bias": "NEUTRAL",
                    "confidence": "N/A"
                }
            }
        
        adapter = self.exchange.get_adapter()
        positions = await adapter.get_positions()
        summary = await self.get_summary()
        
        # Total PnL
        total_pnl = sum(p.unrealized_pnl for p in positions)
        
        # PnL Contributions
        contributions = []
        for pos in positions:
            if total_pnl != 0:
                contribution_pct = (pos.unrealized_pnl / total_pnl) * 100
            else:
                contribution_pct = 0.0
            
            contributions.append({
                "symbol": pos.symbol.replace("USDT", ""),
                "pnl": pos.unrealized_pnl,
                "contribution_pct": round(contribution_pct, 2)
            })
        
        # Sort by PnL (best first)
        contributions = sorted(contributions, key=lambda x: x["pnl"], reverse=True)
        
        # Best / Worst
        best = contributions[0] if contributions else None
        worst = contributions[-1] if contributions else None
        
        # System Mode (derived from deployment)
        deployment_pct = summary.deployment_pct
        
        if deployment_pct < 20:
            regime = "DEFENSIVE"
            bias = "CASH"
            confidence = "LOW CONVICTION"
        elif deployment_pct < 60:
            regime = "SELECTIVE"
            bias = "BALANCED"
            confidence = "MEDIUM CONVICTION"
        else:
            regime = "AGGRESSIVE"
            bias = "LONG"
            confidence = "HIGH CONVICTION"
        
        return {
            "deployment_pct": round(deployment_pct, 2),
            "total_pnl": round(total_pnl, 2),
            "contributions": contributions,
            "best": best,
            "worst": worst,
            "system_mode": {
                "regime": regime,
                "bias": bias,
                "confidence": confidence
            }
        }
    
    async def get_decision(self) -> dict:
        """
        Get decision layer (regime, drivers, risk).
        
        Returns:
            dict: Decision intelligence
        """
        intelligence = await self.get_intelligence()
        mode = intelligence["system_mode"]
        
        drivers = []
        for contrib in intelligence["contributions"]:
            is_leader = intelligence["best"] and intelligence["best"]["symbol"] == contrib["symbol"]
            drivers.append({
                "type": "position",
                "symbol": contrib["symbol"],
                "impact": round(contrib["contribution_pct"] / 100, 4),
                "pnl": contrib["pnl"],
                "reason": "PnL leader" if is_leader else "Supporting contribution"
            })
        
        summary = await self.get_summary()
        
        return {
            "regime": mode["regime"],
            "bias": mode["bias"],
            "confidence": mode["confidence"],
            "drivers": drivers,
            "risk": {
                "exposure": round(intelligence["deployment_pct"] / 100, 4),
                "drawdown": round(abs(summary.drawdown_pct) / 100, 4),
                "concentration": round(max([d["impact"] for d in drivers], default=0), 4)
            }
        }
    
    async def get_timeline_events(self) -> List[dict]:
        """
        Get timeline events (entries, exits, regime changes).
        
        Returns:
            List[dict]: Timeline events
        """
        events = []
        
        # Get all cases (active + closed)
        active_cases = self.cases.get_active_cases()
        closed_cases = self.cases.get_closed_cases()
        all_cases = active_cases + closed_cases
        
        for case in all_cases:
            # Entry event
            if case.opened_at:
                events.append({
                    "id": f"{case.case_id}-entry",
                    "timestamp": int(case.opened_at.timestamp()),
                    "event": "ENTRY",
                    "symbol": case.symbol.replace("USDT", ""),
                    "price": case.entry_price
                })
            
            # Exit event (for closed cases)
            if case.closed_at:
                events.append({
                    "id": f"{case.case_id}-exit",
                    "timestamp": int(case.closed_at.timestamp()),
                    "event": "EXIT",
                    "symbol": case.symbol.replace("USDT", ""),
                    "price": case.current_price
                })
        
        # Sort by timestamp and return last 20
        events.sort(key=lambda x: x["timestamp"])
        return events[-20:]
    
    async def get_narrative(self) -> dict:
        """
        Get portfolio narrative (summary, signals, action).
        
        Returns:
            dict: Narrative intelligence
        """
        summary = await self.get_summary()
        intelligence = await self.get_intelligence()
        
        top_contributor = intelligence["best"]["symbol"] if intelligence["best"] else "No leader"
        
        # Build summary text
        summary_text = (
            f"Portfolio is in {intelligence['system_mode']['regime'].lower()} mode with "
            f"{summary.deployment_pct:.1f}% deployed capital. "
            f"{top_contributor} is currently the main PnL driver."
        )
        
        # Build signals
        signals = [
            f"Top contributor: {top_contributor}",
            f"Exposure at {summary.deployment_pct:.1f}%",
            f"Total PnL {summary.total_pnl:+.2f}"
        ]
        
        # Determine action
        if summary.deployment_pct < 70:
            action = "Hold and monitor leaders"
        else:
            action = "Monitor concentration risk"
        
        return {
            "summary": summary_text,
            "signals": signals,
            "action": action
        }
    
    async def get_asset_performance(self, symbol: str) -> List[dict]:
        """
        Get asset performance over time (sparkline data).
        
        Args:
            symbol: Asset symbol (e.g., "BTC", "ETH")
        
        Returns:
            List[dict]: Performance points
        """
        target = symbol.replace("USDT", "")
        
        if not self.exchange.is_connected():
            return []
        
        adapter = self.exchange.get_adapter()
        positions = await adapter.get_positions()
        
        # Find position for symbol
        position = next((p for p in positions if p.symbol == f"{target}USDT"), None)
        
        if not position:
            return []
        
        # Build performance from equity history
        # (Simple approximation: we track value of this position over time)
        points = []
        
        for point in self.equity_history:
            # Approximate: current position value at that time
            # (In real system, you'd store historical position values)
            points.append({
                "time": point.timestamp,
                "value": round(position.qty * position.mark_price, 2)
            })
        
        return points[-40:]  # Last 40 points for sparkline
    
    async def broadcast_summary_if_changed(self):
        """
        Sprint WS-3: Broadcast portfolio.summary snapshot if state changed.
        
        This method:
        1. Gets current portfolio summary (state fixation)
        2. Broadcasts via WebSocket (with hash debounce)
        
        Called after position sync or other portfolio state changes.
        """
        try:
            from modules.ws_hub.service_locator import get_ws_broadcaster
            
            broadcaster = get_ws_broadcaster()
            
            # State fixation: get current portfolio summary
            summary = await self.get_summary()
            
            # Convert Pydantic model to dict
            summary_dict = summary.dict() if hasattr(summary, 'dict') else summary.__dict__
            
            # Broadcast (debouncer will skip if hash unchanged)
            await broadcaster.broadcast_snapshot("portfolio.summary", summary_dict)
            logger.debug("[WS-3] portfolio.summary broadcast attempted (debouncer active)")
        
        except Exception as e:
            # Non-critical: don't break portfolio logic if WS fails
            logger.debug(f"[WS-3] portfolio.summary broadcast failed (non-critical): {e}")


# Singleton instance
_portfolio_service: Optional[PortfolioService] = None


def init_portfolio_service(exchange_service, trading_case_service, db=None):
    """Initialize portfolio service singleton."""
    global _portfolio_service
    _portfolio_service = PortfolioService(exchange_service, trading_case_service, db)
    logger.info("[PortfolioService] Initialized")


def get_portfolio_service() -> PortfolioService:
    """Get portfolio service singleton."""
    if _portfolio_service is None:
        raise RuntimeError("PortfolioService not initialized. Call init_portfolio_service() first.")
    return _portfolio_service
