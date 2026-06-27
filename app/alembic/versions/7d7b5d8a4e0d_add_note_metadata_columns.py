"""add note metadata columns

Revision ID: 7d7b5d8a4e0d
Revises: 24bc7bbde314
Create Date: 2026-03-31 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "7d7b5d8a4e0d"
down_revision: Union[str, Sequence[str], None] = "24bc7bbde314"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("notes", sa.Column("content", sa.Text(), nullable=True))
    op.add_column("notes", sa.Column("file_type", sa.String(length=100), nullable=True))
    op.add_column("notes", sa.Column("uploaded_by", sa.UUID(), nullable=True))
    op.add_column(
        "notes",
        sa.Column("is_free", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.create_foreign_key(
        "fk_notes_uploaded_by_users",
        "notes",
        "users",
        ["uploaded_by"],
        ["id"],
        ondelete="SET NULL",
    )
    op.alter_column("notes", "is_free", server_default=None)


def downgrade() -> None:
    op.drop_constraint("fk_notes_uploaded_by_users", "notes", type_="foreignkey")
    op.drop_column("notes", "is_free")
    op.drop_column("notes", "uploaded_by")
    op.drop_column("notes", "file_type")
    op.drop_column("notes", "content")
