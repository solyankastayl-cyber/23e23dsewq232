"""
Risk Guard Layer — Position & Execution Safety
================================================
P1: Hard guards for execution pipeline.

Guards:
1. MAX_POSITION_SIZE_USD — reject oversized positions
2. MAX_OPEN_POSITIONS — reject when too many open
3. Duplicate Protection — 1 decision → 1 position
4. Close Integrity — every close writes an outcome
5. Kill Switch — halt all trading if total PnL < threshold
"""

import logging
import os
from datetime import datetime, timezone
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

# ─── Constants ───────────────────────────────────────
MAX_POSITION_SIZE_USD = float(os.getenv("MAX_POSITION_SIZE_USD", "100"))
MAX_OPEN_POSITIONS = int(os.getenv("MAX_OPEN_POSITIONS", "5"))
KILL_SWITCH_THRESHOLD_USD = float(os.getenv("KILL_SWITCH_THRESHOLD_USD", "-10"))


class RiskGuard:
    """
    Pre-execution risk guard. Checks all safety constraints before
    allowing an order to proceed.
    """

    def __init__(self, db=None):
        self.db = db  # motor async db (trading_os)
        
        # STEP 1.5.8: Per-experiment state isolation (NO shared state!)
        from collections import defaultdict
        
        # Per-experiment kill switch
        self._kill_switch_state = defaultdict(lambda: {
            "active": False,
            "reason": None,
            "activated_at": None
        })
        
        # Per-experiment stats
        self._stats_by_experiment = defaultdict(lambda: {
            "total_checked": 0,
            "passed": 0,
            "rejected_max_positions": 0,
            "rejected_max_size": 0,
            "rejected_duplicate": 0,
            "rejected_kill_switch": 0,
        })
        
        logger.info(
            f"[RiskGuard] Initialized with per-experiment isolation: "
            f"max_size=${MAX_POSITION_SIZE_USD}, "
            f"max_positions={MAX_OPEN_POSITIONS}, "
            f"kill_threshold=${KILL_SWITCH_THRESHOLD_USD}"
        )

    async def check_pre_execution(
        self, payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Run all pre-execution checks. Returns:
          {"allowed": True} or {"allowed": False, "reason": "..."}
        """
        # STEP 1.5.8.1: Extract experiment_id first (safe fallback)
        experiment_id = payload.get("experiment_id", "baseline_btc")
        
        self._stats_by_experiment[experiment_id]["total_checked"] += 1
        symbol = payload.get("symbol", "?")
        decision_id = payload.get("decision_id", payload.get("clientOrderId", ""))
        size_usd = payload.get("size_usd", payload.get("notional_usd", 0))

        # ── Guard 5: Kill Switch (per-experiment) ───────
        if self._kill_switch_state[experiment_id]["active"]:
            self._stats_by_experiment[experiment_id]["rejected_kill_switch"] += 1
            reason = f"KILL SWITCH ACTIVE ({experiment_id}): {self._kill_switch_state[experiment_id]['reason']}"
            logger.critical(f"[RiskGuard] REJECTED {symbol}: {reason}")
            return {"allowed": False, "reason": reason}

        # Check kill switch threshold (per-experiment)
        await self._check_kill_switch(experiment_id)
        if self._kill_switch_state[experiment_id]["active"]:
            self._stats_by_experiment[experiment_id]["rejected_kill_switch"] += 1
            reason = f"KILL SWITCH ACTIVATED ({experiment_id}): {self._kill_switch_state[experiment_id]['reason']}"
            logger.critical(f"[RiskGuard] REJECTED {symbol}: {reason}")
            return {"allowed": False, "reason": reason}

        # ── Guard 1: Max open positions (per-experiment) ─
        open_count = await self._count_open_positions(experiment_id)
        if open_count >= MAX_OPEN_POSITIONS:
            self._stats_by_experiment[experiment_id]["rejected_max_positions"] += 1
            reason = (
                f"max open positions reached ({open_count}/{MAX_OPEN_POSITIONS})"
            )
            logger.warning(f"[RiskGuard] REJECTED {symbol}: {reason}")
            return {"allowed": False, "reason": reason}

        # ── Guard 2: Max position size ───────────────────
        if size_usd > MAX_POSITION_SIZE_USD:
            self._stats_by_experiment[experiment_id]["rejected_max_size"] += 1
            reason = (
                f"position size ${size_usd:.2f} exceeds max "
                f"${MAX_POSITION_SIZE_USD:.2f}"
            )
            logger.warning(f"[RiskGuard] REJECTED {symbol}: {reason}")
            return {"allowed": False, "reason": reason}

        # ── Guard 3: Duplicate protection ────────────────
        if decision_id:
            dup = await self._check_duplicate(decision_id, experiment_id)
            if dup:
                self._stats_by_experiment[experiment_id]["rejected_duplicate"] += 1
                reason = f"duplicate execution for decision {decision_id}"
                logger.warning(f"[RiskGuard] SKIPPED {symbol}: {reason}")
                return {"allowed": False, "reason": reason}

        # All passed
        self._stats_by_experiment[experiment_id]["passed"] += 1
        logger.info(
            f"[RiskGuard] PASSED {symbol}: open={open_count}/{MAX_OPEN_POSITIONS}, "
            f"size=${size_usd:.2f}/{MAX_POSITION_SIZE_USD} ({experiment_id})"
        )
        return {"allowed": True}

    # ─── Internal helpers ────────────────────────────────

    async def _count_open_positions(self, experiment_id: str = "baseline_btc") -> int:
        """STEP 1.5.8.2: Count open positions for specific experiment only"""
        if self.db is None:
            return 0
        try:
            # Filter by experiment_id
            return await self.db.trading_cases.count_documents(
                {"status": "ACTIVE", "experiment_id": experiment_id}
            )
        except Exception as e:
            logger.error(f"[RiskGuard] Failed to count positions for {experiment_id}: {e}")
            return 0

    async def _check_duplicate(self, decision_id: str, experiment_id: str = "baseline_btc") -> bool:
        """STEP 1.5.8.3: Check duplicate within experiment only"""
        if self.db is None:
            return False
        try:
            # Check if decision already exists in THIS experiment
            existing = await self.db.trading_cases.find_one(
                {"decision_id": decision_id, "experiment_id": experiment_id}
            )
            return existing is not None
        except Exception as e:
            logger.error(f"[RiskGuard] Duplicate check failed for {decision_id} ({experiment_id}): {e}")
            return False

    async def _check_kill_switch(self, experiment_id: str = "baseline_btc"):
        """STEP 1.5.8.4: Check kill switch for specific experiment only"""
        if self.db is None:
            return
        try:
            pipeline = [
                {"$match": {"experiment_id": experiment_id, "status": "CLOSED"}},
                {"$group": {"_id": None, "total": {"$sum": "$realized_pnl"}}},
            ]
            cursor = self.db.trading_cases.aggregate(pipeline)
            results = await cursor.to_list(length=1)
            total_pnl = results[0]["total"] if results else 0.0

            if total_pnl < KILL_SWITCH_THRESHOLD_USD:
                self._kill_switch_state[experiment_id]["active"] = True
                self._kill_switch_state[experiment_id]["reason"] = (
                    f"total PnL ${total_pnl:.2f} < ${KILL_SWITCH_THRESHOLD_USD:.2f}"
                )
                self._kill_switch_state[experiment_id]["activated_at"] = datetime.now(timezone.utc).isoformat()
                logger.critical(
                    f"[RiskGuard] KILL SWITCH ACTIVATED for {experiment_id}: {self._kill_switch_state[experiment_id]['reason']}"
                )
        except Exception as e:
            logger.error(f"[RiskGuard] Kill switch check failed for {experiment_id}: {e}")

    # ─── Close integrity (Guard 4) ───────────────────────

    @staticmethod
    def verify_close_pnl(
        symbol: str,
        side: str,
        entry_price: float,
        exit_price: float,
        qty: float,
        stored_pnl: float,
    ) -> bool:
        """
        PnL sanity check on position close.
        Returns True if verified, False if mismatch.
        """
        direction = 1.0 if side == "LONG" else -1.0
        calculated_pnl = (exit_price - entry_price) * qty * direction

        if abs(calculated_pnl - stored_pnl) > 0.01:
            logger.error(
                f"[RiskGuard] PNL MISMATCH: {symbol} {side} "
                f"calculated={calculated_pnl:.4f} stored={stored_pnl:.4f} "
                f"entry={entry_price} exit={exit_price} qty={qty}"
            )
            return False

        logger.info(
            f"[RiskGuard] PNL VERIFIED: {symbol} {side} "
            f"entry=${entry_price:,.2f} exit=${exit_price:,.2f} "
            f"qty={qty:.6f} pnl=${calculated_pnl:.4f}"
        )
        # Also print for visibility in logs
        print(
            f"[RiskGuard] PNL VERIFIED: {symbol} {side} "
            f"entry=${entry_price:,.2f} exit=${exit_price:,.2f} "
            f"qty={qty:.6f} pnl=${calculated_pnl:.4f}"
        )
        return True

    async def integrity_check(self) -> Dict[str, Any]:
        """
        Periodic integrity check: orphaned outcomes, unclosed positions,
        PnL mismatches.
        """
        result = {
            "orphaned_outcomes": 0,
            "unclosed_positions_without_pnl": 0,
            "pnl_mismatches": 0,
            "checked_at": datetime.now(timezone.utc).isoformat(),
        }
        if self.db is None:
            return result

        try:
            # Closed cases without outcomes
            closed_cases = await self.db.trading_cases.find(
                {"status": "CLOSED"}, {"_id": 0, "decision_id": 1}
            ).to_list(length=500)
            closed_decision_ids = {
                c["decision_id"] for c in closed_cases if c.get("decision_id")
            }

            outcomes = await self.db.decision_outcomes.find(
                {}, {"_id": 0, "decision_id": 1}
            ).to_list(length=500)
            outcome_decision_ids = {
                o["decision_id"] for o in outcomes if o.get("decision_id")
            }

            # Orphaned outcomes (outcome exists but no CLOSED case)
            orphaned = outcome_decision_ids - closed_decision_ids
            result["orphaned_outcomes"] = len(orphaned)

            # PnL mismatches on closed cases
            closed_full = await self.db.trading_cases.find(
                {"status": "CLOSED"},
                {"_id": 0, "symbol": 1, "side": 1, "entry_price": 1,
                 "current_price": 1, "qty": 1, "realized_pnl": 1,
                 "avg_entry_price": 1},
            ).to_list(length=500)
            for c in closed_full:
                entry = c.get("avg_entry_price") or c.get("entry_price", 0)
                exit_p = c.get("current_price", 0)
                qty = c.get("qty", 0)
                side = c.get("side", "LONG")
                stored = c.get("realized_pnl", 0)
                direction = 1.0 if side == "LONG" else -1.0
                calc = (exit_p - entry) * qty * direction
                if abs(calc - stored) > 0.01:
                    result["pnl_mismatches"] += 1

        except Exception as e:
            logger.error(f"[RiskGuard] Integrity check failed: {e}")

        if result["orphaned_outcomes"] or result["pnl_mismatches"]:
            logger.warning(f"[RiskGuard] Integrity issues: {result}")
        else:
            logger.info(f"[RiskGuard] Integrity OK: {result}")

        return result

    # ─── API helpers ─────────────────────────────────────

    async def get_status(self, experiment_id: str = "baseline_btc") -> Dict[str, Any]:
        """
        Get status for specific experiment.
        
        Args:
            experiment_id: Experiment to get status for (default: baseline_btc)
        """
        total_pnl = 0.0
        open_positions = 0
        if self.db is not None:
            try:
                pipeline = [
                    {"$match": {"status": "CLOSED", "experiment_id": experiment_id}},
                    {"$group": {"_id": None, "total": {"$sum": "$realized_pnl"}}},
                ]
                cursor = self.db.trading_cases.aggregate(pipeline)
                results = await cursor.to_list(length=1)
                total_pnl = results[0]["total"] if results else 0.0
            except Exception:
                pass
            try:
                open_positions = await self.db.portfolio_positions.count_documents(
                    {"status": "OPEN", "experiment_id": experiment_id}
                )
            except Exception:
                pass
        
        state = self._kill_switch_state[experiment_id]
        return {
            "experiment_id": experiment_id,
            "kill_switch_active": state["active"],
            "kill_switch_reason": state["reason"],
            "kill_switch_activated_at": state["activated_at"],
            "total_pnl": round(total_pnl, 4),
            "open_positions": open_positions,
            "config": {
                "max_position_size_usd": MAX_POSITION_SIZE_USD,
                "max_open_positions": MAX_OPEN_POSITIONS,
                "kill_switch_threshold_usd": KILL_SWITCH_THRESHOLD_USD,
            },
            "stats": dict(self._stats_by_experiment[experiment_id]),
        }

    def get_stats(self, experiment_id: Optional[str] = None) -> Dict[str, Any]:
        """
        STEP 1.5.9: Get stats with optional experiment filter
        
        Args:
            experiment_id: If provided, return stats for that experiment only
                          If None, return baseline_btc for backward compatibility
        """
        if experiment_id:
            return self._stats_by_experiment[experiment_id]
        else:
            # Backward compatibility: return baseline stats
            return self._stats_by_experiment["baseline_btc"]

    def reset_kill_switch(self, experiment_id: str = "baseline_btc"):
        """
        Reset kill switch for specific experiment.
        
        Args:
            experiment_id: Experiment to reset (default: baseline_btc)
        """
        self._kill_switch_state[experiment_id]["active"] = False
        self._kill_switch_state[experiment_id]["reason"] = None
        self._kill_switch_state[experiment_id]["activated_at"] = None
        logger.info(f"[RiskGuard] Kill switch RESET manually for {experiment_id}")
        return {"ok": True, "message": f"Kill switch reset for {experiment_id}"}


# ─── Singleton ───────────────────────────────────────
_risk_guard: Optional[RiskGuard] = None


def init_risk_guard(db) -> RiskGuard:
    global _risk_guard
    _risk_guard = RiskGuard(db=db)
    return _risk_guard


def get_risk_guard() -> Optional[RiskGuard]:
    return _risk_guard
