"""
PHASE 7 - Correlation Engine API Routes
=========================================
REST API endpoints for correlation intelligence.

Endpoints:
- GET /api/correlation/matrix
- GET /api/correlation/rolling
- GET /api/correlation/lead-lag
- GET /api/correlation/regime
- GET /api/correlation/signals
- GET /api/correlation/{assetA}/{assetB}
- GET /api/correlation/health
"""

import random
from typing import Optional, List
from datetime import datetime, timezone
from fastapi import APIRouter, Query, HTTPException
from pydantic import BaseModel

from .correlation_types import (
    AssetPair, AssetClass, CorrelationMethod, CorrelationRegime,
    DEFAULT_PAIRS, REGIME_THRESHOLDS
)
from .correlation_matrix import CorrelationMatrixEngine
from .rolling_correlation import RollingCorrelationEngine
from .lead_lag_detector import LeadLagDetector
from .regime_classifier import RegimeClassifier
from .cross_asset_signals import CrossAssetSignalGenerator
from .correlation_repository import CorrelationRepository


router = APIRouter(prefix="/api/correlation", tags=["Correlation Intelligence"])


# Initialize engines
matrix_engine = CorrelationMatrixEngine()
rolling_engine = RollingCorrelationEngine()
lead_lag_detector = LeadLagDetector()
regime_classifier = RegimeClassifier()
signal_generator = CrossAssetSignalGenerator()
repository = CorrelationRepository()


# ===== Mock Data Generators =====

def generate_mock_returns(asset: str, n: int = 100) -> List[float]:
    """Generate mock return series for testing."""
    base_vol = {
        "BTC": 0.03, "ETH": 0.04, "TOTAL": 0.025,
        "SPX": 0.01, "NASDAQ": 0.012, "DXY": 0.003,
        "GOLD": 0.008, "US10Y": 0.002
    }.get(asset, 0.02)
    
    returns = []
    for _ in range(n):
        r = random.gauss(0, base_vol)
        returns.append(r)
    
    return returns


def generate_mock_asset_returns() -> dict:
    """Generate mock returns for all tracked assets."""
    assets = ["BTC", "ETH", "TOTAL", "SPX", "NASDAQ", "DXY", "GOLD", "US10Y"]
    
    # Generate correlated returns
    base_returns = generate_mock_returns("BTC", 150)
    
    asset_returns = {"BTC": base_returns}
    
    # ETH highly correlated with BTC
    eth_returns = [r * 1.2 + random.gauss(0, 0.01) for r in base_returns]
    asset_returns["ETH"] = eth_returns
    
    # TOTAL correlated with BTC
    total_returns = [r * 0.9 + random.gauss(0, 0.008) for r in base_returns]
    asset_returns["TOTAL"] = total_returns
    
    # SPX partially correlated
    spx_returns = [r * 0.4 + random.gauss(0, 0.008) for r in base_returns]
    asset_returns["SPX"] = spx_returns
    
    # NASDAQ more correlated with crypto
    nasdaq_returns = [r * 0.5 + random.gauss(0, 0.01) for r in base_returns]
    asset_returns["NASDAQ"] = nasdaq_returns
    
    # DXY inversely correlated
    dxy_returns = [r * -0.2 + random.gauss(0, 0.002) for r in base_returns]
    asset_returns["DXY"] = dxy_returns
    
    # GOLD mixed correlation
    gold_returns = [r * 0.1 + random.gauss(0, 0.005) for r in base_returns]
    asset_returns["GOLD"] = gold_returns
    
    # US10Y low correlation
    us10y_returns = [random.gauss(0, 0.001) for _ in base_returns]
    asset_returns["US10Y"] = us10y_returns
    
    return asset_returns


# ===== Request/Response Models =====

class CorrelationMatrixResponse(BaseModel):
    symbol: str
    timeframe: str
    method: str
    window_size: int
    pair_count: int
    matrix: dict
    summary: dict
    strongest: list
    computed_at: str


class RollingCorrelationResponse(BaseModel):
    pair_id: str
    timeframe: str
    window_size: int
    current_value: float
    mean_value: float
    std_value: float
    trend: str
    change: dict
    computed_at: str


class LeadLagResponse(BaseModel):
    pair_id: str
    leader: str
    follower: str
    lag_candles: int
    lag_correlation: float
    confidence: float
    computed_at: str


class RegimeResponse(BaseModel):
    regime: str
    confidence: float
    description: str
    trading_implications: list
    correlations: dict
    duration_candles: int
    computed_at: str


class SignalsResponse(BaseModel):
    total_signals: int
    net_direction: str
    avg_strength: float
    signals: list
    summary: dict
    computed_at: str


# ===== API Endpoints =====

@router.get("/health")
async def correlation_health():
    """Health check for Correlation Engine."""
    return {
        "status": "healthy",
        "version": "phase7_correlation_v1",
        "engines": {
            "matrix": "ready",
            "rolling": "ready",
            "lead_lag": "ready",
            "regime": "ready",
            "signals": "ready"
        },
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@router.get("/matrix", response_model=CorrelationMatrixResponse)
async def get_correlation_matrix(
    symbol: str = Query("MULTI", description="Symbol or MULTI for all"),
    timeframe: str = Query("4h", description="Timeframe"),
    method: str = Query("PEARSON", description="Correlation method"),
    window: int = Query(30, description="Window size in candles")
):
    """
    Get correlation matrix for all tracked asset pairs.
    
    Returns correlations between:
    - BTC, ETH, TOTAL (crypto)
    - SPX, NASDAQ (equities)
    - DXY (dollar)
    - GOLD (commodity)
    - US10Y (bonds)
    """
    try:
        # Generate mock data for demo
        asset_returns = generate_mock_asset_returns()
        
        # Calculate matrix
        corr_method = CorrelationMethod(method.upper())
        matrix = matrix_engine.calculate_matrix(
            asset_returns=asset_returns,
            pairs=DEFAULT_PAIRS,
            method=corr_method,
            window_size=window
        )
        
        # Get summary and strongest
        summary = matrix_engine.get_matrix_summary(matrix)
        strongest = matrix_engine.get_strongest_correlations(matrix, n=5)
        
        # Convert to serializable format
        matrix_dict = {k: v.to_dict() for k, v in matrix.items()}
        strongest_list = [s.to_dict() for s in strongest]
        
        # Try to save to repository
        try:
            repository.save_correlation_matrix(matrix, symbol, timeframe)
        except Exception:
            pass  # Non-critical
        
        return CorrelationMatrixResponse(
            symbol=symbol,
            timeframe=timeframe,
            method=method,
            window_size=window,
            pair_count=len(matrix),
            matrix=matrix_dict,
            summary=summary,
            strongest=strongest_list,
            computed_at=datetime.now(timezone.utc).isoformat()
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/rolling", response_model=RollingCorrelationResponse)
async def get_rolling_correlation(
    asset_a: str = Query("BTC", description="First asset"),
    asset_b: str = Query("SPX", description="Second asset"),
    timeframe: str = Query("4h", description="Timeframe"),
    window: int = Query(30, description="Rolling window size")
):
    """
    Get rolling correlation for a specific asset pair.
    
    Shows how correlation changes over time.
    """
    try:
        # Generate mock data
        asset_returns = generate_mock_asset_returns()
        
        if asset_a not in asset_returns or asset_b not in asset_returns:
            raise HTTPException(status_code=400, detail=f"Unknown asset: {asset_a} or {asset_b}")
        
        pair = AssetPair(
            asset_a, asset_b,
            AssetClass.CRYPTO_MAJOR, AssetClass.EQUITY_INDEX
        )
        
        rolling = rolling_engine.calculate_rolling(
            returns_a=asset_returns[asset_a],
            returns_b=asset_returns[asset_b],
            pair=pair,
            window_size=window
        )
        
        change = rolling_engine.get_correlation_change(rolling, lookback=10)
        
        return RollingCorrelationResponse(
            pair_id=pair.pair_id,
            timeframe=timeframe,
            window_size=window,
            current_value=round(rolling.current_value, 4),
            mean_value=round(rolling.mean_value, 4),
            std_value=round(rolling.std_value, 4),
            trend=rolling.trend,
            change=change,
            computed_at=datetime.now(timezone.utc).isoformat()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/lead-lag", response_model=LeadLagResponse)
async def get_lead_lag(
    asset_a: str = Query("SPX", description="First asset"),
    asset_b: str = Query("BTC", description="Second asset"),
    timeframe: str = Query("4h", description="Timeframe"),
    max_lag: int = Query(10, description="Maximum lag to test")
):
    """
    Detect lead/lag relationship between two assets.
    
    Determines which asset leads and by how many candles.
    """
    try:
        asset_returns = generate_mock_asset_returns()
        
        if asset_a not in asset_returns or asset_b not in asset_returns:
            raise HTTPException(status_code=400, detail=f"Unknown asset")
        
        pair = AssetPair(
            asset_a, asset_b,
            AssetClass.EQUITY_INDEX, AssetClass.CRYPTO_MAJOR
        )
        
        result = lead_lag_detector.detect_lead_lag(
            returns_a=asset_returns[asset_a],
            returns_b=asset_returns[asset_b],
            pair=pair,
            max_lag=max_lag
        )
        
        # Save to repository
        try:
            repository.save_lead_lag_result(result, "MULTI", timeframe)
        except Exception:
            pass
        
        return LeadLagResponse(
            pair_id=pair.pair_id,
            leader=result.leader,
            follower=result.follower,
            lag_candles=result.lag_candles,
            lag_correlation=round(result.lag_correlation, 4),
            confidence=round(result.confidence, 3),
            computed_at=datetime.now(timezone.utc).isoformat()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/lead-lag/all")
async def get_all_lead_lag(
    timeframe: str = Query("4h", description="Timeframe")
):
    """
    Get lead/lag analysis for all key pairs.
    """
    try:
        asset_returns = generate_mock_asset_returns()
        
        results = lead_lag_detector.analyze_all_pairs(
            asset_returns=asset_returns,
            max_lag=10
        )
        
        # Get summary
        summary = lead_lag_detector.get_summary(results)
        leaders = lead_lag_detector.get_leading_assets(results)
        macro_signals = lead_lag_detector.get_macro_signals(results)
        
        return {
            "timeframe": timeframe,
            "pair_count": len(results),
            "results": {k: v.to_dict() for k, v in results.items()},
            "summary": summary,
            "leading_assets": leaders,
            "macro_signals": macro_signals,
            "computed_at": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/regime", response_model=RegimeResponse)
async def get_current_regime(
    timeframe: str = Query("4h", description="Timeframe"),
    btc_trend: str = Query("NEUTRAL", description="BTC trend: UP, DOWN, NEUTRAL")
):
    """
    Classify current market correlation regime.
    
    Regimes:
    - MACRO_DOMINANT: Crypto follows traditional markets
    - CRYPTO_NATIVE: Crypto moves independently
    - RISK_ON: Everything rallying together
    - RISK_OFF: Everything selling together
    - DECOUPLING: Correlations breaking down
    - TRANSITIONING: Regime changing
    """
    try:
        asset_returns = generate_mock_asset_returns()
        
        # Calculate correlation matrix first
        matrix = matrix_engine.calculate_matrix(asset_returns)
        
        # Classify regime
        regime_state = regime_classifier.classify_from_matrix(
            correlation_matrix=matrix,
            btc_trend=btc_trend.upper(),
            correlation_volatility=random.uniform(0.05, 0.2)
        )
        
        # Save to repository
        try:
            repository.save_regime(regime_state, timeframe)
        except Exception:
            pass
        
        return RegimeResponse(
            regime=regime_state.regime.value,
            confidence=round(regime_state.confidence, 3),
            description=regime_state.description,
            trading_implications=regime_state.trading_implications,
            correlations={
                "btc_spx": round(regime_state.btc_spx_corr, 4),
                "btc_dxy": round(regime_state.btc_dxy_corr, 4),
                "btc_eth": round(regime_state.btc_eth_corr, 4),
                "crypto_equity_avg": round(regime_state.crypto_equity_avg, 4)
            },
            duration_candles=regime_state.duration_candles,
            computed_at=datetime.now(timezone.utc).isoformat()
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/regime/history")
async def get_regime_history(
    timeframe: str = Query("4h", description="Timeframe"),
    limit: int = Query(20, description="Number of records")
):
    """Get regime classification history."""
    try:
        history = regime_classifier.get_regime_history(limit)
        stats = regime_classifier.get_regime_stats()
        
        return {
            "timeframe": timeframe,
            "history": history,
            "stats": stats,
            "retrieved_at": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/regime/favorable")
async def check_regime_favorable(
    direction: str = Query("LONG", description="Trade direction"),
    timeframe: str = Query("4h", description="Timeframe")
):
    """Check if current regime is favorable for a trade direction."""
    try:
        result = regime_classifier.is_favorable_regime(direction)
        
        return {
            "direction": direction,
            "timeframe": timeframe,
            **result,
            "checked_at": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/signals", response_model=SignalsResponse)
async def get_correlation_signals(
    target_asset: str = Query("BTC", description="Target asset for signals"),
    min_strength: float = Query(0.3, description="Minimum signal strength"),
    timeframe: str = Query("4h", description="Timeframe")
):
    """
    Get cross-asset trading signals.
    
    Signal types:
    - MACRO_DIVERGENCE: Macro moved, crypto hasn't followed
    - LEAD_SIGNAL: Leading asset suggests direction
    - DXY_SIGNAL: Dollar-based signal
    - EQUITY_SIGNAL: Equity-based signal
    - REGIME_SHIFT: Regime change signal
    """
    try:
        asset_returns = generate_mock_asset_returns()
        
        # Get current returns (last value)
        current_returns = {k: v[-1] if v else 0 for k, v in asset_returns.items()}
        
        # Calculate matrix
        matrix = matrix_engine.calculate_matrix(asset_returns)
        
        # Get lead/lag
        lead_lag_results = lead_lag_detector.analyze_all_pairs(asset_returns)
        
        # Get regime
        regime_state = regime_classifier.classify_from_matrix(matrix)
        
        # Generate signals
        signals = signal_generator.generate_all_signals(
            asset_returns=current_returns,
            correlation_matrix=matrix,
            lead_lag_results=lead_lag_results,
            current_regime=regime_state
        )
        
        # Filter signals
        filtered = signal_generator.filter_signals(
            signals,
            min_strength=min_strength
        )
        
        # Get summary
        summary = signal_generator.get_signal_summary(filtered)
        
        # Save to repository
        try:
            repository.save_signals_batch(filtered)
        except Exception:
            pass
        
        return SignalsResponse(
            total_signals=len(filtered),
            net_direction=summary.get("net_direction", "NEUTRAL"),
            avg_strength=summary.get("avg_strength", 0),
            signals=[s.to_dict() for s in filtered[:20]],  # Limit to 20
            summary=summary,
            computed_at=datetime.now(timezone.utc).isoformat()
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/signals/history")
async def get_signal_history(
    target_asset: str = Query("BTC", description="Target asset"),
    limit: int = Query(50, description="Number of signals")
):
    """Get historical signals."""
    try:
        signals = repository.get_signal_history(target_asset, limit)
        
        return {
            "target_asset": target_asset,
            "count": len(signals),
            "signals": signals,
            "retrieved_at": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{asset_a}/{asset_b}")
async def get_pair_correlation(
    asset_a: str,
    asset_b: str,
    timeframe: str = Query("4h", description="Timeframe"),
    window: int = Query(30, description="Window size")
):
    """
    Get detailed correlation analysis for a specific asset pair.
    """
    try:
        asset_returns = generate_mock_asset_returns()
        
        if asset_a.upper() not in asset_returns or asset_b.upper() not in asset_returns:
            raise HTTPException(status_code=400, detail="Unknown asset")
        
        asset_a = asset_a.upper()
        asset_b = asset_b.upper()
        
        pair = AssetPair(
            asset_a, asset_b,
            AssetClass.CRYPTO_MAJOR, AssetClass.EQUITY_INDEX
        )
        
        # Calculate correlation
        corr, p_value = matrix_engine.calculate_correlation(
            asset_returns[asset_a][-window:],
            asset_returns[asset_b][-window:]
        )
        strength = matrix_engine.classify_strength(corr)
        
        # Calculate rolling
        rolling = rolling_engine.calculate_rolling(
            asset_returns[asset_a],
            asset_returns[asset_b],
            pair,
            window
        )
        
        # Detect lead/lag
        lead_lag = lead_lag_detector.detect_lead_lag(
            asset_returns[asset_a],
            asset_returns[asset_b],
            pair
        )
        
        # Get breakout detection
        breakout = rolling_engine.detect_correlation_breakout(rolling)
        
        return {
            "pair": pair.to_dict(),
            "timeframe": timeframe,
            "correlation": {
                "value": round(corr, 4),
                "p_value": round(p_value, 4),
                "strength": strength.value,
                "window_size": window
            },
            "rolling": rolling.to_dict(),
            "lead_lag": lead_lag.to_dict(),
            "breakout": breakout,
            "computed_at": datetime.now(timezone.utc).isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats")
async def get_correlation_stats():
    """Get repository and engine statistics."""
    try:
        repo_stats = repository.get_stats()
        regime_stats = regime_classifier.get_regime_stats()
        
        return {
            "repository": repo_stats,
            "regime_distribution": regime_stats,
            "tracked_assets": ["BTC", "ETH", "TOTAL", "SPX", "NASDAQ", "DXY", "GOLD", "US10Y"],
            "default_pairs": [p.pair_id for p in DEFAULT_PAIRS],
            "retrieved_at": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
