import time, asyncio
from typing import List, Dict
from core.config import settings
from core.utils.logger import get_logger
from core.llm.models import LLMResponse

logger=get_logger("LLMRouter")

class LLMRouter:
    async def route(self, state, messages:List[Dict]=None, **kw):
        start=time.time()
        msgs=messages or state.messages
        contains_pii="@" in str(msgs)
        if contains_pii:
            resp=await self._local(msgs)
        elif settings.OPENAI_API_KEY:
            resp=await self._cloud(msgs)
        else:
            resp=await self._local(msgs)
        resp.latency=time.time()-start
        return resp

    async def _cloud(self,msg):
        await asyncio.sleep(0.3)
        return LLMResponse(content="[CLOUD] "+msg[-1]["content"],model=settings.DEFAULT_CLOUD_MODEL,provider="openai")

    async def _local(self,msg):
        await asyncio.sleep(0.1)
        return LLMResponse(content="[LOCAL] "+msg[-1]["content"],model=settings.DEFAULT_LOCAL_MODEL,provider="ollama")
