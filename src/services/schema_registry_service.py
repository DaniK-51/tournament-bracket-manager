"""Schema Registry Service for managing JSON Schema definitions.

This service handles CRUD operations for JSON Schemas, versioning,
and runtime validation of data against schemas.
"""

import uuid
from typing import Any

from jsonschema import Draft7Validator, ValidationError
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models.schema_registry import SchemaRegistry, TargetEntity


class SchemaRegistryService:
    """Service for managing JSON Schema registry operations."""

    def __init__(self, db_session: AsyncSession):
        self.db = db_session

    async def create_schema(
        self,
        name: str,
        discipline: str,
        target_entity: TargetEntity,
        json_schema: dict[str, Any],
        created_by: uuid.UUID | None = None,
    ) -> SchemaRegistry:
        """Create a new schema or new version of existing schema.

        Auto-increments version number if schema with same name exists.

        Args:
            name: Schema name (e.g., "csgo_best_of_3")
            discipline: Sport/game type (e.g., "CS:GO", "Chess")
            target_entity: Which entity this validates (TEAM, MATCH, TOURNAMENT)
            json_schema: Full JSON Schema definition
            created_by: UUID of API key creating the schema

        Returns:
            Created SchemaRegistry instance with auto-assigned version
        """
        # Get current max version for this schema name
        stmt = select(func.max(SchemaRegistry.version)).where(
            SchemaRegistry.name == name
        )
        result = await self.db.execute(stmt)
        current_version = result.scalar() or 0
        new_version = current_version + 1

        schema = SchemaRegistry(
            name=name,
            discipline=discipline,
            target_entity=target_entity,
            version=new_version,
            json_schema=json_schema,
            is_active=True,
            created_by=created_by,
        )

        self.db.add(schema)
        await self.db.flush()
        await self.db.refresh(schema)

        return schema

    async def get_schema(self, schema_id: uuid.UUID) -> SchemaRegistry | None:
        """Get a specific schema by ID.

        Args:
            schema_id: UUID of the schema to retrieve

        Returns:
            SchemaRegistry instance or None if not found
        """
        stmt = select(SchemaRegistry).where(SchemaRegistry.id == schema_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def list_schemas(
        self,
        discipline_filter: str | None = None,
        entity_filter: TargetEntity | None = None,
        active_only: bool = False,
    ) -> list[SchemaRegistry]:
        """List schemas with optional filters.

        Args:
            discipline_filter: Filter by discipline (e.g., "CS:GO")
            entity_filter: Filter by target entity type
            active_only: Only return active schemas

        Returns:
            List of matching SchemaRegistry instances
        """
        stmt = select(SchemaRegistry).order_by(
            SchemaRegistry.name,
            SchemaRegistry.version.desc(),
        )

        if discipline_filter:
            stmt = stmt.where(SchemaRegistry.discipline == discipline_filter)
        if entity_filter:
            stmt = stmt.where(SchemaRegistry.target_entity == entity_filter)
        if active_only:
            stmt = stmt.where(SchemaRegistry.is_active == True)

        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def validate_data(
        self, schema_id: uuid.UUID, data: dict[str, Any]
    ) -> dict[str, Any]:
        """Validate data against a schema.

        Args:
            schema_id: UUID of schema to validate against
            data: Data to validate

        Returns:
            Dict with 'valid' boolean and 'errors' list
        """
        schema = await self.get_schema(schema_id)
        if not schema:
            return {"valid": False, "errors": ["Schema not found"]}

        validator = Draft7Validator(schema.json_schema)
        errors = list(validator.iter_errors(data))

        if errors:
            error_messages = [
                {"path": list(error.path), "message": error.message}
                for error in errors
            ]
            return {"valid": False, "errors": error_messages}

        return {"valid": True, "errors": []}

    async def deactivate_schema(self, schema_id: uuid.UUID) -> SchemaRegistry | None:
        """Mark a schema as inactive.

        Inactive schemas cannot be used by new tournaments but remain
        available for existing tournaments that reference them.

        Args:
            schema_id: UUID of schema to deactivate

        Returns:
            Updated SchemaRegistry instance or None if not found
        """
        schema = await self.get_schema(schema_id)
        if not schema:
            return None

        schema.is_active = False
        await self.db.flush()
        await self.db.refresh(schema)

        return schema

    async def get_active_schema_by_name(
        self, name: str
    ) -> SchemaRegistry | None:
        """Get the latest active version of a schema by name.

        Args:
            name: Schema name to look up

        Returns:
            Latest active SchemaRegistry instance or None
        """
        stmt = (
            select(SchemaRegistry)
            .where(SchemaRegistry.name == name)
            .where(SchemaRegistry.is_active == True)
            .order_by(SchemaRegistry.version.desc())
            .limit(1)
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
