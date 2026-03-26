"""AI-assisted rubric grading service."""
import json
import uuid
from typing import Any

import httpx

from app.config import settings


async def build_grading_context(
    student_id: uuid.UUID,
    project_id: uuid.UUID,
    rubric_dimensions: list[dict],
    conversation_messages: list[dict],
    git_events: list[dict],
) -> str:
    """Assemble the grading prompt for the AI."""
    rubric_text = "\n".join(
        f"## {d['name']} (max {d['max_score']})\n{d['description']}\n\nScoring criteria:\n{d['scoring_criteria']}"
        for d in rubric_dimensions
    )

    messages_text = "\n".join(
        f"[{m['created_at']}] {m['role'].upper()}: {m['content']}"
        for m in conversation_messages
    )

    git_text = "\n".join(
        f"[{e['created_at']}] {e['event_type']}: {e.get('commit_message') or e.get('pr_title') or e.get('branch_name', '')}"
        + (" (FORCE PUSH)" if e.get("forced") else "")
        for e in git_events
    )

    return f"""You are grading a student's work on an agentic coding project.

## Rubric Dimensions
{rubric_text}

## Student's AI Conversation History
{messages_text}

## Student's Git Activity
{git_text}

For each rubric dimension, provide:
1. A score (integer, 0 to max_score)
2. A short justification (1-3 sentences referencing specific evidence)

Respond ONLY with valid JSON in this format:
{{
  "scores": [
    {{
      "dimension_name": "...",
      "score": <integer>,
      "justification": "..."
    }}
  ]
}}"""


async def request_ai_grading(prompt: str) -> list[dict[str, Any]]:
    """
    Send grading prompt to AI proxy using platform service token.
    Returns list of {{dimension_name, score, justification}}.
    """
    import jwt as pyjwt
    from datetime import datetime, timedelta, timezone

    # Service token — not tied to any user, bypasses consent check
    now = datetime.now(timezone.utc)
    service_token = pyjwt.encode(
        {
            "sub": "platform-service",
            "role": "service",
            "iat": now,
            "exp": now + timedelta(minutes=5),
            "type": "access",
        },
        settings.jwt_secret,
        algorithm="HS256",
    )

    messages = [{"role": "user", "content": prompt}]

    async with httpx.AsyncClient(timeout=120.0) as client:
        async with client.stream(
            "POST",
            f"{settings.proxy_url}/v1/chat",
            json={
                "messages": messages,
                "conversation_id": str(uuid.uuid4()),
                "project_id": None,   # service call, no project
                "service_call": True,
            },
            headers={"Authorization": f"Bearer {service_token}"},
        ) as resp:
            resp.raise_for_status()
            full_text = ""
            async for line in resp.aiter_lines():
                if line.startswith("data: "):
                    data = line[6:]
                    if data == "[DONE]":
                        break
                    chunk = json.loads(data)
                    if delta := chunk.get("delta", {}).get("content"):
                        full_text += delta

    parsed = json.loads(full_text)
    return parsed["scores"]
