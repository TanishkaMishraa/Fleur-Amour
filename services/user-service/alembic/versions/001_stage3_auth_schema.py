"""Stage 3: Complete auth and user management schema

Revision ID: 001_stage3_auth
Revises:
Create Date: 2025-01-01 00:00:00.000000

Creates ALL tables for Stage 3 authentication and user management:
  users, oauth_accounts, user_sessions, user_preferences,
  user_profiles, fragrance_profiles, facial_scans,
  wardrobes, wardrobe_items, outfits, outfit_items,
  recommendation_sessions, recommendations,
  user_product_interactions, saved_products,
  chat_sessions, chat_messages,
  notifications, notification_preferences,
  uploads, style_reports, reviews
"""
from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "001_stage3_auth"
down_revision: str | None = None
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    # ── Extensions (idempotent) ───────────────────────────────────────────────
    op.execute("CREATE EXTENSION IF NOT EXISTS \"uuid-ossp\"")
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # ── Enums ─────────────────────────────────────────────────────────────────
    user_role_enum = postgresql.ENUM(
        "user", "stylist", "admin",
        name="user_role_enum", create_type=True
    )
    user_role_enum.create(op.get_bind(), checkfirst=True)

    # ── users ─────────────────────────────────────────────────────────────────
    op.create_table(
        "users",
        sa.Column("id",                          postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("email",                       sa.String(255),  nullable=False),
        sa.Column("hashed_password",             sa.String(255),  nullable=True),
        sa.Column("full_name",                   sa.String(255),  nullable=False),
        sa.Column("avatar_url",                  sa.String(512),  nullable=True),
        # Status
        sa.Column("is_active",                   sa.Boolean,      nullable=False, server_default=sa.true()),
        sa.Column("is_verified",                 sa.Boolean,      nullable=False, server_default=sa.false()),
        sa.Column("role",                        postgresql.ENUM("user", "stylist", "admin", name="user_role_enum", create_type=False), nullable=False, server_default="user"),
        # Email verification
        sa.Column("email_verification_token",    sa.String(128),  nullable=True),
        sa.Column("email_verification_sent_at",  sa.DateTime(timezone=True), nullable=True),
        sa.Column("email_verified_at",           sa.DateTime(timezone=True), nullable=True),
        # Password reset
        sa.Column("password_reset_token",        sa.String(128),  nullable=True),
        sa.Column("password_reset_sent_at",      sa.DateTime(timezone=True), nullable=True),
        sa.Column("password_changed_at",         sa.DateTime(timezone=True), nullable=True),
        # MFA
        sa.Column("mfa_enabled",                 sa.Boolean,      nullable=False, server_default=sa.false()),
        sa.Column("mfa_secret",                  sa.String(64),   nullable=True),
        # Security / lockout
        sa.Column("failed_login_attempts",       sa.Integer,      nullable=False, server_default="0"),
        sa.Column("locked_until",                sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_login_at",               sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_login_ip",               sa.String(45),   nullable=True),
        # Soft delete
        sa.Column("is_deleted",                  sa.Boolean,      nullable=False, server_default=sa.false()),
        sa.Column("deleted_at",                  sa.DateTime(timezone=True), nullable=True),
        # Timestamps
        sa.Column("created_at",                  sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at",                  sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_users_email",      "users", ["email"])
    op.create_index("ix_users_role",       "users", ["role"])
    op.create_index("ix_users_is_deleted", "users", ["is_deleted"])
    op.create_index("ix_users_email_verification_token", "users", ["email_verification_token"])
    op.create_index("ix_users_password_reset_token",     "users", ["password_reset_token"])
    op.create_unique_constraint("uq_users_email", "users", ["email"])

    # ── oauth_accounts ─────────────────────────────────────────────────────────
    op.create_table(
        "oauth_accounts",
        sa.Column("id",               postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("user_id",          postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("provider",         sa.String(50),   nullable=False),
        sa.Column("provider_user_id", sa.String(255),  nullable=False),
        sa.Column("provider_email",   sa.String(255),  nullable=True),
        sa.Column("access_token",     sa.String(2048), nullable=True),
        sa.Column("refresh_token",    sa.String(2048), nullable=True),
        sa.Column("token_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at",       sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at",       sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_oauth_accounts_user_id", "oauth_accounts", ["user_id"])
    op.create_unique_constraint("uq_oauth_provider_user", "oauth_accounts", ["provider", "provider_user_id"])

    # ── user_sessions ─────────────────────────────────────────────────────────
    op.create_table(
        "user_sessions",
        sa.Column("id",                  postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("user_id",             postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("refresh_token_hash",  sa.String(64),  nullable=False, unique=True),
        sa.Column("device_name",         sa.String(255), nullable=True),
        sa.Column("device_type",         sa.String(50),  nullable=True),
        sa.Column("ip_address",          sa.String(45),  nullable=True),
        sa.Column("user_agent",          sa.String(500), nullable=True),
        sa.Column("location",            sa.String(100), nullable=True),
        sa.Column("last_active_at",      sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at",          sa.DateTime(timezone=True), nullable=False),
        sa.Column("is_active",           sa.Boolean,     nullable=False, server_default=sa.true()),
        sa.Column("created_at",          sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at",          sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_user_sessions_user_id",            "user_sessions", ["user_id"])
    op.create_index("ix_user_sessions_refresh_token_hash", "user_sessions", ["refresh_token_hash"])
    op.create_index("ix_user_sessions_is_active",          "user_sessions", ["is_active"])

    # ── user_preferences ──────────────────────────────────────────────────────
    op.create_table(
        "user_preferences",
        sa.Column("id",                    postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("user_id",               postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True),
        # Notifications
        sa.Column("email_marketing",        sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("email_recommendations",  sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("email_product_updates",  sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("email_security_alerts",  sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("push_recommendations",   sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("push_tryon_complete",    sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("push_scan_complete",     sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("in_app_notifications",   sa.Boolean, nullable=False, server_default=sa.true()),
        # Display
        sa.Column("theme",            sa.String(20), nullable=False, server_default="dark"),
        sa.Column("language",         sa.String(10), nullable=False, server_default="en"),
        sa.Column("currency",         sa.String(3),  nullable=False, server_default="USD"),
        sa.Column("measurement_unit", sa.String(10), nullable=False, server_default="metric"),
        # Privacy
        sa.Column("profile_public",        sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("allow_data_training",   sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("allow_personalisation", sa.Boolean, nullable=False, server_default=sa.true()),
        # Extended
        sa.Column("extended", postgresql.JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_user_preferences_user_id", "user_preferences", ["user_id"])

    # ── user_profiles ─────────────────────────────────────────────────────────
    op.create_table(
        "user_profiles",
        sa.Column("id",                   postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("user_id",              postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("skin_tone",            sa.String(20),  nullable=True),
        sa.Column("skin_type",            sa.String(20),  nullable=True),
        sa.Column("undertone",            sa.String(20),  nullable=True),
        sa.Column("hair_type",            sa.String(50),  nullable=True),
        sa.Column("hair_color",           sa.String(50),  nullable=True),
        sa.Column("eye_color",            sa.String(50),  nullable=True),
        sa.Column("body_shape",           sa.String(30),  nullable=True),
        sa.Column("height_cm",            sa.Float,       nullable=True),
        sa.Column("weight_kg",            sa.Float,       nullable=True),
        sa.Column("age_range",            sa.String(20),  nullable=True),
        sa.Column("style_archetypes",     postgresql.JSONB, nullable=True),
        sa.Column("fragrance_family",     postgresql.JSONB, nullable=True),
        sa.Column("skin_concerns",        postgresql.JSONB, nullable=True),
        sa.Column("avoided_ingredients",  postgresql.JSONB, nullable=True),
        sa.Column("budget_range",         sa.String(20),  nullable=True),
        sa.Column("currency",             sa.String(3),   nullable=False, server_default="USD"),
        sa.Column("onboarding_complete",  sa.Boolean,     nullable=False, server_default=sa.false()),
        sa.Column("quiz_version",         sa.Integer,     nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_user_profiles_user_id", "user_profiles", ["user_id"])

    # ── facial_scans ──────────────────────────────────────────────────────────
    op.create_table(
        "facial_scans",
        sa.Column("id",               postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("user_id",          postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("storage_path",     sa.String(512), nullable=False),
        sa.Column("face_shape",       sa.String(50),  nullable=True),
        sa.Column("skin_analysis",    postgresql.JSONB, nullable=True),
        sa.Column("facial_features",  postgresql.JSONB, nullable=True),
        sa.Column("landmark_data",    postgresql.JSONB, nullable=True),
        sa.Column("model_version",    sa.String(50),  nullable=True),
        sa.Column("quality_score",    sa.Float,       nullable=True),
        sa.Column("is_active",        sa.Boolean,     nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_facial_scans_user_id",   "facial_scans", ["user_id"])
    op.create_index("ix_facial_scans_is_active", "facial_scans", ["is_active"])

    # ── uploads ───────────────────────────────────────────────────────────────
    op.create_table(
        "uploads",
        sa.Column("id",               postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("user_id",          postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("purpose",          sa.String(50),  nullable=False),
        sa.Column("status",           sa.String(20),  nullable=False, server_default="pending"),
        sa.Column("s3_key",           sa.String(512), nullable=False),
        sa.Column("s3_bucket",        sa.String(255), nullable=False),
        sa.Column("content_type",     sa.String(100), nullable=False),
        sa.Column("size_bytes",       sa.Integer,     nullable=True),
        sa.Column("celery_task_id",   sa.String(255), nullable=True),
        sa.Column("result_url",       sa.String(512), nullable=True),
        sa.Column("error_message",    sa.String(500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_uploads_user_id",       "uploads", ["user_id"])
    op.create_index("ix_uploads_status",        "uploads", ["status"])
    op.create_index("ix_uploads_celery_task_id","uploads", ["celery_task_id"])

    # ── wardrobes ─────────────────────────────────────────────────────────────
    op.create_table(
        "wardrobes",
        sa.Column("id",         postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("user_id",    postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name",       sa.String(100), nullable=False),
        sa.Column("is_default", sa.Boolean,     nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_wardrobes_user_id", "wardrobes", ["user_id"])

    # ── chat_sessions ─────────────────────────────────────────────────────────
    op.create_table(
        "chat_sessions",
        sa.Column("id",              postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("user_id",         postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("session_token",   sa.String(128), nullable=False, unique=True),
        sa.Column("context_summary", sa.Text,        nullable=True),
        sa.Column("last_active_at",  sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_active",       sa.Boolean,     nullable=False, server_default=sa.true()),
        sa.Column("created_at",      sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at",      sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_chat_sessions_user_id",      "chat_sessions", ["user_id"])
    op.create_index("ix_chat_sessions_session_token","chat_sessions", ["session_token"])

    # ── notifications ─────────────────────────────────────────────────────────
    op.create_table(
        "notifications",
        sa.Column("id",                postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("user_id",           postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("notification_type", sa.String(50),  nullable=False),
        sa.Column("title",             sa.String(255), nullable=False),
        sa.Column("body",              sa.Text,        nullable=False),
        sa.Column("deep_link",         sa.String(512), nullable=True),
        sa.Column("is_read",           sa.Boolean,     nullable=False, server_default=sa.false()),
        sa.Column("created_at",        sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at",        sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_notifications_user_id", "notifications", ["user_id"])
    op.create_index("ix_notifications_is_read", "notifications", ["is_read"])


def downgrade() -> None:
    op.drop_table("notifications")
    op.drop_table("chat_sessions")
    op.drop_table("wardrobes")
    op.drop_table("uploads")
    op.drop_table("facial_scans")
    op.drop_table("user_profiles")
    op.drop_table("user_preferences")
    op.drop_table("user_sessions")
    op.drop_table("oauth_accounts")
    op.drop_table("users")
    op.execute("DROP TYPE IF EXISTS user_role_enum")
