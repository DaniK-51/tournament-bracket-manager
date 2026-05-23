# Data Model

This document provides detailed specifications for all database entities in the Tournament Management System.

## Design Principles

1. **UUID Primary Keys**: All entities use UUID for primary keys to enable distributed generation and avoid information leakage
2. **JSONB for Flexibility**: JSONB columns store discipline-specific data with application-level JSON Schema validation
3. **Audit Trail**: Every entity tracks creation and update timestamps
4. **Referential Integrity**: Foreign keys enforce relationships; cascade deletes where appropriate
5. **Soft Deletes**: Critical entities use soft deletes (is_archived flag) instead of hard deletes

## Entity Relationship Diagram

```
┌──────────────────────┐
│   schema_registry    │
│──────────────────────│
│ id (UUID, PK)        │◄────┐
│ name                 │     │
│ discipline           │     │
│ target_entity        │     │
│ version              │     │
│ json_schema (JSONB)  │     │
│ is_active            │     │
│ created_by           │     │
│ created_at           │     │
└──────────────────────┘     │
                             │ used by
                             │
      ┌──────────────────────┼──────────────────────┐
      │                      │                      │
      ▼                      ▼                      │
┌─────────────┐       ┌─────────────┐              │
│ tournament  │       │   team      │              │
│─────────────│       │─────────────│              │
│ id (UUID)   │◄──────│ tournament_id│              │
│ name        │       │ name        │              │
│ discipline  │       │ players     │              │
│ format_cfg  │       │ metadata    │──(validated)─┘
│ metadata    │───────│ (JSONB)     │
│ created_at  │       │ seed        │
└─────────────┘       └─────────────┘
      │
      │ contains
      ▼
┌─────────────┐
│    node     │       ┌─────────────┐
│─────────────│       │   match     │
│ uuid (PK)   │◄──────│ node_uuid   │
│ tournament_id│      │─────────────│
│ node_type   │      │ team_a_id   │
│ stage_info  │      │ team_b_id   │
│ matches[]   │─────►│ score       │
│ next_nodes  │      │ status      │
│ overlay_cfg │      │ winner_id   │
│ metadata    │      │ metadata    │──(validated)─┐
└─────────────┘      └─────────────┘              │
                                                  │
                                                  │
      ┌───────────────────────────────────────────┘
      │
      ▼
┌─────────────┐
│ api_key     │
│─────────────│
│ id (UUID)   │
│ key_hash    │
│ role        │
│ permissions │
│ expires_at  │
└─────────────┘

┌─────────────┐
│  audit_log  │
│─────────────│
│ id (UUID)   │
│ entity_type │
│ entity_id   │
│ action      │
│ before      │
│ after       │
│ actor_id    │
│ timestamp   │
└─────────────┘
```

---

## Schema Registry Entity

**Purpose:** Store JSON Schema definitions for validating tournament-specific data formats.

### Table: `schema_registry`

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | UUID | PRIMARY KEY, DEFAULT uuid_generate_v4() | Unique identifier |
| `name` | VARCHAR(255) | NOT NULL | Schema name (e.g., "csgo_best_of_3") |
| `discipline` | VARCHAR(100) | NOT NULL | Discipline (e.g., "CS:GO", "Chess") |
| `target_entity` | ENUM | NOT NULL | Which entity this validates: `TEAM`, `MATCH`, `TOURNAMENT` |
| `version` | INTEGER | NOT NULL, DEFAULT 1 | Auto-incremented per schema name |
| `json_schema` | JSONB | NOT NULL | Full JSON Schema definition |
| `is_active` | BOOLEAN | NOT NULL, DEFAULT true | Whether new tournaments can use this |
| `created_by` | UUID | FK → api_keys.id | API key that created this schema |
| `created_at` | TIMESTAMP | NOT NULL, DEFAULT now() | Creation timestamp |
| `updated_at` | TIMESTAMP | NOT NULL, DEFAULT now() | Last update timestamp |

### Indexes

```sql
CREATE INDEX idx_schema_registry_name ON schema_registry(name);
CREATE INDEX idx_schema_registry_discipline ON schema_registry(discipline);
CREATE INDEX idx_schema_registry_target ON schema_registry(target_entity);
CREATE INDEX idx_schema_registry_active ON schema_registry(is_active) WHERE is_active = true;
CREATE INDEX idx_schema_registry_jsonb ON schema_registry USING GIN(json_schema);
```

### Example JSON Schema (CS:GO Match)

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

---

## Tournament Entity

**Purpose:** Core tournament container with format configuration and schema references.

### Table: `tournaments`

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | UUID | PRIMARY KEY, DEFAULT uuid_generate_v4() | Unique identifier |
| `name` | VARCHAR(255) | NOT NULL | Tournament name |
| `discipline` | VARCHAR(100) | NOT NULL | Competition type (e.g., "CS:GO") |
| `format_config` | JSONB | NOT NULL | Format-specific rules |
| `metadata` | JSONB | NOT NULL | Schema references + custom fields |
| `created_at` | TIMESTAMP | NOT NULL, DEFAULT now() | Creation timestamp |
| `updated_at` | TIMESTAMP | NOT NULL, DEFAULT now() | Last update timestamp |
| `is_archived` | BOOLEAN | NOT NULL, DEFAULT false | Soft delete flag |

### format_config Structure

```json
{
  "type": "double_elim",
  "grand_final_reset": true,
  "third_place_match": false,
  "group_stage": {
    "enabled": false,
    "groups_count": 4,
    "advance_per_group": 2
  }
}
```

### metadata Structure

```json
{
  "team_schema_id": "uuid-of-team-schema",
  "match_schema_id": "uuid-of-match-schema",
  "custom_fields": {
    "prize_pool": "$10,000",
    "region": "EU",
    "organizer": "Example Org"
  }
}
```

### Indexes

```sql
CREATE INDEX idx_tournaments_discipline ON tournaments(discipline);
CREATE INDEX idx_tournaments_archived ON tournaments(is_archived) WHERE is_archived = false;
CREATE INDEX idx_tournaments_metadata ON tournaments USING GIN(metadata);
```

---

## Team Entity

**Purpose:** Store team information with flexible player rosters validated against schemas.

### Table: `teams`

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | UUID | PRIMARY KEY, DEFAULT uuid_generate_v4() | Unique identifier |
| `tournament_id` | UUID | FK → tournaments.id, NOT NULL | Parent tournament |
| `name` | VARCHAR(255) | NOT NULL | Team name |
| `players` | JSONB | NOT NULL | Player roster (schema-validated) |
| `metadata` | JSONB | NOT NULL | Team-specific data (schema-validated) |
| `seed` | INTEGER | Nullable | Seeding position |
| `created_at` | TIMESTAMP | NOT NULL, DEFAULT now() | Creation timestamp |
| `updated_at` | TIMESTAMP | NOT NULL, DEFAULT now() | Last update timestamp |

### players Examples

**Simple (list of names):**
```json
["Player1", "Player2", "Player3", "Player4", "Player5"]
```

**Structured (with roles):**
```json
[
  {"id": "...", "ign": "Player1", "real_name": "John Doe", "role": "captain"},
  {"id": "...", "ign": "Player2", "real_name": "Jane Smith", "role": "rifleman"}
]
```

**IRL Sports:**
```json
[
  {"number": 10, "position": "forward", "name": "John Doe"},
  {"number": 1, "position": "goalkeeper", "name": "Jane Smith"}
]
```

### metadata Examples

**Esports:**
```json
{
  "logo_url": "https://example.com/logo.png",
  "region": "EU",
  "social_links": {"twitter": "@team", "website": "https://team.com"}
}
```

**IRL Sports:**
```json
{
  "jersey_color": "red",
  "home_venue": "Stadium Name",
  "coach": "Coach Name"
}
```

### Indexes

```sql
CREATE INDEX idx_teams_tournament ON teams(tournament_id);
CREATE INDEX idx_teams_players ON teams USING GIN(players);
CREATE INDEX idx_teams_metadata ON teams USING GIN(metadata);
```

---

## Node Entity (Bracket Building Block)

**Purpose:** Represent bracket positions (matches, groups, finals) as graph nodes.

### Table: `nodes`

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `uuid` | UUID | PRIMARY KEY, DEFAULT uuid_generate_v4() | Unique identifier (used in APIs) |
| `tournament_id` | UUID | FK → tournaments.id, NOT NULL | Parent tournament |
| `node_type` | ENUM | NOT NULL | Type: `STANDARD`, `ROUND_ROBIN_GROUP`, `FINAL`, `CONSOLATION`, `SWISS_ROUND`, `GROUP_STAGE` |
| `stage_info` | JSONB | NOT NULL | Stage/group/round information |
| `matches` | UUID[] | ARRAY, NOT NULL, DEFAULT [] | List of match UUIDs in this node |
| `next_nodes` | JSONB | NOT NULL | Map of outcome → next node UUID |
| `overlay_config` | JSONB | Nullable | Hints for external overlay software |
| `metadata` | JSONB | Nullable | Additional node-specific data |
| `created_at` | TIMESTAMP | NOT NULL, DEFAULT now() | Creation timestamp |

### node_type Enum Values

| Value | Description |
|-------|-------------|
| `STANDARD` | Regular elimination match |
| `ROUND_ROBIN_GROUP` | Round Robin group with multiple matches |
| `FINAL` | Grand final or championship match |
| `CONSOLATION` | Consolation/losers bracket match |
| `SWISS_ROUND` | Swiss system round |
| `GROUP_STAGE` | Group stage node |

### stage_info Structure

**Standard Match:**
```json
{
  "stage_number": 1,
  "bracket": "winners",
  "description": "Winners Round 1"
}
```

**Round Robin Group:**
```json
{
  "stage_number": 0,
  "group_letter": "A",
  "description": "Group A",
  "total_rounds": 3
}
```

**Swiss Round:**
```json
{
  "stage_number": 2,
  "round_number": 2,
  "description": "Swiss Round 2",
  "score_threshold": "2-0"
}
```

### next_nodes Structure

**Standard (Double Elim):**
```json
{
  "winner": "uuid-of-next-winners-match",
  "loser": "uuid-of-next-losers-match"
}
```

**Round Robin:**
```json
{
  "1st": "uuid-of-semifinal-1",
  "2nd": "uuid-of-semifinal-2",
  "3rd": "uuid-of-consolation-final",
  "4th": null
}
```

**Swiss:**
```json
{
  "score_2_0": "uuid-of-next-2-0-match",
  "score_1_1": "uuid-of-next-1-1-match",
  "score_0_2": "uuid-of-consolation"
}
```

### overlay_config Structure

```json
{
  "position": "top_left",
  "label": "Winners Final",
  "priority": 1,
  "display_order": 5
}
```

### Indexes

```sql
CREATE INDEX idx_nodes_tournament ON nodes(tournament_id);
CREATE INDEX idx_nodes_type ON nodes(node_type);
CREATE INDEX idx_nodes_stage ON nodes USING GIN(stage_info);
CREATE INDEX idx_nodes_next ON nodes USING GIN(next_nodes);
CREATE INDEX idx_nodes_matches ON nodes USING GIN(matches);
```

---

## Match Entity

**Purpose:** Store individual match data with schema-validated scores and metadata.

### Table: `matches`

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `uuid` | UUID | PRIMARY KEY, DEFAULT uuid_generate_v4() | Unique identifier |
| `node_uuid` | UUID | FK → nodes.uuid, NOT NULL | Parent node |
| `team_a_id` | UUID | FK → teams.id, Nullable | First participant |
| `team_b_id` | UUID | FK → teams.id, Nullable | Second participant |
| `participants` | JSONB | Nullable | For multi-team matches |
| `score` | JSONB | NOT NULL, DEFAULT '{}' | Match score (schema-validated) |
| `status` | ENUM | NOT NULL, DEFAULT 'scheduled' | Match status |
| `start_time` | TIMESTAMP | Nullable | Scheduled start time |
| `end_time` | TIMESTAMP | Nullable | Actual end time |
| `metadata` | JSONB | NOT NULL, DEFAULT '{}' | Match-specific data (schema-validated) |
| `winner_id` | UUID | FK → teams.id, Nullable | Winning team |
| `result_metadata` | JSONB | Nullable | Computed results for standings |
| `created_at` | TIMESTAMP | NOT NULL, DEFAULT now() | Creation timestamp |
| `updated_at` | TIMESTAMP | NOT NULL, DEFAULT now() | Last update timestamp |

### status Enum Values

| Value | Description |
|-------|-------------|
| `scheduled` | Match scheduled but not started |
| `in_progress` | Match currently being played |
| `completed` | Match finished |
| `cancelled` | Match cancelled |
| `postponed` | Match postponed to later time |

### score Examples

**Best of 3 (CS:GO):**
```json
{
  "team_a": 2,
  "team_b": 1,
  "maps": [
    {"map": "Dust2", "team_a": 16, "team_b": 14, "winner": "a"},
    {"map": "Mirage", "team_a": 12, "team_b": 16, "winner": "b"},
    {"map": "Inferno", "team_a": 16, "team_b": 10, "winner": "a"}
  ]
}
```

**Points (Basketball):**
```json
{
  "team_a": 98,
  "team_b": 95,
  "quarters": [
    {"team_a": 25, "team_b": 22},
    {"team_a": 24, "team_b": 28},
    {"team_a": 26, "team_b": 21},
    {"team_a": 23, "team_b": 24}
  ]
}
```

**Chess:**
```json
{
  "white": 1,
  "black": 0,
  "moves": 45,
  "opening": "Sicilian Defense",
  "eco_code": "B90"
}
```

**Battle Royale (Multi-team):**
```json
{
  "teams": [
    {"team_id": "...", "placement": 1, "kills": 10},
    {"team_id": "...", "placement": 2, "kills": 8},
    {"team_id": "...", "placement": 3, "kills": 5}
  ]
}
```

### metadata Examples

**Esports:**
```json
{
  "vod_link": "https://twitch.tv/videos/...",
  "server_ip": "192.168.1.100:27015",
  "map_veto": ["Dust2", "Mirage", "Inferno"],
  "round_history": [...]
}
```

**IRL Sports:**
```json
{
  "venue": "Stadium Name",
  "referee": "Referee Name",
  "attendance": 50000,
  "weather": {"temperature": 22, "conditions": "sunny"}
}
```

### result_metadata Structure

```json
{
  "points_earned": 3,
  "tiebreaker_value": 1.5,
  "advancement_status": "qualified"
}
```

### Indexes

```sql
CREATE INDEX idx_matches_node ON matches(node_uuid);
CREATE INDEX idx_matches_team_a ON matches(team_a_id);
CREATE INDEX idx_matches_team_b ON matches(team_b_id);
CREATE INDEX idx_matches_winner ON matches(winner_id);
CREATE INDEX idx_matches_status ON matches(status);
CREATE INDEX idx_matches_score ON matches USING GIN(score);
CREATE INDEX idx_matches_metadata ON matches USING GIN(metadata);
```

---

## API Key Entity

**Purpose:** Store hashed API keys for authentication and authorization.

### Table: `api_keys`

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | UUID | PRIMARY KEY, DEFAULT uuid_generate_v4() | Unique identifier |
| `key_hash` | VARCHAR(255) | NOT NULL | Bcrypt-hashed API key |
| `role` | ENUM | NOT NULL | Access role |
| `tournament_id` | UUID | FK → tournaments.id, Nullable | Scope limitation |
| `permissions` | JSONB | NOT NULL, DEFAULT '{}' | Fine-grained permissions |
| `created_at` | TIMESTAMP | NOT NULL, DEFAULT now() | Creation timestamp |
| `expires_at` | TIMESTAMP | Nullable | Expiration date |

### role Enum Values

| Value | Permissions |
|-------|-------------|
| `admin` | Full access to all tournaments and schemas |
| `organizer` | Full access to assigned tournaments |
| `judge` | Can update match scores only |
| `overlay_director` | Read-only access for overlays |

### permissions Structure

```json
{
  "can_edit_schemas": false,
  "can_delete_matches": true,
  "can_manage_teams": true,
  "can_view_audit_log": false
}
```

### Indexes

```sql
CREATE INDEX idx_api_keys_role ON api_keys(role);
CREATE INDEX idx_api_keys_tournament ON api_keys(tournament_id);
CREATE INDEX idx_api_keys_expires ON api_keys(expires_at);
```

---

## Audit Log Entity

**Purpose:** Track all mutations with before/after snapshots for complete history.

### Table: `audit_log`

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | UUID | PRIMARY KEY, DEFAULT uuid_generate_v4() | Unique identifier |
| `entity_type` | VARCHAR(50) | NOT NULL | Type of entity changed |
| `entity_id` | UUID | NOT NULL | ID of changed entity |
| `action` | ENUM | NOT NULL | Action performed |
| `before` | JSONB | Nullable | State before change |
| `after` | JSONB | Nullable | State after change |
| `actor_id` | UUID | FK → api_keys.id | Who made the change |
| `context` | JSONB | Nullable | Additional context |
| `timestamp` | TIMESTAMP | NOT NULL, DEFAULT now() | When change occurred |

### action Enum Values

| Value | Description |
|-------|-------------|
| `created` | Entity was created |
| `updated` | Entity was modified |
| `deleted` | Entity was deleted/archived |
| `score_updated` | Match score was changed |
| `status_changed` | Match/entity status changed |
| `schema_locked` | Tournament schema was locked |

### Indexes

```sql
CREATE INDEX idx_audit_entity ON audit_log(entity_type, entity_id);
CREATE INDEX idx_audit_actor ON audit_log(actor_id);
CREATE INDEX idx_audit_timestamp ON audit_log(timestamp DESC);
CREATE INDEX idx_audit_action ON audit_log(action);
CREATE INDEX idx_audit_before ON audit_log USING GIN(before);
CREATE INDEX idx_audit_after ON audit_log USING GIN(after);
```

---

## Common Patterns

### Soft Delete Pattern

Critical entities use soft deletes:

```python
class SoftDeleteMixin:
    is_archived = Column(Boolean, default=False, nullable=False)

# Query only active records
select(Tournament).where(Tournament.is_archived == False)

# Archive instead of delete
tournament.is_archived = True
```

### Timestamp Tracking

All entities track timestamps:

```python
class TimestampMixin:
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
```

### JSONB Querying

PostgreSQL GIN indexes enable efficient JSONB queries:

```sql
-- Find tournaments by discipline in metadata
SELECT * FROM tournaments 
WHERE metadata->>'custom_fields'->>'region' = 'EU';

-- Find teams with specific player
SELECT * FROM teams 
WHERE players @> '[{"ign": "Player1"}]';
```

## Next Steps

Continue reading:
- [API Reference](./05-api-reference.md) - Complete endpoint documentation
- [Schema Registry](./06-schema-registry.md) - Deep dive into schema management
