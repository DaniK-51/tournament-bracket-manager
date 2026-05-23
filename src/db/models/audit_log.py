"""Audit Log model for tracking all changes."""

import enum
from sqlalchemy import Column, String, ForeignKey, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from src.db.models.base import BaseModel


class AuditAction(enum.Enum):
    """Enum for audit log actions."""

    CREATE = "CREATE"
    UPDATE = "UPDATE"
    DELETE = "DELETE"


class AuditLog(BaseModel):
    """Audit Log entity for tracking all mutations in the system.

    Every create, update, and delete operation writes an entry to this table.
    This provides a complete audit trail with before/after snapshots.

    Fields:
        id: Unique identifier
        entity_type: Type of entity affected (e.g., "Tournament", "Team", "Match")
        entity_id: UUID of the affected entity
        action: What happened (CREATE, UPDATE, DELETE)
        before_data: Previous state of the entity (JSONB, null for CREATE)
        after_data: New state of the entity (JSONB, null for DELETE)
        api_key_id: Which API key performed the action
        tournament_id: Reference to tournament (for filtering by tournament)

    Use Cases:
        - Compliance and auditing
        - Debugging issues
        - Rollback/recovery
        - Activity monitoring
    """

    __tablename__ = "audit_log"

    entity_type = Column(String(100), nullable=False, index=True)
    entity_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    action = Column(SQLEnum(AuditAction), nullable=False)
    before_data = Column(JSONB, nullable=True)
    after_data = Column(JSONB, nullable=True)
    api_key_id = Column(UUID(as_uuid=True), ForeignKey("api_key.id"), nullable=True, index=True)
    tournament_id = Column(UUID(as_uuid=True), ForeignKey("tournaments.id"), nullable=True, index=True)

    # Relationships
    api_key = relationship("ApiKey")
    tournament = relationship("Tournament")

    def __repr__(self) -> str:
        return f"<AuditLog(action={self.action.value}, entity_type={self.entity_type}, entity_id={self.entity_id})>"
