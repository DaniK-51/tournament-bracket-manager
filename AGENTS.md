# Backend Development Standards

This document outlines the standards and best practices for the tournament bracket manager backend application using Python, FastAPI, PostgreSQL, and Docker.

## Technology Stack

- **Framework**: FastAPI
- **Language**: Python 3.9+
- **Database**: PostgreSQL
- **Containerization**: Docker
- **API Documentation**: OpenAPI/Swagger

## Code Structure

```
src/
├── main.py                # FastAPI application entry point
├── api/
│   ├── __init__.py
│   └── v1/
│       ├── __init__.py
│   	├── routes/
│   	│   ├── __init__.py
│   	│   └── tournament.py
│   	└── dependencies.py
├── models/
│   ├── __init__.py
│   └── tournament.py        # Pydantic models
├── schemas/
│   ├── __init__.py
│   └── tournament.py        # Database models (SQLAlchemy)
├── services/
│   ├── __init__.py
│   └── tournament_service.py # Business logic
├── repositories/
│   ├── __init__.py
│   └── tournament_repo.py   # Data access layer
├── database/
│   ├── __init__.py
│   └── session.py           # Database connection
├── config/
│   ├── __init__.py
│   └── settings.py          # Application configuration
├── utils/
│   ├── __init__.py
│   └── helpers.py           # Utility functions
└── tests/
    ├── __init__.py
    └── test_tournament.py   # Test cases
```

## Python Standards

### Code Formatting
- Follow PEP 8 guidelines
- Use Black for code formatting (line length: 88 characters)
- Use isort for import sorting
- Use flake8 for linting

### Type Hints
- Use type hints for all function parameters and return values
- Leverage Pydantic models for data validation
- Use Union types when appropriate
- Use Optional for nullable values

### Error Handling
- Use custom exceptions that inherit from HTTPException
- Implement proper error codes and messages
- Log all errors with appropriate context
- Never expose sensitive information in error messages

```python
from fastapi import HTTPException, status

class TournamentNotFoundError(HTTPException):
    def __init__(self, tournament_id: int):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tournament with id {tournament_id} not found"
        )
```

## FastAPI Best Practices

### Route Organization
- Group routes by version (v1, v2, etc.)
- Group routes by resource type
- Use APIRouter for modular route organization
- Include proper tags for API documentation

### Dependency Injection
- Use FastAPI's dependency injection system for shared logic
- Create reusable dependencies for authentication, database sessions, etc.
- Use Depends() for function-level dependencies

```python
from fastapi import Depends, APIRouter
from sqlalchemy.orm import Session

from database.session import get_db

router = APIRouter(prefix="/tournaments", tags=["tournaments"])

@router.get("/{tournament_id}")
def get_tournament(tournament_id: int, db: Session = Depends(get_db)):
    # Implementation here
    pass
```

### Data Validation
- Use Pydantic models for request/response validation
- Define separate models for input, output, and database
- Use field validation with validators when needed
- Leverage Pydantic's built-in validators (EmailStr, UrlStr, etc.)

## Database Standards (PostgreSQL)

### Schema Design
- Use descriptive table and column names
- Follow singular noun convention for table names
- Use UUIDs for primary keys when distributed systems are involved
- Use integer IDs with auto-increment for simple cases
- Include created_at and updated_at timestamps on all tables

### SQLAlchemy Usage
- Use SQLAlchemy ORM for database operations
- Follow repository pattern for data access
- Use async database operations when possible
- Implement proper indexing on frequently queried fields

```python
from sqlalchemy import Column, Integer, String, DateTime, func
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class Tournament(Base):
    __tablename__ = "tournaments"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    description = Column(String)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
```

## Docker Configuration

### Container Best Practices
- Use official Python base images
- Use multi-stage builds for production
- Minimize image size by removing unnecessary packages
- Use non-root user in containers
- Set proper environment variables

### Dockerfile Example

```dockerfile
# Use official Python runtime as base image
FROM python:3.9-slim

# Set working directory
WORKDIR /app

# Copy requirements first to leverage Docker cache
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create non-root user
RUN adduser --disabled-password --gecos '' appuser && chown -R appuser:appuser /app
USER appuser

# Expose port
EXPOSE 8000

# Run the application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### docker-compose.yml

```yaml
version: '3.8'

services:
  web:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://user:password@db:5432/tournament_db
      - ENVIRONMENT=development
    depends_on:
      - db
    volumes:
      - ./src:/app/src

  db:
    image: postgres:13
    environment:
      - POSTGRES_DB=tournament_db
      - POSTGRES_USER=user
      - POSTGRES_PASSWORD=password
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data

volumes:
  postgres_data:
```

## API Design Guidelines

### RESTful Conventions
- Use nouns for endpoint URLs, not verbs
- Use plural nouns for collections
- Use HTTP methods appropriately (GET, POST, PUT, PATCH, DELETE)
- Use consistent URL patterns

### Status Codes
- 200: Success (GET, PUT, PATCH)
- 201: Created (POST)
- 204: No Content (DELETE)
- 400: Bad Request (validation errors)
- 401: Unauthorized
- 403: Forbidden
- 404: Not Found
- 422: Unprocessable Entity (validation errors)
- 500: Internal Server Error

### Versioning
- Use URL path versioning (/api/v1/resource)
- Maintain backward compatibility within major versions
- Deprecate old versions with proper notice

### Rate Limiting
- Implement rate limiting for public endpoints
- Use Redis for storing rate limit data
- Return proper headers (RateLimit-Limit, RateLimit-Remaining)

## Testing Standards

### Test Structure
- Follow the same structure as the application code
- Use pytest for testing
- Include unit, integration, and end-to-end tests
- Use factory_boy for test data creation

### Test Coverage
- Aim for 80%+ test coverage
- Test edge cases and error conditions
- Use pytest-cov for coverage reporting
- Include database integration tests

### Testing Best Practices
- Use pytest fixtures for shared test setup
- Mock external services and APIs
- Use transactional test databases
- Implement health check endpoints and test them

```python
import pytest
from fastapi.testclient import TestClient

from main import app

client = TestClient(app)

@pytest.fixture
def test_db():
    # Setup test database
    pass


def test_get_tournament_success(test_db):
    response = client.get("/tournaments/1")
    assert response.status_code == 200
    assert "name" in response.json()


def test_get_tournament_not_found(test_db):
    response = client.get("/tournaments/999")
    assert response.status_code == 404
```

## Project Setup

### Requirements

Create a `requirements.txt` file with the following dependencies:

```txt
fastapi==0.68.0
uvicorn==0.15.0
sqlalchemy==1.4.23
psycopg2-binary==2.9.1
pydantic==1.8.2
pytest==6.2.4
pytest-cov==2.12.1
```

### Project Initialization

1. Create the project structure:
```bash
cd tournament-bracket-manager
mkdir -p src/{api/v1/routes,models,schemas,services,repositories,database,config,utils,tests}
```

2. Create empty __init__.py files:
```bash
touch src/{__init__.py,api/__init__.py,api/v1/__init__.py,api/v1/routes/__init__.py,models/__init__.py,schemas/__init__.py,services/__init__.py,repositories/__init__.py,database/__init__.py,config/__init__.py,utils/__init__.py,tests/__init__.py}
```

3. Create the main application file (src/main.py)

### Environment Variables

Create a `.env` file for development:

```env
ENVIRONMENT=development
DATABASE_URL=postgresql://user:password@localhost:5432/tournament_db
SECRET_KEY=your-secret-key-here
DEBUG=True
```

Create a `.env.example` file for documentation:

```env
ENVIRONMENT=development
DATABASE_URL=postgresql://user:password@localhost:5432/tournament_db
SECRET_KEY=your-secret-key-here
DEBUG=True
```

## Development Workflow

1. Start development containers:
```bash
docker-compose up -d
```

2. Run tests:
```bash
docker-compose exec web pytest
```

3. Run linting:
```bash
docker-compose exec web flake8 src/
```

4. Format code:
```bash
docker-compose exec web black src/
```

## Deployment

### Production Dockerfile

Create a `Dockerfile.prod` for production:

```dockerfile
# Build stage
FROM python:3.9-slim as builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends gcc

# Copy and install Python dependencies
COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

# Production stage
FROM python:3.9-slim

WORKDIR /app

# Copy installed dependencies from builder stage
COPY --from=builder /root/.local /root/.local

# Copy application code
COPY . .

# Create non-root user
RUN adduser --disabled-password --gecos '' appuser && chown -R appuser:appuser /app
USER appuser

# Expose port
EXPOSE 8000

# Run the application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
```

### Production docker-compose.yml

Create a `docker-compose.prod.yml`:

```yaml
version: '3.8'

services:
  web:
    build: 
      context: .
      dockerfile: Dockerfile.prod
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://user:password@db:5432/tournament_db
      - ENVIRONMENT=production
      - DEBUG=False
    depends_on:
      - db
    command: "uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4"

  db:
    image: postgres:13
    environment:
      - POSTGRES_DB=tournament_db
      - POSTGRES_USER=user
      - POSTGRES_PASSWORD=password
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U user -d tournament_db"]
      interval: 30s
      timeout: 10s
      retries: 3

volumes:
  postgres_data:
```

### CI/CD Pipeline

Example GitHub Actions workflow (.github/workflows/ci.yml):

```yaml
name: CI

on:
  push:
    branches: [ main ]
  pull_request:
    branches: [ main ]

jobs:
  test:
    runs-on: ubuntu-latest
    
    services:
      postgres:
        image: postgres:13
        env:
          POSTGRES_DB: tournament_test
          POSTGRES_USER: user
          POSTGRES_PASSWORD: password
        ports:
          - 5432:5432
        options: --health-cmd pg_isready --health-interval 10s --health-timeout 5s --health-retries 5
    
    steps:
    - uses: actions/checkout@v2
    
    - name: Set up Python
      uses: actions/setup-python@v2
      with:
        python-version: 3.9
        
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
        
    - name: Run tests
      env:
        DATABASE_URL: postgresql://user:password@localhost:5432/tournament_test
      run: |
        pytest --cov=src --cov-report=xml
        
    - name: Upload coverage to Codecov
      uses: codecov/codecov-action@v1
      
  lint:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v2
    
    - name: Set up Python
      uses: actions/setup-python@v2
      with:
        python-version: 3.9
        
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
        pip install black flake8
        
    - name: Check code formatting
      run: |
        black --check src/
        
    - name: Lint with flake8
      run: |
        flake8 src/
```

<!-- TODO: Conventional Commits policy -->
