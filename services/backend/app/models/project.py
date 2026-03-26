import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, SmallInteger, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Course(Base):
    __tablename__ = "courses"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String, nullable=False)
    slug: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    gitea_org: Mapped[str | None] = mapped_column(String)   # Gitea org name
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    course_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    slug: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    # AI model config (falls back to platform env defaults)
    provider: Mapped[str | None] = mapped_column(String)
    model: Mapped[str | None] = mapped_column(String)
    api_key_encrypted: Mapped[str | None] = mapped_column(String)
    # Resource overrides (JSON: {cpu_quota, mem_limit}); NULL = use global defaults
    resource_overrides: Mapped[dict | None] = mapped_column(JSONB)
    # Base skeleton content (JSON: {filename: content})
    skeleton_files: Mapped[dict | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class RubricDimension(Base):
    __tablename__ = "rubric_dimensions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    scoring_criteria: Mapped[str] = mapped_column(Text, nullable=False)
    max_score: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=5)
    is_mandatory: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    display_order: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class StudentProjectSettings(Base):
    """Per-student per-project AI model override (student supplies own API key)."""
    __tablename__ = "student_project_settings"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    student_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    provider: Mapped[str | None] = mapped_column(String)
    model: Mapped[str | None] = mapped_column(String)
    api_key_encrypted: Mapped[str | None] = mapped_column(String)
