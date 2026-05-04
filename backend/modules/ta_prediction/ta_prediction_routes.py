"""
TA Prediction Routes
=====================
Endpoints under /api/prediction/ta/*

Mirrors the contract of /api/prediction/exchange/* so the SAME UI (BtcForecastChart
+ right panel + rolling forecasts table) can render TA-based predictions.

  GET /api/prediction/ta/graph4?asset=BTC&horizon=7D&timeframe=4H
  GET /api/prediction/ta/forecast?asset=BTC&timeframe=4H
  GET /api/prediction/ta/live-price?asset=BTC&timeframe=1H
  GET /api/prediction/ta/health

Pass 2 clean contract (single-TF, no padding):
  GET /api/prediction/ta/v2/forecast?symbol=BTCUSDT&tf=4H
"""

from fastapi import APIRouter, Query
from datetime import datetime, timezone

from modules.ta_prediction.ta_prediction_service import (
    build_ta_prediction,
    build_ta_targets,
    build_ta_single_forecast,
    get_live_price,
)
from modules.ta_engine.utils.time_utils import normalize_tf

router = APIRouter(prefix="/api/prediction/ta", tags=["ta-prediction"])


def _resolve_symbol(asset: str) -> str:
    """Asset → trading symbol used internally."""
    a = (asset or "BTC").upper().strip()
    if a.endswith("USDT") or a.endswith("USD"):
        return a if a.endswith("USDT") else a[:-3] + "USDT"
    return a + "USDT"


@router.get("/health")
async def health():
    return {
        "ok": True,
        "module": "ta_prediction",
        "core": "prediction_core",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/graph4")
async def graph4(
    asset: str = Query("BTC"),
    horizon: str = Query("7D"),
    timeframe: str = Query("4H"),
):
    """Main chart payload — same shape as exchange/graph4."""
    symbol = _resolve_symbol(asset)
    tf = normalize_tf(timeframe)
    return await build_ta_prediction(symbol=symbol, timeframe=tf, horizon=horizon, asset=asset.upper())


@router.get("/forecast")
async def forecast(
    asset: str = Query("BTC"),
    timeframe: str = Query("4H"),
):
    """Multi-horizon targets (24H/7D/30D) — same shape as exchange/forecast."""
    symbol = _resolve_symbol(asset)
    tf = normalize_tf(timeframe)
    return await build_ta_targets(symbol=symbol, timeframe=tf, asset=asset.upper())


@router.get("/v2/forecast")
async def forecast_v2(
    symbol: str = Query("BTCUSDT", description="Trading pair, e.g. BTCUSDT"),
    tf: str = Query("4H", description="Canonical timeframe: 1H, 4H, 1D"),
):
    """
    Pass 2 single-TF clean contract.

    Response shape:
    {
      "symbol": "BTCUSDT",
      "timeframe": "4H",
      "direction": "bullish"|"bearish"|"neutral",
      "confidence": 0..1,
      "forecast": [{"ts": ms, "price": ...}, ...],
      "targets": {
        "expected_move_pct": 0.034,
        "target_price": 70300,
        "max_upside": 71200,
        "max_drawdown": 69500
      },
      "timestamp": "2026-04-26T20:00:00Z",
      "_meta": {direction, confidence, volatility, drift_d, weak, ...},
      "_ta": {summary, strength, has_explanation, has_indicators, has_structure}
    }

    Honest properties:
      * NEUTRAL or weak (conf < 0.15) → flat-with-noise forecast (no fake trend)
      * Same input ⇒ same output (deterministic seeded RNG)
      * targets.target_price === forecast[-1].price
      * No fabricated confidence/volatility (no 0.5 / 0.02 fallbacks)
    """
    s = (symbol or "BTCUSDT").upper().strip()
    if not s.endswith("USDT") and not s.endswith("USD"):
        s = s + "USDT"
    timeframe = normalize_tf(tf)
    return await build_ta_single_forecast(symbol=s, timeframe=timeframe)


@router.get("/live-price")
async def live_price(
    asset: str = Query("BTC"),
    timeframe: str = Query("1H"),
):
    """Live price polling — same shape as exchange/live-price."""
    symbol = _resolve_symbol(asset)
    tf = normalize_tf(timeframe)
    return get_live_price(symbol, timeframe=tf)

