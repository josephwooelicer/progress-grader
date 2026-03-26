"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-03-26
"""
from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- users ---
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("role", sa.String(), nullable=False),
        sa.Column("hashed_password", sa.String(), nullable=False),
        sa.Column("keycloak_id", sa.String(), nullable=True),
        sa.Column("gitea_username", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)
    op.create_index("ix_users_keycloak_id", "users", ["keycloak_id"], unique=True)

    # --- refresh_tokens ---
    op.create_table(
        "refresh_tokens",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("token_hash", sa.String(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_refresh_tokens_user_id", "refresh_tokens", ["user_id"])

    # --- courses ---
    op.create_table(
        "courses",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("slug", sa.String(), nullable=False, unique=True),
        sa.Column("gitea_org", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # --- projects ---
    op.create_table(
        "projects",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("course_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("slug", sa.String(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("provider", sa.String(), nullable=True),
        sa.Column("model", sa.String(), nullable=True),
        sa.Column("api_key_encrypted", sa.String(), nullable=True),
        sa.Column("resource_overrides", postgresql.JSONB(), nullable=True),
        sa.Column("skeleton_files", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_projects_course_id", "projects", ["course_id"])

    # --- rubric_dimensions ---
    op.create_table(
        "rubric_dimensions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("scoring_criteria", sa.Text(), nullable=False),
        sa.Column("max_score", sa.SmallInteger(), nullable=False),
        sa.Column("is_mandatory", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("display_order", sa.SmallInteger(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_rubric_dimensions_project_id", "rubric_dimensions", ["project_id"])

    # --- student_project_settings ---
    op.create_table(
        "student_project_settings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("student_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("provider", sa.String(), nullable=True),
        sa.Column("model", sa.String(), nullable=True),
        sa.Column("api_key_encrypted", sa.String(), nullable=True),
        sa.UniqueConstraint("student_id", "project_id", name="uq_student_project_settings"),
    )

    # --- workspaces ---
    op.create_table(
        "workspaces",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("student_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("state", sa.String(), nullable=False, server_default="pending"),
        sa.Column("container_id", sa.String(), nullable=True),
        sa.Column("url", sa.String(), nullable=True),
        sa.Column("gitea_token_encrypted", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("student_id", "project_id", name="uq_workspaces_student_project"),
    )
    op.create_index("ix_workspaces_student_id", "workspaces", ["student_id"])

    # --- workspace_heartbeats ---
    op.create_table(
        "workspace_heartbeats",
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
    )

    # --- workspace_archives ---
    op.create_table(
        "workspace_archives",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("student_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("minio_key", sa.String(), nullable=False),
        sa.Column("size_bytes", sa.BigInteger(), nullable=True),
        sa.Column("archived_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("purge_after", sa.DateTime(timezone=True), nullable=False),
        sa.Column("purged_at", sa.DateTime(timezone=True), nullable=True),
    )

    # --- consents ---
    op.create_table(
        "consents",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("student_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("agreed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("agreement_text", sa.Text(), nullable=False),
        sa.Column("ip_address", postgresql.INET(), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("student_id", "project_id", name="uq_consents_student_project"),
    )
    op.create_index("ix_consents_student_project", "consents", ["student_id", "project_id"])

    # --- conversations ---
    op.create_table(
        "conversations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("student_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("system_prompt", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_message_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("message_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_tokens", sa.Integer(), nullable=False, server_default="0"),
    )
    op.create_index("ix_conversations_student_project", "conversations", ["student_id", "project_id"])

    # --- conversation_messages ---
    op.create_table(
        "conversation_messages",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("conversation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("student_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("role", sa.String(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("model", sa.String(), nullable=False),
        sa.Column("input_tokens", sa.Integer(), nullable=True),
        sa.Column("output_tokens", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_conv_messages_conversation_id", "conversation_messages", ["conversation_id"])
    op.create_index("ix_conv_messages_student_project", "conversation_messages", ["student_id", "project_id"])

    # --- git_events ---
    op.create_table(
        "git_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("student_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("event_type", sa.String(), nullable=False),
        sa.Column("payload", postgresql.JSONB(), nullable=False),
        sa.Column("commit_sha", sa.String(), nullable=True),
        sa.Column("commit_message", sa.Text(), nullable=True),
        sa.Column("branch_name", sa.String(), nullable=True),
        sa.Column("pr_number", sa.Integer(), nullable=True),
        sa.Column("pr_title", sa.String(), nullable=True),
        sa.Column("pr_description", sa.Text(), nullable=True),
        sa.Column("forced", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_git_events_student_project", "git_events", ["student_id", "project_id"])

    # --- rubric_scores ---
    op.create_table(
        "rubric_scores",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("student_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("dimension_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("teacher_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("suggested_score", sa.SmallInteger(), nullable=True),
        sa.Column("suggested_justification", sa.Text(), nullable=True),
        sa.Column("confirmed_score", sa.SmallInteger(), nullable=True),
        sa.Column("confirmed_justification", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_rubric_scores_student_project", "rubric_scores", ["student_id", "project_id"])

    # --- timeline_comments ---
    op.create_table(
        "timeline_comments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("teacher_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("student_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("entry_type", sa.String(), nullable=False),
        sa.Column("entry_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_timeline_comments_entry", "timeline_comments", ["entry_type", "entry_id"])

    # --- timeline_flags ---
    op.create_table(
        "timeline_flags",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("teacher_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("student_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("entry_type", sa.String(), nullable=False),
        sa.Column("entry_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_timeline_flags_teacher_entry", "timeline_flags", ["teacher_id", "entry_type", "entry_id"])


def downgrade() -> None:
    op.drop_table("timeline_flags")
    op.drop_table("timeline_comments")
    op.drop_table("rubric_scores")
    op.drop_table("git_events")
    op.drop_table("conversation_messages")
    op.drop_table("conversations")
    op.drop_table("consents")
    op.drop_table("workspace_archives")
    op.drop_table("workspace_heartbeats")
    op.drop_table("workspaces")
    op.drop_table("student_project_settings")
    op.drop_table("rubric_dimensions")
    op.drop_table("projects")
    op.drop_table("courses")
    op.drop_table("refresh_tokens")
    op.drop_table("users")
