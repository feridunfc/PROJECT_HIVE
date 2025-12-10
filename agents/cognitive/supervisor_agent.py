from __future__ import annotations

from agents.base.base_agent import AgentConfig, BaseAgent
from core.graph_engine.state import NeuralState


class SupervisorAgent(BaseAgent):
    def __init__(self) -> None:
        config = AgentConfig(
            name="Supervisor",
            role="orchestrator",
            goal="Break the overall goal into concrete, sequential development steps.",
            constraints=[
                "Keep steps between 3 and 7",
                "Each step should be unambiguous",
            ],
        )
        super().__init__(config)

    async def _build_user_prompt(self, state: NeuralState) -> str:
        return f"""User goal: {state.goal}

Produce a numbered list of development steps to achieve this goal.
Each step should be one short sentence."""

    async def _process_response(self, response, state: NeuralState) -> str:
        plan = response.content.strip()
        state.artifacts["plan"] = plan
        return plan
