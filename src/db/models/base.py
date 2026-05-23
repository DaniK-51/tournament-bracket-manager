"""Base model with common fields for all entities."""

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import Column, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, declared_attr


class BaseModel(DeclarativeBase):
    """Base class for all SQLAlchemy models with common fields.

    All models inherit:
    - UUID primary key
    - created_at timestamp
    - updated_at timestamp
    """

    @declared_attr.directive
    def __tablename__(cls) -> str:
        """Generate table name from class name (snake_case)."""
        # Convert CamelCase to snake_case
        name = cls.__name__
        return "".join(["_" + c.lower() if c.isupper() else c for c in name]).lstrip("_")

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    def to_dict(self) -> dict[str, Any]:
        """Convert model to dictionary representation."""
        return {
            column.name: getattr(self, column.name)
            for column in self.__table__.columns
        }
