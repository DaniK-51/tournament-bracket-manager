# Technology Stack

This document details the technology choices for the Tournament Management System. All technology decisions are fixed and must be followed strictly.

## Core Technologies

### Language: Python 3.11+

**Why Python?**
- Rapid development with strong typing support
- Excellent async ecosystem
- Rich validation libraries (Pydantic, jsonschema)
- Strong testing frameworks

**Requirements:**
- Type hints required on all functions and variables
- Async/await patterns throughout
- Follow PEP 8 style guidelines

```python
# Example: Proper type hints
from typing import Optional, List, Dict, Any
from uuid import UUID

async def get_tournament(tournament_id: UUID) -> Optional[Tournament]:
    """Fetch tournament by ID."""
    ...
```

### Web Framework: FastAPI (Latest)

**Why FastAPI?**
- Native async support
- Automatic OpenAPI documentation
- Pydantic integration for validation
- WebSocket support out of the box
- High performance (on par with Node.js and Go)

**Key Features Used:**
- Dependency injection for services
- Background tasks for audit logging
- WebSocket endpoints for real-time updates
- Automatic request/response validation

```python
# Example: FastAPI endpoint with dependency injection
from fastapi import APIRouter, Depends, WebSocket

router = APIRouter()

@router.get("/tournaments/{tournament_id}")
async def get_tournament(
    tournament_id: UUID,
    db: AsyncSession = Depends(get_db_session)
) -> TournamentResponse:
    ...

@router.websocket("/ws/tournaments/{tournament_id}")
async def tournament_updates(websocket: WebSocket, tournament_id: UUID):
    ...
```

### Database: PostgreSQL 15+

**Why PostgreSQL?**
- JSONB columns for flexible data storage
- Native JSON Schema validation support
- Excellent performance for complex queries
- Strong consistency guarantees
- Advanced indexing (GIN indexes on JSONB)

**Key Features Used:**
- JSONB columns with application-level JSON Schema validation
- GIN indexes for efficient JSON querying
- UUID primary keys via `uuid_generate_v4()`
- Foreign key constraints for referential integrity
- Row-level security (future enhancement)

### Async Database Driver: asyncpg + SQLAlchemy 2.0 Async

**Why this combination?**
- `asyncpg`: Fastest PostgreSQL driver for Python
- `SQLAlchemy 2.0`: Mature ORM with full async support
- Type-safe query building
- Connection pooling built-in

**Important:** Synchronous database drivers are **FORBIDDEN**.

```python
# Example: SQLAlchemy 2.0 async session
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

engine = create_async_engine(DATABASE_URL, echo=True)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def get_db_session() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session
```

### ORM: SQLAlchemy 2.0+ (Async Mode Only)

**Why SQLAlchemy 2.0?**
- Complete async support
- Type-safe query interface
- Eager loading to prevent N+1 queries
- Migration support via Alembic

**Requirements:**
- Use async mode only (`AsyncSession`)
- Enable eager loading for relationships
- Avoid N+1 query patterns

```python
# Example: Model definition with relationships
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy import String, DateTime, func
from sqlalchemy.dialects.postgresql import UUID, JSONB

class Base(DeclarativeBase):
    pass

class Tournament(Base):
    __tablename__ = "tournaments"
    
    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    discipline: Mapped[str] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    
    # Relationships with eager loading
    teams: Mapped[List["Team"]] = relationship(
        back_populates="tournament",
        lazy="selectin"  # Prevents N+1 queries
    )
```

### Migrations: Alembic (Latest)

**Why Alembic?**
- Integrates with SQLAlchemy
- Auto-generate migrations from model changes
- Version control for database schema
- Support for data migrations

**Workflow:**
```bash
# Generate migration from model changes
alembic revision --autogenerate -m "Add tournament table"

# Apply migrations
alembic upgrade head

# Rollback
alembic downgrade -1
```

### Validation: jsonschema + Pydantic V2

**Why both?**
- **Pydantic**: Request/response validation, type coercion
- **jsonschema**: Runtime JSON Schema validation against tournament-specific schemas

**Usage Pattern:**
```python
from pydantic import BaseModel, Field
from jsonschema import validate, ValidationError
import jsonschema

# Pydantic for API request/response models
class CreateTournamentRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    discipline: str
    team_schema_id: UUID
    match_schema_id: UUID

# jsonschema for tournament-specific data validation
def validate_team_data(data: dict, schema: dict) -> bool:
    try:
        jsonschema.validate(instance=data, schema=schema)
        return True
    except ValidationError as e:
        raise ValueError(f"Schema validation failed: {e.message}")
```

### Real-time Communication: WebSocket (Native FastAPI)

**Why WebSocket?**
- Bi-directional communication
- Low latency updates
- Efficient for frequent small messages
- Built into FastAPI

**Use Cases:**
- Live score updates
- Bracket state changes
- Match status notifications
- Overlay synchronization

```python
# Example: WebSocket manager pattern
from fastapi import WebSocket
from typing import Dict, Set

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[UUID, Set[WebSocket]] = {}
    
    async def connect(self, websocket: WebSocket, tournament_id: UUID):
        await websocket.accept()
        self.active_connections.setdefault(tournament_id, set()).add(websocket)
    
    async def broadcast(self, tournament_id: UUID, message: dict):
        if tournament_id in self.active_connections:
            for connection in self.active_connections[tournament_id]:
                await connection.send_json(message)
```

### Authentication: Custom API Keys (Hashed with bcrypt)

**Why API Keys?**
- Simple integration for external systems
- No OAuth complexity for internal tools
- Fine-grained permission control
- Easy rotation and revocation

**Security:**
- Keys hashed with bcrypt before storage
- Never store plain text keys
- Support for expiration dates
- Role-based access control (RBAC)

```python
# Example: API key hashing and verification
import bcrypt
from secrets import token_urlsafe

def generate_api_key() -> str:
    return token_urlsafe(32)

def hash_api_key(key: str) -> str:
    return bcrypt.hashpw(key.encode(), bcrypt.gensalt()).decode()

def verify_api_key(key: str, hashed: str) -> bool:
    return bcrypt.checkpw(key.encode(), hashed.encode())
```

### Containerization: Docker + Docker Compose

**Why Docker?**
- Consistent development environment
- Easy deployment
- Service isolation
- Reproducible builds

**Multi-stage Builds:**
```dockerfile
# Example: Multi-stage Dockerfile
FROM python:3.11-slim as builder

WORKDIR /app
COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

FROM python:3.11-slim

WORKDIR /app
COPY --from=builder /root/.local /root/.local
COPY . .

ENV PATH=/root/.local/bin:$PATH
CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Testing: pytest + httpx (Latest)

**Why pytest + httpx?**
- Excellent async test support
- Rich fixture system
- httpx for async HTTP client in tests
- Code coverage integration

**Test Structure:**
```python
# Example: Async test with httpx
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_create_tournament(client: AsyncClient, auth_headers: dict):
    response = await client.post(
        "/tournaments",
        json={"name": "Test Tournament", "discipline": "CS:GO"},
        headers=auth_headers
    )
    assert response.status_code == 201
    assert "id" in response.json()
```

## Forbidden Technologies

The following are explicitly **FORBIDDEN**:

❌ Synchronous database drivers (psycopg2, etc.)
❌ ORMs without async support (Django ORM, peewee sync mode)
❌ MongoDB/NoSQL databases (except PostgreSQL JSONB)
❌ GraphQL (REST + WebSocket is the standard)
❌ Synchronous web frameworks (Flask, Django)

## Development Tools (Recommended)

| Tool | Purpose | Required |
|------|---------|----------|
| pre-commit | Git hooks for linting | Recommended |
| black | Code formatting | Yes |
| ruff | Fast linting | Yes |
| mypy | Type checking | Yes |
| pytest-cov | Coverage reporting | Yes |
| docker-compose | Local development | Yes |

## Version Compatibility Matrix

| Component | Minimum Version | Notes |
|-----------|-----------------|-------|
| Python | 3.11 | 3.12+ recommended |
| PostgreSQL | 15 | JSON Schema support |
| FastAPI | 0.100.0 | WebSocket improvements |
| SQLAlchemy | 2.0.0 | Async rewrite |
| Pydantic | 2.0.0 | V2 breaking changes |
| Alembic | 1.10.0 | SQLAlchemy 2.0 support |

## Next Steps

Continue reading:
- [System Architecture](./03-system-architecture.md) - How components interact
- [Development Guide](./10-development-guide.md) - Setting up your environment
