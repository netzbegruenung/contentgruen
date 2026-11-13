-- Vormoderation fuer unbeantwortete Suchanfragen (Entscheidung des Maintainers vom
-- 13.11.2026, juristische Vorpruefung P6)
--
-- suchanfrage_freigaben: je Aussage aus einer Suchanfrage, die ein Admin geprueft
-- hat, ob er sie fuer alle freigegeben (freigegeben = true) oder abgelehnt hat, und
-- wann. Eine unbeantwortete Suchanfrage sehen Nicht-Admins nur noch, wenn sie ueber
-- der Schwelle der Kennzahl "Suchen ohne Treffer" liegt und freigegeben ist
-- (mvp/backend/semantic-search-service/app/services/suchen_ohne_treffer_service.py).
-- Kein Text, keine Kennung des Admins.
--
-- Neue Datenbanken brauchen dieses Skript nicht: create_all legt die Tabelle beim
-- Start an, auch in bestehenden Datenbanken, vor dem Einspielen der Migrationen.
--
-- Vorhandene Daten: Was beim Einspielen schon fuer alle sichtbar war, bleibt es.
-- Jede Aussage, nach der in der laufenden und den drei Wochen davor (UTC) mindestens
-- zwei Personen ohne Treffer gesucht haben, gilt als freigegeben; dieselbe Schwelle
-- wie MINDESTANZAHL und WOCHEN_STANDARD im Dienst. Darunter sind auch Aussagen, die
-- nicht aus einer Suchanfrage stammen; fuer sie hat die Zeile keine Wirkung. Der
-- Nachtrag laeuft nur auf einer leeren Tabelle, ein zweiter Lauf gibt also nichts
-- frei, was inzwischen ueber die Schwelle gekommen ist.
--
-- Anwenden: siehe README.md in diesem Verzeichnis.

BEGIN;

CREATE TABLE IF NOT EXISTS suchanfrage_freigaben (
    statement_id UUID NOT NULL,
    freigegeben BOOLEAN NOT NULL,
    entschieden_am TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    PRIMARY KEY (statement_id)
);

INSERT INTO suchanfrage_freigaben (statement_id, freigegeben)
SELECT statement_id, true
FROM suchen_ohne_treffer
WHERE woche >= (date_trunc('week', now() AT TIME ZONE 'UTC'))::date - 21
  AND NOT EXISTS (SELECT 1 FROM suchanfrage_freigaben)
GROUP BY statement_id
HAVING sum(personen) >= 2
ON CONFLICT (statement_id) DO NOTHING;

COMMIT;
