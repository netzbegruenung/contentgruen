-- Anzeigenamen: Vorname und Initial je Kennung ("Anna B.")
--
-- Karten zeigen beim Autor und beim Einwerfer den Anzeigenamen statt der
-- Kennung. Das BFF leitet ihn aus den Claims ab und schickt ihn im Header
-- X-User-Display-Name; der Semantic-Service legt ihn hier ab, sobald er sich
-- aendert. Es ist die einzige Stelle mit einem Namen: Qdrant und raw_inputs
-- tragen weiter nur die Kennung.
--
-- Neue Datenbanken brauchen dieses Skript nicht: die Tabelle wird beim Start
-- von SQLAlchemy angelegt (infrastructure/database/connection.py:48), und
-- create_all legt fehlende Tabellen auch in bestehenden Datenbanken an. Das
-- Skript dokumentiert das Schema und dient Umgebungen, in denen die Tabelle vor
-- dem ersten Start des neuen Dienstes existieren soll.
--
-- Loeschen: docs/LOESCHKONZEPT.md, Schritt 2.
--
-- Anwenden: siehe README.md in diesem Verzeichnis.

BEGIN;

CREATE TABLE IF NOT EXISTS users (
    user_id VARCHAR(255) PRIMARY KEY,
    anzeigename VARCHAR(100) NOT NULL,
    aktualisiert_am TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

COMMIT;
