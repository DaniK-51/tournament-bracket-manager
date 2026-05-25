# Tournament Bracket Manager Implementation Plan

This document outlines the implementation plan for the tournament bracket manager backend application based on the requirements in IDEA.md and the development standards in AGENTS.md.

## Architecture Overview

The application will follow a clean architecture pattern with the following layers:

1. **API Layer**: FastAPI routes and controllers
2. **Service Layer**: Business logic and orchestration
3. **Repository Layer**: Data access and persistence
4. **Database Layer**: PostgreSQL storage

The application will be containerized using Docker and will expose a RESTful API for managing tournaments, matches, and nodes in a tournament bracket.

## Data Model

### Tournament Entity
- id: int (6-digit number)
- name: str
- discipline: str
- created_at: DateTime
- updated_at: DateTime
- bracket: directed graph (stored as JSONB)

### Node Entity
- uuid: UUID
- type: Enum["stage_match", "round_robin_group", "final_position"]
- metadata: JSONB (flexible storage for node-specific data)
- winner_next_node_uuid: UUID (reference to next node for winner)
- loser_next_node_uuid: UUID (reference to next node for loser)
- position_next_node_uuids: Dict[int, UUID] (for group nodes, mapping position to next node)
- matches: List[UUID] (references to matches within this node)
- created_at: DateTime
- updated_at: DateTime

### Match Entity
- uuid: UUID
- metadata: JSONB (flexible storage for match-specific data like teams, scores, etc.)
- created_at: DateTime
- updated_at: DateTime

The directed graph structure of the tournament bracket will be represented by nodes that contain references to other nodes, allowing for complex tournament structures including single elimination, double elimination, round-robin groups, and hybrid formats.

## API Endpoints

### Tournament Management
- `POST /tournament/new` - Create a new tournament
- `GET /tournament/{ID}` - Retrieve a tournament by ID
- `PUT /tournament/{ID}` - Update a tournament
- `DELETE /tournament/{ID}` - Delete a tournament

### Node Management
- `POST /tournament/{ID}/node/new` - Create a new node in a tournament
- `GET /node/{UUID}` or `GET /tournament/{ID}/node/{UUID}` - Retrieve a node
- `PUT /node/{UUID}` or `PUT /tournament/{ID}/node/{UUID}` - Update a node
- `DELETE /node/{UUID}` or `DELETE /tournament/{ID}/node/{UUID}` - Delete a node

### Match Management
- `POST /tournament/{ID}/match/new` - Create a new match in a tournament
- `GET /match/{UUID}` or `GET /tournament/{ID}/match/{UUID}` - Retrieve a match
- `PUT /match/{UUID}` or `PUT /tournament/{ID}/match/{UUID}` - Update a match
- `DELETE /match/{UUID}` or `DELETE /tournament/{ID}/match/{UUID}` - Delete a match

### WebSocket Endpoints
- `wss://<host>/ws` - Main WebSocket endpoint for real-time updates

**Client to Server Messages:**
- `tournament.subscribe` / `tournament.unsubscribe`
- `match.subscribe` / `match.unsubscribe` / `match.get`
- `node.subscribe` / `node.unsubscribe` / `node.get`

**Server to Client Messages:**
- `tournament.snapshot` / `tournament.updated`
- `match.snapshot` / `match.updated` / `match.created` / `match.deleted` / `match.response`
- `node.snapshot` / `node.updated` / `node.created` / `node.deleted` / `node.response`
- `error`

## Implementation Approach

The implementation will follow the technology stack and code structure specified in AGENTS.md:

1. **Framework**: FastAPI for building the REST API with automatic OpenAPI/Swagger documentation
2. **Language**: Python 3.9+ with type hints and Pydantic for data validation
3. **Database**: PostgreSQL with SQLAlchemy ORM for data persistence
4. **Containerization**: Docker for consistent development and deployment environments
5. **WebSocket Support**: FastAPI's built-in WebSocket capabilities for real-time communication

The WebSocket implementation will follow the same clean architecture pattern:

1. **WebSocket Layer**: FastAPI WebSocket endpoints and connection management
2. **Event Service Layer**: Business logic for handling WebSocket events and subscriptions
3. **Broadcast Service**: Real-time update broadcasting to subscribed clients
4. **Message Format**: JSON-based messages with proper typing and validation using Pydantic models

## Project Structure

```
src/
├── main.py                # FastAPI application entry point
├── api/
│   ├── __init__.py
│   └── v1/
│       ├── __init__.py
│       ├── routes/
│       │   ├── __init__.py
│       │   ├── tournament.py
│       │   └── websocket.py     # WebSocket routes and handlers
│       └── dependencies.py
├── models/
│   ├── __init__.py
│   ├── tournament.py        # Pydantic models for tournament entities
│   ├── websocket.py         # Pydantic models for WebSocket messages
│   └── events.py            # Pydantic models for event payloads
├── schemas/
│   ├── __init__.py
│   └── tournament.py        # Database models (SQLAlchemy)
├── services/
│   ├── __init__.py
│   ├── tournament_service.py # Business logic for tournament operations
│   └── websocket_service.py  # Business logic for WebSocket events and broadcasting
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
    ├── test_tournament.py   # Test cases for tournament API
    └── test_websocket.py    # Test cases for WebSocket functionality
```

## Implementation Steps

1. **Project Setup**
   - Create the project directory structure
   - Initialize Git repository
   - Create requirements.txt with dependencies
   - Set up Docker and docker-compose files
   - Include WebSocket dependencies in requirements.txt (e.g., websockets, fastapi-websocket)

2. **WebSocket Implementation**
   - Create WebSocket endpoint at `wss://<host>/ws`
   - Implement connection management and subscription handling
   - Develop message routing for tournament, match, and node events
   - Implement real-time update broadcasting for subscribed clients
   - Add request-response correlation using `id` field
   - Ensure proper error handling and message validation

3. **Database Configuration**
   - Configure PostgreSQL connection
   - Define SQLAlchemy models for Tournament, Node, and Match entities
   - Implement database session management

4. **Database Configuration**
   - Configure PostgreSQL connection
   - Define SQLAlchemy models for Tournament, Node, and Match entities
   - Implement database session management

5. **Core Models**
   - Create Pydantic models for request/response validation
   - Define database schemas using SQLAlchemy
   - Implement the directed graph structure for tournament brackets

6. **Repository Layer**
   - Implement data access methods for CRUD operations
   - Create repository classes for Tournament, Node, and Match entities
   - Ensure proper error handling and validation

7. **Service Layer**
   - Implement business logic for tournament management
   - Create services for handling complex operations like bracket generation
   - Ensure proper validation and error handling

8. **API Layer**
   - Define API routes using FastAPI
   - Implement route handlers for all endpoints
   - Add proper request validation and response formatting
   - Include comprehensive API documentation

9. **Testing**
   - Write unit tests for models, services, and repositories
   - Create integration tests for API endpoints
   - Implement test fixtures for database operations
   - Ensure 80%+ test coverage

10. **Documentation**
   - Generate OpenAPI documentation
   - Create README with setup instructions
   - Document API usage examples

11. **Deployment Preparation**
   - Create production Docker configuration
   - Set up CI/CD pipeline
   - Prepare environment variables and configuration

## Timeline

- Day 1-2: Project setup and database configuration
- Day 3: WebSocket implementation and connection management
- Day 4: Core models and repository layer implementation
- Day 5-6: Service layer and business logic (including WebSocket event services)
- Day 7-8: API layer and endpoint implementation (REST and WebSocket)
- Day 9: Testing and test coverage (including WebSocket functionality)
- Day 10: Documentation and final preparations

## Risk Assessment

1. **Complex Graph Operations**: The directed graph structure for tournament brackets may require complex traversal algorithms. Mitigation: Implement comprehensive unit tests for graph operations and use established graph libraries if needed.

2. **Data Consistency**: Ensuring data consistency across related entities (tournaments, nodes, matches) is critical. Mitigation: Use database transactions and implement proper validation in the service layer.

3. **Performance**: Large tournaments with many matches and nodes could impact performance. Mitigation: Implement proper indexing on frequently queried fields and consider caching strategies for read-heavy operations.

4. **API Complexity**: The API needs to handle various tournament formats. Mitigation: Design a flexible data model using JSONB for metadata and implement clear API documentation with examples.

5. **WebSocket Scalability**: Real-time updates for multiple clients could impact server performance under high load. Mitigation: Implement connection pooling, message batching, and consider using Redis for pub/sub in production.

6. **Message Ordering and Reliability**: Ensuring proper message ordering and delivery in WebSocket communication. Mitigation: Implement message sequencing with the `id` field and acknowledge mechanism for critical operations.

By following this plan and the standards outlined in AGENTS.md, we will create a robust, scalable tournament bracket manager that can handle various tournament formats and integrate seamlessly with overlay applications.
