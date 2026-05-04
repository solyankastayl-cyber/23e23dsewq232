"""
P1.1 Error Classifier - Categorize Exchange Errors

Classifies errors into:
- RETRYABLE: Safe to retry (network, 5xx, timeouts)
- FATAL: Don't retry (invalid params, auth, insufficient balance)
- RATE_LIMIT: Special handling (rate limit hit)

CRITICAL: Wrong classification = money loss or infinite loops
"""

import logging
from typing import Union
from .retry_policy import ErrorType

logger = logging.getLogger(__name__)


class BinanceErrorClassifier:
    """
    Classifies Binance API errors for retry logic.
    
    Based on Binance error codes:
    https://binance-docs.github.io/apidocs/futures/en/#error-codes
    """
    
    # Binance error codes (commonly seen)
    INSUFFICIENT_BALANCE = -2019
    INVALID_ORDER = -2010
    INVALID_SIDE = -1102
    INVALID_SYMBOL = -1121
    INVALID_API_KEY = -2015
    INVALID_SIGNATURE = -1022
    IP_BANNED = -2015
    
    # Rate limit codes
    RATE_LIMIT_HIT = -1003
    REQUEST_WEIGHT_EXCEEDED = -1003
    
    # Server errors (retryable)
    INTERNAL_ERROR = -1000
    SERVICE_UNAVAILABLE = -1001
    TIMEOUT = -1007
    
    @staticmethod
    def classify(error: Exception) -> ErrorType:
        """
        Classify error for retry decision.
        
        Args:
            error: Exception from Binance API
        
        Returns:
            ErrorType (RETRYABLE, FATAL, or RATE_LIMIT)
        """
        error_str = str(error).lower()
        error_msg = repr(error).lower()
        
        # 1. Rate Limit Errors
        if any(phrase in error_str for phrase in [
            "rate limit",
            "too many requests",
            "-1003",
            "request weight exceeded",
            "429"
        ]):
            logger.warning(f"⏱️ RATE_LIMIT detected: {error}")
            return ErrorType.RATE_LIMIT
        
        # 2. Fatal Errors (DON'T RETRY)
        fatal_indicators = [
            "invalid api",
            "invalid signature",
            "-2015",  # Invalid API key
            "-1022",  # Invalid signature
            "insufficient balance",
            "-2019",  # Insufficient balance
            "invalid order",
            "-2010",  # Duplicate order
            "invalid symbol",
            "-1121",
            "invalid side",
            "-1102",
            "unauthorized",
            "forbidden",
            "400",  # Bad request (params issue)
        ]
        
        if any(phrase in error_str for phrase in fatal_indicators):
            logger.error(f"❌ FATAL error detected (no retry): {error}")
            return ErrorType.FATAL
        
        # 3. Network/Timeout Errors (RETRYABLE)
        retryable_indicators = [
            "timeout",
            "connection",
            "reset",
            "network",
            "503",  # Service unavailable
            "502",  # Bad gateway
            "504",  # Gateway timeout
            "500",  # Internal server error
            "-1000",  # Internal error
            "-1001",  # Service unavailable
            "-1007",  # Timeout
            "read timed out",
            "connection aborted",
            "connection reset",
        ]
        
        if any(phrase in error_str for phrase in retryable_indicators):
            logger.warning(f"⚠️ RETRYABLE error detected: {error}")
            return ErrorType.RETRYABLE
        
        # 4. Default: treat unknown errors as RETRYABLE (safer)
        # Better to retry unknown error than fail immediately
        logger.warning(
            f"⚠️ UNKNOWN error, defaulting to RETRYABLE: {error}"
        )
        return ErrorType.RETRYABLE


class GenericErrorClassifier:
    """
    Generic error classifier for non-Binance adapters.
    
    Falls back to HTTP status code classification.
    """
    
    @staticmethod
    def classify(error: Exception) -> ErrorType:
        """
        Classify error based on HTTP status codes and common patterns.
        
        Args:
            error: Exception from API call
        
        Returns:
            ErrorType
        """
        error_str = str(error).lower()
        
        # Rate limits
        if "429" in error_str or "rate limit" in error_str:
            return ErrorType.RATE_LIMIT
        
        # Client errors (4xx) - usually fatal
        if any(code in error_str for code in ["400", "401", "403", "404"]):
            return ErrorType.FATAL
        
        # Server errors (5xx) - retryable
        if any(code in error_str for code in ["500", "502", "503", "504"]):
            return ErrorType.RETRYABLE
        
        # Timeouts - retryable
        if "timeout" in error_str or "timed out" in error_str:
            return ErrorType.RETRYABLE
        
        # Connection errors - retryable
        if any(phrase in error_str for phrase in [
            "connection",
            "reset",
            "network",
            "refused"
        ]):
            return ErrorType.RETRYABLE
        
        # Default: retryable (safer)
        return ErrorType.RETRYABLE


def classify_binance_error(error: Exception) -> ErrorType:
    """
    Convenience function for Binance error classification.
    
    Args:
        error: Exception from Binance API
    
    Returns:
        ErrorType
    """
    return BinanceErrorClassifier.classify(error)


def classify_generic_error(error: Exception) -> ErrorType:
    """
    Convenience function for generic error classification.
    
    Args:
        error: Exception from any API
    
    Returns:
        ErrorType
    """
    return GenericErrorClassifier.classify(error)
