"""
Idea Auto-Update Worker
========================

Background worker that:
1. Auto-updates active ideas every 5-10 min
2. Auto-resolves ideas based on price breakouts

Rules:
- update: if pattern or lifecycle changed → create new version
- resolve: price > top → success_up | price < bottom → invalidated
"""

import os
import sys
import time
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
import threading

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from modules.ta_engine.ideas.idea_service import IdeaService, get_idea_service
from modules.ta_engine.setup.setup_builder import get_setup_builder

logger = logging.getLogger(__name__)

# Config
UPDATE_INTERVAL_SECONDS = 300  # 5 minutes
RESOLVE_CHECK_INTERVAL_SECONDS = 60  # 1 minute


class IdeaAutoWorker:
    """Background worker for auto-updating and resolving ideas."""
    
    def __init__(self):
        self.service: Optional[IdeaService] = None
        self.setup_builder = None
        self._running = False
        self._update_thread: Optional[threading.Thread] = None
        self._resolve_thread: Optional[threading.Thread] = None
    
    def start(self):
        """Start background workers."""
        if self._running:
            logger.info("Worker already running")
            return
        
        self._running = True
        self.service = get_idea_service()
        self.setup_builder = get_setup_builder()
        
        # Start update thread
        self._update_thread = threading.Thread(target=self._update_loop, daemon=True)
        self._update_thread.start()
        
        # Start resolve thread
        self._resolve_thread = threading.Thread(target=self._resolve_loop, daemon=True)
        self._resolve_thread.start()
        
        logger.info("Idea auto-worker started")
    
    def stop(self):
        """Stop background workers."""
        self._running = False
        logger.info("Idea auto-worker stopped")
    
    def _update_loop(self):
        """Main update loop — runs every 5 min."""
        while self._running:
            try:
                self._auto_update_ideas()
            except Exception as e:
                logger.error(f"Auto-update error: {e}")
            
            time.sleep(UPDATE_INTERVAL_SECONDS)
    
    def _resolve_loop(self):
        """Main resolve loop — runs every 1 min."""
        while self._running:
            try:
                self._auto_resolve_ideas()
            except Exception as e:
                logger.error(f"Auto-resolve error: {e}")
            
            time.sleep(RESOLVE_CHECK_INTERVAL_SECONDS)
    
    def _auto_update_ideas(self):
        """
        Auto-update active ideas.
        
        For each active idea:
        1. Get fresh TA snapshot
        2. Compare with latest version
        3. If pattern or lifecycle changed → add new version
        """
        if not self.service:
            return
        
        active_ideas = self.service.list_ideas(status="active", limit=100)
        updated_count = 0
        
        for idea in active_ideas:
            try:
                # Get latest version
                latest = idea.versions[-1] if idea.versions else None
                if not latest:
                    continue
                
                latest_snapshot = latest.setup_snapshot or {}
                
                # Get fresh TA snapshot
                result = self.setup_builder.build(idea.asset, idea.timeframe)
                
                # Extract pattern info
                new_pattern = None
                new_lifecycle = None
                
                if result.top_setup:
                    new_pattern = result.top_setup.setup_type.value
                elif result.primary_pattern:
                    new_pattern = result.primary_pattern.get("type")
                
                # Compare
                old_pattern = latest_snapshot.get("pattern")
                old_lifecycle = latest_snapshot.get("lifecycle")
                
                if new_pattern != old_pattern or new_lifecycle != old_lifecycle:
                    # Create new version
                    new_snapshot = {
                        "pattern": new_pattern or old_pattern,
                        "lifecycle": new_lifecycle or old_lifecycle,
                        "probability": {
                            "up": result.bullish_prob if hasattr(result, 'bullish_prob') else 0.5,
                            "down": result.bearish_prob if hasattr(result, 'bearish_prob') else 0.5,
                        },
                        "levels": latest_snapshot.get("levels", {}),
                        "interpretation": self._auto_interpret(
                            new_pattern,
                            result.structure_context.get("market_state") if hasattr(result, 'structure_context') else None,
                            new_lifecycle
                        ),
                    }
                    
                    self.service.add_version(idea.idea_id, new_snapshot)
                    updated_count += 1
                    logger.info(f"Updated idea {idea.idea_id}: {old_pattern} → {new_pattern}")
            
            except Exception as e:
                logger.warning(f"Failed to update idea {idea.idea_id}: {e}")
                continue
        
        if updated_count > 0:
            logger.info(f"Auto-updated {updated_count} ideas")
    
    def _auto_resolve_ideas(self):
        """
        Auto-resolve ideas based on price breakouts.
        
        Rules:
        - price > levels.top → success_up, correct
        - price < levels.bottom → invalidated, wrong
        """
        if not self.service:
            return
        
        active_ideas = self.service.list_ideas(status="active", limit=100)
        resolved_count = 0
        
        for idea in active_ideas:
            try:
                # Get latest version
                latest = idea.versions[-1] if idea.versions else None
                if not latest:
                    continue
                
                snapshot = latest.setup_snapshot or {}
                levels = snapshot.get("levels", {})
                
                top = levels.get("top")
                bottom = levels.get("bottom")
                
                if not top or not bottom:
                    continue
                
                # Get current price
                current_price = self._get_current_price(idea.asset)
                if not current_price:
                    continue
                
                # Check for breakout
                if current_price > top:
                    # Success up
                    self.service.resolve_idea(
                        idea_id=idea.idea_id,
                        result="correct",
                        outcome="success_up",
                        result_price=current_price,
                        pnl_pct=((current_price - top) / top) * 100,
                    )
                    resolved_count += 1
                    logger.info(f"Resolved idea {idea.idea_id}: success_up at {current_price}")
                
                elif current_price < bottom:
                    # Invalidated
                    self.service.resolve_idea(
                        idea_id=idea.idea_id,
                        result="wrong",
                        outcome="invalidated",
                        result_price=current_price,
                        pnl_pct=((current_price - bottom) / bottom) * 100,
                    )
                    resolved_count += 1
                    logger.info(f"Resolved idea {idea.idea_id}: invalidated at {current_price}")
            
            except Exception as e:
                logger.warning(f"Failed to resolve idea {idea.idea_id}: {e}")
                continue
        
        if resolved_count > 0:
            logger.info(f"Auto-resolved {resolved_count} ideas")
    
    def _get_current_price(self, asset: str) -> Optional[float]:
        """Get current price for asset."""
        try:
            import requests
            response = requests.get(
                f"https://api.binance.com/api/v3/ticker/price?symbol={asset}USDT",
                timeout=5
            )
            if response.ok:
                return float(response.json()["price"])
        except:
            pass
        return None
    
    def _auto_interpret(self, pattern: str, market_state: str, lifecycle: str) -> str:
        """Rule-based auto-interpretation (no LLM)."""
        if lifecycle == "confirmed_up":
            return "Breakout confirmed ↑"
        if lifecycle == "confirmed_down":
            return "Breakdown confirmed ↓"
        if market_state in ("compression", "consolidating"):
            return "Market was consolidating"
        if market_state == "trending_up":
            return "Uptrend in progress"
        if market_state == "trending_down":
            return "Downtrend in progress"
        if pattern in ("triangle", "wedge"):
            return "Converging price action"
        if pattern in ("rectangle", "range"):
            return "Horizontal consolidation"
        return "Neutral structure"


# Singleton instance
_worker_instance: Optional[IdeaAutoWorker] = None


def get_idea_worker() -> IdeaAutoWorker:
    """Get singleton worker instance."""
    global _worker_instance
    if _worker_instance is None:
        _worker_instance = IdeaAutoWorker()
    return _worker_instance


def start_auto_worker():
    """Start the auto-worker (call from server startup)."""
    worker = get_idea_worker()
    worker.start()


def stop_auto_worker():
    """Stop the auto-worker."""
    worker = get_idea_worker()
    worker.stop()
