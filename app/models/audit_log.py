import uuid

from sqlalchemy import Column, DateTime, ForeignKey, Index, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from app.db.base import Base


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    actor_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    action = Column(String(100), nullable=False)
    resource_type = Column(String(100), nullable=False)
    resource_id = Column(String(100), nullable=False)
    old_values = Column(JSONB, nullable=True)
    new_values = Column(JSONB, nullable=True)
    metadata_json = Column("metadata", JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    actor = relationship("User", passive_deletes=True)

    __table_args__ = (
        Index("ix_audit_logs_actor_user_id", "actor_user_id"),
        Index("ix_audit_logs_action", "action"),
        Index("ix_audit_logs_resource_type", "resource_type"),
        Index("ix_audit_logs_created_at", "created_at"),
    )
