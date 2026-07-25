-- Initialize ContentGrün Application Database
-- This database stores application-specific data separate from the Qdrant vector database

-- The application user and database are created by the postgres entrypoint from
-- POSTGRES_USER / POSTGRES_PASSWORD / POSTGRES_DB. Do not create the role here: a
-- hardcoded password would become the live credential in any environment that does
-- not set POSTGRES_USER.

-- Create usage tracking table
CREATE TABLE IF NOT EXISTS usage_tracking (
    content_id UUID PRIMARY KEY,
    usage_count INTEGER DEFAULT 0 NOT NULL,
    last_used TIMESTAMP WITH TIME ZONE,
    first_used TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL
);

-- Create usage events table for detailed tracking
CREATE TABLE IF NOT EXISTS usage_events (
    id SERIAL PRIMARY KEY,
    content_id UUID NOT NULL,
    user_id VARCHAR(255),
    event_type VARCHAR(50) DEFAULT 'copy' NOT NULL,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    session_id VARCHAR(255),
    ip_hash VARCHAR(64), -- Store hashed IP for analytics without privacy concerns
    user_agent VARCHAR(500),
    FOREIGN KEY (content_id) REFERENCES usage_tracking(content_id) ON DELETE CASCADE
);

-- Create user statistics view
CREATE OR REPLACE VIEW user_usage_statistics AS
SELECT
    ut.user_id,
    COUNT(DISTINCT ut.content_id) as unique_contents_contributed,
    SUM(t.usage_count) as total_usage_count,
    MAX(t.last_used) as last_content_used,
    MIN(t.first_used) as first_content_used
FROM usage_tracking t
JOIN (
    SELECT DISTINCT content_id, user_id
    FROM usage_events
    WHERE user_id IS NOT NULL
) ut ON t.content_id = ut.content_id
GROUP BY ut.user_id;

-- Create indexes for performance
CREATE INDEX idx_usage_events_content_id ON usage_events(content_id);
CREATE INDEX idx_usage_events_user_id ON usage_events(user_id);
CREATE INDEX idx_usage_events_timestamp ON usage_events(timestamp DESC);
CREATE INDEX idx_usage_events_content_timestamp ON usage_events(content_id, timestamp DESC); -- Composite index for time-based queries
CREATE INDEX idx_usage_tracking_usage_count ON usage_tracking(usage_count DESC);
CREATE INDEX idx_usage_tracking_last_used ON usage_tracking(last_used DESC);

-- Create function to update the updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create trigger to automatically update updated_at
CREATE TRIGGER update_usage_tracking_updated_at
    BEFORE UPDATE ON usage_tracking
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Grant appropriate permissions
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO app_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO app_user;
GRANT ALL PRIVILEGES ON ALL FUNCTIONS IN SCHEMA public TO app_user;
