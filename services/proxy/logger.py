"""Async background logger — writes conversation messages to DB."""
import uuid
from datetime import datetime, timezone

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


async def log_message(
    db: AsyncSession,
    conversation_id: uuid.UUID,
    student_id: uuid.UUID,
    project_id: uuid.UUID,
    role: str,
    content: str,
    model: str,
    input_tokens: int | None,
    output_tokens: int | None,
) -> None:
    """Insert a single conversation message row."""
    await db.execute(
        text(
            """
            INSERT INTO conversation_messages
              (id, conversation_id, student_id, project_id, role, content, model, input_tokens, output_tokens)
            VALUES
              (:id, :cid, :sid, :pid, :role, :content, :model, :in_tok, :out_tok)
            """
        ),
        {
            "id": uuid.uuid4(),
            "cid": conversation_id,
            "sid": student_id,
            "pid": project_id,
            "role": role,
            "content": content,
            "model": model,
            "in_tok": input_tokens,
            "out_tok": output_tokens,
        },
    )
    # Increment message_count on conversation
    await db.execute(
        text(
            "UPDATE conversations SET message_count = message_count + 1 WHERE id = :cid"
        ),
        {"cid": conversation_id},
    )
    await db.commit()
