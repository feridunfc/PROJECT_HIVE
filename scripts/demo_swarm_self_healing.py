import asyncio
from pathlib import Path

from core.graph_engine.state import NeuralState
from core.swarm.coordinator import SwarmCoordinator, SwarmConfig, ConsensusStrategy
from core.graph_engine.node import BaseNode
from agents.technical.dev_agent import DevAgent
from agents.technical.debugger_agent import DebuggerAgent
from agents.technical.tester_agent import TesterAgent


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
    goal = "Bilerek hatalı bir script üret ve sonra kendi kendini düzelt."
    state = NeuralState(goal=goal)

    project_root = Path(".")
    output_dir = Path("output")

    dev_node = DevNode(output_dir=output_dir)
    tester_node = TesterNode(project_root=project_root)
    debugger_node = DebuggerNode(project_root=project_root)

    config = SwarmConfig(
        agents=[dev_node, tester_node, debugger_node],
        strategy=ConsensusStrategy.FIRST,
    )
    coordinator = SwarmCoordinator(config=config)

    final_state = await coordinator.orchestrate(state)

    print("Run ID:", final_state.run_id)
    print("Artifacts:", final_state.artifacts)
    print("Errors:", final_state.errors)


if __name__ == "__main__":
    asyncio.run(main())
