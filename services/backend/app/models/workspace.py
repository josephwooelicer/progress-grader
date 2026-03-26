import uuid
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Workspace(Base):
    __tablename__ = "workspaces"
    __table_args__ = (UniqueConstraint("student_id", "project_id"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    student_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    state: Mapped[str] = mapped_column(String, nullable=False, default="pending")
    # pending | running | paused | destroyed
    container_id: Mapped[str | None] = mapped_column(String)   # Docker container ID
    url: Mapped[str | None] = mapped_column(String)            # assigned subdomain URL
    gitea_token_encrypted: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class WorkspaceHeartbeat(Base):
    """Last-seen timestamp per running workspace — used for pause detection."""
    __tablename__ = "workspace_heartbeats"

    workspace_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class WorkspaceArchive(Base):
    """Record of archived workspace volumes (zip stored in Minio)."""
    __tablename__ = "workspace_archives"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    student_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    minio_key: Mapped[str] = mapped_column(String, nullable=False)
    size_bytes: Mapped[int | None] = mapped_column(BigInteger)
    archived_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    purge_after: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    purged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
