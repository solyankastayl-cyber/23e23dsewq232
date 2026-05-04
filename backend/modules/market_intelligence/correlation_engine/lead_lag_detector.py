"""
PHASE 7 - Lead/Lag Detector
=============================
Determines which asset leads and which follows using cross-correlation.
Identifies lead/lag relationships for predictive trading signals.

Key pairs for macro intelligence:
- SPX -> BTC (macro leads crypto)
- DXY -> BTC (dollar strength impacts crypto)
- ETH -> altcoins (ETH leads alt market)
- BTC -> total crypto market
"""

import math
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timezone

from .correlation_types import (
    AssetPair, LeadLagResult, AssetClass, DEFAULT_PAIRS
)


class LeadLagDetector:
    """
    Detects lead/lag relationships between assets using cross-correlation.
    Identifies which asset moves first and by how many candles.
    """
    
    def __init__(self):
        self.max_lag = 20  # Maximum lag to test (candles)
        self.min_data_points = 50  # Minimum data for reliable detection
        
        # Key macro-crypto relationships
        self.macro_pairs = [
            AssetPair("SPX", "BTC", AssetClass.EQUITY_INDEX, AssetClass.CRYPTO_MAJOR),
            AssetPair("NASDAQ", "BTC", AssetClass.EQUITY_INDEX, AssetClass.CRYPTO_MAJOR),
            AssetPair("DXY", "BTC", AssetClass.FOREX, AssetClass.CRYPTO_MAJOR),
            AssetPair("US10Y", "BTC", AssetClass.BOND, AssetClass.CRYPTO_MAJOR),
            AssetPair("GOLD", "BTC", AssetClass.COMMODITY, AssetClass.CRYPTO_MAJOR),
        ]
        
        # Crypto internal relationships
        self.crypto_pairs = [
            AssetPair("BTC", "ETH", AssetClass.CRYPTO_MAJOR, AssetClass.CRYPTO_MAJOR),
            AssetPair("BTC", "TOTAL", AssetClass.CRYPTO_MAJOR, AssetClass.CRYPTO_MAJOR),
            AssetPair("ETH", "TOTAL", AssetClass.CRYPTO_MAJOR, AssetClass.CRYPTO_MAJOR),
        ]
    
    def cross_correlate(
        self,
        returns_a: List[float],
        returns_b: List[float],
        max_lag: int = None
    ) -> Dict[int, float]:
        """
        Calculate cross-correlation at different lag values.
        
        Positive lag: returns_a leads returns_b
        Negative lag: returns_b leads returns_a
        
        Returns: Dict mapping lag to correlation value
        """
        if max_lag is None:
            max_lag = self.max_lag
        
        n = min(len(returns_a), len(returns_b))
        if n < self.min_data_points:
            return {}
        
        # Normalize returns
        mean_a = sum(returns_a[:n]) / n
        mean_b = sum(returns_b[:n]) / n
        std_a = math.sqrt(sum((x - mean_a) ** 2 for x in returns_a[:n]) / n)
        std_b = math.sqrt(sum((x - mean_b) ** 2 for x in returns_b[:n]) / n)
        
        if std_a == 0 or std_b == 0:
            return {}
        
        norm_a = [(x - mean_a) / std_a for x in returns_a[:n]]
        norm_b = [(x - mean_b) / std_b for x in returns_b[:n]]
        
        lag_correlations = {}
        
        # Test both positive and negative lags
        for lag in range(-max_lag, max_lag + 1):
            if lag >= 0:
                # A leads B (A[t] vs B[t+lag])
                a_slice = norm_a[:n - lag] if lag > 0 else norm_a
                b_slice = norm_b[lag:] if lag > 0 else norm_b
            else:
                # B leads A (B[t] vs A[t+|lag|])
                abs_lag = abs(lag)
                a_slice = norm_a[abs_lag:]
                b_slice = norm_b[:n - abs_lag]
            
            if len(a_slice) < 20:
                continue
            
            # Calculate correlation
            corr = sum(a * b for a, b in zip(a_slice, b_slice)) / len(a_slice)
            lag_correlations[lag] = corr
        
        return lag_correlations
    
    def find_optimal_lag(
        self,
        lag_correlations: Dict[int, float]
    ) -> Tuple[int, float]:
        """
        Find the lag with the highest absolute correlation.
        
        Returns: (optimal_lag, correlation_at_lag)
        """
        if not lag_correlations:
            return 0, 0.0
        
        # Find lag with max absolute correlation
        optimal_lag = max(lag_correlations.keys(), key=lambda k: abs(lag_correlations[k]))
        return optimal_lag, lag_correlations[optimal_lag]
    
    def detect_lead_lag(
        self,
        returns_a: List[float],
        returns_b: List[float],
        pair: AssetPair,
        max_lag: int = None
    ) -> LeadLagResult:
        """
        Detect lead/lag relationship between two assets.
        
        Args:
            returns_a: Return series for asset A
            returns_b: Return series for asset B
            pair: AssetPair defining the relationship
            max_lag: Maximum lag to test
        
        Returns:
            LeadLagResult with leader, follower, lag, and confidence
        """
        lag_correlations = self.cross_correlate(returns_a, returns_b, max_lag)
        
        if not lag_correlations:
            return LeadLagResult(
                pair=pair,
                leader=pair.asset_a,
                follower=pair.asset_b,
                lag_candles=0,
                lag_correlation=0.0,
                confidence=0.0,
                lag_correlations={},
                computed_at=datetime.now(timezone.utc)
            )
        
        optimal_lag, lag_corr = self.find_optimal_lag(lag_correlations)
        
        # Determine leader/follower based on lag sign
        if optimal_lag > 0:
            # Positive lag: A leads B
            leader = pair.asset_a
            follower = pair.asset_b
        elif optimal_lag < 0:
            # Negative lag: B leads A
            leader = pair.asset_b
            follower = pair.asset_a
            optimal_lag = abs(optimal_lag)  # Report as positive
        else:
            # No lag (simultaneous)
            leader = pair.asset_a
            follower = pair.asset_b
        
        # Calculate confidence based on:
        # 1. Strength of lag correlation
        # 2. How much stronger lag corr is vs zero-lag
        # 3. Data quality
        zero_lag_corr = lag_correlations.get(0, 0)
        improvement = abs(lag_corr) - abs(zero_lag_corr)
        
        confidence = min(0.95, max(0.1, (
            abs(lag_corr) * 0.5 +  # Correlation strength
            max(0, improvement) * 0.3 +  # Improvement over zero-lag
            0.2  # Base confidence
        )))
        
        # Calculate p-value approximation
        n = min(len(returns_a), len(returns_b))
        if abs(lag_corr) < 1 and n > 2:
            t_stat = lag_corr * math.sqrt(n - 2) / math.sqrt(1 - lag_corr**2 + 0.0001)
            p_value = 2 * (1 - min(0.9999, abs(t_stat) / (abs(t_stat) + 1)))
        else:
            p_value = 0.05
        
        return LeadLagResult(
            pair=pair,
            leader=leader,
            follower=follower,
            lag_candles=optimal_lag,
            lag_correlation=lag_corr,
            confidence=confidence,
            p_value=p_value,
            lag_correlations=lag_correlations,
            computed_at=datetime.now(timezone.utc)
        )
    
    def analyze_all_pairs(
        self,
        asset_returns: Dict[str, List[float]],
        pairs: List[AssetPair] = None,
        max_lag: int = None
    ) -> Dict[str, LeadLagResult]:
        """
        Analyze lead/lag for multiple asset pairs.
        
        Args:
            asset_returns: Dict mapping asset name to return series
            pairs: List of pairs to analyze (default: all default pairs)
            max_lag: Maximum lag to test
        
        Returns:
            Dict mapping pair_id to LeadLagResult
        """
        if pairs is None:
            pairs = self.macro_pairs + self.crypto_pairs + DEFAULT_PAIRS
        
        results = {}
        
        for pair in pairs:
            if pair.asset_a not in asset_returns or pair.asset_b not in asset_returns:
                continue
            
            returns_a = asset_returns[pair.asset_a]
            returns_b = asset_returns[pair.asset_b]
            
            result = self.detect_lead_lag(returns_a, returns_b, pair, max_lag)
            results[pair.pair_id] = result
        
        return results
    
    def get_leading_assets(
        self,
        results: Dict[str, LeadLagResult],
        min_confidence: float = 0.5
    ) -> List[Dict]:
        """
        Get list of assets that lead other assets.
        
        Returns:
            List of dicts with leader info, sorted by frequency
        """
        leader_counts = {}
        leader_details = {}
        
        for result in results.values():
            if result.confidence < min_confidence:
                continue
            
            if result.lag_candles == 0:
                continue  # Skip simultaneous pairs
            
            leader = result.leader
            if leader not in leader_counts:
                leader_counts[leader] = 0
                leader_details[leader] = []
            
            leader_counts[leader] += 1
            leader_details[leader].append({
                "follower": result.follower,
                "lag_candles": result.lag_candles,
                "correlation": round(result.lag_correlation, 4),
                "confidence": round(result.confidence, 3)
            })
        
        # Sort by leadership frequency
        sorted_leaders = sorted(leader_counts.keys(), key=lambda x: leader_counts[x], reverse=True)
        
        return [
            {
                "asset": leader,
                "leads_count": leader_counts[leader],
                "followers": leader_details[leader]
            }
            for leader in sorted_leaders
        ]
    
    def get_macro_signals(
        self,
        results: Dict[str, LeadLagResult],
        min_confidence: float = 0.6
    ) -> List[Dict]:
        """
        Extract macro-driven signals from lead/lag analysis.
        
        Returns trading signals based on macro assets leading crypto.
        """
        signals = []
        
        macro_leaders = ["SPX", "NASDAQ", "DXY", "US10Y", "GOLD"]
        crypto_followers = ["BTC", "ETH", "TOTAL"]
        
        for pair_id, result in results.items():
            if result.confidence < min_confidence:
                continue
            
            if result.lag_candles == 0:
                continue
            
            # Check for macro -> crypto lead
            if result.leader in macro_leaders and result.follower in crypto_followers:
                # Determine signal direction
                if result.leader == "DXY":
                    # DXY up = crypto down (inverse)
                    direction = "BEARISH" if result.lag_correlation > 0 else "BULLISH"
                else:
                    # SPX/NASDAQ up = crypto up (positive)
                    direction = "BULLISH" if result.lag_correlation > 0 else "BEARISH"
                
                signals.append({
                    "type": "MACRO_LEAD",
                    "leader": result.leader,
                    "follower": result.follower,
                    "lag_candles": result.lag_candles,
                    "direction": direction,
                    "strength": abs(result.lag_correlation),
                    "confidence": result.confidence,
                    "description": f"{result.leader} leads {result.follower} by {result.lag_candles} candles"
                })
        
        return sorted(signals, key=lambda x: x["confidence"], reverse=True)
    
    def get_summary(self, results: Dict[str, LeadLagResult]) -> Dict:
        """
        Get summary statistics from lead/lag analysis.
        """
        if not results:
            return {}
        
        valid_results = [r for r in results.values() if r.confidence > 0.3]
        
        if not valid_results:
            return {
                "total_pairs": len(results),
                "valid_pairs": 0
            }
        
        avg_lag = sum(r.lag_candles for r in valid_results) / len(valid_results)
        avg_confidence = sum(r.confidence for r in valid_results) / len(valid_results)
        avg_corr = sum(abs(r.lag_correlation) for r in valid_results) / len(valid_results)
        
        # Count unique leaders
        leaders = set(r.leader for r in valid_results if r.lag_candles > 0)
        
        return {
            "total_pairs": len(results),
            "valid_pairs": len(valid_results),
            "avg_lag_candles": round(avg_lag, 1),
            "avg_confidence": round(avg_confidence, 3),
            "avg_lag_correlation": round(avg_corr, 4),
            "unique_leaders": list(leaders),
            "strongest_lead_lag": max(valid_results, key=lambda x: abs(x.lag_correlation)).to_dict() if valid_results else None
        }
