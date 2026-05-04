"""Audit Helper - P0.7

Safe fire-and-forget async task execution for audit logging.
Ensures audit never blocks trading flow while maintaining observability.
"""

import asyncio
import logging
from typing import Coroutine, Any

logger = logging.getLogger(__name__)


def run_audit_task(coro: Coroutine[Any, Any, None], context: str):
    """
    Execute audit task in fire-and-forget mode with error handling.
    
    This is the ONLY way to call audit repositories from sync/async code.
    Never use await or create_task directly.
    
    Args:
        coro: Coroutine to execute (audit insert operation)
        context: Context string for error logging
    
    Pattern:
        run_audit_task(
            audit_controller.decision.insert({...}),
            context="decision_audit"
        )
    """
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        # Fallback: no running loop (shouldn't happen in FastAPI)
        logger.warning(f"[AUDIT] No event loop for {context}, using asyncio.run")
        asyncio.run(_safe_wrapper(coro, context))
        return
    
    # Create task in existing event loop
    task = loop.create_task(_safe_wrapper(coro, context))
    task.add_done_callback(_handle_task_result)


async def _safe_wrapper(coro: Coroutine[Any, Any, None], context: str):
    """Wrap coroutine with error handling"""
    try:
        await coro
        logger.debug(f"[AUDIT] {context} completed")
    except Exception as e:
        # CRITICAL: Log but don't raise (audit must never break trading)
        logger.error(f"[AUDIT ERROR] {context}: {e}", exc_info=True)


def _handle_task_result(task: asyncio.Task):
    """Handle task completion (catch any remaining exceptions)"""
    try:
        task.result()
    except Exception:
        # Already logged in wrapper
        pass
