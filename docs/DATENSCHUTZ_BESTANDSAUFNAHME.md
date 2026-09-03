# Datenschutz-Bestandsaufnahme (Art. 13 DSGVO)

> **Zweck:** belegte Faktenbasis für die Datenschutzerklärung. Keine juristische Bewertung,
> keine Empfehlung — nur, was im Code steht, mit Fundstelle.
>
> **Stand:** Commit `95b565e0d37d5ee9d0a20249f2031a7e1b9851e4` (`main`, sauberer Arbeitsbaum)
> **Analysedatum:** 2026-08-25
> **Nicht committet.** Am Code wurde nichts geändert.

## Lesehilfe

- **KONFIGURIERT** = der Wert steht in einer Settings-/Config-Klasse.
  **WIRKSAM** = ein Codepfad liest ihn tatsächlich. Wo beides auseinanderfällt, steht es dabei.
- **UNSICHER** markiert jede Stelle, an der ich mir nicht sicher bin, mit Begründung.
- **NICHT IM REPO ENTSCHEIDBAR** = hängt an Deployment-Konfiguration (SaltStack-Pillar), die
  außerhalb dieses Repos liegt. Alle diese Punkte sind in **Teil 4** gebündelt.
- Zeilennummern beziehen sich auf den oben genannten Commit.

Pfadabkürzungen in den Tabellen:

| Kürzel | Vollpfad |
|--------|----------|
| `app/` | `mvp/backend/semantic-search-service/app/` |
| `BFF/` | `mvp/backend/BFF/` |
| `fe/` | `mvp/frontend/contentgruen-frontend/src/` |

---

# Teil 1 — Datenspeicher

## 1.0 Wie das PostgreSQL-Schema entsteht (vier Mechanismen)

Die Vorannahme „`init.sql` ist nicht vollständig" trifft zu. Gefunden habe ich **vier**
Mechanismen, die Tabellen anlegen:

| # | Mechanismus | Beleg | Legt an |
|---|-------------|-------|---------|
| 1 | `init.sql`, in das Postgres-Image gebacken, läuft nur bei leerem Datenverzeichnis | `mvp/backend/postgres-app/init.sql` (74 Zeilen) | `usage_tracking`, `usage_events`, View `user_usage_statistics`, 6 Indizes, 1 Trigger |
| 2 | SQLAlchemy `Base.metadata.create_all` beim ersten DB-Zugriff | `app/infrastructure/database/connection.py:48`, aufgerufen aus `:87` | **alle 6** ORM-Tabellen: `usage_tracking`, `usage_events`, `search_events`, `content_reports`, `raw_inputs`, `raw_input_content_links` |
| 3 | Rohes DDL zur Laufzeit | `app/repositories/vote_repository.py:20-40`, aufgerufen aus `app/services/voting_service.py:18` | `votes` + 3 Indizes |
| 4 | Handmigrationen für Bestandsumgebungen | `mvp/backend/postgres-app/migrations/2026-08-19-rohinput-fangkorb.sql`, `…-search-events-pseudonymisieren.sql` | dieselben Tabellen wie (2), plus `TRUNCATE`/`DROP COLUMN` auf `search_events` |

**Konsequenz:** `init.sql` deckt **2 von 7** Tabellen ab. Wer das Schema aus `init.sql` liest,
sieht `search_events`, `content_reports`, `raw_inputs`, `raw_input_content_links` und `votes`
nicht.

**Gefundene Tabellen: 7** (+ 1 View). Suchmethoden dafür in Anhang B.

---

## 1.1 PostgreSQL — `usage_tracking`

Aggregatzähler pro Inhalt, kein Personenbezug.

| Feld | Typ | Definiert in | Personenbezug | Wer schreibt | Wer kann lesen | Wirksame Löschfrist |
|------|-----|--------------|---------------|--------------|----------------|---------------------|
| `content_id` | UUID PK | `app/infrastructure/database/models.py:35`; `init.sql:11` | nein — Inhalts-ID | `app/repositories/usage_tracking_repository.py:64` | öffentlich über `GET /api/v1/usage/content/{id}` (`app/api/v1/usage.py:158`, in der BFF-Public-Liste `BFF/Proxy/IdentityHeaderTransform.cs:31`) | **keine** |
| `usage_count` | Integer | `models.py:36`; `init.sql:12` | nein | `models.py:54-62` (`increment_usage`) | dito | **keine** |
| `last_used` / `first_used` | Timestamptz | `models.py:37-38`; `init.sql:13-14` | nein | `models.py:60-62` | dito | **keine** |
| `created_at` / `updated_at` | Timestamptz | `models.py:39-47`; `init.sql:15-16` | nein | Server-Default + Trigger `init.sql:66-69` | dito | **keine** |

**Löschfrist explizit ausgeschlossen:** `app/repositories/usage_tracking_repository.py:278-280` —
„usage_tracking aggregate counters are **preserved forever**". Der einzige Cleanup-Pfad rührt
diese Tabelle nicht an.

---

## 1.2 PostgreSQL — `usage_events`  ⚠️ der personenbezogenste Speicher

Ein Ereignis pro Kopiervorgang eines Inhalts.

| Feld | Typ | Definiert in | Personenbezug | Wer schreibt (Codepfad) | Wer kann lesen | Wirksame Löschfrist |
|------|-----|--------------|---------------|--------------------------|----------------|---------------------|
| `id` | BigInteger PK | `models.py:70`; `init.sql:21` | nein | ORM | s.u. | 90 Tage |
| `content_id` | UUID FK→`usage_tracking` | `models.py:71-75`; `init.sql:22` | nein (aber verknüpfend) | `usage_tracking_repository.py:77` | s.u. | 90 Tage |
| `user_id` | VARCHAR(255) | `models.py:76`; `init.sql:23` | **ja, wenn gefüllt** — Keycloak-`sub` bzw. `user-00x`; siehe Befund unten | `usage_tracking_repository.py:78` ← `services/usage_tracking_service.py:76` ← `api/v1/usage.py:129` (`current_user`) | s.u. | 90 Tage |
| `event_type` | VARCHAR(50), default `copy` | `models.py:77`; `init.sql:24` | nein | `usage_tracking_repository.py:79` | s.u. | 90 Tage |
| `timestamp` | Timestamptz | `models.py:78-80`; `init.sql:25` | nein für sich | Server-Default | s.u. | 90 Tage |
| `session_id` | VARCHAR(255) | `models.py:81`; `init.sql:26` | **pseudonym** — client-erzeugte UUID aus `localStorage`, unbefristet stabil (siehe 1.10) | `usage_tracking_repository.py:80` ← `api/v1/usage.py:130` ← Request-Body `session_id` | s.u. | 90 Tage |
| `ip_hash` | VARCHAR(64) | `models.py:82`; `init.sql:27` | **pseudonym** — SHA-256 **ohne Salt**, doppelt angewendet (Befund unten) | `usage_tracking_repository.py:71-73` ← `api/v1/usage.py:111-119,131` | s.u. | 90 Tage |
| `user_agent` | VARCHAR(500) | `models.py:83`; `init.sql:28` | **ja, mittelbar** — Browser/OS/Version, auf 500 Zeichen gekürzt | `usage_tracking_repository.py:82` ← `api/v1/usage.py:82,122-123,132` | s.u. | 90 Tage |

### Wer kann lesen

| Weg | Auth-Stufe | Beleg |
|-----|-----------|-------|
| `GET /api/v1/usage/content/{id}` (nur Zähler) | **öffentlich** | `api/v1/usage.py:158`; BFF-Public-Liste `IdentityHeaderTransform.cs:31` |
| `GET /api/v1/usage/trending` | **öffentlich** | `api/v1/usage.py:219`; `IdentityHeaderTransform.cs:32` |
| `GET /api/v1/usage/users/{user_id}/usage-stats` | Admin-Prüfung `settings.is_admin_user` — **wirkungslos, siehe unten** | `api/v1/usage.py:186-203` |
| `GET /api/v1/metrics/mvp-dashboard`, `/usage-trend`, `/helpful-rate` (aggregiert) | **öffentlich, gar keine Auth-Dependency** | `api/v1/metrics.py:143-144, 245-248, 283-286`; `IdentityHeaderTransform.cs:29` |
| View `user_usage_statistics` (JOIN über `user_id`) | nur direkter DB-Zugriff | `init.sql:33-46` |
| Backup-Dumps | Dateisystemzugriff | s. 1.11 |

### Befund E-1 — `user_id` wird über den Live-Pfad **nie** gefüllt (KONFIGURIERT ≠ WIRKSAM)

`api/v1/usage.py:83` bezieht `current_user` aus `Depends(get_current_user_optional)`.
`app/dependencies.py:210` deklariert dort den Parameter `x_user_id: Optional[str] = Header(None)`.
FastAPI leitet daraus den Headernamen **`X-User-Id`** ab (Unterstriche → Bindestriche).

Das BFF setzt aber **`X-User`** — `BFF/Proxy/IdentityHeaderTransform.cs:17`, gesetzt in `:53`
bzw. `:67`. Ein Header `X-User-Id` wird **nirgends im Repo** erzeugt: repo-weiter Grep über
`*.cs`, `*.ts`, `*.py`, `*.yml`, `*.conf` nach `x-user-id`/`x_user_id` liefert ausschließlich
`dependencies.py:210,213,216` (die Definition selbst) sowie `dependencies.py:220` und
`api/v1/moderation.py:78`, die beide `alias="X-User"` explizit setzen.

Empirisch nachgeprüft (FastAPI-`TestClient` gegen eine Nachbildung derselben Dependency):

```
mit Header X-User      ->  {'u': None}
mit Header X-User-Id   ->  {'u': 'alice'}
```

**Wirksam:** `usage_events.user_id` ist über den regulären Weg Frontend → BFF → Backend
immer `NULL`. Die Nutzungsprotokollierung läuft faktisch nur über `session_id`, `ip_hash`
und `user_agent`.

*Einschränkung (UNSICHER in eine Richtung):* Das gilt für den Weg über das BFF. Wer die
Semantic-Search-API direkt erreicht, kann `X-User-Id` selbst setzen und den Wert damit
beliebig befüllen — der Transform entfernt nur `X-User` und `X-Is-Admin`
(`IdentityHeaderTransform.cs:45-46`), nicht `X-User-Id`. Im Dev-Compose ist Port 8000
veröffentlicht (`mvp/docker-compose.dev.yml:65-66`); im Test-Compose nicht
(`docker-compose.tst.yml:47`: „No port mapping, only reachable internally via BFF"). Für
Produktion: Teil 4.

**Nebenwirkung derselben Ursache:** `settings.is_admin_user(current_user)` in
`api/v1/usage.py:200,255,285` bekommt dadurch immer `None` und liefert immer `False`
(`app/core/config.py:123`). Diese drei Endpunkte antworten also konstant 403 — die
Admin-Sicht auf `usage_events` ist über die API nicht erreichbar.

### Befund E-2 — `ip_hash` ist ungesalzen und wird doppelt gehasht

1. `api/v1/usage.py:112-114` bestimmt die Client-IP (bevorzugt erstes Element von `X-Forwarded-For`).
2. `api/v1/usage.py:117-119`: `ip_hash = sha256(client_ip)` — **kein Salt, kein Key**.
3. `api/v1/usage.py:131` übergibt diesen Hex-String als Parameter `ip_address=` weiter.
4. `app/repositories/usage_tracking_repository.py:71-73` hasht den empfangenen Wert **erneut**:
   `ip_hash = sha256(ip_address)`.

Gespeichert wird also `SHA256(hex(SHA256(ip)))`. Beide Stufen sind schlüssellos und
deterministisch; der IPv4-Raum ist vollständig durchrechenbar. Der Kommentar
`init.sql:27` („hashed IP for analytics **without privacy concerns**") und
`models.py:82` („Store hashed IP for privacy") beschreiben eine Schutzwirkung, die
ein ungesalzener Hash über einen erschöpfbaren Wertebereich nicht hat.

*Zum Vergleich:* `search_events.actor_hash` macht es anders — HMAC mit Secret plus
Tagesrotation (1.4).

### Befund E-3 — die 90 Tage sind ein Fallback, kein konfigurierter Wert

`app/core/config.py:136-139` definiert vier Einstellungen in Kleinschreibung
(Pydantic-Feldnamen, `env_prefix = "SEMANTIC_SEARCH_"`, `config.py:165`):

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
keine Wirkung — das ist auch für Teil 4 relevant: Die Frist ist **nicht** deployment-abhängig,
sie steht fest.

Der Scheduler läuft: `app/main.py:103` ruft `start_cleanup_scheduler()` beim Startup, plus
ein sofortiger Lauf beim Start (`usage_cleanup_service.py:98-99`).

Gelöscht wird ausschließlich aus `usage_events`
(`usage_tracking_repository.py:297-301`, Filter `timestamp < cutoff`).

---

## 1.3 PostgreSQL — `search_events`

| Feld | Typ | Definiert in | Personenbezug | Wer schreibt | Wer kann lesen | Wirksame Löschfrist |
|------|-----|--------------|---------------|--------------|----------------|---------------------|
| `id` | BigInteger PK | `models.py:110` | nein | ORM | s.u. | **keine** |
| `actor_hash` | VARCHAR(64), nullable | `models.py:111` | **pseudonym, tagesrotierend** — Details unten | `app/repositories/search_tracking_repository.py:44` ← `services/search_tracking_service.py:98-105` ← `api/v1/search.py:257-261` | s.u. | **keine** |
| `results_count` | Integer | `models.py:112` | nein | `search_tracking_repository.py:44` | s.u. | **keine** |
| `timestamp` | Timestamptz | `models.py:113-115` | nein für sich | Server-Default | s.u. | **keine** |

**Nicht (mehr) vorhanden:** `query_text`, `user_id`, `session_id`, `ip_hash` — entfernt durch
`migrations/2026-08-19-search-events-pseudonymisieren.sql:30-33`, Bestandsdaten per
`TRUNCATE` (`:25`) plus `VACUUM FULL` (`:42`) verworfen. Begründung im ORM dokumentiert
(`models.py:97-106`).

**Lesen:** ausschließlich aggregiert über `GET /api/v1/metrics/daily-active-users`
(`api/v1/metrics.py:165-168`) und `/searches-per-user` (`:193-196`) — **beide ohne jede
Auth-Dependency**, und `/api/v1/metrics/` steht in der BFF-Public-Liste
(`IdentityHeaderTransform.cs:29`). Die zugrundeliegenden Queries:
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
  (`search_tracking_service.py:83-84`, Aufruf `api/v1/search.py:257-261`) ✓
- Der Hash enthält die Kennung nicht (Test `:54-62`) ✓

### Befund S-2 — das Secret ist im Repo nirgends gesetzt; der Fallback ist zufällig pro Prozess

`app/core/config.py:133`: `actor_hash_secret: Optional[str] = None`, Env-Name wäre
`SEMANTIC_SEARCH_ACTOR_HASH_SECRET` (Prefix `config.py:165`).

Repo-weiter Grep nach `ACTOR_HASH_SECRET` über `*.yml`, `*.yaml`, `*.env*`, `*.sh`, `*.md`:
**kein Treffer.** Weder `docker-compose.dev.yml` noch `docker-compose.tst.yml` setzen es.

Wenn nicht gesetzt, greift `_FALLBACK_SECRET = secrets.token_hex(32)`
(`search_tracking_service.py:25`) — einmal pro **Prozess**.

Was das bedeutet (Kommentar `config.py:128-132` beschreibt es korrekt):
- Datenschutzseitig **unkritischer**, nicht kritischer: der Schlüssel existiert nur im
  Arbeitsspeicher und ist nach einem Neustart unwiederbringlich weg. Aus den gespeicherten
  Hashes lässt sich dann selbst mit Kenntnis aller Nutzerkennungen nichts mehr rekonstruieren.
- Fachlich falsch: jeder Neustart eröffnet einen neuen Pseudonymraum. Dieselbe Person zählt
  am selben Tag mehrfach → „Daily Active Users" ist nach oben verzerrt.

Ob in Produktion gesetzt: **Teil 4, Frage 4-A.**

### Befund S-3 — für `search_events` existiert Löschcode, den niemand aufruft

`app/repositories/search_tracking_repository.py:187-211` implementiert `cleanup_old_events()`
(DELETE auf `SearchEvent` älter als `days_to_keep`).

Aufrufer: **keiner.** Der einzige Cleanup-Pfad ist
`services/cleanup/usage_cleanup_service.py:52` → `services/usage_tracking_service.py:300`
→ `repositories/usage_tracking_repository.py:297` — also ausschließlich `usage_events`.
Grep nach `cleanup_old_events` über das gesamte Repo (Anhang B, Methode M-4) findet nur
Definitionen und den einen `usage`-Aufrufpfad.

**Wirksame Löschfrist für `search_events`: keine.**

---

## 1.4 PostgreSQL — `content_reports`

| Feld | Typ | Definiert in | Personenbezug | Wer schreibt | Wer kann lesen | Wirksame Löschfrist |
|------|-----|--------------|---------------|--------------|----------------|---------------------|
| `id` | UUID PK | `models.py:129-133` | nein | `app/repositories/content_report_repository.py:49` | s.u. | **keine** |
| `content_id` | UUID | `models.py:134` | nein | `content_report_repository.py:50` | s.u. | **keine** |
| `content_type` | VARCHAR(50) | `models.py:135` | nein | `:51` | s.u. | **keine** |
| `reported_by_user_id` | VARCHAR(255) | `models.py:136` | **ja** — Keycloak-`sub`/`user-00x`; `"anonymous"` wird zu `NULL` normalisiert | `api/v1/moderation.py:114` → `content_report_repository.py:53` | s.u. | **keine** |
| `reported_by_session_id` | VARCHAR(255) | `models.py:137` | **pseudonym** — localStorage-UUID | `api/v1/moderation.py:115` → `:54` | s.u. | **keine** |
| `reason` | VARCHAR(100) | `models.py:138` | nein | `:52` | s.u. | **keine** |
| `description` | **Text, Freitext** | `models.py:139` | **potenziell ja** — Nutzereingabe, kein Filter | `:55` | s.u. | **keine** |
| `status` | VARCHAR(20) | `models.py:140` | nein | `:56` | s.u. | **keine** |
| `created` | Timestamptz | `models.py:141` | nein | Server-Default | s.u. | **keine** |
| `reviewed_by` | VARCHAR(255) | `models.py:142` | **ja** — Kennung der moderierenden Person | Moderationspfad | s.u. | **keine** |
| `reviewed_at` | Timestamptz | `models.py:143` | nein | dito | s.u. | **keine** |
| `resolution_notes` | **Text, Freitext** | `models.py:144` | **potenziell ja** | dito | s.u. | **keine** |

Constraint `models.py:151-154`: mindestens eine der beiden Melderkennungen muss gesetzt sein —
eine vollständig anonyme Meldung ist per Schema ausgeschlossen.

**Wer kann lesen:** `GET /api/v1/moderation/reports` und `/stats`, `PUT …/dismiss`, `DELETE` —
alle vier mit `Depends(require_admin)` (`api/v1/moderation.py:146,184,222,255`).
`require_admin` (`app/dependencies.py:219-235`) prüft `X-User` ≠ leer/`anonymous`
**und** `X-Is-Admin: true`; letzteres setzt nur das BFF aus Claims
(`IdentityHeaderTransform.cs:56-63`) und entfernt einen mitgeschickten Wert vorher
bedingungslos (`:46`). Das ist der einzige Speicher mit funktionierender Admin-Schranke.

**Schreiben:** `POST /api/v1/moderation/report` ist **öffentlich**
(`IdentityHeaderTransform.cs:34`) — anonymes Melden mit Session-ID ist vorgesehen.

**Löschfrist: keine.** Grep über `repositories/`, `services/`, `api/` nach DELETE-Pfaden
(Anhang B, M-4) findet für `ContentReport` keinen. `moderation_service.py:134-152`
löscht den *gemeldeten Inhalt* aus Qdrant, nicht die Meldung.

---

## 1.5 PostgreSQL — `raw_inputs` (Fangkorb)

| Feld | Typ | Definiert in | Personenbezug | Wer schreibt | Wer kann lesen | Wirksame Löschfrist |
|------|-----|--------------|---------------|--------------|----------------|---------------------|
| `id` | UUID PK | `models.py:175-179`; Migration `:27` | nein | `app/repositories/raw_input_repository.py:64` | s.u. | **keine** |
| `content` | **Text, Freitext** (max. 5000, `dtos/raw_input.py:51`) | `models.py:180`; Migration `:28` | **potenziell ja** — freier Satz | `raw_input_repository.py:65` | s.u. | **keine** |
| `url` | Text (max. 2000) | `models.py:181`; Migration `:29` | **potenziell ja** — Link auf fremde Beiträge/Profile | `:66` | s.u. | **keine** |
| `image_url` | Text (max. 2000) | `models.py:182`; Migration `:30` | **potenziell ja** — Bild Dritter | `:67` | s.u. | **keine** |
| `submitted_by` | VARCHAR(255), nullable | `models.py:183`; Migration `:32` | **ja** — Keycloak-`sub`/`user-00x` | `api/v1/raw_input.py:55` → `raw_input_repository.py:68` | s.u. | **keine** |
| `source_channel` | VARCHAR(50), default `web` | `models.py:184` | nein | `:69` | s.u. | **keine** |
| `status` | VARCHAR(20), default `open` | `models.py:185` | nein | `:70` | s.u. | **keine** |
| `created_at` | Timestamptz | `models.py:186-188` | nein | Server-Default | s.u. | **keine** |

### Wer wird als Einwerfer gespeichert

`app/api/v1/raw_input.py:30-40` (`_einwerfende_person`): der Wert des `X-User`-Headers;
`"anonymous"` und leer werden bewusst zu `None`. `X-User` ist der Keycloak-`sub` bzw. bei
Managed/Dummy-Auth `user-001`/`user-002`/`test-user-id-1`
(`BFF/Program.cs:615-619` `ClaimUtilities.GetUserId` — `sub`, ersatzweise `NameIdentifier`).
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
- `/api/v1/rawinput/` steht in **keiner** BFF-Public-Liste
  (`IdentityHeaderTransform.cs:26-35`, `BFF/Program.cs:435-442`) — bei `USE_KEYCLOAK=true`
  greift damit die YARP-Autorisierung. Bei `USE_KEYCLOAK=false` wird der Proxy **ohne**
  Autorisierungspipeline gemappt (`BFF/Program.cs:461`: `app.MapReverseProxy();`), dann
  schützt nur noch der Frontend-Guard, der clientseitig ist. Beide Compose-Dateien im Repo
  setzen `false` (`docker-compose.dev.yml:112`, `docker-compose.tst.yml:66`).

**Löschfrist: keine.** Der ORM-Kommentar sagt es selbst (`models.py:216-218`): Einwürfe
werden nicht gelöscht; der Fremdschlüssel mit `ON DELETE CASCADE` existiert nur, damit ein
*späteres* Löschen aus Datenschutzgründen keine Verweise auf Nichts hinterlässt.

---

## 1.6 PostgreSQL — `raw_input_content_links`

| Feld | Typ | Definiert in | Personenbezug | Wer schreibt | Wer kann lesen | Wirksame Löschfrist |
|------|-----|--------------|---------------|--------------|----------------|---------------------|
| `id` | UUID PK | `models.py:227-231` | nein | **niemand** | — | **keine** |
| `raw_input_id` | UUID FK→`raw_inputs` ON DELETE CASCADE | `models.py:232-236` | nein | **niemand** | — | Kaskade beim Löschen des Einwurfs |
| `content_id` | UUID (kein FK, zeigt nach Qdrant) | `models.py:237` | nein | **niemand** | — | **keine** |
| `created_by` | VARCHAR(255) | `models.py:238` | **ja** (wenn je gefüllt) | **niemand** | — | **keine** |
| `created_at` | Timestamptz | `models.py:239-241` | nein | **niemand** | — | **keine** |

**Die Tabelle ist heute leer.** Der ORM-Docstring stellt es ausdrücklich fest
(`models.py:208-209`: „**Heute schreibt niemand in diese Tabelle** — die Verarbeitung ist
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
- aggregiert und **öffentlich**: `/api/v1/metrics/helpful-rate` (`api/v1/metrics.py:283-286`)
- `/api/v1/voting/` steht **nicht** in der BFF-Public-Liste (`IdentityHeaderTransform.cs:26-35`),
  wohl aber in der Frontend-Liste (`fe/app/shared/public-endpoints.ts`) — siehe Anhang A, A-3

**Löschung:** Es gibt `delete_vote` (`vote_repository.py:93-96`), aber nur als
nutzergesteuertes Zurücknehmen einer Stimme (`DELETE /api/v1/voting/…`, `voting.py:55,113`).
Keine zeit- oder kontobasierte Löschung. **Wirksame Löschfrist: keine.**

---

## 1.8 PostgreSQL — View `user_usage_statistics`

`init.sql:33-46`. Aggregiert `usage_tracking` × DISTINCT(`content_id`,`user_id`) aus
`usage_events`, gruppiert nach `ut.user_id`. Enthält damit `user_id` im Klartext.

Nur bei direktem Datenbankzugriff lesbar — Grep über `app/` nach
`user_usage_statistics` findet **keinen** Anwendungscode, der die View benutzt.
Da `usage_events.user_id` faktisch `NULL` bleibt (Befund E-1) und die View auf
`WHERE user_id IS NOT NULL` filtert (`init.sql:44`), liefert sie derzeit leere Ergebnisse.

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
| `original_author` | `base_content.py:87` | **ja** — Keycloak-`sub`; bei Suchanfragen `system:suchanfrage` | `api/v1/post.py:111`, `api/v1/image.py:99`, `services/content/{statement,commentary,generic_text,reference}_service.py:167/131/94/128` | **öffentlich, und sichtbar gerendert** (s.u.) | **keine** |
| `last_modified_by` | `base_content.py:88` | **ja** | `api/v1/post.py:112`, `api/v1/image.py:100` | öffentlich; in `/contributions` als Spalte (`fe/app/contributions-view/contributions-view.component.html:67-69`) | **keine** |
| `authors[]` (`AuthorEntry.name`, `.role`) | `base_content.py:89`, `domain/models/author_entry.py:17-18` | **ja** | `api/v1/post.py:113`, `api/v1/image.py:101` | öffentlich | **keine** |
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
| `statement` | `replysuggestions[]` | `statement.py:69` | Freitext |
| `reference` | `reference_string` | `reference.py:18` | Freitext/Quellenangabe |

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

`POST /api/v1/search/searchByText` ist ein Public-Endpoint (`IdentityHeaderTransform.cs:28`,
`BFF/Program.cs:435-442`). Die Antwort-DTOs betten das **vollständige** DB-Entry ein —
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

- `delete_by_id` / `delete_by_filter` existieren (`qdrant_embeddings_manager.py:465,477`).
- Aufgerufen nur aus `services/moderation_service.py:152` (`delete_content`), erreichbar über
  `DELETE /api/v1/moderation/…` mit `require_admin` (`api/v1/moderation.py:178-184`).
- **Keine** zeit- oder kontobasierte Löschung. Kein Pfad, der die Beiträge einer Person löscht
  oder deren Kennung anonymisiert.

**Wirksame Löschfrist Qdrant: keine.** Löschung nur einzeln durch Moderation.

**Qdrant-Zugangsschutz:** Grep über die Compose-Dateien nach `QDRANT__SERVICE__API_KEY`/
`api_key`: kein Treffer — im Repo ist **keine** Qdrant-Authentifizierung konfiguriert.
Im Dev-Compose sind 6333/6334 auf dem Host veröffentlicht
(`docker-compose.dev.yml:17-19`); im Test-Compose nicht. Produktion: Teil 4.

---

## 1.10 Logs (stdout der Container)

Es gibt **zwei** Wege, wie Text auf stdout landet: das konfigurierte Logging und nackte
`print()`-Aufrufe, die kein Loglevel filtert.

### 1.10.1 `print()` im Python-Backend — filterlos

**93** `print()`-Aufrufe in `api/`, `services/`, `repositories/`, `core/`, `domain/`
(Zählmethode: Anhang B, M-5). Die mit Personenbezug:

| Was landet auf stdout | Fundstelle |
|-----------------------|------------|
| **Nutzerkennung** (`X-User`) im Klartext | `app/api/v1/contribution.py:36`, `app/api/v1/generic_text.py:133`, `app/api/v1/commentary.py:99`, `app/api/v1/statement.py:105` — jeweils `print(f"X-User header: {x_user}")` |
| **vollständiger Request** inkl. Suchtext bzw. Beitragstext | `api/v1/statement.py:75,100,159,205,248`, `api/v1/commentary.py:66,94`, `api/v1/generic_text.py:99,128`, `api/v1/content.py:73`, `api/v1/test.py:47` |
| **sämtliche eingehende Header** — Name und Wert, Zeile für Zeile | `api/v1/test.py:35-37` (`GET /api/v1/test/headers`) |

Zu `test.py:35-37`: YARP kopiert per Default alle eingehenden Header in den Proxy-Request;
der Transform entfernt ausschließlich `X-User` und `X-Is-Admin`
(`IdentityHeaderTransform.cs:45-46`). Der **Cookie-Header mit `ContentGruenAuthCookie`**
wird also mit weitergereicht und von diesem Endpunkt ins Log geschrieben. Der Router ist
unbedingt gemountet (`app/main.py:34,182`).

*Einschränkung:* Der Cookie ist DataProtection-verschlüsselt (`BFF/Program.cs:314-316`);
im Log steht Chiffrat, nicht Klartext. Es ist trotzdem ein gültiges Sitzungstoken.

### 1.10.2 Logger im Python-Backend

Loglevel: `app/core/config.py:76` `log_level: str = "INFO"`; gesetzt auf `DEBUG` im Dev-Compose
(`docker-compose.dev.yml:78`) und auf `INFO` im Test-Compose (`docker-compose.tst.yml:46`).
Alles Folgende steht auf **INFO** oder darunter, wird also in beiden Umgebungen ausgegeben.

| Was | Level | Fundstelle |
|-----|-------|------------|
| **vollständiger Suchtext** — `query='…'` | INFO | `app/api/v1/search.py:78-79` |
| Suchtext (leicht ersetzt: `;`→`,`, `'`→`"`) | DEBUG | `app/services/content/base_content_service.py:78-79`, `services/content/statement_service.py:69-70` |
| Suchtext in Trefferzeilen | INFO/DEBUG | `repositories/implementations/qdrant/base_repository.py:150`, `…/statement_repository.py:162` |
| Suchtext im Fehlerfall | ERROR | `repositories/implementations/qdrant/statement_repository.py:173` |
| Suchtext-Keywords | DEBUG | `services/keyword_overlap_service.py:109` |
| **Nutzerkennung + Session-ID** beim Nutzungs-Tracking | INFO | `app/api/v1/usage.py:92-93`; nochmals `services/usage_tracking_service.py:63-64,82-83` |
| **Nutzerkennung** bei jeder Stimmabgabe | INFO | `app/api/v1/voting.py:39,69,97,127` und `services/voting_service.py:34,93` |
| **Einwerfer-Kennung** beim Fangkorb-Einwurf | INFO | `app/repositories/raw_input_repository.py:75-77` |
| **Melder-Kennung bzw. Session-ID** bei jeder Meldung | INFO | `app/repositories/content_report_repository.py:61-63` |
| Nutzerkennung bei manuellem Cleanup | INFO | `app/api/v1/usage.py:294-295` |
| Nutzerkennung bei `/recent` | DEBUG | `app/api/v1/content.py:111` |
| Nutzerkennung bei Suche | DEBUG | `app/api/v1/search.py:85` |

**Bemerkenswert:** der Suchtext wurde aus `search_events` bewusst entfernt
(Migration `…-search-events-pseudonymisieren.sql:3-9`, ORM-Kommentar `models.py:99-101`) —
über `api/v1/search.py:78-79` steht er weiterhin bei **jeder** Suche im Containerlog, auf
INFO.

### 1.10.3 Logs im BFF (.NET)

`Console.WriteLine` gibt es **nicht mehr** — Grep über alle `*.cs` unter `mvp/backend/BFF/`:
kein Treffer. `/api/check-session` gibt nur noch den Bool aus
(`BFF/Program.cs:414-416`, Level Debug).

Was bleibt:

| Was | Level | Fundstelle |
|-----|-------|------------|
| **E-Mail-Adresse** bei fehlgeschlagenem Login | Warning | `BFF/Controllers/AuthController.cs:55` |
| **E-Mail-Adresse** bei erfolgreichem Login | Information | `BFF/Controllers/AuthController.cs:91` |
| **E-Mail-Adresse** bei überschrittenem Auth-Rate-Limit | Warning | `BFF/Services/ManagedUserService.cs:126` |
| **E-Mail-Adresse** „user not found" | Warning | `ManagedUserService.cs:137` |
| **E-Mail-Adresse + UserId** bei erfolgreicher Authentifizierung | Information | `ManagedUserService.cs:147` |
| **E-Mail-Adresse** „invalid password" | Warning | `ManagedUserService.cs:153` |
| **E-Mail-Adresse** im Fehlerfall | Error | `ManagedUserService.cs:160` |
| Nutzerkennung beim Header-Setzen | Debug | `IdentityHeaderTransform.cs:54,62` |
| Pfad eines geschützten Endpunkts ohne Nutzer | **Warning** | `IdentityHeaderTransform.cs:72` |

Das betrifft nur den Managed-Auth-Pfad (`USE_KEYCLOAK=false`). Im Keycloak-Modus laufen die
Anmeldedaten nicht durch das BFF.

### 1.10.4 Webserver-Logs

Die nginx-Konfigurationen im Repo setzen **weder** `access_log` **noch** `log_format` —
geprüft: `mvp/frontend/contentgruen-frontend/nginx.conf` (26 Zeilen),
`nginx.docker.conf` (65 Zeilen), `mvp/tst-server-config/frontend-nginx.conf` (44),
`backend-nginx.conf` (53). Damit gilt der nginx-Default (`access_log` an, Kombiformat
**mit Client-IP**). Sie reichen die IP zusätzlich nach innen weiter:
`proxy_set_header X-Real-IP $remote_addr` und `X-Forwarded-For`
(`nginx.docker.conf:17-18,27-28,36-37`; `tst-server-config/frontend-nginx.conf:35-36`;
`backend-nginx.conf:35-36`).

Das BFF wertet `X-Forwarded-*` aus (`BFF/Program.cs:326` `UseForwardedHeaders()`), mit
geleerten `KnownNetworks`/`KnownProxies` (`:306-307`) — begründet `:299-305`.

**Kein `logging:`-Block, kein Rotationslimit** in `docker-compose.dev.yml` oder
`docker-compose.tst.yml` (Grep nach `logging`/`max-size`: nur ein Kommentar
`docker-compose.dev.yml:77` und Netzwerk-/Volume-`driver`-Einträge). Es gilt der Docker-Default
`json-file`, unbegrenzt.

**Wirksame Löschfrist für Logs: im Repo keine.** Alles Weitere: Teil 4, Frage 4-E.

---

## 1.11 Browser-seitige Speicherung

Erhebungsmethode: Grep über `fe/` nach `localStorage`, `sessionStorage`, `document.cookie`
(Anhang B, M-6). `document.cookie` kommt **nicht** vor — die App setzt selbst keine Cookies.

### Cookies

| Name | Gesetzt von | Inhalt | Flags | Lebensdauer |
|------|-------------|--------|-------|-------------|
| `ContentGruenAuthCookie` (Keycloak-Modus) | `BFF/Program.cs:59` | ASP.NET-Cookie-Auth-Ticket, DataProtection-verschlüsselt; enthält **alle Keycloak-Claims** (`sub`, `email`, Name — Scopes `openid`,`profile`,`email`, `Program.cs:72-74`; Übernahme `:95-102`) **plus die Tokens**, da `options.SaveTokens = true` (`:71`) | `HttpOnly` (`:62`), `Secure = Always` (`:61`), `SameSite = None` (`:60`) | keine explizite Setzung → ASP.NET-Default 14 Tage. **UNSICHER:** ich habe keine `ExpireTimeSpan`-Zuweisung für diesen Zweig gefunden; der Default ist mein Schluss aus dem Framework, nicht aus dem Repo |
| `ContentGruenAuthCookie` (Managed/Dummy-Modus) | `BFF/Program.cs:135` | Claims `NameIdentifier`, `Name`, `name`, `Email`, `sub`, `auth_method`, `user_id`, ggf. `Role=admin` (`AuthController.cs:60-76`) | `HttpOnly` (`:138`), `SecurePolicy = SameAsRequest` (`:137` — **über http also ohne `Secure`**), `SameSite = Lax` (`:136`) | **8 Stunden**, persistent (`AuthController.cs:81-83`) |
| dito, Dummy-Login | `Program.cs:135` | Claims `name`, `GivenName`, `Surname`, `NameIdentifier=test-user-id-1` (`Program.cs:519-525`) | wie oben | **1 Stunde**, persistent (`Program.cs:531-535`) |
| OIDC-Korrelations-/Nonce-Cookies | ASP.NET-OIDC-Handler, indirekt über `Program.cs:65-127` | Flow-State | Framework-Default `SameSite=None`, `Secure` abhängig vom weitergereichten Schema (`Program.cs:322-325`) | Sekunden bis Minuten |

Ein **Schlüsselring** liegt unter `/keys` (`Program.cs:314-316`,
`SetApplicationName("contentgruen-bff")`). Ohne gemountetes Volume entwertet jeder
Container-Neustart alle bestehenden Cookies (`:310-313`).

### localStorage — überlebt das Schließen des Browsers

| Schlüssel | Inhalt | Gesetzt in | Lebensdauer |
|-----------|--------|------------|-------------|
| `gutgesagt_session_id` | UUID v4, **pseudonymer Dauer-Identifikator** | `fe/app/services/session.service.ts:11,40,63` und — zweite, identische Implementierung — `fe/app/services/search.service.ts:28-37` | **unbegrenzt**, siehe Befund B-1 |
| `gutgesagt-metrics-seen` | `"true"`, ob das Metrik-Panel schon gesehen wurde | `fe/app/metrics/metrics.component.ts:35,41` | unbegrenzt |

Wohin die Session-ID geht: als Header `X-Session-Id` bei jeder Suche
(`search.service.ts:56-58`) und bei jeder Meldung (`moderation.service.ts:70`), im Body beim
Nutzungs-Tracking (`usage-tracking.service.ts:109-110`). Das BFF reicht den Header
unverändert durch (`IdentityHeaderTransform.cs:77-82`). Gespeichert wird er in
`usage_events.session_id` (1.2) und `content_reports.reported_by_session_id` (1.4); in
`search_events` fließt er nur noch in den Tagespseudonym-Hash ein (1.3).

**Befund B-1:** `SessionService` hat `clearSessionId()` (`session.service.ts:49-52`) und
`regenerateSessionId()` (`:38-43`) — Grep über `fe/` (ohne Specs) findet **keinen Aufrufer**
für beide. Die Session-ID wird auch beim Logout nicht zurückgesetzt. Sie ist damit ein
dauerhafter, geräteübergreifend eindeutiger Identifikator, der anonyme und angemeldete
Nutzung desselben Browsers verbindet.

**Befund B-2:** Erzeugt wird sie mit `Math.random()`
(`session.service.ts:74-78`, `search.service.ts:32-36`), nicht mit `crypto.randomUUID()`.
Für Datenschutz ohne Belang, für Ratbarkeit relevant — siehe Anhang A, A-5.

### sessionStorage — wird beim Schließen des Tabs verworfen

| Schlüssel | Inhalt | Gesetzt in |
|-----------|--------|------------|
| `profilePicture` | Dicebear-URL des gewählten Avatars | `fe/app/app.component.ts:232` |
| `anonymousAvatar` | Dicebear-URL des Anonym-Avatars | `app.component.ts:237,250`, `result-view.component.ts:303` |
| `userAvatar` | Dicebear-URL | `result-view.component.ts:312` |
| `loginReturnUrl` | Ziel-URL nach dem Login | `login.component.ts:35,47`, `login-selector.component.ts:39,75` |

Alle vier ohne eigenen Personenbezug (Avatare sind aus festen Seeds erzeugt, nicht aus
Nutzerdaten — `app.component.ts:58-76`), aber sie sind Endgerätespeicherung im Sinne des
§ 25 TDDDG.

---

## 1.12 Dateisystem und Backups

| Speicher | Inhalt | Beleg | Personenbezug |
|----------|--------|-------|---------------|
| `/metadata` (Volume `semantic_search_metadata`) | Seeding-Status: Dateinamen, Zähler, Zeitstempel, PID | `app/services/seeding/seeding_status.py:260-261,283-284`, `seeding_service.py:161-162`; Volume `docker-compose.tst.yml:49` | **nein** — Grep über `services/seeding/` nach Schreibpfaden zeigt nur Dateilisten und Fortschrittszähler |
| `/keys` | DataProtection-Schlüsselring | `BFF/Program.cs:314-316` | nein, aber sicherheitsrelevant |
| `/opt/contentgruen-backups/daily|weekly` | **vollständige Kopien** von Qdrant-Snapshot und PostgreSQL-Dump | `mvp/scripts/backup/backup.sh`; Host-Mount `docker-compose.tst.yml:31,51` | **ja — enthält alles aus 1.1–1.9** |
| `mvp/config/managed-users.json` | 2 Konten: E-Mail, bcrypt-Hash, Anzeigename, UserId, `isAdmin` | im Git getrackt; gemountet `docker-compose.tst.yml:70` (`./config:/config:ro`) | **ja** (Testkonten `test.user@example.com`, `admin@contentgruen.com`) |

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
| 2-A | **api.dicebear.com** (Avatare) | Bei **jedem Seitenaufruf mit Avatar**: IP-Adresse, User-Agent, Referer des Besuchers — auch **nicht angemeldeter** | 26 fest verdrahtete URLs in `fe/app/app.component.ts:59-76` und `fe/app/result-view/result-view.component.ts:96-112`; gerendert als `<img [src]>` in `fe/app/app.component.html:73`, `fe/app/shared/components/mobile-menu/mobile-menu.html:5`, `fe/app/shared/components/mobile-header/mobile-header.component.html:24` | **ja** — Dicebear ist ein externer Dienst; Betreiberstandort aus dem Repo nicht bestimmbar | **ja, immer.** Der Aufruf hängt an keiner Konfiguration. **Nicht in RECHTSTEXTE_LUECKEN.md verzeichnet** — siehe Teil 3, W-8 |
| 2-B | **beliebige Bild-Hosts** | IP + User-Agent des **Betrachters** gehen an den Host des jeweiligen Bildes | `<img [src]="result.image_result.image_url">` in `fe/app/image-result-item/image-result-item.component.html:41`; Wert stammt aus `domain/models/image.py:37`, vom Beitragenden frei eingegeben (`fe/app/add-image/add-image.component.html:34`) | abhängig vom eingetragenen Host — nicht vorhersagbar | **ja**, sobald ein Bildbeitrag im Suchergebnis erscheint. Suche ist öffentlich → betrifft auch nicht angemeldete Besucher |
| 2-C | **OpenAI** (`gpt-4o-mini`) | **Bild-URL** und ein fester deutscher Prompt. Nicht übermittelt: Nutzerkennung, Session-ID, IP. OpenAI ruft das Bild anschließend **selbst** beim Host ab | `app/services/vision/caption_suggestion_service.py:17,26-38`; Prompt `:6-10`; Client `AsyncOpenAI` `:2`. Zwei Auslöser: (a) `POST /api/v1/image/suggestCaption` (`app/api/v1/image.py:134-146`, angemeldet, rate-limited `middleware/rate_limit.py:39`), (b) Hintergrund-Worker für `PENDING_DESCRIPTION` (`services/vision/image_description_worker.py:37-39`, gestartet `app/main.py:119-122`) | **ja, USA** | **abhängig von `OPENAI_API_KEY` — siehe Befund V-1** |
| 2-D | **Keycloak** (Netzbegrünung) | Authorization-Code-Flow, Scopes `openid`, `profile`, `email`; zurück kommen `sub`, `email`, Name | `BFF/Program.cs:65-127`, Scopes `:72-74`, Callback `:75` | nein (EU, **UNSICHER** — Authority steht nicht im Repo, s. Teil 4) | **nur bei `USE_KEYCLOAK=true`**. Beide Compose-Dateien im Repo setzen `false` (`docker-compose.dev.yml:112`, `docker-compose.tst.yml:66`); Code-Default ist `true` (`Program.cs:19`) |
| 2-E | **Anthropic** (`claude-sonnet-4-5`) | Beitragstexte aus einer Korpusdatei | `mvp/scripts/manual/check_wirkung_baseline.py` | ja, USA | **nein — toter Pfad für die Anwendung.** Ein manuell auszuführendes Skript unter `scripts/manual/`, von keinem Anwendungscode importiert; `anthropic` steht **nicht** in `mvp/backend/semantic-search-service/requirements.txt` (dort nur `openai>=1.35.0`, Zeile 30) |
| 2-F | Qdrant-Snapshot-API | Vollständige Sammlung inkl. aller Payloads | `app/scripts/backup_qdrant.py:87`, `restore_qdrant.py:73` | nein — `localhost`/Docker-intern | ja, beim Backup |
| — | Google Fonts | — | vormals `index.html` | — | **nein, entfernt.** `src/index.html` (14 Zeilen) enthält keinen externen Link mehr; Schriften liegen in `public/fonts/` (11 Dateien), Einbindung `src/styles/fonts.css`. Grep nach `fonts.googleapis`/`fonts.gstatic` in `src/` und `public/`: nur ein historischer Kommentar `styles/fonts.css:4`. **Bestätigt D-N10 der Lückenliste** |
| — | Analyse-/Tracking-Dienste | — | — | — | **nicht gefunden.** Kein Matomo, kein Google Analytics, kein Sentry: Grep nach `http(s)://` über alle `*.ts`/`*.html`/`*.scss` in `fe/src` ergibt außer 2-A/2-B nur redaktionelle Links (netzbegruenung.de, qdrant.tech, chatbegruenung.de, ec.europa.eu) |

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
(`app/core/config.py:103-108`, `AliasChoices`). Grep über alle `*.yml`/`*.yaml`/`*.env*` im
Repo nach `OPENAI`: **kein Treffer.** In Dev und Test ist der Pfad damit inaktiv.
Für Produktion: Teil 4, Frage 4-B.

---

# Teil 3 — Widersprüche zwischen Code und den vorhandenen Rechtstexten

Geprüft gegen `fe/app/datenschutz/datenschutz.component.html` (240 Zeilen) und
`docs/RECHTSTEXTE_LUECKEN.md` (221 Zeilen, Stand 2026-08-19).

## 3.1 Der Datenschutztext behauptet etwas, das der Code nicht einhält

| # | Text sagt | Code sagt | Belege |
|---|-----------|-----------|--------|
| **W-1** | „Wir erheben lediglich **anonymisierte** Nutzungsstatistiken" | `usage_events` speichert `session_id` (dauerhafte localStorage-UUID), `ip_hash` (ungesalzenes SHA-256) und `user_agent` im Klartext, verknüpft mit `content_id` und Zeitstempel. Das ist pseudonym, nicht anonym | Text `datenschutz.component.html:156-158` ⟷ `app/infrastructure/database/models.py:76-83`; Hash-Bildung `app/api/v1/usage.py:117-119` + `repositories/usage_tracking_repository.py:71-73` |
| **W-2** | „Diese Website verwendet **keine Analyse-Tools von Drittanbietern**" (formal richtig) und Abschnitt 5 beschreibt Drittanbieter-Einbindung **abstrakt, ohne einen einzigen zu nennen** | Zwei konkrete, laufende Drittabrufe aus dem Browser: **api.dicebear.com** und beliebige **Bild-Hosts** | Text `:156-157` und `:164-177` ⟷ `fe/app/app.component.ts:59-76`, `fe/app/app.component.html:73`, `fe/app/image-result-item/image-result-item.component.html:41` |
| **W-3** | „Sie können sich auf dieser Website **registrieren**" mit Erhebungsliste Benutzername/E-Mail/Passwort/Zeitpunkt | Es gibt keine Registrierungsroute. Zugänge werden manuell in `managed-users.json` angelegt oder kommen über Keycloak | Text `:126-140` ⟷ `fe/app/app.routes.ts` (keine Register-Route), `mvp/config/managed-users.json`. Deckungsgleich mit Lückenliste X1 |
| **W-4** | „Daten, die Sie in ein **Kontaktformular** eingeben" | Kein Kontaktformular im Frontend | Text `:26-27` ⟷ Lückenliste X2, von mir nicht widerlegt |
| **W-5** | Cookie-Abschnitt kennt nur „Sitzungscookies" und „Authentifizierungscookies" | Zusätzlich **zwei localStorage-Schlüssel** (unbegrenzt haltbar, überleben den Browserneustart) und **vier sessionStorage-Schlüssel** | Text `:93-106` ⟷ 1.11 dieses Berichts. Die Lückenliste (X5) nennt dabei noch die alten Schlüsselnamen `contentgruen-metrics-seen`; seit PR #24 heißen sie `gutgesagt-metrics-seen` (`fe/app/metrics/metrics.component.ts:35,41`) und `gutgesagt_session_id` (`session.service.ts:11`) |
| **W-6** | „Authentifizierungscookies … für die **Dauer Ihrer Sitzung**" | Persistente Cookies mit fester Lebensdauer: 8 h (Managed), 1 h (Dummy), Framework-Default (Keycloak). Sie überleben das Schließen des Browsers — `IsPersistent = true` | Text `:105` ⟷ `BFF/Controllers/AuthController.cs:81-83`, `BFF/Program.cs:531-535` |
| **W-7** | „Kommentar- und Beitragsfunktion … werden neben Ihrem Kommentar auch Zeitpunkt und **Nutzername** gespeichert" | Gespeichert werden zusätzlich `last_modified_by`, `authors[]` und die **vollständige `edit_history[]`** mit Editor und Zeitstempel je Änderung — und all das ist für **nicht angemeldete** Besucher über die öffentliche Suche abrufbar und sichtbar gerendert | Text `:142-147` ⟷ `app/domain/models/base_content.py:87-90`, `app/domain/models/edit_entry.py:22-24`, `app/dtos/search.py:46,58`, `fe/app/commentary-result-item/commentary-result-item.component.html:213`. Die Lückenliste (D-N3) benennt die Edit-History, aber lässt die Sichtbarkeitsfrage offen („☐ nur intern ☐ öffentlich") — **der Code beantwortet sie: öffentlich** |
| **W-8** | Text nennt Server-Log-Felder (Browsertyp, OS, Referrer, Hostname, Uhrzeit, IP) und stellt fest: „Eine **Zusammenführung** dieser Daten mit anderen Datenquellen wird nicht vorgenommen" | Die Anwendungslogs enthalten Suchtexte, Nutzerkennungen, Session-IDs, Einwerfer- und Melderkennungen — im selben Logstream wie die Zugriffe, mit denselben Zeitstempeln. Ob das eine „Zusammenführung" ist, ist Bewertungssache; **faktisch liegen die Daten nebeneinander vor** | Text `:113-122` ⟷ 1.10 dieses Berichts |
| **W-9** | Rechte-Abschnitt sagt Auskunft, Berichtigung, **Löschung**, Einschränkung, Übertragbarkeit zu | Es gibt **keinen** Codepfad, der die Daten einer Person findet oder löscht. Kein Export, kein Konto-Löschen, keine Anonymisierung von `original_author`. Löschen kann nur: die Moderation einen einzelnen Inhalt (`api/v1/moderation.py:178-184`), und eine Person ihre eigene Stimme (`api/v1/voting.py:55,113`) | Text `:196-212` ⟷ Grep über alle DELETE-Pfade (Anhang B, M-4). Auch `STATUS.md:42` führt „Export/import backup" als **offen** |
| **W-10** | „Diese Seite nutzt … eine SSL- bzw. TLS-Verschlüsselung" | Trifft für Produktion zu (Reverse Proxy). Im BFF ist der Cookie im Managed-Modus aber auf `SecurePolicy = SameAsRequest` gesetzt (`:137`) — über http ginge er ohne `Secure`-Flag hinaus | Text `:218-224` ⟷ `BFF/Program.cs:137`. Praktisch nur im Dev-Betrieb relevant |

## 3.2 Korrekturen und Ergänzungen zu `docs/RECHTSTEXTE_LUECKEN.md`

Die Lückenliste ist überwiegend präzise. Vier Punkte muss sie fortschreiben:

| # | Lückenliste sagt | Tatsächlicher Stand | Beleg |
|---|------------------|---------------------|-------|
| **L-1** | X4/D-N10: nach dem Wegfall von Google Fonts bleibe „**kein** realer Anwendungsfall übrig, der Abschnitt kann ersatzlos gestrichen werden" (`:107`, `:171`) | **Falsch.** Es bleiben **zwei**: api.dicebear.com (immer aktiv, auch anonym) und beliebige externe Bild-Hosts in Suchergebnissen. Abschnitt 5 muss also nicht gestrichen, sondern konkretisiert werden | `fe/app/app.component.ts:59-76`, `fe/app/app.component.html:73`, `fe/app/image-result-item/image-result-item.component.html:41` — vgl. Teil 2, 2-A und 2-B |
| **L-2** | D-M1: Speicherdauer/Löschfristen „kommt im gesamten Dokument nicht vor … Suchverlauf: ___" (`:89`) | Teilweise beantwortbar: **`usage_events` = 90 Tage** (fest verdrahtet, nicht konfigurierbar, Befund E-3). **`search_events`, `content_reports`, `raw_inputs`, `votes`, Qdrant, `usage_tracking` = keine Frist.** Backups halten alles zusätzlich bis zu 4 Wochen | `services/cleanup/usage_cleanup_service.py:172`, `repositories/usage_tracking_repository.py:278-280,297-301`, `scripts/backup/backup.sh:24-25` |
| **L-3** | D-N4: „Bei jedem Kopieren … wird festgehalten, **wer** welchen Beitrag wann genutzt hat" (`:121`) | Zu korrigieren: **`user_id` bleibt leer** (Befund E-1, empirisch bestätigt). Festgehalten wird *welcher Browser* (Session-ID, IP-Hash, User-Agent), nicht *welches Konto*. Für den Text macht das einen Unterschied — die Verarbeitung ist pseudonym-gerätebezogen, nicht kontobezogen | `app/dependencies.py:210` ⟷ `BFF/Proxy/IdentityHeaderTransform.cs:17,53,67` |
| **L-4** | Der Fangkorb (`raw_inputs`) kommt **gar nicht** vor | Die Liste datiert auf 2026-08-19, der Fangkorb wurde am 2026-08-22 gemergt (PR #19, Merge `c957750`). Fehlender D-N-Eintrag: Freitext + Fremd-URLs + `submitted_by`, ohne Löschfrist, für **alle** angemeldeten Nutzenden namentlich einsehbar | 1.5 dieses Berichts |

Bestätigt und unverändert: **X1** (keine Registrierung), **X2** (kein Kontaktformular),
**X3** (Aussage „anonymisiert" trifft für `usage_events` weiter nicht zu),
**D-N4b** (`search_events` pseudonymisiert wie beschrieben),
**D-N8** (Embeddings lokal — `SentenceTransformer` im eigenen Container, kein
ausgehender Aufruf; Teil 2 bestätigt das durch Ausschluss),
**D-N10** (Google Fonts entfernt),
**Abschnitt 5** (keine Consent-Checkbox — Grep über `fe/app` nach
`mat-checkbox|consent|einwillig|zustimm|akzeptier|nutzungsbedingung` findet außerhalb der
Rechtstextseiten nur den Footer-Link `fe/app/footer/footer.component.html:25-26`).

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
(`app/core/config.py:103-108`)

| Wert | Konsequenz |
|------|-----------|
| gesetzt | Bild-URLs gehen an OpenAI (USA) — **Drittlandtransfer**, sowohl synchron über `/suggestCaption` als auch über den Hintergrund-Worker. Erfordert Beschreibung in der Datenschutzerklärung, AV-Vertrag und Art.-46-Garantien |
| nicht gesetzt | `DirectText()` — kein Aufruf, nichts zu beschreiben (Befund V-1) |

*Achtung:* `STATUS.md:22` behauptet als Tatsache, es sei „no OpenAI key configured in
production". Die Lückenliste lässt dieselbe Frage offen (`:127`: „Aktiv in Prod? ☐ ja ☐ nein").
**Der Pillar entscheidet, nicht STATUS.md.**

### 4-C · `USE_KEYCLOAK`
**Dienst:** `contentgruen-bff` · **Im Repo:** `false` in beiden Compose-Dateien
(`docker-compose.dev.yml:112`, `docker-compose.tst.yml:143` für das Frontend / `:66`, `:85`
für tst); **Code-Default ist `true`** (`BFF/Program.cs:19`)

| Wert | Konsequenz |
|------|-----------|
| `true` | Anmeldung über Netzbegrünung-Keycloak. Claims `sub`, `email`, Name kommen ins Auth-Cookie, zusätzlich die Tokens (`SaveTokens = true`, `Program.cs:71`). Der Reverse-Proxy erhält eine Autorisierungspipeline (`Program.cs:426-460`). **Für die Erklärung:** IdP benennen, Verantwortlichkeitsabgrenzung/AVV klären |
| `false` | Managed Auth aus `managed-users.json` (E-Mail + bcrypt). **E-Mail-Adressen erscheinen in den Container-Logs** (7 Stellen, 1.10.3). Der Proxy wird **ohne** Autorisierungspipeline gemappt (`Program.cs:461`) — jeder API-Pfad steht offen, siehe Anhang A, A-1 |
| nicht gesetzt | wie `true` |

### 4-D · Inhalt der produktiven `managed-users.json`
**Dienst:** `contentgruen-bff`, Mount `./config:/config:ro`
(`docker-compose.tst.yml:70`) · **Im Repo:** zwei Testkonten

Frage: liegen dort echte Personen (Name + E-Mail) — und wenn ja, wie viele und wie lange nach
Ende der Nutzung? Konsequenz: dann ist ein weiterer personenbezogener Speicher zu beschreiben,
inklusive Löschfrist, die es im Code nicht gibt.

### 4-E · Logging-Konfiguration des Docker-Hosts
**Dienst:** alle · **Im Repo:** kein `logging:`-Block, keine `max-size`, keine `max-file`

Fragen: Welcher Log-Treiber? Werden Container-Logs zentral gesammelt (journald, Loki, …)?
Welche Rotation/Aufbewahrung? Konsequenz: **das ist die Löschfrist für alles aus 1.10** —
Suchtexte, Nutzerkennungen, Session-IDs, E-Mail-Adressen. Ohne diese Antwort ist die
Zeile „Server-Logs: ___ Tage" der Lückenliste (D-M1) nicht ausfüllbar.

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
(`app/core/config.py:112`)

| Wert | Konsequenz |
|------|-----------|
| gesetzt | Die Endpunkte `/api/v1/usage/users/{id}/usage-stats`, `/cleanup/status`, `/cleanup/run` wären für diese Kennungen gedacht — **greifen aber trotzdem nie**, weil `current_user` wegen Befund E-1 immer `None` ist |
| leer/nicht gesetzt | `is_admin_user()` liefert immer `False` (`config.py:123`) → diese drei Endpunkte antworten konstant 403 |

### 4-I · Erreichbarkeit von Qdrant, PostgreSQL und der Semantic-Search-API
**Dienste:** `qdrant`, `postgres-app`, `contentgruen-semantic-search` · **Im Repo:**
Dev veröffentlicht 6333/6334, 5433 und 8000 (`docker-compose.dev.yml:17-19,45-46,65-66`);
Test veröffentlicht PostgreSQL auf `127.0.0.1:5432` (`docker-compose.tst.yml:27`) und
Semantic Search gar nicht (`:47`)

Fragen: Sind in Produktion Ports veröffentlicht? Ist Qdrant durch einen API-Key geschützt
(im Repo ist **keiner** konfiguriert)? Konsequenz: Wenn Port 8000 erreichbar ist, kann jeder
die Auth des BFF umgehen — inklusive `X-User-Id` selbst setzen (Befund E-1) und
`GET /api/v1/rawinput/getRawInputs` samt Einwerferkennungen abrufen.

### 4-J · PostgreSQL-Zugangsdaten
**Dienst:** `postgres-app` · **Im Repo:** Klartext `changeme`
(`docker-compose.tst.yml:24,42`; `docker-compose.dev.yml:70`; Default auch
`app/core/config.py:27`)

Frage: Wird in Produktion ein anderes Passwort gesetzt? Konsequenz: falls nicht, ist der
Speicher aus 1.1–1.8 mit einem im Repo öffentlich lesbaren Passwort erreichbar.

---

# Teil 5 — Die vorab genannten Punkte, geprüft

| Vorannahme | Ergebnis |
|------------|----------|
| „`usage_events` enthält `user_id`, `session_id`, `ip_hash`, `user_agent`, verknüpft mit `content_id`" | **Stimmt und ist vollständig** — die Tabelle hat genau 8 Spalten (`models.py:70-83`): dazu `id`, `event_type`, `timestamp`. **Aber:** `user_id` wird über den Live-Pfad nie gefüllt (Befund E-1), und `ip_hash` ist ungesalzen und doppelt gehasht (Befund E-2) |
| „Eine Retention-Einstellung wird unter anderem Namen gelesen, deshalb greift immer der Fallback" | **Bestätigt und größer als vermutet:** nicht eine, sondern **alle vier** Cleanup-Einstellungen (`usage_cleanup_service.py:172,184,189,190` gegen `config.py:136-139`). **Wirksam: 90 Tage, täglich 02:00, nicht abschaltbar, über die Umgebung nicht änderbar** (Befund E-3, empirisch verifiziert) |
| „Für mehrere Tabellen existiert vermutlich gar keine Löschlogik" | **Bestätigt.** Von 7 Tabellen hat **eine** eine wirksame Frist: `usage_events` (90 Tage). Ohne jede Löschung: `usage_tracking` (ausdrücklich „preserved forever", `usage_tracking_repository.py:279`), `search_events` (Löschcode vorhanden, **kein Aufrufer** — Befund S-3), `content_reports`, `raw_inputs`, `raw_input_content_links`, `votes`. Qdrant ebenso |
| „Fangkorb: wer wird als Einwerfer gespeichert, wer sieht das?" | Gespeichert wird der `X-User`-Wert = Keycloak-`sub` bzw. `user-00x`; `"anonymous"` → `NULL` (`api/v1/raw_input.py:30-40,55`). **Gesehen wird es von jeder angemeldeten Person** — `getRawInputs` liefert bewusst alle Einwürfe (`:76-77`), das DTO trägt `submitted_by` (`dtos/raw_input.py:97`), das Frontend zeigt es als Tabellenspalte (`raw-input-list.component.ts:52`, `.html:53`) |
| „Suchereignisse sollen pseudonymisiert sein (rotierender Actor-Hash) — stimmt das, kommt das Secret aus der Umgebung, was passiert ohne?" | **Implementiert wie beschrieben** (Befund S-1): HMAC-SHA256 über `<Kennung>|<UTC-Datum>`, Suchtext wird gar nicht erst übergeben, durch 7 Unit-Tests abgesichert. Das Secret **kann** aus `SEMANTIC_SEARCH_ACTOR_HASH_SECRET` kommen, ist im Repo aber **nirgends gesetzt**. Ohne Secret: zufälliger 32-Byte-Schlüssel pro Prozess (`search_tracking_service.py:25`) → datenschutzseitig stärker, statistisch unbrauchbar (Befund S-2) |
| „Bildbeschriftung per KI: aktiv, und wovon abhängig?" | Hängt **allein** an `OPENAI_API_KEY`/`SEMANTIC_SEARCH_OPENAI_API_KEY`, ausgewertet **einmal beim Modulimport** (`content_registry.py:107-118`, Befund V-1). Im Repo nirgends gesetzt → in Dev und Test **inaktiv**. Übermittelt wird die **Bild-URL** plus fester Prompt, **keine** Nutzerkennung. OpenAI lädt das Bild danach selbst beim Host. Produktion: Teil 4, 4-B |

---

# Anhang A — Sicherheitsbefunde ohne Datenschutzbezug

Aufgefallen während der Analyse, nicht weiterverfolgt.

| # | Befund | Beleg |
|---|--------|-------|
| **A-1** | Bei `USE_KEYCLOAK=false` wird der Reverse Proxy **ohne Autorisierungspipeline** gemappt (`app.MapReverseProxy();`) — kein API-Pfad ist am Proxy geschützt. Beide Compose-Dateien im Repo setzen `false` | `BFF/Program.cs:461` gegen `:426-460` |
| **A-2** | `IdentityHeaderTransform` entfernt `X-User` und `X-Is-Admin`, **nicht** `X-User-Id`. YARP reicht unbekannte Header durch. Ein Client kann damit `usage_events.user_id` und die `is_admin_user`-Prüfungen in `api/v1/usage.py:200,255,285` selbst befüllen | `IdentityHeaderTransform.cs:45-46` ⟷ `app/dependencies.py:210` |
| **A-3** | Vier **verschiedene** Public-Endpoint-Listen: `IdentityHeaderTransform.cs:26-35` (7 Einträge), `BFF/Program.cs:435-442` (5), `mvp/shared/PublicEndpoints.cs:8-15` (5, wieder andere — und toter Code: nicht in `ContentGruen.sln`, von nirgends referenziert), `fe/app/shared/public-endpoints.ts` (9) | s. Fundstellen |
| **A-4** | `api/v1/seeding.py` hat auf keinem seiner 8 Endpunkte eine Auth-Dependency, obwohl vier Docstrings „allows administrators" behaupten. `POST /start`, `/reset`, `/stop` sind darunter | `app/api/v1/seeding.py:124,166,224,258`; gemountet `app/main.py:189` |
| **A-5** | Session-IDs werden mit `Math.random()` erzeugt, nicht mit `crypto.randomUUID()`. Sie autorisieren anonyme Meldungen und Nutzungs-Tracking | `fe/app/services/session.service.ts:74-78`, `fe/app/services/search.service.ts:32-36` |
| **A-6** | Der Debug-Router `api/v1/test.py` (18 KB) ist unbedingt gemountet und gibt über `/headers` alle eingehenden Header inklusive Cookie auf stdout aus | `app/main.py:34,182`; `app/api/v1/test.py:32-38` |
| **A-7** | `mvp/config/managed-users.json` ist im Git getrackt und enthält zwei bcrypt-Hashes, einer davon für ein Konto mit `isAdmin: true` | Datei im Working Tree, `git ls-files` erfasst sie |
| **A-8** | PostgreSQL-Passwort `changeme` im Klartext in `docker-compose.tst.yml:24,42`, im Dev-Compose `:70` und als Default in `app/core/config.py:27` | s. Fundstellen |
| **A-9** | Die Metrik-Endpunkte haben **keine** Auth-Dependency und `/api/v1/metrics/` steht in der BFF-Public-Liste. DAU-Zahlen, Suchen-pro-Nutzer-Verteilung, „helpful rate" sind damit weltweit lesbar | `app/api/v1/metrics.py:143-144,165-168,193-196,219-222,245-248,283-286`; `IdentityHeaderTransform.cs:29` |
| **A-10** | `POST /api/v1/post/addPost` und `/api/v1/image/addImage` unterliegen **keinem** Rate-Limit — die Liste umfasst nur 6 andere Schreibpfade | `app/middleware/rate_limit.py:34-43` |

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

---

*Ende der Bestandsaufnahme. Am Code wurde nichts geändert; diese Datei ist nicht committet.*
