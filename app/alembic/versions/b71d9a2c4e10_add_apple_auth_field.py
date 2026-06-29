"""add Apple authentication field

Revision ID: b71d9a2c4e10
Revises: a91f4c2e7d30
"""
from alembic import op
import sqlalchemy as sa

revision = "b71d9a2c4e10"
down_revision = "a91f4c2e7d30"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("apple_id", sa.String(255), nullable=True))
    op.create_unique_constraint("uq_users_apple_id", "users", ["apple_id"])


def downgrade() -> None:
    op.drop_constraint("uq_users_apple_id", "users", type_="unique")
    op.drop_column("users", "apple_id")
