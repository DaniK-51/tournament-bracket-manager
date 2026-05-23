"""API Key model for authentication and authorization."""

import enum
from sqlalchemy import Column, String, Boolean, ForeignKey, DateTime, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from src.db.models.base import BaseModel


class ApiKeyRole(enum.Enum):
    """Enum for API key roles with different permission levels."""

    ADMIN = "admin"  # Full access to everything
    ORGANIZER = "organizer"  # Can manage tournaments, teams, matches
    JUDGE = "judge"  # Can update match scores only
    OVERLAY_DIRECTOR = "overlay_director"  # Read-only access for overlays
    VIEWER = "viewer"  # Limited read-only access (exempt from some auth checks)


class ApiKey(BaseModel):
    """API Key entity for authentication and role-based access control.

    API keys are hashed using bcrypt before storage. Each key has a role
    that determines its permissions, and can optionally be scoped to a
    specific tournament.

    Fields:
        id: Unique identifier
        key_hash: Hashed API key (bcrypt)
        role: Access level (admin, organizer, judge, overlay_director, viewer)
        tournament_id: Scope of access (null = all tournaments)
        permissions: Fine-grained permissions override (JSONB)
            Example: {"can_edit_schemas": false, "can_delete_matches": true}
        created_at: Creation timestamp
        expires_at: Optional expiration timestamp

    Security: The actual API key value is only shown once at creation time.
    Only the hash is stored in the database.
    """

    __tablename__ = "api_key"

    key_hash = Column(String(255), nullable=False, unique=True, index=True)
    role = Column(SQLEnum(ApiKeyRole), nullable=False, default=ApiKeyRole.VIEWER)
    tournament_id = Column(UUID(as_uuid=True), ForeignKey("tournaments.id"), nullable=True, index=True)
    permissions = Column(JSONB, default=dict)
    expires_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    scoped_tournament = relationship("Tournament", foreign_keys=[tournament_id])
    created_schemas = relationship("SchemaRegistry", back_populates="creator")

    def __repr__(self) -> str:
        return f"<ApiKey(role={self.role.value}, tournament_id={self.tournament_id})>"
