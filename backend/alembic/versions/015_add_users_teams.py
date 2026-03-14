"""Add users, teams, and user_teams tables for SSO authentication and team membership.

Revision ID: 015_add_users_teams
Revises: 014_add_documentation
Create Date: 2026-03-11
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "015_add_users_teams"
down_revision: str | None = "014_add_documentation"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "teams",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("source", sa.String(50), nullable=False, server_default="sso"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name", name="uq_teams_name"),
    )
    op.create_index("ix_teams_name", "teams", ["name"])

    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("sub", sa.String(255), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("display_name", sa.String(255), nullable=False),
        sa.Column("role", sa.String(50), nullable=False, server_default="member"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("last_login", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("sub", name="uq_users_sub"),
        sa.UniqueConstraint("email", name="uq_users_email"),
    )
    op.create_index("ix_users_sub", "users", ["sub"])
    op.create_index("ix_users_email", "users", ["email"])

    op.create_table(
        "user_teams",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("team_id", sa.Uuid(), nullable=False),
        sa.Column("role_in_team", sa.String(50), nullable=False, server_default="member"),
        sa.Column("joined_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["team_id"], ["teams.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "team_id", name="uq_user_team"),
    )
    op.create_index("ix_user_teams_user_id", "user_teams", ["user_id"])
    op.create_index("ix_user_teams_team_id", "user_teams", ["team_id"])


def downgrade() -> None:
    op.drop_index("ix_user_teams_team_id", table_name="user_teams")
    op.drop_index("ix_user_teams_user_id", table_name="user_teams")
    op.drop_table("user_teams")

    op.drop_index("ix_users_email", table_name="users")
    op.drop_index("ix_users_sub", table_name="users")
    op.drop_table("users")

    op.drop_index("ix_teams_name", table_name="teams")
    op.drop_table("teams")
