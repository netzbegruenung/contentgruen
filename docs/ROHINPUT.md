# Rohinput ("Fangkorb") — Analyse und Entwurf

> Status: **Entwurf, Phase 1 (Analyse).** Nichts davon ist implementiert. Das Dokument
> beantwortet fünf Fragen: Wo gehört Rohinput ins Modell, wo liegt der Übergang zum
> fertigen Beitrag, welche Felder braucht er, was ist die kleinste sichtbare Umsetzung,
> und was am Datenmodell würde eine spätere Queue mit Zuweisung und Punkten blockieren.
> Companion zu [CONTENT_MODEL.md](./CONTENT_MODEL.md) (Architektur) und
> [ROADMAP.md](./ROADMAP.md) (Reihenfolge).

## Die Idee in einem Satz

Wer einen guten Post sieht, soll ihn in drei Sekunden ablegen können — Link, Screenshot
oder ein Satz — ohne ihn sofort zu destillieren. Das Destillieren (Argument herausarbeiten,
Metadaten, Quellen) passiert später und möglicherweise von jemand anderem.

Das ist keine neue Inhaltsart, sondern eine **Trennung von Erfassung und Verarbeitung**.
Diese Unterscheidung trägt die ganze Analyse: Rohinput ist kein halbfertiger Beitrag,
sondern ein *Arbeitsauftrag mit Anhang*.

---

## 1. Befunde: was das bestehende Modell erzwingt

Sechs Eigenschaften des heutigen Systems bestimmen, welche Variante teuer wird und welche
billig. Alle sind im Code nachgeprüft.

**B1 — Es gibt genau eine Qdrant-Collection.** Trotz `index_name` in jeder Spec liegen alle
Typen in `content_collection`; getrennt wird nur über das Payload-Feld `content_type`
(`repositories/implementations/qdrant/base_repository.py:60-83`). "Ein eigener Index für
Rohinput" existiert als Option nicht.

**B2 — Jedes Speichern erzeugt ein Embedding.** `upsert` reicht den Text an
`upsert_batch` weiter, das unbedingt `encode_text` aufruft
(`base_repository.py:199-241`, `services/embeddings/qdrant_embeddings_manager.py:294-337`).
Es gibt keinen Weg, etwas in Qdrant abzulegen, ohne es zu vektorisieren. Bei leerem Text
entsteht ein `""`-Vektor — beim captionless Bild bewusst in Kauf genommen, als Muster aber
nicht schön: ein Fangkorb voller Rohlinks legt Rausch-Vektoren in dieselbe Collection, aus
der die Suche zieht.

**B3 — Die Suche ist eine explizite Liste, kein Automatismus.** `/searchByText` durchsucht
nur Typen, die in der Spec-Liste in `api/v1/search.py:167-199` stehen. Ein neuer
`ContentType` taucht dort **nicht** von selbst auf. Zusätzlich filtert jede Suche drei
Status heraus (`PENDING_DESCRIPTION`, `DESCRIPTION_FAILED`, `PENDING_REVIEW`,
`base_repository.py:111-140`). Es gibt also zwei erprobte Hebel, um Inhalte unsichtbar zu
halten.

*Aber:* die aggregierten Endpunkte `/api/v1/content/searchContent` und
`/api/v1/content/getAll` laufen über das Repository mit `content_type=None` und sehen
**alles**. Das Frontend benutzt beide heute nicht (nur `/content/recent`, das auf
Commentary + GenerictText hartkodiert ist, `api/v1/content.py:97-200`), über den
BFF-Catch-all sind sie aber erreichbar.

**B4 — "Meine Beiträge" ist typ-blind.** `/getContributionsOfUser` benutzt das aggregierte
Repository (`api/v1/contribution.py:24-60`), filtert also **jeden** Content-Type mit
passendem `original_author` heraus. Ein neuer Typ erscheint dort automatisch. Es gibt genau
eine Ausnahme, und die ist der Präzedenzfall für unseren Fall: Suchanfragen werden über
`must_not origin = search_query` ausgeblendet, weil sie „kein Beitrag" sind
(`base_repository.py:31-46`, dokumentiert in `domain/models/content_origin.py`).

**B5 — Zwei Zähler zählen aggregiert.** `total_records_count` in „Meine Beiträge"
(`getCountByAuthor`, dieselbe Filterlogik) speist die Kacheln *Beiträge* und *Durchschnitt*
(`contributions-view.component.html:14-22`), und `content_count` im Metrics-Endpunkt ist ein
aggregiertes `count()` (`api/v1/metrics.py:121`). Beide würden Rohinput mitzählen. Nicht
betroffen: `usage_count` (PostgreSQL, zählt Kopiervorgänge — Rohinput wird nie kopiert) und
`content_created_per_week` (basiert auf `usage_tracking.first_used`).

**B6 — Workflow-Zustand gehört heute schon nach PostgreSQL, nicht nach Qdrant.**
`content_reports` (`infrastructure/database/models.py:124-144`) ist bereits eine
Moderations-Queue mit exakt den Feldern, die eine Bearbeitungs-Queue braucht: `status`,
`reviewed_by`, `reviewed_at`, `resolution_notes`. Tabellen entstehen per
`Base.metadata.create_all` beim Start (`infrastructure/database/connection.py:48`), für die
Produktion gibt es das Muster datierter SQL-Migrationen
(`mvp/backend/postgres-app/migrations/`). Eine neue Tabelle ist billig.

**B7 — Es gibt keinen Datei-Upload. Nirgends.** Kein `UploadFile`/`multipart` im Backend,
kein `FormData`/`<input type="file">` im Frontend, kein Blob-Storage. Der Bildtyp nimmt eine
`image_url` auf eine öffentlich erreichbare Datei entgegen (`domain/models/image.py`). Das
trifft die Idee an einer empfindlichen Stelle: **„Screenshot ablegen" ist heute nicht
möglich** — siehe [Abschnitt 4](#4-die-kleinste-sichtbare-umsetzung).

---

## 2. Frage 1 — Wie fügt sich Rohinput ins bestehende Modell?

### Variante A — Neuer `ContentType` in der Registry

Ein Eintrag in `REGISTRY` (`domain/content_registry.py`), ein `RawInputDbEntry`, ein
Router — genau der Weg, den Post und Image gegangen sind.

| Dimension | Konsequenz |
|---|---|
| **Suche** | Nicht automatisch drin (B3) — der Typ wird schlicht nicht in die Spec-Liste eingetragen. Aber: über `/content/searchContent` und `/content/getAll` sichtbar; wer den Typ später doch suchbar machen will, hat einen Schalter. |
| **Embeddings** | Zwang (B2). Jede Ablage kostet einen E5-Call, jeder reine Link erzeugt einen Rausch-Vektor in der produktiven Collection. Kein Fehler, aber Ballast, der mit der Menge wächst — und der Fangkorb soll ja viel Volumen haben. |
| **Meine Beiträge** | Erscheint automatisch (B4), gemischt mit fertigen Beiträgen, in einer Tabelle mit den Spalten Text/Nutzung. Braucht entweder eine bewusste Ausnahme (zweiter `must_not`-Filter, nach dem Suchanfragen-Muster) oder eine Umgestaltung der Ansicht. |
| **Zähler** | Verzerrt `total_records_count` und `content_count` (B5). Die Kachel „Durchschnitt" (Gesamtnutzung ÷ Beiträge) sinkt mit jedem Einwurf — ausgerechnet die Zahl, die Mitwirkende belohnen soll, wird durchs Mitwirken schlechter. Behebbar, aber es ist die zweite Ausnahme derselben Bauart. |
| **Aufwand** | Am kleinsten im Backend (~1/2 Tag, erprobtes Muster). |
| **Später** | Schwach: siehe [Abschnitt 6](#6-frage-5--was-eine-sp%C3%A4tere-queue-blockieren-w%C3%BCrde). Qdrant kann kein atomares „Claim". |

### Variante B — Eigener Status an bestehenden Typen

Rohinput ist ein `generic_text` (o. ä.) im Status `RAW`, den die Verarbeitung auffüllt.

| Dimension | Konsequenz |
|---|---|
| **Suche** | Sauber lösbar: ein weiterer Status im `must_not`-Filter, genau ein Ort, exaktes Vorbild `PENDING_DESCRIPTION` (B3). |
| **Embeddings** | Zwang wie A; beim Fertigstellen wird derselbe Punkt neu geschrieben und neu vektorisiert — technisch elegant, der Rohinput *wird* der Beitrag. |
| **Meine Beiträge** | Wie A: automatisch drin, gleiche Verwässerung. |
| **Zähler** | Wie A. |
| **Aufwand** | Scheinbar am kleinsten — bis man die Pflichtfelder sieht. |
| **Kern-Einwand** | **Man muss beim Einwerfen den Zieltyp wählen.** „Ist das ein Kommentar oder eine Hintergrundinfo?" ist genau die Destillier-Entscheidung, die die Idee vermeiden will. Dazu kommen Pflichtfelder (`title` min. 3 Zeichen, `references`-Liste, bei Commentary `style`), eine Statusmaschine, die erweitert werden müsste (`is_valid_transition`), und ein Typwechsel bei der Verarbeitung, der ein Löschen+Neuanlegen ist, weil die Modelle andere Felder haben. |

Variante B verliert nicht an der Technik, sondern am Ziel: Sie modelliert Rohinput als
halbfertigen Beitrag und zwingt ihm damit dessen Korsett auf.

### Variante C — Eigene Entität außerhalb (PostgreSQL-Tabelle `raw_inputs`)

Rohinput ist überhaupt kein Content, sondern ein Arbeitsvorrat neben dem Content —
strukturell wie `content_reports` (B6).

| Dimension | Konsequenz |
|---|---|
| **Suche** | Gar nicht betroffen. Kein Vektor, kein Filter, keine Spec, kein Risiko fürs Kernprodukt. Preis: keine semantische Suche *im* Fangkorb (Dublettenerkennung „hat das schon jemand eingeworfen?" gibt es erst, wenn man sie baut). |
| **Embeddings** | Keine. Das Einwerfen ist ein reiner INSERT — der schnellste denkbare Pfad, passend zum 3-Sekunden-Anspruch, und keine Rausch-Vektoren. |
| **Meine Beiträge** | Erscheint **nicht** — muss man wollen. Der Fangkorb bekommt eine eigene Liste. Ein späteres Zusammenführen („12 eingeworfen, 4 davon verarbeitet") ist eine bewusste Entscheidung statt eines Nebeneffekts. |
| **Zähler** | Unberührt. `content_count` bleibt „echte Inhalte", die Durchschnitts-Kachel bleibt ehrlich. |
| **Aufwand** | Im Backend etwas größer als A (Tabelle + Repository + Service + Router, kein Registry-Rabatt), aber ohne Ausnahmen. Der Unterschied verschwindet im Gesamtaufwand — siehe [Abschnitt 5](#5-aufwand). |
| **Später** | Am stärksten: relationale Transaktionen erlauben ein atomares Claim, eine n:m-Verknüpfungstabelle und eine Punkte-Ereignistabelle nach dem Vorbild von `usage_events`. |

### Empfehlung: Variante C

Drei Gründe, in absteigender Wichtigkeit:

1. **Rohinput ist kein Inhalt, sondern Arbeit.** Er wird nicht gesucht, nicht kopiert, nicht
   bewertet, nicht moderiert. Alles, was `BaseContentDbEntry` mitbringt — Score, Votes,
   Report-Flags, Visibility, Edit-History, Vektor — ist für ihn tot. Ihn dort einzuhängen
   heißt, 20 Felder zu erben, um 5 zu benutzen, und dafür an drei Stellen Ausnahmen zu
   pflegen (Suche, Meine Beiträge, Zähler).
2. **Die Zähler-Verwässerung ist kein Detail.** Die Kacheln in „Meine Beiträge" sind die
   einzige Anerkennung, die das System heute ausschüttet. Ein Feature, das sie beim Benutzen
   verschlechtert, wird nicht benutzt.
3. **Die spätere Queue entscheidet die Wahl.** Zuweisung („ich nehm das") ist ein
   Wettlauf zweier Nutzer um dieselbe Zeile. PostgreSQL löst das mit einer Transaktion;
   Qdrant hat dafür kein Werkzeug (B2/B6). Wer die Queue will, baut sie in Variante A/B
   später *doch* in PostgreSQL — dann aber mit dem Zustand an zwei Orten.

**Gegenargument, ehrlich benannt:** Variante C gibt die Registry-Ersparnis auf, die
CONTENT_MODEL.md gerade erst erkämpft hat, und man schreibt ein Repository von Hand. Das ist
der richtige Preis, weil der Registry-Pfad Suchbarkeit *voraussetzt* — er ist die Antwort auf
„noch eine Inhaltsart", nicht auf „noch ein Arbeitsschritt". Rohinput ist Letzteres. Sollte
sich später zeigen, dass der Fangkorb doch durchsuchbar sein muss, ist der Weg C → A offen:
beim Verarbeiten (oder nachträglich per Backfill) einen Content-Eintrag erzeugen. Der
umgekehrte Weg — Workflow-Zustand aus Qdrant herausoperieren — ist teurer.

---

## 3. Frage 2 — Wo liegt der Übergang zum fertigen Beitrag?

Drei Möglichkeiten: Der Rohinput wird **konsumiert** (verschwindet), er **bleibt als
Herkunft** (der Beitrag zeigt auf ihn), oder **beides** (er bleibt, verschwindet aber aus der
Queue).

**Empfehlung: beides.** Der Rohinput wird nie gelöscht; er bekommt einen Status
(`offen → in_arbeit → verarbeitet | verworfen`) und eine Verknüpfung zu dem, was aus ihm
entstanden ist. Aus dem Fangkorb verschwindet er, aus der Datenbank nicht.

Das ist nicht Ordnungsliebe, sondern eine Anforderung aus dem, was später darauf aufsetzen
soll:

- **Punkte für verarbeitete Beiträge** brauchen einen Beleg, *wer eingeworfen* und *wer
  verarbeitet* hat. Wird der Rohinput beim Verarbeiten konsumiert, ist die Finder-Rolle
  verloren — der fertige Beitrag kennt nur noch seinen Autor. Die Punkte für den Finder wären
  nicht mehr rekonstruierbar.
- **Verworfene Rohinputs sind Information.** Ein Link, den schon dreimal jemand angeschaut
  und weggelegt hat, soll nicht ein viertes Mal in der Queue auftauchen.
- **Doppelte Einwürfe** („den Post hat gestern schon jemand geschickt") lassen sich nur
  erkennen, wenn der alte Eintrag noch da ist.

**Die Verknüpfung muss n:m sein.** Ein Rohinput kann mehrere Beiträge hervorbringen (ein
Thread → ein Kommentar *und* eine Hintergrundinfo), und ein Beitrag kann aus mehreren
Rohinputs entstehen. Ein einzelnes Feld `resulting_content_id` wäre genau die Blockade, die
Frage 5 sucht — deshalb eine Verknüpfungstabelle `(raw_input_id, content_id, created,
created_by)`. Sie ist billig, solange sie von Anfang an so gedacht ist, und teuer, wenn man
sie aus einem Fremdschlüssel nachträglich herausschält.

Ob der fertige Beitrag die Herkunft **anzeigt** („aus einem Einwurf von X"), ist eine
Produktentscheidung für später; das Datenmodell soll sie nur nicht verbauen.

---

## 4. Frage 3 — Welche Felder braucht Rohinput minimal?

### Der Kern

| Feld | Warum | Schon modelliert? |
|---|---|---|
| `id` | — | überall (UUID) |
| `content` (Text) | Der eine Satz *oder* die Notiz zum Link. Nullable. | `BaseContent.text` — aber dort **Pflichtfeld** |
| `url` | Der Link auf den Post | `Reference.reference_string`, `Post.url`, `Image.image_url` — dreimal, in drei Modellen, ohne gemeinsame Basis |
| `image_url` | Screenshot — **siehe Einschränkung unten** | `Image.image_url` (nur URL, kein Upload) |
| `submitted_by` | Wer eingeworfen hat | `original_author` + `authors: List[AuthorEntry]`; `X-User`-Header ist die einzige Identität im System |
| `created` | Wann | überall |
| `status` | offen / in Arbeit / verarbeitet / verworfen | `ContentStatus` — passt aber nicht: dessen Zustände beschreiben Moderation, nicht Bearbeitung |
| `source_channel` | web / share / mail — für den Instagram-Eingang | nirgends. `ContentOrigin.INGESTED` existiert und wird von niemandem benutzt |

**Mindestens eines von `content`, `url`, `image_url` muss gefüllt sein** — das ist die einzige
Validierungsregel, die der Fangkorb verträgt. Jede weitere Pflicht (Titel, Kategorie, Thema)
ist eine Destillier-Entscheidung und gehört nicht in den Einwurf.

### Was sich wiederverwenden lässt — und was nicht

- **Wiederverwendbar:** `AuthorEntry` (hat ein `role`-Feld — brauchbar, um später *Finder*
  von *Bearbeiter* zu unterscheiden), die `X-User`-Konvention, der `AuthGuard`, das
  BFF-Catch-all-Routing (ein neuer Backend-Endpunkt braucht **keine** BFF-Änderung).
- **Vorbild, nicht Wiederverwendung:** `CommentaryReference` ist das existierende Muster für
  „Verknüpfung mit Notiz, die nur für diesen Beitrag gilt" — konzeptionell die Vorlage für
  die n:m-Tabelle aus Abschnitt 3, technisch aber an Commentary/GenericText gebunden.
- **Nicht wiederverwendbar:** `BaseContentDbEntry` als Ganzes (siehe Abschnitt 2, Grund 1).
  Es gibt keine schlanke gemeinsame Basis für „hat eine URL"; die drei URL-Felder sind
  unabhängig gewachsen.

### Die Einschränkung, die benannt werden muss: Screenshots

**„Screenshot ablegen" ist heute technisch nicht möglich** (B7). Es gibt im ganzen Stack
keinen Datei-Upload und keinen Ort, an dem eine Datei liegen könnte. Der Bildtyp umgeht das,
indem er eine öffentlich erreichbare URL verlangt — was für kuratierte Bilder funktioniert
und für „ich mach schnell einen Screenshot" nicht.

Drei Wege, keiner davon in der kleinsten Umsetzung enthalten:

1. **Bild-URL statt Datei** (Rechtsklick → Bildadresse kopieren). Kostet nichts, deckt den
   Fall „Post-Bild" ab, den Fall „Screenshot" nicht.
2. **Ein Volume + statisches Ausliefern über nginx.** ~1 Tag; braucht Größenlimit,
   Content-Type-Prüfung, Aufräumen, Backup-Einbindung.
3. **Objektspeicher (MinIO/S3).** Sauberste Lösung, größte Abhängigkeit; erst sinnvoll, wenn
   auch der Instagram-Eingang kommt, der ebenfalls Bilder anliefert.

Empfehlung: Phase 1 mit **Link + Text + optionaler Bild-URL** ausliefern, den Upload als
eigenen, sichtbar getrennten Schritt planen — und im UI nicht so tun, als ginge es schon.

### Nebenbemerkung, keine Blockade

Ein Fangkorb sammelt fremde Inhalte (Posts namentlich bekannter Personen) wörtlich und
dauerhaft. Der `post`-Typ tut das heute schon, der Fangkorb würde es in größerem Volumen und
ohne Kuratierung tun. Das berührt die offenen Punkte in
[RECHTSTEXTE_LUECKEN.md](./RECHTSTEXTE_LUECKEN.md) (Urheberrecht, personenbezogene Daten,
Löschkonzept). Kein Grund, nicht zu bauen — aber der interne Charakter des Fangkorbs
(`ContentVisibility.INTERNAL` ist Default) sollte eine bewusste Zusage bleiben, keine
Voreinstellung, die irgendwann jemand umstellt.

---

## 5. Frage 4 — Die kleinste sichtbare Umsetzung

**Umfang: Einwerfen und Liste. Sonst nichts.** Keine Queue, keine Zuweisung, keine Punkte,
kein Verarbeiten-Knopf, kein Upload. Der Status wird gespeichert, aber nur `offen` gesetzt.

### Backend

- Tabelle `raw_inputs` (SQLAlchemy-Modell → `create_all` legt sie an; datierte
  SQL-Migration für die Produktion nach Vorbild `migrations/2026-08-19-*.sql`).
- Repository nach Vorbild `repositories/content_report_repository.py`.
- Router `api/v1/raw_input.py` mit `POST /addRawInput` und `GET /getRawInputs`
  (paginiert, neueste zuerst), in `main.py` eingehängt.
- `/addRawInput` in die Pfadliste der Rate-Limit-Middleware aufnehmen
  (`middleware/rate_limit.py:31-41`) — ein 3-Sekunden-Einwurf ist per Konstruktion
  spam-anfällig.
- **BFF: keine Änderung.** Das Catch-all leitet `/api/v1/**` weiter und setzt `X-User`; nur
  wer anonymen Zugriff will, müsste die Public-Liste anfassen — will man hier nicht.

### Frontend

Der Ort ist die eigentliche Produktfrage. `contribute-view` ist eine *Kategorienauswahl* für
fertige Beiträge (Karten mobil, Akkordeon am Desktop) — eine vierte Karte „Fangkorb" wäre
billig, würde den Einwurf aber hinter genau die Auswahl stellen, die er vermeiden soll.

**Empfehlung:** ein eigener, immer erreichbarer Einwurf.

- **Eingabe:** Route `/einwerfen` + Eintrag in Kopfzeile und Mobil-Menü (die Navigation
  läuft über Events in `app.component.html` / `mobile-header` / `mobile-menu` — mehrere
  kleine Dateien). Ein Formular: **ein** Textfeld für Link *oder* Satz (beides darf drin
  stehen), ein optionales Feld für eine Bild-URL, ein Knopf. Kein Titel, keine Kategorie,
  keine Pflichtfelder außer „irgendetwas". Nach dem Absenden bleibt das Formular offen und
  leer, damit man drei Sachen hintereinander einwerfen kann.
- **Zusätzlich** die Karte in `contribute-view`, die auf dieselbe Route zeigt — kostet
  ~20 Zeilen und findet die Leute ab, die dort nach dem Einwurf suchen.
- **Liste:** Route `/fangkorb`, Material-Tabelle nach dem Muster von `contributions-view`
  (Spalten: Inhalt/Link, von wem, wann, Status; Paginator; neueste zuerst). Bewusst **alle**
  Einwürfe, nicht nur die eigenen: der Fangkorb ist ein gemeinsamer Vorrat, und die Liste
  ist die Vorstufe der späteren Queue.
- `raw-input.service.ts` nach Vorbild `image.service.ts` (~40 Zeilen).

### Aufwand

Agentengestützt, eine Person, inkl. Tests und Review — Spanne, keine Zusage:

| Teil | Aufwand |
|---|---|
| Backend (Tabelle, Repository, Router, Migration, Rate-Limit) | 0,5–1 Tag |
| Tests (Unit für Repository/Service, API-Test; Vorbilder in `tests/integration/test_post_type.py` ≈ 157 Zeilen) | 0,5 Tag |
| Frontend Einwurf + Liste + Navigation + Service | 1–1,5 Tage |
| Politur, Mobil, Durchstich am Dev-Stack | 0,5 Tag |
| **Summe** | **2,5–3,5 Tage** |

**Wichtig für die Variantenwahl:** Variante A (Registry-Typ) spart im Backend etwa einen
halben Tag und gibt ihn für die Ausnahmen bei Zählern und „Meine Beiträge" wieder aus. Das
Frontend — der größere Posten — ist in beiden Varianten identisch. **Die Entscheidung kostet
heute praktisch nichts und unterscheidet sich erst später deutlich.** Genau deshalb sollte
sie jetzt nach dem Später entschieden werden.

Nicht enthalten und separat zu planen: Bild-Upload (1–2 Tage, siehe Abschnitt 4),
Instagram-Eingang, Queue, Punkte.

---

## 6. Frage 5 — Was eine spätere Queue blockieren würde

Nur benannt, nichts davon wird jetzt gebaut. Die Reihenfolge ist nach Schwere sortiert.

1. **Workflow-Zustand in Qdrant-Payloads.** `assignee` und `claimed_at` ändern sich häufig;
   ein Qdrant-Upsert schreibt den Punkt neu und vektorisiert neu (`update_status` ist die
   einzige Ausnahme, ein gezielter Payload-Update). Vor allem: es gibt kein
   `SELECT … FOR UPDATE`. Zwei Leute, die gleichzeitig „ich nehm das" drücken, bekommen beide
   den Zuschlag. **Das ist der stärkste Grund für Variante C.**
2. **Eine 1:1-Verknüpfung Rohinput → Beitrag.** Ein Feld `resulting_content_id` schließt aus,
   dass aus einem Einwurf zwei Beiträge werden oder aus drei Einwürfen einer. Eine
   Verknüpfungstabelle kostet jetzt nichts und später viel (Abschnitt 3).
3. **Den Rohinput beim Verarbeiten löschen oder überschreiben.** Zerstört den Beleg für die
   Finder-Punkte, die Herkunft und die Dublettenerkennung — unumkehrbar.
4. **Nur ein Autorenfeld.** `last_modified_by` wird bei jeder Änderung überschrieben, die
   Rollen *Finder* und *Bearbeiter* sind daraus nicht rekonstruierbar. `AuthorEntry.role`
   existiert und wäre der Platz dafür — heute setzt niemand eine Rolle.
5. **Punkte als Zähler statt als Ereignisse.** Ein Feld „Punktestand" ist nicht prüfbar, nicht
   korrigierbar und nicht erklärbar („wofür?"). Das Muster gibt es schon: `usage_events` ist
   eine append-only Ereignistabelle, aus der `usage_tracking` abgeleitet wird
   (`infrastructure/database/models.py:30-93`). Punkte gehören genauso gebaut.
6. **Es gibt keine Nutzertabelle.** Identität ist ein String aus `X-User` (Keycloak-ID oder
   Dummy-Login); Profile, Anzeigenamen und Punktestände haben heute keinen Ort. Punkte und
   Bestenlisten (Rung 6 der Roadmap) brauchen einen — das ist eine eigene Entscheidung mit
   DSGVO-Anteil, keine Nebenwirkung des Fangkorbs.
7. **Ein harter Login-Zwang im Datenmodell.** Der Instagram-Share-Eingang kommt über ein
   Share-Sheet, nicht über eine Browser-Session; er liefert einen Rohinput ohne interaktiven
   Login. Wenn `submitted_by` NOT NULL ist, verbaut das den Eingang. Nullable
   `submitted_by` plus ein `source_channel`-Feld halten die Tür auf — **einbauen als Feld,
   nicht als Funktion.**

---

## 7. Zusammenfassung

- **Variante C** (eigene PostgreSQL-Entität) — Rohinput ist Arbeit, kein Inhalt. Keine
  Vektoren, keine Ausnahmen in Suche, „Meine Beiträge" und Zählern, und der einzige Ort, an
  dem eine Zuweisung später atomar funktioniert.
- **Übergang:** Rohinput bleibt erhalten *und* verschwindet aus der Queue. n:m-Verknüpfung
  zum entstandenen Beitrag, weil die Punkte sonst nicht rekonstruierbar sind.
- **Felder minimal:** Text, URL, Bild-URL (mindestens eines), Einwerfer, Zeit, Status,
  Kanal. Wiederverwendbar sind `AuthorEntry`, die `X-User`-Konvention und das BFF-Routing;
  `BaseContentDbEntry` bewusst nicht.
- **Kleinste Umsetzung:** `/einwerfen` (ein Feld, ein Knopf) + `/fangkorb` (Liste),
  **2,5–3,5 Tage**. Ohne Screenshot-Upload — der ist heute nirgends im Stack möglich und
  braucht einen eigenen Schritt.
- **Nicht verbauen:** Zustand in PostgreSQL statt Qdrant, n:m statt 1:1, nichts löschen,
  Rollen an Autoren, Punkte als Ereignisse, `submitted_by` nullable plus `source_channel`.
