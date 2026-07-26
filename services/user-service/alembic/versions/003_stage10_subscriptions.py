"""Stage 10: Subscription System — subscriptions, subscription_usage tables

Revision ID: 003_stage10_subscriptions
Revises: 002_stage5_color
Create Date: 2025-01-04 00:00:00.000000
"""
from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from alembic import op

revision: str = "003_stage10_subscriptions"
down_revision: str | None = "002_stage5_color"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    # ── Enums ─────────────────────────────────────────────────────────────────
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE subscription_plan_enum AS ENUM ('free','glow','radiance','luxe');
        EXCEPTION WHEN duplicate_object THEN NULL;
        END $$;
    """)
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE subscription_status_enum AS ENUM
                ('active','cancelled','past_due','trialing','expired');
        EXCEPTION WHEN duplicate_object THEN NULL;
        END $$;
    """)

    # ── subscriptions ──────────────────────────────────────────────────────────
    op.create_table(
        "subscriptions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("uuid_generate_v4()")),
        sa.Column("user_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="CASCADE"),
                  nullable=False, unique=True, index=True),
        sa.Column("plan",   postgresql.ENUM("free","glow","radiance","luxe",
                                    name="subscription_plan_enum", create_type=False),
                  nullable=False, server_default="free"),
        sa.Column("status", postgresql.ENUM("active","cancelled","past_due","trialing","expired",
                                    name="subscription_status_enum", create_type=False),
                  nullable=False, server_default="active"),
        # Payment provider data
        sa.Column("provider",           sa.String(30),  nullable=True,
                  comment="razorpay | stripe"),
        sa.Column("provider_sub_id",    sa.String(255), nullable=True, index=True),
        sa.Column("provider_customer_id",sa.String(255),nullable=True),
        # Billing period
        sa.Column("current_period_start", sa.DateTime(timezone=True), nullable=True),
        sa.Column("current_period_end",   sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancel_at_period_end", sa.Boolean, nullable=False,
                  server_default=sa.false()),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("trial_end",    sa.DateTime(timezone=True), nullable=True),
        # Misc
        sa.Column("metadata", postgresql.JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
    )
    op.create_index("ix_subscriptions_plan",   "subscriptions", ["plan"])
    op.create_index("ix_subscriptions_status", "subscriptions", ["status"])

    # ── subscription_usage (feature usage counters, reset monthly) ────────────
    op.create_table(
        "subscription_usage",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("uuid_generate_v4()")),
        sa.Column("user_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="CASCADE"),
                  nullable=False, index=True),
        sa.Column("period_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("period_end",   sa.DateTime(timezone=True), nullable=False),
        # Usage counters
        sa.Column("facial_scans",         sa.Integer, nullable=False, server_default="0"),
        sa.Column("ai_chat_messages",     sa.Integer, nullable=False, server_default="0"),
        sa.Column("style_dna_reports",    sa.Integer, nullable=False, server_default="0"),
        sa.Column("alternatives_lookups", sa.Integer, nullable=False, server_default="0"),
        sa.Column("tryon_sessions",       sa.Integer, nullable=False, server_default="0"),
        sa.Column("wardrobe_items_added", sa.Integer, nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
    )

    # Default subscription row for every existing user
    op.execute("""
        INSERT INTO subscriptions (id, user_id, plan, status, created_at, updated_at)
        SELECT uuid_generate_v4(), id, 'free', 'active', now(), now()
        FROM users
        ON CONFLICT (user_id) DO NOTHING
    """)


def downgrade() -> None:
    op.drop_table("subscription_usage")
    op.drop_table("subscriptions")
    op.execute("DROP TYPE IF EXISTS subscription_status_enum")
    op.execute("DROP TYPE IF EXISTS subscription_plan_enum")
