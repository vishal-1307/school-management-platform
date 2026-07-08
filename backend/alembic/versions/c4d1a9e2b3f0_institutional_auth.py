"""Institutional auth: login_id + password_hash + token_version, drop clerk_id.

Pre-existing users get 'legacy-<id>' login IDs and an unusable password
sentinel ('!') — they cannot sign in until an admin resets their password
or the demo seed replaces them. Uses batch_alter_table so the same
migration runs on both Postgres (live Neon DB) and SQLite (CI check).

Revision ID: c4d1a9e2b3f0
Revises: ba7fbb0b1d69
Create Date: 2026-07-08
"""

from alembic import op
import sqlalchemy as sa

revision = "c4d1a9e2b3f0"
down_revision = "ba7fbb0b1d69"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("users") as batch:
        batch.add_column(sa.Column("login_id", sa.String(length=50), nullable=True))
        batch.add_column(sa.Column("password_hash", sa.String(length=100), nullable=True))
        batch.add_column(
            sa.Column("token_version", sa.Integer(), nullable=False, server_default="0")
        )

    # '||' concatenation works on both Postgres and SQLite.
    op.execute("UPDATE users SET login_id = 'legacy-' || id, password_hash = '!'")

    with op.batch_alter_table("users") as batch:
        batch.alter_column("login_id", existing_type=sa.String(length=50), nullable=False)
        batch.alter_column(
            "password_hash", existing_type=sa.String(length=100), nullable=False
        )
        batch.drop_index("ix_users_clerk_id")
        batch.drop_column("clerk_id")
        batch.create_index("ix_users_login_id", ["login_id"], unique=True)


def downgrade() -> None:
    with op.batch_alter_table("users") as batch:
        batch.drop_index("ix_users_login_id")
        batch.add_column(sa.Column("clerk_id", sa.String(length=200), nullable=True))

    op.execute("UPDATE users SET clerk_id = 'legacy-' || id")

    with op.batch_alter_table("users") as batch:
        batch.alter_column("clerk_id", existing_type=sa.String(length=200), nullable=False)
        batch.create_index("ix_users_clerk_id", ["clerk_id"], unique=True)
        batch.drop_column("login_id")
        batch.drop_column("password_hash")
        batch.drop_column("token_version")
