"""
Adaptive Risk Service
Phase 5: R2 Adaptive Risk v1

Context-aware capital allocation layer.

Architecture:
- R2 = multiplicative layer AFTER R1
- final_size = R1_size * R2_multiplier
- Deterministic: same inputs → same outputs
- Explainability: components logged and visible

R2 v1 Components:
1. Drawdown-aware sizing
2. Loss-streak dampening

Source of Truth:
- Drawdown: portfolio.drawdown_pct (portfolio truth layer)
- Loss Streak: execution_events (execution history truth)
"""

from typing import Dict, Any, List
import logging

from .config import ADAPTIVE_RISK_DEFAULTS

logger = logging.getLogger(__name__)


class AdaptiveRiskService:
    """
    Adaptive Risk Service (R2 v1)
    
    Provides context-aware sizing adjustments based on:
    - Portfolio drawdown
    - Recent loss streaks
    
    R2 is a multiplicative layer applied AFTER R1:
    final_notional = R1_notional * R2_multiplier
    """
    
    def __init__(self, portfolio_service, execution_repo, config=None):
        """
        Initialize Adaptive Risk Service.
        
        Args:
            portfolio_service: PortfolioService for drawdown calculation
            execution_repo: ExecutionEventRepository for loss streak
            config: Optional config dict (defaults to ADAPTIVE_RISK_DEFAULTS)
        """
        self.portfolio = portfolio_service
        self.execution_repo = execution_repo
        self.config = config or ADAPTIVE_RISK_DEFAULTS
        
        logger.info("[R2] AdaptiveRiskService initialized")
        logger.info(f"[R2]   - Min multiplier: {self.config['min_multiplier']}")
        logger.info(f"[R2]   - Max multiplier: {self.config['max_multiplier']}")
    
    async def evaluate(self, signal: Dict[str, Any]) -> Dict[str, Any]:
        """
        Evaluate R2 adaptive risk multiplier.
        
        Args:
            signal: Signal dict (contains symbol, side, etc.)
        
        Returns:
            {
                "multiplier": float,           # Final R2 multiplier (0.3-1.0)
                "components": {
                    "drawdown": float,         # Drawdown component (0.4-1.0)
                    "loss_streak": float       # Loss streak component (0.5-1.0)
                },
                "debug": {
                    "drawdown_pct": float,     # Portfolio drawdown %
                    "loss_streak_count": int   # Consecutive losses
                }
            }
        """
        # Component 1: Drawdown-aware sizing
        drawdown_component, drawdown_pct = await self._evaluate_drawdown()
        
        # Component 2: Loss-streak dampening
        loss_streak_component, loss_streak_count = await self._evaluate_loss_streak()
        
        # Final R2 multiplier (product of components)
        raw_multiplier = drawdown_component * loss_streak_component
        
        # Clamp to [min, max] range
        multiplier = max(
            self.config['min_multiplier'],
            min(raw_multiplier, self.config['max_multiplier'])
        )
        
        result = {
            "multiplier": round(multiplier, 4),
            "components": {
                "drawdown": round(drawdown_component, 4),
                "loss_streak": round(loss_streak_component, 4)
            },
            "debug": {
                "drawdown_pct": round(drawdown_pct, 2),
                "loss_streak_count": loss_streak_count
            }
        }
        
        logger.debug(f"[R2] Evaluated: multiplier={result['multiplier']}, "
                    f"drawdown={drawdown_component}, loss_streak={loss_streak_component}")
        
        return result
    
    async def _evaluate_drawdown(self) -> tuple[float, float]:
        """
        Evaluate drawdown component.
        
        Returns:
            (multiplier, drawdown_pct)
        """
        try:
            # Get portfolio summary (source of truth)
            summary = await self.portfolio.get_summary()
            drawdown_pct = abs(summary.drawdown_pct)  # Make positive
            
            # Map drawdown to multiplier
            mapping = self.config['drawdown_mapping']
            
            for rule in mapping:
                if drawdown_pct < rule['max_drawdown_pct']:
                    return (rule['multiplier'], drawdown_pct)
            
            # Fallback (should not reach if mapping covers inf)
            return (0.4, drawdown_pct)
        
        except Exception as e:
            logger.error(f"[R2] Drawdown evaluation failed: {e}")
            # Safe fallback: no reduction if evaluation fails
            return (1.0, 0.0)
    
    async def _evaluate_loss_streak(self) -> tuple[float, int]:
        """
        Evaluate loss-streak component.
        
        Returns:
            (multiplier, streak_count)
        """
        try:
            # Get recent closed trades (filled orders from execution_events)
            filled_events = await self.execution_repo.find_by_type("ORDER_FILLED")
            
            # Limit to lookback window
            lookback = self.config['loss_streak_lookback']
            recent_fills = filled_events[:lookback]
            
            # Calculate consecutive losses from most recent
            streak_count = 0
            for event in recent_fills:
                # Check if trade was profitable (simplified: check pnl or realized_pnl)
                # For now, check if event has loss indicator
                # (Real implementation would check closed position PnL)
                
                # Placeholder: assume we have pnl in event debug
                pnl = event.get("debug", {}).get("realized_pnl", 0)
                
                if pnl < 0:
                    streak_count += 1
                else:
                    # Streak broken
                    break
            
            # Map streak to multiplier
            mapping = self.config['loss_streak_mapping']
            
            for rule in mapping:
                if streak_count <= rule['max_streak']:
                    return (rule['multiplier'], streak_count)
            
            # Fallback (should not reach if mapping covers inf)
            return (0.5, streak_count)
        
        except Exception as e:
            logger.error(f"[R2] Loss streak evaluation failed: {e}")
            # Safe fallback: no reduction if evaluation fails
            return (1.0, 0)


# Singleton instance
_adaptive_risk_service = None


def get_adaptive_risk_service():
    """Get singleton AdaptiveRiskService instance."""
    if _adaptive_risk_service is None:
        raise RuntimeError("AdaptiveRiskService not initialized")
    return _adaptive_risk_service


def init_adaptive_risk_service(service):
    """Initialize singleton AdaptiveRiskService."""
    global _adaptive_risk_service
    _adaptive_risk_service = service
    logger.info("[R2] AdaptiveRiskService singleton initialized")
