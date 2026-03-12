"""Add CHECK constraints on users.role and visibility_grants.grant_level.

Ensures only valid role values ('admin', 'member', 'viewer') are stored in
the users table and only valid grant levels ('viewer', 'editor') in
visibility_grants.

Revision ID: 020_add_role_check_constraints
Revises: 019_add_grant_level
Create Date: 2026-03-12
"""

from typing import Sequence, Union

from alembic import op

revision: str = "020_add_role_check_constraints"
down_revision: Union[str, None] = "019_add_grant_level"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Normalise any invalid role values before adding constraint
    op.execute(
        "UPDATE users SET role = 'member' "
        "WHERE role NOT IN ('admin', 'member', 'viewer')"
    )
    op.create_check_constraint(
        "ck_users_role",
        "users",
        "role IN ('admin', 'member', 'viewer')",
    )

    # Normalise any invalid grant_level values before adding constraint
    op.execute(
        "UPDATE visibility_grants SET grant_level = 'viewer' "
        "WHERE grant_level NOT IN ('viewer', 'editor')"
    )
    op.create_check_constraint(
        "ck_visibility_grants_grant_level",
        "visibility_grants",
        "grant_level IN ('viewer', 'editor')",
    )


def downgrade() -> None:
    op.drop_constraint("ck_visibility_grants_grant_level", "visibility_grants")
    op.drop_constraint("ck_users_role", "users")
