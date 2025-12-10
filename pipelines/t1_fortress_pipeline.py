from __future__ import annotations
from pathlib import Path
from core.config import settings
from core.graph_engine.state import NeuralState
from core.policy.policy_engine import PolicyEngine
from core.swarm.coordinator import SwarmCoordinator, SwarmConfig
from core.swarm.consensus import ConsensusStrategy

# Agentların mevcut olduğunu varsayıyoruz, yoksa importlar hata verir.
# Bu örnek için importları varsayılan yerlerden yapıyoruz.
from agents.cognitive.supervisor_agent import SupervisorAgent
from agents.cognitive.architect_agent import ArchitectAgent
from agents.technical.dev_agent import DevAgent
from agents.technical.tester_agent import TesterAgent
from agents.technical.debugger_agent import DebuggerAgent

class T1FortressPipeline:
    def __init__(self) -> None:
        self.policy = PolicyEngine()

        # Agentları konfigüre et (Gerekirse burada AgentConfig kullanılarak init edilir)
        # Örnek: self.agents = [SupervisorAgent(AgentConfig(...)), ...]
        # Şimdilik mevcut classların uyumlu olduğunu varsayıyoruz (BaseAgent fix'i sayesinde)
        self.agents = [
            SupervisorAgent(),
            ArchitectAgent(),
            DevAgent(),
            TesterAgent(),
            DebuggerAgent(),
        ]

        self.swarm_config = SwarmConfig(
            agents=self.agents,
            strategy=ConsensusStrategy.MAJORITY_VOTE,
            max_rounds=settings.MAX_SWARM_ROUNDS,
        )
        self.coordinator = SwarmCoordinator(self.swarm_config)

    async def run(self, goal: str) -> NeuralState:
        # T1 modu ile başlat
        state = NeuralState(goal=goal, mode="t1")

        # 1. Swarm Execution
        state = await self.coordinator.orchestrate(state)

        # 2. Policy Check (Fortress Layer)
        last_msg = state.messages[-1]["content"] if state.messages else ""

        # Kod artifact'ini kontrol et
        code_map = state.artifacts.get("generated_code", {})
        for filename, code in code_map.items():
            violations = self.policy.check_code(code, {"goal": goal})
            if violations:
                for v in violations:
                    state.add_error("policy_violation", v.message, {"severity": v.severity.value})

        return state
