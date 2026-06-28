"""add Google authentication fields

Revision ID: a91f4c2e7d30
Revises: d5a72e9c1b44
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "a91f4c2e7d30"
down_revision: Union[str, Sequence[str], None] = "d5a72e9c1b44"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column("users", "password_hash", existing_type=sa.String(255), nullable=True)
    op.add_column("users", sa.Column("auth_provider", sa.String(20), nullable=False, server_default="local"))
    op.add_column("users", sa.Column("google_id", sa.String(255), nullable=True))
    op.add_column("users", sa.Column("profile_image", sa.String(2048), nullable=True))
    op.add_column("users", sa.Column("email_verified", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.create_unique_constraint("uq_users_google_id", "users", ["google_id"])


def downgrade() -> None:
    op.drop_constraint("uq_users_google_id", "users", type_="unique")
    op.drop_column("users", "email_verified")
    op.drop_column("users", "profile_image")
    op.drop_column("users", "google_id")
    op.drop_column("users", "auth_provider")
    op.execute(
        "UPDATE users SET password_hash = "
        "'$2b$12$knbAVE5MbHa3JYLDCsqQMeTqeLxIQezKY/y56iYW4YEJhT/Wjf3vK' "
        "WHERE password_hash IS NULL"
    )
    op.alter_column("users", "password_hash", existing_type=sa.String(255), nullable=False)
