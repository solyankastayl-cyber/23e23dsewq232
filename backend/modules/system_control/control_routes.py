"""
System Control API Routes

PHASE 33 — System Control Layer API

Endpoints:
- GET  /api/v1/control/health              - Health check
- GET  /api/v1/control/state/{symbol}      - Get full cockpit state
- GET  /api/v1/control/decision/{symbol}   - Get decision state
- GET  /api/v1/control/risk/{symbol}       - Get risk state
- GET  /api/v1/control/alerts/{symbol}     - Get active alerts
- POST /api/v1/control/recompute/{symbol}  - Force recomputation
- GET  /api/v1/control/summary             - Get control summary
"""

from typing import List
from datetime import datetime, timezone
from fastapi import APIRouter, Query

from .decision_engine import get_decision_engine
from .risk_engine import get_risk_engine
from .alert_engine import get_alert_engine
from .cockpit_state import get_cockpit_aggregator

from .control_types import (
    MARKET_STATES,
    RISK_LEVELS,
    ALERT_TYPES,
)

from core.frozen_constants import (
    SYSTEM_VERSION,
    SYSTEM_VERSION_NUMBER,
    ASSET_UNIVERSE,
    INTELLIGENCE_LAYERS,
)


router = APIRouter(
    prefix="/api/v1/control",
    tags=["System Control Layer"],
)


# ══════════════════════════════════════════════════════════════
# Health Check
# ══════════════════════════════════════════════════════════════

@router.get("/health")
async def control_health() -> dict:
    """Health check for system control layer."""
    return {
        "status": "ok",
        "module": "system_control",
        "phase": "33",
        "system_version": SYSTEM_VERSION,
        "version": SYSTEM_VERSION_NUMBER,
        "intelligence_layers": len(INTELLIGENCE_LAYERS),
        "market_states": MARKET_STATES,
        "risk_levels": RISK_LEVELS,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


# ══════════════════════════════════════════════════════════════
# GET /api/v1/control/state/{symbol}
# ══════════════════════════════════════════════════════════════

@router.get("/state/{symbol}")
async def get_cockpit_state(
    symbol: str,
) -> dict:
    """
    Get full cockpit state for symbol.
    
    Returns decision, risk, and alerts aggregated.
    """
    aggregator = get_cockpit_aggregator()
    state = aggregator.get_cockpit_state(symbol)
    
    return {
        "status": "ok",
        "symbol": symbol.upper(),
        "decision": {
            "market_state": state.decision_state.market_state,
            "dominant_scenario": state.decision_state.dominant_scenario,
            "dominant_direction": state.decision_state.dominant_direction,
            "recommended_strategy": state.decision_state.recommended_strategy,
            "recommended_direction": state.decision_state.recommended_direction,
            "confidence": state.decision_state.confidence,
            "reasoning": state.decision_state.reasoning,
        },
        "risk": {
            "risk_level": state.risk_state.risk_level,
            "risk_score": state.risk_state.risk_score,
            "max_allowed_position": state.risk_state.max_allowed_position,
            "stress_indicator": state.risk_state.stress_indicator,
            "expected_volatility": state.risk_state.expected_volatility,
            "volatility_regime": state.risk_state.volatility_regime,
            "risk_factors": state.risk_state.risk_factors,
        },
        "alerts": {
            "active_count": state.active_alert_count,
            "alerts": [
                {
                    "alert_id": a.alert_id,
                    "type": a.alert_type,
                    "severity": a.severity,
                    "title": a.title,
                    "message": a.message,
                    "created_at": a.created_at.isoformat(),
                }
                for a in state.alerts[:10]
            ],
        },
        "intelligence": {
            "top_hypothesis": state.top_hypothesis,
            "top_scenario": state.top_scenario,
            "alpha_score": state.decision_state.alpha_score,
            "regime_score": state.decision_state.regime_score,
            "microstructure_score": state.decision_state.microstructure_score,
            "similarity_score": state.decision_state.similarity_score,
            "cross_asset_score": state.decision_state.cross_asset_score,
        },
        "allocation": state.capital_allocation,
        "system_status": state.system_status,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


# ══════════════════════════════════════════════════════════════
# GET /api/v1/control/decision/{symbol}
# ══════════════════════════════════════════════════════════════

@router.get("/decision/{symbol}")
async def get_decision(
    symbol: str,
) -> dict:
    """
    Get market decision state for symbol.
    """
    engine = get_decision_engine()
    decision = engine.get_current_decision(symbol)
    
    if decision is None:
        decision = engine.generate_decision(symbol)
    
    return {
        "status": "ok",
        "symbol": symbol.upper(),
        "market_state": decision.market_state,
        "dominant_scenario": decision.dominant_scenario,
        "recommended_strategy": decision.recommended_strategy,
        "recommended_direction": decision.recommended_direction,
        "confidence": decision.confidence,
        "risk_level": decision.risk_level,
        "hypothesis_type": decision.hypothesis_type,
        "top_scenario_type": decision.top_scenario_type,
        "top_scenario_probability": decision.top_scenario_probability,
        "scores": {
            "alpha": decision.alpha_score,
            "regime": decision.regime_score,
            "microstructure": decision.microstructure_score,
            "similarity": decision.similarity_score,
            "cross_asset": decision.cross_asset_score,
        },
        "reasoning": decision.reasoning,
        "timestamp": decision.timestamp.isoformat(),
    }


# ══════════════════════════════════════════════════════════════
# GET /api/v1/control/risk/{symbol}
# ══════════════════════════════════════════════════════════════

@router.get("/risk/{symbol}")
async def get_risk(
    symbol: str,
) -> dict:
    """
    Get risk state for symbol.
    """
    engine = get_risk_engine()
    risk = engine.get_current_risk(symbol)
    
    if risk is None:
        risk = engine.assess_risk(symbol)
    
    return {
        "status": "ok",
        "symbol": symbol.upper(),
        "risk_level": risk.risk_level,
        "risk_score": risk.risk_score,
        "exposure": {
            "long": risk.exposure_long,
            "short": risk.exposure_short,
            "net": risk.net_exposure,
        },
        "limits": {
            "max_allowed_position": risk.max_allowed_position,
            "current_utilization": risk.current_utilization,
        },
        "stress": {
            "stress_indicator": risk.stress_indicator,
            "liquidation_pressure": risk.liquidation_pressure,
            "cascade_probability": risk.cascade_probability,
        },
        "volatility": {
            "expected": risk.expected_volatility,
            "regime": risk.volatility_regime,
        },
        "risk_factors": risk.risk_factors,
        "timestamp": risk.timestamp.isoformat(),
    }


# ══════════════════════════════════════════════════════════════
# GET /api/v1/control/alerts/{symbol}
# ══════════════════════════════════════════════════════════════

@router.get("/alerts/{symbol}")
async def get_alerts(
    symbol: str,
    active_only: bool = Query(default=True),
    limit: int = Query(default=50, ge=1, le=200),
) -> dict:
    """
    Get alerts for symbol.
    """
    engine = get_alert_engine()
    
    if active_only:
        alerts = engine.get_active_alerts(symbol)
    else:
        alerts = engine.get_all_alerts(symbol, limit)
    
    # Count by severity
    critical_count = len([a for a in alerts if a.severity == "CRITICAL"])
    warning_count = len([a for a in alerts if a.severity == "WARNING"])
    info_count = len([a for a in alerts if a.severity == "INFO"])
    
    return {
        "status": "ok",
        "symbol": symbol.upper(),
        "total_alerts": len(alerts),
        "by_severity": {
            "critical": critical_count,
            "warning": warning_count,
            "info": info_count,
        },
        "alerts": [
            {
                "alert_id": a.alert_id,
                "type": a.alert_type,
                "severity": a.severity,
                "title": a.title,
                "message": a.message,
                "trigger_value": a.trigger_value,
                "threshold_value": a.threshold_value,
                "acknowledged": a.acknowledged,
                "created_at": a.created_at.isoformat(),
                "expires_at": a.expires_at.isoformat() if a.expires_at else None,
            }
            for a in alerts[:limit]
        ],
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


# ══════════════════════════════════════════════════════════════
# POST /api/v1/control/recompute/{symbol}
# ══════════════════════════════════════════════════════════════

@router.post("/recompute/{symbol}")
async def recompute_state(
    symbol: str,
) -> dict:
    """
    Force recomputation of all control states.
    """
    aggregator = get_cockpit_aggregator()
    state = aggregator.recompute_all(symbol)
    
    return {
        "status": "ok",
        "symbol": symbol.upper(),
        "decision": {
            "market_state": state.decision_state.market_state,
            "recommended_strategy": state.decision_state.recommended_strategy,
            "confidence": state.decision_state.confidence,
        },
        "risk": {
            "risk_level": state.risk_state.risk_level,
            "risk_score": state.risk_state.risk_score,
        },
        "alerts_generated": state.active_alert_count,
        "recomputed_at": datetime.now(timezone.utc).isoformat(),
    }


# ══════════════════════════════════════════════════════════════
# GET /api/v1/control/summary
# ══════════════════════════════════════════════════════════════

@router.get("/summary")
async def get_control_summary(
    symbols: str = Query(default="BTC,ETH,SOL", description="Comma-separated symbols"),
) -> dict:
    """
    Get control summary across multiple symbols.
    """
    symbol_list = [s.strip().upper() for s in symbols.split(",")]
    
    aggregator = get_cockpit_aggregator()
    summary = aggregator.get_control_summary(symbol_list)
    
    return {
        "status": "ok",
        "symbols_monitored": summary.symbols_monitored,
        "alerts": {
            "total": summary.total_alerts,
            "critical": summary.critical_alerts,
        },
        "risk_overview": {
            "high_risk": summary.high_risk_symbols,
            "extreme_risk": summary.extreme_risk_symbols,
        },
        "opportunities": summary.opportunity_symbols,
        "system_status": summary.system_status,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


# ══════════════════════════════════════════════════════════════
# POST /api/v1/control/alerts/{symbol}/acknowledge
# ══════════════════════════════════════════════════════════════

@router.post("/alerts/{symbol}/acknowledge")
async def acknowledge_alert(
    symbol: str,
    alert_id: str = Query(..., description="Alert ID to acknowledge"),
) -> dict:
    """
    Acknowledge an alert.
    """
    engine = get_alert_engine()
    success = engine.acknowledge_alert(symbol, alert_id)
    
    return {
        "status": "ok" if success else "not_found",
        "symbol": symbol.upper(),
        "alert_id": alert_id,
        "acknowledged": success,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
