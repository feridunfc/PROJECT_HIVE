from __future__ import annotations
from dataclasses import dataclass
from typing import List, Sequence
from core.config import settings
from core.graph_engine.state import NeuralState
from core.graph_engine.nodes import BaseNode
from core.swarm.conversation import SwarmConversation
from core.swarm.consensus import ConsensusEngine, ConsensusStrategy
from core.utils.logger import get_logger

logger = get_logger("SwarmCoordinator")

@dataclass
class SwarmConfig:
    agents: Sequence[BaseNode]
    strategy: ConsensusStrategy = ConsensusStrategy.MAJORITY_VOTE
    max_rounds: int = settings.MAX_SWARM_ROUNDS

class SwarmCoordinator:
    def __init__(self, config: SwarmConfig) -> None:
        self.config = config
        self.conversation = SwarmConversation()
        self.consensus = ConsensusEngine()

    async def orchestrate(self, state: NeuralState) -> NeuralState:
        logger.info(
            "🐝 Swarm started",
            extra={
                "run_id": state.run_id,
                "agents": [a.name for a in self.config.agents],
                "strategy": self.config.strategy.value,
            },
        )

        for round_no in range(1, self.config.max_rounds + 1):
            logger.info("Swarm round", extra={"run_id": state.run_id, "round": round_no})
            votes: List[str] = []

            for agent in self.config.agents:
                # Agent'ı çalıştır
                state = await agent.execute(state)

                # Son mesajı al
                last_msg = state.messages[-1] if state.messages else {}
                content = last_msg.get("content", "")

                # Konuşma geçmişine ekle
                self.conversation.add(
                    role="assistant",
                    content=content,
                    agent_name=agent.name,
                    metadata={"round": round_no},
                )

                # Basit başarı kontrolü (Consensus için oy)
                lower = content.lower()
                if any(k in lower for k in ["tests passed", "syntax ok", "fixed", "success"]):
                    votes.append("success")
                else:
                    votes.append("pass")

            # Consensus Kontrolü
            if self.consensus.evaluate(self.config.strategy, votes):
                logger.info("✅ Swarm consensus reached", extra={"run_id": state.run_id})
                return state

        logger.warning("⚠️ Swarm max rounds reached without consensus", extra={"run_id": state.run_id})
        return state
