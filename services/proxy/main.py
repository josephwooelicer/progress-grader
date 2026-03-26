"""
AI Proxy — POST /v1/chat (SSE streaming)
Standalone FastAPI service. Shares JWT_SECRET and DATABASE_URL with backend.
"""
import json
import os
import uuid
from datetime import datetime, timezone
from typing import AsyncIterator

import jwt as pyjwt
from fastapi import BackgroundTasks, FastAPI, Header, HTTPException, Request, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

import auth as proxy_auth
import consent as proxy_consent
import context_tracker
import logger as proxy_logger
import model_resolver

DATABASE_URL = os.environ.get("DATABASE_URL", "")
engine = create_async_engine(DATABASE_URL, pool_pre_ping=True)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

app = FastAPI(title="Progress Grader AI Proxy", version="1.0.0")


class ChatRequest(BaseModel):
    conversation_id: uuid.UUID
    project_id: uuid.UUID | None = None
    messages: list[dict]
    system_prompt: str | None = None
    service_call: bool = False  # Platform-internal calls skip consent check


def _get_provider_module(provider: str):
    if provider == "anthropic":
        from providers import anthropic
        return anthropic
    # Default to OpenAI-compatible
    from providers import openai
    return openai


@app.post("/v1/chat")
async def chat(
    request: ChatRequest,
    background_tasks: BackgroundTasks,
    authorization: str | None = Header(default=None),
):
    # --- Auth ---
    token = (authorization or "").removeprefix("Bearer ").strip()
    if not token:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Missing token")

    try:
        payload = proxy_auth.verify_jwt(token)
    except pyjwt.PyJWTError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid token")

    user_id = uuid.UUID(payload["sub"])
    role = payload.get("role", "student")
    is_service = role == "service" or request.service_call

    async with AsyncSessionLocal() as db:
        # --- Consent check (skip for service calls) ---
        if not is_service and request.project_id:
            if not await proxy_consent.has_consent(db, user_id, request.project_id):
                raise HTTPException(status.HTTP_403_FORBIDDEN, "Consent required for this project")

        # --- Context window check ---
        current_tokens = await context_tracker.get_token_usage(db, request.conversation_id)
        if current_tokens >= context_tracker.HARD_LIMIT_TOKENS:
            raise HTTPException(
                status.HTTP_429_TOO_MANY_REQUESTS,
                detail={
                    "error": "context_limit_reached",
                    "message": "You have reached the context limit for this conversation. Please start a new conversation.",
                    "context_usage_pct": 100.0,
                },
            )

        # --- Resolve model ---
        provider, model, api_key = await model_resolver.resolve_model(
            db, user_id, request.project_id
        )

    if not api_key:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "No API key configured")

    # --- Prepare messages ---
    messages = list(request.messages)
    if request.system_prompt:
        messages = [{"role": "system", "content": request.system_prompt}] + messages

    provider_module = _get_provider_module(provider)

    async def event_stream() -> AsyncIterator[str]:
        full_response = ""
        input_tokens: int | None = None
        output_tokens: int | None = None
        started_at = datetime.now(timezone.utc).isoformat()

        try:
            async for chunk in provider_module.stream_chat(model, api_key, messages):
                if chunk.delta:
                    full_response += chunk.delta

                if chunk.input_tokens is not None:
                    input_tokens = chunk.input_tokens
                if chunk.output_tokens is not None:
                    output_tokens = chunk.output_tokens

                if chunk.delta:
                    data = json.dumps({"delta": {"content": chunk.delta}})
                    yield f"data: {data}\n\n"

        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
            return

        # Final chunk with usage
        total_new = (input_tokens or 0) + (output_tokens or 0)

        async with AsyncSessionLocal() as db:
            new_total = await context_tracker.increment_tokens(
                db,
                request.conversation_id,
                user_id,
                request.project_id or uuid.UUID(int=0),
                total_new,
                started_at,
            )
            usage_pct = context_tracker.calc_usage_pct(new_total)

            if not is_service:
                # Log user messages and assistant response
                for msg in request.messages:
                    await proxy_logger.log_message(
                        db,
                        request.conversation_id,
                        user_id,
                        request.project_id or uuid.UUID(int=0),
                        msg["role"],
                        msg["content"],
                        model,
                        input_tokens if msg == request.messages[-1] else None,
                        None,
                    )
                await proxy_logger.log_message(
                    db,
                    request.conversation_id,
                    user_id,
                    request.project_id or uuid.UUID(int=0),
                    "assistant",
                    full_response,
                    model,
                    None,
                    output_tokens,
                )

        done_data = json.dumps({
            "done": True,
            "context_usage_pct": usage_pct,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
        })
        yield f"data: {done_data}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@app.get("/health")
async def health():
    return {"ok": True}
