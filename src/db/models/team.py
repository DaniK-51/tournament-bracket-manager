"""Team model for storing team/participant information."""

from sqlalchemy import Column, String, Integer, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from src.db.models.base import BaseModel


class Team(BaseModel):
    """Team entity representing a tournament participant.

    Teams can be traditional sports teams, esports teams, or individual
    competitors (treated as a team of one). The players and metadata fields
    are validated against the tournament's team_schema.

    Fields:
        id: Unique identifier
        tournament_id: Reference to parent tournament
        name: Team name
        players: List of player objects (JSONB, validated against schema)
            - Simple: ["Player1", "Player2"]
            - Structured: [{"id": "...", "ign": "Player1", "role": "captain"}]
            - IRL Sports: [{"number": 10, "position": "forward", "name": "John"}]
        seed: Seeding/ranking information (optional)
        metadata: Discipline-specific data (JSONB, validated against schema)
            - Esports: {"logo_url": "...", "region": "EU", "social_links": {...}}
            - IRL Sports: {"jersey_color": "red", "home_venue": "...", "coach": "..."}
            - Chess: {"fide_rating": 2500, "title": "GM"}

    Validation: Both players and metadata are validated against the tournament's
    locked team_schema at creation/update time.
    """

    __tablename__ = "teams"

    tournament_id = Column(UUID(as_uuid=True), ForeignKey("tournaments.id"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    players = Column(JSONB, nullable=False, default=list)
    seed = Column(Integer, nullable=True)
    # Renamed from 'metadata' to avoid conflict with SQLAlchemy reserved name
    custom_metadata = Column("metadata", JSONB, default=dict)

    # Relationships
    tournament = relationship("Tournament", back_populates="teams")
    matches_as_team_a = relationship("Match", foreign_keys="Match.team_a_id", back_populates="team_a")
    matches_as_team_b = relationship("Match", foreign_keys="Match.team_b_id", back_populates="team_b")

    def __repr__(self) -> str:
        return f"<Team(name='{self.name}', tournament_id={self.tournament_id})>"
