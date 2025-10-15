# Database Migrations

This directory contains SQL migration scripts for the OpenShift Partner Labs MCP Server database.

## Migration Files

- `001_create_tables.sql` - Initial database schema creation

## Running Migrations

### Manual Execution

Connect to your PostgreSQL database and run the migration files in order:

```bash
# Using psql
psql -h localhost -p 5432 -U postgres -d openshift_partner_labs_mcp_server -f migrations/001_create_tables.sql
```

### Using Environment Variables

```bash
export POSTGRES_HOST=localhost
export POSTGRES_PORT=5432
export POSTGRES_DB=openshift_partner_labs_mcp_server
export POSTGRES_USER=postgres
export POSTGRES_PASSWORD=yourpassword

psql -h $POSTGRES_HOST -p $POSTGRES_PORT -U $POSTGRES_USER -d $POSTGRES_DB -f migrations/001_create_tables.sql
```

### Docker/Podman

If running PostgreSQL in a container:

```bash
# Copy migration file to container
podman cp migrations/001_create_tables.sql postgres-container:/tmp/

# Execute migration
podman exec -i postgres-container psql -U postgres -d openshift_partner_labs_mcp_server -f /tmp/001_create_tables.sql
```

## Database Schema

The initial migration creates the following tables:

### users
- `id` - Primary key
- `username` - Unique username
- `email` - User email address
- `red_hat_uuid` - Optional Red Hat SSO UUID
- `created_at` - Timestamp of creation
- `updated_at` - Timestamp of last update

### clusters
- `id` - Primary key
- `name` - Unique cluster name
- `namespace` - Kubernetes namespace
- `owner_id` - Foreign key to users table
- `status` - Current cluster status
- `cluster_type` - Type of cluster (e.g., 'ocp', 'rosa')
- `provider` - Cloud provider ('aws', 'azure', 'gcp')
- `region` - Cloud region
- `acm_managed_cluster_name` - ACM managed cluster name
- `hibernation_enabled` - Whether hibernation is enabled
- `created_at` - Timestamp of creation
- `updated_at` - Timestamp of last update
- `deleted_at` - Soft delete timestamp

### cluster_events
- `id` - Primary key
- `cluster_id` - Foreign key to clusters table
- `event_type` - Type of event
- `description` - Event description
- `metadata` - JSON metadata
- `created_at` - Timestamp of event

## Views

- `active_clusters` - View of non-deleted clusters with owner information
- `cluster_stats` - Summary statistics of clusters by provider and status

## Indexes

The migration creates appropriate indexes for:
- User lookups by username, email, and Red Hat UUID
- Cluster lookups by name, owner, status, provider, and timestamps
- Event lookups by cluster and event type

## Permissions

The migration grants necessary permissions to the `openshift_partner_labs_mcp_server` user. Adjust the `GRANT` statements in the migration file based on your security requirements.

## Future Migrations

When adding new migrations:

1. Create a new file with incremental numbering: `002_description.sql`
2. Include a description comment at the top
3. Use `IF NOT EXISTS` clauses where appropriate
4. Test the migration on a copy of production data
5. Update this README with the new migration details