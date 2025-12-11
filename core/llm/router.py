# core/llm/router.py
import time
import httpx
import json
from typing import List, Dict, Any
from core.config import settings
from core.utils.logger import get_logger
from core.llm.models import LLMResponse
from core.graph_engine.state import NeuralState

logger = get_logger("LLMRouter")


class LLMRouter:
    async def route(self, state: NeuralState, messages: List[Dict] = None) -> LLMResponse:
        start_time = time.time()
        # Mesajları al (parametre olarak gelmediyse state'ten al)
        msgs = messages or state.messages

        # Basit PII Kontrolü (Email veya Telefon varsa yerel model)
        # Gerçek hayatta burası daha gelişmiş bir regex veya model olmalı
        contains_pii = "@" in str(msgs)

        try:
            # 1. Senaryo: PII var veya OpenAI Key yok -> YEREL (Ollama)
            if contains_pii or not settings.OPENAI_API_KEY:
                if contains_pii:
                    logger.info("🔒 PII Detected. Routing to LOCAL (Ollama)...")
                else:
                    logger.warning("⚠️ No OpenAI Key found. Routing to LOCAL (Ollama)...")
                response = await self._call_ollama(msgs)

            # 2. Senaryo: Güvenli -> BULUT (OpenAI)
            else:
                logger.info("☁️ Routing to CLOUD (OpenAI)...")
                response = await self._call_openai(msgs)

        except Exception as e:
            # Hata durumunda (Örn: İnternet yok veya API hatası) -> Fallback
            logger.error(f"❌ Primary Model Failed: {e}. Trying Fallback to LOCAL...")
            try:
                response = await self._call_ollama(msgs)
            except Exception as e2:
                # İkisi de çalışmazsa hata dön
                response = LLMResponse(
                    content=f"CRITICAL ERROR: Both models failed. {e} / {e2}",
                    model="error",
                    provider="none",
                    error=str(e2)
                )

        response.latency = time.time() - start_time
        return response

    async def _call_openai(self, messages: List[Dict]) -> LLMResponse:
        async with httpx.AsyncClient(timeout=60.0) as client:
            payload = {
                "model": settings.DEFAULT_CLOUD_MODEL,
                "messages": messages,
                "temperature": 0.7
            }
            # OpenAI API Çağrısı
            resp = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {settings.OPENAI_API_KEY}"},
                json=payload
            )
            resp.raise_for_status()
            data = resp.json()

            return LLMResponse(
                content=data["choices"][0]["message"]["content"],
                model=data["model"],
                provider="openai",
                usage=data.get("usage", {})
            )

    async def _call_ollama(self, messages: List[Dict]) -> LLMResponse:
        # Ollama genellikle localhost:11434 üzerinde çalışır
        async with httpx.AsyncClient(timeout=120.0) as client:
            payload = {
                "model": settings.DEFAULT_LOCAL_MODEL,
                "messages": messages,
                "stream": False
            }
            try:
                # Ollama Chat Endpoint
                resp = await client.post(f"{settings.OLLAMA_BASE_URL}/chat", json=payload)

                if resp.status_code == 200:
                    data = resp.json()
                    return LLMResponse(
                        content=data["message"]["content"],
                        model=data["model"],
                        provider="ollama",
                        usage={"total_tokens": data.get("eval_count", 0)}
                    )
                else:
                    raise Exception(f"Ollama Status: {resp.status_code}")

            except httpx.ConnectError:
                # Eğer Ollama çalışmıyorsa sistemi kilitlememek için Mock cevap dön
                logger.critical("Ollama is NOT running locally!")
                return LLMResponse(
                    content="[SYSTEM ERROR] Ollama (Local LLM) is not running. Please start it or set OPENAI_API_KEY.",
                    model="error",
                    provider="local_error"
                )