from core.graph_engine.nodes import BaseNode
from core.llm.router import LLMRouter
from core.utils.logger import get_logger

class BaseAgent(BaseNode):
    def __init__(self,name,role,goal,backstory=""):
        super().__init__(name)
        self.role=role
        self.goal=goal
        self.backstory=backstory or f"You are an expert {role}"
        self.router=LLMRouter()
        self.logger=get_logger(name)

    async def run(self,state):
        sysmsg={"role":"system","content":f"{self.role}:{self.goal}"}
        msgs=[sysmsg]+state.messages
        res=await self.router.route(state,messages=msgs)
        state.add_message("assistant",res.content,self.name)
        return state
