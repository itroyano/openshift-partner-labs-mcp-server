# Archived Tools

This directory contains tools that were developed for an older database schema and are no longer compatible with the current OpenShift Partner Labs implementation.

## Files

### `cluster_tools.py`
- **Status**: Archived (incompatible with current schema)
- **Original Purpose**: Direct cluster management tools for ACM operations
- **Issues**: References non-existent database models (UserCreateRequest, ClusterCreateRequest, etc.)
- **Current Alternative**: Lab management is handled through `../lab_tools.py` which integrates cluster operations with the lab lifecycle

### `database_tools.py`
- **Status**: Archived (incompatible with current schema)
- **Original Purpose**: Database query tools for user and cluster management
- **Issues**: References old schema tables (`users`, `clusters`, `cluster_events`) that don't exist in current PostgreSQL schema
- **Current Alternative**: Database operations are integrated into lab and company management tools

## Schema Evolution

The current OpenShift Partner Labs schema focuses on:
- **Companies**: Partner organizations (`companies` table)
- **Labs**: Partner lab instances with full lifecycle management (`labs` table)
- **Events**: Optional audit trail for lab operations (`lab_events` table)

The older schema these tools were designed for included:
- **Users**: Individual user management (replaced by contact fields in labs)
- **Clusters**: Direct cluster management (integrated into lab lifecycle)
- **Cluster Events**: Cluster-specific events (replaced by lab events)

## Reference Value

These files are preserved for:
- **Historical reference** - Understanding the evolution of the codebase
- **Code patterns** - Useful patterns for ACM integration and database operations
- **Future development** - Potential basis for additional tooling if needed

## Note

**These files are not imported or registered in the MCP server** and will not be executed. They are kept purely for reference and potential future use.