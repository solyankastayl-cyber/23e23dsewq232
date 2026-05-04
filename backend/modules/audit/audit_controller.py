"""Audit Controller - P0.7

Координирует все audit repositories.
Предоставляет единую точку доступа для всей системы.
"""

from typing import Dict, Any
import logging
from .execution_audit_repository import ExecutionAuditRepository
from .decision_audit_repository import DecisionAuditRepository
from .strategy_action_repository import StrategyActionRepository
from .learning_audit_repository import LearningAuditRepository

logger = logging.getLogger(__name__)


class AuditController:
    """
    Audit Controller - Orchestrates all audit repositories
    
    Provides single entry point for system-wide auditing.
    """
    
    def __init__(self, motor_db):
        """
        Initialize all audit repositories with Motor async collections.
        
        Args:
            motor_db: Motor AsyncIOMotorDatabase instance
        """
        self.execution = ExecutionAuditRepository(motor_db.execution_audit)
        self.decision = DecisionAuditRepository(motor_db.decision_audit)
        self.strategy = StrategyActionRepository(motor_db.strategy_actions)
        self.learning = LearningAuditRepository(motor_db.learning_audit)
        
        logger.info("✅ AuditController initialized with all repositories")
    
    async def ensure_indexes(self):
        """Create indexes for all audit collections"""
        await self.execution.ensure_indexes()
        await self.decision.ensure_indexes()
        await self.strategy.ensure_indexes()
        await self.learning.ensure_indexes()
        logger.info("✅ All audit indexes created")
    
    async def get_summary(self) -> Dict[str, Any]:
        """
        Get summary statistics for all audit logs.
        
        Returns:
            Summary with counts for each audit type
        """
        return {
            "execution_events": await self.execution.count(),
            "decisions": await self.decision.count(),
            "strategy_actions": await self.strategy.count(),
            "learning_cycles": await self.learning.count()
        }
