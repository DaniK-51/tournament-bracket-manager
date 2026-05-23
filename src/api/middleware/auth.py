"""API Key middleware for authentication and authorization."""

import bcrypt
from fastapi import Request, HTTPException, status
from fastapi.security import APIKeyHeader
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models.api_key import ApiKey, ApiKeyRole


API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)


class ApiKeyMiddleware:
    """Middleware for API key authentication and role-based access control.

    This middleware:
    1. Extracts X-API-Key header from requests
    2. Hashes and validates against database
    3. Attaches api_key object to request state
    4. Enforces role-based permissions

    Note: VIEWER role is exempt from some auth checks (read-only operations).
    """

    def __init__(self, db_session: AsyncSession):
        self.db = db_session

    @staticmethod
    def hash_api_key(api_key: str) -> str:
        """Hash an API key using bcrypt.

        Args:
            api_key: Plain text API key

        Returns:
            Bcrypt hashed key
        """
        return bcrypt.hashpw(api_key.encode(), bcrypt.gensalt()).decode()

    @staticmethod
    def verify_api_key(api_key: str, key_hash: str) -> bool:
        """Verify an API key against its hash.

        Args:
            api_key: Plain text API key
            key_hash: Stored bcrypt hash

        Returns:
            True if key matches hash
        """
        return bcrypt.checkpw(api_key.encode(), key_hash.encode())

    async def authenticate(self, request: Request) -> ApiKey | None:
        """Authenticate request using API key header.

        Args:
            request: FastAPI request object

        Returns:
            ApiKey instance if valid, None otherwise

        Raises:
            HTTPException: If API key is invalid or expired
        """
        api_key_value = await API_KEY_HEADER(request)

        if not api_key_value:
            return None

        # Find API key in database
        stmt = select(ApiKey).where(ApiKey.key_hash == self.hash_api_key(api_key_value))
        result = await self.db.execute(stmt)
        api_key = result.scalar_one_or_none()

        if not api_key:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid API key",
                headers={"WWW-Authenticate": "X-API-Key"},
            )

        # Check expiration
        if api_key.expires_at and api_key.expires_at < request.state.now:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="API key has expired",
                headers={"WWW-Authenticate": "X-API-Key"},
            )

        return api_key

    async def check_permissions(
        self,
        api_key: ApiKey | None,
        required_role: ApiKeyRole = ApiKeyRole.VIEWER,
        tournament_id: str | None = None,
    ) -> None:
        """Check if API key has required permissions.

        Args:
            api_key: Authenticated API key (can be None for public endpoints)
            required_role: Minimum role required for this operation
            tournament_id: Optional tournament ID for scope checking

        Raises:
            HTTPException: If permissions are insufficient
        """
        if not api_key:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="API key required",
            )

        # Check role hierarchy
        role_hierarchy = {
            ApiKeyRole.VIEWER: 0,
            ApiKeyRole.OVERLAY_DIRECTOR: 1,
            ApiKeyRole.JUDGE: 2,
            ApiKeyRole.ORGANIZER: 3,
            ApiKeyRole.ADMIN: 4,
        }

        if role_hierarchy.get(api_key.role, -1) < role_hierarchy.get(required_role, 0):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required: {required_role.value}",
            )

        # Check tournament scope
        if tournament_id and api_key.tournament_id:
            if str(api_key.tournament_id) != tournament_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="API key is scoped to a different tournament",
                )

        # Check fine-grained permissions (if defined)
        # TODO: Implement permission override checks based on api_key.permissions


async def get_api_key_middleware(db_session: AsyncSession) -> ApiKeyMiddleware:
    """Dependency factory for ApiKeyMiddleware."""
    return ApiKeyMiddleware(db_session)
