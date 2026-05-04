"""
Take Profit Engine
==================

Engine for take profit management (PHASE 1.3)
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass

from .position_policy_types import (
    TakeProfitType,
    TPPlacement,
    TakeProfitConfig
)


@dataclass
class TPCalculation:
    """Result of TP calculation"""
    tp_type: TakeProfitType
    entry_price: float
    stop_price: float
    targets: List[Dict[str, Any]]  # List of TP levels
    total_rr: float
    notes: List[str]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "tpType": self.tp_type.value,
            "entryPrice": round(self.entry_price, 8),
            "stopPrice": round(self.stop_price, 8),
            "targets": self.targets,
            "totalRR": round(self.total_rr, 2),
            "notes": self.notes
        }


class TakeProfitEngine:
    """
    Engine for calculating and managing take profits.
    """
    
    def __init__(self):
        self._configs = self._build_default_configs()
    
    def _build_default_configs(self) -> Dict[str, TakeProfitConfig]:
        """Build default TP configs per strategy"""
        
        return {
            # TREND_CONFIRMATION - Trailing TP for runners
            "TREND_CONFIRMATION": TakeProfitConfig(
                tp_type=TakeProfitType.TRAILING_TP,
                placement=TPPlacement.TRAILING,
                rr_ratio=2.0,
                trailing_activation_pct=0.5,
                trailing_distance_pct=0.3,
                use_multiple_targets=True,
                targets=[
                    {"rr": 1.0, "sizePct": 0.3},
                    {"rr": 2.0, "sizePct": 0.3},
                    {"rr": 0, "sizePct": 0.4, "trailing": True}  # Rest trails
                ]
            ),
            
            # MOMENTUM_BREAKOUT - Fixed RR
            "MOMENTUM_BREAKOUT": TakeProfitConfig(
                tp_type=TakeProfitType.FIXED_RR,
                placement=TPPlacement.RR_RATIO,
                rr_ratio=2.0,
                use_multiple_targets=True,
                targets=[
                    {"rr": 1.5, "sizePct": 0.5},
                    {"rr": 2.5, "sizePct": 0.5}
                ]
            ),
            
            # MEAN_REVERSION - Structure TP
            "MEAN_REVERSION": TakeProfitConfig(
                tp_type=TakeProfitType.STRUCTURE_TP,
                placement=TPPlacement.RESISTANCE,
                structure_levels=["resistance", "vwap", "liquidity"],
                rr_ratio=1.5,
                use_multiple_targets=True,
                targets=[
                    {"rr": 1.0, "sizePct": 0.5},
                    {"rr": 1.5, "sizePct": 0.5}
                ]
            )
        }
    
    def calculate_tp(
        self,
        strategy: str,
        entry_price: float,
        stop_price: float,
        direction: str,  # LONG or SHORT
        resistance: Optional[float] = None,
        support: Optional[float] = None,
        vwap: Optional[float] = None
    ) -> TPCalculation:
        """
        Calculate take profit levels.
        """
        
        strategy_upper = strategy.upper()
        config = self._configs.get(strategy_upper, self._configs["MOMENTUM_BREAKOUT"])
        
        is_long = direction.upper() == "LONG"
        risk = abs(entry_price - stop_price)
        
        targets = []
        notes = []
        
        if config.tp_type == TakeProfitType.FIXED_RR:
            # Calculate TP based on RR ratio
            for target in config.targets:
                rr = target.get("rr", config.rr_ratio)
                size_pct = target.get("sizePct", 1.0)
                
                if is_long:
                    tp_price = entry_price + (risk * rr)
                else:
                    tp_price = entry_price - (risk * rr)
                
                targets.append({
                    "price": round(tp_price, 8),
                    "rr": rr,
                    "sizePct": size_pct,
                    "distancePct": round((abs(tp_price - entry_price) / entry_price) * 100, 4),
                    "trailing": False
                })
            
            notes.append(f"Fixed RR targets at {[t['rr'] for t in config.targets]}R")
        
        elif config.tp_type == TakeProfitType.STRUCTURE_TP:
            # Structure-based TP
            if is_long:
                structure_target = resistance or vwap or (entry_price * 1.02)
            else:
                structure_target = support or vwap or (entry_price * 0.98)
            
            # Calculate RR to structure
            structure_distance = abs(structure_target - entry_price)
            structure_rr = structure_distance / risk if risk > 0 else 1.5
            
            for target in config.targets:
                rr = target.get("rr", structure_rr)
                size_pct = target.get("sizePct", 1.0)
                
                if is_long:
                    tp_price = entry_price + (risk * rr)
                else:
                    tp_price = entry_price - (risk * rr)
                
                targets.append({
                    "price": round(tp_price, 8),
                    "rr": round(rr, 2),
                    "sizePct": size_pct,
                    "distancePct": round((abs(tp_price - entry_price) / entry_price) * 100, 4),
                    "trailing": False
                })
            
            notes.append(f"Structure TP targeting {config.structure_levels}")
        
        elif config.tp_type == TakeProfitType.TRAILING_TP:
            # Trailing TP
            for target in config.targets:
                rr = target.get("rr", 0)
                size_pct = target.get("sizePct", 1.0)
                is_trailing = target.get("trailing", False)
                
                if is_trailing:
                    # Trailing portion - no fixed TP
                    targets.append({
                        "price": None,
                        "rr": None,
                        "sizePct": size_pct,
                        "distancePct": None,
                        "trailing": True,
                        "trailingActivation": config.trailing_activation_pct,
                        "trailingDistance": config.trailing_distance_pct
                    })
                else:
                    if is_long:
                        tp_price = entry_price + (risk * rr)
                    else:
                        tp_price = entry_price - (risk * rr)
                    
                    targets.append({
                        "price": round(tp_price, 8),
                        "rr": rr,
                        "sizePct": size_pct,
                        "distancePct": round((abs(tp_price - entry_price) / entry_price) * 100, 4),
                        "trailing": False
                    })
            
            notes.append(f"Trailing TP with partial targets and trailing remainder")
        
        # Calculate total RR
        total_rr = max([t.get("rr", 0) or 0 for t in targets]) if targets else config.rr_ratio
        
        return TPCalculation(
            tp_type=config.tp_type,
            entry_price=entry_price,
            stop_price=stop_price,
            targets=targets,
            total_rr=total_rr,
            notes=notes
        )
    
    def get_config_for_strategy(self, strategy: str) -> TakeProfitConfig:
        """Get TP config for strategy"""
        return self._configs.get(strategy.upper(), self._configs["MOMENTUM_BREAKOUT"])
    
    def get_all_tp_types(self) -> List[Dict[str, Any]]:
        """Get all TP types with descriptions"""
        return [
            {
                "type": TakeProfitType.FIXED_RR.value,
                "name": "Fixed Risk/Reward",
                "description": "Take profit at fixed multiples of risk",
                "useCases": ["Momentum Breakout", "Clear targets"],
                "example": "Entry at 100, Stop at 98 (2 risk), TP at 104 (2R)"
            },
            {
                "type": TakeProfitType.STRUCTURE_TP.value,
                "name": "Structure TP",
                "description": "Take profit at structure levels (resistance, VWAP, liquidity)",
                "useCases": ["Mean Reversion", "Range trading"],
                "example": "Exit at resistance or VWAP level"
            },
            {
                "type": TakeProfitType.TRAILING_TP.value,
                "name": "Trailing TP",
                "description": "Let profits run with trailing stop",
                "useCases": ["Trend following", "Strong momentum"],
                "example": "Partial exits + trail remainder"
            }
        ]
    
    def get_strategy_matrix(self) -> Dict[str, Dict[str, Any]]:
        """Get strategy-TP matrix"""
        return {
            strategy: {
                "tpType": config.tp_type.value,
                "placement": config.placement.value,
                "defaultRR": config.rr_ratio,
                "multiTarget": config.use_multiple_targets,
                "targetCount": len(config.targets)
            }
            for strategy, config in self._configs.items()
        }


# Global singleton
take_profit_engine = TakeProfitEngine()
