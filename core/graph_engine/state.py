from uuid import uuid4
from typing import List, Dict, Any

class NeuralState:
    def __init__(self, goal:str, mode:str="t0"):
        self.run_id=str(uuid4())
        self.goal=goal
        self.mode=mode
        self.messages=[]
        self.errors=[]
        self.artifacts={}
        self.budget=10.0
        self.budget_used=0.0

    def add_message(self,role,content,name=None):
        self.messages.append({"role":role,"content":content,"name":name})
        return self

    def add_error(self,msg):
        self.errors.append(msg)
        return self

    def add_artifact(self,key,val):
        self.artifacts[key]=val
        return self
