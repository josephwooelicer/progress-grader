import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class GitEvent(Base):
    __tablename__ = "git_events"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    student_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    # push | force_push | branch_create | branch_delete | pr_open | pr_merge
    event_type: Mapped[str] = mapped_column(String, nullable=False)
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False)
    commit_sha: Mapped[str | None] = mapped_column(String)
    commit_message: Mapped[str | None] = mapped_column(Text)
    branch_name: Mapped[str | None] = mapped_column(String)
    pr_number: Mapped[int | None] = mapped_column(Integer)
    pr_title: Mapped[str | None] = mapped_column(String)
    pr_description: Mapped[str | None] = mapped_column(Text)
    forced: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
