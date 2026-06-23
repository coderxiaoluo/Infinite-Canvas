"""rename users.email to username

Revision ID: 002_username
Revises: 001_initial_auth
Create Date: 2026-06-23
"""

from typing import Sequence, Union

from alembic import op

revision: str = "002_username"
down_revision: Union[str, None] = "001_initial_auth"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_index("ix_users_email", table_name="users")
    op.alter_column("users", "email", new_column_name="username")
    op.create_index("ix_users_username", "users", ["username"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_users_username", table_name="users")
    op.alter_column("users", "username", new_column_name="email")
    op.create_index("ix_users_email", "users", ["email"], unique=True)
