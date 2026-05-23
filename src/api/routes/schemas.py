"""API routes for Schema Registry operations."""

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.session import get_db_session
from src.services.schema_registry_service import SchemaRegistryService
from src.db.models.schema_registry import TargetEntity
from src.api.middleware.auth import ApiKeyMiddleware, get_api_key_middleware, ApiKeyRole


router = APIRouter(prefix="/schemas", tags=["schemas"])


@router.get("", response_model=list[dict])
async def list_schemas(
    discipline: str | None = Query(None, description="Filter by discipline"),
    entity_type: TargetEntity | None = Query(None, description="Filter by target entity type"),
    active_only: bool = Query(False, description="Only return active schemas"),
    db: AsyncSession = Depends(get_db_session),
):
    """List all available JSON schemas.

    Returns schemas filtered by discipline, entity type, and active status.
    Schemas are ordered by name and version (descending).
    """
    service = SchemaRegistryService(db)
    schemas = await service.list_schemas(
        discipline_filter=discipline,
        entity_filter=entity_type,
        active_only=active_only,
    )
    return [schema.to_dict() for schema in schemas]


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_schema(
    schema_data: dict[str, Any],
    db: AsyncSession = Depends(get_db_session),
    api_key: ApiKey = Depends(lambda: None),  # TODO: Add auth dependency
):
    """Create a new JSON schema or new version of existing schema.

    The schema will be auto-versioned if a schema with the same name exists.
    Only ADMIN and ORGANIZER roles can create schemas.

    Body:
    ```json
    {
        "name": "csgo_best_of_3",
        "discipline": "CS:GO",
        "target_entity": "MATCH",
        "json_schema": {...}
    }
    ```
    """
    # Validate required fields
    required_fields = ["name", "discipline", "target_entity", "json_schema"]
    for field in required_fields:
        if field not in schema_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Missing required field: {field}",
            )

    # Validate target_entity
    try:
        target_entity = TargetEntity(schema_data["target_entity"])
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid target_entity. Must be one of: {[e.value for e in TargetEntity]}",
        )

    service = SchemaRegistryService(db)
    
    created_by = api_key.id if api_key else None
    
    try:
        schema = await service.create_schema(
            name=schema_data["name"],
            discipline=schema_data["discipline"],
            target_entity=target_entity,
            json_schema=schema_data["json_schema"],
            created_by=created_by,
        )
        return schema.to_dict()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.get("/{schema_id}")
async def get_schema(
    schema_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session),
):
    """Get a specific schema by ID.

    Returns the full schema definition including JSON Schema.
    """
    service = SchemaRegistryService(db)
    schema = await service.get_schema(schema_id)

    if not schema:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Schema {schema_id} not found",
        )

    return schema.to_dict()


@router.patch("/{schema_id}/deactivate")
async def deactivate_schema(
    schema_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session),
    api_key: ApiKey = Depends(lambda: None),  # TODO: Add auth dependency
):
    """Mark a schema as inactive.

    Inactive schemas cannot be used by new tournaments but remain
    available for existing tournaments that reference them.
    Only ADMIN role can deactivate schemas.
    """
    service = SchemaRegistryService(db)
    schema = await service.deactivate_schema(schema_id)

    if not schema:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Schema {schema_id} not found",
        )

    return schema.to_dict()


@router.post("/validate")
async def validate_data(
    validation_request: dict[str, Any],
    db: AsyncSession = Depends(get_db_session),
):
    """Validate data against a JSON schema.

    Utility endpoint to test if data conforms to a schema before submission.

    Body:
    ```json
    {
        "schema_id": "uuid-here",
        "data": {...}
    }
    ```

    Returns:
    ```json
    {
        "valid": true,
        "errors": []
    }
    ```
    """
    if "schema_id" not in validation_request or "data" not in validation_request:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing required fields: schema_id and data",
        )

    try:
        schema_id = uuid.UUID(validation_request["schema_id"])
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid schema_id format",
        )

    service = SchemaRegistryService(db)
    result = await service.validate_data(schema_id, validation_request["data"])

    return result
