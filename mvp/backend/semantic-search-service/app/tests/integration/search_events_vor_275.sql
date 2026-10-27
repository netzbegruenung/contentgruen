-- search_events vor #275, wie create_all sie aus dem Modell anlegte: die Kennung
-- aus einer Sequenz, fortlaufend in der Reihenfolge der Suchen.
CREATE TABLE search_events (
    id BIGSERIAL NOT NULL,
    actor_hash VARCHAR(64),
    results_count INTEGER NOT NULL,
    timestamp TIMESTAMP WITH TIME ZONE
        DEFAULT (date_trunc('day', now() AT TIME ZONE 'UTC') AT TIME ZONE 'UTC') NOT NULL,
    PRIMARY KEY (id)
);
CREATE INDEX idx_search_events_actor_hash ON search_events (actor_hash);
CREATE INDEX idx_search_events_timestamp ON search_events (timestamp);
