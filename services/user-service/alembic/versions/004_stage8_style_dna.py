"""Stage 8: Style DNA System — quiz_sessions, quiz_responses, style_dna_reports

Revision ID: 004_stage8_style_dna
Revises: 003_stage10_subscriptions
Create Date: 2025-01-03 00:00:00.000000

Creates:
  - quiz_status_enum
  - style_dna_status_enum
  - quiz_sessions
  - quiz_responses
  - style_dna_reports
"""
from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from alembic import op

revision: str = "004_stage8_style_dna"
down_revision: str | None = "003_stage10_subscriptions"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    # ── Enums ─────────────────────────────────────────────────────────────────
    quiz_status_enum = postgresql.ENUM(
        "in_progress", "completed", "abandoned",
        name="quiz_status_enum", create_type=True,
    )
    quiz_status_enum.create(op.get_bind(), checkfirst=True)

    style_dna_status_enum = postgresql.ENUM(
        "queued", "generating", "ready", "failed",
        name="style_dna_status_enum", create_type=True,
    )
    style_dna_status_enum.create(op.get_bind(), checkfirst=True)

    # ── quiz_sessions ─────────────────────────────────────────────────────────
    op.create_table(
        "quiz_sessions",
        sa.Column("id",           postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("uuid_generate_v4()")),
        sa.Column("user_id",      postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="CASCADE"),
                  nullable=False, index=True),
        sa.Column("quiz_version", sa.String(10),  nullable=False, server_default="2.0"),
        sa.Column("status",       postgresql.ENUM("in_progress", "completed", "abandoned",
                                          name="quiz_status_enum", create_type=False),
                  nullable=False, server_default="in_progress", index=True),
        sa.Column("current_step", sa.Integer, nullable=False, server_default="0"),
        sa.Column("total_steps",  sa.Integer, nullable=False, server_default="0"),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        # Computed dimensions
        sa.Column("style_axis",     sa.Float, nullable=True),
        sa.Column("energy_axis",    sa.Float, nullable=True),
        sa.Column("structure_axis", sa.Float, nullable=True),
        sa.Column("occasion_mix",   postgresql.JSONB, nullable=True),
        sa.Column("lifestyle_tags", postgresql.JSONB, nullable=True),
        sa.Column("budget_tier",    sa.String(20), nullable=True),
        sa.Column("primary_archetype",   sa.String(50), nullable=True),
        sa.Column("secondary_archetype", sa.String(50), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
    )

    # ── quiz_responses ────────────────────────────────────────────────────────
    op.create_table(
        "quiz_responses",
        sa.Column("id",              postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("uuid_generate_v4()")),
        sa.Column("session_id",      postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("quiz_sessions.id", ondelete="CASCADE"),
                  nullable=False, index=True),
        sa.Column("question_id",     sa.String(50),  nullable=False),
        sa.Column("question_index",  sa.Integer,     nullable=False),
        sa.Column("answer_value",    sa.Text,        nullable=True),
        sa.Column("answer_options",  postgresql.JSONB, nullable=True),
        sa.Column("answer_scores",   postgresql.JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
    )

    # ── style_dna_reports ─────────────────────────────────────────────────────
    op.create_table(
        "style_dna_reports",
        sa.Column("id",              postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("uuid_generate_v4()")),
        sa.Column("user_id",         postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="CASCADE"),
                  nullable=False, index=True),
        sa.Column("quiz_session_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("quiz_sessions.id", ondelete="SET NULL"),
                  nullable=True),
        sa.Column("facial_scan_id",  postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("facial_scans.id", ondelete="SET NULL"),
                  nullable=True),
        sa.Column("status", postgresql.ENUM("queued", "generating", "ready", "failed",
                                    name="style_dna_status_enum", create_type=False),
                  nullable=False, server_default="queued", index=True),
        sa.Column("report_version",  sa.String(10), nullable=False, server_default="1.0"),
        sa.Column("celery_task_id",  sa.String(255), nullable=True),
        # Content
        sa.Column("headline",        sa.String(300), nullable=True),
        sa.Column("narrative",       sa.Text,        nullable=True),
        sa.Column("beauty_profile",               postgresql.JSONB, nullable=True),
        sa.Column("skin_profile",                 postgresql.JSONB, nullable=True),
        sa.Column("color_profile_section",        postgresql.JSONB, nullable=True),
        sa.Column("fashion_profile",              postgresql.JSONB, nullable=True),
        sa.Column("fragrance_profile_section",    postgresql.JSONB, nullable=True),
        sa.Column("hairstyle_profile",            postgresql.JSONB, nullable=True),
        sa.Column("recommendations",              postgresql.JSONB, nullable=True),
        sa.Column("personality",                  postgresql.JSONB, nullable=True),
        sa.Column("occasion_guide",               postgresql.JSONB, nullable=True),
        # Deliverable
        sa.Column("pdf_s3_key",  sa.String(512), nullable=True),
        sa.Column("pdf_url",     sa.String(512), nullable=True),
        sa.Column("pdf_size_kb", sa.Integer,     nullable=True),
        # Freshness
        sa.Column("data_hash",  sa.String(64), nullable=True),
        sa.Column("is_current", sa.Boolean,    nullable=False, server_default=sa.true(), index=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
    )


def downgrade() -> None:
    op.drop_table("style_dna_reports")
    op.drop_table("quiz_responses")
    op.drop_table("quiz_sessions")
    op.execute("DROP TYPE IF EXISTS style_dna_status_enum")
    op.execute("DROP TYPE IF EXISTS quiz_status_enum")
