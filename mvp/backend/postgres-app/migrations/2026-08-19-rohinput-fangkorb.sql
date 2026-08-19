-- Fangkorb: Rohinput als eigene Entitaet
--
-- Rohinput ist bewusst kein ContentType in Qdrant, sondern ein Arbeitsvorrat
-- daneben (Begruendung: docs/ROHINPUT.md, Variante C). Er wird nie gesucht,
-- kopiert oder bewertet, aber sein Zustand aendert sich - und eine spaetere
-- Zuweisung ist ein Wettlauf zweier Nutzer um dieselbe Zeile, den nur eine
-- Transaktion entscheidet.
--
-- raw_input_content_links bleibt zunaechst leer: die Verarbeitung ist nicht
-- gebaut. Die Tabelle entsteht trotzdem jetzt, weil die Beziehung n:m ist und
-- ein spaeter nachgeruesteter Fremdschluessel auf einer gefuellten Tabelle
-- teuer waere.
--
-- Neue Datenbanken brauchen dieses Skript nicht: die Tabellen werden beim Start
-- von SQLAlchemy angelegt (infrastructure/database/connection.py:48) und haben
-- dann direkt dieses Schema. Nur bereits laufende Umgebungen migrieren.
--
-- Anwenden:
--   docker exec -i contentgruen-app-postgres psql -U app_user -d contentgruen_app \
--     < mvp/backend/postgres-app/migrations/2026-08-19-rohinput-fangkorb.sql

BEGIN;

-- gen_random_uuid() steckt seit PostgreSQL 13 in der Standardinstallation;
-- aeltere Staende brauchen pgcrypto. content_reports verwendet dieselbe Vorgabe.
CREATE TABLE IF NOT EXISTS raw_inputs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    content TEXT,
    url TEXT,
    image_url TEXT,
    -- Nullable: der geplante Instagram-Share-Eingang kommt ohne Sitzung an.
    submitted_by VARCHAR(255),
    source_channel VARCHAR(50) NOT NULL DEFAULT 'web',
    status VARCHAR(20) NOT NULL DEFAULT 'open',
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    -- Ein leerer Einwurf ist kein Einwurf. Die einzige inhaltliche Pflicht.
    CONSTRAINT check_raw_input_not_empty
        CHECK (content IS NOT NULL OR url IS NOT NULL OR image_url IS NOT NULL)
);

CREATE INDEX IF NOT EXISTS idx_raw_inputs_status ON raw_inputs(status);
CREATE INDEX IF NOT EXISTS idx_raw_inputs_created_at ON raw_inputs(created_at);
CREATE INDEX IF NOT EXISTS idx_raw_inputs_submitted_by ON raw_inputs(submitted_by);

-- content_id zeigt auf einen Qdrant-Punkt und kann deshalb kein Fremdschluessel
-- sein. raw_input_id ist einer - nicht weil Einwuerfe geloescht wuerden, sondern
-- damit ein Loeschen aus Datenschutzgruenden keine Verweise auf Nichts hinterlaesst.
CREATE TABLE IF NOT EXISTS raw_input_content_links (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    raw_input_id UUID NOT NULL REFERENCES raw_inputs(id) ON DELETE CASCADE,
    content_id UUID NOT NULL,
    created_by VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_raw_input_links_raw_input_id
    ON raw_input_content_links(raw_input_id);
CREATE INDEX IF NOT EXISTS idx_raw_input_links_content_id
    ON raw_input_content_links(content_id);
-- Dieselbe Paarung nur einmal - zweimal "verarbeitet" zaehlt spaeter sonst doppelt.
CREATE UNIQUE INDEX IF NOT EXISTS idx_raw_input_links_unique
    ON raw_input_content_links(raw_input_id, content_id);

COMMIT;
