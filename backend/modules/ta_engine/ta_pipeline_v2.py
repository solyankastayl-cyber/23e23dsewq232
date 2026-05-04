"""
TA Engine - Main Pipeline (v2)
Multi-layer analysis: 1 chart → 10 layers → synthesis

ARCHITECTURE:
RAW CHART
→ Layer 1: Structure
→ Layer 2: Trendlines
→ Layer 3: Channels
→ Layer 4: Figures (PRIMARY)
→ Layer 5: Levels
→ Layer 6: Fibonacci
→ Layer 7: Candles
→ Layer 8: Elliott
→ Layer 9: Regime
→ Layer 10: Confirmation
→ SYNTHESIS
"""

from typing import List, Dict, Optional
from .core.chart_basis import get_basis_builder, ChartBasis
from .groups.base import GroupResult, GROUP_STRUCTURE, GROUP_CHANNELS, GROUP_FIGURES
from .groups.structure_layer import get_structure_layer
from .groups.channel_layer import get_channel_layer
from .groups.figure_layer_v2 import get_figure_layer_v2  # USE V2!
from .synthesis.synthesis_engine import get_synthesis_engine


class TAPipelineV2:
    """
    Multi-layer TA pipeline.
    
    Runs all layers independently, then synthesizes.
    """
    
    def __init__(self):
        self.basis_builder = get_basis_builder()
        self.synthesis = get_synthesis_engine()
        
        # Initialize layers - USE FIGURE_LAYER_V2
        self.layers = {
            GROUP_STRUCTURE: get_structure_layer(),
            GROUP_CHANNELS: get_channel_layer(),
            GROUP_FIGURES: get_figure_layer_v2(),  # V2: Structure-first approach
        }
    
    def run(
        self,
        candles: List[Dict],
        timeframe: str = "1D",
        symbol: str = "BTC"
    ) -> Dict:
        """
        Run full TA pipeline.
        
        Args:
            candles: OHLCV candle data
            timeframe: Chart timeframe
            symbol: Trading pair
            
        Returns:
            Complete TA synthesis
        """
        # Stage 1: Build common basis
        basis = self.basis_builder.build(candles, timeframe, symbol)
        
        print(f"[TAPipeline] Built basis: {len(candles)} candles, "
              f"{len(basis.pivots)} pivots, {len(basis.swings)} swings")
        
        # Stage 2: Run each layer independently
        layer_results = {}
        
        for group_name, layer in self.layers.items():
            try:
                result = layer.run(basis)
                layer_results[group_name] = result
                
                findings_count = len(result.findings) if result.findings else 0
                print(f"[TAPipeline] {group_name}: {findings_count} findings")
                
            except Exception as e:
                print(f"[TAPipeline] {group_name} FAILED: {e}")
                layer_results[group_name] = GroupResult(group=group_name)
        
        # Stage 3: Synthesize results
        synthesis = self.synthesis.synthesize(layer_results)
        
        # Log main pattern
        main = synthesis.get("main_pattern")
        if main:
            print(f"[TAPipeline] MAIN: {main.get('type')} score={main.get('score', 0):.2f}")
        else:
            print("[TAPipeline] No main pattern found")
        
        return {
            "ok": True,
            "timeframe": timeframe,
            "symbol": symbol,
            "basis": basis.to_dict(),
            **synthesis,
        }
    
    def get_pattern_render_contract(self, candles: List[Dict], timeframe: str = "1D") -> Optional[Dict]:
        """
        Convenience method: Run pipeline and return pattern_render_contract.
        
        This is what the frontend needs.
        """
        result = self.run(candles, timeframe)
        
        ui = result.get("ui", {})
        return ui.get("pattern_render_contract")


# Singleton
_pipeline_v2 = None

def get_ta_pipeline_v2() -> TAPipelineV2:
    global _pipeline_v2
    if _pipeline_v2 is None:
        _pipeline_v2 = TAPipelineV2()
    return _pipeline_v2


# ═══════════════════════════════════════════════════════════════
# INTEGRATION WITH EXISTING per_tf_builder
# ═══════════════════════════════════════════════════════════════

def run_ta_v2(candles: List[Dict], timeframe: str = "1D", symbol: str = "BTC") -> Dict:
    """
    Standalone function to run TA v2 pipeline.
    
    Can be called from per_tf_builder or ta_routes.
    """
    pipeline = get_ta_pipeline_v2()
    return pipeline.run(candles, timeframe, symbol)


def get_pattern_contract_v2(candles: List[Dict], timeframe: str = "1D") -> Optional[Dict]:
    """
    Get pattern_render_contract using v2 pipeline.
    
    Returns None if no pattern found.
    """
    pipeline = get_ta_pipeline_v2()
    return pipeline.get_pattern_render_contract(candles, timeframe)
