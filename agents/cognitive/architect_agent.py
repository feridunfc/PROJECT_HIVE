from __future__ import annotations

from agents.base.base_agent import AgentConfig, BaseAgent
from core.graph_engine.state import NeuralState


class ArchitectAgent(BaseAgent):
    def __init__(self) -> None:
        config = AgentConfig(
            name="Architect",
            role="software architect",
            goal="Design a minimal but extensible file and component layout.",
            constraints=[
                "Prefer small, focused modules",
                "Focus on clarity over cleverness",
            ],
        )
        super().__init__(config)

    async def _build_user_prompt(self, state: NeuralState) -> str:
        plan = state.artifacts.get("plan", "")
        return f"""Overall goal: {state.goal}

High-level plan:
{plan}

Design a minimal architecture for this. 
Return a markdown list of files and their responsibilities."""

    async def _process_response(self, response, state: NeuralState) -> str:
        manifest = response.content.strip()
        state.artifacts["manifest"] = manifest
        return manifest
