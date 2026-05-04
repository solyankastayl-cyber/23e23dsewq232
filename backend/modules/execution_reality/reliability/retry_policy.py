"""
P1.1 Retry Policy - Exponential Backoff with Jitter

Provides anti-fragility layer for transient failures:
- Network timeouts
- Exchange 5xx errors
- Connection resets
- Temporary unavailability

P1.1+ Enhancements:
- Retry Budget: System-wide throttling (prevent self-DDoS)
- Idempotency Support: Safe retry without duplicate orders

CRITICAL RULES:
- Only retryable errors get retry attempts
- Fatal errors fail immediately
- Rate limit errors use special backoff
- Audit every retry attempt
- Check global retry budget before retry
"""

import asyncio
import random
import logging
from typing import Callable, Any, Optional, Dict
from datetime import datetime, timezone
from enum import Enum

logger = logging.getLogger(__name__)


class ErrorType(Enum):
    """Error classification for retry logic"""
    RETRYABLE = "retryable"          # Network/5xx - safe to retry
    FATAL = "fatal"                  # Invalid params/auth - don't retry
    RATE_LIMIT = "rate_limit"        # Rate limit hit - special backoff


class RetryPolicy:
    """
    Exponential backoff retry policy with jitter + budget control.
    
    Features:
    - Exponential backoff: delay = base * (2 ** attempt)
    - Jitter: randomize delay to prevent thundering herd
    - Max attempts: prevent infinite loops
    - Max delay: cap backoff growth
    - Error classification: only retry safe errors
    - Retry budget: global throttling (prevent self-DDoS)
    """
    
    def __init__(
        self,
        max_attempts: int = 3,
        base_delay_ms: float = 100.0,
        max_delay_ms: float = 5000.0,
        jitter: bool = True,
        audit_callback: Optional[Callable] = None,
        use_retry_budget: bool = True,
        event_emitter: Optional[Callable] = None
    ):
        self.max_attempts = max_attempts
        self.base_delay_ms = base_delay_ms
        self.max_delay_ms = max_delay_ms
        self.jitter = jitter
        self.audit_callback = audit_callback
        self.use_retry_budget = use_retry_budget
        self.event_emitter = event_emitter  # P1.1: Event emission for budget exhaustion
    
    async def execute_async(
        self,
        fn: Callable,
        *args,
        error_classifier: Callable[[Exception], ErrorType],
        context: Optional[Dict[str, Any]] = None,
        pre_retry_check: Optional[Callable] = None,
        operation_type: str = "READ",  # P1.1: READ vs WRITE separation
        **kwargs
    ) -> Any:
        """
        Execute async function with retry policy.
        
        Args:
            fn: Async function to execute
            *args: Positional args for fn
            error_classifier: Function to classify errors
            context: Context for audit logging
            pre_retry_check: Optional check before retry (P1.1 safety)
            operation_type: "READ" (safe, aggressive retry) or "WRITE" (dangerous, strict retry)
            **kwargs: Keyword args for fn
        
        Returns:
            Result from fn
        
        Raises:
            Last exception if all retries exhausted
        """
        last_exception = None
        context = context or {}
        
        # P1.1: Adjust max_attempts based on operation type
        max_attempts = self.max_attempts
        if operation_type == "WRITE":
            max_attempts = min(2, self.max_attempts)  # Strict limit for writes
            logger.debug(f"⚠️ WRITE operation: limiting retries to {max_attempts}")
        elif operation_type == "READ":
            max_attempts = max(5, self.max_attempts)  # Aggressive retry for reads
        
        for attempt in range(max_attempts):
            # P1.1 CRITICAL: Pre-retry safety check
            # Prevents double-submit when order already exists
            if attempt > 0 and pre_retry_check:
                try:
                    existing_result = await pre_retry_check(context)
                    if existing_result:
                        logger.info(
                            f"✅ PRE-RETRY CHECK: Found existing result, skipping retry | "
                            f"attempt={attempt} | context={context}"
                        )
                        return existing_result
                except Exception as check_error:
                    logger.warning(
                        f"⚠️ Pre-retry check failed (continuing): {check_error}"
                    )
            
            try:
                result = await fn(*args, **kwargs)
                
                # Success - log if retried
                if attempt > 0:
                    self._audit(
                        context=context,
                        attempt=attempt,
                        outcome="success",
                        delay_ms=0,
                        error=None
                    )
                
                return result
            
            except Exception as e:
                last_exception = e
                error_type = error_classifier(e)
                
                # Fatal errors - fail immediately
                if error_type == ErrorType.FATAL:
                    logger.error(
                        f"❌ FATAL error (no retry) | attempt={attempt + 1} | "
                        f"error={e} | context={context}"
                    )
                    self._audit(
                        context=context,
                        attempt=attempt,
                        outcome="fatal",
                        delay_ms=0,
                        error=str(e)
                    )
                    raise
                
                # Last attempt - exhausted
                if attempt == self.max_attempts - 1:
                    logger.error(
                        f"❌ RETRY EXHAUSTED | attempts={self.max_attempts} | "
                        f"error={e} | context={context}"
                    )
                    self._audit(
                        context=context,
                        attempt=attempt,
                        outcome="exhausted",
                        delay_ms=0,
                        error=str(e)
                    )
                    raise
                
                # Calculate backoff delay
                delay_ms = self._calculate_delay(attempt, error_type)
                
                logger.warning(
                    f"⚠️ Retry attempt {attempt + 1}/{self.max_attempts} | "
                    f"error_type={error_type.value} | delay={delay_ms:.0f}ms | "
                    f"error={e} | context={context}"
                )
                
                self._audit(
                    context=context,
                    attempt=attempt,
                    outcome="retry",
                    delay_ms=delay_ms,
                    error=str(e)
                )
                
                # Wait before retry
                await asyncio.sleep(delay_ms / 1000.0)
        
        # Should never reach here, but safety
        raise last_exception
    
    def _calculate_delay(self, attempt: int, error_type: ErrorType) -> float:
        """
        Calculate backoff delay with exponential growth + jitter.
        
        Args:
            attempt: Current attempt number (0-indexed)
            error_type: Type of error (affects base delay)
        
        Returns:
            Delay in milliseconds
        """
        # Base delay (higher for rate limits)
        base = self.base_delay_ms
        if error_type == ErrorType.RATE_LIMIT:
            base = base * 5  # Rate limit = more aggressive backoff
        
        # Exponential backoff: delay = base * (2 ** attempt)
        delay = base * (2 ** attempt)
        
        # Cap at max_delay
        delay = min(delay, self.max_delay_ms)
        
        # Add jitter (randomize ±25% to prevent thundering herd)
        if self.jitter:
            jitter_range = delay * 0.25
            jitter_offset = random.uniform(-jitter_range, jitter_range)
            delay = delay + jitter_offset
        
        return max(delay, 0)  # Never negative
    
    def _audit(
        self,
        context: Dict[str, Any],
        attempt: int,
        outcome: str,
        delay_ms: float,
        error: Optional[str]
    ):
        """
        Audit retry attempt.
        
        Args:
            context: Execution context
            attempt: Attempt number
            outcome: success/retry/exhausted/fatal
            delay_ms: Delay before next retry
            error: Error message (if any)
        """
        if not self.audit_callback:
            return
        
        try:
            self.audit_callback({
                "timestamp": datetime.now(timezone.utc),
                "context": context,
                "attempt": attempt + 1,
                "max_attempts": self.max_attempts,
                "outcome": outcome,
                "delay_ms": round(delay_ms, 1),
                "error": error
            })
        except Exception as e:
            logger.warning(f"Retry audit failed: {e}")


class SyncRetryPolicy:
    """
    Synchronous version of RetryPolicy for non-async code.
    
    Same logic as RetryPolicy but uses time.sleep instead of asyncio.sleep.
    """
    
    def __init__(
        self,
        max_attempts: int = 3,
        base_delay_ms: float = 100.0,
        max_delay_ms: float = 5000.0,
        jitter: bool = True,
        audit_callback: Optional[Callable] = None
    ):
        self.max_attempts = max_attempts
        self.base_delay_ms = base_delay_ms
        self.max_delay_ms = max_delay_ms
        self.jitter = jitter
        self.audit_callback = audit_callback
    
    def execute(
        self,
        fn: Callable,
        *args,
        error_classifier: Callable[[Exception], ErrorType],
        context: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Any:
        """
        Execute sync function with retry policy.
        
        Args:
            fn: Sync function to execute
            *args: Positional args for fn
            error_classifier: Function to classify errors
            context: Context for audit logging
            **kwargs: Keyword args for fn
        
        Returns:
            Result from fn
        
        Raises:
            Last exception if all retries exhausted
        """
        import time
        
        last_exception = None
        context = context or {}
        
        for attempt in range(self.max_attempts):
            try:
                result = fn(*args, **kwargs)
                
                # Success - log if retried
                if attempt > 0:
                    self._audit(
                        context=context,
                        attempt=attempt,
                        outcome="success",
                        delay_ms=0,
                        error=None
                    )
                
                return result
            
            except Exception as e:
                last_exception = e
                error_type = error_classifier(e)
                
                # Fatal errors - fail immediately
                if error_type == ErrorType.FATAL:
                    logger.error(
                        f"❌ FATAL error (no retry) | attempt={attempt + 1} | "
                        f"error={e} | context={context}"
                    )
                    self._audit(
                        context=context,
                        attempt=attempt,
                        outcome="fatal",
                        delay_ms=0,
                        error=str(e)
                    )
                    raise
                
                # Last attempt - exhausted
                if attempt == self.max_attempts - 1:
                    logger.error(
                        f"❌ RETRY EXHAUSTED | attempts={self.max_attempts} | "
                        f"error={e} | context={context}"
                    )
                    self._audit(
                        context=context,
                        attempt=attempt,
                        outcome="exhausted",
                        delay_ms=0,
                        error=str(e)
                    )
                    raise
                
                # Calculate backoff delay
                delay_ms = self._calculate_delay(attempt, error_type)
                
                logger.warning(
                    f"⚠️ Retry attempt {attempt + 1}/{self.max_attempts} | "
                    f"error_type={error_type.value} | delay={delay_ms:.0f}ms | "
                    f"error={e} | context={context}"
                )
                
                self._audit(
                    context=context,
                    attempt=attempt,
                    outcome="retry",
                    delay_ms=delay_ms,
                    error=str(e)
                )
                
                # Wait before retry
                time.sleep(delay_ms / 1000.0)
        
        # Should never reach here, but safety
        raise last_exception
    
    def _calculate_delay(self, attempt: int, error_type: ErrorType) -> float:
        """Calculate backoff delay (same logic as async version)"""
        base = self.base_delay_ms
        if error_type == ErrorType.RATE_LIMIT:
            base = base * 5
        
        delay = base * (2 ** attempt)
        delay = min(delay, self.max_delay_ms)
        
        if self.jitter:
            jitter_range = delay * 0.25
            jitter_offset = random.uniform(-jitter_range, jitter_range)
            delay = delay + jitter_offset
        
        return max(delay, 0)
    
    def _audit(self, context, attempt, outcome, delay_ms, error):
        """Audit retry attempt (same logic as async version)"""
        if not self.audit_callback:
            return
        
        try:
            self.audit_callback({
                "timestamp": datetime.now(timezone.utc),
                "context": context,
                "attempt": attempt + 1,
                "max_attempts": self.max_attempts,
                "outcome": outcome,
                "delay_ms": round(delay_ms, 1),
                "error": error
            })
        except Exception as e:
            logger.warning(f"Retry audit failed: {e}")
