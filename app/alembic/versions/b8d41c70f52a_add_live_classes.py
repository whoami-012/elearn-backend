"""add Agora live classes and attendance

Revision ID: b8d41c70f52a
Revises: 7d7b5d8a4e0d
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "b8d41c70f52a"
down_revision: Union[str, Sequence[str], None] = "7d7b5d8a4e0d"
branch_labels = None
depends_on = None


def upgrade() -> None:
    live_status = postgresql.ENUM("scheduled", "live", "completed", "cancelled", name="live_class_status", create_type=False)
    attendance_status = postgresql.ENUM("present", "partial", "absent", name="attendance_status", create_type=False)
    live_status.create(op.get_bind(), checkfirst=True)
    attendance_status.create(op.get_bind(), checkfirst=True)
    op.create_table(
        "live_classes",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("course_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("courses.id", ondelete="CASCADE"), nullable=False),
        sa.Column("faculty_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("agora_channel_name", sa.String(128), nullable=False, unique=True),
        sa.Column("scheduled_start_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("scheduled_end_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("duration_minutes", sa.Integer(), nullable=False),
        sa.Column("status", live_status, nullable=False, server_default="scheduled"),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("ended_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("scheduled_end_time > scheduled_start_time", name="ck_live_class_time_order"),
        sa.CheckConstraint("duration_minutes > 0", name="ck_live_class_duration"),
    )
    op.create_index("idx_live_classes_course_status", "live_classes", ["course_id", "status"])
    op.create_index("idx_live_classes_faculty", "live_classes", ["faculty_id"])
    op.create_table(
        "live_class_attendance",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("live_class_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("live_classes.id", ondelete="CASCADE"), nullable=False),
        sa.Column("student_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("agora_uid", sa.BigInteger(), nullable=False),
        sa.Column("joined_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("left_at", sa.DateTime(timezone=True)),
        sa.Column("duration_seconds", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("attendance_status", attendance_status, nullable=False, server_default="absent"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("live_class_id", "student_id", name="uq_attendance_student_class"),
        sa.UniqueConstraint("live_class_id", "agora_uid", name="uq_attendance_channel_uid"),
        sa.CheckConstraint("agora_uid > 0 AND agora_uid <= 4294967295", name="ck_agora_uid_range"),
    )
    op.create_index("idx_attendance_class", "live_class_attendance", ["live_class_id"])


def downgrade() -> None:
    op.drop_index("idx_attendance_class", table_name="live_class_attendance")
    op.drop_table("live_class_attendance")
    op.drop_index("idx_live_classes_faculty", table_name="live_classes")
    op.drop_index("idx_live_classes_course_status", table_name="live_classes")
    op.drop_table("live_classes")
    postgresql.ENUM(name="attendance_status").drop(op.get_bind(), checkfirst=True)
    postgresql.ENUM(name="live_class_status").drop(op.get_bind(), checkfirst=True)
