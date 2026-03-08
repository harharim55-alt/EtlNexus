"""Drop code_path column — pipelines now discovered from Airflow, not git

Revision ID: 004_drop_code_path
Revises: 003_drop_dag_networks
Create Date: 2026-03-08
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "004_drop_code_path"
down_revision: Union[str, None] = "003_drop_dag_networks"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_column("pipelines", "code_path")


def downgrade() -> None:
    op.add_column("pipelines", sa.Column("code_path", sa.String(500), nullable=True))
