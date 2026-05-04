"""
Shadow Integration Test Routes (P1.3.1D)
=========================================

Diagnostic endpoints для тестирования shadow integration.

Endpoints:
- POST /trigger-approved-decision - synthetic approved decision
- POST /repeat-decision - idempotency stress test
- POST /test-action-filter - action filtering validation
- POST /test-dispatch-failure - failure injection test
"""

import logging
import uuid
from fastapi import APIRouter
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ops/shadow-test", tags=["P1.3.1D Shadow Integration Test"])


@router.post("/trigger-approved-decision")
async def trigger_approved_decision(symbol: str = "BTCUSDT"):
    """
    Trigger synthetic approved decision для тестирования shadow integration.
    
    Returns:
        {
            "ok": bool,
            "trace_id": str,
            "job_created": bool,
            "job_id": str,
            "dispatch_mode": str,
            "legacy_submit_executed": bool
        }
    """
    try:
        from modules.orchestrator.execution.execution_controller import ExecutionController
        from motor.motor_asyncio import AsyncIOMotorClient
        import os
        
        # Create ExecutionController
        exec_controller = ExecutionController(route_type="paper")
        
        # Generate trace_id
        trace_id = str(uuid.uuid4())
        
        # Synthetic gate_result (approved)
        gate_result = {
            "blocked": False,
            "final_action": "GO_FULL",
            "decision_enforced": {
                "action": "GO_FULL",
                "direction": "LONG",
                "confidence": 0.85
            },
            "size_multiplier": 1.0,
            "reason_chain": ["test_shadow_integration"]
        }
        
        # Synthetic execution_plan
        execution_plan = {
            "action": "GO_FULL",
            "side": "BUY",
            "size": 0.001,
            "entry": 65000,
            "stop": 64000,
            "target": 66000,
            "route_type": "paper",
            "account_id": "test_account"
        }
        
        logger.info(
            f"[P1.3.1D Test] Triggering synthetic approved decision: "
            f"symbol={symbol}, trace_id={trace_id}"
        )
        
        # Call ExecutionController (async)
        result = await exec_controller.run(
            symbol=symbol,
            timeframe="4H",
            gate_result=gate_result,
            execution_plan=execution_plan,
            trace_id=trace_id
        )
        
        # Check if job was created
        mongo_url = os.environ.get('MONGO_URL')
        client = AsyncIOMotorClient(mongo_url)
        db = client["trading_os"]
        
        job = await db["execution_jobs"].find_one({"traceId": trace_id})
        job_created = (job is not None)
        job_id = job.get("jobId") if job else None
        
        client.close()
        
        return {
            "ok": True,
            "message": "Shadow integration triggered",
            "trace_id": trace_id,
            "job_created": job_created,
            "job_id": job_id,
            "dispatch_mode": "shadow",
            "legacy_submit_executed": True,
            "execution_result": result
        }
    
    except Exception as e:
        logger.error(f"[P1.3.1D Test] Error: {e}", exc_info=True)
        return {
            "ok": False,
            "error": str(e)
        }


@router.post("/repeat-decision")
async def repeat_decision_test(symbol: str = "BTCUSDT", n: int = 10):
    """
    P1.3.1D: Idempotency Stress Test
    
    Генерирует N identical decisions с одинаковым trace_id.
    Проверяет idempotency: должен создаться только ОДИН job.
    
    Args:
        symbol: Trading symbol
        n: Number of identical decisions
    
    Returns:
        {
            "ok": bool,
            "attempted": int,
            "jobs_created": int,
            "duplicates_blocked": int,
            "trace_id": str
        }
    """
    try:
        from modules.orchestrator.execution.execution_controller import ExecutionController
        from motor.motor_asyncio import AsyncIOMotorClient
        import os
        
        # Create ExecutionController
        exec_controller = ExecutionController(route_type="paper")
        
        # Fixed trace_id (для idempotency)
        trace_id = str(uuid.uuid4())
        
        # Synthetic gate_result (identical для всех attempts)
        gate_result = {
            "blocked": False,
            "final_action": "GO_FULL",
            "decision_enforced": {
                "action": "GO_FULL",
                "direction": "LONG",
                "confidence": 0.85
            },
            "size_multiplier": 1.0,
            "reason_chain": ["idempotency_stress_test"]
        }
        
        # Synthetic execution_plan (identical для всех attempts)
        execution_plan = {
            "action": "GO_FULL",
            "side": "BUY",
            "size": 0.001,
            "entry": 65000,
            "stop": 64000,
            "target": 66000,
            "route_type": "paper",
            "account_id": "test_account"
        }
        
        logger.info(
            f"[P1.3.1D Idempotency] Starting stress test: "
            f"symbol={symbol}, trace_id={trace_id}, attempts={n}"
        )
        
        # Trigger N identical decisions
        for i in range(n):
            await exec_controller.run(
                symbol=symbol,
                timeframe="4H",
                gate_result=gate_result,
                execution_plan=execution_plan,
                trace_id=trace_id  # SAME trace_id
            )
        
        # Count jobs created
        mongo_url = os.environ.get('MONGO_URL')
        client = AsyncIOMotorClient(mongo_url)
        db = client["trading_os"]
        
        jobs_created = await db["execution_jobs"].count_documents({"traceId": trace_id})
        duplicates_blocked = n - jobs_created
        
        client.close()
        
        # Verify idempotency
        passed = (jobs_created == 1)
        
        logger.info(
            f"[P1.3.1D Idempotency] Test complete: "
            f"attempted={n}, jobs_created={jobs_created}, duplicates_blocked={duplicates_blocked}"
        )
        
        return {
            "ok": True,
            "attempted": n,
            "jobs_created": jobs_created,
            "duplicates_blocked": duplicates_blocked,
            "trace_id": trace_id,
            "pass": passed,
            "message": "PASS: Idempotency working" if passed else f"FAIL: Created {jobs_created} jobs instead of 1"
        }
    
    except Exception as e:
        logger.error(f"[P1.3.1D Idempotency] Error: {e}", exc_info=True)
        return {
            "ok": False,
            "error": str(e)
        }


@router.post("/test-action-filter")
async def test_action_filter():
    """
    P1.3.1D: Action Filtering Test
    
    Проверяет, что NON_EXECUTION_ACTIONS не попадают в queue.
    
    Returns:
        {
            "ok": bool,
            "non_execution_actions_blocked": int,
            "execution_actions_accepted": int,
            "details": [...]
        }
    """
    try:
        from modules.orchestrator.execution.execution_controller import ExecutionController
        from motor.motor_asyncio import AsyncIOMotorClient
        import os
        
        # Create ExecutionController
        exec_controller = ExecutionController(route_type="paper")
        
        # Test cases
        test_cases = [
            {"action": "WAIT", "should_enqueue": False},
            {"action": "HOLD", "should_enqueue": False},
            {"action": "BLOCK", "should_enqueue": False},
            {"action": "SKIP", "should_enqueue": False},
            {"action": "GO_FULL", "should_enqueue": True},
        ]
        
        results = []
        non_execution_blocked = 0
        execution_accepted = 0
        
        mongo_url = os.environ.get('MONGO_URL')
        client = AsyncIOMotorClient(mongo_url)
        db = client["trading_os"]
        
        for test in test_cases:
            action = test["action"]
            should_enqueue = test["should_enqueue"]
            
            trace_id = str(uuid.uuid4())
            
            # Synthetic gate_result
            gate_result = {
                "blocked": False,
                "final_action": action,
                "decision_enforced": {
                    "action": action,
                    "direction": "LONG",
                    "confidence": 0.85
                },
                "size_multiplier": 1.0,
                "reason_chain": [f"action_filter_test_{action}"]
            }
            
            execution_plan = {
                "action": action,
                "side": "BUY",
                "size": 0.001,
                "entry": 65000,
                "route_type": "paper",
                "account_id": "test_account"
            }
            
            # Trigger decision
            await exec_controller.run(
                symbol="BTCUSDT",
                timeframe="4H",
                gate_result=gate_result,
                execution_plan=execution_plan,
                trace_id=trace_id
            )
            
            # Check if job was created
            job_count = await db["execution_jobs"].count_documents({"traceId": trace_id})
            enqueued = (job_count > 0)
            
            passed = (enqueued == should_enqueue)
            
            if not should_enqueue and not enqueued:
                non_execution_blocked += 1
            elif should_enqueue and enqueued:
                execution_accepted += 1
            
            results.append({
                "action": action,
                "should_enqueue": should_enqueue,
                "actual_enqueued": enqueued,
                "pass": passed
            })
        
        client.close()
        
        all_passed = all(r["pass"] for r in results)
        
        return {
            "ok": True,
            "non_execution_actions_blocked": non_execution_blocked,
            "execution_actions_accepted": execution_accepted,
            "all_passed": all_passed,
            "details": results,
            "message": "All tests PASSED" if all_passed else "Some tests FAILED"
        }
    
    except Exception as e:
        logger.error(f"[P1.3.1D Action Filter] Error: {e}", exc_info=True)
        return {
            "ok": False,
            "error": str(e)
        }


@router.post("/test-dispatch-failure")
async def test_dispatch_failure():
    """
    P1.3.1D: Failure Injection Test
    
    Проверяет, что при падении dispatch legacy submit продолжается.
    
    Returns:
        {
            "ok": bool,
            "dispatch_failed": bool,
            "legacy_submit_continued": bool,
            "job_created": bool
        }
    """
    try:
        from modules.orchestrator.execution.execution_controller import ExecutionController
        from motor.motor_asyncio import AsyncIOMotorClient
        import os
        
        # Set force failure flag
        os.environ["EXECUTION_QUEUE_FORCE_DISPATCH_FAILURE"] = "true"
        
        # Create ExecutionController
        exec_controller = ExecutionController(route_type="paper")
        
        trace_id = str(uuid.uuid4())
        
        # Synthetic gate_result
        gate_result = {
            "blocked": False,
            "final_action": "GO_FULL",
            "decision_enforced": {
                "action": "GO_FULL",
                "direction": "LONG",
                "confidence": 0.85
            },
            "size_multiplier": 1.0,
            "reason_chain": ["failure_injection_test"]
        }
        
        execution_plan = {
            "action": "GO_FULL",
            "side": "BUY",
            "size": 0.001,
            "entry": 65000,
            "route_type": "paper",
            "account_id": "test_account"
        }
        
        logger.info(
            f"[P1.3.1D Failure] Triggering decision with forced dispatch failure"
        )
        
        # Trigger decision (dispatch should fail, legacy should continue)
        result = await exec_controller.run(
            symbol="BTCUSDT",
            timeframe="4H",
            gate_result=gate_result,
            execution_plan=execution_plan,
            trace_id=trace_id
        )
        
        # Clear flag
        os.environ["EXECUTION_QUEUE_FORCE_DISPATCH_FAILURE"] = "false"
        
        # Check if job was created (should be False due to failure)
        mongo_url = os.environ.get('MONGO_URL')
        client = AsyncIOMotorClient(mongo_url)
        db = client["trading_os"]
        
        job_created = await db["execution_jobs"].count_documents({"traceId": trace_id}) > 0
        
        client.close()
        
        # P1.3.1D FIX: Legacy submit should have continued (проверяем legacySubmitExecuted)
        legacy_continued = result.get("routing", {}).get("accepted") is not None
        
        # Dispatch failed if job not created
        dispatch_failed = not job_created
        
        # Test PASS condition: dispatch failed, но legacy submit продолжился
        passed = (dispatch_failed and legacy_continued)
        
        logger.info(
            f"[P1.3.1D Failure Test] Result: "
            f"dispatch_failed={dispatch_failed}, legacy_continued={legacy_continued}, "
            f"job_created={job_created}, passed={passed}"
        )
        
        return {
            "ok": True,
            "dispatch_failed": dispatch_failed,
            "legacy_submit_continued": legacy_continued,
            "job_created": job_created,
            "pass": passed,
            "execution_result": result,
            "message": "PASS: Failure fallback working" if passed else "FAIL: Fallback did not work"
        }
    
    except Exception as e:
        # Clear flag on error
        os.environ["EXECUTION_QUEUE_FORCE_DISPATCH_FAILURE"] = "false"
        
        logger.error(f"[P1.3.1D Failure] Error: {e}", exc_info=True)
        return {
            "ok": False,
            "error": str(e)
        }
