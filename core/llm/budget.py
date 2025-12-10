from __future__ import annotations
from typing import Dict
from core.graph_engine.state import NeuralState
from core.utils.logger import get_logger

logger = get_logger("BudgetManager")

class BudgetManager:
    @staticmethod
    def estimate_cost(provider: str, model: str, usage: Dict) -> float:
        # Basit token maliyet hesabı (Stub)
        total_tokens = usage.get("total_tokens", 0)
        if provider == "openai":
            return total_tokens * 0.000002
        return 0.0

    @classmethod
    def apply_cost(cls, state: NeuralState, provider: str, model: str, usage: Dict) -> None:
        cost = cls.estimate_cost(provider, model, usage)
        state.update_budget(cost)
        logger.info("Budget updated", extra={"used": state.budget_used, "delta": cost})
