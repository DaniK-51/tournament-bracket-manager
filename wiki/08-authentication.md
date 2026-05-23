# Authentication & Authorization

This document describes the authentication and authorization system for the Tournament Management System.

## Overview

The system uses API key-based authentication with role-based access control (RBAC). This approach is chosen for:
- Simple integration with external systems (overlays, bots, admin panels)
- No OAuth complexity for internal tools
- Fine-grained permission control
- Easy key rotation and revocation

---

## Authentication Flow

### 1. API Key Generation

Admins create API keys for users/systems:

```bash
POST /auth/keys
{
  "role": "organizer",
  "tournament_id": "uuid-tournament",  // Optional: scope to specific tournament
  "permissions": {
    "can_edit_schemas": false,
    "can_delete_matches": true
  },
  "expires_at": "2024-12-31T23:59:59Z"
}
```

Response includes the plain text key **once**:

```json
{
  "id": "uuid-key",
  "key": "sk_live_abc123xyz789...",  // Store this securely!
  "role": "organizer",
  "created_at": "2024-01-20T10:00:00Z"
}
```

⚠️ **Important**: The plain text key is only shown once. Store it securely.

### 2. API Request Authentication

Clients include the API key in requests:

```http
GET /tournaments/uuid-tournament
X-API-Key: sk_live_abc123xyz789...
```

### 3. Server-Side Validation

Middleware validates the key on every request:

```python
async def auth_middleware(request: Request, call_next):
    api_key = request.headers.get("X-API-Key")
    
    if not api_key:
        raise HTTPException(status_code=401, detail="Missing API key")
    
    # Hash and compare
    api_key_data = await verify_api_key(api_key)
    
    if not api_key_data:
        raise HTTPException(status_code=401, detail="Invalid API key")
    
    # Check expiration
    if api_key_data.expires_at and api_key_data.expires_at < datetime.utcnow():
        raise HTTPException(status_code=401, detail="API key expired")
    
    # Attach to request context
    request.state.api_key = api_key_data
    
    response = await call_next(request)
    return response
```

---

## Roles and Permissions

### Built-in Roles

| Role | Description | Default Permissions |
|------|-------------|---------------------|
| `admin` | System administrator | Full access to all resources |
| `organizer` | Tournament organizer | Full access to assigned tournaments |
| `judge` | Match judge | Update match scores only |
| `overlay_director` | Overlay operator | Read-only access for overlays |

### Permission Matrix

| Permission | admin | organizer | judge | overlay_director |
|------------|-------|-----------|-------|------------------|
| Create tournaments | ✅ | ❌ | ❌ | ❌ |
| Edit any tournament | ✅ | ❌ | ❌ | ❌ |
| Edit assigned tournaments | ✅ | ✅ | ❌ | ❌ |
| Manage schemas | ✅ | ❌ | ❌ | ❌ |
| Manage API keys | ✅ | ❌ | ❌ | ❌ |
| View audit log | ✅ | ❌ | ❌ | ❌ |
| Update match scores | ✅ | ✅ | ✅ | ❌ |
| View matches | ✅ | ✅ | ✅ | ✅ |
| WebSocket subscriptions | ✅ | ✅ | ✅ | ✅ |

### Custom Permissions

Organizers can have fine-grained permissions:

```json
{
  "can_edit_schemas": false,
  "can_delete_matches": true,
  "can_manage_teams": true,
  "can_view_audit_log": false,
  "can_create_api_keys": false
}
```

---

## Tournament Scoping

API keys can be scoped to specific tournaments:

```python
# Key scoped to single tournament
api_key = APIKey(
    role="organizer",
    tournament_id=uuid_tournament,  # Can only access this tournament
    permissions={}
)

# Key with global access
api_key = APIKey(
    role="admin",
    tournament_id=None,  # Can access all tournaments
    permissions={}
)
```

When a key is scoped, the middleware enforces access:

```python
async def check_tournament_access(
    requested_tournament_id: UUID,
    api_key: APIKey
) -> bool:
    if api_key.tournament_id is None:
        return True  # Admin access
    
    return api_key.tournament_id == requested_tournament_id
```

---

## Password Hashing

API keys are hashed with bcrypt before storage:

```python
import bcrypt
from secrets import token_urlsafe

def generate_api_key() -> str:
    """Generate cryptographically secure API key."""
    return token_urlsafe(32)  # 256-bit entropy

def hash_api_key(key: str) -> str:
    """Hash API key with bcrypt."""
    salt = bcrypt.gensalt(rounds=12)
    return bcrypt.hashpw(key.encode(), salt).decode()

def verify_api_key(key: str, hashed: str) -> bool:
    """Verify API key against hash."""
    return bcrypt.checkpw(key.encode(), hashed.encode())
```

---

## Key Rotation

### Rotating Compromised Keys

```bash
# 1. Revoke old key
DELETE /auth/keys/{old-key-id}

# 2. Create new key
POST /auth/keys
{
  "role": "organizer",
  "tournament_id": "uuid-tournament"
}

# 3. Update all systems using the key
# Distribute new key securely
```

### Scheduled Rotation

Implement automatic expiration:

```python
# Create key with 90-day expiration
expires_at = datetime.utcnow() + timedelta(days=90)

api_key = APIKey(
    role="organizer",
    expires_at=expires_at
)
```

---

## WebSocket Authentication

WebSocket connections authenticate via query parameter or subprotocol:

### Query Parameter Method

```javascript
const ws = new WebSocket(
  'ws://localhost:8000/ws/tournaments/uuid?api_key=sk_live_...'
);
```

### Header Method (Subprotocol)

```javascript
const ws = new WebSocket(
  'ws://localhost:8000/ws/tournaments/uuid',
  ['Bearer', 'sk_live_...']
);
```

Server-side validation:

```python
@app.websocket("/ws/tournaments/{tournament_id}")
async def websocket_endpoint(websocket: WebSocket, tournament_id: UUID):
    # Get API key from query or headers
    api_key = websocket.query_params.get("api_key")
    
    if not api_key:
        await websocket.close(code=4001)
        return
    
    # Validate key
    api_key_data = await verify_api_key(api_key)
    
    if not api_key_data:
        await websocket.close(code=4002)
        return
    
    # Check tournament access
    if not await check_tournament_access(tournament_id, api_key_data):
        await websocket.close(code=4003)
        return
    
    # Accept connection
    await manager.connect(websocket, tournament_id, api_key_data)
```

---

## Security Best Practices

### 1. Secure Key Storage

**Never:**
- ❌ Store keys in plain text
- ❌ Commit keys to version control
- ❌ Share keys via insecure channels

**Always:**
- ✅ Use environment variables
- ✅ Use secret management services (AWS Secrets Manager, HashiCorp Vault)
- ✅ Rotate keys regularly

### 2. Principle of Least Privilege

Give users only the permissions they need:

```python
# Bad: Giving admin access to judge
api_key = APIKey(role="admin")  # ❌ Too much access

# Good: Specific role with minimal permissions
api_key = APIKey(
    role="judge",
    permissions={
        "can_update_scores": True,
        "can_delete_matches": False
    }
)  # ✅ Minimal access
```

### 3. Rate Limiting

Implement rate limiting per API key:

```python
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@router.get("/tournaments/{id}")
@limiter.limit("100/minute")
async def get_tournament(request: Request, id: UUID):
    ...
```

Rate limits by role:
- `admin`: 1000 requests/minute
- `organizer`: 500 requests/minute
- `judge`: 200 requests/minute
- `overlay_director`: 100 requests/minute

### 4. Audit All Authentication Events

Log authentication attempts:

```python
await audit_service.log_event(
    entity_type="authentication",
    action="api_key_used",
    metadata={
        "api_key_id": str(api_key.id),
        "endpoint": request.url.path,
        "method": request.method,
        "ip_address": client_ip,
        "user_agent": request.headers.get("User-Agent"),
        "success": True
    }
)
```

---

## Error Codes

### HTTP Authentication Errors

| Status Code | Meaning | Response |
|-------------|---------|----------|
| 401 | Missing API key | `{"detail": "Missing API key"}` |
| 401 | Invalid API key | `{"detail": "Invalid API key"}` |
| 401 | Expired API key | `{"detail": "API key has expired"}` |
| 403 | Insufficient permissions | `{"detail": "Insufficient permissions"}` |
| 403 | Tournament access denied | `{"detail": "Access denied to this tournament"}` |

### WebSocket Close Codes

| Code | Meaning |
|------|---------|
| 4001 | Missing authentication |
| 4002 | Invalid API key |
| 4003 | Tournament access denied |
| 4004 | Key expired during session |

---

## Implementation Example

### Complete Auth Flow

```python
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import APIKeyHeader
from sqlalchemy.ext.asyncio import AsyncSession

app = FastAPI()

API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)

async def get_current_api_key(
    api_key: str = Depends(API_KEY_HEADER),
    db: AsyncSession = Depends(get_db_session)
) -> APIKey:
    """Get and validate current API key."""
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API key"
        )
    
    # Hash and lookup
    result = await db.execute(
        select(APIKey).where(APIKey.is_active == True)
    )
    
    for key in result.scalars():
        if verify_api_key(api_key, key.key_hash):
            # Check expiration
            if key.expires_at and key.expires_at < datetime.utcnow():
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="API key expired"
                )
            
            return key
    
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid API key"
    )

@router.get("/tournaments/{tournament_id}")
async def get_tournament(
    tournament_id: UUID,
    current_api_key: APIKey = Depends(get_current_api_key),
    db: AsyncSession = Depends(get_db_session)
):
    """Get tournament with authorization check."""
    # Check tournament access
    if current_api_key.tournament_id:
        if current_api_key.tournament_id != tournament_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this tournament"
            )
    
    # Proceed with request
    tournament = await get_tournament_by_id(db, tournament_id)
    return tournament
```

---

## Next Steps

Continue reading:
- [Audit Trail](./09-audit-trail.md) - Tracking all system changes
- [Development Guide](./10-development-guide.md) - Setting up your environment
