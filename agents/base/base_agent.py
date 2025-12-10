from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List
from core.graph_engine.nodes import BaseNode
from core.graph_engine.state import NeuralState
from core.llm.router import LLMRouter
from core.utils.logger import get_logger

@dataclass
class AgentConfig:
    name: str
    role: str
    goal: str
    backstory: str = ""
    constraints: List[str] = field(default_factory=list)
    examples: List[str] = field(default_factory=list)

class BaseAgent(BaseNode):
    """
    Enterprise base agent:
    - AgentConfig tabanlı
    - System + user prompt üretir
    - LLMRouter kullanır
    """

    def __init__(self, config: AgentConfig) -> None:
        super().__init__(config.name)
        self.config = config
        self.router = LLMRouter()
        self.logger = get_logger(f"Agent.{config.name}")

    # --- Overridable hooks ---
    async def _build_user_prompt(self, state: NeuralState) -> str:
        """Alt sınıflar bunu implemente etmeli."""
        raise NotImplementedError

    async def _process_response(self, response: Any, state: NeuralState) -> str:
        # Default: cevabı direkt geçir
        return getattr(response, "content", str(response))

    # --- Internal helpers ---
    def _build_system_prompt(self, state: NeuralState) -> str:
        lines = [
            f"You are {self.config.name}, a {self.config.role}.",
            f"GOAL: {self.config.goal}",
        ]
        if self.config.backstory:
            lines.append(f"BACKSTORY: {self.config.backstory}")
        if self.config.constraints:
            lines.append("CONSTRAINTS:")
            lines.extend(f"- {c}" for c in self.config.constraints)
        return "\n".join(lines)

    # --- Main execution ---
    async def execute(self, state: NeuralState) -> NeuralState:
        self.logger.info(
            "Starting agent execution",
            extra={"run_id": state.run_id, "step": state.step},
        )

        system_msg = {
            "role": "system",
            "content": self._build_system_prompt(state),
        }

        # User prompt'u oluştur
        user_content = await self._build_user_prompt(state)
        user_msg = {
            "role": "user",
            "content": user_content,
        }

        messages: List[Dict[str, Any]] = [system_msg] + state.messages + [user_msg]

        # LLM call
        response = await self.router.route(state, messages=messages)

        # Agent-specific processing
        result_content = await self._process_response(response, state)

        # State update
        state.add_message(
            role="assistant",
            content=result_content,
            name=self.config.name,
            metadata={
                "model": response.model,
                "provider": response.provider,
                "latency": response.latency,
            },
        )

        self.logger.info(
            "Agent execution finished",
            extra={"run_id": state.run_id, "step": state.step},
        )
        return state

    # Eski interface uyumluluğu için:
    async def run(self, state: NeuralState) -> NeuralState:
        return await self.execute(state)
