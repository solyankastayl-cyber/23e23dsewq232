"""
Expected vs Actual Engine - Compares planned trade with market reality
"""
from datetime import datetime, timezone
from typing import List, Dict, Optional


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class ExpectedVsActualEngine:
    """
    Evaluates shadow trades against actual market movement.
    
    This is the core truth engine that answers:
    - Did the entry get reached?
    - Was target hit or stop hit first?
    - What was the actual drift from planned entry?
    - Was it a wrong early (stop before target opportunity)?
    """
    
    def evaluate(self, shadow_trade: dict, market_path: List[dict]) -> dict:
        """
        Evaluate a shadow trade against a market path (list of candles).
        
        market_path should be list of dicts with: timestamp, open, high, low, close
        """
        entry = shadow_trade.get("planned_entry")
        stop = shadow_trade.get("planned_stop")
        target = shadow_trade.get("planned_target")
        direction = shadow_trade.get("direction", "NEUTRAL")
        
        # Initialize tracking
        entry_reached = False
        actual_entry = None
        actual_exit = None
        entry_candle_idx = None
        exit_candle_idx = None
        
        target_hit = False
        stop_hit = False
        expired = False
        
        # Track first opportunity for target (to detect wrong_early)
        target_was_achievable = False
        
        # Process candles in order
        for idx, candle in enumerate(market_path):
            high = candle.get("high", 0)
            low = candle.get("low", 0)
            
            # Check entry condition
            if not entry_reached and entry is not None:
                if direction == "LONG":
                    # For LONG: entry at or below the planned entry price
                    if low <= entry:
                        entry_reached = True
                        actual_entry = min(entry, high)  # Worst case fill at entry or high if gapped
                        entry_candle_idx = idx
                elif direction == "SHORT":
                    # For SHORT: entry at or above the planned entry price
                    if high >= entry:
                        entry_reached = True
                        actual_entry = max(entry, low)  # Worst case fill at entry or low if gapped
                        entry_candle_idx = idx
            
            # If entered, check exit conditions
            if entry_reached:
                if direction == "LONG":
                    # Check target first (benefit of doubt)
                    if target is not None and high >= target:
                        target_hit = True
                        actual_exit = target
                        exit_candle_idx = idx
                        break
                    # Then check stop
                    if stop is not None and low <= stop:
                        stop_hit = True
                        actual_exit = stop
                        exit_candle_idx = idx
                        break
                    # Track if target was achievable at some point
                    if target is not None and high >= target * 0.995:  # Within 0.5% of target
                        target_was_achievable = True
                        
                elif direction == "SHORT":
                    # Check target first
                    if target is not None and low <= target:
                        target_hit = True
                        actual_exit = target
                        exit_candle_idx = idx
                        break
                    # Then check stop
                    if stop is not None and high >= stop:
                        stop_hit = True
                        actual_exit = stop
                        exit_candle_idx = idx
                        break
                    # Track if target was achievable
                    if target is not None and low <= target * 1.005:
                        target_was_achievable = True
        
        # Determine final result
        if not entry_reached:
            expired = True
            result = "EXPIRED"
            reason = "entry_not_reached"
        elif target_hit:
            result = "WIN"
            reason = "target_reached_after_entry"
        elif stop_hit:
            result = "LOSS"
            reason = "stop_reached_after_entry"
        else:
            result = "OPEN"
            reason = "trade_still_open"
        
        # Calculate PnL
        pnl = 0.0
        pnl_pct = 0.0
        
        if actual_entry and actual_exit:
            if direction == "LONG":
                pnl = actual_exit - actual_entry
                pnl_pct = ((actual_exit - actual_entry) / actual_entry) * 100
            elif direction == "SHORT":
                pnl = actual_entry - actual_exit
                pnl_pct = ((actual_entry - actual_exit) / actual_entry) * 100
        
        # Calculate drift (difference between planned and actual entry)
        drift_bps = 0.0
        if entry and actual_entry:
            drift_bps = abs(actual_entry - entry) / entry * 10000  # in basis points
        
        # Detect wrong_early
        wrong_early = stop_hit and target_was_achievable
        if stop_hit and not target_was_achievable:
            wrong_early = True  # Stop before any chance at target
        
        # Calculate timing
        time_to_entry_ms = None
        time_in_trade_ms = None
        
        if entry_candle_idx is not None and len(market_path) > 0:
            # Rough estimate based on candle positions
            try:
                entry_ts = datetime.fromisoformat(market_path[entry_candle_idx].get("timestamp", "").replace("Z", "+00:00"))
                start_ts = datetime.fromisoformat(market_path[0].get("timestamp", "").replace("Z", "+00:00"))
                time_to_entry_ms = int((entry_ts - start_ts).total_seconds() * 1000)
                
                if exit_candle_idx is not None:
                    exit_ts = datetime.fromisoformat(market_path[exit_candle_idx].get("timestamp", "").replace("Z", "+00:00"))
                    time_in_trade_ms = int((exit_ts - entry_ts).total_seconds() * 1000)
            except:
                pass
        
        return {
            "shadow_id": shadow_trade["shadow_id"],
            "symbol": shadow_trade["symbol"],
            
            "result": result,
            "actual_entry": actual_entry,
            "actual_exit": actual_exit,
            
            "target_hit": target_hit,
            "stop_hit": stop_hit,
            "expired": expired,
            
            "pnl": round(pnl, 6),
            "pnl_pct": round(pnl_pct, 4),
            
            "entry_reached": entry_reached,
            "drift_bps": round(drift_bps, 2),
            
            "wrong_early": wrong_early,
            "validation_reason": reason,
            
            "time_to_entry_ms": time_to_entry_ms,
            "time_in_trade_ms": time_in_trade_ms,
            
            "validated_at": utc_now(),
        }
    
    def evaluate_batch(
        self, 
        shadow_trades: List[dict], 
        market_paths: Dict[str, List[dict]]
    ) -> List[dict]:
        """
        Evaluate multiple shadow trades against their respective market paths.
        
        market_paths is a dict keyed by shadow_id containing the candle list.
        """
        results = []
        for shadow in shadow_trades:
            shadow_id = shadow["shadow_id"]
            if shadow_id in market_paths:
                result = self.evaluate(shadow, market_paths[shadow_id])
                results.append(result)
        return results
