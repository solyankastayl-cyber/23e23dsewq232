"""
PHASE 15.4 — Alpha Redundancy Engine
=====================================
Measures signal consensus density - how many signals say the same thing.

Purpose:
    Different from Correlation. Correlation measures similarity between
    two signals. Redundancy measures consensus across ALL signals.
    
    When 8 out of 10 signals say LONG, the system might feel highly
    confident. But this is often false confidence - the signals may
    be capturing the same market phenomenon from different angles.

Formula:
    redundancy_score = max(signals_long, signals_short) / total_signals
    diversity_score = 1 - redundancy_score

Redundancy States:
    - LOW: < 0.40 (signals are diverse)
    - MEDIUM: 0.40-0.65 (moderate consensus)
    - HIGH: > 0.65 (strong consensus = risk of overconfidence)

Key Principle:
    Redundancy NEVER blocks a signal.
    It only reduces confidence to prevent overweighting consensus.
"""

import os
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass, field
from enum import Enum
import random

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from modules.alpha_ecology.alpha_ecology_types import RedundancyState

# MongoDB
from pymongo import MongoClient, DESCENDING

MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.environ.get("DB_NAME", "ta_engine")


# ══════════════════════════════════════════════════════════════
# REDUNDANCY THRESHOLDS
# ══════════════════════════════════════════════════════════════

REDUNDANCY_THRESHOLDS = {
    # Score to state mapping
    "low_max": 0.40,
    "medium_max": 0.65,
    # Above medium_max = HIGH
}


REDUNDANCY_MODIFIERS = {
    RedundancyState.DIVERSIFIED: {
        "confidence_modifier": 1.0,
        "size_modifier": 1.0,
    },
    RedundancyState.NORMAL: {
        "confidence_modifier": 0.92,
        "size_modifier": 0.92,
    },
    RedundancyState.REDUNDANT: {
        "confidence_modifier": 0.80,
        "size_modifier": 0.80,
    },
}


# ══════════════════════════════════════════════════════════════
# SIGNAL DIRECTION ENUM
# ══════════════════════════════════════════════════════════════

class SignalDirection(str, Enum):
    LONG = "LONG"
    SHORT = "SHORT"
    NEUTRAL = "NEUTRAL"


# ══════════════════════════════════════════════════════════════
# REDUNDANCY RESULT CONTRACT
# ══════════════════════════════════════════════════════════════

@dataclass
class SignalVote:
    """Individual signal vote with direction."""
    signal_type: str
    direction: SignalDirection
    confidence: float
    source: str  # "ta", "exchange", "structure", etc.


@dataclass
class AlphaRedundancyResult:
    """
    Output from Alpha Redundancy Engine.
    
    Measures signal consensus and diversity.
    """
    symbol: str
    timestamp: datetime
    
    # Signal counts
    total_signals: int
    signals_long: int
    signals_short: int
    signals_neutral: int
    
    # Scores
    redundancy_score: float
    diversity_score: float
    redundancy_state: RedundancyState
    
    # Dominant direction
    dominant_direction: SignalDirection
    consensus_strength: float  # How strong the consensus is
    
    # Modifiers
    confidence_modifier: float
    size_modifier: float
    
    # Explainability
    reason: str
    signal_breakdown: Dict[str, str] = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        return {
            "symbol": self.symbol,
            "timestamp": self.timestamp.isoformat(),
            "total_signals": self.total_signals,
            "signals_long": self.signals_long,
            "signals_short": self.signals_short,
            "signals_neutral": self.signals_neutral,
            "redundancy_score": round(self.redundancy_score, 4),
            "diversity_score": round(self.diversity_score, 4),
            "redundancy_state": self.redundancy_state.value,
            "dominant_direction": self.dominant_direction.value,
            "consensus_strength": round(self.consensus_strength, 4),
            "confidence_modifier": round(self.confidence_modifier, 4),
            "size_modifier": round(self.size_modifier, 4),
            "reason": self.reason,
            "signal_breakdown": self.signal_breakdown,
        }


# ══════════════════════════════════════════════════════════════
# ALPHA REDUNDANCY ENGINE
# ══════════════════════════════════════════════════════════════

class AlphaRedundancyEngine:
    """
    Alpha Redundancy Engine - PHASE 15.4
    
    Measures signal consensus density to detect when many signals
    are saying the same thing, which can lead to overconfidence.
    
    Key Difference from Correlation:
        - Correlation: Signal A behaves like Signal B
        - Redundancy: Many signals agree on direction (LONG/SHORT)
    
    Key Principle:
        Redundancy NEVER blocks a signal.
        It only reduces confidence to prevent overweighting.
    """
    
    def __init__(self):
        self.client = MongoClient(MONGO_URL)
        self.db = self.client[DB_NAME]
    
    def analyze(self, symbol: str) -> AlphaRedundancyResult:
        """
        Analyze signal redundancy for a symbol.
        
        Args:
            symbol: Trading pair (BTC, ETH, SOL)
        
        Returns:
            AlphaRedundancyResult with redundancy state and modifiers
        """
        now = datetime.now(timezone.utc)
        
        # Collect signal directions
        signal_votes = self._collect_signal_votes(symbol)
        
        # Count directions
        total = len(signal_votes)
        long_count = sum(1 for s in signal_votes if s.direction == SignalDirection.LONG)
        short_count = sum(1 for s in signal_votes if s.direction == SignalDirection.SHORT)
        neutral_count = sum(1 for s in signal_votes if s.direction == SignalDirection.NEUTRAL)
        
        # Compute redundancy score
        if total > 0:
            redundancy_score = max(long_count, short_count) / total
        else:
            redundancy_score = 0.0
        
        # Diversity is inverse
        diversity_score = 1.0 - redundancy_score
        
        # Determine state
        redundancy_state = self._determine_redundancy_state(redundancy_score)
        
        # Dominant direction
        if long_count > short_count:
            dominant = SignalDirection.LONG
            consensus = long_count / total if total > 0 else 0
        elif short_count > long_count:
            dominant = SignalDirection.SHORT
            consensus = short_count / total if total > 0 else 0
        else:
            dominant = SignalDirection.NEUTRAL
            consensus = neutral_count / total if total > 0 else 0
        
        # Get modifiers
        modifiers = REDUNDANCY_MODIFIERS[redundancy_state]
        conf_mod = modifiers["confidence_modifier"]
        size_mod = modifiers["size_modifier"]
        
        # Fine-tune based on severity
        if redundancy_state == RedundancyState.REDUNDANT:
            severity = (redundancy_score - 0.65) / 0.35  # 0-1 within HIGH range
            conf_mod *= (1.0 - 0.15 * severity)  # Down to 0.68
            size_mod *= (1.0 - 0.15 * severity)
        
        # Build signal breakdown
        breakdown = {s.signal_type: s.direction.value for s in signal_votes}
        
        # Build reason
        reason = self._build_reason(redundancy_state, redundancy_score, dominant, total)
        
        return AlphaRedundancyResult(
            symbol=symbol,
            timestamp=now,
            total_signals=total,
            signals_long=long_count,
            signals_short=short_count,
            signals_neutral=neutral_count,
            redundancy_score=redundancy_score,
            diversity_score=diversity_score,
            redundancy_state=redundancy_state,
            dominant_direction=dominant,
            consensus_strength=consensus,
            confidence_modifier=max(0.5, conf_mod),  # Never below 0.5
            size_modifier=max(0.5, size_mod),
            reason=reason,
            signal_breakdown=breakdown,
        )
    
    def get_modifier_for_symbol(self, symbol: str) -> Dict[str, float]:
        """
        Get redundancy modifiers for Trading Product integration.
        """
        result = self.analyze(symbol)
        
        return {
            "redundancy_confidence_modifier": result.confidence_modifier,
            "redundancy_size_modifier": result.size_modifier,
            "redundancy_state": result.redundancy_state.value,
            "redundancy_score": result.redundancy_score,
            "diversity_score": result.diversity_score,
            "dominant_direction": result.dominant_direction.value,
        }
    
    # ═══════════════════════════════════════════════════════════════
    # SIGNAL COLLECTION
    # ═══════════════════════════════════════════════════════════════
    
    def _collect_signal_votes(self, symbol: str) -> List[SignalVote]:
        """
        Collect signal directions from all signal sources.
        
        Sources:
        - TA signals (trend, momentum, etc.)
        - Exchange signals (funding, OI)
        - Structure signals (support, resistance)
        """
        votes = []
        
        # TA Signals
        ta_votes = self._get_ta_signal_votes(symbol)
        votes.extend(ta_votes)
        
        # Exchange Signals
        exchange_votes = self._get_exchange_signal_votes(symbol)
        votes.extend(exchange_votes)
        
        # Structure Signals
        structure_votes = self._get_structure_signal_votes(symbol)
        votes.extend(structure_votes)
        
        return votes
    
    def _get_ta_signal_votes(self, symbol: str) -> List[SignalVote]:
        """Get TA signal directions."""
        from modules.alpha_ecology.alpha_decay_engine import SIGNAL_TYPES
        
        votes = []
        
        # Get latest hypothesis or use heuristics
        hypothesis = self.db.hypothesis_results.find_one(
            {"symbol": symbol},
            sort=[("timestamp", DESCENDING)]
        )
        
        for signal_type in SIGNAL_TYPES:
            # Try to get from stored data
            if hypothesis and "signals" in hypothesis:
                sig_data = hypothesis["signals"].get(signal_type, {})
                direction_str = sig_data.get("direction", "NEUTRAL")
                confidence = sig_data.get("confidence", 0.5)
            else:
                # Generate based on signal type characteristics
                direction_str, confidence = self._estimate_signal_direction(symbol, signal_type)
            
            direction = SignalDirection(direction_str)
            
            votes.append(SignalVote(
                signal_type=signal_type,
                direction=direction,
                confidence=confidence,
                source="ta",
            ))
        
        return votes
    
    def _get_exchange_signal_votes(self, symbol: str) -> List[SignalVote]:
        """Get exchange-based signal directions."""
        votes = []
        
        # Funding signal
        funding_direction = self._get_funding_direction(symbol)
        votes.append(SignalVote(
            signal_type="funding_sentiment",
            direction=funding_direction,
            confidence=0.6,
            source="exchange",
        ))
        
        # OI signal
        oi_direction = self._get_oi_direction(symbol)
        votes.append(SignalVote(
            signal_type="oi_sentiment",
            direction=oi_direction,
            confidence=0.55,
            source="exchange",
        ))
        
        # Liquidation signal
        liq_direction = self._get_liquidation_direction(symbol)
        votes.append(SignalVote(
            signal_type="liquidation_sentiment",
            direction=liq_direction,
            confidence=0.5,
            source="exchange",
        ))
        
        return votes
    
    def _get_structure_signal_votes(self, symbol: str) -> List[SignalVote]:
        """Get structure-based signal directions."""
        votes = []
        
        # Price structure
        structure_direction = self._get_price_structure_direction(symbol)
        votes.append(SignalVote(
            signal_type="price_structure",
            direction=structure_direction,
            confidence=0.6,
            source="structure",
        ))
        
        # Volume structure
        volume_direction = self._get_volume_structure_direction(symbol)
        votes.append(SignalVote(
            signal_type="volume_structure",
            direction=volume_direction,
            confidence=0.55,
            source="structure",
        ))
        
        return votes
    
    def _estimate_signal_direction(
        self,
        symbol: str,
        signal_type: str,
    ) -> Tuple[str, float]:
        """
        Estimate signal direction based on recent price action and signal type.
        """
        # Get recent candles
        candles = list(self.db.candles.find({
            "symbol": symbol,
            "timeframe": "1d"
        }).sort("timestamp", DESCENDING).limit(5))
        
        if len(candles) < 2:
            return "NEUTRAL", 0.5
        
        # Compute price change
        price_change = (candles[0].get("close", 0) - candles[-1].get("close", 0)) / candles[-1].get("close", 1)
        
        # Signal type bias
        trend_signals = ["trend_breakout", "trend_pullback", "momentum_continuation", "channel_breakout"]
        reversal_signals = ["mean_reversion", "support_bounce", "resistance_rejection", "double_bottom", "double_top"]
        
        if signal_type in trend_signals:
            # Trend signals follow price direction
            if price_change > 0.02:
                return "LONG", 0.65 + random.uniform(-0.1, 0.1)
            elif price_change < -0.02:
                return "SHORT", 0.65 + random.uniform(-0.1, 0.1)
            else:
                return "NEUTRAL", 0.5
        
        elif signal_type in reversal_signals:
            # Reversal signals counter price direction
            if price_change > 0.03:
                return "SHORT", 0.55 + random.uniform(-0.1, 0.1)
            elif price_change < -0.03:
                return "LONG", 0.55 + random.uniform(-0.1, 0.1)
            else:
                return "NEUTRAL", 0.5
        
        else:
            # Default: slightly biased by price
            if price_change > 0.01:
                return "LONG", 0.55
            elif price_change < -0.01:
                return "SHORT", 0.55
            return "NEUTRAL", 0.5
    
    def _get_funding_direction(self, symbol: str) -> SignalDirection:
        """Get direction based on funding rate."""
        funding = self.db.exchange_funding_context.find_one(
            {"symbol": symbol},
            sort=[("timestamp", DESCENDING)]
        )
        
        if not funding:
            return SignalDirection.NEUTRAL
        
        rate = funding.get("funding_rate", 0)
        
        # Positive funding = longs pay shorts = bearish sentiment
        if rate > 0.0003:
            return SignalDirection.SHORT
        elif rate < -0.0003:
            return SignalDirection.LONG
        
        return SignalDirection.NEUTRAL
    
    def _get_oi_direction(self, symbol: str) -> SignalDirection:
        """Get direction based on OI change."""
        oi_data = list(self.db.exchange_oi_snapshots.find({
            "symbol": symbol
        }).sort("timestamp", DESCENDING).limit(2))
        
        if len(oi_data) < 2:
            return SignalDirection.NEUTRAL
        
        oi_change = (oi_data[0].get("oi_usd", 0) - oi_data[1].get("oi_usd", 0)) / oi_data[1].get("oi_usd", 1)
        
        # Rising OI = new positions = trend continuation
        if oi_change > 0.03:
            return SignalDirection.LONG
        elif oi_change < -0.03:
            return SignalDirection.SHORT
        
        return SignalDirection.NEUTRAL
    
    def _get_liquidation_direction(self, symbol: str) -> SignalDirection:
        """Get direction based on liquidation imbalance."""
        now = datetime.now(timezone.utc)
        lookback = now - timedelta(hours=24)
        
        liqs = list(self.db.exchange_liquidation_events.find({
            "symbol": symbol,
            "timestamp": {"$gte": lookback}
        }))
        
        if not liqs:
            return SignalDirection.NEUTRAL
        
        long_liqs = sum(1 for l in liqs if l.get("side") == "LONG")
        short_liqs = sum(1 for l in liqs if l.get("side") == "SHORT")
        
        # More long liquidations = bearish
        if long_liqs > short_liqs * 1.5:
            return SignalDirection.SHORT
        elif short_liqs > long_liqs * 1.5:
            return SignalDirection.LONG
        
        return SignalDirection.NEUTRAL
    
    def _get_price_structure_direction(self, symbol: str) -> SignalDirection:
        """Get direction based on price structure."""
        candles = list(self.db.candles.find({
            "symbol": symbol,
            "timeframe": "1d"
        }).sort("timestamp", DESCENDING).limit(10))
        
        if len(candles) < 5:
            return SignalDirection.NEUTRAL
        
        # Simple: higher highs = bullish
        highs = [c.get("high", 0) for c in candles]
        recent_high = max(highs[:3])
        older_high = max(highs[3:])
        
        if recent_high > older_high * 1.02:
            return SignalDirection.LONG
        elif recent_high < older_high * 0.98:
            return SignalDirection.SHORT
        
        return SignalDirection.NEUTRAL
    
    def _get_volume_structure_direction(self, symbol: str) -> SignalDirection:
        """Get direction based on volume structure."""
        candles = list(self.db.candles.find({
            "symbol": symbol,
            "timeframe": "1d"
        }).sort("timestamp", DESCENDING).limit(10))
        
        if len(candles) < 5:
            return SignalDirection.NEUTRAL
        
        # Volume on up days vs down days
        up_volume = sum(c.get("volume", 0) for c in candles if c.get("close", 0) > c.get("open", 0))
        down_volume = sum(c.get("volume", 0) for c in candles if c.get("close", 0) < c.get("open", 0))
        
        if up_volume > down_volume * 1.3:
            return SignalDirection.LONG
        elif down_volume > up_volume * 1.3:
            return SignalDirection.SHORT
        
        return SignalDirection.NEUTRAL
    
    # ═══════════════════════════════════════════════════════════════
    # STATE DETERMINATION
    # ═══════════════════════════════════════════════════════════════
    
    def _determine_redundancy_state(self, score: float) -> RedundancyState:
        """Determine redundancy state from score."""
        if score < REDUNDANCY_THRESHOLDS["low_max"]:
            return RedundancyState.DIVERSIFIED
        elif score < REDUNDANCY_THRESHOLDS["medium_max"]:
            return RedundancyState.NORMAL
        else:
            return RedundancyState.REDUNDANT
    
    def _build_reason(
        self,
        state: RedundancyState,
        score: float,
        dominant: SignalDirection,
        total: int,
    ) -> str:
        """Build human-readable reason."""
        if state == RedundancyState.DIVERSIFIED:
            return f"low_redundancy_diverse_signals_{total}_total"
        elif state == RedundancyState.NORMAL:
            return f"moderate_consensus_{dominant.value}_{score:.0%}"
        else:
            return f"high_redundancy_{score:.0%}_signals_{dominant.value}"


# ═══════════════════════════════════════════════════════════════
# SINGLETON
# ═══════════════════════════════════════════════════════════════

_engine: Optional[AlphaRedundancyEngine] = None


def get_alpha_redundancy_engine() -> AlphaRedundancyEngine:
    """Get singleton engine instance."""
    global _engine
    if _engine is None:
        _engine = AlphaRedundancyEngine()
    return _engine
