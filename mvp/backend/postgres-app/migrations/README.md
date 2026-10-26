# Migrationen der App-Datenbank (PostgreSQL)

Handgeschriebene SQL-Skripte für **bestehende** Datenbanken. Es gibt kein
Migrationswerkzeug und keine Tabelle, die festhält, was schon gelaufen ist: Wer
deployt, wendet die neuen Skripte selbst an, in der Reihenfolge ihrer
Dateinamen.

## Wann eine Migration nötig ist

Beim Start legt der Semantic-Service fehlende Tabellen selbst an
(`Base.metadata.create_all` in
`mvp/backend/semantic-search-service/app/infrastructure/database/connection.py`),
bei einem leeren Volume zusätzlich `mvp/backend/postgres-app/init.sql`. Neue
Datenbanken haben dadurch sofort das aktuelle Schema.

`create_all` legt aber nur **fehlende Tabellen** an. Es ergänzt keine Spalten,
ändert keine Typen, Indizes oder Constraints und löscht nichts. Für alles davon
braucht eine bestehende Datenbank ein Skript hier, und zwar **bevor** der neue
Dienst startet. Für eine reine neue Tabelle ist ein Skript optional; es
dokumentiert dann das Schema.

## Anwenden

Aus dem Wurzelverzeichnis des Repos, für jedes noch nicht angewendete Skript:

```bash
PG_CONTAINER=gutgesagt-app-postgres PG_DB=gutgesagt_app
docker exec -i "$PG_CONTAINER" psql -U app_user -d "$PG_DB" -v ON_ERROR_STOP=1 \
  < mvp/backend/postgres-app/migrations/<datei>.sql
```

- `-v ON_ERROR_STOP=1` bricht beim ersten Fehler ab (Exit-Code 3). Ohne die
  Option liefe `psql` nach einem Fehler weiter und meldete am Ende Erfolg.
- Die Skripte laufen in einer Transaktion (`BEGIN; … COMMIT;`): Schlägt eines
  fehl, bleibt die Datenbank, wie sie war. Ausnahme ist jeweils das
  `VACUUM FULL` am Ende von `2026-08-19-search-events-pseudonymisieren.sql` und
  `2026-08-25-usage-events-datensparsamkeit.sql`, das in PostgreSQL nicht in
  einer Transaktion laufen darf. Es läuft nach dem `COMMIT`; schlägt es fehl,
  ist die Migration schon festgeschrieben. Dann **nur** das `VACUUM FULL …;`
  einzeln nachholen, nicht das ganze Skript erneut starten (siehe „Erneut
  anwenden“).
- `PG_CONTAINER` und `PG_DB` sind Container und Datenbank der Umgebung. Wo die
  Umbenennung aus #206 noch nicht ausgerollt ist, gelten die alten Namen
  `contentgruen-app-postgres` und `contentgruen_app`.
- Ob eine Umgebung ein Skript braucht und ob es vor dem Start des neuen
  Dienstes laufen muss, steht im Kopf des Skripts.

### Erneut anwenden

Die meisten Skripte dürfen mehrfach laufen. Zwei ältere nicht:

- `2026-08-19-search-events-pseudonymisieren.sql` leert `search_events` bei
  **jedem** Lauf (`TRUNCATE`). Ein zweiter Lauf löscht alle seither erfassten
  Suchereignisse.
- `2026-08-25-usage-events-datensparsamkeit.sql` bricht beim zweiten Lauf ab,
  weil die umbenannte Spalte `user_agent` fehlt. Dank Transaktion bleibt die
  Datenbank dabei unverändert.

## Konvention für neue Migrationen

- **Dateiname:** `JJJJ-MM-TT-<thema>.sql`, Datum der Erstellung, Thema kurz,
  kleingeschrieben, mit Bindestrichen. Das Datum legt die Reihenfolge fest;
  bei gleichem Datum gilt die alphabetische Reihenfolge des Dateinamens.
- **Kopf:** ein SQL-Kommentar, der sagt
  1. was sich ändert und warum,
  2. ob neue Datenbanken das Skript brauchen (meist nicht, siehe oben) und ob es
     vor dem Start des neuen Dienstes laufen muss,
  3. wie vorhandene Daten nachgetragen oder verworfen werden,
  4. als letzte Zeile: `-- Anwenden: siehe README.md in diesem Verzeichnis.`

  Den Befehl selbst nicht in den Kopf kopieren. Er steht nur hier, damit eine
  Umbenennung (Container, Datenbank, Pfad) nur diese Datei ändert.
- **Idempotent:** `IF NOT EXISTS` / `IF EXISTS` und Nachträge, die einen zweiten
  Lauf überstehen. Ein neues Skript darf mehrfach laufen, ohne Daten zu
  verlieren. Geht das nicht, sagt der Kopf es ausdrücklich und hier steht es
  unter „Erneut anwenden“.
- **Transaktion:** `BEGIN;` am Anfang, `COMMIT;` am Ende. Was nicht in einer
  Transaktion laufen darf (etwa `VACUUM`), steht danach und ist im Kopf erklärt.
- **Gleiches Schema wie `create_all`:** Was das Skript anlegt, muss genau dem
  entsprechen, was die SQLAlchemy-Modelle in einer neuen Datenbank erzeugen.
  Ändert sich eine Tabelle, die auch `mvp/backend/postgres-app/init.sql`
  anlegt, dort mitziehen.
- **Angewendete Skripte nicht ändern.** Ein Fehler wird mit einem neuen Skript
  korrigiert. Ausnahme sind reine Kommentaränderungen; das SQL bleibt Zeichen
  für Zeichen gleich.
