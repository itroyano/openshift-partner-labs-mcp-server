-- Migration: Create tables for OpenShift Partner Labs MCP Server
-- Version: 001
-- Description: Initial database schema for users, clusters, and cluster events

-- Create users table
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(255) NOT NULL UNIQUE,
    email VARCHAR(255) NOT NULL,
    red_hat_uuid VARCHAR(255) UNIQUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes on users table
CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_red_hat_uuid ON users(red_hat_uuid) WHERE red_hat_uuid IS NOT NULL;

-- Create clusters table
CREATE TABLE IF NOT EXISTS clusters (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL UNIQUE,
    namespace VARCHAR(255) NOT NULL,
    owner_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'pending',
    cluster_type VARCHAR(100),
    provider VARCHAR(100),
    region VARCHAR(100),
    acm_managed_cluster_name VARCHAR(255),
    hibernation_enabled BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    deleted_at TIMESTAMP WITH TIME ZONE NULL
);

-- Create indexes on clusters table
CREATE INDEX IF NOT EXISTS idx_clusters_name ON clusters(name);
CREATE INDEX IF NOT EXISTS idx_clusters_owner_id ON clusters(owner_id);
CREATE INDEX IF NOT EXISTS idx_clusters_status ON clusters(status);
CREATE INDEX IF NOT EXISTS idx_clusters_provider ON clusters(provider);
CREATE INDEX IF NOT EXISTS idx_clusters_created_at ON clusters(created_at);
CREATE INDEX IF NOT EXISTS idx_clusters_deleted_at ON clusters(deleted_at) WHERE deleted_at IS NOT NULL;

-- Create cluster_events table
CREATE TABLE IF NOT EXISTS cluster_events (
    id SERIAL PRIMARY KEY,
    cluster_id INTEGER NOT NULL REFERENCES clusters(id) ON DELETE CASCADE,
    event_type VARCHAR(100) NOT NULL,
    description TEXT,
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes on cluster_events table
CREATE INDEX IF NOT EXISTS idx_cluster_events_cluster_id ON cluster_events(cluster_id);
CREATE INDEX IF NOT EXISTS idx_cluster_events_event_type ON cluster_events(event_type);
CREATE INDEX IF NOT EXISTS idx_cluster_events_created_at ON cluster_events(created_at);
CREATE INDEX IF NOT EXISTS idx_cluster_events_metadata ON cluster_events USING GIN(metadata) WHERE metadata IS NOT NULL;

-- Create function to automatically update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create triggers to automatically update updated_at
DROP TRIGGER IF EXISTS update_users_updated_at ON users;
CREATE TRIGGER update_users_updated_at 
    BEFORE UPDATE ON users 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_clusters_updated_at ON clusters;
CREATE TRIGGER update_clusters_updated_at 
    BEFORE UPDATE ON clusters 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

-- Insert some default data for testing (optional)
INSERT INTO users (username, email, red_hat_uuid) VALUES 
    ('admin', 'admin@example.com', 'admin-uuid-123')
ON CONFLICT (username) DO NOTHING;

-- Create a view for active clusters (not deleted)
CREATE OR REPLACE VIEW active_clusters AS
SELECT 
    c.*,
    u.username as owner_username,
    u.email as owner_email
FROM clusters c
LEFT JOIN users u ON c.owner_id = u.id
WHERE c.deleted_at IS NULL;

-- Create a view for cluster summary statistics
CREATE OR REPLACE VIEW cluster_stats AS
SELECT 
    COUNT(*) as total_clusters,
    COUNT(CASE WHEN status = 'ready' THEN 1 END) as ready_clusters,
    COUNT(CASE WHEN status = 'hibernated' THEN 1 END) as hibernated_clusters,
    COUNT(CASE WHEN status = 'creating' THEN 1 END) as creating_clusters,
    COUNT(CASE WHEN status = 'error' THEN 1 END) as error_clusters,
    COUNT(CASE WHEN hibernation_enabled = true THEN 1 END) as hibernation_enabled_clusters,
    provider,
    COUNT(*) as clusters_per_provider
FROM active_clusters
GROUP BY provider;

-- Grant permissions (adjust as needed for your environment)
-- These are example permissions - modify based on your security requirements
GRANT SELECT, INSERT, UPDATE, DELETE ON users TO openshift_partner_labs_mcp_server;
GRANT SELECT, INSERT, UPDATE, DELETE ON clusters TO openshift_partner_labs_mcp_server;
GRANT SELECT, INSERT, UPDATE, DELETE ON cluster_events TO openshift_partner_labs_mcp_server;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO openshift_partner_labs_mcp_server;
GRANT SELECT ON active_clusters TO openshift_partner_labs_mcp_server;
GRANT SELECT ON cluster_stats TO openshift_partner_labs_mcp_server;