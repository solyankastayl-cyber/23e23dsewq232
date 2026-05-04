"""
Research Reporting Module (S2.5)
================================

Generates comprehensive research reports that bridge
Research Lab (S2) with Capital Allocation (S3).

Components:
- report_types.py: Data models for reports
- report_generator.py: Main report generation service
- report_formatter.py: Formatting utilities
- report_routes.py: API endpoints
"""

from .report_types import (
    ResearchReport,
    LeaderboardEntry,
    WalkForwardAnalysis,
    StrategyDiagnostics,
    AllocationReadiness,
    ReportWarning,
    WarningLevel
)

from .report_generator import (
    ReportGenerator,
    report_generator
)

from .report_routes import router as report_router


__all__ = [
    # Types
    "ResearchReport",
    "LeaderboardEntry",
    "WalkForwardAnalysis",
    "StrategyDiagnostics",
    "AllocationReadiness",
    "ReportWarning",
    "WarningLevel",
    
    # Generator
    "ReportGenerator",
    "report_generator",
    
    # Routes
    "report_router"
]


print("[Reporting] S2.5 Research Report module loaded")
