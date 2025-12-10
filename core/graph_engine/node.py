from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional

from core.graph_engine.state import NeuralState


class BaseNode(ABC):
    """Graph üzerindeki her bir adım için temel node sınıfı."""

    def __init__(self, name: str) -> None:
        self.name = name

    @abstractmethod
    async def execute(self, state: NeuralState) -> NeuralState:  # pragma: no cover
        ...

    async def __call__(self, state: NeuralState) -> NeuralState:
        return await self.execute(state)
