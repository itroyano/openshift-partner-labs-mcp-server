# Database Migrations

This directory contains SQL migration scripts for the OpenShift Partner Labs MCP Server database.

## Migration Files

- `002_labs_schema.sql` - OpenShift Partner Labs schema with companies and labs tables

## Running Migrations

### Manual Execution

Connect to your PostgreSQL database and run the migration files in order:

```bash
# Using psql
psql -h localhost -p 5432 -U postgres -d openshift_partner_labs_app -f migrations/002_labs_schema.sql
```

### Using Environment Variables

```bash
export DATABASE_HOST=localhost
export DATABASE_PORT=5432
export DATABASE_DB=openshift_partner_labs_app
export DATABASE_USER=postgres
export DATABASE_PASSWORD=yourpassword

psql -h $DATABASE_HOST -p $DATABASE_PORT -U $DATABASE_USER -d $DATABASE_DB -f migrations/002_labs_schema.sql
```

### Docker/Podman

If running PostgreSQL in a container:

```bash
# Copy migration file to container
podman cp migrations/002_labs_schema.sql postgres-container:/tmp/

# Execute migration
podman exec -i postgres-container psql -U postgres -d openshift_partner_labs_app -f /tmp/002_labs_schema.sql
```

## Database Schema

The migration creates the following tables for OpenShift Partner Labs management:

### companies
- `id` - Primary key (integer)
- `company_name` - Partner company name (varchar 64, NOT NULL)
- `curated` - Curated partner status (smallint: 0=no, 1=yes)
- `created_at` - Timestamp of creation
- `updated_at` - Timestamp of last update

### labs
- `id` - Primary key (integer)
- `cluster_id` - UUID of the OpenShift cluster (char 36, NOT NULL)
- `generated_name` - Human-friendly lab name (varchar 32, UNIQUE)
- `state` - Lab lifecycle state (varchar 12): pending, approved, active, extended, completed, denied
- `cluster_name` - Actual cluster name (varchar 32)
- `openshift_version` - OpenShift version (varchar 16)
- `cluster_size` - Cluster size (varchar 7): small, medium, large, xlarge, custom
- `company_id` - Foreign key to companies table (integer, nullable)
- `request_type` - Lab request type (varchar 12): general, engineering, rosa, rhoai, nvidia, ocpv
- `partner` - Partner lab flag (smallint: 0=no, 1=yes)
- `sponsor` - Lab sponsor email (varchar 64)
- `cloud_provider` - Cloud provider (varchar 8): AWS, Azure, Google, IBM, Oracle, etc.
- `primary_first` - Primary contact first name (varchar 32)
- `primary_last` - Primary contact last name (varchar 32)
- `primary_email` - Primary contact email (varchar 64)
- `secondary_first` - Secondary contact first name (varchar 32)
- `secondary_last` - Secondary contact last name (varchar 32)
- `secondary_email` - Secondary contact email (varchar 64)
- `region` - Deployment region (varchar 5): na1, na2, emea, apac1, apac2, latam
- `always_on` - Always-on flag (smallint: 0=no, 1=yes)
- `project_name` - Project identifier (varchar 32)
- `lease_time` - Lab lease duration (varchar 2): 1d, 1w, 1m, 2w, 2d
- `description` - Lab description (text)
- `notes` - Additional notes (text)
- `start_date` - Lab start date (timestamp)
- `end_date` - Lab end date (timestamp)
- `hold` - Hold flag for manual review (smallint: 0=no, 1=yes)
- `created_at` - Timestamp of creation
- `updated_at` - Timestamp of last update

### lab_events (optional)
- `id` - Primary key (serial)
- `lab_id` - Foreign key to labs table (integer, NOT NULL)
- `event_type` - Type of event (varchar 100)
- `description` - Event description (text)
- `metadata` - JSON metadata (jsonb)
- `created_at` - Timestamp of event

**Note**: The `lab_events` table is optional and commented out in the migration by default. Uncomment the relevant sections to enable full audit trail functionality.

## Indexes

The migration creates comprehensive indexes for optimal performance:

### Company Indexes
- `idx_companies_name` - Company name lookups
- `idx_companies_curated` - Curated partner filtering
- `idx_companies_created_at` - Temporal queries

### Lab Indexes
- `idx_labs_cluster_id` - Cluster ID lookups
- `idx_labs_state` - Lab state filtering
- `idx_labs_company_id` - Company association queries
- `idx_labs_request_type` - Request type filtering
- `idx_labs_partner` - Partner lab filtering
- `idx_labs_cloud_provider` - Cloud provider filtering
- `idx_labs_region` - Region filtering
- `idx_labs_primary_email` - Contact lookups
- `idx_labs_sponsor` - Sponsor filtering
- `idx_labs_start_date` - Start date queries
- `idx_labs_end_date` - End date queries
- `idx_labs_created_at` - Temporal queries
- `idx_labs_always_on` - Always-on lab filtering (partial index)
- `idx_labs_hold` - Hold status filtering (partial index)

### Lab Events Indexes (if enabled)
- `idx_lab_events_lab_id` - Event lookups by lab
- `idx_lab_events_event_type` - Event type filtering
- `idx_lab_events_created_at` - Temporal event queries
- `idx_lab_events_metadata` - JSON metadata queries (GIN index)

## Data Integrity

The migration includes comprehensive check constraints:
- Lab states validation (pending, approved, active, extended, completed, denied)
- Request types validation (general, engineering, rosa, rhoai, nvidia, ocpv)
- Cluster sizes validation (small, medium, large, xlarge, custom)
- Cloud providers validation (AWS, Azure, Google, IBM, Oracle, Alibaba, Linode, Vultr, DigitalO)
- Regions validation (na1, na2, emea, apac1, apac2, latam)
- Lease times validation (1d, 1w, 1m, 2w, 2d)
- Date constraints (end_date > start_date)

## Migration Features

- **Full idempotency**: Can be run multiple times safely
- **Existence checks**: All operations include proper IF EXISTS/IF NOT EXISTS checks
- **Error handling**: Graceful handling of missing objects
- **Comprehensive documentation**: Inline comments explaining each section

## Future Migrations

When adding new migrations:

1. Create a new file with incremental numbering: `003_description.sql`
2. Include a description comment at the top
3. Use proper existence checks (`IF EXISTS`/`IF NOT EXISTS`) for all operations
4. Follow the idempotent patterns established in `002_labs_schema.sql`
5. Test the migration on a copy of production data
6. Update this README with the new migration details

**Migration Naming Convention:**
- `001_*` - Reserved for historical migrations
- `002_labs_schema.sql` - Current OpenShift Partner Labs schema
- `003_*` - Next migration (your addition)

**Best Practices:**
- Always include rollback procedures in migration comments
- Use transactions for complex migrations
- Test with both empty and populated databases
- Document any manual steps required