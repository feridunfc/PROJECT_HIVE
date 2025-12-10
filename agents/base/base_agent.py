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
    tools: List[str] = field(default_factory=list)
    capabilities: List[str] = field(default_factory=list)
    max_retries: int = 1
    timeout: int = 60


class BaseAgent(BaseNode):
    def __init__(self, config: AgentConfig) -> None:
        super().__init__(config.name)
        self.config = config
        self.router = LLMRouter()
        self.logger = get_logger(f"Agent.{config.name}")

    async def _build_user_prompt(self, state: NeuralState) -> str:
        raise NotImplementedError

    async def _process_response(self, response: Any, state: NeuralState) -> str:
        return getattr(response, "content", str(response))

    def _build_system_prompt(self, state: NeuralState) -> str:
        lines = [
            f"You are {self.config.name}, a {self.config.role}.",
            f"GOAL: {self.config.goal}",
        ]
        if self.config.backstory:
            lines.append(f"BACKSTORY: {self.config.backstory}")
        if self.config.capabilities:
            lines.append("CAPABILITIES:")
            lines.extend(f"- {c}" for c in self.config.capabilities)
        if self.config.constraints:
            lines.append("CONSTRAINTS:")
            lines.extend(f"- {c}" for c in self.config.constraints)
        if self.config.tools:
            lines.append(f"TOOLS AVAILABLE: {', '.join(self.config.tools)}")
        return "\n".join(lines)

    async def execute(self, state: NeuralState) -> NeuralState:
        self.logger.info(
            "Starting agent execution",
            extra={"run_id": state.run_id, "step": state.step},
        )

        system_msg = {"role": "system", "content": self._build_system_prompt(state)}
        user_content = await self._build_user_prompt(state)
        user_msg = {"role": "user", "content": user_content}

        messages: List[Dict[str, Any]] = [system_msg] + state.messages + [user_msg]
        response = await self.router.route(state, messages=messages)
        result_content = await self._process_response(response, state)

        state.add_message(
            role="assistant",
            content=result_content,
            name=self.config.name,
            metadata={
                "model": getattr(response, "model", None),
                "provider": getattr(response, "provider", None),
                "latency": getattr(response, "latency", None),
            },
        )

        self.logger.info(
            "Agent execution finished",
            extra={"run_id": state.run_id, "step": state.step},
        )
        return state

    async def run(self, state: NeuralState) -> NeuralState:
        return await self.execute(state)
