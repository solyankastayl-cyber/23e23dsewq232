"""
Scanner Types

Core data structures for scanning system.
"""

import time
from dataclasses import dataclass, field
from typing import Dict, Optional, Any, Literal


# ══════════════════════════════════════════════════════════════
# Enums
# ══════════════════════════════════════════════════════════════

JobType = Literal["ta_scan", "prediction_build", "prediction_evaluate"]
JobStatus = Literal["queued", "running", "done", "failed"]


# ══════════════════════════════════════════════════════════════
# Asset Registry
# ══════════════════════════════════════════════════════════════

@dataclass
class AssetRegistryItem:
    """Asset in the scanning universe."""
    symbol: str
    exchange: str
    is_active: bool
    volume_rank: int
    quote: str = "USDT"
    category: str = "crypto"  # crypto, forex, stock
    updated_at: int = field(default_factory=lambda: int(time.time()))
    
    def to_dict(self) -> dict:
        return {
            "symbol": self.symbol,
            "exchange": self.exchange,
            "is_active": self.is_active,
            "volume_rank": self.volume_rank,
            "quote": self.quote,
            "category": self.category,
            "updated_at": self.updated_at,
        }
    
    @staticmethod
    def from_dict(d: dict) -> "AssetRegistryItem":
        return AssetRegistryItem(
            symbol=d["symbol"],
            exchange=d.get("exchange", "binance"),
            is_active=d.get("is_active", True),
            volume_rank=d.get("volume_rank", 999),
            quote=d.get("quote", "USDT"),
            category=d.get("category", "crypto"),
            updated_at=d.get("updated_at", int(time.time())),
        )


# ══════════════════════════════════════════════════════════════
# Scan Job
# ══════════════════════════════════════════════════════════════

@dataclass
class ScanJob:
    """Single scanning job in the queue."""
    job_id: str
    job_type: JobType
    symbol: str
    timeframe: str
    created_at: int
    priority: int = 5  # Higher = more important
    payload: Dict[str, Any] = field(default_factory=dict)
    status: JobStatus = "queued"
    started_at: Optional[int] = None
    finished_at: Optional[int] = None
    error: Optional[str] = None
    
    @staticmethod
    def make(
        job_type: JobType,
        symbol: str,
        timeframe: str,
        priority: int = 5,
        payload: Optional[Dict] = None
    ) -> "ScanJob":
        """Create a new scan job."""
        return ScanJob(
            job_id=f"{job_type}:{symbol}:{timeframe}:{int(time.time() * 1000)}",
            job_type=job_type,
            symbol=symbol,
            timeframe=timeframe,
            created_at=int(time.time()),
            priority=priority,
            payload=payload or {},
        )
    
    def to_dict(self) -> dict:
        return {
            "job_id": self.job_id,
            "job_type": self.job_type,
            "symbol": self.symbol,
            "timeframe": self.timeframe,
            "status": self.status,
            "priority": self.priority,
            "created_at": self.created_at,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "error": self.error,
            "payload": self.payload,
        }
    
    @staticmethod
    def from_dict(d: dict) -> "ScanJob":
        return ScanJob(
            job_id=d["job_id"],
            job_type=d["job_type"],
            symbol=d["symbol"],
            timeframe=d["timeframe"],
            created_at=d.get("created_at", int(time.time())),
            priority=d.get("priority", 5),
            payload=d.get("payload", {}),
            status=d.get("status", "queued"),
            started_at=d.get("started_at"),
            finished_at=d.get("finished_at"),
            error=d.get("error"),
        )


# ══════════════════════════════════════════════════════════════
# TA Snapshot
# ══════════════════════════════════════════════════════════════

@dataclass
class TASnapshot:
    """Technical analysis snapshot for an asset."""
    symbol: str
    timeframe: str
    created_at: int
    latest: bool
    ta_payload: Dict[str, Any]
    
    def to_dict(self) -> dict:
        return {
            "symbol": self.symbol,
            "timeframe": self.timeframe,
            "created_at": self.created_at,
            "latest": self.latest,
            "ta_payload": self.ta_payload,
        }


# ══════════════════════════════════════════════════════════════
# Prediction Snapshot
# ══════════════════════════════════════════════════════════════

@dataclass
class PredictionSnapshot:
    """Prediction snapshot for an asset."""
    symbol: str
    timeframe: str
    created_at: int
    latest: bool
    prediction_payload: Dict[str, Any]
    status: str = "pending"  # pending, resolved, expired
    score: float = 0.0
    publishable: bool = False
    
    def to_dict(self) -> dict:
        return {
            "symbol": self.symbol,
            "timeframe": self.timeframe,
            "created_at": self.created_at,
            "latest": self.latest,
            "prediction_payload": self.prediction_payload,
            "status": self.status,
            "score": self.score,
            "publishable": self.publishable,
        }


# ══════════════════════════════════════════════════════════════
# Constants
# ══════════════════════════════════════════════════════════════

# Supported timeframes for scanning
SCAN_TIMEFRAMES = ["4H", "1D"]

# Default limits
DEFAULT_ASSET_LIMIT = 100
MAX_ASSET_LIMIT = 500

# Job priorities
PRIORITY_HIGH = 10
PRIORITY_NORMAL = 5
PRIORITY_LOW = 1

# Publishability thresholds
MIN_CONFIDENCE_FOR_PUBLISH = 0.55
MIN_EXPECTED_RETURN_FOR_PUBLISH = 0.02
