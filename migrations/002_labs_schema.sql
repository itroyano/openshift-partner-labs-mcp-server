-- Migration: Labs Schema for OpenShift Partner Labs MCP Server
-- Version: 002
-- Description: Replace cluster-focused schema with lab-focused schema for partner lab management

-- Drop old tables (in reverse dependency order)
DROP TABLE IF EXISTS cluster_events CASCADE;
DROP TABLE IF EXISTS clusters CASCADE;
DROP TABLE IF EXISTS users CASCADE;

-- Drop old views and functions
DROP VIEW IF EXISTS active_clusters CASCADE;
DROP VIEW IF EXISTS cluster_stats CASCADE;
DROP TRIGGER IF EXISTS update_users_updated_at ON users;
DROP TRIGGER IF EXISTS update_clusters_updated_at ON clusters;
DROP FUNCTION IF EXISTS update_updated_at_column CASCADE;

-- Create companies table
CREATE TABLE IF NOT EXISTS companies (
    id SERIAL PRIMARY KEY,
    company_name VARCHAR(64) NOT NULL UNIQUE,
    curated BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create labs table (main table based on MySQL schema)
CREATE TABLE IF NOT EXISTS labs (
    id SERIAL PRIMARY KEY,
    cluster_id CHAR(36) NOT NULL UNIQUE,
    generated_name VARCHAR(32) NOT NULL UNIQUE,
    state VARCHAR(12) NOT NULL DEFAULT 'pending',
    cluster_name VARCHAR(32) NOT NULL,
    openshift_version VARCHAR(16) NOT NULL,
    cluster_size VARCHAR(7) NOT NULL,
    company_id INTEGER REFERENCES companies(id) ON DELETE SET NULL,
    request_type VARCHAR(12) NOT NULL,
    partner BOOLEAN NOT NULL DEFAULT FALSE,
    sponsor VARCHAR(64) NOT NULL,
    cloud_provider VARCHAR(8) NOT NULL,
    primary_first VARCHAR(32) NOT NULL,
    primary_last VARCHAR(32) NOT NULL,
    primary_email VARCHAR(64) NOT NULL,
    secondary_first VARCHAR(32) NOT NULL,
    secondary_last VARCHAR(32) NOT NULL,
    secondary_email VARCHAR(64) NOT NULL,
    region VARCHAR(5) NOT NULL,
    always_on BOOLEAN NOT NULL DEFAULT FALSE,
    project_name VARCHAR(32) NOT NULL,
    lease_time VARCHAR(2) NOT NULL,
    description TEXT NOT NULL,
    notes TEXT NOT NULL,
    start_date TIMESTAMP WITH TIME ZONE NOT NULL,
    end_date TIMESTAMP WITH TIME ZONE NOT NULL,
    hold BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create lab_events table for audit trail
CREATE TABLE IF NOT EXISTS lab_events (
    id SERIAL PRIMARY KEY,
    lab_id INTEGER NOT NULL REFERENCES labs(id) ON DELETE CASCADE,
    event_type VARCHAR(100) NOT NULL,
    description TEXT,
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for performance

-- Companies indexes
CREATE INDEX IF NOT EXISTS idx_companies_name ON companies(company_name);
CREATE INDEX IF NOT EXISTS idx_companies_curated ON companies(curated);
CREATE INDEX IF NOT EXISTS idx_companies_created_at ON companies(created_at);

-- Labs indexes
CREATE INDEX IF NOT EXISTS idx_labs_cluster_id ON labs(cluster_id);
CREATE INDEX IF NOT EXISTS idx_labs_generated_name ON labs(generated_name);
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
CREATE INDEX IF NOT EXISTS idx_labs_always_on ON labs(always_on) WHERE always_on = true;
CREATE INDEX IF NOT EXISTS idx_labs_hold ON labs(hold) WHERE hold = true;

-- Lab events indexes
CREATE INDEX IF NOT EXISTS idx_lab_events_lab_id ON lab_events(lab_id);
CREATE INDEX IF NOT EXISTS idx_lab_events_event_type ON lab_events(event_type);
CREATE INDEX IF NOT EXISTS idx_lab_events_created_at ON lab_events(created_at);
CREATE INDEX IF NOT EXISTS idx_lab_events_metadata ON lab_events USING GIN(metadata) WHERE metadata IS NOT NULL;

-- Create function to automatically update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create triggers to automatically update updated_at
DROP TRIGGER IF EXISTS update_companies_updated_at ON companies;
CREATE TRIGGER update_companies_updated_at
    BEFORE UPDATE ON companies
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_labs_updated_at ON labs;
CREATE TRIGGER update_labs_updated_at
    BEFORE UPDATE ON labs
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Create useful views for reporting and monitoring

-- Active labs view (not completed or denied)
CREATE OR REPLACE VIEW active_labs AS
SELECT
    l.*,
    c.company_name,
    c.curated as company_curated
FROM labs l
LEFT JOIN companies c ON l.company_id = c.id
WHERE l.state IN ('pending', 'approved', 'active', 'extended');

-- Lab summary statistics
CREATE OR REPLACE VIEW lab_stats AS
SELECT
    COUNT(*) as total_labs,
    COUNT(CASE WHEN state = 'pending' THEN 1 END) as pending_labs,
    COUNT(CASE WHEN state = 'approved' THEN 1 END) as approved_labs,
    COUNT(CASE WHEN state = 'active' THEN 1 END) as active_labs,
    COUNT(CASE WHEN state = 'extended' THEN 1 END) as extended_labs,
    COUNT(CASE WHEN state = 'completed' THEN 1 END) as completed_labs,
    COUNT(CASE WHEN state = 'denied' THEN 1 END) as denied_labs,
    COUNT(CASE WHEN partner = true THEN 1 END) as partner_labs,
    COUNT(CASE WHEN always_on = true THEN 1 END) as always_on_labs,
    COUNT(CASE WHEN hold = true THEN 1 END) as on_hold_labs
FROM labs;

-- Labs by cloud provider
CREATE OR REPLACE VIEW lab_stats_by_provider AS
SELECT
    cloud_provider,
    COUNT(*) as total_labs,
    COUNT(CASE WHEN state = 'active' THEN 1 END) as active_labs,
    COUNT(CASE WHEN partner = true THEN 1 END) as partner_labs
FROM labs
GROUP BY cloud_provider
ORDER BY total_labs DESC;

-- Labs by request type
CREATE OR REPLACE VIEW lab_stats_by_request_type AS
SELECT
    request_type,
    COUNT(*) as total_labs,
    COUNT(CASE WHEN state = 'active' THEN 1 END) as active_labs,
    COUNT(CASE WHEN partner = true THEN 1 END) as partner_labs
FROM labs
GROUP BY request_type
ORDER BY total_labs DESC;

-- Labs by region
CREATE OR REPLACE VIEW lab_stats_by_region AS
SELECT
    region,
    COUNT(*) as total_labs,
    COUNT(CASE WHEN state = 'active' THEN 1 END) as active_labs
FROM labs
GROUP BY region
ORDER BY total_labs DESC;

-- Expiring labs (end date within 7 days)
CREATE OR REPLACE VIEW expiring_labs AS
SELECT
    l.*,
    c.company_name,
    (l.end_date - NOW()) as time_remaining
FROM labs l
LEFT JOIN companies c ON l.company_id = c.id
WHERE l.state IN ('active', 'extended')
  AND l.end_date <= NOW() + INTERVAL '7 days'
  AND l.end_date > NOW()
ORDER BY l.end_date;

-- Overdue labs (past end date but still active)
CREATE OR REPLACE VIEW overdue_labs AS
SELECT
    l.*,
    c.company_name,
    (NOW() - l.end_date) as overdue_duration
FROM labs l
LEFT JOIN companies c ON l.company_id = c.id
WHERE l.state IN ('active', 'extended')
  AND l.end_date < NOW()
ORDER BY l.end_date;

-- Insert sample data from the MySQL dump (matching the company structure)
-- First, insert companies
INSERT INTO companies (id, company_name, curated, created_at, updated_at) VALUES
(1, 'Myovant Sciences Ltd.', false, '2024-07-16 05:45:10', '2024-07-16 22:19:50'),
(2, 'Archrock, Inc.', false, '2024-07-16 05:47:04', '2024-07-24 18:15:50'),
(3, 'American Equity Investment Life Holding Company', false, '2024-07-16 05:55:18', '2024-07-22 22:52:46'),
(4, 'First Trust MLP and Energy Income Fund', false, '2024-07-16 05:58:10', '2024-07-17 09:46:14'),
(5, 'Monogram Residential Trust, Inc.', false, '2024-07-16 06:02:23', '2024-07-25 18:06:54'),
(6, 'Cellectar Biosciences, Inc.', false, '2024-07-16 06:09:44', '2024-07-18 00:46:16'),
(7, 'Eagle Materials Inc', true, '2024-07-16 06:12:59', '2024-07-24 14:20:17'),
(8, 'UCP, Inc.', false, '2024-07-16 06:21:45', '2024-07-17 03:20:59'),
(9, 'Hologic, Inc.', true, '2024-07-16 06:26:03', '2024-07-23 20:35:47'),
(10, 'Eastern Company (The)', true, '2024-07-16 06:30:18', '2024-07-17 09:19:32')
ON CONFLICT (id) DO NOTHING;

-- Update sequence for companies
SELECT setval('companies_id_seq', (SELECT MAX(id) FROM companies));

-- Grant permissions (adjust as needed for your environment)
-- These are example permissions - modify based on your security requirements
GRANT SELECT, INSERT, UPDATE, DELETE ON companies TO openshift_partner_labs_mcp_server;
GRANT SELECT, INSERT, UPDATE, DELETE ON labs TO openshift_partner_labs_mcp_server;
GRANT SELECT, INSERT, UPDATE, DELETE ON lab_events TO openshift_partner_labs_mcp_server;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO openshift_partner_labs_mcp_server;
GRANT SELECT ON active_labs TO openshift_partner_labs_mcp_server;
GRANT SELECT ON lab_stats TO openshift_partner_labs_mcp_server;
GRANT SELECT ON lab_stats_by_provider TO openshift_partner_labs_mcp_server;
GRANT SELECT ON lab_stats_by_request_type TO openshift_partner_labs_mcp_server;
GRANT SELECT ON lab_stats_by_region TO openshift_partner_labs_mcp_server;
GRANT SELECT ON expiring_labs TO openshift_partner_labs_mcp_server;
GRANT SELECT ON overdue_labs TO openshift_partner_labs_mcp_server;

-- Add check constraints for data integrity
ALTER TABLE labs ADD CONSTRAINT chk_labs_state
    CHECK (state IN ('pending', 'approved', 'active', 'extended', 'completed', 'denied'));

ALTER TABLE labs ADD CONSTRAINT chk_labs_request_type
    CHECK (request_type IN ('general', 'engineering', 'rosa', 'rhoai', 'nvidia', 'ocpv'));

ALTER TABLE labs ADD CONSTRAINT chk_labs_cluster_size
    CHECK (cluster_size IN ('small', 'medium', 'large', 'xlarge', 'custom'));

ALTER TABLE labs ADD CONSTRAINT chk_labs_cloud_provider
    CHECK (cloud_provider IN ('AWS', 'Azure', 'Google', 'IBM', 'Oracle', 'Alibaba', 'Linode', 'Vultr', 'DigitalO'));

ALTER TABLE labs ADD CONSTRAINT chk_labs_region
    CHECK (region IN ('na1', 'na2', 'emea', 'apac1', 'apac2', 'latam'));

ALTER TABLE labs ADD CONSTRAINT chk_labs_lease_time
    CHECK (lease_time IN ('1d', '1w', '1m', '2w', '2d'));

ALTER TABLE labs ADD CONSTRAINT chk_labs_dates
    CHECK (end_date > start_date);

-- Add comments for documentation
COMMENT ON TABLE companies IS 'Partner companies that can request labs';
COMMENT ON TABLE labs IS 'OpenShift Partner Labs with full lifecycle management';
COMMENT ON TABLE lab_events IS 'Audit trail for all lab operations and state changes';

COMMENT ON COLUMN labs.cluster_id IS 'UUID identifier for the cluster';
COMMENT ON COLUMN labs.generated_name IS 'Human-friendly name for the lab (unique)';
COMMENT ON COLUMN labs.state IS 'Current state of the lab (pending, approved, active, extended, completed, denied)';
COMMENT ON COLUMN labs.request_type IS 'Type of lab request (general, engineering, rosa, rhoai, nvidia, ocpv)';
COMMENT ON COLUMN labs.partner IS 'Whether this is a partner lab';
COMMENT ON COLUMN labs.always_on IS 'Whether the cluster should remain always running';
COMMENT ON COLUMN labs.hold IS 'Whether the lab is on hold';
COMMENT ON COLUMN labs.lease_time IS 'Duration of the lab lease (1d, 1w, 1m, 2w, 2d)';

-- Final optimization: analyze tables for better query planning
ANALYZE companies;
ANALYZE labs;
ANALYZE lab_events;