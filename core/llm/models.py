from pydantic import BaseModel
from typing import Optional, Dict

class LLMResponse(BaseModel):
    content: str
    model: str
    provider: str
    usage: Optional[Dict[str,int]]=None
    latency: float=0.0
    error: Optional[str]=None
