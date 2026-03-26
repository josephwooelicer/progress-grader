import uuid
from datetime import datetime

from sqlalchemy import DateTime, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import INET, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Consent(Base):
    __tablename__ = "consents"
    __table_args__ = (UniqueConstraint("student_id", "project_id"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    student_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    agreed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    agreement_text: Mapped[str] = mapped_column(Text, nullable=False)
    ip_address: Mapped[str | None] = mapped_column(INET)
    # Retained for future policy — never set by application code
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
