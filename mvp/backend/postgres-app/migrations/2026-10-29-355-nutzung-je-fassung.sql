-- Nutzung je Fassung eines Kommentars (#355)
--
-- Ein Kommentar hat eine Mittelfassung und optional eine Kurz- und eine
-- Langfassung; kopiert und gezaehlt wird je Fassung. Zwei Aenderungen:
--
--   usage_events.fassung  welche Fassung kopiert wurde ("kurz", "mittel",
--                         "lang"), fuer den Zuwachs der letzten 7 Tage je
--                         Fassung in "Meine Beitraege". Leer bei anderen
--                         Beitragstypen.
--   nutzung_je_fassung    die Summe je Beitrag und Fassung. Ein eigener Zaehler
--                         wie usage_tracking, weil die usage_events nach ihrer
--                         Frist geloescht werden.
--
-- Neue Datenbanken brauchen das Skript nicht: create_all legt die neue Tabelle
-- an, init.sql hat die Spalte. Bestehende Datenbanken brauchen es fuer die
-- Spalte, create_all ergaenzt keine Spalten.
--
-- Nachtragen: nichts. Nutzung von vor #355 hat keine Fassung; welche Fassung
-- damals kopiert wurde, ist nicht bekannt und wird nicht geschaetzt.
--
-- Anwenden: siehe README.md in diesem Verzeichnis.

BEGIN;

ALTER TABLE usage_events ADD COLUMN IF NOT EXISTS fassung VARCHAR(10);

CREATE TABLE IF NOT EXISTS nutzung_je_fassung (
    content_id UUID NOT NULL,
    fassung VARCHAR(10) NOT NULL,
    nutzung INTEGER NOT NULL,
    PRIMARY KEY (content_id, fassung),
    FOREIGN KEY (content_id) REFERENCES usage_tracking(content_id) ON DELETE CASCADE
);

COMMIT;
