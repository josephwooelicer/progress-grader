"""Student API: own conversations."""
import uuid

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import StudentUser
from app.models.conversation import Conversation, ConversationMessage

router = APIRouter(prefix="/api/student", tags=["student"])


@router.get("/projects/{project_id}/conversations")
async def list_conversations(
    project_id: uuid.UUID,
    current_user: StudentUser,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Conversation).where(
            Conversation.student_id == current_user.id,
            Conversation.project_id == project_id,
        ).order_by(Conversation.started_at.desc())
    )
    conversations = result.scalars().all()
    return {
        "conversations": [
            {
                "id": str(c.id),
                "started_at": c.started_at.isoformat(),
                "last_message_at": c.last_message_at.isoformat(),
                "message_count": c.message_count,
                "total_tokens": c.total_tokens,
            }
            for c in conversations
        ]
    }


@router.get("/conversations/{conversation_id}/messages")
async def get_messages(
    conversation_id: uuid.UUID,
    current_user: StudentUser,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(ConversationMessage).where(
            ConversationMessage.conversation_id == conversation_id,
            ConversationMessage.student_id == current_user.id,
        ).order_by(ConversationMessage.created_at)
    )
    messages = result.scalars().all()
    return {
        "messages": [
            {
                "id": str(m.id),
                "role": m.role,
                "content": m.content,
                "model": m.model,
                "input_tokens": m.input_tokens,
                "output_tokens": m.output_tokens,
                "created_at": m.created_at.isoformat(),
            }
            for m in messages
        ]
    }
