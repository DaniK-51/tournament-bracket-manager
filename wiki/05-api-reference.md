# API Reference

Complete documentation of all REST API endpoints and WebSocket connections.

## Base URL

```
Production: https://api.tournament-system.com/v1
Development: http://localhost:8000/v1
```

## Authentication

All API requests require authentication via API key:

```http
X-API-Key: your-api-key-here
```

### Authentication Middleware

The API key is validated on every request. The middleware:
1. Extracts the API key from the `X-API-Key` header
2. Hashes the provided key and compares with stored hash
3. Attaches API key data to request context
4. Enforces role-based permissions

### Error Responses

| Status Code | Meaning | Example |
|-------------|---------|---------|
| 401 | Missing or invalid API key | `{"detail": "Invalid API key"}` |
| 403 | Insufficient permissions | `{"detail": "Insufficient permissions"}` |
| 404 | Resource not found | `{"detail": "Tournament not found"}` |
| 400 | Validation error | `{"detail": "Schema validation failed", "errors": [...]}` |
| 500 | Server error | `{"detail": "Internal server error"}` |

---

## Schema Registry Endpoints

Manage JSON Schema definitions for tournament-specific data validation.

### GET /schemas

List all available schemas.

**Query Parameters:**
- `discipline` (optional): Filter by discipline
- `target_entity` (optional): Filter by entity type (`TEAM`, `MATCH`, `TOURNAMENT`)
- `is_active` (optional): Filter by active status (default: `true`)
- `limit` (optional): Pagination limit (default: 50, max: 100)
- `offset` (optional): Pagination offset

**Response:** `200 OK`

```json
{
  "schemas": [
    {
      "id": "uuid-123",
      "name": "csgo_best_of_3",
      "discipline": "CS:GO",
      "target_entity": "MATCH",
      "version": 1,
      "is_active": true,
      "created_at": "2024-01-15T10:30:00Z",
      "created_by": "uuid-456"
    }
  ],
  "total": 1,
  "limit": 50,
  "offset": 0
}
```

---

### POST /schemas

Create a new schema version.

**Request Body:**
```json
{
  "name": "csgo_best_of_3",
  "discipline": "CS:GO",
  "target_entity": "MATCH",
  "json_schema": {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "object",
    "properties": {
      "team_a_score": {"type": "integer"},
      "team_b_score": {"type": "integer"}
    },
    "required": ["team_a_score", "team_b_score"]
  }
}
```

**Behavior:**
- If schema name exists, auto-increments version number
- Validates that `json_schema` is valid JSON Schema draft-07
- Sets `is_active` to `true` by default

**Response:** `201 Created`

```json
{
  "id": "uuid-789",
  "name": "csgo_best_of_3",
  "discipline": "CS:GO",
  "target_entity": "MATCH",
  "version": 2,
  "json_schema": {...},
  "is_active": true,
  "created_at": "2024-01-20T14:00:00Z",
  "created_by": "uuid-456"
}
```

---

### GET /schemas/{id}

Get specific schema with full JSON Schema definition.

**Path Parameters:**
- `id`: Schema UUID

**Response:** `200 OK`

```json
{
  "id": "uuid-123",
  "name": "csgo_best_of_3",
  "discipline": "CS:GO",
  "target_entity": "MATCH",
  "version": 1,
  "json_schema": {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "object",
    "properties": {
      "team_a_score": {"type": "integer", "minimum": 0},
      "team_b_score": {"type": "integer", "minimum": 0},
      "maps": {
        "type": "array",
        "items": {...}
      }
    },
    "required": ["team_a_score", "team_b_score"]
  },
  "is_active": true,
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-01-15T10:30:00Z",
  "created_by": "uuid-456"
}
```

---

### PUT /schemas/{id}

Update schema (creates new version, never modifies existing).

**Path Parameters:**
- `id`: Schema UUID (of any version with this name)

**Request Body:** Same as POST /schemas

**Behavior:**
- Creates a new version with incremented version number
- Original version remains unchanged
- New version becomes the active version automatically

**Response:** `201 Created` (new version created)

---

### PATCH /schemas/{id}/deactivate

Mark schema as inactive (new tournaments can't use it).

**Path Parameters:**
- `id`: Schema UUID

**Behavior:**
- Sets `is_active` to `false`
- Existing tournaments using this schema are unaffected
- Returns current schema state

**Response:** `200 OK`

```json
{
  "id": "uuid-123",
  "name": "csgo_best_of_3",
  "is_active": false,
  "updated_at": "2024-01-20T15:00:00Z"
}
```

---

### POST /schemas/validate

Validate JSON data against a schema (utility endpoint).

**Request Body:**
```json
{
  "schema_id": "uuid-123",
  "data": {
    "team_a_score": 2,
    "team_b_score": 1
  }
}
```

**Response:** `200 OK`

```json
{
  "valid": true,
  "errors": []
}
```

**Or if invalid:**
```json
{
  "valid": false,
  "errors": [
    {"field": "team_a_score", "message": "must be an integer"},
    {"field": "maps", "message": "required field missing"}
  ]
}
```

---

## Tournament Management Endpoints

### POST /tournaments

Create a new tournament.

**Request Body:**
```json
{
  "name": "Winter Championship 2024",
  "discipline": "CS:GO",
  "format_config": {
    "type": "double_elim",
    "grand_final_reset": true
  },
  "metadata": {
    "team_schema_id": "uuid-team-schema",
    "match_schema_id": "uuid-match-schema",
    "custom_fields": {
      "prize_pool": "$10,000",
      "region": "EU"
    }
  }
}
```

**Behavior:**
1. Validates that referenced schemas exist and are active
2. Creates tournament entity
3. Generates initial bracket structure based on `format_config`
4. **Locks schema references** - cannot be changed after first team/match is added
5. Logs audit event

**Response:** `201 Created`

```json
{
  "id": "uuid-tournament",
  "name": "Winter Championship 2024",
  "discipline": "CS:GO",
  "format_config": {...},
  "metadata": {...},
  "created_at": "2024-01-20T10:00:00Z",
  "schema_locked": false
}
```

---

### GET /tournaments

List all tournaments.

**Query Parameters:**
- `discipline` (optional): Filter by discipline
- `status` (optional): Filter by status (`upcoming`, `active`, `completed`, `archived`)
- `limit` (optional): Pagination limit
- `offset` (optional): Pagination offset

**Response:** `200 OK`

```json
{
  "tournaments": [
    {
      "id": "uuid-1",
      "name": "Winter Championship 2024",
      "discipline": "CS:GO",
      "status": "active",
      "created_at": "2024-01-20T10:00:00Z"
    }
  ],
  "total": 1,
  "limit": 50,
  "offset": 0
}
```

---

### GET /tournaments/{id}

Get tournament details with full bracket graph.

**Path Parameters:**
- `id`: Tournament UUID or 6-digit ID

**Query Parameters:**
- `include_teams` (optional): Include team data (default: `true`)
- `include_matches` (optional): Include match data (default: `true`)

**Response:** `200 OK`

```json
{
  "id": "uuid-tournament",
  "name": "Winter Championship 2024",
  "discipline": "CS:GO",
  "format_config": {...},
  "metadata": {
    "team_schema_id": "uuid-team-schema",
    "match_schema_id": "uuid-match-schema"
  },
  "teams": [...],
  "nodes": [
    {
      "uuid": "uuid-node-1",
      "node_type": "STANDARD",
      "stage_info": {"stage_number": 0, "bracket": "winners"},
      "matches": [
        {
          "uuid": "uuid-match-1",
          "team_a_id": "uuid-team-a",
          "team_b_id": "uuid-team-b",
          "score": {},
          "status": "scheduled"
        }
      ],
      "next_nodes": {
        "winner": "uuid-node-2",
        "loser": "uuid-node-3"
      }
    }
  ],
  "created_at": "2024-01-20T10:00:00Z",
  "updated_at": "2024-01-20T10:00:00Z"
}
```

---

### PUT /tournaments/{id}

Update tournament metadata/config.

**Path Parameters:**
- `id`: Tournament UUID

**Request Body:**
```json
{
  "name": "Updated Tournament Name",
  "format_config": {...},
  "metadata": {
    "custom_fields": {...}
  }
}
```

**Restrictions:**
- **Cannot change `team_schema_id` or `match_schema_id`** after first team/match is created
- Attempting to change locked fields returns `400 Bad Request`

**Response:** `200 OK`

---

### DELETE /tournaments/{id}

Archive/delete tournament.

**Path Parameters:**
- `id`: Tournament UUID

**Behavior:**
- Sets `is_archived` to `true` (soft delete)
- All related data remains accessible but marked as archived
- Requires `admin` role

**Response:** `204 No Content`

---

## Team Operations

### POST /tournaments/{id}/teams

Register a team for a tournament.

**Path Parameters:**
- `id`: Tournament UUID

**Request Body:**
```json
{
  "name": "Team Alpha",
  "seed": 1,
  "players": ["Player1", "Player2", "Player3"],
  "metadata": {
    "logo_url": "https://example.com/logo.png",
    "region": "EU"
  }
}
```

**Behavior:**
1. Validates `players` and `metadata` against tournament's `team_schema`
2. **Triggers schema lock** if this is the first team
3. Adds team to tournament

**Response:** `201 Created`

```json
{
  "id": "uuid-team",
  "tournament_id": "uuid-tournament",
  "name": "Team Alpha",
  "players": [...],
  "metadata": {...},
  "seed": 1,
  "created_at": "2024-01-20T11:00:00Z"
}
```

---

### GET /tournaments/{id}/teams

List all teams in a tournament.

**Response:** `200 OK`

```json
{
  "teams": [
    {
      "id": "uuid-team-1",
      "name": "Team Alpha",
      "players": [...],
      "seed": 1
    }
  ],
  "total": 8
}
```

---

### PUT /teams/{id}

Update team information.

**Path Parameters:**
- `id`: Team UUID

**Request Body:** Same as POST (partial update allowed)

**Response:** `200 OK`

---

### DELETE /teams/{id}

Remove team from tournament.

**Path Parameters:**
- `id`: Team UUID

**Restrictions:**
- Cannot remove team if they have completed matches
- Requires `organizer` or `admin` role

**Response:** `204 No Content`

---

## Node Operations (Bracket Manipulation)

### GET /nodes/{uuid}

Get specific node by UUID.

**Path Parameters:**
- `uuid`: Node UUID

**Response:** `200 OK`

```json
{
  "uuid": "uuid-node",
  "tournament_id": "uuid-tournament",
  "node_type": "ROUND_ROBIN_GROUP",
  "stage_info": {"group_letter": "A"},
  "matches": ["uuid-match-1", "uuid-match-2"],
  "next_nodes": {"1st": "uuid-semifinal-1", "2nd": "uuid-semifinal-2"},
  "overlay_config": {"position": "top_left", "label": "Group A"}
}
```

---

### PUT /nodes/{uuid}

Update node configuration.

**Path Parameters:**
- `uuid`: Node UUID

**Request Body:**
```json
{
  "next_nodes": {"winner": "uuid-new-next"},
  "overlay_config": {...}
}
```

**Use Cases:**
- Manually adjust bracket progression
- Update overlay display configuration
- Modify stage information

**Response:** `200 OK`

---

## Match Operations

### GET /matches/{uuid}

Get specific match by UUID.

**Path Parameters:**
- `uuid`: Match UUID

**Response:** `200 OK`

```json
{
  "uuid": "uuid-match",
  "node_uuid": "uuid-node",
  "team_a_id": "uuid-team-a",
  "team_b_id": "uuid-team-b",
  "score": {
    "team_a": 2,
    "team_b": 1,
    "maps": [...]
  },
  "status": "completed",
  "winner_id": "uuid-team-a",
  "metadata": {
    "vod_link": "https://twitch.tv/...",
    "server_ip": "..."
  },
  "start_time": "2024-01-20T14:00:00Z",
  "end_time": "2024-01-20T15:30:00Z"
}
```

---

### PUT /matches/{uuid}/score

Update match score.

**Path Parameters:**
- `uuid`: Match UUID

**Request Body:**
```json
{
  "score": {
    "team_a": 2,
    "team_b": 1,
    "maps": [...]
  },
  "status": "completed"
}
```

**Behavior:**
1. Validates score against tournament's `match_schema`
2. Determines winner based on score
3. Updates `winner_id` field
4. Triggers progression logic (advances winner to next match)
5. Broadcasts WebSocket event to subscribers
6. Logs audit event

**Response:** `200 OK`

```json
{
  "uuid": "uuid-match",
  "score": {...},
  "status": "completed",
  "winner_id": "uuid-team-a",
  "updated_at": "2024-01-20T15:30:00Z",
  "progression": {
    "advanced_to": "uuid-next-match"
  }
}
```

---

### PUT /matches/{uuid}/status

Update match status.

**Path Parameters:**
- `uuid`: Match UUID

**Request Body:**
```json
{
  "status": "in_progress"
}
```

**Valid Status Values:**
- `scheduled`
- `in_progress`
- `completed`
- `cancelled`
- `postponed`

**Response:** `200 OK`

---

### POST /matches/{uuid}/assign

Assign teams to a match.

**Path Parameters:**
- `uuid`: Match UUID

**Request Body:**
```json
{
  "team_a_id": "uuid-team-a",
  "team_b_id": "uuid-team-b"
}
```

**Use Cases:**
- Manual team assignment (e.g., after organizer adjustment)
- Assigning teams to Round Robin group matches

**Response:** `200 OK`

---

## Authentication Endpoints

### POST /auth/keys

Create a new API key.

**Request Body:**
```json
{
  "role": "organizer",
  "tournament_id": "uuid-tournament",
  "permissions": {
    "can_edit_schemas": false,
    "can_delete_matches": false
  },
  "expires_at": "2024-12-31T23:59:59Z"
}
```

**Response:** `201 Created`

```json
{
  "id": "uuid-key",
  "key": "sk_live_abc123xyz...",  // Only shown once!
  "role": "organizer",
  "permissions": {...},
  "created_at": "2024-01-20T10:00:00Z",
  "expires_at": "2024-12-31T23:59:59Z"
}
```

⚠️ **Important:** The plain text API key is only returned once. Store it securely.

---

### DELETE /auth/keys/{id}

Revoke an API key.

**Path Parameters:**
- `id`: API key UUID

**Behavior:**
- Immediately invalidates the key
- All sessions using this key are terminated

**Response:** `204 No Content`

---

## Audit Log Endpoints

### GET /audit

Retrieve audit log entries.

**Query Parameters:**
- `entity_type` (optional): Filter by entity type
- `entity_id` (optional): Filter by specific entity
- `action` (optional): Filter by action type
- `actor_id` (optional): Filter by who made the change
- `from` (optional): Start timestamp (ISO 8601)
- `to` (optional): End timestamp (ISO 8601)
- `limit` (optional): Pagination limit

**Response:** `200 OK`

```json
{
  "entries": [
    {
      "id": "uuid-audit-1",
      "entity_type": "match",
      "entity_id": "uuid-match",
      "action": "score_updated",
      "before": {
        "score": {"team_a": 1, "team_b": 0}
      },
      "after": {
        "score": {"team_a": 2, "team_b": 0}
      },
      "actor_id": "uuid-api-key",
      "timestamp": "2024-01-20T15:30:00Z"
    }
  ],
  "total": 150,
  "limit": 50,
  "offset": 0
}
```

---

### GET /audit/{entity_type}/{entity_id}

Get complete history for a specific entity.

**Path Parameters:**
- `entity_type`: Type of entity (`tournament`, `team`, `match`, `node`)
- `entity_id`: Entity UUID

**Response:** `200 OK`

```json
{
  "entity_type": "match",
  "entity_id": "uuid-match",
  "history": [
    {
      "action": "created",
      "before": null,
      "after": {...},
      "timestamp": "2024-01-20T10:00:00Z"
    },
    {
      "action": "status_changed",
      "before": {"status": "scheduled"},
      "after": {"status": "in_progress"},
      "timestamp": "2024-01-20T14:00:00Z"
    },
    {
      "action": "score_updated",
      "before": {"score": {}},
      "after": {"score": {"team_a": 2, "team_b": 1}},
      "timestamp": "2024-01-20T15:30:00Z"
    }
  ]
}
```

---

## WebSocket API

Real-time updates for tournament state changes.

### Connection Endpoint

```
ws://localhost:8000/ws/tournaments/{tournament_id}
```

### Authentication

Include API key in query parameter or header:

```
ws://localhost:8000/ws/tournaments/{tournament_id}?api_key=your-key
```

Or via WebSocket subprotocol header.

### Event Types

#### `match.score_updated`

Fired when a match score is updated.

```json
{
  "type": "match.score_updated",
  "data": {
    "match_uuid": "uuid-match",
    "node_uuid": "uuid-node",
    "score": {"team_a": 2, "team_b": 1},
    "winner_id": "uuid-team-a",
    "status": "completed"
  },
  "timestamp": "2024-01-20T15:30:00Z"
}
```

#### `match.status_changed`

Fired when match status changes.

```json
{
  "type": "match.status_changed",
  "data": {
    "match_uuid": "uuid-match",
    "old_status": "scheduled",
    "new_status": "in_progress"
  },
  "timestamp": "2024-01-20T14:00:00Z"
}
```

#### `team.registered`

Fired when a new team registers.

```json
{
  "type": "team.registered",
  "data": {
    "team_id": "uuid-team",
    "name": "Team Alpha",
    "seed": 1
  },
  "timestamp": "2024-01-20T11:00:00Z"
}
```

#### `bracket.progression`

Fired when a team advances in the bracket.

```json
{
  "type": "bracket.progression",
  "data": {
    "team_id": "uuid-team",
    "from_match": "uuid-match-1",
    "to_match": "uuid-match-2",
    "from_node": "uuid-node-1",
    "to_node": "uuid-node-2"
  },
  "timestamp": "2024-01-20T15:30:00Z"
}
```

#### `tournament.updated`

Fired when tournament metadata changes.

```json
{
  "type": "tournament.updated",
  "data": {
    "tournament_id": "uuid-tournament",
    "changes": ["name", "format_config"]
  },
  "timestamp": "2024-01-20T12:00:00Z"
}
```

### Client Example (JavaScript)

```javascript
const ws = new WebSocket(
  'ws://localhost:8000/ws/tournaments/uuid-tournament?api_key=your-key'
);

ws.onmessage = (event) => {
  const message = JSON.parse(event.data);
  
  switch (message.type) {
    case 'match.score_updated':
      console.log('Score updated:', message.data);
      updateOverlay(message.data);
      break;
    case 'bracket.progression':
      console.log('Team advanced:', message.data);
      updateBracket(message.data);
      break;
  }
};

ws.onerror = (error) => {
  console.error('WebSocket error:', error);
};

ws.onclose = () => {
  console.log('Connection closed, reconnecting...');
  setTimeout(connect, 5000);
};
```

---

## Rate Limiting

API requests are rate-limited per API key:

| Role | Requests/minute | Requests/hour |
|------|-----------------|---------------|
| admin | 1000 | 50,000 |
| organizer | 500 | 25,000 |
| judge | 200 | 10,000 |
| overlay_director | 100 | 5,000 |

Rate limit headers are included in responses:

```http
X-RateLimit-Limit: 500
X-RateLimit-Remaining: 499
X-RateLimit-Reset: 1705756800
```

---

## Next Steps

Continue reading:
- [Schema Registry](./06-schema-registry.md) - Deep dive into schema management
- [Bracket Engine](./07-bracket-engine.md) - How brackets are generated and managed
