"""
Execution Submit Simulator (P1.3.2)
====================================

Dry-run submit emulator для тестирования worker runtime БЕЗ реальных вызовов биржи.

P1.3.2 Constraint: dry_run = true (no real exchange calls)
"""

import logging
import asyncio
import uuid
from typing import Dict, Any
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class ExecutionSubmitSimulator:
    """
    Dry-run execution submit simulator.
    
    Эмулирует submit→ack flow без реальных вызовов биржи.
    """
    
    def __init__(self, simulate_latency_ms: int = 100, failure_rate: float = 0.0):
        """
        Args:
            simulate_latency_ms: Simulated network latency in milliseconds
            failure_rate: Simulated failure rate (0.0-1.0) для retry testing
        """
        self.simulate_latency_ms = simulate_latency_ms
        self.failure_rate = failure_rate  # P1.3.2B: configurable failures
        
        logger.info(
            f"✅ ExecutionSubmitSimulator initialized (DRY-RUN mode): "
            f"latency={simulate_latency_ms}ms, failure_rate={failure_rate:.1%}"
        )
    
    async def submit_order(
        self,
        job_id: str,
        trace_id: str,
        payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Simulate order submit (dry-run).
        
        Args:
            job_id: Job identifier
            trace_id: Causal trace ID
            payload: Execution job payload
        
        Returns:
            {
                "success": bool,
                "order_id": str (если success),
                "error": str (если failure),
                "simulated": true
            }
        """
        # Simulate network latency
        await asyncio.sleep(self.simulate_latency_ms / 1000.0)
        
        # Simulate failure (if configured)
        import random
        if random.random() < self.failure_rate:
            error = "SIMULATED_FAILURE: Random failure triggered"
            logger.warning(
                f"[DRY-RUN] Submit failed (simulated): job_id={job_id}, "
                f"trace_id={trace_id}, error={error}"
            )
            
            return {
                "success": False,
                "error": error,
                "simulated": True,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        
        # Simulate success
        simulated_order_id = f"sim-{uuid.uuid4().hex[:16]}"
        
        logger.info(
            f"✅ [DRY-RUN] Order submitted (simulated): job_id={job_id}, "
            f"trace_id={trace_id}, order_id={simulated_order_id}, "
            f"symbol={payload.get('symbol')}, side={payload.get('side')}, "
            f"qty={payload.get('final_size')}"
        )
        
        return {
            "success": True,
            "order_id": simulated_order_id,
            "exchange_order_id": simulated_order_id,
            "status": "FILLED",  # Instant fill for dry-run
            "filled_qty": payload.get("final_size", 0.0),
            "avg_price": payload.get("entry_price", 0.0),
            "simulated": True,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "payload": {
                "symbol": payload.get("symbol"),
                "side": payload.get("side"),
                "quantity": payload.get("final_size"),
                "price": payload.get("entry_price"),
                "orderType": payload.get("execution_mode", "LIMIT")
            }
        }
    
    async def cancel_order(self, order_id: str) -> Dict[str, Any]:
        """
        Simulate order cancellation (dry-run).
        
        Args:
            order_id: Order identifier
        
        Returns:
            {
                "success": bool,
                "simulated": true
            }
        """
        await asyncio.sleep(self.simulate_latency_ms / 1000.0)
        
        logger.info(f"✅ [DRY-RUN] Order cancelled (simulated): order_id={order_id}")
        
        return {
            "success": True,
            "order_id": order_id,
            "status": "CANCELLED",
            "simulated": True,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    
    async def get_order_status(self, order_id: str) -> Dict[str, Any]:
        """
        Simulate order status query (dry-run).
        
        Args:
            order_id: Order identifier
        
        Returns:
            {
                "order_id": str,
                "status": str,
                "simulated": true
            }
        """
        await asyncio.sleep(self.simulate_latency_ms / 1000.0)
        
        return {
            "order_id": order_id,
            "status": "FILLED",
            "simulated": True,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }


# Global singleton instance (опционально)
_submit_simulator: ExecutionSubmitSimulator = None


def get_submit_simulator() -> ExecutionSubmitSimulator:
    """Get singleton ExecutionSubmitSimulator instance."""
    global _submit_simulator
    if _submit_simulator is None:
        _submit_simulator = ExecutionSubmitSimulator()
    return _submit_simulator


def set_submit_simulator(simulator: ExecutionSubmitSimulator):
    """Set singleton ExecutionSubmitSimulator instance."""
    global _submit_simulator
    _submit_simulator = simulator
    logger.info("✅ ExecutionSubmitSimulator singleton set")
