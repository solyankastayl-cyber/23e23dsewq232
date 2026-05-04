"""
Dynamic Risk Engine Service
Sprint R1: Intelligent position sizing + exposure management

Flow:
    Signal → RiskManager → DynamicRiskEngine → AutoSafety → ExecutionBridge
    
Features:
    - Confidence-based sizing (min_conf → max_conf maps to min_mult → max_mult)
    - Regime multipliers (TREND_UP = bigger, RANGE = smaller)
    - Symbol exposure caps (max $ per symbol)
    - Portfolio exposure caps (max % deployed)
"""

from __future__ import annotations

import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


class DynamicRiskEngine:
    """
    Deterministic, confidence-aware position sizing.
    
    NOT ML-based. NOT Kelly. Just:
        size = base * confidence_multiplier * regime_multiplier
    
    Then check:
        - symbol exposure
        - portfolio exposure
    """
    
    def __init__(self, portfolio_service, position_repo, config: Dict[str, Any]):
        self.portfolio_service = portfolio_service
        self.position_repo = position_repo
        self.config = config
        logger.info("[DynamicRisk] Engine initialized")

    async def evaluate(self, signal: Dict[str, Any]) -> Dict[str, Any]:
        """
        Evaluate position sizing for signal.
        
        Args:
            signal: {symbol, side, confidence, entry_price, metadata, ...}
        
        Returns:
            {
                "approved": bool,
                "reason": str | None,
                "notional_usd": float,
                "qty": float,
                "size_multiplier": float,
                "symbol_exposure_usd": float,
                "portfolio_exposure_pct": float,
                "debug": dict
            }
        """
        if not self.config.get("enabled", True):
            logger.debug("[DynamicRisk] Engine disabled, passing through")
            return {
                "approved": True,
                "reason": None,
                "notional_usd": 0,
                "qty": 0,
                "size_multiplier": 1.0,
                "symbol_exposure_usd": 0,
                "portfolio_exposure_pct": 0,
                "debug": {},
            }

        # Extract signal data
        symbol = signal.get("symbol")
        
        # CRITICAL: Idempotency check - reject signals without confidence
        confidence = signal.get("confidence")
        if confidence is None or confidence == 0:
            logger.warning(f"[DynamicRisk] BLOCKED: {symbol} - NO_CONFIDENCE (confidence={confidence})")
            return {
                "approved": False,
                "reason": "NO_CONFIDENCE",
                "notional_usd": 0,
                "qty": 0,
                "size_multiplier": 0,
                "symbol_exposure_usd": 0,
                "portfolio_exposure_pct": 0,
                "debug": {"raw_confidence": confidence},
            }
        
        confidence = float(confidence)
        entry_price = float(signal.get("entry_price") or signal.get("price") or 0)

        if entry_price <= 0:
            logger.warning(f"[DynamicRisk] Invalid entry price: {entry_price}")
            return {
                "approved": False,
                "reason": "INVALID_ENTRY_PRICE",
                "notional_usd": 0,
                "qty": 0,
                "size_multiplier": 0,
                "symbol_exposure_usd": 0,
                "portfolio_exposure_pct": 0,
                "debug": {"entry_price": entry_price},
            }

        # Check minimum confidence
        min_conf = self.config["min_confidence"]
        max_conf = self.config["max_confidence"]

        if confidence < min_conf:
            logger.info(f"[DynamicRisk] BLOCKED: confidence {confidence:.3f} < {min_conf}")
            return {
                "approved": False,
                "reason": "CONFIDENCE_TOO_LOW",
                "notional_usd": 0,
                "qty": 0,
                "size_multiplier": 0,
                "symbol_exposure_usd": 0,
                "portfolio_exposure_pct": 0,
                "debug": {"confidence": confidence, "min_confidence": min_conf},
            }

        # Calculate confidence-based multiplier
        size_multiplier = self._confidence_multiplier(confidence, min_conf, max_conf)
        
        # CRITICAL: Clamp size_multiplier to safety bounds
        MIN_SIZE_MULTIPLIER = float(self.config["min_size_multiplier"])
        MAX_SIZE_MULTIPLIER = float(self.config["max_size_multiplier"])
        size_multiplier = max(MIN_SIZE_MULTIPLIER, min(size_multiplier, MAX_SIZE_MULTIPLIER))

        # Apply regime multiplier (if available)
        regime = signal.get("metadata", {}).get("regime", "UNKNOWN")
        regime_multiplier = self.config["regime_multipliers"].get(regime, 1.0)

        final_multiplier = size_multiplier * regime_multiplier
        
        # CRITICAL: Clamp final multiplier again to ensure safety
        final_multiplier = max(MIN_SIZE_MULTIPLIER, min(final_multiplier, MAX_SIZE_MULTIPLIER))

        # Calculate notional
        base_notional = float(self.config["base_notional_usd"])
        notional_usd = base_notional * final_multiplier
        
        # CRITICAL: Clamp notional to max symbol exposure
        MAX_SYMBOL_NOTIONAL_USD = float(self.config["max_symbol_notional_usd"])
        notional_usd = min(notional_usd, MAX_SYMBOL_NOTIONAL_USD)

        # Check portfolio exposure
        summary = await self.portfolio_service.get_summary()
        # deployment_pct comes as percentage (e.g., 80.88), convert to decimal
        portfolio_exposure_pct = float(summary.deployment_pct or 0.0) / 100.0
        equity = float(summary.total_equity or 0.0)

        if portfolio_exposure_pct >= self.config["max_portfolio_exposure_pct"]:
            logger.info(f"[DynamicRisk] BLOCKED: portfolio exposure {portfolio_exposure_pct:.1%} >= {self.config['max_portfolio_exposure_pct']:.1%}")
            return {
                "approved": False,
                "reason": "MAX_PORTFOLIO_EXPOSURE",
                "notional_usd": 0,
                "qty": 0,
                "size_multiplier": final_multiplier,
                "symbol_exposure_usd": 0,
                "portfolio_exposure_pct": portfolio_exposure_pct,
                "debug": {"portfolio_exposure_pct": portfolio_exposure_pct, "max_allowed": self.config["max_portfolio_exposure_pct"]},
            }

        # Check symbol exposure
        symbol_exposure_usd = await self._get_symbol_exposure_usd(symbol)

        if symbol_exposure_usd + notional_usd > self.config["max_symbol_notional_usd"]:
            logger.info(f"[DynamicRisk] BLOCKED: {symbol} exposure {symbol_exposure_usd + notional_usd:.2f} > {self.config['max_symbol_notional_usd']}")
            return {
                "approved": False,
                "reason": "MAX_SYMBOL_EXPOSURE",
                "notional_usd": 0,
                "qty": 0,
                "size_multiplier": final_multiplier,
                "symbol_exposure_usd": symbol_exposure_usd,
                "portfolio_exposure_pct": portfolio_exposure_pct,
            }

        # Calculate quantity
        qty = notional_usd / entry_price
        
        # CRITICAL: Clamp qty to minimum (Binance futures minQty-like safety)
        MIN_QTY = 0.001
        qty = max(qty, MIN_QTY)
        
        # Debug metadata for explainability
        debug_meta = {
            "base_notional": base_notional,
            "confidence": confidence,
            "confidence_component": size_multiplier,
            "regime": regime,
            "regime_component": regime_multiplier,
            "final_multiplier": final_multiplier,
            "raw_notional": base_notional * final_multiplier,
            "clamped_notional": notional_usd,
            "entry_price": entry_price,
            "raw_qty": notional_usd / entry_price,
            "clamped_qty": qty,
        }

        logger.info(f"[DynamicRisk] APPROVED: {symbol} conf={confidence:.3f} mult={final_multiplier:.2f} qty={qty:.4f}")

        return {
            "approved": True,
            "reason": None,
            "notional_usd": round(notional_usd, 4),
            "qty": round(qty, 6),
            "size_multiplier": round(final_multiplier, 4),
            "symbol_exposure_usd": round(symbol_exposure_usd, 4),
            "portfolio_exposure_pct": round(portfolio_exposure_pct, 4),
            "debug": debug_meta,
        }

    def _confidence_multiplier(self, confidence: float, min_conf: float, max_conf: float) -> float:
        """
        Map confidence [min_conf, max_conf] → [min_mult, max_mult]
        
        Linear interpolation.
        """
        low = self.config["min_size_multiplier"]
        high = self.config["max_size_multiplier"]

        if confidence <= min_conf:
            return low
        if confidence >= max_conf:
            return high

        # Linear interpolation
        norm = (confidence - min_conf) / (max_conf - min_conf)
        return low + (high - low) * norm

    async def _get_symbol_exposure_usd(self, symbol: str) -> float:
        """
        Calculate total USD exposure for symbol across all open positions.
        """
        try:
            rows = await self.position_repo.find_open_by_symbol(symbol)
            total = 0.0
            for row in rows:
                qty = float(row.get("qty", 0) or 0)
                mark = float(row.get("mark_price", 0) or row.get("entry_price", 0) or 0)
                total += qty * mark
            return total
        except Exception as e:
            logger.error(f"[DynamicRisk] Failed to get symbol exposure: {e}")
            return 0.0
