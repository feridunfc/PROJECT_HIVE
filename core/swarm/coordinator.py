from core.utils.logger import get_logger
logger=get_logger("Swarm")

class SwarmCoordinator:
    def __init__(self,agents): self.agents=agents
    async def run(self,state):
        for _ in range(3):
            for ag in self.agents:
                state=await ag.run(state)
                if "fix" in (state.messages[-1]["content"].lower()):
                    return state
        return state
