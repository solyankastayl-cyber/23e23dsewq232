"""Allocator V4 — Covariance-Aware Portfolio Optimizer

Extends V3 with:
- Covariance matrix calculation
- Portfolio volatility optimization
- Greedy portfolio construction
- Marginal risk contribution
"""

import numpy as np
import logging
from typing import List, Dict, Any

from .allocator_v3 import StrategyAllocatorV3
from .covariance import covariance_matrix
from .optimizer import PortfolioOptimizer

logger = logging.getLogger(__name__)


class StrategyAllocatorV4(StrategyAllocatorV3):
    """V4 allocator with covariance-aware optimization.
    
    Inherits all V3 logic + adds portfolio optimization layer.
    """
    
    def __init__(
        self,
        vol_penalty: float = 0.35,
        exec_penalty: float = 0.15,
        concentration_penalty: float = 0.20
    ):
        """
        Args:
            vol_penalty: Weight for portfolio volatility penalty
            exec_penalty: Weight for execution cost penalty
            concentration_penalty: Weight for concentration penalty
        """
        super().__init__()
        self.optimizer = PortfolioOptimizer(
            vol_penalty=vol_penalty,
            exec_penalty=exec_penalty,
            concentration_penalty=concentration_penalty
        )
    
    def allocate(
        self,
        signals: List[Signal],
        stats_map: Dict[str, StrategyStats],
        portfolio: Dict[str, Any],
        execution_map: Dict[str, Dict[str, Any]],
        regime: str,
        open_positions: List[Dict[str, Any]] = None,
        price_history_map: Dict[str, List[float]] = None
    ) -> Dict[str, Any]:
        """
        Allocate capital using V4 mathematics.
        
        Args:
            signals: Trading signals
            stats_map: Strategy performance stats
            portfolio: Portfolio state
            execution_map: Execution quality data
            regime: Market regime
            open_positions: Currently open positions
            price_history_map: Historical prices for covariance calculation
        
        Returns:
            {
                "decisions": [...],
                "allocator_meta": {...}
            }
        """
        logger.info(
            f"[AllocatorV4] Starting allocation: {len(signals)} signals, "
            f"price_history={'available' if price_history_map else 'missing'}"
        )
        
        # CRITICAL: Fallback to V3 if no price history
        if not price_history_map or len(price_history_map) < 2:
            logger.warning(
                "[AllocatorV4] Insufficient price history for covariance — "
                "falling back to V3"
            )
            result = super().allocate(
                signals=signals,
                stats_map=stats_map,
                portfolio=portfolio,
                execution_map=execution_map,
                regime=regime,
                open_positions=open_positions
            )
            result["allocator_meta"]["version"] = "V4 (V3 fallback)"
            return result
        
        # STEP 1: Run V3 logic to get candidate trades
        v3_result = super().allocate(
            signals=signals,
            stats_map=stats_map,
            portfolio=portfolio,
            execution_map=execution_map,
            regime=regime,
            open_positions=open_positions
        )
        
        v3_decisions = v3_result.get("decisions", [])
        
        if not v3_decisions:
            logger.info("[AllocatorV4] No V3 decisions to optimize")
            v3_result["allocator_meta"]["version"] = "V4 (no candidates)"
            return v3_result
        
        logger.info(f"[AllocatorV4] V3 generated {len(v3_decisions)} candidates")
        
        # STEP 2: Calculate covariance matrix
        try:
            symbols, cov = covariance_matrix(price_history_map)
            
            if cov.size == 0:
                logger.warning("[AllocatorV4] Empty covariance matrix — falling back to V3")
                v3_result["allocator_meta"]["version"] = "V4 (empty cov)"
                return v3_result
            
            logger.info(f"[AllocatorV4] Covariance matrix: {len(symbols)} symbols")
        
        except Exception as e:
            logger.error(f"[AllocatorV4] Covariance calculation failed: {e}", exc_info=True)
            v3_result["allocator_meta"]["version"] = "V4 (cov error)"
            return v3_result
        
        # STEP 3: Add concentration scores to candidates
        equity = float(portfolio.get("equity", 0.0))
        
        for d in v3_decisions:
            size_usd = float(d.get("size_usd", 0.0))
            concentration = size_usd / equity if equity > 0 else 0.0
            d["concentration_score"] = concentration
        
        # STEP 4: Run portfolio optimizer
        try:
            optimized_decisions = self.optimizer.optimize(
                candidates=v3_decisions,
                symbols=symbols,
                cov=cov,
                max_positions=self.MAX_POSITIONS
            )
            
            logger.info(
                f"[AllocatorV4] Optimizer selected {len(optimized_decisions)} positions "
                f"from {len(v3_decisions)} candidates"
            )
        
        except Exception as e:
            logger.error(f"[AllocatorV4] Optimization failed: {e}", exc_info=True)
            v3_result["allocator_meta"]["version"] = "V4 (optimizer error)"
            return v3_result
        
        # STEP 5: Calculate portfolio metrics
        portfolio_vol = 0.0
        try:
            if optimized_decisions:
                weights = []
                for s in symbols:
                    w = sum(
                        float(d.get("size_usd", 0.0))
                        for d in optimized_decisions
                        if d["symbol"] == s
                    )
                    weights.append(w)
                
                weights = np.array(weights, dtype=float)
                total = weights.sum()
                
                if total > 0:
                    weights = weights / total
                    from .portfolio_math import portfolio_volatility
                    portfolio_vol = portfolio_volatility(weights, cov)
        
        except Exception as e:
            logger.warning(f"[AllocatorV4] Portfolio vol calculation failed: {e}")
        
        # STEP 6: Return optimized result
        return {
            "decisions": optimized_decisions,
            "allocator_meta": {
                "version": "V4",
                "regime": regime,
                "drawdown": v3_result["allocator_meta"].get("drawdown", 0.0),
                "drawdown_multiplier": v3_result["allocator_meta"].get("drawdown_multiplier", 1.0),
                "signals_in": len(signals),
                "signals_out": len(optimized_decisions),
                "v3_candidates": len(v3_decisions),
                "portfolio_volatility": round(portfolio_vol, 6),
                "optimizer_config": {
                    "vol_penalty": self.optimizer.vol_penalty,
                    "exec_penalty": self.optimizer.exec_penalty,
                    "concentration_penalty": self.optimizer.concentration_penalty,
                },
            },
        }


# Import types from V3 (for type hints)
from .types import Signal, StrategyStats
