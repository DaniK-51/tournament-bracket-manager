# System Architecture

This document describes the layered architecture of the Tournament Management System, including component responsibilities and interactions.

## Layer Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    External Clients                          │
│  (Overlay Software, Admin Panels, Mobile Apps, Bots)        │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                   API Layer (FastAPI)                        │
│  ┌─────────────┬─────────────┬─────────────┬─────────────┐  │
│  │   REST API  │  WebSocket  │    Auth     │   Schema    │  │
│  │  Endpoints  │   Manager   │  Middleware │  Validator  │  │
│  └─────────────┴─────────────┴─────────────┴─────────────┘  │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                 Service/Business Logic Layer                 │
│  ┌─────────────┬─────────────┬─────────────┬─────────────┐  │
│  │  Tournament │   Bracket   │    Match    │    Audit    │  │
│  │   Service   │   Engine    │   Service   │   Service   │  │
│  └─────────────┴─────────────┴─────────────┴─────────────┘  │
│  ┌─────────────┬─────────────┬─────────────┐                │
│  │   Schema    │   Team      │  Progression│                │
│  │  Registry   │  Service    │   Engine    │                │
│  └─────────────┴─────────────┴─────────────┘                │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                   Data Access Layer                          │
│  ┌─────────────────────────────────────────────────────┐    │
│  │         SQLAlchemy 2.0 Async Repository             │    │
│  └─────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                  PostgreSQL Database                         │
│  ┌──────────┬──────────┬──────────┬──────────┬──────────┐  │
│  │tournaments│  teams   │  nodes   │  matches │  audit   │  │
│  └──────────┴──────────┴──────────┴──────────┴──────────┘  │
│  ┌──────────┬──────────┬──────────┬──────────┐             │
│  │ api_keys │ schemas  │  (JSONB  columns    for   flex)   │  │
│  └──────────┴──────────┴───────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

## Directory Structure

```
src/
├── __init__.py
├── api/                      # API Layer
│   ├── __init__.py
│   ├── main.py               # FastAPI app initialization
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── tournaments.py    # Tournament CRUD + schema locking
│   │   ├── teams.py          # Team registration with validation
│   │   ├── nodes.py          # Bracket graph manipulation
│   │   ├── matches.py        # Match scoring with validation
│   │   ├── schemas.py        # Schema registry CRUD
│   │   ├── auth.py           # API key management
│   │   └── audit.py          # Audit log retrieval
│   ├── websocket/
│   │   ├── __init__.py
│   │   ├── manager.py        # Connection manager + subscriptions
│   │   └── events.py         # Event types and serialization
│   └── middleware/
│       ├── __init__.py
│       └── auth.py           # API key authentication
│
├── services/                 # Business Logic Layer
│   ├── __init__.py
│   ├── tournament_service.py     # Create, update, archive
│   ├── bracket_engine.py         # Generate bracket graphs
│   ├── match_service.py          # Score updates, status
│   ├── team_service.py           # Registration, rosters
│   ├── schema_registry_service.py # Schema CRUD, versioning
│   ├── progression_engine.py     # Auto-advance winners
│   └── audit_service.py          # Write logs, retrieve history
│
├── db/                       # Data Access Layer
│   ├── __init__.py
│   ├── session.py            # Async session factory
│   ├── models/
│   │   ├── __init__.py
│   │   ├── base.py           # Base model with common fields
│   │   ├── tournament.py     # Tournament model
│   │   ├── team.py           # Team model
│   │   ├── node.py           # Bracket node model
│   │   ├── match.py          # Match model
│   │   ├── schema_registry.py # JSON Schema definitions
│   │   ├── api_key.py        # API key model
│   │   └── audit_log.py      # Audit trail model
│   └── repositories/
│       ├── __init__.py
│       ├── tournament_repo.py # Complex tournament queries
│       ├── team_repo.py
│       ├── match_repo.py
│       └── schema_repo.py
│
└── core/                     # Core utilities
    ├── __init__.py
    ├── config.py             # Application configuration
    ├── security.py           # Authentication utilities
    └── exceptions.py         # Custom exception classes
```

## Component Responsibilities

### API Layer (FastAPI)

**Purpose:** Handle all external communication

**Responsibilities:**
1. Route HTTP requests to appropriate service methods
2. Manage WebSocket connections for real-time updates
3. Validate API keys and enforce role-based permissions
4. Perform runtime JSON Schema validation
5. Serialize/deserialize data between JSON and Python objects
6. Handle errors and return appropriate HTTP status codes

**Key Components:**

#### `main.py` - Application Entry Point
```python
from fastapi import FastAPI
from .routes import tournaments, teams, matches, schemas, auth, audit
from .websocket import manager

app = FastAPI(title="Tournament Management System")

# Register routers
app.include_router(tournaments.router, prefix="/tournaments", tags=["tournaments"])
app.include_router(teams.router, prefix="/teams", tags=["teams"])
app.include_router(matches.router, prefix="/matches", tags=["matches"])
app.include_router(schemas.router, prefix="/schemas", tags=["schemas"])
app.include_router(auth.router, prefix="/auth", tags=["authentication"])
app.include_router(audit.router, prefix="/audit", tags=["audit"])

# WebSocket endpoint
@app.websocket("/ws/tournaments/{tournament_id}")
async def websocket_endpoint(websocket: WebSocket, tournament_id: UUID):
    await manager.connect(websocket, tournament_id)
```

#### `middleware/auth.py` - Authentication Middleware
```python
from fastapi import Request, HTTPException, status
from ..core.security import verify_api_key

async def auth_middleware(request: Request, call_next):
    api_key = request.headers.get("X-API-Key")
    if not api_key:
        raise HTTPException(status_code=401, detail="Missing API key")
    
    # Verify and attach user context to request
    request.state.api_key_data = await verify_api_key(api_key)
    
    response = await call_next(request)
    return response
```

#### `websocket/manager.py` - Connection Manager
```python
from fastapi import WebSocket
from typing import Dict, Set
from uuid import UUID

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[UUID, Set[WebSocket]] = {}
    
    async def connect(self, websocket: WebSocket, tournament_id: UUID):
        await websocket.accept()
        self.active_connections.setdefault(tournament_id, set()).add(websocket)
    
    def disconnect(self, websocket: WebSocket, tournament_id: UUID):
        if tournament_id in self.active_connections:
            self.active_connections[tournament_id].remove(websocket)
    
    async def broadcast(self, tournament_id: UUID, event_type: str, data: dict):
        message = {
            "type": event_type,
            "data": data,
            "timestamp": datetime.utcnow().isoformat()
        }
        if tournament_id in self.active_connections:
            for connection in self.active_connections[tournament_id]:
                await connection.send_json(message)
```

### Service/Business Logic Layer

**Purpose:** Implement business rules and workflows

**Responsibilities:**
1. Implement tournament creation workflows
2. Generate bracket structures (Single/Double Elim, Round Robin, Swiss)
3. Calculate standings and progression logic
4. Enforce schema locking rules
5. Trigger audit log entries
6. Broadcast WebSocket events on state changes

**Key Services:**

#### `tournament_service.py`
```python
class TournamentService:
    def __init__(self, db: AsyncSession, schema_service: SchemaRegistryService):
        self.db = db
        self.schema_service = schema_service
    
    async def create_tournament(
        self,
        name: str,
        discipline: str,
        format_config: dict,
        team_schema_id: UUID,
        match_schema_id: UUID
    ) -> Tournament:
        # Validate schemas exist and are active
        await self.schema_service.validate_schema_ids(team_schema_id, match_schema_id)
        
        # Create tournament with locked schema references
        tournament = Tournament(
            name=name,
            discipline=discipline,
            format_config=format_config,
            metadata={
                "team_schema_id": str(team_schema_id),
                "match_schema_id": str(match_schema_id)
            }
        )
        
        self.db.add(tournament)
        await self.db.commit()
        await self.db.refresh(tournament)
        
        # Log audit event
        await audit_service.log_creation(tournament)
        
        return tournament
```

#### `bracket_engine.py`
```python
class BracketEngine:
    """Generate and manipulate tournament bracket graphs."""
    
    async def generate_double_elimination(
        self,
        tournament_id: UUID,
        team_count: int
    ) -> List[Node]:
        """Generate double elimination bracket structure."""
        nodes = []
        
        # Calculate rounds needed
        winners_rounds = math.ceil(math.log2(team_count))
        losers_rounds = (winners_rounds - 1) * 2
        
        # Create winners bracket nodes
        for round_num in range(winners_rounds):
            matches_in_round = team_count // (2 ** (round_num + 1))
            for match_num in range(matches_in_round):
                node = Node(
                    tournament_id=tournament_id,
                    node_type=NodeType.STANDARD,
                    stage_info={"stage_number": round_num, "bracket": "winners"},
                    next_nodes={}  # Will be populated as we build
                )
                nodes.append(node)
        
        # Create losers bracket nodes
        # ... implementation continues
        
        # Connect nodes (set next_nodes relationships)
        self._connect_bracket_nodes(nodes)
        
        return nodes
```

#### `progression_engine.py`
```python
class ProgressionEngine:
    """Handle automatic team progression through brackets."""
    
    async def advance_winner(self, match: Match) -> None:
        """Advance winning team to next match/node."""
        if not match.winner_id:
            return
        
        # Get parent node
        node = await self._get_node_by_uuid(match.node_uuid)
        
        # Determine next node based on bracket position
        next_node_uuid = node.next_nodes.get("winner")
        if not next_node_uuid:
            return  # No advancement (e.g., grand final)
        
        next_node = await self._get_node(next_node_uuid)
        
        # Update next match with qualified team
        await self._assign_team_to_match(next_node, match.winner_id)
        
        # Check if tournament is complete
        await self._check_tournament_completion(node.tournament_id)
```

### Data Access Layer

**Purpose:** Abstract database operations

**Responsibilities:**
1. Async database operations via SQLAlchemy 2.0
2. Connection pooling management
3. Query optimization (eager loading, avoiding N+1)
4. Transaction management

**Repository Pattern Example:**

```python
class TournamentRepository:
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def get_by_id(self, tournament_id: UUID) -> Optional[Tournament]:
        result = await self.session.execute(
            select(Tournament)
            .options(
                selectinload(Tournament.teams),
                selectinload(Tournament.nodes).selectinload(Node.matches)
            )
            .where(Tournament.id == tournament_id)
        )
        return result.scalar_one_or_none()
    
    async def get_with_full_bracket(self, tournament_id: UUID) -> Optional[Tournament]:
        """Get tournament with complete bracket graph."""
        result = await self.session.execute(
            select(Tournament)
            .options(
                selectinload(Tournament.teams),
                selectinload(Tournament.nodes)
                    .selectinload(Node.matches)
                    .selectinload(Match.team_a),
                selectinload(Tournament.nodes)
                    .selectinload(Node.matches)
                    .selectinload(Match.team_b)
            )
            .where(Tournament.id == tournament_id)
        )
        return result.scalar_one_or_none()
```

## Data Flow Examples

### Creating a Tournament

```
Client Request
    │
    ▼
┌─────────────────────────────────────────┐
│ API Layer                               │
│  POST /tournaments                      │
│  ├─ Validate API Key (middleware)       │
│  ├─ Validate Request Body (Pydantic)    │
│  └─ Call Tournament Service             │
└─────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────┐
│ Service Layer                           │
│  TournamentService.create_tournament()  │
│  ├─ Validate Schema IDs                 │
│  ├─ Create Tournament Entity            │
│  ├─ Generate Bracket (BracketEngine)    │
│  ├─ Save to Database                    │
│  └─ Log Audit Event                     │
└─────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────┐
│ Data Access Layer                       │
│  TournamentRepository.save()            │
│  └─ SQLAlchemy Async Session            │
└─────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────┐
│ Database                                │
│  INSERT into tournaments                │
│  INSERT into nodes                      │
│  INSERT into audit_log                  │
└─────────────────────────────────────────┘
    │
    ▼
Response to Client (201 Created)
```

### Updating Match Score (with Real-time Update)

```
Judge Updates Score
    │
    ▼
┌─────────────────────────────────────────┐
│ API Layer                               │
│  PUT /matches/{match_id}/score          │
│  ├─ Validate API Key                    │
│  ├─ Validate Score vs Match Schema      │
│  └─ Call Match Service                  │
└─────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────┐
│ Service Layer                           │
│  MatchService.update_score()            │
│  ├─ Validate Score Format               │
│  ├─ Update Match Entity                 │
│  ├─ Determine Winner                    │
│  ├─ Trigger Progression (if complete)   │
│  ├─ Save to Database                    │
│  ├─ Log Audit Event                     │
│  └─ Broadcast WebSocket Event           │
└─────────────────────────────────────────┘
    │                           │
    ▼                           ▼
┌─────────────────┐     ┌───────────────────┐
│ Database        │     │ WebSocket Clients │
│ UPDATE matches  │     │ (Overlays, etc.)  │
│ INSERT audit    │     │ Real-time update  │
└─────────────────┘     └───────────────────┘
```

## Error Handling Strategy

```python
# Custom exception hierarchy
class TournamentException(Exception):
    """Base exception for tournament system."""
    pass

class SchemaValidationError(TournamentException):
    """Raised when JSON Schema validation fails."""
    pass

class SchemaLockError(TournamentException):
    """Raised when attempting to change locked schema."""
    pass

class BracketIntegrityError(TournamentException):
    """Raised when bracket structure is invalid."""
    pass

class PermissionDeniedError(TournamentException):
    """Raised when API key lacks required permissions."""
    pass

# Exception handlers in API layer
@app.exception_handler(SchemaValidationError)
async def schema_validation_handler(request: Request, exc: SchemaValidationError):
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"detail": str(exc)}
    )

@app.exception_handler(PermissionDeniedError)
async def permission_handler(request: Request, exc: PermissionDeniedError):
    return JSONResponse(
        status_code=status.HTTP_403_FORBIDDEN,
        content={"detail": "Insufficient permissions"}
    )
```

## Performance Considerations

### Database Optimization

1. **Eager Loading**: Always use `selectinload()` or `joinedload()` to prevent N+1 queries
2. **Indexing**: GIN indexes on JSONB columns for efficient querying
3. **Connection Pooling**: Configure appropriate pool size for workload
4. **Batch Operations**: Use bulk inserts/updates where possible

### Caching Strategy

1. **Tournament State**: Cache frequently accessed tournament bracket data
2. **Schema Definitions**: Cache JSON Schemas to avoid repeated database lookups
3. **Invalidation**: Clear cache on write operations via WebSocket events

### WebSocket Scaling

1. **Room-based Subscriptions**: Clients subscribe only to relevant tournaments
2. **Event Batching**: Batch rapid updates to reduce message volume
3. **Backpressure**: Implement message queues for high-traffic scenarios

## Next Steps

Continue reading:
- [Data Model](./04-data-model.md) - Detailed entity specifications
- [API Reference](./05-api-reference.md) - Complete endpoint documentation
