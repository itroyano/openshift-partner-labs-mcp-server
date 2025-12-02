-- Migration: Labs Schema for OpenShift Partner Labs MCP Server
-- Version: 002
-- Description: PostgreSQL schema matching the exact structure from postgresql_dummy_data_schema.sql

-- Create DB (run as a superuser or a role that can create DBs)
-- Note: This CREATE DATABASE command may fail if DB already exists, which is fine
-- CREATE DATABASE openshift_partner_labs_app;

-- Drop existing objects if they exist (in proper dependency order)

-- Drop constraints if they exist
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'chk_labs_state') THEN
        ALTER TABLE labs DROP CONSTRAINT chk_labs_state;
    END IF;
    IF EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'chk_labs_request_type') THEN
        ALTER TABLE labs DROP CONSTRAINT chk_labs_request_type;
    END IF;
    IF EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'chk_labs_cluster_size') THEN
        ALTER TABLE labs DROP CONSTRAINT chk_labs_cluster_size;
    END IF;
    IF EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'chk_labs_cloud_provider') THEN
        ALTER TABLE labs DROP CONSTRAINT chk_labs_cloud_provider;
    END IF;
    IF EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'chk_labs_region') THEN
        ALTER TABLE labs DROP CONSTRAINT chk_labs_region;
    END IF;
    IF EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'chk_labs_lease_time') THEN
        ALTER TABLE labs DROP CONSTRAINT chk_labs_lease_time;
    END IF;
    IF EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'chk_labs_dates') THEN
        ALTER TABLE labs DROP CONSTRAINT chk_labs_dates;
    END IF;
EXCEPTION
    WHEN undefined_table THEN NULL; -- Ignore if tables don't exist yet
END $$;

-- Drop indexes if they exist
DROP INDEX IF EXISTS idx_companies_name;
DROP INDEX IF EXISTS idx_companies_curated;
DROP INDEX IF EXISTS idx_companies_created_at;
DROP INDEX IF EXISTS idx_labs_cluster_id;
DROP INDEX IF EXISTS idx_labs_state;
DROP INDEX IF EXISTS idx_labs_company_id;
DROP INDEX IF EXISTS idx_labs_request_type;
DROP INDEX IF EXISTS idx_labs_partner;
DROP INDEX IF EXISTS idx_labs_cloud_provider;
DROP INDEX IF EXISTS idx_labs_region;
DROP INDEX IF EXISTS idx_labs_primary_email;
DROP INDEX IF EXISTS idx_labs_sponsor;
DROP INDEX IF EXISTS idx_labs_start_date;
DROP INDEX IF EXISTS idx_labs_end_date;
DROP INDEX IF EXISTS idx_labs_created_at;
DROP INDEX IF EXISTS idx_labs_always_on;
DROP INDEX IF EXISTS idx_labs_hold;

-- Optional: Drop lab_events indexes (uncomment if lab_events table exists)
-- DROP INDEX IF EXISTS idx_lab_events_lab_id;
-- DROP INDEX IF EXISTS idx_lab_events_event_type;
-- DROP INDEX IF EXISTS idx_lab_events_created_at;
-- DROP INDEX IF EXISTS idx_lab_events_metadata;

-- Drop tables if they exist (in dependency order)
DROP TABLE IF EXISTS lab_events;
DROP TABLE IF EXISTS labs;
DROP TABLE IF EXISTS companies;

-- Companies table
CREATE TABLE IF NOT EXISTS companies (
    id           SERIAL PRIMARY KEY,
    company_name varchar(64) NOT NULL,
    curated      smallint    NOT NULL,
    created_at   timestamp   NOT NULL,
    updated_at   timestamp   NOT NULL
);

-- Labs table
CREATE TABLE IF NOT EXISTS labs (
    id              SERIAL       PRIMARY KEY,
    cluster_id      char(36)     NOT NULL,
    generated_name  varchar(32)  NOT NULL,
    state           varchar(12)  NOT NULL,
    cluster_name    varchar(32)  NOT NULL,
    openshift_version varchar(16) NOT NULL,
    cluster_size    varchar(7)   NOT NULL,
    company_id      integer      NULL,
    request_type    varchar(12)  NOT NULL,
    partner         smallint     NOT NULL,
    sponsor         varchar(64)  NOT NULL,
    cloud_provider  varchar(8)   NOT NULL,
    primary_first   varchar(32)  NOT NULL,
    primary_last    varchar(32)  NOT NULL,
    primary_email   varchar(64)  NOT NULL,
    secondary_first varchar(32)  NOT NULL,
    secondary_last  varchar(32)  NOT NULL,
    secondary_email varchar(64)  NOT NULL,
    region          varchar(5)   NOT NULL,
    always_on       smallint     NOT NULL,
    project_name    varchar(32)  NOT NULL,
    lease_time      varchar(2)   NOT NULL,
    description     text         NOT NULL,
    notes           text         NOT NULL,
    start_date      timestamp    NOT NULL,
    end_date        timestamp    NOT NULL,
    hold            smallint     NOT NULL,
    created_at      timestamp    NOT NULL,
    updated_at      timestamp    NOT NULL,
    CONSTRAINT labs_pk UNIQUE (generated_name),
    CONSTRAINT labs_companies_id_fk
        FOREIGN KEY (company_id) REFERENCES companies (id)
);

-- Optional: Create lab_events table for audit trail (uncomment to enable event tracking)
-- CREATE TABLE IF NOT EXISTS lab_events (
--     id SERIAL PRIMARY KEY,
--     lab_id INTEGER NOT NULL REFERENCES labs(id) ON DELETE CASCADE,
--     event_type VARCHAR(100) NOT NULL,
--     description TEXT,
--     metadata JSONB,
--     created_at TIMESTAMP NOT NULL DEFAULT NOW()
-- );

-- Optional: Create indexes for lab_events table (uncomment if lab_events table is enabled)
-- CREATE INDEX IF NOT EXISTS idx_lab_events_lab_id ON lab_events(lab_id);
-- CREATE INDEX IF NOT EXISTS idx_lab_events_event_type ON lab_events(event_type);
-- CREATE INDEX IF NOT EXISTS idx_lab_events_created_at ON lab_events(created_at);
-- CREATE INDEX IF NOT EXISTS idx_lab_events_metadata ON lab_events USING GIN(metadata) WHERE metadata IS NOT NULL;

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_companies_name ON companies(company_name);
CREATE INDEX IF NOT EXISTS idx_companies_curated ON companies(curated);
CREATE INDEX IF NOT EXISTS idx_companies_created_at ON companies(created_at);

CREATE INDEX IF NOT EXISTS idx_labs_cluster_id ON labs(cluster_id);
CREATE INDEX IF NOT EXISTS idx_labs_state ON labs(state);
CREATE INDEX IF NOT EXISTS idx_labs_company_id ON labs(company_id);
CREATE INDEX IF NOT EXISTS idx_labs_request_type ON labs(request_type);
CREATE INDEX IF NOT EXISTS idx_labs_partner ON labs(partner);
CREATE INDEX IF NOT EXISTS idx_labs_cloud_provider ON labs(cloud_provider);
CREATE INDEX IF NOT EXISTS idx_labs_region ON labs(region);
CREATE INDEX IF NOT EXISTS idx_labs_primary_email ON labs(primary_email);
CREATE INDEX IF NOT EXISTS idx_labs_sponsor ON labs(sponsor);
CREATE INDEX IF NOT EXISTS idx_labs_start_date ON labs(start_date);
CREATE INDEX IF NOT EXISTS idx_labs_end_date ON labs(end_date);
CREATE INDEX IF NOT EXISTS idx_labs_created_at ON labs(created_at);
CREATE INDEX IF NOT EXISTS idx_labs_always_on ON labs(always_on) WHERE always_on = 1;
CREATE INDEX IF NOT EXISTS idx_labs_hold ON labs(hold) WHERE hold = 1;

-- Add check constraints for data integrity (with existence checks)
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'chk_labs_state') THEN
        ALTER TABLE labs ADD CONSTRAINT chk_labs_state
            CHECK (state IN ('pending', 'approved', 'active', 'extended', 'completed', 'denied'));
    END IF;
END $$;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'chk_labs_request_type') THEN
        ALTER TABLE labs ADD CONSTRAINT chk_labs_request_type
            CHECK (request_type IN ('general', 'engineering', 'rosa', 'rhoai', 'nvidia', 'ocpv'));
    END IF;
END $$;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'chk_labs_cluster_size') THEN
        ALTER TABLE labs ADD CONSTRAINT chk_labs_cluster_size
            CHECK (cluster_size IN ('small', 'medium', 'large', 'xlarge', 'custom'));
    END IF;
END $$;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'chk_labs_cloud_provider') THEN
        ALTER TABLE labs ADD CONSTRAINT chk_labs_cloud_provider
            CHECK (cloud_provider IN ('AWS', 'Azure', 'Google', 'IBM', 'Oracle', 'Alibaba', 'Linode', 'Vultr', 'DigitalO'));
    END IF;
END $$;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'chk_labs_region') THEN
        ALTER TABLE labs ADD CONSTRAINT chk_labs_region
            CHECK (region IN ('na1', 'na2', 'emea', 'apac1', 'apac2', 'latam'));
    END IF;
END $$;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'chk_labs_lease_time') THEN
        ALTER TABLE labs ADD CONSTRAINT chk_labs_lease_time
            CHECK (lease_time IN ('1d', '1w', '1m', '2w', '2d'));
    END IF;
END $$;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'chk_labs_dates') THEN
        ALTER TABLE labs ADD CONSTRAINT chk_labs_dates
            CHECK (end_date > start_date);
    END IF;
END $$;

-- Add comments for documentation (with existence checks)
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'companies') THEN
        COMMENT ON TABLE companies IS 'Partner companies that can request labs';
    END IF;
END $$;

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'labs') THEN
        COMMENT ON TABLE labs IS 'OpenShift Partner Labs with full lifecycle management';

        -- Add column comments if table exists
        COMMENT ON COLUMN labs.cluster_id IS 'UUID identifier for the cluster';
        COMMENT ON COLUMN labs.generated_name IS 'Human-friendly name for the lab (unique)';
        COMMENT ON COLUMN labs.state IS 'Current state of the lab (pending, approved, active, extended, completed, denied)';
        COMMENT ON COLUMN labs.request_type IS 'Type of lab request (general, engineering, rosa, rhoai, nvidia, ocpv)';
        COMMENT ON COLUMN labs.partner IS 'Whether this is a partner lab (0=no, 1=yes)';
        COMMENT ON COLUMN labs.always_on IS 'Whether the cluster should remain always running (0=no, 1=yes)';
        COMMENT ON COLUMN labs.hold IS 'Whether the lab is on hold (0=no, 1=yes)';
        COMMENT ON COLUMN labs.lease_time IS 'Duration of the lab lease (1d, 1w, 1m, 2w, 2d)';
    END IF;
END $$;

-- Final optimization: analyze tables for better query planning (with existence checks)
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'companies') THEN
        ANALYZE companies;
    END IF;

    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'labs') THEN
        ANALYZE labs;
    END IF;

    -- Optional: Analyze lab_events table if it exists
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'lab_events') THEN
        ANALYZE lab_events;
    END IF;
END $$;

-- Migration complete!
--
-- Note: This migration script is fully idempotent and can be run multiple times safely.
-- All creation and deletion operations include proper existence checks.
--
-- To enable event tracking:
-- 1. Uncomment the lab_events table creation section above
-- 2. Uncomment the lab_events index creation section above
-- 3. Uncomment the lab_events drop statements in the cleanup section
-- 4. Run the migration again
--
-- The application code already includes error-handling for missing lab_events table,
-- so event tracking will work automatically once the table is created.