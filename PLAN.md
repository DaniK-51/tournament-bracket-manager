# Tournament Management System - AI Agent Implementation Plan

> **Document Purpose**: This plan is optimized for AI agent implementation. Each section contains explicit, unambiguous specifications. AI agents should follow phases sequentially, validating each step before proceeding.

## Executive Summary

Build a universal tournament management backend that handles **ANY competition format** across **ALL disciplines** (esports, traditional sports, virtual competitions, IRL events, battle royale, racing, etc.). 

**Key Innovation**: A runtime-configurable JSON Schema registry allows organizers to define discipline-specific data formats without code changes. The system stores brackets as directed graphs and validates all data against schemas locked at tournament creation.

---

## Core Principles

1. **Maximum Flexibility**: Support every tournament format imaginable
2. **Runtime Schema Evolution**: Data formats changeable without redeployment
3. **Graph-Based Brackets**: Store tournament structure as directed graph with UUID references
4. **External Overlay Architecture**: This service stores data only; overlays render externally
5. **Schema Locking**: Tournaments lock to specific schema versions to prevent breaking changes
6. **Complete Audit Trail**: Every change tracked with full history
7. **High Performance**: Target 1000 concurrent big tournaments with sub-100ms read latency

---

## Technology Stack (Fixed)

| Component | Technology | Version | Notes |
|-----------|-----------|---------|-------|
| Language | Python | 3.11+ | Type hints required |
| Framework | FastAPI | Latest | Swagger UI optional |
| Database | PostgreSQL | 15+ | JSONB + JSON Schema validation |
| Async Driver | asyncpg | Latest | Via SQLAlchemy 2.0 Async |
| ORM | SQLAlchemy | 2.0+ | Async mode only |
| Migrations | Alembic | Latest | Auto-generate where possible |
| Validation | jsonschema + Pydantic V2 | Latest | Runtime JSON Schema validation |
| Real-time | WebSocket | Native | FastAPI WebSocket |
| Auth | API Keys | Custom | Hashed with bcrypt |
| Containerization | Docker + Docker Compose | Latest | Multi-stage builds |
| Testing | pytest + httpx | Latest | Async test support |

**Forbidden**: Synchronous database drivers, ORMs without async support, MongoDB/NoSQL (except JSONB), GraphQL

---

## System Architecture

### Layer Diagram

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

### Core Components Specification

#### 1. API Layer (FastAPI)

**Responsibilities**:
- Route HTTP requests to appropriate service methods
- Handle WebSocket connections for real-time updates
- Validate API keys and enforce role-based permissions
- Perform runtime JSON Schema validation against tournament-specific schemas
- Serialize/deserialize data between JSON and Python objects

**Key Files** (AI Agent Implementation Target):
```
src/api/
├── __init__.py
├── main.py                 # FastAPI app initialization
├── routes/
│   ├── __init__.py
│   ├── tournaments.py      # Tournament CRUD + schema locking logic
│   ├── teams.py            # Team registration with schema validation
│   ├── nodes.py            # Bracket graph manipulation
│   ├── matches.py          # Match scoring with schema validation
│   ├── schemas.py          # Schema registry CRUD operations
│   ├── auth.py             # API key management
│   └── audit.py            # Audit log retrieval
├── websocket/
│   ├── __init__.py
│   ├── manager.py          # Connection manager + room subscriptions
│   └── events.py           # Event types and serialization
└── middleware/
    ├── __init__.py
    └── auth.py             # API key authentication
```

#### 2. Service/Business Logic Layer

**Responsibilities**:
- Implement tournament creation workflows
- Generate bracket structures (Single/Double Elim, Round Robin, Swiss)
- Calculate standings and progression logic
- Enforce schema locking rules
- Trigger audit log entries
- Broadcast WebSocket events on state changes

**Key Files**:
```
src/services/
├── __init__.py
├── tournament_service.py   # Create, update, archive tournaments
├── bracket_engine.py       # Generate and manipulate bracket graphs
├── match_service.py        # Score updates, status transitions
├── team_service.py         # Registration, roster management
├── schema_registry_service.py  # Schema CRUD, versioning, validation
├── progression_engine.py   # Auto-advance winners, handle tiebreakers
└── audit_service.py        # Write audit logs, retrieve history
```

#### 3. Data Access Layer

**Responsibilities**:
- Async database operations via SQLAlchemy 2.0
- Connection pooling management
- Query optimization (eager loading, avoiding N+1)
- Transaction management

**Key Files**:
```
src/db/
├── __init__.py
├── session.py              # Async session factory
├── models/
│   ├── __init__.py
│   ├── base.py             # Base model with common fields
│   ├── tournament.py       # Tournament model
│   ├── team.py             # Team model
│   ├── node.py             # Node (bracket building block) model
│   ├── match.py            # Match model
│   ├── schema_registry.py  # JSON Schema registry model
│   ├── api_key.py          # API key model
│   └── audit_log.py        # Audit trail model
└── repositories/
    ├── __init__.py
    ├── tournament_repo.py  # Complex tournament queries
    ├── team_repo.py
    ├── match_repo.py
    └── schema_repo.py
```

#### 4. Database Layer (PostgreSQL)

**Critical Design Decisions**:
- All entities use UUID primary keys (uuid_generate_v4())
- JSONB columns for flexible data with application-level JSON Schema validation
- GIN indexes on JSONB columns for efficient querying
- Separate `schema_registry` table stores JSON Schema definitions
- `audit_log` table captures every mutation with before/after snapshots
- Foreign keys enforce referential integrity; cascade deletes where appropriate

---

## Data Model

### Schema Registry Entity (NEW - Core Flexibility Mechanism)
- `id` (UUID): Unique identifier
- `name`: Schema name (e.g., "csgo_best_of_3", "chess_classical", "mobba_5v5")
- `discipline`: String (e.g., "CS:GO", "Chess", "League of Legends")
- `target_entity`: Enum (`TEAM`, `MATCH`, `TOURNAMENT`) - which entity this schema validates
- `version`: Integer (auto-incremented per schema name)
- `json_schema`: JSONB - Full JSON Schema definition for validation
- `is_active`: Boolean - whether new tournaments can use this version
- `created_at`, `updated_at`: Timestamps
- `created_by`: UUID of API key that created it

**Example JSON Schema for CS:GO Match:**
```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "properties": {
    "team_a_score": {"type": "integer", "minimum": 0},
    "team_b_score": {"type": "integer", "minimum": 0},
    "maps": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "map_name": {"type": "string"},
          "team_a_score": {"type": "integer"},
          "team_b_score": {"type": "integer"},
          "winner": {"type": "string", "enum": ["a", "b"]}
        },
        "required": ["map_name", "team_a_score", "team_b_score", "winner"]
      }
    },
    "veto_order": {"type": "array", "items": {"type": "string"}}
  },
  "required": ["team_a_score", "team_b_score"]
}
```

### Tournament Entity
- `id` (UUID): Primary identifier
- `name`: Tournament name
- `discipline`: String (e.g., "CS:GO", "LoL", "Chess")
- `format_config` (JSONB): Format-specific rules 
  - Example: `{"type": "double_elim", "grand_final_reset": true}`
- `metadata`: **Reference to schema versions** + flexible data
  - `team_schema_id`: UUID → which schema validates team data
  - `match_schema_id`: UUID → which schema validates match scores
  - `custom_fields`: JSONB for additional tournament-specific data
- `created_at`, `updated_at`: Timestamps

**Key Point:** Once a tournament starts, schema references are LOCKED. Changing schemas requires creating a new tournament or explicit migration.

### Team Entity
- `id` (UUID): Unique identifier
- `tournament_id` (UUID): Reference to parent tournament
- `name`: Team name
- `players` (JSONB): **Validated against tournament's team_schema**
  - Simple: `["Player1", "Player2"]`
  - Structured: `[{"id": "...", "ign": "Player1", "real_name": "...", "role": "captain"}]`
  - IRL Sports: `[{"number": 10, "position": "forward", "name": "John Doe"}]`
  - Virtual/Esports: `[{"steam_id": "...", "ign": "...", "rank": 2500}]`
- `seed`: Seeding information (optional)
- `metadata` (JSONB): **Validated against tournament's team_schema** - discipline-specific data
  - Esports: `{"logo_url": "...", "region": "EU", "social_links": {...}}`
  - IRL Sports: `{"jersey_color": "red", "home_venue": "...", "coach": "..."}`
  - Chess: `{"fide_rating": 2500, "title": "GM"}`

### Node Entity (Bracket Building Block)
- `uuid` (UUID): Unique identifier (used in API endpoints)
- `tournament_id` (UUID): Reference to parent tournament
- `node_type`: Enum (`STANDARD`, `ROUND_ROBIN_GROUP`, `FINAL`, `CONSOLATION`, `SWISS_ROUND`, `GROUP_STAGE`)
  - **Round Robin exists as a specific node type** containing multiple matches
  - **Swiss Round node type** for Swiss format tournaments
  - Extensible for any competition structure
- `stage_info` (JSONB): 
  - `stage_number`: int
  - `group_letter`: str (optional, e.g., "A", "B")
  - `round_number`: int (for Swiss)
  - `description`: str
- `matches`: List of match UUIDs belonging to this node
- `next_nodes` (JSONB/Relationship): Map of position/outcome → next node UUID
  - Standard: `{"winner": "uuid-abc", "loser": "uuid-def"}`
  - Round Robin: `{"1st": "uuid-ghi", "2nd": "uuid-jkl", "3rd": "uuid-mno"}`
  - Swiss: `{"score_3_0": "uuid-pqr", "score_2_1": "uuid-stu"}`
- `overlay_config` (JSONB): Hints for external overlay software
  - Example: `{"position": "top_left", "label": "Winners Final", "priority": 1}`
  - *Note: Actual overlay rendering happens in separate software*
- `metadata` (JSONB): Additional node-specific data (not validated, free-form)

### Match Entity
- `uuid` (UUID): Unique identifier
- `node_uuid` (UUID): Reference to parent node
- `team_a_id` (UUID, nullable): First participant
- `team_b_id` (UUID, nullable): Second participant (nullable for byes or multi-team matches)
- `participants` (JSONB, nullable): For multi-team/multi-player matches
  - Example: `[{"team_id": "...", "position": 1}, {"team_id": "...", "position": 2}]`
- `score` (JSONB): **Validated against tournament's match_schema**
  - Best of 3 (CS:GO): `{"team_a": 2, "team_b": 1, "maps": [{"map": "Dust2", "winner": "a"}, ...]}`
  - Points (Basketball): `{"team_a": 98, "team_b": 95, "quarters": [...]}`
  - Chess: `{"white": 1, "black": 0, "moves": 45, "opening": "Sicilian Defense"}`
  - Multi-team Battle Royale: `{"teams": [{"id": "...", "placement": 1, "kills": 10}, ...]}`
  - Virtual Racing: `{"laps": [...], "best_time": "1:23.456", "penalties": 0}`
- `status`: Enum (`scheduled`, `in_progress`, `completed`, `cancelled`, `postponed`)
- `start_time`: Scheduled start time (nullable)
- `end_time`: Actual end time (nullable)
- `metadata` (JSONB): **Validated against tournament's match_schema** - discipline-specific data
  - Esports: VOD link, server IP, map veto order, round history
  - IRL Sports: venue, referee, attendance, weather conditions
  - Chess: time control, opening eco code, PGN link
- `winner_id` (UUID, nullable): Points to winning team for progression logic
- `result_metadata` (JSONB): Computed results for standings
  - Points earned, tiebreaker values, etc.

### API Key Entity
- `id` (UUID): Unique identifier
- `key_hash`: Hashed API key
- `role`: Enum (`admin`, `organizer`, `judge`, `overlay_director`)
- `tournament_id` (UUID, nullable): Scope of access (null = all tournaments)
- `permissions` (JSONB): Fine-grained permissions override
  - Example: `{"can_edit_schemas": false, "can_delete_matches": true}`
- `created_at`: Timestamp
- `expires_at`: Optional expiration

## API Endpoints

### Schema Registry Operations (NEW - Core Flexibility)
- `GET /schemas` - List all available schemas (filterable by discipline, entity type)
- `POST /schemas` - Create new schema version
  - Body: `{name, discipline, target_entity, json_schema}`
  - Auto-increments version if name exists
- `GET /schemas/{id}` - Get specific schema with full JSON Schema definition
- `PUT /schemas/{id}` - Update schema (creates new version, never modifies existing)
- `PATCH /schemas/{id}/deactivate` - Mark schema as inactive (new tournaments can't use it)
- `POST /schemas/validate` - Validate JSON data against a schema (utility endpoint)
  - Body: `{schema_id, data}`
  - Returns: `{valid: bool, errors: [...]}`

### Tournament Management
- `POST /tournaments` - Create new tournament
  - Body: `{name, discipline, format_config, metadata: {team_schema_id, match_schema_id}}`
- `GET /tournaments/{id}` - Get tournament details with full bracket graph
- `PUT /tournaments/{id}` - Update tournament metadata/config
  - **Note**: Cannot change schema references after first team/match is created
- `DELETE /tournaments/{id}` - Archive/delete tournament
- `GET /tournaments` - List all tournaments (filterable by discipline, status, date)

### Team Operations
- `POST /tournaments/{id}/teams` - Register team
  - Body: `{name, seed, players, metadata}` - **Validated against tournament's team_schema**
  - Returns validation errors if data doesn't match schema
- `GET /tournaments/{id}/teams` - List all teams in tournament
- `GET /teams/{uuid}` - Get specific team details
- `PUT /teams/{uuid}` - Update team roster/metadata (validated against schema)
- `DELETE /teams/{uuid}` - Remove team from tournament
- `POST /teams/bulk-import` - Import multiple teams from CSV/JSON
  - Validates each row against schema, reports per-row errors

### Node & Bracket Operations
- `POST /tournaments/{id}/nodes` - Add new node to bracket
  - Body: `{type: "ROUND_ROBIN_GROUP"|"SWISS_ROUND"|..., stage_info: {...}, overlay_config: {...}}`
- `GET /tournaments/{id}/bracket` - Get full bracket graph structure
- `GET /nodes/{uuid}` - Get specific node details with matches
- `PUT /nodes/{uuid}` - Update node configuration
- `POST /nodes/{uuid}/connect` - Define edges (link nodes together)
  - Body: `{winner_next: "uuid", loser_next: "uuid"}` or `{position_map: {"1st": "uuid", "2nd": "uuid"}}`
  - Supports complex mappings for Round Robin, Swiss, etc.

### Match Operations
- `GET /nodes/{uuid}/matches` - List all matches in a node
- `POST /nodes/{uuid}/matches` - Create match within node
  - Body: `{team_a_id, team_b_id, start_time, metadata}` - metadata validated against schema
- `GET /matches/{uuid}` - Get specific match details
- `PATCH /matches/{uuid}` - Update match score/status (Judge/Organizer only)
  - Body: `{score: {...}, status: "completed", winner_id: "uuid"}` - **score validated against tournament's match_schema**
  - Returns validation errors if score format doesn't match schema
- `POST /matches/{uuid}/finalize` - Confirm result and trigger progression logic
- `POST /matches/bulk-update` - Batch update multiple match results

### Real-time Updates
- `WS /ws/tournaments/{id}` - WebSocket for real-time bracket updates
  - Events: `match.updated`, `match.created`, `node.changed`, `team.registered`, `schema.changed`
  - Authentication: API key required for Overlay Director role (viewers can connect without auth if public)
  - Messages include schema version info for client-side validation

### Authentication (Admin Only)
- `POST /auth/api-keys` - Generate new API key
  - Body: `{role: "judge", tournament_id: "optional-uuid", expires_at: "optional", permissions: {...}}`
- `GET /auth/api-keys` - List all API keys
- `DELETE /auth/api-keys/{key_id}` - Revoke API key

### Audit & History
- `GET /tournaments/{id}/audit` - Get full audit trail for a tournament
- `GET /audit/{entity_type}/{entity_id}` - Get history of specific entity
- `GET /audit?api_key_id={key_id}&from={date}&to={date}` - Filter by actor and date range
- `POST /audit/export` - Export audit log for compliance/archival

## AI Agent Implementation Phases

> **Instructions for AI Agents**: Complete phases sequentially. Each phase has explicit acceptance criteria. Do not proceed to the next phase until all checkboxes are marked complete and tests pass.

### Phase 1: Foundation & Schema Registry (Week 1-2)

**Goal**: Working database schema, basic API, schema registry operational

#### Tasks
- [ ] **1.1 Project Scaffolding**
  - Create directory structure per Architecture section
  - Initialize `pyproject.toml` with dependencies (FastAPI, SQLAlchemy, asyncpg, alembic, jsonschema, pytest)
  - Configure Docker Compose (PostgreSQL 15 + app service)
  - Set up `.env.example` with all required environment variables
  - Create `.gitignore` for Python/Docker

- [ ] **1.2 Database Models**
  - Implement all SQLAlchemy 2.0 async models:
    - `SchemaRegistry` (json_schema JSONB, versioning fields)
    - `Tournament` (format_config JSONB, metadata with schema references)
    - `Team` (players JSONB, metadata JSONB)
    - `Node` (node_type enum, stage_info JSONB, next_nodes JSONB)
    - `Match` (score JSONB, status enum, result_metadata JSONB)
    - `ApiKey` (key_hash, role enum, permissions JSONB)
    - `AuditLog` (entity_type, entity_id, action, before/after JSONB, api_key_id)
  - All models must have `created_at`, `updated_at` timestamps
  - All primary keys must be UUID

- [ ] **1.3 Alembic Migrations**
  - Generate initial migration creating all tables
  - Add GIN indexes on all JSONB columns
  - Add indexes on foreign key columns
  - Verify migration runs cleanly on fresh database

- [ ] **1.4 Schema Registry Service**
  - Implement `SchemaRegistryService` with methods:
    - `create_schema(name, discipline, target_entity, json_schema)` → auto-increments version
    - `get_schema(schema_id)` → returns full schema with version
    - `list_schemas(discipline_filter, entity_filter, active_only)` 
    - `validate_data(schema_id, data)` → returns `{valid: bool, errors: list}`
    - `deactivate_schema(schema_id)` → marks as inactive
  - Write unit tests for each method

- [ ] **1.5 API Key Authentication**
  - Implement `ApiKeyMiddleware` that:
    - Extracts `X-API-Key` header
    - Hashes and validates against database
    - Attaches `api_key` object to request state
    - Enforces role-based access (viewers exempt)
  - Implement `/auth/api-keys` CRUD endpoints (Admin only)
  - Write integration tests for auth flow

- [ ] **1.6 Basic Tournament CRUD**
  - Implement `/tournaments` POST/GET/PUT/DELETE endpoints
  - On tournament creation, validate that referenced `team_schema_id` and `match_schema_id` exist
  - Implement schema locking: prevent changing schema references after first team/match exists
  - Write integration tests

#### Acceptance Criteria
- [ ] Docker Compose starts app + PostgreSQL successfully
- [ ] All migrations apply without errors
- [ ] Can create schema via API, retrieve it, validate sample data against it
- [ ] Can create API key, use it to authenticate requests
- [ ] Can create tournament with schema references, verify locking works
- [ ] All endpoints return proper error codes (400, 401, 403, 404, 500)
- [ ] Unit test coverage > 80% for services layer

---

### Phase 2: Bracket Engine & Node Management (Week 3-4)

**Goal**: Full bracket graph manipulation, Round Robin node type working

#### Tasks
- [ ] **2.1 Node CRUD Endpoints**
  - Implement `/tournaments/{id}/nodes` POST/GET
  - Implement `/nodes/{uuid}` GET/PUT
  - Support all node types: `STANDARD`, `ROUND_ROBIN_GROUP`, `FINAL`, `CONSOLATION`, `SWISS_ROUND`, `GROUP_STAGE`
  - Validate `stage_info` structure per node type

- [ ] **2.2 Graph Connectivity**
  - Implement `/nodes/{uuid}/connect` endpoint
  - Support flexible edge definitions:
    - Standard: `{winner_next: "uuid", loser_next: "uuid"}`
    - Round Robin: `{position_map: {"1st": "uuid", "2nd": "uuid", ...}}`
    - Swiss: `{score_mapping: {"3-0": "uuid", "2-1": "uuid"}}`
  - Validate no cycles introduced in graph
  - Validate referenced nodes exist in same tournament

- [ ] **2.3 Bracket Generation Service**
  - Implement `BracketEngine.generate_single_elim(teams, seed_order)` → returns list of nodes
  - Implement `BracketEngine.generate_double_elim(teams, seed_order)` → returns list of nodes with winner/loser brackets
  - Implement `BracketEngine.generate_round_robin(teams, group_size)` → returns Round Robin group nodes
  - Auto-generate matches within Round Robin groups (n*(n-1)/2 matches per group)
  - Write unit tests verifying correct number of rounds/matches

- [ ] **2.4 Round Robin Standings Logic**
  - Implement `RoundRobinService.calculate_standings(group_node_uuid)` 
  - Support configurable point systems via `format_config`:
    - Default: win=3, draw=1, loss=0
    - Custom: defined in tournament's `format_config`
  - Handle tiebreakers (head-to-head, goal differential, etc.)
  - Return sorted standings with qualification positions

- [ ] **2.5 Audit Integration**
  - Ensure every node create/update/delete writes to `audit_log`
  - Include before/after snapshots
  - Implement `/tournaments/{id}/audit` endpoint with filtering

#### Acceptance Criteria
- [ ] Can create Single Elim bracket for 8 teams (7 nodes, 7 matches)
- [ ] Can create Double Elim bracket for 8 teams (15 nodes, 15 matches)
- [ ] Can create Round Robin group for 4 teams (6 matches), calculate standings
- [ ] Can connect nodes with complex position mappings
- [ ] Graph validation rejects cycles and cross-tournament references
- [ ] Audit log captures all changes with accurate before/after data
- [ ] Integration tests cover all bracket generation scenarios

---

### Phase 3: Match Management & Runtime Validation (Week 5)

**Goal**: Full match lifecycle with schema-validated scoring

#### Tasks
- [ ] **3.1 Match CRUD Endpoints**
  - Implement `/nodes/{uuid}/matches` POST/GET
  - Implement `/matches/{uuid}` GET/PATCH
  - Support nullable participants (byes, TBD teams)
  - Support multi-team matches via `participants` JSONB

- [ ] **3.2 Schema-Validated Scoring**
  - On match score update, retrieve tournament's `match_schema_id`
  - Fetch JSON Schema from registry
  - Validate submitted score against schema using `jsonschema` library
  - Return detailed validation errors if invalid
  - Examples to test:
    - CS:GO Bo3: `{team_a: 2, team_b: 1, maps: [...]}`
    - Chess: `{white: 1, black: 0, moves: 45}`
    - Basketball: `{team_a: 98, team_b: 95, quarters: [...]}`
    - Battle Royale: `{teams: [{id, placement, kills}]}`

- [ ] **3.3 Match Status Workflow**
  - Implement state machine: `scheduled` → `in_progress` → `completed`
  - Allow transitions: `scheduled` ↔ `in_progress`, `in_progress` → `completed`, any → `cancelled`/`postponed`
  - Validate status transitions (e.g., can't complete a match with no score)
  - Judge/Organizer roles only can update scores

- [ ] **3.4 Progression Engine**
  - Implement `ProgressionEngine.on_match_completed(match_uuid)`
  - Determine winner based on score (respecting schema structure)
  - Update `winner_id` on match
  - Look up next node(s) based on graph edges
  - Auto-advance winner to next match if opponent already determined
  - Handle Round Robin: update standings, check if group complete

- [ ] **3.5 Bulk Operations**
  - Implement `POST /teams/bulk-import`:
    - Accept CSV or JSON array
    - Validate each row against team schema
    - Report per-row errors, partial success
    - Atomic transaction: all-or-nothing or skip failures option
  - Implement `GET /tournaments/{id}/export`:
    - Export full tournament state (teams, nodes, matches, results)
    - Portable JSON format for backup/migration

#### Acceptance Criteria
- [ ] Score validation rejects data not matching tournament's schema
- [ ] Can update match through full lifecycle with audit trail
- [ ] Completing a match auto-advances winner to next round
- [ ] Round Robin standings update automatically on match completion
- [ ] Bulk import handles 100+ teams with detailed error reporting
- [ ] Export produces valid JSON with full tournament state
- [ ] Role permissions enforced (Judge can score, Viewer cannot)

---

### Phase 4: Real-Time Updates & Performance (Week 6)

**Goal**: WebSocket real-time updates, optimized for high load

#### Tasks
- [ ] **4.1 WebSocket Manager**
  - Implement connection manager with room subscriptions (per tournament)
  - Support authentication: API key for Overlay Director, optional for viewers
  - Handle reconnection with last-event-ID resumption
  - Implement heartbeat/ping-pong for connection health

- [ ] **4.2 Event Broadcasting**
  - Define event types: `match.created`, `match.updated`, `match.completed`, `node.changed`, `team.registered`, `standings.updated`
  - Broadcast events to all subscribed clients on state changes
  - Include schema version info in events for client-side validation
  - Debounce rapid updates (batch within 100ms window)

- [ ] **4.3 Performance Optimization**
  - Implement Redis caching for frequently-read tournament brackets
  - Cache TTL: 30 seconds, invalidate on write
  - Optimize N+1 queries with `selectinload` eager loading
  - Add database connection pool tuning (size 20-50)
  - Profile slow queries, add missing indexes

- [ ] **4.4 External Overlay Testing**
  - Create simple WebSocket client simulating overlay software
  - Verify sub-100ms latency from match update to overlay notification
  - Test with 100+ concurrent WebSocket connections

#### Acceptance Criteria
- [ ] WebSocket clients receive real-time updates on match changes
- [ ] Reconnection resumes event stream without data loss
- [ ] 100 concurrent WebSocket connections stable
- [ ] Read latency < 100ms p95 with caching enabled
- [ ] No N+1 queries detected in query profiling
- [ ] Overlay simulation receives all events correctly

---

### Phase 5: Production Hardening (Week 7-8)

**Goal**: Production-ready deployment with full test coverage

#### Tasks
- [ ] **5.1 Comprehensive Testing**
  - Unit tests: All services, validators, engines (>90% coverage)
  - Integration tests: All API endpoints with realistic scenarios
  - Load tests: 1000 concurrent tournaments, 5000 WebSocket connections
  - Chaos tests: Database disconnects, invalid schema submissions

- [ ] **5.2 Documentation**
  - Swagger UI with examples for all endpoints
  - Include JSON Schema examples for multiple disciplines
  - Write deployment guide (Docker, env vars, scaling)
  - Write API consumer guide for overlay developers

- [ ] **5.3 Monitoring & Observability**
  - Structured JSON logging with correlation IDs
  - Prometheus metrics: request latency, error rates, WS connections, DB pool usage
  - Health check endpoints: `/health/live`, `/health/ready`
  - Alert thresholds configured for error rates, response times

- [ ] **5.4 Sample Schemas Library**
  - Pre-load sample schemas for common disciplines:
    - Esports: CS:GO Bo3, LoL Bo5, Valorant Bo3
    - Traditional Sports: Basketball, Soccer, Tennis
    - Mind Sports: Chess Classical, Blitz
    - Virtual: iRacing, Battle Royale
  - Document how to create custom schemas

- [ ] **5.5 Security Audit**
  - Verify API key hashing uses bcrypt
  - SQL injection prevention (parameterized queries)
  - Rate limiting on auth endpoints
  - CORS configuration for known origins
  - Input sanitization on all JSONB fields

#### Acceptance Criteria
- [ ] All tests pass (unit, integration, load)
- [ ] Code coverage > 90%
- [ ] Swagger UI fully documented with examples
- [ ] Load test passes: 1000 tournaments, 5000 WS connections, <100ms p95
- [ ] Sample schemas pre-loaded and validated
- [ ] Security audit finds no critical/high vulnerabilities
- [ ] Deployment guide tested end-to-end

---

## Database Schema (PostgreSQL)

```sql
-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================
-- SCHEMA REGISTRY (Core Flexibility Mechanism)
-- ============================================

CREATE TABLE schema_registry (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    discipline VARCHAR(100),
    target_entity VARCHAR(50) NOT NULL CHECK (target_entity IN ('TEAM', 'MATCH', 'TOURNAMENT')),
    version INTEGER NOT NULL DEFAULT 1,
    json_schema JSONB NOT NULL, -- Full JSON Schema definition
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by UUID REFERENCES api_keys(id),
    UNIQUE (name, version) -- Same schema name can have multiple versions
);

CREATE INDEX idx_schema_registry_name ON schema_registry(name);
CREATE INDEX idx_schema_registry_discipline ON schema_registry(discipline);
CREATE INDEX idx_schema_registry_entity ON schema_registry(target_entity);
CREATE INDEX idx_schema_registry_active ON schema_registry(is_active) WHERE is_active = TRUE;

-- ============================================
-- TOURNAMENTS
-- ============================================

CREATE TABLE tournaments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    discipline VARCHAR(100),
    format_config JSONB DEFAULT '{}',
    metadata JSONB DEFAULT '{}', -- Contains: team_schema_id, match_schema_id, custom_fields
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Add constraint to ensure schema IDs in metadata reference valid schemas
-- (This is enforced at application level for flexibility)

-- ============================================
-- TEAMS (with schema validation)
-- ============================================

CREATE TABLE teams (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tournament_id UUID REFERENCES tournaments(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    seed INTEGER,
    players JSONB DEFAULT '[]', -- Validated against tournament's team_schema
    metadata JSONB DEFAULT '{}', -- Validated against tournament's team_schema
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================
-- API KEYS (with fine-grained permissions)
-- ============================================

CREATE TABLE api_keys (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    key_hash VARCHAR(255) NOT NULL UNIQUE,
    role VARCHAR(50) NOT NULL CHECK (role IN ('admin', 'organizer', 'judge', 'overlay_director')),
    tournament_id UUID REFERENCES tournaments(id) ON DELETE CASCADE,
    description VARCHAR(255),
    permissions JSONB DEFAULT '{}', -- Fine-grained permission overrides
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP
);

-- ============================================
-- NODES (bracket elements with graph edges)
-- ============================================

CREATE TABLE nodes (
    uuid UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tournament_id UUID REFERENCES tournaments(id) ON DELETE CASCADE,
    node_type VARCHAR(50) NOT NULL CHECK (node_type IN ('STANDARD', 'ROUND_ROBIN_GROUP', 'FINAL', 'CONSOLATION', 'SWISS_ROUND', 'GROUP_STAGE')),
    stage_info JSONB DEFAULT '{}', -- {stage_number: 1, group_letter: \"A\", round_number: 3}
    next_nodes JSONB DEFAULT '{}', -- {winner: \"uuid\", loser: \"uuid\", 1st: \"uuid\", score_3_0: \"uuid\"}
    overlay_config JSONB DEFAULT '{}', -- {position: \"top_left\", label: \"Finals\"}
    metadata JSONB DEFAULT '{}', -- Free-form, not validated
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================
-- MATCHES (with schema validation)
-- ============================================

CREATE TABLE matches (
    uuid UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    node_uuid UUID REFERENCES nodes(uuid) ON DELETE CASCADE,
    team_a_id UUID REFERENCES teams(id),
    team_b_id UUID REFERENCES teams(id),
    participants JSONB DEFAULT '[]', -- For multi-team matches: [{team_id, position}, ...]
    score JSONB DEFAULT '{}', -- Validated against tournament's match_schema
    status VARCHAR(50) DEFAULT 'scheduled' CHECK (status IN ('scheduled', 'in_progress', 'completed', 'cancelled', 'postponed')),
    start_time TIMESTAMP,
    end_time TIMESTAMP,
    winner_id UUID REFERENCES teams(id),
    metadata JSONB DEFAULT '{}', -- Validated against tournament's match_schema
    result_metadata JSONB DEFAULT '{}', -- Computed: points earned, tiebreakers
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================
-- AUDIT LOG (complete history tracking)
-- ============================================

CREATE TABLE audit_log (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tournament_id UUID REFERENCES tournaments(id) ON DELETE CASCADE,
    entity_type VARCHAR(50) NOT NULL, -- 'tournament', 'team', 'node', 'match', 'api_key', 'schema_registry'
    entity_id UUID NOT NULL,
    action VARCHAR(20) NOT NULL CHECK (action IN ('CREATE', 'UPDATE', 'DELETE')),
    api_key_id UUID REFERENCES api_keys(id), -- Who made the change
    old_values JSONB, -- State before change (null for CREATE)
    new_values JSONB, -- State after change (null for DELETE)
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================
-- INDEXES FOR PERFORMANCE
-- ============================================

-- Foreign key indexes
CREATE INDEX idx_teams_tournament ON teams(tournament_id);
CREATE INDEX idx_nodes_tournament ON nodes(tournament_id);
CREATE INDEX idx_matches_node ON matches(node_uuid);
CREATE INDEX idx_api_keys_tournament ON api_keys(tournament_id);
CREATE INDEX idx_tournaments_discipline ON tournaments(discipline);

-- GIN indexes for JSONB queries
CREATE INDEX idx_tournaments_format_config ON tournaments USING GIN(format_config);
CREATE INDEX idx_tournaments_metadata ON tournaments USING GIN(metadata);
CREATE INDEX idx_teams_players ON teams USING GIN(players);
CREATE INDEX idx_teams_metadata ON teams USING GIN(metadata);
CREATE INDEX idx_matches_score ON matches USING GIN(score);
CREATE INDEX idx_matches_metadata ON matches USING GIN(metadata);
CREATE INDEX idx_nodes_stage_info ON nodes USING GIN(stage_info);
CREATE INDEX idx_nodes_next_nodes ON nodes USING GIN(next_nodes);
CREATE INDEX idx_schema_registry_json ON schema_registry USING GIN(json_schema);

-- Audit log indexes
CREATE INDEX idx_audit_tournament ON audit_log(tournament_id);
CREATE INDEX idx_audit_entity ON audit_log(entity_type, entity_id);
CREATE INDEX idx_audit_created ON audit_log(created_at DESC);
CREATE INDEX idx_audit_api_key ON audit_log(api_key_id);
```
```

## Flexibility Mechanisms

### Schema Registry System (Core Innovation)

The Schema Registry enables **runtime-changeable data formats** without code changes:

1. **Schema Definition**: Organizers define JSON Schemas for their discipline
2. **Versioning**: Multiple versions of same schema coexist
3. **Tournament Locking**: Each tournament locks to specific schema versions
4. **Validation**: All JSONB data validated against referenced schemas at API layer
5. **Evolution**: New tournaments can use updated schemas; old tournaments unaffected

#### Workflow Example:
```
1. Admin creates schema "csgo_bo3_v1" for CS:GO Best-of-3 matches
2. Tournament A created, references "csgo_bo3_v1" 
3. Admin creates "csgo_bo3_v2" with additional fields (e.g., overtime rules)
4. Tournament B created, references "csgo_bo3_v2"
5. Tournament A continues using v1 schema - no breaking changes
6. Optional: Tournament A can be migrated to v2 if needed
```

### JSONB Usage Strategy

| Entity | JSONB Field | Validation | Purpose | Example |
|--------|-------------|------------|---------|---------|
| Tournament | `format_config` | No | Format-specific rules | `{"type": "swiss", "rounds": 5}` |
| Tournament | `metadata` | Optional (tournament_schema) | Extra tournament data | `{"prize_pool": "$10000"}` |
| Team | `players` | **Yes (team_schema)** | Roster storage | `[{"number": 10, "position": "forward"}]` |
| Team | `metadata` | **Yes (team_schema)** | Team-specific data | `{"fide_rating": 2500, "title": "GM"}` |
| Node | `stage_info` | No | Stage/group identification | `{"stage": 2, "group": "A"}` |
| Node | `next_nodes` | No | Graph edge definitions | `{"winner": "uuid", "top_2": [...]}` |
| Match | `score` | **Yes (match_schema)** | Discipline-specific scoring | `{"white": 1, "moves": 45}` |
| Match | `metadata` | **Yes (match_schema)** | Match-specific data | `{"opening": "Sicilian Defense"}` |

### Supported Discipline Patterns

#### Esports (CS:GO, LoL, Dota 2)
- Teams: Player rosters with game IDs, roles, ranks
- Matches: Map scores, veto order, side selection, overtime rules
- Metadata: Server IPs, VOD links, spectator delay

#### Traditional Sports (Basketball, Football, Tennis)
- Teams: Player numbers, positions, coach info, home venue
- Matches: Quarter/half scores, fouls, timeouts, venue, referee
- Metadata: Attendance, weather conditions, broadcast info

#### Mind Sports (Chess, Go, Bridge)
- Teams/Players: Ratings, titles (GM, IM), federation IDs
- Matches: Time controls, opening codes, move histories (PGN)
- Metadata: Tournament director, arbiter notes

#### Virtual Competitions (Sim Racing, Fitness Apps)
- Teams: Driver licenses, car setups, team principals
- Matches: Lap times, penalties, track conditions, fuel strategy
- Metadata: Telemetry data links, iRatings, safety ratings

#### Battle Royale / Multi-team Formats
- Teams: Squad compositions, drop locations
- Matches: Placements, eliminations, damage dealt, survival time
- Metadata: Zone timers, loot tracking

### Round Robin as Node Type
- A `Node` with `type='ROUND_ROBIN_GROUP'` contains N*(N-1)/2 matches
- All teams in the group are stored in match relationships
- Standing calculation service computes rankings based on match results
- Tiebreaker rules defined in tournament's `format_config`
- Top X teams programmatically linked to next stage via `next_nodes`

### Schema Evolution Without Breaking Changes

1. **Backward Compatibility**: Old tournaments keep working with old schemas
2. **Migration Tools**: Optional data migration between schema versions
3. **Validation Layer**: Pydantic + jsonschema library validates at runtime
4. **Hot Updates**: New schemas available immediately for new tournaments

## Security Considerations
- API keys stored as hashes (bcrypt or argon2)
- Rate limiting on API endpoints (via FastAPI middleware)
- Input validation on all endpoints (Pydantic models)
- SQL injection prevention via SQLAlchemy parameterized queries
- CORS configuration for frontend/overlay integration
- WebSocket authentication with token expiration

## Testing Strategy
- Unit tests for bracket generation logic
- Unit tests for Round Robin standing calculations
- Integration tests for all API endpoints
- WebSocket connection and event tests
- Database migration tests (Alembic upgrade/downgrade)
- Load testing for concurrent WebSocket connections
- Role-based permission tests

## Deployment Notes
- Docker containerization (FastAPI app + PostgreSQL)
- Environment variables for configuration (DB URL, API key secret)
- Database backup strategy (pg_dump scheduled jobs)
- Horizontal scaling considerations for WebSocket connections (Redis pub/sub for multi-instance)
- Logging: Structured JSON logs for monitoring integration

## Audit & History System

### Requirements
- Full audit history for every tournament change
- Track all CRUD operations on: Tournaments, Teams, Nodes, Matches, API Keys
- Store: who made the change (API key ID), what changed, when, and before/after values

### Implementation Approach
- **Audit Log Table**: Separate table storing all changes with JSONB diffs
- **Event Triggers**: PostgreSQL triggers or SQLAlchemy events to auto-capture changes
- **Query Interface**: Endpoint to retrieve historical states of any entity

### Audit Log Schema
```sql
CREATE TABLE audit_log (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tournament_id UUID REFERENCES tournaments(id) ON DELETE CASCADE,
    entity_type VARCHAR(50) NOT NULL, -- 'tournament', 'team', 'node', 'match', 'api_key'
    entity_id UUID NOT NULL,
    action VARCHAR(20) NOT NULL CHECK (action IN ('CREATE', 'UPDATE', 'DELETE')),
    api_key_id UUID REFERENCES api_keys(id), -- Who made the change
    old_values JSONB, -- State before change (null for CREATE)
    new_values JSONB, -- State after change (null for DELETE)
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for efficient querying
CREATE INDEX idx_audit_tournament ON audit_log(tournament_id);
CREATE INDEX idx_audit_entity ON audit_log(entity_type, entity_id);
CREATE INDEX idx_audit_created ON audit_log(created_at DESC);
CREATE INDEX idx_audit_api_key ON audit_log(api_key_id);
```

### Audit Endpoints
- `GET /tournaments/{id}/audit` - Get full audit trail for a tournament
- `GET /audit/{entity_type}/{entity_id}` - Get history of specific entity
- `GET /audit?api_key_id={key_id}&from={date}&to={date}` - Filter by actor and date range

## Bulk Operations

### Supported Operations
- **Team Import**: CSV/JSON upload to register multiple teams at once
  - Endpoint: `POST /tournaments/{id}/teams/bulk`
  - Validates format, reports errors per row, partial success handling
- **Bracket Export**: Full tournament state export (JSON)
  - Endpoint: `GET /tournaments/{id}/export`
  - Includes: teams, nodes, matches, results in portable format
- **Match Results Import**: Batch update match scores
  - Endpoint: `POST /tournaments/{id}/matches/bulk-update`
  - For importing results from external scoring systems

## Performance Optimization (Target: 1000 Concurrent Big Tournaments)

### Database Optimization
- **Connection Pooling**: Asyncpg connection pool with size tuning (default 20-50 connections)
- **Query Optimization**: 
  - Careful indexing strategy (avoid over-indexing JSONB)
  - Use covering indexes where possible
  - EXPLAIN ANALYZE all critical queries
- **Read Replicas**: Architecture supports read replicas for heavy read loads (overlays polling)
- **Partitioning**: Consider time-based partitioning for audit_log and matches tables if data grows large

### Application Optimization
- **Caching Strategy**:
  - Redis cache for frequently accessed tournament brackets (TTL: 30s-1m)
  - Cache invalidation on write operations
- **Async Everything**: Full async stack (FastAPI → SQLAlchemy → asyncpg)
- **WebSocket Efficiency**:
  - Room-based subscriptions (per tournament)
  - Debounce rapid updates (batch multiple changes within 100ms window)
  - Consider Redis pub/sub for multi-instance deployments
- **Pagination**: All list endpoints support pagination (cursor-based for large datasets)
- **N+1 Query Prevention**: Eager loading with SQLAlchemy selectinload/joinedload

### Scalability Targets
- **Concurrent Tournaments**: 1000 active tournaments
- **Matches per Tournament**: Up to 10,000 (large Swiss/RR formats)
- **WebSocket Connections**: 5,000+ concurrent (overlays + viewers)
- **API Response Time**: <100ms p95 for reads, <500ms p95 for writes
- **Database Size**: Plan for 100GB+ with proper vacuuming and maintenance

### Monitoring & Observability
- **Metrics**: Request latency, error rates, WebSocket connections, DB query times
- **Logging**: Structured JSON logs with correlation IDs
- **Alerting**: Thresholds for error rates, response times, connection pool exhaustion
- **Profiling**: Periodic load testing to identify bottlenecks

---

## Quick Start for AI Agents

1. **Read this document completely** before writing any code
2. **Start with Phase 1** - do not skip ahead
3. **Run tests frequently** - each subtask should have tests
4. **Commit often** - small, atomic commits per feature
5. **Validate against acceptance criteria** before marking tasks complete

### File Structure to Create

```
/workspace/
├── PLAN.md (this file)
├── pyproject.toml
├── docker-compose.yml
├── Dockerfile
├── .env.example
├── .gitignore
└── src/
    ├── __init__.py
    ├── main.py
    ├── config.py
    ├── api/
    │   ├── __init__.py
    │   ├── routes/
    │   ├── websocket/
    │   └── middleware/
    ├── services/
    ├── db/
    │   ├── models/
    │   └── repositories/
    └── tests/
        ├── unit/
        └── integration/
```

### First Command to Run

```bash
# After reading this plan, start by creating the project structure:
mkdir -p src/{api/{routes,websocket,middleware},services,db/{models,repositories},tests/{unit,integration}}
touch src/__init__.py pyproject.toml docker-compose.yml Dockerfile .env.example .gitignore
```

Then proceed with **Phase 1.1: Project Scaffolding**.

---

**Good luck! This system will power tournaments across ALL disciplines.**
