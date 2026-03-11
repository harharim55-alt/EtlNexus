"""Add documentation, last_updated_by, last_updated_at to pipelines.

Revision ID: 014_add_documentation
Revises: 013_add_execution_plan
Create Date: 2026-03-11
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "014_add_documentation"
down_revision: Union[str, None] = "013_add_execution_plan"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "pipelines",
        sa.Column("documentation", sa.Text(), nullable=True),
    )
    op.add_column(
        "pipelines",
        sa.Column("last_updated_by", sa.String(255), nullable=True),
    )
    op.add_column(
        "pipelines",
        sa.Column("last_updated_at", sa.DateTime(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("pipelines", "last_updated_at")
    op.drop_column("pipelines", "last_updated_by")
    op.drop_column("pipelines", "documentation")
