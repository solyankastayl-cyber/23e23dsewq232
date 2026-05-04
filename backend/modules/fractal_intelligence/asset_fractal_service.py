"""
PHASE 25.2 — Asset Fractal Service

Aggregates all three asset fractal adapters (BTC, SPX, DXY).
Provides unified API for cross-asset fractal intelligence.
"""

from typing import Optional, Dict, Any
from datetime import datetime

from .asset_fractal_types import (
    AssetFractalContext,
    MultiAssetFractalContext,
    AssetFractalHealthStatus,
)
from .btc_fractal_adapter import BTCFractalAdapter, get_btc_fractal_adapter
from .spx_fractal_adapter import SPXFractalAdapter, get_spx_fractal_adapter
from .dxy_fractal_adapter import DXYFractalAdapter, get_dxy_fractal_adapter


class AssetFractalService:
    """
    Service that aggregates all asset fractal adapters.
    
    Provides:
    - Individual asset contexts
    - Multi-asset context
    - Health status
    """
    
    def __init__(self):
        self.btc_adapter = get_btc_fractal_adapter()
        self.spx_adapter = get_spx_fractal_adapter()
        self.dxy_adapter = get_dxy_fractal_adapter()
        
        self._last_multi_context: Optional[MultiAssetFractalContext] = None
    
    # ═══════════════════════════════════════════════════════════
    # Individual Asset Methods
    # ═══════════════════════════════════════════════════════════
    
    async def get_btc_context(self) -> AssetFractalContext:
        """Get BTC fractal context."""
        return await self.btc_adapter.build_context()
    
    async def get_spx_context(self) -> AssetFractalContext:
        """Get SPX fractal context."""
        return await self.spx_adapter.build_context()
    
    async def get_dxy_context(self) -> AssetFractalContext:
        """Get DXY fractal context."""
        return await self.dxy_adapter.build_context()
    
    def get_btc_context_sync(self) -> AssetFractalContext:
        """Get BTC fractal context (sync)."""
        return self.btc_adapter.build_context_sync()
    
    def get_spx_context_sync(self) -> AssetFractalContext:
        """Get SPX fractal context (sync)."""
        return self.spx_adapter.build_context_sync()
    
    def get_dxy_context_sync(self) -> AssetFractalContext:
        """Get DXY fractal context (sync)."""
        return self.dxy_adapter.build_context_sync()
    
    # ═══════════════════════════════════════════════════════════
    # Multi-Asset Methods
    # ═══════════════════════════════════════════════════════════
    
    async def get_all_contexts(self) -> MultiAssetFractalContext:
        """
        Get all three asset fractal contexts.
        
        Returns unified MultiAssetFractalContext.
        """
        btc = await self.get_btc_context()
        spx = await self.get_spx_context()
        dxy = await self.get_dxy_context()
        
        multi = MultiAssetFractalContext(
            btc=btc,
            spx=spx,
            dxy=dxy,
            timestamp=datetime.utcnow(),
        )
        
        self._last_multi_context = multi
        return multi
    
    def get_all_contexts_sync(self) -> MultiAssetFractalContext:
        """Get all contexts synchronously."""
        btc = self.get_btc_context_sync()
        spx = self.get_spx_context_sync()
        dxy = self.get_dxy_context_sync()
        
        multi = MultiAssetFractalContext(
            btc=btc,
            spx=spx,
            dxy=dxy,
            timestamp=datetime.utcnow(),
        )
        
        self._last_multi_context = multi
        return multi
    
    # ═══════════════════════════════════════════════════════════
    # Integration with Macro Context
    # ═══════════════════════════════════════════════════════════
    
    def build_dxy_from_macro(
        self,
        macro_usd_bias: str,
        macro_confidence: float,
    ) -> AssetFractalContext:
        """
        Build DXY context from macro USD bias.
        
        Used when DXY fractal service unavailable but macro is available.
        """
        return self.dxy_adapter.build_from_macro_context(macro_usd_bias, macro_confidence)
    
    async def get_all_contexts_with_macro_fallback(
        self,
        macro_usd_bias: Optional[str] = None,
        macro_confidence: Optional[float] = None,
    ) -> MultiAssetFractalContext:
        """
        Get all contexts, using macro fallback for DXY if needed.
        """
        btc = await self.get_btc_context()
        spx = await self.get_spx_context()
        
        # Try DXY fractal first, fall back to macro-derived
        try:
            dxy = await self.get_dxy_context()
            if dxy.context_state == "BLOCKED" and macro_usd_bias:
                dxy = self.build_dxy_from_macro(
                    macro_usd_bias,
                    macro_confidence or 0.5
                )
        except Exception:
            if macro_usd_bias:
                dxy = self.build_dxy_from_macro(
                    macro_usd_bias,
                    macro_confidence or 0.5
                )
            else:
                dxy = self.get_dxy_context_sync()
        
        multi = MultiAssetFractalContext(
            btc=btc,
            spx=spx,
            dxy=dxy,
            timestamp=datetime.utcnow(),
        )
        
        self._last_multi_context = multi
        return multi
    
    # ═══════════════════════════════════════════════════════════
    # Health
    # ═══════════════════════════════════════════════════════════
    
    def get_health(self) -> AssetFractalHealthStatus:
        """Get health status of asset fractal service."""
        btc_ok = False
        spx_ok = False
        dxy_ok = False
        last_update = None
        
        if self._last_multi_context:
            btc_ok = self._last_multi_context.btc.context_state != "BLOCKED"
            spx_ok = self._last_multi_context.spx.context_state != "BLOCKED"
            dxy_ok = self._last_multi_context.dxy.context_state != "BLOCKED"
            last_update = self._last_multi_context.timestamp
        
        if btc_ok and spx_ok and dxy_ok:
            status = "OK"
        elif btc_ok or spx_ok or dxy_ok:
            status = "DEGRADED"
        else:
            status = "ERROR"
        
        return AssetFractalHealthStatus(
            status=status,
            btc_available=btc_ok,
            spx_available=spx_ok,
            dxy_available=dxy_ok,
            last_update=last_update,
        )


# Singleton
_service: Optional[AssetFractalService] = None

def get_asset_fractal_service() -> AssetFractalService:
    global _service
    if _service is None:
        _service = AssetFractalService()
    return _service
