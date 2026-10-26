-- Initialize Gut gesagt Application Database
-- This database stores application-specific data separate from the Qdrant vector database

-- The application user and database are created by the postgres entrypoint from
-- POSTGRES_USER / POSTGRES_PASSWORD / POSTGRES_DB. Do not create the role here: a
-- hardcoded password would become the live credential in any environment that does
-- not set POSTGRES_USER.

-- Das Schema hier muss genau dem entsprechen, was create_all aus den Modellen
-- (app/infrastructure/database/models.py) anlegt: Spalten, Defaults, Indizes,
-- keine Trigger. tests/integration/test_migrationen.py prueft das. Bis #285 wich
-- es ab; Bestandsdatenbanken gleicht migrations/2026-10-27-init-angleichen.sql an.

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
--
-- Bewusst ohne user_id, ip_hash und user_agent: keine der drei Spalten wurde je
-- von einer Abfrage gelesen. user_id blieb ueberdies leer, weil das BFF den
-- Header X-User setzt und die Dependency X-User-Id las. An die Stelle des
-- User-Agent-Rohwerts tritt device_category mit "mobile", "tablet", "desktop"
-- oder "unknown" (app/utils/device_category.py). Bestandsdatenbanken migriert
-- migrations/2026-08-25-usage-events-datensparsamkeit.sql.
CREATE TABLE IF NOT EXISTS usage_events (
    id BIGSERIAL PRIMARY KEY,
    content_id UUID NOT NULL,
    event_type VARCHAR(50) DEFAULT 'copy' NOT NULL,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    session_id VARCHAR(255),
    device_category VARCHAR(20),
    FOREIGN KEY (content_id) REFERENCES usage_tracking(content_id) ON DELETE CASCADE
);

-- Die frueher hier definierte View user_usage_statistics ist entfallen: sie
-- gruppierte nach usage_events.user_id. Kein Anwendungscode hat sie je benutzt
-- (die Nutzungsstatistik in /api/v1/usage/users/me/usage-stats kommt aus Qdrant
-- und usage_tracking, siehe repositories/usage_tracking_repository.py).

-- Create indexes for performance
CREATE INDEX idx_usage_events_content_id ON usage_events(content_id);
CREATE INDEX idx_usage_events_timestamp ON usage_events(timestamp);

-- Kein Trigger fuer updated_at: Das setzt das Modell (onupdate), alle Schreibwege
-- laufen ueber das ORM.

-- Grant appropriate permissions
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO app_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO app_user;
GRANT ALL PRIVILEGES ON ALL FUNCTIONS IN SCHEMA public TO app_user;
