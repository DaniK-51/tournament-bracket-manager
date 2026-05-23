"""Schema Registry model for JSON Schema storage and versioning."""

from sqlalchemy import Column, String, Integer, Boolean, ForeignKey, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
import enum

from src.db.models.base import BaseModel


class TargetEntity(enum.Enum):
    """Enum for which entity type a schema validates."""

    TEAM = "TEAM"
    MATCH = "MATCH"
    TOURNAMENT = "TOURNAMENT"


class SchemaRegistry(BaseModel):
    """JSON Schema registry for runtime-configurable data validation.

    This table stores JSON Schema definitions that can be updated without
    code changes. Each schema version is immutable - updates create new versions.

    Fields:
        id: Unique identifier
        name: Schema name (e.g., "csgo_best_of_3", "chess_classical")
        discipline: Sport/game type (e.g., "CS:GO", "Chess", "League of Legends")
        target_entity: Which entity this schema validates (TEAM, MATCH, TOURNAMENT)
        version: Auto-incremented version number per schema name
        json_schema: Full JSON Schema definition
        is_active: Whether new tournaments can use this version
        created_by: UUID of API key that created it
    """

    __tablename__ = "schema_registry"

    name = Column(String(255), nullable=False, index=True)
    discipline = Column(String(100), nullable=False, index=True)
    target_entity = Column(SQLEnum(TargetEntity), nullable=False, index=True)
    version = Column(Integer, nullable=False, default=1)
    json_schema = Column(JSONB, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    created_by = Column(UUID(as_uuid=True), ForeignKey("api_key.id"), nullable=True)

    # Relationship to API key
    creator = relationship("ApiKey", back_populates="created_schemas")

    __table_args__ = (
        # Unique constraint: only one active version per name at a time
        # But we allow multiple versions for history
        None,
    )

    def __repr__(self) -> str:
        return f"<SchemaRegistry(name='{self.name}', version={self.version}, discipline='{self.discipline}')>"
