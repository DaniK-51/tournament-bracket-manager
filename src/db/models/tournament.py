"""Tournament model for storing tournament configurations."""

from sqlalchemy import Column, String, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from src.db.models.base import BaseModel


class Tournament(BaseModel):
    """Tournament entity representing a competition instance.

    This is the central entity that ties together teams, nodes (bracket structure),
    and matches. Tournaments lock to specific schema versions at creation time.

    Fields:
        id: Unique identifier
        name: Tournament name
        discipline: Sport/game type (e.g., "CS:GO", "LoL", "Chess")
        format_config: Format-specific rules as JSONB
            Example: {"type": "double_elim", "grand_final_reset": true}
        metadata: Schema references and custom fields
            - team_schema_id: UUID of schema validating team data
            - match_schema_id: UUID of schema validating match scores
            - custom_fields: Additional tournament-specific data
        created_at: Creation timestamp
        updated_at: Last update timestamp

    Key Point: Once a tournament starts, schema references are LOCKED.
    Changing schemas requires creating a new tournament or explicit migration.
    """

    __tablename__ = "tournaments"

    name = Column(String(255), nullable=False)
    discipline = Column(String(100), nullable=False, index=True)
    format_config = Column(JSONB, nullable=False, default=dict)
    
    # Schema references (locked after first team/match creation)
    team_schema_id = Column(UUID(as_uuid=True), ForeignKey("schema_registry.id"), nullable=True)
    match_schema_id = Column(UUID(as_uuid=True), ForeignKey("schema_registry.id"), nullable=True)
    
    # Custom metadata (free-form, not validated) - renamed from 'metadata' to avoid conflict
    custom_metadata = Column("metadata", JSONB, default=dict)

    # Relationships
    teams = relationship("Team", back_populates="tournament", cascade="all, delete-orphan")
    nodes = relationship("Node", back_populates="tournament", cascade="all, delete-orphan")
    matches = relationship("Match", back_populates="tournament", cascade="all, delete-orphan")
    
    # Schema relationships
    team_schema = relationship("SchemaRegistry", foreign_keys=[team_schema_id])
    match_schema = relationship("SchemaRegistry", foreign_keys=[match_schema_id])

    # Indexes for common queries
    __table_args__ = (
        Index("idx_tournaments_discipline_status", "discipline"),
        Index("idx_tournaments_schema_refs", "team_schema_id", "match_schema_id"),
    )

    def __repr__(self) -> str:
        return f"<Tournament(name='{self.name}', discipline='{self.discipline}')>"
