"""
Execution Handler
=================
Sprint A2.3: Unified execution interface for DRY_RUN and REAL modes.
"""

import logging
import os
from datetime import datetime, timezone
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class ExecutionHandler:
    """
    Execution handler с поддержкой DRY_RUN и REAL режимов.
    
    Режим определяется через ENV EXECUTION_MODE:
    - DRY_RUN: используется simulator
    - REAL: используется OrderManager
    """
    
    def __init__(self, simulator=None, order_manager=None):
        self.simulator = simulator
        self.order_manager = order_manager
        
        # Определяем режим из ENV
        self.mode = os.getenv("EXECUTION_MODE", "DRY_RUN")
        
        # DEBUG: Confirm mode читается корректно
        import sys
        print(f"[ExecutionHandler] EXECUTION_MODE={self.mode} (from os.getenv)", file=sys.stderr, flush=True)
        
        if self.mode not in ["DRY_RUN", "PAPER", "REAL"]:
            raise ValueError(f"Invalid EXECUTION_MODE: {self.mode}. Must be DRY_RUN, PAPER, or REAL")
        
        # Валидация зависимостей
        if self.mode in ["DRY_RUN", "PAPER"] and not self.simulator:
            raise ValueError(f"{self.mode} mode requires simulator")
        
        if self.mode == "REAL" and not self.order_manager:
            raise ValueError("REAL mode requires order_manager")
        
        logger.info(f"[ExecutionHandler] Initialized in {self.mode} mode")
    
    async def execute_order(
        self,
        job_id: str,
        trace_id: Optional[str],
        payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute order based on current mode.
        Pre-execution risk guards are checked first.
        """
        try:
            # ── Pre-execution Risk Guard ──────────────────
            try:
                from modules.risk_guard import get_risk_guard
                guard = get_risk_guard()
                if guard:
                    check = await guard.check_pre_execution(payload)
                    if not check.get("allowed"):
                        reason = check.get("reason", "unknown")
                        logger.warning(
                            f"[ExecutionHandler] ORDER REJECTED by RiskGuard: "
                            f"job_id={job_id} symbol={payload.get('symbol')} reason={reason}"
                        )
                        return {
                            "success": False,
                            "error": f"RiskGuard: {reason}",
                            "mode": self.mode,
                            "job_id": job_id,
                            "rejected_by": "risk_guard",
                        }
            except Exception as e:
                logger.error(f"[ExecutionHandler] RiskGuard check failed: {e}")

            if self.mode == "DRY_RUN":
                logger.info(
                    f"[ExecutionHandler] DRY_RUN execute: job_id={job_id} symbol={payload.get('symbol')}"
                )
                result = await self.simulator.submit_order(
                    job_id=job_id,
                    trace_id=trace_id,
                    payload=payload
                )
                return result
            
            elif self.mode == "PAPER":
                logger.info(
                    f"[ExecutionHandler] PAPER execute: job_id={job_id} symbol={payload.get('symbol')}"
                )
                
                # PAPER mode: Enrich payload with real market price
                enriched_payload = await self._enrich_paper_payload(payload)
                
                result = await self.simulator.submit_order(
                    job_id=job_id,
                    trace_id=trace_id,
                    payload=enriched_payload
                )
                return result
            
            elif self.mode == "REAL":
                logger.info(
                    f"[ExecutionHandler] REAL execute: job_id={job_id} symbol={payload.get('symbol')}"
                )
                
                # OrderManager.place_order() возвращает результат напрямую
                exchange_result = await self.order_manager.place_order(payload)
                
                # Нормализуем результат в формат ExecutionQueue
                return {
                    "success": True,
                    "result": exchange_result,
                    "mode": "REAL",
                    "job_id": job_id,
                }
        
        except Exception as e:
            logger.exception(f"[ExecutionHandler] Execution failed: job_id={job_id}")
            return {
                "success": False,
                "error": str(e),
                "mode": self.mode,
                "job_id": job_id,
            }
    

    def _symbol_to_coinbase(self, symbol: str) -> str:
        """Convert BTCUSDT → BTC-USD for Coinbase API."""
        mapping = {
            "BTCUSDT": "BTC-USD",
            "ETHUSDT": "ETH-USD",
            "SOLUSDT": "SOL-USD",
            "BNBUSDT": "BNB-USD",
            "XRPUSDT": "XRP-USD",
            "ADAUSDT": "ADA-USD",
            "AVAXUSDT": "AVAX-USD",
            "LINKUSDT": "LINK-USD",
            "DOGEUSDT": "DOGE-USD",
        }
        return mapping.get(symbol, symbol.replace("USDT", "-USD"))

    async def _enrich_paper_payload(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Enrich payload with REAL market price from Coinbase for PAPER mode.
        
        Uses CoinbaseProvider.get_ticker() for live prices (public API, no key needed).
        This ensures entry_price reflects the actual market price at execution moment.
        """
        symbol = payload.get("symbol")
        side = payload.get("side")
        quantity = payload.get("quantity", 0.0)
        size_usd = payload.get("size_usd", payload.get("notional_usd", 0.0))
        
        # Get REAL current market price from Coinbase
        market_price = None
        try:
            from modules.data.coinbase_provider import CoinbaseProvider
            provider = CoinbaseProvider()
            coinbase_symbol = self._symbol_to_coinbase(symbol)
            ticker = await provider.get_ticker(coinbase_symbol)
            if ticker and ticker.get("price", 0) > 0:
                market_price = float(ticker["price"])
                logger.info(f"[PAPER] Got REAL price from Coinbase: {symbol} = ${market_price:,.2f}")
        except Exception as e:
            logger.warning(f"[PAPER] Coinbase price fetch failed for {symbol}: {e}")
        
        # If Coinbase failed, try PriceService (simulated but better than hardcoded)
        if market_price is None:
            try:
                from modules.market_data.price_service import get_price_service
                price_svc = await get_price_service()
                market_price = await price_svc.get_mark_price(symbol)
                logger.info(f"[PAPER] Using PriceService price: {symbol} = ${market_price:,.2f}")
            except Exception as e:
                logger.warning(f"[PAPER] PriceService failed for {symbol}: {e}")
        
        # Last resort: use signal price (never use hardcoded $50k)
        if market_price is None:
            market_price = payload.get("price", payload.get("entry_price", 0))
            logger.warning(f"[PAPER] Using signal price as last resort: {symbol} = ${market_price:,.2f}")
        
        # Recalculate quantity from size_usd if available
        if size_usd and market_price > 0:
            quantity = size_usd / market_price
            logger.info(f"[PAPER] Recalculated qty: ${size_usd:.2f} / ${market_price:,.2f} = {quantity:.6f}")
        
        # Enrich payload
        enriched = {
            **payload,
            "entry_price": market_price,
            "price": market_price,
            "final_size": quantity,
            "signal_price": payload.get("signal_price", payload.get("price", payload.get("entry_price", 0))),
        }

        # ── EXECUTION AUDIT LOG ──
        signal_price = enriched["signal_price"]
        slippage = abs(market_price - signal_price) if signal_price and signal_price > 0 else None
        slippage_pct = (slippage / signal_price * 100) if slippage is not None and signal_price > 0 else None
        exec_ts = datetime.now(timezone.utc).isoformat()

        print(
            f"EXECUTION AUDIT: symbol={symbol} "
            f"signal_price=${signal_price:,.2f} "
            f"execution_price=${market_price:,.2f} "
            f"slippage={'${:,.4f}'.format(slippage) if slippage is not None else 'N/A'} "
            f"slippage_pct={f'{slippage_pct:.4f}%' if slippage_pct is not None else 'N/A'} "
            f"price_source=coinbase "
            f"execution_timestamp={exec_ts}"
        )

        # ── SLIPPAGE SANITY GUARD ──
        MAX_SLIPPAGE_PCT = 1.0
        if slippage_pct is not None and slippage_pct > MAX_SLIPPAGE_PCT:
            logger.warning(
                f"[PAPER] SLIPPAGE REJECTED: {symbol} slippage {slippage_pct:.4f}% "
                f"exceeds max {MAX_SLIPPAGE_PCT}% (signal=${signal_price:,.2f} exec=${market_price:,.2f})"
            )
            print(
                f"SLIPPAGE REJECTED: {symbol} {slippage_pct:.4f}% > {MAX_SLIPPAGE_PCT}% "
                f"signal=${signal_price:,.2f} exec=${market_price:,.2f}"
            )
            raise ValueError(
                f"Slippage {slippage_pct:.4f}% exceeds max {MAX_SLIPPAGE_PCT}% "
                f"(signal=${signal_price:,.2f}, exec=${market_price:,.2f})"
            )
        elif slippage_pct is None:
            print(f"SLIPPAGE CHECK: {symbol} — no signal price available, skipping guard")
        else:
            print(f"SLIPPAGE OK: {symbol} {slippage_pct:.4f}% within {MAX_SLIPPAGE_PCT}% limit")

        logger.info(
            f"[PAPER] Enriched payload: symbol={symbol}, qty={quantity:.6f}, "
            f"market_price=${market_price:,.2f} (REAL)"
        )
        
        return enriched

    def get_mode(self) -> str:
        """Get current execution mode."""
        return self.mode
