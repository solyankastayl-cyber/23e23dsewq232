"""
Render Plan Engine v2
=====================

Builds render-ready TA visualization with 6 ISOLATED LAYERS.

LAYERS:
  A. Market State (trend, channel, volatility, momentum, wyckoff)
  B. Structure (swings, HH/HL/LH/LL, BOS, CHOCH, MSS)
  C. Tools/Indicators (EMA, BB, RSI, MACD, etc.)
  D. Pattern Figures (ONLY from pattern registry - NOT channel/trend)
  E. Liquidity/Smart Money (EQH/EQL, sweeps, OB, FVG, etc.)
  F. Execution (valid/waiting/no_trade, entry, stop, targets)

KEY RULES:
  - 1 timeframe = 1 isolated render plan
  - 1 active primary pattern max
  - 1 active POI zone max
  - 1-2 key liquidity elements max
  - 1 CHOCH/BOS max each
  - 2 overlays max by default
  - 1 pane max by default
  - Execution ALWAYS visible
  - Channel/trend are NOT patterns - they go to market_state

VISUAL HIERARCHY:
  1. Execution (strongest)
  2. Primary figure
  3. POI
  4. Key breakout/invalidation
  5. Structure
  6. Liquidity
  7. Indicators (supportive)
"""

from __future__ import annotations
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone


class RenderPlanEngineV2:
    """
    Builds render_plan with 6 strictly separated layers.
    
    Frontend renders ONLY what this engine returns.
    No analytical assumptions on frontend.
    """
    
    # Limits for clean visualization
    MAX_PRIMARY_PATTERNS = 1
    MAX_ALTERNATIVE_PATTERNS = 1
    MAX_POI_ZONES = 1
    MAX_LIQUIDITY_ELEMENTS = 2
    MAX_STRUCTURE_CHOCH = 1
    MAX_STRUCTURE_BOS = 1
    MAX_STRUCTURE_SWINGS = 6
    MAX_INDICATOR_OVERLAYS = 2
    MAX_INDICATOR_PANES = 1
    
    def build(
        self,
        timeframe: str,
        current_price: float,
        market_state: Dict[str, Any],
        structure: Dict[str, Any],
        indicators: Dict[str, Any],
        patterns: List[Dict[str, Any]],
        liquidity: Dict[str, Any],
        execution: Dict[str, Any],
        poi: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Build complete render plan for ONE timeframe.
        
        Args:
            timeframe: e.g., "4H", "1D"
            current_price: Latest price
            market_state: From MarketStateEngine (Layer A)
            structure: Price action structure (Layer B)
            indicators: Computed indicators (Layer C)
            patterns: Detected pattern figures (Layer D)
            liquidity: Smart money data (Layer E)
            execution: Trade execution status (Layer F)
            poi: Points of interest
        
        Returns:
            Render-ready plan with all 6 layers properly filtered
        """
        # Determine render mode: figure_mode or range_mode
        render_mode = self._determine_render_mode(market_state, patterns)
        
        return {
            "timeframe": timeframe,
            "current_price": current_price,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "render_mode": render_mode,
            
            # Layer A: Market State (context, NOT pattern)
            "market_state": self._build_market_state_layer(market_state),
            
            # Layer B: Structure
            "structure": self._build_structure_layer(structure),
            
            # Layer B2: Key Levels (MAX 5 for readability)
            "levels": self._build_levels_layer(structure, liquidity, current_price),
            
            # Layer C: Indicators (with smart selection based on market_state)
            "indicators": self._build_indicators_layer(indicators, render_mode, market_state),
            
            # Layer D: Pattern Figures (ONLY real patterns, NO channels)
            "patterns": self._build_patterns_layer(patterns, current_price),
            
            # Layer E: Liquidity / Smart Money
            "liquidity": self._build_liquidity_layer(liquidity, current_price),
            
            # Layer F: Execution (ALWAYS present)
            "execution": self._build_execution_layer(execution),
            
            # POI (filtered)
            "poi": self._build_poi_layer(poi, current_price),
            
            # Range boundaries (for range_mode)
            "range_context": self._build_range_context(market_state, liquidity, current_price) if render_mode == "range_mode" else None,
            
            # Meta
            "meta": self._build_meta(market_state, patterns, execution, render_mode),
            
            # Visual hints for frontend
            "visual_priority": self._build_visual_priority(execution, patterns, liquidity, render_mode),
        }
    
    # ═══════════════════════════════════════════════════════════════
    # RENDER MODE DETECTION
    # ═══════════════════════════════════════════════════════════════
    
    def _determine_render_mode(
        self,
        market_state: Dict[str, Any],
        patterns: List[Dict[str, Any]],
    ) -> str:
        """
        Determine render mode: figure_mode or range_mode.
        
        If market is in range/horizontal channel with no valid figure → range_mode
        If valid figure pattern exists → figure_mode
        """
        # Check if we have a valid (non-channel) pattern
        has_valid_pattern = False
        if patterns:
            for p in patterns:
                p_type = (p.get("type") or "").lower()
                # Skip channels/ranges/trends
                if any(kw in p_type for kw in ["channel", "range", "trend", "sideways"]):
                    continue
                if p.get("state") in ["forming", "active"]:
                    has_valid_pattern = True
                    break
        
        if has_valid_pattern:
            return "figure_mode"
        
        # Check market state for range/channel
        if market_state:
            channel_type = market_state.get("channel_type", "")
            trend = market_state.get("trend_direction", "")
            
            # If horizontal channel or sideways trend → range_mode
            if channel_type in ["horizontal_channel", "horizontal"] or trend in ["sideways", "ranging"]:
                return "range_mode"
        
        return "structure_mode"  # Default: focus on structure
    
    # ═══════════════════════════════════════════════════════════════
    # RANGE CONTEXT (for range_mode)
    # ═══════════════════════════════════════════════════════════════
    
    def _build_range_context(
        self,
        market_state: Dict[str, Any],
        liquidity: Dict[str, Any],
        current_price: float,
    ) -> Dict[str, Any]:
        """
        Build range context for range_mode rendering.
        
        Shows:
        - range_high (resistance)
        - range_low (support)  
        - midline
        - liquidity at edges
        - breakout triggers
        """
        if not market_state:
            return None
        
        # Try to determine range boundaries from liquidity
        range_high = None
        range_low = None
        
        if liquidity:
            bsl = liquidity.get("bsl")  # Buy side liquidity (resistance)
            ssl = liquidity.get("ssl")  # Sell side liquidity (support)
            
            if bsl:
                range_high = bsl
            if ssl:
                range_low = ssl
            
            # Also check eq_highs/eq_lows
            eq_highs = liquidity.get("eq_highs", [])
            eq_lows = liquidity.get("eq_lows", [])
            
            if eq_highs and not range_high:
                range_high = max(h.get("price", 0) for h in eq_highs)
            if eq_lows and not range_low:
                range_low = min(l.get("price", 0) for l in eq_lows)
        
        if not range_high or not range_low:
            return None
        
        midline = (range_high + range_low) / 2
        range_size = range_high - range_low
        
        # Determine position in range
        if current_price:
            position_pct = (current_price - range_low) / range_size * 100 if range_size > 0 else 50
        else:
            position_pct = 50
        
        return {
            "range_high": range_high,
            "range_low": range_low,
            "midline": midline,
            "range_size": range_size,
            "position_pct": position_pct,
            "breakout_trigger_up": range_high * 1.005,  # 0.5% above
            "breakout_trigger_down": range_low * 0.995,  # 0.5% below
            "bias": "neutral" if 40 < position_pct < 60 else ("bullish" if position_pct > 60 else "bearish"),
        }
    
    # ═══════════════════════════════════════════════════════════════
    # LAYER A: MARKET STATE
    # ═══════════════════════════════════════════════════════════════
    
    def _build_market_state_layer(self, market_state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Build market state layer.
        
        This is CONTEXT, not pattern.
        Includes: trend, channel, volatility, momentum, wyckoff.
        
        Rendered as background/context badge, NOT as main pattern.
        """
        if not market_state:
            return {
                "trend_direction": "unknown",
                "trend_strength": "no_trend",
                "channel_type": "no_channel",
                "volatility_regime": "normal_volatility",
                "momentum_regime": "neutral",
                "wyckoff_phase": "unknown",
                "trend_score": 0.0,
            }
        
        return {
            "trend_direction": market_state.get("trend_direction", "unknown"),
            "trend_strength": market_state.get("trend_strength", "no_trend"),
            "channel_type": market_state.get("channel_type", "no_channel"),
            "volatility_regime": market_state.get("volatility_regime", "normal_volatility"),
            "momentum_regime": market_state.get("momentum_regime", "neutral"),
            "wyckoff_phase": market_state.get("wyckoff_phase", "unknown"),
            "major_trend": market_state.get("major_trend", "unknown"),
            "minor_trend": market_state.get("minor_trend", "unknown"),
            "trend_score": market_state.get("trend_score", 0.0),
            "atr_normalized": market_state.get("atr_normalized", 0.0),
            "volatility_percentile": market_state.get("volatility_percentile", 50.0),
        }
    
    # ═══════════════════════════════════════════════════════════════
    # LAYER B: STRUCTURE
    # ═══════════════════════════════════════════════════════════════
    
    MAX_CHART_SWINGS = 4  # Max swings to render on chart
    
    def _build_structure_layer(self, structure: Dict[str, Any]) -> Dict[str, Any]:
        """
        Build structure layer for CHART RENDERING.
        
        STRICT LIMITS for readability:
        - MAX 4 swings (not 6!)
        - 1 CHOCH max
        - 1 BOS max
        - Prioritize HH/LL over HL/LH
        """
        if not structure:
            return {
                "swings": [],
                "choch": None,
                "bos": None,
                "bias": "neutral",
            }
        
        # Get swings and normalize format
        raw_swings = structure.get("swings", [])
        
        # Prioritize: HH/LL are more important than HL/LH
        def swing_importance(s):
            label = s.get("label", s.get("type", ""))
            if label in ["HH", "LL"]:
                return 2
            elif label in ["HL", "LH"]:
                return 1
            return 0
        
        # Sort by importance, then take last MAX_CHART_SWINGS
        sorted_swings = sorted(raw_swings, key=lambda s: (swing_importance(s), s.get("time", 0)))
        limited_swings = sorted_swings[-self.MAX_CHART_SWINGS:]
        
        # Normalize format: label → type
        normalized = []
        for s in limited_swings:
            normalized.append({
                "time": s.get("time"),
                "price": s.get("price"),
                "type": s.get("label", s.get("type", "H")),  # HH/HL/LH/LL
            })
        
        # Get most recent CHOCH
        choch_list = structure.get("choch", [])
        choch = choch_list[-1] if choch_list else structure.get("last_choch")
        
        # Get most recent BOS
        bos_list = structure.get("bos", [])
        bos = bos_list[-1] if bos_list else structure.get("last_bos")
        
        return {
            "swings": normalized,
            "choch": choch,
            "bos": bos,
            "bias": structure.get("bias", "neutral"),
        }

    # ═══════════════════════════════════════════════════════════════
    # LAYER B2: KEY LEVELS (MAX 5 for chart readability)
    # ═══════════════════════════════════════════════════════════════
    
    MAX_CHART_LEVELS = 5
    
    def _build_levels_layer(
        self,
        structure: Dict[str, Any],
        liquidity: Dict[str, Any],
        current_price: float,
    ) -> List[Dict[str, Any]]:
        """
        Build key levels for chart rendering.
        
        STRICT LIMIT: MAX 5 levels.
        
        Sources:
        - structure.active_supports / active_resistances
        - liquidity.key_levels
        - swing highs/lows as implicit levels
        
        Scoring:
        - touches * 0.5
        - recency * 0.3
        - volume * 0.2
        """
        levels = []
        
        # 1. From structure (supports/resistances)
        if structure:
            for lvl in structure.get("active_supports", []):
                levels.append({
                    "price": lvl.get("price", lvl) if isinstance(lvl, dict) else lvl,
                    "type": "support",
                    "strength": lvl.get("strength", 0.5) if isinstance(lvl, dict) else 0.5,
                    "source": "structure",
                })
            for lvl in structure.get("active_resistances", []):
                levels.append({
                    "price": lvl.get("price", lvl) if isinstance(lvl, dict) else lvl,
                    "type": "resistance",
                    "strength": lvl.get("strength", 0.5) if isinstance(lvl, dict) else 0.5,
                    "source": "structure",
                })
        
        # 2. From liquidity key_levels
        if liquidity:
            for lvl in liquidity.get("key_levels", []):
                price = lvl.get("price", lvl) if isinstance(lvl, dict) else lvl
                levels.append({
                    "price": price,
                    "type": "resistance" if price > current_price else "support",
                    "strength": lvl.get("strength", 0.6) if isinstance(lvl, dict) else 0.6,
                    "source": "liquidity",
                })
        
        # 3. From swing points (HH/LL as strong levels)
        if structure:
            for swing in structure.get("swings", []):
                label = swing.get("label", swing.get("type", ""))
                if label in ["HH", "LL"]:
                    price = swing.get("price")
                    if price:
                        levels.append({
                            "price": price,
                            "type": "resistance" if label == "HH" else "support",
                            "strength": 0.8,  # HH/LL are strong
                            "source": "swing",
                        })
        
        # Deduplicate by price (within 0.5% tolerance)
        unique_levels = []
        for lvl in levels:
            is_duplicate = False
            for existing in unique_levels:
                if abs(lvl["price"] - existing["price"]) / existing["price"] < 0.005:
                    # Keep the stronger one
                    if lvl["strength"] > existing["strength"]:
                        existing.update(lvl)
                    is_duplicate = True
                    break
            if not is_duplicate:
                unique_levels.append(lvl)
        
        # Sort by strength and take top MAX_CHART_LEVELS
        sorted_levels = sorted(unique_levels, key=lambda x: x["strength"], reverse=True)
        return sorted_levels[:self.MAX_CHART_LEVELS]

    
    # ═══════════════════════════════════════════════════════════════
    # LAYER C: INDICATORS (SMART SELECTION)
    # ═══════════════════════════════════════════════════════════════
    
    def _build_indicators_layer(
        self, 
        indicators: Dict[str, Any], 
        render_mode: str = "figure_mode",
        market_state: Dict[str, Any] = None,
    ) -> Dict[str, Any]:
        """
        Build indicators layer with SMART SELECTION.
        
        Like a trader, not a bot:
        - Trending market → EMA 20/50 + RSI
        - Ranging market → BBands + RSI
        - High volatility → VWAP + ATR
        
        STRICT LIMITS: 2 overlays, 1 pane
        """
        if not indicators:
            return {
                "overlays": [],
                "panes": [],
            }
        
        all_overlays = indicators.get("overlays", [])
        all_panes = indicators.get("panes", [])
        
        # Extract market context
        trend = market_state.get("trend_direction", "unknown") if market_state else "unknown"
        volatility = market_state.get("volatility_state", "normal") if market_state else "normal"
        
        # Smart selection based on market state
        selected_overlays = []
        selected_panes = []
        
        # Helper to find indicator by id
        def find_ind(ind_list, ind_id):
            for ind in ind_list:
                if ind.get("id", "").lower() == ind_id.lower():
                    return ind
            return None
        
        # HIGH VOLATILITY → VWAP + ATR
        if volatility in ["high", "extreme"]:
            vwap = find_ind(all_overlays, "vwap")
            if vwap:
                selected_overlays.append(vwap)
            atr = find_ind(all_panes, "atr")
            if atr:
                selected_panes.append(atr)
        
        # TRENDING MARKET → EMA 20/50 + RSI
        elif trend in ["uptrend", "downtrend", "strong_uptrend", "strong_downtrend"]:
            ema20 = find_ind(all_overlays, "ema_20")
            ema50 = find_ind(all_overlays, "ema_50")
            if ema20:
                selected_overlays.append(ema20)
            if ema50:
                selected_overlays.append(ema50)
            rsi = find_ind(all_panes, "rsi")
            if rsi:
                selected_panes.append(rsi)
        
        # RANGING MARKET → BBands + RSI
        elif trend in ["ranging", "sideways", "consolidation"]:
            bbands = find_ind(all_overlays, "bbands") or find_ind(all_overlays, "bollinger")
            if bbands:
                selected_overlays.append(bbands)
            rsi = find_ind(all_panes, "rsi")
            if rsi:
                selected_panes.append(rsi)
        
        # FALLBACK → EMA + RSI
        if not selected_overlays:
            ema20 = find_ind(all_overlays, "ema_20")
            ema50 = find_ind(all_overlays, "ema_50")
            if ema20:
                selected_overlays.append(ema20)
            if ema50:
                selected_overlays.append(ema50)
        
        if not selected_panes:
            rsi = find_ind(all_panes, "rsi")
            if rsi:
                selected_panes.append(rsi)
        
        return {
            "overlays": selected_overlays[:self.MAX_INDICATOR_OVERLAYS],
            "panes": selected_panes[:self.MAX_INDICATOR_PANES],
        }
    
    # ═══════════════════════════════════════════════════════════════
    # LAYER D: PATTERN FIGURES
    # ═══════════════════════════════════════════════════════════════
    
    def _build_patterns_layer(
        self, patterns: List[Dict[str, Any]], current_price: float
    ) -> Dict[str, Any]:
        """
        Build pattern figures layer.
        
        ONLY real patterns from registry.
        NOT channel, trend, EMA, or market state.
        
        ВАЖНО: Active Range (is_active=True) — это ВАЛИДНЫЙ паттерн!
        Range — это режим рынка, который нужно показывать пока нет breakout.
        
        If no valid pattern exists, explicitly show "no_active_figure".
        """
        # Check if any patterns passed
        if not patterns:
            return {
                "primary": None,
                "alternative": None,
                "has_figure": False,
                "status": "no_active_figure",
                "reason": "Market in channel/range mode — no reversal or continuation figure detected",
                "hint": "This is normal. Wait for breakout or pattern formation.",
                "all_detected": [],
            }
        
        # Filter valid patterns
        valid_patterns = []
        active_range = None  # Special handling for active range
        
        for p in patterns:
            p_type = (p.get("type") or "").lower()
            
            # SPECIAL CASE: Active Range (Range Regime Engine V2)
            # Active range IS a valid pattern - it's a market regime we need to show
            # Includes: "range", "loose_range", "tight_range", etc.
            if "range" in p_type and p.get("is_active") == True:
                # This is from Range Regime Engine V2 - it's valid!
                active_range = p
                continue
            
            # Skip channels/trends that are NOT from Range Regime Engine
            if any(kw in p_type for kw in ["channel", "trend", "sideways"]):
                continue
            
            # Skip inactive/closed ranges
            if "range" in p_type and p.get("is_active") == False:
                continue
            
            # Check score and state
            score = p.get("score", p.get("confidence", 0))
            state = p.get("state", "active")
            if score >= 0.5 and state in ["forming", "active", "testing_upper", "testing_lower"]:
                if self._is_near_price(p, current_price):
                    valid_patterns.append(p)
        
        # If we have an active range, add it to valid patterns
        if active_range:
            valid_patterns.insert(0, active_range)  # Priority
        
        if not valid_patterns:
            return {
                "primary": None,
                "alternative": None,
                "has_figure": False,
                "status": "no_active_figure",
                "reason": f"Found {len(patterns)} candidates but none qualify (low score or invalid state)",
                "all_detected": patterns,
            }
        
        # Sort by score (but active range stays at top)
        def sort_key(x):
            # Active range always first
            if x.get("type", "").lower() == "range" and x.get("is_active"):
                return (1, x.get("score", x.get("confidence", 0)))
            return (0, x.get("score", x.get("confidence", 0)))
        
        sorted_patterns = sorted(valid_patterns, key=sort_key, reverse=True)
        
        primary = sorted_patterns[0] if sorted_patterns else None
        alternative = sorted_patterns[1] if len(sorted_patterns) > 1 else None
        
        return {
            "primary": self._format_pattern(primary) if primary else None,
            "alternative": self._format_pattern(alternative) if alternative else None,
            "has_figure": primary is not None,
            "status": "active_figure" if primary else "no_active_figure",
            "reason": None,
            "all_detected": patterns,
        }
    
    def _is_near_price(self, pattern: Dict[str, Any], current_price: float) -> bool:
        """Check if pattern is relevant to current price."""
        breakout = pattern.get("breakout_level")
        invalidation = pattern.get("invalidation_level")
        
        if not breakout and not invalidation:
            return True
        
        # Pattern should be within 20% of current price
        tolerance = current_price * 0.20
        
        if breakout:
            if abs(breakout - current_price) > tolerance:
                return False
        
        return True
    
    def _format_pattern(self, pattern: Dict[str, Any]) -> Dict[str, Any]:
        """Format pattern for rendering."""
        # Get direction from multiple sources
        direction = pattern.get("direction") or pattern.get("bias") or pattern.get("direction_bias")
        
        result = {
            "id": pattern.get("id"),
            "type": pattern.get("type"),
            "name": pattern.get("name"),
            "category": pattern.get("category"),
            "direction": direction,  # Frontend expects 'direction'
            "bias": direction,  # Keep bias for backwards compatibility
            "state": pattern.get("state"),
            "score": pattern.get("score", pattern.get("confidence")),
            "confidence": pattern.get("confidence"),
            "breakout_level": pattern.get("breakout_level"),
            "invalidation_level": pattern.get("invalidation_level", pattern.get("invalidation")),
            "target_levels": pattern.get("target_levels", []),
            "points": pattern.get("points", []),
            "start_index": pattern.get("start_index"),
            "end_index": pattern.get("end_index"),
        }
        
        # Range Regime Engine V2 specific fields
        if pattern.get("is_active") is not None:
            result["is_active"] = pattern.get("is_active")
        if pattern.get("forward_bars") is not None:
            result["forward_bars"] = pattern.get("forward_bars")
        if pattern.get("breakout_state") is not None:
            result["breakout_state"] = pattern.get("breakout_state")
        if pattern.get("respect_score") is not None:
            result["respect_score"] = pattern.get("respect_score")
        if pattern.get("state_reason"):
            result["state_reason"] = pattern.get("state_reason")
        if pattern.get("engine"):
            result["engine"] = pattern.get("engine")
        
        return result
    
    # ═══════════════════════════════════════════════════════════════
    # LAYER E: LIQUIDITY / SMART MONEY
    # ═══════════════════════════════════════════════════════════════
    
    def _build_liquidity_layer(
        self, liquidity: Dict[str, Any], current_price: float
    ) -> Dict[str, Any]:
        """
        Build liquidity layer for chart rendering.
        
        LIMITS:
        - Max 2 BSL (above price)
        - Max 2 SSL (below price)
        - 1 recent sweep
        
        Sources:
        - pools (BSL/SSL)
        - equal_highs / equal_lows
        - sweeps
        """
        if not liquidity:
            return {
                "bsl": [],
                "ssl": [],
                "sweeps": [],
            }
        
        # Extract BSL/SSL from pools
        pools = liquidity.get("pools", [])
        bsl_list = [p for p in pools if p.get("type") == "buy_side_liquidity" and p.get("status") == "active"]
        ssl_list = [p for p in pools if p.get("type") == "sell_side_liquidity" and p.get("status") == "active"]
        
        # Sort by distance to current price, take nearest
        bsl_list.sort(key=lambda x: abs(x.get("price", 0) - current_price))
        ssl_list.sort(key=lambda x: abs(x.get("price", 0) - current_price))
        
        # Format for chart rendering (max 2 each)
        bsl_formatted = [
            {
                "price": p.get("price"),
                "strength": p.get("strength"),
                "touches": p.get("touches"),
                "label": p.get("label"),
            }
            for p in bsl_list[:2]
        ]
        
        ssl_formatted = [
            {
                "price": p.get("price"),
                "strength": p.get("strength"),
                "touches": p.get("touches"),
                "label": p.get("label"),
            }
            for p in ssl_list[:2]
        ]
        
        # Get most recent sweep
        all_sweeps = liquidity.get("sweeps", [])
        recent_sweep = None
        if all_sweeps:
            # Most recent by index
            recent_sweep = max(all_sweeps, key=lambda x: x.get("index", 0))
            recent_sweep = {
                "type": recent_sweep.get("type"),
                "price": recent_sweep.get("sweep_price"),
                "pool_price": recent_sweep.get("pool_price"),
                "direction": recent_sweep.get("direction"),
                "time": recent_sweep.get("time"),
                "description": recent_sweep.get("description"),
            }
        
        return {
            "bsl": bsl_formatted,
            "ssl": ssl_formatted,
            "sweeps": [recent_sweep] if recent_sweep else [],
        }
    
    # ═══════════════════════════════════════════════════════════════
    # LAYER F: EXECUTION
    # ═══════════════════════════════════════════════════════════════
    
    def _build_execution_layer(self, execution: Dict[str, Any]) -> Dict[str, Any]:
        """
        Build execution layer.
        
        ALWAYS visible. One of:
        - valid: shows entry, stop, targets, R:R
        - waiting: shows reason for waiting
        - no_trade: shows detailed reason why no trade
        
        Never empty. Never disappears.
        """
        if not execution:
            return {
                "status": "no_trade",
                "reason": "Insufficient analysis data",
                "detail": "Unable to compute execution - missing market data",
                "entry": None,
                "stop": None,
                "targets": [],
                "rr": None,
            }
        
        status = execution.get("status", "no_trade")
        
        if status == "valid":
            entry_plan = execution.get("entry_plan", {})
            stop_plan = execution.get("stop_plan", {})
            
            return {
                "status": "valid",
                "direction": execution.get("direction"),
                "model": execution.get("model"),
                "entry": entry_plan,
                "entry_zone": {
                    "low": entry_plan.get("zone_low") if entry_plan else None,
                    "high": entry_plan.get("zone_high") if entry_plan else None,
                    "ideal": entry_plan.get("price") if entry_plan else None,
                },
                "stop": stop_plan.get("price") if stop_plan else None,
                "stop_reason": stop_plan.get("reason") if stop_plan else None,
                "targets": execution.get("targets", []),
                "rr": execution.get("rr"),
                "risk_profile": execution.get("risk_profile"),
                "size_factor": execution.get("size_factor"),
                "reason": execution.get("reason", "Valid setup found"),
                "detail": f"Model: {execution.get('model', 'N/A')}, Direction: {execution.get('direction', 'N/A')}",
            }
        
        elif status == "waiting":
            return {
                "status": "waiting",
                "reason": execution.get("reason", "Waiting for confirmation"),
                "detail": execution.get("detail", "Setup forming, awaiting trigger"),
                "waiting_for": execution.get("waiting_for", []),
                "entry": None,
                "stop": None,
                "targets": [],
                "rr": None,
            }
        
        else:  # no_trade
            # Determine detailed reason
            reason = execution.get("reason", "No valid setup")
            detail = execution.get("detail")
            
            if not detail:
                # Try to infer reason from execution data
                if not execution.get("valid"):
                    detail = "No confirmed trade setup"
                elif execution.get("direction") == "no_trade":
                    detail = "Market conditions unfavorable"
                else:
                    detail = "Setup does not meet entry criteria"
            
            return {
                "status": "no_trade",
                "reason": reason,
                "detail": detail,
                "entry": None,
                "stop": None,
                "targets": [],
                "rr": None,
            }
    
    # ═══════════════════════════════════════════════════════════════
    # POI LAYER
    # ═══════════════════════════════════════════════════════════════
    
    def _build_poi_layer(
        self, poi: Optional[Dict[str, Any]], current_price: float
    ) -> List[Dict[str, Any]]:
        """
        Build POI layer.
        
        Limits: 1 active POI zone closest to price.
        """
        if not poi:
            return []
        
        zones = poi.get("zones", [])
        if not zones:
            return []
        
        # Find closest zone to price
        def zone_distance(z):
            mid = (z.get("price_low", 0) + z.get("price_high", 0)) / 2
            if mid == 0:
                mid = (z.get("lower", 0) + z.get("upper", 0)) / 2
            return abs(mid - current_price) if current_price else 0
        
        sorted_zones = sorted(zones, key=zone_distance)
        
        return sorted_zones[:self.MAX_POI_ZONES]
    
    # ═══════════════════════════════════════════════════════════════
    # META & VISUAL PRIORITY
    # ═══════════════════════════════════════════════════════════════
    
    def _build_meta(
        self,
        market_state: Dict[str, Any],
        patterns: List[Dict[str, Any]],
        execution: Dict[str, Any],
        render_mode: str = "figure_mode",
    ) -> Dict[str, Any]:
        """Build meta information."""
        # Determine focus
        if execution and execution.get("status") == "valid":
            focus = "execution"
        elif render_mode == "range_mode":
            focus = "range"
        elif patterns and any(p.get("state") == "active" for p in patterns):
            focus = "pattern"
        else:
            focus = "structure"
        
        # Determine regime from market state
        regime = "range"
        if market_state:
            trend = market_state.get("trend_direction", "unknown")
            channel = market_state.get("channel_type", "")
            
            if trend in ["uptrend", "downtrend"]:
                regime = "trend"
            elif channel in ["ascending_channel", "descending_channel"]:
                regime = "trend"
            elif channel == "horizontal_channel" or trend == "sideways":
                regime = "range"
        
        # Tradeability
        tradeability = "high" if execution and execution.get("status") == "valid" else "low"
        if regime == "range" and focus != "execution":
            tradeability = "low"
        
        return {
            "focus": focus,
            "regime": regime,
            "render_mode": render_mode,
            "tradeability": tradeability,
            "view_mode": "auto",  # Can be: auto, classic_ta, smart_money, minimal
        }
    
    def _build_visual_priority(
        self,
        execution: Dict[str, Any],
        patterns: List[Dict[str, Any]],
        liquidity: Dict[str, Any],
        render_mode: str = "figure_mode",
    ) -> Dict[str, Any]:
        """
        Build visual priority hints for frontend.
        
        Priority order:
        1. Execution (entry/stop/targets)
        2. Primary pattern
        3. POI
        4. Key breakout/invalidation
        5. Structure
        6. Liquidity
        7. Indicators
        """
        priority = []
        
        # 1. Execution always highest
        if execution and execution.get("status") == "valid":
            priority.append({
                "layer": "execution",
                "weight": 1.0,
                "z_index": 100,
                "line_weight": "heavy",
            })
        
        # 2. Primary pattern
        if patterns and any(p.get("state") == "active" for p in patterns):
            priority.append({
                "layer": "patterns",
                "weight": 0.9,
                "z_index": 90,
                "line_weight": "medium",
            })
        
        # 3. POI
        priority.append({
            "layer": "poi",
            "weight": 0.8,
            "z_index": 80,
            "style": "translucent",
        })
        
        # 4. Structure
        priority.append({
            "layer": "structure",
            "weight": 0.6,
            "z_index": 60,
            "line_weight": "light",
            "style": "subdued",
        })
        
        # 5. Liquidity
        priority.append({
            "layer": "liquidity",
            "weight": 0.5,
            "z_index": 50,
            "style": "dashed",
        })
        
        # 6. Indicators
        priority.append({
            "layer": "indicators",
            "weight": 0.4,
            "z_index": 40,
            "style": "supportive",
        })
        
        return {
            "order": priority,
            "execution_visible": execution.get("status") == "valid" if execution else False,
            "pattern_visible": bool(patterns and any(p.get("state") == "active" for p in patterns)),
            "range_mode": render_mode == "range_mode",
        }


# Singleton
_render_plan_engine_v2: Optional[RenderPlanEngineV2] = None


def get_render_plan_engine_v2() -> RenderPlanEngineV2:
    global _render_plan_engine_v2
    if _render_plan_engine_v2 is None:
        _render_plan_engine_v2 = RenderPlanEngineV2()
    return _render_plan_engine_v2
