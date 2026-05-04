"""
PHASE 24.1 — Fractal Context Client

HTTP client for communicating with TypeScript fractal endpoints.
Handles graceful fallback when fractal service is unavailable.
"""

import httpx
import os
from typing import Optional, Tuple
from datetime import datetime
import logging

from .fractal_context_types import (
    RawFractalSignal,
    RawFractalDecision,
    RawFractalGovernance,
    RawPhaseResponse,
)

logger = logging.getLogger(__name__)


class FractalClient:
    """
    Client for TypeScript fractal endpoints.
    
    Endpoints:
    - GET /api/fractal/v2.1/signal
    - GET /api/fractal/v2.1/phase
    - GET /api/fractal/v2.1/reliability
    - GET /api/fractal/health
    """
    
    # Default to internal service URL (same container)
    DEFAULT_BASE_URL = "http://localhost:8001"
    
    # Timeout settings
    TIMEOUT_SECONDS = 3.0
    
    def __init__(self, base_url: Optional[str] = None):
        """
        Initialize fractal client.
        
        Args:
            base_url: Base URL for fractal service. Defaults to localhost:8001.
        """
        self.base_url = base_url or os.environ.get(
            "FRACTAL_SERVICE_URL", 
            self.DEFAULT_BASE_URL
        )
        self._last_signal_ts: Optional[datetime] = None
        self._last_error: Optional[str] = None
        self._last_latency_ms: Optional[int] = None
    
    @property
    def last_signal_ts(self) -> Optional[datetime]:
        return self._last_signal_ts
    
    @property
    def last_error(self) -> Optional[str]:
        return self._last_error
    
    @property
    def last_latency_ms(self) -> Optional[int]:
        return self._last_latency_ms
    
    def _get_fallback_signal(self) -> RawFractalSignal:
        """Return fallback signal when service is unavailable."""
        return RawFractalSignal(
            decision=RawFractalDecision(
                action="HOLD",
                confidence=0.0,
                reliability=0.0,
            ),
            horizons=[],
            risk=None,
            reliability=None,
            governance=RawFractalGovernance(mode="HALT"),
        )
    
    async def get_signal(self, symbol: str = "BTC") -> Tuple[RawFractalSignal, bool]:
        """
        Fetch fractal signal from TS endpoint.
        
        Args:
            symbol: Asset symbol (default: BTC)
            
        Returns:
            Tuple of (signal, success_flag)
        """
        start_time = datetime.utcnow()
        
        try:
            async with httpx.AsyncClient(timeout=self.TIMEOUT_SECONDS) as client:
                response = await client.get(
                    f"{self.base_url}/api/fractal/v2.1/signal",
                    params={"symbol": symbol}
                )
                
                self._last_latency_ms = int(
                    (datetime.utcnow() - start_time).total_seconds() * 1000
                )
                
                if response.status_code == 200:
                    data = response.json()
                    self._last_signal_ts = datetime.utcnow()
                    self._last_error = None
                    
                    # Parse response into RawFractalSignal
                    return self._parse_signal_response(data), True
                else:
                    self._last_error = f"HTTP {response.status_code}"
                    logger.warning(f"Fractal signal endpoint returned {response.status_code}")
                    return self._get_fallback_signal(), False
                    
        except httpx.TimeoutException:
            self._last_error = "Timeout"
            self._last_latency_ms = int(self.TIMEOUT_SECONDS * 1000)
            logger.warning("Fractal signal endpoint timed out")
            return self._get_fallback_signal(), False
            
        except Exception as e:
            self._last_error = str(e)
            logger.error(f"Fractal signal fetch error: {e}")
            return self._get_fallback_signal(), False
    
    async def get_phase(self, symbol: str = "BTC") -> Tuple[RawPhaseResponse, bool]:
        """
        Fetch phase classification from TS endpoint.
        
        Args:
            symbol: Asset symbol
            
        Returns:
            Tuple of (phase_response, success_flag)
        """
        try:
            async with httpx.AsyncClient(timeout=self.TIMEOUT_SECONDS) as client:
                response = await client.get(
                    f"{self.base_url}/api/fractal/v2.1/phase",
                    params={"symbol": symbol}
                )
                
                if response.status_code == 200:
                    data = response.json()
                    return RawPhaseResponse(
                        ok=data.get("ok", False),
                        phase=data.get("phase"),
                        confidence=data.get("confidence"),
                        phaseDetails=data.get("phaseDetails"),
                    ), True
                else:
                    return RawPhaseResponse(ok=False), False
                    
        except Exception as e:
            logger.warning(f"Fractal phase fetch error: {e}")
            return RawPhaseResponse(ok=False), False
    
    async def get_reliability(self, symbol: str = "BTC") -> Tuple[dict, bool]:
        """
        Fetch reliability metrics from TS endpoint.
        
        Args:
            symbol: Asset symbol
            
        Returns:
            Tuple of (reliability_dict, success_flag)
        """
        try:
            async with httpx.AsyncClient(timeout=self.TIMEOUT_SECONDS) as client:
                response = await client.get(
                    f"{self.base_url}/api/fractal/v2.1/reliability"
                )
                
                if response.status_code == 200:
                    return response.json(), True
                else:
                    return {}, False
                    
        except Exception as e:
            logger.warning(f"Fractal reliability fetch error: {e}")
            return {}, False
    
    async def health_check(self) -> Tuple[bool, str, Optional[int]]:
        """
        Check if fractal service is healthy.
        
        Returns:
            Tuple of (is_healthy, governance_mode, latency_ms)
        """
        start_time = datetime.utcnow()
        
        try:
            async with httpx.AsyncClient(timeout=2.0) as client:
                response = await client.get(f"{self.base_url}/api/fractal/health")
                
                latency_ms = int(
                    (datetime.utcnow() - start_time).total_seconds() * 1000
                )
                
                if response.status_code == 200:
                    data = response.json()
                    return True, data.get("governance", {}).get("mode", "UNKNOWN"), latency_ms
                else:
                    return False, "UNAVAILABLE", latency_ms
                    
        except Exception as e:
            logger.warning(f"Fractal health check failed: {e}")
            return False, "UNAVAILABLE", None
    
    def _parse_signal_response(self, data: dict) -> RawFractalSignal:
        """Parse raw JSON response into RawFractalSignal."""
        
        # Handle different response formats
        # Format 1: Direct signal response
        # Format 2: Wrapped in 'data' key
        signal_data = data.get("data", data) if "data" in data else data
        
        # Parse decision
        decision_raw = signal_data.get("decision") or signal_data.get("assembled")
        decision = None
        if decision_raw:
            decision = RawFractalDecision(
                action=decision_raw.get("action", "HOLD"),
                confidence=decision_raw.get("confidence", 0.0),
                reliability=decision_raw.get("reliability", 0.0),
                sizeMultiplier=decision_raw.get("sizeMultiplier"),
            )
        
        # Parse horizons
        horizons_raw = signal_data.get("horizons") or signal_data.get("signalsByHorizon")
        horizons = []
        if isinstance(horizons_raw, list):
            horizons = horizons_raw
        elif isinstance(horizons_raw, dict):
            # Convert dict format {"7d": {...}, "14d": {...}} to list
            for key, val in horizons_raw.items():
                h = int(key.replace("d", "")) if "d" in key else int(key)
                horizons.append({
                    "h": h,
                    "action": val.get("action"),
                    "expectedReturn": val.get("expectedReturn", 0.0),
                    "confidence": val.get("confidence", 0.0),
                    "weight": val.get("weight", 0.0),
                })
        
        # Parse governance
        gov_raw = signal_data.get("governance")
        governance = RawFractalGovernance(
            mode=gov_raw.get("mode", "NORMAL") if gov_raw else "NORMAL"
        )
        
        return RawFractalSignal(
            decision=decision,
            horizons=horizons,
            risk=signal_data.get("risk"),
            reliability=signal_data.get("reliability"),
            governance=governance,
            market=signal_data.get("market") or signal_data.get("meta"),
            explain=signal_data.get("explain"),
        )
