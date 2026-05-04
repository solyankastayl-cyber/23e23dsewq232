"""
Signal Ranking V2 - AI-powered signal quality assessment

Ranks signals based on 5 factors:
- Alpha (35%): Confidence + Risk/Reward
- Historical (25%): Strategy win rate, Sharpe, drawdown
- Regime Fit (15%): Strategy alignment with current market regime
- Execution Fit (15%): Expected slippage, latency
- Portfolio Fit (10%): Risk heat, duplicate positions

Output: RankedSignal with final_score, acceptance decision, reasoning
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass
class RankedSignal:
    """Ranked signal with quality score and acceptance decision"""
    symbol: str
    strategy: str
    side: str
    entry: float
    stop: float
    target: float
    confidence: float
    final_score: float
    accepted: bool
    reject_reason: Optional[str]
    rank_reason: str
    confidence_bucket: str
    meta: Dict[str, Any]


def clamp(x: float, lo: float = 0.0, hi: float = 1.0) -> float:
    """Clamp value between lo and hi"""
    return max(lo, min(hi, x))


def bucketize(score: float) -> str:
    """Convert score to letter grade (A/B/C/D)"""
    if score >= 0.80:
        return "A"
    if score >= 0.65:
        return "B"
    if score >= 0.55:
        return "C"
    return "D"


def safe_float(v: Any, default: float = 0.0) -> float:
    """Safely convert value to float"""
    try:
        return float(v)
    except Exception:
        return default


def is_valid_signal_structure(signal: Dict[str, Any]) -> bool:
    """
    Check if signal has valid structure for trading
    
    Validates:
    - entry, stop, target are present and non-zero
    - stop_distance > 0 (stop != entry)
    
    Returns:
        True if signal structure is valid, False otherwise
    """
    entry = safe_float(signal.get("entry", 0.0))
    stop = safe_float(signal.get("stop", 0.0))
    target = safe_float(signal.get("target", 0.0))
    
    # All prices must be present and positive
    if entry <= 0 or stop <= 0 or target <= 0:
        return False
    
    # Stop distance must be > 0 (stop cannot equal entry)
    stop_distance = abs(entry - stop)
    if stop_distance <= 0:
        return False
    
    return True


def compute_alpha_score(signal: Dict[str, Any]) -> float:
    """
    Compute alpha quality from signal confidence and R:R ratio
    
    Formula: confidence * 0.7 + rr_score * 0.3
    RR normalized: rr/3.0 (3.0 R:R = perfect)
    """
    confidence = safe_float(signal.get("confidence", 0.0))
    
    entry = safe_float(signal.get("entry", 0.0))
    stop = safe_float(signal.get("stop", 0.0))
    target = safe_float(signal.get("target", 0.0))

    risk = abs(entry - stop)
    reward = abs(target - entry)

    rr = 0.0
    if risk > 0:
        rr = reward / risk

    rr_score = clamp(rr / 3.0)  # rr 3.0 => maxed
    return clamp(confidence * 0.7 + rr_score * 0.3)


def compute_historical_score(stats: Dict[str, Any]) -> float:
    """
    Compute strategy historical performance score
    
    Factors:
    - Win rate (40%)
    - Sharpe ratio (25%)
    - Drawdown penalty (20%)
    - Recent PnL (15%)
    """
    win_rate = clamp(safe_float(stats.get("win_rate", 0.5)))
    sharpe = safe_float(stats.get("sharpe", 0.0))
    dd = abs(safe_float(stats.get("drawdown", 0.0)))
    recent_pnl = safe_float(stats.get("recent_pnl", 0.0))

    sharpe_score = clamp((sharpe + 1.0) / 3.0)     # sharpe 2 => ~1.0
    dd_penalty = clamp(1.0 - dd / 0.20)            # 20% dd => 0
    pnl_score = clamp((recent_pnl + 0.05) / 0.10)  # -5%..+5% range

    return clamp(
        win_rate * 0.40
        + sharpe_score * 0.25
        + dd_penalty * 0.20
        + pnl_score * 0.15
    )


def compute_regime_fit(signal: Dict[str, Any], regime: str) -> float:
    """
    Compute how well strategy fits current market regime
    
    Regime mappings:
    - trend: trend/breakout strategies score high
    - chop: meanrev strategies score high
    - high_vol: breakout strategies moderate
    """
    strategy = (signal.get("strategy") or "").lower()

    if regime == "trend":
        if "trend" in strategy or "breakout" in strategy:
            return 0.9
        if "meanrev" in strategy:
            return 0.45

    if regime == "chop":
        if "meanrev" in strategy:
            return 0.85
        if "trend" in strategy:
            return 0.5
        if "breakout" in strategy:
            return 0.6

    if regime == "high_vol":
        if "breakout" in strategy:
            return 0.7
        return 0.45

    return 0.6  # neutral


def compute_execution_fit(execution: Dict[str, Any]) -> float:
    """
    Compute execution quality expectation
    
    Factors:
    - Expected slippage (65%)
    - Expected latency (35%)
    """
    slip = safe_float(execution.get("expected_slippage_bps", 5.0))
    latency = safe_float(execution.get("expected_latency_ms", 120.0))

    slip_score = clamp(1.0 - slip / 25.0)       # 25 bps => 0
    latency_score = clamp(1.0 - latency / 800.0)  # 800ms => 0

    return clamp(slip_score * 0.65 + latency_score * 0.35)


def compute_portfolio_fit(
    signal: Dict[str, Any],
    portfolio: Dict[str, Any],
    open_positions: List[Dict[str, Any]],
) -> float:
    """
    Compute fit with current portfolio state
    
    Factors:
    - Risk heat (higher heat = lower score)
    - Duplicate position penalty (already have position on same symbol)
    """
    symbol = signal.get("symbol")
    same_symbol_open = any(
        (p.get("symbol") == symbol and p.get("status", "OPEN") == "OPEN") 
        for p in open_positions
    )

    risk_heat = safe_float(portfolio.get("risk_heat", 0.0))
    heat_score = clamp(1.0 - risk_heat / 0.70)  # 70% heat => 0

    duplicate_penalty = 0.35 if same_symbol_open else 1.0

    return clamp(heat_score * duplicate_penalty)


def rank_one_signal(
    signal: Dict[str, Any],
    strategy_stats: Dict[str, Any],
    regime: str,
    execution: Dict[str, Any],
    portfolio: Dict[str, Any],
    open_positions: List[Dict[str, Any]],
    min_score: float = 0.45,
) -> RankedSignal:
    """
    Rank a single signal with 5-factor scoring
    
    Returns: RankedSignal with final_score and acceptance decision
    """
    alpha = compute_alpha_score(signal)
    historical = compute_historical_score(strategy_stats or {})
    regime_fit = compute_regime_fit(signal, regime)
    execution_fit = compute_execution_fit(execution or {})
    portfolio_fit = compute_portfolio_fit(signal, portfolio or {}, open_positions or [])

    final_score = clamp(
        alpha * 0.35
        + historical * 0.25
        + regime_fit * 0.15
        + execution_fit * 0.15
        + portfolio_fit * 0.10
    )

    accepted = final_score >= min_score
    reject_reason = None if accepted else f"rank_score_below_threshold_{final_score:.2f}"

    rank_reason = (
        f"alpha={alpha:.2f}, hist={historical:.2f}, regime={regime_fit:.2f}, "
        f"exec={execution_fit:.2f}, portfolio={portfolio_fit:.2f}"
    )

    return RankedSignal(
        symbol=str(signal.get("symbol")),
        strategy=str(signal.get("strategy")),
        side=str(signal.get("side")),
        entry=safe_float(signal.get("entry")),
        stop=safe_float(signal.get("stop")),
        target=safe_float(signal.get("target")),
        confidence=safe_float(signal.get("confidence")),
        final_score=final_score,
        accepted=accepted,
        reject_reason=reject_reason,
        rank_reason=rank_reason,
        confidence_bucket=bucketize(final_score),
        meta={
            "alpha_score": alpha,
            "historical_score": historical,
            "regime_fit": regime_fit,
            "execution_fit": execution_fit,
            "portfolio_fit": portfolio_fit,
            "regime": regime,
            # PHASE 3.2: Include features for filtering
            "cluster": signal.get("cluster", "unknown"),
            "timeframe": signal.get("timeframe", "unknown"),
            "alignment": signal.get("alignment", "unknown"),
        },
    )


def rank_signals(
    signals: List[Dict[str, Any]],
    stats_map: Dict[str, Dict[str, Any]],
    execution_map: Dict[str, Dict[str, Any]],
    regime: str,
    portfolio: Dict[str, Any],
    open_positions: List[Dict[str, Any]],
    min_score: float = 0.45,
) -> List[RankedSignal]:
    """
    Rank all signals and sort by final_score descending
    
    With fallback: if no signals pass min_score threshold,
    automatically accept top-2 ranked signals (if valid structure)
    
    Returns: List of RankedSignal sorted by quality (best first)
    """
    ranked: List[RankedSignal] = []

    for signal in signals:
        strategy = str(signal.get("strategy"))
        symbol = str(signal.get("symbol"))

        ranked_signal = rank_one_signal(
            signal=signal,
            strategy_stats=stats_map.get(strategy, {}),
            regime=regime,
            execution=execution_map.get(symbol, {}),
            portfolio=portfolio,
            open_positions=open_positions,
            min_score=min_score,
        )
        ranked.append(ranked_signal)

    # Sort by final_score descending (best signals first)
    ranked.sort(key=lambda x: x.final_score, reverse=True)
    
    # ═══════════════════════════════════════════════════════════════
    # PHASE 3.2: CONTROLLED FILTERING (Discovery Debugging)
    # ═══════════════════════════════════════════════════════════════
    # Apply data-driven filters based on feature performance analysis
    # Source: /api/debug/features-from-shadow
    
    for r in ranked:
        # Extract features from meta
        features = r.meta if hasattr(r, 'meta') else {}
        cluster = features.get("cluster", "unknown")
        alignment = features.get("alignment", "unknown")
        timeframe = features.get("timeframe", "unknown")
        
        # === HARD FILTER: Reject alts (33% winrate, negative PnL) ===
        if cluster == "alts":
            r.accepted = False
            r.reject_reason = "phase32_filter_alts"
            r.rank_reason += " | PHASE32_REJECT_ALTS"
            continue
        
        # === CONDITIONAL FILTER: Reject weak 1h signals ===
        # Keep strong 1h signals (score >= 0.7), reject weak ones
        if timeframe == "1h" and r.final_score < 0.7:
            r.accepted = False
            r.reject_reason = "phase32_filter_1h_low_score"
            r.rank_reason += " | PHASE32_REJECT_1H_WEAK"
            continue
        
        # === BOOST: Amplify 4h signals (56% winrate, best performer) ===
        if timeframe == "4h":
            original_score = r.final_score
            r.final_score *= 1.15
            r.final_score = min(r.final_score, 1.0)  # Cap at 1.0
            r.rank_reason += f" | PHASE32_BOOST_4H({original_score:.2f}→{r.final_score:.2f})"
        
        # === PENALTY: Reduce divergent alignment signals ===
        if alignment == "divergent":
            original_score = r.final_score
            r.final_score *= 0.85
            r.rank_reason += f" | PHASE32_PENALTY_DIVERGENT({original_score:.2f}→{r.final_score:.2f})"
    
    # Re-sort after score adjustments (boosts/penalties)
    ranked.sort(key=lambda x: x.final_score, reverse=True)
    
    # FALLBACK LOGIC: If no signals accepted after filtering, force top-2 valid signals
    accepted_signals = [r for r in ranked if r.accepted]
    
    if len(accepted_signals) == 0 and len(ranked) > 0:
        # No signals passed threshold - apply fallback
        # Select top-2 ranked signals with valid structure
        fallback_candidates = []
        
        for r in ranked:
            # Check if signal has valid structure
            signal_dict = {
                "entry": r.entry,
                "stop": r.stop,
                "target": r.target,
                "symbol": r.symbol,
            }
            
            if is_valid_signal_structure(signal_dict):
                fallback_candidates.append(r)
            
            # Take max 2 signals
            if len(fallback_candidates) >= 2:
                break
        
        # Force accept fallback candidates
        for r in fallback_candidates:
            r.accepted = True
            r.reject_reason = None
            r.rank_reason += " | FALLBACK_ACCEPT"
        
        # Log fallback activation
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(
            f"[Ranking] Fallback activated: {len(fallback_candidates)} signals force-accepted "
            f"(top-2 valid from {len(ranked)} total)"
        )
    
    return ranked
