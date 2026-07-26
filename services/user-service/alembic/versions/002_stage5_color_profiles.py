"""Stage 5: Color Intelligence — add color_profiles table

Revision ID: 002_stage5_color
Revises: 001_stage3_auth
Create Date: 2025-01-01 01:00:00.000000
"""
from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from alembic import op

revision: str = "002_stage5_color"
down_revision: str | None = "001_stage3_auth"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.create_table(
        "color_profiles",
        sa.Column("id",          postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("uuid_generate_v4()")),
        sa.Column("user_id",     postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="CASCADE"),
                  nullable=False, index=True),
        sa.Column("scan_id",     postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("facial_scans.id", ondelete="SET NULL"),
                  nullable=True, index=True),
        # Season
        sa.Column("season",              sa.String(30),  nullable=False),
        sa.Column("season_confidence",   sa.Float,       nullable=False, server_default="0.0"),
        sa.Column("season_description",  sa.String(1000),nullable=True),
        # Source attributes (denormalised for fast access)
        sa.Column("skin_tone",           sa.String(20),  nullable=True),
        sa.Column("undertone",           sa.String(20),  nullable=True),
        sa.Column("skin_hex",            sa.String(7),   nullable=True),
        sa.Column("ita_angle",           sa.Float,       nullable=True),
        sa.Column("fitzpatrick",         sa.Integer,     nullable=True),
        sa.Column("hair_color_hex",      sa.String(7),   nullable=True),
        sa.Column("eye_color",           sa.String(50),  nullable=True),
        # Palette JSONB
        sa.Column("palette_best",        postgresql.JSONB, nullable=True),
        sa.Column("palette_avoid",       postgresql.JSONB, nullable=True),
        sa.Column("palette_neutrals",    postgresql.JSONB, nullable=True),
        sa.Column("palette_accents",     postgresql.JSONB, nullable=True),
        # Recommendations JSONB
        sa.Column("makeup_recommendations",      postgresql.JSONB, nullable=True),
        sa.Column("lipstick_recommendations",    postgresql.JSONB, nullable=True),
        sa.Column("hair_color_recommendations",  postgresql.JSONB, nullable=True),
        sa.Column("outfit_recommendations",      postgresql.JSONB, nullable=True),
        sa.Column("jewelry_recommendations",     postgresql.JSONB, nullable=True),
        # Metadata
        sa.Column("engine_version", sa.String(20), nullable=False, server_default="1.0.0"),
        sa.Column("is_active",      sa.Boolean,    nullable=False, server_default=sa.true(),
                  index=True),
        sa.Column("created_at",     sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("updated_at",     sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
    )


def downgrade() -> None:
    op.drop_table("color_profiles")
