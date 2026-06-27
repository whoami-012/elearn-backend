"""add restricted academic messaging

Revision ID: d5a72e9c1b44
Revises: b8d41c70f52a
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "d5a72e9c1b44"
down_revision: Union[str, Sequence[str], None] = "b8d41c70f52a"
branch_labels = None
depends_on = None


def upgrade() -> None:
    message_type = postgresql.ENUM("text", "file", "text_with_file", name="message_type", create_type=False)
    message_type.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "direct_conversations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("participant_one_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("participant_two_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("participant_one_id <> participant_two_id", name="ck_direct_conversation_distinct_users"),
        sa.CheckConstraint("participant_one_id < participant_two_id", name="ck_direct_conversation_normalized_pair"),
        sa.UniqueConstraint("participant_one_id", "participant_two_id", name="uq_direct_conversation_participants"),
    )
    op.create_index("ix_direct_conversations_participant_one", "direct_conversations", ["participant_one_id"])
    op.create_index("ix_direct_conversations_participant_two", "direct_conversations", ["participant_two_id"])
    op.create_index("ix_direct_conversations_updated_at", "direct_conversations", ["updated_at"])

    op.create_table(
        "messages",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("conversation_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("direct_conversations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("sender_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("message_type", message_type, nullable=False),
        sa.Column("content", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("edited_at", sa.DateTime(timezone=True)),
        sa.Column("deleted_at", sa.DateTime(timezone=True)),
        sa.Column("client_message_id", sa.String(128)),
        sa.UniqueConstraint("sender_id", "client_message_id", name="uq_message_sender_client_id"),
    )
    op.create_index("ix_messages_conversation_created", "messages", ["conversation_id", "created_at", "id"])
    op.create_index("ix_messages_sender", "messages", ["sender_id"])
    op.add_column("direct_conversations", sa.Column("last_message_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key("fk_conversation_last_message", "direct_conversations", "messages", ["last_message_id"], ["id"], ondelete="SET NULL")

    op.create_table(
        "message_attachments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("message_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("messages.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("original_filename", sa.String(255), nullable=False),
        sa.Column("storage_key", sa.String(512), nullable=False, unique=True),
        sa.Column("mime_type", sa.String(128), nullable=False),
        sa.Column("file_extension", sa.String(16), nullable=False),
        sa.Column("file_size", sa.BigInteger(), nullable=False),
        sa.Column("checksum", sa.String(64), nullable=False),
        sa.Column("scan_status", sa.String(20), nullable=False, server_default="clean"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("file_size > 0", name="ck_message_attachment_positive_size"),
    )

    op.create_table(
        "conversation_read_states",
        sa.Column("conversation_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("direct_conversations.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("last_read_message_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("messages.id", ondelete="SET NULL")),
        sa.Column("last_read_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_read_states_user", "conversation_read_states", ["user_id"])
    op.execute("""
        CREATE FUNCTION enforce_message_sender_membership() RETURNS trigger AS $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM direct_conversations c
                WHERE c.id = NEW.conversation_id
                  AND NEW.sender_id IN (c.participant_one_id, c.participant_two_id)
            ) THEN
                RAISE EXCEPTION 'message sender must be a conversation participant';
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)
    op.execute("""
        CREATE TRIGGER trg_message_sender_membership
        BEFORE INSERT OR UPDATE OF conversation_id, sender_id ON messages
        FOR EACH ROW EXECUTE FUNCTION enforce_message_sender_membership();
    """)
    op.execute("""
        CREATE FUNCTION enforce_conversation_last_message() RETURNS trigger AS $$
        BEGIN
            IF NEW.last_message_id IS NOT NULL AND NOT EXISTS (
                SELECT 1 FROM messages m
                WHERE m.id = NEW.last_message_id AND m.conversation_id = NEW.id
            ) THEN
                RAISE EXCEPTION 'last message must belong to the conversation';
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)
    op.execute("""
        CREATE TRIGGER trg_conversation_last_message
        BEFORE INSERT OR UPDATE OF last_message_id ON direct_conversations
        FOR EACH ROW EXECUTE FUNCTION enforce_conversation_last_message();
    """)
    op.execute("""
        CREATE FUNCTION enforce_read_state_membership() RETURNS trigger AS $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM direct_conversations c
                WHERE c.id = NEW.conversation_id
                  AND NEW.user_id IN (c.participant_one_id, c.participant_two_id)
            ) THEN
                RAISE EXCEPTION 'read-state user must be a conversation participant';
            END IF;
            IF NEW.last_read_message_id IS NOT NULL AND NOT EXISTS (
                SELECT 1 FROM messages m
                WHERE m.id = NEW.last_read_message_id AND m.conversation_id = NEW.conversation_id
            ) THEN
                RAISE EXCEPTION 'read position must belong to the conversation';
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)
    op.execute("""
        CREATE TRIGGER trg_read_state_membership
        BEFORE INSERT OR UPDATE ON conversation_read_states
        FOR EACH ROW EXECUTE FUNCTION enforce_read_state_membership();
    """)


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trg_read_state_membership ON conversation_read_states")
    op.execute("DROP FUNCTION IF EXISTS enforce_read_state_membership()")
    op.execute("DROP TRIGGER IF EXISTS trg_conversation_last_message ON direct_conversations")
    op.execute("DROP FUNCTION IF EXISTS enforce_conversation_last_message()")
    op.execute("DROP TRIGGER IF EXISTS trg_message_sender_membership ON messages")
    op.execute("DROP FUNCTION IF EXISTS enforce_message_sender_membership()")
    op.drop_index("ix_read_states_user", table_name="conversation_read_states")
    op.drop_table("conversation_read_states")
    op.drop_table("message_attachments")
    op.drop_constraint("fk_conversation_last_message", "direct_conversations", type_="foreignkey")
    op.drop_column("direct_conversations", "last_message_id")
    op.drop_index("ix_messages_sender", table_name="messages")
    op.drop_index("ix_messages_conversation_created", table_name="messages")
    op.drop_table("messages")
    op.drop_index("ix_direct_conversations_updated_at", table_name="direct_conversations")
    op.drop_index("ix_direct_conversations_participant_two", table_name="direct_conversations")
    op.drop_index("ix_direct_conversations_participant_one", table_name="direct_conversations")
    op.drop_table("direct_conversations")
    postgresql.ENUM(name="message_type").drop(op.get_bind(), checkfirst=True)
