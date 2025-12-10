from __future__ import annotations

import os
from typing import Any, Dict

import httpx

from core.config import settings


class OpenAIClient:
    def __init__(self, model: str | None = None) -> None:
        self.model = model or settings.DEFAULT_CLOUD_MODEL
        self.api_key = settings.OPENAI_API_KEY or os.getenv("OPENAI_API_KEY")
        self.base_url = "https://api.openai.com/v1/chat/completions"

    async def chat(self, prompt: str) -> Dict[str, Any]:
        if not self.api_key:
            raise RuntimeError("OPENAI_API_KEY is not set")

        payload = {
            "model": self.model,
            "messages": [
                {"role": "user", "content": prompt},
            ],
            "temperature": settings.TEMPERATURE,
            "max_tokens": settings.MAX_TOKENS,
        }

        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                self.base_url,
                json=payload,
                headers={"Authorization": f"Bearer {self.api_key}"},
            )
            resp.raise_for_status()
            return resp.json()
