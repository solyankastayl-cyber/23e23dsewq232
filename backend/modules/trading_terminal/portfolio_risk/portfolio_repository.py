"""
TT3 - Portfolio Repository
==========================
In-memory storage for portfolio capital state.
Later can be replaced with MongoDB/real account state.
"""


class PortfolioRepository:
    """Stores portfolio capital state"""
    
    def __init__(self):
        self.base_equity = 10000.0
        self.realized_pnl = 0.0
        self.daily_drawdown = 0.0
        self.max_drawdown = 0.0
        self.kill_switch = False
        self.active_guardrails: list = []
        self.block_reasons: list = []

    def get_base_equity(self) -> float:
        return self.base_equity

    def set_base_equity(self, value: float):
        self.base_equity = float(value)

    def get_realized_pnl(self) -> float:
        return self.realized_pnl

    def set_realized_pnl(self, value: float):
        self.realized_pnl = float(value)

    def get_daily_drawdown(self) -> float:
        return self.daily_drawdown

    def set_daily_drawdown(self, value: float):
        self.daily_drawdown = float(value)

    def get_max_drawdown(self) -> float:
        return self.max_drawdown

    def set_max_drawdown(self, value: float):
        self.max_drawdown = float(value)

    def get_kill_switch(self) -> bool:
        return self.kill_switch

    def set_kill_switch(self, value: bool):
        self.kill_switch = bool(value)

    def get_active_guardrails(self) -> list:
        return list(self.active_guardrails)

    def set_active_guardrails(self, items: list):
        self.active_guardrails = list(items or [])

    def add_guardrail(self, guardrail: str):
        if guardrail not in self.active_guardrails:
            self.active_guardrails.append(guardrail)

    def remove_guardrail(self, guardrail: str):
        if guardrail in self.active_guardrails:
            self.active_guardrails.remove(guardrail)

    def get_block_reasons(self) -> list:
        return list(self.block_reasons)

    def set_block_reasons(self, items: list):
        self.block_reasons = list(items or [])

    def add_block_reason(self, reason: str):
        if reason not in self.block_reasons:
            self.block_reasons.append(reason)

    def clear_block_reasons(self):
        self.block_reasons = []

    def reset(self):
        """Reset to defaults"""
        self.__init__()
