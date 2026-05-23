# Schema Registry Guide

The Schema Registry is the core flexibility mechanism of the Tournament Management System. It allows organizers to define custom data formats for any discipline without code changes.

## What is the Schema Registry?

The Schema Registry stores JSON Schema definitions that validate:
- **Team data**: Player rosters, team metadata
- **Match data**: Scores, match metadata
- **Tournament data**: Custom tournament fields

## Key Concepts

### Schema Versioning

Schemas are versioned automatically:
- Each schema has a `name` and `version` number
- Updating a schema creates a new version (never modifies existing)
- Tournaments lock to specific schema versions at creation time
- Old versions remain immutable for historical integrity

### Schema Locking

When a tournament is created:
1. Organizer specifies which schema versions to use
2. Once the first team or match is added, schemas are **locked**
3. Locked schemas cannot be changed for that tournament
4. This ensures data consistency throughout the tournament lifecycle

### Target Entities

Each schema targets one entity type:

| Target Entity | Validates | Example Use |
|--------------|-----------|-------------|
| `TEAM` | Team `players` and `metadata` fields | CS:GO roster with Steam IDs |
| `MATCH` | Match `score` and `metadata` fields | Best-of-3 score format |
| `TOURNAMENT` | Tournament custom fields | Prize pool, region info |

---

## Creating Schemas

### Example: CS:GO Team Schema

```json
{
  "name": "csgo_team_v2",
  "discipline": "CS:GO",
  "target_entity": "TEAM",
  "json_schema": {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "object",
    "properties": {
      "players": {
        "type": "array",
        "minItems": 5,
        "maxItems": 7,
        "items": {
          "type": "object",
          "properties": {
            "steam_id": {
              "type": "string",
              "pattern": "^STEAM_[0-5]:[0-1]:\\d+$"
            },
            "ign": {"type": "string", "minLength": 1, "maxLength": 32},
            "real_name": {"type": "string"},
            "role": {
              "type": "string",
              "enum": ["captain", "rifler", "awper", "support", "entry"]
            },
            "country": {"type": "string", "minLength": 2, "maxLength": 2}
          },
          "required": ["steam_id", "ign", "role"]
        }
      },
      "metadata": {
        "type": "object",
        "properties": {
          "team_logo_url": {"type": "string", "format": "uri"},
          "region": {"type": "string"},
          "social_links": {
            "type": "object",
            "properties": {
              "twitter": {"type": "string", "format": "uri"},
              "website": {"type": "string", "format": "uri"}
            }
          }
        }
      }
    },
    "required": ["players"]
  }
}
```

### Example: Chess Match Schema

```json
{
  "name": "chess_classical_match",
  "discipline": "Chess",
  "target_entity": "MATCH",
  "json_schema": {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "object",
    "properties": {
      "white_score": {"type": "number", "minimum": 0, "maximum": 1},
      "black_score": {"type": "number", "minimum": 0, "maximum": 1},
      "moves": {"type": "integer", "minimum": 0},
      "opening": {"type": "string"},
      "eco_code": {
        "type": "string",
        "pattern": "^[A-E]\\d{2}$"
      },
      "time_control": {
        "type": "string",
        "enum": ["classical", "rapid", "blitz", "bullet"]
      },
      "pgn_link": {"type": "string", "format": "uri"}
    },
    "required": ["white_score", "black_score"]
  }
}
```

### Example: Battle Royale Match Schema

```json
{
  "name": "battle_royale_multi_team",
  "discipline": "Fortnite",
  "target_entity": "MATCH",
  "json_schema": {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "object",
    "properties": {
      "teams": {
        "type": "array",
        "minItems": 2,
        "maxItems": 20,
        "items": {
          "type": "object",
          "properties": {
            "team_id": {"type": "string"},
            "placement": {"type": "integer", "minimum": 1},
            "kills": {"type": "integer", "minimum": 0},
            "survival_time": {"type": "number"},
            "eliminated_by": {"type": "string"}
          },
          "required": ["team_id", "placement", "kills"]
        }
      },
      "match_duration": {"type": "number"},
      "zone_timings": {
        "type": "array",
        "items": {"type": "number"}
      }
    },
    "required": ["teams"]
  }
}
```

---

## Schema Lifecycle

### 1. Create Schema

```bash
POST /schemas
Content-Type: application/json
X-API-Key: admin-key

{
  "name": "my_game_schema",
  "discipline": "My Game",
  "target_entity": "MATCH",
  "json_schema": {...}
}
```

Response:
```json
{
  "id": "uuid-schema",
  "name": "my_game_schema",
  "version": 1,
  "is_active": true
}
```

### 2. Use Schema in Tournament

```bash
POST /tournaments
Content-Type: application/json
X-API-Key: organizer-key

{
  "name": "My Tournament",
  "discipline": "My Game",
  "metadata": {
    "team_schema_id": "uuid-team-schema",
    "match_schema_id": "uuid-schema"
  }
}
```

### 3. Schema Becomes Locked

Once you add the first team or match:
```bash
POST /tournaments/{id}/teams
# After this request, schemas are LOCKED
```

Attempting to change locked schemas:
```bash
PUT /tournaments/{id}
{
  "metadata": {
    "match_schema_id": "new-uuid"  # ❌ Returns 400 Bad Request
  }
}
```

### 4. Update Schema (New Version)

To improve a schema:
```bash
PUT /schemas/{id}
{
  "name": "my_game_schema",
  "json_schema": {...improved version...}
}
```

This creates version 2. Version 1 remains unchanged and continues to be used by existing tournaments.

### 5. Deprecate Old Schema

When no new tournaments should use an old schema:
```bash
PATCH /schemas/{id}/deactivate
```

Existing tournaments continue using it, but new tournaments cannot select it.

---

## Validation Behavior

### When Validation Occurs

1. **Team Registration**: `players` and `metadata` validated against team schema
2. **Score Submission**: `score` and `metadata` validated against match schema
3. **Tournament Creation**: Custom fields validated against tournament schema (if specified)

### Validation Errors

Invalid data returns detailed errors:

```json
{
  "detail": "Schema validation failed",
  "errors": [
    {
      "field": "players[0].steam_id",
      "message": "does not match pattern '^STEAM_[0-5]:[0-1]:\\d+$'",
      "value": "invalid-id"
    },
    {
      "field": "players",
      "message": "must have at least 5 items",
      "value": ["Player1", "Player2"]
    }
  ]
}
```

---

## Best Practices

### Schema Design

1. **Start Minimal**: Begin with required fields only, add optional fields later
2. **Use Descriptive Names**: Schema names should indicate purpose and version
3. **Include Examples**: Document expected data formats in schema descriptions
4. **Plan for Evolution**: Design schemas that can be extended without breaking changes

### Versioning Strategy

1. **Semantic Versioning in Names**: Use `csgo_bo3_v1`, `csgo_bo3_v2` naming
2. **Never Modify Published Schemas**: Always create new versions
3. **Deprecate Gradually**: Keep old schemas active until all tournaments complete
4. **Document Changes**: Maintain changelog for each schema

### Discipline-Specific Considerations

**Esports:**
- Include player IDs (Steam, Riot, etc.)
- Support substitute players
- Track social media handles

**Traditional Sports:**
- Support jersey numbers
- Include positions/roles
- Track statistics relevant to the sport

**Virtual Competitions:**
- Support large team counts (battle royale)
- Include placement-based scoring
- Track in-game metrics

---

## Querying Schemas

### List Active Schemas for Discipline

```bash
GET /schemas?discipline=CS:GO&is_active=true
```

### Get Latest Version of Schema

```bash
GET /schemas?name=csgo_best_of_3&limit=1
# Returns highest version number
```

### Find Schemas by Target Entity

```bash
GET /schemas?target_entity=MATCH
```

---

## Advanced Features

### Conditional Validation

Use `oneOf` for different match formats:

```json
{
  "properties": {
    "score_format": {
      "oneOf": [
        {
          "type": "object",
          "properties": {
            "best_of": {"const": 1},
            "winner": {"type": "string"}
          }
        },
        {
          "type": "object",
          "properties": {
            "best_of": {"const": 3},
            "maps": {"type": "array"}
          }
        }
      ]
    }
  }
}
```

### Custom Format Validators

For complex validation beyond JSON Schema:

```python
# In your service layer
def validate_custom_rules(data: dict, schema_context: dict) -> bool:
    # Custom logic here
    if data.get("best_of") == 3 and len(data.get("maps", [])) > 3:
        raise ValueError("Best of 3 cannot have more than 3 maps")
    return True
```

---

## Troubleshooting

### Common Issues

**Issue**: "Schema not found"
- **Cause**: Referencing non-existent or inactive schema
- **Solution**: Check schema ID and ensure `is_active=true`

**Issue**: "Cannot change schema after lock"
- **Cause**: Attempting to modify locked tournament schemas
- **Solution**: Create new tournament with desired schemas

**Issue**: "Validation fails unexpectedly"
- **Cause**: Data doesn't match schema constraints
- **Solution**: Review schema definition and error details

---

## Next Steps

Continue reading:
- [Bracket Engine](./07-bracket-engine.md) - How brackets are generated
- [Authentication & Authorization](./08-authentication.md) - Managing access control
