import asyncio

from core.graph_engine.state import NeuralState
from core.graph_engine.engine import NeuralGraphEngine
from core.graph_engine.node import BaseNode


class HelloNode(BaseNode):
    def __init__(self) -> None:
        super().__init__("hello")

    async def execute(self, state: NeuralState) -> NeuralState:
        state.add_message(role="system", content="Hello from graph engine", agent="hello_node")
        return state


async def main() -> None:
    state = NeuralState(goal="Demo sprint 0 graph")

    engine = NeuralGraphEngine()
    engine.add_node(HelloNode())

    final_state = await engine.execute(state)
    print("Messages:")
    for m in final_state.messages:
        print(f"- [{m.role}] {m.agent}: {m.content}")


if __name__ == "__main__":
    asyncio.run(main())
