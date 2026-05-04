"""
PHASE 7 - Cross Asset Signals
===============================
Generates trading signals based on cross-asset correlation analysis.

Signal Types:
- MACRO_DIVERGENCE: Macro asset moved, crypto hasn't followed yet
- CORRELATION_BREAK: Correlation breaking from historical norm
- LEAD_SIGNAL: Leading asset suggests direction for follower
- REGIME_SHIFT: Market regime changing, impacts positioning
- DXY_SIGNAL: Dollar strength/weakness signal for crypto
- EQUITY_SIGNAL: Equity markets signal for crypto direction
"""

import uuid
from typing import Dict, List, Optional
from datetime import datetime, timezone, timedelta

from .correlation_types import (
    CrossAssetSignal, CorrelationValue, LeadLagResult, RegimeState,
    CorrelationRegime, AssetPair, AssetClass
)


class CrossAssetSignalGenerator:
    """
    Generates trading signals from cross-asset correlation analysis.
    """
    
    def __init__(self):
        self.signal_validity_hours = 4  # Signals valid for N hours
        self.min_confidence_threshold = 0.5
        
        # Signal generation rules
        self.rules = {
            "dxy_inverse": True,  # DXY up = crypto down
            "spx_positive": True,  # SPX up = crypto up
            "gold_mixed": True,    # Gold can be positive or inverse
        }
    
    def generate_signal_id(self) -> str:
        """Generate unique signal ID."""
        return f"sig_{uuid.uuid4().hex[:12]}"
    
    def generate_macro_divergence_signal(
        self,
        macro_asset: str,
        macro_return: float,
        crypto_asset: str,
        crypto_return: float,
        correlation: float,
        historical_correlation: float
    ) -> Optional[CrossAssetSignal]:
        """
        Generate signal when macro asset moved but crypto hasn't followed.
        
        Example: SPX up 2% today, BTC flat -> expect BTC catch-up
        """
        now = datetime.now(timezone.utc)
        
        # Check if there's meaningful divergence
        expected_crypto_move = macro_return * correlation
        actual_divergence = expected_crypto_move - crypto_return
        
        # Need at least 0.5% divergence to signal
        if abs(actual_divergence) < 0.005:
            return None
        
        # Determine direction
        if self.rules.get("dxy_inverse") and macro_asset == "DXY":
            # DXY inverse relationship
            if macro_return > 0 and crypto_return >= 0:
                direction = "BEARISH"
                description = f"DXY strengthened {macro_return*100:.1f}%, {crypto_asset} hasn't sold off yet"
            elif macro_return < 0 and crypto_return <= 0:
                direction = "BULLISH"
                description = f"DXY weakened {abs(macro_return)*100:.1f}%, {crypto_asset} hasn't rallied yet"
            else:
                return None
        else:
            # Positive correlation (SPX, NASDAQ)
            if macro_return > 0 and crypto_return < macro_return * 0.5:
                direction = "BULLISH"
                description = f"{macro_asset} up {macro_return*100:.1f}%, {crypto_asset} lagging - expect catch-up"
            elif macro_return < 0 and crypto_return > macro_return * 0.5:
                direction = "BEARISH"
                description = f"{macro_asset} down {abs(macro_return)*100:.1f}%, {crypto_asset} lagging - expect selloff"
            else:
                return None
        
        # Calculate strength based on divergence size
        strength = min(1.0, abs(actual_divergence) / 0.03)  # 3% divergence = max strength
        
        # Calculate confidence
        confidence = min(0.9, abs(correlation) * 0.5 + strength * 0.3 + 0.2)
        
        return CrossAssetSignal(
            signal_id=self.generate_signal_id(),
            signal_type="MACRO_DIVERGENCE",
            trigger_asset=macro_asset,
            target_asset=crypto_asset,
            direction=direction,
            strength=strength,
            description=description,
            generated_at=now,
            valid_until=now + timedelta(hours=self.signal_validity_hours)
        )
    
    def generate_lead_signal(
        self,
        lead_lag_result: LeadLagResult,
        leader_return: float,
        min_confidence: float = 0.6
    ) -> Optional[CrossAssetSignal]:
        """
        Generate signal based on lead/lag relationship.
        
        Example: SPX leads BTC by 2 candles, SPX just moved up -> expect BTC up
        """
        if lead_lag_result.confidence < min_confidence:
            return None
        
        if lead_lag_result.lag_candles == 0:
            return None  # No lead/lag detected
        
        now = datetime.now(timezone.utc)
        
        # Determine expected move direction
        if lead_lag_result.lag_correlation > 0:
            # Positive correlation: follower moves same direction
            if leader_return > 0:
                direction = "BULLISH"
            else:
                direction = "BEARISH"
        else:
            # Negative correlation: follower moves opposite
            if leader_return > 0:
                direction = "BEARISH"
            else:
                direction = "BULLISH"
        
        # Special case for DXY (inverse relationship)
        if lead_lag_result.leader == "DXY":
            direction = "BEARISH" if leader_return > 0 else "BULLISH"
        
        # Calculate signal strength
        strength = min(1.0, abs(leader_return) * 20)  # 5% move = max strength
        
        # Adjust for lag confidence
        strength *= lead_lag_result.confidence
        
        description = (
            f"{lead_lag_result.leader} moved {leader_return*100:.2f}%. "
            f"Leads {lead_lag_result.follower} by {lead_lag_result.lag_candles} candles. "
            f"Expect {direction.lower()} move."
        )
        
        return CrossAssetSignal(
            signal_id=self.generate_signal_id(),
            signal_type="LEAD_SIGNAL",
            trigger_asset=lead_lag_result.leader,
            target_asset=lead_lag_result.follower,
            direction=direction,
            strength=strength,
            description=description,
            lead_lag_basis=lead_lag_result,
            generated_at=now,
            valid_until=now + timedelta(hours=lead_lag_result.lag_candles)  # Valid for lag period
        )
    
    def generate_correlation_break_signal(
        self,
        pair: AssetPair,
        current_corr: float,
        historical_corr: float,
        historical_std: float
    ) -> Optional[CrossAssetSignal]:
        """
        Generate signal when correlation breaks from historical norm.
        
        Example: BTC-SPX correlation drops from 0.7 to 0.2 -> regime change
        """
        now = datetime.now(timezone.utc)
        
        # Calculate z-score of current correlation
        if historical_std == 0:
            return None
        
        z_score = (current_corr - historical_corr) / historical_std
        
        # Need significant break (2+ standard deviations)
        if abs(z_score) < 2.0:
            return None
        
        # Determine signal characteristics
        if z_score > 0:
            # Correlation increased
            if current_corr > 0:
                signal_type = "CORRELATION_SURGE"
                description = f"{pair.asset_a}-{pair.asset_b} correlation surged to {current_corr:.2f}. Assets now highly correlated."
            else:
                signal_type = "CORRELATION_FLIP"
                description = f"{pair.asset_a}-{pair.asset_b} correlation flipped positive. Relationship changed."
        else:
            # Correlation decreased
            if current_corr > 0:
                signal_type = "CORRELATION_DECAY"
                description = f"{pair.asset_a}-{pair.asset_b} correlation dropped to {current_corr:.2f}. Decoupling in progress."
            else:
                signal_type = "CORRELATION_FLIP"
                description = f"{pair.asset_a}-{pair.asset_b} correlation flipped negative. Inverse relationship forming."
        
        strength = min(1.0, abs(z_score) / 4)  # 4 sigma = max strength
        
        return CrossAssetSignal(
            signal_id=self.generate_signal_id(),
            signal_type=signal_type,
            trigger_asset=pair.asset_a,
            target_asset=pair.asset_b,
            direction="NEUTRAL",  # Correlation breaks don't have directional bias
            strength=strength,
            description=description,
            generated_at=now,
            valid_until=now + timedelta(hours=self.signal_validity_hours * 2)
        )
    
    def generate_regime_shift_signal(
        self,
        old_regime: CorrelationRegime,
        new_regime: RegimeState,
        target_asset: str = "BTC"
    ) -> Optional[CrossAssetSignal]:
        """
        Generate signal when market regime changes.
        """
        now = datetime.now(timezone.utc)
        
        if old_regime == new_regime.regime:
            return None
        
        # Determine directional implication
        bullish_regimes = [CorrelationRegime.RISK_ON, CorrelationRegime.CRYPTO_NATIVE]
        bearish_regimes = [CorrelationRegime.RISK_OFF]
        neutral_regimes = [CorrelationRegime.TRANSITIONING, CorrelationRegime.DECOUPLING]
        
        if new_regime.regime in bullish_regimes:
            direction = "BULLISH"
            action = "Consider adding to positions"
        elif new_regime.regime in bearish_regimes:
            direction = "BEARISH"
            action = "Consider reducing exposure"
        else:
            direction = "NEUTRAL"
            action = "Wait for regime clarity"
        
        description = (
            f"Regime shift: {old_regime.value} -> {new_regime.regime.value}. "
            f"{action}. {new_regime.description}"
        )
        
        return CrossAssetSignal(
            signal_id=self.generate_signal_id(),
            signal_type="REGIME_SHIFT",
            trigger_asset="MARKET",
            target_asset=target_asset,
            direction=direction,
            strength=new_regime.confidence,
            description=description,
            regime_basis=new_regime,
            generated_at=now,
            valid_until=now + timedelta(hours=self.signal_validity_hours * 4)
        )
    
    def generate_dxy_signal(
        self,
        dxy_return: float,
        dxy_trend: str,  # UP, DOWN, NEUTRAL
        btc_dxy_corr: float,
        target_asset: str = "BTC"
    ) -> Optional[CrossAssetSignal]:
        """
        Generate signal based on DXY (Dollar Index) movement.
        
        DXY strength typically bearish for crypto.
        """
        now = datetime.now(timezone.utc)
        
        # Need meaningful DXY move
        if abs(dxy_return) < 0.003:  # 0.3%
            return None
        
        # DXY inverse relationship with crypto
        if dxy_return > 0:
            direction = "BEARISH"
            description = f"DXY strengthened {dxy_return*100:.2f}%. Dollar strength typically pressures crypto."
        else:
            direction = "BULLISH"
            description = f"DXY weakened {abs(dxy_return)*100:.2f}%. Dollar weakness typically supports crypto."
        
        # Strengthen signal if trend confirms
        if dxy_trend == "UP" and direction == "BEARISH":
            strength = min(1.0, abs(dxy_return) * 30)
            description += " DXY trend is up - sustained pressure likely."
        elif dxy_trend == "DOWN" and direction == "BULLISH":
            strength = min(1.0, abs(dxy_return) * 30)
            description += " DXY trend is down - sustained support likely."
        else:
            strength = min(0.7, abs(dxy_return) * 20)
        
        # Adjust for correlation
        strength *= max(0.5, abs(btc_dxy_corr))
        
        return CrossAssetSignal(
            signal_id=self.generate_signal_id(),
            signal_type="DXY_SIGNAL",
            trigger_asset="DXY",
            target_asset=target_asset,
            direction=direction,
            strength=strength,
            description=description,
            generated_at=now,
            valid_until=now + timedelta(hours=self.signal_validity_hours)
        )
    
    def generate_equity_signal(
        self,
        spx_return: float,
        nasdaq_return: float,
        btc_spx_corr: float,
        target_asset: str = "BTC"
    ) -> Optional[CrossAssetSignal]:
        """
        Generate signal based on equity market movement.
        """
        now = datetime.now(timezone.utc)
        
        # Average equity move
        equity_return = (spx_return + nasdaq_return) / 2
        
        # Need meaningful move
        if abs(equity_return) < 0.005:  # 0.5%
            return None
        
        # Positive correlation with crypto
        if equity_return > 0:
            direction = "BULLISH"
            description = f"Equities rallied (SPX {spx_return*100:.2f}%, NASDAQ {nasdaq_return*100:.2f}%). Risk-on environment supports crypto."
        else:
            direction = "BEARISH"
            description = f"Equities sold off (SPX {spx_return*100:.2f}%, NASDAQ {nasdaq_return*100:.2f}%). Risk-off pressure on crypto."
        
        # NASDAQ more correlated with crypto
        if abs(nasdaq_return) > abs(spx_return):
            description += " Tech/NASDAQ leading - stronger crypto correlation."
        
        strength = min(1.0, abs(equity_return) * 15)
        
        # Adjust for correlation
        strength *= max(0.3, abs(btc_spx_corr))
        
        return CrossAssetSignal(
            signal_id=self.generate_signal_id(),
            signal_type="EQUITY_SIGNAL",
            trigger_asset="SPX",
            target_asset=target_asset,
            direction=direction,
            strength=strength,
            description=description,
            generated_at=now,
            valid_until=now + timedelta(hours=self.signal_validity_hours)
        )
    
    def generate_all_signals(
        self,
        asset_returns: Dict[str, float],
        correlation_matrix: Dict[str, CorrelationValue],
        lead_lag_results: Dict[str, LeadLagResult],
        current_regime: Optional[RegimeState] = None,
        previous_regime: Optional[CorrelationRegime] = None
    ) -> List[CrossAssetSignal]:
        """
        Generate all applicable signals from current market state.
        """
        signals = []
        
        # Extract key returns
        btc_return = asset_returns.get("BTC", 0)
        eth_return = asset_returns.get("ETH", 0)
        spx_return = asset_returns.get("SPX", 0)
        nasdaq_return = asset_returns.get("NASDAQ", 0)
        dxy_return = asset_returns.get("DXY", 0)
        
        # Extract key correlations
        btc_spx_corr = correlation_matrix.get("BTC_SPX").value if "BTC_SPX" in correlation_matrix else 0.5
        btc_dxy_corr = correlation_matrix.get("BTC_DXY").value if "BTC_DXY" in correlation_matrix else -0.3
        
        # Generate DXY signal
        dxy_trend = "UP" if dxy_return > 0.001 else ("DOWN" if dxy_return < -0.001 else "NEUTRAL")
        dxy_signal = self.generate_dxy_signal(dxy_return, dxy_trend, btc_dxy_corr)
        if dxy_signal:
            signals.append(dxy_signal)
        
        # Generate equity signal
        equity_signal = self.generate_equity_signal(spx_return, nasdaq_return, btc_spx_corr)
        if equity_signal:
            signals.append(equity_signal)
        
        # Generate macro divergence signals
        for macro_asset in ["SPX", "NASDAQ", "DXY"]:
            if macro_asset in asset_returns:
                corr_key = f"BTC_{macro_asset}"
                if corr_key in correlation_matrix:
                    div_signal = self.generate_macro_divergence_signal(
                        macro_asset=macro_asset,
                        macro_return=asset_returns[macro_asset],
                        crypto_asset="BTC",
                        crypto_return=btc_return,
                        correlation=correlation_matrix[corr_key].value,
                        historical_correlation=0.5  # Placeholder
                    )
                    if div_signal:
                        signals.append(div_signal)
        
        # Generate lead signals
        for pair_id, lead_lag in lead_lag_results.items():
            if lead_lag.leader in asset_returns:
                lead_signal = self.generate_lead_signal(
                    lead_lag_result=lead_lag,
                    leader_return=asset_returns[lead_lag.leader]
                )
                if lead_signal:
                    signals.append(lead_signal)
        
        # Generate regime shift signal
        if current_regime and previous_regime:
            regime_signal = self.generate_regime_shift_signal(
                old_regime=previous_regime,
                new_regime=current_regime
            )
            if regime_signal:
                signals.append(regime_signal)
        
        # Sort by strength
        signals.sort(key=lambda x: x.strength, reverse=True)
        
        return signals
    
    def filter_signals(
        self,
        signals: List[CrossAssetSignal],
        min_strength: float = 0.3,
        signal_types: Optional[List[str]] = None,
        direction: Optional[str] = None
    ) -> List[CrossAssetSignal]:
        """
        Filter signals by criteria.
        """
        filtered = signals
        
        # Filter by strength
        filtered = [s for s in filtered if s.strength >= min_strength]
        
        # Filter by type
        if signal_types:
            filtered = [s for s in filtered if s.signal_type in signal_types]
        
        # Filter by direction
        if direction:
            filtered = [s for s in filtered if s.direction == direction.upper()]
        
        return filtered
    
    def get_signal_summary(self, signals: List[CrossAssetSignal]) -> Dict:
        """
        Get summary of current signals.
        """
        if not signals:
            return {
                "total_signals": 0,
                "net_direction": "NEUTRAL"
            }
        
        bullish = sum(1 for s in signals if s.direction == "BULLISH")
        bearish = sum(1 for s in signals if s.direction == "BEARISH")
        
        if bullish > bearish:
            net_direction = "BULLISH"
        elif bearish > bullish:
            net_direction = "BEARISH"
        else:
            net_direction = "NEUTRAL"
        
        avg_strength = sum(s.strength for s in signals) / len(signals)
        
        by_type = {}
        for s in signals:
            if s.signal_type not in by_type:
                by_type[s.signal_type] = 0
            by_type[s.signal_type] += 1
        
        return {
            "total_signals": len(signals),
            "bullish_count": bullish,
            "bearish_count": bearish,
            "neutral_count": len(signals) - bullish - bearish,
            "net_direction": net_direction,
            "avg_strength": round(avg_strength, 3),
            "by_type": by_type,
            "strongest_signal": signals[0].to_dict() if signals else None
        }
