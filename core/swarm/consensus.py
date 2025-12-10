from __future__ import annotations
from enum import Enum
from typing import List

from core.utils.logger import get_logger

logger = get_logger("ConsensusEngine")


class ConsensusStrategy(Enum):
    MAJORITY_VOTE = "majority"
    UNANIMITY = "unanimity"
    MANAGER_DECIDES = "manager"


class ConsensusEngine:
    @staticmethod
    def evaluate(strategy: ConsensusStrategy, votes: List[str]) -> bool:
        if not votes:
            return False

        total = len(votes)
        positive = votes.count("approve") + votes.count("pass") + votes.count("success")

        logger.info(
            "🗳️ Consensus Check",
            extra={"positive": positive, "total": total, "strategy": strategy.value},
        )

        if strategy == ConsensusStrategy.MAJORITY_VOTE:
            return (positive / total) > 0.5
        elif strategy == ConsensusStrategy.UNANIMITY:
            return positive == total

        return (positive / total) > 0.5
