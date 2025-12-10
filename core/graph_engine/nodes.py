class BaseNode:
    def __init__(self,name): self.name=name
    async def run(self,state): raise NotImplementedError
