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
-- Vorhandene Daten: kein Nachtrag. Auch was beim Einspielen schon ueber der
-- Schwelle lag, sehen Nicht-Admins erst nach Freigabe durch das Moderationsteam.
--
-- Anwenden: siehe README.md in diesem Verzeichnis.

BEGIN;

CREATE TABLE IF NOT EXISTS suchanfrage_freigaben (
    statement_id UUID NOT NULL,
    freigegeben BOOLEAN NOT NULL,
    entschieden_am TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    PRIMARY KEY (statement_id)
);

COMMIT;
