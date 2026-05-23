"""Match model for storing match results and scores."""

import enum
from sqlalchemy import Column, String, ForeignKey, Enum as SQLEnum, DateTime
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from src.db.models.base import BaseModel


class MatchStatus(enum.Enum):
    """Enum for match status states."""

    SCHEDULED = "scheduled"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    POSTPONED = "postponed"


class Match(BaseModel):
    """Match entity representing a single game/match within a tournament.

    Matches are contained within nodes and store the score/results. The score
    and metadata fields are validated against the tournament's match_schema.

    Fields:
        uuid: Unique identifier
        node_uuid: Reference to parent node
        team_a_id: First participant (nullable for byes)
        team_b_id: Second participant (nullable for multi-team matches)
        participants: For multi-team/multi-player matches (JSONB, nullable)
            Example: [{"team_id": "...", "position": 1}, {"team_id": "...", "position": 2}]
        score: Match score (JSONB, validated against tournament's match_schema)
            - Best of 3 (CS:GO): {"team_a": 2, "team_b": 1, "maps": [...]}
            - Points (Basketball): {"team_a": 98, "team_b": 95, "quarters": [...]}
            - Chess: {"white": 1, "black": 0, "moves": 45, "opening": "..."}
            - Multi-team Battle Royale: {"teams": [{"id": "...", "placement": 1, "kills": 10}, ...]}
            - Virtual Racing: {"laps": [...], "best_time": "1:23.456", "penalties": 0}
        status: Current match status
        start_time: Scheduled start time (nullable)
        end_time: Actual end time (nullable)
        metadata: Discipline-specific data (JSONB, validated against schema)
            - Esports: VOD link, server IP, map veto order, round history
            - IRL Sports: venue, referee, attendance, weather conditions
            - Chess: time control, opening eco code, PGN link
        winner_id: Points to winning team for progression logic (nullable)
        result_metadata: Computed results for standings (JSONB)
            - Points earned, tiebreaker values, etc.

    Validation: Both score and metadata are validated against the tournament's
    locked match_schema at creation/update time.
    """

    __tablename__ = "matches"

    uuid = Column(UUID(as_uuid=True), unique=True, nullable=False, index=True)
    node_uuid = Column(UUID(as_uuid=True), ForeignKey("nodes.uuid"), nullable=False, index=True)
    
    # Participants (nullable for byes or multi-team matches)
    team_a_id = Column(UUID(as_uuid=True), ForeignKey("teams.id"), nullable=True)
    team_b_id = Column(UUID(as_uuid=True), ForeignKey("teams.id"), nullable=True)
    participants = Column(JSONB, nullable=True)
    
    # Score and status
    score = Column(JSONB, default=dict)
    status = Column(SQLEnum(MatchStatus), nullable=False, default=MatchStatus.SCHEDULED)
    start_time = Column(DateTime(timezone=True), nullable=True)
    end_time = Column(DateTime(timezone=True), nullable=True)
    
    # Metadata and results - renamed from 'metadata' to avoid conflict
    custom_metadata = Column("metadata", JSONB, default=dict)
    winner_id = Column(UUID(as_uuid=True), ForeignKey("teams.id"), nullable=True, index=True)
    result_metadata = Column(JSONB, default=dict)

    # Relationships
    tournament = relationship("Tournament", back_populates="matches")
    team_a = relationship("Team", foreign_keys=[team_a_id], back_populates="matches_as_team_a")
    team_b = relationship("Team", foreign_keys=[team_b_id], back_populates="matches_as_team_b")
    winner = relationship("Team", foreign_keys=[winner_id])

    def __repr__(self) -> str:
        return f"<Match(uuid={self.uuid}, status={self.status.value})>"
