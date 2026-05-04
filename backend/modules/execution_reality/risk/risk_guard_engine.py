"""Risk Guard Engine

Преобразует health status в действия (защитные меры).
"""

import logging
from typing import List

logger = logging.getLogger(__name__)


class RiskGuardEngine:
    """Движок защитных мер"""

    def evaluate(self, health_status: str) -> List[str]:
        """
        Определить actions по health status.
        
        Args:
            health_status: "HEALTHY" | "WARNING" | "CRITICAL"
        
        Returns:
            Список actions: ["HARD_STOP", "CLOSE_ALL", "REDUCE_SIZE", "FREEZE_WEAK_STRATEGIES"]
        """
        actions = []

        if health_status == "CRITICAL":
            # Критическое состояние: жёсткая остановка + закрытие всего
            actions.append("HARD_STOP")
            actions.append("CLOSE_ALL")
            logger.critical("🚨 CRITICAL health status → actions: HARD_STOP, CLOSE_ALL")

        elif health_status == "WARNING":
            # Предупреждение: снижение риска
            actions.append("REDUCE_SIZE")
            actions.append("FREEZE_WEAK_STRATEGIES")
            logger.warning("⚠️ WARNING health status → actions: REDUCE_SIZE, FREEZE_WEAK_STRATEGIES")

        else:  # HEALTHY
            # Нет действий
            pass

        return actions
