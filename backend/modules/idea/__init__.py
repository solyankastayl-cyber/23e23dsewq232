"""
Idea Module — Analysis-first idea management
============================================

Components:
  - IdeaEngineV1 — Create, update, track ideas
  - IdeaRepository — Data persistence
  - Models — Data structures

Usage:
  from modules.idea import get_idea_engine_v1
  
  engine = get_idea_engine_v1()
  result = engine.create_from_analysis(
      asset="BTCUSDT",
      timeframe="1D",
      decision=decision,
      scenarios=scenarios,
      explanation=explanation,
  )
"""

from .models import (
    Idea,
    IdeaVersion,
    IdeaStatus,
    Favorite,
    IdeaUpdateRecommendation,
)

from .repository import (
    IdeaRepository,
    get_idea_repository,
)

from .idea_engine_v1 import (
    IdeaEngineV1,
    get_idea_engine_v1,
    idea_engine_v1,
)

__all__ = [
    # Models
    "Idea",
    "IdeaVersion",
    "IdeaStatus",
    "Favorite",
    "IdeaUpdateRecommendation",
    # Repository
    "IdeaRepository",
    "get_idea_repository",
    # Engine
    "IdeaEngineV1",
    "get_idea_engine_v1",
    "idea_engine_v1",
]
