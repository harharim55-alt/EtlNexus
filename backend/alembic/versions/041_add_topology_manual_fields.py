"""Add reads_from_manual and feeds_into_manual to pipelines

Allows product owners to manually define upstream/downstream pipeline
connections for the topology view.

Revision ID: 041_add_topology_manual_fields
Revises: 040_add_feature_flags
Create Date: 2026-04-09
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "041_add_topology_manual_fields"
down_revision: str | None = "040_add_feature_flags"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("pipelines", sa.Column("reads_from_manual", sa.JSON(), nullable=True))
    op.add_column("pipelines", sa.Column("feeds_into_manual", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("pipelines", "feeds_into_manual")
    op.drop_column("pipelines", "reads_from_manual")
