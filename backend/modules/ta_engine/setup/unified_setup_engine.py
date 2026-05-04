"""
Unified Setup Engine (USE)
===========================

Builds ONE coherent setup from all TA components.

NOT summing signals — VALIDATING a chain:
  liquidity → displacement → structure shift → POI/Fib location → entry

If chain is incomplete → NO TRADE

Output:
  {
    "valid": bool,
    "direction": "long" | "short" | "no_trade",
    "narrative": str,
    "chain": [...],
    "conflicts": [...],
    "entry_context": {...}
  }
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional


class UnifiedSetupEngine:
    """
    Builds one coherent setup from:
    - decision
    - structure_context
    - liquidity
    - displacement
    - choch_validation
    - poi
    - fib
    - active_pattern
    - ta_context
    """

    def build(
        self,
        decision: Dict[str, Any],
        structure_context: Dict[str, Any],
        liquidity: Dict[str, Any],
        displacement: Dict[str, Any],
        choch_validation: Dict[str, Any],
        poi: Dict[str, Any],
        fib: Optional[Dict[str, Any]],
        active_pattern: Optional[Dict[str, Any]],
        ta_context: Dict[str, Any],
        current_price: float,
    ) -> Dict[str, Any]:
        """Build unified setup with validation chain."""
        
        # 1. Resolve direction
        direction = self._resolve_direction(decision, structure_context, choch_validation)
        if direction == "no_trade":
            return self._no_trade("no directional agreement")

        chain: List[str] = []
        conflicts: List[str] = []

        # 2. Check liquidity sweep (REQUIRED)
        sweep_ok = self._check_sweep(liquidity, direction)
        if sweep_ok:
            chain.append(sweep_ok)
        else:
            return self._no_trade("no liquidity event")

        # 3. Check displacement (REQUIRED)
        displacement_ok = self._check_displacement(displacement, direction)
        if displacement_ok:
            chain.append(displacement_ok)
        else:
            return self._no_trade("no displacement")

        # 4. Check structure confirmation (REQUIRED)
        structure_ok = self._check_structure(structure_context, choch_validation, direction)
        if structure_ok:
            chain.append(structure_ok)
        else:
            return self._no_trade("no structure confirmation")

        # 5. Check entry location (POI or Fib OR Pattern) (REQUIRED)
        poi_ok = self._check_poi(poi, current_price, direction)
        fib_ok = self._check_fib(fib, current_price, direction)
        pattern_entry_ok = self._check_pattern_entry(active_pattern, current_price, direction)

        if poi_ok:
            chain.append(poi_ok)
        elif fib_ok:
            chain.append(fib_ok)
        elif pattern_entry_ok:
            chain.append(pattern_entry_ok)
        else:
            return self._no_trade("no entry location")

        # 6. Check pattern support (OPTIONAL but strengthens)
        pattern_ok = self._check_pattern(active_pattern, direction)
        if pattern_ok:
            chain.append(pattern_ok)

        # 7. Collect conflicts
        conflicts = self._collect_conflicts(
            ta_context=ta_context,
            active_pattern=active_pattern,
            structure_context=structure_context,
            direction=direction,
        )

        # 8. Too many conflicts → NO TRADE
        if len(conflicts) >= 3:
            return self._no_trade("too many conflicts", conflicts=conflicts, chain=chain)

        # 9. Build entry context
        entry_context = self._build_entry_context(
            direction=direction,
            poi=poi,
            fib=fib,
            active_pattern=active_pattern,
            current_price=current_price,
        )

        return {
            "valid": True,
            "direction": direction,
            "narrative": self._build_narrative(direction, chain),
            "chain": chain,
            "conflicts": conflicts,
            "entry_context": entry_context,
        }

    # ---------------------------------------------------------
    # Direction Resolution
    # ---------------------------------------------------------
    def _resolve_direction(
        self,
        decision: Dict[str, Any],
        structure_context: Dict[str, Any],
        choch_validation: Dict[str, Any],
    ) -> str:
        """Resolve trade direction from multiple sources."""
        decision_bias = decision.get("bias") or decision.get("direction", "neutral")
        structure_bias = structure_context.get("bias", "neutral")

        # CHOCH takes priority if valid
        if choch_validation.get("is_valid"):
            choch_dir = choch_validation.get("direction")
            if choch_dir == "bullish" and decision_bias != "bearish":
                return "long"
            if choch_dir == "bearish" and decision_bias != "bullish":
                return "short"

        # Decision + Structure alignment
        if decision_bias == "bullish" and structure_bias != "bearish":
            return "long"
        if decision_bias == "bearish" and structure_bias != "bullish":
            return "short"

        return "no_trade"

    # ---------------------------------------------------------
    # Chain Validators
    # ---------------------------------------------------------
    def _check_sweep(self, liquidity: Dict[str, Any], direction: str) -> Optional[str]:
        """Check for liquidity sweep."""
        sweeps = liquidity.get("sweeps", []) if liquidity else []
        pools = liquidity.get("pools", []) if liquidity else []

        # For LONG: need sell-side sweep (sweep of lows)
        # For SHORT: need buy-side sweep (sweep of highs)
        wanted = "sell_side" if direction == "long" else "buy_side"
        alt_wanted = "SSL" if direction == "long" else "BSL"

        for s in sweeps:
            sweep_type = s.get("type", "").lower()
            if wanted in sweep_type or alt_wanted.lower() in sweep_type:
                return f"{alt_wanted} swept"
        
        # Check pools
        for p in pools:
            pool_type = p.get("type", "").lower()
            if wanted in pool_type or (direction == "long" and "ssl" in pool_type) or (direction == "short" and "bsl" in pool_type):
                if p.get("swept") or p.get("grabbed"):
                    return f"{alt_wanted} grabbed"
        
        return None

    def _check_displacement(self, displacement: Dict[str, Any], direction: str) -> Optional[str]:
        """Check for displacement (strong impulse move)."""
        events = displacement.get("events", []) if displacement else []
        
        # Also check direct displacement properties
        has_displacement = displacement.get("has_displacement", False)
        disp_direction = displacement.get("direction", "")
        
        wanted = "bullish" if direction == "long" else "bearish"

        # Check events
        for e in events:
            event_dir = e.get("direction", "").lower()
            is_impulse = e.get("impulse", False) or e.get("is_strong", False)
            
            if wanted in event_dir and is_impulse:
                return f"{wanted} displacement confirmed"
        
        # Check direct properties
        if has_displacement and wanted in disp_direction.lower():
            return f"{wanted} displacement detected"

        return None

    def _check_structure(
        self,
        structure_context: Dict[str, Any],
        choch_validation: Dict[str, Any],
        direction: str,
    ) -> Optional[str]:
        """Check for structure confirmation (CHOCH or aligned structure)."""
        
        # CHOCH is strongest confirmation
        if choch_validation.get("is_valid"):
            choch_dir = choch_validation.get("direction", "")
            if direction == "long" and choch_dir == "bullish":
                return "valid bullish CHOCH"
            if direction == "short" and choch_dir == "bearish":
                return "valid bearish CHOCH"

        # Structure bias alignment
        regime = structure_context.get("regime", "unknown")
        bias = structure_context.get("bias", "neutral")

        if direction == "long" and bias == "bullish":
            return f"bullish structure ({regime})"
        if direction == "short" and bias == "bearish":
            return f"bearish structure ({regime})"

        return None

    def _check_poi(self, poi: Dict[str, Any], current_price: float, direction: str) -> Optional[str]:
        """Check if price is at relevant POI zone."""
        zones = poi.get("zones", []) if poi else []
        
        # For LONG: need demand zone
        # For SHORT: need supply zone
        wanted = "demand" if direction == "long" else "supply"

        for z in zones:
            zone_type = z.get("type", "").lower()
            if wanted not in zone_type:
                continue
            
            # Skip mitigated zones
            if z.get("mitigated", False):
                continue

            zl = float(z.get("price_low", z.get("lower", 0)))
            zh = float(z.get("price_high", z.get("upper", 0)))

            # Check if price is within or near zone (2% buffer)
            buffer = (zh - zl) * 0.5 if zh > zl else current_price * 0.02
            if zl - buffer <= current_price <= zh + buffer:
                return f"active {wanted} zone near price"
        
        return None

    def _check_fib(self, fib: Optional[Dict[str, Any]], current_price: float, direction: str) -> Optional[str]:
        """Check if price is at key Fibonacci level."""
        if not fib:
            return None

        # Check multiple fib sources
        levels = fib.get("levels", {})
        if not levels:
            # Try retracement levels
            retracements = fib.get("retracements", [])
            for r in retracements:
                level_val = r.get("level", 0)
                price = r.get("price", 0)
                if level_val in [0.382, 0.5, 0.618, 0.786]:
                    dist = abs(float(price) - current_price) / max(current_price, 1e-9)
                    if dist < 0.02:
                        return f"fib {level_val} reaction zone"

        # Check levels dict
        key_levels = ["0.382", "0.5", "0.618", "0.786", "50%", "61.8%"]
        
        for key in key_levels:
            level = levels.get(key)
            if level is None:
                continue

            try:
                price = float(level) if not isinstance(level, dict) else float(level.get("price", 0))
            except:
                continue

            dist = abs(price - current_price) / max(current_price, 1e-9)
            if dist < 0.02:
                return f"fib {key} reaction zone"
        
        return None

    def _check_pattern(self, active_pattern: Optional[Dict[str, Any]], direction: str) -> Optional[str]:
        """Check if pattern supports direction."""
        if not active_pattern:
            return None

        bias = active_pattern.get("direction_bias") or active_pattern.get("direction", "neutral")
        pattern_type = active_pattern.get("type", "pattern")

        if direction == "long" and bias.lower() == "bullish":
            return f"{pattern_type.replace('_', ' ')} supports long"
        if direction == "short" and bias.lower() == "bearish":
            return f"{pattern_type.replace('_', ' ')} supports short"
        
        return None

    def _check_pattern_entry(self, active_pattern: Optional[Dict[str, Any]], current_price: float, direction: str) -> Optional[str]:
        """
        Check if pattern provides a valid entry location.
        
        Pattern can serve as entry if:
        1. Has breakout_level
        2. Price is near breakout level (within 5%)
        3. Pattern direction aligns with trade direction
        """
        if not active_pattern:
            return None
        
        breakout = active_pattern.get("breakout_level")
        invalidation = active_pattern.get("invalidation")
        bias = (active_pattern.get("direction_bias") or active_pattern.get("direction", "neutral")).lower()
        pattern_type = active_pattern.get("type", "pattern")
        
        if not breakout:
            return None
        
        # Check direction alignment
        if direction == "long" and bias != "bullish":
            return None
        if direction == "short" and bias != "bearish":
            return None
        
        # Check if price is near pattern zone (within 5% of breakout or invalidation)
        dist_to_breakout = abs(breakout - current_price) / max(current_price, 1e-9)
        dist_to_invalidation = abs(invalidation - current_price) / max(current_price, 1e-9) if invalidation else 1.0
        
        # Pattern is valid entry if price is within pattern zone
        if dist_to_breakout < 0.08 or dist_to_invalidation < 0.08:
            return f"{pattern_type.replace('_', ' ')} provides entry at breakout ${breakout:,.0f}"
        
        return None

    # ---------------------------------------------------------
    # Conflict Detection
    # ---------------------------------------------------------
    def _collect_conflicts(
        self,
        ta_context: Dict[str, Any],
        active_pattern: Optional[Dict[str, Any]],
        structure_context: Dict[str, Any],
        direction: str,
    ) -> List[str]:
        """Collect signals that conflict with the setup direction."""
        conflicts: List[str] = []

        # Check top drivers
        top = ta_context.get("top_drivers", []) if ta_context else []
        for driver in top[:5]:
            signal = driver.get("signal", "").lower()
            name = driver.get("name") or driver.get("source_id", "unknown")

            if direction == "long" and signal == "bearish":
                conflicts.append(f"{name} is bearish")
            if direction == "short" and signal == "bullish":
                conflicts.append(f"{name} is bullish")

        # Check pattern conflict
        if active_pattern:
            pbias = (active_pattern.get("direction_bias") or active_pattern.get("direction", "neutral")).lower()
            if direction == "long" and pbias == "bearish":
                conflicts.append("active pattern is bearish")
            if direction == "short" and pbias == "bullish":
                conflicts.append("active pattern is bullish")

        # Check structure conflict
        sbias = structure_context.get("bias", "neutral").lower()
        if direction == "long" and sbias == "bearish":
            conflicts.append("structure bias is bearish")
        if direction == "short" and sbias == "bullish":
            conflicts.append("structure bias is bullish")

        return conflicts[:5]

    # ---------------------------------------------------------
    # Entry Context
    # ---------------------------------------------------------
    def _build_entry_context(
        self,
        direction: str,
        poi: Dict[str, Any],
        fib: Optional[Dict[str, Any]],
        active_pattern: Optional[Dict[str, Any]],
        current_price: float,
    ) -> Dict[str, Any]:
        """Build entry context with zones and levels."""
        
        # Find nearest POI zone
        poi_zone = self._nearest_poi_zone(poi, current_price, direction)
        
        # Find nearest fib level
        fib_level = self._nearest_fib_level(fib, current_price)
        
        # Pattern-derived levels
        pattern_levels = None
        if active_pattern:
            breakout = active_pattern.get("breakout_level")
            invalidation = active_pattern.get("invalidation_level") or active_pattern.get("invalidation")
            
            if breakout and invalidation:
                height = abs(breakout - invalidation)
                
                if direction == "long":
                    pattern_levels = {
                        "entry_zone": [breakout, breakout * 1.005],
                        "stop": invalidation,
                        "tp1": breakout + height,
                        "tp2": breakout + height * 1.618,
                    }
                else:
                    pattern_levels = {
                        "entry_zone": [breakout * 0.995, breakout],
                        "stop": invalidation,
                        "tp1": breakout - height,
                        "tp2": breakout - height * 1.618,
                    }

        return {
            "model": "sweep_displacement_structure_return",
            "direction": direction,
            "preferred_zone": poi_zone,
            "fib_support": fib_level,
            "pattern_levels": pattern_levels,
        }

    def _nearest_poi_zone(self, poi: Dict[str, Any], current_price: float, direction: str) -> Optional[Dict[str, Any]]:
        """Find nearest relevant POI zone."""
        zones = poi.get("zones", []) if poi else []
        wanted = "demand" if direction == "long" else "supply"

        candidates = []
        for z in zones:
            if wanted not in z.get("type", "").lower():
                continue
                
            zl = float(z.get("price_low", z.get("lower", 0)))
            zh = float(z.get("price_high", z.get("upper", 0)))
            mid = (zl + zh) / 2
            dist = abs(mid - current_price) / max(current_price, 1e-9)
            candidates.append((dist, {
                "type": z.get("type"),
                "lower": zl,
                "upper": zh,
                "strength": z.get("strength", 0.5),
            }))

        if not candidates:
            return None

        candidates.sort(key=lambda x: x[0])
        return candidates[0][1]

    def _nearest_fib_level(self, fib: Optional[Dict[str, Any]], current_price: float) -> Optional[Dict[str, Any]]:
        """Find nearest Fibonacci level."""
        if not fib:
            return None

        levels = fib.get("levels", {})
        best = None
        best_dist = 10**9

        for k, v in levels.items():
            try:
                price = float(v) if not isinstance(v, dict) else float(v.get("price", 0))
            except (ValueError, TypeError, AttributeError):
                continue

            dist = abs(price - current_price)
            if dist < best_dist:
                best = {"level": k, "price": price}
                best_dist = dist

        return best

    # ---------------------------------------------------------
    # Output Helpers
    # ---------------------------------------------------------
    def _build_narrative(self, direction: str, chain: List[str]) -> str:
        """Build human-readable narrative from chain."""
        base = " → ".join(chain)
        prefix = "LONG" if direction == "long" else "SHORT"
        return f"{prefix}: {base}"

    def _no_trade(
        self, 
        reason: str, 
        conflicts: Optional[List[str]] = None, 
        chain: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Return NO TRADE result."""
        return {
            "valid": False,
            "direction": "no_trade",
            "narrative": f"NO TRADE: {reason}",
            "chain": chain or [],
            "conflicts": conflicts or [],
            "entry_context": None,
        }


# Singleton
_unified_setup_engine: Optional[UnifiedSetupEngine] = None


def get_unified_setup_engine() -> UnifiedSetupEngine:
    """Get singleton unified setup engine."""
    global _unified_setup_engine
    if _unified_setup_engine is None:
        _unified_setup_engine = UnifiedSetupEngine()
    return _unified_setup_engine
