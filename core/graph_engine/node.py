from abc import ABC, abstractmethod
from .state import NeuralState

class BaseNode(ABC):
    def __init__(self, name: str):
        self.name = name

    @abstractmethod
    async def run(self, state: NeuralState) -> NeuralState:
        pass
