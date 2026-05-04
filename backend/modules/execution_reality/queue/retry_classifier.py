"""
Retry Classifier (P1.1C)
========================

Production-grade error classifier with Binance-specific error codes.

Error Categories:
- Retryable: transient (network, timeout, rate limit, 5xx)
- Non-retryable: deterministic (invalid params, insufficient balance, duplicate)
- Success (idempotency): duplicate order treated as success
"""

import logging
from typing import Tuple, Literal
from .queue_models import DLQClassification

logger = logging.getLogger(__name__)

ErrorClassification = Literal["retryable", "non_retryable", "duplicate_success"]


class RetryClassifier:
    """
    Production-grade error classifier.
    
    P1.1C Features:
    - Binance error code taxonomy
    - Duplicate order handling (-2010 → success)
    - Exponential backoff with cap
    - Error type categorization
    """
    
    # Binance-specific error codes
    # https://binance-docs.github.io/apidocs/spot/en/#error-codes
    
    # Duplicate order = IDEMPOTENCY SUCCESS
    DUPLICATE_ERROR_CODES = [
        -2010,  # NEW_ORDER_REJECTED (duplicate clientOrderId)
    ]
    
    # Retryable errors (transient)
    RETRYABLE_ERROR_CODES = [
        -1001,  # DISCONNECTED
        -1003,  # TOO_MANY_REQUESTS (rate limit)
        -1006,  # UNEXPECTED_RESP
        -1007,  # TIMEOUT
        -1021,  # TIMESTAMP_OUT_OF_SYNC (clock skew)
    ]
    
    # Non-retryable errors (deterministic business rule violations)
    NON_RETRYABLE_ERROR_CODES = [
        -1013,  # INVALID_QUANTITY
        -1100,  # ILLEGAL_CHARS
        -1101,  # TOO_MANY_PARAMETERS
        -1102,  # MANDATORY_PARAM_EMPTY_OR_MALFORMED
        -1104,  # NOT_ALL_SENT_PARAMETERS_WERE_READ
        -1105,  # PARAM_EMPTY
        -1106,  # PARAM_NOT_REQUIRED
        -1111,  # PRECISION_OVER_MAXIMUM
        -1112,  # NO_ORDERS_ON_BOOK
        -1114,  # TIME_IN_FORCE_NOT_ALLOWED
        -1115,  # INVALID_ORDER_TYPE
        -1116,  # INVALID_SIDE
        -1117,  # EMPTY_NEW_CL_ORD_ID
        -1118,  # EMPTY_ORG_CL_ORD_ID
        -1121,  # INVALID_SYMBOL
        -1136,  # ORDER_QUANTITY_TOO_SMALL
        -2010,  # Also non-retryable if NOT duplicate (will be checked separately)
        -2011,  # UNKNOWN_ORDER
    ]
    
    # Generic retryable keywords (fallback)
    RETRYABLE_KEYWORDS = [
        "timeout",
        "connection",
        "network",
        "unavailable",
        "503",
        "502",
        "500",
        "temporarily",
        "try again",
    ]
    
    # Generic non-retryable keywords (fallback)
    NON_RETRYABLE_KEYWORDS = [
        "invalid quantity",
        "invalid symbol",
        "insufficient",
        "balance",
        "margin",
        "precision",
        "lot size",
        "min notional",
        "filter failure",
        "400",
        "401",
        "403",
        "404",
    ]
    
    def classify(
        self,
        error: Exception | str,
        error_code: int | None = None
    ) -> Tuple[ErrorClassification, DLQClassification]:
        """
        Classify error for retry decision.
        
        Args:
            error: Exception or error message
            error_code: Binance error code (if available)
        
        Returns:
            (classification, dlq_classification)
            
        Classifications:
            - "retryable" → retry with backoff
            - "non_retryable" → move to DLQ
            - "duplicate_success" → treat as success (idempotency)
        """
        error_str = str(error).lower()
        
        # 1. Check Binance error codes (highest priority)
        if error_code is not None:
            # Duplicate order = SUCCESS (idempotency)
            if error_code in self.DUPLICATE_ERROR_CODES:
                logger.info(
                    f"✅ Duplicate order detected (code={error_code}) → treating as SUCCESS"
                )
                return "duplicate_success", "non_retryable"
            
            # Retryable Binance errors
            if error_code in self.RETRYABLE_ERROR_CODES:
                logger.debug(
                    f"♻️ Retryable Binance error: code={error_code}, error={error}"
                )
                return "retryable", "retry_exhausted"
            
            # Non-retryable Binance errors
            if error_code in self.NON_RETRYABLE_ERROR_CODES:
                logger.debug(
                    f"❌ Non-retryable Binance error: code={error_code}, error={error}"
                )
                return "non_retryable", "non_retryable"
        
        # 2. Keyword-based classification (fallback)
        
        # Check non-retryable keywords first (higher confidence)
        for keyword in self.NON_RETRYABLE_KEYWORDS:
            if keyword in error_str:
                logger.debug(
                    f"❌ Non-retryable error (keyword='{keyword}'): {error}"
                )
                return "non_retryable", "non_retryable"
        
        # Check retryable keywords
        for keyword in self.RETRYABLE_KEYWORDS:
            if keyword in error_str:
                logger.debug(
                    f"♻️ Retryable error (keyword='{keyword}'): {error}"
                )
                return "retryable", "retry_exhausted"
        
        # 3. Unknown error → conservative default (non-retryable)
        logger.warning(
            f"⚠️ Unknown error classification → defaulting to NON-RETRYABLE: {error}"
        )
        return "non_retryable", "unknown_error"
    
    def get_backoff_seconds(self, attempt: int) -> float:
        """
        Get exponential backoff delay.
        
        Formula: min(2^attempt, 30)
        
        Args:
            attempt: Current attempt number (0-indexed)
        
        Returns:
            Delay in seconds
        
        Examples:
            attempt=0 → 1s
            attempt=1 → 2s
            attempt=2 → 4s
            attempt=3 → 8s
            attempt=4 → 16s
            attempt=5+ → 30s (capped)
        """
        delay = min(2 ** attempt, 30)
        return float(delay)
