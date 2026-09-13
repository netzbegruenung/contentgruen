# Nachlese Destillier-Ablauf v1

Stand: 13.09.2026. Gesammelt bei der Analyse und Umsetzung des Destillier-Ablaufs
(Titel als Behauptung, Entwurf/Status im Backend, Destillier-Ansicht). Nichts davon ist
Teil von v1. Pfade relativ zu `mvp/backend/semantic-search-service/app/` (`app/`) und
`mvp/frontend/contentgruen-frontend/src/app/` (`fe/`).

## 1. Datenschutz – muss nachgezogen werden

Mit v1 entstehen neue personenbezogene Daten. Die Rechtstexte wurden bewusst nicht
angefasst.

- **Datenschutzerklärung, Abschnitt „Einwürfe in den Fangkorb“**
  (`fe/datenschutz/datenschutz.component.html:342-369`). Bisher steht dort nur der
  Einwurf selbst. Neu sind:
  - `processed_by` / `processed_at`: Wer einen Einwurf verarbeitet hat, ist für alle
    Angemeldeten sichtbar (über `GET /rawinput/getRawInputs`, analog zu `submitted_by`).
  - die Verknüpfung Einwurf → Beitrag (`raw_input_content_links`).
  - Entwurfssätze (`raw_input_drafts`): je Person gespeichert, nur für diese Person
    sichtbar, ohne Löschfrist.
- **`docs/DATENSCHUTZ_BESTANDSAUFNAHME.md`**
  - §1.5: `status` wird jetzt geschrieben (`discarded`, `processed`).
  - §1.6: „Wer schreibt: niemand“ stimmt nicht mehr (`PATCH /rawinput/{id}/status`).
  - neuer Abschnitt `raw_input_drafts` (`user_id`, `sentence`, `updated_at`).
- **`docs/LOESCHKONZEPT.md`** (`:25-27`, `:94-95`, `:102`): `raw_input_drafts` der
  Person löschen (`DELETE ... WHERE user_id = :uid`) und in die VACUUM-Liste aufnehmen.
  Die Nullung von `raw_input_content_links.created_by` ist schon vorgesehen.

## 2. Spätere Aufgabe: Titel in den Vektor

Heute geht nur `text` in die Einbettung (`app/repositories/implementations/qdrant/base_repository.py:231-237`,
Präfix `passage:`; Suchanfragen und Statements mit `query:`,
`app/services/embeddings/qdrant_embeddings_manager.py:273-274, 280-290, 309-315`). Der Titel
liegt nur im Payload.

- **Warum:** Der Titel ist jetzt eine Behauptung in einem Satz und damit sprachlich nah an
  Suchanfragen und Statements. Ein vorangestellter Titel im Passage-Text dürfte das
  Matching verbessern, vor allem bei kurzen Texten. Gemessen ist das nicht.
- **Kosten:** eine Codestelle plus Neuberechnung aller Vektoren (Re-Index-Skript gibt es
  nicht), Backup vorher (`scripts/backup_qdrant.py`), Vorher-/Nachher-Vergleich an einem
  kleinen Anfragesatz. Umstellung und Neuberechnung im selben Deploy, sonst mischen sich
  alte und neue Vektoren.
- **Nebenwirkung:** Der Kommentar-Dedup vergleicht Vektoren (Schwelle 0,97,
  `app/core/config.py:95`, `app/services/content/commentary_service.py:121-126`) und
  müsste neu kalibriert werden.
- `_embedding_fields` wird berechnet und geloggt, aber nie benutzt
  (`base_repository.py:78-85`) – das Log behauptet eine Konfiguration, die nicht wirkt.

## 3. Follow-ups aus der Spezifikation

- **Anzeigenamen** statt Keycloak-Kennungen in der „Von“-Spalte
  (`fe/raw-input-list/raw-input-list.component.ts:118-120`) und bei `processed_by`. Es
  gibt keine Nutzertabelle; das BFF reicht keinen Namen weiter
  (`mvp/backend/BFF/Proxy/IdentityHeaderTransform.cs:40-47`).
- **Kartenansicht des Fangkorbs** (ursprünglich Paket 4): vier Zustände, Typfarbe der
  fertigen Karte, Satz/Link/Name. v1 behält die Tabelle.
- **Icons.**

## 4. Gesehen bei der Analyse

### Frontend

1. Der Cache-Interceptor (`fe/auth/cache.interceptor.ts:54-59`) invalidiert nur Einträge
   mit dem eigenen Mutationspfad und ignoriert PATCH. Für den Fangkorb löst v1 das
   gezielt (`cacheService.delete('/api/v1/rawinput')`), generell bleibt es: Nach einem
   neuen Beitrag sind etwa gecachte Such- und Listenantworten bis zu 5 Minuten alt.
2. `.image-card` (`fe/contribute-view/contribute-view.component.html:112`) und
   `.image-color` (`:189-190`) sind benutzt, aber nirgends definiert.
3. Zwei verschiedene Blautöne für Hintergrundinfo:
   `fe/contribute-view/contribute-view.component.css:87-89` gegenüber
   `src/theme/custom-theme.scss:177`. Post nutzt `--generictext-bg`
   (`fe/post-result-item/post-result-item.component.scss:18`).
4. Die Mobil-Wildcards in `fe/shared/styles/_result-item-base.scss`
   (`[class*="-title"]`, `-text`, `-type`, `-references` …) treffen Klassen, für die sie
   nicht gedacht sind. Für `-header-info` ist das seit dem Titel-Umbau ausgenommen, der
   Rest besteht.
5. Desktop reserviert neben dem Titel 65 px für Badges (`_result-item-base.scss:73`),
   bis zu drei Badges brauchen rechnerisch 120 px (`:266-276`) – Überlappung möglich.
6. Post-Header ohne eigene Höhe, anders als Kommentar und Hintergrundinfo
   (`fe/post-result-item/post-result-item.component.scss:17-20`).
7. Bildtitel dürfen 200 Zeichen haben, die Karte zeigt eine Zeile mit Auslassung
   (`fe/image-result-item/image-result-item.component.scss:24-30`).
8. Das Hintergrundinfo-Formular meldet Erfolg erst nach zwei Sekunden
   (`fe/add-generictext/add-generictext.component.ts`, `setTimeout(..., 2000)` in
   `saveGenericTextForm`); im Destillier-Ablauf springt der nächste Einwurf dort
   entsprechend verzögert auf, beim Kommentar sofort.
9. `isMobile` in `fe/raw-input-list/raw-input-list.component.ts:58,71-77` wird berechnet
   und nicht benutzt.
10. Die Beitrags-Wrapper springen außerhalb des Destillier-Ablaufs nach dem Speichern
    immer nach `/contribute`, auch wenn sie über `/workflow/*` aufgerufen wurden.
11. **Beobachten:** Die Titelbox ist mobil auf vier Zeilen festgelegt. Gemessen passen bei
    390 px Breite 105–110 Zeichen, bei 360 px 85–100; längere Titel werden mit Auslassung
    gekürzt.

### Backend

12. Rate-Limiter: ein Zähler je Person für alle Pfade, nur im Speicher, Pfadvergleich per
    Teilstring (`app/middleware/rate_limit.py:25-46`). Ein neuer Beitrag und ein Einwurf
    teilen sich also das Kontingent von 10 pro Minute.
13. Der Kommentar-Router ignoriert `was_new`; der stille Dedup (0,97) meldet dem Nutzer
    Erfolg und liefert die ID eines fremden Kommentars (`app/api/v1/commentary.py:153-163`).
    Im Destillier-Ablauf verweist die Verknüpfung dann auf diesen Kommentar.
14. Hintergrundinfo hat keine Ähnlichkeitsprüfung (`app/services/content/generic_text_service.py:83`).
15. Der Bild-Endpunkt hat kein `response_model` und baut die Antwort von Hand
    (`app/api/v1/image.py:72, 108-123`).

### Daten und Doku

16. Seed-Titel sind überwiegend Etiketten statt Behauptungen (58 von 94 Kommentaren
    umzutiteln, 19 grenzwertig); `Generationen-Weisheit` steht doppelt in
    `mvp/data/seed/v1.0/statements_with_commentaries/top10.json`; „Stadtflucht dank
    Grüner Politik“ lässt sich gegen die eigene Position lesen. Ob es einen Update-Weg für
    Titel bestehender Einträge gibt, ist ungeklärt.
17. Veraltete Doku: `docs/ROHINPUT.md:3-4` („Nichts davon ist implementiert“),
    `docs/DATENSCHUTZ_BESTANDSAUFNAHME.md` verweist auf `dtos/raw_input.py:97` (tatsächlich
    `:102`, seit v1 verschoben).
18. Der lokale Dev-Stack enthielt drei Testeinträge vom 13.08. („Testinhalt Quellen-Flush“,
    „Quellentest gt7“, „Quellentest verify2“).

### Betrieb

19. Test liefert auf `/api/v1/*` ohne Anmeldung die App-Startseite mit Status 200, auch für
    den öffentlichen `getMetrics` – ein Monitoring auf Statuscodes übersieht dort Ausfälle.
20. Dev-VM: Die Shell des Agent-Harness erbt ein veraltetes `SSH_AUTH_SOCK` statt
    `~/.ssh/agent.sock`; `git push` scheitert dann mit `Permission denied (publickey)`,
    bis der stabile Pfad für den Aufruf gesetzt wird.
