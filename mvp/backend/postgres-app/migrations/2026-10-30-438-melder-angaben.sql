-- Angaben nach Art. 16 Abs. 2 DSA an einer Meldung (#438)
--
-- Der Meldedialog fragt jetzt freiwillig Name und E-Mail-Adresse der meldenden
-- Person ab und verlangt die Erklaerung, in gutem Glauben zu melden. Die drei
-- Angaben stehen an der Meldung in content_reports; nur Admins sehen sie, und sie
-- gehen mit der Meldung nach deren Loeschfrist (docs/LOESCHKONZEPT.md).
--
-- Neue Datenbanken brauchen dieses Skript nicht: create_all legt die Tabelle mit
-- den Spalten an. Bestehende brauchen es, weil create_all keine Spalten ergaenzt.
--
-- Vorhandene Meldungen behalten NULL: Sie wurden ohne diese Angaben abgegeben.
--
-- Anwenden: siehe README.md in diesem Verzeichnis.

BEGIN;

ALTER TABLE content_reports ADD COLUMN IF NOT EXISTS melder_name VARCHAR(200);
ALTER TABLE content_reports ADD COLUMN IF NOT EXISTS melder_email VARCHAR(254);
ALTER TABLE content_reports ADD COLUMN IF NOT EXISTS guter_glaube BOOLEAN;

COMMIT;
