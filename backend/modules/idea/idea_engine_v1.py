"""
Idea Engine V1 — Create, Update, Track Ideas
============================================

Core functions:
  - Create idea from analysis
  - Update idea (creates new version)
  - Track idea status
  - Check for update recommendations

This is the bridge from:
  analysis → idea → history
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .models import IdeaStatus, IdeaUpdateRecommendation
from .repository import IdeaRepository, get_idea_repository


class IdeaEngineV1:
    """
    Idea management engine.
    
    Converts analysis results into persistent, versioned ideas.
    """

    def __init__(self, repo: Optional[IdeaRepository] = None):
        """
        Initialize engine.
        
        Args:
            repo: IdeaRepository instance (uses singleton if None)
        """
        self.repo = repo or get_idea_repository()

    # ---------------------------------------------------------
    # CREATE
    # ---------------------------------------------------------
    def create_from_analysis(
        self,
        asset: str,
        timeframe: str,
        decision: Dict[str, Any],
        scenarios: List[Dict[str, Any]],
        explanation: Dict[str, Any],
        user_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Create new idea from analysis results.
        
        Args:
            asset: Asset symbol (e.g., "BTCUSDT")
            timeframe: Timeframe (e.g., "1D")
            decision: Decision Engine V2 output
            scenarios: Scenario Engine V3 output (list)
            explanation: Explanation Engine V1 output
            user_id: Optional user ID
        
        Returns:
            {"idea": {...}, "version": {...}}
        """
        # Create idea container
        idea = self.repo.create_idea(
            asset=asset,
            timeframe=timeframe,
            user_id=user_id,
        )
        
        # Build version data from analysis
        version_data = self._build_version_data(decision, scenarios, explanation)
        
        # Create first version
        version = self.repo.create_version(idea["id"], version_data)
        
        return {
            "idea": idea,
            "version": version,
        }

    # ---------------------------------------------------------
    # UPDATE
    # ---------------------------------------------------------
    def update_idea(
        self,
        idea_id: str,
        decision: Dict[str, Any],
        scenarios: List[Dict[str, Any]],
        explanation: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Update idea with new analysis (creates new version).
        
        Old version is preserved. New version links to previous.
        
        Args:
            idea_id: Existing idea ID
            decision: New Decision Engine V2 output
            scenarios: New Scenario Engine V3 output
            explanation: New Explanation Engine V1 output
        
        Returns:
            New version dict
        """
        # Build version data
        version_data = self._build_version_data(decision, scenarios, explanation)
        
        # Create new version (preserves old)
        version = self.repo.create_version(idea_id, version_data)
        
        return version

    # ---------------------------------------------------------
    # STATUS TRACKING
    # ---------------------------------------------------------
    def update_status(
        self,
        idea_id: str,
        current_price: float,
        trigger_price: Optional[float] = None,
        invalidation_price: Optional[float] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Update idea status based on current price.
        
        Simple logic:
          - Price at trigger → PLAYING_OUT
          - Price at invalidation → INVALIDATED
        
        Args:
            idea_id: Idea ID
            current_price: Current market price
            trigger_price: Trigger level (optional, extracted from version if None)
            invalidation_price: Invalidation level (optional)
        
        Returns:
            Updated version dict or None
        """
        version = self.repo.get_current_version(idea_id)
        if not version:
            return None
        
        current_status = version.get("status", IdeaStatus.ACTIVE.value)
        
        # Skip if already terminal
        if current_status in [IdeaStatus.VALIDATED.value, IdeaStatus.INVALIDATED.value]:
            return version
        
        # Parse trigger/invalidation from version if not provided
        # (In real implementation, would need price extraction from text)
        # For now, just check status based on simple rules
        
        new_status = self._determine_status(
            current_status=current_status,
            bias=version.get("bias", "neutral"),
            confidence=version.get("confidence", 0.5),
        )
        
        if new_status != current_status:
            return self.repo.update_version_status(version["id"], IdeaStatus(new_status))
        
        return version

    def check_update_recommendation(
        self,
        idea_id: str,
        new_decision: Dict[str, Any],
    ) -> Optional[IdeaUpdateRecommendation]:
        """
        Check if idea needs update based on new analysis.
        
        Compares current version with new decision to detect:
          - Bias shift
          - Significant confidence change
          - Structure change
        
        Args:
            idea_id: Idea ID
            new_decision: Fresh decision from analysis
        
        Returns:
            IdeaUpdateRecommendation or None if no update needed
        """
        version = self.repo.get_current_version(idea_id)
        if not version:
            return None
        
        old_bias = version.get("bias", "neutral")
        new_bias = new_decision.get("bias", "neutral")
        
        old_confidence = version.get("confidence", 0.5)
        new_confidence = new_decision.get("confidence", 0.5)
        
        # Check for bias shift
        if old_bias != new_bias:
            return IdeaUpdateRecommendation(
                idea_id=idea_id,
                reason="bias_shifted",
                urgency="high",
                details=f"Bias changed from {old_bias} to {new_bias}",
            )
        
        # Check for significant confidence change
        if abs(new_confidence - old_confidence) >= 0.2:
            urgency = "high" if abs(new_confidence - old_confidence) >= 0.3 else "medium"
            return IdeaUpdateRecommendation(
                idea_id=idea_id,
                reason="confidence_changed",
                urgency=urgency,
                details=f"Confidence changed from {old_confidence:.2f} to {new_confidence:.2f}",
            )
        
        return None

    # ---------------------------------------------------------
    # QUERIES
    # ---------------------------------------------------------
    def get_idea_with_history(self, idea_id: str) -> Optional[Dict[str, Any]]:
        """
        Get idea with full version history.
        
        Returns:
            {
                "idea": {...},
                "current_version": {...},
                "version_history": [...]
            }
        """
        idea = self.repo.get_idea(idea_id)
        if not idea:
            return None
        
        current_version = self.repo.get_current_version(idea_id)
        version_history = self.repo.get_versions_by_idea(idea_id)
        
        return {
            "idea": idea,
            "current_version": current_version,
            "version_history": version_history,
        }

    def get_user_ideas(
        self,
        user_id: str,
        include_current_version: bool = True,
    ) -> List[Dict[str, Any]]:
        """Get all ideas for a user."""
        ideas = self.repo.get_ideas_by_user(user_id)
        
        if include_current_version:
            for idea in ideas:
                idea["current_version"] = self.repo.get_current_version(idea["id"])
        
        return ideas

    def get_asset_ideas(
        self,
        asset: str,
        include_current_version: bool = True,
    ) -> List[Dict[str, Any]]:
        """Get all ideas for an asset."""
        ideas = self.repo.get_ideas_by_asset(asset)
        
        if include_current_version:
            for idea in ideas:
                idea["current_version"] = self.repo.get_current_version(idea["id"])
        
        return ideas

    # ---------------------------------------------------------
    # HELPERS
    # ---------------------------------------------------------
    def _build_version_data(
        self,
        decision: Dict[str, Any],
        scenarios: List[Dict[str, Any]],
        explanation: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Build version data from analysis components."""
        primary = scenarios[0] if scenarios else {}
        
        return {
            # Decision snapshot
            "bias": decision.get("bias", "neutral"),
            "confidence": decision.get("confidence", 0.5),
            "strength": decision.get("strength", "medium"),
            "tradeability": decision.get("tradeability", "conditional"),
            
            # Scenario snapshot
            "scenario_direction": primary.get("direction", "neutral"),
            "scenario_probability": primary.get("probability", 0.5),
            "scenario_title": primary.get("title", ""),
            "scenario_summary": primary.get("summary", ""),
            
            # Key levels
            "trigger": primary.get("trigger", ""),
            "invalidation": primary.get("invalidation", ""),
            
            # Explanation snapshot
            "explanation_summary": explanation.get("summary", ""),
            "explanation_reasoning": explanation.get("technical_reasoning", ""),
            "explanation_risks": explanation.get("risk_factors", ""),
            "short_text": explanation.get("short_text", ""),
        }

    def _determine_status(
        self,
        current_status: str,
        bias: str,
        confidence: float,
    ) -> str:
        """Determine status based on simple rules."""
        # This is simplified — real implementation would use price data
        if current_status == IdeaStatus.ACTIVE.value:
            # Could transition to PLAYING_OUT based on external signals
            return IdeaStatus.ACTIVE.value
        
        return current_status


# ---------------------------------------------------------
# Factory / Singleton
# ---------------------------------------------------------
_idea_engine_v1_instance: Optional[IdeaEngineV1] = None


def get_idea_engine_v1(repo: Optional[IdeaRepository] = None) -> IdeaEngineV1:
    """Get singleton instance of IdeaEngineV1."""
    global _idea_engine_v1_instance
    if _idea_engine_v1_instance is None:
        _idea_engine_v1_instance = IdeaEngineV1(repo)
    return _idea_engine_v1_instance


# Direct import singleton
idea_engine_v1 = IdeaEngineV1()
