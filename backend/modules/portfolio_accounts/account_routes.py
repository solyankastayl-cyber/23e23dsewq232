"""
Account Routes - PHASE 5.4
==========================

REST API endpoints for Portfolio Accounts Engine.

Endpoints:
- GET  /api/portfolio-accounts/health
- GET  /api/portfolio-accounts/state
- POST /api/portfolio-accounts/refresh
- GET  /api/portfolio-accounts/accounts
- GET  /api/portfolio-accounts/balances
- GET  /api/portfolio-accounts/positions
- GET  /api/portfolio-accounts/margin
- GET  /api/portfolio-accounts/exchange/{exchange}
- GET  /api/portfolio-accounts/exposure
- GET  /api/portfolio-accounts/history
"""

from typing import Dict, List, Any, Optional
from datetime import datetime
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from .account_types import RefreshAccountsRequest
from .portfolio_state_builder import get_portfolio_state_builder
from .account_aggregator import get_account_aggregator
from .balance_aggregator import get_balance_aggregator
from .position_aggregator import get_position_aggregator
from .margin_engine import get_margin_engine
from .account_repository import AccountRepository


router = APIRouter(prefix="/api/portfolio-accounts", tags=["Portfolio Accounts"])

# Initialize repository
repository = AccountRepository()


# ============================================
# Request Models
# ============================================

class RefreshRequest(BaseModel):
    """Request to refresh portfolio data"""
    exchanges: List[str] = Field(default_factory=lambda: ["BINANCE", "BYBIT", "OKX"])
    save_snapshot: bool = True


# ============================================
# Health & Status
# ============================================

@router.get("/health")
async def portfolio_health():
    """Health check"""
    builder = get_portfolio_state_builder()
    
    return {
        "status": "healthy",
        "version": "phase_5.4",
        "components": [
            "account_aggregator",
            "balance_aggregator",
            "position_aggregator",
            "margin_engine",
            "portfolio_state_builder"
        ],
        "component_status": builder.get_component_status(),
        "timestamp": datetime.utcnow().isoformat()
    }


@router.get("/status")
async def get_status():
    """Get portfolio engine status"""
    builder = get_portfolio_state_builder()
    
    return {
        "state_builder": builder.get_status(),
        "components": builder.get_component_status(),
        "timestamp": datetime.utcnow().isoformat()
    }


# ============================================
# Portfolio State
# ============================================

@router.get("/state")
async def get_portfolio_state():
    """Get unified portfolio state"""
    builder = get_portfolio_state_builder()
    
    # Build fresh state
    state = await builder.build_state()
    
    # Save to repository
    try:
        repository.save_state(builder.get_state_summary())
    except Exception as e:
        print(f"Error saving state: {e}")
    
    return {
        "state": builder.get_state_summary(),
        "timestamp": datetime.utcnow().isoformat()
    }


@router.post("/refresh")
async def refresh_portfolio(request: RefreshRequest):
    """Refresh portfolio data from exchanges"""
    builder = get_portfolio_state_builder()
    
    # Build state for specified exchanges
    state = await builder.build_state(request.exchanges)
    
    # Optionally save snapshot
    if request.save_snapshot:
        try:
            repository.save_state(builder.get_state_summary())
        except Exception:
            pass
    
    return {
        "refreshed": True,
        "exchanges": request.exchanges,
        "state": builder.get_state_summary(),
        "timestamp": datetime.utcnow().isoformat()
    }


# ============================================
# Accounts
# ============================================

@router.get("/accounts")
async def get_accounts(exchange: Optional[str] = Query(default=None)):
    """Get portfolio accounts"""
    aggregator = get_account_aggregator()
    
    # Refresh first
    await aggregator.refresh_accounts()
    
    if exchange:
        account = aggregator.get_account(exchange)
        if not account:
            raise HTTPException(status_code=404, detail=f"Account {exchange} not found")
        
        return {
            "account": account.dict(),
            "timestamp": datetime.utcnow().isoformat()
        }
    
    accounts = aggregator.get_all_accounts()
    
    return {
        "count": len(accounts),
        "accounts": [a.dict() for a in accounts],
        "summary": aggregator.get_aggregation_summary(),
        "timestamp": datetime.utcnow().isoformat()
    }


# ============================================
# Balances
# ============================================

@router.get("/balances")
async def get_balances(
    exchange: Optional[str] = Query(default=None),
    asset: Optional[str] = Query(default=None)
):
    """Get portfolio balances"""
    aggregator = get_balance_aggregator()
    
    # Refresh first
    await aggregator.refresh_balances()
    
    if exchange:
        balances = aggregator.get_balances_by_exchange(exchange)
        return {
            "exchange": exchange.upper(),
            "count": len(balances),
            "balances": [b.dict() for b in balances],
            "timestamp": datetime.utcnow().isoformat()
        }
    
    if asset:
        agg_balance = aggregator.get_asset_balance(asset)
        if not agg_balance:
            return {
                "asset": asset.upper(),
                "error": "Asset not found",
                "timestamp": datetime.utcnow().isoformat()
            }
        
        return {
            "asset": asset.upper(),
            "aggregated": agg_balance.dict(),
            "timestamp": datetime.utcnow().isoformat()
        }
    
    # All balances
    all_balances = aggregator.get_all_balances()
    aggregated = aggregator.get_aggregated_balances()
    
    return {
        "count": len(all_balances),
        "balances": [b.dict() for b in all_balances],
        "aggregated_by_asset": {
            asset: ab.dict() for asset, ab in aggregated.items()
        },
        "summary": aggregator.get_summary(),
        "timestamp": datetime.utcnow().isoformat()
    }


@router.get("/balances/distribution")
async def get_balance_distribution():
    """Get balance distribution"""
    aggregator = get_balance_aggregator()
    
    # Refresh first
    await aggregator.refresh_balances()
    
    return {
        "by_asset": aggregator.get_asset_distribution(),
        "by_exchange": aggregator.get_exchange_distribution(),
        "total_usd_value": aggregator.get_total_usd_value(),
        "timestamp": datetime.utcnow().isoformat()
    }


# ============================================
# Positions
# ============================================

@router.get("/positions")
async def get_positions(
    exchange: Optional[str] = Query(default=None),
    symbol: Optional[str] = Query(default=None)
):
    """Get portfolio positions"""
    aggregator = get_position_aggregator()
    
    # Refresh first
    await aggregator.refresh_positions()
    
    if exchange:
        positions = aggregator.get_positions_by_exchange(exchange)
        return {
            "exchange": exchange.upper(),
            "count": len(positions),
            "positions": [p.dict() for p in positions],
            "timestamp": datetime.utcnow().isoformat()
        }
    
    if symbol:
        positions = aggregator.get_positions_by_symbol(symbol)
        aggregated = aggregator.get_aggregated_positions().get(symbol.upper())
        
        return {
            "symbol": symbol.upper(),
            "count": len(positions),
            "positions": [p.dict() for p in positions],
            "aggregated": aggregated.dict() if aggregated else None,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    # All positions
    all_positions = aggregator.get_all_positions()
    aggregated = aggregator.get_aggregated_positions()
    
    return {
        "count": len(all_positions),
        "positions": [p.dict() for p in all_positions],
        "aggregated_by_symbol": {
            sym: ap.dict() for sym, ap in aggregated.items()
        },
        "summary": aggregator.get_summary(),
        "timestamp": datetime.utcnow().isoformat()
    }


@router.get("/positions/long-short")
async def get_long_short_split():
    """Get long/short position split"""
    aggregator = get_position_aggregator()
    
    # Refresh first
    await aggregator.refresh_positions()
    
    return {
        "split": aggregator.get_long_short_split(),
        "total_unrealized_pnl": aggregator.get_total_unrealized_pnl(),
        "total_notional": aggregator.get_total_notional(),
        "timestamp": datetime.utcnow().isoformat()
    }


# ============================================
# Margin
# ============================================

@router.get("/margin")
async def get_margin(exchange: Optional[str] = Query(default=None)):
    """Get margin information"""
    # First refresh accounts and positions
    account_agg = get_account_aggregator()
    position_agg = get_position_aggregator()
    margin_engine = get_margin_engine()
    
    await account_agg.refresh_accounts()
    await position_agg.refresh_positions()
    margin_engine.calculate_margin()
    
    if exchange:
        margin_info = margin_engine.get_margin_info(exchange)
        if not margin_info:
            raise HTTPException(status_code=404, detail=f"Margin info for {exchange} not found")
        
        return {
            "exchange": exchange.upper(),
            "margin": margin_info.dict(),
            "timestamp": datetime.utcnow().isoformat()
        }
    
    all_margin = margin_engine.get_all_margin_info()
    portfolio_margin = margin_engine.get_portfolio_margin()
    
    return {
        "portfolio": portfolio_margin,
        "by_exchange": {
            ex: info.dict() for ex, info in all_margin.items()
        },
        "stress_flags": margin_engine.get_stress_flags(),
        "headroom": margin_engine.get_margin_headroom(),
        "timestamp": datetime.utcnow().isoformat()
    }


# ============================================
# Exchange-specific
# ============================================

@router.get("/exchange/{exchange}")
async def get_exchange_details(exchange: str):
    """Get detailed info for specific exchange"""
    builder = get_portfolio_state_builder()
    
    # Build state
    await builder.build_state([exchange.upper()])
    
    breakdown = builder.get_exchange_breakdown()
    
    if exchange.upper() not in breakdown:
        raise HTTPException(status_code=404, detail=f"Exchange {exchange} not found")
    
    # Get detailed data
    account_agg = get_account_aggregator()
    balance_agg = get_balance_aggregator()
    position_agg = get_position_aggregator()
    margin_engine = get_margin_engine()
    
    account = account_agg.get_account(exchange)
    balances = balance_agg.get_balances_by_exchange(exchange)
    positions = position_agg.get_positions_by_exchange(exchange)
    margin = margin_engine.get_margin_info(exchange)
    
    return {
        "exchange": exchange.upper(),
        "summary": breakdown[exchange.upper()],
        "account": account.dict() if account else None,
        "balances": [b.dict() for b in balances],
        "positions": [p.dict() for p in positions],
        "margin": margin.dict() if margin else None,
        "timestamp": datetime.utcnow().isoformat()
    }


# ============================================
# Exposure
# ============================================

@router.get("/exposure")
async def get_exposure(symbol: Optional[str] = Query(default=None)):
    """Get position exposure"""
    aggregator = get_position_aggregator()
    
    # Refresh first
    await aggregator.refresh_positions()
    
    exposure = aggregator.get_exposure(symbol)
    
    if symbol and not exposure:
        return {
            "symbol": symbol.upper(),
            "error": "No exposure for symbol",
            "timestamp": datetime.utcnow().isoformat()
        }
    
    return {
        "exposure": {
            sym: exp.dict() for sym, exp in exposure.items()
        },
        "timestamp": datetime.utcnow().isoformat()
    }


# ============================================
# History
# ============================================

@router.get("/history")
async def get_history(
    limit: int = Query(default=100, ge=1, le=1000),
    days: int = Query(default=7, ge=1, le=30)
):
    """Get portfolio history"""
    builder = get_portfolio_state_builder()
    
    # Get in-memory history
    in_memory = builder.get_history(limit)
    
    # Get from repository
    db_history = repository.get_state_history(limit)
    
    return {
        "in_memory": {
            "count": len(in_memory),
            "entries": in_memory
        },
        "database": {
            "count": len(db_history),
            "entries": db_history
        },
        "timestamp": datetime.utcnow().isoformat()
    }


@router.get("/history/equity")
async def get_equity_history(
    days: int = Query(default=7, ge=1, le=30),
    limit: int = Query(default=100, ge=1, le=1000)
):
    """Get equity history"""
    builder = get_portfolio_state_builder()
    
    # In-memory equity series
    equity_series = builder.get_equity_series(limit)
    
    # From database
    db_equity = repository.get_equity_history(days, limit)
    
    return {
        "series": equity_series,
        "database": db_equity,
        "timestamp": datetime.utcnow().isoformat()
    }


@router.get("/history/pnl")
async def get_pnl_history(
    days: int = Query(default=7, ge=1, le=30),
    limit: int = Query(default=100, ge=1, le=1000)
):
    """Get PnL history"""
    builder = get_portfolio_state_builder()
    
    # In-memory PnL series
    pnl_series = builder.get_pnl_series(limit)
    
    # From database
    db_pnl = repository.get_pnl_history(days, limit)
    
    return {
        "series": pnl_series,
        "database": db_pnl,
        "timestamp": datetime.utcnow().isoformat()
    }


# ============================================
# Analytics
# ============================================

@router.get("/analytics")
async def get_analytics(days: int = Query(default=7, ge=1, le=30)):
    """Get portfolio analytics"""
    analytics = repository.get_analytics(days)
    
    return {
        "analytics": analytics,
        "timestamp": datetime.utcnow().isoformat()
    }
