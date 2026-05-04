"""
Portfolio Manager Engine

PHASE 38 — Portfolio Manager (Markowitz Model)

Core engine for multi-asset portfolio management.

Key improvements over naive implementation:
1. Portfolio variance: wᵀΣw (not Σ position_risk)
2. Correlation matrix (not pairwise)
3. Target-based rebalancing (3% threshold)
4. Proper risk contribution calculation

Pipeline:
hypothesis → portfolio targets → portfolio manager → execution brain
"""

import hashlib
from typing import Optional, Dict, List, Tuple
from datetime import datetime, timezone
from collections import defaultdict
import math

from .portfolio_types import (
    PortfolioState,
    PortfolioPosition,
    PortfolioTarget,
    PortfolioRisk,
    ExposureState,
    CorrelationMatrix,
    RebalanceResult,
    PositionRequest,
    CapitalRotationRequest,
    PortfolioHistoryEntry,
    EXPOSURE_LIMITS,
    RISK_THRESHOLDS,
    MAX_SINGLE_POSITION,
    CORRELATION_PENALTY_THRESHOLD,
    MAX_CORRELATION_PENALTY,
    REBALANCE_THRESHOLD,
)


# ══════════════════════════════════════════════════════════════
# Portfolio Manager Engine
# ══════════════════════════════════════════════════════════════

class PortfolioManagerEngine:
    """
    Portfolio Manager Engine — PHASE 38 (Markowitz)
    
    Manages multi-asset portfolio with proper risk model:
    - Portfolio variance = wᵀΣw
    - Correlation penalty = position_weight × (1 - avg_correlation)
    - Rebalance trigger: |current - target| > 3%
    """
    
    def __init__(self, initial_capital: float = 1000000.0):
        self._capital = initial_capital
        self._positions: Dict[str, PortfolioPosition] = {}
        self._targets: Dict[str, PortfolioTarget] = {}
        self._state_history: List[PortfolioHistoryEntry] = []
        self._correlation_cache: Optional[CorrelationMatrix] = None
        self._returns_cache: Dict[str, List[float]] = {}
    
    # ═══════════════════════════════════════════════════════════
    # 1. Target Management (NEW)
    # ═══════════════════════════════════════════════════════════
    
    def set_targets(self, targets: List[PortfolioTarget]) -> Dict[str, any]:
        """
        Set target allocations from hypothesis.
        
        Pipeline: hypothesis → portfolio targets → portfolio manager
        """
        self._targets.clear()
        
        total_weight = 0.0
        adjusted_targets = []
        
        for target in targets:
            symbol = target.symbol.upper()
            
            # Cap at max single position
            capped_weight = min(target.target_weight, MAX_SINGLE_POSITION)
            
            adjusted_target = PortfolioTarget(
                symbol=symbol,
                target_weight=capped_weight,
                direction=target.direction,
                confidence=target.confidence,
                source_hypothesis_id=target.source_hypothesis_id,
                priority=target.priority,
            )
            
            self._targets[symbol] = adjusted_target
            adjusted_targets.append(adjusted_target)
            total_weight += capped_weight
        
        # Check exposure limits
        long_weight = sum(t.target_weight for t in adjusted_targets if t.direction == "LONG")
        short_weight = sum(t.target_weight for t in adjusted_targets if t.direction == "SHORT")
        
        warnings = []
        if long_weight > EXPOSURE_LIMITS["MAX_LONG"]:
            warnings.append(f"Long targets ({long_weight:.1%}) exceed limit ({EXPOSURE_LIMITS['MAX_LONG']:.0%})")
        if short_weight > EXPOSURE_LIMITS["MAX_SHORT"]:
            warnings.append(f"Short targets ({short_weight:.1%}) exceed limit ({EXPOSURE_LIMITS['MAX_SHORT']:.0%})")
        
        return {
            "targets_set": len(adjusted_targets),
            "total_target_weight": round(total_weight, 4),
            "long_target_weight": round(long_weight, 4),
            "short_target_weight": round(short_weight, 4),
            "warnings": warnings,
        }
    
    def get_targets(self) -> List[PortfolioTarget]:
        """Get current target allocations."""
        return list(self._targets.values())
    
    def get_target(self, symbol: str) -> Optional[PortfolioTarget]:
        """Get target for specific symbol."""
        return self._targets.get(symbol.upper())
    
    # ═══════════════════════════════════════════════════════════
    # 2. Position Management
    # ═══════════════════════════════════════════════════════════
    
    def add_position(self, request: PositionRequest) -> Tuple[bool, str, Optional[PortfolioPosition]]:
        """
        Add a new position to portfolio.
        
        Validates:
        - Position limit (max 10%)
        - Exposure limit (max 70% long/short)
        - Correlation penalty (matrix-based)
        
        Returns: (success, message, position)
        """
        symbol = request.symbol.upper()
        
        # 1. Check if position already exists
        if symbol in self._positions:
            return False, f"Position for {symbol} already exists", None
        
        # 2. Validate position size limit
        position_percent = request.size_usd / self._capital
        if position_percent > MAX_SINGLE_POSITION:
            max_size = self._capital * MAX_SINGLE_POSITION
            return False, f"Position exceeds {MAX_SINGLE_POSITION*100}% limit. Max: ${max_size:,.0f}", None
        
        # 3. Check exposure limits
        current_exposure = self.calculate_exposure()
        
        if request.direction == "LONG":
            new_exposure = current_exposure.long_exposure + position_percent
            if new_exposure > EXPOSURE_LIMITS["MAX_LONG"]:
                available = EXPOSURE_LIMITS["MAX_LONG"] - current_exposure.long_exposure
                return False, f"Long exposure would exceed limit. Available: {available*100:.1f}%", None
        else:
            new_exposure = current_exposure.short_exposure + position_percent
            if new_exposure > EXPOSURE_LIMITS["MAX_SHORT"]:
                available = EXPOSURE_LIMITS["MAX_SHORT"] - current_exposure.short_exposure
                return False, f"Short exposure would exceed limit. Available: {available*100:.1f}%", None
        
        # 4. Calculate correlation penalty (matrix-based)
        correlation_penalty, correlated_with = self._calculate_correlation_penalty_matrix(symbol, request.direction)
        
        # 5. Apply correlation penalty to size
        adjusted_size = request.size_usd * (1 - correlation_penalty)
        
        # 6. Calculate max loss
        if request.direction == "LONG":
            max_loss_pct = (request.entry_price - request.stop_loss) / request.entry_price
        else:
            max_loss_pct = (request.stop_loss - request.entry_price) / request.entry_price
        max_loss_usd = adjusted_size * max_loss_pct
        
        # 7. Risk contribution will be recalculated with full portfolio
        risk_contribution = max_loss_usd / self._capital
        
        # 8. Create position
        position = PortfolioPosition(
            symbol=symbol,
            direction=request.direction,
            size_usd=adjusted_size,
            size_percent=adjusted_size / self._capital,
            entry_price=request.entry_price,
            current_price=request.entry_price,
            stop_loss=request.stop_loss,
            take_profit=request.take_profit,
            risk_contribution=round(risk_contribution, 4),
            max_loss_usd=round(max_loss_usd, 2),
            correlation_penalty=correlation_penalty,
            correlated_with=correlated_with,
        )
        
        self._positions[symbol] = position
        
        # Invalidate correlation cache
        self._correlation_cache = None
        
        # Recalculate risk contributions for all positions
        self._recalculate_risk_contributions()
        
        message = f"Position added: {symbol} {request.direction} ${adjusted_size:,.0f}"
        if correlation_penalty > 0:
            message += f" (reduced by {correlation_penalty*100:.0f}% due to correlation)"
        
        return True, message, position
    
    def close_position(self, symbol: str) -> Tuple[bool, str]:
        """Close a position."""
        symbol = symbol.upper()
        
        if symbol not in self._positions:
            return False, f"No position found for {symbol}"
        
        position = self._positions.pop(symbol)
        
        # Invalidate correlation cache
        self._correlation_cache = None
        
        # Recalculate risk contributions
        if self._positions:
            self._recalculate_risk_contributions()
        
        return True, f"Closed {symbol} {position.direction} position"
    
    def update_position_price(self, symbol: str, current_price: float) -> bool:
        """Update current price and P&L for a position."""
        symbol = symbol.upper()
        
        if symbol not in self._positions:
            return False
        
        position = self._positions[symbol]
        position.current_price = current_price
        
        # Calculate unrealized P&L
        if position.direction == "LONG":
            pnl_pct = (current_price - position.entry_price) / position.entry_price
        else:
            pnl_pct = (position.entry_price - current_price) / position.entry_price
        
        position.unrealized_pnl_percent = round(pnl_pct, 4)
        position.unrealized_pnl_usd = round(position.size_usd * pnl_pct, 2)
        
        return True
    
    def _recalculate_risk_contributions(self):
        """
        Recalculate risk contributions using Markowitz decomposition.
        
        Risk contribution of asset i = w_i * (Σw)_i / σ_p
        """
        if not self._positions:
            return
        
        # Get correlation/covariance matrix
        corr_matrix = self.get_correlation_matrix()
        
        symbols = list(self._positions.keys())
        n = len(symbols)
        
        if n == 1:
            # Single position - 100% risk contribution
            symbol = symbols[0]
            self._positions[symbol].risk_contribution = self._positions[symbol].max_loss_usd / self._capital
            return
        
        # Get weights and covariance matrix
        weights = []
        for sym in symbols:
            weights.append(self._positions[sym].size_percent)
        
        # Calculate portfolio variance
        portfolio_var = self._calculate_portfolio_variance(symbols, weights, corr_matrix)
        portfolio_vol = math.sqrt(portfolio_var) if portfolio_var > 0 else 0.0001
        
        # Calculate marginal risk contribution for each asset
        for i, sym in enumerate(symbols):
            w_i = weights[i]
            
            # Marginal contribution = w_i * Σ(w_j * cov_ij) / portfolio_vol
            marginal = 0.0
            for j, sym_j in enumerate(symbols):
                w_j = weights[j]
                cov_ij = corr_matrix.covariance_matrix.get(sym, {}).get(sym_j, 0.0)
                marginal += w_j * cov_ij
            
            marginal *= w_i
            if portfolio_vol > 0:
                risk_contrib = marginal / portfolio_vol
            else:
                risk_contrib = w_i  # Fallback to weight
            
            # Normalize and store
            self._positions[sym].risk_contribution = round(max(min(risk_contrib, 1.0), 0.0), 4)
    
    # ═══════════════════════════════════════════════════════════
    # 3. Exposure Calculation
    # ═══════════════════════════════════════════════════════════
    
    def calculate_exposure(self) -> ExposureState:
        """Calculate current portfolio exposure."""
        long_exposure = 0.0
        short_exposure = 0.0
        exposure_by_symbol = {}
        
        for symbol, position in self._positions.items():
            position_pct = position.size_usd / self._capital
            exposure_by_symbol[symbol] = position_pct
            
            if position.direction == "LONG":
                long_exposure += position_pct
            else:
                short_exposure += position_pct
        
        net_exposure = long_exposure - short_exposure
        gross_exposure = long_exposure + short_exposure
        
        return ExposureState(
            long_exposure=round(long_exposure, 4),
            short_exposure=round(short_exposure, 4),
            net_exposure=round(net_exposure, 4),
            gross_exposure=round(gross_exposure, 4),
            exposure_by_symbol=exposure_by_symbol,
            long_within_limit=long_exposure <= EXPOSURE_LIMITS["MAX_LONG"],
            short_within_limit=short_exposure <= EXPOSURE_LIMITS["MAX_SHORT"],
            total_within_limit=gross_exposure <= EXPOSURE_LIMITS["MAX_TOTAL"],
            available_long_capacity=round(max(EXPOSURE_LIMITS["MAX_LONG"] - long_exposure, 0), 4),
            available_short_capacity=round(max(EXPOSURE_LIMITS["MAX_SHORT"] - short_exposure, 0), 4),
        )
    
    # ═══════════════════════════════════════════════════════════
    # 4. Risk Calculation (Markowitz wᵀΣw)
    # ═══════════════════════════════════════════════════════════
    
    def calculate_risk(self) -> PortfolioRisk:
        """
        Calculate portfolio risk using Markowitz model.
        
        portfolio_variance = wᵀΣw
        portfolio_volatility = √variance
        """
        if not self._positions:
            return PortfolioRisk()
        
        symbols = list(self._positions.keys())
        weights = [self._positions[sym].size_percent for sym in symbols]
        
        # Get correlation/covariance matrix
        corr_matrix = self.get_correlation_matrix()
        
        # Calculate portfolio variance: wᵀΣw
        portfolio_variance = self._calculate_portfolio_variance(symbols, weights, corr_matrix)
        portfolio_volatility = math.sqrt(portfolio_variance) if portfolio_variance > 0 else 0.0
        
        # Risk by symbol
        risk_by_symbol = {}
        risk_contrib_by_symbol = {}
        max_drawdown_usd = 0.0
        
        for symbol, position in self._positions.items():
            risk_by_symbol[symbol] = position.max_loss_usd / self._capital
            risk_contrib_by_symbol[symbol] = position.risk_contribution
            max_drawdown_usd += position.max_loss_usd
        
        # Normalize portfolio risk (volatility as % of capital)
        # Assuming daily volatility, annualize and normalize
        annualized_vol = portfolio_volatility * math.sqrt(252)
        normalized_risk = min(annualized_vol, 1.0)
        
        # Classify risk level based on normalized risk
        if normalized_risk < RISK_THRESHOLDS["LOW"]:
            risk_level = "LOW"
        elif normalized_risk < RISK_THRESHOLDS["MEDIUM"]:
            risk_level = "MEDIUM"
        elif normalized_risk < RISK_THRESHOLDS["HIGH"]:
            risk_level = "HIGH"
        else:
            risk_level = "CRITICAL"
        
        # Concentration risk (Herfindahl index)
        concentration_risk = self._calculate_concentration_risk()
        
        # Correlation risk
        correlation_risk = corr_matrix.avg_correlation
        
        # VaR estimates (assuming normal distribution)
        var_95 = portfolio_volatility * 1.645  # 95% confidence
        var_99 = portfolio_volatility * 2.326  # 99% confidence
        
        return PortfolioRisk(
            portfolio_variance=round(portfolio_variance, 8),
            portfolio_volatility=round(portfolio_volatility, 6),
            portfolio_risk=round(normalized_risk, 4),
            risk_level=risk_level,
            risk_by_symbol=risk_by_symbol,
            risk_contribution_by_symbol=risk_contrib_by_symbol,
            max_drawdown_usd=round(max_drawdown_usd, 2),
            max_drawdown_percent=round(max_drawdown_usd / self._capital, 4) if self._capital > 0 else 0,
            concentration_risk=round(concentration_risk, 4),
            correlation_risk=round(correlation_risk, 4),
            var_95_percent=round(var_95, 6),
            var_99_percent=round(var_99, 6),
        )
    
    def _calculate_portfolio_variance(
        self,
        symbols: List[str],
        weights: List[float],
        corr_matrix: CorrelationMatrix,
    ) -> float:
        """
        Calculate portfolio variance: wᵀΣw
        
        variance = Σᵢ Σⱼ wᵢ wⱼ σᵢⱼ
        """
        if not symbols or not weights:
            return 0.0
        
        n = len(symbols)
        variance = 0.0
        
        for i in range(n):
            for j in range(n):
                w_i = weights[i]
                w_j = weights[j]
                
                # Get covariance from matrix
                sym_i = symbols[i]
                sym_j = symbols[j]
                
                cov_ij = corr_matrix.covariance_matrix.get(sym_i, {}).get(sym_j, 0.0)
                
                # Fallback if covariance not available
                if cov_ij == 0.0 and i != j:
                    corr_ij = corr_matrix.matrix.get(sym_i, {}).get(sym_j, 0.5)
                    vol_i = corr_matrix.volatilities.get(sym_i, 0.02)
                    vol_j = corr_matrix.volatilities.get(sym_j, 0.02)
                    cov_ij = corr_ij * vol_i * vol_j
                elif cov_ij == 0.0 and i == j:
                    vol_i = corr_matrix.volatilities.get(sym_i, 0.02)
                    cov_ij = vol_i ** 2
                
                variance += w_i * w_j * cov_ij
        
        return max(variance, 0.0)
    
    def _calculate_concentration_risk(self) -> float:
        """Calculate portfolio concentration risk (Herfindahl index)."""
        if not self._positions:
            return 0.0
        
        total = sum(p.size_usd for p in self._positions.values())
        if total == 0:
            return 0.0
        
        hhi = sum((p.size_usd / total) ** 2 for p in self._positions.values())
        
        n = len(self._positions)
        if n <= 1:
            return 1.0
        
        min_hhi = 1 / n
        normalized = (hhi - min_hhi) / (1 - min_hhi) if (1 - min_hhi) > 0 else 0
        
        return min(max(normalized, 0.0), 1.0)
    
    # ═══════════════════════════════════════════════════════════
    # 5. Correlation Matrix (Full Matrix)
    # ═══════════════════════════════════════════════════════════
    
    def get_correlation_matrix(self) -> CorrelationMatrix:
        """
        Get or calculate full correlation matrix.
        
        Also calculates covariance matrix for Markowitz.
        """
        if self._correlation_cache:
            return self._correlation_cache
        
        symbols = list(self._positions.keys())
        if len(symbols) < 1:
            return CorrelationMatrix(symbols=symbols)
        
        # Get returns for all symbols
        returns_data = {}
        for sym in symbols:
            returns_data[sym] = self._get_asset_returns(sym)
        
        # Calculate volatilities (std dev of returns)
        volatilities = {}
        for sym, returns in returns_data.items():
            if len(returns) >= 2:
                mean_ret = sum(returns) / len(returns)
                variance = sum((r - mean_ret) ** 2 for r in returns) / len(returns)
                volatilities[sym] = math.sqrt(variance)
            else:
                volatilities[sym] = 0.02  # Default 2% daily volatility
        
        # Calculate correlation matrix
        matrix = {}
        covariance_matrix = {}
        high_pairs = []
        total_corr = 0.0
        pair_count = 0
        
        for i, sym1 in enumerate(symbols):
            matrix[sym1] = {}
            covariance_matrix[sym1] = {}
            
            for j, sym2 in enumerate(symbols):
                if i == j:
                    # Diagonal - correlation with self = 1
                    matrix[sym1][sym2] = 1.0
                    covariance_matrix[sym1][sym2] = volatilities[sym1] ** 2  # Variance
                elif j < i:
                    # Already calculated - symmetric
                    matrix[sym1][sym2] = matrix[sym2][sym1]
                    covariance_matrix[sym1][sym2] = covariance_matrix[sym2][sym1]
                else:
                    # Calculate correlation
                    corr = self._calculate_correlation(
                        returns_data.get(sym1, []),
                        returns_data.get(sym2, [])
                    )
                    matrix[sym1][sym2] = corr
                    
                    # Calculate covariance: cov = corr * vol1 * vol2
                    cov = corr * volatilities[sym1] * volatilities[sym2]
                    covariance_matrix[sym1][sym2] = cov
                    
                    # Track high correlation pairs
                    if abs(corr) >= CORRELATION_PENALTY_THRESHOLD:
                        high_pairs.append((sym1, sym2, corr))
                    
                    total_corr += abs(corr)
                    pair_count += 1
        
        avg_corr = total_corr / pair_count if pair_count > 0 else 0.0
        
        self._correlation_cache = CorrelationMatrix(
            symbols=symbols,
            matrix=matrix,
            covariance_matrix=covariance_matrix,
            volatilities=volatilities,
            high_correlation_pairs=high_pairs,
            avg_correlation=round(avg_corr, 4),
        )
        
        return self._correlation_cache
    
    def _get_asset_returns(self, symbol: str) -> List[float]:
        """Get historical returns for an asset."""
        # Check cache first
        if symbol in self._returns_cache:
            return self._returns_cache[symbol]
        
        # Try from database
        try:
            from core.database import get_database
            db = get_database()
            if db:
                candles = list(db.candles.find(
                    {"symbol": symbol},
                    {"_id": 0, "close": 1}
                ).sort("timestamp", -1).limit(60))
                
                if len(candles) >= 2:
                    returns = []
                    for i in range(len(candles) - 1):
                        ret = (candles[i]["close"] - candles[i + 1]["close"]) / candles[i + 1]["close"]
                        returns.append(ret)
                    
                    self._returns_cache[symbol] = returns
                    return returns
        except Exception:
            pass
        
        # Generate synthetic returns based on symbol
        seed = int(hashlib.md5(symbol.encode()).hexdigest()[:8], 16)
        import random
        random.seed(seed)
        
        base_vol = 0.02  # 2% base daily volatility
        returns = [random.gauss(0, base_vol) for _ in range(30)]
        
        self._returns_cache[symbol] = returns
        return returns
    
    def _calculate_correlation(self, returns1: List[float], returns2: List[float]) -> float:
        """Calculate Pearson correlation between two return series."""
        if len(returns1) < 5 or len(returns2) < 5:
            return 0.5  # Default moderate correlation
        
        n = min(len(returns1), len(returns2))
        r1 = returns1[:n]
        r2 = returns2[:n]
        
        mean1 = sum(r1) / n
        mean2 = sum(r2) / n
        
        cov = sum((r1[i] - mean1) * (r2[i] - mean2) for i in range(n)) / n
        
        var1 = sum((x - mean1) ** 2 for x in r1) / n
        var2 = sum((x - mean2) ** 2 for x in r2) / n
        
        std1 = math.sqrt(var1) if var1 > 0 else 0.0001
        std2 = math.sqrt(var2) if var2 > 0 else 0.0001
        
        corr = cov / (std1 * std2)
        return round(max(min(corr, 1.0), -1.0), 4)
    
    def _calculate_correlation_penalty_matrix(
        self,
        new_symbol: str,
        direction: str,
    ) -> Tuple[float, List[str]]:
        """
        Calculate correlation penalty using matrix approach.
        
        penalty = avg_correlation_with_same_direction_positions × position_weight_factor
        """
        if not self._positions:
            return 0.0, []
        
        same_direction_symbols = [
            sym for sym, pos in self._positions.items()
            if pos.direction == direction
        ]
        
        if not same_direction_symbols:
            return 0.0, []
        
        # Get returns for new symbol
        new_returns = self._get_asset_returns(new_symbol)
        
        # Calculate average correlation with same-direction positions
        total_corr = 0.0
        high_corr_symbols = []
        
        for sym in same_direction_symbols:
            existing_returns = self._get_asset_returns(sym)
            corr = self._calculate_correlation(new_returns, existing_returns)
            
            if corr >= CORRELATION_PENALTY_THRESHOLD:
                high_corr_symbols.append(sym)
            
            total_corr += abs(corr)
        
        avg_corr = total_corr / len(same_direction_symbols)
        
        # Calculate penalty based on average correlation
        if avg_corr >= CORRELATION_PENALTY_THRESHOLD:
            excess = avg_corr - CORRELATION_PENALTY_THRESHOLD
            penalty = excess * (MAX_CORRELATION_PENALTY / (1 - CORRELATION_PENALTY_THRESHOLD))
            penalty = min(penalty, MAX_CORRELATION_PENALTY)
        else:
            penalty = 0.0
        
        return round(penalty, 4), high_corr_symbols
    
    # ═══════════════════════════════════════════════════════════
    # 6. Rebalancing (Target-based, 3% threshold)
    # ═══════════════════════════════════════════════════════════
    
    def check_rebalance_needed(self) -> Tuple[bool, Dict[str, float], float]:
        """
        Check if rebalance is needed.
        
        Trigger: |current_weight - target_weight| > 3%
        
        Returns: (needs_rebalance, weight_deviations, max_deviation)
        """
        if not self._targets:
            return False, {}, 0.0
        
        weight_deviations = {}
        max_deviation = 0.0
        
        # Check each target
        for symbol, target in self._targets.items():
            current_position = self._positions.get(symbol)
            current_weight = current_position.size_percent if current_position else 0.0
            
            deviation = abs(current_weight - target.target_weight)
            weight_deviations[symbol] = round(deviation, 4)
            
            if deviation > max_deviation:
                max_deviation = deviation
        
        # Check positions without targets (should be closed)
        for symbol in self._positions:
            if symbol not in self._targets:
                current_weight = self._positions[symbol].size_percent
                weight_deviations[symbol] = round(current_weight, 4)
                if current_weight > max_deviation:
                    max_deviation = current_weight
        
        needs_rebalance = max_deviation > REBALANCE_THRESHOLD
        
        return needs_rebalance, weight_deviations, round(max_deviation, 4)
    
    def rebalance(self) -> RebalanceResult:
        """
        Rebalance portfolio to match targets.
        
        Triggers when:
        - |current_weight - target_weight| > 3%
        - Exposure limits exceeded
        - Risk level CRITICAL
        """
        result = RebalanceResult()
        
        # Get current state
        risk_before = self.calculate_risk()
        result.risk_before = risk_before.portfolio_risk
        result.variance_before = risk_before.portfolio_variance
        
        # Check weight deviations
        needs_rebalance, weight_deviations, max_deviation = self.check_rebalance_needed()
        result.weight_deviations = weight_deviations
        result.max_deviation = max_deviation
        
        if needs_rebalance:
            result.rebalance_triggered = True
            result.reason = f"Weight deviation ({max_deviation:.1%}) exceeds threshold ({REBALANCE_THRESHOLD:.0%})"
        
        # Check exposure limits
        exposure = self.calculate_exposure()
        
        if not exposure.long_within_limit:
            result.rebalance_triggered = True
            result.reason = f"Long exposure ({exposure.long_exposure:.1%}) exceeds limit"
            
            # Find long positions to reduce
            excess = exposure.long_exposure - EXPOSURE_LIMITS["MAX_LONG"]
            long_positions = sorted(
                [(s, p) for s, p in self._positions.items() if p.direction == "LONG"],
                key=lambda x: x[1].size_percent,
                reverse=True
            )
            
            for symbol, position in long_positions:
                if excess <= 0:
                    break
                
                reduce_pct = min(position.size_percent, excess)
                result.positions_to_reduce.append({
                    "symbol": symbol,
                    "current_weight": position.size_percent,
                    "reduce_by_percent": round(reduce_pct, 4),
                    "reduce_by_usd": round(reduce_pct * self._capital, 2),
                })
                excess -= reduce_pct
        
        if not exposure.short_within_limit:
            result.rebalance_triggered = True
            if not result.reason:
                result.reason = f"Short exposure ({exposure.short_exposure:.1%}) exceeds limit"
            
            excess = exposure.short_exposure - EXPOSURE_LIMITS["MAX_SHORT"]
            short_positions = sorted(
                [(s, p) for s, p in self._positions.items() if p.direction == "SHORT"],
                key=lambda x: x[1].size_percent,
                reverse=True
            )
            
            for symbol, position in short_positions:
                if excess <= 0:
                    break
                
                reduce_pct = min(position.size_percent, excess)
                result.positions_to_reduce.append({
                    "symbol": symbol,
                    "current_weight": position.size_percent,
                    "reduce_by_percent": round(reduce_pct, 4),
                    "reduce_by_usd": round(reduce_pct * self._capital, 2),
                })
                excess -= reduce_pct
        
        # Check risk level
        if risk_before.risk_level == "CRITICAL":
            result.rebalance_triggered = True
            if not result.reason:
                result.reason = "Portfolio risk is CRITICAL"
            
            # Close riskiest positions until risk is acceptable
            risky_positions = sorted(
                self._positions.items(),
                key=lambda x: x[1].risk_contribution,
                reverse=True
            )
            
            cumulative_risk = risk_before.portfolio_risk
            for symbol, position in risky_positions:
                if cumulative_risk <= RISK_THRESHOLDS["MEDIUM"]:
                    break
                
                result.positions_to_close.append(symbol)
                result.capital_freed += position.size_usd
                cumulative_risk -= position.risk_contribution
        
        # Calculate adjustments based on targets
        if result.rebalance_triggered and self._targets:
            for symbol, target in self._targets.items():
                current = self._positions.get(symbol)
                current_weight = current.size_percent if current else 0.0
                
                deviation = target.target_weight - current_weight
                
                if deviation > REBALANCE_THRESHOLD:
                    # Need to increase position
                    result.positions_to_increase.append({
                        "symbol": symbol,
                        "direction": target.direction,
                        "current_weight": round(current_weight, 4),
                        "target_weight": round(target.target_weight, 4),
                        "increase_by_percent": round(deviation, 4),
                        "increase_by_usd": round(deviation * self._capital, 2),
                    })
                    result.capital_required += deviation * self._capital
                    
                    if not current:
                        result.positions_to_open.append({
                            "symbol": symbol,
                            "direction": target.direction,
                            "target_weight": round(target.target_weight, 4),
                            "size_usd": round(target.target_weight * self._capital, 2),
                        })
                
                elif deviation < -REBALANCE_THRESHOLD:
                    # Need to reduce position
                    if symbol not in [p["symbol"] for p in result.positions_to_reduce]:
                        result.positions_to_reduce.append({
                            "symbol": symbol,
                            "current_weight": round(current_weight, 4),
                            "target_weight": round(target.target_weight, 4),
                            "reduce_by_percent": round(abs(deviation), 4),
                            "reduce_by_usd": round(abs(deviation) * self._capital, 2),
                        })
                        result.capital_freed += abs(deviation) * self._capital
            
            # Positions not in targets should be closed
            for symbol in list(self._positions.keys()):
                if symbol not in self._targets and symbol not in result.positions_to_close:
                    result.positions_to_close.append(symbol)
                    result.capital_freed += self._positions[symbol].size_usd
        
        # Calculate new allocations
        for target in self._targets.values():
            result.new_allocations[target.symbol] = round(target.target_weight, 4)
        
        # Estimate risk after rebalance
        result.risk_after = result.risk_before * 0.8 if result.rebalance_triggered else result.risk_before
        result.variance_after = result.variance_before * 0.8 if result.rebalance_triggered else result.variance_before
        
        result.capital_freed = round(result.capital_freed, 2)
        result.capital_required = round(result.capital_required, 2)
        
        return result
    
    # ═══════════════════════════════════════════════════════════
    # 7. Capital Rotation (Based on targets + correlation + risk)
    # ═══════════════════════════════════════════════════════════
    
    def rotate_capital(
        self,
        request: CapitalRotationRequest,
    ) -> Dict[str, any]:
        """
        Rotate capital to new targets.
        
        Considers:
        - Portfolio correlation
        - Risk contribution
        - Confidence scores
        """
        # Set new targets
        target_result = self.set_targets(request.targets)
        
        # Sort targets by priority and confidence
        sorted_targets = sorted(
            request.targets,
            key=lambda t: (t.priority, t.confidence),
            reverse=True
        )
        
        rotation_plan = []
        total_allocated = 0.0
        
        for target in sorted_targets:
            symbol = target.symbol.upper()
            base_weight = min(target.target_weight, MAX_SINGLE_POSITION)
            
            # Apply correlation penalty if enabled
            if request.consider_correlation and self._positions:
                penalty, _ = self._calculate_correlation_penalty_matrix(symbol, target.direction)
                adjusted_weight = base_weight * (1 - penalty)
            else:
                adjusted_weight = base_weight
                penalty = 0.0
            
            # Apply risk contribution factor if enabled
            if request.consider_risk_contribution:
                # Higher confidence = less risk adjustment
                risk_factor = 1.0 - (0.2 * (1 - target.confidence))
                adjusted_weight *= risk_factor
            else:
                risk_factor = 1.0
            
            # Check exposure limits
            if target.direction == "LONG":
                max_available = EXPOSURE_LIMITS["MAX_LONG"] - total_allocated
            else:
                max_available = EXPOSURE_LIMITS["MAX_SHORT"]
            
            final_weight = min(adjusted_weight, max_available, MAX_SINGLE_POSITION)
            
            rotation_plan.append({
                "symbol": symbol,
                "direction": target.direction,
                "base_weight": round(base_weight, 4),
                "correlation_penalty": round(penalty, 4),
                "risk_factor": round(risk_factor, 4),
                "final_weight": round(final_weight, 4),
                "final_amount_usd": round(final_weight * self._capital, 2),
                "confidence": round(target.confidence, 4),
                "priority": target.priority,
            })
            
            if target.direction == "LONG":
                total_allocated += final_weight
        
        return {
            "rotation_plan": rotation_plan,
            "total_long_allocation": round(total_allocated, 4),
            "targets_processed": len(rotation_plan),
            "warnings": target_result.get("warnings", []),
        }
    
    # ═══════════════════════════════════════════════════════════
    # 8. Diversification Score
    # ═══════════════════════════════════════════════════════════
    
    def calculate_diversification_score(self) -> float:
        """
        Calculate diversification score [0, 1].
        
        Components:
        - Concentration (Herfindahl)
        - Correlation
        - Direction balance
        """
        if len(self._positions) <= 1:
            return 0.0
        
        # Components
        concentration_risk = self._calculate_concentration_risk()
        
        corr_matrix = self.get_correlation_matrix()
        correlation_risk = corr_matrix.avg_correlation
        
        # Direction balance
        exposure = self.calculate_exposure()
        direction_balance = 1 - abs(exposure.net_exposure) / max(exposure.gross_exposure, 0.01)
        
        # Combine
        diversification = (
            0.40 * (1 - concentration_risk)
            + 0.35 * (1 - correlation_risk)
            + 0.25 * direction_balance
        )
        
        return round(max(min(diversification, 1.0), 0.0), 4)
    
    # ═══════════════════════════════════════════════════════════
    # 9. Get Portfolio State
    # ═══════════════════════════════════════════════════════════
    
    def get_state(self) -> PortfolioState:
        """Get complete portfolio state."""
        exposure = self.calculate_exposure()
        risk = self.calculate_risk()
        diversification = self.calculate_diversification_score()
        
        # Check rebalance needed
        needs_rebalance, weight_deviations, max_deviation = self.check_rebalance_needed()
        
        # Calculate P&L
        total_pnl_usd = sum(p.unrealized_pnl_usd for p in self._positions.values())
        total_pnl_pct = total_pnl_usd / self._capital if self._capital > 0 else 0
        
        # Allocated capital
        allocated = sum(p.size_usd for p in self._positions.values())
        
        # Warnings
        warnings = []
        if risk.risk_level in ("HIGH", "CRITICAL"):
            warnings.append(f"Portfolio risk is {risk.risk_level}")
        if not exposure.long_within_limit:
            warnings.append("Long exposure exceeds limit")
        if not exposure.short_within_limit:
            warnings.append("Short exposure exceeds limit")
        if risk.concentration_risk > 0.6:
            warnings.append("High concentration risk")
        if needs_rebalance:
            warnings.append(f"Rebalance needed (max deviation: {max_deviation:.1%})")
        
        # Get correlation info
        corr_matrix = self.get_correlation_matrix()
        total_penalty = sum(p.correlation_penalty * p.size_usd for p in self._positions.values())
        
        state = PortfolioState(
            total_capital=self._capital,
            available_capital=self._capital - allocated,
            allocated_capital=allocated,
            positions=list(self._positions.values()),
            position_count=len(self._positions),
            target_positions=list(self._targets.values()),
            long_exposure=exposure.long_exposure,
            short_exposure=exposure.short_exposure,
            net_exposure=exposure.net_exposure,
            gross_exposure=exposure.gross_exposure,
            portfolio_variance=risk.portfolio_variance,
            portfolio_volatility=risk.portfolio_volatility,
            portfolio_risk=risk.portfolio_risk,
            risk_level=risk.risk_level,
            diversification_score=diversification,
            total_unrealized_pnl_usd=round(total_pnl_usd, 2),
            total_unrealized_pnl_percent=round(total_pnl_pct, 4),
            avg_correlation=corr_matrix.avg_correlation,
            correlation_penalty_applied=round(total_penalty, 2),
            rebalance_required=needs_rebalance,
            max_weight_deviation=max_deviation,
            is_healthy=len(warnings) == 0,
            warnings=warnings,
        )
        
        # Save to history
        self._save_history_entry(state)
        
        return state
    
    def _save_history_entry(self, state: PortfolioState):
        """Save state snapshot to history."""
        entry = PortfolioHistoryEntry(
            total_capital=state.total_capital,
            allocated_capital=state.allocated_capital,
            position_count=state.position_count,
            long_exposure=state.long_exposure,
            short_exposure=state.short_exposure,
            net_exposure=state.net_exposure,
            portfolio_variance=state.portfolio_variance,
            portfolio_volatility=state.portfolio_volatility,
            portfolio_risk=state.portfolio_risk,
            risk_level=state.risk_level,
            total_pnl_usd=state.total_unrealized_pnl_usd,
            total_pnl_percent=state.total_unrealized_pnl_percent,
            diversification_score=state.diversification_score,
            avg_correlation=state.avg_correlation,
        )
        
        self._state_history.append(entry)
        
        # Keep only last 1000 entries
        if len(self._state_history) > 1000:
            self._state_history = self._state_history[-1000:]
    
    def get_history(self, limit: int = 100) -> List[PortfolioHistoryEntry]:
        """Get portfolio history."""
        return self._state_history[-limit:]
    
    def get_positions(self) -> List[PortfolioPosition]:
        """Get all positions."""
        return list(self._positions.values())
    
    def get_position(self, symbol: str) -> Optional[PortfolioPosition]:
        """Get specific position."""
        return self._positions.get(symbol.upper())
    
    # ═══════════════════════════════════════════════════════════
    # 10. Integration with Execution Brain
    # ═══════════════════════════════════════════════════════════
    
    def validate_execution_plan(
        self,
        symbol: str,
        direction: str,
        size_usd: float,
    ) -> Tuple[bool, str, float]:
        """
        Validate execution plan against portfolio constraints.
        
        Returns: (approved, message, adjusted_size)
        """
        symbol = symbol.upper()
        
        # Check position limit
        size_pct = size_usd / self._capital
        if size_pct > MAX_SINGLE_POSITION:
            max_size = self._capital * MAX_SINGLE_POSITION
            return False, f"Exceeds position limit ({MAX_SINGLE_POSITION:.0%})", max_size
        
        # Check exposure limit
        exposure = self.calculate_exposure()
        
        if direction == "LONG":
            new_exposure = exposure.long_exposure + size_pct
            if new_exposure > EXPOSURE_LIMITS["MAX_LONG"]:
                available = exposure.available_long_capacity * self._capital
                return False, f"Exceeds long exposure limit ({EXPOSURE_LIMITS['MAX_LONG']:.0%})", available
        else:
            new_exposure = exposure.short_exposure + size_pct
            if new_exposure > EXPOSURE_LIMITS["MAX_SHORT"]:
                available = exposure.available_short_capacity * self._capital
                return False, f"Exceeds short exposure limit ({EXPOSURE_LIMITS['MAX_SHORT']:.0%})", available
        
        # Apply correlation penalty
        penalty, _ = self._calculate_correlation_penalty_matrix(symbol, direction)
        adjusted_size = size_usd * (1 - penalty)
        
        message = "Approved"
        if penalty > 0:
            message = f"Approved with {penalty:.0%} correlation penalty"
        
        return True, message, round(adjusted_size, 2)
    
    def get_execution_constraints(self, symbol: str, direction: str) -> Dict:
        """
        Get constraints for execution brain.
        
        Returns limits and penalties for a potential position.
        """
        exposure = self.calculate_exposure()
        
        if direction == "LONG":
            max_available_pct = exposure.available_long_capacity
        else:
            max_available_pct = exposure.available_short_capacity
        
        # Cap at single position limit
        max_position_pct = min(max_available_pct, MAX_SINGLE_POSITION)
        max_position_usd = max_position_pct * self._capital
        
        # Get correlation penalty
        penalty, correlated_with = self._calculate_correlation_penalty_matrix(symbol, direction)
        
        return {
            "symbol": symbol,
            "direction": direction,
            "max_position_percent": round(max_position_pct, 4),
            "max_position_usd": round(max_position_usd, 2),
            "correlation_penalty": round(penalty, 4),
            "correlated_with": correlated_with,
            "effective_max_usd": round(max_position_usd * (1 - penalty), 2),
        }


# ══════════════════════════════════════════════════════════════
# Singleton
# ══════════════════════════════════════════════════════════════

_portfolio_engine: Optional[PortfolioManagerEngine] = None


def get_portfolio_manager_engine() -> PortfolioManagerEngine:
    """Get singleton instance of PortfolioManagerEngine."""
    global _portfolio_engine
    if _portfolio_engine is None:
        _portfolio_engine = PortfolioManagerEngine()
    return _portfolio_engine
