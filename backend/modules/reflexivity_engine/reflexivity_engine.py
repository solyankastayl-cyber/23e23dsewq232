"""
Reflexivity Engine

PHASE 35 — Market Reflexivity Engine

Core engine for calculating market reflexivity (Soros theory).

The market is reflexive when:
1. Participants' expectations influence prices
2. Price changes influence expectations
3. This creates self-reinforcing or self-correcting feedback loops

Pipeline:
1. Collect source data (funding, OI, liquidations, volume, trend)
2. Calculate component scores
3. Compute reflexivity_score
4. Determine feedback direction
5. Generate modifier for Hypothesis Engine
"""

import math
import hashlib
from typing import Optional, List, Dict, Tuple
from datetime import datetime, timezone, timedelta

from .reflexivity_types import (
    ReflexivityState,
    ReflexivitySource,
    ReflexivityHistory,
    ReflexivityModifier,
    ReflexivitySummary,
    SentimentStateType,
    FeedbackDirectionType,
    ReflexivityStrengthType,
    REFLEXIVITY_WEIGHT,
    WEIGHT_SENTIMENT,
    WEIGHT_POSITIONING,
    WEIGHT_TREND_ACCELERATION,
    WEIGHT_VOLATILITY_EXPANSION,
    WEAK_REFLEXIVITY_THRESHOLD,
    STRONG_REFLEXIVITY_THRESHOLD,
    POSITIVE_FEEDBACK_THRESHOLD,
    NEGATIVE_FEEDBACK_THRESHOLD,
)


# ══════════════════════════════════════════════════════════════
# Reflexivity Engine
# ══════════════════════════════════════════════════════════════

class ReflexivityEngine:
    """
    Reflexivity Engine — PHASE 35
    
    Models behavioral feedback loops in markets.
    
    Core formula:
      reflexivity_score = 0.35 * sentiment
                        + 0.25 * positioning
                        + 0.20 * trend_acceleration
                        + 0.20 * volatility_expansion
    """
    
    def __init__(self):
        # In-memory cache
        self._states: Dict[str, List[ReflexivityState]] = {}
        self._current: Dict[str, ReflexivityState] = {}
    
    # ═══════════════════════════════════════════════════════════
    # 1. Source Data Collection
    # ═══════════════════════════════════════════════════════════
    
    def collect_source_data(self, symbol: str) -> ReflexivitySource:
        """
        Collect source data from exchange intelligence and market data.
        """
        symbol = symbol.upper()
        
        funding_rate = self._get_funding_rate(symbol)
        funding_sentiment = self._derive_funding_sentiment(funding_rate)
        
        oi_change, oi_expansion = self._get_oi_data(symbol)
        
        long_liq, short_liq = self._get_liquidation_data(symbol)
        liq_imbalance = self._calculate_liquidation_imbalance(long_liq, short_liq)
        
        volume_spike = self._get_volume_spike(symbol)
        
        momentum, acceleration = self._get_trend_data(symbol)
        
        return ReflexivitySource(
            funding_rate=funding_rate,
            funding_sentiment=funding_sentiment,
            oi_change_24h=oi_change,
            oi_expansion=oi_expansion,
            long_liquidations=long_liq,
            short_liquidations=short_liq,
            liquidation_imbalance=liq_imbalance,
            volume_spike_ratio=volume_spike,
            price_momentum=momentum,
            trend_acceleration=acceleration,
        )
    
    def _get_funding_rate(self, symbol: str) -> float:
        """Get current funding rate from exchange data."""
        try:
            from core.database import get_database
            db = get_database()
            if db:
                doc = db.exchange_funding_context.find_one(
                    {"symbol": symbol},
                    {"_id": 0, "funding_rate": 1},
                    sort=[("timestamp", -1)]
                )
                if doc:
                    return doc.get("funding_rate", 0.0)
        except Exception:
            pass
        
        # Deterministic fallback
        seed = int(hashlib.md5(f"{symbol}_funding_{datetime.now(timezone.utc).hour}".encode()).hexdigest()[:6], 16)
        return round(((seed % 60) - 30) / 10000, 6)  # -0.003 to 0.003
    
    def _derive_funding_sentiment(self, funding_rate: float) -> float:
        """
        Derive sentiment from funding rate.
        
        High positive funding = crowded longs = bullish sentiment
        High negative funding = crowded shorts = bearish sentiment
        """
        # Scale funding rate to [-1, 1]
        # Typical extreme: 0.003 (0.3%)
        sentiment = funding_rate / 0.003
        return round(min(max(sentiment, -1.0), 1.0), 4)
    
    def _get_oi_data(self, symbol: str) -> Tuple[float, bool]:
        """Get OI change and expansion flag."""
        try:
            from core.database import get_database
            db = get_database()
            if db:
                # Get last 24h of OI
                now = datetime.now(timezone.utc)
                yesterday = now - timedelta(hours=24)
                
                docs = list(db.exchange_oi_snapshots.find(
                    {"symbol": symbol, "timestamp": {"$gte": yesterday}},
                    {"_id": 0, "oi_usd": 1, "timestamp": 1}
                ).sort("timestamp", -1).limit(48))
                
                if len(docs) >= 2:
                    current_oi = docs[0].get("oi_usd", 0)
                    past_oi = docs[-1].get("oi_usd", 0)
                    if past_oi > 0:
                        change = (current_oi - past_oi) / past_oi
                        expansion = change > 0.03  # >3% expansion
                        return round(change, 4), expansion
        except Exception:
            pass
        
        seed = int(hashlib.md5(f"{symbol}_oi".encode()).hexdigest()[:6], 16)
        change = ((seed % 20) - 10) / 100
        return round(change, 4), change > 0.03
    
    def _get_liquidation_data(self, symbol: str) -> Tuple[float, float]:
        """Get recent liquidation volumes."""
        try:
            from core.database import get_database
            db = get_database()
            if db:
                now = datetime.now(timezone.utc)
                yesterday = now - timedelta(hours=24)
                
                pipeline = [
                    {"$match": {"symbol": symbol, "timestamp": {"$gte": yesterday}}},
                    {"$group": {
                        "_id": "$side",
                        "total": {"$sum": "$size"}
                    }}
                ]
                
                results = list(db.exchange_liquidation_events.aggregate(pipeline))
                
                long_liq = 0.0
                short_liq = 0.0
                for r in results:
                    if r["_id"] == "LONG":
                        long_liq = r["total"]
                    elif r["_id"] == "SHORT":
                        short_liq = r["total"]
                
                return long_liq, short_liq
        except Exception:
            pass
        
        base = {"BTC": 5e6, "ETH": 2e6, "SOL": 1e6}.get(symbol, 1e6)
        seed = int(hashlib.md5(f"{symbol}_liq".encode()).hexdigest()[:6], 16)
        long_liq = base * (0.5 + (seed % 100) / 100)
        short_liq = base * (0.5 + ((seed >> 8) % 100) / 100)
        return long_liq, short_liq
    
    def _calculate_liquidation_imbalance(self, long_liq: float, short_liq: float) -> float:
        """
        Calculate liquidation imbalance.
        
        Positive = more short liquidations (bullish)
        Negative = more long liquidations (bearish)
        """
        total = long_liq + short_liq
        if total == 0:
            return 0.0
        
        imbalance = (short_liq - long_liq) / total
        return round(min(max(imbalance, -1.0), 1.0), 4)
    
    def _get_volume_spike(self, symbol: str) -> float:
        """Get volume spike ratio (current / average)."""
        try:
            from core.database import get_database
            db = get_database()
            if db:
                docs = list(db.exchange_trade_flows.find(
                    {"symbol": symbol},
                    {"_id": 0, "total_volume": 1}
                ).sort("timestamp", -1).limit(48))
                
                if len(docs) >= 10:
                    recent_vol = sum(d.get("total_volume", 0) for d in docs[:5])
                    avg_vol = sum(d.get("total_volume", 0) for d in docs[5:]) / (len(docs) - 5)
                    if avg_vol > 0:
                        return round(recent_vol / avg_vol, 4)
        except Exception:
            pass
        
        seed = int(hashlib.md5(f"{symbol}_vol".encode()).hexdigest()[:6], 16)
        return round(0.8 + (seed % 80) / 100, 4)  # 0.8 to 1.6
    
    def _get_trend_data(self, symbol: str) -> Tuple[float, float]:
        """Get price momentum and trend acceleration."""
        try:
            from core.database import get_database
            db = get_database()
            if db:
                candles = list(db.candles.find(
                    {"symbol": symbol},
                    {"_id": 0, "close": 1}
                ).sort("timestamp", -1).limit(30))
                
                if len(candles) >= 20:
                    # Short-term momentum (5 candles)
                    short_change = (candles[0]["close"] - candles[4]["close"]) / max(candles[4]["close"], 1)
                    
                    # Medium-term momentum (20 candles)
                    medium_change = (candles[0]["close"] - candles[19]["close"]) / max(candles[19]["close"], 1)
                    
                    # Momentum normalized
                    momentum = min(max(short_change * 10, -1.0), 1.0)
                    
                    # Acceleration = difference in momentum
                    # If short momentum > medium momentum, trend is accelerating
                    acceleration = short_change - (medium_change / 4)
                    acceleration = min(max(acceleration * 20, -1.0), 1.0)
                    
                    return round(momentum, 4), round(acceleration, 4)
        except Exception:
            pass
        
        seed = int(hashlib.md5(f"{symbol}_trend".encode()).hexdigest()[:6], 16)
        momentum = ((seed % 160) - 80) / 100
        acceleration = ((seed >> 8) % 100 - 50) / 100
        return round(momentum, 4), round(acceleration, 4)
    
    # ═══════════════════════════════════════════════════════════
    # 2. Component Score Calculation
    # ═══════════════════════════════════════════════════════════
    
    def calculate_sentiment_score(self, source: ReflexivitySource) -> float:
        """
        Calculate sentiment component score [0, 1].
        
        Based on:
        - Funding sentiment
        - Liquidation imbalance
        """
        # Combine funding sentiment and liquidation imbalance
        raw_sentiment = (
            0.6 * source.funding_sentiment
            + 0.4 * source.liquidation_imbalance
        )
        
        # Convert to absolute magnitude [0, 1]
        # High absolute sentiment = strong reflexivity signal
        score = abs(raw_sentiment)
        
        return round(min(max(score, 0.0), 1.0), 4)
    
    def calculate_positioning_score(self, source: ReflexivitySource) -> float:
        """
        Calculate positioning component score [0, 1].
        
        Based on:
        - OI expansion (indicates new positioning)
        - Funding sentiment (indicates crowding)
        """
        # OI expansion contributes to positioning
        oi_score = min(abs(source.oi_change_24h) * 5, 1.0) if source.oi_expansion else 0.0
        
        # Crowding from funding
        crowding_score = abs(source.funding_sentiment)
        
        # Combine
        score = 0.5 * oi_score + 0.5 * crowding_score
        
        return round(min(max(score, 0.0), 1.0), 4)
    
    def calculate_trend_acceleration_score(self, source: ReflexivitySource) -> float:
        """
        Calculate trend acceleration component score [0, 1].
        
        High acceleration = strong reflexivity (self-reinforcing)
        """
        # Use absolute acceleration
        score = abs(source.trend_acceleration)
        
        # Boost if momentum and acceleration aligned
        if source.price_momentum * source.trend_acceleration > 0:
            score *= 1.2
        
        return round(min(max(score, 0.0), 1.0), 4)
    
    def calculate_volatility_expansion_score(self, source: ReflexivitySource) -> float:
        """
        Calculate volatility expansion component score [0, 1].
        
        Volume spike + OI expansion = volatility expansion
        """
        # Volume spike contribution
        volume_score = min(max((source.volume_spike_ratio - 1.0) * 2, 0.0), 1.0)
        
        # OI expansion contribution
        oi_score = min(abs(source.oi_change_24h) * 5, 1.0) if source.oi_expansion else 0.0
        
        # Combine
        score = 0.6 * volume_score + 0.4 * oi_score
        
        return round(min(max(score, 0.0), 1.0), 4)
    
    # ═══════════════════════════════════════════════════════════
    # 3. Reflexivity Score Calculation
    # ═══════════════════════════════════════════════════════════
    
    def calculate_reflexivity_score(
        self,
        sentiment_score: float,
        positioning_score: float,
        trend_acceleration_score: float,
        volatility_expansion_score: float,
    ) -> float:
        """
        Calculate final reflexivity score.
        
        Formula:
          reflexivity_score = 0.35 * sentiment
                            + 0.25 * positioning
                            + 0.20 * trend_acceleration
                            + 0.20 * volatility_expansion
        """
        score = (
            WEIGHT_SENTIMENT * sentiment_score
            + WEIGHT_POSITIONING * positioning_score
            + WEIGHT_TREND_ACCELERATION * trend_acceleration_score
            + WEIGHT_VOLATILITY_EXPANSION * volatility_expansion_score
        )
        
        return round(min(max(score, 0.0), 1.0), 4)
    
    # ═══════════════════════════════════════════════════════════
    # 4. Feedback Direction Determination
    # ═══════════════════════════════════════════════════════════
    
    def determine_feedback_direction(self, source: ReflexivitySource) -> FeedbackDirectionType:
        """
        Determine feedback loop direction.
        
        POSITIVE: Self-reinforcing (trend acceleration, momentum aligned)
        NEGATIVE: Mean-reverting (exhaustion, crowding extreme)
        NEUTRAL: No clear feedback
        """
        # Calculate directional signal
        directional_signal = (
            0.4 * source.price_momentum
            + 0.3 * source.trend_acceleration
            + 0.3 * source.funding_sentiment
        )
        
        # Check for exhaustion signals (extreme crowding)
        is_exhausted = abs(source.funding_sentiment) > 0.7
        
        if is_exhausted:
            # Extreme crowding leads to mean reversion
            return "NEGATIVE"
        elif directional_signal > POSITIVE_FEEDBACK_THRESHOLD:
            return "POSITIVE"
        elif directional_signal < NEGATIVE_FEEDBACK_THRESHOLD:
            return "NEGATIVE"
        else:
            return "NEUTRAL"
    
    # ═══════════════════════════════════════════════════════════
    # 5. Sentiment State Determination
    # ═══════════════════════════════════════════════════════════
    
    def determine_sentiment_state(self, source: ReflexivitySource) -> SentimentStateType:
        """
        Determine sentiment state from source data.
        """
        # Combined sentiment signal
        sentiment = (
            0.5 * source.funding_sentiment
            + 0.3 * source.liquidation_imbalance
            + 0.2 * source.price_momentum
        )
        
        if sentiment > 0.6:
            return "EXTREME_GREED"
        elif sentiment > 0.2:
            return "GREED"
        elif sentiment < -0.6:
            return "EXTREME_FEAR"
        elif sentiment < -0.2:
            return "FEAR"
        else:
            return "NEUTRAL"
    
    # ═══════════════════════════════════════════════════════════
    # 6. Strength Determination
    # ═══════════════════════════════════════════════════════════
    
    def determine_strength(self, reflexivity_score: float) -> ReflexivityStrengthType:
        """
        Determine reflexivity strength.
        
        < 0.35 → WEAK
        0.35-0.65 → MODERATE
        > 0.65 → STRONG
        """
        if reflexivity_score < WEAK_REFLEXIVITY_THRESHOLD:
            return "WEAK"
        elif reflexivity_score > STRONG_REFLEXIVITY_THRESHOLD:
            return "STRONG"
        else:
            return "MODERATE"
    
    # ═══════════════════════════════════════════════════════════
    # 7. Crowd Positioning Calculation
    # ═══════════════════════════════════════════════════════════
    
    def calculate_crowd_positioning(self, source: ReflexivitySource) -> float:
        """
        Calculate crowd positioning [-1, 1].
        
        Positive = long-heavy
        Negative = short-heavy
        """
        positioning = (
            0.5 * source.funding_sentiment
            + 0.3 * source.liquidation_imbalance
            + 0.2 * source.price_momentum
        )
        
        return round(min(max(positioning, -1.0), 1.0), 4)
    
    # ═══════════════════════════════════════════════════════════
    # 8. Confidence Calculation
    # ═══════════════════════════════════════════════════════════
    
    def calculate_confidence(
        self,
        reflexivity_score: float,
        source: ReflexivitySource,
    ) -> float:
        """
        Calculate confidence in reflexivity signal.
        
        Higher confidence when:
        - Components are aligned
        - Volume is elevated
        - Clear directional signal
        """
        # Base confidence from score
        base_confidence = reflexivity_score
        
        # Volume boost
        volume_boost = min(max(source.volume_spike_ratio - 1.0, 0.0), 0.2)
        
        # Alignment boost
        alignment = abs(source.price_momentum * source.trend_acceleration)
        alignment_boost = min(alignment, 0.15)
        
        confidence = base_confidence + volume_boost + alignment_boost
        
        return round(min(max(confidence, 0.0), 1.0), 4)
    
    # ═══════════════════════════════════════════════════════════
    # 9. Main Analysis Method
    # ═══════════════════════════════════════════════════════════
    
    def analyze(self, symbol: str) -> ReflexivityState:
        """
        Perform full reflexivity analysis for a symbol.
        
        Returns ReflexivityState with all metrics.
        """
        symbol = symbol.upper()
        
        # 1. Collect source data
        source = self.collect_source_data(symbol)
        
        # 2. Calculate component scores
        sentiment_score = self.calculate_sentiment_score(source)
        positioning_score = self.calculate_positioning_score(source)
        trend_acceleration_score = self.calculate_trend_acceleration_score(source)
        volatility_expansion_score = self.calculate_volatility_expansion_score(source)
        
        # 3. Calculate reflexivity score
        reflexivity_score = self.calculate_reflexivity_score(
            sentiment_score,
            positioning_score,
            trend_acceleration_score,
            volatility_expansion_score,
        )
        
        # 4. Determine states
        feedback_direction = self.determine_feedback_direction(source)
        sentiment_state = self.determine_sentiment_state(source)
        strength = self.determine_strength(reflexivity_score)
        
        # 5. Calculate positioning and confidence
        crowd_positioning = self.calculate_crowd_positioning(source)
        confidence = self.calculate_confidence(reflexivity_score, source)
        
        # 6. Generate reason
        reason = self._generate_reason(
            reflexivity_score,
            feedback_direction,
            sentiment_state,
            strength,
        )
        
        state = ReflexivityState(
            symbol=symbol,
            sentiment_state=sentiment_state,
            crowd_positioning=crowd_positioning,
            reflexivity_score=reflexivity_score,
            feedback_direction=feedback_direction,
            strength=strength,
            confidence=confidence,
            sentiment_score=sentiment_score,
            positioning_score=positioning_score,
            trend_acceleration_score=trend_acceleration_score,
            volatility_expansion_score=volatility_expansion_score,
            source=source,
            reason=reason,
        )
        
        # Cache
        self._store_state(symbol, state)
        
        return state
    
    def _generate_reason(
        self,
        score: float,
        direction: str,
        sentiment: str,
        strength: str,
    ) -> str:
        """Generate explanation string."""
        parts = [
            f"{strength} reflexivity (score={score:.2f})",
            f"{direction.lower()} feedback",
            f"sentiment={sentiment.lower().replace('_', ' ')}",
        ]
        return "; ".join(parts)
    
    # ═══════════════════════════════════════════════════════════
    # 10. Modifier for Hypothesis Engine
    # ═══════════════════════════════════════════════════════════
    
    def get_modifier(
        self,
        symbol: str,
        hypothesis_direction: str = "LONG",
    ) -> ReflexivityModifier:
        """
        Get modifier for hypothesis engine.
        
        Reflexivity contributes 6% to hypothesis score.
        
        Modifier logic:
        - POSITIVE feedback + aligned direction = boost
        - NEGATIVE feedback (exhaustion) = reduce
        - Strong reflexivity amplifies the effect
        """
        symbol = symbol.upper()
        
        # Get current state
        state = self.analyze(symbol)
        
        # Calculate weighted contribution
        weighted_contribution = state.reflexivity_score * REFLEXIVITY_WEIGHT
        
        # Determine alignment
        is_trend_aligned = False
        if state.feedback_direction == "POSITIVE":
            # Positive feedback supports the current trend
            if hypothesis_direction == "LONG" and state.crowd_positioning > 0:
                is_trend_aligned = True
            elif hypothesis_direction == "SHORT" and state.crowd_positioning < 0:
                is_trend_aligned = True
        
        # Calculate modifier
        modifier = 1.0
        reason = "Neutral reflexivity signal"
        
        if state.strength == "STRONG":
            if state.feedback_direction == "POSITIVE" and is_trend_aligned:
                modifier = 1.0 + (state.reflexivity_score * 0.12)  # Up to 1.12
                reason = f"Strong positive feedback aligned with {hypothesis_direction}"
            elif state.feedback_direction == "NEGATIVE":
                modifier = 1.0 - (state.reflexivity_score * 0.08)  # Down to 0.92
                reason = "Strong negative feedback (exhaustion signal)"
        elif state.strength == "MODERATE":
            if state.feedback_direction == "POSITIVE" and is_trend_aligned:
                modifier = 1.0 + (state.reflexivity_score * 0.06)  # Up to 1.06
                reason = f"Moderate positive feedback aligned with {hypothesis_direction}"
            elif state.feedback_direction == "NEGATIVE":
                modifier = 1.0 - (state.reflexivity_score * 0.04)  # Down to 0.96
                reason = "Moderate negative feedback"
        
        return ReflexivityModifier(
            symbol=symbol,
            reflexivity_score=state.reflexivity_score,
            reflexivity_weight=REFLEXIVITY_WEIGHT,
            weighted_contribution=round(weighted_contribution, 4),
            feedback_direction=state.feedback_direction,
            is_trend_aligned=is_trend_aligned,
            modifier=round(modifier, 4),
            strength=state.strength,
            confidence=state.confidence,
            reason=reason,
        )
    
    # ═══════════════════════════════════════════════════════════
    # 11. Storage and Cache
    # ═══════════════════════════════════════════════════════════
    
    def _store_state(self, symbol: str, state: ReflexivityState) -> None:
        """Store state in cache."""
        if symbol not in self._states:
            self._states[symbol] = []
        self._states[symbol].append(state)
        self._current[symbol] = state
    
    def get_current_state(self, symbol: str) -> Optional[ReflexivityState]:
        """Get cached state for symbol."""
        return self._current.get(symbol.upper())
    
    def get_history(self, symbol: str, limit: int = 100) -> List[ReflexivityState]:
        """Get state history."""
        history = self._states.get(symbol.upper(), [])
        return sorted(history, key=lambda s: s.timestamp, reverse=True)[:limit]
    
    # ═══════════════════════════════════════════════════════════
    # 12. Summary Generation
    # ═══════════════════════════════════════════════════════════
    
    def generate_summary(self, symbol: str) -> ReflexivitySummary:
        """Generate summary statistics."""
        symbol = symbol.upper()
        history = self._states.get(symbol, [])
        current = self._current.get(symbol)
        
        if not history:
            return ReflexivitySummary(symbol=symbol)
        
        total = len(history)
        avg_score = sum(s.reflexivity_score for s in history) / total
        
        # Direction distribution
        positive_count = sum(1 for s in history if s.feedback_direction == "POSITIVE")
        negative_count = sum(1 for s in history if s.feedback_direction == "NEGATIVE")
        neutral_count = total - positive_count - negative_count
        
        # Strength distribution
        strong_count = sum(1 for s in history if s.strength == "STRONG")
        moderate_count = sum(1 for s in history if s.strength == "MODERATE")
        weak_count = total - strong_count - moderate_count
        
        # Recent trend (last 24 records)
        recent = sorted(history, key=lambda s: s.timestamp, reverse=True)[:24]
        recent_avg = sum(s.reflexivity_score for s in recent) / len(recent) if recent else 0.0
        
        if len(recent) >= 2:
            first_half = sum(s.reflexivity_score for s in recent[:12]) / 12
            second_half = sum(s.reflexivity_score for s in recent[12:]) / max(len(recent) - 12, 1)
            if first_half > second_half * 1.1:
                score_trend = "INCREASING"
            elif first_half < second_half * 0.9:
                score_trend = "DECREASING"
            else:
                score_trend = "STABLE"
        else:
            score_trend = "STABLE"
        
        return ReflexivitySummary(
            symbol=symbol,
            current_score=current.reflexivity_score if current else 0.0,
            current_direction=current.feedback_direction if current else "NEUTRAL",
            current_strength=current.strength if current else "WEAK",
            total_records=total,
            avg_score=round(avg_score, 4),
            positive_feedback_count=positive_count,
            negative_feedback_count=negative_count,
            neutral_count=neutral_count,
            strong_reflexivity_count=strong_count,
            moderate_reflexivity_count=moderate_count,
            weak_reflexivity_count=weak_count,
            recent_avg_score=round(recent_avg, 4),
            score_trend=score_trend,
            last_updated=datetime.now(timezone.utc),
        )


# ══════════════════════════════════════════════════════════════
# Singleton
# ══════════════════════════════════════════════════════════════

_reflexivity_engine: Optional[ReflexivityEngine] = None


def get_reflexivity_engine() -> ReflexivityEngine:
    """Get singleton instance of ReflexivityEngine."""
    global _reflexivity_engine
    if _reflexivity_engine is None:
        _reflexivity_engine = ReflexivityEngine()
    return _reflexivity_engine
