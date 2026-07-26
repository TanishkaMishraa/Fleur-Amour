"""Stage 7: Smart Alternative Engine — add product_alternatives table

Revision ID: 003_stage7_alternatives
Revises: 002_stage5_color
Create Date: 2025-01-02 00:00:00
"""
from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from alembic import op

revision: str = "003_stage7_alternatives"
down_revision: str | None = "002_stage5_color"


def upgrade() -> None:
    op.create_table(
        "product_alternatives",
        sa.Column("id",             postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("uuid_generate_v4()")),
        sa.Column("source_id",      postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("products.id", ondelete="CASCADE"),
                  nullable=False, index=True),
        sa.Column("alt_id",         postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("products.id", ondelete="CASCADE"),
                  nullable=False, index=True),
        # Similarity scores
        sa.Column("overall_score",    sa.Float, nullable=False, index=True),
        sa.Column("embedding_score",  sa.Float, nullable=True),
        sa.Column("ingredient_score", sa.Float, nullable=True),
        sa.Column("formula_score",    sa.Float, nullable=True),
        sa.Column("shade_score",      sa.Float, nullable=True),
        sa.Column("fragrance_score",  sa.Float, nullable=True),
        sa.Column("style_score",      sa.Float, nullable=True),
        # Match metadata
        sa.Column("match_types",   postgresql.JSONB, nullable=True),
        sa.Column("match_detail",  postgresql.JSONB, nullable=True),
        # Price
        sa.Column("source_price",  sa.Numeric(10, 2), nullable=False),
        sa.Column("alt_price",     sa.Numeric(10, 2), nullable=False),
        sa.Column("price_savings", sa.Numeric(10, 2), nullable=False),
        sa.Column("savings_pct",   sa.Float,          nullable=False),
        sa.Column("currency",      sa.String(3),      nullable=False, server_default="INR"),
        # Quality
        sa.Column("is_best_value",   sa.Boolean,    nullable=False, server_default=sa.false(), index=True),
        sa.Column("rank",            sa.Integer,    nullable=False, server_default="1"),
        sa.Column("engine_version",  sa.String(20), nullable=False, server_default="1.0.0"),
        # Timestamps
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        # Constraints
        sa.UniqueConstraint("source_id", "alt_id", name="uq_product_alternative"),
        sa.CheckConstraint("overall_score >= 0 AND overall_score <= 1", name="ck_alt_score_range"),
        sa.CheckConstraint("price_savings >= 0", name="ck_alt_savings_positive"),
    )
    op.create_index("ix_alternatives_source_score",
                    "product_alternatives", ["source_id", "overall_score"])
    op.create_index("ix_alternatives_source_rank",
                    "product_alternatives", ["source_id", "rank"])


def downgrade() -> None:
    op.drop_table("product_alternatives")
