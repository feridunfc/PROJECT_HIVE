import asyncio
from pathlib import Path

from core.graph_engine.state import NeuralState
from core.graph_engine.engine import NeuralGraphEngine
from core.graph_engine.node import BaseNode
from agents.cognitive.supervisor_agent import SupervisorAgent
from agents.cognitive.architect_agent import ArchitectAgent
from agents.technical.dev_agent import DevAgent
from agents.technical.tester_agent import TesterAgent
from agents.technical.debugger_agent import DebuggerAgent


class SupervisorNode(BaseNode):
    def __init__(self) -> None:
        super().__init__("supervisor")
        self.agent = SupervisorAgent()

    async def execute(self, state: NeuralState) -> NeuralState:
        return await self.agent.execute(state)


class ArchitectNode(BaseNode):
    def __init__(self) -> None:
        super().__init__("architect")
        self.agent = ArchitectAgent()

    async def execute(self, state: NeuralState) -> NeuralState:
        return await self.agent.execute(state)


class DevNode(BaseNode):
    def __init__(self, output_dir: Path) -> None:
        super().__init__("dev")
        self.agent = DevAgent(output_dir=output_dir)

    async def execute(self, state: NeuralState) -> NeuralState:
        return await self.agent.execute(state)


class TesterNode(BaseNode):
    def __init__(self, project_root: Path) -> None:
        super().__init__("tester")
        self.agent = TesterAgent(project_root=project_root)

    async def execute(self, state: NeuralState) -> NeuralState:
        return await self.agent.execute(state)


class DebuggerNode(BaseNode):
    def __init__(self, project_root: Path) -> None:
        super().__init__("debugger")
        self.agent = DebuggerAgent(project_root=project_root)

    async def execute(self, state: NeuralState) -> NeuralState:
        return await self.agent.execute(state)


async def main() -> None:
    goal = "Konsoldan çalışan, dört işlem yapabilen basit bir Python hesap makinesi yaz."
    state = NeuralState(goal=goal)

    project_root = Path(".")
    output_dir = Path("output")

    engine = NeuralGraphEngine()
    engine.add_node(SupervisorNode())
    engine.add_node(ArchitectNode())
    engine.add_node(DevNode(output_dir=output_dir))
    engine.add_node(TesterNode(project_root=project_root))
    engine.add_node(DebuggerNode(project_root=project_root))

    engine.add_edge("supervisor", "architect")
    engine.add_edge("architect", "dev")
    engine.add_edge("dev", "tester")
    engine.add_edge(
        "tester",
        "debugger",
        condition=lambda s: s.artifacts.get("test_result") == "fail",
    )

    final_state = await engine.execute(state)
    print("Run ID:", final_state.run_id)
    print("Artifacts:", final_state.artifacts)
    print("Errors:", final_state.errors)


if __name__ == "__main__":
    asyncio.run(main())
