"""
Failover Engine API Routes
==========================

REST API для Failover Engine.

Endpoints:
- GET /api/failover/status - текущий статус системы
- GET /api/failover/exchange/{exchange} - статус биржи
- GET /api/failover/latency - статистика латентности
- GET /api/failover/rate-limit - статусы rate limits
- GET /api/failover/events - события failover
- GET /api/failover/history - история по запросу
"""

from typing import Dict, List, Any, Optional
from datetime import datetime
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from .failover_types import (
    SystemStatus,
    FailoverEventType,
    FailoverHistoryQuery
)
from .failover_engine import FailoverEngine
from .failover_repository import FailoverRepository


router = APIRouter(prefix="/api/failover", tags=["Failover Engine"])

# Initialize
engine = FailoverEngine()
repository = FailoverRepository()


# ============================================
# Request/Response Models
# ============================================

class RecordRequestModel(BaseModel):
    """Модель записи запроса"""
    exchange: str = "BINANCE"
    latency_ms: float = 100.0
    success: bool = True
    error: Optional[str] = None


class EmergencyTriggerModel(BaseModel):
    """Модель триггера emergency"""
    reason: str = "Manual trigger"


# ============================================
# API Endpoints
# ============================================

@router.get("/health")
async def failover_health():
    """Health check"""
    return {
        "status": "healthy",
        "version": "phase_4.4",
        "components": [
            "exchange_health_monitor",
            "latency_monitor",
            "rate_limit_monitor",
            "connection_guard",
            "failover_engine"
        ],
        "timestamp": datetime.utcnow().isoformat()
    }


@router.get("/status")
async def get_status():
    """Получить текущий статус системы"""
    state = engine.evaluate()
    
    return {
        "system_status": state.system_status.value,
        "primary_exchange": state.primary_exchange,
        "fallback_exchange": state.fallback_exchange,
        "active_actions": [a.value for a in state.active_actions],
        "throttle_factor": state.throttle_factor,
        "position_size_factor": state.position_size_factor,
        "new_positions_allowed": state.new_positions_allowed,
        "execution_paused": state.execution_paused,
        "recent_errors": state.recent_errors,
        "active_failover_exchanges": state.active_failover_exchanges,
        "last_status_change": state.last_status_change.isoformat() if state.last_status_change else None,
        "failover_started_at": state.failover_started_at.isoformat() if state.failover_started_at else None,
        "exchanges": {
            ex: {
                "status": h.status.value,
                "health_score": h.health_score,
                "latency_ms": h.avg_latency_ms,
                "error_rate": h.error_rate,
                "latency_grade": h.latency_grade.value
            }
            for ex, h in state.exchanges.items()
        },
        "updated_at": state.updated_at.isoformat()
    }


@router.get("/exchange/{exchange}")
async def get_exchange_status(exchange: str):
    """Получить статус конкретной биржи"""
    exchange = exchange.upper()
    
    status = engine.get_exchange_status(exchange)
    
    return {
        "exchange": exchange,
        "health": status["health"],
        "latency": status["latency"],
        "rate_limit": status["rate_limit"],
        "connection": status["connection"],
        "recommended_action": status["recommended_action"],
        "timestamp": datetime.utcnow().isoformat()
    }


@router.get("/latency")
async def get_latency_stats(exchange: Optional[str] = Query(default=None)):
    """Получить статистику латентности"""
    if exchange:
        stats = engine.latency_monitor.get_stats(exchange.upper())
        trend = engine.latency_monitor.get_trend(exchange.upper())
        return {
            "exchange": exchange.upper(),
            "stats": stats,
            "trend": trend
        }
    else:
        all_stats = engine.latency_monitor.get_all_stats()
        return {
            "exchanges": all_stats,
            "timestamp": datetime.utcnow().isoformat()
        }


@router.get("/rate-limit")
async def get_rate_limit_status(exchange: Optional[str] = Query(default=None)):
    """Получить статус rate limits"""
    if exchange:
        exchange = exchange.upper()
        all_status = engine.rate_limit_monitor.get_all_status(exchange)
        recommendation = engine.rate_limit_monitor.get_recommended_action(exchange)
        
        return {
            "exchange": exchange,
            "limits": {
                lt: {
                    "limit": s.limit_value,
                    "used": s.used_value,
                    "remaining": s.remaining,
                    "utilization_pct": s.utilization_pct,
                    "is_approaching": s.is_approaching_limit,
                    "is_exceeded": s.is_exceeded
                }
                for lt, s in all_status.items()
            },
            "recommendation": recommendation,
            "timestamp": datetime.utcnow().isoformat()
        }
    else:
        comparison = engine.rate_limit_monitor.get_comparison()
        return {
            "exchanges": comparison,
            "timestamp": datetime.utcnow().isoformat()
        }


@router.get("/connection")
async def get_connection_status(exchange: Optional[str] = Query(default=None)):
    """Получить статус соединений"""
    if exchange:
        health = engine.connection_guard.check_health(exchange.upper())
        action = engine.connection_guard.get_recommended_action(exchange.upper())
        
        return {
            "exchange": exchange.upper(),
            "health": health,
            "recommended_action": action.value,
            "timestamp": datetime.utcnow().isoformat()
        }
    else:
        all_status = engine.connection_guard.get_all_status()
        return {
            "connections": {
                ex: {
                    ct: {
                        "state": s.state.value,
                        "last_heartbeat": s.last_heartbeat.isoformat() if s.last_heartbeat else None,
                        "latency_ms": s.latency_ms,
                        "reconnect_attempts": s.reconnect_attempts
                    }
                    for ct, s in conns.items()
                }
                for ex, conns in all_status.items()
            },
            "timestamp": datetime.utcnow().isoformat()
        }


@router.get("/events")
async def get_events(
    limit: int = Query(default=50, ge=1, le=500),
    severity: Optional[str] = Query(default=None)
):
    """Получить недавние события"""
    events = engine.get_events(limit)
    
    if severity:
        events = [e for e in events if e.get("severity") == severity.upper()]
    
    return {
        "count": len(events),
        "events": events,
        "timestamp": datetime.utcnow().isoformat()
    }


@router.get("/history")
async def get_history(
    exchange: Optional[str] = Query(default=None),
    event_type: Optional[str] = Query(default=None),
    severity: Optional[str] = Query(default=None),
    limit: int = Query(default=100, ge=1, le=1000)
):
    """Получить историю событий из базы"""
    query = FailoverHistoryQuery(
        exchange=exchange.upper() if exchange else None,
        severity=severity.upper() if severity else None,
        limit=limit
    )
    
    if event_type:
        try:
            query.event_type = FailoverEventType(event_type)
        except ValueError:
            pass
    
    events = repository.get_events(query)
    
    return {
        "filters": {
            "exchange": exchange,
            "event_type": event_type,
            "severity": severity
        },
        "count": len(events),
        "events": events
    }


@router.get("/stats")
async def get_stats(days: int = Query(default=7, ge=1, le=30)):
    """Получить статистику failover"""
    stats = repository.get_stats(days)
    
    return {
        "period_days": days,
        "stats": stats,
        "timestamp": datetime.utcnow().isoformat()
    }


@router.get("/exchange-comparison")
async def compare_exchanges(days: int = Query(default=7, ge=1, le=30)):
    """Сравнить биржи"""
    comparison = repository.get_exchange_comparison(days)
    
    # Also get current health
    current_health = engine.health_monitor.get_all_health()
    
    return {
        "period_days": days,
        "historical": comparison,
        "current": {
            ex: {
                "status": h.status.value,
                "health_score": h.health_score,
                "latency_ms": h.avg_latency_ms,
                "error_rate": h.error_rate
            }
            for ex, h in current_health.items()
        },
        "timestamp": datetime.utcnow().isoformat()
    }


@router.post("/record")
async def record_request(request: RecordRequestModel):
    """Записать результат запроса"""
    result = engine.record_request(
        exchange=request.exchange.upper(),
        latency_ms=request.latency_ms,
        success=request.success,
        error=request.error
    )
    
    return {
        "recorded": True,
        "exchange": request.exchange.upper(),
        "analysis": result
    }


@router.post("/emergency")
async def trigger_emergency(request: EmergencyTriggerModel):
    """Принудительно активировать EMERGENCY режим"""
    state = engine.trigger_emergency(request.reason)
    
    return {
        "triggered": True,
        "system_status": state.system_status.value,
        "active_actions": [a.value for a in state.active_actions],
        "message": f"Emergency triggered: {request.reason}",
        "timestamp": datetime.utcnow().isoformat()
    }


@router.post("/reset")
async def reset_system():
    """Сбросить систему в NORMAL режим"""
    state = engine.reset()
    
    return {
        "reset": True,
        "system_status": state.system_status.value,
        "message": "System reset to NORMAL",
        "timestamp": datetime.utcnow().isoformat()
    }


@router.get("/config")
async def get_config():
    """Получить конфигурацию failover"""
    config = engine.config
    
    return {
        "latency_thresholds": {
            "normal_ms": config.latency_normal_ms,
            "degraded_ms": config.latency_degraded_ms,
            "critical_ms": config.latency_critical_ms
        },
        "error_rate_thresholds": {
            "warning": config.error_rate_warning,
            "critical": config.error_rate_critical
        },
        "rate_limit_thresholds": {
            "warning_pct": config.rate_limit_warning_pct,
            "critical_pct": config.rate_limit_critical_pct
        },
        "timeouts": {
            "api_timeout_ms": config.api_timeout_ms,
            "websocket_heartbeat_timeout_ms": config.websocket_heartbeat_timeout_ms
        },
        "recovery": {
            "auto_recovery_enabled": config.auto_recovery_enabled,
            "recovery_check_interval_seconds": config.recovery_check_interval_seconds,
            "min_recovery_health_score": config.min_recovery_health_score
        }
    }


# ============================================
# Batch Operations
# ============================================

class BatchRecordRequest(BaseModel):
    """Batch записей"""
    requests: List[RecordRequestModel] = Field(default_factory=list)


@router.post("/batch-record")
async def batch_record(request: BatchRecordRequest):
    """Batch запись запросов"""
    results = []
    
    for req in request.requests[:100]:  # Limit 100
        result = engine.record_request(
            exchange=req.exchange.upper(),
            latency_ms=req.latency_ms,
            success=req.success,
            error=req.error
        )
        results.append({
            "exchange": req.exchange.upper(),
            "latency_ms": req.latency_ms,
            "grade": result.get("grade")
        })
    
    return {
        "recorded": len(results),
        "results": results,
        "timestamp": datetime.utcnow().isoformat()
    }
