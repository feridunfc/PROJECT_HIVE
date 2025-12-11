import asyncio
from typing import Dict
from .state import NeuralState
from .node import BaseNode

class GraphEngine:
    def __init__(self):
        self.nodes: Dict[str, BaseNode] = {}
        self.edges: Dict[str, str] = {}
        self.start_node = None

    def register_node(self, node: BaseNode):
        self.nodes[node.name] = node

    def add_edge(self, from_node: str, to_node: str):
        self.edges[from_node] = to_node

    def set_start(self, name: str):
        self.start_node = name

    async def execute(self, state: NeuralState):
        current_name = self.start_node
        print(f"🚀 Execution Started: {state.goal}")

        while current_name:
            node = self.nodes.get(current_name)
            if not node: break

            print(f"⚙️  Running Node: {current_name}")
            state = await node.run(state)

            current_name = self.edges.get(current_name)

        print("✅ Execution Finished")
        return state
