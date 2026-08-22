# Registrierung und Accountnutzung — Entscheidungsgrundlage

**Status:** Analyse. Keine Entscheidung, keine Implementierung, keine Schema-Migration.
**Anlass:** Die Zielgruppe ist nicht mehr auf Mitglieder der Netzbegrünung e.V. begrenzt.
Unter dem Label **GutGesagt** soll die Plattform einem breiteren, dem Verein nicht
angehörenden Publikum offenstehen. Der heutige Login läuft über den extern verwalteten
Keycloak-Realm `user.netzbegruenung.de`.
**Grundlage:** Stand des Repositories auf `main` (Merge-Commit `1617f48`). Alles unten
Behauptete ist im Repo belegt; was nicht belegbar war, steht in
[Abschnitt 6](#6-was-aus-dem-repo-nicht-verifizierbar-war).

---

## 1. Phase 1 — Bestandsaufnahme

### 1.1 Wie Auth heute tatsächlich verdrahtet ist

Der gesamte Authentifizierungs-Apparat sitzt im BFF. Frontend und Python-Backend
authentifizieren nicht selbst — das Frontend kennt nur Cookies und einen Bool-Schalter,
das Backend kennt nur einen vom BFF gesetzten HTTP-Header.

#### Der zentrale Schalter

`USE_KEYCLOAK` (Bool) entscheidet beim Start des BFF über zwei sich ausschließende
Zweige — `mvp/backend/BFF/Program.cs:18`:

| Zweig | Bedingung | Was registriert wird |
| --- | --- | --- |
| Keycloak | `USE_KEYCLOAK=true` | Cookie-Scheme + OpenID-Connect-Scheme (`Program.cs:39–128`) |
| Lokal | `USE_KEYCLOAK=false` | nur Cookie-Scheme + `DummyAuthStartupFilter` (`Program.cs:130–147`) |

Der Schalter ist an **drei** Stellen wirksam, nicht an einer:

1. Registrierung der Auth-Schemes (`Program.cs:39`).
2. Aufsetzen des YARP-Proxy — mit Keycloak wird eine Autorisierungs-Pipeline vor den
   Proxy gehängt, ohne Keycloak nicht (`Program.cs:489–528`).
3. Frontend: `useKeycloak` in `src/environments/environment*.ts`, zur Laufzeit per
   `replace-env.sh` in die gebauten JS-Dateien substituiert.

#### OIDC-Konfiguration

Gelesen wird die Sektion `Keycloak` aus der .NET-Konfiguration
(`Program.cs:42`), also die Schlüssel `Keycloak:Authority`, `Keycloak:ClientId`,
`Keycloak:ClientSecret`. Fehlt einer davon, wirft der Start (`Program.cs:44–49`).

Wo diese Werte herkommen:

| Ort | Inhalt |
| --- | --- |
| `mvp/backend/BFF/appsettings.json` | **keine** Keycloak-Sektion, nur `USE_KEYCLOAK: "false"` |
| `mvp/backend/BFF/appsettings.Test.json` | Dummy-Werte (`http://localhost/fake-keycloak`) für die Unit-Tests |
| `mvp/backend/BFF/Properties/launchSettings.json` | `USE_KEYCLOAK=false` |
| `mvp/docker-compose.dev.yml:112` | `USE_KEYCLOAK=false` |
| `mvp/docker-compose.tst.yml:66` | `USE_KEYCLOAK=false` |
| Produktion | **nicht im Repo** — SaltStack-Compose, Secrets aus Passbolt-gestütztem Pillar (`docs/DEPLOYMENT.md:133`, `:152`) |

**Konsequenz:** Realm, Issuer, Client-ID und Client-Secret stehen an *keiner* Stelle in
diesem Repository. Sie kommen ausschließlich als Umgebungsvariablen
(`Keycloak__Authority`, `Keycloak__ClientId`, `Keycloak__ClientSecret`) aus einer Datei,
die im SaltStack-Repo der Verdigado liegt und auf die dieses Projekt keinen Schreibzugriff
hat.

Fest verdrahtet im Code sind dagegen:

- `options.CallbackPath = "/signin-oidc"` (`Program.cs:74`)
- die Scopes `openid`, `profile`, `email` (`Program.cs:70–72`)
- `ValidIssuer = Authority` und `ValidAudience = ClientId` (`Program.cs:122–127`)
- ein Redirect-URI-Rewrite, das das Schema hart auf `https` setzt (`Program.cs:78–86`)

#### Wie viele Stellen ändern sich bei einem anderen IdP oder einem zweiten Realm?

Die Antwort fällt scharf auseinander:

**Anderer IdP / anderer Realm, aber weiterhin genau einer:**
**null Zeilen Anwendungscode.** Der BFF spricht generisches OIDC über den
Microsoft-Standard-Handler. Es ändern sich drei Umgebungsvariablen im Salt-Pillar. Der
einzige denkbare Codeeingriff ist das Claim-Mapping, falls ein IdP `sub` oder `name`
anders benennt — die Extraktion liegt gekapselt in `ClaimUtilities`
(`Program.cs:683–698`), das ist eine Klasse mit zwei Methoden.

**Ein zweiter Realm / zweiter IdP parallel zum bestehenden:** deutlich mehr. Betroffen
wären mindestens:

| Datei | Was |
| --- | --- |
| `mvp/backend/BFF/Program.cs:64–128` | zweites `AddOpenIdConnect`-Scheme mit eigenem Namen und eigenem `CallbackPath` |
| `mvp/backend/BFF/Program.cs:39` | Verzweigung, die heute binär ist, muss mehrwertig werden |
| `mvp/backend/BFF/Controllers/AuthController.cs:109–121` | `Challenge()` hängt hart an `OpenIdConnectDefaults.AuthenticationScheme`; das Scheme muss Parameter werden |
| `mvp/backend/BFF/Controllers/AuthController.cs:123–144` | Logout unterscheidet heute nur `auth_method == "keycloak"` gegen „alles andere“ |
| `mvp/backend/BFF/Controllers/AuthController.cs:30–40` + `Models/ManagedUser.cs:48–58` | `AuthModesResponse` ist ein Zwei-Bool-DTO und müsste eine Liste werden |
| `src/app/login/login-selector.component.ts:8–11`, `.html` | `AuthModes`-Interface und die zwei fest gerenderten Kacheln |
| `src/environments/environment*.ts` + `replace-env.sh` | `useKeycloak` als String-Bool trägt keinen dritten Zustand |

Grob: **7 Dateien, 2 DTOs, 1 Frontend-Komponente.**

#### Der bereits vorhandene zweite Pfad

Wichtig für alles Weitere: neben Keycloak existiert bereits eine vollständige
**hauseigene Passwort-Anmeldung**, die niemand mehr „Dummy-Auth“ nennen sollte:

- `mvp/backend/BFF/Services/ManagedUserService.cs` (202 Zeilen) — BCrypt-Prüfung,
  5-Minuten-Cache, Rate-Limit von 5 Fehlversuchen je 15 Minuten
- `mvp/backend/BFF/Models/ManagedUser.cs` — `email`, `passwordHash`, `displayName`,
  `userId`, `createdAt`, `isAdmin`
- `mvp/backend/BFF/Controllers/AuthController.cs:43–104` — `POST /api/auth/login/managed`
- `mvp/config/managed-users.json` — die Nutzerbasis, **eine im Repo eingecheckte
  JSON-Datei** (`.gitignore:15` nimmt sie ausdrücklich von der Ignore-Regel aus)
- `mvp/config/generate-user-config.py` — erzeugt diese Datei aus einer lokalen
  `user-passwords.txt` im Format `email:passwort:anzeigename`
- Mount: `./config:/config:ro` in `docker-compose.dev.yml:114` und `.tst.yml:69`

Dieser Pfad ist **read-only by design**: eine gemountete Datei, ein Cache, keinerlei
Schreibpfad. Es gibt keine Anlege-, Ändere- oder Lösch-Funktion für Nutzer. Neue Accounts
entstehen heute, indem jemand lokal ein Skript laufen lässt und die erzeugte JSON-Datei
auf den Server bringt.

Und: die Zweige schließen sich **nicht** vollständig aus. Bei `USE_KEYCLOAK=true` wird das
Cookie-Scheme ebenfalls registriert, `ManagedUserService` wird unbedingt in den
DI-Container gelegt (`Program.cs:190–192`), und `AuthController.LoginManaged` meldet in genau
dieses Cookie-Scheme an. **Keycloak und die hauseigene Anmeldung können heute schon
parallel laufen** — die Login-Auswahlseite ist bereits darauf ausgelegt und zeigt beide
Kacheln (`src/app/login/login-selector.component.html:45–90`). Das ist die
architektonisch wichtigste Einzelbeobachtung dieser Bestandsaufnahme.

#### Sicherheitsrelevante Nebenwirkung des Schalters

Bei `USE_KEYCLOAK=false` entfällt die Autorisierungs-Pipeline vor dem Proxy
(`Program.cs:527`: schlichtes `app.MapReverseProxy()`). Nicht authentifizierte Anfragen an
geschützte Endpunkte werden dann **weitergeleitet**, es wird lediglich eine Warnung
geloggt (`Program.cs:280–283`). Dass sie trotzdem scheitern, liegt allein daran, dass die
Schreib-Endpunkte im Python-Backend den Header verpflichtend deklarieren
(`x_user: str = Header(...)`, z. B. `api/v1/statement.py:97`) und FastAPI ohne ihn mit 422
antwortet. Das ist ein Zufallstreffer, kein Gate.

**Jede Option, die Keycloak in Produktion abschaltet, muss diesen Zweig angleichen.** Das
sind rund 30 Zeilen in `Program.cs:489–528`, aber sie dürfen nicht vergessen werden.

#### Der Weg der Identität durch den Stack

```
Browser ──Cookie "ContentGruenAuthCookie"──▶ BFF
                                             │  ClaimUtilities.GetUserId()  → "sub" | NameIdentifier
                                             │  ClaimUtilities.GetUserName() → Name | "name" | GivenName
                                             ▼
                              YARP-Transform (Program.cs:243–283)
                                             │  Header  X-User: <sub>
                                             │  Header  X-Is-Admin: true   (nur wenn Admin-Claim)
                                             ▼
                                     Python Semantic-Search-Service
```

Das Python-Backend sieht **nur** den String in `X-User`. Es gibt dort kein Token, keine
Signaturprüfung, keine IdP-Kenntnis. Validiert wird der String rein syntaktisch in
`app/auth/authorization.py:16–51`: 2 bis 100 Zeichen, Zeichenklasse
`^[a-zA-Z0-9._@-]+$`.

**Konkrete Stolperfalle für jede Self-Registration-Option:**
`check_user_permissions` (`app/auth/authorization.py:54–93`) verweigert Schreiboperationen,
wenn die User-ID eine der Zeichenketten `admin`, `root`, `system`, `test123`, `guest`
enthält. Sobald eine E-Mail-Adresse als User-ID dient, kann jemand mit
`administration@…` oder `guesthouse@…` sich anmelden, aber nichts beitragen. Wer eine
E-Mail-basierte ID einführt, muss diese Prüfung anfassen.

Der Cookie ist `HttpOnly`, `SameSite=None`/`Secure=Always` im Keycloak-Zweig
(`Program.cs:57–59`) und `SameSite=Lax`/`SameAsRequest` im lokalen Zweig
(`Program.cs:134–136`). In Produktion liegen Frontend
(`contentgruen.netzbegruenung.de`) und BFF (`bff.contentgruen.netzbegruenung.de`) unter
derselben registrierbaren Domain (`docs/DEPLOYMENT.md:123–125`); `Lax` ist damit
cross-origin, aber same-site und funktioniert. Die DataProtection-Keys liegen auf einem
Volume `/keys` (`Program.cs:368–370`), damit Cookies einen Container-Neustart überleben.

---

### 1.2 Was an der Identität hängt

**Es gibt keine Nutzertabelle.** Weder in PostgreSQL noch in Qdrant. Die externe ID ist
zugleich der Primärschlüssel, der Fremdschlüssel und der Anzeigename.

#### In Qdrant (Content)

`BaseContentDbEntry` (`app/domain/models/base_content.py:42–100`) trägt drei
identitätsführende Felder:

| Feld | Typ | Inhalt |
| --- | --- | --- |
| `original_author` | `str` | roher `X-User`-Wert |
| `last_modified_by` | `str` | roher `X-User`-Wert |
| `authors` | `List[AuthorEntry]` | `AuthorEntry(name=<X-User>)` — **kein** separater Klarname |

Gesetzt wird das in jedem Content-Service identisch, jeweils aus demselben `author`-String:
`services/content/statement_service.py:158–160`,
`services/content/reference_service.py:128–130`,
`services/content/commentary_service.py:131–133`,
`services/content/generic_text_service.py:94–96`,
`api/v1/image.py:99–101`, `api/v1/post.py:111–113`.

Abgefragt wird es über einen Qdrant-Payload-Filter auf `original_author`
(`repositories/implementations/qdrant/base_repository.py:319` in `get_by_author`,
`:389` in `get_count_by_author`). Das ist die Grundlage von „Meine Beiträge“
(`api/v1/contribution.py:25–49`, Frontend `src/app/contributions-view/`).

#### In PostgreSQL (Interaktion)

| Tabelle | Spalte | Definiert in |
| --- | --- | --- |
| `votes` | `user_id VARCHAR(255) NOT NULL`, `UNIQUE(user_id, content_id)`, drei Indizes darauf | `repositories/vote_repository.py:23–34` |
| `usage_events` | `user_id` (optional), zusätzlich `session_id` für anonyme Nutzung | `repositories/usage_tracking_repository.py:28–83` |
| Content-Reports | Reporter-Kennung | `repositories/content_report_repository.py` |

`get_user_statistics` (`usage_tracking_repository.py:137 ff.`) verknüpft beide Welten: es
zählt Nutzungsereignisse zu Inhalten, deren `original_author` in Qdrant der User-ID
entspricht. Die Verknüpfung ist ein **String-Vergleich über zwei Datenbanken hinweg**.

#### Die daraus folgende Kernaussage

> Die Nutzeridentität ist eine **externe, undurchsichtige Zeichenkette ohne jede
> Indirektion**. Sie ist in Qdrant-Payloads und in PostgreSQL-Spalten dupliziert, an
> mindestens 8 Schreibstellen und 5 Lesestellen. Es gibt keine Mapping-Tabelle, keinen
> internen Surrogatschlüssel und keinen Ort, an dem ein Wechsel der Identität abgefangen
> werden könnte.

Praktisch heißt das: Ein Wechsel des Identitätsanbieters ändert den `sub` jedes Nutzers.
Ohne eine vorgeschaltete Mapping-Tabelle verlieren damit **alle** bestehenden Beiträge,
Stimmen und Statistiken ihre Zuordnung. Das betrifft jede Option unten außer der
Minimalvariante von (f) und der Client-Variante von (a).

Die Gegenmaßnahme ist in allen Fällen dieselbe und ist **unabhängig von der
Optionswahl**: eine Nutzertabelle im BFF, die eine stabile interne ID auf ein oder mehrere
`(issuer, subject)`-Paare abbildet, sowie das Setzen dieser internen ID in `X-User` statt
des rohen `sub`. Das ist der einzige Codeeingriff, der sich für jede der sechs Optionen
lohnt, und der einzige, der die Reversibilität aller anderen Entscheidungen deutlich
erhöht. Aufwand grob **10–16 h** (Tabelle, Repository, Anpassung von
`ClaimUtilities`/Transform, Rückschreiben der bestehenden Werte).

---

### 1.3 Welche Nutzerdaten die Anwendung braucht

| Datum | Wird heute gebraucht? | Woher heute | Wo verwendet |
| --- | --- | --- | --- |
| Stabile ID | **ja, zwingend** | Keycloak `sub`, bzw. `userId` aus `managed-users.json` | `X-User`, `original_author`, `votes.user_id` |
| Anzeigename | ja, für die Oberfläche | Claims `name`/`given_name`, bzw. `displayName` | `/api/user-info` → `UserInfo.userName` (`src/app/auth/auth.service.ts:7–13`), Kopfzeile |
| Admin-Kennzeichen | ja | Claim `isAdmin`/`role=admin`, bzw. `isAdmin` in der JSON | `X-Is-Admin` (`Program.cs:265–272`), `require_admin` (`dependencies.py:219–235`), `AdminGuard` |
| E-Mail | **nein** | Scope `email` wird angefordert, `ManagedUser.Email` existiert | wird nirgends gelesen außer als Login-Kennung im hauseigenen Pfad |
| Rolle/Zuordnung („KV Bayreuth“) | **existiert nicht** | — | — |

Drei Feststellungen dazu:

1. **Der Anzeigename wird nirgends persistiert.** Was an einem Beitrag als Autor steht,
   ist die User-ID selbst (`AuthorEntry(name=author)`, siehe oben). Bei Keycloak ist das
   eine UUID. Wenn an Inhalten je ein lesbarer Name oder eine Zuordnung erscheinen soll,
   ist das ein eigenes Vorhaben — unabhängig von der Frage, wer sich registrieren darf.
2. **Eine Organisations-/Gliederungszuordnung gibt es im Datenmodell überhaupt nicht.**
   Die einzige Erwähnung eines Kreisverbands im gesamten Code ist der Fließtext der
   Beta-Zugangs-Anfrage (`login-selector.component.html:30`). Wenn „KV Bayreuth“ als
   Attribution gewünscht ist, muss das Feld erst geschaffen werden — im BFF-Profil, im
   Qdrant-Payload und in der Anzeige.
3. **Die E-Mail-Adresse ist heute funktional überflüssig.** Sie wird angefordert, aber
   nicht verwendet. Sobald eine der Optionen (c), (d) oder (f) kommt, wird sie zum
   tragenden Datum — mit den entsprechenden datenschutzrechtlichen Folgen.

#### Kein Mailversand im gesamten Stack

Eine Suche über `mvp/` nach `smtp`, `MailKit`, `aiosmtplib`, `fastapi_mail`, `email.mime`
liefert **keinen einzigen Treffer**. `BFF.csproj` enthält keine Mail-Bibliothek. Der
Anwendung fehlt jede Fähigkeit, eine E-Mail zu versenden.

Das ist die härteste technische Randbedingung dieser Entscheidung: **Optionen (c), (d) und
die Ausbaustufe von (f) setzen einen Baustein voraus, den es nicht gibt** — Bibliothek,
SMTP-Relay oder Versanddienst, SPF-/DKIM-/DMARC-Einträge auf der Absenderdomain,
Zustellungsüberwachung und Bounce-Behandlung. Die Optionen (a), (b) und (e) verlagern
genau diesen Baustein an den Identitätsanbieter.

#### Vorhandenes, auf das aufgebaut werden kann

- Moderation: Meldefunktion, Report-Tabelle, Admin-Oberfläche unter `src/app/admin/`
  (`content-moderation`, `mvp-dashboard`), `require_admin`, Sichtbarkeits- und
  Statusmodell (`ContentStatus`, `ContentVisibility`).
- Rate-Limiting: `middleware/rate_limit.py` (10/Min., 100/Std. auf Anlage-Endpunkte,
  Schlüssel ist der `X-User`-Header), `utils/rate_limiter.py` für Meldungen.
- Login-Fehlversuchs-Bremse im BFF (`ManagedUserService.cs:82–114`).

Für eine öffentliche Anmeldung ist das eine brauchbare, aber nicht ausreichende Basis: das
Rate-Limit schlüsselt auf `X-User`, ist also pro Konto wirksam, nicht gegen die massenhafte
Anlage neuer Konten. Ein Registrierungs-Endpunkt bräuchte eine eigene, IP-basierte Bremse.

---

### 1.4 Zusammenfassung der Änderungsfläche

| Fläche | Dateien | Bewertung |
| --- | --- | --- |
| Ein IdP gegen einen anderen tauschen | 0 Code, 3 Env-Variablen im Salt-Pillar | trivial |
| Claim-Abweichungen eines anderen IdP | `Program.cs:683–698` | klein, gekapselt |
| Zweiter IdP parallel | 7 Dateien, 2 DTOs, 1 Frontend-Komponente | mittel |
| Keycloak in Produktion abschalten | zusätzlich `Program.cs:489–528` | klein, aber sicherheitsrelevant |
| Nutzer schreibend verwalten | `ManagedUserService` komplett, neue Tabelle | groß — heute existiert kein Schreibpfad |
| Identität wechselfest machen | neue Nutzertabelle + `X-User`-Belegung | 10–16 h, für alle Optionen sinnvoll |
| Mailversand | existiert nicht | eigener Baustein |

---

## 2. Phase 2 — Optionen

Alle Aufwände sind Entwicklungsstunden für eine mit dem Code vertraute Person,
einschließlich Anpassung der bestehenden Tests, **ohne** Wartezeit auf Dritte, ohne
Redaktion der Rechtstexte und ohne Design. Wartezeit auf externe Zuständigkeiten ist
separat als Kalenderzeit ausgewiesen, weil sie sich nicht durch Mehrarbeit verkürzen lässt.

---

### (a) Eigener Realm oder eigener Client mit Self-Registration im bestehenden Keycloak

Zwei deutlich verschiedene Untervarianten, die getrennt zu bewerten sind.

#### (a1) Eigener Client im bestehenden Realm `user.netzbegruenung.de`

**Beschreibung.** Gut gesagt bekommt einen eigenen OIDC-Client, damit
Branding, Redirect-URIs und Scopes unabhängig sind. Self-Registration ist damit **nicht**
erreichbar: „User registration“ ist in Keycloak eine **Realm**-Einstellung, kein
Client-Attribut. Sie einzuschalten öffnet die Registrierung für *alle* Anwendungen, die an
diesem Realm hängen — also für die gesamte Netzbegrünung-Landschaft.

**Code-Änderungen.** Keine. `Keycloak__ClientId` und `Keycloak__ClientSecret` im Pillar.
**Infrastruktur/Salt.** Zwei Pillar-Werte, ein Neustart des BFF-Containers.
**Externe Zuständigkeit.** Client-Anlage und Secret-Hinterlegung beim Verdigado-Team.
Für Self-Registration: eine Realm-weite Entscheidung, die dieses Projekt nicht treffen kann
und die realistischerweise abgelehnt wird.
**Aufwand.** 1–2 h. Kalenderzeit für die Client-Anlage: Tage bis Wochen.
**Betriebsaufwand.** Unverändert null.
**Reversibilität.** Vollständig — zwei Pillar-Werte zurücksetzen.
**Recht.** Unverändert. Keine öffentliche Anmeldung, also keine neuen Pflichten.

**Fazit:** löst das gestellte Problem nicht. Nur relevant, falls man Branding und
Redirect-Kontrolle vom Zugangsmodell trennen will.

#### (a2) Eigener Realm `gutgesagt` auf derselben Keycloak-Instanz

**Beschreibung.** Ein zweiter Realm mit eigener Registrierung, eigenem Branding, eigener
Passwort-Policy und eigener Mailkonfiguration. Optional per Identity Brokering an den
bestehenden Realm gekoppelt, damit Netzbegrünung-Mitglieder ihren Account weiter nutzen.

**Code-Änderungen.**
- Ohne Brokering, wenn der neue Realm der *einzige* IdP wird: **keine**. Nur
  `Keycloak__Authority` auf die neue Realm-URL.
- Mit Parallelbetrieb beider Realms: die 7 Dateien aus [1.1](#wie-viele-stellen-ändern-sich-bei-einem-anderen-idp-oder-einem-zweiten-realm)
  (`Program.cs`, `AuthController.cs`, `Models/ManagedUser.cs`,
  `login-selector.component.{ts,html}`, `environment*.ts`, `replace-env.sh`).
- Mit Brokering statt Parallelbetrieb: wieder **keine** — die Anbieterauswahl passiert dann
  in Keycloak, nicht in unserem Frontend. Dafür kommt der `sub` aus dem neuen Realm,
  also andere IDs für alle bestehenden Nutzer.

**Infrastruktur/Salt.** `Keycloak__Authority` im Pillar. Im Keycloak selbst: Realm anlegen,
Registrierungsformular konfigurieren, E-Mail-Verifikation aktivieren, SMTP des Realms
einrichten, Theme/Branding auf GutGesagt, Brute-Force-Schutz, ggf. reCAPTCHA gegen
Bot-Registrierungen, ggf. Identity Provider zum Alt-Realm.
**Externe Zuständigkeit.** **Hoch und dauerhaft.** Realm-Anlage, jede spätere Änderung an
Registrierungsfeldern, Mailtexten, Theme oder Policy läuft über das Verdigado-Team. Auch
Nutzerverwaltung (Sperren, Löschen, Auskunft nach Art. 15 DSGVO) findet in deren
Administrationsoberfläche statt.
**Aufwand.** Eigene Entwicklung 2–4 h (nur Realm ohne Parallelbetrieb) bis 12–20 h
(Zwei-Realm-Parallelbetrieb im Frontend). Der eigentliche Aufwand liegt beim Realm-Setup
und ist fremd. Kalenderzeit: Wochen.
**Betriebsaufwand danach.** Gering im eigenen Team — kein eigener Serverdienst, kein
eigener Mailversand, kein eigener Passwort-Reset-Support. Alles Betriebliche liegt beim
Realm-Betreiber. Das ist zugleich der Vorteil und die Abhängigkeit.
**Reversibilität.** Mittel. Die Nutzerbasis liegt in fremder Hand. Ein späterer Wegzug
bedeutet Export aus dem Realm (nur mit Kooperation) und neue `sub`-Werte.
**Recht.** Es entsteht eine öffentliche Anmeldung, also greift der volle Katalog aus
[Abschnitt 3](#3-querschnitt-datenschutz-impressum-nutzungsbedingungen). Zusätzlich
projektspezifisch: die Nutzerkonten liegen bei einem Dritten. Verantwortlichkeit und
Auftragsverarbeitung nach Art. 28 DSGVO zwischen dem Betreiber von GutGesagt und
Netzbegrünung/Verdigado sind schriftlich zu klären; die Datenschutzerklärung muss den
Identitätsanbieter benennen.

---

### (b) Eigene Keycloak-Instanz oder anderer IdP

**Beschreibung.** Ein selbst betriebener Identitätsanbieter — Keycloak, Authentik, Zitadel
— unter einer eigenen Subdomain. Alternativ ein gehosteter Anbieter (Auth0, Ory Network,
Clerk), was die Betriebsfrage gegen eine neue Drittabhängigkeit und laufende Kosten tauscht.

**Code-Änderungen.** Praktisch keine, und das ist die Pointe: der BFF spricht generisches
OIDC. Es ändern sich `Keycloak__Authority`, `Keycloak__ClientId`, `Keycloak__ClientSecret`.
Realistisch dazu:
- `mvp/backend/BFF/Program.cs:683–698` — Claim-Mapping, falls der IdP `sub` oder `name`
  anders liefert. Zwei Methoden.
- `mvp/backend/BFF/Program.cs:74` — `CallbackPath`, falls sich die Redirect-URI ändern soll.
- Kosmetik: die Sektion heißt weiterhin `Keycloak`, die Frontend-Kachel heißt
  „Netzbegrünung Login / SSO über Keycloak“ (`login-selector.component.html:52–53`). Rein
  redaktionell, aber sonst irreführend.

**Infrastruktur/Salt.** Substanziell: Container plus eigene Datenbank im Salt-Compose,
DNS-Eintrag, nginx-Server-Block, TLS-Zertifikat, Backup des IdP-Datenbestands zusätzlich zu
den bestehenden zwei Datenbanken (`mvp/scripts/backup/backup.sh` deckt heute Qdrant und
PostgreSQL ab, nicht einen dritten Dienst), SMTP-Anbindung für Verifikation und
Passwort-Reset, Monitoring. `docs/DEPLOYMENT.md` und `docs/ARCHITECTURE.md` beschreiben
danach eine andere Topologie.
**Externe Zuständigkeit.** **Einmalig hoch, danach gering.** Server, Salt-States und nginx
gehören dem Verdigado-Admin-Team; ohne die geht kein neuer Dienst auf die Maschine. Nach
dem Aufsetzen ist die inhaltliche Kontrolle über Realm, Registrierung, Branding und
Nutzerverwaltung vollständig beim Projekt.
**Aufwand.** 24–48 h für Aufsetzen, Härtung, Anbindung, Test in allen drei Umgebungen,
Dokumentation. Bei einem gehosteten Anbieter eher 8–16 h.
**Betriebsaufwand danach.** **Der höchste aller Optionen.** Ein eigener IdP ist ein
sicherheitskritischer, dauerhaft zu patchender Dienst mit Datenbank, Backup, Migration bei
Major-Upgrades und Nutzer-Support. Bei einem gehosteten Anbieter fällt das weg, dafür
kommen Kosten und Vertragsbindung.
**Reversibilität.** Mittel bis gut. Die Nutzerbasis gehört dem Projekt und ist exportierbar;
ein Wechsel des IdP ändert aber wieder die `sub`-Werte (siehe [1.2](#12-was-an-der-identität-hängt)).
**Recht.** Voller Katalog aus Abschnitt 3. Bei Eigenbetrieb ist das Projekt allein
verantwortlich — kein Auftragsverarbeitungsvertrag nötig, dafür volle Verantwortung für
Passwort-Speicherung, Protokollierung und Löschkonzept. Bei einem gehosteten Anbieter
umgekehrt: Auftragsverarbeitungsvertrag zwingend, bei US-Anbietern zusätzlich die
Drittlandthematik.

---

### (c) Self-Registration mit E-Mail-Verifikation in der eigenen Anwendung

**Beschreibung.** Kein IdP. Die Registrierung wird ausgebaut auf dem bereits existierenden
hauseigenen Anmeldepfad: Formular, Bestätigungsmail mit Token, Aktivierung, Login mit
E-Mail und Passwort.

**Code-Änderungen.** Der größte Umbau von allen. Der bestehende Pfad ist eine
schreibgeschützt gemountete JSON-Datei und muss auf eine Datenbank umgestellt werden.

| Datei | Änderung |
| --- | --- |
| `mvp/backend/BFF/Services/ManagedUserService.cs` | vollständig umgebaut: Datenbank statt Datei, Cache entfällt, Schreiboperationen kommen dazu |
| `mvp/backend/BFF/Models/ManagedUser.cs` | Felder `IsVerified`, `VerificationToken`, `TokenExpiresAt`, `PasswordResetToken` |
| `mvp/backend/BFF/Controllers/AuthController.cs` | neue Aktionen `register`, `verify`, `resend-verification`, `forgot-password`, `reset-password` — oder besser ein eigener `RegistrationController.cs` |
| `mvp/backend/BFF/Services/` | neu: `EmailService.cs` — heute existiert **nichts** davon |
| `mvp/backend/BFF/BFF.csproj` | neu: Mail-Bibliothek und Datenbanktreiber (BFF hat heute **keine** Datenbankanbindung) |
| `mvp/backend/BFF/Program.cs:489–528` | Autorisierungs-Pipeline auch im Nicht-Keycloak-Zweig (siehe 1.1) |
| `mvp/config/managed-users.json`, `generate-user-config.py`, Compose-Mounts | entfallen bzw. werden zum einmaligen Import |
| `mvp/docker-compose.{dev,tst}.yml` | Datenbank-Zugangsdaten und SMTP-Konfiguration für das BFF |
| `src/app/login/` | neue Registrierungs-Komponente, Verifikations-Seite, Passwort-vergessen-Seite, Routen in `app.routes.ts` |
| `src/app/login/login-selector.component.html:1–37` | der ganze Erklärblock „Aktuell ist keine Selbstregistrierung möglich“ entfällt |
| `app/auth/authorization.py:54–93` | `suspicious_patterns` kollidiert mit E-Mail-basierten IDs (siehe 1.1) |

Zusätzlich zwingend, weil öffentlich erreichbar: IP-basiertes Rate-Limit auf den
Registrierungs-Endpunkt (das vorhandene Limit schlüsselt auf `X-User` und greift hier
nicht), Schutz vor Konto-Enumeration bei „Passwort vergessen“, Bot-Abwehr.

**Infrastruktur/Salt.** Das BFF bekommt erstmals eine Datenbank — entweder ein eigenes
Schema in der bestehenden `contentgruen_app` oder ein eigener Dienst; Backup-Skript
erweitern. SMTP-Relay oder Versanddienst, Absenderdomain mit SPF/DKIM/DMARC, Pillar-Werte
für die Zugangsdaten.
**Externe Zuständigkeit.** **Die geringste aller Optionen im laufenden Betrieb.** Nötig ist
ein Versandweg für E-Mails und die DNS-Einträge der Absenderdomain. Kein fremder
Identitätsanbieter, keine fremde Realm-Verwaltung, keine fremde Nutzerbasis.
**Aufwand.** 40–70 h. Untere Grenze bei Verzicht auf Passwort-Reset im ersten Wurf
(riskant, erzeugt Support-Last), obere Grenze mit Reset, Bot-Abwehr und Kontolöschung.
**Betriebsaufwand danach.** Mittel bis hoch, aber anders gelagert als bei (b): kein
Serverdienst zu patchen, dafür Mailzustellbarkeit (Bounces, Spam-Ordner, Blacklisting),
Spam-Registrierungen und persönlicher Support bei Anmeldeproblemen. Zu bedenken: es gibt
laut `STATUS.md` noch keine produktive Beobachtbarkeit — Zustellprobleme fielen zunächst
gar nicht auf.
**Reversibilität.** Gering bis mittel. Der Code ist zurückbaubar, die Nutzerbasis ist es
nicht: Passwörter sind BCrypt-Hashes und lassen sich nicht zu einem IdP migrieren, ohne
dass alle Betroffenen ein neues Passwort setzen.
**Recht.** Die höchsten Anforderungen aller Optionen, weil das Projekt Passwörter und
E-Mail-Adressen selbst verarbeitet. Double-Opt-In ist zu dokumentieren (Zeitpunkt,
IP-Adresse — die wiederum selbst personenbezogen ist und eine Löschfrist braucht),
Löschkonzept, Auskunftsverfahren, TOM-Beschreibung. Die vorhandene Datenschutzerklärung
beschreibt unter „Registrierung auf dieser Website“
(`datenschutz.component.html:126–140`) bereits genau diesen Fall — sie ist derzeit
inhaltlich unzutreffend, weil es keine Selbstregistrierung gibt, und würde durch diese
Option erstmals korrekt.

---

### (d) Login per Magic Link ohne Passwort

**Beschreibung.** Wie (c), aber es gibt kein Passwort. Nutzer geben ihre E-Mail-Adresse
ein und erhalten einen einmalig gültigen, kurzlebigen Anmeldelink.

**Code-Änderungen.** Dieselbe Liste wie (c) mit drei Unterschieden:
- **entfällt:** BCrypt-Prüfung (`ManagedUserService.cs:116–163`), Passwort-Reset,
  Passwortfeld im Formular, Passwort-Policy
- **entfällt:** die Fehlversuchs-Bremse in ihrer heutigen Form
  (`ManagedUserService.cs:82–114`) — es gibt kein Passwort zum Erraten
- **kommt hinzu:** Token-Modell mit kryptografisch zufälligem Wert, kurzer Gültigkeit
  (5–15 Min.), Einmalverbrauch, Bindung an die anfragende Sitzung gegen Weiterleitungs-
  Missbrauch, sowie ein Verhalten, das nicht verrät, ob eine Adresse registriert ist

`BFF.csproj` braucht weiterhin Mail-Bibliothek und Datenbanktreiber; `EmailService.cs`
ist weiterhin neu zu bauen. Das Frontend wird schlanker (ein Feld statt vier Formulare).

**Infrastruktur/Salt.** Identisch zu (c).
**Externe Zuständigkeit.** Identisch zu (c) — nur der Versandweg.
**Aufwand.** 30–55 h. Etwa 20–25 % unter (c), weil Passwort-Reset, Passwortwechsel und
Passwort-Policy komplett entfallen — das ist erfahrungsgemäß der aufwendigste Teil von (c).
**Betriebsaufwand danach.** Mittel. Weniger Support („Passwort vergessen“ verschwindet als
Kategorie), aber ein neues Klumpenrisiko: **der Mailversand ist der einzige Anmeldepfad.**
Eine Zustellstörung oder ein Spam-Filter-Problem ist kein Komfortproblem, sondern ein
Totalausfall der Anmeldung für Betroffene. Ohne produktive Beobachtbarkeit ist das schwer
zu bemerken. Hinzu kommt die Nutzererwartung: Magic Links sind auf Mobilgeräten
gewöhnungsbedürftig, weil der Link im Mail-Programm-Browser landet und die Sitzung dort
entsteht statt in der eigentlichen App.
**Reversibilität.** Gut. Es gibt keine Passwörter, also nichts, was einer späteren
Migration zu einem IdP im Weg steht: Nutzer werden über die E-Mail-Adresse
wiedererkannt, sofern die Mapping-Tabelle aus [1.2](#12-was-an-der-identität-hängt)
existiert. **Von den drei Eigenbau-Optionen ist das die am leichtesten rückabwickelbare.**
**Recht.** Wie (c), mit einer Erleichterung: keine Passwortspeicherung, also entfallen die
Anforderungen an Passwort-Hashing und -Policy. Der Rest bleibt, einschließlich
Protokollierung der Anmeldelinks und deren Löschfrist.

---

### (e) Social-/OIDC-Login über Dritte

**Beschreibung.** Anmeldung über bestehende Konten bei Dritten — Google, Apple, GitHub,
oder thematisch näher: ein Fediverse-/Mastodon-Anbieter.

**Code-Änderungen.** Technisch die Zwei-IdP-Variante aus [1.1](#wie-viele-stellen-ändern-sich-bei-einem-anderen-idp-oder-einem-zweiten-realm),
und zwar in ihrer offenen Form — nicht zwei Anbieter, sondern n:
- `mvp/backend/BFF/Program.cs:39–128` — ein Authentication-Scheme je Anbieter, jeweils
  mit eigenem `CallbackPath`; die heutige Bool-Verzweigung wird zur Anbieterliste
- `mvp/backend/BFF/Controllers/AuthController.cs:109–121` — `Challenge()` mit Scheme als
  Parameter statt hart verdrahtet; `:123–144` — Logout je Anbieter
- `mvp/backend/BFF/Controllers/AuthController.cs:30–40`,
  `mvp/backend/BFF/Models/ManagedUser.cs:48–58` — `AuthModesResponse` von zwei Bools auf
  eine Liste
- `src/app/login/login-selector.component.{ts,html}` — Kacheln aus der Liste rendern
- `mvp/backend/BFF/Program.cs:683–698` — Claim-Mapping je Anbieter; die Anbieter liefern
  `sub`, `name` und `email` unterschiedlich, GitHub etwa hat kein OIDC im engeren Sinn
- **zwingend:** die Mapping-Tabelle aus [1.2](#12-was-an-der-identität-hängt). Ohne sie
  ist ein Nutzer, der beim nächsten Mal die andere Kachel drückt, ein neuer Nutzer und
  sieht seine eigenen Beiträge nicht mehr. Bei (a)–(d) ist die Tabelle empfehlenswert,
  hier ist sie Voraussetzung.

**Infrastruktur/Salt.** Kein neuer Dienst, kein Mailversand. Je Anbieter ein Client-Secret
im Pillar und eine registrierte Redirect-URI.
**Externe Zuständigkeit.** **Hoch und dauerhaft, verteilt auf mehrere Parteien.** Je
Anbieter eine Entwickler-Registrierung, ein Konto, Zustimmung zu dessen
Nutzungsbedingungen, ggf. ein Review-Verfahren (Apple, teils Google) und die dauerhafte
Möglichkeit, dass der Anbieter Bedingungen ändert oder den Zugang entzieht.
**Aufwand.** 8–16 h für den ersten Anbieter einschließlich Umbau auf Mehrfach-Schemes,
danach 3–6 h je weiterem Anbieter. Plus 10–16 h für die Mapping-Tabelle, hier nicht
optional.
**Betriebsaufwand danach.** Gering im Alltag — kein eigener Dienst, kein Mailversand, kein
Passwort-Support. Dafür punktuell unangenehm: Secret-Rotation, Ablauf von Zertifikaten,
einseitige Änderungen der Anbieter-API.
**Reversibilität.** Gut auf der Code-Seite, schlecht auf der Nutzer-Seite: Wer nur ein
Google-Konto hinterlegt hat, verliert bei Abschaltung dieses Anbieters den Zugang, solange
kein zweiter Anmeldeweg verknüpft ist.
**Recht.** **Die politisch heikelste Option.** GutGesagt ist eine Plattform für politische
Meinungsäußerung; die Anmeldedaten sagen etwas über die politische Betätigung der
Betroffenen aus, was in die Nähe von Art. 9 DSGVO rückt. Ein Social-Login teilt einem
Dritten mit, dass und wann sich eine bestimmte Person hier anmeldet. Bei US-Anbietern
kommen Drittlandtransfer und die entsprechenden Garantien hinzu; nötig sind eine
ausdrückliche Einwilligung vor dem ersten Kontakt mit dem Anbieter (also kein Vorab-Laden
von Anbieter-Ressourcen), eine Nennung in der Datenschutzerklärung und ein Cookie-Banner,
sobald Anbieter-Skripte eingebunden werden. Über das Rechtliche hinaus ist zu bedenken,
wie es wirkt, wenn eine grün geprägte Plattform „Weiter mit Google“ anbietet. Ein
Fediverse-Anbieter wäre thematisch stimmiger, technisch aber heterogen und für die
Zielgruppe außerhalb des Vereins vermutlich zu voraussetzungsreich.

---

### (f) Registrierungsanfrage mit manueller Freischaltung

**Beschreibung.** Interessierte stellen eine Anfrage, jemand prüft und schaltet frei. Das
ist **der heutige Zustand** — die Login-Auswahlseite trägt die Überschrift „Aktuell ist
keine Selbstregistrierung möglich“ und verweist auf eine `mailto:`-Adresse
(`login-selector.component.html:1–37`). Die Freischaltung erfolgt über
`generate-user-config.py` und `managed-users.json`.

Zwei Ausbaustufen mit sehr unterschiedlichem Profil.

#### (f1) Minimalvariante — Texte anpassen, Verfahren beibehalten

**Code-Änderungen.** Ausschließlich Frontend-Text:
`src/app/login/login-selector.component.html:22–31` — die Bedingung
„Mitgliedschaft bei Netzbegrünung“ und „nenne uns den Grünen Kreisverband, in dem du
Mitglied bist“ streichen bzw. auf das breitere Publikum umformulieren; Zeile 52–53 die
Kachelbeschriftung. Dazu die Umbenennung auf GutGesagt, wo sie ansteht.
**Infrastruktur/Salt.** Keine.
**Externe Zuständigkeit.** Ein funktionierendes Postfach. Sonst nichts.
**Aufwand.** 1–3 h.
**Betriebsaufwand danach.** **Wächst linear mit der Nutzerzahl und ist der Kern des
Problems.** Jeder einzelne Zugang bedeutet: Mail lesen, Passwort erzeugen, Skript laufen
lassen, JSON auf den Server bringen, BFF neu starten, Zugangsdaten per Mail
zurückschicken. Bei einem breiteren Publikum ist das nach kurzer Zeit nicht mehr
tragbar — und der Versand von Klartext-Passwörtern per E-Mail ist zudem schwer zu
verteidigen.
**Reversibilität.** Vollständig.
**Recht.** Der geringste Zusatzbedarf: keine öffentliche Anmeldung im technischen Sinn.
Trotzdem werden E-Mail-Adressen zweckgebunden verarbeitet und Konten geführt. Impressum
und Datenschutzerklärung sind unabhängig davon zu vervollständigen (siehe Abschnitt 3),
weil sie heute Platzhalter enthalten.

#### (f2) Ausbauvariante — Formular plus Freischaltung in der Admin-Oberfläche

**Code-Änderungen.**

| Datei | Änderung |
| --- | --- |
| `mvp/backend/BFF/Controllers/` | neu: Endpunkt zur Anfrage-Entgegennahme, öffentlich, IP-rate-limitiert |
| `mvp/backend/BFF/Services/ManagedUserService.cs` | Schreibpfad, Datenbank statt Datei (wie in (c)) |
| `mvp/backend/BFF/BFF.csproj` | Datenbanktreiber; Mail-Bibliothek, sobald Zugangsdaten automatisch versandt werden |
| `mvp/backend/BFF/Program.cs:489–528` | Autorisierungs-Pipeline im Nicht-Keycloak-Zweig |
| `src/app/admin/` | neuer Bereich neben `content-moderation` und `mvp-dashboard`; `AdminGuard` und `require_admin` sind vorhanden und nutzbar |
| `src/app/login/login-selector.component.html` | Formular statt `mailto:` |

**Infrastruktur/Salt.** Datenbank für das BFF; Mailversand, sobald die Freischaltung nicht
mehr händisch beantwortet wird.
**Externe Zuständigkeit.** Gering — dieselbe wie (c), nur ohne Verifikationsmail, solange
manuell geantwortet wird.
**Aufwand.** 20–35 h.
**Betriebsaufwand danach.** Bleibt personengebunden — die Prüfung selbst wird nicht
automatisiert, nur ihre Abwicklung verkürzt. Bei starkem Zulauf entsteht ein Rückstau, und
Wartezeit auf Freischaltung ist der wirksamste Abbruchgrund im gesamten Anmeldevorgang.
**Reversibilität.** Hoch. Der Anfrage-Endpunkt ist abschaltbar, ohne dass an der
Anmeldung selbst etwas hängt.
**Recht.** Wie (c) für die Anfragedaten, mit einem eigenen Punkt: eine manuelle
Zulassungsentscheidung ist eine begründungsbedürftige Auswahl. Die Nutzungsbedingungen
decken das bereits ab — „Ein Anspruch auf Registrierung oder Aufrechterhaltung eines
Nutzerkontos besteht nicht“ (`nutzungsbedingungen.component.html:65`). Zu ergänzen ist,
was mit abgelehnten Anfragen geschieht und wann deren Daten gelöscht werden.

---

## 3. Querschnitt: Datenschutz, Impressum, Nutzungsbedingungen

### 3.1 Ausgangslage im Repo

Alle drei Rechtstexte existieren als Angular-Komponenten und sind über die Fußzeile
erreichbar:

| Seite | Datei | Umfang | Zustand |
| --- | --- | --- | --- |
| Impressum | `src/app/impressum/impressum.component.html` | 143 Zeilen | **12 Platzhalter** in eckigen Klammern |
| Datenschutz | `src/app/datenschutz/datenschutz.component.html` | 240 Zeilen | **10 Platzhalter** |
| Nutzungsbedingungen | `src/app/nutzungsbedingungen/nutzungsbedingungen.component.html` | 270 Zeilen | Platzhalter im Datum; Zeile 264 trägt den Hinweis „Dies sind Platzhalter-Nutzungsbedingungen. Bitte lassen Sie diese von einem [Rechtskundigen] prüfen“ |

Unausgefüllt sind unter anderem Name und Anschrift des Anbieters, die
vertretungsberechtigte Person, Register und Registernummer, die Kontaktdaten der oder des
Datenschutzbeauftragten und die zuständige Aufsichtsbehörde.

**Das ist ein eigenständiger, von der Optionswahl unabhängiger Handlungsbedarf.** Ein
Impressum mit `[Vollständiger Name/Organisation]` ist bereits im heutigen Betrieb
angreifbar; mit einer öffentlichen Anmeldung wird es zum ernsten Risiko. Es sollte vor
jeder der sechs Optionen erledigt werden, nicht danach.

### 3.2 Was bei jeder öffentlichen Anmeldung hinzukommt

Unabhängig davon, welche Option gewählt wird, sobald sich Menschen ohne Vereinsbezug
selbst anmelden können:

**Impressum.** Der Anbieter muss vollständig benannt sein — Name/Organisation, Anschrift,
Vertretung, Kontakt, Register. Zusätzlich ist zu klären und sichtbar zu machen, **wer
GutGesagt eigentlich betreibt**: Netzbegrünung e.V. oder eine andere Trägerschaft. Solange
das ungeklärt ist, lässt sich keine der Rechtsseiten korrekt ausfüllen, und die Frage der
datenschutzrechtlichen Verantwortlichkeit bei Option (a) ist ebenfalls nicht beantwortbar.

**Datenschutzerklärung.** Zu ergänzen bzw. zu korrigieren:
- Der Abschnitt „Registrierung auf dieser Website“
  (`datenschutz.component.html:126–140`) beschreibt heute einen Vorgang, den es nicht
  gibt. Er wird mit (c), (d) oder (f2) erstmals zutreffend und muss auf die tatsächlich
  erhobenen Felder abgeglichen werden.
- Der eingesetzte Identitätsanbieter ist zu benennen — bei (a) Netzbegrünung/Verdigado,
  bei (b) der eigene oder gehostete Dienst, bei (e) jeder einzelne Drittanbieter.
- Rechtsgrundlage der Kontoführung (Art. 6 Abs. 1 lit. b DSGVO), Speicherdauer,
  Löschverfahren.
- Der Abschnitt „Kommentar- und Beitragsfunktion“ (`:143–150`) spricht vom „gewählten
  Nutzernamen“. Tatsächlich wird die rohe User-ID gespeichert
  (siehe [1.2](#12-was-an-der-identität-hängt)) — bei Keycloak eine UUID. Das ist zu
  korrigieren oder das Datenmodell entsprechend anzupassen.
- Protokolldaten des Anmeldevorgangs: IP-Adressen bei Double-Opt-In (c), Anmeldelinks (d)
  und Anfragedaten (f2) sind personenbezogen und brauchen eine Löschfrist.

**Nutzungsbedingungen.** Die vorhandenen Klauseln tragen den Fall bereits erstaunlich gut:
- § 3 Abs. 1: „Für die vollständige Nutzung der Plattform ist eine Registrierung
  erforderlich“ (`:53`)
- § 3 Abs. 4: kein Anspruch auf Registrierung (`:65`) — deckt (f) ab
- § 1 Abs. 3: Mindestalter 16 Jahre (`:19`)
- Moderations-, Sperr- und Kündigungsklauseln sind vorhanden

Nachzuziehen ist im Wesentlichen die **Beschreibung des Zugangsverfahrens** und die
Einwilligung in die Nutzungsbedingungen als Teil des Anmeldevorgangs (aktives Ankreuzen,
protokolliert). Bei einem breiteren Publikum ohne Vereinsbindung gewinnen außerdem die
Moderationsklauseln an praktischer Bedeutung: die vorhandene Meldefunktion und der
Admin-Bereich sind vorhanden, aber auf eine überschaubare, bekannte Nutzerschaft
zugeschnitten.

**Altersprüfung.** Das Mindestalter von 16 Jahren steht in den Bedingungen, wird technisch
aber nirgends erhoben. Bei einer offenen Anmeldung ist zumindest eine Bestätigung im
Formular üblich.

### 3.3 Rechtsfolgen im Vergleich

| Option | Wo liegen Konto und Passwort | Zusätzlich nötig |
| --- | --- | --- |
| (a1) | fremder Realm, kein neuer Zugang | nichts Neues |
| (a2) | fremder Realm | Verantwortlichkeit/Auftragsverarbeitung mit Verdigado klären, IdP benennen |
| (b) Eigenbetrieb | eigener Dienst | volle Eigenverantwortung, TOM, Löschkonzept, Backup des IdP |
| (b) gehostet | Dritter | Auftragsverarbeitungsvertrag, bei US-Anbieter Drittlandtransfer |
| (c) | eigene Datenbank | Double-Opt-In-Nachweis, Passwort-Sicherheit, Löschkonzept |
| (d) | eigene Datenbank, **keine Passwörter** | wie (c) ohne Passwort-Anforderungen |
| (e) | Dritte | Einwilligung vor Anbieterkontakt, Drittlandtransfer, politische Signalwirkung |
| (f1) | eigene JSON-Datei | nichts über den ohnehin bestehenden Bedarf hinaus |
| (f2) | eigene Datenbank | Umgang mit abgelehnten Anfragen, Löschfrist |

---

## 4. Vergleich

### 4.1 Übersicht

| | Eigener Code | Infrastruktur | Fremdabhängigkeit | Aufwand | Betrieb danach | Reversibilität |
| --- | --- | --- | --- | --- | --- | --- |
| **(a1)** Client im Bestandsrealm | keiner | keine | hoch (Realm-Betreiber) | 1–2 h | null | vollständig |
| **(a2)** eigener Realm | 0 h bzw. 12–20 h bei Parallelbetrieb | keine eigene | **hoch, dauerhaft** | 2–20 h | **gering** | mittel |
| **(b)** eigener IdP | ~0 h Anwendungscode | **hoch** (Dienst, DB, DNS, TLS, Backup, SMTP) | einmalig hoch, danach gering | 24–48 h | **hoch** | mittel–gut |
| **(c)** Self-Registration + Mailverifikation | **sehr hoch** | mittel (DB im BFF, SMTP) | **gering** | 40–70 h | mittel–hoch | gering–mittel |
| **(d)** Magic Link | hoch | mittel (DB im BFF, SMTP) | **gering** | 30–55 h | mittel | **gut** |
| **(e)** Social/OIDC | mittel | keine | **hoch, verteilt** | 8–16 h + 3–6 h je Anbieter + 10–16 h Mapping | gering | gut (Code) / schlecht (Nutzer) |
| **(f1)** Anfrage per Mail, Texte anpassen | **minimal** (nur Text) | keine | minimal (ein Postfach) | 1–3 h | **wächst linear mit der Nutzerzahl** | vollständig |
| **(f2)** Anfrage-Formular + Admin-Freischaltung | mittel | mittel (DB im BFF) | gering | 20–35 h | personengebunden | hoch |

### 4.2 Die beiden ausdrücklich verlangten Benennungen

**Geringste Änderung an bestehendem Code: (a1), (a2) ohne Parallelbetrieb und (b) —
gleichauf bei null Zeilen Anwendungscode.**

Das ist kein Näherungswert. Der BFF spricht generisches OIDC über den
Standard-Handler; Issuer, Client-ID und Secret kommen aus der Konfiguration
(`Program.cs:42`) und stehen nicht im Repository. Ein anderer Realm oder ein völlig
anderer Identitätsanbieter ist eine Änderung an drei Umgebungsvariablen im Salt-Pillar.
Der einzige realistische Codeeingriff wäre ein abweichendes Claim-Mapping in
`ClaimUtilities` (`Program.cs:683–698`) — zwei Methoden.

Diese drei unterscheiden sich massiv im *Gesamtaufwand* — (b) verlangt einen neuen
produktiven Dienst — aber nicht in der Menge des zu ändernden Anwendungscodes.

Rechnet man Infrastruktur mit, ist **(f1) die kleinste Gesamtänderung überhaupt**: eine
Handvoll Zeilen Fließtext in `login-selector.component.html`, sonst nichts. Sie
verschiebt das Problem allerdings vollständig in den laufenden Betrieb.

**Geringste Abhängigkeit von Dritten: (c) und (d).**

Beide brauchen keinen Identitätsanbieter, keine fremde Realm-Verwaltung, keine
Client-Registrierung bei einer Plattform und keine fremde Nutzerbasis. Die einzige externe
Abhängigkeit ist ein Versandweg für E-Mails plus DNS-Einträge auf der eigenen
Absenderdomain — beides austauschbar, ohne dass sich am Zugangsmodell etwas ändert. Unter
den beiden hat **(d)** die etwas geringere Abhängigkeit, weil kein Passwortbestand
entsteht, der einen späteren Wechsel blockiert.

**(f1)** hätte formal noch weniger Abhängigkeit — ein Postfach genügt —, ist aber keine
Selbstbedienungslösung und beantwortet die eigentliche Frage nicht.

**Diese beiden Kriterien fallen maximal auseinander, und das ist die eigentliche
Entscheidung:**

```
    wenig eigener Code                            viel eigener Code
    viel Fremdabhängigkeit                        wenig Fremdabhängigkeit
    ├─────────────────────────────────────────────────────────────────┤
   (a1) (a2)        (e)          (b)         (f2)        (d)        (c)
```

(a) und (e) minimieren die eigene Arbeit und maximieren die Abhängigkeit von Dritten.
(c) und (d) tun das genaue Gegenteil. (b) ist der Sonderfall: wenig Anwendungscode, wenig
dauerhafte Fremdabhängigkeit — bezahlt mit dem höchsten Betriebsaufwand aller Optionen.
(f) liegt außerhalb dieser Achse, weil es Aufwand nicht in Code, sondern in
wiederkehrende Handarbeit umwandelt.

### 4.3 Was bei jeder Option gleich bleibt

Vier Posten sind optionsunabhängig und sollten bei der Aufwandsschätzung nicht der
jeweiligen Option zugerechnet werden:

| Posten | Aufwand | Warum |
| --- | --- | --- |
| Rechtstexte vervollständigen | redaktionell/juristisch | 22 Platzhalter, unabhängig vom Zugangsmodell |
| Nutzertabelle mit interner ID im BFF | 10–16 h | macht jede spätere Auth-Entscheidung reversibel; bei (e) zwingend |
| Autorisierungs-Pipeline im Nicht-Keycloak-Zweig (`Program.cs:489–528`) | 2–4 h | betrifft (c), (d), (f2); heute nur zufällig dicht |
| Anzeigename bzw. Attribution im Datenmodell | eigenes Vorhaben | fehlt komplett, unabhängig von der Anmeldung |

---

## 5. Offene Punkte, die die Entscheidung beeinflussen

1. **Wer betreibt GutGesagt rechtlich?** Netzbegrünung e.V. oder eine andere Trägerschaft?
   Ohne diese Antwort lassen sich weder Impressum noch die Verantwortlichkeitsfrage bei
   Option (a) klären.
2. **Soll der bestehende Netzbegrünung-Login erhalten bleiben?** Falls ja, ist bei jeder
   Option außer (a1) ein Parallelbetrieb zweier Anmeldewege zu bauen — das sind die 7
   Dateien aus [1.1](#wie-viele-stellen-ändern-sich-bei-einem-anderen-idp-oder-einem-zweiten-realm)
   und erhöht (c), (d), (e) und (f2) jeweils um 12–20 h.
3. **Ist das Verdigado-Admin-Team bereit**, einen eigenen Realm anzulegen und dauerhaft
   zu pflegen (a2), bzw. einen zusätzlichen Dienst auf die Maschine zu lassen (b)? Beides
   ist Voraussetzung, nicht Ergebnis der Entscheidung.
4. **Gibt es einen nutzbaren Mailversand?** Ohne einen solchen sind (c), (d) und die
   Ausbaustufe von (f) nicht umsetzbar — der Stack kann heute keine einzige E-Mail
   verschicken.
5. **Wie viel Moderationslast ist tragbar?** Vorhanden sind Meldefunktion, Report-Tabelle
   und Admin-Oberfläche, jedoch zugeschnitten auf eine kleine, bekannte Nutzerschaft. Das
   Rate-Limit schlüsselt auf `X-User` und bremst pro Konto, nicht die massenhafte Anlage
   von Konten. Eine offene Anmeldung ohne Vorprüfung verändert dieses Risiko qualitativ.
6. **Soll eine Attribution wie „KV Bayreuth“ an Beiträgen erscheinen?** Falls ja, ist das
   ein eigenes Vorhaben im Datenmodell und beeinflusst die Optionswahl insofern, als ein
   selbst kontrolliertes Profil ((b), (c), (d), (f2)) beliebige Zusatzfelder erlaubt,
   während ein fremder Realm ((a)) dafür ein Custom-Attribut und einen Claim-Mapper beim
   Betreiber braucht.

---

## 6. Was aus dem Repo nicht verifizierbar war

Ausdrücklich als ungeprüft gekennzeichnet, weil außerhalb dieses Repositories:

- **Der konkrete Produktionswert von `USE_KEYCLOAK`.** Alle im Repo eingecheckten
  Konfigurationen — `appsettings.json`, `launchSettings.json`,
  `docker-compose.dev.yml:112`, `docker-compose.tst.yml:66` — setzen `false`. Dass
  Produktion `true` fährt, steht in `docs/DEPLOYMENT.md:15` und `STATUS.md:17`, ist aber
  nicht in einer Konfigurationsdatei dieses Repos belegt.
- **Realm-Name, Issuer-URL, Client-ID und Client-Secret der Produktion.** Liegen im
  SaltStack-Repo der Verdigado bzw. in Passbolt (`docs/DEPLOYMENT.md:133`, `:152`).
- **Ob der Realm `user.netzbegruenung.de` Self-Registration, Identity Brokering oder
  Custom-Attribute unterstützt bzw. erlaubt.** Das ist eine Frage der Realm-Konfiguration
  und der Betreiber-Bereitschaft, nicht des Codes.
- **Ob auf den Produktionsmaschinen ein SMTP-Relay verfügbar ist.**
- **Der Inhalt des produktiven `managed-users.json`.** Die eingecheckte Datei enthält zwei
  offensichtliche Testkonten (`test.user@example.com`, `admin@contentgruen.com`); im
  Produktions-Compose wird `./config` gemountet, dessen Inhalt auf dem Server liegt.

---

## Anhang: Belegstellen

| Thema | Fundstelle |
| --- | --- |
| Auth-Schalter | `mvp/backend/BFF/Program.cs:18`, `:39`, `:489` |
| OIDC-Konfiguration | `mvp/backend/BFF/Program.cs:42–128` |
| Claim-Extraktion | `mvp/backend/BFF/Program.cs:683–698` |
| `X-User`-Weitergabe | `mvp/backend/BFF/Program.cs:243–283` |
| Öffentliche Endpunkte | `mvp/backend/BFF/Program.cs:247–258`, `:501–511` |
| Anmelde-Endpunkte | `mvp/backend/BFF/Controllers/AuthController.cs:30`, `:43`, `:109`, `:123` |
| Hauseigene Nutzerverwaltung | `mvp/backend/BFF/Services/ManagedUserService.cs`, `Models/ManagedUser.cs` |
| Nutzerbasis und Erzeugung | `mvp/config/managed-users.json`, `mvp/config/generate-user-config.py` |
| Login-Auswahlseite | `src/app/login/login-selector.component.{ts,html}` |
| Frontend-Auth | `src/app/auth/{auth.service.ts,auth.guard.ts,admin.guard.ts,public.guard.ts}` |
| Autor am Inhalt | `app/domain/models/base_content.py:42–100`, `app/domain/models/author_entry.py` |
| Autor-Filter | `app/repositories/implementations/qdrant/base_repository.py:319`, `:389` |
| Stimmen-Tabelle | `app/repositories/vote_repository.py:23–34` |
| Nutzungsereignisse | `app/repositories/usage_tracking_repository.py:28–83`, `:137 ff.` |
| User-ID-Validierung | `app/auth/authorization.py:16–93` |
| Admin-Prüfung | `app/dependencies.py:219–235` |
| Rate-Limiting | `app/middleware/rate_limit.py`, `app/utils/rate_limiter.py` |
| Rechtstexte | `src/app/{impressum,datenschutz,nutzungsbedingungen}/*.component.html` |
| Deployment und Salt | `docs/DEPLOYMENT.md:113–176` |
