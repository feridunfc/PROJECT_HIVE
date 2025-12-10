import asyncio

from core.llm.router import LLMRouter
from core.utils.logger import get_logger

logger = get_logger("demo_llm_router")


async def main() -> None:
    router = LLMRouter()
    resp = await router.route(
        prompt="Kısaca PROJECT_HIVE nedir? 1 paragraf Türkçe anlat.",
        mode="t0",
        contains_pii=False,
        budget=0.01,
    )
    print("Model:", resp.model)
    print("Provider:", resp.provider.value)
    print("Content:", resp.content[:400])


if __name__ == "__main__":
    asyncio.run(main())
