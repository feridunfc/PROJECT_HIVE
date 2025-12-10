from __future__ import annotations

from core.graph_engine.state import NeuralState
from core.swarm.coordinator import SwarmCoordinator, SwarmConfig
from agents.cognitive.supervisor_agent import SupervisorAgent
from agents.cognitive.architect_agent import ArchitectAgent
from agents.technical.dev_agent import DevAgent
from agents.technical.tester_agent import TesterAgent
from agents.technical.debugger_agent import DebuggerAgent
from core.config import settings


class T0VelocityPipeline:
    """Rapid prototyping pipeline.

    Flow: Supervisor -> Architect -> Dev -> Tester -> Debugger
    """

    def __init__(self) -> None:
        self.agents = [
            SupervisorAgent(),
            ArchitectAgent(),
            DevAgent(),
            TesterAgent(),
            DebuggerAgent(),
        ]

        self.swarm_config = SwarmConfig(
            agents=self.agents,
            max_rounds=settings.MAX_SWARM_ROUNDS,
        )
        self.coordinator = SwarmCoordinator(self.swarm_config)

    async def run(self, goal: str) -> NeuralState:
        state = NeuralState(goal=goal, mode="t0")
        final_state = await self.coordinator.orchestrate(state)
        return final_state
