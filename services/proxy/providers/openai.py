"""OpenAI-compatible provider adapter (OpenAI, AIMLAPI, Azure, Ollama, etc.)."""
import os
from typing import AsyncIterator

import httpx

from providers import ProviderChunk

_DEFAULT_BASE_URL = "https://api.openai.com/v1"


async def stream_chat(
    model: str,
    api_key: str,
    messages: list[dict],
) -> AsyncIterator[ProviderChunk]:
    base_url = os.environ.get("DEFAULT_BASE_URL", "").rstrip("/") or _DEFAULT_BASE_URL
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    body = {
        "model": model,
        "messages": messages,
        "stream": True,
        "stream_options": {"include_usage": True},
    }

    async with httpx.AsyncClient(timeout=120.0) as client:
        async with client.stream(
            "POST",
            f"{base_url}/chat/completions",
            json=body,
            headers=headers,
        ) as resp:
            resp.raise_for_status()
            input_tokens: int | None = None
            output_tokens: int | None = None

            async for line in resp.aiter_lines():
                if not line.startswith("data: "):
                    continue
                data = line[6:]
                if data == "[DONE]":
                    break

                import json
                chunk = json.loads(data)

                # Usage is in the final chunk when stream_options.include_usage=True
                if usage := chunk.get("usage"):
                    input_tokens = usage.get("prompt_tokens")
                    output_tokens = usage.get("completion_tokens")

                choices = chunk.get("choices", [])
                if choices:
                    delta = choices[0].get("delta", {}).get("content") or ""
                    yield ProviderChunk(
                        delta=delta,
                        input_tokens=input_tokens if not choices else None,
                        output_tokens=output_tokens if not choices else None,
                    )

            # Yield a final empty chunk carrying usage totals
            yield ProviderChunk(delta="", input_tokens=input_tokens, output_tokens=output_tokens)
