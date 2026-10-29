# Migrationen der App-Datenbank (PostgreSQL)

Handgeschriebene SQL-Skripte für **bestehende** Datenbanken. Der
Semantic-Service spielt sie beim Start selbst ein, in der Reihenfolge ihrer
Dateinamen ohne `.sql` (siehe „Konvention für neue Migrationen“, Dateiname), und
hält in der Tabelle `migrationsprotokoll` fest, was gelaufen ist. Die Skripte
liegen dafür im Image des Dienstes unter `/migrations`. Wer deployt, muss nichts
von Hand einspielen.

## Wann eine Migration nötig ist

Beim Start legt der Semantic-Service fehlende Tabellen selbst an
(`Base.metadata.create_all` in
`mvp/backend/semantic-search-service/app/infrastructure/database/connection.py`),
bei einem leeren Volume zusätzlich `mvp/backend/postgres-app/init.sql`. Neue
Datenbanken haben dadurch sofort das aktuelle Schema.

`create_all` legt aber nur **fehlende Tabellen** an. Es ergänzt keine Spalten,
ändert keine Typen, Indizes oder Constraints und löscht nichts. Für alles davon
braucht eine bestehende Datenbank ein Skript hier, und zwar **bevor** der neue
Dienst Anfragen annimmt; das stellt das Einspielen beim Start sicher. Für eine
reine neue Tabelle ist ein Skript optional; es dokumentiert dann das Schema.

## Einspielen

Beim Start, nach `create_all` und bevor er Anfragen annimmt, spielt der
Semantic-Service jedes Skript ein, das noch nicht im Protokoll steht
(`mvp/backend/semantic-search-service/app/infrastructure/database/migrationen.py`).
Ein neues Skript läuft ohne Codeänderung mit: Datei hier ablegen, das nächste
Image enthält sie.

- **Transaktion:** Jedes Skript läuft bis zu seinem `COMMIT` in einer
  Transaktion, der Eintrag im Protokoll wird in derselben Transaktion
  geschrieben. Skript und Eintrag gelten zusammen oder gar nicht.
- **Sperren:** Jedes Skript wartet höchstens 30 s auf eine Sperre, ein Skript
  mit eigenem `SET LOCAL lock_timeout` so lange, wie es dort steht
  (`2026-10-26-init-angleichen.sql`: 5 s).
- **Fehler:** Schlägt ein Skript fehl, etwa weil es eine Sperre nicht bekommt,
  rollt es zurück und steht als
  `fehlgeschlagen` im Protokoll, mit der ersten Zeile der Fehlermeldung. Der
  Dienst startet dann nicht, spätere Skripte laufen nicht. Mit einer
  Restart-Policy (im Dev-Stack `restart: unless-stopped`) startet Docker den
  Dienst neu, und der nächste Start versucht das Skript erneut. Was
  schiefging, steht im Log des Dienstes.
- **Nach dem `COMMIT`:** Das `VACUUM FULL` am Ende von
  `2026-08-19-search-events-pseudonymisieren.sql`,
  `2026-08-25-usage-events-datensparsamkeit.sql` und
  `2026-10-26-search-events-nur-tag.sql` darf in PostgreSQL nicht in einer
  Transaktion laufen und läuft danach einzeln, ebenfalls mit höchstens 30 s
  Warten auf die Sperre. Scheitert es, ist die Migration schon festgeschrieben und steht als `nachlauf_offen` im Protokoll; der Dienst
  startet trotzdem, denn das Schema stimmt. Der nächste Start holt nur das
  `VACUUM FULL` nach, nicht das ganze Skript.
- **Von Hand eingespielt:** Die wiederholbaren Skripte laufen einfach noch
  einmal und landen dann im Protokoll. Die drei nicht wiederholbaren (siehe
  „Erneut anwenden“) erkennt der Dienst an ihrer Wirkung und vermerkt sie als
  `erkannt`, ohne sie zu starten. Beim ersten Start mit diesem Ablauf auf einer
  Bestandsdatenbank laufen deshalb alle übrigen Skripte einmal erneut; das
  dauert Sekunden und sperrt kurz die Tabellen, die sie ändern.
- **Gleichzeitige Starts:** Eine Advisory-Sperre lässt einen zweiten Dienst
  warten, bis der erste fertig ist, höchstens 10 Minuten.
- **Image:** Die Skripte stecken im Image des Semantic-Service. Ein neues
  Skript kommt erst mit einem neu gebauten Image an; ändert ein PR sonst nichts
  am Dienst, baut die CI nach dem Merge kein neues `:main`-Image (Pfadfilter in
  `.github/workflows/build.yml`).

Den Stand zeigt das Protokoll:

```sql
SELECT name, status, zeitpunkt, fehler FROM migrationsprotokoll ORDER BY name;
```

Nach dem Einspielen einer Sicherung (`mvp/scripts/backup/restore.sh`) steht im
Protokoll der Stand der Sicherung. `restore.sh` startet den Semantic-Service
danach neu, und er spielt die seither hinzugekommenen Skripte ein. Wer anders
zurückspielt, startet den Dienst selbst neu.

### Von Hand einspielen

Nur nötig, wenn ein Skript laufen soll, ohne den Dienst neu zu starten. Aus dem
Wurzelverzeichnis des Repos:

```bash
PG_CONTAINER=gutgesagt-app-postgres PG_DB=gutgesagt_app
docker exec -i "$PG_CONTAINER" psql -U app_user -d "$PG_DB" -v ON_ERROR_STOP=1 \
  < mvp/backend/postgres-app/migrations/<datei>.sql
```

- `-v ON_ERROR_STOP=1` bricht beim ersten Fehler ab (Exit-Code 3). Ohne die
  Option liefe `psql` nach einem Fehler weiter und meldete am Ende Erfolg.
- Schlägt das `VACUUM FULL` nach dem `COMMIT` fehl, **nur** das
  `VACUUM FULL …;` einzeln nachholen, nicht das ganze Skript erneut starten.
- Container und Datenbank heißen in Entwicklung, Test und Produktion gleich.
  Wer sie abweichend betreibt, ändert die Zuweisung von `PG_CONTAINER` und
  `PG_DB` in der ersten Zeile; vorher exportierte Werte überschreibt sie.
- Ins Protokoll schreibt `psql` nichts. Beim nächsten Start läuft das Skript
  deshalb noch einmal, außer es ist eines der drei nicht wiederholbaren.

### Erneut anwenden

Die meisten Skripte dürfen mehrfach laufen. Drei ältere nicht; für sie steht in
`NICHT_WIEDERHOLBAR` (`migrationen.py`), woran der Dienst erkennt, dass sie
schon eingespielt sind:

- `2026-08-19-search-events-pseudonymisieren.sql` leert `search_events` bei
  **jedem** Lauf (`TRUNCATE`). Ein zweiter Lauf löscht alle seither erfassten
  Suchereignisse. Eingespielt ist es, wenn `search_events` die Spalte
  `actor_hash` hat.
- `2026-08-25-usage-events-datensparsamkeit.sql` bricht beim zweiten Lauf ab,
  weil die umbenannte Spalte `user_agent` fehlt. Dank Transaktion bleibt die
  Datenbank dabei unverändert. Eingespielt ist es, wenn `usage_events` keine
  Spalte `user_agent` mehr hat.
- `2026-09-13-fangkorb-v2.sql` übersteht einen zweiten Lauf ohne Fehler, sein
  Nachtrag am Ende ändert dann aber Daten: Ein Beitrag, der ohne Satz
  ausformuliert wurde (`draft_id` leer), hinge danach an einem später
  geschriebenen Satz derselben Person. Eingespielt ist es, wenn
  `raw_input_content_links` die Spalte `draft_id` hat.

## Konvention für neue Migrationen

Der Unit-Test
`mvp/backend/semantic-search-service/app/tests/unit/test_migrationskonvention.py`
prüft für jede Datei hier den Dateinamen, die letzte Kopfzeile, dass kein
Kommentar einen Befehl zum Anwenden enthält, und die Transaktion, dazu dass die
Reihenfolge mit und ohne `.sql` gleich ist (außer beim Paar unten). Er läuft mit
den Unit-Tests: im Pre-commit-Hook, mit `make test-backend(-fast)` und in der
GitHub-CI nach dem Merge.

Idempotenz und Gleichheit mit `create_all` prüft der Integrationstest
`mvp/backend/semantic-search-service/app/tests/integration/test_migrationen.py`
gegen ein echtes PostgreSQL: Jedes Skript läuft zweimal auf einer Datenbank im
aktuellen Schema, und die ganze Kette läuft auf einer Datenbank ohne die Tabellen,
die Skripte selbst anlegen, sowie auf Datenbanken aus `init.sql`: dem heutigen,
dem vor #285 und dem ältesten der öffentlichen Historie; danach muss das Schema
dem von `create_all` gleichen (Spalten, Defaults, Indizes, Constraints,
Sequenzen, Trigger, Funktionen). `init.sql` allein muss es ebenfalls ergeben.
Den automatischen Ablauf prüfen die Tests `test_einspielen_*` in derselben Datei
auf denselben Ständen, dazu den zweiten Lauf, eine belegte Sperre, einen
gescheiterten Nachlauf und eine neue Datei.
Ausgenommen ist `2026-08-25-usage-events-datensparsamkeit.sql`, das beim zweiten
Lauf abbricht („Erneut anwenden“); es läuft nur auf der Datenbank aus dem
ältesten `init.sql`, dort einmal. `2026-08-19-search-events-pseudonymisieren.sql`
läuft mit, sein `TRUNCATE` trifft im Test nur leere Tabellen. Starten:
`tests/TESTING_GUIDE.md` im Semantic-Service, Abschnitt „Integration Tests Against
PostgreSQL“. Den übrigen Inhalt des Kopfs prüft kein Test.

- **Dateiname:** `JJJJ-MM-TT-<thema>.sql`, Datum der Erstellung, Thema kurz,
  kleingeschrieben, mit Bindestrichen. Das Datum legt die Reihenfolge fest;
  bei gleichem Datum gilt die alphabetische Reihenfolge des Namens **ohne**
  `.sql`: `2026-10-26-suchen-ohne-treffer.sql` vor
  `2026-10-26-suchen-ohne-treffer-personen.sql`, das die Tabelle des ersten
  voraussetzt. `ls` und `*.sql` sortieren mit Endung und damit diese beiden
  falsch herum. Ein neues Thema deshalb nicht so benennen, dass es mit dem
  Thema eines anderen Skripts vom selben Tag beginnt; der Unit-Test weist das ab.
- **Kopf:** ein SQL-Kommentar, der sagt
  1. was sich ändert und warum,
  2. ob neue Datenbanken das Skript brauchen (meist nicht, siehe oben),
  3. wie vorhandene Daten nachgetragen oder verworfen werden,
  4. als letzte Zeile: `-- Anwenden: siehe README.md in diesem Verzeichnis.`

  Den Befehl selbst nicht in den Kopf oder einen anderen Kommentar kopieren.
  Er steht nur hier, damit eine Umbenennung (Container, Datenbank, Pfad) nur
  diese Datei ändert.
- **Idempotent:** `IF NOT EXISTS` / `IF EXISTS` und Nachträge, die einen zweiten
  Lauf überstehen. Ein neues Skript darf mehrfach laufen, ohne Daten zu
  verlieren: Von Hand eingespielt, läuft es beim nächsten Start noch einmal.
  Geht das nicht, sagt der Kopf es ausdrücklich, hier steht es unter „Erneut
  anwenden“, und `NICHT_WIEDERHOLBAR` bekommt eine Abfrage, die seine Wirkung
  erkennt.
- **Transaktion:** `BEGIN;` am Anfang, `COMMIT;` am Ende. Was nicht in einer
  Transaktion laufen darf, steht danach und ist im Kopf erklärt. Der Test lässt
  dort nur `VACUUM` und die `CONCURRENTLY`-Formen von `CREATE INDEX`,
  `DROP INDEX` und `REINDEX` zu.
- **Gleiches Schema wie `create_all`:** Was das Skript anlegt, muss genau dem
  entsprechen, was die SQLAlchemy-Modelle in einer neuen Datenbank erzeugen.
  Ändert sich eine Tabelle, die auch `mvp/backend/postgres-app/init.sql`
  anlegt, dort mitziehen. Trigger und Funktionen legt `create_all` nicht an;
  gehören sie zum Schema, dann ins Modell (etwa über ein DDL-Ereignis), nicht nur
  in ein Skript.
- **Angewendete Skripte nicht ändern und nicht umbenennen.** Ein Fehler wird
  mit einem neuen Skript korrigiert. Ausnahme sind reine Kommentaränderungen;
  das SQL bleibt Zeichen für Zeichen gleich. Der Dateiname ist der Schlüssel im
  Protokoll; ein umbenanntes Skript liefe noch einmal.
- **Sperren:** Muss ein Skript eine viel genutzte Tabelle sperren, mit
  `SET LOCAL lock_timeout` kürzer begrenzen wie `2026-10-26-init-angleichen.sql`.
  Sonst wartet der Start des Dienstes bis zu 30 s auf die Sperre.
