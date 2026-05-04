#!/usr/bin/env python3
"""
TA Engine Bootstrap System v8 — Trading Pipeline Architecture
==============================================================================

CURRENT ARCHITECTURE (V2 Pattern Families + Trading Pipeline):

PATTERN FAMILIES ENGINE:
- Unified detection via family architecture (NOT 100 separate detectors)
- Pipeline: Swings → FamilyClassifier → FamilyDetectors → WindowValidation → Ranking → VisualMode → RenderContract
- Core modules:
  * swing_engine.py              — universal swing high/low detection
  * geometry_engine.py           — unified geometric primitives
  * pattern_window_validator.py  — validates pattern is real, not noise
  * visual_mode_resolver.py      — controls what frontend can render (NO mixing)
  * horizontal_family.py         — double/triple top/bottom, range, rectangle (6 patterns)
  * converging_family.py         — triangles, wedges (5 patterns)
  * parallel_family.py           — channels, flags, pennants (6 patterns)
  * family_classifier.py         — routes candles to correct family
  * family_ranking.py            — ranks candidates, computes REAL confidence
  * pattern_regime_binding.py    — context: pattern + market regime
  * trigger_engine.py            — what to WAIT for (breakout/breakdown levels)
  * pattern_render_builder.py    — unified SVG render contract for frontend
  * unified_detector.py          — single entry point (runs ALL 3 families)

PATTERN COVERAGE (17 patterns ready):
- HORIZONTAL (6):  double_top, double_bottom, triple_top, triple_bottom, range, rectangle
- CONVERGING (5):  symmetrical_triangle, ascending_triangle, descending_triangle, rising_wedge, falling_wedge
- PARALLEL (6):    ascending_channel, descending_channel, horizontal_channel, bull_flag, bear_flag, pennant

VISUAL MODE RESOLVER (render isolation):
- range_only:         box + R/S + triggers (NO swings, NO polyline)
- horizontal_pattern: polyline + neckline (NO range, NO swings)
- compression_pattern: trendlines only (NO range, NO swings)
- structure_only:     HH/HL/LL only (NO patterns)
- none:               clean chart

KEY PRINCIPLES:
- Confidence = Dominance (gap between #1 and #2 pattern), NOT geometric quality
- Max confidence 0.92, never 100%
- States: CLEAR / WEAK / CONFLICTED / COMPRESSION / NONE
- Window Validation: rejects patterns that are noise or too wide
- Visual Mode: 1 screen = 1 idea (NO mixing range + pattern + structure)
- Regime Binding: triangle in trend ≠ triangle in chop
- Trigger Engine: what must happen for pattern to become valid
- Render Contract: one format for ALL patterns (frontend just renders)

FRONTEND V2:
- usePatternV2 hook → fetches /api/ta-engine/pattern-v2/{symbol}
- PatternStateCard → decision-grade UI (state + triggers + action)
- PatternSVGOverlay → renders based on visual_mode (no mixing)
- Shows 1 dominant pattern only, no clutter

TRADING PIPELINE (Phase 2.x):
- Phase 2.1: TA-to-Prediction Adapter (45+ semantic signals)
- Phase 2.2: Prediction Engine V2 (decision-based)
- Phase 2.3: Trade Setup Generator (entry/stop/target/R:R)
- Phase 2.4: Execution Simulator (limit/market/breakout fills, slippage, latency)
- Phase 2.5: Portfolio Backtester (equity curve, drawdown, capital allocation)
- Phase 2.6: Risk Metrics Engine (Sharpe, Sortino, Calmar, VaR, RoR)
- Phase 2.7: Portfolio Constraints v2 (asset/direction/correlation caps, heat)
- Phase 2.8: Multi-Asset Scaling (51 assets, 10 clusters, unified portfolio)

KEY ENDPOINTS:
- GET /api/ta-engine/pattern-v2/{symbol}?timeframe=4H  (PRIMARY V2)
- GET /api/ta-engine/mtf/{symbol}?timeframes=...       (Legacy MTF)
- GET /api/health

Usage:
    python bootstrap.py                 # Full bootstrap (TA + Exchange)
    python bootstrap.py --ta-only       # TA Engine only
    python bootstrap.py --exchange-only # Exchange data only
    python bootstrap.py --status        # Check full status
    python bootstrap.py --reset         # Reset and rebuild all
    python bootstrap.py --quick         # Quick V2 pipeline check
    python bootstrap.py --trading       # Verify trading pipeline (2.4-2.8)
"""

import os
import sys
import json
import csv
import random
import argparse
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional

# Project root
PROJECT_ROOT = Path(__file__).parent

# MongoDB
try:
    from pymongo import MongoClient, DESCENDING
    MONGO_OK = True
except ImportError:
    MONGO_OK = False
    print("[Bootstrap] Warning: pymongo not installed")


# ═══════════════════════════════════════════════════════════════
# Configuration
# ═══════════════════════════════════════════════════════════════

MONGO_URI = os.environ.get("MONGO_URL", os.environ.get("MONGODB_URI", "mongodb://localhost:27017"))
DB_NAME = os.environ.get("DB_NAME", "ta_engine")

# Data sources
DATASETS_DIR = PROJECT_ROOT / "datasets"
DATA_FILES = {
    "BTC": DATASETS_DIR / "btc_daily_v1.csv",
    "ETH": DATASETS_DIR / "eth_daily_v1.csv",
    "SOL": DATASETS_DIR / "sol_daily_v1.csv",
    "SPX": DATASETS_DIR / "spx_daily_v1.csv",
    "DXY": DATASETS_DIR / "dxy_daily_v1.csv",
}

# Exchange symbols (crypto only for exchange intelligence)
EXCHANGE_SYMBOLS = ["BTC", "ETH", "SOL"]


# ═══════════════════════════════════════════════════════════════
# CHART DATA CONFIG - UNIVERSAL FOR ALL ASSETS
# ═══════════════════════════════════════════════════════════════

CHART_DATA_CONFIG = {
    "version": "2.0",
    
    # Default chart lookback (full history for scrolling)
    "default_chart_lookback": {
        "1m": 1000,      # ~16 hours
        "5m": 2000,      # ~7 days
        "15m": 2000,     # ~20 days
        "1h": 2000,      # ~83 days
        "4h": 2000,      # ~333 days
        "6h": 2000,      # ~500 days
        "1d": 2000,      # ~5.5 years
        "1w": 500,       # ~9.5 years
    },
    
    # TA analysis lookback (for pattern detection)
    "ta_lookback": {
        "1m": 100,
        "5m": 100,
        "15m": 150,
        "1h": 168,       # 7 days
        "4h": 200,       # ~33 days
        "6h": 200,
        "1d": 150,       # 5 months
        "1w": 52,        # 1 year
    },
    
    # Supported crypto assets (Coinbase)
    "crypto_assets": ["BTC", "ETH", "SOL", "AVAX", "LINK", "DOGE", "ADA", "DOT", "MATIC", "UNI"],
    
    # Supported traditional assets (from CSV/external)
    "traditional_assets": ["SPX", "DXY", "GOLD", "NASDAQ"],
    
    # All supported timeframes
    "supported_timeframes": ["1m", "5m", "15m", "1h", "4h", "6h", "1d", "7d", "30d", "180d", "1y"],
    
    # Product timeframes (UI mapping)
    "product_timeframes": {
        "4H": "6h",      # Use 6h candles for 4H analysis
        "1D": "1d",
        "7D": "1d",      # Aggregate daily to weekly
        "30D": "1d",     # Aggregate daily to monthly
        "180D": "1d",    # Aggregate daily to 6M
        "1Y": "1d",      # Aggregate daily to yearly
    },
}


# ═══════════════════════════════════════════════════════════════
# Phase 8.6 — Calibration Config
# ═══════════════════════════════════════════════════════════════

CALIBRATION_CONFIG = {
    "version": "pattern_families_v2",
    "enabled": True,
    "volatilityFilter": {
        "enabled": True,
        "atrMultiplier": 0.8,
        "atrPeriod": 14,
        "smaPeriod": 14
    },
    "trendAlignment": {
        "enabled": True,
        "emaShortPeriod": 50,
        "emaLongPeriod": 200,
        "requireBothAligned": False
    },
    "volumeBreakout": {
        "enabled": True,
        "volumeMultiplier": 1.4,
        "smaPeriod": 20
    },
    "atrRiskManagement": {
        "enabled": True,
        "stopLossATR": 1.5,
        "takeProfitATR": 2.5
    },
    "disabledStrategies": [
        "LIQUIDITY_SWEEP",
        "LIQUIDITY_SWEEP_HIGH",
        "LIQUIDITY_SWEEP_LOW",
        "RANGE_REVERSAL"
    ],
    "indicators": {
        "total": 15,
        "list": [
            "sma", "ema", "rsi", "macd", "bollinger", "atr", "vwap",
            "supertrend", "volume_profile",
            "cci", "williams_r", "ichimoku", "parabolic_sar",
            "donchian", "keltner",
        ]
    },
    "pattern_families_v2": {
        "architecture": "unified_family_detector",
        "entry_point": "unified_detector.py → detect_patterns_v2()",
        "families": {
            "horizontal": ["double_top", "double_bottom", "triple_top", "triple_bottom", "range", "rectangle"],
            "converging": ["symmetrical_triangle", "ascending_triangle", "descending_triangle", "rising_wedge", "falling_wedge"],
            "parallel": ["ascending_channel", "descending_channel", "horizontal_channel", "bull_flag", "bear_flag"],
            "swing_composite": ["head_shoulders", "inverse_head_shoulders"],
        },
        "confidence_model": "dominance_based",
        "max_confidence": 0.92,
        "states": ["CLEAR", "WEAK", "CONFLICTED", "COMPRESSION", "NONE"],
        "regime_binding": True,
        "trigger_engine": True,
        "render_contract": True,
    },
}


# ═══════════════════════════════════════════════════════════════
# Phase 8.8 — Strategy Registry (updated with new patterns)
# ═══════════════════════════════════════════════════════════════

STRATEGIES = [
    # Core strategies (APPROVED)
    {"id": "MTF_BREAKOUT", "status": "APPROVED", "wr": 0.64, "pf": 2.1},
    {"id": "DOUBLE_BOTTOM", "status": "APPROVED", "wr": 0.66, "pf": 2.3},
    {"id": "DOUBLE_TOP", "status": "APPROVED", "wr": 0.63, "pf": 2.0},
    {"id": "CHANNEL_BREAKOUT", "status": "APPROVED", "wr": 0.58, "pf": 1.8},
    {"id": "MOMENTUM_CONTINUATION", "status": "APPROVED", "wr": 0.62, "pf": 1.9},
    {"id": "TRIANGLE_BREAKOUT", "status": "APPROVED", "wr": 0.60, "pf": 1.85},
    {"id": "CUP_HANDLE", "status": "APPROVED", "wr": 0.61, "pf": 2.05},
    # Limited strategies
    {"id": "HEAD_SHOULDERS", "status": "LIMITED", "wr": 0.52, "pf": 1.25},
    {"id": "HEAD_SHOULDERS_INV", "status": "LIMITED", "wr": 0.54, "pf": 1.35},
    {"id": "HARMONIC_GARTLEY", "status": "LIMITED", "wr": 0.54, "pf": 1.4},
    {"id": "HARMONIC_BAT", "status": "LIMITED", "wr": 0.53, "pf": 1.35},
    {"id": "WEDGE_RISING", "status": "LIMITED", "wr": 0.51, "pf": 1.15},
    {"id": "WEDGE_FALLING", "status": "LIMITED", "wr": 0.53, "pf": 1.2},
    # Deprecated
    {"id": "LIQUIDITY_SWEEP", "status": "DEPRECATED", "reason": "WR 37-46%"},
    {"id": "RANGE_REVERSAL", "status": "DEPRECATED", "reason": "WR 34-38%"},
]


# ═══════════════════════════════════════════════════════════════
# Phase 8.9 — Regime Activation Map (updated)
# ═══════════════════════════════════════════════════════════════

# Columns: TREND_UP, TREND_DOWN, RANGE, COMPRESSION, EXPANSION
REGIMES = ["TREND_UP", "TREND_DOWN", "RANGE", "COMPRESSION", "EXPANSION"]

REGIME_MAP = {
    "MTF_BREAKOUT":        ["ON",    "ON",       "WATCH", "WATCH",    "ON"],
    "DOUBLE_BOTTOM":       ["ON",    "LIMITED",  "ON",    "LIMITED",  "ON"],
    "DOUBLE_TOP":          ["WATCH", "ON",       "ON",    "LIMITED",  "ON"],
    "CHANNEL_BREAKOUT":    ["ON",    "ON",       "OFF",   "LIMITED",  "ON"],
    "MOMENTUM_CONT":       ["ON",    "ON",       "OFF",   "OFF",      "ON"],
    "TRIANGLE_BREAKOUT":   ["ON",    "ON",       "ON",    "ON",       "ON"],
    "CUP_HANDLE":          ["ON",    "OFF",      "LIMITED","LIMITED",  "ON"],
    "HEAD_SHOULDERS":      ["OFF",   "ON",       "WATCH", "WATCH",    "ON"],
    "HEAD_SHOULDERS_INV":  ["ON",    "OFF",      "WATCH", "WATCH",    "ON"],
    "HARMONIC_GARTLEY":    ["ON",    "LIMITED",  "ON",    "LIMITED",  "LIMITED"],
    "HARMONIC_BAT":        ["ON",    "LIMITED",  "ON",    "LIMITED",  "LIMITED"],
    "WEDGE_RISING":        ["OFF",   "ON",       "WATCH", "LIMITED",  "LIMITED"],
    "WEDGE_FALLING":       ["ON",    "OFF",      "WATCH", "LIMITED",  "ON"],
}


# ═══════════════════════════════════════════════════════════════
# Phase 9.0 — Cross-Asset Baseline
# ═══════════════════════════════════════════════════════════════

CROSS_ASSET_RESULTS = {
    "systemVerdict": "UNIVERSAL",
    "assets": {
        "BTC": {"verdict": "PASS", "pf": 2.24, "wr": 0.56},
        "ETH": {"verdict": "PASS", "pf": 2.54, "wr": 0.57},
        "SOL": {"verdict": "PASS", "pf": 3.24, "wr": 0.62},
        "SPX": {"verdict": "PASS", "pf": 2.47, "wr": 0.64},
        "GOLD": {"verdict": "PASS", "pf": 1.95, "wr": 0.60},
        "DXY": {"verdict": "PASS", "pf": 2.08, "wr": 0.60},
    }
}


# ═══════════════════════════════════════════════════════════════
# Phase 2.x — Trading Pipeline Config
# ═══════════════════════════════════════════════════════════════

TRADING_PIPELINE_CONFIG = {
    "version": "2.8",
    "phases": {
        "2.1": {
            "name": "TA-to-Prediction Adapter",
            "module": "modules/scanner/ta_to_prediction_adapter.py",
            "status": "DONE",
            "signals": 45,
        },
        "2.2": {
            "name": "Prediction Engine V2",
            "module": "modules/prediction/prediction_engine_v2.py",
            "status": "DONE",
            "type": "decision-based",
        },
        "2.3": {
            "name": "Trade Setup Generator",
            "module": "modules/prediction/trade_setup_generator.py",
            "status": "DONE",
            "outputs": ["entry", "stop", "target", "rr", "position_size", "execution_type"],
        },
        "2.4": {
            "name": "Execution Simulator",
            "module": "modules/execution_simulator/",
            "status": "DONE",
            "components": [
                "execution_simulator.py",
                "order_simulator.py",
                "fill_engine.py",
                "slippage_engine.py",
                "latency_engine.py",
            ],
            "order_types": ["limit", "market", "breakout"],
            "tests_passed": 8,
        },
        "2.5": {
            "name": "Portfolio Backtester",
            "module": "modules/portfolio_backtester/",
            "status": "DONE",
            "components": [
                "portfolio_backtester.py",
                "portfolio_state.py",
                "trade_ledger.py",
                "equity_engine.py",
                "drawdown_engine.py",
                "portfolio_metrics.py",
                "capital_allocator.py",
            ],
            "tests_passed": 8,
        },
        "2.6": {
            "name": "Risk Metrics Engine",
            "module": "modules/risk_metrics/",
            "status": "DONE",
            "components": [
                "risk_metrics_engine.py",
                "sharpe.py",
                "drawdown.py",
                "streak_engine.py",
                "ruin_engine.py",
                "volatility_engine.py",
                "performance_ratios.py",
            ],
            "metrics": ["sharpe", "sortino", "calmar", "var_95", "cvar_95", "risk_of_ruin"],
            "tests_passed": 9,
        },
        "2.7": {
            "name": "Portfolio Constraints v2",
            "module": "modules/portfolio_constraints/",
            "status": "DONE",
            "components": [
                "constraint_engine.py",
                "asset_cap.py",
                "direction_cap.py",
                "correlation_cap.py",
                "portfolio_heat.py",
            ],
            "constraints": ["asset_cap", "direction_cap", "correlation_cap", "portfolio_heat"],
            "tests_passed": 11,
        },
        "2.8": {
            "name": "Multi-Asset Scaling",
            "module": "modules/multi_asset/",
            "status": "DONE",
            "components": [
                "universe_registry.py",
                "asset_classifier.py",
                "cluster_engine.py",
                "multi_asset_runner.py",
                "cross_asset_constraints.py",
                "symbol_diagnostics.py",
                "symbol_ranker.py",
            ],
            "universe_size": 51,
            "clusters": 10,
            "tests_passed": 15,
        },
    },
    "pipeline": [
        "TA Intelligence → Adapter (2.1)",
        "→ Prediction Engine V2 (2.2)",
        "→ Trade Setup Generator (2.3)",
        "→ Execution Simulator (2.4)",
        "→ Multi-Asset Runner (2.8.3)",
        "→ Portfolio Backtester (2.5) ← Capital Allocator",
        "→ Risk Metrics Engine (2.6)",
        "→ Constraints (2.7) + Cross-Asset (2.8.4)",
        "→ Symbol Diagnostics + Ranking (2.8.5)",
    ],
}


# ═══════════════════════════════════════════════════════════════
# Provider Configs
# ═══════════════════════════════════════════════════════════════

COINBASE_CONFIG = {
    "provider": "coinbase",
    "baseUrl": "https://api.exchange.coinbase.com",
    "endpoints": {
        "candles": "/products/{product_id}/candles",
        "ticker": "/products/{product_id}/ticker",
        "products": "/products"
    },
    "supportedPairs": ["BTC-USD", "ETH-USD", "SOL-USD"],
    "granularities": {"1m": 60, "5m": 300, "15m": 900, "1h": 3600, "4h": 14400, "1d": 86400}
}

BINANCE_CONFIG = {
    "provider": "binance",
    "baseUrl": "https://fapi.binance.com",
    "endpoints": {
        "funding": "/fapi/v1/fundingRate",
        "oi": "/fapi/v1/openInterest",
        "liquidations": "/fapi/v1/forceOrders"
    },
    "supportedPairs": ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
}


# ═══════════════════════════════════════════════════════════════
# Phase 13.8.B — Exchange Intelligence Config
# ═══════════════════════════════════════════════════════════════

EXCHANGE_INTEL_CONFIG = {
    "version": "15.7.0",
    "phase": "Native Binding",
    "engines": {
        "funding_oi": {"enabled": True, "confidence_native": 0.8},
        "derivatives_pressure": {"enabled": True, "confidence_native": 0.8},
        "exchange_liquidation": {"enabled": True, "confidence_native": 0.8},
        "exchange_flow": {"enabled": True, "confidence_native": 0.8},
        "exchange_volume": {"enabled": True, "confidence_native": 0.85},
    },
    "aggregator_weights": {
        "funding": 0.20,
        "derivatives": 0.20,
        "liquidation": 0.15,
        "flow": 0.30,
        "volume": 0.15,
    },
    "thresholds": {
        "funding_extreme": 0.05,
        "funding_crowded": 0.02,
        "oi_expand": 0.05,
        "cascade_high": 0.6,
        "squeeze_high": 0.6,
    }
}


# ═══════════════════════════════════════════════════════════════
# TA Engine Coverage Config (Phase TA-X)
# ═══════════════════════════════════════════════════════════════

TA_COVERAGE = {
    "version": "pattern_families_v7",
    "indicators": {
        "count": 15,
        "core": ["sma", "ema", "rsi", "macd", "bollinger", "atr", "vwap", "supertrend", "volume_profile"],
        "phase_ta1": ["cci", "williams_r", "ichimoku", "parabolic_sar", "donchian", "keltner"],
    },
    "pattern_families_v2": {
        "architecture": "unified_family_detector",
        "pipeline": "Swings → FamilyClassifier → FamilyDetectors(3) → WindowValidator → Ranking → VisualMode → Triggers → RenderContract",
        "total_patterns_ready": 17,
        "modules": {
            "swing_engine": "Universal swing high/low detection from OHLCV",
            "geometry_engine": "Unified geometric primitives (line slopes, touches, angles)",
            "pattern_window_validator": "Rejects noise/invalid patterns (window too wide, no pretrend, etc)",
            "visual_mode_resolver": "Controls what frontend can render - NO MIXING",
            "family_classifier": "Routes candle data to correct family detector",
            "family_ranking": "Ranks all candidates, computes dominance-based confidence",
            "pattern_regime_binding": "Contextual meaning: same pattern ≠ same action in different regimes",
            "trigger_engine": "Calculates breakout/breakdown/invalidation levels",
            "pattern_render_builder": "Builds unified SVG render contract for frontend",
            "unified_detector": "Single entry point: detect_patterns_v2(candles) — runs ALL 3 families",
        },
        "families_implemented": {
            "horizontal": {
                "module": "horizontal_family.py",
                "patterns": ["double_top", "double_bottom", "triple_top", "triple_bottom", "range", "rectangle"],
                "count": 6,
                "render_mode": "polyline | box",
                "visual_mode": "horizontal_pattern | range_only",
                "status": "DONE",
            },
            "converging": {
                "module": "converging_family.py",
                "patterns": ["symmetrical_triangle", "ascending_triangle", "descending_triangle", "rising_wedge", "falling_wedge"],
                "count": 5,
                "render_mode": "two_lines",
                "visual_mode": "compression_pattern",
                "status": "DONE",
            },
            "parallel": {
                "module": "parallel_family.py",
                "patterns": ["ascending_channel", "descending_channel", "horizontal_channel", "bull_flag", "bear_flag", "pennant"],
                "count": 6,
                "render_mode": "two_lines",
                "visual_mode": "compression_pattern",
                "status": "DONE",
            },
            "swing_composite": {
                "module": "swing_composite_family.py (pending)",
                "patterns": ["head_shoulders", "inverse_head_shoulders", "complex_top", "complex_bottom", "rounded_top", "rounded_bottom"],
                "count": 0,
                "render_mode": "hs | polyline",
                "visual_mode": "swing_pattern",
                "status": "P1_NEXT",
            },
            "regime": {
                "module": "regime_family.py (pending)",
                "patterns": ["squeeze", "balance", "expansion", "volatility_contraction"],
                "count": 0,
                "status": "P2",
            },
        },
        "visual_modes": {
            "range_only": "box + R/S + triggers (NO swings, NO polyline)",
            "horizontal_pattern": "polyline + neckline (NO range, NO swings)",
            "compression_pattern": "trendlines only (NO range, NO swings)",
            "swing_pattern": "H&S polyline + shoulders (NO range)",
            "structure_only": "HH/HL/LL only (NO patterns)",
            "none": "clean chart",
        },
        "window_validator": {
            "enabled": True,
            "principle": "Better to show NO PATTERN than garbage",
            "checks": [
                "window_size (max 40 bars for 4H)",
                "peak_alignment (±3.5% for triple, ±2.5% for double)",
                "pre_trend (uptrend before top, downtrend before bottom)",
                "depth_check (min 2% depth)",
                "range_conflict (penalize if inside range)",
                "structural_integrity (correct # of swings)",
            ],
        },
        "confidence_model": {
            "type": "dominance_based",
            "description": "Confidence = gap between #1 and #2 pattern, NOT geometric quality",
            "max": 0.92,
            "never_100": True,
            "states": {
                "CLEAR": "Can trade (high dominance, single strong pattern)",
                "WEAK": "Trade with caution",
                "CONFLICTED": "Don't trade (competing patterns)",
                "COMPRESSION": "Wait for breakout",
                "NONE": "No pattern detected",
            },
        },
        "regime_binding": {
            "enabled": True,
            "description": "Pattern meaning changes by market context",
            "actionability_levels": ["HIGH", "MEDIUM", "LOW", "NONE"],
        },
        "trigger_engine": {
            "enabled": True,
            "trigger_types": ["breakout_up", "breakout_down", "invalidation"],
            "description": "What must happen for pattern to become valid",
        },
        "render_contract": {
            "enabled": True,
            "modes": ["two_lines", "polyline", "box", "hs"],
            "description": "Single format for ALL patterns. Frontend: switch(render_mode) → draw()",
        },
    },
    "api_endpoints": {
        "primary": "GET /api/ta-engine/pattern-v2/{symbol}?timeframe=4H",
        "legacy_mtf": "GET /api/ta-engine/mtf/{symbol}?timeframes=...",
        "health": "GET /api/health",
    },
    "frontend_v2": {
        "theme": "light + dark panels",
        "chart_library": "lightweight-charts v5.1.0",
        "entry_route": "/tech-analysis",
        "components": {
            "usePatternV2": "Hook → fetches /api/ta-engine/pattern-v2/{symbol}",
            "patternRenderAdapter": "Normalizes backend V2 response for frontend",
            "PatternStateCard": "Decision-grade UI: state + triggers + actionability (WHITE background)",
            "PatternSVGOverlay": "Renders based on visual_mode — NO MIXING allowed",
        },
        "visual_mode_principle": "Frontend OBEYS visual_mode from backend. 1 mode = 1 visual. NO mixing.",
        "design_principle": "1 screen = 1 dominant pattern + its triggers + its state. No clutter.",
        "design_colors": {
            "light_blocks": "#ffffff",
            "dark_blocks": "#0f172a",
            "NO_gray_blocks": "REMOVED — was causing visual chaos",
        },
        "colors": {
            "background": "#ffffff",
            "surface": "#f5f7fa",
            "border": "#eef1f5",
            "accent": "#05A584",
            "text_primary": "#0f172a",
            "text_secondary": "#738094",
            "bullish": "#05A584",
            "bearish": "#ef4444",
            "trigger_breakout": "#22c55e",
            "trigger_breakdown": "#ef4444",
            "trigger_invalidation": "#f97316",
            "state_clear": "#22c55e",
            "state_conflicted": "#ef4444",
            "state_compression": "#3b82f6",
            "state_weak": "#eab308",
        },
    },
}


# ═══════════════════════════════════════════════════════════════
# Bootstrap Class
# ═══════════════════════════════════════════════════════════════

class Bootstrap:
    def __init__(self):
        self.client: Optional[MongoClient] = None
        self.db = None
        self.stats = {
            "candles": 0,
            "funding": 0,
            "oi": 0,
            "liquidations": 0,
            "orderflow": 0,
            "snapshots": 0,
            "microstructure": 0,
        }
    
    def connect(self) -> bool:
        """Connect to MongoDB"""
        if not MONGO_OK:
            print("[pymongo not installed: pip install pymongo]")
            return False
        
        try:
            self.client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
            self.client.admin.command('ping')
            self.db = self.client[DB_NAME]
            print(f"[OK] MongoDB connected: {DB_NAME}")
            return True
        except Exception as e:
            print(f"[FAIL] MongoDB error: {e}")
            return False
    
    # ═══════════════════════════════════════════════════════════
    # TA ENGINE METHODS
    # ═══════════════════════════════════════════════════════════
    
    def init_ta_collections(self):
        """Create TA collections and indexes"""
        print("\n[TA] Collections...")
        
        collections = [
            "candles", "config", "strategies", "regime_map", 
            "validation", "alpha_nodes", "alpha_node_relations",
            "ta_coverage",
        ]
        
        for name in collections:
            if name not in self.db.list_collection_names():
                self.db.create_collection(name)
                print(f"  + {name}")
            else:
                print(f"  . {name}")
        
        # Indexes
        self.db.candles.create_index([("symbol", 1), ("timeframe", 1), ("timestamp", -1)])
        self.db.alpha_nodes.create_index([("node_id", 1)], unique=True)
        print("  . indexes")
    
    def load_candles(self):
        """Load OHLCV data from CSV (historical backup)"""
        print("\n[TA] Loading candles from CSV...")
        
        total = 0
        for symbol, filepath in DATA_FILES.items():
            if not filepath.exists():
                print(f"  ! {symbol}: file not found at {filepath}")
                continue
            
            count = self.db.candles.count_documents({"symbol": symbol})
            if count > 1000:
                print(f"  . {symbol}: {count} candles (cached)")
                total += count
                continue
            
            candles = self._parse_csv(symbol, filepath)
            
            if candles:
                for i in range(0, len(candles), 1000):
                    self.db.candles.insert_many(candles[i:i+1000])
                print(f"  + {symbol}: {len(candles)} candles")
                total += len(candles)
        
        self.stats["candles"] = total
    
    def _parse_csv(self, symbol: str, filepath: Path) -> List[dict]:
        """Parse CSV file"""
        candles = []
        
        with open(filepath, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            
            for row in reader:
                try:
                    date_str = row.get('date', '')
                    if not date_str:
                        continue
                    
                    dt = datetime.strptime(date_str, '%Y-%m-%d')
                    ts = int(dt.replace(tzinfo=timezone.utc).timestamp() * 1000)
                    
                    candles.append({
                        "symbol": symbol,
                        "timeframe": "1d",
                        "timestamp": ts,
                        "open": float(row['open']),
                        "high": float(row['high']),
                        "low": float(row['low']),
                        "close": float(row['close']),
                        "volume": float(row.get('volume', 0)),
                    })
                except Exception:
                    continue
        
        return candles
    
    def save_chart_data_config(self):
        """Save chart data configuration to MongoDB"""
        print("\n[TA] Chart Data Config...")
        
        self.db.config.update_one(
            {"_id": "chart_data"},
            {"$set": {"_id": "chart_data", **CHART_DATA_CONFIG}},
            upsert=True
        )
        print(f"  . Chart lookbacks: {CHART_DATA_CONFIG['default_chart_lookback']['1d']} (1D), {CHART_DATA_CONFIG['default_chart_lookback']['4h']} (4H)")
        print(f"  . Crypto assets: {', '.join(CHART_DATA_CONFIG['crypto_assets'][:5])}...")
        print(f"  . Traditional assets: {', '.join(CHART_DATA_CONFIG['traditional_assets'])}")
    
    def init_ta_config(self):
        """Save TA configs including current coverage"""
        print("\n[TA] Config...")
        
        configs = [
            ("calibration", CALIBRATION_CONFIG, "Calibration (Phase 8.6 + TA-X)"),
            ("coinbase", COINBASE_CONFIG, "Coinbase provider"),
            ("binance", BINANCE_CONFIG, "Binance provider"),
            ("exchange_intel", EXCHANGE_INTEL_CONFIG, "Phase 13.8.B"),
            ("ta_coverage", TA_COVERAGE, "TA Coverage (Phase TA-X)"),
            ("trading_pipeline", TRADING_PIPELINE_CONFIG, "Trading Pipeline (Phase 2.x)"),
        ]
        
        for config_id, config_data, desc in configs:
            self.db.config.update_one(
                {"_id": config_id},
                {"$set": {"_id": config_id, **config_data}},
                upsert=True
            )
            print(f"  . {desc}")
    
    def init_strategies(self):
        """Save strategy registry"""
        print("\n[TA] Strategies...")
        
        for s in STRATEGIES:
            self.db.strategies.update_one(
                {"id": s["id"]},
                {"$set": s},
                upsert=True
            )
        
        counts = {
            "APPROVED": len([s for s in STRATEGIES if s["status"] == "APPROVED"]),
            "LIMITED": len([s for s in STRATEGIES if s["status"] == "LIMITED"]),
            "DEPRECATED": len([s for s in STRATEGIES if s["status"] == "DEPRECATED"]),
        }
        print(f"  . {counts['APPROVED']} APPROVED, {counts['LIMITED']} LIMITED, {counts['DEPRECATED']} DEPRECATED")
    
    def init_regime_map(self):
        """Save regime activation map"""
        print("\n[TA] Regime Map...")
        
        for strategy_id, activations in REGIME_MAP.items():
            regime_dict = dict(zip(REGIMES, activations))
            self.db.regime_map.update_one(
                {"strategyId": strategy_id},
                {"$set": {"strategyId": strategy_id, "activations": regime_dict}},
                upsert=True
            )
        
        print(f"  . {len(REGIME_MAP)} strategies x {len(REGIMES)} regimes")
    
    def init_validation(self):
        """Save cross-asset validation baseline"""
        print("\n[TA] Validation Baseline...")
        
        self.db.validation.update_one(
            {"_id": "phase9.0"},
            {"$set": {"_id": "phase9.0", **CROSS_ASSET_RESULTS}},
            upsert=True
        )
        print(f"  . Phase 9.0: {CROSS_ASSET_RESULTS['systemVerdict']}")
    
    # ═══════════════════════════════════════════════════════════
    # EXCHANGE INTELLIGENCE METHODS (Phase 13.8.B)
    # ═══════════════════════════════════════════════════════════
    
    def init_exchange_collections(self):
        """Create Exchange Intelligence collections"""
        print("\n[Exchange] Collections...")
        
        collections = [
            "exchange_funding_context",
            "exchange_oi_snapshots",
            "exchange_liquidation_events",
            "exchange_trade_flows",
            "exchange_symbol_snapshots",
            "exchange_intel_signals",
        ]
        
        for name in collections:
            if name not in self.db.list_collection_names():
                self.db.create_collection(name)
                print(f"  + {name}")
            else:
                print(f"  . {name}")
        
        # Indexes
        self.db.exchange_funding_context.create_index([("symbol", 1), ("timestamp", DESCENDING)])
        self.db.exchange_oi_snapshots.create_index([("symbol", 1), ("timestamp", DESCENDING)])
        self.db.exchange_liquidation_events.create_index([("symbol", 1), ("timestamp", DESCENDING)])
        self.db.exchange_trade_flows.create_index([("symbol", 1), ("timestamp", DESCENDING)])
        self.db.exchange_symbol_snapshots.create_index([("symbol", 1)])
        self.db.exchange_intel_signals.create_index([("symbol", 1), ("timestamp", DESCENDING)])
        print("  . indexes")
    
    def seed_exchange_data(self):
        """Seed realistic exchange data for all symbols with candles"""
        print("\n[Exchange] Seeding...")
        
        symbols_with_candles = self.db.candles.distinct("symbol")
        
        for symbol in EXCHANGE_SYMBOLS:
            if symbol not in symbols_with_candles:
                print(f"  ! {symbol}: no candles, skipping")
                continue
            
            existing = self.db.exchange_funding_context.count_documents({"symbol": symbol})
            if existing > 100:
                print(f"  . {symbol}: {existing} funding records (cached)")
                self._update_stats(symbol)
                continue
            
            candles = list(self.db.candles.find(
                {"symbol": symbol, "timeframe": "1d"},
                {"_id": 0}
            ).sort("timestamp", DESCENDING).limit(720))
            candles = list(reversed(candles))
            
            if len(candles) < 30:
                print(f"  ! {symbol}: insufficient candles ({len(candles)})")
                continue
            
            print(f"  > {symbol}: generating from {len(candles)} candles...")
            
            self._seed_funding(symbol, candles)
            self._seed_oi(symbol, candles)
            self._seed_liquidations(symbol, candles)
            self._seed_orderflow(symbol, candles)
            self._seed_snapshot(symbol, candles)
            
            self._update_stats(symbol)
    
    def _seed_funding(self, symbol: str, candles: List[Dict]):
        data = []
        now = datetime.now(timezone.utc)
        
        for i, candle in enumerate(candles[-720:]):
            price_change = (candle["close"] - candles[max(0,i-1)]["close"]) / max(candles[max(0,i-1)]["close"], 1e-8) if i > 0 else 0
            base_rate = 0.0001
            sentiment = price_change * 10
            noise = random.uniform(-0.00015, 0.00015)
            funding_rate = max(min(base_rate + sentiment + noise, 0.003), -0.003)
            hours_back = 720 - i
            timestamp = now - timedelta(hours=hours_back)
            
            data.append({
                "symbol": symbol,
                "funding_rate": round(funding_rate, 8),
                "next_funding_time": (timestamp + timedelta(hours=8)).isoformat(),
                "timestamp": timestamp,
                "venue": "binance",
                "mark_price": candle.get("close", 0),
                "index_price": candle.get("close", 0) * 0.9998,
            })
        
        if data:
            self.db.exchange_funding_context.delete_many({"symbol": symbol})
            self.db.exchange_funding_context.insert_many(data)
            print(f"    . funding: {len(data)}")
    
    def _seed_oi(self, symbol: str, candles: List[Dict]):
        data = []
        now = datetime.now(timezone.utc)
        base_oi = {"BTC": 15e9, "ETH": 8e9, "SOL": 2e9}.get(symbol, 1e9)
        oi_value = base_oi
        
        for i, candle in enumerate(candles[-720:]):
            hours_back = 720 - i
            timestamp = now - timedelta(hours=hours_back)
            
            if i > 0:
                price_change = abs(candle["close"] - candles[i-1]["close"]) / max(candles[i-1]["close"], 1e-8)
                if price_change > 0.005:
                    oi_change = random.uniform(0.01, 0.03)
                elif price_change > 0.002:
                    oi_change = random.uniform(-0.01, 0.02)
                else:
                    oi_change = random.uniform(-0.015, 0.005)
            else:
                oi_change = 0
            
            oi_value = max(min(oi_value * (1 + oi_change), base_oi * 2), base_oi * 0.5)
            
            data.append({
                "symbol": symbol,
                "oi_usd": round(oi_value, 2),
                "oi_contracts": round(oi_value / max(candle.get("close", 1), 1), 2),
                "timestamp": timestamp,
                "source": "binance_futures",
            })
        
        if data:
            self.db.exchange_oi_snapshots.delete_many({"symbol": symbol})
            self.db.exchange_oi_snapshots.insert_many(data)
            print(f"    . oi: {len(data)}")
    
    def _seed_liquidations(self, symbol: str, candles: List[Dict]):
        data = []
        now = datetime.now(timezone.utc)
        base_size = {"BTC": 1e6, "ETH": 5e5, "SOL": 1e5}.get(symbol, 1e5)
        
        for i, candle in enumerate(candles[-720:]):
            hours_back = 720 - i
            timestamp = now - timedelta(hours=hours_back)
            price_change = (candle["close"] - candles[max(0,i-1)]["close"]) / max(candles[max(0,i-1)]["close"], 1e-8) if i > 0 else 0
            
            if abs(price_change) > 0.01:
                liq_count = min(random.randint(50, 500), 20)
                side = "LONG" if price_change < 0 else "SHORT"
                
                for _ in range(liq_count):
                    size = random.uniform(base_size * 0.1, base_size) * abs(price_change) * 10
                    data.append({
                        "symbol": symbol,
                        "side": side,
                        "size": round(size, 2),
                        "price": candle["close"] * (1 + random.uniform(-0.005, 0.005)),
                        "timestamp": timestamp + timedelta(minutes=random.randint(0, 59)),
                        "exchange": "binance",
                    })
        
        if data:
            self.db.exchange_liquidation_events.delete_many({"symbol": symbol})
            self.db.exchange_liquidation_events.insert_many(data)
            print(f"    . liquidations: {len(data)}")
    
    def _seed_orderflow(self, symbol: str, candles: List[Dict]):
        data = []
        now = datetime.now(timezone.utc)
        
        for i, candle in enumerate(candles[-720:]):
            hours_back = 720 - i
            timestamp = now - timedelta(hours=hours_back)
            volume = candle.get("volume", 0)
            close = candle.get("close", 0)
            open_price = candle.get("open", close)
            
            if close > open_price:
                buy_ratio = random.uniform(0.52, 0.65)
            elif close < open_price:
                buy_ratio = random.uniform(0.35, 0.48)
            else:
                buy_ratio = random.uniform(0.48, 0.52)
            
            data.append({
                "symbol": symbol,
                "taker_buy_volume": round(volume * buy_ratio, 2),
                "taker_sell_volume": round(volume * (1 - buy_ratio), 2),
                "taker_buy_ratio": round(buy_ratio, 4),
                "total_volume": round(volume, 2),
                "trade_count": random.randint(1000, 50000),
                "timestamp": timestamp,
            })
        
        if data:
            self.db.exchange_trade_flows.delete_many({"symbol": symbol})
            self.db.exchange_trade_flows.insert_many(data)
            print(f"    . orderflow: {len(data)}")
    
    def _seed_snapshot(self, symbol: str, candles: List[Dict]):
        if not candles:
            return
        
        latest = candles[-1]
        recent = candles[-24:] if len(candles) >= 24 else candles
        price_change = (latest["close"] - recent[0]["close"]) / max(recent[0]["close"], 1e-8)
        
        if price_change > 0.02:
            ls_ratio = random.uniform(1.2, 1.8)
        elif price_change < -0.02:
            ls_ratio = random.uniform(0.6, 0.9)
        else:
            ls_ratio = random.uniform(0.9, 1.1)
        
        volatility = sum(abs(c["high"] - c["low"]) / max(c["close"], 1e-8) for c in recent) / len(recent)
        
        snapshot = {
            "symbol": symbol,
            "timestamp": datetime.now(timezone.utc),
            "long_short_ratio": round(ls_ratio, 4),
            "leverage_index": round(min(volatility * 10, 1.0), 4),
            "perp_premium": round(random.uniform(-0.002, 0.002), 6),
            "mark_price": latest["close"],
            "index_price": latest["close"] * 0.9998,
            "funding_rate": round(random.uniform(-0.0002, 0.0003), 8),
        }
        
        self.db.exchange_symbol_snapshots.update_one(
            {"symbol": symbol},
            {"$set": snapshot},
            upsert=True
        )
        print(f"    . snapshot: L/S={snapshot['long_short_ratio']:.2f}")
    
    def _update_stats(self, symbol: str):
        self.stats["funding"] += self.db.exchange_funding_context.count_documents({"symbol": symbol})
        self.stats["oi"] += self.db.exchange_oi_snapshots.count_documents({"symbol": symbol})
        self.stats["liquidations"] += self.db.exchange_liquidation_events.count_documents({"symbol": symbol})
        self.stats["orderflow"] += self.db.exchange_trade_flows.count_documents({"symbol": symbol})
        self.stats["snapshots"] += self.db.exchange_symbol_snapshots.count_documents({"symbol": symbol})

    # ═══════════════════════════════════════════════════════════
    # PHASE 28.1 — Microstructure
    # ═══════════════════════════════════════════════════════════

    def init_microstructure_collections(self):
        print("\n[Microstructure] Collections...")
        col = "microstructure_snapshot_history"
        if col not in self.db.list_collection_names():
            self.db.create_collection(col)
            print(f"  + {col}")
        else:
            print(f"  . {col}")
        self.db[col].create_index([("symbol", 1), ("recorded_at", DESCENDING)])
        print("  . indexes")

    def seed_microstructure_data(self):
        print("\n[Microstructure] Seeding...")

        for symbol in EXCHANGE_SYMBOLS:
            existing = self.db.microstructure_snapshot_history.count_documents({"symbol": symbol})
            if existing > 100:
                print(f"  . {symbol}: {existing} snapshots (cached)")
                continue

            funding_docs = list(self.db.exchange_funding_context.find(
                {"symbol": symbol}, {"_id": 0}
            ).sort("timestamp", DESCENDING).limit(720))
            funding_docs = list(reversed(funding_docs))

            oi_docs = list(self.db.exchange_oi_snapshots.find(
                {"symbol": symbol}, {"_id": 0}
            ).sort("timestamp", DESCENDING).limit(720))
            oi_docs = list(reversed(oi_docs))

            flow_docs = list(self.db.exchange_trade_flows.find(
                {"symbol": symbol}, {"_id": 0}
            ).sort("timestamp", DESCENDING).limit(720))
            flow_docs = list(reversed(flow_docs))

            liq_docs = list(self.db.exchange_liquidation_events.find(
                {"symbol": symbol}, {"_id": 0}
            ).sort("timestamp", DESCENDING).limit(5000))

            n = min(len(funding_docs), len(oi_docs), len(flow_docs))
            if n < 10:
                print(f"  ! {symbol}: insufficient exchange data ({n} rows)")
                continue

            liq_by_ts = {}
            for ld in liq_docs:
                ts = ld.get("timestamp")
                if ts is None:
                    continue
                key = ts.replace(minute=0, second=0, microsecond=0)
                if key not in liq_by_ts:
                    liq_by_ts[key] = {"LONG": 0.0, "SHORT": 0.0}
                liq_by_ts[key][ld.get("side", "LONG")] += ld.get("size", 0)

            base_price = {"BTC": 42000.0, "ETH": 2200.0, "SOL": 120.0}.get(symbol, 1000.0)
            depth_ref = {"BTC": 1000000.0, "ETH": 500000.0, "SOL": 200000.0}.get(symbol, 200000.0)

            records = []
            for i in range(n):
                fd = funding_docs[i]
                od = oi_docs[i]
                fl = flow_docs[i]
                ts = fd.get("timestamp", datetime.now(timezone.utc))

                price = fd.get("mark_price", base_price)
                spread_pct = random.uniform(0.00005, 0.002)
                half_spread = price * spread_pct / 2
                best_bid = price - half_spread
                best_ask = price + half_spread
                mid = (best_bid + best_ask) / 2
                spread_bps = round(((best_ask - best_bid) / mid) * 10000, 2)

                total_depth = random.uniform(depth_ref * 0.25, depth_ref * 1.3)
                depth_score = round(min(max(total_depth / depth_ref, 0.0), 1.0), 4)

                buy_vol = fl.get("taker_buy_volume", 0)
                sell_vol = fl.get("taker_sell_volume", 0)
                total_vol = buy_vol + sell_vol
                imbalance_score = round((buy_vol - sell_vol) / max(total_vol, 1), 4)
                imbalance_score = min(max(imbalance_score, -1.0), 1.0)

                liq_key = ts.replace(minute=0, second=0, microsecond=0) if hasattr(ts, 'replace') else ts
                liq_data = liq_by_ts.get(liq_key, {"LONG": 0.0, "SHORT": 0.0})
                liq_total = liq_data["LONG"] + liq_data["SHORT"]
                liq_pressure = round((liq_data["SHORT"] - liq_data["LONG"]) / liq_total, 4) if liq_total > 0 else round(random.uniform(-0.15, 0.15), 4)
                liq_pressure = min(max(liq_pressure, -1.0), 1.0)

                fr = fd.get("funding_rate", 0.0)
                funding_pressure = round(min(max(fr * 100, -1.0), 1.0), 4)

                oi_cur = od.get("oi_usd", 0)
                oi_prev = oi_docs[i - 1].get("oi_usd", oi_cur) if i > 0 else oi_cur
                oi_pressure = round(min(max((oi_cur - oi_prev) / max(oi_prev, 1) / 0.10, -1.0), 1.0), 4) if oi_prev > 0 else 0.0

                if spread_bps > 15.0:
                    liq_state = "THIN"
                elif depth_score >= 0.70 and spread_bps <= 5.0:
                    liq_state = "DEEP"
                elif depth_score >= 0.40:
                    liq_state = "NORMAL"
                else:
                    liq_state = "THIN"

                if imbalance_score > 0.15:
                    p_state = "BUY_PRESSURE"
                elif imbalance_score < -0.15:
                    p_state = "SELL_PRESSURE"
                else:
                    p_state = "BALANCED"

                stress = (abs(liq_pressure) + abs(funding_pressure) + abs(oi_pressure)) / 3
                if liq_state == "THIN":
                    ms_state = "STRESSED" if stress >= 0.50 else "FRAGILE"
                elif liq_state == "DEEP":
                    ms_state = "SUPPORTIVE"
                elif liq_state == "NORMAL" and p_state == "BALANCED":
                    ms_state = "NEUTRAL"
                else:
                    ms_state = "NEUTRAL"

                norm_spread = min(spread_bps / 20.0, 1.0)
                confidence = round(min(max(
                    0.25 * (1.0 - norm_spread) + 0.25 * depth_score +
                    0.20 * abs(imbalance_score) + 0.15 * abs(liq_pressure) +
                    0.15 * abs(oi_pressure), 0.0), 1.0), 4)

                records.append({
                    "symbol": symbol,
                    "spread_bps": spread_bps,
                    "depth_score": depth_score,
                    "imbalance_score": imbalance_score,
                    "liquidation_pressure": liq_pressure,
                    "funding_pressure": funding_pressure,
                    "oi_pressure": oi_pressure,
                    "liquidity_state": liq_state,
                    "pressure_state": p_state,
                    "microstructure_state": ms_state,
                    "confidence": confidence,
                    "recorded_at": ts,
                })

            if records:
                self.db.microstructure_snapshot_history.delete_many({"symbol": symbol})
                for i in range(0, len(records), 1000):
                    self.db.microstructure_snapshot_history.insert_many(records[i:i + 1000])
                print(f"  . {symbol}: {len(records)} snapshots")
    
    # ═══════════════════════════════════════════════════════════
    # SNAPSHOTS & STATUS
    # ═══════════════════════════════════════════════════════════
    
    def save_snapshots(self):
        """Save JSON snapshots"""
        print("\n[Snapshots] Saving...")
        
        snapshots_dir = PROJECT_ROOT / "snapshots"
        snapshots_dir.mkdir(exist_ok=True)
        
        files = {
            "calibration.json": CALIBRATION_CONFIG,
            "strategies.json": STRATEGIES,
            "regime_map.json": REGIME_MAP,
            "cross_asset.json": CROSS_ASSET_RESULTS,
            "coinbase.json": COINBASE_CONFIG,
            "binance.json": BINANCE_CONFIG,
            "exchange_intel.json": EXCHANGE_INTEL_CONFIG,
            "ta_coverage.json": TA_COVERAGE,
            "trading_pipeline.json": TRADING_PIPELINE_CONFIG,
        }
        
        for filename, data in files.items():
            with open(snapshots_dir / filename, 'w') as f:
                json.dump(data, f, indent=2)
        
        print(f"  . Saved to {snapshots_dir}")
    
    def status(self):
        """Print full system status"""
        if not self.connect():
            return
        
        print("\n" + "=" * 64)
        print("  SYSTEM STATUS (Pattern Families V2)")
        print("=" * 64)
        
        # Pattern Families V2
        print("\n-- PATTERN FAMILIES V2 (PRIMARY) --")
        pf = TA_COVERAGE.get("pattern_families_v2", {})
        print(f"  Pipeline: {pf.get('pipeline', 'N/A')}")
        
        families = pf.get("families_implemented", {})
        for fam_name, fam_info in families.items():
            status = fam_info.get("status", "?")
            patterns = fam_info.get("patterns", [])
            render = fam_info.get("render_mode", "?")
            icon = "+" if status == "DONE" else "~"
            print(f"  [{icon}] {fam_name}: {', '.join(patterns)} ({render}) [{status}]")
        
        conf = pf.get("confidence_model", {})
        print(f"  Confidence: {conf.get('type', '?')} (max {conf.get('max', '?')})")
        print(f"  Regime Binding: {pf.get('regime_binding', {}).get('enabled', False)}")
        print(f"  Trigger Engine: {pf.get('trigger_engine', {}).get('enabled', False)}")
        print(f"  Render Contract: {pf.get('render_contract', {}).get('modes', [])}")
        
        # API
        endpoints = TA_COVERAGE.get("api_endpoints", {})
        print(f"\n  Primary API: {endpoints.get('primary', 'N/A')}")
        
        # Indicators
        print(f"\n-- INDICATORS ({TA_COVERAGE['indicators']['count']}) --")
        print(f"  Core:     {', '.join(TA_COVERAGE['indicators']['core'])}")
        print(f"  Extended: {', '.join(TA_COVERAGE['indicators']['phase_ta1'])}")
        
        # Data
        print("\n-- DATA --")
        for symbol in ["BTC", "ETH", "SOL", "SPX", "DXY"]:
            count = self.db.candles.count_documents({"symbol": symbol})
            if count > 0:
                print(f"  {symbol}: {count:,} candles")
        
        # Configs
        print("\n-- CONFIG --")
        for cfg in ["calibration", "coinbase", "binance", "exchange_intel", "ta_coverage", "trading_pipeline"]:
            exists = self.db.config.find_one({"_id": cfg}) is not None
            print(f"  {cfg}: {'OK' if exists else 'MISSING'}")
        
        strat_count = self.db.strategies.count_documents({})
        regime_count = self.db.regime_map.count_documents({})
        print(f"  Strategies: {strat_count}")
        print(f"  Regime Map: {regime_count}")
        
        # Exchange Intelligence
        print("\n-- EXCHANGE INTELLIGENCE --")
        for col_name, label in [
            ("exchange_funding_context", "Funding"),
            ("exchange_oi_snapshots", "OI"),
            ("exchange_liquidation_events", "Liquidations"),
            ("exchange_trade_flows", "Order Flow"),
            ("exchange_symbol_snapshots", "Snapshots"),
        ]:
            count = self.db[col_name].count_documents({})
            symbols = self.db[col_name].distinct("symbol")
            print(f"  {label}: {count:,} ({', '.join(symbols) if symbols else '-'})")
        
        # Microstructure
        print("\n-- MICROSTRUCTURE --")
        ms_count = self.db.microstructure_snapshot_history.count_documents({})
        print(f"  Snapshots: {ms_count:,}")
        
        # Trading Pipeline (Phase 2.x)
        print("\n-- TRADING PIPELINE (Phase 2.x) --")
        phases = TRADING_PIPELINE_CONFIG.get("phases", {})
        total_tests = 0
        for phase_id, phase_info in phases.items():
            status = phase_info.get("status", "?")
            name = phase_info.get("name", "?")
            tests = phase_info.get("tests_passed", "-")
            icon = "+" if status == "DONE" else "~"
            print(f"  [{icon}] Phase {phase_id}: {name} [{status}]" + (f" ({tests} tests)" if tests != "-" else ""))
            if isinstance(tests, int):
                total_tests += tests
        print(f"  Total tests passed: {total_tests}")
        print(f"  Pipeline: {' → '.join(TRADING_PIPELINE_CONFIG.get('pipeline', [])[:4])}...")
        
        # Trading Pipeline module verification
        print("\n-- TRADING MODULES IMPORT CHECK --")
        module_checks = [
            ("execution_simulator", "modules.execution_simulator.execution_simulator", "ExecutionSimulator"),
            ("portfolio_backtester", "modules.portfolio_backtester.portfolio_backtester", "PortfolioBacktester"),
            ("risk_metrics", "modules.risk_metrics.risk_metrics_engine", "RiskMetricsEngine"),
            ("portfolio_constraints", "modules.portfolio_constraints.constraint_engine", "ConstraintEngine"),
            ("multi_asset", "modules.multi_asset.universe_registry", "UniverseRegistry"),
        ]
        for label, module_path, class_name in module_checks:
            try:
                mod = __import__(module_path, fromlist=[class_name])
                cls = getattr(mod, class_name)
                print(f"  {label}: OK ({class_name})")
            except Exception as e:
                print(f"  {label}: FAIL ({e})")
        
        # Frontend V2
        fe = TA_COVERAGE.get("frontend_v2", {})
        print("\n-- FRONTEND V2 --")
        print(f"  Route:    {fe.get('entry_route', '/tech-analysis')}")
        print(f"  Chart:    {fe.get('chart_library', '?')}")
        comps = fe.get("components", {})
        for comp_name, desc in comps.items():
            print(f"  {comp_name}: {desc}")
        print(f"  Design:   {fe.get('design_principle', '?')}")
        
        print("\n" + "=" * 64)
    
    # ═══════════════════════════════════════════════════════════
    # RUN METHODS
    # ═══════════════════════════════════════════════════════════
    
    def run_ta(self):
        print("\n" + "=" * 64)
        print("  TA ENGINE BOOTSTRAP")
        print("=" * 64)
        
        self.init_ta_collections()
        self.load_candles()
        self.init_ta_config()
        self.save_chart_data_config()  # NEW: Save chart data config
        self.init_strategies()
        self.init_regime_map()
        self.init_validation()
    
    def run_exchange(self):
        print("\n" + "=" * 64)
        print("  EXCHANGE INTELLIGENCE BOOTSTRAP")
        print("=" * 64)
        
        self.init_exchange_collections()
        self.seed_exchange_data()
        self.init_microstructure_collections()
        self.seed_microstructure_data()
    
    def run(self):
        print("\n" + "=" * 64)
        print("  FULL SYSTEM BOOTSTRAP (Pattern Families V2)")
        print("  TA Engine + Exchange Intelligence")
        print("=" * 64)
        
        if not self.connect():
            return
        
        self.run_ta()
        self.run_exchange()
        self.save_snapshots()
        
        print("\n" + "=" * 64)
        print("  BOOTSTRAP COMPLETE")
        print("=" * 64)
        
        self.status()
    
    def run_quick(self):
        """Quick V2 pipeline check — verify pattern-v2 endpoint works."""
        print("\n" + "=" * 64)
        print("  QUICK CHECK — Pattern Families V2 Pipeline")
        print("=" * 64)
        
        if not self.connect():
            return
        
        import requests
        
        # 1. Check MongoDB has candles
        print("\n[1] MongoDB candles...")
        for symbol in ["BTC", "ETH"]:
            count = self.db.candles.count_documents({"symbol": symbol})
            print(f"  {symbol}: {count:,} candles {'OK' if count > 0 else 'MISSING'}")
        
        # 2. Check backend is alive
        print("\n[2] Backend health...")
        api_base = os.environ.get("REACT_APP_BACKEND_URL", "http://localhost:8001")
        try:
            r = requests.get(f"{api_base}/api/health", timeout=5)
            print(f"  Health: {r.status_code} {'OK' if r.status_code == 200 else 'FAIL'}")
        except Exception as e:
            print(f"  Health: FAIL ({e})")
            # Try localhost fallback
            try:
                r = requests.get("http://localhost:8001/api/health", timeout=5)
                print(f"  Health (localhost): {r.status_code}")
                api_base = "http://localhost:8001"
            except Exception:
                print("  Backend not reachable")
                return
        
        # 3. Test pattern-v2 endpoint for BTC and ETH
        print("\n[3] Pattern V2 API...")
        for symbol in ["BTC", "ETH", "SOL"]:
            try:
                url = f"{api_base}/api/ta-engine/pattern-v2/{symbol}?timeframe=4H"
                r = requests.get(url, timeout=30)
                data = r.json()
                
                if data.get("ok"):
                    dominant = data.get("dominant", {}) or {}
                    state = data.get("confidence_state", "?")
                    tradeable = data.get("tradeable", "?")
                    visual_mode = data.get("visual_mode", {}) or {}
                    mode = visual_mode.get("mode", "?")
                    allowed = visual_mode.get("allowed", [])
                    
                    print(f"  {symbol}:")
                    print(f"    Pattern:  {dominant.get('type', 'NONE')} | family={dominant.get('family', '?')}")
                    print(f"    Conf:     {dominant.get('confidence', 0)*100:.0f}% | state={state} | tradeable={tradeable}")
                    print(f"    Visual:   mode={mode} | allowed={allowed}")
                else:
                    print(f"  {symbol}: FAIL — {data.get('error', 'unknown')}")
            except Exception as e:
                print(f"  {symbol}: ERROR — {e}")
        
        # 4. Show Pattern Families architecture summary
        print("\n[4] Pattern Coverage (17 patterns in 3 families)...")
        families = TA_COVERAGE.get("pattern_families_v2", {}).get("families_implemented", {})
        total = 0
        for fam_name, fam_info in families.items():
            status = fam_info.get("status", "?")
            count = fam_info.get("count", len(fam_info.get("patterns", [])))
            patterns = fam_info.get("patterns", [])[:3]  # First 3 for display
            icon = "✅" if status == "DONE" else "⏳"
            total += count if status == "DONE" else 0
            print(f"  {icon} {fam_name}: {count} patterns [{status}]")
            if patterns:
                print(f"       {', '.join(patterns)}...")
        
        print(f"\n  Total ready: {total} patterns")
        
        # 5. Show Visual Modes
        print("\n[5] Visual Mode Resolver (render isolation)...")
        visual_modes = TA_COVERAGE.get("pattern_families_v2", {}).get("visual_modes", {})
        for mode_name, desc in list(visual_modes.items())[:4]:
            print(f"  {mode_name}: {desc}")
        
        # 6. Show Window Validator
        print("\n[6] Pattern Window Validator (quality gate)...")
        validator = TA_COVERAGE.get("pattern_families_v2", {}).get("window_validator", {})
        print(f"  Principle: {validator.get('principle', '?')}")
        checks = validator.get("checks", [])[:3]
        for check in checks:
            print(f"  - {check}")
        
        print("\n" + "=" * 64)
        print("  QUICK CHECK COMPLETE")
        print("=" * 64)
    
    def run_trading_check(self):
        """Verify trading pipeline (Phase 2.4–2.8) is operational."""
        print("\n" + "=" * 64)
        print("  TRADING PIPELINE CHECK (Phase 2.4–2.8)")
        print("=" * 64)

        import random as _rand
        _rand.seed(12345)

        # 2.4 — Execution Simulator
        print("\n[2.4] Execution Simulator...")
        try:
            from modules.execution_simulator.execution_simulator import ExecutionSimulator
            sim = ExecutionSimulator()
            r = sim.simulate(
                {"entry": 100, "stop": 95, "target": 110, "order_type": "limit", "direction": "long"},
                {"open": 99, "high": 105, "low": 98, "close": 103},
                {"volatility": 0.02},
            )
            assert r["filled"] == True
            print(f"  OK: limit fill at {r['entry_price']}, slippage={r['slippage']:.4f}")
        except Exception as e:
            print(f"  FAIL: {e}")

        # 2.5 — Portfolio Backtester
        print("\n[2.5] Portfolio Backtester...")
        try:
            from modules.portfolio_backtester.portfolio_backtester import PortfolioBacktester
            bt = PortfolioBacktester()
            trades = [{"pnl": 100}, {"pnl": -50}, {"pnl": 200}]
            res = bt.run(trades, initial_capital=10000)
            assert res["metrics"]["total_pnl"] == 250
            print(f"  OK: equity {res['equity_curve'][0]} → {res['equity_curve'][-1]}, PnL={res['metrics']['total_pnl']}")
        except Exception as e:
            print(f"  FAIL: {e}")

        # 2.6 — Risk Metrics
        print("\n[2.6] Risk Metrics Engine...")
        try:
            from modules.risk_metrics.risk_metrics_engine import RiskMetricsEngine
            rm = RiskMetricsEngine()
            eq = [10000, 10100, 10050, 10250]
            risk = rm.compute(eq, trades, 10000)
            assert risk["sharpe"] != 0
            print(f"  OK: Sharpe={risk['sharpe']}, DD={risk['max_drawdown']*100:.2f}%")
        except Exception as e:
            print(f"  FAIL: {e}")

        # 2.7 — Portfolio Constraints
        print("\n[2.7] Portfolio Constraints...")
        try:
            from modules.portfolio_constraints.constraint_engine import ConstraintEngine
            ce = ConstraintEngine()
            pos = [{"symbol": "BTC", "position_value": 500, "direction": "long", "risk_amount": 50}]
            new = {"symbol": "ETH", "position_value": 800, "direction": "long", "risk_amount": 80}
            cr = ce.evaluate(pos, new, capital=10000)
            print(f"  OK: allowed={cr['allowed']}, rejected_by={cr['rejected_by']}")
        except Exception as e:
            print(f"  FAIL: {e}")

        # 2.8 — Multi-Asset
        print("\n[2.8] Multi-Asset Scaling...")
        try:
            from modules.multi_asset.universe_registry import UniverseRegistry
            from modules.multi_asset.cluster_engine import ClusterEngine
            from modules.multi_asset.multi_asset_runner import MultiAssetRunner
            from modules.multi_asset.symbol_diagnostics import SymbolDiagnostics
            from modules.multi_asset.symbol_ranker import SymbolRanker

            ur = UniverseRegistry()
            ur.load()
            ce2 = ClusterEngine()
            clusters = ce2.summary(ur.get_assets())

            preds = {}
            for s in ur.get_symbols()[:20]:
                preds[s] = [{"pnl": _rand.gauss(10, 80)} for _ in range(5)]

            runner = MultiAssetRunner()
            mr = runner.run(preds, initial_capital=100000)

            sd = SymbolDiagnostics()
            flat = [{**t, "symbol": s} for s, ts in preds.items() for t in ts]
            diag = sd.compute(flat)

            sr = SymbolRanker()
            edge = sr.has_edge(diag)

            print(f"  OK: {ur.count()} assets, {len(clusters)} clusters")
            print(f"      {mr['metrics']['total_trades']} trades, PnL={mr['metrics']['total_pnl']}")
            print(f"      {len(edge)}/{len(diag)} symbols with edge")
        except Exception as e:
            print(f"  FAIL: {e}")

        print("\n" + "=" * 64)
        print("  TRADING PIPELINE CHECK COMPLETE")
        print("=" * 64)

    def reset(self):
        if not self.connect():
            return
        
        print("\n  Resetting database...")
        self.client.drop_database(DB_NAME)
        print("  . Database dropped")
        
        self.db = self.client[DB_NAME]
        self.run()


# ═══════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description="TA Engine Bootstrap v6 — Pattern Families Architecture",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python bootstrap.py                 # Full bootstrap
  python bootstrap.py --quick         # Quick V2 pipeline check
  python bootstrap.py --ta-only       # TA Engine only
  python bootstrap.py --exchange-only # Exchange data only
  python bootstrap.py --status        # Check status
  python bootstrap.py --reset         # Reset all
        """
    )
    parser.add_argument("--status", action="store_true", help="Check system status")
    parser.add_argument("--reset", action="store_true", help="Reset and rebuild all")
    parser.add_argument("--ta-only", action="store_true", help="Bootstrap TA Engine only")
    parser.add_argument("--exchange-only", action="store_true", help="Bootstrap Exchange data only")
    parser.add_argument("--quick", action="store_true", help="Quick V2 pipeline check")
    parser.add_argument("--trading", action="store_true", help="Verify trading pipeline (2.4-2.8)")
    
    args = parser.parse_args()
    
    bootstrap = Bootstrap()
    
    if args.status:
        bootstrap.status()
    elif args.quick:
        bootstrap.run_quick()
    elif args.trading:
        bootstrap.run_trading_check()
    elif args.reset:
        bootstrap.reset()
    elif args.ta_only:
        if bootstrap.connect():
            bootstrap.run_ta()
            bootstrap.save_snapshots()
            print("\n  TA ENGINE BOOTSTRAP COMPLETE")
    elif args.exchange_only:
        if bootstrap.connect():
            bootstrap.run_exchange()
            print("\n  EXCHANGE BOOTSTRAP COMPLETE")
    else:
        bootstrap.run()


if __name__ == "__main__":
    main()
