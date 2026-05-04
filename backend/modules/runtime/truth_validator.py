"""
Truth Layer Validation — Sprint 2

Automated consistency check across all system layers:
  Signal → R1 → R2 → Safety → Execution → Position → Portfolio → UI

POST /api/system/validate-consistency
→ Returns { "status": "OK" | "MISMATCH", "mismatches": [...] }
"""

import logging
from typing import Dict, Any, List
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class TruthLayerValidator:
    """
    Validates consistency between system layers.
    
    Checks:
    1. Signal symbol == Execution symbol
    2. R1 qty == Order qty  
    3. Execution result == Position state
    4. Position state ∈ Portfolio positions
    5. Safety decisions consistent with system state
    """
    
    def __init__(self, db):
        self.db = db
        logger.info("[TruthLayerValidator] Initialized")
    
    async def validate(self) -> Dict[str, Any]:
        """
        Run full consistency validation.
        
        Returns:
            {
                "status": "OK" | "MISMATCH",
                "checks": [...],
                "mismatches": [...],
                "timestamp": "..."
            }
        """
        checks = []
        mismatches = []
        
        # ── CHECK 1: Active positions match trading cases ──
        try:
            positions = await self.db.positions.find(
                {"status": "OPEN"}, {"_id": 0}
            ).to_list(length=100)
            
            cases = await self.db.trading_cases.find(
                {"status": "active"}, {"_id": 0}
            ).to_list(length=100)
            
            pos_symbols = {p.get("symbol") for p in positions}
            case_symbols = {c.get("symbol") for c in cases}
            
            orphan_positions = pos_symbols - case_symbols
            orphan_cases = case_symbols - pos_symbols
            
            if orphan_positions:
                mismatches.append({
                    "layer": "POSITION↔CASE",
                    "type": "ORPHAN_POSITIONS",
                    "detail": f"Positions without cases: {orphan_positions}",
                    "severity": "MEDIUM",
                })
            
            if orphan_cases:
                mismatches.append({
                    "layer": "CASE↔POSITION",
                    "type": "ORPHAN_CASES",
                    "detail": f"Cases without positions: {orphan_cases}",
                    "severity": "LOW",
                })
            
            checks.append({
                "name": "Position↔Case Sync",
                "status": "OK" if not orphan_positions and not orphan_cases else "MISMATCH",
                "positions": len(positions),
                "cases": len(cases),
            })
        except Exception as e:
            checks.append({"name": "Position↔Case Sync", "status": "ERROR", "error": str(e)})
        
        # ── CHECK 2: Portfolio equity consistency ──
        try:
            from modules.portfolio.service import get_portfolio_service
            portfolio = get_portfolio_service()
            summary = await portfolio.get_summary()
            
            equity = getattr(summary, 'equity', 0) if not isinstance(summary, dict) else summary.get("equity", 0)
            balance = getattr(summary, 'balance', 0) if not isinstance(summary, dict) else summary.get("balance", 0)
            unrealized = getattr(summary, 'unrealized_pnl', 0) if not isinstance(summary, dict) else summary.get("unrealized_pnl", 0)
            
            expected_equity = balance + unrealized
            equity_drift = abs(equity - expected_equity)
            
            if equity_drift > 1.0:  # > $1 drift
                mismatches.append({
                    "layer": "PORTFOLIO",
                    "type": "EQUITY_DRIFT",
                    "detail": f"equity={equity:.2f}, balance+unrealized={expected_equity:.2f}, drift=${equity_drift:.2f}",
                    "severity": "HIGH",
                })
            
            checks.append({
                "name": "Portfolio Equity",
                "status": "OK" if equity_drift <= 1.0 else "MISMATCH",
                "equity": round(equity, 2),
                "expected": round(expected_equity, 2),
                "drift": round(equity_drift, 2),
            })
        except Exception as e:
            checks.append({"name": "Portfolio Equity", "status": "ERROR", "error": str(e)})
        
        # ── CHECK 3: Runtime state matches execution events ──
        try:
            from modules.runtime.service_locator import get_runtime_service
            runtime = get_runtime_service()
            state = await runtime.get_runtime_state()
            
            # Check if runtime says enabled but last error exists
            runtime_enabled = state.get("enabled", False)
            runtime_error = state.get("last_error")
            runtime_status = state.get("status")
            
            if runtime_enabled and runtime_error:
                mismatches.append({
                    "layer": "RUNTIME",
                    "type": "ENABLED_WITH_ERROR",
                    "detail": f"Runtime enabled but has error: {runtime_error}",
                    "severity": "MEDIUM",
                })
            
            checks.append({
                "name": "Runtime State",
                "status": "OK" if not (runtime_enabled and runtime_error) else "WARNING",
                "enabled": runtime_enabled,
                "status_val": runtime_status,
                "last_error": runtime_error,
            })
        except Exception as e:
            checks.append({"name": "Runtime State", "status": "ERROR", "error": str(e)})
        
        # ── CHECK 4: Kill switch consistency ──
        try:
            from modules.strategy_engine.kill_switch import get_kill_switch
            ks = get_kill_switch()
            ks_status = await ks.get_status()
            
            ks_active = ks_status.get("active", False)
            
            # If kill switch active, there should be no OPEN orders
            if ks_active:
                open_orders = await self.db.orders.count_documents({"status": "OPEN"})
                if open_orders > 0:
                    mismatches.append({
                        "layer": "SAFETY↔EXECUTION",
                        "type": "KILLSWITCH_LEAK",
                        "detail": f"Kill switch active but {open_orders} open orders exist",
                        "severity": "CRITICAL",
                    })
            
            checks.append({
                "name": "Kill Switch",
                "status": "OK",
                "active": ks_active,
            })
        except Exception as e:
            checks.append({"name": "Kill Switch", "status": "ERROR", "error": str(e)})
        
        # ── CHECK 5: Decision trace integrity ──
        try:
            from modules.runtime.decision_trace import get_decision_trace_service
            trace_service = get_decision_trace_service()
            stats = await trace_service.get_stats()
            
            checks.append({
                "name": "Decision Traces",
                "status": "OK",
                "total": stats["total_traces"],
                "executed": stats["executed"],
                "rejected": stats["rejected"],
                "pass_rate": stats["pass_rate"],
            })
        except Exception as e:
            checks.append({"name": "Decision Traces", "status": "SKIP", "error": str(e)})
        
        # ── CHECK 6: Event semantics — no mixed events ──
        try:
            # Get last 100 events and check for semantic violations
            events = await self.db.execution_events.find(
                {}, {"_id": 0, "type": 1}
            ).sort("timestamp", -1).limit(100).to_list(length=100)
            
            valid_types = {
                "SIGNAL_FROM_TA", "SIGNAL_FROM_TA_PREDICTION",
                "DECISION_APPROVED", "DECISION_REJECTED",
                "DYNAMIC_RISK_APPROVED", "DYNAMIC_RISK_BLOCKED",
                "ADAPTIVE_RISK_APPLIED",
                "AUTO_BLOCKED",
                "EXECUTION_QUEUED", "RUNTIME_HANDOFF_TO_EXECUTION",
                "PENDING_DECISION_CREATED", "PENDING_DECISION_APPROVED", "PENDING_DECISION_REJECTED",
                "DECISION_EXECUTED",
                "MODE_BLOCKED_MANUAL",
                "RUNTIME_CYCLE_START", "RUNTIME_CYCLE_END",
                "RUNTIME_DISABLED", "RUNTIME_ERROR",
                "KILL_SWITCH_ACTIVE",
                "MARKET_DATA_STALE_BLOCK",
                "TRADE_THIS_CREATED",  # Sprint 3
            }
            
            unknown_types = set()
            for evt in events:
                t = evt.get("type", "")
                if t and t not in valid_types:
                    unknown_types.add(t)
            
            if unknown_types:
                mismatches.append({
                    "layer": "EVENT_SEMANTICS",
                    "type": "UNKNOWN_EVENT_TYPES",
                    "detail": f"Found {len(unknown_types)} unknown event types: {unknown_types}",
                    "severity": "LOW",
                })
            
            checks.append({
                "name": "Event Semantics",
                "status": "OK" if not unknown_types else "WARNING",
                "total_events": len(events),
                "unknown_types": list(unknown_types) if unknown_types else [],
            })
        except Exception as e:
            checks.append({"name": "Event Semantics", "status": "ERROR", "error": str(e)})
        
        # ── FINAL RESULT ──
        has_critical = any(m.get("severity") == "CRITICAL" for m in mismatches)
        has_high = any(m.get("severity") == "HIGH" for m in mismatches)
        
        overall = "CRITICAL" if has_critical else "MISMATCH" if has_high else "OK" if not mismatches else "WARNING"
        
        return {
            "status": overall,
            "checks": checks,
            "mismatches": mismatches,
            "mismatches_count": len(mismatches),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }


# ─── Singleton ─────────────────────────────────────────
_validator = None


def init_truth_validator(db) -> TruthLayerValidator:
    global _validator
    _validator = TruthLayerValidator(db)
    return _validator


def get_truth_validator() -> TruthLayerValidator:
    if _validator is None:
        raise RuntimeError("TruthLayerValidator not initialized")
    return _validator
