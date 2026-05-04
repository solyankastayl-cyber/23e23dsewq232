"""
Per-Timeframe TA Builder
========================

Builds COMPLETE TA payload for a single timeframe.
Each TF is an isolated world — NO mixing between timeframes.

Output for each TF:
  {
    "timeframe": "4H",
    "candles": [...],
    "decision": {...},
    "structure_context": {...},
    "liquidity": {...},
    "displacement": {...},
    "fib": {...},
    "poi": {...},
    "primary_pattern": {...},
    "unified_setup": {...},
    "trade_setup": {...},
    "execution": {...},
    "base_layer": {...},
    "chain_map": [...]   # For chain highlighting
  }
"""

from __future__ import annotations
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

# Import all engines
from modules.ta_engine.setup.pattern_validator_v2 import get_pattern_validator_v2
from modules.ta_engine.setup.structure_engine_v2 import get_structure_engine_v2
from modules.ta_engine.setup.structure_context_engine import structure_context_engine
from modules.ta_engine.setup.pattern_ranking_engine import pattern_ranking_engine
from modules.ta_engine.setup.pattern_selector import get_pattern_selector

# NEW: Structure Builder v2 + Pattern Engine v3
from modules.ta_engine.setup.structure_builder import get_structure_builder
from modules.ta_engine.setup.pattern_engine_v3 import get_pattern_engine_v3

# NEW: Anchor-based pattern engine (PRO level)
from modules.ta_engine.anchor_pattern_engine import get_best_pattern, detect_patterns

# Get singleton instance
pattern_selector = get_pattern_selector()
from modules.ta_engine.setup.pattern_expiration import pattern_expiration_engine
from modules.ta_engine.setup.pattern_registry import run_all_detectors, filter_by_structure, penalize_overused_patterns, validate_candidate

# IMPORTANT: Import pattern_detectors_unified to register all detectors
# This triggers @register_pattern decorators at import time
from modules.ta_engine.setup import pattern_detectors_unified  # noqa: F401

# Ranking Engine V2 — Context-Aware Decision System
from modules.ta_engine.pattern_ranking_engine_v2 import (
    rank_patterns_v2,
    compute_confidence_state,
    compute_market_quality,
)

# Entry Engine — Trade Setup Builder (ONLY when CLEAR)
from modules.ta_engine.entry_engine import build_trade_setup

# PRO Pattern Engine (final layer)
from modules.ta_engine.pro_pattern_engine import run_pro_pattern_engine, build_ui_pattern_payload

from modules.ta_engine.decision import get_decision_engine_v2
from modules.ta_engine.scenario import get_scenario_engine_v3
from modules.ta_engine.structure import get_choch_validation_engine
from modules.ta_engine.liquidity import get_liquidity_engine
from modules.ta_engine.displacement import get_displacement_engine
from modules.ta_engine.poi import get_poi_engine
from modules.ta_engine.fibonacci import get_fibonacci_engine
from modules.ta_engine.trade_setup import get_trade_setup_generator
from modules.ta_engine.setup.unified_setup_engine import get_unified_setup_engine
from modules.ta_engine.execution import get_execution_layer
from modules.ta_engine.setup.indicator_engine import get_indicator_engine
from modules.ta_engine.indicators import get_indicator_registry, get_confluence_engine
from modules.ta_engine.indicators.indicator_visualization import IndicatorVisualizationEngine
from modules.ta_engine.indicators.indicator_insights import get_indicator_insights_engine
from modules.ta_engine.contribution import get_contribution_engine
from modules.ta_engine.render_plan import get_render_plan_engine_v2
from modules.ta_engine.market_state import get_market_state_engine
from modules.ta_engine.patterns.pattern_geometry_contract import normalize_pattern_geometry
from modules.ta_engine.structure import StructureVisualizationBuilder

# Final Analysis Resolver - NEVER returns empty
from modules.ta_engine.setup.final_analysis_resolver import get_final_analysis_resolver

# Pattern Priority System - selects ONE dominant pattern
from modules.ta_engine.setup.pattern_priority_system import get_pattern_priority_system

# Render Stack Builder - Multi-pattern visualization (1 dominant + 2 secondary)
from modules.ta_engine.pattern_families.render_stack_builder import build_render_stack

# Watch Levels Engine — "What to Watch" (breakout/breakdown levels)
from modules.ta_engine.watch_levels_engine import build_watch_levels

# Pattern Lifecycle Engine — forming / confirmed / invalidated
from modules.ta_engine.pattern_lifecycle_engine import build_lifecycle

# Geometry Layer - builds & validates geometry
from modules.ta_engine.geometry.pattern_geometry_builder import get_pattern_geometry_builder
from modules.ta_engine.geometry.wedge_shape_validator import get_wedge_shape_validator
from modules.ta_engine.geometry.main_render_gate import get_main_render_gate
from modules.ta_engine.geometry.geometry_normalizer import get_geometry_normalizer, normalize_pattern
from modules.ta_engine.geometry.pattern_projection_engine import get_pattern_projection_engine
from modules.ta_engine.geometry.render_profile import configure_pattern_render, get_render_profile


# Singleton for visualization engine
_indicator_viz_engine = None
_render_plan_engine_v2 = None
_market_state_engine = None
_structure_viz_builder = None

def get_indicator_viz_engine():
    global _indicator_viz_engine
    if _indicator_viz_engine is None:
        _indicator_viz_engine = IndicatorVisualizationEngine()
    return _indicator_viz_engine

def _get_render_plan_engine():
    global _render_plan_engine_v2
    if _render_plan_engine_v2 is None:
        _render_plan_engine_v2 = get_render_plan_engine_v2()
    return _render_plan_engine_v2

def _get_market_state_engine():
    global _market_state_engine
    if _market_state_engine is None:
        _market_state_engine = get_market_state_engine()
    return _market_state_engine

def _get_structure_viz_builder():
    global _structure_viz_builder
    if _structure_viz_builder is None:
        _structure_viz_builder = StructureVisualizationBuilder()
    return _structure_viz_builder


# TF Configuration
TF_CONFIG = {
    "1H": {
        "lookback": 168,        # 7 days of hourly
        "pivot_window": 2,
        "min_pivot_distance": 3,
        "pattern_window": 120,
        "candle_type": "1h",
        "description": "Micro entry timing"
    },
    "4H": {
        "lookback": 200,
        "pivot_window": 3,
        "min_pivot_distance": 5,
        "pattern_window": 150,
        "candle_type": "4h",
        "description": "Entry timing"
    },
    "1D": {
        "lookback": 150,
        "pivot_window": 5,
        "min_pivot_distance": 8,
        "pattern_window": 100,
        "candle_type": "1d",
        "description": "Setup patterns"
    },
    "7D": {
        "lookback": 65,        # ~65 weekly candles = ~1.2 years
        "pivot_window": 2,      # Smaller for aggregated data
        "min_pivot_distance": 2,
        "pattern_window": 50,
        "candle_type": "7d",
        "description": "Weekly formations"
    },
    # 1M - Monthly (proper TA name)
    "1M": {
        "lookback": 42,         # ~42 monthly candles = ~3.5 years
        "pivot_window": 2,      # Very small for monthly
        "min_pivot_distance": 1,
        "pattern_window": 30,
        "candle_type": "1M",
        "description": "Monthly structure"
    },
    # 30D - Legacy alias for 1M
    "30D": {
        "lookback": 42,         # Same as 1M
        "pivot_window": 2,
        "min_pivot_distance": 1,
        "pattern_window": 30,
        "candle_type": "30d",
        "description": "Monthly structure (legacy)"
    },
    # 6M - Semi-annual (proper TA name)
    "6M": {
        "lookback": 12,         # ~12 half-year candles = ~6 years
        "pivot_window": 1,      # Minimal for 6-month
        "min_pivot_distance": 1,
        "pattern_window": 10,
        "candle_type": "6M",
        "description": "Macro cycles"
    },
    # 180D - Legacy alias for 6M
    "180D": {
        "lookback": 12,         # Same as 6M
        "pivot_window": 1,
        "min_pivot_distance": 1,
        "pattern_window": 10,
        "candle_type": "180d",
        "description": "Macro cycles (legacy)"
    },
    "1Y": {
        "lookback": 11,         # ~11 yearly candles = ~11 years
        "pivot_window": 1,      # Minimal for yearly
        "min_pivot_distance": 1,
        "pattern_window": 8,
        "candle_type": "1Y",
        "description": "Secular trends"
    },
}


class PerTimeframeBuilder:
    """
    Builds complete TA payload for ONE timeframe.
    Isolated from other timeframes — each TF is its own world.
    """
    
    def build(
        self,
        candles: List[Dict[str, Any]],
        symbol: str,
        timeframe: str,
        mtf_context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Build complete TA for a single timeframe.
        
        Args:
            candles: OHLCV candles for this specific timeframe
            symbol: Trading pair (e.g., "BTCUSDT")
            timeframe: The timeframe string (e.g., "4H", "1D")
            mtf_context: Optional MTF context for alignment calculation
        """
        import time as time_module
        start_time = time_module.time()
        print(f"[PerTF] Starting build for {symbol}:{timeframe} with {len(candles)} candles")
        
        config = TF_CONFIG.get(timeframe, TF_CONFIG["1D"])
        
        # ═══════════════════════════════════════════════════════════════
        # HTF ROUTING — Use HTF Context Engine for macro timeframes
        # ═══════════════════════════════════════════════════════════════
        HTF_TIMEFRAMES = {"1M", "30D", "6M", "180D", "1Y"}
        
        if timeframe.upper() in HTF_TIMEFRAMES:
            print(f"[PerTF] Routing to HTF Context Engine for {timeframe}")
            return self._build_htf_context(candles, symbol, timeframe)
        
        # Minimum candles depends on timeframe
        # Higher TFs like 180D and 1Y have limited historical data
        MIN_CANDLES_MAP = {
            "1H": 30,
            "4H": 30,
            "1D": 30,
            "7D": 20,
            "30D": 10,
            "180D": 5,
            "1Y": 5,
        }
        min_candles = MIN_CANDLES_MAP.get(timeframe.upper(), 30)
        
        # Empty result template
        empty = self._empty_result(timeframe, symbol)
        
        if len(candles) < min_candles:
            print(f"[PerTF] Not enough candles ({len(candles)} < {min_candles})")
            return empty
        
        current_price = float(candles[-1]["close"])
        
        # =============================================
        # STEP 1: STRUCTURE ANALYSIS (FIRST!)
        # =============================================
        print(f"[PerTF] Step 1: Structure analysis...")
        structure_v2 = get_structure_engine_v2(timeframe)
        validator = get_pattern_validator_v2(timeframe.upper(), config)
        pivot_highs_raw, pivot_lows_raw = validator.find_pivots(candles)
        print(f"[PerTF] Found {len(pivot_highs_raw)} highs, {len(pivot_lows_raw)} lows")
        
        # Convert Pivot objects to dicts for engines that need dict
        pivot_highs = [
            {"price": p.value, "index": p.index, "time": p.time}
            for p in pivot_highs_raw
        ]
        pivot_lows = [
            {"price": p.value, "index": p.index, "time": p.time}
            for p in pivot_lows_raw
        ]
        
        if len(pivot_highs) < 2 or len(pivot_lows) < 2:
            print(f"[PerTF] Not enough pivots (highs={len(pivot_highs)}, lows={len(pivot_lows)})")
            # For higher timeframes with limited data, proceed with available pivots
            if timeframe.upper() in ("180D", "1Y") and (len(pivot_highs) >= 1 or len(pivot_lows) >= 1):
                print(f"[PerTF] Proceeding with limited pivots for {timeframe}")
            else:
                return empty
        
        print(f"[PerTF] Building structure_state...")
        structure_state = structure_v2.build(
            candles=candles,
            pivots_high=pivot_highs,
            pivots_low=pivot_lows,
        )
        
        print(f"[PerTF] Building structure_context...")
        structure_context = structure_context_engine.build(
            candles=candles,
            pivots_high=pivot_highs,
            pivots_low=pivot_lows,
        )
        
        # Convert to dict for engines that need dict
        structure_context_dict = structure_context.to_dict()
        
        # =============================================
        # STEP 2: LIQUIDITY & DISPLACEMENT
        # =============================================
        print(f"[PerTF] Step 2: Liquidity & Displacement...")
        liquidity_engine = get_liquidity_engine()
        liquidity = liquidity_engine.build(candles)
        
        displacement_engine = get_displacement_engine()
        displacement = displacement_engine.build(candles)
        
        # =============================================
        # STEP 3: CHOCH VALIDATION
        # =============================================
        print(f"[PerTF] Step 3: CHOCH validation...")
        choch_engine = get_choch_validation_engine()
        choch_validation = choch_engine.build(
            structure_context=structure_context_dict,
            liquidity=liquidity,
            displacement=displacement,
            base_layer={},
        )
        
        # =============================================
        # STEP 4: POI & FIBONACCI
        # =============================================
        print(f"[PerTF] Step 4: POI & Fibonacci...")
        poi_engine = get_poi_engine()
        poi = poi_engine.build(candles, displacement)
        
        fib_engine = get_fibonacci_engine()
        fib = fib_engine.build(candles, pivot_highs, pivot_lows, structure_context_dict, timeframe)
        
        # =============================================
        # STEP 5: PATTERN DETECTION (Using Pattern Engine v3)
        # =============================================
        print(f"[PerTF] Step 5: Pattern detection...")
        
        # NEW: Build clean structure from pivots using Structure Builder v2
        structure_builder = get_structure_builder(timeframe)
        
        # Combine pivot highs and lows with type info
        # Handle both dict and Pivot objects
        combined_pivots = []
        for h in pivot_highs_raw:
            if hasattr(h, 'value'):
                # Pivot object
                p = {
                    "value": h.value,
                    "price": h.value,
                    "time": h.time if hasattr(h, 'time') else 0,
                    "index": h.index if hasattr(h, 'index') else 0,
                    "type": "high",
                }
            elif isinstance(h, dict):
                p = h.copy()
                p["type"] = "high"
                p["price"] = p.get("value", p.get("price", 0))
            else:
                continue
            combined_pivots.append(p)
        
        for l in pivot_lows_raw:
            if hasattr(l, 'value'):
                # Pivot object
                p = {
                    "value": l.value,
                    "price": l.value,
                    "time": l.time if hasattr(l, 'time') else 0,
                    "index": l.index if hasattr(l, 'index') else 0,
                    "type": "low",
                }
            elif isinstance(l, dict):
                p = l.copy()
                p["type"] = "low"
                p["price"] = p.get("value", p.get("price", 0))
            else:
                continue
            combined_pivots.append(p)
        
        # Sort by index/time
        combined_pivots.sort(key=lambda x: x.get("index", x.get("time", 0)))
        
        # Build clean structure
        clean_structure = structure_builder.build(combined_pivots)
        print(f"[PerTF] Clean structure: {len(clean_structure['structure'])} points, "
              f"{len(clean_structure['highs'])} highs, {len(clean_structure['lows'])} lows")
        
        # NEW: Use Pattern Engine v3 for detection
        pattern_engine = get_pattern_engine_v3(timeframe)
        v3_patterns = pattern_engine.detect(clean_structure)
        print(f"[PerTF] Pattern Engine v3 found: {len(v3_patterns)} patterns")
        
        # Also run legacy detectors for compatibility
        all_candidates = run_all_detectors(
            candles=candles,
            pivots_high=pivot_highs_raw,
            pivots_low=pivot_lows_raw,
            levels=[],
            structure_ctx=structure_context,
            timeframe=timeframe,
            config=config
        )
        print(f"[PerTF] Legacy detectors found: {len(all_candidates)}")
        
        # Convert v3 patterns to PatternCandidate format
        for v3_pat in v3_patterns:
            from modules.ta_engine.setup.pattern_candidate import PatternCandidate
            
            # Get geometry from v3 pattern
            v3_geo = v3_pat.geometry
            
            # Build points dict for PatternCandidate
            points = {}
            if "upper" in v3_geo:
                points["upper"] = v3_geo["upper"]
            if "lower" in v3_geo:
                points["lower"] = v3_geo["lower"]
            if "peaks" in v3_geo:
                points["peaks"] = v3_geo["peaks"]
            if "troughs" in v3_geo:
                points["troughs"] = v3_geo["troughs"]
            if "neckline" in v3_geo:
                points["neckline"] = [v3_geo["neckline"]] if isinstance(v3_geo["neckline"], dict) else v3_geo["neckline"]
            if "markers" in v3_geo:
                points["markers"] = v3_geo["markers"]
            
            candidate = PatternCandidate(
                type=v3_pat.type,
                direction=v3_pat.direction,
                confidence=v3_pat.confidence,
                geometry_score=0.8,  # v3 patterns have validated geometry
                touch_count=v3_pat.touches_upper + v3_pat.touches_lower,
                containment=0.7,
                line_scores={"upper": v3_pat.touches_upper * 10, "lower": v3_pat.touches_lower * 10},
                points=points,
                anchor_points=v3_geo.get("anchor_highs", []) + v3_geo.get("anchor_lows", []),
                start_index=0,
                end_index=len(candles) - 1,
                last_touch_index=len(candles) - 1,
            )
            all_candidates.append(candidate)
        
        print(f"[PerTF] Total candidates: {len(all_candidates)}")
        for c in all_candidates[:5]:
            print(f"[PerTF]   - {c.type}: geo={c.geometry_score:.2f}, conf={c.confidence:.2f}")
        
        # Validate and filter
        validated = [c for c in all_candidates if validate_candidate(c)]
        print(f"[PerTF] After validation: {len(validated)}")
        
        gated = filter_by_structure(validated, structure_context)
        print(f"[PerTF] After structure filter: {len(gated)}")
        
        # Hard filter for recency
        filtered = self._hard_filter_recency(gated, candles)
        print(f"[PerTF] After recency filter: {len(filtered)}")
        
        # Expire old patterns
        live = pattern_expiration_engine.filter_expired(filtered, len(candles) - 1, timeframe)
        print(f"[PerTF] After expiration: {len(live)}")
        
        # Rank patterns
        ranked = pattern_ranking_engine.rank(
            candidates=live,
            structure_ctx=structure_context,
            levels=[],
            current_price=current_price,
        )
        
        # Penalize overused
        diversified = penalize_overused_patterns(ranked)
        
        # Select best with market context using PSE v2.0
        primary_pattern, alternatives = pattern_selector.select(
            diversified,
            candles=candles,
            current_price=current_price,
            market_state=structure_context_dict,
            structure_context=structure_context_dict,
            levels=[],
            liquidity=liquidity,
            fib=fib,
            poi=poi,
        )
        print(f"[PerTF] Pattern selected: {primary_pattern.type if primary_pattern else 'None'}")
        
        # =============================================
        # STEP 5A: DOMINANCE FILTER (NEW!)
        # Pattern must be DOMINANT (coverage > 20%)
        # Otherwise → structure fallback
        # =============================================
        dominance_score = None
        pattern_rejections = []
        
        if primary_pattern:
            priority_system = get_pattern_priority_system()
            dominant_pattern, dominance_score, pattern_rejections = priority_system.select_primary(
                [primary_pattern] + (alternatives or []),
                candles,
                timeframe,
            )
            
            if dominant_pattern:
                # Pattern passes dominance check
                primary_pattern = dominant_pattern
                print(f"[PerTF] ✅ DOMINANT pattern: {primary_pattern.type} "
                      f"(coverage={dominance_score.coverage:.1%}, score={dominance_score.final_score:.2f})")
            else:
                # Pattern rejected - too small or low score → structure fallback
                print(f"[PerTF] ❌ Pattern rejected (not dominant): {pattern_rejections}")
                primary_pattern = None
                alternatives = []
        
        # =============================================
        # STEP 5B: PATTERN RENDER CONTRACT V8 (HISTORY SCAN)
        # =============================================
        print(f"[PerTF] Step 5b: Scanning history for patterns...")
        try:
            # NEW V8: Use History Scanner - find LAST VALID STRUCTURE
            from modules.ta_engine.pattern.anchor_pattern_builder import get_anchor_pattern_builder
            from modules.ta_engine.pattern_history_scanner import PatternHistoryScanner
            
            anchor_builder = get_anchor_pattern_builder()
            
            # Create detector function for scanner
            def detect_pattern_in_window(window_candles):
                return anchor_builder.build(window_candles)
            
            # Initialize scanner
            scanner = PatternHistoryScanner()
            
            # Scan history - pass detector as argument (not stored)
            pattern_render_contract, alt_render_contracts = scanner.scan(
                candles, 
                timeframe,
                pattern_detector=detect_pattern_in_window
            )
            
            if pattern_render_contract:
                # Mark as V8 HISTORY SCAN engine
                pattern_render_contract["engine"] = "V8_HISTORY_SCAN"
                pattern_render_contract["source"] = "HISTORY_SCAN_V8"
                
                is_fallback = pattern_render_contract.get("is_fallback", False)
                
                if is_fallback:
                    print(f"[PerTF] 📊 Structure fallback: {pattern_render_contract.get('direction')}")
                else:
                    print(f"[PerTF] ✅ History scan pattern: {pattern_render_contract.get('type')} "
                          f"score={pattern_render_contract.get('_final_score', 0):.2f} "
                          f"recency={pattern_render_contract.get('_recency', 0):.2f}")
                
                # Mark alternatives
                for i, alt in enumerate(alt_render_contracts):
                    alt["engine"] = "V8_HISTORY_SCAN"
                    alt["source"] = "HISTORY_SCAN_V8"
                    alt["is_alternative"] = True
                    alt["alternative_rank"] = i + 1
            else:
                print(f"[PerTF] ⚠️ No pattern found even with history scan")
                alt_render_contracts = []
            
        except Exception as e:
            print(f"[PerTF] Pattern build error: {e}")
            import traceback
            traceback.print_exc()
            pattern_render_contract = None
            alt_render_contracts = []
        
        # ═══════════════════════════════════════════════════════════════
        # STEP 5c: PATTERN DETECTION via ta_pipeline_v2 ONLY
        # ═══════════════════════════════════════════════════════════════
        # CRITICAL: NO FALLBACK TO OLD PIPELINE
        USE_TA_PIPELINE_V2_ONLY = True
        
        print(f"[PerTF] Step 5c: Pattern detection (V2 ONLY)...")
        display_message = None
        candidate_pattern = None
        geometry_contract_dict = None  # For final_analysis UI
        
        if USE_TA_PIPELINE_V2_ONLY:
            try:
                from modules.ta_engine.ta_pipeline_v2 import get_pattern_contract_v2
                pattern_render_contract = get_pattern_contract_v2(candles, timeframe)
                
                if pattern_render_contract:
                    pattern_render_contract["engine"] = "V2_MULTI_LAYER"
                    pattern_render_contract["source"] = "TA_PIPELINE_V2"
                    pattern_render_contract["pipeline_source"] = "v2"
                    
                    # ═══════════════════════════════════════════════════════════
                    # GEOMETRY LAYER - Full Validation Pipeline
                    # ═══════════════════════════════════════════════════════════
                    
                    # EXTRACT boundaries and debug FIRST (CRITICAL!)
                    boundaries = pattern_render_contract.get("boundaries", [])
                    debug = pattern_render_contract.get("debug", {})
                    pattern_type = pattern_render_contract.get("type", "")
                    
                    print(f"[PerTF] Extracted: type={pattern_type}, boundaries={len(boundaries)}, "
                          f"debug_keys={list(debug.keys())}")
                    
                    # 1. Build geometry contract
                    geometry_builder = get_pattern_geometry_builder()
                    geometry_contract = geometry_builder.build(
                        pattern_type=pattern_type,
                        boundaries=boundaries,
                        candles=candles,
                        debug_info=debug,
                    )
                    
                    print(f"[PerTF] Geometry built: valid={geometry_contract.is_valid}, "
                          f"compression={geometry_contract.compression_ratio:.2f}, "
                          f"cleanliness={geometry_contract.cleanliness:.2f}")
                    
                    # 2. Validate shape (wedge-specific)
                    shape_validation = None
                    
                    if "wedge" in pattern_type:
                        wedge_validator = get_wedge_shape_validator()
                        shape_validation = wedge_validator.validate(
                            pattern_type=pattern_type,
                            upper_slope=geometry_contract.upper_slope,
                            lower_slope=geometry_contract.lower_slope,
                            compression_ratio=geometry_contract.compression_ratio,
                            touches_upper=debug.get("touch_upper", 2),
                            touches_lower=debug.get("touch_lower", 2),
                            cleanliness=geometry_contract.cleanliness,
                            apex_distance_bars=0,
                            window_bars=debug.get("window_bars", 20),
                        )
                        print(f"[PerTF] Wedge shape validation: valid={shape_validation.is_valid}, "
                              f"reason={shape_validation.reason}")
                    
                    # 3. Calculate coverage for render gate
                    total_range = max(c["high"] for c in candles) - min(c["low"] for c in candles)
                    
                    upper_val = geometry_contract.upper_boundary.get("y1", 0)
                    lower_val = geometry_contract.lower_boundary.get("y1", 0)
                    if upper_val == 0:
                        # Fallback to extracting from boundaries list
                        for b in boundaries:
                            if isinstance(b, dict):
                                if "upper" in b.get("id", ""):
                                    upper_val = max(b.get("y1", 0), b.get("y2", 0))
                                elif "lower" in b.get("id", ""):
                                    lower_val = min(b.get("y1", 0), b.get("y2", 0))
                    
                    pattern_range = abs(upper_val - lower_val) if upper_val and lower_val else 0
                    coverage_ratio = pattern_range / total_range if total_range > 0 else 0
                    window_bars = debug.get("window_bars", 20)
                    
                    # 4. Main Render Gate
                    render_gate = get_main_render_gate()
                    gate_result = render_gate.check(
                        timeframe=timeframe,
                        geometry_contract=geometry_contract.to_dict() if geometry_contract else None,
                        shape_validation=shape_validation.to_dict() if shape_validation else {"is_valid": True},
                        coverage_ratio=coverage_ratio,
                        window_bars=window_bars,
                        touches_upper=debug.get("touch_upper", 2),
                        touches_lower=debug.get("touch_lower", 2),
                        cleanliness=geometry_contract.cleanliness if geometry_contract else 0.5,
                    )
                    
                    print(f"[PerTF] Render Gate: should_render={gate_result.should_render}, "
                          f"coverage={gate_result.coverage_ratio:.1%}, "
                          f"required={gate_result.required_coverage:.0%}")
                    
                    if not gate_result.should_render:
                        print(f"[PerTF] ❌ Pattern REJECTED by Render Gate: {gate_result.reason}")
                        pattern_render_contract = None
                        display_message = gate_result.reason or "Pattern does not meet display criteria."
                    else:
                        print(f"[PerTF] ✅ Pattern PASSED Render Gate")
                        # Add geometry to contract
                        geometry_contract_dict = geometry_contract.to_dict()  # SAVE for final_analysis
                        pattern_render_contract["geometry_contract"] = geometry_contract_dict
                        pattern_render_contract["shape_validation"] = shape_validation.to_dict() if shape_validation else None
                        pattern_render_contract["render_gate"] = gate_result.to_dict()
                        
                        # ═══════════════════════════════════════════════════════════
                        # GEOMETRY NORMALIZATION — Clean up anchors for better visuals
                        # ═══════════════════════════════════════════════════════════
                        try:
                            normalizer = get_geometry_normalizer()
                            norm_result = normalizer.normalize(pattern_render_contract)
                            if norm_result.was_normalized:
                                pattern_render_contract = norm_result.pattern
                                print(f"[PerTF] ✨ Geometry normalized: {norm_result.normalization_type} "
                                      f"changes={norm_result.changes}")
                        except Exception as norm_err:
                            print(f"[PerTF] ⚠️ Normalization skipped: {norm_err}")
                        
                        # ═══════════════════════════════════════════════════════════
                        # PATTERN PROJECTION — Build full projection with targets
                        # ═══════════════════════════════════════════════════════════
                        try:
                            projection_engine = get_pattern_projection_engine()
                            # Get current price from last candle
                            current_price = candles[-1]["close"] if candles else None
                            projection = projection_engine.build(pattern_render_contract, current_price)
                            if projection:
                                pattern_render_contract["projection_contract"] = projection
                                print(f"[PerTF] 🎯 Projection built: stage={projection.get('stage')}, "
                                      f"primary={projection.get('projection', {}).get('primary', {}).get('direction')}, "
                                      f"target={projection.get('projection', {}).get('primary', {}).get('target')}")
                        except Exception as proj_err:
                            print(f"[PerTF] ⚠️ Projection skipped: {proj_err}")
                        
                        # ═══════════════════════════════════════════════════════════
                        # RENDER PROFILE — Configure what to draw based on mode/stage
                        # ═══════════════════════════════════════════════════════════
                        try:
                            pattern_render_contract = configure_pattern_render(pattern_render_contract)
                        except Exception as rp_err:
                            print(f"[PerTF] ⚠️ Render profile skipped: {rp_err}")
                        
                        # Log
                        print(f"[PerTF] V2 RESULT: {{"
                              f"tf: '{timeframe}', "
                              f"type: '{pattern_type}', "
                              f"coverage: {coverage_ratio:.1%}, "
                              f"window: {window_bars}, "
                              f"cleanliness: {geometry_contract.cleanliness:.2f}"
                              f"}}")
                else:
                    print(f"[PerTF] V2: No pattern found for {timeframe}")
                    display_message = "No dominant pattern detected."
                    
            except Exception as e:
                print(f"[PerTF] V2 pipeline error: {e}")
                import traceback
                traceback.print_exc()
                pattern_render_contract = None
                display_message = "Pattern analysis unavailable."
        
        # Display Gate for V2 patterns
        if pattern_render_contract:
            from modules.ta_engine.display_gate import get_display_gate
            display_gate = get_display_gate()
            
            gate_result = display_gate.evaluate(pattern_render_contract)
            
            if gate_result.should_display:
                print(f"[PerTF] ✅ Display Gate PASSED: {pattern_render_contract.get('type')}")
                pattern_render_contract["display_approved"] = True
                pattern_render_contract["display_gate_scores"] = gate_result.gate_scores
                
                # V2 pattern passed all checks - use it as primary for final_analysis
                # Convert render contract to primary_pattern format
                primary_pattern = None  # Will be handled separately
                
            else:
                print(f"[PerTF] ❌ Display Gate REJECTED: {gate_result.reason}")
                # Keep pattern as candidate but mark as not displayable
                pattern_render_contract["display_approved"] = False
                pattern_render_contract["display_rejected_reason"] = gate_result.reason
                display_message = gate_result.fallback_message
                
                # Don't show rejected pattern to user - set to None for rendering
                # But keep in response as "candidate_pattern" for debugging
                candidate_pattern = pattern_render_contract
                pattern_render_contract = None
                print(f"[PerTF] Fallback message: {display_message}")
        else:
            display_message = "Market structure is developing. No dominant pattern detected."
        
        # =============================================
        # STEP 5d: ANCHOR ENGINE (PRO LEVEL)
        # =============================================
        # If V2 pipeline failed, try anchor-based detection
        anchor_pattern = None
        if pattern_render_contract is None:
            try:
                print(f"[PerTF] Step 5d: Anchor-based pattern detection...")
                anchor_result = get_best_pattern(candles)
                
                if anchor_result and anchor_result.is_valid:
                    print(f"[PerTF] ✅ Anchor engine found: {anchor_result.pattern_type} "
                          f"(conf={anchor_result.confidence:.2f})")
                    
                    # Convert to render contract format
                    anchor_pattern = {
                        "type": anchor_result.pattern_type,
                        "engine": "ANCHOR_ENGINE_V1",
                        "source": "anchor_pattern_engine",
                        "confidence": anchor_result.confidence,
                        "anchors": anchor_result.anchors,
                        "boundaries": [
                            {
                                "id": "upper_line",
                                "kind": "trendline",
                                "x1": anchor_result.upper[0]["time"],
                                "y1": anchor_result.upper[0]["price"],
                                "x2": anchor_result.upper[-1]["time"],
                                "y2": anchor_result.upper[-1]["price"],
                            },
                            {
                                "id": "lower_line",
                                "kind": "trendline",
                                "x1": anchor_result.lower[0]["time"],
                                "y1": anchor_result.lower[0]["price"],
                                "x2": anchor_result.lower[-1]["time"],
                                "y2": anchor_result.lower[-1]["price"],
                            },
                        ],
                        "window": anchor_result.window,
                        "breakout_level": anchor_result.breakout_level,
                        "display_approved": True,
                        "geometry_contract": {
                            "is_valid": True,
                            "anchors": anchor_result.anchors,
                            "upper_boundary": {
                                "x1": anchor_result.upper[0]["time"],
                                "y1": anchor_result.upper[0]["price"],
                                "x2": anchor_result.upper[-1]["time"],
                                "y2": anchor_result.upper[-1]["price"],
                            },
                            "lower_boundary": {
                                "x1": anchor_result.lower[0]["time"],
                                "y1": anchor_result.lower[0]["price"],
                                "x2": anchor_result.lower[-1]["time"],
                                "y2": anchor_result.lower[-1]["price"],
                            },
                            "boundaries": {
                                "upper": {
                                    "x1": anchor_result.upper[0]["time"],
                                    "y1": anchor_result.upper[0]["price"],
                                    "x2": anchor_result.upper[-1]["time"],
                                    "y2": anchor_result.upper[-1]["price"],
                                },
                                "lower": {
                                    "x1": anchor_result.lower[0]["time"],
                                    "y1": anchor_result.lower[0]["price"],
                                    "x2": anchor_result.lower[-1]["time"],
                                    "y2": anchor_result.lower[-1]["price"],
                                },
                            },
                            "window": anchor_result.window,
                        },
                    }
                    
                    # Use anchor pattern as main
                    pattern_render_contract = anchor_pattern
                    geometry_contract_dict = anchor_pattern["geometry_contract"]
                    display_message = f"{anchor_result.pattern_type.replace('_', ' ').title()} detected"
                else:
                    print(f"[PerTF] Anchor engine: No valid pattern found")
                    
            except Exception as e:
                print(f"[PerTF] Anchor engine error: {e}")
        
        # =============================================
        # STEP 5e: PRO PATTERN ENGINE (FINAL LAYER)
        # =============================================
        # This is the ultimate pattern detection layer
        # Combines strict + loose patterns, always has something to show
        pro_pattern_stack = None
        pro_pattern_payload = None
        
        try:
            print(f"[PerTF] Step 5e: PRO Pattern Engine...")
            current_price = candles[-1].get("close", 0) if candles else 0
            
            pro_pattern_stack = run_pro_pattern_engine(candles, current_price)
            pro_pattern_payload = build_ui_pattern_payload(pro_pattern_stack)
            
            if pro_pattern_payload.get("pattern"):
                print(f"[PerTF] ✅ PRO Engine found: {pro_pattern_payload['pattern_meta']['label']} "
                      f"(mode={pro_pattern_payload['pattern_meta']['mode']}, "
                      f"conf={pro_pattern_payload['pattern_meta']['confidence']:.2f}, "
                      f"state={pro_pattern_payload['pattern_meta']['state']})")
                
                # If no pattern_render_contract yet, use PRO engine result
                if pattern_render_contract is None:
                    pattern_render_contract = pro_pattern_payload["pattern"]
                    pattern_render_contract["source"] = "PRO_PATTERN_ENGINE"
                    pattern_render_contract["display_approved"] = True  # Mark as approved
                    display_message = f"{pro_pattern_payload['pattern_meta']['label']} {pro_pattern_payload['pattern_meta']['state']}"
                    
                    # Build geometry_contract from anchors
                    anchors = pattern_render_contract.get("anchors", [])
                    if len(anchors) >= 3:  # Reduced from 4 to allow triangular patterns
                        geometry_contract_dict = {
                            "is_valid": True,
                            "anchors": anchors,
                            "boundaries": pattern_render_contract.get("meta", {}).get("boundaries", {}),
                            "mode": pattern_render_contract.get("mode", "loose"),
                        }
            else:
                print(f"[PerTF] PRO Engine: No pattern (strict={pro_pattern_stack.get('strict_count', 0)}, "
                      f"loose={pro_pattern_stack.get('loose_count', 0)})")
                
        except Exception as e:
            print(f"[PerTF] PRO Engine error: {e}")
            import traceback
            traceback.print_exc()
        
        # =============================================
        # STEP 6: INDICATORS & TA CONTEXT
        # =============================================
        print(f"[PerTF] Step 6: Indicators...")
        indicator_engine = get_indicator_engine()
        indicator_result = indicator_engine.analyze_all(candles)
        
        # Convert indicator results to dict format expected by decision engine
        indicator_signals = [s.to_dict() if hasattr(s, 'to_dict') else s for s in indicator_result] if indicator_result else []
        
        # Count bullish/bearish signals
        bullish_count = sum(1 for s in indicator_signals if s.get('bias') == 'bullish')
        bearish_count = sum(1 for s in indicator_signals if s.get('bias') == 'bearish')
        neutral_count = len(indicator_signals) - bullish_count - bearish_count
        
        # Compute indicator visualization data (overlays + panes for chart)
        print(f"[PerTF] Step 6b: Indicator visualization...")
        indicator_viz_engine = get_indicator_viz_engine()
        indicators_viz = indicator_viz_engine.compute_all(candles)
        
        # Compute indicator insights (interpretations for Research view)
        print(f"[PerTF] Step 6c: Indicator insights...")
        insights_engine = get_indicator_insights_engine()
        indicator_insights = insights_engine.analyze(indicators_viz.get("panes", []))
        
        # Build TA context with proper structure
        ta_context = {
            "regime": structure_context.regime if structure_context else "unknown",
            "bias": structure_context.bias if structure_context else "neutral",
            "indicators": {
                "total": len(indicator_signals),
                "bullish": bullish_count,
                "bearish": bearish_count,
                "neutral": neutral_count,
                "signals": indicator_signals,
            },
            "pattern": primary_pattern.to_dict() if primary_pattern else None,
        }
        
        # =============================================
        # STEP 7: DECISION ENGINE
        # =============================================
        print(f"[PerTF] Step 7: Decision engine...")
        decision_engine = get_decision_engine_v2()
        decision = decision_engine.build(
            mtf_context=mtf_context or {},
            structure_context=structure_context_dict,
            primary_pattern=primary_pattern.to_dict() if primary_pattern else None,
            ta_context=ta_context,
        )
        
        # =============================================
        # STEP 8: UNIFIED SETUP & TRADE SETUP
        # =============================================
        print(f"[PerTF] Step 8: Unified setup...")
        unified_engine = get_unified_setup_engine()
        unified_setup = unified_engine.build(
            decision=decision,
            structure_context=structure_context_dict,
            liquidity=liquidity,
            displacement=displacement,
            choch_validation=choch_validation,
            poi=poi,
            fib=fib,
            active_pattern=primary_pattern.to_dict() if primary_pattern else None,
            ta_context=ta_context,
            current_price=current_price,
        )
        
        trade_setup_gen = get_trade_setup_generator()
        trade_setup = trade_setup_gen.build(
            decision=decision,
            scenarios=[],  # No scenarios in per-TF mode
            base_layer={},
            structure_context=structure_context_dict,
            current_price=current_price,
        )
        
        # =============================================
        # STEP 9: EXECUTION LAYER
        # =============================================
        print(f"[PerTF] Step 9: Execution layer...")
        execution_layer = get_execution_layer()
        
        # Use MTF context if provided, otherwise create simple context
        exec_mtf_context = mtf_context or {
            "alignment": "mixed",
            "tradeability": "medium",
        }
        
        execution = execution_layer.build(
            mtf_context=exec_mtf_context,
            unified_setup=unified_setup,
            trade_setup=trade_setup,
            active_pattern=primary_pattern.to_dict() if primary_pattern else None,
            poi=poi,
            fib=fib,
            current_price=current_price,
        )
        print(f"[PerTF] Execution status: {execution.get('status')}")
        
        # =============================================
        # STEP 10: BUILD CHAIN MAP (for highlighting)
        # =============================================
        print(f"[PerTF] Step 10: Chain map...")
        chain_map = self._build_chain_map(
            unified_setup=unified_setup,
            liquidity=liquidity,
            displacement=displacement,
            choch_validation=choch_validation,
            poi=poi,
            primary_pattern=primary_pattern.to_dict() if primary_pattern else None,
            candles=candles,
        )
        
        # =============================================
        # STEP 11: BUILD RENDER PLAN V2 (for clean chart rendering)
        # =============================================
        print(f"[PerTF] Step 11: Render plan v2...")
        try:
            # Compute market state
            ms_engine = _get_market_state_engine()
            market_state = ms_engine.analyze(candles)
            
            # Build structure visualization with swings
            viz_builder = _get_structure_viz_builder()
            structure_viz = viz_builder.build(
                pivots_high=pivot_highs_raw,
                pivots_low=pivot_lows_raw,
                structure_context=structure_context_dict,
                candles=candles,
            )
            
            # Merge structure_context with visualization
            events = structure_viz.get("events", [])
            bos_event = next((e for e in events if "bos" in e.get("type", "")), None)
            choch_event = next((e for e in events if "choch" in e.get("type", "")), None)
            
            structure_for_render = {
                **structure_context_dict,
                "swings": structure_viz.get("pivot_points", []),
                "bos": bos_event,
                "choch": choch_event,
            }
            
            # Get patterns as list
            patterns = []
            if primary_pattern:
                patterns.append(primary_pattern.to_dict())
            
            # V2: Include pattern_render_contract (ALL types - range, head_shoulders, etc.) if approved
            prc = pattern_render_contract
            print(f"[PerTF] PRC check: prc={prc is not None}, display_approved={prc.get('display_approved') if prc else None}, type={prc.get('type') if prc else None}")
            if prc and prc.get("display_approved"):
                prc_type = prc.get("type", "")
                print(f"[PerTF] Pattern type: {prc_type}, is_range: {'range' in prc_type.lower()}")
                # Check if this is a range-type pattern
                if "range" in prc_type.lower():
                    # Calculate forward extension
                    forward_bars = 30
                    if candles and len(candles) >= 2:
                        interval = candles[-1].get("time", 0) - candles[-2].get("time", 0)
                        if interval > 1e12:
                            interval = interval // 1000
                        forward_time = candles[-1].get("time", 0)
                        if forward_time > 1e12:
                            forward_time = forward_time // 1000
                        forward_time = forward_time + interval * forward_bars
                    else:
                        forward_time = 0
                    
                    # Extract boundaries from meta
                    boundaries = prc.get("meta", {}).get("boundaries", {})
                    upper = boundaries.get("upper", {})
                    lower = boundaries.get("lower", {})
                    resistance = prc.get("meta", {}).get("resistance", upper.get("y2", 0))
                    support = prc.get("meta", {}).get("support", lower.get("y2", 0))
                    
                    range_pattern = {
                        "type": prc_type,
                        "is_active": True,
                        "confidence": prc.get("confidence", 0.5),
                        "direction": prc.get("bias", "neutral"),
                        "state": prc.get("state", "active"),
                        "forward_bars": forward_bars,
                        "breakout_level": resistance,
                        "invalidation": support,
                        "points": {
                            "upper": [
                                {"time": upper.get("x1", 0), "value": resistance},
                                {"time": forward_time, "value": resistance},
                            ],
                            "lower": [
                                {"time": lower.get("x1", 0), "value": support},
                                {"time": forward_time, "value": support},
                            ],
                            "mid": [
                                {"time": upper.get("x1", 0), "value": (resistance + support) / 2},
                                {"time": forward_time, "value": (resistance + support) / 2},
                            ],
                        }
                    }
                    patterns.append(range_pattern)
                    print(f"[PerTF] Added range pattern to render_plan: {prc_type}")
                else:
                    # NON-RANGE PATTERNS (head_shoulders, triangle, wedge, etc.)
                    # Determine direction from multiple sources
                    prc_direction = prc.get("direction")
                    if not prc_direction:
                        prc_direction = prc.get("bias")
                    if not prc_direction:
                        prc_direction = prc.get("meta", {}).get("direction")
                    if not prc_direction:
                        prc_direction = prc.get("meta", {}).get("bias")
                    # For head_shoulders, infer from pattern subtype
                    if not prc_direction and "head_shoulders" in prc_type.lower():
                        if "inverse" in prc_type.lower():
                            prc_direction = "bullish"
                        else:
                            prc_direction = "bearish"  # Standard H&S is bearish reversal
                    
                    non_range_pattern = {
                        "type": prc_type,
                        "is_active": True,
                        "confidence": prc.get("confidence", 0.5),
                        "score": prc.get("confidence", 0.5),
                        "direction": prc_direction or "neutral",
                        "state": prc.get("state", "forming"),
                        "quality": prc.get("quality", 0.5),
                    }
                    
                    # Build points from anchors
                    anchors = prc.get("anchors", [])
                    if anchors and len(anchors) >= 2:
                        non_range_pattern["points"] = {
                            "anchors": [
                                {"time": a.get("x"), "value": a.get("y"), "role": a.get("role")}
                                for a in anchors if a.get("x") and a.get("y")
                            ]
                        }
                    
                    patterns.append(non_range_pattern)
                    print(f"[PerTF] Added non-range pattern to render_plan: {prc_type}, conf={prc.get('confidence')}")
            
            
            # Build render plan
            rp_engine = _get_render_plan_engine()
            render_plan = rp_engine.build(
                timeframe=timeframe,
                current_price=current_price,
                market_state=market_state.to_dict(),
                structure=structure_for_render,
                indicators=indicators_viz,
                patterns=patterns,
                liquidity=liquidity,
                execution=execution,
                poi=poi,
            )
            print(f"[PerTF] Render plan built: swings={len(render_plan.get('structure', {}).get('swings', []))}")
        except Exception as e:
            print(f"[PerTF] Render plan error: {e}")
            render_plan = None
        
        # =============================================
        # ASSEMBLE RESULT
        # =============================================
        elapsed = time_module.time() - start_time
        print(f"[PerTF] Build completed in {elapsed:.2f}s")
        
        # Get interpretation from InterpretationEngine
        try:
            from modules.ta_engine.interpretation.interpretation_engine import get_interpretation_engine
            from modules.ta_engine.mtf_engine import MTFEngine
            ie = get_interpretation_engine()
            tf_role = MTFEngine.classify_tf(timeframe)
            
            # Build data dict for interpretation
            # CRITICAL: Include pro_pattern if no strict pattern (for loose patterns)
            pattern_for_interp = primary_pattern.to_dict() if primary_pattern else None
            if not pattern_for_interp and pro_pattern_payload and pro_pattern_payload.get("pattern"):
                pattern_for_interp = pro_pattern_payload["pattern"]
            
            interp_data = {
                "trend": structure_context_dict.get("bias", "neutral"),
                "regime": structure_context_dict.get("regime", "unknown"),
                "pattern": pattern_for_interp,
                "structure": structure_context_dict,
                "levels": (render_plan.get("levels", []) if render_plan else []),
            }
            interpretation = ie.interpret(tf_role, interp_data)
            print(f"[PerTF] Interpretation: {interpretation[:80]}...")
        except Exception as e:
            print(f"[PerTF] Interpretation error: {e}")
            interpretation = None
        
        # =============================================
        # NARRATIVE ENGINE — human-readable market story
        # =============================================
        try:
            from modules.ta_engine.narrative_engine import build_market_narrative
            
            # Get context for narrative (safely)
            volatility_value = None
            if market_state:
                if hasattr(market_state, 'volatility'):
                    volatility_value = market_state.volatility
                elif isinstance(market_state, dict):
                    volatility_value = market_state.get("volatility")
            
            context_for_narrative = {
                "volatility": volatility_value,
                "regime": structure_context_dict.get("regime"),
                "phase": structure_context_dict.get("phase"),
            }
            
            narrative = build_market_narrative(
                structure=structure_context_dict,
                pattern=pattern_for_interp,
                context=context_for_narrative,
            )
            print(f"[PerTF] Narrative: {narrative.get('short', '')[:60]}...")
        except Exception as e:
            print(f"[PerTF] Narrative error: {e}")
            narrative = {"short": "Analyzing...", "full": "Market analysis in progress."}
        
        # =============================================
        # TA AGGREGATOR — 10 LAYER DECISION SYSTEM (NEW!)
        # =============================================
        try:
            from modules.ta_engine.ta_aggregator import aggregate_ta_layers
            
            ta_layers = aggregate_ta_layers(
                candles=candles,
                structure=structure_context_dict,
                pivots={"high": pivot_highs, "low": pivot_lows},
                pattern=primary_pattern.to_dict() if primary_pattern else None,
                pattern_render_contract=pattern_render_contract,
                indicators=indicator_insights.to_dict() if hasattr(indicator_insights, 'to_dict') else {},
                current_price=current_price,
                timeframe=timeframe,
            )
            print(f"[PerTF] TA Layers: regime={ta_layers.get('regime', {}).get('regime')}, "
                  f"bias={ta_layers.get('probability', {}).get('dominant_bias')}")
        except Exception as e:
            print(f"[PerTF] TA Aggregator error: {e}")
            import traceback
            traceback.print_exc()
            ta_layers = None
        
        # =============================================
        # WATCH LEVELS — "What to Watch" (breakout/breakdown)
        # =============================================
        try:
            dom_for_wl = pattern_render_contract if pattern_render_contract else (
                primary_pattern.to_dict() if primary_pattern else None
            )
            watch_levels = build_watch_levels({"dominant": dom_for_wl}) if dom_for_wl else []
        except Exception as e:
            print(f"[PerTF] Watch levels error: {e}")
            watch_levels = []
        
        # =============================================
        # LIFECYCLE — forming / confirmed / invalidated
        # =============================================
        try:
            dom_for_lc = pattern_render_contract if pattern_render_contract else (
                primary_pattern.to_dict() if primary_pattern else None
            )
            lifecycle = build_lifecycle(dom_for_lc, current_price) if dom_for_lc else {"state": "forming", "label": "Developing"}
        except Exception as e:
            print(f"[PerTF] Lifecycle error: {e}")
            lifecycle = {"state": "forming", "label": "Developing"}
        
        # =============================================
        # MARKET STATE LABEL — for intelligence & history
        # =============================================
        market_state_label = "NEUTRAL"
        if ta_layers:
            regime = ta_layers.get("regime", {})
            if isinstance(regime, dict):
                market_state_label = regime.get("label", "NEUTRAL")
            elif isinstance(regime, str):
                market_state_label = regime
        
        result = {
            "timeframe": timeframe,
            "symbol": symbol,
            "candles": candles,
            "candle_count": len(candles),
            "current_price": current_price,
            
            # INTERPRETATION — human-readable TA analysis
            "interpretation": interpretation,
            
            # WATCH LEVELS — breakout/breakdown observational levels
            "watch_levels": watch_levels,
            
            # LIFECYCLE — pattern state machine
            "lifecycle": lifecycle,
            
            # NARRATIVE — market story (NEW!)
            "narrative": narrative,
            
            # Structure (use dict, not object)
            "structure_context": structure_context_dict,
            "structure_state": structure_state.to_dict() if hasattr(structure_state, 'to_dict') else structure_state,
            
            # Smart Money
            "liquidity": liquidity,
            "displacement": displacement,
            "choch_validation": choch_validation,
            "poi": poi,
            "fib": fib,
            
            # Patterns — RENDER CONTRACT V4
            "primary_pattern": primary_pattern.to_dict() if primary_pattern else None,
            "pattern_geometry": normalize_pattern_geometry(primary_pattern.to_dict()) if primary_pattern else None,
            "pattern_render_contract": self._clean_pattern_for_response(pattern_render_contract),  # NEW: render-ready geometry (None if rejected)
            "alternative_patterns": [a.to_dict() for a in alternatives] if alternatives else [],
            "alternative_render_contracts": [self._clean_pattern_for_response(a) for a in alt_render_contracts],  # NEW: alternatives render-ready
            
            # Dominance info (why pattern was/wasn't shown)
            "pattern_dominance": dominance_score.to_dict() if dominance_score else None,
            "pattern_rejections": pattern_rejections if pattern_rejections else None,
            
            # Display Gate result
            "display_message": display_message,  # Fallback message when no pattern shown
            "candidate_pattern": self._clean_pattern_for_response(candidate_pattern),  # Pattern that failed gate (cleaned)
            
            # Indicators (convert IndicatorSignal objects to dicts)
            "indicator_result": [s.to_dict() if hasattr(s, 'to_dict') else s for s in indicator_result] if indicator_result else [],
            "indicators": indicators_viz,  # {overlays: [...], panes: [...]} for chart rendering
            "indicator_insights": indicator_insights.to_dict(),  # RSI/MACD interpretations for Research
            "ta_context": ta_context,
            
            # Decision & Setup
            "decision": decision,
            "unified_setup": unified_setup,
            "trade_setup": trade_setup,
            "execution": execution,
            
            # Chain highlighting
            "chain_map": chain_map,
            
            # RENDER PLAN V2 — for clean chart rendering
            "render_plan": render_plan,
            
            # ═══════════════════════════════════════════════════════════════
            # FINAL ANALYSIS — NEVER EMPTY
            # ═══════════════════════════════════════════════════════════════
            # analysis_mode: figure | structure | context
            # ALWAYS returns meaningful analysis even if no pattern found
            # Use V2 pattern_render_contract if it passed all checks, otherwise primary_pattern
            # NEW: Pass pro_pattern_payload for loose pattern support
            "final_analysis": self._build_final_analysis(
                timeframe=timeframe,
                candles=candles,
                primary_pattern=(
                    pattern_render_contract if pattern_render_contract and pattern_render_contract.get("display_approved")
                    else (primary_pattern.to_dict() if primary_pattern else None)
                ),
                geometry_contract=geometry_contract_dict,
                pro_pattern_payload=pro_pattern_payload,
            ),
            
            # TA LAYERS — 10 layer decision system (NEW!)
            "ta_layers": ta_layers,
            
            # ═══════════════════════════════════════════════════════════════
            # TA EXPLORER — FULL AUDIT MODE (patterns_all, rejected, dominant)
            # ═══════════════════════════════════════════════════════════════
            "ta_explorer": self._build_ta_explorer(
                ta_layers=ta_layers,
                pro_pattern_stack=pro_pattern_stack,
                pattern_render_contract=pattern_render_contract,
                pattern_rejections=pattern_rejections,
                structure_context=structure_context_dict,
                timeframe=timeframe,
            ),
            
            # Quick access to key TA state
            "market_state": {
                "structure": ta_layers.get("structure") if ta_layers else None,
                "impulse": ta_layers.get("impulse") if ta_layers else None,
                "regime": ta_layers.get("regime") if ta_layers else None,
            } if ta_layers else None,
            "probability": ta_layers.get("probability") if ta_layers else None,
            "scenarios": ta_layers.get("scenarios") if ta_layers else None,
            "active_range": ta_layers.get("active_range") if ta_layers else None,
            "ta_narrative": ta_layers.get("narrative") if ta_layers else None,
            
            # ═══════════════════════════════════════════════════════════════
            # RENDER STACK — Multi-pattern visualization (1 dominant + 2 secondary)
            # ═══════════════════════════════════════════════════════════════
            "render_stack": build_render_stack(
                patterns_ranked=[],
                active_range=ta_layers.get("active_range") if ta_layers else None,
                candles=candles,
                dominant_pattern=pattern_render_contract if pattern_render_contract else (
                    primary_pattern.to_dict() if primary_pattern else None
                ),
                alternative_patterns=[a.to_dict() for a in alternatives] if alternatives else [],
            ),
            
            # ═══════════════════════════════════════════════════════════════
            # MTF CONTEXT — Higher timeframe context for overlay
            # ═══════════════════════════════════════════════════════════════
            "mtf_context": self._build_mtf_context(mtf_context, timeframe) if mtf_context else None,
            
            # ═══════════════════════════════════════════════════════════════
            # INTELLIGENCE — Unified decision payload for scorecard
            # ═══════════════════════════════════════════════════════════════
            "intelligence": self._build_intelligence(
                market_state=market_state_label,
                dominant_pattern=pattern_render_contract if pattern_render_contract else (
                    primary_pattern.to_dict() if primary_pattern else {}
                ),
                lifecycle=lifecycle,
                mtf_context=self._build_mtf_context(mtf_context, timeframe) if mtf_context else None,
                watch_levels=watch_levels,
                candles=candles,  # Pass candles for live probability calculation
                probabilities=None,  # Will come from similarity engine when populated
                symbol=symbol,  # For performance stats lookup
            ),
            
            # Meta
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        
        # ═══════════════════════════════════════════════════════════════
        # PATTERN HISTORY — Store snapshot on significant changes
        # ═══════════════════════════════════════════════════════════════
        try:
            from core.database import get_database
            from modules.ta_engine.pattern_history_engine import get_history_manager
            
            db = get_database()
            if db is None:
                print(f"[PerTF] History: DB is None, skipping")
            else:
                history_manager = get_history_manager(db)
                
                # Get dominant pattern for history
                dom_pattern = pattern_render_contract if pattern_render_contract else (
                    primary_pattern.to_dict() if primary_pattern else None
                )
                
                if dom_pattern:
                    # Process and store if significant (market_state_label already defined above)
                    stored = history_manager.process_analysis_result(
                        symbol=symbol,
                        timeframe=timeframe,
                        market_state=market_state_label,
                        dominant=dom_pattern,
                        alternatives=[a.to_dict() for a in alternatives] if alternatives else [],
                        render_contract=dom_pattern,
                    )
                    if stored:
                        print(f"[PerTF] History stored: {symbol}/{timeframe} - {dom_pattern.get('type')}")
                else:
                    print(f"[PerTF] History: No dominant pattern for {symbol}/{timeframe}")
        except Exception as e:
            import traceback
            print(f"[PerTF] History storage error: {e}")
            traceback.print_exc()
        
        # ═══════════════════════════════════════════════════════════════
        # AUTO-TRACKING — Record confirmed setups for performance learning
        # ═══════════════════════════════════════════════════════════════
        try:
            from core.database import get_database
            from modules.ta_engine.auto_tracking_engine import auto_track_if_confirmed
            
            db = get_database()
            if db is not None:
                dom_pattern = pattern_render_contract if pattern_render_contract else (
                    primary_pattern.to_dict() if primary_pattern else None
                )
                
                if dom_pattern:
                    current_price = candles[-1].get("close") if candles else None
                    
                    tracked_id = auto_track_if_confirmed(
                        symbol=symbol,
                        timeframe=timeframe,
                        pattern=dom_pattern,
                        current_price=current_price,
                        market_state=market_state_label,
                        db=db,
                    )
                    
                    if tracked_id:
                        print(f"[PerTF] Auto-tracked: {symbol}/{timeframe} - {dom_pattern.get('type')} {dom_pattern.get('lifecycle')}")
        except Exception as e:
            print(f"[PerTF] Auto-tracking error: {e}")
        
        return result
    
    def _build_mtf_context(self, mtf_context: Optional[Dict], current_tf: str) -> Optional[Dict]:
        """
        Build MTF context for overlay rendering.
        
        Only includes:
        - Higher TF range (box)
        - Key levels (support/resistance)
        - Market state
        
        Does NOT include patterns, polylines, etc.
        """
        if not mtf_context:
            return None
        
        try:
            # Get higher TF data
            htf_data = None
            htf_name = None
            
            # TF hierarchy: 1H -> 4H -> 1D
            if current_tf in ("1H", "4H"):
                htf_data = mtf_context.get("1D") or mtf_context.get("daily")
                htf_name = "1D"
            elif current_tf == "1D":
                htf_data = mtf_context.get("7D") or mtf_context.get("weekly")
                htf_name = "7D"
            
            if not htf_data:
                return None
            
            # Extract only what we need for overlay
            result = {
                "timeframe": htf_name,
                "market_state": None,
                "range": None,
                "levels": [],
            }
            
            # Market state
            ta_layers = htf_data.get("ta_layers") or {}
            regime = ta_layers.get("regime") or {}
            if isinstance(regime, dict):
                result["market_state"] = regime.get("label") or regime.get("type")
            elif isinstance(regime, str):
                result["market_state"] = regime
            
            # Active range (box)
            active_range = ta_layers.get("active_range") or htf_data.get("active_range")
            if active_range and active_range.get("top") and active_range.get("bottom"):
                result["range"] = {
                    "start_time": active_range.get("start_time"),
                    "end_time": active_range.get("end_time"),
                    "top": active_range.get("top"),
                    "bottom": active_range.get("bottom"),
                }
            
            # Key levels (support/resistance)
            watch_levels = htf_data.get("watch_levels") or []
            for lvl in watch_levels[:4]:  # Max 4 levels
                if lvl.get("price"):
                    result["levels"].append({
                        "price": lvl.get("price"),
                        "type": lvl.get("type", "level"),
                        "label": lvl.get("label", ""),
                    })
            
            return result
            
        except Exception as e:
            print(f"[PerTF] MTF context error: {e}")
            return None

    def _build_intelligence(
        self,
        market_state: str,
        dominant_pattern: Dict,
        lifecycle: Dict = None,
        mtf_context: Dict = None,
        watch_levels: List[Dict] = None,
        candles: List[Dict] = None,
        probabilities: Dict = None,
        symbol: str = None,
    ) -> Dict:
        """
        Build unified intelligence payload for scorecard.
        
        V2: Now includes live_probability and bayesian_probability
        V3: Now includes performance stats (self-learning weights)
        """
        try:
            from modules.ta_engine.intelligence_builder import build_intelligence_payload
            from modules.ta_engine.live_probability_engine import compute_live_probability, apply_bayesian_update
            from modules.ta_engine.pattern_performance_stats import get_stats_manager
            from core.database import get_database
            
            # Compute live probability if we have pattern and candles
            live_probability = None
            bayesian_probability = None
            performance = None
            
            if dominant_pattern and candles and len(candles) >= 10:
                live_probability = compute_live_probability(
                    pattern=dominant_pattern,
                    candles=candles[-20:],  # Last 20 candles
                    prior_probability=probabilities,
                )
                
                if live_probability:
                    bayesian_probability = apply_bayesian_update(
                        prior=probabilities,
                        live=live_probability,
                        evidence=live_probability.get("factors", []),
                    )
            
            # Load performance stats for self-learning weights
            try:
                db = get_database()
                if db is not None:
                    stats_manager = get_stats_manager(db)
                    if stats_manager:
                        pattern_type = dominant_pattern.get("type", "unknown")
                        regime = market_state.lower() if market_state else "unknown"
                        
                        # Get stats summary
                        stats_summary = stats_manager.get_summary(symbol)
                        total_samples = stats_summary.get("total_samples", 0)
                        
                        # Get specific weight for this pattern
                        weight = stats_manager.get_weight(pattern_type, regime, symbol)
                        
                        # Find winrate for this pattern
                        pattern_stats = stats_summary.get("patterns", [])
                        pattern_winrate = None
                        pattern_samples = 0
                        
                        for ps in pattern_stats:
                            if ps.get("pattern") == pattern_type:
                                pattern_winrate = ps.get("winrate")
                                pattern_samples = ps.get("samples", 0)
                                break
                        
                        # Return performance if we have any tracked data
                        if total_samples > 0:
                            performance = {
                                "win_rate": pattern_winrate if pattern_winrate is not None else 0,  # Ensure numeric
                                "weight": weight,
                                "samples": pattern_samples,
                                "total_tracked": total_samples,
                                "pattern_type": pattern_type,
                                "top_patterns": pattern_stats[:3],  # Top 3 performing patterns
                            }
            except Exception as pe:
                print(f"[PerTF] Performance stats error: {pe}")
            
            return build_intelligence_payload(
                market_state=market_state,
                dominant_pattern=dominant_pattern or {},
                lifecycle=lifecycle,
                mtf_context=mtf_context,
                watch_levels=watch_levels,
                probabilities=probabilities,
                similarity_matches=None,  # TODO: Add when similarity history is populated
                live_probability=live_probability,
                bayesian_probability=bayesian_probability,
                performance=performance,
            )
        except Exception as e:
            print(f"[PerTF] Intelligence build error: {e}")
            return None

    def _clean_pattern_for_response(self, pattern: Optional[Dict]) -> Optional[Dict]:
        """
        Clean pattern dict for JSON response.
        
        Removes internal keys (starting with _) and non-serializable objects.
        """
        if pattern is None:
            return None
        
        cleaned = {}
        for key, value in pattern.items():
            # Skip internal keys
            if key.startswith("_"):
                continue
            
            # Skip callable objects (functions)
            if callable(value):
                continue
            
            # Recursively clean nested dicts
            if isinstance(value, dict):
                cleaned[key] = self._clean_pattern_for_response(value)
            elif isinstance(value, list):
                cleaned[key] = [
                    self._clean_pattern_for_response(item) if isinstance(item, dict) else item
                    for item in value
                    if not callable(item)
                ]
            else:
                cleaned[key] = value
        
        return cleaned

    def _hard_filter_recency(self, candidates: List, candles: List[Dict]) -> List:
        """Filter patterns that are too old."""
        if not candidates or not candles:
            return candidates
        
        total = len(candles)
        filtered = []
        
        for c in candidates:
            recency = (total - 1 - c.last_touch_index) / max(total, 1)
            if recency > 0.35:
                continue
            if c.end_index < total * 0.7:
                continue
            filtered.append(c)
        
        return filtered
    
    def _build_ta_explorer(
        self,
        ta_layers: Optional[Dict],
        pro_pattern_stack: Optional[Dict],
        pattern_render_contract: Optional[Dict],
        pattern_rejections: Optional[List],
        structure_context: Optional[Dict],
        timeframe: str,
    ) -> Dict:
        """
        Build TA Explorer payload for full audit mode.
        
        NOW WITH V2 RANKING ENGINE:
        - Context-aware scoring (structure + HTF + regime alignment)
        - Conflict penalty for opposing patterns
        - Confidence state (clear / weak / conflicted)
        - Market quality assessment
        
        Returns:
        - dominant: winner pattern with why_selected + confidence_state
        - patterns_all: all detected patterns ranked by FINAL score
        - patterns_rejected: patterns that failed validation
        - ta_layers: full 10-layer breakdown
        - confidence_state: clear / weak / conflicted
        - market_quality: high / medium / low + tradeable
        """
        try:
            # 1. Build patterns_all from pro_pattern_stack
            patterns_raw = []
            if pro_pattern_stack and pro_pattern_stack.get("all_patterns"):
                for p in pro_pattern_stack["all_patterns"]:
                    patterns_raw.append({
                        "type": p.get("type", "unknown"),
                        "mode": p.get("mode", "loose"),
                        "score": p.get("confidence", 0),
                        "stage": p.get("state", "forming"),
                        "renderable": bool(p.get("anchors")),
                        "bias": p.get("bias", "neutral"),
                        "source_layer": "pattern_engine",
                    })
            
            # Add active_range as pattern candidate if exists
            if ta_layers and ta_layers.get("active_range"):
                ar = ta_layers["active_range"]
                range_score = 0.7 if ar.get("status") == "active" else 0.5
                patterns_raw.append({
                    "type": "active_range",
                    "mode": "regime",
                    "score": range_score,
                    "stage": ar.get("state", "active"),
                    "renderable": True,
                    "bias": "neutral",
                    "source_layer": "range_regime_engine",
                })
            
            # ══════════════════════════════════════════════════════════════
            # V2 RANKING ENGINE — Context-Aware Decision System
            # ══════════════════════════════════════════════════════════════
            structure_layer = ta_layers.get("structure", {}) if ta_layers else {}
            regime_layer = ta_layers.get("regime", {}) if ta_layers else {}
            
            # Get HTF context (use structure as proxy for now)
            htf_context = {
                "bias": structure_layer.get("trend", "neutral"),
            }
            
            # Run V2 ranking
            patterns_ranked = rank_patterns_v2(
                patterns=patterns_raw,
                structure=structure_layer,
                htf_context=htf_context,
                regime=regime_layer,
            )
            
            # Compute confidence state
            confidence_state = compute_confidence_state(patterns_ranked)
            
            # Compute market quality
            market_quality = compute_market_quality(patterns_ranked, confidence_state)
            
            # 2. Build patterns_rejected
            patterns_rejected = []
            if pattern_rejections:
                for r in pattern_rejections:
                    if isinstance(r, dict):
                        patterns_rejected.append({
                            "type": r.get("type", "unknown"),
                            "reason": r.get("reason", "Failed validation"),
                        })
                    elif isinstance(r, str):
                        patterns_rejected.append({
                            "type": "pattern",
                            "reason": r,
                        })
            
            # 3. Build dominant with V2 scoring
            dominant = None
            
            if patterns_ranked:
                winner = patterns_ranked[0]
                
                # Build why_selected with component breakdown
                why_selected = []
                components = winner.get("components", {})
                
                why_selected.append(f"Final score: {winner['final_score']:.1f}")
                why_selected.append(f"Base: {components.get('base', 0):.1f}")
                
                if components.get("structure", 0) != 0:
                    sign = "+" if components["structure"] > 0 else ""
                    why_selected.append(f"Structure alignment: {sign}{components['structure']:.0f}")
                
                if components.get("htf", 0) != 0:
                    sign = "+" if components["htf"] > 0 else ""
                    why_selected.append(f"HTF alignment: {sign}{components['htf']:.0f}")
                
                if components.get("regime", 0) != 0:
                    sign = "+" if components["regime"] > 0 else ""
                    why_selected.append(f"Regime fit: {sign}{components['regime']:.0f}")
                
                if components.get("conflict", 0) != 0:
                    why_selected.append(f"Conflict penalty: {components['conflict']:.0f}")
                
                # Add confidence state description
                if confidence_state == "clear":
                    why_selected.append("Strong dominant signal")
                elif confidence_state == "conflicted":
                    why_selected.append("WARNING: Competing signals detected")
                elif confidence_state == "weak":
                    why_selected.append("Moderate confidence, manage risk")
                
                dominant = {
                    "type": winner["type"],
                    "mode": winner["mode"],
                    "score": winner["final_score"],  # Use final_score!
                    "base_score": winner.get("base_score", winner.get("score", 0)),
                    "stage": winner["stage"],
                    "renderable": winner["renderable"],
                    "bias": winner.get("bias", "neutral"),
                    "confidence_state": confidence_state,
                    "why_selected": why_selected,
                    "components": components,
                }
            
            # 4. Build full ta_layers breakdown with proper naming
            layers_formatted = {}
            if ta_layers:
                layers_formatted = {
                    "layer_1_structure": ta_layers.get("structure", {}),
                    "layer_2_impulse": ta_layers.get("impulse", {}),
                    "layer_3_regime": ta_layers.get("regime", {}),
                    "layer_4_range": ta_layers.get("active_range", {}),
                    "layer_5_pattern": ta_layers.get("pattern", {}),
                    "layer_6_confluence": ta_layers.get("confluence", {}),
                    "layer_7_probability": ta_layers.get("probability", {}),
                    "layer_8_scenarios": ta_layers.get("scenarios", {}),
                    "layer_9_timing": ta_layers.get("timing", {}),
                    "layer_10_narrative": ta_layers.get("narrative", {}),
                }
            
            # ══════════════════════════════════════════════════════════════
            # RENDER STACK — Multi-pattern visualization (NEW!)
            # ══════════════════════════════════════════════════════════════
            # Show 1 dominant + 2 secondary patterns for richer visualization
            active_range = ta_layers.get("active_range") if ta_layers else None
            render_stack = build_render_stack(
                patterns_ranked=patterns_ranked,
                active_range=active_range,
                candles=None,
                dominant_pattern=pattern_render_contract,  # Use pattern_render_contract as fallback
            )
            
            return {
                "timeframe": timeframe,
                "dominant": dominant,
                "patterns_all": patterns_ranked,  # Now with final_score + components
                "patterns_rejected": patterns_rejected,
                "ta_layers": layers_formatted,
                "confidence_state": confidence_state,
                "market_quality": market_quality,
                # ══════════════════════════════════════════════════════════════
                # RENDER STACK — 1 dominant + 2 secondary patterns
                # ══════════════════════════════════════════════════════════════
                "render_stack": render_stack,
                # ══════════════════════════════════════════════════════════════
                # TRADE SETUP — ONLY when confidence_state = CLEAR
                # ══════════════════════════════════════════════════════════════
                "trade_setup": build_trade_setup(
                    dominant=dominant,
                    ta_layers=layers_formatted,
                    confidence_state=confidence_state,
                ),
            }
            
        except Exception as e:
            print(f"[PerTF] TA Explorer build error: {e}")
            import traceback
            traceback.print_exc()
            return {
                "timeframe": timeframe,
                "dominant": None,
                "patterns_all": [],
                "patterns_rejected": [],
                "ta_layers": {},
            }
    
    def _build_final_analysis(
        self,
        timeframe: str,
        candles: List[Dict[str, Any]],
        primary_pattern: Optional[Dict[str, Any]],
        geometry_contract: Optional[Dict[str, Any]] = None,
        pro_pattern_payload: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Build final analysis that NEVER returns empty.
        
        If figure exists -> mode = "figure"
        Else if structure meaningful -> mode = "structure"  
        Else -> mode = "context"
        
        ALWAYS returns title + text in summary.
        NEW: Includes ui block with main_overlay and geometry for frontend.
        NEW: Uses PRO pattern engine for loose patterns (always shows something)
        """
        try:
            resolver = get_final_analysis_resolver()
            result = resolver.resolve(
                timeframe=timeframe,
                candles=candles,
                figure_result=primary_pattern,
            )
            final = result.to_dict()
            
            # ═══════════════════════════════════════════════════════════
            # UI BLOCK WITH PRO ENGINE SUPPORT
            # ═══════════════════════════════════════════════════════════
            # Priority:
            # 1. STRICT pattern with valid geometry → solid render
            # 2. LOOSE pattern from PRO engine → dashed render
            # 3. Structure fallback → no overlay
            
            geo = None
            pattern_type = None
            geo_source = None
            pattern_mode = None
            render_profile = None
            
            # Try STRICT geometry first
            if geometry_contract and geometry_contract.get("is_valid"):
                geo = geometry_contract
                geo_source = "anchor_geometry"
                pattern_type = primary_pattern.get("type") if primary_pattern else None
                
                # Check if this is actually a loose pattern masquerading as strict
                # PRO engine sets "mode" in geometry_contract
                pattern_mode = geometry_contract.get("mode", "strict")
                
                if pattern_mode == "loose":
                    render_profile = {
                        "opacity": 0.10,
                        "lineWidth": 1.5,
                        "dash": True,
                        "fill": True,
                    }
                else:
                    render_profile = {
                        "opacity": 0.22,
                        "lineWidth": 2.5,
                        "dash": False,
                        "fill": True,
                    }
            
            # Try PRO engine LOOSE pattern if no strict
            elif pro_pattern_payload and pro_pattern_payload.get("pattern"):
                pro_pattern = pro_pattern_payload["pattern"]
                pattern_type = pro_pattern.get("type")
                pattern_mode = pro_pattern.get("mode", "loose")
                render_profile = pro_pattern.get("render_profile", {
                    "opacity": 0.10,
                    "lineWidth": 1.5,
                    "dash": True,
                    "fill": True,
                })
                
                # Build geometry from PRO pattern anchors
                # LOWERED from 3 to 2 anchors for loose patterns (range has 4 corners = 4 anchors from build_anchors)
                anchors = pro_pattern.get("anchors", [])
                boundaries = pro_pattern.get("meta", {}).get("boundaries", {})
                
                # For loose_range: even with 2 anchors, we have boundaries
                if len(anchors) >= 2 or boundaries:
                    geo = {
                        "is_valid": True,
                        "anchors": anchors,
                        "boundaries": boundaries,
                        "mode": pattern_mode,
                    }
                    geo_source = "pro_pattern_engine"
            
            # Determine if we can render
            can_render = (
                geo is not None
                and pattern_type is not None
                and geo_source is not None
            )
            
            if can_render:
                # Update analysis mode
                final["analysis_mode"] = "figure"
                
                # Update summary based on pattern mode
                label = pattern_type.replace("_", " ").title() if pattern_type else "Pattern"
                
                if pattern_mode == "loose":
                    state = "forming"
                    if pro_pattern_payload and pro_pattern_payload.get("pattern_meta"):
                        state = pro_pattern_payload["pattern_meta"].get("state", "forming")
                    final["summary"]["title"] = f"{label} Developing"
                    final["summary"]["text"] = f"A {label.lower()} formation is developing. Currently {state}."
                else:
                    # Strict pattern
                    final["summary"]["title"] = f"{label} Detected"
                    final["summary"]["text"] = f"A {label.lower()} pattern has been identified with high confidence."
                
                final["ui"] = {
                    "main_overlay": {
                        "type": pattern_type,
                        "render_mode": "polygon",
                        "geometry": geo,
                        "source": geo_source,
                        "mode": pattern_mode,
                        "render_profile": render_profile,
                    },
                }
                
                # Add alternatives if available
                if pro_pattern_payload and pro_pattern_payload.get("alternatives"):
                    final["ui"]["alternatives"] = pro_pattern_payload["alternatives"]
                    
            else:
                # NO geometry → check if we have ANY pattern info from PRO engine
                if pro_pattern_payload and pro_pattern_payload.get("pattern"):
                    # We have a pattern but can't render geometry
                    pro_pattern = pro_pattern_payload["pattern"]
                    label = pro_pattern.get("type", "structure").replace("_", " ").title()
                    mode = pro_pattern.get("mode", "loose")
                    
                    final["analysis_mode"] = "structure"
                    if mode == "loose":
                        final["summary"]["title"] = f"{label} Developing"
                        final["summary"]["text"] = f"A {label.lower()} formation is developing. Market structure is forming."
                    else:
                        final["summary"]["title"] = f"{label} Detected"
                        final["summary"]["text"] = f"A {label.lower()} pattern detected. Structure identified."
                else:
                    # Truly no pattern
                    final["analysis_mode"] = "structure"
                    final["summary"]["title"] = "Structure Developing"
                    final["summary"]["text"] = "Market structure is in transition."
                    
                final["ui"] = {
                    "main_overlay": None,
                }
            
            return final
            
        except Exception as e:
            # Fallback - STILL never empty
            return {
                "timeframe": timeframe,
                "analysis_mode": "context",
                "figure": None,
                "structure": {
                    "trend": "neutral",
                    "phase": "unknown",
                    "swing_state": "Analysis unavailable",
                    "bias": "neutral",
                    "is_meaningful": False,
                },
                "context": {
                    "regime": "unknown",
                    "volatility": "normal",
                    "location": "unknown",
                    "range_position": "middle",
                },
                "ui": {"main_overlay": None},
                "summary": {
                    "title": "Analysis temporarily unavailable",
                    "text": f"Unable to analyze {timeframe}. Error: {str(e)[:50]}",
                },
            }
    
    def _build_chain_map(
        self,
        unified_setup: Dict[str, Any],
        liquidity: Dict[str, Any],
        displacement: Dict[str, Any],
        choch_validation: Dict[str, Any],
        poi: Dict[str, Any],
        primary_pattern: Optional[Dict[str, Any]],
        candles: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """
        Build chain_map for chart highlighting.
        
        Maps each chain element to chart coordinates.
        """
        chain_map = []
        chain = unified_setup.get("chain", [])
        
        # Map sweeps
        sweeps = liquidity.get("sweeps", []) if liquidity else []
        for sweep in sweeps[:2]:
            chain_map.append({
                "type": "sweep",
                "label": sweep.get("label", "sweep"),
                "direction": sweep.get("direction"),
                "candle_index": sweep.get("candle_index"),
                "price": sweep.get("price"),
            })
        
        # Map displacement events
        events = displacement.get("events", []) if displacement else []
        for event in events[:2]:
            chain_map.append({
                "type": "displacement",
                "direction": event.get("direction"),
                "start_index": event.get("start_index"),
                "end_index": event.get("end_index"),
                "impulse": event.get("impulse"),
            })
        
        # Map CHOCH
        if choch_validation and choch_validation.get("is_valid"):
            chain_map.append({
                "type": "choch",
                "direction": choch_validation.get("direction"),
                "price": choch_validation.get("price"),
                "candle_index": choch_validation.get("candle_index"),
            })
        
        # Map POI zones
        zones = poi.get("zones", []) if poi else []
        for zone in zones[:3]:
            chain_map.append({
                "type": "poi",
                "zone_type": zone.get("type"),
                "price_low": zone.get("price_low", zone.get("lower")),
                "price_high": zone.get("price_high", zone.get("upper")),
            })
        
        # Map pattern
        if primary_pattern:
            chain_map.append({
                "type": "pattern",
                "pattern_type": primary_pattern.get("type"),
                "direction_bias": primary_pattern.get("direction_bias"),
                "breakout_level": primary_pattern.get("breakout_level"),
                "invalidation": primary_pattern.get("invalidation"),
            })
        
        return chain_map

    # ═══════════════════════════════════════════════════════════════
    # HTF CONTEXT BUILDER — For 1M/6M/1Y timeframes
    # ═══════════════════════════════════════════════════════════════
    
    def _build_htf_context(
        self,
        candles: List[Dict[str, Any]],
        symbol: str,
        timeframe: str
    ) -> Dict[str, Any]:
        """
        Build HTF context for macro timeframes (1M, 6M, 1Y).
        
        Uses HTF Context Engine instead of pattern detection.
        Returns macro context, NOT forced patterns.
        """
        from modules.ta_engine.htf_context_engine import get_htf_context_engine
        
        htf_engine = get_htf_context_engine()
        htf_context = htf_engine.build_context(candles, timeframe)
        
        current_price = float(candles[-1]["close"]) if candles else 0
        
        # Build render_plan for HTF (simplified)
        render_plan = {
            "timeframe": timeframe,
            "current_price": current_price,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "render_mode": "htf_context_mode",
            "market_state": {
                "trend": htf_context.get("trend", "unknown"),
                "current_price": current_price,
            },
            "structure": {
                "swings": [],  # HTF doesn't show minor swings
                "trend": htf_context.get("trend"),
            },
            "levels": [
                {
                    "price": lvl["price"],
                    "type": lvl["type"],
                    "strength": lvl.get("touches", 1) / 3,  # Normalize
                    "source": "htf_macro",
                }
                for lvl in htf_context.get("major_levels", [])
            ],
            "liquidity": None,
            "execution": None,
        }
        
        # Build interpretation for display
        interpretation = htf_context.get("interpretation", f"{timeframe} analysis")
        
        return {
            "timeframe": timeframe,
            "symbol": symbol,
            "candles": candles,
            "candle_count": len(candles),
            "current_price": current_price,
            "interpretation": interpretation,
            
            # HTF Context (NEW)
            "htf_context": htf_context,
            "is_htf": True,
            
            # Structure (from HTF context)
            "structure_context": {
                "type": htf_context.get("trend", "unknown"),
                "trend_direction": htf_context.get("trend"),
                "is_htf": True,
                "macro_structure": htf_context.get("macro_structure"),
            },
            "structure_state": {
                "direction": htf_context.get("trend"),
                "is_htf": True,
            },
            
            # Levels (from HTF context)
            "liquidity": None,  # HTF doesn't track micro liquidity
            "displacement": None,
            "choch_validation": None,
            "poi": None,
            "fib": None,
            
            # Pattern — HTF does NOT force patterns
            "primary_pattern": None,
            "pattern_geometry": None,
            "pattern_render_contract": None,
            "alternative_patterns": [],
            "alternative_render_contracts": [],
            
            # Indicators (minimal for HTF)
            "indicator_result": [],
            "indicators": {"overlays": [], "panes": []},
            "indicator_insights": {},
            
            # Decision (from HTF context)
            "ta_context": {
                "role": "HTF",
                "timeframe": timeframe,
                "trend": htf_context.get("trend"),
                "confidence": htf_context.get("confidence", 0),
            },
            "decision": {
                "direction": "context_only",  # HTF provides context, not trading direction
                "confidence": htf_context.get("confidence", 0),
                "rationale": interpretation,
                "is_htf_context": True,
            },
            
            # No trade setup for HTF
            "unified_setup": {"valid": False, "direction": "context_only", "chain": []},
            "trade_setup": {"primary": None},
            "execution": {"valid": False, "is_htf": True},
            
            # Render plan
            "render_plan": render_plan,
            "chain_map": [],
            
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    
    def _empty_result(self, timeframe: str, symbol: str) -> Dict[str, Any]:
        """Return empty result template."""
        return {
            "timeframe": timeframe,
            "symbol": symbol,
            "candles": [],
            "candle_count": 0,
            "current_price": 0,
            "structure_context": None,
            "liquidity": None,
            "displacement": None,
            "choch_validation": None,
            "poi": None,
            "fib": None,
            "primary_pattern": None,
            "alternative_patterns": [],
            "indicator_result": None,
            "indicators": {"overlays": [], "panes": []},  # Empty renderable indicators
            "indicator_insights": {},  # Empty insights
            "ta_context": None,
            "decision": None,
            "unified_setup": {"valid": False, "direction": "no_trade", "chain": []},
            "trade_setup": None,
            "execution": {"valid": False},
            "chain_map": [],
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }


# Factory
_per_tf_builder = None

def get_per_timeframe_builder() -> PerTimeframeBuilder:
    global _per_tf_builder
    if _per_tf_builder is None:
        _per_tf_builder = PerTimeframeBuilder()
    return _per_tf_builder


def build_ta_from_candles(
    candles: List[Dict[str, Any]],
    symbol: str,
    timeframe: str
) -> Dict[str, Any]:
    """
    Build TA from candles (for backtest use).
    
    This is a convenience wrapper around PerTimeframeBuilder.build().
    
    Args:
        candles: OHLCV candle data
        symbol: Trading pair
        timeframe: Timeframe string
    
    Returns:
        TA payload dict
    """
    builder = get_per_timeframe_builder()
    return builder.build(candles, symbol, timeframe)
