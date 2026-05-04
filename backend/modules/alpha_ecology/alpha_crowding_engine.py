"""
PHASE 15.2 — Alpha Crowding Engine
===================================
Detects when too many participants are in the same signal.

Purpose:
    Crowding is one of the main reasons signals stop working.
    When everyone is on the same side, the risk of reversal increases.

Data Sources:
    - Funding rates (exchange_funding_context)
    - Open Interest (exchange_oi_snapshots)
    - Liquidations (exchange_liquidation_events)
    - Volume (exchange_trade_flows)

Crowding Score Formula:
    crowding_score = 0.35*funding + 0.25*oi + 0.25*liquidations + 0.15*volume

States:
    - LOW_CROWDING: < 0.30 (safe to trade normally)
    - MEDIUM_CROWDING: 0.30-0.50 (slight caution)
    - HIGH_CROWDING: 0.50-0.70 (reduce size)
    - EXTREME_CROWDING: > 0.70 (minimal exposure)

Key Principle:
    Crowding NEVER blocks a signal.
    It only reduces risk exposure.
"""

import os
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timezone, timedelta
import math

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from modules.alpha_ecology.alpha_ecology_types import (
    CrowdingState,
)

# MongoDB
from pymongo import MongoClient, DESCENDING

MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.environ.get("DB_NAME", "ta_engine")


# ══════════════════════════════════════════════════════════════
# CROWDING THRESHOLDS
# ══════════════════════════════════════════════════════════════

CROWDING_THRESHOLDS = {
    # Score to state mapping
    "low_max": 0.30,
    "medium_max": 0.50,
    "high_max": 0.70,
    # Above high_max = EXTREME
    
    # Funding thresholds
    "funding_extreme": 0.0005,  # 0.05% = extreme
    "funding_crowded": 0.0002,  # 0.02% = crowded
    
    # OI thresholds (change ratio)
    "oi_high_change": 0.05,    # 5% OI change = significant
    "oi_extreme_change": 0.10,  # 10% OI change = extreme
    
    # Liquidation thresholds
    "liq_high_count": 100,
    "liq_extreme_count": 500,
    
    # Volume spike threshold
    "volume_spike_mult": 2.0,   # 2x average = spike
    "volume_extreme_mult": 3.5, # 3.5x = extreme
    
    # Lookback periods
    "funding_hours": 24,
    "oi_hours": 24,
    "liq_hours": 12,
    "volume_hours": 24,
}


CROWDING_WEIGHTS = {
    "funding": 0.35,
    "oi": 0.25,
    "liquidation": 0.25,
    "volume": 0.15,
}


CROWDING_MODIFIERS = {
    CrowdingState.LOW_CROWDING: {
        "confidence_modifier": 1.0,
        "size_modifier": 1.0,
    },
    CrowdingState.MEDIUM_CROWDING: {
        "confidence_modifier": 0.95,
        "size_modifier": 0.95,
    },
    CrowdingState.HIGH_CROWDING: {
        "confidence_modifier": 0.85,
        "size_modifier": 0.85,
    },
    CrowdingState.EXTREME_CROWDING: {
        "confidence_modifier": 0.70,
        "size_modifier": 0.70,
    },
}


# ══════════════════════════════════════════════════════════════
# CROWDING RESULT CONTRACT
# ══════════════════════════════════════════════════════════════

from dataclasses import dataclass, field
from typing import Any


@dataclass
class AlphaCrowdingResult:
    """
    Output from Alpha Crowding Engine.
    
    Measures market crowding level based on exchange data.
    """
    symbol: str
    timestamp: datetime
    
    # Component scores (0.0 - 1.0)
    funding_extreme: float
    oi_pressure: float
    liquidation_pressure: float
    volume_spike: float
    
    # Aggregated
    crowding_score: float
    crowding_state: CrowdingState
    
    # Modifiers
    confidence_modifier: float
    size_modifier: float
    
    # Explainability
    reason: str
    drivers: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        return {
            "symbol": self.symbol,
            "timestamp": self.timestamp.isoformat(),
            "funding_extreme": round(self.funding_extreme, 4),
            "oi_pressure": round(self.oi_pressure, 4),
            "liquidation_pressure": round(self.liquidation_pressure, 4),
            "volume_spike": round(self.volume_spike, 4),
            "crowding_score": round(self.crowding_score, 4),
            "crowding_state": self.crowding_state.value,
            "confidence_modifier": round(self.confidence_modifier, 4),
            "size_modifier": round(self.size_modifier, 4),
            "reason": self.reason,
            "drivers": self.drivers,
        }


# ══════════════════════════════════════════════════════════════
# ALPHA CROWDING ENGINE
# ══════════════════════════════════════════════════════════════

class AlphaCrowdingEngine:
    """
    Alpha Crowding Engine - PHASE 15.2
    
    Detects market crowding using exchange data:
    - Funding rates
    - Open Interest
    - Liquidations
    - Volume
    
    Key Principle:
        Crowding NEVER blocks a signal.
        It only reduces risk exposure.
    """
    
    def __init__(self):
        self.client = MongoClient(MONGO_URL)
        self.db = self.client[DB_NAME]
    
    def analyze(self, symbol: str) -> AlphaCrowdingResult:
        """
        Analyze crowding for a symbol.
        
        Args:
            symbol: Trading pair (BTC, ETH, SOL)
        
        Returns:
            AlphaCrowdingResult with crowding state and modifiers
        """
        now = datetime.now(timezone.utc)
        
        # Compute component scores
        funding_score = self._compute_funding_extreme(symbol)
        oi_score = self._compute_oi_pressure(symbol)
        liq_score = self._compute_liquidation_pressure(symbol)
        volume_score = self._compute_volume_spike(symbol)
        
        # Weighted crowding score
        crowding_score = (
            CROWDING_WEIGHTS["funding"] * funding_score
            + CROWDING_WEIGHTS["oi"] * oi_score
            + CROWDING_WEIGHTS["liquidation"] * liq_score
            + CROWDING_WEIGHTS["volume"] * volume_score
        )
        
        # Determine state
        crowding_state = self._determine_crowding_state(crowding_score)
        
        # Get modifiers
        modifiers = CROWDING_MODIFIERS[crowding_state]
        conf_mod = modifiers["confidence_modifier"]
        size_mod = modifiers["size_modifier"]
        
        # Fine-tune modifiers based on severity
        if crowding_state == CrowdingState.EXTREME_CROWDING:
            # More extreme = lower modifiers
            severity = (crowding_score - 0.70) / 0.30  # 0-1 within extreme
            conf_mod *= (1.0 - 0.15 * severity)  # Down to 0.595
            size_mod *= (1.0 - 0.20 * severity)  # Down to 0.56
        
        # Build reason
        reason = self._build_reason(
            crowding_state, funding_score, oi_score, liq_score, volume_score
        )
        
        # Build drivers
        drivers = {
            "funding_raw": funding_score,
            "oi_raw": oi_score,
            "liquidation_raw": liq_score,
            "volume_raw": volume_score,
            "weights": CROWDING_WEIGHTS,
            "dominant_factor": self._get_dominant_factor(
                funding_score, oi_score, liq_score, volume_score
            ),
        }
        
        return AlphaCrowdingResult(
            symbol=symbol,
            timestamp=now,
            funding_extreme=funding_score,
            oi_pressure=oi_score,
            liquidation_pressure=liq_score,
            volume_spike=volume_score,
            crowding_score=crowding_score,
            crowding_state=crowding_state,
            confidence_modifier=max(0.5, conf_mod),  # Never below 0.5
            size_modifier=max(0.5, size_mod),        # Never below 0.5
            reason=reason,
            drivers=drivers,
        )
    
    def get_modifier_for_symbol(self, symbol: str) -> Dict[str, float]:
        """
        Get crowding modifiers for integration with Trading Decision.
        
        Returns dict with confidence and size modifiers.
        """
        result = self.analyze(symbol)
        
        return {
            "crowding_confidence_modifier": result.confidence_modifier,
            "crowding_size_modifier": result.size_modifier,
            "crowding_state": result.crowding_state.value,
            "crowding_score": result.crowding_score,
        }
    
    # ═══════════════════════════════════════════════════════════════
    # COMPONENT SCORE COMPUTATION
    # ═══════════════════════════════════════════════════════════════
    
    def _compute_funding_extreme(self, symbol: str) -> float:
        """
        Compute funding extreme score (0.0 - 1.0).
        
        Higher funding = more crowded in one direction.
        """
        now = datetime.now(timezone.utc)
        lookback = now - timedelta(hours=CROWDING_THRESHOLDS["funding_hours"])
        
        # Get recent funding data
        funding_data = list(self.db.exchange_funding_context.find({
            "symbol": symbol,
            "timestamp": {"$gte": lookback}
        }).sort("timestamp", DESCENDING).limit(24))
        
        if not funding_data:
            return 0.0
        
        # Get average absolute funding rate
        funding_rates = [abs(f.get("funding_rate", 0)) for f in funding_data]
        avg_funding = sum(funding_rates) / len(funding_rates)
        
        # Get max funding
        max_funding = max(funding_rates) if funding_rates else 0
        
        # Normalize to 0-1 score
        # Extreme threshold = 1.0, crowded = 0.5, below = proportional
        extreme_thresh = CROWDING_THRESHOLDS["funding_extreme"]
        crowded_thresh = CROWDING_THRESHOLDS["funding_crowded"]
        
        if avg_funding >= extreme_thresh:
            score = 0.8 + 0.2 * min((avg_funding - extreme_thresh) / extreme_thresh, 1.0)
        elif avg_funding >= crowded_thresh:
            ratio = (avg_funding - crowded_thresh) / (extreme_thresh - crowded_thresh)
            score = 0.4 + 0.4 * ratio
        else:
            score = (avg_funding / crowded_thresh) * 0.4
        
        # Boost for max spike
        if max_funding >= extreme_thresh * 1.5:
            score = min(1.0, score + 0.15)
        
        return min(1.0, score)
    
    def _compute_oi_pressure(self, symbol: str) -> float:
        """
        Compute OI pressure score (0.0 - 1.0).
        
        Rising OI + stagnant price = overcrowding.
        Rising OI + rising price = healthy trend.
        """
        now = datetime.now(timezone.utc)
        lookback = now - timedelta(hours=CROWDING_THRESHOLDS["oi_hours"])
        
        # Get OI data
        oi_data = list(self.db.exchange_oi_snapshots.find({
            "symbol": symbol,
            "timestamp": {"$gte": lookback}
        }).sort("timestamp", DESCENDING).limit(24))
        
        if len(oi_data) < 2:
            return 0.0
        
        # Get OI change
        latest_oi = oi_data[0].get("oi_usd", 0)
        oldest_oi = oi_data[-1].get("oi_usd", 1)
        oi_change = (latest_oi - oldest_oi) / oldest_oi if oldest_oi > 0 else 0
        
        # Get price change from candles
        candles = list(self.db.candles.find({
            "symbol": symbol,
            "timeframe": "1d"
        }).sort("timestamp", DESCENDING).limit(2))
        
        if len(candles) >= 2:
            price_change = abs(candles[0].get("close", 0) - candles[1].get("close", 0))
            price_change_pct = price_change / candles[1].get("close", 1) if candles[1].get("close", 0) > 0 else 0
        else:
            price_change_pct = 0.02  # Default assumption
        
        # OI pressure = OI rising faster than price would justify
        # High OI change + low price change = crowding
        oi_abs = abs(oi_change)
        
        if oi_abs < 0.01:
            # Very low OI change = no crowding signal
            return 0.1
        
        # OI to price ratio (higher = more crowding)
        if price_change_pct > 0.001:
            oi_price_ratio = oi_abs / price_change_pct
        else:
            oi_price_ratio = oi_abs * 100  # Price stable, OI moving = crowding
        
        # Normalize
        if oi_abs >= CROWDING_THRESHOLDS["oi_extreme_change"]:
            base_score = 0.7
        elif oi_abs >= CROWDING_THRESHOLDS["oi_high_change"]:
            ratio = (oi_abs - CROWDING_THRESHOLDS["oi_high_change"]) / \
                    (CROWDING_THRESHOLDS["oi_extreme_change"] - CROWDING_THRESHOLDS["oi_high_change"])
            base_score = 0.4 + 0.3 * ratio
        else:
            base_score = (oi_abs / CROWDING_THRESHOLDS["oi_high_change"]) * 0.4
        
        # Adjust for OI/price divergence
        if oi_price_ratio > 5:
            base_score = min(1.0, base_score + 0.2)
        elif oi_price_ratio > 2:
            base_score = min(1.0, base_score + 0.1)
        
        return min(1.0, base_score)
    
    def _compute_liquidation_pressure(self, symbol: str) -> float:
        """
        Compute liquidation pressure score (0.0 - 1.0).
        
        Growing liquidation clusters = crowding unwinding.
        """
        now = datetime.now(timezone.utc)
        lookback = now - timedelta(hours=CROWDING_THRESHOLDS["liq_hours"])
        
        # Get liquidation events
        liq_events = list(self.db.exchange_liquidation_events.find({
            "symbol": symbol,
            "timestamp": {"$gte": lookback}
        }))
        
        if not liq_events:
            return 0.0
        
        liq_count = len(liq_events)
        total_size = sum(e.get("size", 0) for e in liq_events)
        
        # Count by side
        long_liqs = sum(1 for e in liq_events if e.get("side") == "LONG")
        short_liqs = sum(1 for e in liq_events if e.get("side") == "SHORT")
        
        # Imbalance = one-sided liquidations = crowding on that side
        if liq_count > 0:
            imbalance = abs(long_liqs - short_liqs) / liq_count
        else:
            imbalance = 0
        
        # Normalize count
        extreme_count = CROWDING_THRESHOLDS["liq_extreme_count"]
        high_count = CROWDING_THRESHOLDS["liq_high_count"]
        
        if liq_count >= extreme_count:
            count_score = 0.8 + 0.2 * min((liq_count - extreme_count) / extreme_count, 1.0)
        elif liq_count >= high_count:
            ratio = (liq_count - high_count) / (extreme_count - high_count)
            count_score = 0.4 + 0.4 * ratio
        else:
            count_score = (liq_count / high_count) * 0.4
        
        # Combine count score with imbalance
        # High imbalance + high count = very crowded
        final_score = count_score * 0.7 + imbalance * 0.3
        
        return min(1.0, final_score)
    
    def _compute_volume_spike(self, symbol: str) -> float:
        """
        Compute volume spike score (0.0 - 1.0).
        
        Volume >> rolling average = retail participation spike.
        """
        now = datetime.now(timezone.utc)
        lookback = now - timedelta(hours=CROWDING_THRESHOLDS["volume_hours"])
        
        # Get recent trade flows
        flows = list(self.db.exchange_trade_flows.find({
            "symbol": symbol,
            "timestamp": {"$gte": lookback}
        }).sort("timestamp", DESCENDING).limit(24))
        
        if len(flows) < 2:
            return 0.0
        
        # Recent volume (last 6 hours)
        recent_flows = flows[:6] if len(flows) >= 6 else flows[:len(flows)//2]
        recent_vol = sum(f.get("total_volume", 0) for f in recent_flows)
        
        # Historical average (rest)
        hist_flows = flows[6:] if len(flows) >= 6 else flows[len(flows)//2:]
        hist_vol = sum(f.get("total_volume", 0) for f in hist_flows)
        
        if hist_vol == 0:
            return 0.0
        
        # Normalize to same time period
        if len(hist_flows) > 0:
            hist_avg = hist_vol / len(hist_flows) * len(recent_flows)
        else:
            hist_avg = hist_vol
        
        # Volume ratio
        vol_ratio = recent_vol / hist_avg if hist_avg > 0 else 1.0
        
        # Normalize to score
        spike_thresh = CROWDING_THRESHOLDS["volume_spike_mult"]
        extreme_thresh = CROWDING_THRESHOLDS["volume_extreme_mult"]
        
        if vol_ratio >= extreme_thresh:
            score = 0.8 + 0.2 * min((vol_ratio - extreme_thresh) / extreme_thresh, 1.0)
        elif vol_ratio >= spike_thresh:
            ratio = (vol_ratio - spike_thresh) / (extreme_thresh - spike_thresh)
            score = 0.4 + 0.4 * ratio
        else:
            score = (vol_ratio / spike_thresh) * 0.4
        
        return min(1.0, max(0.0, score))
    
    # ═══════════════════════════════════════════════════════════════
    # STATE DETERMINATION
    # ═══════════════════════════════════════════════════════════════
    
    def _determine_crowding_state(self, score: float) -> CrowdingState:
        """Determine crowding state from score."""
        if score < CROWDING_THRESHOLDS["low_max"]:
            return CrowdingState.LOW_CROWDING
        elif score < CROWDING_THRESHOLDS["medium_max"]:
            return CrowdingState.MEDIUM_CROWDING
        elif score < CROWDING_THRESHOLDS["high_max"]:
            return CrowdingState.HIGH_CROWDING
        else:
            return CrowdingState.EXTREME_CROWDING
    
    def _get_dominant_factor(
        self,
        funding: float,
        oi: float,
        liq: float,
        volume: float,
    ) -> str:
        """Get the dominant crowding factor."""
        factors = {
            "funding": funding,
            "oi": oi,
            "liquidation": liq,
            "volume": volume,
        }
        return max(factors, key=factors.get)
    
    def _build_reason(
        self,
        state: CrowdingState,
        funding: float,
        oi: float,
        liq: float,
        volume: float,
    ) -> str:
        """Build human-readable reason."""
        dominant = self._get_dominant_factor(funding, oi, liq, volume)
        
        if state == CrowdingState.LOW_CROWDING:
            return "low_crowding_safe_to_trade"
        elif state == CrowdingState.MEDIUM_CROWDING:
            return f"medium_crowding_driven_by_{dominant}"
        elif state == CrowdingState.HIGH_CROWDING:
            return f"high_crowding_{dominant}_elevated"
        else:
            return f"extreme_crowding_{dominant}_critical"


# ═══════════════════════════════════════════════════════════════
# SINGLETON
# ═══════════════════════════════════════════════════════════════

_engine: Optional[AlphaCrowdingEngine] = None


def get_alpha_crowding_engine() -> AlphaCrowdingEngine:
    """Get singleton engine instance."""
    global _engine
    if _engine is None:
        _engine = AlphaCrowdingEngine()
    return _engine
