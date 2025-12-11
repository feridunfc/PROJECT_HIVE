# pipelines/t1_fortress_pipeline.py
from __future__ import annotations
from core.config import settings
from core.graph_engine.state import NeuralState
from core.policy.policy_engine import PolicyEngine
from core.swarm.coordinator import SwarmCoordinator, SwarmConfig
from core.swarm.consensus import ConsensusStrategy

# Agent Imports
from agents.cognitive.supervisor_agent import SupervisorAgent
from agents.cognitive.architect_agent import ArchitectAgent
from agents.technical.dev_agent import DevAgent
from agents.technical.tester_agent import TesterAgent
from agents.technical.debugger_agent import DebuggerAgent


class T1FortressPipeline:
    """
    Fortress pipeline:
    - T0 benzeri flow
    - Policy + Budget + Self-Healing entegrasyonu
    """

    def __init__(self) -> None:
        self.policy = PolicyEngine()

        # DÜZELTME: Agent'lar artık __init__ parametresi almıyor.
        # Konfigürasyonları kendi içlerinde (AgentConfig) yönetiliyor.
        # Path objeleri ve argümanlar kaldırıldı.
        self.agents = [
            SupervisorAgent(),
            ArchitectAgent(),
            DevAgent(),  # <-- Argüman YOK
            TesterAgent(),  # <-- Argüman YOK
            DebuggerAgent(),  # <-- Argüman YOK
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

        # 1) Swarm ile çözüm üret
        state = await self.coordinator.orchestrate(state)

        # 2) Policy check (Fortress Layer)
        last_msg = state.messages[-1]["content"] if state.messages else ""

        # LLM Çıktısını kontrol et
        violations = self.policy.check_llm_output(last_msg, {"goal": goal})

        # Kod Artifact'lerini kontrol et
        code_map = state.artifacts.get("generated_code", {})
        if isinstance(code_map, dict):
            for filename, code in code_map.items():
                # Policy Engine'e string olarak kod gönderiyoruz
                violations.extend(self.policy.check_code(str(code), {"goal": goal}))

        # İhlalleri State'e ekle
        if violations:
            for v in violations:
                state.add_error(
                    error_type=v.code,
                    message=v.message,
                    details={"severity": v.severity.value, **(v.details or {})},
                )

        return state