# Development Guide

This guide helps new developers set up their environment and start contributing to the Tournament Management System.

## Prerequisites

Before you begin, ensure you have the following installed:

| Tool | Version | Purpose | Installation Link |
|------|---------|---------|-------------------|
| Python | 3.11+ | Runtime | [python.org](https://www.python.org/downloads/) |
| PostgreSQL | 15+ | Database | [postgresql.org](https://www.postgresql.org/download/) |
| Docker | Latest | Containerization | [docker.com](https://www.docker.com/get-started) |
| Git | Latest | Version control | [git-scm.com](https://git-scm.com/downloads) |

## Quick Start

### 1. Clone the Repository

```bash
git clone https://github.com/your-org/tournament-system.git
cd tournament-system
```

### 2. Set Up Virtual Environment

```bash
# Create virtual environment
python -m venv venv

# Activate (macOS/Linux)
source venv/bin/activate

# Activate (Windows)
venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

### 4. Set Up Database with Docker

```bash
# Start PostgreSQL container
docker-compose up -d postgres

# Wait for database to be ready
sleep 5

# Run migrations
alembic upgrade head
```

### 5. Configure Environment

Create `.env` file in project root:

```bash
# .env
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/tournament_db
SECRET_KEY=your-secret-key-here
DEBUG=true
```

### 6. Run Development Server

```bash
uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000
```

Visit `http://localhost:8000/docs` for Swagger UI.

---

## Project Structure

```
tournament-system/
├── src/
│   ├── api/              # FastAPI routes and middleware
│   │   ├── routes/       # Endpoint handlers
│   │   ├── websocket/    # WebSocket management
│   │   └── middleware/   # Authentication, CORS, etc.
│   ├── services/         # Business logic
│   ├── db/               # Database layer
│   │   ├── models/       # SQLAlchemy models
│   │   └── repositories/ # Data access objects
│   └── core/             # Configuration, utilities
├── tests/                # Test suite
│   ├── unit/             # Unit tests
│   ├── integration/      # Integration tests
│   └── e2e/              # End-to-end tests
├── alembic/              # Database migrations
├── docker/               # Docker configurations
├── docs/                 # Documentation
└── scripts/              # Utility scripts
```

---

## Development Workflow

### 1. Create Feature Branch

```bash
git checkout main
git pull origin main
git checkout -b feature/your-feature-name
```

### 2. Make Changes

Follow coding standards:
- Use type hints on all functions
- Write docstrings for public methods
- Keep functions small and focused
- Follow SOLID principles

### 3. Run Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test file
pytest tests/unit/test_tournament_service.py

# Run async tests
pytest -vv --asyncio-mode=auto
```

### 4. Code Quality Checks

```bash
# Format code
black src/ tests/

# Lint code
ruff check src/ tests/

# Type checking
mypy src/
```

### 5. Commit Changes

```bash
git add .
git commit -m "feat: add your feature description"
```

Follow [Conventional Commits](https://www.conventionalcommits.org/):
- `feat:` New feature
- `fix:` Bug fix
- `docs:` Documentation changes
- `style:` Code style changes
- `refactor:` Code refactoring
- `test:` Test additions/changes
- `chore:` Maintenance tasks

### 6. Create Pull Request

Push your branch and create a PR on GitHub.

---

## Database Setup

### Running Migrations

```bash
# Generate new migration
alembic revision --autogenerate -m "Description of changes"

# Apply migrations
alembic upgrade head

# Rollback one migration
alembic downgrade -1

# View migration history
alembic history
```

### Seeding Test Data

```bash
# Run seed script
python scripts/seed_data.py

# Seed specific tournament
python scripts/seed_data.py --tournament-id uuid-here
```

---

## Testing Guidelines

### Writing Tests

```python
import pytest
from uuid import uuid4
from src.services.tournament_service import TournamentService

@pytest.mark.asyncio
async def test_create_tournament(db_session: AsyncSession):
    # Arrange
    service = TournamentService(db_session)
    
    # Act
    tournament = await service.create_tournament(
        name="Test Tournament",
        discipline="CS:GO",
        format_config={"type": "single_elim"},
        team_schema_id=uuid4(),
        match_schema_id=uuid4()
    )
    
    # Assert
    assert tournament.name == "Test Tournament"
    assert tournament.discipline == "CS:GO"
    assert tournament.id is not None
```

### Test Fixtures

Common fixtures are in `tests/conftest.py`:

```python
@pytest.fixture
async def db_session():
    """Create async database session for tests."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    async with AsyncSessionLocal() as session:
        yield session
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

@pytest.fixture
def auth_headers():
    """Return headers with valid API key."""
    return {"X-API-Key": "test-api-key"}
```

---

## Debugging

### Enable Debug Logging

Add to `.env`:
```bash
LOG_LEVEL=DEBUG
SQL_ECHO=true
```

### Using Debugger

```python
import pdb; pdb.set_trace()  # Traditional breakpoint
breakpoint()  # Python 3.7+

# Or use VS Code debugger with launch.json
```

### Query Debugging

```python
# Log SQL queries
from sqlalchemy import event

@event.listens_for(engine.sync_engine, "before_cursor_execute")
def receive_before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    print("Query:", statement)
    print("Parameters:", parameters)
```

---

## Common Tasks

### Adding New Endpoint

1. Create route handler in `src/api/routes/your_module.py`
2. Add service method in `src/services/your_service.py`
3. Add repository method if needed
4. Write tests
5. Update API documentation

### Adding New Model

1. Create model in `src/db/models/your_model.py`
2. Add to `src/db/models/__init__.py`
3. Generate migration: `alembic revision --autogenerate -m "Add your_model"`
4. Create repository in `src/db/repositories/your_repo.py`
5. Create service in `src/services/your_service.py`

### Adding New Schema Type

1. Define JSON Schema in schema registry
2. Test validation with sample data
3. Document in wiki

---

## Troubleshooting

### Database Connection Issues

```bash
# Check if PostgreSQL is running
docker ps | grep postgres

# Restart database container
docker-compose restart postgres

# Check connection string
echo $DATABASE_URL
```

### Migration Errors

```bash
# Reset database (DEVELOPMENT ONLY)
docker-compose down -v
docker-compose up -d postgres
alembic upgrade head
```

### Import Errors

```bash
# Ensure you're in virtual environment
which python  # Should point to venv/bin/python

# Reinstall dependencies
pip install -r requirements.txt
```

---

## Code Style Examples

### Good Function Definition

```python
from typing import Optional, List
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession

async def get_tournament_with_bracket(
    session: AsyncSession,
    tournament_id: UUID,
    include_teams: bool = True
) -> Optional[Tournament]:
    """
    Fetch tournament with complete bracket structure.
    
    Args:
        session: Database session
        tournament_id: Tournament UUID
        include_teams: Whether to include team data
        
    Returns:
        Tournament object or None if not found
    """
    query = select(Tournament).where(Tournament.id == tournament_id)
    
    if include_teams:
        query = query.options(selectinload(Tournament.teams))
    
    result = await session.execute(query)
    return result.scalar_one_or_none()
```

### Error Handling

```python
from src.core.exceptions import TournamentNotFoundException

async def get_tournament(tournament_id: UUID) -> Tournament:
    tournament = await repo.get_by_id(tournament_id)
    
    if not tournament:
        raise TournamentNotFoundException(
            f"Tournament {tournament_id} not found"
        )
    
    return tournament
```

---

## Performance Tips

1. **Use Eager Loading**: Prevent N+1 queries with `selectinload()`
2. **Batch Operations**: Use bulk inserts for multiple records
3. **Index JSONB Columns**: Add GIN indexes for JSONB queries
4. **Cache Schemas**: Cache frequently accessed schema definitions
5. **Limit Result Sets**: Always paginate list endpoints

---

## Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [SQLAlchemy 2.0 Documentation](https://docs.sqlalchemy.org/en/20/)
- [PostgreSQL JSONB Documentation](https://www.postgresql.org/docs/current/datatype-json.html)
- [JSON Schema Documentation](https://json-schema.org/)
- [pytest Documentation](https://docs.pytest.org/)

---

## Getting Help

- Check existing issues on GitHub
- Read the wiki documentation
- Ask in the development chat channel
- Review similar implementations in the codebase

## Next Steps

After setting up your environment:
1. Read [System Architecture](./03-system-architecture.md) for component overview
2. Explore the codebase by running the server
3. Try fixing a beginner-friendly issue
4. Read [Testing Strategy](./11-testing.md) for testing best practices
