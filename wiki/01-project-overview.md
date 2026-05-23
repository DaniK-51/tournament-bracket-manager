# Project Overview

## What is This Project?

The Tournament Management System is a **universal backend application** that manages tournaments for any competition format across all disciplines. It stores tournament brackets and team lists, providing structured workflows for judges and overlay directors.

## Core Purpose

This system solves the problem of managing complex tournament structures across different competitive disciplines:

- **Esports**: CS:GO, League of Legends, Dota 2, Valorant
- **Traditional Sports**: Basketball, Soccer, Tennis, Chess
- **Virtual Competitions**: Racing simulators, Battle Royale games
- **Any Competition Format**: Single elimination, double elimination, round robin, Swiss, custom formats

## Key Features

### 1. Universal Format Support
The system can handle any tournament structure through runtime-configurable JSON Schemas. No code changes are needed to support new game types or competition formats.

### 2. Graph-Based Bracket Storage
Tournament brackets are stored as directed graphs:
- **Nodes** represent matches, groups, or final positions
- **Edges** define progression paths (who advances where)
- **UUIDs** provide stable references for API operations

### 3. Schema Locking
When a tournament is created, it locks to specific schema versions. This ensures:
- Data consistency throughout the tournament lifecycle
- No breaking changes mid-tournament
- Ability to evolve schemas for future tournaments

### 4. External Overlay Architecture
This service focuses on data storage and management. Overlays render externally, consuming data via REST API or WebSocket connections.

### 5. Complete Audit Trail
Every change is tracked with full history:
- Who made the change
- When it was made
- What changed (before/after snapshots)
- Why it was changed (optional context)

## Use Cases

### Judge Workflow
Judges can:
- Record match results with discipline-specific data
- Validate scores against schema rules
- Track match status (scheduled, in progress, completed)
- Add metadata (VOD links, referee notes, etc.)

### Overlay Director Workflow
Overlay directors can:
- Subscribe to real-time updates via WebSocket
- Fetch bracket state for visualization
- Access match data for display
- Receive instant notifications on score changes

### Tournament Organizer Workflow
Organizers can:
- Create tournaments with custom data schemas
- Register teams with flexible player information
- Configure bracket structures
- Manage API keys for different roles

## Tournament Structure Example

```
Tournament: "Winter Championship 2024"
├── ID: 6-digit number (e.g., 123456)
├── Discipline: "CS:GO"
├── Format: Double Elimination
├── Schema References:
│   ├── Team Schema: "csgo_team_v2"
│   └── Match Schema: "csgo_best_of_3_v1"
└── Bracket (Directed Graph):
    ├── Node A (Stage Match)
    │   ├── Match 1: Team X vs Team Y
    │   └── Next: Winner → Node C, Loser → Node B
    ├── Node B (Losers Round 1)
    │   ├── Match 2: Loser of A vs Team Z
    │   └── Next: Winner → Node D, Loser → Eliminated
    └── Node C (Winners Final)
        └── ... continues to Grand Final
```

## Entity Relationships

```
┌─────────────┐       ┌─────────────┐
│ Tournament  │◄──────│   Schema    │
│             │       │  Registry   │
└──────┬──────┘       └─────────────┘
       │
       ├──────────────┐
       │              │
       ▼              ▼
┌─────────────┐  ┌─────────────┐
│    Team     │  │    Node     │
└─────────────┘  └──────┬──────┘
                        │
                        ▼
                  ┌─────────────┐
                  │   Match     │
                  └─────────────┘
```

## API Design Philosophy

The API follows RESTful principles with these key endpoints:

- `POST /new/{ID}` - Create new tournament
- `GET /{ID}` - Get tournament by ID
- `GET /{UUID}` - Get specific node/match by UUID
- `PUT /{ID}/{UUID}` - Update node/match
- `POST /{ID}/add` - Add team/match to tournament

See [API Reference](./05-api-reference.md) for complete endpoint documentation.

## Performance Targets

The system is designed to handle:
- **1000+ concurrent big tournaments**
- **Sub-100ms read latency**
- **High write throughput** during peak match times

## Next Steps

Continue reading:
- [Technology Stack](./02-technology-stack.md) - Tools and technologies used
- [System Architecture](./03-system-architecture.md) - Component design and interactions
