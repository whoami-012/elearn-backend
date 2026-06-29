"""add message attachment metadata

Revision ID: c93e7a1d5f20
Revises: b71d9a2c4e10
"""

from alembic import op
import sqlalchemy as sa


revision = "c93e7a1d5f20"
down_revision = "b71d9a2c4e10"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "message_attachments",
        sa.Column("attachment_type", sa.String(length=16), nullable=False, server_default="file"),
    )
    op.add_column(
        "message_attachments",
        sa.Column("thumbnail_url", sa.String(length=1024), nullable=True),
    )
    op.execute(
        """
        UPDATE message_attachments
        SET attachment_type = CASE
            WHEN mime_type LIKE 'image/%' THEN 'image'
            WHEN mime_type LIKE 'video/%' THEN 'video'
            ELSE 'file'
        END
        """
    )


def downgrade() -> None:
    op.drop_column("message_attachments", "thumbnail_url")
    op.drop_column("message_attachments", "attachment_type")
