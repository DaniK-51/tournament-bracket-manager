# Audit Trail Guide

The audit trail system provides complete visibility into all changes made in the Tournament Management System.

## Purpose

The audit trail serves several critical purposes:

1. **Accountability**: Track who made each change
2. **Debugging**: Understand what changed and when
3. **Compliance**: Meet regulatory requirements for data tracking
4. **Disaster Recovery**: Restore previous states if needed
5. **Analytics**: Analyze usage patterns and system behavior

---

## What Gets Audited

### Automatic Auditing

The following operations are automatically audited:

| Entity | Actions Audited | Details Captured |
|--------|-----------------|------------------|
| Tournament | Create, Update, Archive | All field changes |
| Team | Create, Update, Delete | Roster changes, metadata updates |
| Match | Create, Update, Score changes | Score before/after, status changes |
| Node | Create, Update | Bracket structure changes |
| Schema | Create, Update, Deactivate | Schema version changes |
| API Key | Create, Revoke | Key lifecycle events |

### Manual Auditing

Custom business logic can log additional events:

```python
await audit_service.log_event(
    entity_type="tournament",
    entity_id=str(tournament_id),
    action="bracket_regenerated",
    context={"reason": "Team count changed", "old_count": 8, "new_count": 16},
    actor_id=str(api_key.id)
)
```

---

## Audit Log Structure

### Database Schema

```sql
CREATE TABLE audit_log (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    entity_type VARCHAR(50) NOT NULL,
    entity_id UUID NOT NULL,
    action VARCHAR(50) NOT NULL,
    before JSONB,
    after JSONB,
    actor_id UUID REFERENCES api_keys(id),
    context JSONB,
    timestamp TIMESTAMP NOT NULL DEFAULT now()
);

-- Indexes for efficient querying
CREATE INDEX idx_audit_entity ON audit_log(entity_type, entity_id);
CREATE INDEX idx_audit_timestamp ON audit_log(timestamp DESC);
CREATE INDEX idx_audit_actor ON audit_log(actor_id);
```

### Entry Structure

```json
{
  "id": "uuid-audit-entry",
  "entity_type": "match",
  "entity_id": "uuid-match",
  "action": "score_updated",
  "before": {
    "score": {"team_a": 1, "team_b": 0},
    "status": "in_progress",
    "winner_id": null
  },
  "after": {
    "score": {"team_a": 2, "team_b": 0},
    "status": "completed",
    "winner_id": "uuid-team-a"
  },
  "actor_id": "uuid-api-key",
  "context": {
    "ip_address": "192.168.1.100",
    "user_agent": "JudgePanel/1.0"
  },
  "timestamp": "2024-01-20T15:30:00Z"
}
```

---

## Querying Audit Logs

### Get Entity History

```bash
GET /audit/match/uuid-match
```

Response:
```json
{
  "entity_type": "match",
  "entity_id": "uuid-match",
  "history": [
    {
      "id": "uuid-1",
      "action": "created",
      "before": null,
      "after": {
        "team_a_id": "uuid-a",
        "team_b_id": "uuid-b",
        "status": "scheduled"
      },
      "timestamp": "2024-01-20T10:00:00Z"
    },
    {
      "id": "uuid-2",
      "action": "status_changed",
      "before": {"status": "scheduled"},
      "after": {"status": "in_progress"},
      "timestamp": "2024-01-20T14:00:00Z"
    },
    {
      "id": "uuid-3",
      "action": "score_updated",
      "before": {"score": {}, "status": "in_progress"},
      "after": {"score": {"team_a": 2}, "status": "completed"},
      "timestamp": "2024-01-20T15:30:00Z"
    }
  ]
}
```

### Filter by Time Range

```bash
GET /audit?from=2024-01-20T00:00:00Z&to=2024-01-20T23:59:59Z
```

### Filter by Actor

```bash
GET /audit?actor_id=uuid-judge
```

### Filter by Action Type

```bash
GET /audit?action=score_updated
```

---

## Implementation

### Service Layer

```python
class AuditService:
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def log_change(
        self,
        entity_type: str,
        entity_id: str,
        action: str,
        before: Optional[dict],
        after: Optional[dict],
        actor_id: str,
        context: Optional[dict] = None
    ) -> AuditLog:
        """Log an entity change."""
        entry = AuditLog(
            entity_type=entity_type,
            entity_id=entity_id,
            action=action,
            before=before,
            after=after,
            actor_id=actor_id,
            context=context
        )
        
        self.db.add(entry)
        await self.db.commit()
        
        return entry
    
    async def get_entity_history(
        self,
        entity_type: str,
        entity_id: str
    ) -> List[AuditLog]:
        """Get complete history for an entity."""
        result = await self.db.execute(
            select(AuditLog)
            .where(
                AuditLog.entity_type == entity_type,
                AuditLog.entity_id == entity_id
            )
            .order_by(AuditLog.timestamp.asc())
        )
        
        return result.scalars().all()
```

### Automatic Hook Example

```python
from sqlalchemy import event

@event.listens_for(Match, 'before_update')
def receive_before_update(mapper, connection, target):
    """Automatically log match updates."""
    # Get current state from database
    old_state = get_current_state(target.id)
    
    # Get new state
    new_state = target.dict()
    
    # Determine what changed
    changes = get_changes(old_state, new_state)
    
    if changes:
        # Queue audit log (will be committed with transaction)
        queue_audit_log(
            entity_type="match",
            entity_id=str(target.id),
            action="updated",
            before=old_state,
            after=new_state,
            changes=changes
        )
```

---

## Use Cases

### 1. Dispute Resolution

When there's a dispute about a match result:

```bash
# Get complete match history
GET /audit/match/uuid-contested-match

# Review all score changes
GET /audit/match/uuid-contested-match?action=score_updated
```

### 2. Investigating Suspicious Activity

```bash
# Find all changes by specific user
GET /audit?actor_id=uuid-suspect

# Find all deletions in time range
GET /audit?action=deleted&from=2024-01-20T00:00:00Z
```

### 3. Restoring Previous State

```python
async def restore_entity_state(
    entity_type: str,
    entity_id: str,
    target_timestamp: datetime
):
    """Restore entity to previous state."""
    # Get audit entries up to target timestamp
    history = await audit_service.get_entity_history(
        entity_type, entity_id
    )
    
    # Find state at target time
    target_state = None
    for entry in history:
        if entry.timestamp <= target_timestamp:
            target_state = entry.after
        else:
            break
    
    if target_state:
        # Apply restoration
        await restore_from_state(entity_type, entity_id, target_state)
        
        # Log restoration
        await audit_service.log_event(
            entity_type=entity_type,
            entity_id=entity_id,
            action="restored",
            context={
                "restored_to_timestamp": target_timestamp.isoformat(),
                "reason": "Data corruption recovery"
            }
        )
```

### 4. Compliance Reporting

```python
async def generate_compliance_report(
    tournament_id: UUID,
    start_date: date,
    end_date: date
) -> dict:
    """Generate compliance report for tournament."""
    audit_entries = await audit_service.get_tournament_audit(
        tournament_id, start_date, end_date
    )
    
    report = {
        "tournament_id": str(tournament_id),
        "period": {
            "start": start_date.isoformat(),
            "end": end_date.isoformat()
        },
        "summary": {
            "total_changes": len(audit_entries),
            "score_changes": len([e for e in audit_entries if e.action == "score_updated"]),
            "structural_changes": len([e for e in audit_entries if e.action == "bracket_updated"]),
            "unique_actors": len(set(e.actor_id for e in audit_entries))
        },
        "entries": audit_entries
    }
    
    return report
```

---

## Retention Policy

### Default Retention

| Data Age | Retention |
|----------|-----------|
| 0-30 days | Full detail |
| 30-90 days | Full detail |
| 90-365 days | Summary only (no before/after) |
| 1+ years | Archived (cold storage) |

### Archival Process

```python
async def archive_old_audit_logs():
    """Archive audit logs older than 1 year."""
    cutoff_date = datetime.utcnow() - timedelta(days=365)
    
    # Get old entries
    old_entries = await db.execute(
        select(AuditLog).where(AuditLog.timestamp < cutoff_date)
    )
    
    # Export to cold storage
    await export_to_archive(old_entries.scalars().all())
    
    # Delete or truncate old entries
    await db.execute(
        delete(AuditLog).where(AuditLog.timestamp < cutoff_date)
    )
    
    await db.commit()
```

---

## Performance Optimization

### Partitioning

For high-volume systems, partition audit_log by time:

```sql
CREATE TABLE audit_log (
    id UUID DEFAULT uuid_generate_v4(),
    entity_type VARCHAR(50) NOT NULL,
    entity_id UUID NOT NULL,
    action VARCHAR(50) NOT NULL,
    before JSONB,
    after JSONB,
    actor_id UUID,
    timestamp TIMESTAMP NOT NULL DEFAULT now()
) PARTITION BY RANGE (timestamp);

-- Create monthly partitions
CREATE TABLE audit_log_2024_01 PARTITION OF audit_log
    FOR VALUES FROM ('2024-01-01') TO ('2024-02-01');

CREATE TABLE audit_log_2024_02 PARTITION OF audit_log
    FOR VALUES FROM ('2024-02-01') TO ('2024-03-01');
```

### Selective Auditing

For very high-frequency operations, audit only significant changes:

```python
def should_audit_score_change(old_score: dict, new_score: dict) -> bool:
    """Only audit meaningful score changes."""
    # Don't audit minor updates during live scoring
    if old_score.get('team_a') == new_score.get('team_a') and \
       old_score.get('team_b') == new_score.get('team_b'):
        return False
    
    # Do audit final score
    if new_score.get('status') == 'completed':
        return True
    
    # Do audit if score difference changed
    old_diff = old_score.get('team_a', 0) - old_score.get('team_b', 0)
    new_diff = new_score.get('team_a', 0) - new_score.get('team_b', 0)
    
    return old_diff != new_diff
```

---

## Security Considerations

### Tamper Prevention

1. **Immutable Records**: Never update or modify audit entries
2. **Append-Only**: Only INSERT operations allowed on audit_log
3. **Database Permissions**: Restrict DELETE/UPDATE on audit_log table
4. **Hash Chain**: Optionally hash entries to detect tampering

```python
import hashlib

def calculate_entry_hash(entry: AuditLog, previous_hash: str) -> str:
    """Calculate hash for integrity verification."""
    content = f"{previous_hash}{entry.entity_type}{entry.entity_id}{entry.timestamp}"
    return hashlib.sha256(content.encode()).hexdigest()
```

### Access Control

Audit logs should only be accessible to:
- `admin` role: Full access
- `organizer` role: Access to their tournaments only
- Others: No access (unless explicitly granted)

---

## Next Steps

Continue reading:
- [Testing Strategy](./11-testing.md) - Testing best practices
- [Deployment](./12-deployment.md) - Production deployment guide
