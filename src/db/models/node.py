"""Node model for bracket structure (directed graph building blocks)."""

import enum
from sqlalchemy import Column, String, ForeignKey, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from src.db.models.base import BaseModel


class NodeType(enum.Enum):
    """Enum for different node types in bracket structures."""

    STANDARD = "STANDARD"  # Standard elimination match
    ROUND_ROBIN_GROUP = "ROUND_ROBIN_GROUP"  # Round robin group containing multiple matches
    FINAL = "FINAL"  # Grand final
    CONSOLATION = "CONSOLATION"  # Consolation/3rd place match
    SWISS_ROUND = "SWISS_ROUND"  # Swiss format round
    GROUP_STAGE = "GROUP_STAGE"  # Group stage (general)


class Node(BaseModel):
    """Node entity representing a bracket building block.

    Nodes form a directed graph that represents the tournament bracket structure.
    Each node can contain one or more matches and has connections to next nodes
    based on outcomes.

    Fields:
        uuid: Unique identifier (used in API endpoints)
        tournament_id: Reference to parent tournament
        node_type: Type of node (STANDARD, ROUND_ROBIN_GROUP, etc.)
        stage_info: Stage/group/round information (JSONB)
            - stage_number: int
            - group_letter: str (optional, e.g., "A", "B")
            - round_number: int (for Swiss)
            - description: str
        matches: List of match UUIDs belonging to this node
        next_nodes: Map of position/outcome → next node UUID (JSONB)
            - Standard: {"winner": "uuid-abc", "loser": "uuid-def"}
            - Round Robin: {"1st": "uuid-ghi", "2nd": "uuid-jkl", "3rd": "uuid-mno"}
            - Swiss: {"score_3_0": "uuid-pqr", "score_2_1": "uuid-stu"}
        overlay_config: Hints for external overlay software (JSONB)
            Example: {"position": "top_left", "label": "Winners Final", "priority": 1}
        metadata: Additional node-specific data (free-form, not validated)

    Note: Actual overlay rendering happens in separate software.
    """

    __tablename__ = "nodes"

    uuid = Column(UUID(as_uuid=True), unique=True, nullable=False, index=True)
    tournament_id = Column(UUID(as_uuid=True), ForeignKey("tournaments.id"), nullable=False, index=True)
    node_type = Column(SQLEnum(NodeType), nullable=False, default=NodeType.STANDARD)
    stage_info = Column(JSONB, default=dict)
    matches = Column(JSONB, default=list)
    next_nodes = Column(JSONB, default=dict)
    overlay_config = Column(JSONB, default=dict)
    # Renamed from 'metadata' to avoid conflict with SQLAlchemy reserved name
    custom_metadata = Column("metadata", JSONB, default=dict)

    # Relationships
    tournament = relationship("Tournament", back_populates="nodes")

    def __repr__(self) -> str:
        return f"<Node(uuid={self.uuid}, type={self.node_type.value})>"
