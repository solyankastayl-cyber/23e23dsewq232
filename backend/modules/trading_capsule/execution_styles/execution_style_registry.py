"""
Execution Style Registry
========================

Реестр всех стилей исполнения.
"""

from typing import Dict, List, Optional

from .execution_style_types import (
    ExecutionStyleType,
    ExecutionStyleDefinition,
    EntryConfig,
    ExitConfig,
    EntryBehavior,
    ExitBehavior
)


class ExecutionStyleRegistry:
    """
    Registry of all execution styles.
    """
    
    def __init__(self):
        self._styles: Dict[ExecutionStyleType, ExecutionStyleDefinition] = {}
        self._build_registry()
    
    def _build_registry(self):
        """Build registry of all execution styles"""
        
        # ===========================================
        # CLEAN_ENTRY
        # ===========================================
        self._styles[ExecutionStyleType.CLEAN_ENTRY] = ExecutionStyleDefinition(
            style_type=ExecutionStyleType.CLEAN_ENTRY,
            name="Clean Entry",
            description="Single clean entry with fixed risk. No averaging, no scaling. Standard TP/SL execution.",
            
            entry_config=EntryConfig(
                behavior=EntryBehavior.SINGLE,
                single_entry=True,
                max_entries=1,
                entry_spacing_pct=0.0,
                entry_size_distribution=[1.0],
                require_confirmation=True,
                allow_aggressive_entry=False
            ),
            
            exit_config=ExitConfig(
                behavior=ExitBehavior.FULL_AT_TARGET,
                partial_exits=[],
                time_exit_enabled=False,
                defensive_enabled=True,
                structure_break_exit=True,
                volatility_exit=False,
                trailing_enabled=False
            ),
            
            risk_level="LOW",
            max_position_adds=0,
            max_total_risk_pct=1.5,
            
            characteristics=[
                "Single entry point",
                "Fixed position size",
                "No averaging",
                "Clear risk definition",
                "Simple execution"
            ],
            use_cases=[
                "Trend Confirmation entries",
                "Momentum Breakout entries",
                "Conservative profiles",
                "Clear invalidation setups"
            ],
            warnings=[
                "May miss optimal entry if price moves quickly",
                "No opportunity to improve average price"
            ]
        )
        
        # ===========================================
        # SCALED_ENTRY
        # ===========================================
        self._styles[ExecutionStyleType.SCALED_ENTRY] = ExecutionStyleDefinition(
            style_type=ExecutionStyleType.SCALED_ENTRY,
            name="Scaled Entry",
            description="Entry split into multiple planned parts. Allows improving average price within predefined limits.",
            
            entry_config=EntryConfig(
                behavior=EntryBehavior.LADDER,
                single_entry=False,
                max_entries=3,
                entry_spacing_pct=0.5,  # 0.5% between entries
                entry_size_distribution=[0.5, 0.3, 0.2],  # 50%, 30%, 20%
                require_confirmation=True,
                allow_aggressive_entry=False
            ),
            
            exit_config=ExitConfig(
                behavior=ExitBehavior.FULL_AT_TARGET,
                partial_exits=[],
                time_exit_enabled=False,
                defensive_enabled=True,
                structure_break_exit=True,
                volatility_exit=True,
                trailing_enabled=False
            ),
            
            risk_level="MODERATE",
            max_position_adds=2,
            max_total_risk_pct=2.5,
            
            characteristics=[
                "Multiple entry points",
                "Planned ladder entries",
                "Can improve average price",
                "Requires more capital",
                "Complex execution"
            ],
            use_cases=[
                "Mean Reversion in range markets",
                "Trend pullback entries",
                "Support/Resistance zone entries",
                "Balanced profiles"
            ],
            warnings=[
                "Higher total exposure",
                "Can extend losses if wrong",
                "Requires strict risk caps",
                "Not for trending markets"
            ]
        )
        
        # ===========================================
        # PARTIAL_EXIT
        # ===========================================
        self._styles[ExecutionStyleType.PARTIAL_EXIT] = ExecutionStyleDefinition(
            style_type=ExecutionStyleType.PARTIAL_EXIT,
            name="Partial Exit",
            description="Scale out of position in parts. Take partial profits while keeping exposure for larger moves.",
            
            entry_config=EntryConfig(
                behavior=EntryBehavior.SINGLE,
                single_entry=True,
                max_entries=1,
                require_confirmation=True
            ),
            
            exit_config=ExitConfig(
                behavior=ExitBehavior.PARTIAL_SCALING,
                partial_exits=[
                    {"target_pct": 0.5, "size_pct": 0.5},   # Exit 50% at 50% of target
                    {"target_pct": 1.0, "size_pct": 0.5}    # Exit remaining at full target
                ],
                time_exit_enabled=False,
                defensive_enabled=True,
                structure_break_exit=True,
                trailing_enabled=True,
                trailing_activation_pct=0.5,
                trailing_distance_pct=0.3
            ),
            
            risk_level="MODERATE",
            max_position_adds=0,
            max_total_risk_pct=2.0,
            
            characteristics=[
                "Lock in partial profits early",
                "Keep exposure for runners",
                "Reduced risk after first exit",
                "Balance between profit and potential"
            ],
            use_cases=[
                "Trend following positions",
                "Breakout trades with uncertainty",
                "Volatile markets",
                "All profiles"
            ],
            warnings=[
                "May exit too early on strong moves",
                "Complexity in tracking partial positions"
            ]
        )
        
        # ===========================================
        # TIME_EXIT
        # ===========================================
        self._styles[ExecutionStyleType.TIME_EXIT] = ExecutionStyleDefinition(
            style_type=ExecutionStyleType.TIME_EXIT,
            name="Time Exit",
            description="Exit position if not profitable within specified time. Prevents holding dead trades.",
            
            entry_config=EntryConfig(
                behavior=EntryBehavior.SINGLE,
                single_entry=True,
                max_entries=1,
                require_confirmation=True
            ),
            
            exit_config=ExitConfig(
                behavior=ExitBehavior.TIME_BASED,
                partial_exits=[],
                time_exit_enabled=True,
                time_exit_bars=12,  # Exit after 12 bars if not profitable
                defensive_enabled=True,
                structure_break_exit=True
            ),
            
            risk_level="LOW",
            max_position_adds=0,
            max_total_risk_pct=1.5,
            
            characteristics=[
                "Time-based exit trigger",
                "Prevents holding stale trades",
                "Forces trade resolution",
                "Good for momentum trades"
            ],
            use_cases=[
                "Momentum Breakout trades",
                "News-driven entries",
                "Short-term setups",
                "Aggressive profiles"
            ],
            warnings=[
                "May exit before trade plays out",
                "Requires timeframe-appropriate settings"
            ]
        )
        
        # ===========================================
        # DEFENSIVE_EXIT
        # ===========================================
        self._styles[ExecutionStyleType.DEFENSIVE_EXIT] = ExecutionStyleDefinition(
            style_type=ExecutionStyleType.DEFENSIVE_EXIT,
            name="Defensive Exit",
            description="Rapid protective exit on adverse conditions. Prioritizes capital protection over profit.",
            
            entry_config=EntryConfig(
                behavior=EntryBehavior.SINGLE,
                single_entry=True,
                max_entries=1,
                require_confirmation=True
            ),
            
            exit_config=ExitConfig(
                behavior=ExitBehavior.DEFENSIVE,
                partial_exits=[],
                time_exit_enabled=False,
                defensive_enabled=True,
                structure_break_exit=True,
                volatility_exit=True,
                trailing_enabled=False
            ),
            
            risk_level="LOW",
            max_position_adds=0,
            max_total_risk_pct=1.0,
            
            characteristics=[
                "Fast protective exits",
                "Structure break triggers close",
                "Volatility spike triggers close",
                "Reduce-only mode available",
                "Capital preservation priority"
            ],
            use_cases=[
                "All strategies as safety layer",
                "High volatility environments",
                "Uncertain market conditions",
                "Conservative profiles"
            ],
            warnings=[
                "May exit prematurely on noise",
                "Requires proper trigger tuning"
            ]
        )
    
    def get_style(self, style_type: ExecutionStyleType) -> Optional[ExecutionStyleDefinition]:
        """Get style definition by type"""
        return self._styles.get(style_type)
    
    def get_all_styles(self) -> List[ExecutionStyleDefinition]:
        """Get all style definitions"""
        return list(self._styles.values())
    
    def get_entry_styles(self) -> List[ExecutionStyleDefinition]:
        """Get styles primarily focused on entry"""
        return [
            self._styles[ExecutionStyleType.CLEAN_ENTRY],
            self._styles[ExecutionStyleType.SCALED_ENTRY]
        ]
    
    def get_exit_styles(self) -> List[ExecutionStyleDefinition]:
        """Get styles primarily focused on exit"""
        return [
            self._styles[ExecutionStyleType.PARTIAL_EXIT],
            self._styles[ExecutionStyleType.TIME_EXIT],
            self._styles[ExecutionStyleType.DEFENSIVE_EXIT]
        ]


# Global singleton
style_registry = ExecutionStyleRegistry()
