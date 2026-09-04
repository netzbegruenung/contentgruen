# Datenschutz-Bestandsaufnahme (Art. 13 DSGVO)

> **Zweck:** belegte Faktenbasis für die Datenschutzerklärung. Keine juristische Bewertung,
> keine Empfehlung — nur, was im Code steht, mit Fundstelle.
>
> **Stand:** Commit `fae44b4` (`main`)
> **Erstanalyse:** 2026-08-25 gegen `95b565e0d37d5ee9d0a20249f2031a7e1b9851e4`
> **Fortgeschrieben:** 2026-09-03 gegen `fae44b4`. Alle Zeilennummern beziehen sich auf
> `fae44b4`; wo eine Aussage der Erstanalyse durch die zwischenzeitlichen Änderungen
> hinfällig geworden ist, steht das ausdrücklich dabei statt sie stillschweigend zu
> ersetzen. Am Code wurde für diese Aufnahme nichts geändert.
> **Fundstellen nachgeprüft:** 2026-09-04. Jede der rund 430 Zeilenangaben im Dokument
> wurde maschinell aufgelöst und gegen `fae44b4` gelesen (Anhang B, M-14). Ergebnis:
> ein inhaltlicher Fehler (`/metrics/helpful-rate` war in 1.7 noch als öffentlich
> geführt — er ist seit PR #29 admin-only) und rund 80 verschobene Zeilenangaben, die
> überwiegend aus der Erstanalyse stammten: `models.py` ist seit `95b565e` um 12 Zeilen
> gewachsen, wodurch alle Angaben ab `search_events` um denselben Betrag danebenlagen.
> Beides ist korrigiert.

## Lesehilfe

- **KONFIGURIERT** = der Wert steht in einer Settings-/Config-Klasse.
  **WIRKSAM** = ein Codepfad liest ihn tatsächlich. Wo beides auseinanderfällt, steht es dabei.
- **UNSICHER** markiert jede Stelle, an der ich mir nicht sicher bin, mit Begründung.
- **NICHT IM REPO ENTSCHEIDBAR** = hängt an Deployment-Konfiguration (SaltStack-Pillar), die
  außerhalb dieses Repos liegt. Alle diese Punkte sind in **Teil 4** gebündelt.
- Zeilennummern beziehen sich auf den oben genannten Commit `fae44b4`.
- **ERLEDIGT** markiert einen Befund der Erstanalyse, den der Code inzwischen behebt.

Pfadabkürzungen in den Tabellen:

| Kürzel | Vollpfad |
|--------|----------|
| `app/` | `mvp/backend/semantic-search-service/app/` |
| `BFF/` | `mvp/backend/BFF/` |
| `fe/` | `mvp/frontend/contentgruen-frontend/src/` |

---

# Teil 0 — Was sich seit der Erstanalyse geändert hat

Zwischen `95b565e` (25.08.) und `fae44b4` sind drei Pull Requests gemergt, die
unmittelbar an den hier beschriebenen Verarbeitungen ansetzen. Die Kurzfassung; die
Belege stehen jeweils im betroffenen Abschnitt.

| PR | Was | Folge für diese Aufnahme |
|----|-----|--------------------------|
| **#27** Datenminimierung | `usage_events` verliert die Spalten `user_id`, `ip_hash` und `user_agent`; an deren Stelle tritt `device_category`. Die View `user_usage_statistics` entfällt | **1.2 neu geschrieben**, **1.8 entfällt**, Befunde **E-1** und **E-2** erledigt |
| **#29** Härtung Phase 2 | Auth-Gate gilt in beiden Betriebsarten; `EndpointPolicy` als einzige Endpunktliste; Metrik-Endpunkte admin-only; Debug-Router `api/v1/test.py` gelöscht; alle 93 `print()` entfernt; Suchtext nicht mehr protokolliert; Nutzerkennungen in Logs nur noch als 8-stelliges Pseudonym; E-Mail-Adressen aus den BFF-Logs entfernt; `X-User-Id` wird am Proxy entfernt und die Dependency liest `X-User`; Rate-Limit auf `/moderation/report` auf einen flüchtigen Adress-Hash umgestellt; `managed-users.json` aus dem Git genommen | **1.10 neu geschrieben**, Anhang A überwiegend erledigt |
| **#32** Voraussetzungen | Cookie-Laufzeit im Keycloak-Zweig explizit 8 h gleitend; Session-ID in `localStorage` rotiert nach 30 Tagen und kommt aus `crypto.randomUUID()`; Warnhinweis zum OpenAI-Key in `core/config.py` und `CLAUDE.md` | **1.11 aktualisiert**, Befunde **B-1**, **B-2** erledigt |

**Unverändert geblieben und weiterhin gültig** sind die drei Befunde, an denen die
Datenschutzerklärung am meisten hängt:

- **E-3** — die Retention-Einstellungen werden in falscher Schreibweise gelesen; wirksam
  sind unverändert 90 Tage, täglich 02:00, weder abschaltbar noch konfigurierbar.
- **S-3** — für `search_events` existiert Löschcode ohne Aufrufer. Keine Frist.
- **Q-1/Q-2** — jede Suchanfrage wird dauerhaft als Inhalt in Qdrant gespeichert, und die
  Autorenkennung jedes Beitrags ist über die öffentliche Suche für jeden abrufbar.

---

# Teil 1 — Datenspeicher

## 1.0 Wie das PostgreSQL-Schema entsteht (vier Mechanismen)

Die Vorannahme „`init.sql` ist nicht vollständig" trifft zu. Gefunden habe ich **vier**
Mechanismen, die Tabellen anlegen:

| # | Mechanismus | Beleg | Legt an |
|---|-------------|-------|---------|
| 1 | `init.sql`, in das Postgres-Image gebacken, läuft nur bei leerem Datenverzeichnis | `mvp/backend/postgres-app/init.sql` (67 Zeilen) | `usage_tracking`, `usage_events`, 5 Indizes, 1 Trigger. Die früher hier definierte View `user_usage_statistics` ist mit PR #27 entfallen (`init.sql:37-40`) |
| 2 | SQLAlchemy `Base.metadata.create_all` beim ersten DB-Zugriff | `app/infrastructure/database/connection.py:48`, aufgerufen aus `:87` | **alle 6** ORM-Tabellen: `usage_tracking`, `usage_events`, `search_events`, `content_reports`, `raw_inputs`, `raw_input_content_links` |
| 3 | Rohes DDL zur Laufzeit | `app/repositories/vote_repository.py:20-40`, aufgerufen aus `app/services/voting_service.py:18` | `votes` + 3 Indizes |
| 4 | Handmigrationen für Bestandsumgebungen | `migrations/2026-08-19-rohinput-fangkorb.sql`, `…-search-events-pseudonymisieren.sql`, `2026-08-25-usage-events-datensparsamkeit.sql` | dieselben Tabellen wie (2), plus `TRUNCATE`/`DROP COLUMN` auf `search_events` und `DROP COLUMN`/`DROP VIEW` auf `usage_events` |

**Konsequenz:** `init.sql` deckt **2 von 7** Tabellen ab. Wer das Schema aus `init.sql` liest,
sieht `search_events`, `content_reports`, `raw_inputs`, `raw_input_content_links` und `votes`
nicht.

**Gefundene Tabellen: 7.** Die eine View ist entfallen (1.8). Suchmethoden dafür in Anhang B.

---

## 1.1 PostgreSQL — `usage_tracking`

Aggregatzähler pro Inhalt, kein Personenbezug.

| Feld | Typ | Definiert in | Personenbezug | Wer schreibt | Wer kann lesen | Wirksame Löschfrist |
|------|-----|--------------|---------------|--------------|----------------|---------------------|
| `content_id` | UUID PK | `app/infrastructure/database/models.py:35`; `init.sql:11` | nein — Inhalts-ID | `app/repositories/usage_tracking_repository.py:61,65` | öffentlich über `GET /api/v1/usage/content/{id}` (`app/api/v1/usage.py:147`, in `BFF/Proxy/EndpointPolicy.cs:28`) | **keine** |
| `usage_count` | Integer | `models.py:36`; `init.sql:12` | nein | `models.py:54-62` (`increment_usage`) | dito | **keine** |
| `last_used` / `first_used` | Timestamptz | `models.py:37-38`; `init.sql:13-14` | nein | `models.py:60-62` | dito | **keine** |
| `created_at` / `updated_at` | Timestamptz | `models.py:39-47`; `init.sql:15-16` | nein | Server-Default + Trigger `init.sql:59-62` | dito | **keine** |

**Löschfrist explizit ausgeschlossen:** `app/repositories/usage_tracking_repository.py:274-276` —
„usage_tracking aggregate counters are **preserved forever**". Der einzige Cleanup-Pfad rührt
diese Tabelle nicht an.

---

## 1.2 PostgreSQL — `usage_events`

Ein Ereignis pro Kopiervorgang eines Inhalts.

> **Neu geschrieben gegenüber der Erstanalyse.** PR #27 hat die drei personenbeziehbaren
> Spalten entfernt: `user_id`, `ip_hash` und `user_agent`. Migration
> `mvp/backend/postgres-app/migrations/2026-08-25-usage-events-datensparsamkeit.sql`
> (`DROP COLUMN` für die ersten beiden, Umbenennung von `user_agent` nach
> `device_category` mit `USING NULL`, anschließend `VACUUM FULL`), neues Schema in
> `app/infrastructure/database/models.py:65-105` und `mvp/backend/postgres-app/init.sql:19-35`.
> Damit ist dies **nicht mehr der personenbezogenste Speicher** der Anlage; das ist jetzt
> `raw_inputs` (1.5) beziehungsweise der Qdrant-Payload (1.9).

| Feld | Typ | Definiert in | Personenbezug | Wer schreibt (Codepfad) | Wer kann lesen | Wirksame Löschfrist |
|------|-----|--------------|---------------|--------------------------|----------------|---------------------|
| `id` | BigInteger PK | `models.py:85`; `init.sql:28` | nein | ORM | s.u. | 90 Tage |
| `content_id` | UUID FK→`usage_tracking` | `models.py:86-90`; `init.sql:29` | nein (aber verknüpfend) | `usage_tracking_repository.py:69` | s.u. | 90 Tage |
| `event_type` | VARCHAR(50), default `copy` | `models.py:91`; `init.sql:30` | nein | `usage_tracking_repository.py:70` | s.u. | 90 Tage |
| `timestamp` | Timestamptz | `models.py:92-94`; `init.sql:31` | nein für sich | Server-Default | s.u. | 90 Tage |
| `session_id` | VARCHAR(255) | `models.py:95`; `init.sql:32` | **pseudonym** — client-erzeugte UUID aus `localStorage`, seit PR #32 nach 30 Tagen rotierend (siehe 1.11) | `usage_tracking_repository.py:71` ← `api/v1/usage.py:120` ← Request-Body `session_id` | s.u. | 90 Tage |
| `device_category` | VARCHAR(20) | `models.py:96`; `init.sql:33` | **nein** — genau vier Werte: `mobile`, `tablet`, `desktop`, `unknown` | `usage_tracking_repository.py:72` ← `api/v1/usage.py:114,121`, abgeleitet in `app/utils/device_category.py` | s.u. | 90 Tage |

### Was **nicht mehr** gespeichert wird

| Entfallene Spalte | Was sie enthielt | Ersatz |
|-------------------|------------------|--------|
| `user_id` | Keycloak-`sub` bzw. `user-00x`; blieb über den Live-Pfad ohnehin immer `NULL` (Befund E-1) | keiner — die Nutzungserfassung ist jetzt ausdrücklich kontounabhängig |
| `ip_hash` | ungesalzenes, doppelt angewandtes SHA-256 über die Client-IP (Befund E-2) | keiner. Die IP wird an keiner Stelle mehr persistiert; sie geht nur noch flüchtig in den Rate-Limit-Schlüssel für Meldungen ein (1.4) |
| `user_agent` | Rohwert, bis zu 500 Zeichen | `device_category` — vier Werte, der Rohwert verlässt `utils/device_category.py` nicht (`api/v1/usage.py:82,114`) |

Bestandswerte wurden verworfen, nicht umgerechnet (Begründung in der Migration `:22-24`),
und mit `VACUUM FULL` (`:57`) physisch entfernt.

### Wer kann lesen

| Weg | Auth-Stufe | Beleg |
|-----|-----------|-------|
| `GET /api/v1/usage/content/{id}` (nur Zähler) | **öffentlich** | `api/v1/usage.py:147-149`; `BFF/Proxy/EndpointPolicy.cs:28` |
| `GET /api/v1/usage/trending` | **öffentlich** | `api/v1/usage.py:209-211`; `EndpointPolicy.cs:29` |
| `GET /api/v1/usage/users/{user_id}/usage-stats` | Admin-Prüfung `settings.is_admin_user` — **seit PR #29 wirksam**, siehe unten | `api/v1/usage.py:175-207` |
| `GET /api/v1/metrics/mvp-dashboard`, `/usage-trend`, `/helpful-rate` (aggregiert) | **`Depends(require_admin)`** — vorher ohne jede Auth-Dependency und öffentlich am BFF | `api/v1/metrics.py:192-195, 300-304, 339-343`; nur `/getMetrics` steht noch in `EndpointPolicy.cs:34` |
| Backup-Dumps | Dateisystemzugriff | s. 1.12 |

Die View `user_usage_statistics` ist entfallen (1.8).

### Befund E-1 — ERLEDIGT: die Dependency liest jetzt `X-User`

Die Erstanalyse hatte belegt, dass `app/dependencies.py` den Header `X-User-Id` deklarierte,
während das BFF `X-User` setzt — `usage_events.user_id` blieb dadurch immer `NULL`, und
`settings.is_admin_user()` bekam immer `None`.

Behoben an beiden Enden:

- `app/dependencies.py:217` deklariert `Header(None, alias="X-User")`, ebenso
  `require_admin` (`:234-235`). Die Kommentare `:225-229` halten die alte Fehlerklasse fest.
- `BFF/Proxy/IdentityHeaderTransform.cs:43` nimmt `X-User-Id` in die Liste der Header auf,
  die der Transform bedingungslos entfernt (`:59`). Ein Client kann sich damit nicht mehr
  per Header eine fremde Identität geben (vormals Anhang A, A-2).

**Folge:** Die Admin-Prüfung in `api/v1/usage.py:189,245,275` greift jetzt tatsächlich,
sofern `SEMANTIC_SEARCH_ADMIN_USERS` gesetzt ist (Teil 4, 4-H). Die Spalte `user_id`, um
die es ursprünglich ging, gibt es nicht mehr.

### Befund E-2 — ERLEDIGT: es wird keine IP mehr gespeichert

`api/v1/usage.py` bildet keinen IP-Hash mehr; die Spalte ist weg. Die einzige verbliebene
IP-Verarbeitung im Backend ist `app/utils/client_identity.py` für das Rate-Limit auf dem
anonymen Meldeweg (1.4): Salt zufällig pro Prozess (`:40`), SHA-256, auf 16 Hex-Zeichen
gekürzt (`:85`), nur im Arbeitsspeicher des gleitenden Fensters. Weder Datenbank noch Log
sehen den Wert; das Modul dokumentiert das ausdrücklich (`:14-28`).

### Befund E-3 — UNVERÄNDERT: die 90 Tage sind ein Fallback, kein konfigurierter Wert

`app/core/config.py:146-150` definiert vier Einstellungen in Kleinschreibung
(Pydantic-Feldnamen, `env_prefix = "SEMANTIC_SEARCH_"`):

```
enable_usage_cleanup: bool = True
usage_retention_days: int = 90
cleanup_hour: int = 2
cleanup_minute: int = 0
```

`app/services/cleanup/usage_cleanup_service.py` liest **alle vier in Großschreibung**:

| Zeile | Gelesen als | Existiert auf `settings`? | Folge |
|-------|-------------|---------------------------|-------|
| `:172` | `getattr(settings, "USAGE_RETENTION_DAYS", 90)` | nein | immer **90** |
| `:184` | `getattr(settings, "ENABLE_USAGE_CLEANUP", True)` | nein | immer **an** |
| `:189` | `getattr(settings, "CLEANUP_HOUR", 2)` | nein | immer **02** |
| `:190` | `getattr(settings, "CLEANUP_MINUTE", 0)` | nein | immer **:00** |

Empirisch nachgeprüft mit `pydantic_settings` (gleiche Feld-/Prefix-Konstellation):

```
SEMANTIC_SEARCH_USAGE_RETENTION_DAYS=30 gesetzt
  s.usage_retention_days                      -> 30
  getattr(s,'USAGE_RETENTION_DAYS','FALLBACK') -> FALLBACK
```

**Wirksam ist demnach: 90 Tage, täglich 02:00 UTC, nicht abschaltbar, nicht über die
Umgebung veränderbar.** Ein `SEMANTIC_SEARCH_USAGE_RETENTION_DAYS` im Salt-Pillar hätte
keine Wirkung. Für die Datenschutzerklärung ist das die günstige Richtung: die Frist ist
gerade deshalb belastbar, weil sie fest verdrahtet ist. Als Fehler bleibt sie trotzdem
stehen — wer sie ändern will, muss den Code ändern, und wer sie über den Pillar zu ändern
glaubt, irrt sich still.

Der Scheduler läuft: `app/main.py:102` ruft `start_cleanup_scheduler()` beim Startup, plus
ein sofortiger Lauf beim Start (`usage_cleanup_service.py:97-99`).

Gelöscht wird ausschließlich aus `usage_events`
(`usage_tracking_repository.py:291-296`, Filter `timestamp < cutoff`).

---

## 1.3 PostgreSQL — `search_events`

| Feld | Typ | Definiert in | Personenbezug | Wer schreibt | Wer kann lesen | Wirksame Löschfrist |
|------|-----|--------------|---------------|--------------|----------------|---------------------|
| `id` | BigInteger PK | `models.py:122` | nein | ORM | s.u. | **keine** |
| `actor_hash` | VARCHAR(64), nullable | `models.py:123` | **pseudonym, tagesrotierend** — Details unten | `app/repositories/search_tracking_repository.py:44` ← `services/search_tracking_service.py:98-105` ← `api/v1/search.py:256-264` | s.u. | **keine** |
| `results_count` | Integer | `models.py:124` | nein | `search_tracking_repository.py:44` | s.u. | **keine** |
| `timestamp` | Timestamptz | `models.py:125-127` | nein für sich | Server-Default | s.u. | **keine** |

**Nicht (mehr) vorhanden:** `query_text`, `user_id`, `session_id`, `ip_hash` — entfernt durch
`migrations/2026-08-19-search-events-pseudonymisieren.sql:30-33`, Bestandsdaten per
`TRUNCATE` (`:25`) plus `VACUUM FULL` (`:42`) verworfen. Begründung im ORM dokumentiert
(`models.py:109-118`).

**Lesen:** ausschließlich aggregiert über `GET /api/v1/metrics/daily-active-users`
(`api/v1/metrics.py:217-221`) und `/searches-per-user` (`:246-250`). Beide verlangen seit
PR #29 `Depends(require_admin)`; am BFF ist von `/api/v1/metrics/` nur noch der einzelne
Pfad `/getMetrics` ohne Anmeldung erreichbar (`BFF/Proxy/EndpointPolicy.cs:30-34`, mit
Begründung). Vorher stand das ganze Präfix in der Public-Liste und keiner der sechs
Betriebskennzahlen-Endpunkte hatte eine Auth-Dependency — die DAU-Zahlen waren damit
weltweit lesbar (vormals Anhang A, A-9). Die zugrundeliegenden Queries:
`search_tracking_repository.py:77-82` (COUNT DISTINCT) und `:114-123` (GROUP BY).

### Befund S-1 — Pseudonymisierung ist implementiert wie beschrieben

`app/services/search_tracking_service.py:34-72`:

```python
actor_id = user_id or session_id          # :59
if not actor_id: return None              # :60-61
day = moment.strftime("%Y-%m-%d")         # UTC, :64-65
secret = settings.actor_hash_secret or _FALLBACK_SECRET   # :67
return hmac.new(secret, f"{actor_id}|{day}", sha256).hexdigest()  # :68-72
```

- HMAC-SHA256, nicht nacktes SHA-256 ✓
- UTC-Datum im Nachrichtentext → tägliche Rotation ✓ (Test: `app/tests/unit/services/test_search_tracking_service.py:38-45`)
- Suchtext wird nicht übergeben — `track_search()` nimmt ihn gar nicht entgegen
  (`search_tracking_service.py:83-84`, Aufruf `api/v1/search.py:256-264`) ✓
- Der Hash enthält die Kennung nicht (Test `:54-62`) ✓

### Befund S-2 — das Secret ist im Repo nirgends gesetzt; der Fallback ist zufällig pro Prozess

`app/core/config.py:144`: `actor_hash_secret: Optional[str] = None`, Env-Name wäre
`SEMANTIC_SEARCH_ACTOR_HASH_SECRET` (Prefix `config.py:176`).

Repo-weiter Grep nach `ACTOR_HASH_SECRET` über `*.yml`, `*.yaml`, `*.env*`, `*.sh`, `*.md`:
**kein Treffer.** Weder `docker-compose.dev.yml` noch `docker-compose.tst.yml` setzen es.

Wenn nicht gesetzt, greift `_FALLBACK_SECRET = secrets.token_hex(32)`
(`search_tracking_service.py:25`) — einmal pro **Prozess**.

Was das bedeutet (Kommentar `config.py:139-143` beschreibt es korrekt):
- Datenschutzseitig **unkritischer**, nicht kritischer: der Schlüssel existiert nur im
  Arbeitsspeicher und ist nach einem Neustart unwiederbringlich weg. Aus den gespeicherten
  Hashes lässt sich dann selbst mit Kenntnis aller Nutzerkennungen nichts mehr rekonstruieren.
- Fachlich falsch: jeder Neustart eröffnet einen neuen Pseudonymraum. Dieselbe Person zählt
  am selben Tag mehrfach → „Daily Active Users" ist nach oben verzerrt.

Ob in Produktion gesetzt: **Teil 4, Frage 4-A.**

### Befund S-3 — für `search_events` existiert Löschcode, den niemand aufruft

`app/repositories/search_tracking_repository.py:187-211` implementiert `cleanup_old_events()`
(DELETE auf `SearchEvent` älter als `days_to_keep`).

Aufrufer: **keiner — auch auf `fae44b4` nicht.** Repo-weiter Grep nach `cleanup_old_events`
liefert fünf Treffer: die beiden Definitionen (`search_tracking_repository.py:187`,
`usage_tracking_repository.py:270`) und den einen Aufrufpfad
`services/cleanup/usage_cleanup_service.py:52` → `services/usage_tracking_service.py:241,253`
→ `repositories/usage_tracking_repository.py:270` sowie den manuellen Endpunkt
`api/v1/usage.py:290`. Alle vier zeigen auf `usage_events`.
Grep nach `cleanup_old_events` über das gesamte Repo (Anhang B, Methode M-4) findet nur
Definitionen und den einen `usage`-Aufrufpfad.

**Wirksame Löschfrist für `search_events`: keine.**

---

## 1.4 PostgreSQL — `content_reports`

| Feld | Typ | Definiert in | Personenbezug | Wer schreibt | Wer kann lesen | Wirksame Löschfrist |
|------|-----|--------------|---------------|--------------|----------------|---------------------|
| `id` | UUID PK | `models.py:141-145` | nein | `app/repositories/content_report_repository.py:49` | s.u. | **keine** |
| `content_id` | UUID | `models.py:146` | nein | `content_report_repository.py:50` | s.u. | **keine** |
| `content_type` | VARCHAR(50) | `models.py:147` | nein | `:51` | s.u. | **keine** |
| `reported_by_user_id` | VARCHAR(255) | `models.py:148` | **ja** — Keycloak-`sub`/`user-00x`; `"anonymous"` wird zu `NULL` normalisiert | `api/v1/moderation.py:159` → `content_report_repository.py:53` | s.u. | **keine** |
| `reported_by_session_id` | VARCHAR(255) | `models.py:149` | **pseudonym** — localStorage-UUID | `api/v1/moderation.py:160` → `:54` | s.u. | **keine** |
| `reason` | VARCHAR(100) | `models.py:150` | nein | `:52` | s.u. | **keine** |
| `description` | **Text, Freitext** | `models.py:151` | **potenziell ja** — Nutzereingabe, kein Filter | `:55` | s.u. | **keine** |
| `status` | VARCHAR(20) | `models.py:152` | nein | `:56` | s.u. | **keine** |
| `created` | Timestamptz | `models.py:153` | nein | Server-Default | s.u. | **keine** |
| `reviewed_by` | VARCHAR(255) | `models.py:154` | **ja** — Kennung der moderierenden Person | Moderationspfad | s.u. | **keine** |
| `reviewed_at` | Timestamptz | `models.py:155` | nein | dito | s.u. | **keine** |
| `resolution_notes` | **Text, Freitext** | `models.py:156` | **potenziell ja** | dito | s.u. | **keine** |

Constraint `models.py:163-166`: mindestens eine der beiden Melderkennungen muss gesetzt sein —
eine vollständig anonyme Meldung ist per Schema ausgeschlossen.

**Wer kann lesen:** `GET /api/v1/moderation/reports` und `/stats`, `PUT …/dismiss`, `DELETE` —
alle vier mit `Depends(require_admin)` (`api/v1/moderation.py:191,229,267,300`).
`require_admin` (`app/dependencies.py:233-249`) prüft `X-User` ≠ leer/`anonymous`
**und** `X-Is-Admin: true`; letzteres setzt nur das BFF aus Claims
(`IdentityHeaderTransform.cs:56-63`) und entfernt einen mitgeschickten Wert vorher
bedingungslos (`:46`). Das ist der einzige Speicher mit funktionierender Admin-Schranke.

**Schreiben:** `POST /api/v1/moderation/report` ist **öffentlich**
(`BFF/Proxy/EndpointPolicy.cs:30`) — anonymes Melden ist ausdrücklich vorgesehen, der
Router begründet es mit Art. 16 DSA (`api/v1/moderation.py:97-112`).

**Seit PR #29 zusätzlich (alles in `api/v1/moderation.py:89-181`):**

| Was | Beleg | Datenschutzrelevanz |
|-----|-------|---------------------|
| Das Rate-Limit hängt nicht mehr an `X-Session-Id`, sondern an einem flüchtigen Hash der Client-Adresse | `:116-128`, `utils/client_identity.py:73-85` | Die IP wird verarbeitet, aber nicht gespeichert und nicht geloggt: Salt zufällig pro Prozess, 16 Hex-Zeichen, nur im Fenster des Limiters |
| Angemeldete Melder unterliegen zusätzlich einem Limit auf der Kennung | `:119-120` | — |
| Doppelmeldung derselben Person zum selben Inhalt legt keine zweite Zeile an | `services/moderation_service.py:66-73`, `repositories/content_report_repository.py:67-97` | weniger gespeicherte Daten |
| Der gemeldete Inhalt muss existieren, bevor eine Zeile entsteht | `:132-136`, `moderation_service.py:93-119` | verhindert Zeilen ohne Bezugsobjekt |
| `X-Session-Id` wird nur übernommen, wenn es eine UUID ist, sonst verworfen | `:151`, `client_identity.py:88-116` | in der Spalte steht kein beliebiger Freitext mehr |
| Die Melderkennung steht nicht mehr in der Logzeile | `content_report_repository.py:60-62` | s. 1.10 |

**Löschfrist: keine.** Grep über `repositories/`, `services/`, `api/` nach DELETE-Pfaden
(Anhang B, M-4) findet für `ContentReport` keinen. `moderation_service.py:134-152`
löscht den *gemeldeten Inhalt* aus Qdrant, nicht die Meldung.

---

## 1.5 PostgreSQL — `raw_inputs` (Fangkorb)

| Feld | Typ | Definiert in | Personenbezug | Wer schreibt | Wer kann lesen | Wirksame Löschfrist |
|------|-----|--------------|---------------|--------------|----------------|---------------------|
| `id` | UUID PK | `models.py:187-191`; Migration `:27` | nein | `app/repositories/raw_input_repository.py:64` | s.u. | **keine** |
| `content` | **Text, Freitext** (max. 5000, `dtos/raw_input.py:51`) | `models.py:192`; Migration `:28` | **potenziell ja** — freier Satz | `raw_input_repository.py:65` | s.u. | **keine** |
| `url` | Text (max. 2000) | `models.py:193`; Migration `:29` | **potenziell ja** — Link auf fremde Beiträge/Profile | `:66` | s.u. | **keine** |
| `image_url` | Text (max. 2000) | `models.py:194`; Migration `:30` | **potenziell ja** — Bild Dritter | `:67` | s.u. | **keine** |
| `submitted_by` | VARCHAR(255), nullable | `models.py:195`; Migration `:32` | **ja** — Keycloak-`sub`/`user-00x` | `api/v1/raw_input.py:55` → `raw_input_repository.py:68` | s.u. | **keine** |
| `source_channel` | VARCHAR(50), default `web` | `models.py:196` | nein | `:69` | s.u. | **keine** |
| `status` | VARCHAR(20), default `open` | `models.py:197` | nein | `:70` | s.u. | **keine** |
| `created_at` | Timestamptz | `models.py:198-200` | nein | Server-Default | s.u. | **keine** |

### Wer wird als Einwerfer gespeichert

`app/api/v1/raw_input.py:30-40` (`_einwerfende_person`): der Wert des `X-User`-Headers;
`"anonymous"` und leer werden bewusst zu `None`. `X-User` ist der Keycloak-`sub` bzw. bei
Managed/Dummy-Auth `user-001`/`user-002`/`test-user-id-1`
(`BFF/Program.cs:642-646` `ClaimUtilities.GetUserId` — `sub`, ersatzweise `NameIdentifier`).
Kein Klarname, keine E-Mail.

### Wer bekommt das zu sehen

`GET /api/v1/rawinput/getRawInputs` (`api/v1/raw_input.py:67-87`) liefert **alle** Einwürfe,
nicht nur die eigenen — ausdrücklich so gewollt (`:76-77`). Das Response-DTO
`RawInputResponse` enthält `submitted_by` (`app/dtos/raw_input.py:97`), und das Repository
gibt das Feld mit aus (`raw_input_repository.py:35`).

Das Frontend zeigt es als eigene Tabellenspalte:
`fe/app/raw-input-list/raw-input-list.component.ts:52`
(`displayedColumns = ['inhalt','submitted_by','created_at','status']`),
Template `raw-input-list.component.html:53`, Fallback-Beschriftung
„ohne Kennung" bei `NULL` (`raw-input-list.component.ts:119`).

**Also: jede angemeldete Person sieht bei jedem Einwurf, wer ihn eingeworfen hat.**

Schutzstufe davor:
- Frontend-Route `/fangkorb` liegt hinter `AuthGuard` (`fe/app/app.routes.ts:28-30`).
- Der Router selbst hat **keine** Auth-Dependency (`api/v1/raw_input.py:67-72`).
- `/api/v1/rawinput/` steht **nicht** in `EndpointPolicy.AllowAnonymous`
  (`BFF/Proxy/EndpointPolicy.cs:24-35`) und ist damit am BFF nur angemeldet erreichbar.
  **Seit PR #29 gilt das in beiden Betriebsarten:** der Auth-Gate hängt nicht mehr an
  `USE_KEYCLOAK`, sondern läuft als eigene Middleware in der Proxy-Pipeline
  (`BFF/Program.cs:466-486`). Die Erstanalyse hatte hier den gravierenderen Stand
  beschrieben — bei `USE_KEYCLOAK=false` wurde der Proxy vorher ohne
  Autorisierungspipeline gemappt und es schützte nur der clientseitige Frontend-Guard
  (vormals Anhang A, A-1). **ERLEDIGT.**

**Löschfrist: keine.** Der ORM-Kommentar sagt es selbst (`models.py:228-230`): Einwürfe
werden nicht gelöscht; der Fremdschlüssel mit `ON DELETE CASCADE` existiert nur, damit ein
*späteres* Löschen aus Datenschutzgründen keine Verweise auf Nichts hinterlässt.

---

## 1.6 PostgreSQL — `raw_input_content_links`

| Feld | Typ | Definiert in | Personenbezug | Wer schreibt | Wer kann lesen | Wirksame Löschfrist |
|------|-----|--------------|---------------|--------------|----------------|---------------------|
| `id` | UUID PK | `models.py:239-243` | nein | **niemand** | — | **keine** |
| `raw_input_id` | UUID FK→`raw_inputs` ON DELETE CASCADE | `models.py:244-248` | nein | **niemand** | — | Kaskade beim Löschen des Einwurfs |
| `content_id` | UUID (kein FK, zeigt nach Qdrant) | `models.py:249` | nein | **niemand** | — | **keine** |
| `created_by` | VARCHAR(255) | `models.py:250` | **ja** (wenn je gefüllt) | **niemand** | — | **keine** |
| `created_at` | Timestamptz | `models.py:251-253` | nein | **niemand** | — | **keine** |

**Die Tabelle ist heute leer.** Der ORM-Docstring stellt es ausdrücklich fest
(`models.py:220-221`: „**Heute schreibt niemand in diese Tabelle** — die Verarbeitung ist
nicht gebaut"), die Migration ebenso
(`2026-08-19-rohinput-fangkorb.sql:9-10`). Grep nach `RawInputContentLink` über das ganze
Repo findet nur die Modelldefinition und die Migration — keinen Schreibpfad, keinen Leser.

Für die Datenschutzerklärung: existierende, aber unbenutzte Struktur. **UNSICHER** ist nur,
ob in einer Bestandsdatenbank aus einem früheren Stand Zeilen liegen — das kann ich aus dem
Repo nicht sehen, halte es aber für ausgeschlossen, da es nie einen Schreibpfad gab.

---

## 1.7 PostgreSQL — `votes`

Nicht in `init.sql`, nicht im ORM, nicht in den Migrationen — **zur Laufzeit per rohem DDL**
angelegt (`app/repositories/vote_repository.py:20-40`, aufgerufen aus
`app/services/voting_service.py:18`).

| Feld | Typ | Definiert in | Personenbezug | Wer schreibt | Wer kann lesen | Wirksame Löschfrist |
|------|-----|--------------|---------------|--------------|----------------|---------------------|
| `id` | UUID PK `gen_random_uuid()` | `vote_repository.py:24` | nein | `:49-55` (`upsert_vote`) | s.u. | **keine** |
| `user_id` | VARCHAR(255) **NOT NULL** | `vote_repository.py:25` | **ja** — Keycloak-`sub`; anonym ist hier nicht möglich | `:49-55` ← `api/v1/voting.py:31,62,89,120` ← `get_current_user` (`voting.py:17`, Alias `X-User` — hier korrekt) | s.u. | **keine** |
| `content_id` | UUID NOT NULL | `vote_repository.py:26` | nein | dito | s.u. | **keine** |
| `vote_type` | VARCHAR(20) CHECK `like`/`dislike` | `vote_repository.py:27` | **ja i.V.m. `user_id`** — Meinungsäußerung zu politischem Inhalt | dito | s.u. | **keine** |
| `created` | Timestamp (**ohne** Zeitzone) | `vote_repository.py:28` | nein | `datetime.utcnow()` `:71` | s.u. | **keine** |

`UNIQUE(user_id, content_id)` (`vote_repository.py:29`) → eine Stimme pro Person und Inhalt,
Änderungen überschreiben (`ON CONFLICT DO UPDATE`, `:51-54`).

**Wer kann lesen:**
- eigene Stimme: `GET /api/v1/voting/content/{id}` (`api/v1/voting.py:140-144`),
  `POST /votes/batch` (`:159-163`) — jeweils auf `X-User` gefiltert
- Summen ohne Personenbezug: `GET /api/v1/voting/content/{id}/stats` (`:169-171`)
- aggregiert, aber **nicht mehr öffentlich**: `/api/v1/metrics/helpful-rate` verlangt seit
  PR #29 `Depends(require_admin)` (`api/v1/metrics.py:339-343`) und steht am BFF nicht in
  `EndpointPolicy.AllowAnonymous` (`EndpointPolicy.cs:24-36`). Die Erstanalyse hatte den
  Endpunkt als öffentlich geführt; das traf für `95b565e` zu, für `fae44b4` nicht mehr
- `/api/v1/voting/` steht **nicht** in `EndpointPolicy.AllowAnonymous` (`BFF/Proxy/EndpointPolicy.cs:24-35`),
  wohl aber in der Frontend-Liste (`fe/app/shared/public-endpoints.ts`). Das ist seit PR #29
  kein Widerspruch mehr, sondern gewollt: die Frontend-Liste entscheidet nur, ob auf
  `/login` umgeleitet wird, und der Kommentar in `EndpointPolicy.cs:11-16` hält den
  Unterschied fest

**Löschung:** Es gibt `delete_vote` (`vote_repository.py:93-96`), aber nur als
nutzergesteuertes Zurücknehmen einer Stimme (`DELETE /api/v1/voting/…`, `voting.py:55,113`).
Keine zeit- oder kontobasierte Löschung. **Wirksame Löschfrist: keine.**

---

## 1.8 PostgreSQL — View `user_usage_statistics` — **ENTFALLEN**

Die View gruppierte nach `usage_events.user_id` und enthielt diese Kennung im Klartext.
Sie ist mit PR #27 gefallen: `DROP VIEW IF EXISTS user_usage_statistics` in
`migrations/2026-08-25-usage-events-datensparsamkeit.sql:36`, und `init.sql:37-40`
dokumentiert an ihrer Stelle, warum sie nicht wiederkommt. Anwendungscode hat sie nie
benutzt — die Nutzerstatistik hinter `/api/v1/usage/users/{id}/usage-stats` liest Qdrant
und `usage_tracking`.

Für die Datenschutzerklärung: nichts zu beschreiben.

---

## 1.9 Qdrant — Vektor-Payloads

**Wie der Payload entsteht:** `app/repositories/implementations/qdrant/base_repository.py:204`
serialisiert das **vollständige** Pydantic-Modell (`json.loads(item_input.model_dump_json())`)
und übergibt es unverändert als Payload an
`services/embeddings/qdrant_embeddings_manager.py:330`
(`PointStruct(id=…, vector=…, payload=document)`). Es gibt **keine** Feldauswahl und keinen
Ausschluss — was am Modell steht, steht im Payload.

Sammlung: `content_collection` (`app/core/config.py:23`), alle Inhaltstypen in **einer**
Collection, unterschieden über `content_type` (`qdrant_embeddings_manager.py:320`).

### Gemeinsame Payload-Felder aller Inhaltstypen (`app/domain/models/base_content.py`)

| Feld | Definiert in | Personenbezug | Wer schreibt | Wer kann lesen | Wirksame Löschfrist |
|------|--------------|---------------|--------------|----------------|---------------------|
| `text` | `base_content.py:29` | **potenziell ja** — Freitext des Beitrags **und** jeder Suchanfrage (s.u.) | Add-Endpunkte; `api/v1/search.py:105-119` | **öffentlich** über `POST /api/v1/search/searchByText` | **keine** |
| `content_type` | `base_content.py:30` | nein | dito | öffentlich | **keine** |
| `id`, `created`, `last_modified` | `base_content.py:84-86` | nein für sich | dito | öffentlich | **keine** |
| `original_author` | `base_content.py:87` | **ja** — Keycloak-`sub`; bei Suchanfragen `system:suchanfrage` | `api/v1/post.py:109`, `api/v1/image.py:101`, `services/content/{statement,commentary,generic_text,reference}_service.py:167/131/94/128` | **öffentlich, und sichtbar gerendert** (s.u.) | **keine** |
| `last_modified_by` | `base_content.py:88` | **ja** | `api/v1/post.py:110`, `api/v1/image.py:102` | öffentlich; in `/contributions` als Spalte (`fe/app/contributions-view/contributions-view.component.html:67-69`) | **keine** |
| `authors[]` (`AuthorEntry.name`, `.role`) | `base_content.py:89`, `domain/models/author_entry.py:17-18` | **ja** | `api/v1/post.py:111`, `api/v1/image.py:103` | öffentlich | **keine** |
| `edit_history[]` (`EditEntry.editor`, `.timestamp`, `.action`) | `base_content.py:90`, `domain/models/edit_entry.py:22-24` | **ja — vollständige Bearbeitungshistorie mit Kennung und Zeitstempel** | Content-Services | öffentlich | **keine** |
| `status`, `origin`, `visibility` | `base_content.py:91-92,100` | nein | dito | öffentlich | **keine** |
| `most_similar_*`, `report_count`, `is_archived`, `report_flagged`, `rejection_reason`, `block_reason` | `base_content.py:93-99` | nein | dito | öffentlich | **keine** |

### Typspezifische Zusatzfelder mit möglichem Personenbezug

| Typ | Feld | Definiert in | Anmerkung |
|-----|------|--------------|-----------|
| `post` | `author` | `domain/models/post.py:48` | **Handle der ursprünglichen Person auf der Fremdplattform** — Personenbezug **Dritter**, die von der Erhebung nichts wissen |
| `post` | `url`, `platform`, `engagement` | `post.py:47,49,50` | Link auf das Fremdprofil/den Fremdbeitrag |
| `image` | `image_url` | `domain/models/image.py:37` | URL eines Fremdbildes; wird im Browser direkt geladen (Teil 2) |
| `image` | `description_model` | `image.py:39` | Modellname der KI-Beschreibung |
| `commentary`, `generic_text` | `title`, `long_text`, `short_text`, `references[]` | `commentary.py:74-80`, `generic_text.py:71-77` | Freitext |
| `statement` | `replysuggestions[]` | `statement.py:75` | Freitext |
| `reference` | `reference_string` | `reference.py:24` | Freitext/Quellenangabe |

### Befund Q-1 — jede Suchanfrage wird als Inhalt in Qdrant gespeichert

`app/api/v1/search.py:105-119`: der Suchtext wird bei jeder Suche als `Statement` angelegt,
mit `SEARCH_QUERY_AUTHOR` als Autor und `ContentOrigin.SEARCH_QUERY` als Herkunft.

`app/domain/models/content_origin.py:29`:
`SEARCH_QUERY_AUTHOR = "system:suchanfrage"`, mit der Begründung `:30-41`: „wer gesucht hat,
geht aus dem Statement niemand etwas an". Der Doppelpunkt schließt eine Kollision mit
einer echten Kennung aus.

**Wirksam:** der Suchtext selbst wird **dauerhaft** gespeichert und ist danach für alle
suchbar; die suchende Person ist am Datensatz **nicht** erkennbar. Aus `search_events` wurde
der Suchtext entfernt (1.3) — über diesen Weg landet er trotzdem in Qdrant, nur ohne Bezug
zur Person. Das ist eine bewusste Konstruktion, keine Lücke, aber sie gehört in den Text:
*was Nutzende ins Suchfeld tippen, wird Teil des öffentlichen Bestands.*

### Befund Q-2 — Autorenkennung ist für nicht angemeldete Besucher sichtbar

`POST /api/v1/search/searchByText` ist ein Public-Endpoint (`BFF/Proxy/EndpointPolicy.cs:26`).
Die Antwort-DTOs betten das **vollständige** DB-Entry ein —
`app/dtos/search.py:46` (`commentary_result: CommentaryDbEntry`), `:58`
(`generictext_result: GenericTextDbEntry`), analog `post`/`image` (`dtos/search.py:6-7`).
Damit gehen `original_author`, `last_modified_by`, `authors[]` und `edit_history[]` an
jeden Aufrufer.

Das Frontend rendert es sichtbar mit „Von: …":
`fe/app/commentary-result-item/commentary-result-item.component.html:213`,
`generictext-result-item.component.html:198`,
`post-result-item.component.html:152`,
`image-result-item.component.html:98`.

Angezeigt wird der Rohwert des `X-User`-Headers, also die Keycloak-`sub` (eine UUID) bzw.
`user-001`/`test-user-id-1` — **kein Klarname**. Für Betroffene ist es dennoch eine dauerhaft
öffentliche, über alle Beiträge hinweg verknüpfbare Kennung.

### Löschung in Qdrant

- `delete_by_id` / `delete_by_filter` existieren (`qdrant_embeddings_manager.py:463,475`).
- Aufgerufen nur aus `services/moderation_service.py:174-192` (`delete_content`), erreichbar
  über `DELETE /api/v1/moderation/content/{id}` mit `require_admin`
  (`api/v1/moderation.py:223-229`).
- **Keine** zeit- oder kontobasierte Löschung. Kein Pfad, der die Beiträge einer Person löscht
  oder deren Kennung anonymisiert.

**Wirksame Löschfrist Qdrant: keine.** Löschung nur einzeln durch Moderation.

**Qdrant-Zugangsschutz:** Grep über die Compose-Dateien nach `QDRANT__SERVICE__API_KEY`/
`api_key`: kein Treffer — im Repo ist **keine** Qdrant-Authentifizierung konfiguriert.
Im Dev-Compose sind 6333/6334 auf dem Host veröffentlicht
(`docker-compose.dev.yml:24-26`); im Test-Compose nicht. Produktion: Teil 4.

---

## 1.10 Logs (stdout der Container)

> **Neu geschrieben gegenüber der Erstanalyse.** PR #29 hat den Logpfad umgebaut. Was
> hier stand — 93 filterlose `print()`, Suchtexte auf INFO, E-Mail-Adressen an sieben
> Stellen im BFF, ein Debug-Endpunkt, der alle eingehenden Header samt Cookie ausgab — ist
> überwiegend nicht mehr da. Der Abschnitt beschreibt den Stand `fae44b4` und hält daneben
> fest, was entfallen ist.

### 1.10.1 `print()` im Python-Backend — **ENTFALLEN**

Zählung über `api/`, `services/`, `repositories/`, `core/`, `domain/`, `middleware/`,
`utils/` nach `^\s*print(` (Anhang B, M-5): **0 Treffer**. In der Erstanalyse waren es 93,
darunter die Nutzerkennung im Klartext und der vollständige Request inklusive Such- und
Beitragstext.

Mit erledigt: der Debug-Router `app/api/v1/test.py` (485 Zeilen), dessen
`GET /api/v1/test/headers` sämtliche eingehenden Header Zeile für Zeile auf stdout schrieb
— einschließlich des durchgereichten Cookie-Headers mit dem Auth-Ticket. Die Datei ist
gelöscht, der Pfad `/api/v1/test` steht zusätzlich in `EndpointPolicy.Blocked`
(`BFF/Proxy/EndpointPolicy.cs:56-60`) und wird vor Routing und Authentifizierung mit 404
abgewiesen (`BFF/Program.cs:394-407`) — als Riegel für den Fall, dass er zurückkehrt.
Ein Ruff-Regelsatz hält `print` fern (`pyproject.toml`, Regel `T201`, im Pre-Commit-Hook).

### 1.10.2 Logger im Python-Backend

Loglevel: `app/core/config.py:76` `log_level: str = "INFO"`; `DEBUG` im Dev-Compose
(`docker-compose.dev.yml:99`), `INFO` im Test-Compose.

**Der Suchtext wird auf dem Anfragepfad nicht mehr protokolliert.** `api/v1/search.py:78-83`
loggt nur noch `Search request (limit=…)`, mit ausdrücklicher Begründung im Kommentar; die
Zeile darunter (`:86-91`) vermerkt Angemeldet/Anonym ohne Kennung, damit im Log nicht doch
wieder „wer hat wonach gesucht" zusammenläuft. Die früheren Ausgaben in
`services/content/base_content_service.py`, `statement_service.py`,
`repositories/implementations/qdrant/base_repository.py` und
`services/keyword_overlap_service.py` sind entfernt.

**Nutzerkennungen laufen über `log_pseudonym()`** (`app/core/logging.py:168-182`): die
ersten 8 Hex-Zeichen eines SHA-256 über die Kennung, `anonymous` bleibt `anonymous`. Der
Docstring benennt die Grenze selbst — ungesalzen, also über Zeilen hinweg verkettbar und
bei bekanntem Kennungsraum zurückrechenbar; für eine flüchtige Logzeile der Kompromiss,
für gespeicherte Daten nicht.

Was danach noch mit Personenbezug im Log landen kann:

| Was | Level | Fundstelle |
|-----|-------|------------|
| Nutzerkennung als 8-stelliges Pseudonym bei jeder Stimmabgabe | INFO | `services/voting_service.py:35,65,96,126` |
| dito bei Rate-Limit-Überschreitungen | WARNING | `middleware/rate_limiter.py:83,102,120` |
| dito im Fehlerfall der Nutzungsstatistik | ERROR | `api/v1/usage.py:203` |
| **Suchtext im Klartext** — einzige verbliebene Stelle, nur im Ausnahmezweig | ERROR | `repositories/implementations/qdrant/statement_repository.py:173` (`logger.error(f"Query: {query_text}")`) |
| Freitext-Bruchstücke aus Ausnahmen (`exc_info=True`) | ERROR | verteilt; nicht Frame für Frame geprüft, siehe Anhang B, blinder Fleck 6 |

Nicht mehr geloggt: Session-IDs, Einwerfer- und Melderkennungen
(`repositories/raw_input_repository.py`, `repositories/content_report_repository.py:60-62`).

### 1.10.3 Logs im BFF (.NET)

**Die E-Mail-Adressen sind weg.** Die Erstanalyse hatte sieben Stellen aufgeführt, an denen
die eingegebene Adresse ins Log ging — bei jedem Login, jedem Fehlversuch und jedem
Rate-Limit. Auf `fae44b4` steht dort entweder gar keine Kennung oder die interne `UserId`:

| Was | Level | Fundstelle |
|-----|-------|------------|
| „Authentication rate limit exceeded" — ohne Kennung | Warning | `BFF/Services/ManagedUserService.cs:126` |
| „Authentication failed - user not found" — ohne Kennung | Warning | `ManagedUserService.cs:137` |
| „Authentication successful for user: {UserId}" | Information | `ManagedUserService.cs:147` |
| „invalid password for user: {UserId}" | Warning | `ManagedUserService.cs:153` |
| „Authentication error during managed auth" — ohne Kennung | Error | `ManagedUserService.cs:160` |
| „Managed auth login attempted while disabled" / „Failed login attempt via managed auth" — ohne Kennung | Warning | `Controllers/AuthController.cs:67,84` |
| „User {UserId} logged in successfully via managed auth" | Information | `AuthController.cs:120` |
| Nutzerkennung beim Header-Setzen | Debug | `Proxy/IdentityHeaderTransform.cs:67,75` |
| Pfad eines geschützten Endpunkts ohne Nutzer | Warning | `IdentityHeaderTransform.cs:89` |
| Pfad eines am Rand gesperrten Endpunkts | Warning | `Program.cs:399` |

`Console.WriteLine` kommt in keiner `*.cs` mehr vor.

**Folge für die Datenschutzerklärung:** Die `UserId` ist bei Managed Auth `user-001` und
bei Keycloak die `sub`-UUID — kein Klarname und keine Adresse, aber eine über Zeilen
hinweg stabile Kennung. `docs/LOESCHKONZEPT.md` behauptet unter „Was nicht gelöscht wird"
noch, `docker logs` enthalte „Kennung, E-Mail und Client-IP"; für die E-Mail trifft das
seit PR #29 nicht mehr zu. **Die Zeile ist beim Nachziehen der Rechtstexte zu korrigieren.**

### 1.10.4 Webserver-Logs

Die nginx-Konfigurationen setzen **weiterhin weder** `access_log` **noch** `log_format` —
geprüft auf `fae44b4`: `mvp/frontend/contentgruen-frontend/nginx.conf`,
`nginx.docker.conf`, `mvp/tst-server-config/frontend-nginx.conf`, `backend-nginx.conf`.
Damit gilt der nginx-Default (`access_log` an, Kombiformat **mit Client-IP**). Die IP wird
zusätzlich nach innen weitergereicht: `proxy_set_header X-Real-IP $remote_addr` und
`X-Forwarded-For` (`nginx.docker.conf:17-18,27-28,36-37`;
`tst-server-config/frontend-nginx.conf:35-36`; `backend-nginx.conf:35-36`). Das Backend
liest `X-Real-IP` für den Rate-Limit-Schlüssel (`utils/client_identity.py:47`), das BFF
wertet `X-Forwarded-*` aus (`BFF/Program.cs`, `UseForwardedHeaders()`).

**Neu: Rotation in beiden Compose-Dateien im Repo.** Jeder Dienst hat jetzt einen
`logging:`-Block mit `json-file`, `max-size` und `max-file: 3` —
`docker-compose.dev.yml` 20 MB je Datei (`:16-20,47-51,76-80,123-127`),
`docker-compose.tst.yml` 10 MB (`:5-9,28-32,52-56,82-86,110-114`). Das begrenzt den
Plattenverbrauch, ist aber **keine Aufbewahrungsfrist**: wie lange eine Zeile überlebt,
hängt am Durchsatz, nicht an einem Datum.

**Und es gilt nicht für Produktion.** Prod und tst werden über SaltStack ausgerollt, mit
einer Compose-Datei aus einem anderen Repository; die Rotation aus diesem Repo greift dort
nicht. Nach Auskunft des Maintainers ist sie in Salt **nicht** umgesetzt. Für Produktion
gilt damit der Docker-Default `json-file` **ohne Begrenzung**, bzw. was der Host
voreinstellt.

**Wirksame Löschfrist für Logs: im Repo keine, in Produktion nicht begrenzt.**
Alles Weitere: Teil 4, Frage 4-E.

---

## 1.11 Browser-seitige Speicherung

Erhebungsmethode: Grep über `fe/` nach `localStorage`, `sessionStorage`, `document.cookie`
(Anhang B, M-6). `document.cookie` kommt **nicht** vor — die App setzt selbst keine Cookies.

### Cookies

| Name | Gesetzt von | Inhalt | Flags | Lebensdauer |
|------|-------------|--------|-------|-------------|
| `ContentGruenAuthCookie` (Keycloak-Modus) | `BFF/Program.cs:59` | ASP.NET-Cookie-Auth-Ticket, DataProtection-verschlüsselt; enthält **alle Keycloak-Claims** (`sub`, `email`, Name — Scopes `openid`,`profile`,`email`, `Program.cs:82-84`) **plus die Tokens**, da `options.SaveTokens = true` (`:81`) | `HttpOnly` (`:62`), `Secure = Always` (`:61`), `SameSite = None` (`:60`) | **8 Stunden, gleitend** — `ExpireTimeSpan = TimeSpan.FromHours(8)`, `SlidingExpiration = true` (`Program.cs:71-72`) |
| `ContentGruenAuthCookie` (Managed-Modus) | `BFF/Program.cs:147` | Claims `NameIdentifier`, `Name`, `name`, `Email`, `sub`, `auth_method`, `user_id`, ggf. `Role=admin`/`isAdmin` (`AuthController.cs:91-104`) | `HttpOnly` (`:150`), `SecurePolicy = SameAsRequest` (`:149` — **über http also ohne `Secure`**), `SameSite = Lax` (`:148`) | **8 Stunden**, persistent (`AuthController.cs:108-111`) |
| dito, Dummy-Login (**nur Dev**) | `Program.cs:147` | Claims `name`, `GivenName`, `Surname`, `NameIdentifier=test-user-id-1` | wie oben | **1 Stunde**, persistent (`Program.cs:560-561`) |
| OIDC-Korrelations-/Nonce-Cookies | ASP.NET-OIDC-Handler | Flow-State | Framework-Default `SameSite=None`, `Secure` abhängig vom weitergereichten Schema | Sekunden bis Minuten |

> **Erledigt gegenüber der Erstanalyse:** Der Keycloak-Zweig setzte weder `ExpireTimeSpan`
> noch `SlidingExpiration`; es galt der Framework-Default von 14 Tagen, und die Aufnahme
> musste ihn als **UNSICHER** markieren, weil er nicht im Repo stand. PR #32 setzt
> beides explizit. Beide Produktions-Anmeldewege haben damit dieselbe Laufzeit, und die
> Datenschutzerklärung kann eine Zahl nennen, die im Code steht. Formulierung im Text:
> **„8 Stunden ab der letzten Nutzung"** — gleitend, nicht absolut.

Ein **Schlüsselring** liegt unter `/keys` (`Program.cs`, `SetApplicationName("contentgruen-bff")`).
Ohne gemountetes Volume entwertet jeder Container-Neustart alle bestehenden Cookies.

### localStorage — überlebt das Schließen des Browsers

| Schlüssel | Inhalt | Gesetzt in | Lebensdauer |
|-----------|--------|------------|-------------|
| `gutgesagt_session_id` | UUID v4, pseudonyme Gerätekennung | `fe/app/services/session.service.ts:95` | **30 Tage**, danach wird beim nächsten Lesen eine neue vergeben (`:17,58-83`) |
| `gutgesagt_session_id_created_at` | Zeitstempel der Vergabe, Epoch-ms | `session.service.ts:96` | wie oben |
| `gutgesagt-metrics-seen` | `"true"`, ob das Metrik-Panel schon gesehen wurde | `fe/app/metrics/metrics.component.ts:35,41` | unbegrenzt |

Wohin die Session-ID geht: als Header `X-Session-Id` bei jeder Suche
(`search.service.ts:41`) und bei jeder Meldung (`moderation.service.ts`), im Body beim
Nutzungs-Tracking (`usage-tracking.service.ts`). Das BFF reicht den Header unverändert
durch (`IdentityHeaderTransform.cs:93-99`). Gespeichert wird er in
`usage_events.session_id` (1.2) und `content_reports.reported_by_session_id` (1.4); in
`search_events` fließt er nur noch in den Tagespseudonym-Hash ein (1.3). Auf dem Meldeweg
wird er vorher als UUID validiert und andernfalls verworfen
(`utils/client_identity.py:88-116`).

**Befund B-1 — ERLEDIGT.** Die Kennung wurde bisher nur beim Abmelden neu vergeben, und für
`clearSessionId()`/`regenerateSessionId()` fand sich kein Aufrufer; wer sich nie abmeldete,
behielt sie unbegrenzt. PR #32 prüft beim Lesen das Alter (`session.service.ts:76-83`) und
vergibt nach 30 Tagen neu. Bestehende Kennungen haben keinen Zeitstempel und gelten
deshalb als abgelaufen. Die zweite, eigenständige Implementierung in `search.service.ts`
ist entfallen — der Dienst injiziert jetzt den `SessionService` (`search.service.ts:9,22,41`).

**Befund B-2 — ERLEDIGT.** Erzeugt wird sie mit `crypto.randomUUID()`, mit einem Fallback
über `crypto.getRandomValues()` für nicht-sichere Kontexte
(`session.service.ts:113-137`) — nicht mehr mit `Math.random()`.

**Was bleibt:** Die Kennung ist innerhalb ihrer 30 Tage ein stabiler, geräteweiter
Identifikator, der anonyme und angemeldete Nutzung desselben Browsers verbindet. In
`content_reports` stehen `reported_by_user_id` und `reported_by_session_id` nebeneinander
(1.4) — das ist die einzige Stelle im System, an der eine Session-ID einer Person zugeordnet
werden kann, und `docs/LOESCHKONZEPT.md` baut den Löschlauf ausdrücklich darauf auf.
**Für die Datenschutzerklärung heißt das: „pseudonym", nicht „anonym".**

### sessionStorage — wird beim Schließen des Tabs verworfen

| Schlüssel | Inhalt | Gesetzt in |
|-----------|--------|------------|
| `profilePicture` | Pfad des gewählten Avatars (`/avatars/*.svg`, lokal ausgeliefert) | `fe/app/app.component.ts:244` |
| `anonymousAvatar` | Pfad des Anonym-Avatars | `app.component.ts:249,262`, `result-view.component.ts:314` |
| `userAvatar` | Pfad des Nutzer-Avatars | `result-view.component.ts:323` |
| `loginReturnUrl` | Ziel-URL nach dem Login | `login.component.ts:35,47`, `login-selector.component.ts:39,75` |

Alle vier ohne eigenen Personenbezug (die Avatare sind eine feste Liste lokaler
SVG-Dateien, nicht aus Nutzerdaten erzeugt — `app.component.ts:60-78`), aber sie sind
Endgerätespeicherung im Sinne des § 25 TDDDG.

---

## 1.12 Dateisystem und Backups

| Speicher | Inhalt | Beleg | Personenbezug |
|----------|--------|-------|---------------|
| `/metadata` (Volume `semantic_search_metadata`) | Seeding-Status: Dateinamen, Zähler, Zeitstempel, PID | `app/services/seeding/seeding_status.py:260-261,283-284`, `seeding_service.py:161-162`; Volume `docker-compose.tst.yml:70` | **nein** — Grep über `services/seeding/` nach Schreibpfaden zeigt nur Dateilisten und Fortschrittszähler |
| `/keys` | DataProtection-Schlüsselring | `BFF/Program.cs:314-316` | nein, aber sicherheitsrelevant |
| `/opt/contentgruen-backups/daily|weekly` | **vollständige Kopien** von Qdrant-Snapshot und PostgreSQL-Dump | `mvp/scripts/backup/backup.sh`; Host-Mount `docker-compose.tst.yml:45,72` | **ja — enthält alles aus 1.1–1.9** |
| `mvp/config/managed-users.json` | Konten: E-Mail, bcrypt-Hash, Anzeigename, UserId, `isAdmin` | **seit PR #29 nicht mehr im Git** (`.gitignore:19`); getrackt ist nur noch `managed-users.example.json` mit zwei Testkonten. Gemountet `docker-compose.tst.yml` (`./config:/config:ro`) | **ja**, sofern in der Zielumgebung echte Konten eingetragen sind — Teil 4, 4-D. Die beiden Beispielkonten (`test.user@example.com`, `admin@contentgruen.com`) und die historisch eingecheckte Datei bleiben in der Git-Historie |

**Backup-Aufbewahrung — die einzige zweite wirksame Frist im System:**
`mvp/scripts/backup/backup.sh:24-25` — `KEEP_DAILY=7`, `KEEP_WEEKLY=4`; Rotation
`:160-181`. Daraus folgt: personenbezogene Daten leben in Backups **bis zu 4 Wochen** über
ihre Löschung in der Datenbank hinaus. Ob und wann das Skript in Produktion läuft:
Teil 4, Frage 4-F.

---

# Teil 2 — Ausgehende Datenflüsse

Erhebungsmethode: Grep nach `httpx`, `requests.`, `aiohttp`, `urllib`, `AsyncOpenAI`,
`OpenAI(`, `Anthropic`, `fetch(` im Python-Backend; Grep nach `http(s)://` in allen
Frontend-Quellen; Durchsicht von `src/index.html`.

| # | Empfänger | Welche Daten | Codepfad | Drittland | Produktiv aktiv? |
|---|-----------|--------------|----------|-----------|------------------|
| ~~2-A~~ | ~~**api.dicebear.com** (Avatare)~~ | — | — | — | **nein, entfallen.** Die 26 fest verdrahteten `api.dicebear.com`-URLs sind durch 16 lokale SVG-Dateien (12 Profilbilder, 4 Anonym-Varianten) unter `mvp/frontend/contentgruen-frontend/public/avatars/` ersetzt, erzeugt von `scripts/generate-avatars.mjs`; referenziert als `/avatars/*.svg` (`fe/app/app.component.ts:61-78`, `fe/app/result-view/result-view.component.ts`). Damit geht beim Seitenaufruf **keine** IP mehr an Dicebear. Die Erstanalyse hatte das als den einzigen unbedingten Drittabruf geführt |
| 2-B | **beliebige Bild-Hosts** | IP + User-Agent des **Betrachters** gehen an den Host des jeweiligen Bildes | `<img [src]="result.image_result.image_url">` in `fe/app/image-result-item/image-result-item.component.html:41`; Wert stammt aus `domain/models/image.py:37`, vom Beitragenden frei eingegeben (`fe/app/add-image/add-image.component.html:34`) | abhängig vom eingetragenen Host — nicht vorhersagbar | **ja**, sobald ein Bildbeitrag im Suchergebnis erscheint. Suche ist öffentlich → betrifft auch nicht angemeldete Besucher |
| 2-C | **OpenAI** (`gpt-4o-mini`) | **Bild-URL** und ein fester deutscher Prompt. Nicht übermittelt: Nutzerkennung, Session-ID, IP. OpenAI ruft das Bild anschließend **selbst** beim Host ab | `app/services/vision/caption_suggestion_service.py:17,26-38`; Prompt `:6-10`; Client `AsyncOpenAI` `:2`. Zwei Auslöser: (a) `POST /api/v1/image/suggestCaption` (`app/api/v1/image.py:138-150`, angemeldet, rate-limited `middleware/rate_limit.py:39`), (b) Hintergrund-Worker für `PENDING_DESCRIPTION` (`services/vision/image_description_worker.py:37-39`, gestartet `app/main.py:119-122`) | **ja, USA** | **abhängig von `OPENAI_API_KEY` — siehe Befund V-1** |
| 2-D | **Keycloak** (Netzbegrünung) | Authorization-Code-Flow, Scopes `openid`, `profile`, `email`; zurück kommen `sub`, `email`, Name | `BFF/Program.cs:75-127`, Scopes `:82-84`, Callback `:85` | nein (EU, **UNSICHER** — Authority steht nicht im Repo, s. Teil 4) | **nur bei `USE_KEYCLOAK=true`**. Beide Compose-Dateien im Repo setzen `false` (`docker-compose.dev.yml:140,178`, `docker-compose.tst.yml:94,120`); Code-Default ist `true` (`Program.cs:19`) |
| 2-E | **Anthropic** (`claude-sonnet-4-5`) | Beitragstexte aus einer Korpusdatei | `mvp/scripts/manual/check_wirkung_baseline.py` (auf `fae44b4` unverändert vorhanden) | ja, USA | **nein — toter Pfad für die Anwendung.** Ein manuell auszuführendes Skript unter `scripts/manual/`, von keinem Anwendungscode importiert; `anthropic` steht **nicht** in `mvp/backend/semantic-search-service/requirements.txt` (dort nur `openai>=1.35.0`, Zeile 30) |
| 2-F | Qdrant-Snapshot-API | Vollständige Sammlung inkl. aller Payloads | `app/scripts/backup_qdrant.py:87`, `restore_qdrant.py:73` | nein — `localhost`/Docker-intern | ja, beim Backup |
| — | Google Fonts | — | vormals `index.html` | — | **nein, entfernt.** `src/index.html` (14 Zeilen) enthält keinen externen Link mehr; Schriften liegen in `public/fonts/` (11 Dateien), Einbindung `src/styles/fonts.css`. Grep nach `fonts.googleapis`/`fonts.gstatic` in `src/` und `public/`: nur ein historischer Kommentar `styles/fonts.css:4`. **Bestätigt D-N10 der Lückenliste** |
| — | Analyse-/Tracking-Dienste | — | — | — | **nicht gefunden.** Kein Matomo, kein Google Analytics, kein Sentry. Grep nach `http(s)://` über alle `*.ts`/`*.html`/`*.scss` in `fe/src` auf `fae44b4` liefert außer 2-B nur redaktionelle Links (netzbegruenung.de, contentgruen, qdrant.tech, ec.europa.eu) und Beispiel-URLs in Formularhinweisen (`example.com/bild.jpg`) |

**Damit ist 2-B der einzige verbliebene Abruf, den der Browser der Nutzenden an einen
Dritten richtet:** die Bild-URLs, die Beitragende selbst eintragen. Er lässt sich nicht
vorab benennen, weil der Host vom eingetragenen Link abhängt, und er trifft auch nicht
angemeldete Besucher, weil die Suche öffentlich ist. Für die Erklärung heißt das: Abschnitt
„Einbindung von Diensten Dritter" wird **nicht** ersatzlos gestrichen, aber er beschreibt
nur noch diesen einen Fall.

### Befund V-1 — der OpenAI-Pfad wird **beim Modulimport** festgelegt

`app/domain/content_registry.py:107-118`:

```python
ingestion=AiVisionDescription( … CaptionSuggestionService(api_key=_settings.openai_api_key or "", …) )
     if _settings.openai_api_key else DirectText(),
```

Der Ausdruck steht im Modulkörper, wird also **einmal beim Import** ausgewertet
(so auch der Kommentar `:110`: „The IIFE runs once at registry-import time").

Daraus folgt:
- **Ohne** `OPENAI_API_KEY` → `DirectText()` → es geht **nichts** an OpenAI, weder über
  `/suggestCaption` noch über den Worker.
- **Mit** Key → beide Pfade aktiv.
- Ein zur Laufzeit nachgereichter Key ändert nichts; ein Neustart ist nötig.

Der Key wird aus `OPENAI_API_KEY` **oder** `SEMANTIC_SEARCH_OPENAI_API_KEY` gelesen
(`app/core/config.py:114-119`, `AliasChoices`). Grep über alle `*.yml`/`*.yaml`/`*.env*` im
Repo nach `OPENAI`: **kein Treffer.** In Dev und Test ist der Pfad damit inaktiv.
Für Produktion: Teil 4, Frage 4-B.

**Neu seit PR #32:** An beiden Stellen, an denen jemand liest, der den Key setzen würde,
steht jetzt eine Warnung — am Feld selbst (`app/core/config.py:104-113`) und bei den
Umgebungsvariablen in `CLAUDE.md`. Inhalt: die Datenschutzerklärung geht davon aus, dass
dieser Transfer nicht stattfindet, und müsste vorher um einen Abschnitt zum
Drittlandtransfer (Art. 44 ff. DSGVO) erweitert werden; zusätzlich sind ein AV-Vertrag und
Garantien nach Art. 46 DSGVO nötig. `STATUS.md` behauptet den Nichtbetrieb nicht mehr als
Tatsache, sondern als Konfigurationsaussage mit Verweis auf diese Warnung.

Der Hintergrund-Worker läuft unverändert und wird beim Startup gestartet
(`app/main.py:105-123`); ob er etwas an OpenAI schickt, entscheidet allein die
Ingestion-Strategie aus dem Registry.

---

# Teil 3 — Widersprüche zwischen Code und den vorhandenen Rechtstexten

Geprüft gegen `fe/app/datenschutz/datenschutz.component.html` (240 Zeilen, auf `fae44b4`
unverändert) und `docs/RECHTSTEXTE_LUECKEN.md` (221 Zeilen, Stand 2026-08-19).

## 3.1 Der Datenschutztext behauptet etwas, das der Code nicht einhält

| # | Text sagt | Code sagt (Stand `fae44b4`) | Belege |
|---|-----------|------------------------------|--------|
| **W-1** | „Wir erheben lediglich **anonymisierte** Nutzungsstatistiken" | **Weiterhin unzutreffend, aber aus anderem Grund.** IP-Hash und User-Agent sind aus `usage_events` verschwunden, `user_id` ebenfalls. Geblieben ist `session_id` — eine bis zu 30 Tage stabile Gerätekennung, verknüpft mit Inhalt und Zeitstempel — und über `content_reports` gibt es eine Zeile, die genau diese Kennung neben einer Nutzerkennung führt. Das ist pseudonym, nicht anonym | Text `datenschutz.component.html:156-158` ⟷ `models.py:96` (`session_id`), `models.py:150-151` (`content_reports`), `fe/app/services/session.service.ts:17` |
| **W-2** | „Diese Website verwendet **keine Analyse-Tools von Drittanbietern**" (formal richtig) und Abschnitt 5 beschreibt Drittanbieter-Einbindung **abstrakt, ohne einen einzigen zu nennen** | **Nur noch ein realer Fall.** Dicebear ist entfallen (Teil 2, 2-A); es bleiben die von Beitragenden eingetragenen Bild-Hosts, die der Browser jedes Betrachters direkt anspricht | Text `:156-157` und `:164-177` ⟷ `fe/app/image-result-item/image-result-item.component.html:41` |
| **W-3** | „Sie können sich auf dieser Website **registrieren**" mit Erhebungsliste Benutzername/E-Mail/Passwort/Zeitpunkt | Es gibt keine Registrierungsroute. Zugänge werden manuell in `managed-users.json` angelegt oder kommen über Keycloak | Text `:126-140` ⟷ `fe/app/app.routes.ts` (keine Register-Route), `mvp/config/managed-users.example.json`. Deckungsgleich mit Lückenliste X1 |
| **W-4** | „Daten, die Sie in ein **Kontaktformular** eingeben" | Kein Kontaktformular im Frontend | Text `:26-27` ⟷ Lückenliste X2, von mir nicht widerlegt |
| **W-5** | Cookie-Abschnitt kennt nur „Sitzungscookies" und „Authentifizierungscookies" | Zusätzlich **drei localStorage-Schlüssel** und **vier sessionStorage-Schlüssel** | Text `:93-106` ⟷ 1.11 dieses Berichts. Aktuelle Namen: `gutgesagt_session_id`, `gutgesagt_session_id_created_at`, `gutgesagt-metrics-seen` |
| **W-6** | „Authentifizierungscookies … für die **Dauer Ihrer Sitzung**" | Persistente Cookies mit fester Lebensdauer: **8 h gleitend in beiden Produktionswegen** (Keycloak und Managed), 1 h im Dummy-Modus. Sie überleben das Schließen des Browsers — `IsPersistent = true`. Die Zahl steht jetzt im Code und ist im Text nennbar | Text `:105` ⟷ `BFF/Program.cs:71-72`, `BFF/Controllers/AuthController.cs:108-111` |
| **W-7** | „Kommentar- und Beitragsfunktion … werden neben Ihrem Kommentar auch Zeitpunkt und **Nutzername** gespeichert" | **Unverändert.** Gespeichert werden zusätzlich `last_modified_by`, `authors[]` und die **vollständige `edit_history[]`** mit Editor und Zeitstempel je Änderung — und all das ist für **nicht angemeldete** Besucher über die öffentliche Suche abrufbar und sichtbar gerendert | Text `:142-147` ⟷ `app/domain/models/base_content.py:87-90`, `app/dtos/search.py:46,58,70,82`, `fe/app/commentary-result-item/commentary-result-item.component.html:213` und die drei Parallelstellen. Die Lückenliste (D-N3) lässt die Sichtbarkeitsfrage offen — **der Code beantwortet sie: öffentlich** |
| **W-8** | Text nennt Server-Log-Felder (Browsertyp, OS, Referrer, Hostname, Uhrzeit, IP) und stellt fest: „Eine **Zusammenführung** dieser Daten mit anderen Datenquellen wird nicht vorgenommen" | **Deutlich entschärft.** Suchtexte, E-Mail-Adressen und Session-IDs stehen nicht mehr im Anwendungslog; Nutzerkennungen nur noch als 8-stelliges Pseudonym. Es bleibt: derselbe Logstream trägt die nginx-Zugriffe mit voller IP und die Anwendungszeilen mit Pseudonym, mit denselben Zeitstempeln. Als Restrisiko benennbar, nicht mehr als offener Widerspruch | Text `:113-122` ⟷ 1.10 dieses Berichts |
| **W-9** | Rechte-Abschnitt sagt Auskunft, Berichtigung, **Löschung**, Einschränkung, Übertragbarkeit zu | **Unverändert: es gibt keinen Codepfad, der die Daten einer Person findet oder löscht.** Neu ist `docs/LOESCHKONZEPT.md` — eine Handprozedur aus SQL- und Qdrant-Kommandos, die das Dokument selbst als „Vorsorge, keine erprobte Prozedur" bezeichnet und die nie an echten Daten gelaufen ist. Löschen kann per Code weiterhin nur: die Moderation einen einzelnen Inhalt, und eine Person ihre eigene Stimme | Text `:196-212` ⟷ `docs/LOESCHKONZEPT.md:3-8`, Grep über alle DELETE-Pfade (Anhang B, M-4) |
| **W-10** | „Diese Seite nutzt … eine SSL- bzw. TLS-Verschlüsselung" | Trifft für Produktion zu (Reverse Proxy). Im BFF ist der Cookie im Managed-Modus auf `SecurePolicy = SameAsRequest` gesetzt (`Program.cs:149`) — über http ginge er ohne `Secure`-Flag hinaus. Praktisch nur im Dev-Betrieb relevant | Text `:218-224` ⟷ `BFF/Program.cs:149` |
| **W-11** | *(neu)* Der Text nennt **keine** Speicherdauer, **keine** Rechtsgrundlage außer für Server-Logs und Dritt-Inhalte, **keinen** Verantwortlichen (Platzhalter), **kein** Widerspruchsrecht nach Art. 21 und **keine** Empfänger | Alles davon ist Pflichtangabe nach Art. 13 DSGVO | Lückenliste D1–D12, D-M1 bis D-M8 |

## 3.2 Korrekturen und Ergänzungen zu `docs/RECHTSTEXTE_LUECKEN.md`

Die Lückenliste ist überwiegend präzise. Sechs Punkte muss sie fortschreiben:

| # | Lückenliste sagt | Tatsächlicher Stand auf `fae44b4` | Beleg |
|---|------------------|-----------------------------------|-------|
| **L-1** | X4/D-N10: nach dem Wegfall von Google Fonts bleibe „**kein** realer Anwendungsfall übrig, der Abschnitt kann ersatzlos gestrichen werden" (`:107`, `:171`) | **Fast richtig — es bleibt einer.** Die Erstanalyse hatte hier zwei genannt (Dicebear und Bild-Hosts); Dicebear ist seither entfallen. Übrig bleiben die von Beitragenden eingetragenen Bild-Hosts, die der Browser jedes Betrachters direkt anspricht. Abschnitt 5 also **konkretisieren, nicht streichen** — auf genau diesen Fall | `fe/app/image-result-item/image-result-item.component.html:41`, `app/domain/models/image.py:37` |
| **L-2** | D-M1: Speicherdauer/Löschfristen „kommt im gesamten Dokument nicht vor … Suchverlauf: ___" (`:89`) | Teilweise beantwortbar: **`usage_events` = 90 Tage** (fest verdrahtet, nicht konfigurierbar, Befund E-3). **`search_events`, `content_reports`, `raw_inputs`, `votes`, Qdrant, `usage_tracking` = keine Frist.** Die Session-ID im Browser rotiert nach 30 Tagen. Backups halten alles zusätzlich bis zu 4 Wochen. Logs: in Produktion nicht begrenzt | `services/cleanup/usage_cleanup_service.py:172`, `repositories/usage_tracking_repository.py:274-276,291-296`, `fe/app/services/session.service.ts:17`, `scripts/backup/backup.sh:24-25` |
| **L-3** | D-N4: „Bei jedem Kopieren … wird festgehalten, **wer** welchen Beitrag wann genutzt hat" (`:121`) | **Überholt.** Die Spalten `user_id`, `ip_hash` und `user_agent` gibt es nicht mehr (PR #27). Festgehalten wird: welcher Inhalt, welche Art Ereignis, wann, aus welcher Geräteklasse und unter welcher Sitzungskennung. Also *welches Gerät*, nicht *welches Konto* und nicht *welche Adresse* | `models.py:83-105`, `migrations/2026-08-25-usage-events-datensparsamkeit.sql` |
| **L-4** | Der Fangkorb (`raw_inputs`) kommt **gar nicht** vor | Die Liste datiert auf 2026-08-19, der Fangkorb wurde am 2026-08-22 gemergt (PR #19). Fehlender D-N-Eintrag: Freitext + Fremd-URLs + `submitted_by`, ohne Löschfrist, für **alle** angemeldeten Nutzenden namentlich einsehbar | 1.5 dieses Berichts |
| **L-5** | *(neu)* X3 begründet die Aussage „nicht anonymisiert" mit `user_id`, `ip_hash` und `user_agent` in `usage_events` | Diese Begründung trägt nicht mehr — die drei Spalten sind weg. Die **Schlussfolgerung** bleibt trotzdem richtig, jetzt getragen von `session_id` allein (W-1). Die Zeile ist umzuschreiben, nicht zu streichen | `models.py:96` |
| **L-6** | *(neu)* Die Liste kennt vier Public-Endpoint-Listen und ein ungeschütztes `/api/v1/metrics/` | Beides erledigt: `BFF/Proxy/EndpointPolicy.cs` ist die einzige serverseitige Quelle, die Frontend-Liste beantwortet ausdrücklich eine andere Frage; von den Metriken ist nur noch `/getMetrics` anonym erreichbar, die übrigen sechs sind admin-only | `EndpointPolicy.cs:1-35`, `api/v1/metrics.py:192-343` |

Bestätigt und unverändert: **X1** (keine Registrierung), **X2** (kein Kontaktformular),
**D-N4b** (`search_events` pseudonymisiert wie beschrieben),
**D-N8** (Embeddings lokal — `SentenceTransformer` im eigenen Container, kein
ausgehender Aufruf; Teil 2 bestätigt das durch Ausschluss),
**D-N10** (Google Fonts entfernt; `src/index.html` ist auf `fae44b4` weiterhin frei von
externen Links, Schriften liegen in `public/fonts/`),
**Abschnitt 5** (keine Consent-Checkbox — Grep über `fe/app` nach
`mat-checkbox|consent|einwillig|zustimm|akzeptier|nutzungsbedingung` findet außerhalb der
Rechtstextseiten nur den Footer-Link).

---

# Teil 4 — Was im Repo nicht entscheidbar ist

Jede Frage so formuliert, dass ein Blick in den Salt-Pillar sie beantwortet: **Variable →
Dienst → Konsequenz je Wert.**

### 4-A · `SEMANTIC_SEARCH_ACTOR_HASH_SECRET`
**Dienst:** `contentgruen-semantic-search` · **Im Repo:** nirgends gesetzt
(`app/core/config.py:133`)

| Wert | Konsequenz |
|------|-----------|
| gesetzt (fester String) | Pseudonyme sind über Neustarts hinweg stabil; DAU-Zahl korrekt. Wer das Secret **und** eine Kennung kennt, kann prüfen, ob diese Person an einem bestimmten Tag gesucht hat → das Secret ist selbst schützenswert |
| nicht gesetzt | Zufälliges Secret pro Prozess (`services/search_tracking_service.py:25`). Datenschutzseitig günstiger (nach Neustart unumkehrbar), aber DAU-Zahl überhöht |

### 4-B · `OPENAI_API_KEY` bzw. `SEMANTIC_SEARCH_OPENAI_API_KEY`
**Dienst:** `contentgruen-semantic-search` · **Im Repo:** nirgends gesetzt
(`app/core/config.py:114-119`)

| Wert | Konsequenz |
|------|-----------|
| gesetzt | Bild-URLs gehen an OpenAI (USA) — **Drittlandtransfer**, sowohl synchron über `/suggestCaption` als auch über den Hintergrund-Worker. Erfordert Beschreibung in der Datenschutzerklärung, AV-Vertrag und Art.-46-Garantien |
| nicht gesetzt | `DirectText()` — kein Aufruf, nichts zu beschreiben (Befund V-1) |

*Achtung:* `STATUS.md:22` behauptet als Tatsache, es sei „no OpenAI key configured in
production". Die Lückenliste lässt dieselbe Frage offen (`:127`: „Aktiv in Prod? ☐ ja ☐ nein").
**Der Pillar entscheidet, nicht STATUS.md.**

### 4-C · `USE_KEYCLOAK`
**Dienst:** `contentgruen-bff` · **Im Repo:** `false` in beiden Compose-Dateien
(`docker-compose.dev.yml:140` BFF / `:178` Frontend, `docker-compose.tst.yml:94` BFF / `:120`
für tst); **Code-Default ist `true`** (`BFF/Program.cs:19`)

| Wert | Konsequenz |
|------|-----------|
| `true` | Anmeldung über Netzbegrünung-Keycloak. Claims `sub`, `email`, Name kommen ins Auth-Cookie, zusätzlich die Tokens (`SaveTokens = true`, `Program.cs:71`). Der Reverse-Proxy erhält eine Autorisierungspipeline (`Program.cs:426-460`). **Für die Erklärung:** IdP benennen, Verantwortlichkeitsabgrenzung/AVV klären |
| `false` | Managed Auth aus `managed-users.json` (E-Mail + bcrypt). Die früheren Nebenwirkungen sind mit PR #29 weg: E-Mail-Adressen stehen nicht mehr im Log (1.10.3), und der Auth-Gate gilt unabhängig von dieser Variablen (`Program.cs:466-486`). Für die Erklärung bleibt: ein weiterer Speicher mit E-Mail und Passwort-Hash, siehe 4-D |
| nicht gesetzt | wie `true` |

### 4-D · Inhalt der produktiven `managed-users.json`
**Dienst:** `contentgruen-bff`, Mount `./config:/config:ro` · **Im Repo:** seit PR #29 gar
nicht mehr — die Datei steht in `.gitignore:19`, getrackt ist nur
`managed-users.example.json` mit zwei Testkonten

Frage: liegen dort echte Personen (Name + E-Mail) — und wenn ja, wie viele und wie lange nach
Ende der Nutzung? Konsequenz: dann ist ein weiterer personenbezogener Speicher zu beschreiben,
inklusive Löschfrist, die es im Code nicht gibt.

### 4-E · Logging-Konfiguration des Docker-Hosts
**Dienst:** alle · **Im Repo:** seit PR #29 hat jeder Dienst in `docker-compose.dev.yml`
und `docker-compose.tst.yml` einen `logging:`-Block (`json-file`, `max-size` 20 MB bzw.
10 MB, `max-file: 3`). **Produktion und tst laufen jedoch über eine SaltStack-eigene
Compose-Datei aus einem anderen Repository; nach Auskunft des Maintainers ist die Rotation
dort nicht umgesetzt.**

Fragen: Welcher Log-Treiber setzt Salt? Werden Container-Logs zentral gesammelt (journald,
Loki, …)? Welche Rotation, welche Aufbewahrung — und wird die nginx-`access_log` des
Reverse Proxy mit ihren vollen IP-Adressen mitgeschnitten und wie lange gehalten?

Konsequenz: **das ist die Löschfrist für alles aus 1.10.** Der Inhalt ist seit PR #29
deutlich kleiner — keine Suchtexte, keine E-Mail-Adressen, Nutzerkennungen nur als
Pseudonym —, aber die nginx-Zugriffslogs mit voller Client-IP sind unverändert da.
Solange die Antwort fehlt, ist die einzig ehrliche Angabe in der Erklärung, dass die
Aufbewahrung nicht begrenzt ist und sich nach der Voreinstellung des Hosts richtet.
**Größte verbliebene Lücke in D-M1.**

### 4-F · Backup-Cron und Ablageort
**Dienst:** Host bzw. `contentgruen-postgres-app` · **Im Repo:**
`scripts/backup/backup.sh` mit `KEEP_DAILY=7`, `KEEP_WEEKLY=4` (`:24-25`)

Fragen: Läuft der Cron? Liegt `/opt/contentgruen-backups` auf derselben Maschine oder wird
ausgelagert (Offsite, S3)? Verschlüsselt? Konsequenz: Aufbewahrungsort und -dauer aller
personenbezogenen Daten; bei Auslagerung ein weiterer Empfänger mit AVV-Pflicht.

### 4-G · Keycloak-Realm, Issuer, Client-ID/-Secret
**Dienst:** `contentgruen-bff`, Konfigurationsabschnitt `Keycloak`
(`BFF/Program.cs:67-69,122,124`) · **Im Repo:** keine Werte

Fragen: Welche Authority-URL, welcher Realm, wer betreibt ihn? Konsequenz: Standort der
Verarbeitung, Verantwortlichkeitsabgrenzung bzw. AVV mit Netzbegrünung/Verdigado,
und welche Claims tatsächlich geliefert werden.

### 4-H · `SEMANTIC_SEARCH_ADMIN_USERS`
**Dienst:** `contentgruen-semantic-search` · **Im Repo:** nirgends gesetzt, Default `""`
(`app/core/config.py:123`)

| Wert | Konsequenz |
|------|-----------|
| gesetzt | Die Endpunkte `/api/v1/usage/users/{id}/usage-stats`, `/cleanup/status`, `/cleanup/run` sind für diese Kennungen erreichbar — **seit PR #29 tatsächlich**, weil die Dependency nun `X-User` liest (Befund E-1 erledigt). Wer dort steht, kann die Nutzungsstatistik zu einer beliebigen Kennung abrufen |
| leer/nicht gesetzt | `is_admin_user()` liefert immer `False` (`config.py:134`) → diese drei Endpunkte antworten konstant 403. **Das ist der Stand, den das Repo herstellt** |

Zu unterscheiden davon ist `require_admin` (`dependencies.py:233-249`), das den vom BFF aus
den Claims gesetzten Header `X-Is-Admin` prüft — davon hängen Moderationsposteingang und
die sechs Metrik-Endpunkte ab, und das funktioniert unabhängig von dieser Variablen.

### 4-I · Erreichbarkeit von Qdrant, PostgreSQL und der Semantic-Search-API
**Dienste:** `qdrant`, `postgres-app`, `contentgruen-semantic-search` · **Im Repo:**
Dev veröffentlicht 6333/6334, 5433 und 8000 (`docker-compose.dev.yml:24-26,59-60,86-87`);
Test veröffentlicht PostgreSQL auf `127.0.0.1:5432` (`docker-compose.tst.yml:41`) und
Semantic Search gar nicht (`:68`)

Fragen: Sind in Produktion Ports veröffentlicht? Ist Qdrant durch einen API-Key geschützt
(im Repo ist **keiner** konfiguriert)? Konsequenz: Wenn Port 8000 erreichbar ist, kann jeder
die Auth des BFF umgehen — inklusive `X-User-Id` selbst setzen (Befund E-1) und
`GET /api/v1/rawinput/getRawInputs` samt Einwerferkennungen abrufen.

### 4-J · PostgreSQL-Zugangsdaten
**Dienst:** `postgres-app` · **Im Repo:** Klartext `changeme`
(`docker-compose.tst.yml:38,63`; `docker-compose.dev.yml:57,91`; Default auch
`app/core/config.py:27`)

Frage: Wird in Produktion ein anderes Passwort gesetzt? Konsequenz: falls nicht, ist der
Speicher aus 1.1–1.8 mit einem im Repo öffentlich lesbaren Passwort erreichbar.

---

# Teil 5 — Die vorab genannten Punkte, geprüft

| Vorannahme | Ergebnis auf `fae44b4` |
|------------|------------------------|
| „`usage_events` enthält `user_id`, `session_id`, `ip_hash`, `user_agent`, verknüpft mit `content_id`" | **Traf für `95b565e` zu, für `fae44b4` nicht mehr.** Die Tabelle hat jetzt sechs Spalten (`models.py:85-96`): `id`, `content_id`, `event_type`, `timestamp`, `session_id`, `device_category`. `user_id`, `ip_hash` und `user_agent` sind mit PR #27 gefallen, Bestandswerte per `VACUUM FULL` physisch entfernt |
| „Eine Retention-Einstellung wird unter anderem Namen gelesen, deshalb greift immer der Fallback" | **Bestätigt, größer als vermutet, und weiterhin so:** nicht eine, sondern **alle vier** Cleanup-Einstellungen (`usage_cleanup_service.py:172,184,189,190` gegen `config.py:146-150`). **Wirksam: 90 Tage, täglich 02:00, nicht abschaltbar, über die Umgebung nicht änderbar** (Befund E-3, empirisch verifiziert) |
| „Für mehrere Tabellen existiert vermutlich gar keine Löschlogik" | **Bestätigt, unverändert.** Von 7 Tabellen hat **eine** eine wirksame Frist: `usage_events` (90 Tage). Ohne jede Löschung: `usage_tracking` (ausdrücklich „preserved forever", `usage_tracking_repository.py:274-276`), `search_events` (Löschcode vorhanden, **kein Aufrufer** — Befund S-3), `content_reports`, `raw_inputs`, `raw_input_content_links`, `votes`. Qdrant ebenso |
| „Fangkorb: wer wird als Einwerfer gespeichert, wer sieht das?" | **Unverändert.** Gespeichert wird der `X-User`-Wert = Keycloak-`sub` bzw. `user-00x`; `"anonymous"` → `NULL` (`api/v1/raw_input.py:30-40,55`). **Gesehen wird es von jeder angemeldeten Person** — `getRawInputs` liefert bewusst alle Einwürfe, das DTO trägt `submitted_by` (`dtos/raw_input.py:97`), das Frontend zeigt es als Tabellenspalte (`raw-input-list.component.ts:52`). Neu ist nur, dass die Route jetzt in **beiden** Betriebsarten Anmeldung verlangt |
| „Suchereignisse sollen pseudonymisiert sein (rotierender Actor-Hash) — stimmt das, kommt das Secret aus der Umgebung, was passiert ohne?" | **Implementiert wie beschrieben** (Befund S-1), unverändert: HMAC-SHA256 über `<Kennung>\|<UTC-Datum>`, Suchtext wird gar nicht erst übergeben. Das Secret **kann** aus `SEMANTIC_SEARCH_ACTOR_HASH_SECRET` kommen, ist im Repo aber **nirgends gesetzt**. Ohne Secret: zufälliger 32-Byte-Schlüssel pro Prozess → datenschutzseitig stärker, statistisch unbrauchbar (Befund S-2). Neu: die Metrik-Endpunkte, die darauf lesen, sind admin-only |
| „Bildbeschriftung per KI: aktiv, und wovon abhängig?" | **Unverändert.** Hängt **allein** an `OPENAI_API_KEY`/`SEMANTIC_SEARCH_OPENAI_API_KEY`, ausgewertet **einmal beim Modulimport** (`content_registry.py:107-127`, Befund V-1). Im Repo nirgends gesetzt → in Dev und Test **inaktiv**. Übermittelt wird die **Bild-URL** plus fester Prompt, **keine** Nutzerkennung. Neu ist die Warnung an der Konfigurationsstelle (PR #32). Produktion: Teil 4, 4-B |
| *(neu)* „Nutzungsprotokollierung ist anonym" | **Nein, pseudonym.** `session_id` bleibt eine bis zu 30 Tage stabile Gerätekennung; `content_reports` führt sie neben einer Nutzerkennung. Siehe W-1 |
| *(neu)* „Server-Logs enthalten Suchtexte und E-Mail-Adressen" | **Nicht mehr.** Beides ist mit PR #29 entfernt; geblieben sind die nginx-Zugriffslogs mit voller IP und eine einzelne Suchtext-Ausgabe im Fehlerzweig (`statement_repository.py:173`) |

---

# Anhang A — Sicherheitsbefunde ohne Datenschutzbezug

Aufgefallen während der Erstanalyse. PR #29 hat den größten Teil davon aufgegriffen; der
Stand ist hier je Befund vermerkt.

| # | Befund | Stand auf `fae44b4` |
|---|--------|---------------------|
| **A-1** | Bei `USE_KEYCLOAK=false` wurde der Reverse Proxy **ohne Autorisierungspipeline** gemappt — kein API-Pfad war am Proxy geschützt | **ERLEDIGT.** Der Auth-Gate läuft als eigene Middleware in der Proxy-Pipeline und gilt in beiden Betriebsarten (`BFF/Program.cs:466-486`) |
| **A-2** | `IdentityHeaderTransform` entfernte `X-User` und `X-Is-Admin`, **nicht** `X-User-Id`; ein Client konnte sich per Header eine fremde Identität geben | **ERLEDIGT.** `X-User-Id` steht in der Entfernungsliste (`IdentityHeaderTransform.cs:43`), und die Dependency liest `X-User` (`dependencies.py:217`) |
| **A-3** | Vier **verschiedene** Public-Endpoint-Listen mit drei Bedeutungen und abweichenden Einträgen | **ERLEDIGT.** `BFF/Proxy/EndpointPolicy.cs` ist die einzige serverseitige Quelle und speist Gate und Transform; `mvp/shared/PublicEndpoints.cs` (toter Code) ist gelöscht. Die Frontend-Liste bleibt bewusst eigenständig — sie beantwortet die Frage „Redirect auf /login ja/nein" |
| **A-4** | `api/v1/seeding.py` hat auf keinem seiner 8 Endpunkte eine Auth-Dependency, obwohl vier Docstrings „allows administrators" behaupten | **Am Rand geschlossen, im Router offen.** `/api/v1/seeding` steht in `EndpointPolicy.Blocked` und wird vor Routing mit 404 abgewiesen (`EndpointPolicy.cs:56-59`, `Program.cs:394-407`). Der Router selbst hat weiterhin keine Dependency; wer Port 8000 direkt erreicht, erreicht ihn (Teil 4, 4-I) |
| **A-5** | Session-IDs wurden mit `Math.random()` erzeugt | **ERLEDIGT.** `crypto.randomUUID()` mit `crypto.getRandomValues`-Fallback (`session.service.ts:113-137`) |
| **A-6** | Der Debug-Router `api/v1/test.py` war unbedingt gemountet und gab über `/headers` alle eingehenden Header inklusive Cookie auf stdout aus | **ERLEDIGT.** Datei gelöscht (485 Zeilen), Pfad zusätzlich am Rand gesperrt |
| **A-7** | `mvp/config/managed-users.json` war im Git getrackt und enthielt zwei bcrypt-Hashes, einer für ein Konto mit `isAdmin: true` | **Teilweise.** Die Datei steht in `.gitignore:19`; getrackt ist `managed-users.example.json` mit denselben zwei Beispielkonten. Die Hashes und die frühere Datei bleiben in der Git-Historie |
| **A-8** | PostgreSQL-Passwort `changeme` im Klartext in beiden Compose-Dateien und als Default in `core/config.py` | **UNVERÄNDERT** (`docker-compose.dev.yml:57,91`, `docker-compose.tst.yml:38,63`, `core/config.py:27`). Für Produktion: Teil 4, 4-J |
| **A-9** | Die Metrik-Endpunkte hatten **keine** Auth-Dependency und `/api/v1/metrics/` stand in der BFF-Public-Liste — DAU-Zahlen und „helpful rate" weltweit lesbar | **ERLEDIGT.** Sechs der sieben Endpunkte verlangen `require_admin` (`api/v1/metrics.py:192-343`); am BFF ist nur noch `/getMetrics` anonym (`EndpointPolicy.cs:30-34`) |
| **A-10** | `POST /api/v1/post/addPost` und `/api/v1/image/addImage` unterliegen **keinem** Rate-Limit | **UNVERÄNDERT.** Die Liste in `middleware/rate_limit.py:31-44` umfasst sechs andere Schreibpfade; `/addRawInput` ist neu dazugekommen, `addPost` und `addImage` fehlen weiterhin |

---

# Anhang B — Suchstrategien, und was ich übersehen haben könnte

## Verwendete Methoden

| # | Methode | Womit |
|---|---------|-------|
| M-1 | Alle SQL-Dateien im Repo | `find . -name "*.sql"` → 3 Treffer, alle gelesen |
| M-2 | Zur Laufzeit erzeugte Tabellen | `grep -rn "CREATE TABLE\|CREATE INDEX\|CREATE OR REPLACE" --include="*.py" --include="*.cs"` → 4 Treffer, alle in `vote_repository.py` |
| M-3 | ORM-Tabellen | vollständiges Lesen von `app/infrastructure/database/models.py` (254 Zeilen) — 6 Klassen mit `__tablename__` |
| M-4 | Löschpfade | `grep -rn "\.delete(\|DELETE FROM\|delete_by\|def delete" --include="*.py" repositories/ services/ api/`, dann Rückverfolgung jedes Treffers auf Aufrufer |
| M-5 | stdout-Ausgaben Python | `grep -rn "^\s*print("` über `api/ services/ repositories/ core/ domain/ middleware/ auth/`; zusätzlich gezielte Greps nach `logger.*` mit `{user_id}`, `{x_user}`, `{validated_user}`, `session`, `query_text`, `f"…query` |
| M-6 | Browser-Speicher | `grep -rn "localStorage\|sessionStorage\|document.cookie" fe/src` (ohne `.spec.ts`) |
| M-7 | Ausgehende Verbindungen | `grep -rn "httpx\|requests\.\|aiohttp\|urllib\|AsyncOpenAI\|OpenAI(\|Anthropic\|fetch("` im Backend; `grep -rno "https\?://…"` über alle `*.ts`/`*.html`/`*.scss` im Frontend; vollständiges Lesen von `src/index.html` |
| M-8 | Cookies | vollständiges Lesen von `BFF/Program.cs` (628 Zeilen) und `BFF/Controllers/AuthController.cs` (145 Zeilen) |
| M-9 | Qdrant-Payload | Rückverfolgung von `upsert_batch` (`qdrant_embeddings_manager.py:294-345`) über `base_repository.py:199-239` bis zu den Pydantic-Modellen; alle 6 Typmodelle durchgesehen |
| M-10 | Header-Bindung | empirischer Gegentest mit FastAPI-`TestClient` gegen eine Nachbildung von `get_current_user_optional` |
| M-11 | Retention-Bug | empirischer Gegentest mit `pydantic_settings` und identischer Feld-/Prefix-Konstellation |
| M-12 | Auth-Stufe je Endpunkt | `grep -n "^@router\|Depends(\|Header("` je Router-Datei, abgeglichen mit den vier Public-Listen und den Frontend-Guards in `app.routes.ts` |
| M-13 | Dateisystem-Persistenz | `grep -rn "open(.*'w'\|json.dump\|\.write("` über `services/ repositories/ core/ api/` |
| M-14 | Fundstellen-Abgleich | Skript über das Dokument selbst: jede Angabe der Form `` `datei:zeile` `` (und jede Fortsetzung `` `:zeile` ``) auflösen, Datei öffnen, Zeile lesen und gegen die Behauptung der Zeile halten. Deckt Verschiebungen und Verwechslungen auf, nicht aber eine Fundstelle, die auf die falsche, zufällig passende Stelle zeigt |

## Was diese Methoden nicht erfassen — mögliche blinde Flecken

1. **Bestandsdaten.** Ich habe kein laufendes System angesehen, nur Code. Ob in einer
   produktiven Datenbank Spalten mit Werten stehen, die der aktuelle Code nicht mehr
   schreibt (z. B. `usage_events.user_id` aus der Zeit vor Befund E-1, oder Reste in
   `raw_input_content_links`), sagt der Code nicht. **Ein `\d+` und ein paar
   `SELECT count(*) WHERE … IS NOT NULL` auf der Produktivdatenbank würden das klären.**

2. **Qdrant-Payloads aus dem Seeding.** Die Seed-Daten unter `mvp/data/seed/v1.0/` habe ich
   nicht inhaltlich durchgesehen. Sie tragen laut `app/core/config.py:73`
   `initial_data_author = "ContentGruen Team"`, könnten aber in Freitexten Namen realer
   Personen enthalten (politische Zitate).

3. **Bibliotheken.** Ich habe `requirements.txt` und `package.json` nicht auf Transitiv-
   Abhängigkeiten geprüft, die selbst nach außen telefonieren. Für das Frontend spricht
   das Fehlen jeglicher CDN-Referenz in `index.html` dagegen; belegt ist es nicht.

4. **SaltStack.** Alles, was der Pillar setzt — vier `USE_KEYCLOAK`/`OPENAI`/`ACTOR_HASH`/
   `ADMIN_USERS`-Fragen, Logging, Backup-Cron, Portfreigaben. Vollständig in Teil 4.

5. **Der Keycloak-Realm selbst.** Welche Claims Netzbegrünung tatsächlich liefert und wie
   lange dort Anmeldedaten liegen, ist ein fremdes System.

6. **Nur INFO und darunter geprüft.** Ich habe die Log-Sweeps auf Ausgaben mit erkennbaren
   Identifikatoren gefiltert. Ein `exc_info=True` in einem Fehlerpfad kann Stack-Frames mit
   lokalen Variablen ausgeben, in denen Nutzerdaten stehen — das habe ich nicht Frame für
   Frame durchgespielt.

7. **Zwei Header-Aliasse habe ich nicht erschöpfend geprüft.** Ich habe `X-User`,
   `X-User-Id`, `X-Is-Admin` und `X-Session-Id` verfolgt. Ob weitere `Header(...)`-Parameter
   in Routern still auf nie gesendete Namen zeigen (wie bei Befund E-1), habe ich
   stichprobenartig, nicht systematisch geprüft. **Ein vollständiger Abgleich aller
   `Header(`-Deklarationen im Backend gegen die vom BFF gesetzten Namen wäre die nächste
   Prüfung.**

8. **Die Fortschreibung auf `fae44b4` ist keine zweite Vollerhebung.** Sie geht vom Diff
   `95b565e..fae44b4` aus und prüft gezielt die Stellen nach, an denen die Erstanalyse
   etwas behauptet hat. Ein Speicher oder ein ausgehender Aufruf, den die Erstanalyse
   übersehen hatte und der seither unverändert geblieben ist, fällt dabei nicht auf. Die
   Greps zu Logausgaben, `print()`, Browser-Speicher, externen URLs und Löschpfaden habe
   ich vollständig wiederholt; die Payload- und Endpunkt-Durchsicht (M-9, M-12) nicht.
   Der Fundstellen-Abgleich (M-14) prüft, ob eine Zeilenangabe auf die behauptete Stelle
   zeigt — er prüft nicht, ob an einer *nicht* zitierten Stelle etwas steht, das der
   Aufnahme widerspricht.

---

*Ende der Bestandsaufnahme. Am Code wurde für diese Aufnahme nichts geändert.*
