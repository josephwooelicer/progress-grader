"""
Per-conversation token tracking.
Stores cumulative token counts in the conversations table.
Returns context_usage_pct on each response chunk.
"""
import uuid

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

# Hard limit at which new requests are blocked (429)
HARD_LIMIT_TOKENS = int(__import__("os").environ.get("CONTEXT_HARD_LIMIT", "100000"))


async def get_token_usage(db: AsyncSession, conversation_id: uuid.UUID) -> int:
    """Return current total_tokens for a conversation (0 if new)."""
    row = await db.execute(
        text("SELECT total_tokens FROM conversations WHERE id = :cid LIMIT 1"),
        {"cid": conversation_id},
    )
    result = row.fetchone()
    return result.total_tokens if result else 0


async def increment_tokens(
    db: AsyncSession,
    conversation_id: uuid.UUID,
    student_id: uuid.UUID,
    project_id: uuid.UUID,
    delta: int,
    started_at: str,
) -> int:
    """
    UPSERT conversation row, add delta tokens.
    Returns new total_tokens.
    """
    await db.execute(
        text(
            """
            INSERT INTO conversations (id, student_id, project_id, started_at, last_message_at, total_tokens, message_count)
            VALUES (:cid, :sid, :pid, :started_at, NOW(), :delta, 0)
            ON CONFLICT (id) DO UPDATE
              SET total_tokens = conversations.total_tokens + :delta,
                  last_message_at = NOW()
            """
        ),
        {
            "cid": conversation_id,
            "sid": student_id,
            "pid": project_id,
            "delta": delta,
            "started_at": started_at,
        },
    )
    await db.commit()
    return await get_token_usage(db, conversation_id)


def calc_usage_pct(total_tokens: int) -> float:
    return min(round(total_tokens / HARD_LIMIT_TOKENS * 100, 1), 100.0)
