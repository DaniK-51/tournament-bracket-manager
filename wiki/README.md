# Tournament Management System - Developer Wiki

Welcome to the developer wiki for the Tournament Management System. This wiki is designed to help new developers understand the project architecture, technology stack, and implementation details.

## Table of Contents

1. [Project Overview](./01-project-overview.md)
2. [Technology Stack](./02-technology-stack.md)
3. [System Architecture](./03-system-architecture.md)
4. [Data Model](./04-data-model.md)
5. [API Reference](./05-api-reference.md)
6. [Schema Registry](./06-schema-registry.md)
7. [Bracket Engine](./07-bracket-engine.md)
8. [Authentication & Authorization](./08-authentication.md)
9. [Audit Trail](./09-audit-trail.md)
10. [Development Guide](./10-development-guide.md)
11. [Testing Strategy](./11-testing.md)
12. [Deployment](./12-deployment.md)

## Quick Start for New Developers

If you're new to this project, we recommend reading the documentation in the following order:

1. **Start with** [Project Overview](./01-project-overview.md) to understand what we're building
2. **Review** [Technology Stack](./02-technology-stack.md) to familiarize yourself with the tools
3. **Study** [System Architecture](./03-system-architecture.md) to understand the component design
4. **Explore** [Data Model](./04-data-model.md) to learn about database structure
5. **Follow** [Development Guide](./10-development-guide.md) to set up your environment

## Key Concepts

### Universal Tournament Format
This system supports **ANY competition format** across **ALL disciplines**:
- Esports (CS:GO, League of Legends, Dota 2)
- Traditional Sports (Basketball, Soccer, Tennis)
- Virtual Competitions (Racing, Battle Royale)
- Board Games (Chess, Go)

### Runtime Schema Flexibility
The system uses a JSON Schema registry that allows organizers to define discipline-specific data formats without code changes. Schemas are locked at tournament creation to ensure data consistency.

### Graph-Based Brackets
Tournament brackets are stored as directed graphs where:
- Nodes represent matches, groups, or final positions
- Edges represent progression paths (winner/loser advancement)
- UUIDs are used for all references

## Project Status

Refer to [PLAN.md](../PLAN.md) for the complete implementation plan and current status.

## Contributing

Before contributing, please read the [Development Guide](./10-development-guide.md) for coding standards and contribution workflow.

## License

See [LICENSE](../LICENSE) for licensing information.
