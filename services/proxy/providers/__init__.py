from typing import AsyncIterator, Protocol


class ProviderChunk:
    def __init__(self, delta: str, input_tokens: int | None = None, output_tokens: int | None = None):
        self.delta = delta
        self.input_tokens = input_tokens
        self.output_tokens = output_tokens


class Provider(Protocol):
    async def stream_chat(
        self,
        model: str,
        api_key: str,
        messages: list[dict],
    ) -> AsyncIterator[ProviderChunk]:
        ...
