from __future__ import annotations

from core.config import settings
from core.graph_engine.state import NeuralState
from core.policy.policy_engine import PolicyEngine
from core.swarm.coordinator import SwarmCoordinator, SwarmConfig
from core.swarm.consensus import ConsensusStrategy

from agents.cognitive.supervisor_agent import SupervisorAgent
from agents.cognitive.architect_agent import ArchitectAgent
from agents.technical.dev_agent import DevAgent
from agents.technical.tester_agent import TesterAgent
from agents.technical.debugger_agent import DebuggerAgent


class T1FortressPipeline:
    """Security-focused, enterprise-grade pipeline."""

    def __init__(self) -> None:
        self.policy = PolicyEngine()

        # Yeni (doğru):
        from pathlib import Path

        self.agents = [
            SupervisorAgent(),
            ArchitectAgent(),
            DevAgent(output_dir=Path("output")),  # ← Path objesi
            TesterAgent(project_root=Path("output")),  # ← Path objesi
            DebuggerAgent(),
        ]

        self.swarm_config = SwarmConfig(
            agents=self.agents,
            strategy=ConsensusStrategy.MAJORITY_VOTE,
            max_rounds=settings.MAX_SWARM_ROUNDS,
        )
        self.coordinator = SwarmCoordinator(self.swarm_config)

    async def run(self, goal: str) -> NeuralState:
        state = NeuralState(goal=goal, mode="t1")

        state = await self.coordinator.orchestrate(state)

        code_map = state.artifacts.get("generated_code", {})
        if isinstance(code_map, dict):
            for filename, code in code_map.items():
                violations = self.policy.check_code(
                    str(code), {"goal": goal, "filename": filename}
                )
                if violations:
                    for v in violations:
                        state.add_error(
                            "policy_violation",
                            v.message,
                            {"severity": v.severity.value, "code": v.code},
                        )

        return state
