"""Anthropic provider adapter."""
from typing import AsyncIterator

import httpx

from providers import ProviderChunk


async def stream_chat(
    model: str,
    api_key: str,
    messages: list[dict],
) -> AsyncIterator[ProviderChunk]:
    # Separate system message if present
    system = ""
    user_messages = []
    for m in messages:
        if m["role"] == "system":
            system = m["content"]
        else:
            user_messages.append(m)

    headers = {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }
    body: dict = {
        "model": model,
        "messages": user_messages,
        "max_tokens": 8192,
        "stream": True,
    }
    if system:
        body["system"] = system

    input_tokens: int | None = None
    output_tokens: int | None = None

    async with httpx.AsyncClient(timeout=120.0) as client:
        async with client.stream(
            "POST",
            "https://api.anthropic.com/v1/messages",
            json=body,
            headers=headers,
        ) as resp:
            resp.raise_for_status()

            async for line in resp.aiter_lines():
                if not line.startswith("data: "):
                    continue
                import json
                event = json.loads(line[6:])
                etype = event.get("type")

                if etype == "message_start":
                    usage = event.get("message", {}).get("usage", {})
                    input_tokens = usage.get("input_tokens")
                elif etype == "content_block_delta":
                    delta = event.get("delta", {}).get("text") or ""
                    yield ProviderChunk(delta=delta)
                elif etype == "message_delta":
                    usage = event.get("usage", {})
                    output_tokens = usage.get("output_tokens")
                elif etype == "message_stop":
                    break

    yield ProviderChunk(delta="", input_tokens=input_tokens, output_tokens=output_tokens)
